# QC findings: Motion (universal lyric sheet v1, 112 s), 10 genres x male + female, 2026-11-16

Pipeline: batch 1 (20 takes) → slice checks → retry 1 (4 takes, `qc/motion_retry1`) → retry 2 (3 takes, `qc/motion_retry2`).
Credits: 52,260 (batch) + 10,452 (retry 1) + 7,839 (retry 2) = **70,551**.

## Result: 19 of 20 delivered (`music/motion/`)

| Genre | Male | Female |
|---|---|---|
| Reggaeton | **PASS** (retry 2; 10.8 s intro, all lines) | **PASS** (5 s intro) |
| Afrobeats | **PASS (minor)**: V1 "Motion, motion" sung once | **PASS**: "change in position" elided to "changin' position" (10/10, natural) |
| Bhangra | **PASS** | **PASS** |
| Funk | **PASS** (8.6 s intro) | **PASS** (8.6 s intro) |
| Jazz | **PASS (minor)**: "valid so far as", the "as" is faint | **PASS** (retry 2) |
| A cappella | **PASS** (100% coverage) | ❌ **3 attempts, no pass** (see below) |
| Indie acoustic | **PASS** (4.8 s intro) | **PASS** (8.6 s intro) |
| Pop-punk | **PASS** | **PASS (minor)**: final chorus "Motion, motion" sung once |
| K-pop | **PASS** (7.9 s intro) | **PASS** |
| DnB | **PASS** | **PASS (minor)** (retry 1): first "Motion" clipped at 0 s, a few extra "motion" repeats after the opening chorus; every line complete |

## What failed and how it was fixed

| Take | Attempt 1 | Retry 1 | Retry 2 |
|---|---|---|---|
| Reggaeton male | "local group of galaxies" mangled ("water be deep seas", 10/10) | drops chorus line 2 | ✅ PASS (prompt quoted the full opening chorus) |
| Jazz female | "Earth" missing after the break (0/10) | Verse 1 garbled | ✅ PASS (clear "musical-theatre jazz" diction, horns quieter, "Earth" on the downbeat) |
| A cappella female | "Earth rotates" heard as "Commentates" (10/10) | Verse 2 garbled again | ❌ merges two lines into "Air moves into arteries and veins" (**factually wrong**) |
| DnB female | Opening and "Carry people… planes" garbled ("Harry keep going") | ✅ PASS (minor) | — |

## Lessons
1. **The scorer can miss a merged-line omission.** In a cappella female retry 2 the omission was split into 3 overlapping spans, each under the majority, so the verdict said PASS. Every engine's transcript shows the merge. **Rule: read the full-mix transcript of every PASS take before delivering.**
2. The female a cappella voice keeps losing words at the start of Verse 2 (after the beatbox break) and in fast lists. Next time: ask for **no break** for a cappella, or a male/female duet.
3. Intros of 5-11 s still appear in 7 takes despite the prompt, but no line is lost because of them.
