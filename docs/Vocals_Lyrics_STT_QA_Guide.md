# Vocals & Lyrics: How They Are Created, and How to QA Them with Speech-to-Text

**Purpose.** We check every AI-generated song (ElevenLabs Music `eleven_music_v2_5`) with speech-to-text (ElevenLabs Scribe `eleven_scribe_v1`) to catch **lyric hallucinations**: the song singing content that is not in our lyric sheet, or dropping content that is.

A sung vocal is not a read-aloud script. Real songs, and AI songs trained on them, carry ad-libs, filler vocables, repeats, harmonies and stutters that are **part of the performance, not errors**. This document:

1. Explains how the vocal relates to the lyric sheet, and where extra or missing words come from.
2. Defines a **taxonomy** that separates *contextual vocal material* (allowed) from *true hallucinations* (fail).
3. Gives **rules for scoring an STT transcript** so ad-libs, fillers and harmonies are not counted as hallucinations.
4. Gives **prompt and lyric-writing rules** that reduce unwanted additions at generation time.
5. Lists **real examples from our own runs** (Newton's Laws and Pythagoras projects).

> Scope note: everything below about how the music model behaves is **observed behaviour from our generations**, not documented ElevenLabs internals. Treat it as working knowledge to be updated as we test more.

---

## 1. How the vocal is produced from the lyric sheet

### 1.1 What we send

Each song is one generation with:

| Input | What it controls |
|---|---|
| **Style prompt** (1–3 sentences) | Genre, tempo, instruments, vocal type, delivery (sung / rapped), energy |
| **Custom lyrics** (`lyrics_type: custom`) | The words to be performed, split into sections with tags like `[Verse 1]`, `[Chorus]` |
| **Duration** (`duration_seconds`) | Target length. The model sometimes overrides it: we have seen 40 s requests come back at 48 s, 50 s and 58 s when the lyrics did not fit. |

### 1.2 What the model does with the lyric sheet

The lyric sheet is treated as a **guide for the performance, not a teleprompter**. In our runs the model:

- **Sets lyrics to a melody and rhythm.** To make words fit the bar, it may stretch syllables, repeat words, or add short pickup words.
- **Uses section tags as structure.** Tags (`[Verse]`, `[Chorus]`, `[Hook]`) are not sung. They shape arrangement: verse vs. chorus energy, repeats, builds.
- **Adds genre-typical vocal material** that is not in the sheet: "yeah", "oh", "hey", "whoa", breaths, count-ins, echo repeats of the last word, crowd-style chants, harmonies stacked on a lyric line. Rap adds hype ad-libs; Bollywood adds held vowels and ornaments (melisma); rock adds shouts.
- **May treat text in parentheses as a backing vocal or ad-lib layer.** This follows the common lyric-sheet convention where `(ooh)` means a backing vocal. A note like `(instrumental, no vocals)` inside the lyrics is therefore risky; put such instructions in the style prompt instead.
- **Drops content it cannot fit.** When the lyric sheet is too dense for the duration and delivery style, the model skips lines rather than rushing them. This is the most damaging failure we saw (see §5).
- **Occasionally rewrites a phrase.** It may swap or insert words to make a line singable ("Every action **has** an equal…"). These are the cases QA must catch.

### 1.3 Density is the main control

| Lyric density (40 s song) | Delivery | Result in our tests |
|---|---|---|
| ~85 syllables (Pythagoras) | Sung (pop/rock/Bollywood) | Lyrics sung, minor rushing on the longest line |
| ~115 syllables (Newton, short version) | Sung pop | Every line sung; two small glitches (one repeat, one inflection change) |
| ~165 syllables (Newton, full version) | Rapped | Every line sung, word for word, in 2 of 3 takes |
| ~165 syllables | Sung pop / Bollywood | Verses dropped; often only the chorus sung, or no detectable vocal |

**Rule of thumb:** for melodic genres keep a 40 s song at **≤ ~115 sung syllables**, with short lines (≤ ~12 syllables). Dense, textbook-style lines only survive in rap delivery.

---

## 2. Taxonomy: contextual vocal material vs. hallucination

Every word in the STT transcript that does not match the lyric sheet one-to-one falls into one of these classes.

### 2.1 ALLOWED: contextual vocal material (never a hallucination)

| Class | What it is | Typical STT appearance | Example |
|---|---|---|---|
| **Vocables / non-lexical fillers** | Sung sounds with no meaning | `oh`, `ooh`, `ah`, `yeah`, `hey`, `whoa`, `uh`, `mm`, `na na`, `la la`, `ho` | "yeah, F equals m a" |
| **Hype ad-libs** (rap/pop) | Short exclamations between lines | `yeah`, `let's go`, `come on`, `uh-huh`, `okay` | "let's go! Second law…" |
| **Echo / repeat of a lyric word or phrase** | The last word or line repeated for effect | Duplicated lyric words | "reaction, reaction" |
| **Hook repetition** | Chorus or hook sung more times than written | Extra copies of chorus lines | "Action, reaction!" ×3 |
| **Stutter / restart** | A phrase starts, cuts, restarts | Partial lyric fragment then the full line | "Of class… of classical mechanics" |
| **Harmonies / doubles / backing vocals** | Extra voices singing the **same lyric words** | Same words, sometimes duplicated or merged by STT | Chorus line transcribed twice |
| **Call-and-response** | A backing voice answers a lead line with lyric words | Lyric words out of order or overlapping | Lead: "For every action" / Backing: "reaction!" |
| **Melisma / held vowels** | One syllable stretched over many notes | Word broken up or repeated ("re-e-est", "rest rest") | Bollywood ornaments |
| **Count-ins, breaths, shouts** | "one, two", inhales, shouts | Numbers or nothing | "one, two, three, four" before a rock verse |
| **Pure orthographic variation** | Same words, different spelling or format from STT | `MA` / `ma` / `m a`, `F=ma`, `two` / `2`, punctuation | "F equals MA" = lyric "F equals m a" |

**Shared property:** these add **no new meaning**. Each one is a lyric word, a vocable, or a performance sound.

### 2.2 REVIEW: borderline, flag for a human listen

| Class | Example from our runs | Why it is borderline |
|---|---|---|
| **Function word inserted** | "Every action **has** an equal and opposite reaction" | Meaning unchanged, but the line no longer matches the client's text |
| **Inflection change** | "remains" → "remain" | Could be the singer or an STT mishearing |
| **Word order shuffle inside a line** | "remains at rest" → "remain to rest" | Usually melodic, sometimes meaning-shifting |
| **Short phrase with outside words in an intro or outro** | "'Cause it's all law of motion" | Ad-lib-like position, but it contains words that are not lyric words or vocables |

### 2.3 FAIL: true hallucination

| Class | Example from our runs | Why it fails |
|---|---|---|
| **New content words** (not in the lyric sheet, not a vocable) | "a **body** at rest **stays** at inertia" | Invents a line and changes the wording of the law |
| **Changed technical term, number or formula** | "F is force, **the force and its mass and its** acceleration" | Garbles F = ma, the core fact |
| **Meaning change** | "an object **in uniform movement will remain** uniform velocity" | Paraphrase that alters the physics statement |
| **Garbled / unintelligible substitution** | "Force on **love** accelerate" | Not the lyric, and wrong |
| **Omission of a required line** | Bollywood takes that sang only the chorus | The song does not teach the verses at all |
| **Missing vocal** | Several pop takes: STT returned an empty transcript | Either no vocal, or a vocal STT cannot hear; must be checked (§3.5) |

---

## 3. Scoring rules for STT transcripts

### 3.1 Inputs

- `LYRICS`: the lyric sheet as sent, **with section tags removed**.
- `TRANSCRIPT`: Scribe output text plus **word-level timestamps**.
- `VOCABLES`: allow-list of non-lexical and ad-lib tokens (starter list in §3.6).
- `PROTECTED`: technical terms, numbers and formulas that must appear exactly. For Newton's laws, for example: `inertia, acceleration, momentum, force, mass, magnitude, direction, action, reaction, equal, opposite, F, m, a, three, two`.

### 3.2 Normalize both texts the same way

1. Lowercase; strip punctuation, quotes and hyphens.
2. Expand symbols: `=` → `equals`; `F=ma` / `ma` / `MA` → `f equals m a` (split single-letter variables).
3. Numbers to words (`3` → `three`).
4. Collapse elongations (`re-e-est` → `rest`, `ooooh` → `ooh`).
5. Map contractions consistently (`'cause` → `because`), and keep both forms in the allow-list decisions.

### 3.3 Remove contextual material before comparing

1. **Delete tokens in `VOCABLES`.**
2. **Collapse immediate repeats** (`reaction reaction` → `reaction`; repeated whole lines → one copy).
3. **Collapse stutter-restarts.** If a fragment is a prefix of the line that follows within ~2 s, drop the fragment (`of class of classical mechanics` → `of classical mechanics`).
4. **Collapse extra chorus or hook copies.** Keep one aligned instance per written instance; extra copies are allowed.

### 3.4 Align and classify

Align the cleaned transcript to `LYRICS` with a word-level edit-distance alignment, as used for WER. Then:

| Diff type | Rule |
|---|---|
| **Insertion** of a token that is **in the lyric vocabulary** | ALLOWED (repetition / harmony / call-and-response) |
| **Insertion** of a function word (`has, the, a, and, it, is, of, to, will`) | REVIEW |
| **Insertion** of any other word | **FAIL** (hallucinated content) |
| **Substitution** touching a `PROTECTED` term | **FAIL** |
| **Substitution** that is an inflection of the same word (`remain/remains`) | REVIEW |
| **Substitution**, other | **FAIL** |
| **Deletion** of a `PROTECTED` term, or of ≥ 3 consecutive lyric words | **FAIL** (omission) |
| **Deletion** of a single non-protected word | REVIEW |

**Report per take:**

- **Lyric coverage** = aligned lyric words ÷ total lyric words. Target **≥ 95 %**.
- **Hallucination count** = number of FAIL items. Target **0**.
- **Review list**, with timestamps, for a human to listen to.
- **Vocal onset** = timestamp of the first lyric word. Flag if > 6 s; long instrumental intros were a sign of dropped verses.

### 3.5 Known STT limits on music (do not blame the song for these)

- **Empty transcript ≠ no vocals.** On several takes Scribe returned empty text with the same fixed `language_probability` (0.1245). Treat that as **"STT could not transcribe"**, not "no vocals". Re-check with **vocal isolation** first: run the ElevenLabs voice isolator / `audio_isolation` on the song, then transcribe the isolated vocal, then confirm by ear.
- **Harmonies and doubles** can be merged into one line or transcribed twice.
- **Melisma and held notes** get split or misheard.
- **Heavy mixes** (distorted rock guitars, loud synths) lower STT accuracy. Mishearings like "remain to rest" can be STT errors, not singer errors.
- **STT can hallucinate too.** Treat any FAIL item as a **candidate** until it is confirmed by listening at its timestamp.
- **Audio-event tags.** If the STT outputs tags such as `(laughter)` or `(music)`, strip them before scoring.

### 3.6 Starter `VOCABLES` allow-list

```
oh ooh ah aah uh uhh mm mmm hmm yeah yeh yea ya yo hey ho whoa woah wow
na la da di do ba bam ay ayy eh huh uh-huh okay ok alright
come on let's go here we go check it one two three four
```
Extend per language: Hindi/Bollywood (`haan, arre, aaja, o re, ho ho`); Tamil/Telugu (`ra, re, o`); and so on. Keep **number words** on this list only for count-ins **outside** lyric lines, because numbers inside a line can be protected terms (e.g. "three, four and five" in the Pythagoras song).

---

## 4. Generation-side rules (prevent problems before STT)

### 4.1 Style prompt

- State the delivery explicitly: *"sings only the given lyrics, no ad-libs, no backing vocals singing extra words"* when strict fidelity matters.
- If ad-libs are wanted for genre feel, say *"light ad-libs using only 'yeah' and 'oh'"*, so any ad-lib lands on the allow-list.
- Ask for an early vocal entry: *"vocals start after a 2-second intro and continue to the end"*.
- For dense educational text, ask for **rapped or half-rapped verses** with a sung chorus.

### 4.2 Lyric sheet

- **No instructions inside the lyrics.** Never write `(instrumental, no vocals)` or similar in the lyric field; put it in the prompt.
- **Parentheses = backing vocals.** Only use `( … )` for backing-vocal words you actually want sung. Those words then count as part of `LYRICS` for scoring.
- **Write the ad-libs you accept into the sheet** if you want them scored as expected, e.g. `Action, reaction! (yeah)`.
- **Keep lines short** (≤ ~12 syllables) and the total under the density limits in §1.3.
- **Spell out symbols** the way they should be sung: `F equals m a`, not `F = ma`.
- **Put the must-remember line in the chorus.** Chorus lines were the most reliably sung lines in every failing take.
- **Open the lyric sheet with a `[Hook]` section, and say "No instrumental intro: the song opens directly with the vocal hook" in the prompt.** Without this, the model often plays a 20–28 s instrumental intro (ignoring "2-second intro"), runs out of time and drops the second verse, or stretches the song to 58 s. With the hook at the top, every take in our elements test came back at exactly 40 s with vocals starting in the first 0–8 s.

### 4.3 Process

1. Write the lyrics, verify the stored node shows the exact lyric text, then generate **1–2 test takes** first.
2. Run STT and score with §3 before generating the full set.
3. Only takes with **coverage ≥ 95 % and 0 confirmed FAIL items** go to the client.

---

## 5. Evidence log from our runs

| Song / take | Lyric density | Result (from Scribe) | Classification |
|---|---|---|---|
| Newton full, rap take 1 | ~165 syl, rapped | Every line, word for word | PASS |
| Newton full, rap take 3 | ~165 syl, rapped | Every line; dropped "a is" once | REVIEW (minor omission) |
| Newton full, rap take 2 | ~165 syl, rapped | Cut off before the last chorus lines | FAIL (omission) |
| Newton full, rock take 2 | ~165 syl, sung | Most lines; "Every action **has**…", "in uniform movement will remain…", garbled F = ma line | FAIL (protected term + meaning change) |
| Newton full, rock take 1 | ~165 syl, sung | "Force on love accelerate" etc. | FAIL (garbled) |
| Newton full, pop takes | ~165 syl, sung | Empty transcript | Unconfirmed: needs isolation check |
| Newton full, Bollywood take 1 | ~130 syl, sung | Chorus only, starting at 0:24 | FAIL (omission) |
| Newton full, Bollywood rap-verse test | ~165 syl, hybrid | Almost all lines, but "a body at rest stays at inertia" inserted; 50 s long | FAIL (new content words), duration over limit |
| **Newton short, pop take 2** | **~115 syl, sung** | Every line; "remain, remain to rest"; extra "a is acceleration" fragment | **PASS with REVIEW items** (stutter-restart = allowed; inflection = review) |

| Elements 1–20, round 1 (verse first), 8 takes | ~119 syl | Intros of 20–28 s; 3 takes stretched to 58 s; most dropped elements 11–20 or Calcium; 2 empty transcripts | 1 near-pass in 8 |
| Elements 1–20, round 2 (`[Hook]` first, "no instrumental intro"), 8 takes | ~119 syl | All 40 s; vocals start 0–8 s; 5 of 8 sang all 20 name + symbol pairs | 5 PASS / REVIEW, 3 FAIL |
| Probability catchy (call-and-response, hook bookend), 8 takes: stomp-clap pop, stadium rock, party rap, Bollywood dance | ~120 syl | All 40 s; vocals start 0–7 s; Q&A lines and closing hook sung in 7 of 8; rock t1 skipped "Rolling a four"; rap t2 dropped "Science, statistics" and inserted "Markets"; Bollywood t2 cut off on the last hook | 6 PASS / REVIEW, 2 FAIL |
| Probability catchy, romantic Bollywood duet (male asks, female answers), 2 takes | ~120 syl | Both 40 s, vocals start at 0.6 s; t2 sang every line; t1 skipped "Even number" and has a garbled "and a side, its side" | 1 PASS, 1 FAIL |
| Genre test (Probability call-and-response, 1 take each): Bhangra, Sufi, Garba, Kuthu, Rajasthani folk, EDM, Reggaeton, Afrobeats, Country, Broadway | ~120 syl | PASS: Reggaeton (vocal at 0.3 s), EDM (0.5 s, hook sung twice plus a "Hey!" ad-lib), Bhangra (0.9 s), Afrobeats (0.2 s, "favorable" echoed and "by" dropped), Garba (4 s), Sufi (5 s), Kuthu (8 s intro). FAIL: Rajasthani folk (no words detected in first 16 s), Country (13 s intro, die verse missing, "Equal chances" inserted, lines doubled), Broadway ("certain" dropped, which changes the meaning; final hook cut off by slow theatrical phrasing) | 7 PASS / REVIEW, 3 FAIL |
| Genre test: Jazz swing (140 BPM, "tight on-the-beat phrasing, no scat, no long held notes"), 2 takes | ~120 syl | t2: vocal at 0 s, every line sung, and the group audibly echoes the answers ("Impossible, impossible", "Certain, certain"); t1: 7.5 s intro, every line sung, "three-sixths" echoed | 2 PASS (echo repeats allowed) |
| Genre test: Funk (112 BPM) and Disco (120 BPM), tight-phrasing prompt, 2 takes each | ~120 syl | Funk t1: vocal at 4 s, every line sung word for word, PASS. Funk t2: verse 2 garbled ("Even rolling a four, one six"), so "three-sixths, one-half" was lost, FAIL. Disco t1: vocals stop at 33 s, so the chorus and final hook are missing, FAIL. Disco t2: the backing group adds new words ("Fifty-fifty" twice, "Impossible now") and drops "Science", FAIL | Funk 1/2 PASS, Disco 0/2 |

**Takeaways**

1. Most "hallucinations" in our runs were really **omissions caused by over-dense lyrics**, not invented words.
2. Real new-content hallucinations appeared mostly when the model was **forced to compress** too much text (rock and hybrid takes).
3. Short, rhyming, chorus-led lyrics produced clean takes. The remaining differences were stutters and inflections, which this guide classifies as contextual or review, not as hallucinations.

---

## 6. One-paragraph position statement (for sharing)

> In AI-generated songs, the vocal is a musical performance of the lyric sheet, not a word-for-word reading. Vocables ("oh", "yeah"), echo repeats, extra hook repetitions, stutter-restarts, harmonies and call-and-response lines are standard parts of a sung vocal; they add no new meaning and should not be scored as hallucinations. When we check songs with speech-to-text, we first normalise both texts, remove allow-listed vocables, and collapse repeats and restarts. We then count as hallucinations only: (a) inserted content words that appear neither in the lyrics nor on the vocable list, (b) any change to protected technical terms, numbers or formulas, (c) changes in meaning, and (d) omitted lyric lines. An empty or garbled transcript is treated as an STT limitation until confirmed on an isolated vocal stem and by ear.
