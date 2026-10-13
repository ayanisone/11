import numpy as np

from bn_dub import direct, verify

RATE = 44100


def _burst(freq, secs, amp):
    t = np.arange(int(secs * RATE)) / RATE
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_measure_finds_pause_and_emphasis():
    # three "words": 0.4 s, 0.4 s, then a 0.5 s gap, then a loud 0.4 s word
    sil = np.zeros(int(0.5 * RATE), dtype=np.float32)
    x = np.concatenate([_burst(150, 0.4, 0.2), _burst(150, 0.4, 0.2), sil, _burst(150, 0.4, 0.8)])
    words = [{"text": "one", "start": 0.0, "end": 0.4}, {"text": "two", "start": 0.4, "end": 0.8},
             {"text": "THREE", "start": 1.3, "end": 1.7}]
    m = direct.measure(x, RATE, words)
    assert m.pauses and m.pauses[0][0] == "two" and 0.4 <= m.pauses[0][1] <= 0.6
    assert "THREE" in m.emphasised
    assert 100 < m.f0_median_hz < 200
    assert m.words_per_sec > 0


def test_measure_handles_silence():
    m = direct.measure(np.zeros(RATE, dtype=np.float32), RATE, [])
    assert m.pauses == [] and m.words_per_sec == 0.0


def test_verify_ignores_tags():
    assert verify.similarity("[warm] রোজ জল খান… ভালো থাকুন।", "রোজ জল খান ভালো থাকুন") == 1.0
    assert verify.strip_tags("[quiet intensity] hi [soft] there") == "hi there"
