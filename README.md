# 11 — NE-TTS runner

A repeatable wrapper around
[`sulabhkatiyar/indian-ne-multilingual-tts`](https://huggingface.co/sulabhkatiyar/indian-ne-multilingual-tts):
a multi-speaker VITS model covering 16 low-resource North-East India languages
in 23 voices, at 22 050 Hz mono.

## Run it

```bash
./setup.sh                                   # idempotent; safe to re-run
./.venv/bin/python tts.py --list-voices
./.venv/bin/python tts.py "ia noksao anga dal·begipa rikgimin nokko nikenga" \
    -v grt_female_westgarohills
```

Output lands in `out/<voice>.wav`. The language code is inferred from the voice
name prefix, so `-l` is only needed to override it.

`setup.sh` creates `.venv`, installs the pinned dependencies and downloads the
346 MB checkpoint into `model/`. Cold start takes a few minutes, almost all of
it the dependency install; a warm re-run is instant because each stage is
skipped when it is already done. Neither `.venv/` nor `model/` is committed.

## Requirements

**Python 3.12.** The dependency pins in `requirements.txt` come from the model
card and the install breaks without them. If `python3.12` is not on your PATH,
point at it explicitly:

```bash
PYTHON=/usr/bin/python3.12 ./setup.sh
```

CPU is the default and runs at roughly 4x realtime (a 5-second line renders in
about 1.2 s). Pass `--cuda` if you have a GPU.

## Two things the model card is quiet about

**Output level.** Coqui's `save_wav` peak-normalizes to full scale, so stock
output sits at 0 dBFS with no headroom — stack two clips and you clip. `tts.py`
normalizes to **−1.0 dBFS** instead; `--peak 0` restores the original
behaviour, and any other value sets the target.

**The text front-end is a brick wall.** The model is character-level over a
34-character vocabulary (space, `a–z`, and `·âêîûüṭ`) with *no punctuation and
no capitals*. Characters outside that set are dropped silently by the
front-end — no error, just missing content. `tts.py` lowercases the input and
warns about every character it drops, so a sanitization problem shows up as a
message rather than as a word that quietly vanished from the audio.

## Options

| flag | meaning |
|---|---|
| `-v, --voice` | speaker name (required); see `--list-voices` |
| `-l, --language` | ISO code; inferred from the voice prefix if omitted |
| `-o, --out` | output path (default `out/<voice>.wav`) |
| `--seed` | torch seed, default `1234` |
| `--peak` | target peak in dBFS, default `-1.0` |
| `--cuda` | run on GPU |

Inference settings are whatever `config.json` ships with (`use_sdp=true`,
`inference_noise_scale=0.667`, `inference_noise_scale_dp=1.0`,
`length_scale=1.0`).

## Attribution

Model and training data are CC-BY-4.0, derived from the
[ARTPARK-IISc Vaani](https://vaani.iisc.ac.in/) project. Retain that
attribution when you use these voices.
