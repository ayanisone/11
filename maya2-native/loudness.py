"""ITU-R BS.1770-4 integrated loudness and true-peak, for levelling TTS output.

Maya 2 Native's own release samples land between -21.6 and -27.8 LUFS (6.2 LU of
spread across the 12 voices), so per-utterance normalisation is not optional if
the speech is going into a mix at a fixed dialogue level.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

# K-weighting biquads, specified at 48 kHz by BS.1770-4.
_SHELF_B = np.array([1.53512485958697, -2.69169618940638, 1.19839281085285])
_SHELF_A = np.array([1.0, -1.69065929318241, 0.73248077421585])
_HPF_B = np.array([1.0, -2.0, 1.0])
_HPF_A = np.array([1.0, -1.99004745483398, 0.99007225036621])

__all__ = ["integrated_lufs", "true_peak_dbtp", "normalize"]


def _k_weight(x: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    if sr != 48000:
        x = signal.resample(x, int(round(len(x) * 48000 / sr)))
        sr = 48000
    return signal.lfilter(_HPF_B, _HPF_A, signal.lfilter(_SHELF_B, _SHELF_A, x)), sr


def integrated_lufs(x: np.ndarray, sr: int) -> float:
    """Gated integrated loudness of a mono signal, in LUFS. NaN if nothing passes the gate."""
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    y, sr = _k_weight(x, sr)
    blk, hop = int(0.400 * sr), int(0.100 * sr)  # 400 ms blocks, 75 % overlap
    if len(y) < blk:
        return float("nan")
    ms = np.array([np.mean(y[s:s + blk] ** 2) for s in range(0, len(y) - blk + 1, hop)])
    ms = np.maximum(ms, 1e-20)
    lk = -0.691 + 10 * np.log10(ms)
    keep = lk > -70.0                                               # absolute gate
    if not keep.any():
        return float("nan")
    keep &= lk > (-0.691 + 10 * np.log10(np.mean(ms[keep])) - 10.0)  # relative gate
    if not keep.any():
        return float("nan")
    return float(-0.691 + 10 * np.log10(np.mean(ms[keep])))


def true_peak_dbtp(x: np.ndarray, sr: int, oversample: int = 4) -> float:
    """Inter-sample peak in dBTP, via polyphase oversampling."""
    y = signal.resample_poly(np.asarray(x, dtype=np.float64).reshape(-1), oversample, 1)
    p = float(np.max(np.abs(y)))
    return 20 * np.log10(p) if p > 0 else float("-inf")


def normalize(x: np.ndarray, sr: int, target_lufs: float = -23.0,
              ceiling_dbtp: float = -1.0) -> tuple[np.ndarray, dict]:
    """Scale to `target_lufs`, then pull back if that would breach `ceiling_dbtp`.

    Gain is linear only — no limiting — so the ceiling is honoured by backing the
    whole clip off rather than by squashing peaks. Returns (audio, measurements).
    """
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    src = integrated_lufs(x, sr)
    if not np.isfinite(src):
        return x.astype(np.float32), {"lufs_in": src, "lufs_out": src, "gain_db": 0.0,
                                      "dbtp_out": true_peak_dbtp(x, sr), "ceiling_limited": False}
    gain_db = target_lufs - src
    tp_after = true_peak_dbtp(x, sr) + gain_db
    limited = tp_after > ceiling_dbtp
    if limited:
        gain_db -= tp_after - ceiling_dbtp
    y = x * (10 ** (gain_db / 20))
    return y.astype(np.float32), {"lufs_in": src, "lufs_out": integrated_lufs(y, sr),
                                  "gain_db": gain_db, "dbtp_out": true_peak_dbtp(y, sr),
                                  "ceiling_limited": limited}
