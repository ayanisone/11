# bn-dub — Bengali dubbing chain

ElevenLabs Dubbing v2 rejects `bn` (`Target language 'bn' is not supported`). This repo rebuilds the dubbing
channel strip from the individual processors ElevenLabs *does* sell for Bengali, with Claude handling the
translation, and puts a Gradio console on top so you can edit the cue sheet between stages.

```
source ─► stem split ─► Scribe STT ─► Claude translate ─► direct ─► Eleven v4 TTS ─► fit ─► Scribe QA ─► mix ─► mux
          (vocals /     (words, speakers, (length-aware     (measure the    (one clip     (atempo or   (back-
           background)   language)         spoken Bengali)   original take,  per line)     re-translate) transcribe)
                                                             write [tags])
```

Swap it out for ElevenLabs' own dubbing the day they ship Bengali on v2; the project file keeps your edits.

## Setup (your machine)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # or: pip install -r requirements.txt
cp .env.example .env             # add ELEVENLABS_API_KEY and ANTHROPIC_API_KEY
ffmpeg -version                  # required (brew install ffmpeg / apt install ffmpeg)
```

Optional, for a cleaner background stem on music-heavy sources: `pip install demucs` (slow without a GPU).

## Run the console

```bash
python app.py            # http://127.0.0.1:7860
# or
bn-dub ui --port 7860
```

One page, three moves:

1. **Drop a file**, set *Speaker similarity* (natural Bengali ◄──► like the original speaker), press
   **Prepare script**. It splits stems, transcribes (language auto-detected), translates, directs the
   performance, and instant-clones one voice per speaker from their own isolated lines (falls back to a
   library voice if your plan has no IVC).
2. **Edit the Bengali column** where needed — `[tags]` direct delivery, `…` is a pause. Tick *lock* on lines
   you're happy with.
3. **Generate dub** — speaks (Eleven v4, stability 0.5, no language override), fits each line to its slot,
   verifies, mixes, muxes. Download `dubbed.mp4`. *Audition a line* plays original vs dub.

## CLI (batch)

```bash
bn-dub create ep01 input.mp4 --source-lang en --background isolate
bn-dub voices                                  # list voice_ids
bn-dub voice ep01 speaker_0 <voice_id>
bn-dub run ep01                                # translate → tts → verify → mix
bn-dub stage ep01 translate --ids 3,7          # re-run one stage on some lines
bn-dub stage ep01 mix
```

## How the timing works

Every line owns a **slot**: its own duration plus up to 1.5 s of the silence before the next line.
After TTS, `ratio = clip length ÷ slot`:

| ratio | action |
|---|---|
| ≤ 1.0 | leave it (natural pause); if < 0.6 slow it slightly |
| 1.0 – 1.15 | `atempo` to fit exactly — pitch untouched, inaudible at this range |
| > 1.15 | ask the translator for a line N% shorter, regenerate (up to 3 tries) |
| still too long | clamp at ×1.35 and flag `warn` with the spill in `notes` |

Tune `max_stretch`, `hard_stretch`, `slot_pad` in `bn_dub/config.py`.

## Voice direction

Before TTS, each line's original take is measured from the isolated vocal — pauses (from the waveform, labelled
by the word they follow), words/sec, loudness and pitch range, terminal contour, words hit harder or held
longer — relative to that speaker's own average. Claude turns the numbers into ElevenLabs performance tags
(`[calm]`, `[urgent]`, `[quiet intensity]`, …) and punctuation on the Bengali line, words untouched. The
measurements outrank any impression of the audio; a model guessing from sound alone invents deliveries.

## QA gate

Eleven v4 can repeat or false-start on Indic scripts. *Verify* transcribes each generated clip back with
Scribe and scores it against the script (punctuation/case-insensitive similarity, threshold 0.72). On a miss
it applies a punctuation-first fix (commas, sentence breaks — never a rewrite), regenerates, and re-checks.
Lines that still miss are marked `warn` with what Scribe heard, so you can fix them by ear.

## Background stem modes

- `isolate` (default) — ElevenLabs Voice Isolator gives the vocal; background = mix − vocal, after
  cross-correlation alignment. Clean on VO-over-music; leaves a faint ghost on dense dialogue-and-score mixes.
- `demucs` — local source separation, cleaner, needs `pip install demucs`.
- `duck` — keeps the original mix and sidechain-ducks it under the new vocal (5 ms attack / 250 ms release).
  Only sensible when the original voice is quiet or you want it as a bed.
- `none` — dub vocals only.

## Project layout

```
projects/<name>/
  project.json        the session file: every stage reads/writes this
  source.<ext>        copied input
  mix.wav             extracted full mix
  vocals.wav  background.wav
  segments/NNNN.tts.wav   raw TTS      segments/NNNN.fit.wav   after stretch
  out/dub.wav  out/dubbed.mp4
```

## Tests

```bash
pytest
```

Offline: timing math, segmenting, numpy assembly/duck/limit, lag detection, project round-trip. The API
stages are thin wrappers and are exercised by running a project.

## Limits

- Lip-sync is not attempted; audio timing only.
- The `isolate` background is a phase-inverted subtraction — see the ghost note above.
- v4 infers the language from the script; no `language_code` is sent. Scribe detects the source language.
- Costs: Scribe per minute (×2 with Verify), TTS per character, Claude per token. Instant voice cloning needs
  an ElevenLabs plan that includes IVC.
