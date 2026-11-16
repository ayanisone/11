# QC findings: RBC reggaeton (rhyming lyrics, 55 s), run 2026-11-16

Method: vocals separated with the **ElevenLabs voice isolator** (demucs could not run here, see "Gaps" below). Each song was transcribed 4 times: ElevenLabs Scribe v1 on the full mix, Scribe v1 twice on the vocal stem, and Sarvam Saaras v4 `codemix` on the vocal stem. Sarvam `verbatim` was run once more as a read-only reference. Transcripts were scored with the kit's `song_qc_score.py`, and the doubtful spots were re-checked with `slice_check.py` on all 10 engine runs. The first slice run used Sarvam only, because a placeholder had overridden the environment's ElevenLabs key; it was re-run with the real key.

## Verdicts after review

| Song | Scorer verdict | Final | Issue | Time | Action |
|---|---|---|---|---|---|
| rbc_reggaeton_rhyming_take2 | FAIL | **PASS (minor REVIEW)** | Sings "on average" instead of "on an average" (4/4 runs). The scorer's FAIL "100l" and its REVIEW "point" and "life" items are scoring artifacts (see below) | 0:09 | Deliver |
| rbc_reggaeton_rhyming_take1 | FAIL | **REVIEW (minor)** | (a) "every hundred ml" vs "three hundred ml": in the 10-run slice check, **0 of 5 full-mix runs heard "three"** (4 heard "every"; Scribe heard "grams hundred"). 4 of 5 vocal-stem runs heard "three", but the same stem turns "Transport" into "Greenhouse board" / "Air is full of" two seconds later. So "three" is an **isolator artifact**: the song says "every" | 0:26.2-0:26.9 | Quick listen recommended, likely fine |
| | | | (b) "Role?" before "Transport": **0/10** runs heard it. Missing or swallowed; the fact itself is intact | 0:28.0-0:28.4 | Minor REVIEW |
| | | | (c) "in the spleen" sung as "in spleen" (4/4) | 0:33.5 | Minor, acceptable |

**Key finding:** the ElevenLabs voice-isolator stem damaged the 26-30 s region (vocal-stem runs produce words that don't exist; full-mix runs are clean). The kit assumes a demucs stem. With isolator stems, a word heard **only** in vocal-stem runs and never in full-mix runs should be treated as a stem artifact until someone listens.

**Recommendation:** deliver take 2 (cleanest). Take 1 is also usable, apart from the missing "Role?" cue.

## Scorer artifacts (not singing errors)

| Item flagged | Why it's wrong | Suggested kit fix |
|---|---|---|
| FAIL new word "100l" (take 2, 3/4) | Scribe wrote "100L" and the tokenizer only converts pure digits, so "100l" became an unknown word | Split letter+digit tokens (`100L` → `100 l`) before the number conversion |
| REVIEW "point" dropped | "5.5" is tokenized as "5" "5", so "point" is lost | Turn `\d+\.\d+` into "X point Y" before tokenizing |
| REVIEW "life" dropped | Lyric "Life span" is 2 tokens; engines write "Lifespan" as 1 | Add a compound-join pass (lifespan = life span), or write the lyric as "Lifespan" |
| "R-B-Cs" / "M-L" in the lyric sheet | The tokenizer splits hyphenated letters into "r b cs" while engines write "RBCs" | Join single letters separated by hyphens before tokenizing (here worked around by writing RBCs/ml in the scoring sheet) |
| Sarvam onset "None" | Sarvam gives no word timestamps, only chunk starts | Expected; onset comes from Scribe |

## Gaps in this environment

| Kit step | Status here | Gap | Fix |
|---|---|---|---|
| 1. demucs vocal separation | ❌ Replaced | PyTorch CPU wheels (`download.pytorch.org`) and demucs weights (`dl.fbaipublicfiles.com`) are blocked by the network policy | Allow those 2 hosts, or keep using the ElevenLabs voice isolator (about 1,440 credits per 55 s song, which costs more than all the transcription) |
| 2. Scribe x3 (`song_stt.py`) | ✅ Possible as designed | **Correction:** `ELEVENLABS_API_KEY` *is* set in this environment and works for Scribe (tested: HTTP 200). This run used the MCP connector plus `mcp_stt_adapter.py` because a placeholder had overridden the key. From now on `song_stt.py` runs unchanged, with `language_code` and audio-event tags | None |
| 2. Sarvam codemix + verbatim | ✅ Ran as designed | Key was pasted in chat; it's only in a session temp file | Rotate the key and add it as an environment secret |
| 3. Scoring and report | ✅ Ran as designed | Tokenizer artifacts above | Patch tokenize() |
| 4. Slice check (10 runs) | ✅ 10 of 10 runs (re-run) | — | — |
| 5. Listen and decide | ❌ Not possible here | I can't hear audio | A person listens to the clips in `review_clips/` |
| Install check (`example/`, section 10) | ⏳ Not run yet | Possible now with the key; only the demucs step is blocked (use `/v1/audio-isolation` with the key, or allow the 2 demucs hosts) | — |
| Lyric docs | ✅ | — | — |
