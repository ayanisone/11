# Lyric Fact QC: Thermodynamics (energy transformations)

| | |
|---|---|
| Theory | `lyrics/thermo_theory.txt` (1,120 characters → **1:30 / 90 s**) |
| Lyric sheet | `lyrics/thermo_lyrics_90s_v1.txt` (about 277 sung syllables; budget about 221-246 plain, about 280 for rhymed and rhythmic lines) |
| Subject | Chemistry: Thermodynamics, introduction (NCERT Class 11, Unit 5) |
| Automatic checks | `python3 tools/lyric_fact_check.py lyrics/thermo_theory.txt lyrics/thermo_lyrics_90s_v1.txt` |
| **Gate status** | **PASS: waiting for user approval** |

## A. Automatic checks

| Check | Result |
|---|---|
| Numbers | ✅ The only number is "one" ("from one form into another"), and it's in the theory |
| Lyric words outside the theory | ✅ None |
| Theory terms not sung | 🟡 Mostly connecting words (about, can, may, thus, through, during…). Content words left out: *released* (sung as "heat from chemical reactions"), *concerned / based / carried out* (see B8), *properties* (see B11), *containing / involving* (see B9) |

## B. Claim-by-claim check

| # | Lyric line | Claim | Source match | Science check | Result |
|---|---|---|---|---|---|
| B1 | "Thermodynamics! Energy transformations!" | Thermodynamics is about energy transformations | ✅ "study of these energy transformations…thermodynamics" | ✅ | PASS |
| B2 | "Forms of energy, from one form into another!" | Energy can change from one form into another | ✅ | ✅ | PASS |
| B3 | "Chemical energy, stored by molecules" | Molecules store chemical energy | ✅ | ✅ | PASS |
| B4 | "Fuel burns in air? Heat from chemical reactions!" | Burning fuel in air releases chemical energy as heat | ✅ | ✅ (combustion is exothermic) | PASS |
| B5 | "Methane, cooking gas or coal!" | These are examples of fuels | ✅ | ✅ | PASS |
| B6 | "In an engine? Mechanical work!" | Fuel burning in an engine does mechanical work | ✅ | ✅ | PASS |
| B7 | "Galvanic cell, like dry cell? Electrical energy!" | A galvanic cell such as a dry cell turns chemical energy into electrical energy | ✅ | ✅ | PASS |
| B8 | "Forms of energy, interrelated, under certain conditions, transformed!" | Forms of energy are interrelated and can be transformed under certain conditions | ✅ | ✅ | PASS |
| B9 | "Thermodynamics! The study of these transformations!" | Thermodynamics is the study of energy transformations | ✅ | ✅ | PASS |
| B10 | "Not how, not at what rate: initial and final state!" | Thermodynamics isn't concerned with how or how fast; it's based on initial and final states | ✅ ("concerned about" and "based on" shortened; the meaning holds because the line contrasts "not how / not rate" with "initial and final state") | ✅ (state functions; rate is kinetics, not thermodynamics) | PASS (minor) |
| B11 | "Laws deal with energy changes: Macroscopic systems? A large number of molecules! Rather than microscopic? A few molecules!" | The laws apply to macroscopic systems with many molecules, not to microscopic systems with a few molecules | ✅ | ✅ (classical thermodynamics is about bulk systems) | PASS |
| B12 | "Initial, final states: a system undergoing the change!" | It looks at the initial and final states of a system undergoing a change | ✅ | ✅ | PASS |
| B13 | "Laws apply only when a system is in equilibrium, or moves from one equilibrium state to another!" | The laws apply only at equilibrium, or between equilibrium states | ✅ | ✅ (at NCERT level) | PASS |
| B14 | "In equilibrium, pressure and temperature do not change with time!" | At equilibrium, pressure and temperature stay constant over time | ✅ | ✅ | PASS |

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
