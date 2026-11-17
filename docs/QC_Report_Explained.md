# The QC report, explained simply

This is a plain-language guide to **"Final QC report: all theories since the character-length rule"** (`QC_Report_All_Theories.pdf`). Part 1 explains every technical word the report uses. Part 2 walks through the report section by section. Part 3 lists what's needed from you.

Each term gets a studio comparison first and then the plain meaning. Where the comparison stops holding, it says so.

---

## Part 1: The jargon, explained

### A. Making the songs

| Term | Studio comparison | Plain meaning |
|---|---|---|
| **Theory** | The client's brief or reference track | The lesson text the client sends (e.g. "Fractions"). Every song must teach exactly this, nothing more. |
| **Character-length rule** | A fixed run time, like a 30 s ad spot | The song length comes from the theory length: **500 characters = 40 seconds** (0.08 s per character, maximum 4 minutes). Waves had 2,822 characters, so it got 226 s. |
| **Lyric sheet** | The lyric sheet on the vocal booth stand | The words the AI singer must sing, split into Chorus, Verse 1, Bridge and so on. |
| **Universal sheet** | One vocal take that has to sit in 10 different mixes | One lyric sheet written so it fits all 10 genres, from slow jazz to fast pop-punk, without rushing in any of them. |
| **Density (syllables per second)** | Headroom. Too many words per second is like running a channel too hot: it clips | How many sung syllables are packed into each second. **About 2.2-2.5 per second works; about 3.4 per second failed** (the singer skipped or mashed words). |
| **Chorus-first** | Starting the track on the hook instead of a long intro | The song opens straight on the chorus, so the main idea comes first and the model has no empty intro to fill. |
| **Take** | A take | One finished audio file. For each genre we make a **male take and a female take**. |
| **Genre** | Genre | The 10 styles: Reggaeton, Afrobeats, Bhangra, Funk, Jazz, A cappella + beatbox, Indie acoustic, Pop-punk, K-pop, Liquid DnB (drum and bass). |
| **Prompt** | The producer's notes to the session singer | The written instructions sent with the lyrics: tempo, instruments, voice type, "start singing at 0 seconds", "don't add words". |
| **Generation / render** | Bouncing a mix | The AI (ElevenLabs Music) creating one take. It takes about 3-6 minutes per batch. |
| **Credits** | Studio hours on the invoice | What each take costs on ElevenLabs: about **23 credits per second of song**, so a 226 s take is about 5,273 credits. |
| **Render failure** | A bounce that crashes halfway | ElevenLabs' server errors out and no audio is made. We just run it again. |

### B. Checking the songs (QC)

| Term | Studio comparison | Plain meaning |
|---|---|---|
| **QC (quality control)** | The final listening pass before a song ships | Checking that every word was sung correctly and no fact was changed. |
| **Fact check (Lyric Fact QC)** | Checking the lyric sheet against the brief before the session | Before any audio is made, every lyric line is checked against the theory: no new facts, no wrong numbers, no words from outside the theory. |
| **demucs / vocal stem** | Pulling a stem: soloing the vocal track out of a stereo bounce | A tool that separates the voice from the music, so the speech-to-text tools hear the words clearly. *Where the comparison stops:* the separation isn't perfect, and some music can bleed into the "vocal" track. |
| **Voice isolator** | A cheaper de-mixing plugin we tried first | Used only for RBC (the first theory). It sometimes **invented words that weren't sung**, so we switched to demucs. |
| **Transcription (speech-to-text, STT)** | No clean studio comparison | Software that listens to the audio and writes down the words it hears. |
| **Scribe / Sarvam** | Two different "listeners" | The two transcription services. **Scribe** (from ElevenLabs) is the main one. **Sarvam** (an Indian service) is a second opinion. |
| **Engine run** | One person listening once | One transcription of one take. Each take gets **4 scored runs**: Scribe 3 times (once on the full mix, twice on the vocal stem) and Sarvam once. A second Sarvam run is kept only as a reference. |
| **Scorer / majority vote** | Asking four engineers to listen, then going with what most of them heard | A script compares each run's words with the lyric sheet. A problem counts only if **more than half the runs** agree on it, so one listener's mishearing doesn't fail a song. |
| **Coverage %** | No clean comparison | How much of the lyric sheet the listeners found in the audio. 100% = every word heard. |
| **Slice check** | Looping a 4-bar section and listening 10 times | For a doubtful spot, we cut out those few seconds and run **10 transcriptions** on it alone, for a firm answer (e.g. "10/10 runs heard 'V' instead of 'c'"). |
| **Key-phrase check** | A checklist of must-hear lines for the client | A list of 30-45 important phrases per theory ("numerator", "speed of light… c"). Each must be heard in at least 2 of the 3 Scribe runs, or the take is flagged. |
| **Transcript read** | The engineer reading the lyric printout along with the playback | A human-style read of the full transcript of every flagged take, because the scorer alone sometimes misses mistakes. |
| **Protected word** | No clean comparison | A word that carries the science ("numerator", "amplitude", "T", "c"). Losing one of these is serious; losing "the" or "a" is not. |
| **Vocal onset / intro** | Pre-roll before the vocal comes in | The time before the first sung word. We ask for 0 s; some genres (especially DnB) add a 10-22 s instrumental intro. |

### C. Kinds of mistakes

| Term | Studio comparison | Plain meaning |
|---|---|---|
| **Omission / dropped word** | A word that never made it onto the take | The singer skipped a word or line. |
| **Insertion / ad-lib** | A "yeah!" or "oh baby" the singer threw in | Extra words not in the lyric sheet (e.g. "got it in the corazón"). Not allowed: kids could learn the wrong words. |
| **Sound-alike** | A word that sounds right in the mix but the listener spells it differently | The singing is probably fine, but the transcriber heard a similar word ("one **in** four" heard as "one **and** four"). Usually harmless. |
| **Garbled line** | A mumbled, unusable phrase | The words came out as nonsense ("vive le vivre, new base spleen"). |
| **Wrong fact** | The worst case: the lyric changes meaning | The singer said something scientifically false, e.g. "the speed of light is **V**" instead of **c**. Always a FAIL. |
| **Merged line** | Two lines comped together into one wrong line | Two lyric lines blended into one sentence that means something false. |
| **End squeeze** | Running out of tape before the last chorus | Too many words for the time, so the singer rushes or drops the last chorus. |
| **Call-and-response tags** | Short backing-vocal answers | The short questions and answers in the lyrics ("Top number? Numerator!", "Period, **T**?"). These short bits get dropped most often. |
| **Isolator / stem artifact** | Bleed or phasing in a stem that sounds like a word | A "word" that only appears in the separated vocal track and not in the full mix. It's a tool glitch, not a singing error. |

### D. The verdicts (the grades)

| Verdict | Meaning | Delivered? |
|---|---|---|
| **PASS** | Every fact sung correctly. | Yes |
| **PASS (minor)** | A tiny slip, such as "the" dropped or one word of a doubled pair sung once. No fact lost. | Yes |
| **REVIEW** | Probably fine, but a person should **listen at the time given** before it goes to kids. | Yes, with a note |
| **FAIL** | A fact was lost or changed, or outside words were added. | No, it's regenerated |
| **Retry** | Regenerating a failed take with a fixed prompt. Same lyrics, better instructions. | — |
| **Held back** | Failed 3 times (the first try plus 2 retries). We stop spending credits on it. | No |

---

## Part 2: Walking through the report

### Page 1, top: how to read the opening box
The first three lines of the report are the rules of the game. They say how long each song is (the character rule), how every take was checked (the QC chain in Part 1B, in that order), and what the grades mean (Part 1D).

### Section 1: the summary table
One row per theory, in the order we made them. Read each row left to right:

- **Characters → length**: the theory's size and the song length it produced.
- **Lyric sheet**: which version of the words was used. "v1, v2, v3" are revisions. "Universal" means one sheet for all genres.
- **Takes delivered**: how many good audio files you have.
- **Held back**: which takes failed 3 times.
- **Credits**: what it cost on ElevenLabs. "≈" means estimated, because early runs weren't logged.
- **Folder**: where the audio files are.

**The headline:** from Motion onwards (where the 10 genres × male/female plan started), **80 takes were planned and 72 were delivered (90%)**. **Every genre has at least one usable take in every theory.**

### Section 2: RBC (red blood cells), the first test
This was one genre (reggaeton), 55 seconds long. The best take is **PASS (minor)**: both fact corrections are sung, with small slips like "man **and** on an average". This is also where we found the voice isolator invents words, and switched to demucs.

### Section 3: Thermodynamics, the lesson that changed everything
- **First version (v2):** 7 of 11 genres failed, because we packed in too many words (about 3.4 syllables per second). The channel was clipping.
- **Second version (v3, the universal sheet):** with fewer words (217 syllables in 90 s), 8 of 10 genres passed and 2 were sent for a listen. One of them is **funk at 0:28**, where the listeners heard "cooking gas" as a swear word. Please listen to that before it goes out.
- **K-pop:** kept dropping the one-word answer "Heat!", so we wrote it as **"Heat, heat!"**. Doubling short answers became a permanent rule.

### Section 4: Motion, 19 of 20
Everything passed except the **a cappella female** take. Its third attempt merged two lines into "Air moves into arteries and veins", which is a false statement, so it's held back. This is also where we learned the scorer can miss a merged line, and added the transcript read.

### Section 5: Trigonometry, 17 PASS + 2 REVIEW
- **A cappella male:** held back (the third try sang the y-axis fact wrongly).
- **DnB (both voices):** REVIEW. At this length the DnB style always adds a **22 second instrumental intro** and skips the opening chorus. Every fact is still sung later. We made two versions of each: the full song, and an edit with the intro trimmed off.
- **Your choice is needed here** (see Part 3).

### Section 6: Fractions, 15 PASS + 2 REVIEW, 3 held back
- **Held back:** funk female, K-pop female and DnB female each failed 3 times. The **male** take passes in all three genres, so every genre is still covered.
- **Listen checks:**
  - **Punk female at 1:49**: "X over four" may sound like "X for four".
  - **Reggaeton male at 0:45**: an extra ad-lib, "got it in the corazón", in the instrumental gap.
- **Notes for the client** (about their theory text, not our songs): the apple example should say "equal" parts, and "three people, four slices" isn't explained in the theory.

### Section 7: Waves, still in progress
- **So far:** 15 PASS + 2 REVIEW.
- **Pending:** 3 female takes (punk, K-pop, DnB). Their check was stopped before it finished, so they're marked ⏳.
- **Listen checks:**
  - **Reggaeton female at 3:20**: adds the line "We can get changes in waves".
  - **Afrobeats female at 1:45**: one chorus line is garbled there. It's sung correctly in the other two choruses.
- **Biggest catch:** K-pop male first sang the speed of light as **"V"**, which is wrong. The retry spelled the letters out phonetically in the instructions ("see" for c) and fixed it.
- **Note for the client:** the pond example is printed under "Matter waves" in their text, but it's really a water (mechanical) wave example. The song moves it next to "water waves".

### Section 8: what we learned (now standard practice)
1. **Fewer words per second = cleaner songs.** About 2.2-2.5 syllables per second is the safe headroom.
2. **Short answers and single letters get dropped**, so we double them ("Heat, heat!") and spell letters out in the instructions ("tee", "vee", "see").
3. **Long science phrases at the end of a fast line get mumbled** ("trigonometric identities"). Give them space.
4. **The automatic score isn't enough.** The key-phrase check plus the transcript read caught 5 wrong-fact takes that the scorer had passed.
5. **Genre habits:** female a cappella loses words after the beatbox break; long DnB songs add a 22 s intro; K-pop at fast tempos swaps letters.
6. **Server failures** are simply re-run.

### Section 9: open items
This is the to-do list. It's repeated in Part 3 as plain actions.

---

## Part 3: What I need from you

| Item | What to do |
|---|---|
| **1. Finish Waves** | Say "go" and I'll finish the 3 pending female takes (punk, K-pop, DnB), then update the report. |
| **2. Trigonometry DnB** | Pick one: **A** use the intro-trimmed edits, **B** use the full versions with the 22 s intro, or **C** drop DnB for this theory. |
| **3. Motion a cappella female** | Pick one: **A** remake with no instrumental break, **B** remake as a male/female duet, or **C** skip it (the male take passes). |
| **4. Listen checks (5 spots)** | Fractions punk F **1:49**, fractions reggaeton M **0:45**, waves reggaeton F **3:20**, waves afrobeats F **1:45**, thermodynamics funk **0:28**. If one sounds wrong, tell me and it'll be regenerated. |
| **5. Security** | Change (rotate) the Sarvam API key that was pasted into the chat earlier. |
