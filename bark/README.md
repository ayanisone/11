# Bark test bench

[suno/bark](https://huggingface.co/suno/bark) text-to-audio, run through the Hugging Face `transformers` port, with a small Gradio UI.

## Run

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r bark/requirements.txt
python bark/app.py          # UI on http://localhost:7860
```

CLI one-shot:

```bash
python bark/smoke_test.py suno/bark-small "Hello! [laughs] Testing Bark." v2/en_speaker_6 out.wav
```

## Notes

- Output: 24 kHz mono float32.
- Two models: `suno/bark-small` (faster, rougher) and `suno/bark` (full quality, ~3x slower).
- On CPU, expect generation to run many times slower than real time. A GPU makes it near real time.
- Bark is happiest with ~13 s of text per generation; split longer scripts into sentences.
- Cues: `[laughter]`, `[laughs]`, `[sighs]`, `[music]`, `[gasps]`, `[clears throat]`, `—`/`...` for hesitation, `♪` for singing, CAPS for emphasis.
- Voice presets: `v2/<lang>_speaker_<0-9>` (en, de, es, fr, hi, it, ja, ko, pl, pt, ru, tr, zh).
