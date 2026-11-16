# QC findings: Waves v1 (484 syllables, 226 s), 10 genres x male/female, run 2026-11-16

Method: demucs, then Scribe x3 + Sarvam, then the scorer, then `phrase_check.py` (43 key phrases; "metres" now also accepts the US spelling "meters" that the transcribers use), plus a transcript read of every flagged take. QC wall-clock: 34.3 min. 3 renders failed on ElevenLabs' side and were re-run once.

Scorer: 6 PASS, 2 REVIEW, 12 FAIL. After the transcript read: **12 PASS, 2 REVIEW, 6 sent to retry 1.**

## Delivered (`music/waves/`)
| Take | Verdict | Notes |
|---|---|---|
| afrobeats_male | **PASS** | |
| bhangra_male | **PASS** | 100% coverage, vocal at 0.06 s |
| funk_female | **PASS** | |
| jazz_male | **PASS** | 100% coverage |
| acappella_female | **PASS** | |
| indie_male | **PASS** | 100% coverage |
| acappella_male | **PASS (minor)** | "Movement **of** particles": "of" dropped @1:53 |
| indie_female | **PASS (minor)** | Middle chorus drops "An" @1:30 |
| bhangra_female | **PASS (minor)** | Song ends during the final chorus (after "Greater amplitude"), the repeated hook |
| funk_male | **PASS (minor)** | Final chorus sung as "Waves, waves, carry greater energy" x2: the hook is reshuffled at the end. The first two choruses are complete |
| dnb_male | **PASS (minor)** | Opens with a single "Waves" after 5.6 s; "examples, examples" sung once |
| punk_male | **PASS (minor)** | "The speed of a light (wave)? C, C": "wave" dropped (2/3), c intact |
| reggaeton_female | **REVIEW: listen at 3:20** | Before the final chorus she sings "We can get changes in waves" (outside words, 3/3). Everything else is complete |
| afrobeats_female | **REVIEW: listen at 1:45** | Middle chorus: "period, period, frequency, speed. Amplitude. The energy." The line "Greater amplitude carries greater energy" is garbled there (it's complete in the other two choruses) |

## Sent to retry 1
| Take | Problem |
|---|---|
| reggaeton_male | Bridge/V4 lines lost: "periodic changes in magnetic", "adjacent", "frequency, hertz, one wave per second" (4/4) |
| jazz_female | V1 "Amplitude represents the energy, the energy!" becomes gibberish ("vive le vivre, new base spleen") |
| punk_female | Drops the letters: "Period, ~~T~~", "Velocity, ~~v~~" (4/4) |
| kpop_male | **Wrong fact**: "The speed of a light wave? **V**" (3/3), so c is lost |
| kpop_female | **Wrong fact**: "Amplitude represents the energy. It represents **the wavelength**" (2/3); also "for the Y of G" inserted @3:23 |
| dnb_female | 20.7 s intro; opening chorus lines 2-3 skipped |

## Patterns
1. **Single letters are the new weak spot** (T, v, c): dropped or swapped in 3 takes. The retry prompts spell them out ("tee", "vee", "eff", "see").
2. **"the energy, the energy!"** (a repeat at the line end) was garbled in 2 jazz/K-pop takes.
3. End squeeze was mild this time: 2 takes changed the final chorus, none lost a verse at the end.
