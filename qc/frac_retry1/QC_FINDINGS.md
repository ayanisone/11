# QC findings: Fractions retry 1 (8 takes, prompt fixes only)

| Take | Verdict | Notes |
|---|---|---|
| dnb_male_r1 | **PASS** | 100% coverage, all 33 key phrases. 11 s instrumental intro, but no line lost (batch 1 had 22 s and skipped the chorus) |
| afrobeats_female_r1 | **PASS (minor)** | "a" dropped once @1:27. "Three people, four slices" now correct |
| jazz_male_r1 | **PASS (minor)** | "one in four" heard as "one and four" in 2/3 vocal runs @1:40 (sound-alike). The "You too" insertion is gone |
| jazz_female_r1 | **PASS** | Bridge fixed. 'bottom' minority flag @1:12 is a mix-only mishearing (both vocal runs hear "Bottom number") |
| reggaeton_male_r1 | **REVIEW: listen at 0:45** | V2 "Top number?" fixed, but the break has a vocal ad-lib heard as "got it in the corazón" (10/10 slice runs), and the final chorus is slurred ("Fractions, parts fraction of a wholes"). Reggaeton female is a clean PASS |
| funk_female_r1 | FAIL | Final chorus fixed, but V1 drops "An object" (4/4) |
| kpop_female_r1 | FAIL | V1 garbled: "group of objects", "piece of cake", "fractus" missing (0/3) |
| dnb_female_r1 | FAIL | Opening chorus garbled ("Fractions, fractions" missing 3/3, "Top number … denominator" 2/3) |

Retry 2 (prompt fixes): funk F (sing "An object"), K-pop F (lead alone sings V1 slowly, 118 BPM), DnB F (opening chorus slowly and in full), reggaeton M (English only, nobody sings in the breaks).
