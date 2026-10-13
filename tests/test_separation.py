"""Spectral subtraction must null a misaligned, level-mismatched vocal far better than the phase-inverted sum."""

import numpy as np

from bn_dub import media

RATE = 44100


def _voice(secs, seed=3):
    rng = np.random.default_rng(seed)
    t = np.arange(int(secs * RATE)) / RATE
    env = 0.5 * (1 + np.sin(2 * np.pi * 2.5 * t))                      # syllable-ish envelope
    buzz = sum(np.sin(2 * np.pi * 140 * k * t) / k for k in range(1, 8))  # harmonic "voice"
    return (0.12 * env * buzz + 0.02 * rng.standard_normal(len(t)) * env).astype(np.float32)


def _music(secs):
    t = np.arange(int(secs * RATE)) / RATE
    return (0.25 * np.sin(2 * np.pi * 220 * t) + 0.15 * np.sin(2 * np.pi * 330 * t)).astype(np.float32)


def _residual_db(bg, music, voice_band=(100, 1200)):
    """Energy left in the voice's band after separation, relative to the music-only reference."""
    err = media.to_mono(bg) - music[:len(bg)]
    spec = np.abs(np.fft.rfft(err))
    f = np.fft.rfftfreq(len(err), 1 / RATE)
    band = (f > voice_band[0]) & (f < voice_band[1])
    return 20 * np.log10(np.sqrt(np.mean(spec[band] ** 2)) / np.sqrt(np.mean(np.abs(np.fft.rfft(music))[band] ** 2)) + 1e-12)


def test_spectral_subtract_beats_time_domain_on_imperfect_isolation():
    secs = 4.0
    voice, music = _voice(secs), _music(secs)
    mix = music + voice
    # what a real isolator hands back: late by 13 ms, 2 dB hot, slightly different noise
    isolated = media.shift(voice * media.db_to_gain(2.0), int(0.013 * RATE)) + 0.01 * _voice(secs, seed=9)

    td = media.subtract_aligned(media.to_stereo(mix), media.to_stereo(isolated), rate=RATE)
    sp = media.spectral_subtract(media.to_stereo(mix), media.to_stereo(isolated), rate=RATE)

    before = _residual_db(media.to_stereo(mix), music)
    after_td = _residual_db(td, music)
    after_sp = _residual_db(sp, music)
    assert after_sp < after_td - 6          # clearly better than the phase-inverted sum
    assert after_sp < before - 10           # and clearly removed voice energy vs. the untouched mix


def test_attenuate_regions_only_inside_slots():
    bg = np.ones((3 * RATE, 2), dtype=np.float32) * 0.5
    out = media.attenuate_regions(bg, [(1.0, 2.0)], rate=RATE, amount_db=-6.0, fade_ms=20)
    assert out[int(0.5 * RATE), 0] == 0.5
    assert abs(out[int(1.5 * RATE), 0] - 0.5 * media.db_to_gain(-6.0)) < 1e-4
    assert out[int(2.5 * RATE), 0] == 0.5
    # edges are ramps, not steps
    assert 0.5 * media.db_to_gain(-6.0) < out[int(1.0 * RATE) - int(0.01 * RATE), 0] < 0.5
