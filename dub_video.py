"""Dub one video into several Indian languages with Sarvam's dubbing API.

Usage: python3 dub_video.py path/to/video.mp4 --source hi-IN [--speakers 2]
"""
import argparse
import mimetypes
import os
import time
from pathlib import Path

import httpx
from sarvamai import SarvamAI

# Marathi, Tamil, Gujarati, Telugu, Bengali, Kannada
TARGET_LANGUAGES = ["mr-IN", "ta-IN", "gu-IN", "te-IN", "bn-IN", "kn-IN"]

# Translation settings from Creator Studio: model "Sarvam Plus", style "Urban colloquial".
MODEL_TIER = "plus"
REGISTER = "modern-colloquial"

POLL_SECONDS = 20

# Load .env into the environment (stdlib only, no python-dotenv).
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            key, sep, value = line.strip().partition("=")
            if sep and not key.startswith("#"):
                os.environ.setdefault(key.strip(), value.strip())

parser = argparse.ArgumentParser()
parser.add_argument("video", type=Path)
parser.add_argument("--source", required=True, help="source language code, e.g. hi-IN or en-IN")
parser.add_argument("--speakers", type=int, help="number of speakers (auto-detected if omitted)")
parser.add_argument("--out", type=Path, default=Path("dubbed"))
args = parser.parse_args()

api_key = os.environ.get("SARVAM_API_KEY")
if not api_key:
    raise SystemExit("SARVAM_API_KEY is not set. Add it to .env.")

client = SarvamAI(api_subscription_key=api_key)

create_args = dict(
    source_language_code=args.source,
    target_language_codes=TARGET_LANGUAGES,
    export_options=["video", "audio"],
    voice_cloning=True,  # clone every speaker's own voice
    register=REGISTER,
    disable_watermark=True,
    editor_flow=False,  # auto-export when done; True bills at the editor rate
    job_name=args.video.name,
    request_options={"additional_body_parameters": {"model_tier": MODEL_TIER}},
)
if args.speakers:
    create_args["num_speakers"] = args.speakers

job = client.dubbing.create(**create_args).data
print(f"Created job {job.job_id} (model_tier={job.model_tier}, voice_cloning={job.voice_cloning})")

content_type = mimetypes.guess_type(args.video.name)[0] or "video/mp4"
client.dubbing.upload(job.upload_url, args.video, content_type=content_type).raise_for_status()
print(f"Uploaded {args.video.name}")

client.dubbing.start(job.job_id)
print("Started; polling progress...")

while True:
    status = client.dubbing.get_live_status(job.job_id).data
    print(f"  {status.status:<16} {status.progress:>3}%  {status.current_step_label or ''}")
    if status.status in ("completed", "failed", "partial_failure"):
        break
    time.sleep(POLL_SECONDS)

if status.status == "failed":
    raise SystemExit(f"Dubbing failed: {status.error_message}")

while True:
    exports = client.dubbing.get_export_status(job.job_id).data.exports
    if exports and all(e.status != "in_progress" for e in exports):
        break
    time.sleep(POLL_SECONDS)

out_dir = args.out / args.video.stem
out_dir.mkdir(parents=True, exist_ok=True)
for e in exports:
    if e.status != "completed" or not e.download_url:
        print(f"  {e.target_language} {e.export_type}: {e.status}")
        continue
    ext = Path(httpx.URL(e.download_url).path).suffix or ".bin"
    dest = out_dir / f"{args.video.stem}_{e.target_language}_{e.export_type}{ext}"
    with httpx.stream("GET", e.download_url, follow_redirects=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_bytes():
                fh.write(chunk)
    print(f"  saved {dest}")
