# bn-dub — Bengali dubbing chain

ElevenLabs Dubbing v2 rejects `bn` (`Target language 'bn' is not supported`). This repo rebuilds the dubbing
channel strip from the individual processors ElevenLabs *does* sell for Bengali, with Claude handling the
translation, and puts a Gradio console on top so you can edit the cue sheet between stages.

```
source ─► stem split ─► Scribe STT ─► Claude translate ─► Eleven v3 TTS ─► fit to slot ─► Scribe QA ─► mix ─► mux
          (vocals /     (words +      (length-aware,       (one clip per    (atempo, or     (back-        (vocals +
           background)   speakers)     spoken Bengali)      line, bn)        re-translate)   transcribe)   bg stem)
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

**Tab 1 · Session** — name the project, drop a video/audio file, pick the source language and background
mode, hit *Create*. It extracts the mix, splits stems, transcribes with speaker labels. Then fetch voices
and assign one per speaker (or *Clone this speaker* to IVC a voice from their own isolated lines).

**Tab 2 · Script** — the cue sheet. Each row is one line: `start`, `end`, `speaker`, `source`, `target`,
`romanised`, `ratio`, `status`, `locked`, `notes`. *Translate* fills `target`; edit anything, *Save edits*;
*Generate* speaks and fits; *Verify* back-transcribes and flags misses. Tick `locked` on lines you've
approved so later passes leave them alone. *Audition* plays the original slot and the fitted dub side by side.

**Tab 3 · Mix** — dub vocal gain, background gain, duck amount; *Render* writes `projects/<name>/out/dub.wav`
and `dubbed.mp4` (video stream copied, not re-encoded).

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

## QA gate

Eleven v3 can repeat or false-start on Indic scripts. *Verify* transcribes each generated clip back with
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
- v3/v4 infer the language from the script; `language_code` is only sent for the v2.5 models.
- Costs: Scribe per minute (×2 with Verify), TTS per character, Claude per token. Instant voice cloning needs
  an ElevenLabs plan that includes IVC.
