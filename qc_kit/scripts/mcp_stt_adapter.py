"""Step 2 adapter for environments WITHOUT an ElevenLabs API key.

Builds <project>/stt/<stem>.json in the exact format song_stt.py writes, from:
  - Scribe transcripts produced through the ElevenLabs MCP connector (words.json files
    downloaded from each transcript's words_download_url), and
  - Sarvam Saaras v4 codemix + verbatim, run here with the kit's own chunking logic.

Usage:
  python scripts/mcp_stt_adapter.py <project> <stem> <scribe_mix.json> <scribe_vocals_1.json> <scribe_vocals_2.json> [lang]
Needs SARVAM_API_KEY (env or .env).
"""
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from sarvamai import SarvamAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_env, SARVAM_LANG  # noqa: E402

env = load_env()
project, stem, f_mix, f_v1, f_v2 = Path(sys.argv[1]), sys.argv[2], *sys.argv[3:6]
lang = sys.argv[6] if len(sys.argv) > 6 else "en"


def scribe_from(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    words = [{"w": w["text"], "s": w["start"], "e": w["end"], "type": w.get("type")}
             for w in d.get("words", []) if w.get("type") != "spacing"]
    text = d.get("text") or " ".join(w["w"] for w in words if w["type"] == "word")
    return {"text": text, "lang": d.get("language_code"), "lang_prob": d.get("language_probability"),
            "words": words, "source": "elevenlabs-mcp scribe_v1"}


def load_mono16k(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def sarvam(path, mode):
    """Same chunking as song_stt.py: cut at the quietest 0.3 s window 12-25 s into each chunk."""
    client = SarvamAI(api_subscription_key=env["SARVAM_API_KEY"], timeout=60)
    x, sr = load_mono16k(path), 16000
    dur = len(x) / sr
    cuts = [0.0]
    while dur - cuts[-1] > 25:
        lo, hi = int((cuts[-1] + 12) * sr), int((cuts[-1] + 25) * sr)
        win = int(0.3 * sr)
        rms = [np.sqrt(np.mean(x[i:i + win] ** 2)) for i in range(lo, hi - win, win // 3)]
        cuts.append((lo + int(np.argmin(rms)) * (win // 3) + win // 2) / sr)
    cuts.append(dur)
    chunks = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
            c = Path(tmp) / f"c{i}.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-to", str(b), "-i", str(path),
                            "-ac", "1", "-ar", "16000", str(c)], check=True)
            for attempt in range(3):
                try:
                    with open(c, "rb") as fh:
                        r = client.speech_to_text.transcribe(file=fh, model="saaras:v4", mode=mode,
                                                             language_code=SARVAM_LANG.get(lang, "unknown"))
                    break
                except Exception:
                    if attempt == 2:
                        raise
            chunks.append({"start": round(a, 2), "end": round(b, 2), "text": r.transcript, "lang": r.language_code})
    return {"text": " ".join(c["text"] for c in chunks), "chunks": chunks}


voc = project / "stems" / "htdemucs" / stem / "vocals.wav"
res = {"scribe_mix": scribe_from(f_mix), "scribe_vocals_1": scribe_from(f_v1), "scribe_vocals_2": scribe_from(f_v2)}
for key, mode in (("sarvam_vocals", "codemix"), ("sarvam_verbatim_vocals", "verbatim")):
    try:
        res[key] = sarvam(voc, mode)
    except Exception as e:
        res[key] = {"error": repr(e)}
out = project / "stt"
out.mkdir(exist_ok=True)
(out / f"{stem}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in res.items():
    print(f"--- {k}: {v.get('error') or v['text']}")
