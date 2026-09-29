# Suri TTS dataset (smallest.ai)

Generates one WAV per line of the two CSVs in `data/` using the smallest.ai
Waves API (`POST https://api.smallest.ai/waves/v1/tts`) with the **Suri** voice.

| Setting | Value | API field |
|---|---|---|
| Voice | Suri (`lightning_v3.1_pro` pool, auto-detected) | `voice_id`, `model` |
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

Suri lives in the Lightning v3.1 **Pro** catalog; `--model auto` (default)
finds the voice in the Pro or standard catalog and routes to that pool.

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

## Consolidated ~1-minute tracks

```bash
python3 consolidate.py --src ../suri_dataset --out ../suri_dataset/consolidated
```

Joins the clips in `metadata.csv` order into 45–60 s tracks. Each clip's
built-in head/tail silence (~350–450 ms) is trimmed to a 50 ms pad with 5 ms
fades, then a 400 ms gap is inserted, so lines are ~500 ms apart. A clip that
would push a track past 60 s starts the next track (clips are never cut), and
the last few tracks are rebalanced so none falls under 45 s. Outputs
`track_NNN.wav`, `track_NNN.txt` (transcript), and `tracks.csv` (per-clip
start/end times). Tune with `--gap-ms`, `--min-sec`, `--max-sec`.
