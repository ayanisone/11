# 2026-09-30 — Bajaj Jhanvi Kapoor, RVC pass

Signal chain: ElevenLabs TTS (random host voice) → RVC (Applio) `Bajaj_Jhanvi_Kapoor`.

## Line

> हाय! कैसे हैं आप? आज का दिन बहुत ख़ास है, और मैं चाहती हूँ कि आप इसे पूरे दिल से एन्जॉय करें।

## Stage 1 — ElevenLabs TTS

| Setting | Value |
|---|---|
| Voice | Shreya G – Candid Hinglish Show Host |
| Voice ID | `KawjuInLhxYsnVJlqveG` |
| Model | `eleven_multilingual_v2` |
| Takes | 1 |
| Output | MP3, 128 kbps, 44.1 kHz, mono, 6.73 s |
| Flow | https://elevenlabs.io/app/flows/xIsl3pu3yHlJd0udobz3 |
| Generation ID | `l8I0uTWvrIIo9yFhfYBe` |
| Cost | 145.57 credits |

Voice was picked at random (Python `random.Random(872125762).choice`) from the
female Hindi voices in the workspace whose name or description calls them a host.
Female-only so the source sits in the same register as the target and no pitch
shift is needed.

| Voice | Voice ID |
|---|---|
| Saloni - Podcast Host | `MiJ09Pm6yO8PlBtypPsB` |
| Shruti - Bold, Confident and Energetic | `U5UXnPygDjprjuoeZRK4` |
| Niharika – Engaging Tutorial Host | `SYEXRGbHQjA9lX3UloRo` |
| **Shreya G – Candid Hinglish Show Host** (picked) | `KawjuInLhxYsnVJlqveG` |
| Reva – Immersive History Narrator | `JPxJlEJXg4B4Z9MEVf7P` |

## Stage 2 — RVC

| Setting | Value |
|---|---|
| Model | `Bajaj_Jhanvi_Kapoor` |
| Weight | `Bajaj_Jhanvi_Kapoor_1000e_59000s.pth` (1000 epochs, 59000 steps) |
| Index | `Bajaj_Jhanvi_Kapoor.index` |
| Embedder | contentvec |
| Training data | 00:20:38 |
| Pitch | 0 |
| f0 method | rmvpe |
| Index rate | 0.75 |
| Protect | 0.33 |
| Volume envelope | 1 |
| Use index | true |
| Clean audio | false |
| Split audio | false |
| Export format | WAV |
| Output file | `1a0f3299fdc_content_Bajaj_Jhanvi_Kapoor_1a0f3299fdc.wav` (0.65 MB) |
| Output format | WAV PCM, 48 kHz, 16-bit, mono, 6.72 s |
| Output levels | peak −5.53 dBFS, RMS −23.83 dBFS, 0 clipped samples |
| Inference time | 11.7 s |
