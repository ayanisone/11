"""The floor manager's timing rules, driven with a fake clock."""

import pytest

from duplex.live.claude import clauses, merge_history, with_interjections
from duplex.live.floor import Floor, Params, Verdict


class Sim:
    """Fake clock + a Scribe-like transcript: partials grow within a segment, which commits after 0.6 s of
    silence unless speech resumes first."""

    COMMIT_AFTER = 0.6

    def __init__(self, **params):
        self.f = Floor(Params(**params))
        self.t = 0.0
        self.log = []
        self.seg = ""
        self.pending = None  # (time, text) of the next VAD commit

    def at(self, t):
        """Advance to t in 10 ms ticks, collecting actions."""
        while self.t < t - 1e-9:
            self.t = round(self.t + 0.01, 3)
            if self.pending and self.t >= self.pending[0]:
                self.f.on_committed(self.pending[1], self.t)
                self.pending, self.seg = None, ""
            for a in self.f.step(self.t):
                self.log.append((self.t, a))
                if a.kind == "draft":
                    self.f.on_draft_ready(a.data["draft"])  # TTS instantly ready in these tests
        return self

    def speak(self, text, start, end):
        self.at(start)
        self.pending = None  # speech resumed before Scribe committed: same segment keeps growing
        self.f.on_vad(True, start)
        base = self.seg.split()
        ws = text.split()
        for i in range(1, len(ws) + 1):
            self.at(start + (end - start) * i / len(ws))
            self.seg = " ".join(base + ws[:i])
            self.f.on_partial(self.seg, self.t)
        self.f.on_vad(False, end)
        self.pending = (end + self.COMMIT_AFTER, self.seg)
        return self

    def verdict(self, **kw):
        kw.setdefault("based_on_words", self.f.nwords)
        self.f.on_verdict(Verdict(seq=len(self.log) + int(self.t * 1000), **kw))
        return self

    def kinds(self, kind=None):
        return [(t, a) for t, a in self.log if kind is None or a.kind == kind]


def test_done_turn_released_quickly():
    s = Sim().speak("what do you think of the dad idea", 0.0, 2.0).verdict(state="done", remaining_words=0)
    s.at(3.0)
    (t, rel), = s.kinds("release")
    assert t == pytest.approx(2.0 + 0.25, abs=0.011)
    assert rel.data["user_text"] == "what do you think of the dad idea"
    assert s.kinds("draft")[0][0] < t  # drafted before the gate opened


def test_mid_thought_pause_waits_and_backchannels():
    s = Sim().speak("so we open on the dad in the kitchen and", 0.0, 3.0).verdict(state="continuing",
                                                                                     backchannel="haan")
    s.at(3.5)
    assert not s.kinds("release")
    (t, bc), = s.kinds("backchannel")
    assert bc.data["id"] == "haan" and t == pytest.approx(3.18, abs=0.011)
    s.at(4.5)
    (t, _), = s.kinds("release")  # nothing more came: hard ceiling-ish wait for an unsure turn
    assert t == pytest.approx(3.0 + 1.1, abs=0.011)


def test_backchannel_spacing_and_word_budget():
    s = Sim(bc_min_gap=4.0, eot_unsure=5.0, eot_max=9.0)
    s.speak("one two three four five six", 0.0, 2.0).verdict(state="continuing")
    s.speak("seven eight nine ten eleven twelve", 2.5, 4.0).verdict(state="continuing")
    s.speak("thirteen fourteen fifteen sixteen seventeen", 4.5, 6.5).verdict(state="continuing")
    s.at(7.0)
    times = [t for t, _ in s.kinds("backchannel")]
    assert times == pytest.approx([2.18, 6.68], abs=0.011)  # 4.18 skipped: too soon after the first


def test_user_resuming_cancels_a_stale_draft():
    s = Sim().speak("I was thinking we could", 0.0, 1.5).verdict(state="finishing", remaining_words=1)
    s.at(1.7)
    assert len(s.kinds("draft")) == 1 and not s.kinds("release")  # drafted at 0.12 s, gate held to 0.45 s
    s.speak("shoot it all in one take on a phone", 1.75, 4.0)  # resumes after the listener said "finishing"
    s.at(4.1)
    assert s.kinds("cancel")
    assert not [a for _, a in s.kinds("release") if a.data["draft"] == s.kinds("draft")[0][1].data["draft"]]


def test_overlap_start_before_they_finish():
    s = Sim()
    s.at(0.0)
    s.f.on_vad(True, 0.0)
    for i, w in enumerate("so the twist is the kid saves the dinner".split(), 1):
        s.at(i * 0.3)
        s.f.on_partial(" ".join("so the twist is the kid saves the dinner".split()[:i]), s.t)
    s.verdict(state="finishing", remaining_words=1)
    s.at(3.0)  # still talking: VAD never went off
    (t, rel), = s.kinds("release")
    assert rel.data["overlap"] is True and t < 3.0


def test_backchannel_over_agent_does_not_stop_it_but_words_do():
    s = Sim().speak("pitch me something", 0.0, 1.0).verdict(state="done", remaining_words=0)
    s.at(1.5)
    s.f.on_playback(True, 1.5)
    s.speak("yeah", 2.0, 2.4)
    s.at(2.6)
    assert not s.kinds("stop")
    s.speak("wait wait what if", 3.0, 3.6)
    s.at(3.7)
    assert s.kinds("stop")


def test_long_talkover_stops_even_without_words():
    s = Sim().speak("go on", 0.0, 0.6).verdict(state="done", remaining_words=0)
    s.at(1.0)
    s.f.on_playback(True, 1.0)
    s.at(1.2)
    s.f.on_vad(True, 1.2)
    s.at(2.3)
    (t, _), = s.kinds("stop")
    assert t == pytest.approx(1.2 + 1.0, abs=0.011)


def test_echo_of_agent_is_ignored():
    s = Sim().speak("pitch me something", 0.0, 1.0).verdict(state="done", remaining_words=0)
    s.at(1.5)
    s.f.on_playback(True, 1.5)
    s.f.agent_text = "Okay so picture a dad who cannot cook at all"
    s.f.on_vad(True, 1.6)
    s.f.on_partial("a dad who cannot cook", 1.7)
    s.at(2.0)
    assert not s.kinds("stop")


def test_completion_offered_on_hesitation():
    s = Sim(bc_min_gap=99).speak("and the hostel was in the", 0.0, 2.0)
    s.verdict(state="hesitating", completion="wrong Goa?")
    s.at(2.7)
    (t, c), = s.kinds("complete")
    assert c.data["text"] == "wrong Goa?" and t == pytest.approx(2.6, abs=0.011)


def test_backchannel_words_said_over_agent_are_dropped_after_it_finishes():
    s = Sim().speak("pitch me something", 0.0, 1.0).verdict(state="done", remaining_words=0)
    s.at(1.5)
    s.f.on_playback(True, 1.5)
    s.speak("mm-hmm", 2.0, 2.3)
    s.f.on_playback(False, 4.0)
    assert s.f.user_text == "" and not s.f.turn_open


def test_scribe_segment_words_are_not_double_counted_after_release():
    f = Floor()
    f.on_vad(True, 0.0)
    f.on_partial("so the idea is", 0.5)
    f.on_vad(False, 1.0)
    f.on_verdict(Verdict(state="done", remaining_words=0, based_on_words=4))
    for i in range(1, 40):
        for a in f.step(1.0 + i * 0.01):
            if a.kind == "draft":
                f.on_draft_ready(a.data["draft"])
    assert f.draft and f.draft.released
    f.on_playback(True, 1.5)
    f.on_partial("so the idea is wait", 1.6)  # same Scribe segment keeps growing
    assert f.user_text == "wait"
    f.on_committed("so the idea is wait no", 2.0)
    assert f.user_text == "wait no"


async def test_clause_splitter_sends_first_clause_early():
    async def deltas():
        for d in ["Oh, ", "that's ", "good. ", "The dad ", "and the rangoli— ", "love it", "."]:
            yield d
    got = [c async for c in clauses(deltas())]
    assert got == ["Oh, that's good.", "The dad and the rangoli—", "love it."]


def test_history_alternates_and_interjections_are_spliced():
    h = []
    merge_history(h, "user", "hi")
    merge_history(h, "user", "there")
    merge_history(h, "assistant", "hey")
    assert h == [{"role": "user", "content": "hi there"}, {"role": "assistant", "content": "hey"}]
    assert with_interjections("the hostel was in the", [(5, "wrong Goa?")]) == \
        "the hostel was in the [you said: wrong Goa?]"


def test_old_verdict_does_not_leak_into_the_next_turn():
    s = Sim().speak("and the dog walks right through it, what do you think?", 0.0, 3.0)
    s.verdict(state="done", remaining_words=0, laugh=True)
    s.at(3.5)
    assert s.kinds("release")
    s.f.on_playback(True, 3.6)
    s.speak("wait wait what if it's the grandma", 4.0, 5.5)
    s.at(5.6)
    assert s.kinds("stop")
    laughs = [t for t, a in s.kinds("backchannel") if a.data["id"] == "laugh"]
    assert all(t < 3.5 for t in laughs)
    assert s.f.verdict is None
