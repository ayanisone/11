from bn_dub.transcribe import Word, segment_words


def w(text, start, end, speaker="A"):
    return Word(text=text, start=start, end=end, speaker=speaker)


def test_splits_on_speaker_change_and_long_gap():
    words = [w("Hello", 0.0, 0.3), w("there.", 0.35, 0.6), w("Hi.", 0.7, 0.9, "B"),
             w("Long", 3.0, 3.2, "B"), w("pause.", 3.25, 3.5, "B")]
    segs = segment_words(words, max_secs=12, max_chars=220, split_gap=0.6)
    assert [s.source_text for s in segs] == ["Hello there.", "Hi.", "Long pause."]
    assert [s.speaker for s in segs] == ["A", "B", "B"]
    assert segs[0].start == 0.0 and segs[0].end == 0.6
    assert [s.id for s in segs] == [1, 2, 3]


def test_splits_when_too_long_preferring_sentence_end():
    words = []
    t = 0.0
    for i in range(30):
        text = "word." if i % 5 == 4 else "word"
        words.append(w(text, t, t + 0.4))
        t += 0.5
    segs = segment_words(words, max_secs=6.0, max_chars=1000, split_gap=5.0)
    assert all(s.duration <= 6.0 + 1e-9 for s in segs)
    assert all(s.source_text.endswith(".") for s in segs[:-1])


def test_empty():
    assert segment_words([]) == []


def test_fold_minor_speakers_merges_fragments_into_main():
    from bn_dub.transcribe import fold_minor_speakers
    words = [w("a", 0, 4, "A"), w("b.", 4.1, 8, "A"), w("x", 9, 10, "B"), w("c", 11, 14, "A"),
             w("y", 15, 16.5, "C"), w("long", 18, 24, "D")]
    segs = fold_minor_speakers(segment_words(words, split_gap=0.6))
    assert {s.speaker for s in segs} == {"A", "D"}  # B and C had < 5 s each; D has 6 s and stays


def test_fold_minor_speakers_single_speaker_untouched():
    from bn_dub.transcribe import fold_minor_speakers
    segs = fold_minor_speakers(segment_words([w("a", 0, 1, "A")]))
    assert [s.speaker for s in segs] == ["A"]
