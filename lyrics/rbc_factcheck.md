# Lyric Fact QC: Red Blood Cells (Erythrocytes)

| | |
|---|---|
| Theory | `lyrics/rbc_theory.txt` (688 characters → 55 s) |
| Lyric sheet | `lyrics/rbc_lyrics_55s_v2_rhyming.txt` → fixed as `lyrics/rbc_lyrics_55s_v3_factfixed.txt` |
| Subject | Biology: blood, erythrocytes (NCERT Class 11, Body Fluids and Circulation) |
| Automatic checks | `python3 tools/lyric_fact_check.py lyrics/rbc_theory.txt lyrics/rbc_lyrics_55s_v2_rhyming.txt` |
| **Gate status** | **APPROVED WITH FIXES (user, 2026-11-16): both REVIEW fixes applied in v3** |

## A. Automatic checks

| Check | Result |
|---|---|
| Numbers (5, 5.5, 12, 16, 100, 120) | ✅ All 6 numbers in the theory are sung, and no number in the lyrics is missing from the theory |
| Lyric words outside the theory | ✅ None (only spoken forms: "per cubic millimetre", "ml", "grams", "point") |
| Theory terms not sung | 🟡 healthy, individual, molecules, play, significant: see B2 and B8 |

## B. Claim-by-claim check

Each claim the song makes, compared with the theory (**source match**) and with standard science (**science check**).

| # | Lyric line | Claim | Source match | Science check | Result |
|---|---|---|---|---|---|
| B1 | "Erythrocytes! Red blood cells!" | Erythrocytes are red blood cells | ✅ | ✅ | PASS |
| B2 | "Most abundant of all the cells!" | RBCs are the most abundant cells | ⚠️ Theory says "of all the cells **in blood**" and the lyric drops "in blood" | ✅ true in blood (they are also the most numerous cells in the body, but the theory's claim is about blood) | **REVIEW**: suggest "Most abundant of all the cells in blood!" |
| B3 | "Adult man, on an average, has five to five point five millions of RBCs, per cubic millimetre" | 5–5.5 million RBCs per mm³ of blood in an adult man | ⚠️ Theory says "**healthy** adult man" and "of blood" | ✅ 5–5.5 million/mm³ is the standard adult-male value | **REVIEW**: suggest "Healthy adult man, on an average, has…" |
| B4 | "Formed in? The red bone marrow!" | RBCs are formed in red bone marrow | ✅ ("in the adults" left out) | ✅ in adults (before birth, also the liver and spleen) | PASS (minor) |
| B5 | "Nucleus? Devoid, in most mammals!" | RBCs have no nucleus in most mammals | ✅ | ✅ | PASS |
| B6 | "Biconcave in shape!" | RBCs are biconcave | ✅ | ✅ | PASS |
| B7 | "Haemoglobin! Iron containing complex protein! Red coloured, hence the colour, hence the name!" | Haemoglobin is a red, iron-containing complex protein, and gives the cells their colour and name | ✅ | ✅ | PASS |
| B8 | "Haemoglobin grams? In every hundred ml, twelve to sixteen!" | 12–16 g haemoglobin per 100 ml of blood | ✅ numbers exact ("healthy individual" and "of blood" left out) | ✅ 12–16 g/dL is the standard value | PASS (minor) |
| B9 | "Role? Transport of respiratory gases!" | Haemoglobin's role is transporting respiratory gases | ✅ ("these molecules play a significant role" shortened) | ✅ O₂ and CO₂ transport | PASS |
| B10 | "Life span? One hundred twenty days!" | Average RBC life span is 120 days | ✅ | ✅ | PASS |
| B11 | "Destroyed in the spleen! Graveyard of R-B-Cs!" | RBCs are destroyed in the spleen, the "graveyard of RBCs" | ✅ | ✅ (the liver also helps; the theory names the spleen) | PASS |

## C. Sung-form check (how facts sound when sung)

| Item | Written | Sung as | Result |
|---|---|---|---|
| 5.5 | five point five | "five point five" | ✅ |
| mm⁻³ | per cubic millimetre | "per cubic millimetre" | ✅ |
| 100 ml | hundred M-L | "hundred M-L" | ✅ |
| 120 | one hundred twenty | "one hundred twenty" | ✅ |
| RBC | R-B-C | letter by letter | ✅ |

## D. Verdict

- **Factual errors:** none. Every number and every claim matches the theory and standard science.
- **2 qualifiers dropped (REVIEW):** B2 "in blood" and B3 "healthy". Both make the claim slightly broader than the theory. Recommended fix (+3 syllables, fits the 55 s budget):
  - Hook: "Most abundant of all the cells **in blood**!"
  - Verse 1: "**Healthy** adult man, on an average, has…"
- **Status:** ☐ Approved as is ☑ **Approved with fixes** ☐ Rejected. Fixes applied in v3 (B2: "in blood", B3: "Healthy"); re-check found no FAIL, 173 syllables.
