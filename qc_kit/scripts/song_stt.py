"""Step 2: transcribe every song 4 ways.

  scribe_mix       ElevenLabs Scribe v1 on the full song
  scribe_vocals_1  Scribe on the demucs vocal stem
  scribe_vocals_2  Scribe on the vocal stem again (Scribe is not deterministic)
  sarvam_vocals    Sarvam Saaras v4, mode "codemix", on the vocal stem (<=25 s chunks cut at quiet points).
                   codemix keeps English words in Latin letters, so it can be scored like Scribe.
  sarvam_verbatim_vocals  Saaras v4, mode "verbatim": not scored (English comes out in Devanagari),
                   but it does not tidy away extra words, so read it in the Transcripts sheet.

Usage:  python scripts/song_stt.py <project_dir> [--force] [--only <stem>]
Needs:  <project>/songs.csv, <project>/input/<song_file>, <project>/stems/htdemucs/<stem>/vocals.wav
Writes: <project>/stt/<stem>.json  (skips songs already done unless --force)
"""
import json
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import numpy as np
from sarvamai import SarvamAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_env, read_songs, SARVAM_LANG  # noqa: E402

env = load_env()
for key in ("ELEVENLABS_API_KEY", "SARVAM_API_KEY"):
    if not env.get(key):
        raise SystemExit(f"{key} is not set. Put it in .env (see .env.example).")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
PROJECT = Path(args[0])
FORCE = "--force" in sys.argv
ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
OUT = PROJECT / "stt"
OUT.mkdir(exist_ok=True)
_tl = threading.local()


def scribe(path, lang):
    with open(path, "rb") as f:
        r = httpx.post("https://api.elevenlabs.io/v1/speech-to-text",
                       headers={"xi-api-key": env["ELEVENLABS_API_KEY"]},
                       data={"model_id": "scribe_v1", "language_code": lang,
                             "timestamps_granularity": "word", "tag_audio_events": "true"},
                       files={"file": (Path(path).name, f)}, timeout=300)
    r.raise_for_status()
    d = r.json()
    words = [{"w": w["text"], "s": w["start"], "e": w["end"], "type": w.get("type")}
             for w in d.get("words", []) if w.get("type") != "spacing"]
    return {"text": d.get("text", ""), "lang": d.get("language_code"),
            "lang_prob": d.get("language_probability"), "words": words}


def load_mono16k(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def sarvam_client():
    # One client per thread: a shared client deadlocks its connection pool under threads.
    if not hasattr(_tl, "c"):
        _tl.c = SarvamAI(api_subscription_key=env["SARVAM_API_KEY"], timeout=60)
    return _tl.c


def sarvam(path, mode, lang):
    """Saaras sync calls take ~30 s max, so cut at the quietest 0.3 s window between 12-25 s into each chunk."""
    x = load_mono16k(path)
    sr = 16000
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
                        r = sarvam_client().speech_to_text.transcribe(file=fh, model="saaras:v4", mode=mode,
                                                                    language_code=SARVAM_LANG.get(lang, "unknown"))
                    break
                except Exception:
                    if attempt == 2:
                        raise
            chunks.append({"start": round(a, 2), "end": round(b, 2), "text": r.transcript,
                           "lang": r.language_code})
    return {"text": " ".join(c["text"] for c in chunks), "chunks": chunks}


def run(row):
    stem = row["stem"]
    out = OUT / f"{stem}.json"
    if out.exists() and not FORCE:
        return stem, json.loads(out.read_text(encoding="utf-8")), True
    mix = PROJECT / "input" / row["song_file"]
    voc = PROJECT / "stems" / "htdemucs" / stem / "vocals.wav"
    if not voc.exists():
        raise SystemExit(f"No vocal stem for {stem}: run demucs first (step 1).")
    lang = row["language"]
    jobs = {"scribe_mix": lambda: scribe(mix, lang),
            "scribe_vocals_1": lambda: scribe(voc, lang),
            "scribe_vocals_2": lambda: scribe(voc, lang),
            "sarvam_vocals": lambda: sarvam(voc, "codemix", lang),
            "sarvam_verbatim_vocals": lambda: sarvam(voc, "verbatim", lang)}
    res = {}
    for k, fn in jobs.items():
        try:
            res[k] = fn()
        except Exception as e:
            res[k] = {"error": repr(e)}
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return stem, res, False


rows = [r for r in read_songs(PROJECT) if not ONLY or r["stem"] == ONLY]
with ThreadPoolExecutor(4) as ex:
    for stem, res, cached in ex.map(run, rows):
        print(f"\n===== {stem}" + ("  (cached, use --force to redo)" if cached else ""))
        for k, v in res.items():
            print(f"--- {k}: {v.get('error') or v['text']}")
