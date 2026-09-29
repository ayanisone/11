# Suri TTS dataset (smallest.ai)

Generates one WAV per line of the two CSVs in `data/` using the smallest.ai
Waves API (`POST https://api.smallest.ai/waves/v1/tts`) with the **Suri** voice.

| Setting | Value | API field |
|---|---|---|
| Voice | Suri (looked up via `GET /waves/v1/lightning-v3.1/get_voices`) | `voice_id` |
| Language | auto | `language` |
| Number pronunciation | auto | `number_pronunciation_language` |
| Speed | 1.0 | `speed` |
| Sample rate | 44,100 Hz | `sample_rate` |
| Format | WAV | `output_format` |

Inputs: `data/rashi_pans_transcription.csv` (458 lines) and
`data/teleprompter_lines.csv` (99 lines), 557 clips total.

## Run

Python 3.8+, standard library only.

```bash
cd smallest_tts
export SMALLEST_API_KEY=sk_...        # never commit the key

python3 generate_dataset.py --dry-run     # show the exact request, send nothing
python3 generate_dataset.py --limit 3     # soundcheck: listen to these first
python3 generate_dataset.py               # full run (skips clips already made)
```

If the soundcheck clips sound wrong or garbled, Suri is probably in the Pro
pool; delete `output/suri` and re-run with `--model lightning_v3.1_pro`.

## Output

```
output/suri/
  wavs/<id>.wav      # 44.1 kHz WAV, named by the CSV id
  metadata.csv       # file,text,source_csv,duration_sec (successful clips)
  failures.csv       # only if some lines failed; re-run to retry them
```

Re-running is safe: finished clips are validated and skipped. 429/5xx
responses are retried with backoff; requests are capped at 90/min by default
(`--rpm`, `--workers` to tune).
