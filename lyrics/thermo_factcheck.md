# Lyric Fact QC: Thermodynamics (energy transformations)

| | |
|---|---|
| Theory | `lyrics/thermo_theory.txt` (1,120 characters → **1:30 / 90 s**) |
| Lyric sheet | **`lyrics/thermo_lyrics_90s_v2_rhyming.txt`** (v2: rewritten for full end rhymes and rhymes inside the lines; about 281 sung syllables; v1 kept for reference) |
| Subject | Chemistry: Thermodynamics, introduction (NCERT Class 11, Unit 5) |
| Automatic checks | `python3 tools/lyric_fact_check.py lyrics/thermo_theory.txt lyrics/thermo_lyrics_90s_v1.txt` |
| **Gate status** | **PASS: waiting for user approval** |

## A. Automatic checks

| Check | Result |
|---|---|
| Numbers | ✅ The only number is "one" ("from one form into another"), and it's in the theory |
| Lyric words outside the theory | ✅ None |
| Theory terms not sung | 🟡 Mostly connecting words (about, can, may, thus, through, during…). Content words left out: *released* (sung as "heat from chemical reactions"), *concerned / based / carried out* (see B8), *properties* (see B11), *containing / involving* (see B9) |

## A2. Rhyme map (v2)

| Section | End rhymes | Rhymes inside the lines |
|---|---|---|
| Hook | transforma**tions** / condi**tions** | **form** / trans**form** |
| Verse 1 | mole**cules** / **fuel**; chem**ical** / mechan**ical** / electr**ical** | "**Fuel burns** in air / **Fuel burns** in an engine"; "l**i**ke dr**y** cell" |
| Pre-chorus | trans**formed** / **form** | **forms** / **form** / an**other form** |
| Chorus | r**ate** / st**ate** | "not how / not at what rate"; "initial state, final state" |
| Verse 2 | ch**anges** / ch**ange**; mole**cules** / mole**cules** | **macro**scopic / **micro**scopic |
| Bridge | equilib**rium** / equilib**rium** / equilib**rium** | pres**sure** / tempera**ture**; "state to state, equilibrium to equilibrium" |

## B. Claim-by-claim check (lines updated for v2; claims unchanged)

| # | Lyric line | Claim | Source match | Science check | Result |
|---|---|---|---|---|---|
| B1 | "Thermodynamics! Energy transformations!" | Thermodynamics is about energy transformations | ✅ "study of these energy transformations…thermodynamics" | ✅ | PASS |
| B2 | "Forms of energy, from one form into another!" | Energy can change from one form into another | ✅ | ✅ | PASS |
| B3 | "Chemical energy, stored by molecules" | Molecules store chemical energy | ✅ | ✅ | PASS |
| B4 | "Fuel burns in air? Heat! Reactions, chemical!" | Burning fuel in air releases chemical energy as heat | ✅ | ✅ (combustion is exothermic) | PASS |
| B5 | "Methane, cooking gas or coal: fuel!" | These are examples of fuels | ✅ | ✅ | PASS |
| B6 | "Fuel burns in an engine? Work, mechanical!" | Fuel burning in an engine does mechanical work | ✅ | ✅ | PASS |
| B7 | "Galvanic cell, like dry cell? Energy, electrical!" | A galvanic cell such as a dry cell turns chemical energy into electrical energy | ✅ | ✅ | PASS |
| B8 | "Forms of energy, interrelated, transformed, from one form into another form!" + hook "under certain conditions" | Forms of energy are interrelated and can be transformed under certain conditions | ✅ | ✅ | PASS |
| B9 | "Thermodynamics! The study of these transformations!" | Thermodynamics is the study of energy transformations | ✅ | ✅ | PASS |
| B10 | "Not how, not at what rate, based on initial state, final state!" | Thermodynamics isn't concerned with how or how fast; it's based on initial and final states | ✅ ("concerned about" and "based on" shortened; the meaning holds because the line contrasts "not how / not rate" with "initial and final state") | ✅ (state functions; rate is kinetics, not thermodynamics) | PASS (minor) |
| B11 | "Laws deal with energy changes: Macroscopic systems? A large number of molecules! Rather than microscopic? A few molecules!" | The laws apply to macroscopic systems with many molecules, not to microscopic systems with a few molecules | ✅ | ✅ (classical thermodynamics is about bulk systems) | PASS |
| B12 | "Laws deal with energy changes of a system undergoing the change!" | It looks at the initial and final states of a system undergoing a change | ✅ | ✅ | PASS |
| B13 | "Laws apply only when a system is in equilibrium, or moves, state to state, equilibrium to equilibrium!" | The laws apply only at equilibrium, or between equilibrium states | ✅ | ✅ (at NCERT level) | PASS |
| B14 | "Pressure, temperature, in equilibrium: do not change with time!" | At equilibrium, pressure and temperature stay constant over time | ✅ | ✅ | PASS |

### Fixed while writing (caught by this gate)

| Draft line | Problem | Fix |
|---|---|---|
| "Pressure and temperature do not change with time!" | **Wrong on its own**: P and T change in general, and only stay constant **at equilibrium** | "**In equilibrium**, pressure and temperature do not change with time!" |
| "Laws apply only in equilibrium state, or moves from one…" | The subject is missing, so it reads as if the *laws* move | "Laws apply only when **a system** is in equilibrium, or moves from one equilibrium state to another!" |
| "A system undergoing the change!" | A fragment with no claim | "**Initial, final states**: a system undergoing the change!" |

## C. Sung-form check

| Item | Sung as | Result |
|---|---|---|
| Thermodynamics | ther-mo-dy-NA-mics | ✅ |
| Equilibrium | e-qui-LI-bri-um | ✅ |
| Macroscopic / microscopic | Sung as a pair, so the contrast is heard | ✅ |
| Galvanic | gal-VA-nic | ✅ |

## D. Verdict

- **Factual errors:** none (3 were caught and fixed in drafting).
- **Every section of the theory is covered:** forms of energy, examples (heat, work, electricity), interrelation and transformation, the definition, macroscopic vs microscopic, state-based and not rate-based, equilibrium, and P/T constant at equilibrium.
- **Status:** ☐ Approved as is ☐ Approved with fixes ☐ Rejected. **Generation waits until one box is ticked.**

---

# v3 UNIVERSAL (one sheet for all genres): `lyrics/thermo_lyrics_90s_v3_universal.txt`

Why: in the v2 batch (`qc/thermo_batch1/QC_FINDINGS.md`) 7 of 11 genres failed both takes, mostly by dropping
bridge or final-chorus words in the last 12 s (281 syllables in 90 s, ~3.4/s) or by adding an intro and skipping the hook.
v3 is cut to **217 syllables** (−23%), ~2.6 syllables/s of vocal time with a 4 s break: room for the slower genres.

| Check | Result |
|---|---|
| Automatic: numbers | ✅ "one" only, in the theory |
| Automatic: lyric words outside the theory | ✅ None |
| Structure | Opens on the chorus (hook-first); all unique facts end before the final chorus, so a squeezed ending only loses a repeat |

## Rhyme map (v3)

| Section | End rhymes | Rhymes inside the lines |
|---|---|---|
| Chorus | r**ate** / st**ate** | "not how / not at what rate"; "initial state, final state" |
| Verse 1 | mole**cules** / **fuel**; chem**ical** / mechan**ical** / electr**ical**; condi**tions** / transforma**tions** | "**Fuel burns** … **Fuel**"; "l**i**ke dr**y** cell"; "one **form** … **forms**" |
| Verse 2 | **macro**scopic / **micro**scopic; mole**cules** / mole**cules** | "a large number / a few" contrast |
| Bridge | equilib**rium** ×3 | pres**sure** / tempera**ture**; "state to state, equilibrium to equilibrium" |

## Claim changes vs v2 (all other claims B1–B14 unchanged)

| # | v3 line | Change | Result |
|---|---|---|---|
| B2/B8 | "Interrelated forms, under certain conditions, from one form into another: transformations!" | Hook and pre-chorus merged into Verse 1. Keeps "interrelated", the qualifier "under certain conditions" and "one form into another" | PASS |
| B6 | "In an engine? Work, mechanical!" | Subject "Fuel burns" carried over from the line before ("Fuel burns in air?") | PASS |
| B11 | "Laws deal with energy changes: macroscopic, a large number of molecules, rather than microscopic: a few molecules!" | Merged; claim unchanged | PASS |
| B12 | (removed) "of a system undergoing the change" | The chorus still says "based on initial state, final state"; "a system" is still sung in the bridge | PASS (minor: phrase dropped, meaning held) |
| — | Middle chorus removed | Chorus is now sung 2× (start and end) instead of 3× | No fact lost |

**Gate status (v3): APPROVED (user, 2026-11-16).** ☑ Approved as is ☐ Approved with fixes ☐ Rejected.
