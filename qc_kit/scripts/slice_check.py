"""Step 4: re-check one flagged spot on a short clip with 4 engine settings, and show word timings.

Usage:  python scripts/slice_check.py <project_dir> <song_stem> <start_s> <end_s>
  e.g.  python scripts/slice_check.py example pythagoras_rap_hindi_v2-5_take2 28.0 31.6

What it does
  1. Prints the Scribe word timings in that window (from stt/<stem>.json). A gap of
     ~0.2 s or more between two words means a word was sung there; ~0.05 s means nothing was.
  2. Cuts the window from the vocal stem (.wav) and the full song (_mix.mp3) into review_clips/.
  3. Transcribes both clips with Scribe (song language), Scribe (English), Sarvam Saaras v4 in "codemix"
     and "verbatim" modes, and Sarvam Saarika v2.5. Verbatim and Saarika write what was sung without
     tidying; they are the best at catching an extra or missing short word.
  4. Appends everything to review_clips/slice_checks.json.

Tip: start/end the window between words. A word cut in half at the clip edge comes back as junk.
"""
import json
import subprocess
import sys
from pathlib import Path

import httpx
from sarvamai import SarvamAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_env, read_songs, SARVAM_LANG  # noqa: E402

env = load_env()
project, stem, a, b = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
row = next((r for r in read_songs(project) if r["stem"] == stem), None)
if not row:
    raise SystemExit(f"{stem} is not in songs.csv")
clips = project / "review_clips"
clips.mkdir(exist_ok=True)
tag = f"{stem}_{a:.1f}-{b:.1f}s"

# 1. word timings
stt = project / "stt" / f"{stem}.json"
if stt.exists():
    words = json.loads(stt.read_text(encoding="utf-8")).get("scribe_vocals_1", {}).get("words", [])
    win = [w for w in words if a - 0.5 <= w["s"] <= b + 0.5 and w.get("type") == "word"]
    print("Scribe word timings (vocal stem, run 1):")
    prev = None
    for w in win:
        gap = f"   gap {w['s'] - prev:.2f}s" if prev is not None else ""
        print(f"  {w['s']:6.2f}-{w['e']:6.2f}  {w['w']}{gap}")
        prev = w["e"]

# 2. clips
voc_src = project / "stems" / "htdemucs" / stem / "vocals.wav"
mix_src = project / "input" / row["song_file"]
voc, mix = clips / f"{tag}.wav", clips / f"{tag}_mix.mp3"
for src, dst in ((voc_src, voc), (mix_src, mix)):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-to", str(b), "-i", str(src), str(dst)], check=True)


# 3. engines
def scribe(p, lang):
    with open(p, "rb") as f:
        r = httpx.post("https://api.elevenlabs.io/v1/speech-to-text",
                       headers={"xi-api-key": env["ELEVENLABS_API_KEY"]},
                       data={"model_id": "scribe_v1", "language_code": lang}, files={"file": (p.name, f)},
                       timeout=120)
    r.raise_for_status()
    return r.json().get("text", "")


sv = SarvamAI(api_subscription_key=env["SARVAM_API_KEY"], timeout=60)


def sarvam(p, model, mode=None):
    kw = {"mode": mode, "language_code": SARVAM_LANG.get(row["language"], "unknown")} if mode else {}
    with open(p, "rb") as fh:
        return sv.speech_to_text.transcribe(file=fh, model=model, **kw).transcript


result = {"song": stem, "start": a, "end": b, "clips": [voc.name, mix.name], "runs": {}}
for label, p in (("vocals", voc), ("mix", mix)):
    for name, fn in ((f"scribe_{row['language']}", lambda: scribe(p, row["language"])),
                     ("scribe_en", lambda: scribe(p, "en")),
                     ("saaras_codemix", lambda: sarvam(p, "saaras:v4", "codemix")),
                     ("saaras_verbatim", lambda: sarvam(p, "saaras:v4", "verbatim")),
                     ("saarika_v2.5", lambda: sarvam(p, "saarika:v2.5"))):
        try:
            t = fn()
        except Exception as e:
            t = f"ERROR {e}"
        result["runs"][f"{label}/{name}"] = t
        print(f"  {label:6s} {name:15s} {t}")

log = clips / "slice_checks.json"
data = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
data.append(result)
log.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\nClips: {voc}\n       {mix}\nLogged to {log}")
