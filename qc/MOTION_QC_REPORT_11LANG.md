# Motion ("गति / Motion") – final QC report, 11 languages
Date: 2026-11-24 · Model: ElevenLabs Music v2.5 · Marathi (12th language) is in progress, see the end.

## How every take was checked
1. Lyrics written only from the theory text, then fact-checked against it.
2. Each take: vocals separated, transcribed 3× by ElevenLabs Scribe + Sarvam, scored against the lyric, key-phrase list per language.
3. Every suspect line re-checked with 10-engine slice transcriptions; the full transcript of every PASS take read by hand.
4. Up to 2 prompt-only retries per failed take. Meaning flips (dropped "not", wrong number, wrong word) are always failures.

**PASS** = every line correct. **REVIEW** = usable, one small slip at the time given – worth one listen.

## Summary

| # | Language | Folder | Genres | Files | QC: PASS | QC: REVIEW | Not delivered | Credits |
|---|---|---|---|---|---|---|---|---|
| 1 | English | `music/motion/` | 10 | 19 | 19 | 0 | 1 | 70,551 |
| 2 | Hindi | `music/motion_hi/` | 5 | 10 | 5 | 5 | 0 | 37,095 |
| 3 | Bengali | `music/motion_bn/` | 4 | 8 | 7 | 1 | 0 | 31,033 |
| 4a | Tamil (68 s set) | `music/motion_ta/` | 4 | 7 | 4 | 3 | 1 | 20,631 |
| 4b | Tamil (121 s set) | `music/motion_ta_v2/` | 3 | 6 | 4 | 2 → approved | 0 | 33,876 |
| 5 | Gujarati | `music/motion_gu/` | 4 | 8 | 5 | 3 → approved | 0 | 32,340 |
| 6 | Punjabi | `music/motion_pa/` | 4 | 8 | 6 | 1 + 1 held → approved | 0 | 30,240 |
| 7 | Odia | `music/motion_or/` | 3 | 6 | 5 | 1 → approved | 0 | 22,630 |
| 8 | Assamese | `music/motion_as/` | 3 | 6 | 5 | 1 → approved | 0 | 20,367 |
| 9 | Telugu | `music/motion_te/` | 3 | 6 | 5 | 1 → approved | 0 | 27,975 |
| 10 | Kannada | `music/motion_kn/` | 3 | 6 | 2 | 4 → approved | 0 | 32,484 |
| 11 | Malayalam | `music/motion_ml/` | 3 | 6 | 4 | 2 → approved | 0 | 24,780 |
| | **Total** | | **49** | **96** | **71** | **24 (+1 held, now approved)** | **2** | **≈384,000** |

"→ approved": the user approved these REVIEW takes on 2026-11-23; the files are named `_PASS`. For Hindi, Bengali and the 68 s Tamil set the REVIEW takes still carry `_REVIEW` in the file name.

## Not delivered
- **English – a cappella female:** 3 attempts; the last merged two lines into "Air moves into arteries and veins" (factually wrong). The male a cappella take is PASS.
- **Tamil 68 s – EDM male:** 3 attempts, each failing in a different place ("நீர்" → "நீ", made-up words). The 121 s Tamil set covers Tamil fully.

## Listen-check spots (REVIEW takes)

| Language | Take | Listen at | What you'll hear |
|---|---|---|---|
| Hindi | Bollywood F | 1:22 | "आकार तय" sung like "वस्तु-कार ते" |
| Hindi | Hip-hop F | 0:32 | "पेड़ों से" sounds like "टेढ़ों सा" |
| Hindi | Lo-fi M | 0:31 | "धमनियों" sounds like "धम्मियों"; 9 s intro |
| Hindi | Lo-fi F | 1:04 | "गैलेक्सी" slightly short |
| Hindi | Bhajan-EDM F | 0:02 | opening "समय के साथ" blurred (final chorus clear) |
| Bengali | Rabindra M | 1:30 | file ends after the first line of the final chorus |
| Tamil 68 s | Gaana F | 0:53 | "ஆய்வுக்கு கவனம்" unclear |
| Tamil 68 s | Carnatic F | 0:31 | "அனைத்தும்" blurred |
| Tamil 68 s | EDM F | 0:24 | "காற்று கூட" blurred; 7 s intro |
| Tamil 121 s | Kollywood F | 1:41 | small "நிலை-இலை" stutter |
| Tamil 121 s | Rock F | 0:00 | opening "இயக்கம்!" not sung |
| Gujarati | Bhajan M | 1:10 | tiny "સા-સાપેક્ષ" stutter |
| Gujarati | Garba M | 0:32 | "ધમનીઓ તથા" sung soft |
| Gujarati | Garba F | 1:01 | galaxy line a bit mushy |
| Punjabi | Hip-hop F | 0:08 | first chorus garbles "ਤਬਦੀਲੀ" (final chorus fine) |
| Punjabi | Hip-hop M | – | was held back (loses "ਵੇਗ ਅਤੇ ਤਵਰਣ" or a verse line); delivered on user approval |
| Odia | Cinematic pop M | 0:00 | opening "ଗତି!" not sung |
| Assamese | Indie F | 0:39 | "চুৱিশ" (24) sung a bit short |
| Telugu | Folk M | 0:05 | both choruses skip the opening shout "చలనం!" |
| Kannada | Sandalwood M | 0:08 | small "ಚಲನೆ, ಚಲನೆಯ" repeat |
| Kannada | Folk M | 0:09 | first chorus skips "ವೇಗ" (final chorus has it) |
| Kannada | Indie rock M | 0:08 | first chorus skips "ವೇಗ" (final chorus has it) |
| Kannada | Indie rock F | 1:37 | "ವೇ-ವೇ-ವೇಗೋತ್ಕರ್ಷ" stutter |
| Malayalam | R&B F | 1:48 | three extra "ത്വരണം" after the final chorus |
| Malayalam | Folk M | 0:35 | "വായു" (air) skipped once |

None of these changes a fact. Every meaning-flip found during QC (dropped "not" in Gujarati/Malayalam, "air goes into arteries" in English, "water" → "you" in Tamil) was fixed by a retry or kept out of delivery.

## What we learned
- **Dense lyrics cost retries.** Kannada (longest lyric, 116 s) failed on every first take; one retry with "every line is sung once and in full; never merge, shorten or skip a line" fixed all six. That sentence is now in every prompt.
- **Negations need protecting.** "નથી / ਨਹੀਂ / വരില്ല / होत नाही" get dropped and flip the meaning; the prompt now names the last bridge line and spells out "meaning it does NOT happen".
- **Describe how a word sounds, not how it's spelled** (Bengali "তোরোন" for ত্বরণ fixed three takes).
- **Fast styles are the weak spot:** EDM, hip-hop and a cappella needed the most retries in every language; folk and cinematic were cleanest.
- **The automatic scorer is a first pass only.** Spelling variants (numbers as digits, English loanwords) trigger false fails, and merged lines can slip through, so every take is also read by hand.

## In progress: Marathi (12th language)
Lyrics approved; 3 genres (Lavani folk pop, Marathi cinematic soul, Marathi hip-hop) × male + female.
Lavani male: **PASS**, every line correct first try. The other five timed out on the ElevenLabs server and were re-run once (07:54 UTC); QC follows. Credits so far: 11 × 2,520 = 27,720 (if the timed-out renders were charged).
