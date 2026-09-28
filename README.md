# 11

## Batch TTS from a CSV (ElevenLabs API)

1. Put your names in a CSV with a `name` column (optional `pronunciation` and `text` columns — see `tts/names.example.csv`).
2. Edit `tts/settings.json`: voice, model, language, output format, script line (`{name}` is replaced per row), and `voice_settings` (stability, similarity_boost, speed).
3. Run:
   ```
   export ELEVENLABS_API_KEY=...   # your key; never commit it
   python3 tts/batch_tts.py names.csv --limit 3   # test pass
   python3 tts/batch_tts.py names.csv             # full batch
   ```
   Files land in `tts/output/` with a `log.csv`. Existing files are skipped, so re-running only fills gaps.

Notes: `language_code` is ignored by `eleven_multilingual_v2` (it auto-detects). `style` and `use_speaker_boost` only take effect on models that support them (e.g. `eleven_multilingual_v2`), not `eleven_v4`.
