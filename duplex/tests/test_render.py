"""End-to-end render with the ElevenLabs call faked: exercises caching, alignment parsing, stems, cue sheet."""

import csv
import json
from pathlib import Path

import numpy as np

from duplex import eleven
from duplex.render import render
from duplex.score import Score
from duplex.timeline import read_wav

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "goa_trip_30s.json"


def fake_tts(calls):
    def tts(text, voice_id, *, model_id, output_format="pcm_44100", previous_text=None, next_text=None, seed=None,
            language_code=None, voice_settings=None):
        calls.append((text, previous_text))
        rate = eleven.pcm_rate(output_format)
        chars, starts, ends, t = [], [], [], 0.08
        for c in text:  # tags take no time, every other char 55 ms
            chars.append(c)
            dur = 0.0 if c in "[]" or (starts and chars.count("[") > chars.count("]")) else 0.055
            starts.append(t)
            ends.append(t + dur)
            t += dur
        n = int((t + 0.15) * rate)
        audio = (np.random.default_rng(len(text)).standard_normal(n) * 0.05).astype(np.float32)
        return audio, rate, {"characters": chars, "character_start_times_seconds": starts,
                             "character_end_times_seconds": ends}
    return tts


def test_example_renders_and_caches(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(eleven, "tts_with_timestamps", fake_tts(calls))
    score = Score.model_validate_json(EXAMPLE.read_text())
    report = render(score, tmp_path, voices={}, output_format="pcm_24000")

    assert len(calls) == len(score.lines)
    assert calls[1][1] is not None  # previous line sent as context
    assert not report["warnings"], report["warnings"]  # no self-overlap, no untagged overlaps, all cuts land
    stats = report["stats"]
    assert stats["backchannels"] == 3 and stats["changes_with_overlap_share"] > 0

    mix, rate = read_wav(tmp_path / "mix.wav")
    a, _ = read_wav(tmp_path / "stems" / "A.wav")
    b, _ = read_wav(tmp_path / "stems" / "B.wav")
    assert rate == 24000 and len(mix) == len(a) == len(b)
    np.testing.assert_allclose(a + b, mix, atol=1e-5)

    rows = list(csv.DictReader(open(tmp_path / "cues.csv")))
    assert {r["id"] for r in rows} == {l.id for l in score.lines}
    assert next(r for r in rows if r["id"] == "l3")["cut_off"] == "yes"  # B's l4 cuts A off

    render(score, tmp_path, voices={}, output_format="pcm_24000")  # re-time / re-render: all from cache
    assert len(calls) == len(score.lines)
    assert json.loads((tmp_path / "report.json").read_text())["stats"] == stats


def test_tag_lint_flags_untagged_overlap_and_hyphens(tmp_path, monkeypatch):
    monkeypatch.setattr(eleven, "tts_with_timestamps", fake_tts([]))
    score = Score.model_validate({
        "title": "t", "speakers": [{"speaker": "A", "casting": "x", "voice_id": "a"},
                                   {"speaker": "B", "casting": "y", "voice_id": "b"}],
        "lines": [{"id": "l1", "speaker": "A", "text": "[high-pitched] so we went all the way there"},
                  {"id": "l2", "speaker": "B", "text": "and it rained",
                   "start": {"ref": "l1", "at": "end", "offset_ms": -400}}]})
    warnings = render(score, tmp_path, voices={}, output_format="pcm_24000")["warnings"]
    assert any("hyphen" in w for w in warnings)
    assert any(w.startswith("l2: starts over l1") for w in warnings)
