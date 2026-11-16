# QC findings: Thermodynamics (v2 rhyming lyrics, 90 s), 11 genres x 2 takes, run 2026-11-16

Method: kit as designed. demucs htdemucs vocal stems, then ElevenLabs Scribe x3 (mix + 2 vocal runs) and Sarvam codemix/verbatim, then `song_qc_score.py` majority vote. Doubtful spots re-checked with `slice_check.py` (10 engine runs each). Wall-clock: generation 2.5 min, demucs 13 min, STT + scoring 3.5 min, slice checks ~5 min.

## Result: 3 PASS, 1 REVIEW, 7 genres with no passing take

| Genre | Delivered take | Final verdict | Notes |
|---|---|---|---|
| Afrobeats | take 1 (90 s) | **PASS** | Every line sung, in order. Slice check at 10.5-15.5 s: Scribe 4/4 "methane, cooking gas or coal"; Sarvam's "medicine / that's a cold" is a Sarvam mishearing |
| K-pop | take 2 (90 s) | **PASS** | Every line sung, all 3 choruses complete (the earlier K-pop test dropped a chorus line; this one doesn't). Sarvam hears "nothing" for "methane" 5/5, Scribe hears "methane" 4/4: engine artifact |
| Jazz swing | take 1 (90 s) | **PASS (minor)** | Bridge sings "state to state, equilibrium, **equilibrium** to equilibrium" (one extra repeat of a lyric word, 10/10 runs). No outside word, the fact is intact. "in equilibrium" heard as "and equilibrium" in 5/10: sound-alike |
| Funk | take 1 (90 s) | **REVIEW: listen at 0:15.4** | "cooking gas" is unclear: 2/10 runs hear "liquid gas", 4/10 "could be gas", 2/10 "cooking gas". Likely a slurred "cookin'", but a person must confirm. Rest of the song is complete. Take 2 drops the end of the final chorus |
| Reggaeton | none | FAIL | T1 (100 s): drops "Pressure, temperature, in equilibrium" (4/4), so the B14 fact loses its subject. T2: drops "work" and a chorus, inserts "where" |
| Bhangra | none | FAIL | T1: 12 s instrumental intro, hook garbled. T2: drops "in equilibrium, do not change with time" and the song is cut off mid-final-chorus at 90 s |
| Disco | none | FAIL | T1: drops "Macroscopic?" (4/4) and "Not how, not at what rate" in the final chorus. T2: 10 s intro, chorus dropped |
| A cappella | none | FAIL | T1: sings "do not change with ~~time~~ Thermodynamics" ("time" dropped 10/10 in slice check), so the B14 fact breaks. T2: first chorus replaced by repeated verse fragments plus "Whoa" ad-libs |
| Indie acoustic | none | FAIL | Both takes: 8.5-10.7 s instrumental intro and the **hook is skipped** (4/4). The hook carries "under certain conditions", which is sung nowhere else |
| Pop-punk | none | FAIL | T2: drops "Do not change with time" (4/4). T1: drops "heat", "chemical" and parts of the first chorus |
| DnB | none | FAIL | T1 (100 s): 16.6 s intro, hook skipped. T2: many bridge lines dropped |

## Patterns (feed into the next prompts)

1. **The squeeze is at 78-90 s.** 9 of the failures lose bridge or final-chorus words: "Do not change with time", "Pressure, temperature" or the last chorus. At about 281 sung syllables in 90 s (~3.4 syl/s with the 6 s break) the song is over budget, and the model compresses the end.
2. **Ignoring "no instrumental intro"**: bhangra t1, disco t2, indie t1+t2 and DnB t1 open with 8-17 s of music, and then skip or garble the hook to catch up.
3. **Requested 90 s, got 100 s** on 6 takes. The extra length did not help: 5 of those 6 still fail.
4. Sarvam consistently mishears "methane" ("medicine", "nothing"). Scribe gets it right. Not a song error.

## Fix options for the 7 failed genres

- **A. Regenerate at 100 s** (outside the length rule by +10 s). This gives the bridge room; ~2,330 credits per take.
- **B. Keep 90 s, drop the instrumental break** (6 s back to vocals). Stays within the rule.
- **C. Keep 90 s, cut one chorus repeat** (~25 syllables, ~8 s). This changes the approved lyric sheet, so it needs a Fact-QC re-check (no facts are lost because the chorus is repeated).
