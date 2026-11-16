# Theory → Song Workflow (length-matched)

## 1. Length rule (client)

Count the theory's characters (with spaces and punctuation). Audio length scales at **40 s per 500 characters** (0.08 s per character), never shorter than 40 s.

| Characters | Audio length |
|---|---|
| up to 500 | 0:40 |
| 500–1000 | 0:40–1:20 |
| 1000–1500 | 1:20–2:00 |
| 1500–2000 | 2:00–2:40 |
| 2000–2500 | 2:40–3:20 |
| 2500–3000 | 3:20–4:00 |
| over 3000 | capped at 4:00; confirm with the client |

Run `python3 tools/theory_budget.py theory.txt`. It prints the character count, the target length, the lyric budget and a suggested section plan.

## 2. Lyric budget (measured on ElevenLabs Music v2.5)

- Melodic genres clearly sing about **3 syllables per second** of vocal time (115–120 syllables in 40 s). Rap carries about 3.8.
- Instrumental breaks and a ~2 s tail are subtracted before budgeting.
- Chorus and hook repeats count toward the budget. Repetition is how a short theory fills a longer song *and* how kids remember it.
- Over budget → the model drops lines. Under budget → it stretches lines or adds long instrumentals. Aim for 90–100% of the budget.

## 3. Lyric rules

1. **Cover every section of the theory.** Every heading or concept gets at least one line, in the theory's order.
2. **Only words from the theory.** No filler, and no rhyme words from outside the theory. Rhymes come from the theory's own vocabulary and line endings.
3. **Hook first.** The song opens on the vocal hook; no instrumental intro.
4. **Catchy, not monotonous:**
   - Call-and-response (lead asks, group answers) on key definitions.
   - The chorus states the core idea and comes back 2–4 times depending on length.
   - Songs over 80 s get a short instrumental break (4–8 s), placed after a chorus.
   - Songs over 80 s get a bridge with a change of feel (half-time, breakdown, or call-and-response).
   - Songs over 120 s get a final chorus with a key lift.
5. **Line shape:** short lines, numbers and symbols written the way they're sung ("one-sixth", "N-A"), no parenthesised instructions inside the lyrics.
6. **Prompt:** "No instrumental intro…", the call-and-response wording, "only the exact lyric words", and "finished by N seconds" (N = length − 2).

## 4. Section plans by length

| Length | Structure |
|---|---|
| 40 s | Hook · Verse 1 · Verse 2 · Chorus · Hook |
| 41–80 s | Hook · V1 · Chorus · V2 · Chorus · Break (~4 s) · Hook |
| 81–120 s | Hook · V1 · Pre-chorus · Chorus · Break (~6 s) · V2 · Chorus · Bridge · Final chorus |
| 121–180 s | Hook · V1 · Pre · Chorus · Break · V2 · Chorus · V3 · Bridge (breakdown) · Break · Final chorus (key lift) |
| 181–240 s | Hook · V1 · Pre · Chorus · Break · V2 · Chorus · V3 · Bridge · Break · V4 · Chorus · Break · Final chorus (key lift) |

## 5. Lyric Fact QC gate (before generation, mandatory)

No song is generated until the lyric sheet passes this gate and the user or client approves it.

1. **Automatic checks:** `python3 tools/lyric_fact_check.py <theory.txt> <lyrics.txt>`
   - **Numbers:** every number in the theory is sung, and no sung number is missing from the theory (a FAIL means a possible wrong fact). Sung forms are parsed: "five point five" = 5.5, "one hundred twenty" = 120.
   - **Theory terms not sung:** coverage gaps to confirm.
   - **Lyric words not in the theory:** the "only theory words" rule. Spoken forms of symbols and units are allowed.
2. **Claim-by-claim review** (reviewer fills `lyrics/<topic>_factcheck.md`, template: `lyrics/rbc_factcheck.md`):
   - every factual claim the lyric makes, matched to the theory sentence it comes from (**source match**);
   - checked against standard subject knowledge for that grade (NCERT and similar) (**science check**). This also catches errors in the theory itself; those go back to the client, never get silently "fixed";
   - dropped qualifiers that change scope ("in blood", "healthy", "in most mammals", "on an average") are REVIEW;
   - question-and-answer lines are checked as pairs (the answer must answer that question);
   - sung form: numbers, units, symbols and formulas written the way they must be sung.
3. **Verdict:** PASS / APPROVED WITH FIXES / FAIL. Any number or claim that contradicts the theory or the science is a FAIL and gets rewritten.
4. **Approval:** the user ticks Approved in the report. Only then is the song generated.

## 6. QA

Use the speech-to-text check on every take, as in `Vocals_Lyrics_STT_QA_Guide.md`. For songs over 80 s, also check that each section starts within ±5 s of the planned time, so no section is silently dropped.
