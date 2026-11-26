"""Generate Cartesia Sonic 3.6 audio for the CSV-lines script and teleprompter script.

Each segment is generated on its own, edge silence is trimmed, then segments are
joined with exactly GAP_MS of digital silence. Output: 48 kHz mono 16-bit WAV,
plus a timing CSV per track.
"""
import concurrent.futures as cf
import csv
import io
import json
import os
import re
import sys
import time
import urllib.request
import wave

import numpy as np

VOICE = "e2f51235-ecee-4323-a75c-caff04910b39"
MODEL = "sonic-3.6"
SR = 48000
GAP_MS = 250
TRIM_DB = -50.0      # silence threshold for edge trimming
PAD_MS = 30          # keep this much room before first / after last audible sample
UP = "/root/.claude/uploads/cede7edb-b109-5325-8620-2c11509fb949"
SCRATCH = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(SCRATCH, "cache")
OUT = "/home/user/11/cartesia_output"
os.makedirs(CACHE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def lang_for(text):
    return "hi" if DEVANAGARI.search(text) else "en"


def tts(text, cache_name):
    path = os.path.join(CACHE, cache_name + ".wav")
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    body = json.dumps({
        "model_id": MODEL,
        "transcript": text,
        "voice": {"mode": "id", "id": VOICE},
        "language": lang_for(text),
        "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": SR},
    }).encode()
    for attempt in range(6):
        req = urllib.request.Request(
            "https://api.cartesia.ai/tts/bytes", data=body, method="POST",
            headers={"Cartesia-Version": "2025-04-16", "X-API-Key": "proxy-injected",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
            return path
        except Exception as e:  # noqa: BLE001
            msg = getattr(e, "read", lambda: b"")()[:200]
            print(f"  retry {attempt+1} {cache_name}: {e} {msg}", file=sys.stderr)
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed: {cache_name}")


def read_pcm(path):
    with open(path, "rb") as f:
        raw = f.read()
    with wave.open(io.BytesIO(raw)) as w:
        assert w.getframerate() == SR and w.getsampwidth() == 2, path
        ch = w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1).astype(np.int16)
    return a


def trim(a):
    thr = 32768 * 10 ** (TRIM_DB / 20)
    idx = np.nonzero(np.abs(a.astype(np.int32)) > thr)[0]
    if len(idx) == 0:
        return a
    pad = SR * PAD_MS // 1000
    return a[max(0, idx[0] - pad): min(len(a), idx[-1] + pad + 1)]


def build(name, segments):
    """segments: list of (key, text)."""
    print(f"[{name}] generating {len(segments)} segments", flush=True)
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        paths = list(ex.map(lambda kv: tts(kv[1], f"{name}_{kv[0]}"), segments))
    gap = np.zeros(SR * GAP_MS // 1000, dtype=np.int16)
    parts, rows, cursor = [], [], 0
    for i, ((key, text), p) in enumerate(zip(segments, paths)):
        a = trim(read_pcm(p))
        if i:
            parts.append(gap)
            cursor += len(gap)
        rows.append([i + 1, key, f"{cursor / SR:.3f}", f"{(cursor + len(a)) / SR:.3f}",
                     f"{len(a) / SR:.3f}", lang_for(text), text])
        parts.append(a)
        cursor += len(a)
    full = np.concatenate(parts)
    wav_path = os.path.join(OUT, f"{name}_cartesia_sonic3.6_48k.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(full.tobytes())
    with open(os.path.join(OUT, f"{name}_timings.csv"), "w", newline="", encoding="utf-8") as f:
        cw = csv.writer(f)
        cw.writerow(["index", "key", "start_s", "end_s", "dur_s", "lang", "text"])
        cw.writerows(rows)
    peak = np.abs(full.astype(np.int32)).max() / 32768
    print(f"[{name}] {len(full)/SR/60:.2f} min, peak {20*np.log10(peak):.2f} dBFS -> {wav_path}")


def csv_segments():
    segs = []
    with open(os.path.join(UP, "591bd4ca-csv_lines_script.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if "\t" in line:
                k, t = line.split("\t", 1)
                if t.strip():
                    segs.append((k.strip(), t.strip()))
    plain = [l.strip() for l in open(os.path.join(UP, "110651ba-csv_lines_plain.txt"), encoding="utf-8") if l.strip()]
    assert [t for _, t in segs] == plain, "plain and keyed files differ"
    return segs


def tele_segments():
    txt = open(os.path.join(UP, "f08e703e-teleprompter_script.txt"), encoding="utf-8").read()
    chunks = re.split(r"--- TAKE (\d+)[^\n]*---", txt)
    segs = []
    for n, body in zip(chunks[1::2], chunks[2::2]):
        body = " ".join(l.strip() for l in body.strip().splitlines() if l.strip())
        segs.append((f"TAKE_{n}", body))
    return segs


if __name__ == "__main__":
    which = sys.argv[1:] or ["csv_lines", "teleprompter"]
    if "teleprompter" in which:
        build("teleprompter", tele_segments())
    if "csv_lines" in which:
        build("csv_lines", csv_segments())
