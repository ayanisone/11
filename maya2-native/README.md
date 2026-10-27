# Maya 2 Native — runner + level measurements

[`maya-research/maya2-native`](https://huggingface.co/maya-research/maya2-native) — streaming TTS for 11 Indic
languages + English, 20 built-in voices, zero-shot cross-lingual voice cloning, Apache-2.0. Backbone is
Qwen3-1.7B-Base; audio is Kyutai Mimi, 32 codebooks at 12.5 fps; output is 24 kHz mono.

- `colab.ipynb` — GPU notebook: install, generate, loudness-normalise, clone, stream.
- `loudness.py` — ITU-R BS.1770-4 integrated loudness and true peak, used to level the output.

## Why it can't run in a CPU cloud session

The inference engine is hard-wired to CUDA. `maya3/engine.py` and `serve/` use `torch.cuda.CUDAGraph`,
`torch.cuda.Event`, `torch.cuda.Stream`, `graph_pool_handle`, pinned-memory staging buffers and
`attention="triton"` — 36 CUDA-specific call sites in the live inference path. The `device=` argument on
`Engine.__init__` and `Maya3TTS.from_pretrained` defaults to `"cuda"` but is not a working knob; passing
`"cpu"` fails on the first graph capture. Upstream's own README states Linux, Python 3.10–3.12 and an NVIDIA
GPU with a CUDA 12.8 driver, 8 GB VRAM minimum.

Runtime footprint at `max_seats=1`: **9.2 GB peak while loading, 7.7 GB steady**, plus ~0.5 GB CUDA context.
`max_seats` allocates up front whether seats are busy or not — 9.7 GB at 8 seats, 15.8 GB at 32.

Only the text frontend (`maya3/text/`, pure stdlib), the guards (`maya3/guards.py`, numpy) and the server
against a fake engine are CPU-runnable; upstream ships them as `run_tests.sh`. That exercises normalisation
and chunking, not synthesis.

## Measured: the 12 release samples

Measured with BS.1770-4 K-weighting and 4× oversampled true peak. All 12 are **24 kHz mono PCM_16**.
Noise floor is the 5th-percentile RMS of 50 ms windows; bandwidth is where the Welch PSD falls 40/60 dB off
its peak.

| sample | sec | peak dBFS | dBTP | LUFS | LRA | floor dBFS | BW-40 Hz | BW-60 Hz |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| as_nakul | 5.20 | -10.5 | -10.4 | -26.0 | 4.9 | -62.9 | 6152 | 11994 |
| bn_jahnavi | 8.24 | -8.9 | -8.8 | -26.9 | 5.6 | -84.7 | 11355 | 12000 |
| en_siddhant | 8.00 | -10.5 | -10.5 | -25.4 | 6.7 | -66.7 | 6334 | 12000 |
| gu_vaidehi | 7.84 | -8.5 | -8.4 | -24.6 | 6.8 | -71.4 | 10986 | 12000 |
| hi_ritvik | 7.76 | -7.7 | -7.6 | -25.3 | 6.3 | -86.5 | 3967 | 11953 |
| kn_satvik | 8.96 | -9.9 | -9.9 | -25.9 | 6.1 | -72.7 | 9117 | 12000 |
| ml_anirban | 6.24 | -8.6 | -8.6 | -27.8 | 8.0 | -79.1 | 9615 | 11994 |
| mr_charvi | 9.52 | -7.3 | -7.2 | -25.7 | 7.6 | -84.1 | 10459 | 12000 |
| or_ahana | 7.28 | -12.0 | -12.0 | -26.7 | 7.5 | -84.6 | 11936 | 12000 |
| pa_malini | 6.64 | -11.3 | -11.3 | -26.1 | 6.8 | -76.6 | 11953 | 12000 |
| ta_abhay | 10.16 | -10.1 | -10.1 | -27.5 | 8.5 | -89.3 | 3053 | 10055 |
| te_nivedita | 8.64 | -6.2 | -6.1 | -21.6 | 10.1 | -85.4 | 11777 | 12000 |
| **mean** | 7.87 | -9.3 | -9.3 | -25.8 | 7.1 | -78.7 | 8892 | 11833 |

What matters when using this in a mix:

- **Loudness is not consistent between voices: -21.6 to -27.8 LUFS, 6.2 LU of spread.** Normalise per
  utterance. `loudness.py` does it to a target with a true-peak ceiling, linear gain only, no limiting.
- **Headroom is generous and nothing clips** — mean peak -9.3 dBFS, worst case -6.1 dBTP, zero samples at
  full scale, true peak never more than 0.1 dB above sample peak. No inter-sample peak risk.
- **24 kHz means 12 kHz of bandwidth**, and the content does run flat to Nyquist rather than brickwalling
  early. Fine for dialogue; it is not a 48 kHz deliverable, and resampling up does not restore the top octave.
- **Noise floor is usually -70 to -89 dBFS, but two samples are higher** — `as_nakul` at -62.9 and
  `en_siddhant` at -66.7. Caveat on those two: `as_nakul` is the shortest clip and may not contain enough
  true silence for a 5th-percentile window to land off-speech, so that figure is an upper bound on the floor,
  not necessarily the floor itself.
- **DC offset is negligible** across all 12 (|mean| < 1.1e-4).

## Run it

Open `colab.ipynb` and set an **L4 or A100** runtime. The free T4 is Turing (sm_75) and has no native bf16
while this model ships a bf16 backbone, so expect slow emulation or kernel failures there; cell 1 reports
compute capability, bf16 support and free VRAM before you spend time on an install.

Outside Colab, on any Linux box with a CUDA 12.8 driver:

```bash
python -m venv .venv && source .venv/bin/activate     # Python 3.10-3.12
pip install "maya3[server] @ git+https://github.com/MayaResearch/maya2-native" \
  --extra-index-url https://download.pytorch.org/whl/cu128
```

```python
import soundfile as sf
from maya3 import Maya3TTS

tts = Maya3TTS.from_pretrained("maya-research/maya2-native", max_seats=1)
audio = tts.generate("আপনার অর্ডার পাঠানো হয়েছে।", lang="bn", voice="Jahnavi", normalize=True)
sf.write("speech.wav", audio, 24000)
tts.close()
```

`normalize=True` is required on the Python API — it defaults off there and on in the HTTP/WebSocket servers.
It expands numbers, currency, dates, times, URLs and email addresses into spoken form.

## Known weak spots

From the release's own benchmark (6,000 held-out texts, 12 languages, ~3.5% overall CER):

- **Web addresses: 29% CER** (20% under their revised scorer). Heavy code-mix 16.7%. Listen before trusting
  it with URLs, long digit strings or names.
- **Assamese has no native voice** — no built-in voice has an hour of `as` audio, outputs can drift toward a
  Bengali-like timbre, and it is the weakest language at 5.4% CER.
- **Very short turns** are unstable in voice identity; pad a one-word reply into a phrase.
- **Emotion tags** (`[laughs]`, `[sighs]`, `[whispers]`) are best-effort, not a focus of this release.
- **No audio watermark** in this release. Disclose synthetic speech; clone only voices you have permission to
  use.

Bengali-trained voices (≥1 h `bn`): `Ahana Vaidehi Malini Charvi Jahnavi Anirban Nakul Vasant Siddhant
Satvik`. The other ten are en/hi/ta/te-trained and will speak Bengali cross-lingually, carrying their
training accent.

## Licensing

Weights and inference code are Apache-2.0. Upstream components keep their own: Qwen3-1.7B-Base (Apache-2.0),
Kyutai Mimi (**CC-BY-4.0**), SpeechBrain ECAPA-TDNN (Apache-2.0). The Mimi CC-BY-4.0 attribution requirement
rides along with any redistribution.
