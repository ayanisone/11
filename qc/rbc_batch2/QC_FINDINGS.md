# QC findings: RBC reggaeton v3 (fact-fixed lyrics, 55 s), 2026-11-16

Pipeline (full kit, as designed): demucs vocals → Scribe ×3 (mix + 2× vocals) + Sarvam codemix (+ verbatim read-only) → scorer → slice check (10 runs) on the flagged spot.

| Song | Kit verdict | Final | Notes | Action |
|---|---|---|---|---|
| rbc_reggaeton_v3_take1 | REVIEW | **PASS (minor REVIEW)** | Both fact fixes sung, 5/5 runs: "cells **in blood**" and "**Healthy** adult man". 98% coverage, onset 0.2 s. Minor: "man **and** on an average" (extra "and", 5/5); "per cubic millimetre, these" ("are" dropped, 4/4). "Role?" at 29.4 s is sung but blurred: the slice check heard role 2, Global 2, Gold 2, The 2, nothing 2. One short syllable fills the slot, so it isn't a new word | **Deliver** |
| rbc_reggaeton_v3_take2 | FAIL | **FAIL** | About 40 s instrumental intro; only the hook is sung at 40-55 s (10% coverage). A generation failure, not a lyric problem | Discard |
