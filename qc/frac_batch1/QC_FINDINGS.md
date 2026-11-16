# QC findings: Fractions v1 (386 syllables, 182 s), 10 genres x male/female, run 2026-11-16

Method: demucs, then Scribe x3 + Sarvam, then the majority-vote scorer, then `phrase_check.py` (33 key phrases) and a transcript read of every flagged take, plus a slice check at 107-111.5 s (punk female). QC wall-clock: 29.4 min.

Scorer: 6 PASS, 5 REVIEW, 9 FAIL. After the transcript read: **11 deliverable PASS, 1 REVIEW, 8 sent to retry 1.**

## Delivered (`music/frac/`)

| Take | Verdict | Notes |
|---|---|---|
| afrobeats_male | **PASS** | All lines |
| bhangra_male | **PASS** | All lines |
| bhangra_female | **PASS** | 100% coverage |
| indie_male | **PASS** | 100% coverage |
| kpop_male | **PASS** | All lines |
| funk_male | **PASS (minor)** | "the"→"a" @2:36, sound-alike |
| acappella_male | **PASS (minor)** | A vocal fill ("are the whole, doo doo") in the 5 s break after the Bridge, @2:03. No lyric changed |
| acappella_female | **PASS (minor)** | "one **in** four" heard as "one and four" in 3/4 runs @1:38, sound-alike |
| indie_female | **PASS (minor)** | V4 "the sections **of** the fraction" sung "the section, the fraction" @2:38 |
| punk_male | **PASS (minor)** | "In" dropped from "In ancient times" @0:31 |
| reggaeton_female | **PASS (minor)** | Middle chorus drops "Top number?" @1:28 (it's in the first chorus and V2), and the song ends during the final chorus (the repeated hook is cut off) |
| punk_female | **REVIEW: listen at 1:49** | "X over four" heard as "X for four" / "extra four" in 10/10 slice runs. Probably a slurred "x-o'-four", but a person should check it, because "x for four" would teach the wrong thing. punk_male is a clean alternative |

## Sent to retry 1 (fact lost or changed)

| Take | Problem |
|---|---|
| reggaeton_male | V2 drops "Top number?" (4/4) @1:13, so "Selected or shaded parts of a whole" loses its subject |
| afrobeats_female | "Three people, four slices" sung "Three equal, four slices"; chorus drops "Bottom number?"; V4 drops "the total parts" |
| funk_female | Final chorus mostly missing (4/4) |
| jazz_male | Inserts "You too" after "one over two" @2:13 (4/4); V4 drops "bottom" @2:26 |
| jazz_female | "Three people, four slices" garbled into "Three equal fourths" (wrong maths) |
| kpop_female | V4 drops "Numerator?" @2:39 (4/4); final chorus cut |
| dnb_male | 22 s instrumental intro, opening chorus skipped, middle chorus replaced with garbled V2 lines |
| dnb_female | V2 drops "Two over four?" @1:06 (4/4). No intro this time (vocal at 0.06 s) |

## Patterns

1. **End squeeze is back on the 182 s sheet**: 4 takes lose part or all of the final chorus. The retry prompts say "final chorus sung in full, ending by 178 s".
2. **Question tags get dropped** ("Top number?", "Two over four?", "Numerator?"): the call-and-response short question is the weak spot, as "Heat!" was in thermodynamics.
3. **"Three people, four slices!" is the riskiest line**: 2 of 20 takes turned it into "three equal …". It's an unexplained example (theory note 2 in the fact check), and the model fills the gap with words.
4. DnB male again added a 22 s intro; DnB female did not.
