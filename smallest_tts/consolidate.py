#!/usr/bin/env python3
"""Join the per-line clips into ~45-60 s tracks, in metadata.csv order.

Each clip's leading/trailing silence is trimmed to a short pad (with a short
fade at the cut), then clips are laid end to end with a fixed silent gap.
A clip that would push the current track past --max-sec starts the next
track instead; clips are never cut. Writes track_NNN.wav plus tracks.csv
(clip timings per track) and track_NNN.txt (transcript) to --out.

Standard library only:

    python3 consolidate.py --src ../suri_dataset --out ../suri_dataset/consolidated
"""

import argparse
import array
import csv
import wave
from pathlib import Path


def load_trimmed(path, thr_db, pad_ms, fade_ms):
    with wave.open(str(path)) as w:
        params = w.getparams()
        if params.sampwidth != 2 or params.nchannels != 1:
            raise SystemExit(f"{path}: expected 16-bit mono, got {params.sampwidth * 8}-bit x{params.nchannels}")
        pcm = array.array("h", w.readframes(params.nframes))
    sr = params.framerate
    win = max(1, sr // 100)  # 10 ms analysis windows
    thr = 32768 * 10 ** (thr_db / 20)
    loud = [
        i for i in range(0, len(pcm) - win + 1, win)
        if (sum(x * x for x in pcm[i:i + win]) / win) ** 0.5 > thr
    ]
    pad = sr * pad_ms // 1000
    if loud:
        start, end = max(0, loud[0] - pad), min(len(pcm), loud[-1] + win + pad)
        pcm = pcm[start:end]
    fade = min(len(pcm) // 2, sr * fade_ms // 1000)
    for i in range(fade):
        g = i / fade
        pcm[i] = int(pcm[i] * g)
        pcm[-1 - i] = int(pcm[-1 - i] * g)
    return sr, pcm


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", type=Path, required=True, help="folder with metadata.csv and wavs/")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--min-sec", type=float, default=45.0, help="target minimum track length (default: 45)")
    p.add_argument("--max-sec", type=float, default=60.0, help="hard maximum track length (default: 60)")
    p.add_argument("--gap-ms", type=int, default=400, help="silence inserted between clips (default: 400)")
    p.add_argument("--pad-ms", type=int, default=50, help="silence kept at each clip edge (default: 50)")
    p.add_argument("--fade-ms", type=int, default=5)
    p.add_argument("--silence-db", type=float, default=-50.0, help="trim threshold in dBFS (default: -50)")
    args = p.parse_args()

    rows = list(csv.DictReader(open(args.src / "metadata.csv", encoding="utf-8")))
    clips, sr = [], None
    for r in rows:
        rate, pcm = load_trimmed(args.src / r["file"], args.silence_db, args.pad_ms, args.fade_ms)
        if sr is None:
            sr = rate
        elif rate != sr:
            raise SystemExit(f"{r['file']}: {rate} Hz, expected {sr} Hz")
        clips.append((Path(r["file"]).stem, r["text"], pcm))

    gap = sr * args.gap_ms // 1000
    max_frames = int(args.max_sec * sr)
    tracks, cur, cur_len = [], [], 0
    for clip in clips:
        n = len(clip[2])
        if n > max_frames:
            raise SystemExit(f"{clip[0]} alone is {n / sr:.1f}s, longer than --max-sec")
        added = n + (gap if cur else 0)
        if cur and cur_len + added > max_frames:
            tracks.append(cur)
            cur, cur_len, added = [], 0, n
        cur.append(clip)
        cur_len += added
    if cur:
        tracks.append(cur)

    # Greedy packing leaves a short final track; spread the last few tracks'
    # clips evenly so every track lands in [min, max] when possible.
    def length(track):
        return sum(len(c[2]) for c in track) + gap * (len(track) - 1)

    def split_even(group, k):
        target = (sum(len(c[2]) for c in group) + gap * (len(group) - k)) / k
        out, cur = [], []
        for i, clip in enumerate(group):
            left = len(group) - i
            if cur and len(out) < k - 1 and left >= k - len(out) - 1:
                grown = length(cur + [clip])
                if grown > max_frames or abs(grown - target) > abs(length(cur) - target):
                    out.append(cur)
                    cur = []
            cur.append(clip)
        return out + [cur]

    min_frames = args.min_sec * sr
    if len(tracks) > 1 and length(tracks[-1]) < min_frames:
        for k in range(2, len(tracks) + 1):
            group = [c for t in tracks[-k:] for c in t]
            candidate = split_even(group, k)
            if all(min_frames <= length(t) <= max_frames for t in candidate):
                tracks[-k:] = candidate
                break

    args.out.mkdir(parents=True, exist_ok=True)
    silence = array.array("h", bytes(2 * gap))
    with open(args.out / "tracks.csv", "w", encoding="utf-8", newline="") as f:
        log = csv.writer(f)
        log.writerow(["track", "clip_id", "start_sec", "end_sec", "text"])
        for t, track in enumerate(tracks, 1):
            name = f"track_{t:03d}"
            pcm, lines = array.array("h"), []
            for i, (clip_id, text, clip_pcm) in enumerate(track):
                if i:
                    pcm.extend(silence)
                start = len(pcm) / sr
                pcm.extend(clip_pcm)
                log.writerow([name, clip_id, f"{start:.3f}", f"{len(pcm) / sr:.3f}", text])
                lines.append(text)
            with wave.open(str(args.out / f"{name}.wav"), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                w.writeframes(pcm.tobytes())
            (args.out / f"{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
            flag = "" if len(pcm) / sr >= args.min_sec else "  (short: end of material)"
            print(f"{name}: {len(track):3d} clips, {len(pcm) / sr:5.1f}s{flag}")
    print(f"{len(clips)} clips -> {len(tracks)} tracks in {args.out}")


if __name__ == "__main__":
    main()
