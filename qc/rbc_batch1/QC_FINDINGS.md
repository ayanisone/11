# QC findings: RBC reggaeton (rhyming lyrics, 55 s), run 2026-11-16

Method: vocals separated with the **ElevenLabs voice isolator** (demucs could not run here, see "Gaps" below). Each song was transcribed 4 times: ElevenLabs Scribe v1 on the full mix, Scribe v1 twice on the vocal stem, and Sarvam Saaras v4 `codemix` on the vocal stem. Sarvam `verbatim` was run once more as a read-only reference. Transcripts were scored with the kit's `song_qc_score.py`, and the doubtful spots were re-checked with `slice_check.py`, using Sarvam engines only (6 of the kit's 10 runs).

## Verdicts after review

| Song | Scorer verdict | Final | Issue | Time | Action |
|---|---|---|---|---|---|
| rbc_reggaeton_rhyming_take2 | FAIL | **PASS (minor REVIEW)** | Sings "on average" instead of "on an average" (4/4 runs). The scorer's FAIL "100l" and its REVIEW "point" and "life" items are scoring artifacts (see below) | 0:09 | Deliver |
| rbc_reggaeton_rhyming_take1 | FAIL | **REVIEW: needs a listen** | (a) "every hundred ml" vs "three hundred ml". The slice check split 4 "every" to 5 "three": full-mix runs lean "every", vocal-stem runs lean "three". This changes the fact (100 ml vs 300 ml) | 0:26.2-0:26.9 | Listen to `review_clips/…25.0-28.3s_mix.mp3`. If "three": regenerate |
| | | | (b) "Role?" before "Transport" is weak or missing: only 1 of 10 runs heard it, though there's a 0.40 s gap where it would sit | 0:28.0-0:28.4 | Listen. The fact itself ("transport of respiratory gases") is intact |
| | | | (c) "in the spleen" sung as "in spleen" (4/4) | 0:33.5 | Minor, acceptable |

**Recommendation:** deliver take 2. Keep take 1 only if a listen confirms "every hundred".

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
| 2. Scribe x3 (`song_stt.py`) | ⚠️ Done another way | No `ELEVENLABS_API_KEY`; api.elevenlabs.io is reachable but returns 401. The runs went through the ElevenLabs MCP connector, which has **no `language_code` or `tag_audio_events` option** (it auto-detects language), plus `mcp_stt_adapter.py` | Provide an ElevenLabs API key with speech-to-text access to run the kit unchanged |
| 2. Sarvam codemix + verbatim | ✅ Ran as designed | Key was pasted in chat; it's only in a session temp file | Rotate the key and add it as an environment secret |
| 3. Scoring and report | ✅ Ran as designed | Tokenizer artifacts above | Patch tokenize() |
| 4. Slice check (10 runs) | ⚠️ 6 of 10 runs | The 4 Scribe runs need the API key (401). The MCP connector can't transcribe a local clip: there is no upload tool for local files | API key, or an MCP upload tool |
| 5. Listen and decide | ❌ Not possible here | I can't hear audio | A person listens to the clips in `review_clips/` |
| Install check (`example/`, section 10) | ❌ Not run | The example songs are local files: no upload path to the connector, and no API key | Run with an API key, or on a machine with the full setup |
| Lyric docs | ✅ | — | — |
