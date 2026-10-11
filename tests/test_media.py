import numpy as np
import pytest

from bn_dub import media

RATE = 44100


def tone(freq, secs, amp=0.5, rate=RATE):
    t = np.arange(int(secs * rate)) / rate
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_wav_roundtrip(tmp_path):
    x = tone(440, 0.5)
    p = media.write_wav(tmp_path / "a.wav", x)
    y = media.decode(p, channels=1)
    assert abs(len(y) - len(x)) <= 2
    assert np.max(np.abs(y[:len(x)] - x[:len(y)])) < 2e-3


def test_time_stretch_changes_duration_not_pitch_much(tmp_path):
    src = media.write_wav(tmp_path / "s.wav", tone(440, 2.0))
    dst = media.time_stretch(src, tmp_path / "d.wav", 1.25)
    assert abs(media.duration(dst) - 1.6) < 0.05
    dst2 = media.time_stretch(src, tmp_path / "d2.wav", 0.25)  # chained atempo (0.5 * 0.5)
    assert abs(media.duration(dst2) - 8.0) < 0.1


def test_assemble_places_clips_at_offsets():
    clip = np.ones(RATE // 10, dtype=np.float32) * 0.5  # 100 ms
    out = media.assemble([(1.0, clip), (2.0, clip)], 3.0, rate=RATE, fade_ms=0)
    assert len(out) == 3 * RATE
    assert out[int(1.05 * RATE)] == pytest.approx(0.5)
    assert out[int(2.05 * RATE)] == pytest.approx(0.5)
    assert out[int(0.5 * RATE)] == 0.0
    assert out[int(1.5 * RATE)] == 0.0


def test_assemble_clips_past_end_are_truncated_not_crashing():
    clip = np.ones(RATE, dtype=np.float32)
    out = media.assemble([(2.5, clip), (10.0, clip)], 3.0, rate=RATE)
    assert len(out) == 3 * RATE
    assert out[-1] > 0.0


def test_find_lag_and_subtract():
    rng = np.random.default_rng(7)
    # "voice": noise with a syllable-ish amplitude envelope, so correlation has a single clear peak
    env = 0.5 * (1 + np.sin(2 * np.pi * 3 * np.arange(3 * RATE) / RATE))
    vocals = (rng.standard_normal(3 * RATE) * 0.1 * env).astype(np.float32)
    full = tone(220, 3.0, 0.4) + vocals  # "music" + "voice"
    lag = 441  # 10 ms late
    late_vocals = media.shift(vocals, lag)
    assert media.find_lag(full, late_vocals, rate=RATE) == lag
    bg = media.subtract_aligned(media.to_stereo(full), media.to_stereo(late_vocals), rate=RATE)
    # residual 1 kHz should be mostly gone: compare RMS of bg to music-only
    music_only = media.to_stereo(tone(220, 3.0, 0.4))
    n = min(len(bg), len(music_only)) - lag
    err = media.rms_db(bg[lag:n] - music_only[lag:n])
    assert err < -40


def test_duck_reduces_background_only_under_key():
    bg = np.ones((3 * RATE, 2), dtype=np.float32) * 0.5
    key = np.zeros(3 * RATE, dtype=np.float32)
    key[RATE:2 * RATE] = 0.5  # voice in the middle second
    out = media.duck(bg, key, rate=RATE, amount_db=-12.0)
    assert out[int(0.5 * RATE), 0] == pytest.approx(0.5)
    assert out[int(1.5 * RATE), 0] == pytest.approx(0.5 * media.db_to_gain(-12.0), rel=1e-3)
    # release tail: still partly ducked shortly after the key stops
    assert out[int(2.05 * RATE), 0] < 0.5


def test_limit_only_scales_when_over_ceiling():
    x = np.array([0.5, -0.8], dtype=np.float32)  # -1 dBFS ceiling is 0.891
    assert np.array_equal(media.limit(x, -1.0), x)
    y = media.limit(np.array([1.5, -0.5], dtype=np.float32), -1.0)
    assert media.peak(y) == pytest.approx(media.db_to_gain(-1.0))
