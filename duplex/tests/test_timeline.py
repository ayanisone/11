import numpy as np
import pytest

from duplex.analyze import analyze, segment, to_score, words_from_scribe
from duplex.score import Anchor, Line, Score, SpeakerSpec
from duplex.timeline import (Clip, Word, conversation_stats, find_phrase, mixdown, place, read_wav,
                             spans_from_timeline, strip_tags, words_from_chars, write_wav)

RATE = 1000


def fake_clip(text: str, lead: float = 0.1, word: float = 0.3, gap: float = 0.05, tail: float = 0.2) -> Clip:
    toks = strip_tags(text).split()
    words, t = [], lead
    for tok in toks:
        words.append(Word(tok, round(t, 6), round(t + word, 6)))
        t += word + gap
    n = int(round((t - gap + tail) * RATE))
    audio = np.zeros(n, dtype=np.float32)
    for w in words:
        audio[int(w.start * RATE):int(w.end * RATE)] = 0.1
    return Clip(audio, RATE, words)


def line(id, spk, text, **kw):
    return Line(id=id, speaker=spk, text=text, **kw)


def run(lines):
    return place(lines, {l.id: fake_clip(l.text) for l in lines})


def test_first_line_lands_on_preroll_and_default_gap_follows():
    tl = run([line("l1", "A", "one two three"), line("l2", "B", "four five")])
    a, b = tl.placed["l1"], tl.placed["l2"]
    assert a.offset == pytest.approx(0.5)  # preroll is measured to the first sample of the earliest clip
    assert a.onset == pytest.approx(0.6)
    assert b.onset == pytest.approx(a.speech_end + 0.2)


def test_negative_offset_overlaps_the_tail():
    tl = run([line("l1", "A", "one two three"),
              line("l2", "B", "yes exactly", start=Anchor(ref="l1", at="end", offset_ms=-250))])
    assert tl.placed["l2"].onset == pytest.approx(tl.placed["l1"].speech_end - 0.25)


def test_word_anchor_hits_the_word_and_occurrence():
    tl = run([line("l1", "A", "so the trip, the trip to Goa"),
              line("b1", "B", "mm", kind="backchannel",
                   start=Anchor(ref="l1", at="word", word="trip", occurrence=2, edge="end", offset_ms=100))])
    a = tl.placed["l1"]
    second_trip = [w for w in a.clip.words if w.text.startswith("trip")][1]
    assert tl.placed["b1"].onset == pytest.approx(a.offset + second_trip.end + 0.1)


def test_interrupt_cuts_at_next_word_boundary():
    lines = [line("l1", "A", "last time Rohan booked the wrong place entirely"),
             line("l2", "B", "a hostel in Goa", interrupts=True, yield_ms=150,
                  start=Anchor(ref="l1", at="word", word="booked", edge="end", offset_ms=50))]
    tl = run(lines)
    a, b = tl.placed["l1"], tl.placed["l2"]
    first_after = next(w for w in a.clip.words if a.offset + w.end >= b.onset + 0.15)
    assert first_after.text == "the"
    assert a.cut_at == pytest.approx(a.offset + first_after.end + 0.03)
    assert a.speech_end == pytest.approx(a.cut_at)
    assert not tl.warnings


def test_interrupt_on_last_word_warns_and_does_not_cut():
    tl = run([line("l1", "A", "one two"),
              line("l2", "B", "three", interrupts=True, start=Anchor(ref="l1", at="word", word="two"))])
    assert tl.placed["l1"].cut_at is None
    assert any("no cut" in w for w in tl.warnings)


def test_self_overlap_is_flagged():
    tl = run([line("l1", "A", "one two three"),
              line("l2", "A", "four", start=Anchor(ref="l1", at="start", offset_ms=100))])
    assert any("talks over themselves" in w for w in tl.warnings)


def test_mixdown_stems_sum_to_mix_and_cut_is_silent():
    lines = [line("l1", "A", "last time Rohan booked the wrong place entirely"),
             line("l2", "B", "a hostel", interrupts=True, yield_ms=150,
                  start=Anchor(ref="l1", at="word", word="booked", edge="end", offset_ms=50))]
    tl = run(lines)
    stems, mix, rate, gain = mixdown(tl, fade_ms=40)
    assert gain == 1.0
    np.testing.assert_allclose(stems["A"] + stems["B"], mix, atol=1e-6)
    after_cut = int((tl.placed["l1"].cut_at + 0.05) * rate)
    assert np.all(stems["A"][after_cut:] == 0)


def test_mix_safety_gain_applies_to_stems_too():
    lines = [line("l1", "A", "one two three"),
             line("l2", "B", "four five", start=Anchor(ref="l1", at="start", offset_ms=0), gain_db=20)]
    stems, mix, _, gain = mixdown(run(lines))
    assert gain < 1.0
    assert np.max(np.abs(mix)) == pytest.approx(10 ** (-1 / 20), rel=1e-4)
    np.testing.assert_allclose(stems["A"] + stems["B"], mix, atol=1e-6)


def test_words_from_chars_drops_tags():
    text = "[laughs softly] Hi there, Goa!"
    chars = list(text)
    starts = [i * 0.01 for i in range(len(chars))]
    ends = [s + 0.01 for s in starts]
    words = words_from_chars(chars, starts, ends)
    assert [w.text for w in words] == ["Hi", "there,", "Goa!"]
    assert words[0].start == pytest.approx(text.index("Hi") * 0.01)


def test_find_phrase_normalises_and_fuzzes():
    words = [Word(t, i, i + 0.5) for i, t in enumerate(["The", "colour,", "of", "Goa's", "sea"])]
    assert find_phrase(words, "colour")[0].text == "colour,"
    assert find_phrase(words, "of goas")[1].text == "Goa's"
    assert find_phrase(words, "color")[0].text == "colour,"
    assert find_phrase(words, "Mumbai") is None


def test_wav_roundtrip_24bit(tmp_path):
    x = (np.sin(np.linspace(0, 40, 4800)) * 0.5).astype(np.float32)
    write_wav(tmp_path / "a.wav", x, 48000, 24)
    y, rate = read_wav(tmp_path / "a.wav")
    assert rate == 48000
    np.testing.assert_allclose(x, y, atol=2e-7)


def test_score_rejects_forward_anchor():
    with pytest.raises(ValueError):
        Score(title="t", speakers=[SpeakerSpec(speaker="A", casting="x")],
              lines=[Line(id="l1", speaker="A", text="hi", start=Anchor(ref="l2")),
                     Line(id="l2", speaker="A", text="yo")])


# ------------------------------------------------------------ analysis


def scribe_payload(turns):
    """turns: [(speaker, start, [word, ...])] with 0.3 s words and 0.05 s gaps."""
    words = []
    for spk, t, toks in turns:
        for tok in toks:
            words.append({"text": tok, "start": t, "end": t + 0.3, "type": "word", "speaker_id": spk})
            words.append({"text": " ", "start": t + 0.3, "end": t + 0.35, "type": "spacing", "speaker_id": spk})
            t += 0.35
    return {"words": words}


REFERENCE = [
    ("speaker_0", 0.0, "so we drove all the way to Lonavala and".split()),
    ("speaker_1", 1.2, ["mm-hmm"]),
    ("speaker_0", 3.15, "it rained the whole".split()),
    ("speaker_1", 3.9, "the whole weekend right".split()),  # starts before speaker_0 finishes
    ("speaker_0", 5.8, "exactly".split()),
]


def test_segment_finds_backchannel_and_merges_floor():
    turns = segment(words_from_scribe(scribe_payload(REFERENCE)))
    kinds = [(t.speaker, t.kind) for t in turns]
    assert kinds == [("speaker_0", "line"), ("speaker_1", "backchannel"), ("speaker_1", "line"),
                     ("speaker_0", "line")]
    assert turns[0].text.endswith("the whole")  # the two speaker_0 stretches around the mm-hmm became one turn


def test_stats_report_overlap_and_backchannels():
    stats, _ = analyze(scribe_payload(REFERENCE))
    assert stats["backchannels"] == 1
    assert stats["speaker_changes"] == 2
    assert stats["changes_with_overlap_share"] == 0.5
    assert stats["overlapped_seconds"] > 0


def test_lifted_score_reproduces_reference_timing():
    _, turns = analyze(scribe_payload(REFERENCE))
    score = to_score(turns)
    clips = {l.id: fake_clip(l.text, lead=0.1, word=0.3, gap=0.05) for l in score.lines}
    tl = place(score.lines, clips, preroll=0.0)
    starts = [s.start for s in spans_from_timeline(tl)]
    got = [round(x - starts[0], 3) for x in starts]
    want = [round(t.start - turns[0].start, 3) for t in turns]
    assert want == [0.0, 1.2, 3.9, 5.8]
    assert got == pytest.approx(want, abs=1e-3)
    stats = conversation_stats(spans_from_timeline(tl))
    assert stats["backchannels"] == 1
