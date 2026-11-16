# Lyric Fact QC: Trigonometry (introduction)

| | |
|---|---|
| Theory | `lyrics/trig_theory.txt` (2,059 characters → **2:45 / 165 s**) |
| Lyric sheet | `lyrics/trig_lyrics_165s_v1.txt` (universal sheet for all 10 genres) |
| Subject | Mathematics: Introduction to Trigonometry (Class 10/11 level) |
| Budget | **370 sung syllables**, 2.42 syllables/s over 153 s of vocal time (universal budget 344-382) |
| Structure | Chorus · V1 · break · V2 · Chorus · V3 · Bridge · break · V4 · Final chorus (all unique facts before the final chorus) |
| **Gate status** | **PASS with 2 notes for the client: waiting for user approval** |

## A. Automatic checks

| Check | Result |
|---|---|
| Numbers | ✅ 0, 30, 45, 60, 90 (degrees), "two" sub-branches, "three" functions: all match the theory. (A checker bug that read "thirty, forty-five" as one number was fixed today) |
| Lyric words outside the theory | ✅ None. Symbols sung as words: "f of minus x equals minus f of x" |
| Theory terms not sung | 🟡 Framing words only (basically, consider, let us see, evaluated, mentioned, calculations…) |

## A2. Rhyme map

| Section | End rhymes | Rhymes inside the lines |
|---|---|---|
| Chorus | **tri**an**gle** / **tan** (same "an" vowel) | angles / triangle / tangent / tan; "trigonometry, trigonometry" |
| Verse 1 | **fields** / identi**ties** | **sides** / **find, find**; "formulas, functions" |
| Verse 2 | de**grees** / trigonome**try** | "**two** sub-branches / **two** different types"; plane / spherical |
| Verse 3 | **functions** / **functions** | "hypotenuse, hypotenuse"; "adjacent and opposite" |
| Bridge | f of **x** / f of **x** | "**odd** function / **even** function"; "symmetric / symmetric" |
| Verse 4 | tri**angle** / **angle** | "all the ratios, all the values" |

## B. Claim-by-claim check

| # | Lyric | Claim | Source | Science | Result |
|---|---|---|---|---|---|
| B1 | "Sides and angles of the right-angle triangle! Sine, cosine, tangent! Sin, cos, tan!" | Trigonometry is about the sides and angles of a right triangle; sin, cos, tan abbreviations | ✅ | ✅ | PASS |
| B2 | "One of the most important branches in mathematics, huge application in diverse fields!" | Importance and applications | ✅ | ✅ | PASS |
| B3 | "The study of the relationship between sides and angles" | Definition | ✅ | ✅ | PASS |
| B4 | "Missing, unknown angles or sides? Find, find! Using formulas, functions or trigonometric identities!" | Used to find unknown sides or angles | ✅ | ✅ | PASS |
| B5 | "Angles measured in either degrees or radians" | Units | ✅ | ✅ | PASS |
| B6 | "Commonly used? Zero, thirty, forty-five, sixty, ninety degrees!" | Standard angles | ✅ ("commonly used" kept) | ✅ | PASS |
| B7 | "Two sub-branches? Plane and spherical, two different types of trigonometry!" | Two types | ✅ | ✅ | PASS |
| B8 | "Trigonometric ratios, also called trigonometric functions; sine, cosine and tangent, three important functions!" | Ratios = functions; three main ones | ✅ | ✅ | PASS |
| B9 | "Right-angled triangle: the longest side? Hypotenuse, hypotenuse!" | Hypotenuse is the longest side | ✅ | ✅ | PASS |
| B10 | "The sides referred to as the adjacent and opposite sides!" | Names of the other two sides | ✅ (see note 1) | ✅ | PASS |
| B11 | "Odd function? F of minus x equals minus f of x, symmetric with respect to the origin!" | Odd function definition | ✅ | ✅ | PASS |
| B12 | "Even function? F of minus x equals f of x, symmetric to the y-axis!" | Even function definition | ✅ | ✅ | PASS |
| B13 | "Sine, cosine, tangent of these angles? Easy to memorize! The table: all the ratios, all the values!" | Standard-angle ratios are easy to memorize; a table lists them | ✅ | ✅ | PASS |
| B14 | "Draw a right-angled triangle, one of the acute angles, the corresponding angle!" | Method for finding the ratios | ✅ | ✅ (see note 2) | PASS |

## C. Notes for the client (errors in the theory itself; not "fixed" silently)

1. **Theory sentence:** "the sides **opposite to the hypotenuse** are referred to as the adjacent and opposite sides". This is wrong as written: no side is opposite the hypotenuse. The other two sides are called adjacent and opposite **relative to the chosen acute angle**. The lyric avoids the error by singing only "the sides referred to as the adjacent and opposite sides". The client should correct the theory text.
2. **Theory sentence:** "one of the acute angles will be the corresponding trigonometry angle" (for 0°, 30°, 45°, 60°, 90°). This works for 30°, 45° and 60°. 0° and 90° can't be acute angles of a real triangle; textbooks get them as limiting cases. The lyric repeats the theory, which is fine at this level; flagging only.

## D. Sung forms
| Written | Sung as |
|---|---|
| f(−x) = −f(x) | "F of minus x equals minus f of x" |
| f(−x) = f(x) | "F of minus x equals f of x" |
| 0°, 30°, 45°, 60°, 90° | "Zero, thirty, forty-five, sixty, ninety degrees" |
| sin, cos, tan | "Sin, cos, tan" |
| y-axis | "y-axis" |

## E. Verdict
- **Factual errors in the lyric:** none. **2 notes on the theory text** go to the client (C1 matters, C2 is minor).
- **Every section is covered:** importance, definition, finding unknowns, degrees/radians, standard angles, plane/spherical, ratios = functions, sin/cos/tan, hypotenuse/adjacent/opposite, odd/even with symmetry, memorizing the table, the right-triangle method.
- **Status:** ☐ Approved as is ☐ Approved with fixes ☐ Rejected.
