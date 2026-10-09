"""Batch IndexTTS2 inference with peak normalisation.

Run from inside an index-tts checkout (it imports `indextts`):

    python tts.py --voice voice.wav --text "Hello" --out out.wav
    python tts.py --jobs jobs.jsonl

Each line of a jobs file is a JSON object with keys:
    voice (required), text (required), out (required),
    emo_vector (8 floats: happy, angry, sad, afraid, disgusted, melancholic, surprised, calm),
    emo_audio (path), emo_text (str), emo_alpha (float, default 1.0)
The model is loaded once and reused for every job.
"""
import argparse
import json
import os
import time

import numpy as np
import soundfile as sf
import torch

from indextts.infer_v2 import IndexTTS2


def peak_normalise(path, ceiling_db):
    audio, sr = sf.read(path)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0:
        audio = audio * (10 ** (ceiling_db / 20) / peak)
        sf.write(path, audio, sr, subtype="PCM_16")
    return peak


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model-dir", default="checkpoints")
    p.add_argument("--jobs", help="JSONL file of jobs")
    p.add_argument("--voice", help="speaker reference clip (3-15 s, dry)")
    p.add_argument("--text")
    p.add_argument("--out", default="outputs/out.wav")
    p.add_argument("--emo-vector", help="8 comma-separated floats")
    p.add_argument("--emo-audio")
    p.add_argument("--emo-text")
    p.add_argument("--emo-alpha", type=float, default=1.0)
    p.add_argument("--ceiling-db", type=float, default=-1.0, help="peak normalise target in dBFS")
    p.add_argument("--no-normalise", action="store_true")
    p.add_argument("--no-fp16", action="store_true")
    args = p.parse_args()

    if args.jobs:
        with open(args.jobs) as f:
            jobs = [json.loads(line) for line in f if line.strip()]
    else:
        if not (args.voice and args.text):
            p.error("give --jobs, or both --voice and --text")
        jobs = [{
            "voice": args.voice, "text": args.text, "out": args.out,
            "emo_vector": [float(v) for v in args.emo_vector.split(",")] if args.emo_vector else None,
            "emo_audio": args.emo_audio, "emo_text": args.emo_text, "emo_alpha": args.emo_alpha,
        }]

    cuda = torch.cuda.is_available()
    print(f">> device: {torch.cuda.get_device_name(0) if cuda else 'CPU (slow)'}", flush=True)
    t = time.time()
    tts = IndexTTS2(
        cfg_path=os.path.join(args.model_dir, "config.yaml"),
        model_dir=args.model_dir,
        use_fp16=cuda and not args.no_fp16,
    )
    print(f">> model loaded in {time.time() - t:.1f}s", flush=True)

    for job in jobs:
        out = job["out"]
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        emo_text = job.get("emo_text")
        t = time.time()
        tts.infer(
            spk_audio_prompt=job["voice"],
            text=job["text"],
            output_path=out,
            emo_audio_prompt=job.get("emo_audio"),
            emo_alpha=job.get("emo_alpha", 1.0),
            emo_vector=job.get("emo_vector"),
            use_emo_text=bool(emo_text),
            emo_text=emo_text,
        )
        msg = f">> {out}: {time.time() - t:.1f}s"
        if not args.no_normalise:
            peak = peak_normalise(out, args.ceiling_db)
            msg += f", peak {20 * np.log10(max(peak, 1e-9)):+.1f} dBFS -> {args.ceiling_db:+.1f} dBFS"
        print(msg, flush=True)


if __name__ == "__main__":
    main()
