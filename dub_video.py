"""Dub one video into several Indian languages with Sarvam's dubbing API.

Usage: python3 dub_video.py path/to/video.mp4 --source hi-IN [--speakers 2]
"""
import argparse
from pathlib import Path

from sarvam_dub import download, make_client, submit_job, wait_for_exports

parser = argparse.ArgumentParser()
parser.add_argument("video", type=Path)
parser.add_argument("--source", required=True, help="source language code, e.g. hi-IN or en-IN")
parser.add_argument("--speakers", type=int, help="number of speakers (auto-detected if omitted)")
parser.add_argument("--out", type=Path, default=Path("dubbed"))
args = parser.parse_args()

client = make_client()
job_id = submit_job(client, args.video, args.source, ["video", "audio"], num_speakers=args.speakers)
exports = wait_for_exports(client, job_id, args.video.stem)

out_dir = args.out / args.video.stem
out_dir.mkdir(parents=True, exist_ok=True)
for e in exports:
    if e.status != "completed" or not e.download_url:
        print(f"  {e.target_language} {e.export_type}: {e.status}")
        continue
    dest = download(e.download_url, out_dir / f"{args.video.stem}_{e.target_language}_{e.export_type}")
    print(f"  saved {dest}")
