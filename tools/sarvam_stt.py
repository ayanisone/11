#!/usr/bin/env python3
"""Sarvam speech-to-text for song QA (second opinion next to ElevenLabs Scribe).

Usage:
    SARVAM_API_KEY=... python3 tools/sarvam_stt.py song.mp3 [--lang en-IN] [--model saarika:v2.5]

The synchronous Sarvam endpoint accepts short clips (about 30 s), so the song is
cut into 25 s mono 16 kHz WAV chunks with ffmpeg, each chunk is transcribed,
and the transcripts are joined in order. The key is read from the
SARVAM_API_KEY environment variable and is never written anywhere.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import uuid

URL = "https://api.sarvam.ai/speech-to-text"
CHUNK_SEC = 28  # max chunk length; chunks are split evenly


def duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def transcribe_chunk(wav_path: str, key: str, model: str, lang: str) -> str:
    boundary = uuid.uuid4().hex
    with open(wav_path, "rb") as f:
        audio = f.read()
    parts = []
    for name, value in (("model", model), ("language_code", lang)):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; "
                     f"name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                 f"filename=\"chunk.wav\"\r\nContent-Type: audio/wav\r\n\r\n".encode()
                 + audio + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        URL, data=b"".join(parts), method="POST",
        headers={"api-subscription-key": key,
                 "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode()).get("transcript", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--lang", default="en-IN",
                    help="e.g. en-IN, hi-IN, ta-IN, te-IN, bn-IN, mr-IN, gu-IN, kn-IN, ml-IN")
    ap.add_argument("--model", default="saarika:v2.5")
    args = ap.parse_args()
    key = os.environ.get("SARVAM_API_KEY")
    if not key:
        sys.exit("Set SARVAM_API_KEY")
    total = duration(args.audio)
    # Equal-length chunks of at most 28 s, so no tiny tail chunk (short,
    # music-only tails make the model guess words like "Plus").
    n = max(1, -(-int(total) // 28))
    size = total / n
    texts = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(n):
            start = i * size
            wav = os.path.join(tmp, f"c{i}.wav")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.2f}",
                            "-t", f"{size:.2f}", "-i", args.audio, "-ac", "1",
                            "-ar", "16000", wav], check=True)
            t = transcribe_chunk(wav, key, args.model, args.lang)
            texts.append(t)
            print(f"[{start:.1f}-{start + size:.1f} s] {t}", file=sys.stderr)
    print(" ".join(x.strip() for x in texts if x.strip()))


if __name__ == "__main__":
    main()
