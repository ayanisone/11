# QC findings: Trigonometry (universal lyric sheet v1, 165 s), 10 genres x male + female, 2026-11-16

Pipeline: batch 1 (20) → retry 1 (7, `qc/trig_retry1`) → retry 2 (3, `qc/trig_retry2`). Every delivered take was also checked with `tools/phrase_check.py` (29 key phrases).
Credits: 77,000 + 26,950 + 11,550 = **115,500**.

## Result: 17 PASS + 2 DnB REVIEW + 1 held back

| Genre | Male | Female |
|---|---|---|
| Reggaeton | PASS (10 s intro) | PASS (10 s intro) |
| Afrobeats | PASS (minor: one extra "Symmetric to the y-axis" before the final chorus; one "trigonometry" dropped in the final chorus; 9 s intro) | PASS |
| Bhangra | PASS (retry 1) | PASS (minor: "f" in "f of minus x" faint) |
| Funk | PASS | PASS (minor: "Hypotenuse" sung once) |
| Jazz | PASS (retry 1) | PASS |
| A cappella | ❌ 3 attempts, held back | PASS (retry 1) |
| Indie | PASS (9 s intro) | PASS |
| Pop-punk | PASS (minor: "Let's table" for "The table"; "let" is a theory word) | PASS |
| K-pop | PASS (minor: final chorus opens on one "Trigonometry") | PASS (retry 1) |
| DnB | **REVIEW**: all 3 attempts open with a 22 s instrumental and skip the opening chorus; every fact is still sung, and the chorus is sung twice later. An intro-trimmed edit is provided | **REVIEW**: same |

## Failures and fixes
| Take | Attempt 1 | Retry 1 | Retry 2 |
|---|---|---|---|
| Bhangra male | dropped "Trigonometric ratios" (the ratio = function fact lost its subject) | ✅ | |
| Jazz male | added "Pi, unit circle" (outside words) and garbled "formulas…identities" | ✅ | |
| A cappella female | "trigonometric identities" garbled | ✅ | |
| K-pop female | 23 s intro, opening chorus skipped | ✅ | |
| A cappella male | "identities" garbled | "unknown angles" → "un-angles, angles", "Ooh" ad-lib | ❌ **factually wrong**: "even function… symmetric to the line through origin" |
| DnB male / female | 22 s intro, opening chorus skipped | same (22-25 s) | same (22.1 s), even with a "vocal over pads first, then the drop" prompt |

## Lessons
1. **"Trigonometric identities"** (a long, unfamiliar phrase at the end of a line) was garbled in 4 of 20 first takes. Prompting it by name fixed it in 3 of 4. In future sheets, avoid ending a fast line on a 7+ syllable technical phrase, or give it its own line.
2. **DnB at 165 s always builds a 22 s intro**, every time, whatever the prompt; at 90-112 s it didn't. For long DnB songs, plan to trim the intro in post, or start the lyric sheet with a short sung tag the model can place over the build.
3. The phrase check caught the merged and garbled lines; the scorer alone passed two of them.
