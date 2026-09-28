# 11

## Batch TTS from a CSV (ElevenLabs API)

1. Put your names in a CSV with a `name` column (optional `pronunciation` and `text` columns — see `tts/names.example.csv`).
2. Edit `tts/settings.json` — it mirrors the ElevenLabs web panel:

   | Web panel | `settings.json` | Values |
   |---|---|---|
   | Model | `model_id` | e.g. `eleven_v4` |
   | Stability | `voice_settings.stability` | 0 = Creative … 1 = Robust |
   | Similarity | `voice_settings.similarity_boost` | 0 = Low … 1 = High |
   | Language | `language_code` | `"auto"` or an ISO 639-1 code (`en`, `hi`, …) |
   | Audio effects | `audio_effects.filter_preset_id` | `old_radio`, `robot`, `cheap_microphone`, `phone`, `low_quality_phone`, `bright_phone`, or `null` |
   | | `audio_effects.environment_id` (reverb) | `small_room`, `big_room`, `hall`, `tunnel`, `street`, `valley`, `forest`, or `null` |
   | | `audio_effects.distance` | 0 … 1 (proximity EQ; 0 = close) |
   | | `audio_effects.send_level` | 0 … 1 (effect level) |
   | Output Format | `output_format` | e.g. `mp3_44100_192`, `wav_44100`, `wav_48000` |

   `text_template` is the line spoken per row; `{name}` is replaced with the name.
3. Run:
   ```
   export ELEVENLABS_API_KEY=...   # your key; never commit it
   python3 tts/batch_tts.py --list-effects        # live list of effect IDs
   python3 tts/batch_tts.py names.csv --limit 3   # test pass
   python3 tts/batch_tts.py names.csv             # full batch
   ```
   Files land in `tts/output/` with a `log.csv`. Existing files are skipped, so re-running only fills gaps.

Notes:
- With all effects off (`null` / `0`), no effects are sent and takes come back dry (mono). Turning on an environment returns stereo audio with a reverb tail.
- The effects endpoints (`audio_effects`, `/v1/audio-effects/*`) work on the live API but are not yet in ElevenLabs' published API reference, so they could change.
- `language_code` is ignored by `eleven_multilingual_v2` (it auto-detects). `style` and `use_speaker_boost` only take effect on models that support them (e.g. `eleven_multilingual_v2`), not `eleven_v4`.
