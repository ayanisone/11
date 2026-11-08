# duplex: natural, overlapping two-person dialogue

This folder holds two things, both inspired by Block's **Dessa**:

1. **A live voice agent** in our ElevenLabs workspace. It runs on Eleven v4 Turbo with Claude Haiku 5.5 and is tuned to take turns the way people do.
2. **`duplex`**, a CLI for ads, TVCs and DVCs. Claude writes an *overlap score*: dialogue where every line is timed against a moment in another line. ElevenLabs voices each line, and a timeline engine lays the lines out on two tracks with backchannels, overlaps and cut-offs. It prints speaker stems, a mix and a cue sheet.

---

## 1. What Dessa is, and why it sounds real

**Sourcing note:** block.xyz is blocked by this cloud session's network policy. The facts below come from press coverage of the 24 Oct 2026 launch (TechCrunch, ANI and others), not from Block's page. The demo clips themselves have not been heard. To analyse them, download a clip and run `duplex analyze` on it (section 4).

- **Full-duplex speech-to-speech.** One model listens and speaks at the same time. There is no ASR → LLM → TTS cascade and no text in the loop.
- **Trained only on audio of human conversation.** Block says it used no text and no pretrained model. It learned *when* to come in and when to backchannel ("yeah", "got it") from data, not from rules.
- **Research preview.** Early access is limited to safety researchers. There are no weights, no API, no published latency figures and no benchmarks. Every claim so far is Block's own.

### Why it feels natural: the turn-taking fingerprint

Across languages, the typical gap between one speaker stopping and the next one starting is about **0–200 ms** (Stivers et al., *PNAS* 2009). That is faster than anyone can plan a reply, so people start planning while the other person is still talking. As a result:

| Behaviour | What it sounds like |
|---|---|
| Latching | the answer starts the instant the question ends |
| Overlap | B starts before A finishes, because B already knows where A is going |
| Backchannel | "mm", "haan", "right" under the other person's line, without taking the floor |
| Completion | B finishes A's sentence |
| Cut-off | A stops mid-word when B cuts in, at the next word boundary |

A cascade agent (ElevenLabs, or anything else built as STT → LLM → TTS) is half-duplex. It waits for you to stop, waits for a silence timer, thinks, then speaks. Each of those steps adds hundreds of milliseconds, and the agent hears nothing while it is talking. Dessa removes that structure entirely.

## 2. What ElevenLabs + Claude can and can't match

| Target | Live agent (cascade) | Offline ads (`duplex`) |
|---|---|---|
| Low gap after you stop | **Partly.** Eager turn model, speculative LLM start, fastest LLM + v4 Turbo | **Fully.** Any gap, including negative |
| Backchannels from the AI while *you* talk | **No.** The agent can't speak while listening | **Yes.** They are placed on a word |
| Your "mm-hmm" not stopping the AI | **Yes.** Ignore-list for interruptions | n/a |
| A filler while the AI thinks | **Yes.** LLM-generated 1–3 word reaction after 0.9 s | n/a |
| The AI finishing your sentence | **Prompted only.** It completes after you stop, not over you | **Yes** |
| Cut-offs and overlap | **You can cut it off.** It can't cut you off | **Yes** |

**Conclusion:** live, we can get *close*. With an ElevenLabs cascade we can't build true full-duplex, meaning an AI that backchannels or talks over you mid-sentence. That needs a Dessa- or Moshi-class model. For ads, latency doesn't matter, so we can build *exactly* the Dessa feel. That is what `duplex` does.

## 3. The live agent: "Riff"

- **Agent:** `agent_4401m6yb63ehefdbpqqj0yem90tm` ("Duplex-style · Riff (ad brainstorm partner)"). Talk to it at https://elevenlabs.io/app/talk-to?agent_id=agent_4401m6yb63ehefdbpqqj0yem90tm. If that link doesn't open, find it under ElevenLabs → Agents.
- **Brain:** `claude-haiku-5-5`, reasoning `none`, max 300 tokens, temperature unset (Haiku 5.5 rejects non-default sampling). Backup model: `claude-sonnet-5-5` after 3 s.
- **Voice:** "Anya – Neutral Indian Professional" (`gYf9sqh3BkV9QqFMN9Hs`) on `eleven_v4_turbo`, with stability 0.4, speed 1.05 and expressive tags on.
- **Turn-taking:** `turn_v3`, eagerness `eager`, `speculative_turn` on. Soft timeout of 0.9 s → one LLM-generated 1–3 word reaction. The interruption ignore list covers en + hi defaults plus mm-hmm / yeah / right / haan / achha / theek hai, so your backchannels don't cut it off.
- **Prompt:** short turns, react first, latch onto and finish the user's thought, at most one tag per turn, and drop its line immediately when interrupted.

**What to try:** pitch a half-formed ad idea and trail off mid-sentence. Say "mm-hmm" while it talks; it should keep going. Cut it off; it should follow you.

**What to tune:** if it jumps in too early, set eagerness to `normal`. If the filler feels robotic, set `soft_timeout_config.timeout_seconds` to -1. The conversation logs show per-turn latency, so measure before and after each change.

## 4. `duplex` for TVCs and ads

```bash
cd duplex && pip install -e .
export ELEVENLABS_API_KEY=...      # render / analyze
export ANTHROPIC_API_KEY=...       # write

# 1. Claude writes the overlap score from a brief (default model claude-opus-5-5)
duplex write "30s spot: two flatmates planning a Goa trip; product = shared trip planner; Indian-English, casual" -o score.json

# 2. Voice it: one ElevenLabs take per line (cached), laid out on the timeline
duplex render score.json -o out --voice A=<voice_id> --voice B=<voice_id>

# 3. Reference track: measure a real conversation, optionally lift its timing into a score
duplex analyze dessa_demo.mp3 --score lifted.json
```

`examples/goa_trip_30s.json` is a hand-written score with voices already cast. It contains 3 backchannels, 5 overlapping handovers and an interruption where B finishes A's sentence. Render it with `duplex render examples/goa_trip_30s.json -o out`.

### The overlap score

```json
{"id": "l4", "speaker": "B", "interrupts": true, "yield_ms": 150,
 "text": "[sarcastic] —a hostel in the wrong Goa.",
 "start": {"ref": "l3", "at": "word", "word": "booked", "edge": "end", "offset_ms": 40}}
```

- `start` places this line's **first spoken word** relative to an earlier line. `at` is `end` (handover; a negative `offset_ms` means overlap), `start`, or `word` (land on a word or phrase, with `occurrence` and `edge`).
- `interrupts: true` cuts the anchored line off at the first word boundary `yield_ms` after this line starts, with a 40 ms fade. The interrupted line is written in full, and the cut happens in the edit.
- `kind: backchannel` lines usually sit at `gain_db` -4 to -8.
- Anchors are relative, so a slower re-take of one line moves everything hung off it. Takes are cached by text + voice + model + context, so editing offsets and re-rendering costs **no credits**.

### Outputs

| File | What |
|---|---|
| `out/stems/A.wav`, `out/stems/B.wav` | one stem per speaker on a shared timeline, 24-bit, ready for the session |
| `out/mix.wav` | sum of the stems. Stems and mix share one safety gain (ceiling -1 dBFS sample peak), so they still sum exactly. This is not a loudness master |
| `out/cues.csv` | id, speaker, kind, timecode (25 fps by default), overlaps, cut-off flag, text |
| `out/labels.txt` | Audacity/Reaper region labels |
| `out/report.json` | turn-taking stats (median gap, overlap share, backchannels/min) plus warnings: anchors that don't resolve, a speaker overlapping themselves, interrupts that land too late to cut |

The `analyze` command reports the same stats, so a render can be compared against a reference conversation number for number.

### How the takes are made

- Each line is a separate `/v1/text-to-speech/{voice}/with-timestamps` call on `eleven_v4` (default). The previous line's words are sent as `previous_text`, so an answer sounds like an answer. If the model rejects that field, the call is retried without it.
- Word timings come from the character alignment, with audio tags stripped. If none come back, the fallback is `/v1/forced-alignment`, then a loudness-based estimate (flagged in the report).
- v4 dialogue tags (`[jumping in]`, `[interrupting]`, `[overlapping]`) shape the **delivery**. The timeline does the **placement**. Both are needed: a line rendered alone and then overlapped still sounds like a solo read unless it's tagged. `report.json` warns about any line that starts over another speaker without one of these tags, and about hyphenated tags.
- The writer uses the full Eleven v4 tag set (emotion, delivery, non-verbal, pauses, dialogue timing) and follows v4's rules. A tag holds until the next tag. Tags describe how a line is spoken, not stage directions, so `[grinning]` is not performed. Capitals give emphasis, and numbers stay as written.
- Offline renders use `eleven_v4`. Turbo only matters for live agents.

## 5. Where we can use this

- **TVC/DVC dialogue spots:** two-hander scripts that sound overheard. Deliver stems + cue sheet to the mix, and recast voices without re-timing.
- **Animatics and pre-viz:** a client-ready scratch with real conversational timing before booking actors. Later, use the cue sheet as an ADR guide.
- **Re-voicing improv:** record two actors (or two of us) improvising on a phone. `duplex analyze --score` lifts their timing, then render with cast voices keeps the groove. To change the words, edit `text` but keep the anchor words.
- **Regional versions:** same score structure, translated lines. Check that anchor words still exist in the translation. Eleven v4 covers 90+ languages.
- **Radio and podcast-style ads:** host + guest banter, with backchannels baked in.
- **Live "Riff" agent:** a brainstorming partner for the creative team, a sales and booth demo, or the base for voice-led brand experiences (contests, quizzes). Swap the prompt and voice per brand.

## 6. `duplex live`: the Dessa-style agent (pseudo-duplex)

Riff (section 3) is a cascade: it can't make a sound while you talk. `duplex live` is our own agent that can.
It keeps the mic open the whole time and decides, every 40 ms, what to do with its mouth.

```
browser mic ─► local voice detector ─────────────────────────────┐  (fast: ~40-120 ms)
          └──► Scribe v2 Realtime ─► live transcript ─► Claude Haiku 5.5 "listener"  (slow: ~0.5-1.5 s)
                                                        │ continuing / hesitating / finishing / done,
                                                        │ which backchannel fits, is it funny, how it ends
                                                        ▼
                                                    Floor manager (the knobs) ── every 40 ms decides:
   backchannel ◄── pre-rendered bank (eleven_v4, in the browser: zero delay)     · murmur "mm-hmm" / "haan" / laugh
   reply       ◄── Claude Haiku 5.5 brain ─► clauses ─► eleven_v4_turbo stream  · draft a reply early, behind a gate
                                                                                 · open the gate (or come in before you finish)
   stop        ◄── you talk over it with real words (not "yeah") for > 0.3 s    · cut itself off, remember what you heard
```

```bash
cd duplex && pip install -e '.[live]'
export ELEVENLABS_API_KEY=...  ANTHROPIC_API_KEY=...
duplex live                       # then open http://127.0.0.1:8000, headphones on, press Start
duplex live --voice <voice_id> --language en --set eot_unsure=0.9
```

- On first run it renders the backchannel bank for the voice with `eleven_v4`: 11 sounds × 2 takes, trimmed and peak-normalised. They're cached in `~/.duplex/bank/<voice>/`, so they cost nothing after that.
- The page shows the live transcript, what the listener thinks (`finishing · ~1 word left · would say "haan"`), each response gap in ms, and sliders for the floor knobs. Every session is saved to `sessions/` with its turn-taking stats, in the same format as `duplex analyze`.
- Scribe authenticates with a single-use token, so the API key never rides on the WebSocket.

**Verified here** with the real ElevenLabs services, in headless Chrome with a generated recording as the mic. Claude was replaced by a scripted stand-in, because this sandbox can't call the Anthropic API.

- Backchannels landed in the pauses ("mm-hmm" at 6.5 s, "haan" at 12.4 s) and a laugh came after the funny line.
- The reply started 670–700 ms after the speech ended: about 290 ms of the agent's own wait, plus streaming TTS through this sandbox's proxy.
- Interrupting it with "Wait, wait, what if it's the grandma…" stopped it within about 0.5 s, and the next reply followed the new idea.
- With real Claude, expect a few hundred ms more whenever a reply couldn't be drafted early. The page measures this, so check it on your own setup.

**What it still can't do:** its timing comes from rules plus Claude's judgement, not from learning. It hears you through a transcript that lags 0.5–1 s, so the "before you finish" start only fires when the listener is confident. Each dropped draft costs one short Haiku call and a short TTS clip. Use headphones, or keep the mic ducking on.

**The true full-duplex route** is still open: NVIDIA PersonaPlex-7B (built on Kyutai Moshi; MIT code, NVIDIA Open Model License weights) can be self-hosted on a GPU. It's English-first, our voices and Hinglish would need fine-tuning, and the licence needs checking before commercial use.

## 7. Tests

```bash
cd duplex && pip install -e '.[dev]' && pytest
```

The tests cover the live floor manager's timing rules (fake clock), the live session wiring (fakes), anchor resolution, the v4 tag checks, interruptions, the self-overlap check, stems summing to the mix, 24-bit WAV round-trips, backchannel detection, lifting a reference's timing into a score and re-creating it exactly, and an end-to-end render of the example with a faked TTS (including the cache). The ElevenLabs calls (TTS with timestamps, streaming TTS, Scribe Realtime, the bank) were also run against the live API; the Claude calls were not, because this sandbox can't reach the Anthropic API with a key, so run `duplex write` and `duplex live` once with your key before relying on them.
