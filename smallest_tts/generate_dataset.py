#!/usr/bin/env python3
"""Generate a TTS dataset from CSV line lists with the smallest.ai Waves API.

Each input CSV has two columns: an utterance ID and the text to speak. A header
row of "filename,text" is detected and skipped. Every line is synthesized with
the chosen voice and written to <out>/wavs/<id>.wav, and <out>/metadata.csv
lists every clip that was generated successfully.

Runs are resumable: clips that already exist (and are valid WAVs at the target
sample rate) are skipped, so re-running after an interruption only fills gaps.

Standard library only. Usage:

    export SMALLEST_API_KEY=sk_...
    python3 generate_dataset.py --limit 3        # soundcheck: 3 clips first
    python3 generate_dataset.py                  # full run
"""

import argparse
import csv
import io
import json
import os
import random
import sys
import threading
import time
import urllib.error
import urllib.request
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_INPUTS = [
    HERE / "data" / "rashi_pans_transcription.csv",
    HERE / "data" / "teleprompter_lines.csv",
]
DEFAULT_BASE_URL = "https://api.smallest.ai/waves/v1"
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def read_lines(paths):
    """Return [(utt_id, text, source_name)] from every CSV, in file order."""
    items, seen = [], {}
    for path in paths:
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row_num, row in enumerate(csv.reader(f), start=1):
                if not row or not any(cell.strip() for cell in row):
                    continue
                if row_num == 1 and [c.strip().lower() for c in row[:2]] == ["filename", "text"]:
                    continue
                if len(row) < 2 or not row[1].strip():
                    sys.exit(f"{path}:{row_num}: expected 'id,text', got {row!r}")
                utt_id, text = row[0].strip(), row[1].strip()
                if utt_id in seen:
                    sys.exit(f"{path}:{row_num}: duplicate id {utt_id!r} (first seen in {seen[utt_id]})")
                seen[utt_id] = path.name
                items.append((utt_id, text, path.name))
    return items


def wav_info(data):
    """Return (sample_rate, duration_sec) for WAV bytes, or raise ValueError."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            frames, rate = w.getnframes(), w.getframerate()
    except (wave.Error, EOFError) as e:
        raise ValueError(f"not a valid WAV ({e}); first bytes: {data[:64]!r}")
    if frames == 0:
        raise ValueError("WAV has no audio frames")
    return rate, frames / rate


class RateLimiter:
    """Space request starts at least 60/rpm seconds apart across all threads."""

    def __init__(self, rpm):
        self.interval = 60.0 / rpm if rpm > 0 else 0.0
        self.lock = threading.Lock()
        self.next_slot = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next_slot)
            self.next_slot = slot + self.interval
        if slot > now:
            time.sleep(slot - now)


class Client:
    def __init__(self, base_url, api_key, rpm, max_attempts):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.limiter = RateLimiter(rpm)
        self.max_attempts = max_attempts

    def _request(self, method, path, body=None, accept="application/json"):
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": accept}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        for attempt in range(1, self.max_attempts + 1):
            self.limiter.wait()
            req = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
            retry_after = None
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    return resp.read()
            except urllib.error.HTTPError as e:
                detail = e.read()[:500].decode("utf-8", "replace")
                if e.code not in RETRYABLE_STATUS or attempt == self.max_attempts:
                    raise RuntimeError(f"HTTP {e.code} on {path}: {detail}") from None
                retry_after = e.headers.get("Retry-After")
                reason = f"HTTP {e.code}"
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt == self.max_attempts:
                    raise RuntimeError(f"network error on {path}: {e}") from None
                reason = f"network error: {e}"
            delay = min(60.0, 2 ** attempt) + random.uniform(0, 1)
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    pass
            print(f"  retry {attempt}/{self.max_attempts - 1} in {delay:.1f}s ({reason})", file=sys.stderr)
            time.sleep(delay)

    def find_voice(self, name):
        payload = json.loads(self._request("GET", "/lightning-v3.1/get_voices"))
        voices = payload.get("voices") or []
        wanted = name.strip().lower()
        for v in voices:
            if wanted in (str(v.get("voiceId", "")).lower(), str(v.get("displayName", "")).lower()):
                return v
        close = sorted(
            f"{v.get('voiceId')} ({v.get('displayName')})"
            for v in voices
            if wanted[:2] in str(v.get("voiceId", "")).lower()
        )
        sys.exit(f"Voice {name!r} not found among {len(voices)} voices. Similar: {', '.join(close) or 'none'}")

    def synthesize(self, payload):
        return self._request("POST", "/tts", body=payload, accept="audio/wav")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inputs", nargs="*", type=Path, default=DEFAULT_INPUTS, help="CSV files (default: both files in data/)")
    p.add_argument("--voice", default="suri", help="voice_id or display name (default: suri)")
    p.add_argument("--model", default="lightning_v3.1", choices=["lightning_v3.1", "lightning_v3.1_pro"],
                   help="model pool the voice belongs to (default: lightning_v3.1)")
    p.add_argument("--language", default="auto")
    p.add_argument("--number-pronunciation", default="auto", help="number_pronunciation_language (default: auto)")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--sample-rate", type=int, default=44100)
    p.add_argument("--out", type=Path, default=HERE / "output" / "suri")
    p.add_argument("--limit", type=int, default=0, help="only generate the first N lines (soundcheck)")
    p.add_argument("--workers", type=int, default=4, help="parallel requests (default: 4)")
    p.add_argument("--rpm", type=float, default=90, help="max requests per minute (default: 90)")
    p.add_argument("--max-attempts", type=int, default=6)
    p.add_argument("--overwrite", action="store_true", help="regenerate clips that already exist")
    p.add_argument("--skip-voice-check", action="store_true", help="use --voice as the voice_id without looking it up")
    p.add_argument("--dry-run", action="store_true", help="print the plan and first request, send nothing")
    p.add_argument("--base-url", default=os.environ.get("SMALLEST_BASE_URL", DEFAULT_BASE_URL))
    p.add_argument("--api-key", default=os.environ.get("SMALLEST_API_KEY"), help="default: $SMALLEST_API_KEY")
    args = p.parse_args()

    items = read_lines(args.inputs)
    todo_items = items[: args.limit] if args.limit else items
    wav_dir = args.out / "wavs"

    def payload_for(text, voice_id):
        return {
            "text": text,
            "voice_id": voice_id,
            "model": args.model,
            "language": args.language,
            "number_pronunciation_language": args.number_pronunciation,
            "speed": args.speed,
            "sample_rate": args.sample_rate,
            "output_format": "wav",
        }

    print(f"{len(items)} lines from {len(args.inputs)} file(s); generating {len(todo_items)} -> {wav_dir}")
    if args.dry_run:
        print(json.dumps(payload_for(todo_items[0][1], args.voice), ensure_ascii=False, indent=2))
        return
    if not args.api_key:
        sys.exit("Set SMALLEST_API_KEY (or pass --api-key).")

    client = Client(args.base_url, args.api_key, args.rpm, args.max_attempts)
    voice_id = args.voice
    if not args.skip_voice_check:
        voice = client.find_voice(args.voice)
        voice_id = voice["voiceId"]
        print(f"Voice: {voice_id} ({voice.get('displayName')}) tags={json.dumps(voice.get('tags'), ensure_ascii=False)}")
    print(f"Model: {args.model}  language={args.language}  numbers={args.number_pronunciation}  "
          f"speed={args.speed}  sample_rate={args.sample_rate}")

    wav_dir.mkdir(parents=True, exist_ok=True)

    def existing_duration(path):
        if not path.exists():
            return None
        try:
            rate, dur = wav_info(path.read_bytes())
        except ValueError:
            return None
        return dur if rate == args.sample_rate else None

    todo, durations = [], {}
    for utt_id, text, source in todo_items:
        dur = None if args.overwrite else existing_duration(wav_dir / f"{utt_id}.wav")
        if dur is None:
            todo.append((utt_id, text))
        else:
            durations[utt_id] = dur
    if durations:
        print(f"Skipping {len(durations)} clip(s) already on disk.")

    failures = []

    def work(utt_id, text):
        audio = client.synthesize(payload_for(text, voice_id))
        rate, dur = wav_info(audio)
        if rate != args.sample_rate:
            raise ValueError(f"got {rate} Hz, expected {args.sample_rate} Hz")
        dest = wav_dir / f"{utt_id}.wav"
        tmp = dest.with_suffix(".wav.part")
        tmp.write_bytes(audio)
        tmp.replace(dest)
        return dur

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(work, utt_id, text): (utt_id, text) for utt_id, text in todo}
        for n, fut in enumerate(as_completed(futures), start=1):
            utt_id, text = futures[fut]
            try:
                durations[utt_id] = fut.result()
                print(f"[{n}/{len(todo)}] {utt_id} ok ({durations[utt_id]:.2f}s)")
            except Exception as e:
                failures.append((utt_id, text, str(e)))
                print(f"[{n}/{len(todo)}] {utt_id} FAILED: {e}", file=sys.stderr)

    with open(args.out / "metadata.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "text", "source_csv", "duration_sec"])
        for utt_id, text, source in todo_items:
            if utt_id in durations:
                w.writerow([f"wavs/{utt_id}.wav", text, source, f"{durations[utt_id]:.3f}"])

    fail_path = args.out / "failures.csv"
    if failures:
        with open(fail_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "text", "error"])
            w.writerows(failures)
    elif fail_path.exists():
        fail_path.unlink()

    total = sum(durations.values())
    print(f"\nDone: {len(durations)}/{len(todo_items)} clips, {total / 60:.1f} min of audio -> {args.out}")
    if failures:
        print(f"{len(failures)} failed; see {fail_path}. Re-run the same command to retry just those.")
        sys.exit(1)


if __name__ == "__main__":
    main()
