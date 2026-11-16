# QC findings: Thermodynamics v3 UNIVERSAL lyrics (217 syllables, 90 s), 10 genres x 2 takes, run 2026-11-16

Method: same kit as batch 1 (demucs, Scribe x3 + Sarvam, majority vote), then 8 slice checks (10 engine runs each).
Wall-clock: generation ~3 min, full QC 13.7 min, slice checks ~8 min.

**Compared with v2 (batch 1): scorer PASS went from 2/22 to 9/20, and 9 of 10 genres now have a usable take (7 PASS, 2 REVIEW).**
Every take came back 89-94 s (v2: 6 takes ran to 100 s).

## Delivered (`music/thermo_v3/`)

| Genre | Take | Verdict | Notes |
|---|---|---|---|
| Reggaeton | t1 | **PASS** | All lines. Vocal starts at 5.0 s (short intro) |
| Afrobeats | t1 | **PASS** | All lines. **9.4 s instrumental intro** despite the prompt. T2 starts at 0 s but sings "**Laws**" as "That's/God's/Cars" (10/10) and blurs "certain" (6/10 "set/second"), so not delivered |
| Bhangra | t1 | **PASS (minor)** | Final chorus sung "study of **this transformation**" (10/10) instead of "these transformations". Meaning intact. Vocal at 0.9 s |
| Jazz swing | t1 | **PASS** | All lines, vocal at 0.3 s. The v2 extra "equilibrium" repeat is gone |
| A cappella | t2 | **PASS** | All lines, vocal at 1.1 s |
| Indie acoustic | t1 | **PASS** | 100% coverage on every run, vocal at 1.1 s. (v2: both takes skipped the hook) |
| Pop-punk | t1 | **PASS** | All lines; slice check at 62-66 s clean 10/10. Vocal at 0.2 s |
| DnB | t1 | **REVIEW** | Bridge 1:07-1:13: "or" dropped and "equilibrium to equilibrium" blurred ("Move, state to state. Equilibrium. In equilibrium"). Rest clean, vocal at 0.1 s |
| Funk | t1 | **REVIEW: listen at 0:28** | All 5 vocal-stem runs hear "cooking gas" as a **profanity** ("f***ing gas"); all 5 full-mix runs hear "cooking". Must be checked by ear before it goes to kids. Also an 8.9 s intro. T2 garbles "under certain conditions" (10/10 "sketchy circumstances") |
| K-pop | none | FAIL | Both takes drop "**Heat!**" in Verse 1 (t2 slice check: 0/10 runs hear it), so the fact "fuel burns in air → heat" is lost. T1 also inserts "ends" |

## Patterns

1. The shorter sheet fixed the end squeeze: no take lost "Do not change with time" (v2: 9 takes did).
2. Intros still happen in 3 takes (5-9 s) but the hook is no longer skipped, so no fact is lost.
3. K-pop drops the short one-word answer "Heat!": a fast call-and-response gap. A fix would be "Fuel burns in air? Heat, heat!" or merging it into the line.
4. New lesson: check every "cooking" in fast or slurred genres for a profanity-like sound (funk t1).
