#!/usr/bin/env python3
"""Dub a video into multiple Indian languages with Sarvam's Dubbing API.

Flow (per the official `sarvamai` SDK):
  1. POST /dubbing/jobs                 -> job_id + signed upload_url
  2. PUT  <upload_url>                  -> raw media bytes
  3. POST /dubbing/jobs/{id}/start      -> pipeline begins
  4. GET  /dubbing/jobs/{id}/live-status    (progress only)
  5. GET  /dubbing/jobs/{id}/export-status  (source of truth for downloads)

Usage:
  export SARVAM_API_KEY=...
  python dub.py /path/to/video.mp4 --source hi-IN

Resume polling/downloading an existing job without creating (and paying for) a new one:
  python dub.py --job-id dub_xxxxxxxx
"""

import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sarvamai import SarvamAI

SUPPORTED_LANGS = {
    "en-IN": "English", "hi-IN": "Hindi", "bn-IN": "Bengali", "gu-IN": "Gujarati",
    "kn-IN": "Kannada", "ml-IN": "Malayalam", "mr-IN": "Marathi", "or-IN": "Odia",
    "pa-IN": "Punjabi", "ta-IN": "Tamil", "te-IN": "Telugu", "as-IN": "Assamese",
}
DEFAULT_TARGETS = ["mr-IN", "ta-IN", "te-IN", "kn-IN", "bn-IN", "or-IN"]
DEFAULT_EXPORTS = ["video", "audio", "srt"]
REGISTERS = ["formal", "common-indic", "classic-colloquial", "modern-colloquial", "academic", "auto"]
FALLBACK_EXT = {"video": ".mp4", "audio": ".wav", "mp3": ".mp3", "srt": ".srt"}
JOB_TERMINAL = {"completed", "failed", "partial_failure", "deleted"}


def parse_args():
    p = argparse.ArgumentParser(description="Dub a video with Sarvam's Dubbing API.")
    p.add_argument("video", nargs="?", help="Path to the source video/audio file.")
    p.add_argument("--source", choices=SUPPORTED_LANGS,
                   help="Language spoken in the source video (BCP-47). Required for a new job.")
    p.add_argument("--targets", nargs="+", default=DEFAULT_TARGETS, choices=SUPPORTED_LANGS,
                   help="Languages to dub into. Default: Marathi Tamil Telugu Kannada Bengali Odia.")
    p.add_argument("--speakers", type=int, default=3, help="Number of distinct speakers. Default: 3.")
    p.add_argument("--exports", nargs="+", default=DEFAULT_EXPORTS, choices=["video", "audio", "srt"],
                   help="Outputs per language. Default: video audio srt.")
    p.add_argument("--register", choices=REGISTERS,
                   help="Translation tone. Omit to use the service default.")
    p.add_argument("--watermark", action="store_true", help="Keep Sarvam's watermark (default: disabled).")
    p.add_argument("--job-name", help="Label for the job. Default: the video's filename.")
    p.add_argument("--job-id", help="Resume an existing job instead of creating a new one.")
    p.add_argument("--out", default="dubs", help="Output directory. Default: ./dubs")
    p.add_argument("--poll", type=int, default=15, help="Seconds between status checks. Default: 15.")
    p.add_argument("--timeout", type=int, default=3 * 3600, help="Give up after N seconds. Default: 3h.")
    args = p.parse_args()

    if not args.job_id and not args.video:
        p.error("pass a video path, or --job-id to resume an existing job")
    if not args.job_id and not args.source:
        p.error("--source is required when creating a new job")
    if args.source in args.targets:
        p.error(f"--targets must not include the source language {args.source}")
    if args.speakers < 1:
        p.error("--speakers must be >= 1")
    return args


def create_and_start(client, args):
    video = Path(args.video).expanduser()
    if not video.is_file():
        sys.exit(f"Video not found: {video}")

    kwargs = dict(
        source_language_code=args.source,
        target_language_codes=args.targets,
        export_options=args.exports,
        voice_cloning=True,              # clone each original speaker's voice
        num_speakers=args.speakers,      # tells the diarizer how many voices to separate
        disable_watermark=not args.watermark,
        editor_flow=False,               # exports fire automatically when TTS finishes
        job_name=args.job_name or video.name,
    )
    if args.register:
        kwargs["register"] = args.register

    created = client.dubbing.create(**kwargs).data
    print(f"Created job {created.job_id} (upload URL valid {created.expires_in_hours}h)")

    print(f"Uploading {video.name} ({video.stat().st_size / 1e6:.1f} MB)...")
    client.dubbing.upload(created.upload_url, str(video))

    started = client.dubbing.start(job_id=created.job_id).data
    print(f"Started: {started.status}")
    return created.job_id


def wait_for_pipeline(client, job_id, poll, deadline):
    last = None
    while True:
        s = client.dubbing.get_live_status(job_id).data
        line = f"[{s.progress:3d}%] {s.status} - {s.current_step_label or s.current_step or ''}"
        if line != last:
            print(line)
            last = line
        if s.status in JOB_TERMINAL:
            if s.status != "completed":
                print(f"Job ended with status '{s.status}': {s.error_message or 'no error message'}")
            return s.status
        if time.monotonic() > deadline:
            sys.exit(f"Timed out waiting for job {job_id}. Re-run with --job-id {job_id} to resume.")
        time.sleep(poll)


def latest_exports(client, job_id):
    """Newest export per (language, type); re-exports can leave older entries behind."""
    items = client.dubbing.get_export_status(job_id, limit=100).data.exports
    newest = {}
    for e in items:
        key = (e.target_language, e.export_type)
        if key not in newest or (e.created_at and newest[key].created_at and e.created_at > newest[key].created_at):
            newest[key] = e
    return newest


def wait_for_exports(client, job_id, expected, poll, deadline):
    while True:
        exports = latest_exports(client, job_id)
        pending = [k for k in expected if k not in exports or exports[k].status == "in_progress"]
        if not pending:
            return exports
        if time.monotonic() > deadline:
            print(f"Timed out with {len(pending)} exports still pending: {pending}")
            return exports
        print(f"Waiting on {len(pending)}/{len(expected)} exports...")
        time.sleep(poll)


def download(url, dest):
    with httpx.stream("GET", url, timeout=600, follow_redirects=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_bytes():
                fh.write(chunk)


def main():
    args = parse_args()
    key = os.environ.get("SARVAM_API_KEY")
    if not key:
        sys.exit("Set SARVAM_API_KEY in your environment first.")
    client = SarvamAI(api_subscription_key=key)
    deadline = time.monotonic() + args.timeout

    job_id = args.job_id or create_and_start(client, args)
    wait_for_pipeline(client, job_id, args.poll, deadline)

    expected = [(lang, exp) for lang in args.targets for exp in args.exports]
    exports = wait_for_exports(client, job_id, expected, args.poll, deadline)

    stem = Path(args.video).stem if args.video else job_id
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    failures = []
    for lang, exp in expected:
        e = exports.get((lang, exp))
        name = f"{SUPPORTED_LANGS[lang]} {exp}"
        if not e or e.status != "completed" or not e.download_url:
            failures.append(f"{name}: {e.status if e else 'missing'}")
            continue
        ext = Path(urlparse(e.download_url).path).suffix or FALLBACK_EXT.get(exp, "")
        dest = out / f"{stem}_{lang}_{exp}{ext}"
        download(e.download_url, dest)
        print(f"Saved {dest}")

    if failures:
        print("\nNot downloaded:\n  " + "\n  ".join(failures))
        print(f"Re-run with --job-id {job_id} to retry downloads without re-dubbing.")
        sys.exit(1)
    print(f"\nDone. {len(expected)} files in {out}/")


if __name__ == "__main__":
    main()
