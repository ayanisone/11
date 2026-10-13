"""ffmpeg + numpy audio plumbing. Everything internal is float32 PCM in [-1, 1] at settings.sample_rate."""

from __future__ import annotations

import json
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Optional

import numpy as np

from .config import settings

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"


def _run(cmd: list[str], *, capture: bool = False) -> bytes:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed ({proc.returncode}): {proc.stderr.decode(errors='replace')[-800:]}")
    return proc.stdout if capture else b""


def probe(path: str | Path) -> dict:
    out = _run([FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)], capture=True)
    return json.loads(out)


def duration(path: str | Path) -> float:
    info = probe(path)
    return float(info["format"].get("duration", 0.0))


def has_video(path: str | Path) -> bool:
    return any(s.get("codec_type") == "video" for s in probe(path).get("streams", []))


def extract_audio(src: str | Path, dst: str | Path, *, channels: int = 2, rate: Optional[int] = None) -> Path:
    """Pull the full mix out of a media file as a PCM wav."""
    rate = rate or settings.sample_rate
    _run([FFMPEG, "-y", "-v", "error", "-i", str(src), "-vn", "-ac", str(channels), "-ar", str(rate),
          "-c:a", "pcm_s16le", str(dst)])
    return Path(dst)


def decode(path: str | Path, *, channels: int = 1, rate: Optional[int] = None) -> np.ndarray:
    """Decode any audio file to float32 numpy. Shape: (n,) for mono, (n, channels) otherwise."""
    rate = rate or settings.sample_rate
    raw = _run([FFMPEG, "-v", "error", "-i", str(path), "-vn", "-ac", str(channels), "-ar", str(rate),
                "-f", "f32le", "-"], capture=True)
    arr = np.frombuffer(raw, dtype=np.float32)
    if channels > 1:
        arr = arr.reshape(-1, channels)
    return arr.copy()


def write_wav(path: str | Path, audio: np.ndarray, *, rate: Optional[int] = None) -> Path:
    """Write float32 [-1, 1] audio as 16-bit PCM wav."""
    rate = rate or settings.sample_rate
    audio = np.asarray(audio, dtype=np.float32)
    channels = 1 if audio.ndim == 1 else audio.shape[1]
    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return Path(path)


def time_stretch(src: str | Path, dst: str | Path, ratio: float) -> Path:
    """Speed up (ratio > 1) or slow down (ratio < 1) without changing pitch, via ffmpeg atempo.

    atempo accepts 0.5..100 per instance; we chain instances for anything outside 0.5..2.0.
    """
    if ratio <= 0:
        raise ValueError("ratio must be positive")
    factors: list[float] = []
    r = ratio
    while r > 2.0:
        factors.append(2.0)
        r /= 2.0
    while r < 0.5:
        factors.append(0.5)
        r /= 0.5
    factors.append(r)
    chain = ",".join(f"atempo={f:.6f}" for f in factors)
    _run([FFMPEG, "-y", "-v", "error", "-i", str(src), "-filter:a", chain, "-ar", str(settings.sample_rate),
          "-c:a", "pcm_s16le", str(dst)])
    return Path(dst)


def trim(src: str | Path, dst: str | Path, start: float, end: float) -> Path:
    _run([FFMPEG, "-y", "-v", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(src),
          "-ac", "1", "-ar", str(settings.sample_rate), "-c:a", "pcm_s16le", str(dst)])
    return Path(dst)


def mux(video_src: str | Path, audio_src: str | Path, dst: str | Path) -> Path:
    """Replace the audio track of a video with a new one; video stream is copied, not re-encoded."""
    _run([FFMPEG, "-y", "-v", "error", "-i", str(video_src), "-i", str(audio_src), "-map", "0:v:0", "-map", "1:a:0",
          "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(dst)])
    return Path(dst)


def to_mp3(src: str | Path, dst: str | Path, bitrate: str = "192k") -> Path:
    _run([FFMPEG, "-y", "-v", "error", "-i", str(src), "-c:a", "libmp3lame", "-b:a", bitrate, str(dst)])
    return Path(dst)


# ---------- numpy DSP ----------

def db_to_gain(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def peak(audio: np.ndarray) -> float:
    return float(np.max(np.abs(audio))) if audio.size else 0.0


def rms_db(audio: np.ndarray) -> float:
    if audio.size == 0:
        return -120.0
    r = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    return 20.0 * np.log10(max(r, 1e-9))


def to_mono(audio: np.ndarray) -> np.ndarray:
    return audio if audio.ndim == 1 else audio.mean(axis=1)


def to_stereo(audio: np.ndarray) -> np.ndarray:
    return audio if audio.ndim == 2 else np.stack([audio, audio], axis=1)


def find_lag(reference: np.ndarray, signal: np.ndarray, *, rate: int, max_lag_secs: float = 0.25,
             window_secs: float = 20.0) -> int:
    """Samples by which `signal` is late relative to `reference` (negative = early).

    FFT cross-correlation of the raw waveforms over the loudest `window_secs` of the reference, searched
    within ±max_lag_secs. Catches codec/priming delay from the isolation round-trip. Returns 0 if either
    side is silent.
    """
    ref = to_mono(reference).astype(np.float64)
    sig = to_mono(signal).astype(np.float64)
    n = min(len(ref), len(sig))
    if n == 0:
        return 0
    ref, sig = ref[:n], sig[:n]
    win = min(n, int(window_secs * rate))
    hop = max(1, win // 4)
    best_i, best_e = 0, -1.0
    for i in range(0, max(1, n - win + 1), hop):
        e = float(np.sum(np.square(ref[i:i + win])))
        if e > best_e:
            best_i, best_e = i, e
    ref, sig = ref[best_i:best_i + win], sig[best_i:best_i + win]
    if peak(ref) < 1e-4 or peak(sig) < 1e-4:
        return 0
    ref = ref - ref.mean()
    sig = sig - sig.mean()
    size = 1 << int(np.ceil(np.log2(2 * win)))
    # corr[k] = sum_i ref[i + k] * sig[i]; if sig lags ref by L the peak sits at k = -L.
    corr = np.fft.irfft(np.fft.rfft(ref, size) * np.conj(np.fft.rfft(sig, size)), size)
    max_lag = min(int(max_lag_secs * rate), win - 1)
    ks = np.arange(-max_lag, max_lag + 1)
    vals = corr[ks % size]
    return int(-ks[int(np.argmax(vals))])


def shift(audio: np.ndarray, samples: int) -> np.ndarray:
    """Delay (positive) or advance (negative) by `samples`, zero-padded, same length."""
    if samples == 0:
        return audio
    out = np.zeros_like(audio)
    if samples > 0:
        out[samples:] = audio[:-samples]
    else:
        out[:samples] = audio[-samples:]
    return out


def subtract_aligned(full_mix: np.ndarray, vocals: np.ndarray, *, rate: int) -> np.ndarray:
    """Background ≈ full mix − vocals, after lining the vocals up by cross-correlation.

    Phase-inverted sum: only as clean as the isolator's output is sample-accurate. Expect a faint
    vocal ghost on dense mixes; use demucs mode when that matters.
    """
    full_mix = to_stereo(full_mix)
    vocals = to_stereo(vocals)
    n = min(len(full_mix), len(vocals))
    full_mix, vocals = full_mix[:n], vocals[:n]
    lag = find_lag(full_mix, vocals, rate=rate)
    vocals = shift(vocals, -lag)
    return (full_mix - vocals).astype(np.float32)


def _stft(x: np.ndarray, n_fft: int, hop: int) -> np.ndarray:
    win = np.hanning(n_fft + 1)[:-1].astype(np.float32)
    pad = n_fft // 2
    xp = np.pad(x, (pad, pad))
    n = 1 + (len(xp) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n)[:, None]
    return np.fft.rfft(xp[idx] * win, axis=1)


def _istft(spec: np.ndarray, n_fft: int, hop: int, length: int) -> np.ndarray:
    win = np.hanning(n_fft + 1)[:-1].astype(np.float32)
    frames = np.fft.irfft(spec, n=n_fft, axis=1) * win
    out = np.zeros(hop * (len(frames) - 1) + n_fft, dtype=np.float64)
    norm = np.zeros_like(out)
    for i, fr in enumerate(frames):
        out[i * hop:i * hop + n_fft] += fr
        norm[i * hop:i * hop + n_fft] += win ** 2
    out /= np.maximum(norm, 1e-3)
    pad = n_fft // 2
    return out[pad:pad + length].astype(np.float32)


def spectral_subtract(full_mix: np.ndarray, vocals: np.ndarray, *, rate: int, over: float = 1.6, floor_db: float = -30.0,
                      n_fft: int = 2048, hop: int = 512) -> np.ndarray:
    """Background ≈ mix with the vocal's *magnitude* removed per STFT bin, keeping the mix's phase.

    Unlike a phase-inverted sum this survives codec delay, re-synthesis and level mismatch from the isolator:
    `over` > 1 over-subtracts to kill the vocal ghost, `floor_db` caps how deep a bin can be cut (musical-noise
    guard). Expect some breathing on dense mixes; demucs is the cleaner tool when it's available.
    """
    full_mix = to_stereo(full_mix)
    vocals = to_stereo(vocals)
    n = min(len(full_mix), len(vocals))
    full_mix, vocals = full_mix[:n], vocals[:n]
    lag = find_lag(full_mix, vocals, rate=rate)
    vocals = shift(vocals, -lag)
    floor = db_to_gain(floor_db)
    out = np.zeros_like(full_mix)
    for ch in range(full_mix.shape[1]):
        M = _stft(full_mix[:, ch], n_fft, hop)
        V = _stft(vocals[:, ch], n_fft, hop)
        mag = np.abs(M)
        # per-frame level match so an isolator that returns the vocal 2 dB hot/cold still nulls
        vm = np.abs(V)
        scale = np.sum(mag * vm, axis=1, keepdims=True) / np.maximum(np.sum(vm * vm, axis=1, keepdims=True), 1e-9)
        vm = vm * np.clip(scale, 0.5, 2.0)
        new_mag = np.maximum(mag - over * vm, floor * mag)
        out[:, ch] = _istft(new_mag * np.exp(1j * np.angle(M)), n_fft, hop, n)
    return out


def attenuate_regions(audio: np.ndarray, regions: list[tuple[float, float]], *, rate: int, amount_db: float,
                      fade_ms: float = 60.0) -> np.ndarray:
    """Dialogue-slot duck: pull the bed down by `amount_db` inside each (start, end), with raised-cosine edges."""
    out = to_stereo(audio).copy()
    gain = np.ones(len(out), dtype=np.float32)
    g = db_to_gain(amount_db)
    fade = max(1, int(fade_ms * rate / 1000))
    ramp = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fade))).astype(np.float32)
    for start, end in regions:
        a, b = max(0, int(start * rate) - fade), min(len(out), int(end * rate) + fade)
        if b <= a:
            continue
        seg = np.full(b - a, g, dtype=np.float32)
        k = min(fade, len(seg))
        seg[:k] = 1 - (1 - g) * ramp[:k]
        seg[-k:] = np.minimum(seg[-k:], 1 - (1 - g) * ramp[::-1][:k])
        gain[a:b] = np.minimum(gain[a:b], seg)
    out *= gain[:, None]
    return out


def assemble(clips: list[tuple[float, np.ndarray]], total_secs: float, *, rate: int,
             fade_ms: float = 8.0) -> np.ndarray:
    """Lay mono clips onto a silent mono timeline at their start offsets. Short fades avoid clicks."""
    total = int(round(total_secs * rate))
    out = np.zeros(total, dtype=np.float32)
    fade = int(fade_ms * rate / 1000)
    for start, clip in clips:
        clip = to_mono(np.asarray(clip, dtype=np.float32)).copy()
        if fade and len(clip) > 2 * fade:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            clip[:fade] *= ramp
            clip[-fade:] *= ramp[::-1]
        i = int(round(start * rate))
        if i >= total:
            continue
        j = min(total, i + len(clip))
        out[i:j] += clip[:j - i]
    return out


def envelope_db(audio: np.ndarray, *, rate: int, attack_ms: float = 5.0, release_ms: float = 250.0) -> np.ndarray:
    """Smoothed amplitude envelope in dB, one value per sample. Used as the sidechain key for ducking."""
    x = np.abs(to_mono(audio)).astype(np.float64)
    n = len(x)
    if n == 0:
        return np.zeros(0)
    # Detector runs on 1 ms block peaks (1 kHz control rate) so the Python loop stays cheap.
    block = max(1, rate // 1000)
    pad = (-n) % block
    blocks = np.pad(x, (0, pad)).reshape(-1, block).max(axis=1)
    ctrl_rate = rate / block
    a_att = float(np.exp(-1.0 / (attack_ms * ctrl_rate / 1000.0)))
    a_rel = float(np.exp(-1.0 / (release_ms * ctrl_rate / 1000.0)))
    env = np.empty_like(blocks)
    prev = 0.0
    for i, v in enumerate(blocks):
        a = a_att if v > prev else a_rel
        prev = a * prev + (1.0 - a) * v
        env[i] = prev
    env = np.repeat(env, block)[:n]
    return 20.0 * np.log10(np.maximum(env, 1e-6))


def duck(background: np.ndarray, key: np.ndarray, *, rate: int, amount_db: float, threshold_db: float = -40.0) -> np.ndarray:
    """Sidechain duck: pull `background` down by `amount_db` wherever the `key` is above threshold."""
    env = envelope_db(key, rate=rate)
    gain_db = np.where(env > threshold_db, amount_db, 0.0)
    gain = (10.0 ** (gain_db / 20.0)).astype(np.float32)
    bg = to_stereo(background)
    n = min(len(bg), len(gain))
    out = bg.copy()
    out[:n] *= gain[:n, None]
    return out


def limit(audio: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    """Brickwall-ish safety: scale the whole file down if its peak exceeds the ceiling. No pumping."""
    ceil = db_to_gain(ceiling_db)
    p = peak(audio)
    return audio * (ceil / p) if p > ceil else audio
