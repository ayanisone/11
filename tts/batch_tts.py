#!/usr/bin/env python3
"""Batch text-to-speech from a CSV of names using the ElevenLabs API.

Usage:
    export ELEVENLABS_API_KEY=...        # never commit this
    python3 tts/batch_tts.py names.csv [--settings tts/settings.json] [--out tts/output] [--limit N]

CSV columns:
    name           required; substituted into text_template as {name}
    pronunciation  optional; if filled, spoken instead of `name` (file is still named after `name`)
    text           optional; if filled, spoken as-is instead of the template

Files that already exist in the output folder are skipped, so a failed run can be re-run safely.
"""
import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format={output_format}"


def extension(output_format):
    kind = output_format.split("_")[0]
    return {"mp3": "mp3", "wav": "wav", "opus": "opus", "pcm": "pcm"}.get(kind, "bin")


def slug(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_") or "row"


def synthesize(api_key, settings, text):
    body = {
        "text": text,
        "model_id": settings["model_id"],
        "voice_settings": settings["voice_settings"],
    }
    if settings.get("language_code"):
        body["language_code"] = settings["language_code"]
    url = API.format(voice_id=settings["voice_id"], output_format=settings["output_format"])
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read(), response.headers.get("character-cost")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path")
    parser.add_argument("--settings", default=os.path.join(os.path.dirname(__file__), "settings.json"))
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "output"))
    parser.add_argument("--limit", type=int, help="only render the first N rows (for a test pass)")
    args = parser.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("XI_API_KEY")
    if not api_key:
        sys.exit("Set ELEVENLABS_API_KEY in your environment first.")

    with open(args.settings) as f:
        settings = json.load(f)
    with open(args.csv_path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("name") or "").strip()]
    if args.limit:
        rows = rows[: args.limit]

    os.makedirs(args.out, exist_ok=True)
    ext = extension(settings["output_format"])
    log = []
    for i, row in enumerate(rows, 1):
        name = row["name"].strip()
        spoken = (row.get("pronunciation") or "").strip() or name
        text = (row.get("text") or "").strip() or settings["text_template"].format(name=spoken)
        path = os.path.join(args.out, f"{i:03d}_{slug(name)}.{ext}")
        if os.path.exists(path):
            print(f"[{i}/{len(rows)}] skip   {name} (exists)")
            log.append({"row": i, "name": name, "text": text, "file": path, "status": "skipped", "cost": ""})
            continue
        try:
            audio, cost = synthesize(api_key, settings, text)
            with open(path, "wb") as f:
                f.write(audio)
            print(f"[{i}/{len(rows)}] ok     {name} -> {path}")
            log.append({"row": i, "name": name, "text": text, "file": path, "status": "ok", "cost": cost or ""})
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            print(f"[{i}/{len(rows)}] FAILED {name}: HTTP {e.code} {detail}")
            log.append({"row": i, "name": name, "text": text, "file": "", "status": f"HTTP {e.code}: {detail}", "cost": ""})
        except urllib.error.URLError as e:
            print(f"[{i}/{len(rows)}] FAILED {name}: {e.reason}")
            log.append({"row": i, "name": name, "text": text, "file": "", "status": str(e.reason), "cost": ""})

    with open(os.path.join(args.out, "log.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["row", "name", "text", "file", "status", "cost"])
        writer.writeheader()
        writer.writerows(log)
    failed = sum(1 for r in log if r["status"] not in ("ok", "skipped"))
    print(f"Done: {len(log) - failed} ok/skipped, {failed} failed. Log: {os.path.join(args.out, 'log.csv')}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
