#!/usr/bin/env python3
"""Forced-alignment QA and splice points for batch TTS takes (ElevenLabs /v1/forced-alignment).

Usage:
    export ELEVENLABS_API_KEY=...        # never commit this
    python3 tools/align_qa.py qa  takes.csv [--cache DIR] [--report qa.csv]
    python3 tools/align_qa.py cut take.wav "Hi प्रिया, welcome aboard." --word 2 [--cache DIR]

takes.csv columns:
    file   path to the rendered take (any format the API accepts; WAV also gets level checks)
    text   the script line the take was rendered from

qa   aligns every take against its script and flags, per word:
       FAIL collapsed   word squeezed under --min-word seconds: the take most likely skipped it
       FAIL high_loss   word loss >= --fail-loss: badly matched audio
       WARN loss        word loss >= --warn-ratio x the clip's median word loss: mispronounced or swapped
       WARN stretched   long word with ms/char >= --stretch-ratio x clip median: possible unscripted speech
       WARN gap         silence between words longer than --max-gap seconds
     and per clip: head/tail silence before/after speech, and overall loss.
     Thresholds come from a handful of test takes; recalibrate them on a real batch.
cut  prints in/out points (seconds) for one word, nudged from the aligner's 20 ms grid
     to the quietest 1 ms point within +-40 ms (WAV only), for clean splicing.

Alignment results are cached as JSON in --cache, so re-runs cost nothing.
"""
import argparse
import array
import csv
import hashlib
import json
import math
import os
import statistics
import sys
import urllib.error
import urllib.request
import uuid
import wave

API = "https://api.elevenlabs.io/v1/forced-alignment"


def align(api_key, path, text, cache):
    """Return the aligner response for (audio, text), from cache when possible."""
    with open(path, "rb") as f:
        audio = f.read()
    key = hashlib.sha1(audio + text.encode()).hexdigest()[:16]
    cached = os.path.join(cache, key + ".json")
    if os.path.exists(cached):
        with open(cached, encoding="utf-8") as f:
            return json.load(f)
    if not api_key:
        sys.exit("Set ELEVENLABS_API_KEY in your environment first (or point --cache at existing results).")
    boundary = uuid.uuid4().hex
    body = b"".join([
        f'--{boundary}\r\nContent-Disposition: form-data; name="text"\r\n\r\n'.encode(),
        text.encode(),
        f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{os.path.basename(path)}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n".encode(),
        audio,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    request = urllib.request.Request(
        API,
        data=body,
        headers={"xi-api-key": api_key, "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.load(response)
        result["_character_cost"] = response.headers.get("character-cost")
    os.makedirs(cache, exist_ok=True)
    with open(cached, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result


def read_wav(path):
    """Return (mono samples as floats, sample rate), or (None, None) if not a 16-bit WAV."""
    try:
        w = wave.open(path)
    except (wave.Error, EOFError):
        return None, None
    if w.getsampwidth() != 2:
        return None, None
    ch = w.getnchannels()
    a = array.array("h", w.readframes(w.getnframes()))
    if sys.byteorder == "big":
        a.byteswap()
    return [a[i] / 32768 for i in range(0, len(a), ch)], w.getframerate()


def check(result, text, path, args):
    words = [w for w in result["words"] if w["text"].strip()]
    issues = []
    if not words:
        return [("FAIL", "no_words", "", "aligner returned no words")], {}
    losses = statistics.median(w["loss"] for w in words)
    rates = statistics.median((w["end"] - w["start"]) / max(len(w["text"]), 1) for w in words)
    for i, w in enumerate(words, 1):
        dur = w["end"] - w["start"]
        rate = dur / max(len(w["text"]), 1)
        where = f"{i}:{w['text']}@{w['start']:.2f}"
        if dur < args.min_word:
            issues.append(("FAIL", "collapsed", where, f"{dur * 1000:.0f} ms, loss {w['loss']:.2f}"))
        elif w["loss"] >= args.fail_loss:
            issues.append(("FAIL", "high_loss", where, f"loss {w['loss']:.2f}"))
        elif w["loss"] >= args.warn_ratio * losses:
            issues.append(("WARN", "loss", where, f"loss {w['loss']:.2f} vs clip median {losses:.2f}"))
        if dur >= 0.5 and rate >= args.stretch_ratio * rates:
            issues.append(("WARN", "stretched", where, f"{rate * 1000:.0f} ms/char vs clip median {rates * 1000:.0f}"))
    for a, b in zip(words, words[1:]):
        if b["start"] - a["end"] > args.max_gap:
            issues.append(("WARN", "gap", f"after {a['text']}@{a['end']:.2f}", f"{b['start'] - a['end']:.2f} s"))

    stats = {"loss": round(result["loss"], 3), "words": len(words), "speech_start": words[0]["start"],
             "speech_end": words[-1]["end"]}
    samples, sr = read_wav(path)
    if samples:
        length = len(samples) / sr
        peak = max(abs(s) for s in samples)
        stats.update(length=round(length, 3), head=round(words[0]["start"], 3),
                     tail=round(length - words[-1]["end"], 3),
                     peak_dbfs=round(20 * math.log10(max(peak, 1e-9)), 1))
        if stats["head"] > args.max_head:
            issues.append(("WARN", "head", "", f"{stats['head']:.2f} s before first word"))
        if stats["tail"] > args.max_tail:
            issues.append(("WARN", "tail", "", f"{stats['tail']:.2f} s after last word"))
    return issues, stats


def cmd_qa(args, api_key):
    with open(args.csv_path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("file") or "").strip()]
    report = []
    worst = "OK"
    for row in rows:
        path, text = row["file"].strip(), row["text"].strip()
        try:
            result = align(api_key, path, text, args.cache)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:200]
            report.append({"file": path, "status": "ERROR", "issue": f"HTTP {e.code}", "detail": detail})
            print(f"ERROR {path}: HTTP {e.code} {detail}")
            worst = "FAIL"
            continue
        issues, stats = check(result, text, path, args)
        status = "FAIL" if any(s == "FAIL" for s, *_ in issues) else "WARN" if issues else "OK"
        if status == "FAIL" or (status == "WARN" and worst == "OK"):
            worst = status
        print(f"{status:4} {path}  loss={stats.get('loss')} head={stats.get('head', '-')} tail={stats.get('tail', '-')}")
        for severity, kind, where, detail in issues:
            print(f"     {severity} {kind:9} {where}  {detail}")
        base = {"file": path, "status": status, **{k: stats.get(k, "") for k in ("loss", "head", "tail", "peak_dbfs")}}
        for severity, kind, where, detail in issues or [("", "", "", "")]:
            report.append({**base, "issue": f"{severity} {kind}".strip(), "word": where, "detail": detail})
    if args.report:
        with open(args.report, "w", newline="", encoding="utf-8") as f:
            fields = ["file", "status", "loss", "head", "tail", "peak_dbfs", "issue", "word", "detail"]
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(report)
        print(f"Report: {args.report}")
    sys.exit({"OK": 0, "WARN": 0, "FAIL": 1}[worst])


def quietest(samples, sr, t, reach=0.04):
    """Time of the lowest-energy 1 ms window within +-reach seconds of t."""
    win = max(sr // 1000, 1)
    lo, hi = max(int((t - reach) * sr), 0), min(int((t + reach) * sr), len(samples) - win)
    if hi <= lo:
        return t
    best = min(range(lo, hi, win), key=lambda i: sum(s * s for s in samples[i:i + win]))
    return (best + win // 2) / sr


def cmd_cut(args, api_key):
    result = align(api_key, args.audio, args.text, args.cache)
    words = [w for w in result["words"] if w["text"].strip()]
    if not 1 <= args.word <= len(words):
        sys.exit(f"--word must be 1..{len(words)}; words: {[w['text'] for w in words]}")
    w = words[args.word - 1]
    start, end = w["start"], w["end"]
    samples, sr = read_wav(args.audio)
    if samples:
        start, end = quietest(samples, sr, start), quietest(samples, sr, end)
    print(json.dumps({"word": w["text"], "aligner_in": w["start"], "aligner_out": w["end"],
                      "cut_in": round(start, 4), "cut_out": round(end, 4), "loss": round(w["loss"], 3)},
                     ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache", default=os.path.join(os.path.dirname(__file__), "..", ".align_cache"))
    sub = parser.add_subparsers(dest="command", required=True)
    qa = sub.add_parser("qa", help="flag dropped, garbled and padded takes")
    qa.add_argument("csv_path")
    qa.add_argument("--report", help="write a CSV report here")
    qa.add_argument("--min-word", type=float, default=0.06)
    qa.add_argument("--fail-loss", type=float, default=1.6)
    qa.add_argument("--warn-ratio", type=float, default=1.4)
    qa.add_argument("--stretch-ratio", type=float, default=1.4)
    qa.add_argument("--max-gap", type=float, default=0.8)
    qa.add_argument("--max-head", type=float, default=0.3)
    qa.add_argument("--max-tail", type=float, default=0.6)
    cut = sub.add_parser("cut", help="splice points for one word")
    cut.add_argument("audio")
    cut.add_argument("text")
    cut.add_argument("--word", type=int, required=True, help="1-based index of the word, spaces not counted")
    args = parser.parse_args()
    api_key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("XI_API_KEY")
    {"qa": cmd_qa, "cut": cmd_cut}[args.command](args, api_key)


if __name__ == "__main__":
    main()
