"""Dub a video one character at a time, then mix the dubbed voices back over the M&E bed.

Each --stem is one character's dialogue only: full length and sample-aligned with
the video, with every other character muted. Each stem is dubbed as its own
single-speaker Sarvam job, so each voice clone hears exactly one person.

Usage:
  python3 dub_split.py video.mp4 --source hi-IN --bed me.wav \
      --stem ravi=stems/ravi.wav --stem priya=stems/priya.wav
"""
import argparse
import json
import subprocess
from pathlib import Path

from sarvam_dub import TARGET_LANGUAGES, download, make_client, submit_job, wait_for_exports

# Warn when a dubbed stem's length differs from its source by more than this (seconds).
SYNC_TOLERANCE = 0.5


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


parser = argparse.ArgumentParser()
parser.add_argument("video", type=Path)
parser.add_argument("--source", required=True, help="source language code, e.g. hi-IN or en-IN")
parser.add_argument("--bed", type=Path, required=True, help="music & effects stem with no dialogue")
parser.add_argument("--stem", action="append", required=True, metavar="NAME=PATH",
                    help="one character's dialogue stem; repeat once per character")
parser.add_argument("--out", type=Path, default=Path("dubbed"))
args = parser.parse_args()

stems = {}
for item in args.stem:
    name, sep, path = item.partition("=")
    if not sep or not Path(path).exists():
        raise SystemExit(f"Bad --stem {item!r}: expected NAME=PATH to an existing file")
    stems[name] = Path(path)

video_len = duration(args.video)
for name, path in {**stems, "bed": args.bed}.items():
    if abs(duration(path) - video_len) > SYNC_TOLERANCE:
        raise SystemExit(f"{path} is {duration(path):.2f}s but the video is {video_len:.2f}s; export full-length stems")

out_dir = args.out / f"{args.video.stem}_split"
out_dir.mkdir(parents=True, exist_ok=True)
client = make_client()

# Submit every character first so the jobs render in parallel on Sarvam's side.
jobs = {
    name: submit_job(client, path, args.source, ["audio"], num_speakers=1,
                     job_name=f"{args.video.stem}_{name}")
    for name, path in stems.items()
}

# dubbed[lang][name] = path to that character's dubbed dialogue in that language
dubbed = {lang: {} for lang in TARGET_LANGUAGES}
for name, job_id in jobs.items():
    for e in wait_for_exports(client, job_id, name):
        if e.export_type != "audio":
            continue
        if e.status != "completed" or not e.download_url:
            print(f"  {name} {e.target_language}: {e.status}")
            continue
        dest = download(e.download_url, out_dir / f"{name}_{e.target_language}")
        drift = duration(dest) - duration(stems[name])
        flag = "  <-- check sync" if abs(drift) > SYNC_TOLERANCE else ""
        print(f"  saved {dest} (length drift {drift:+.2f}s){flag}")
        dubbed[e.target_language][name] = dest

# Mix each language: M&E bed + every character's dubbed dialogue, laid onto the original picture.
for lang, voices in dubbed.items():
    missing = set(stems) - set(voices)
    if missing:
        print(f"Skipping {lang}: no dub for {', '.join(sorted(missing))}")
        continue
    inputs = [args.bed, *voices.values()]
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(args.video)]
    for path in inputs:
        cmd += ["-i", str(path)]
    mix_in = "".join(f"[{i + 1}:a]" for i in range(len(inputs)))
    cmd += [
        "-filter_complex", f"{mix_in}amix=inputs={len(inputs)}:duration=first:normalize=0[mix]",
        "-map", "0:v", "-map", "[mix]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(out_dir / f"{args.video.stem}_{lang}.mp4"),
    ]
    subprocess.run(cmd, check=True)
    print(f"Mixed {out_dir / f'{args.video.stem}_{lang}.mp4'}")
