#!/usr/bin/env python3
"""Synthesize speech with the NE-TTS multilingual VITS checkpoint.

    ./.venv/bin/python tts.py --list-voices
    ./.venv/bin/python tts.py "ia noksao anga dal-begipa rikgimin nokko nikenga" -v grt_female_westgarohills
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(HERE, "model")
OUT_DIR = os.path.join(HERE, "out")

# The model is character-level with no punctuation; anything outside this set is
# dropped silently by the front-end, so we check the text before spending a
# forward pass on it.
VOCAB = set(" abcdefghijklmnopqrstuvwxyz·âêîûüṭ")


def load_meta():
    path = os.path.join(MODEL_DIR, "tts_release_meta.json")
    if not os.path.exists(path):
        sys.exit("model/ not found - run ./setup.sh first")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check_text(text):
    """Return cleaned text, warning about characters the front-end will drop."""
    dropped = sorted({c for c in text if c not in VOCAB})
    if dropped:
        shown = " ".join(repr(c) for c in dropped)
        print(f"warning: dropping {len(dropped)} out-of-vocab character(s): {shown}",
              file=sys.stderr)
        print("         the model has no punctuation and no capitals; text is "
              "lowercased and filtered.", file=sys.stderr)
    return "".join(c for c in text if c in VOCAB)


def main():
    ap = argparse.ArgumentParser(description="NE-TTS: 16 North-East India languages.")
    ap.add_argument("text", nargs="?", help="lowercase romanized text to speak")
    ap.add_argument("-v", "--voice", help="speaker name, e.g. grt_female_westgarohills")
    ap.add_argument("-l", "--language", help="ISO code; inferred from the voice prefix if omitted")
    ap.add_argument("-o", "--out", help="output wav path (default: out/<voice>.wav)")
    ap.add_argument("--seed", type=int, default=1234, help="torch seed (default: 1234)")
    ap.add_argument("--peak", type=float, default=-1.0,
                    help="peak-normalize to this dBFS (default: -1.0; use 0 for the "
                         "model card's full-scale behaviour)")
    ap.add_argument("--cuda", action="store_true", help="run on GPU")
    ap.add_argument("--list-voices", action="store_true", help="print voices and exit")
    args = ap.parse_args()

    meta = load_meta()
    voices = sorted(meta["speaker_map"])

    if args.list_voices:
        by_lang = {}
        for v in voices:
            by_lang.setdefault(v.split("_", 1)[0], []).append(v)
        for lang in sorted(by_lang):
            print(f"{lang}  {' '.join(by_lang[lang])}")
        print(f"\n{len(voices)} voices across {len(by_lang)} languages, "
              f"{meta['sample_rate']} Hz mono")
        return

    if not args.text or not args.voice:
        ap.error("both TEXT and --voice are required (see --list-voices)")
    if args.voice not in meta["speaker_map"]:
        ap.error(f"unknown voice {args.voice!r}; see --list-voices")

    language = args.language or args.voice.split("_", 1)[0]
    if language not in meta["language_map"]:
        ap.error(f"unknown language {language!r}; see --list-voices")

    text = check_text(args.text.lower())
    if not text.strip():
        sys.exit("error: nothing left to speak after filtering")

    import numpy as np
    import soundfile as sf
    import torch
    from TTS.utils.synthesizer import Synthesizer

    torch.manual_seed(args.seed)

    # config.json resolves speakers.pth and language_ids.json relative to the cwd.
    cwd = os.getcwd()
    os.chdir(MODEL_DIR)
    try:
        synth = Synthesizer(
            tts_checkpoint="model.pth",
            tts_config_path="config.json",
            tts_speakers_file="speakers.pth",
            tts_languages_file="language_ids.json",
            use_cuda=args.cuda,
        )
        wav = synth.tts(text, speaker_name=args.voice, language_name=language)
    finally:
        os.chdir(cwd)

    wav = np.asarray(wav, dtype=np.float64)
    peak = float(np.max(np.abs(wav)))
    if peak > 0:
        wav = wav * (10.0 ** (args.peak / 20.0) / peak)

    out = args.out or os.path.join(OUT_DIR, f"{args.voice}.wav")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    sf.write(out, wav, synth.output_sample_rate, subtype="PCM_16")

    rms = 20 * np.log10(float(np.sqrt((wav ** 2).mean())))
    print(f"{out}  {len(wav) / synth.output_sample_rate:.2f}s  "
          f"{synth.output_sample_rate} Hz mono  peak {args.peak:+.1f} dBFS  rms {rms:+.1f} dBFS")


if __name__ == "__main__":
    main()
