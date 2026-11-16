# Song Lyric QC: Full Workflow

How to check AI-generated songs (ElevenLabs Music) for **lyric hallucinations**: words the song sings that are not in the lyric sheet, lyric words it leaves out, and words it changes. Ad-libs, "oh/yeah" fillers, repeats, harmonies and stutters are allowed and do not count.

This kit holds everything needed to run the check on any computer:

```
song_lyric_qc_kit/
├── WORKFLOW.md                     ← this file
├── Vocals_Lyrics_STT_QA_Guide.md   ← the rules (what counts as allowed / review / fail)
├── run_all.sh                      ← one command: steps 1-3 + lyric documents
├── requirements.txt                ← Python packages
├── .env.example                    ← copy to .env and add the two API keys
├── scripts/
│   ├── common.py                   ← shared helpers (keys, songs.csv, numbers)
│   ├── song_stt.py                 ← step 2: transcribe (4 scored runs + 1 read-only)
│   ├── song_qc_score.py            ← step 3: score + build the report
│   ├── slice_check.py              ← step 4: re-check one flagged spot
│   └── make_lyric_docs.py          ← optional: one Word lyrics doc per song
├── templates/
│   ├── songs.csv                   ← project config template
│   └── lyrics_template.txt         ← lyric sheet template
└── example/                        ← 4 test songs + lyrics, to prove a new install works
    ├── songs.csv
    ├── input/*.mp3
    └── lyrics/*.txt
```

---

## 1. Quick start

On a computer that is already set up (section 2):

```bash
cd song_lyric_qc_kit
./run_all.sh example
```

Then open `example/song_qc_summary.md` and `example/song_qc_report.xlsx`. For a real job, make a project folder (section 3) and run `./run_all.sh <project_folder>`.

Time for 4 songs of 35-40 s: about 20 s for vocal separation and about 30 s for transcription.

---

## 2. One-time setup on a new computer

### 2.1 Install the tools

| Tool | Mac | Windows |
|---|---|---|
| Python 3.11 or newer | `brew install python` | python.org installer, tick "Add to PATH" |
| ffmpeg | `brew install ffmpeg` | `winget install ffmpeg`, then reopen the terminal |

Check both:

```bash
python3 --version
ffmpeg -version
```

### 2.2 Create the Python environment (inside the kit folder)

Mac / Linux:

```bash
cd song_lyric_qc_kit
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd song_lyric_qc_kit
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

This installs PyTorch, so it takes a few minutes and about 1 GB of disk space.

### 2.3 Add the API keys

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
ELEVENLABS_API_KEY=...   # ElevenLabs account → Profile → API keys (needs speech-to-text access)
SARVAM_API_KEY=...       # dashboard.sarvam.ai → API keys
```

Keys can also be set as shell environment variables instead; those win over `.env`. Never share or commit `.env`.

### 2.4 Prove the install works

```bash
./run_all.sh example
```

The first run downloads the demucs model (about 80 MB) once. Compare your `example/song_qc_summary.md` with **section 10**. If the verdicts match, the setup is correct.

**Windows:** `run_all.sh` needs Git Bash or WSL. Otherwise run the steps one by one (section 4) with `.venv\Scripts\python` in place of `.venv/bin/python`.

---

## 3. Setting up a project

A project is a folder with this layout. Create it anywhere; the kit doesn't care where.

```
kitkat_batch1/
├── songs.csv
├── input/          ← the songs (mp3, wav or m4a)
└── lyrics/         ← one .txt lyric sheet per lyric (songs can share one)
```

### 3.1 `songs.csv`: one row per song file

Copy `templates/songs.csv` and fill it in. Excel can edit it; save as CSV UTF-8.

| Column | Meaning | Example |
|---|---|---|
| `song_file` | File name inside `input/` | `pythagoras_rap_hindi_v2-5_take2.mp3` |
| `lyrics_file` | Lyric sheet path, relative to the project folder | `lyrics/pythagoras_hindi.txt` |
| `title` | Song title, used in the Word doc | `Pythagoras Theorem` |
| `language` | Language code for Scribe | `hi`, `en`, `ta`, `te`, `kn`, `ml`, `mr`, `bn`, `gu`, `pa` |
| `style` | Genre, for the record | `Rap` |
| `model` | Music model, for the record (optional) | `ElevenLabs Music v2.5` |

Several takes of the same song all point to the same `lyrics_file`.

**Language:** use the main language of the lyrics. For Hinglish (Hindi with English words), use `hi`; Scribe then writes Hindi words in Devanagari and English words in Latin letters, which the scorer handles.

### 3.2 The lyric sheet (`lyrics/*.txt`)

Paste the lyrics **exactly as they were sent to the music model**, then add one `# protected:` line.

```
# Client lyric sheet, received 2026-11-12
# protected: hypotenuse a b c square plus equal three four five nine sixteen twenty pythagoras theorem
[Verse]
Right angle triangle में, सबसे लंबी side
Hypotenuse कहलाती, right angle के opposite side
[Chorus]
a square plus b square equals c square
```

Rules the scorer follows:

- Lines starting with `#` are notes and are not scored.
- `[Section]` tags are not scored.
- Text in `( )` is not scored, e.g. `(instrumental, no vocals)`. If you **want** a backing-vocal line scored, write it without brackets.
- **Protected words** are words that must be sung exactly: brand names, product names, numbers, formulas and technical terms. If one is missing or changed, the result is FAIL, not REVIEW. For KitKat, put the brand name, product name, tagline words and any numbers here.
- Write numbers either way ("25" or "twenty-five"); both are turned into words before comparing.
- Write Hindi in Devanagari or in Latin letters; both are compared by sound.

---

## 4. Running it

### Option A: everything at once

```bash
./run_all.sh kitkat_batch1
```

To redo transcription for songs already done, add `--force`: `./run_all.sh kitkat_batch1 --force`. Transcripts are cached in `stt/`, so re-running the scoring after a lyric fix costs nothing.

### Option B: step by step

```bash
P=kitkat_batch1

# Step 1 — separate vocals from music (local, free)
.venv/bin/python -m demucs --two-stems=vocals -n htdemucs -o $P/stems $P/input/*.mp3

# Step 2 — transcribe each song (4 scored runs + 1 read-only; paid API calls)
.venv/bin/python scripts/song_stt.py $P
.venv/bin/python scripts/song_stt.py $P --only pythagoras_rap_hindi_v2-5_take2 --force   # redo one song

# Step 3 — score against the lyrics and build the report (free, instant)
.venv/bin/python scripts/song_qc_score.py $P

# Step 4 — re-check any flagged spot (see section 6)
.venv/bin/python scripts/slice_check.py $P pythagoras_rap_hindi_v2-5_take2 28.0 31.6

# Optional — Word lyric documents per song
.venv/bin/python scripts/make_lyric_docs.py $P
```

### What you get

```
kitkat_batch1/
├── stems/htdemucs/<song>/vocals.wav      ← vocals only
├── stems/htdemucs/<song>/no_vocals.wav   ← music only
├── stt/<song>.json                       ← all 5 transcripts, with word timestamps from Scribe
├── song_qc_summary.md                    ← one verdict per song
├── song_qc_report.xlsx                   ← full report (section 5)
├── song_qc_report.json                   ← same data, machine-readable
├── review_clips/                         ← clips cut by slice_check.py + slice_checks.json
└── lyric_docs/<song> - lyrics.docx       ← one lyric document per song
```

---

## 5. How it works, step by step

### Step 1: separate the vocals (demucs)

**What:** demucs (Meta's open-source model `htdemucs`, run locally) splits each song into `vocals.wav` and `no_vocals.wav`.

**Why:** speech-to-text mishears sung words under loud guitars, drums and synths, and those mistakes look like hallucinations. In the Newton song the full mix came back as "remain, remain to rest". The vocals-only file came back as "remains at rest", which is what was actually sung. Always score the vocal stem.

ElevenLabs' own voice isolator (`audio-isolation` API) would also work. demucs is used because it is free, local and fast.

### Step 2: transcribe each song (4 scored runs + 1 read-only)

| Run | Engine | Audio | Scored? | Why |
|---|---|---|---|---|
| `scribe_mix` | ElevenLabs Scribe v1 | Full song | Yes | Baseline; shows how much the music hurts accuracy |
| `scribe_vocals_1` | Scribe v1 | Vocal stem | Yes | Main run; gives a timestamp for every word |
| `scribe_vocals_2` | Scribe v1 | Vocal stem | Yes | Scribe can give a different answer on the same audio, so a second run shows which words it's unsure of |
| `sarvam_vocals` | Sarvam Saaras v4, mode `codemix` | Vocal stem | Yes | A different company's model as an independent second opinion; strong on Indian languages |
| `sarvam_verbatim_vocals` | Sarvam Saaras v4, mode `verbatim` | Vocal stem | No, read it | Doesn't tidy up, so it catches extra short words the others hide. It writes English in Devanagari ("स्क्वेयर"), which is why it isn't scored. It's in the **Transcripts** sheet |

Scribe settings: `language_code` from `songs.csv`, word timestamps on, audio-event tags on (`[music]` etc. are removed before scoring).

**Sarvam modes matter.** Saaras v4 has several output modes, and they were tested on these songs:

| Mode | English words come out as | Tidies up? | Use |
|---|---|---|---|
| default (`transcribe`) | Changes between runs: sometimes "square", sometimes "स्क्वायर" | Yes | Don't use; it gave 72-85% false coverage on one run |
| `codemix` | "square" (Latin), same every run | Yes, it drops an extra "स्थित" | Scored run |
| `verbatim` | "स्क्वेयर" (Devanagari) | **No**: it kept "सिट" | Read-only run, and in the slice check |

Sarvam's synchronous calls take about 30 s of audio at most, so the vocal stem is cut at the quietest 0.3 s point between 12 s and 25 s, and each piece is transcribed separately. Sarvam gives no word timestamps, only the start time of each piece.

### Step 3: score against the lyrics

Each of the 4 transcripts is scored on its own, following the guide's section 3.

**3a. Clean up both texts the same way**
- lowercase, remove punctuation, and remove the Hindi full stop "।"
- `25` → `twenty five`, `A²` → `a square`, `=` → `equals`, `+` → `plus`, `ma` → `m a`
- `equals` = `equal`, `squared` = `square`, `aur`/`और` = `or`
- Devanagari is converted to Latin letters and simplified to how it sounds, so `कहलाती` = `kehlati` and `बाकी` = `baaki`

**3b. Remove the allowed filler words**: oh, ooh, ah, yeah, hey, whoa, uh, mm, na, la, huh, okay, haan, arre and so on (full list: `VOCABLES` in `song_qc_score.py`).

**3c. Line up the transcript with the lyrics word by word.** Two words count as the same if they sound at least 65% alike. Words of 1-2 letters must match exactly.

**3d. Sort every difference:**

| Difference | Class |
|---|---|
| An extra word that is a lyric word (repeat, echo, harmony, extra chorus) | ALLOWED |
| An extra word that is the start of the next lyric word (stutter-restart, "class… classical") | ALLOWED |
| An extra filler word (has, the, a, and, of, के, का…) | REVIEW |
| An extra word that is not in the lyrics | **FAIL** (new word) |
| A protected word changed to something that sounds different | **FAIL** |
| A protected word changed to something that sounds similar | REVIEW |
| A non-protected word changed to a sound-alike (remain/remains) | REVIEW |
| A non-protected word changed to something unrelated | **FAIL** |
| A protected word missing, or 3+ lyric words missing in a row | **FAIL** (omission) |
| One non-protected word missing | REVIEW |
| 3+ lyric words missing in one place but sung somewhere else | REVIEW (section reordered) |

**3e. Per-run numbers**
- **Lyric coverage** = lyric words found ÷ all lyric words. Target **≥ 95%**.
- **Vocal onset** = time of the first lyric word. Over about 6 s means a long intro; check that nothing was dropped.
- Run verdict: FAIL if any FAIL item or coverage < 95%; REVIEW if any REVIEW item; otherwise PASS.

**3f. Majority vote across the 4 runs (the Consensus sheet).** The same item from different runs is grouped together. An item counts only if **more than half** the runs show it (3 or 4 of 4). Items seen by 1-2 runs are marked "minority: likely STT noise". The song verdict in `song_qc_summary.md` uses only the majority items.

### Step 4: re-check the doubtful spots (slice_check.py)

Run this for:
- every majority FAIL, to confirm it before telling anyone
- every minority item whose type is "new word inserted" or "omission"; a 2/4 vote can still be real (see section 7)

```bash
.venv/bin/python scripts/slice_check.py <project> <song_stem> <start_s> <end_s>
```

Use a window of about 3-5 s around the time in the report. Start and end it in a pause between words; a word cut in half at the edge comes back as junk ("News", "Perpendicular"), and that is not the song's fault.

It prints two kinds of evidence:

1. **Ten transcripts. This is the deciding evidence.** Five engine settings on the vocals clip and five on the full-song clip: Scribe in the song's language, Scribe in English, Saaras `codemix`, Saaras `verbatim` and Saarika v2.5. Count how many of the 10 runs show the issue. Saaras `codemix` tidies up and usually misses an extra short word, so a correct-looking codemix line proves nothing on its own. Scribe, Saaras `verbatim` and Saarika write what was sung.
2. **Word timings and gaps (supporting evidence).** A gap of about 0.2 s or more between two words means something may have been sung there; about 0.05 s means nothing was. Example: in the rap take "theorem" ends at 29.30 and "square" starts at 29.36, so there was no room for the "a". **Caution:** Scribe sometimes folds an extra syllable into a neighbouring word. In one run "side" lasted 0.68 s and swallowed the extra "sit", leaving only a 0.12 s gap. An unusually long word is also a clue.

It also writes the two clips to `review_clips/` for listening.

### Step 5: listen and decide

Speech-to-text only tells you **where to listen**. Before reporting a FAIL, open the clip and listen at the timestamp. Final call:

| What you hear | Final verdict |
|---|---|
| The flagged word really is wrong, missing or extra | FAIL: regenerate the song or fix the lyrics |
| It's fine and the transcription was wrong | PASS: note "STT artifact" in the report |
| Same meaning but not the client's exact text (an inserted "has", remain/remains) | REVIEW: the client or producer decides |

---

## 6. Reading the report

### `song_qc_summary.md`: start here

One row per song: verdict, lyric coverage for the vocal-stem runs, vocal onset, majority items with timestamps, and minority items.

### `song_qc_report.xlsx`

| Sheet | What's in it | Use it for |
|---|---|---|
| **Consensus** | One row per distinct item, with how many runs agree (e.g. `4/4: scribe_mix, …`). Red = majority FAIL, amber = majority REVIEW, green = minority or clean | The working list of what to listen to |
| **Summary** | One row per song × run: coverage, FAIL count, REVIEW count, allowed ad-libs and repeats, onset, verdict | Seeing whether the runs disagree |
| **Items** | Every FAIL and REVIEW item from every run, with the lyric line it belongs to | Detail |
| **Transcripts** | The full text of all 5 transcripts per song, including the read-only Sarvam verbatim | Reading what was actually heard; compare verbatim against the others for extra words |

### Columns explained

- **Lyric word(s)**: what the lyric sheet says at that spot (empty for an extra word).
- **Heard**: what the transcript says (empty for a missing word).
- **≈ time (s)**: where in the song to listen (from Scribe; Sarvam times are only the start of each piece).
- **Engine runs agreeing**: how many of the 4 runs show this item, and which ones.

---

## 7. Worked examples (from the first test run, 2026-11-12)

| Song | Report said | What we did | Final |
|---|---|---|---|
| Newton pop (English) | PASS. One run had "remain to rest" (1/4) | Only the full-song run had it; both vocal runs heard "remains at rest" | **PASS**: the full-mix transcription was wrong |
| Pythagoras rap | FAIL: protected "a" missing at 29.3 s (4/4). REVIEW: "के" missing at ~18 s (4/4) | Slice check: "theorem" → "square" gap is 0.06 s, and all 8 runs say "theorem square" | **FAIL**: sings "Pythagoras theorem square plus b square" |
| Pythagoras rock | REVIEW: section reordered (4/4), 100% coverage | The "Three, four और five / Nine plus sixteen" verse is sung before the chorus instead of after it | **REVIEW**: every word is correct; the order is the client's call |
| Pythagoras Bollywood | Minority item (2/4 or 3/4, varies by run): extra word "स्थित" at ~16.0 s | Saaras codemix drops it and Scribe catches it only some of the time. Slice check (14.2-19.5 s): 8 of 10 runs heard "sit/सिट/सेट", including Saaras verbatim | **FAIL**: sings an extra word that is not in the lyrics |

What these show:
- Transcribe the vocal stem, not the full song (Newton).
- A 2/4 minority item can be real when one engine smooths words away (Bollywood). Always slice-check "new word" and "omission" items, even minority ones.
- Repeating a section in a different order is not a hallucination. Flag it, but don't fail it (rock).

---

## 8. Writing the report for the client or team

Use `song_qc_summary.md` as the base, apply your listening decisions from section 5, and send a table like this:

| Song | Verdict | Issue | Time | Action |
|---|---|---|---|---|
| pythagoras_rap_hindi_v2-5_take2 | FAIL | Sings "theorem square", missing "a" | 0:29 | Regenerate |
| pythagoras_bollywood_hindi_v2-5_take3 | FAIL | Extra word "स्थित" ("sit") | 0:16 | Regenerate or accept |
| pythagoras_rock_hindi_v2-5_take3 | REVIEW | Verse 2 sung before the chorus | 0:17 | Client decision |
| newton_laws_pop_SHORT_english_v2-5 | PASS | — | — | Deliver |

Include:
1. The method in one line: "Vocals separated with demucs, transcribed 4× (ElevenLabs Scribe ×3, Sarvam Saaras codemix ×1, plus Saaras verbatim for reference), scored against the lyric sheet; ad-libs, repeats and stutters allowed; flagged spots re-checked on 10 engine runs and listened to."
2. Exact timestamps, so anyone can jump straight to the spot.
3. The `review_clips/` clips for each FAIL.
4. A clear note on what was confirmed by ear and what was not.

The short position statement in section 6 of `Vocals_Lyrics_STT_QA_Guide.md` can go in the email as-is.

---

## 9. Tuning (in `scripts/song_qc_score.py`)

| What | Where | Default | When to change |
|---|---|---|---|
| Allowed filler words | `VOCABLES` | oh, yeah, hey, haan, arre… | Add language- or genre-specific fillers (Tamil `ra`, Punjabi `balle`…) |
| Filler words that only need REVIEW | `FUNCTION` | has, the, a, के, का… | Add common little words for other languages |
| Word-match threshold | `eq = [[S[i][j] >= .65` in `align()` | 0.65 | Raise if wrong words are being accepted; lower if correct words in heavy accents are being flagged |
| Repeat-match threshold | `sim(tw, w) >= .8` in `score()` | 0.8 | Keep high. At 0.65 "sit" matched "sixteen" and hid a real extra word |
| Spelling equivalents | `SAME` | equals=equal, squared=square, aur=or | Add pairs the transcription writes differently from the lyric sheet |
| Coverage pass mark | `r["coverage"] < .95` in `main()` | 95% | Client requirement |

After any change, re-run `./run_all.sh example` and check that the section 10 results still hold.

---

## 10. Expected results for `example/` (to check a new install)

Verified on a fresh install (2026-11-16):

```
newton_laws_pop_SHORT_english_v2-5      PASS     coverage 100%
pythagoras_bollywood_hindi_v2-5_take3   PASS*    minority: new word "स्थित" ~16.0 s (2/4)  *slice check → real → FAIL
pythagoras_rap_hindi_v2-5_take2         FAIL     protected "a" missing ~29.3 s (4/4); "के" missing ~18.0 s (4/4)
pythagoras_rock_hindi_v2-5_take3        REVIEW   section reordered ~16.8 s (4/4), coverage 100%
```

Scribe gives slightly different answers from run to run, so expect small changes:
- The Bollywood "स्थित" item moves between 2/4 (song PASS) and 3/4 (song FAIL). Either way the slice check settles it as a real FAIL. This is why section 5, step 4 says to slice-check minority "new word" items.
- A 1/4 minority item may appear or disappear (e.g. Newton "an→and" or "at→to").
- The rap and rock verdicts should never change.

Slice-check command for the Bollywood spot: `.venv/bin/python scripts/slice_check.py example pythagoras_bollywood_hindi_v2-5_take3 14.2 19.5`

---

## 11. Known quirks

- **Empty transcript ≠ no vocals.** If Scribe returns empty text (often with `language_probability` ≈ 0.12), the vocal may be buried. Check `stems/.../vocals.wav` by ear before calling it a missing vocal.
- **Saaras tidies, depending on the mode.** `transcribe` and `codemix` drop short words and "correct" grammar ("theorem a" → "a squared"). `verbatim` doesn't. Never decide on a single word from `codemix` alone.
- **Saaras `transcribe` mode changes its script between runs**: the same audio came back as "right angle" once and "राइट एंगल" another time. The kit uses `codemix` for this reason; don't switch it back.
- **Scribe writes Indian-language words in other scripts.** It may put a Hindi song in Tamil or Telugu script when names are South Indian. The scorer compares by sound, so this is fine; never treat Scribe's detected language as proof of how something was pronounced.
- **Numbers.** Engines write "3" or "three"; both are handled. Number words in a count-in ("one, two, three, four" before the verse) show up as extra words, so judge those by ear.
- **Heavy rock or distorted mixes** lower accuracy even on the vocal stem. Trust items that agree across runs and engines.
- **Long instrumental intro** (onset > 6 s) is fine if coverage is still ≥ 95%. If coverage is low as well, verses were probably dropped.
- **`(instrumental, no vocals)` inside the lyrics** is risky at generation time, because the model may sing it as a backing vocal. Put instructions like this in the style prompt instead.

---

## 12. Troubleshooting

| Problem | Fix |
|---|---|
| `ELEVENLABS_API_KEY is not set` | Create `.env` in the kit folder (section 2.3) |
| `No vocal stem for …` | Run step 1 (demucs) first, or check that `song_file` in `songs.csv` matches the file name exactly |
| `Missing …/songs.csv` | Copy `templates/songs.csv` into the project folder |
| A song is missing from the report | Its row in `songs.csv` is missing or misspelled, or `stt/<song>.json` doesn't exist yet |
| `WARNING … sarvam_vocals failed` | Usually rate limiting (`TooManyRequests`). Re-run `song_stt.py <project> --only <stem> --force` |
| demucs is slow | It runs on the CPU; about 5 s per 40 s song on an Apple M-series chip, slower on old laptops. Fine either way |
| `ffmpeg: command not found` | Install ffmpeg (section 2.1) and reopen the terminal |
| Hindi shows as boxes in Excel | Use a font that supports Devanagari, such as Nirmala UI on Windows or Kohinoor on Mac |
| Results look wrong everywhere (low coverage on every song) | Check that the lyric sheet matches what was actually sent to the music model, then run the `example/` project to rule out a broken install |
