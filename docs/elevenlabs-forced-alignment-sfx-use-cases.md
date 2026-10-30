# ElevenLabs Forced Alignment + Sound Effects v3: use cases for the audio team

Researched 2026-10-30 against the live API (`api.elevenlabs.io`, enterprise key) and the live OpenAPI spec
(`/openapi.json`). The docs site was not reachable from the research environment, so every fact below was
either probed live or read from the spec, and is labelled that way.

## Summary

- **Forced Alignment works, and it is cheap.** It handles Hindi, Devanagari and mixed "Hi प्रिया" lines.
  Think of it as Beat Detective with the score already loaded: you give it the script, and it marks where each
  word and character lands. It does not transcribe. Because it has to place every scripted word somewhere,
  a word the TTS **dropped** gets squeezed into a 20–40 ms sliver with a very high loss score. That makes it a
  reliable detector of dropped words in batch VO, which is the hallucination problem the team has.
- **SFX v3 is live.** `eleven_text_to_sound_v3` is accepted by `/v1/sound-generation` and listed in the spec.
  It has **no new parameters** over v2: same 0.5–30 s duration, `loop`, `prompt_influence` and output formats.
  In a single A/B, v3's UI click came back at a usable level (−6 dBFS peak) while v2's was almost silent
  (−40 dBFS). The `loop: true` room tone had a seamless seam. There is still **no video-to-SFX endpoint**;
  spotting stays on our side.
- **Best first move:** run `tools/align_qa.py qa` over every batch-TTS job before delivery. Next, switch the
  name renders to TTS `/with-timestamps` so name boundaries come back for free with the audio.
- **Spend for this whole study:** 239 characters (credits), summed from the `character-cost` header of each response.
  The details are at the end.

## Verified API facts

Legend: **LIVE** = probed or run against the live API in this study. **SPEC** = read from the live OpenAPI spec only.

### Forced Alignment: `POST /v1/forced-alignment`

| Fact | Status |
|---|---|
| `multipart/form-data` with exactly two fields: `file` (audio, any major format, < 1 GB) and `text` (the script) | SPEC + LIVE |
| No language, granularity or model parameters. Probed `language_code`, `granularity`, `model_id`, `diarize`, `enabled_spooled_file`, `timestamps_granularity`, `cloud_storage_url` and `file_format`: all silently ignored | LIVE |
| Language is auto-detected. Devanagari, English and mixed English+Devanagari all aligned | LIVE |
| Response has `characters[]` `{text,start,end}`, `words[]` `{text,start,end,loss}` and an overall `loss` | SPEC + LIVE |
| **Spaces come back as their own entries in `words[]`.** Punctuation stays attached to the word (`"Priya,"`, `"है।"`). Filter out whitespace entries | LIVE |
| **Timestamps sit on a 20 ms grid** (0.08, 0.24, 0.34, …). A forced-in missing word can get a 1 ms offset (`1.841`) | LIVE |
| `loss` is lower when the match is better. On correct takes, English words scored 0.50–0.91 and Hindi words 0.71–1.10 | LIVE |
| Diarization is not supported (per the spec text) | SPEC |
| Empty `text` → 422. Non-audio file → 400 `invalid_audio`. Neither is charged | LIVE |
| Cost (`character-cost` header): **1** for clips of 2.2–2.7 s, **2** for 3.8 s, so roughly 0.5 credit per second of audio | LIVE (small sample) |

### Sound Effects: `POST /v1/sound-generation`

| Fact | Status |
|---|---|
| `model_id` enum is `eleven_text_to_sound_v2` and `eleven_text_to_sound_v3`. A fake ID gets a 422 naming both | SPEC + LIVE |
| v3 is **not** listed in `GET /v1/models`, which lists TTS and STS models only. Use the sound-generation enum as the source of truth | LIVE |
| The spec default is still v2, so **pass `model_id` explicitly** | SPEC |
| `duration_seconds` must be 0.5–30, the same for v2 and v3. Out of range → 400 (not charged). Omit it to let the model choose | LIVE |
| `prompt_influence` must be 0–1 (spec default 0.3). `loop` must be a boolean | LIVE |
| Output formats: `mp3_*` (up to 192 kbps), `wav_8000`–`wav_48000`, `pcm_*`, `opus_48000_*`, `ulaw/alaw_8000`. There is no 96 kHz | SPEC + LIVE |
| Probed for hidden v3 parameters (`seed`, `negative_prompt`, `num_variations`, `stereo`, `bpm`, `fade_in/out`, `reference_audio`, `video`, `start/end_seconds` and about 25 more): **none recognised** | LIVE |
| No video-to-SFX endpoint (`/v1/video-to-sfx` and similar return 404). `/v1/music/video-to-music` exists, but it makes music, not SFX | LIVE |
| `wav_48000` returns **stereo, 16-bit, 48 kHz** | LIVE |
| Short durations come back 20 ms short: 0.5 s → 0.480 s and 1.5 s → 1.480 s. 6 s came back as exactly 6.000 s | LIVE |
| Cost is about **9.3 credits per second** when `duration_seconds` is set (0.5 s = 5, 1.5 s = 14, 6 s = 56). **An auto-duration request billed 47 credits for a 0.48 s clip**, so always set the duration | LIVE |
| `enable_logging=false` (zero retention) is available to enterprise accounts | SPEC |

### Related things found along the way

| Fact | Status |
|---|---|
| `POST /v1/text-to-speech/{voice_id}/with-timestamps` works on `eleven_v4`. It returns base64 audio plus per-character `alignment` and `normalized_alignment`, at the same price as plain TTS | LIVE |
| Its name boundary for `प्रिया` came out at 0.32–0.64 s. Forced Alignment on a separate render of the same line put it at 0.34–0.66 s, so both tools agree to within 20 ms | LIVE |
| That response also carries a `quality_check` key. It was `null`, it is not in the response schema, and no request field turns it on (`quality_check` and three variants were ignored). Worth asking the ElevenLabs account team about, because it may be an ASR check for hallucinations | LIVE, undocumented |
| `GET /v1/audio-effects/catalog` is now in the spec. Besides presets and environments, it lists **`background_noises`**: `call_center`, `cafe`, `city`, `keyboard` | SPEC + LIVE |

## Test results

### Alignment: 4 real takes (Eleven v4, repo voice, `tts/batch_tts.py`) plus 5 deliberately wrong scripts

| Take | Script given to aligner | Overall loss | What the aligner did | `align_qa.py` verdict |
|---|---|---|---|---|
| EN "Hi Priya, welcome aboard." | correct | 0.60 | clean | OK |
| HI "नमस्ते प्रिया, आपका स्वागत है।" | correct | 0.78 | clean | OK |
| Mixed "Hi प्रिया, welcome aboard." | correct | 0.67 | clean. English "Hi" loss 0.91 (highest word) | OK |
| HI health line (9 words) | correct | 0.90 | clean | OK |
| EN | + "today" (**TTS dropped a word**) | 0.88 | "today." squeezed to **19 ms**, loss **1.77** | **FAIL collapsed** |
| HI health | + "तेज़", "बहुत" (**2 dropped words**) | 1.39 | "तेज़" squeezed to **39 ms**, loss **3.83**. "बहुत" lasted 80 ms, loss **1.94** | **FAIL ×2** |
| EN | "welcome" removed (**TTS added a word**) | 0.82 | "aboard." stretched to 820 ms, absorbing "welcome" | WARN stretched |
| EN | "Rahul" instead of "Priya" (**wrong/garbled name**) | 0.78 | timing unchanged. Loss 1.19 against a clip median of 0.77 | WARN loss |
| HI | "राहुल" instead of "प्रिया" | 0.98 | timing unchanged. Loss 1.27 against a median of 0.88 | WARN loss |

Reading the results:
- **Dropped words: strong signal.** The aligner must place every scripted word, so a missing word is like
  forcing quantise onto a hit that was never played: it gets crushed into a sliver. Duration under 60 ms or
  loss of 1.6 or more catches it.
- **Wrong or garbled words: weak signal.** Loss rises about 1.4–1.6× over the clip's median, but the timing
  looks normal. That is a WARN, not proof.
- **Extra spoken words: weak signal.** They get absorbed into a neighbouring word, which looks "stretched".
  Use a speech-to-text diff for these.
- **Use relative thresholds, not absolute ones.** Hindi's baseline loss sits about 0.2–0.3 higher than English. Treat each
  language like a mic channel with its own noise floor: set the gate threshold relative to that channel's floor
  (the clip median), not to one fixed number for the whole desk. That is how `align_qa.py` works.
- **Caveat:** the defaults (`--min-word 0.06 --fail-loss 1.6 --warn-ratio 1.4 --stretch-ratio 1.4`) were tuned
  on these same nine takes. Recalibrate on a real batch of about 200 clips with known good and bad takes before you trust the
  WARN tier.

### SFX: 4 generations on v3 and 1 on v2, all `wav_48000`

| Clip | Model / settings | Credits | Result |
|---|---|---|---|
| UI click | v3, 0.5 s, `prompt_influence` 0.6 | 5 | 0.48 s, peak −6.1 dBFS, transient at 0–2 ms (sample-accurate for spotting), effectively mono |
| UI click (A/B) | v2, same prompt | 5 | peak **−39.7 dBFS**, practically unusable without +30 dB of gain |
| Whoosh "left to right" | v3, 1.5 s, PI 0.5 | 14 | 1.48 s, 172 ms pre-roll, peak at 636 ms. **The pan direction was honoured**: the second half is 8 dB right-heavy |
| Office room tone | v3, 6 s, `loop: true` | 56 | 6.000 s, −36.8 dBFS RMS. **The seam is seamless**: sample jump at the wrap 0.0005, head and tail RMS within 2 dB |
| "Camera shutter click" | v3, no duration | **47** | 0.48 s. The auto-duration request was billed as if it were about 5 s |

`prompt_influence` behaves like **quantise strength**. At 1.0 the output follows the brief rigidly with
little variation between takes. At 0.3 (the default) it is "humanised": more variety, but it sometimes drifts off-brief.
The analogy only covers how literal the result is: it doesn't swing timing.

## Use cases, ranked

Value is weighted toward the team's actual pain points. Effort assumes the tool in `tools/` already exists.

| # | Use case | Value | Effort | API | Cost per unit | Verdict |
|---|---|---|---|---|---|---|
| 1 | Auto-QA of batch TTS (11-language health VO) | **High** | **Low** | Forced Alignment | ~0.5 credit/s of audio (~2–5 per VO line) | **Do now** |
| 2 | Name-clip boundaries for trimming and splicing into a template VO | **High** | **Low** | TTS `/with-timestamps` (free with the render) or Forced Alignment | 0 extra, or ~1 credit/clip | **Do now** |
| 3 | SRT/captions in Indian languages, word timing for kinetic type | High | Medium | Forced Alignment | ~0.5 credit/s | Do next |
| 4 | Custom UI-click and whoosh libraries for explainers | Medium–High | Low | SFX v3 | ~9.3 credits/s (a 0.5 s click = 5) | Do next |
| 5 | Seamless ambience and room-tone loops | Medium | Low | SFX v3, `loop: true` | ~9.3/s, so a 30 s bed ≈ 280 | Do next |
| 6 | VO timing maps for editors and SFX spotting markers | Medium | Low | Forced Alignment (reuse #1's output) | 0 extra | Free by-product of #1 |
| 7 | Alignment-driven ducking / SFX placement map ("sidechain from the script") | Medium | Medium | Forced Alignment plus local DSP | 0 extra | Pilot on one TVC |
| 8 | Per-cue SFX for spotted video events | Medium | Medium | SFX v3 (text only) | ~9.3/s per cue | Keep: spotting stays local |
| — | Fully automatic SFX from video | — | — | none exists | — | **Discard**: no video-to-SFX endpoint |
| — | Lip-sync / viseme prep | Low | — | — | — | **Discard**: output is characters, not phonemes, on a 20 ms grid |

### 1. Auto-QA of batch TTS

- **What it solves.** Dropped words in batch VO: the hallucinations that slip through when nobody listens to clip 847 of 2,000.
  Forced Alignment is a null test against the script. Whatever doesn't cancel is flagged.
- **Calls.** One `POST /v1/forced-alignment` per take (`file` plus the exact `text` that was sent to TTS).
- **Cost.** About 0.5 credit per second. A 1,000-clip batch of 8-second health lines costs about 4,000 credits, which is a rounding error
  next to the TTS itself.
- **Limitations.** It catches dropped words well. It catches swapped or garbled words weakly (WARN only), and extra words only through
  the "stretched" heuristic. Script normalisation matters: if the TTS read "30" as "तीस" but the script says "30",
  the aligner will flag it. Align against the text you actually sent to TTS. Pair it with a speech-to-text diff for full coverage:
  alignment checks timing, STT checks content. They are two meters on the same bus.
- **Sketch.** This is already built:
  ```
  # takes.csv: file,text  (text = exactly what went to TTS)
  python3 tools/align_qa.py qa takes.csv --report qa.csv   # exit 1 if any FAIL
  ```
  It flags `collapsed`, `high_loss`, relative `loss`, `stretched`, long inter-word `gap`, and head/tail silence
  (WAV). It caches results by audio+text hash, so re-runs are free. Hook it in after `tts/batch_tts.py` by writing
  `file,text` from its `log.csv` and re-rendering every FAIL.

### 2. Name-clip trimming and splicing

- **What it solves.** "Hi <name>." clips spliced into a template VO with no clicks and consistent pre-roll.
- **Calls.** Preferred: render with `POST /v1/text-to-speech/{voice}/with-timestamps` instead of the plain
  endpoint. The character timings arrive with the audio at no extra cost, so the batch has nothing left to align. For
  clips that already exist, use Forced Alignment.
- **Limitation: the 20 ms grid.** That is half a frame at 25 fps, and too coarse to cut on. Treat the aligner times like
  a rough marker, then snap to the quietest point nearby, as you'd snap an edit to a zero crossing, and add a 5–10 ms
  crossfade. `align_qa.py cut` does the snap: it searches ±40 ms in 1 ms windows. On the test take it moved
  `प्रिया` from 0.34–0.66 s to 0.308–0.699 s, widening the cut to the quietest points either side.
  Where the analogy stops holding: a zero crossing alone is not enough. Voiced names have no silence between words, so
  for a name followed straight by "welcome" you still need a crossfade, or a template that leaves a pause after the name.
- **Sketch:**
  ```
  python3 tools/align_qa.py cut 003_mix.wav "Hi प्रिया, welcome aboard." --word 2
  # {"word": "प्रिया,", "aligner_in": 0.34, "aligner_out": 0.66, "cut_in": 0.3075, "cut_out": 0.6993, ...}
  ```
  For new batches: switch `synthesize()` in `tts/batch_tts.py` to the `/with-timestamps` URL, `base64`-decode
  `audio_base64`, and write `alignment` next to each file as JSON.

### 3. Subtitles/SRT and kinetic typography in Indian languages

- **What it solves.** Burnt-in or sidecar captions for reels and DVCs in 11 languages, plus word- and character-level timing for
  animated text, without hand-spotting.
- **Calls.** Forced Alignment on the final mixed VO stem (or the dry VO), with the approved translated script.
- **Cost.** ~0.5 credit/s, so a 30 s DVC costs about 15.
- **Limitations.** Drop the whitespace entries. Punctuation stays glued to words, which is fine for captions. Character timings
  are per Unicode code point: a Devanagari matra (ि, ा) gets its own slice, so for per-letter animation group
  characters into aksharas (grapheme clusters) first. There is no diarization, so align each speaker's lines separately.
  Use the dry VO stem rather than the full mix where you can: music under the VO raises loss.
- **Sketch:**
  ```python
  words = [w for w in resp["words"] if w["text"].strip()]
  # chunk into caption cues: break at punctuation (।,.?!) or after ~42 chars / 2 lines / 7 s
  for i, cue in enumerate(chunks(words), 1):
      print(i, srt_time(cue[0]["start"]), "-->", srt_time(cue[-1]["end"]), " ".join(w["text"] for w in cue), sep="\n")
  ```

### 4. UI-click and whoosh libraries for explainers

- **What it solves.** Brand-consistent UI, graphic and transition sound without trawling libraries. Generate a few
  variations per prompt, pick, and file them in the bank.
- **Calls.** `POST /v1/sound-generation?output_format=wav_48000` with `model_id: eleven_text_to_sound_v3`, a set
  `duration_seconds`, and `prompt_influence` 0.5–0.7.
- **Cost.** A click ≈ 5 credits, a 1.5 s whoosh ≈ 14. A 50-sound starter kit is under 1,000 credits.
- **Limitations.** There's no seed and no variations parameter, so each call is a fresh roll. Durations come back 20 ms short.
  Whooshes include their own pre-roll (172 ms in the test), so **sync to the peak, not the file start**: compute the peak
  and store it in the cue sheet. Output is 16-bit only.
- **Sketch:**
  ```python
  body = {"text": prompt, "model_id": "eleven_text_to_sound_v3", "duration_seconds": 0.5, "prompt_influence": 0.6}
  wav = post("/v1/sound-generation?output_format=wav_48000", body)
  peak_ms = argmax(abs(samples)) / 48   # store as the sync point
  ```

### 5. Seamless ambience and room-tone loops

- **What it solves.** Fill beds under VO, room tone to patch edits, and ambience loops for explainers.
- **Calls.** As in #4, with `"loop": true`. The maximum is 30 s per generation.
- **Cost.** ~9.3/s, so a 30 s loop ≈ 280 credits. Generate it once and reuse it everywhere.
- **Limitations.** At 30 s maximum, a loop repeated under a 60 s spot may be audible on steady material. Crossfade-chain two
  different loops (A/B) to break up the repetition. Check the loop under headphones: the seam test passed numerically on one sample.

### 6. VO timing maps for editors and SFX spotting

- **What it solves.** It gives editors and the SFX pass a marker for every word (CSV, or markers imported into the DAW or NLE).
  It costs nothing extra if #1 already ran, because the cached JSON in `.align_cache/` already holds the timings.
- **Limitation.** These are word-level timings only. "Spotting" visual events still needs the video analysis in the SFX pipeline.

### 7. Script-driven ducking and SFX placement: a "sidechain from the script"

- **What it solves.** It generates a music ducking automation lane, and "keep out" zones for SFX, from the VO's word times. It's
  a sidechain key computed in advance, so the dip can start before the first syllable (a negative-latency
  lookahead) instead of reacting to it.
- **Calls.** Forced Alignment output only. The ducking is local DSP or DAW automation.
- **Sketch:**
  ```
  for each speech run (words merged where gap < 300 ms):
      duck music -6 dB from run.start - 120 ms (attack 80 ms) to run.end + 250 ms (release 400 ms)
      mark [run.start, run.end] as "no hard SFX transients" in the cue sheet
  ```
- **Limitation.** It's only as good as the alignment, and gaps are on a 20 ms grid. That's fine for ducking, which works in hundreds of ms.

### 8. Per-cue SFX for spotted events

- **What it solves.** It fills cues where the bank has no match. Spotting (cuts, on-screen events) stays local. Each cue's description
  becomes a text prompt for SFX v3, with `duration_seconds` taken from the cue length.
- **Limitation.** There is no video conditioning. The model never sees the picture, so sync comes entirely from your cue
  times plus the peak offset (#4). Budget for 2–3 rolls on hero cues.

## Next steps

1. **Wire QA into batch TTS.** After each `batch_tts.py` run, build `file,text` from `log.csv`, run
   `align_qa.py qa`, and re-render FAILs automatically (possibly with a different `seed`).
2. **Calibrate the thresholds** on one real 11-language batch of about 200 clips with human pass/fail labels, then adjust
   `--warn-ratio` and `--fail-loss` per language if needed.
3. **Switch the name renders to `/with-timestamps`** so boundaries ship with the audio. Then batch-run `cut`-style snapping
   and export splice points per name.
4. **Ask ElevenLabs** (account team) about: the `quality_check` field on with-timestamps responses; whether an aligner
   language hint is planned; and why the auto-duration SFX call billed 47 credits for a 0.48 s clip.
5. **Pick SFX v3 over v2 by default** wherever the team calls `/v1/sound-generation`. The spec default is still v2.
6. **Pilot #7** (script-driven ducking) on one TVC and compare it against a hand-ridden mix.

## Spend for this study

| Item | Calls | Credits (`character-cost` header) |
|---|---|---|
| TTS test lines (4 × eleven_v4, 108 chars of text) | 4 | 74 |
| TTS with-timestamps comparison (25 chars) | 1 | 15 |
| Forced Alignment (manual runs, tool run, one recheck) | 19 | 23 |
| SFX generations (v3 ×4, v2 ×1, 10 s of audio in total) | 5 | 127 |
| Validation and parameter probes (all 4xx) | ~60 | 0 |
| **Total** | | **239** |

The account's `character_count` rose by about 15.7k over the session window. Idle snapshots and a
single alignment call didn't move it immediately, and this is a shared enterprise workspace, so that rise is
other users' activity: it went up another ~3.7k during a stretch when this study made no billable calls. The figures in the table are the
per-response billing headers.

Test audio and alignment JSON were kept in a scratch directory outside git. No audio, keys or name lists are committed.
