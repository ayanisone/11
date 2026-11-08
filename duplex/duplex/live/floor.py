"""The floor manager: decides, every few tens of milliseconds, what the agent does with its mouth.

It never touches audio or the network. Events come in (user VAD, live transcript, listener verdicts,
playback state); actions come out (backchannel, draft a reply, release it, cancel it, stop talking,
finish the user's sentence). That keeps every timing rule testable with a fake clock.

Signal path, in mixing terms: browser VAD is the sidechain key, the Claude listener is the detector that
decides what kind of moment this is, the Params are the compressor knobs, and a drafted reply sits behind
a gate that this class opens.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from typing import Optional

BACKCHANNEL_WORDS = {
    "mm", "mmm", "mhm", "hmm", "mmhmm", "uhhuh", "yeah", "yep", "yes", "ya", "right", "ok", "okay", "sure",
    "nice", "cool", "true", "haan", "han", "achha", "acha", "accha", "theek", "hai", "ji", "oh", "ah", "wow",
    "gotit", "got", "it", "exactly", "totally", "absolutely",
}


def words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def norm(w: str) -> str:
    return re.sub(r"[\W_]+", "", w.lower())


@dataclass
class Verdict:
    """What the listener thinks is happening in the user's turn right now."""

    state: str = "continuing"  # continuing | hesitating | finishing | done
    remaining_words: int = 3
    backchannel: str = "none"  # bank id, or none
    laugh: bool = False
    completion: str = ""
    based_on_words: int = 0  # how many words of the user's turn it had seen
    seq: int = 0


@dataclass
class Params:
    """The knobs. Defaults are a starting point; tune them live from the page."""

    bc_min_gap: float = 4.0  # s between backchannels
    bc_min_words: int = 5  # words the user must add before the next backchannel
    bc_pause: float = 0.18  # a pause this long invites a backchannel...
    laugh_min_gap: float = 4.0
    eot_done: float = 0.25  # ...and this much silence ends the turn when the listener says "done"
    eot_finishing: float = 0.45
    eot_unsure: float = 1.1  # when the listener thinks they're mid-thought
    eot_max: float = 1.8  # hard ceiling: never leave more dead air than this
    spec_start: float = 0.12  # start drafting a reply this far into a pause the listener calls done/finishing
    spec_unsure: float = 0.35  # ...or this far into any other pause (a dropped draft costs one short Claude + TTS call)
    overlap_start: bool = True  # allow starting before the user has finished (Dessa-style)
    overlap_min_talk: float = 1.0
    overlap_remaining: int = 1
    barge_min: float = 0.3  # user must talk this long over the agent before it considers stopping
    barge_hard: float = 1.0  # ...and after this long it stops whatever the words were
    completion_pause: float = 0.6  # a hesitation this long lets the agent finish the user's sentence
    completion_min_gap: float = 8.0
    stale_words: int = 3  # redraft if the user added this many words since the draft
    verdict_stale_words: int = 4  # ignore a verdict that missed this many words


@dataclass
class Action:
    kind: str  # backchannel | draft | release | cancel | stop | complete
    data: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"{self.kind}({', '.join(f'{k}={v!r}' for k, v in self.data.items())})"


@dataclass
class Draft:
    id: int
    user_text: str
    nwords: int
    ready: bool = False
    released: bool = False


class Floor:
    _ids = itertools.count(1)

    def __init__(self, params: Optional[Params] = None):
        self.p = params or Params()
        self.user_vad = False
        self.vad_t = 0.0  # time of the last VAD transition
        self.talk_start = 0.0
        self.words_at_talk_start = 0
        self.turn_open = False
        self.committed: list[str] = []
        self.partial = ""
        self._consumed = 0  # words of the current Scribe segment already handed to the brain
        self.verdict: Optional[Verdict] = None
        self._verdict_used: set[tuple[int, str]] = set()
        self.last_bc_t = -1e9
        self.bc_words_mark = 0
        self.last_laugh_t = -1e9
        self.last_completion_t = -1e9
        self._pause_acted: set[str] = set()  # things already done during the current pause
        self.agent_playing = False
        self.agent_text = ""  # what the agent is saying now (for the echo guard)
        self.draft: Optional[Draft] = None
        self.words_at_release: Optional[int] = None

    # ------------------------------------------------------------ events

    @property
    def user_text(self) -> str:
        return " ".join([*self.committed, self.partial]).strip()

    @property
    def nwords(self) -> int:
        return len(words(self.user_text))

    def on_vad(self, speaking: bool, t: float) -> None:
        if speaking == self.user_vad:
            return
        self.user_vad, self.vad_t = speaking, t
        if speaking:
            self.talk_start = t
            self.words_at_talk_start = self.nwords
            self._pause_acted.clear()
            if not self.turn_open and not self._agent_active:
                self.turn_open = True

    def _is_echo(self, text: str) -> bool:
        if not self._agent_active or not self.agent_text:
            return False
        heard = [norm(w) for w in words(text)][-6:]
        said = {norm(w) for w in words(self.agent_text)}
        return len(heard) >= 2 and sum(w in said for w in heard) / len(heard) >= 0.75

    def on_partial(self, text: str, t: float) -> None:
        if self._is_echo(text):
            return
        self.partial = " ".join(words(text)[self._consumed:])
        if self.partial and not self.turn_open and not self._agent_active:
            self.turn_open = True

    def on_committed(self, text: str, t: float) -> None:
        if self._is_echo(text):
            self._consumed = 0
            return
        rest = " ".join(words(text)[self._consumed:])
        self._consumed = 0
        self.partial = ""
        if rest:
            self.committed.append(rest)
            if not self.turn_open and not self._agent_active:
                self.turn_open = True

    def on_verdict(self, v: Verdict) -> None:
        self.verdict = v

    def on_playback(self, playing: bool, t: float) -> None:
        self.agent_playing = playing
        if not playing and self.draft and self.draft.released:
            self.draft = None
            self.agent_text = ""
            self.words_at_release = None
            # Anything said over the agent that didn't take the floor was a backchannel: drop it.
            said = [norm(w) for w in words(self.user_text)]
            if said and all(w in BACKCHANNEL_WORDS for w in said) and not self.user_vad:
                self._consumed += len(words(self.partial))
                self.committed, self.partial = [], ""
            elif said or self.user_vad:
                self.turn_open = True
                self._pause_acted.clear()

    def on_draft_ready(self, draft_id: int) -> None:
        if self.draft and self.draft.id == draft_id:
            self.draft.ready = True

    def on_backchannel_played(self, t: float) -> None:
        self.last_bc_t = t
        self.bc_words_mark = self.nwords

    # ------------------------------------------------------------ policy

    @property
    def _agent_active(self) -> bool:
        return self.agent_playing or bool(self.draft and self.draft.released)

    def _current_verdict(self) -> Optional[Verdict]:
        v = self.verdict
        if v is None or not 0 <= self.nwords - v.based_on_words < self.p.verdict_stale_words:
            return None
        return v

    def _eot(self, state: str) -> float:
        return {"done": self.p.eot_done, "finishing": self.p.eot_finishing}.get(state, self.p.eot_unsure)

    def _consume_turn(self) -> str:
        """Hand the user's words to the brain; later partials in the same Scribe segment skip them."""
        text = self.user_text
        self._consumed += len(words(self.partial))
        self.committed, self.partial = [], ""
        self.turn_open = False
        self.bc_words_mark = 0
        self.verdict = None  # a judgement of that turn says nothing about the next one
        return text

    def step(self, t: float) -> list[Action]:
        p, acts = self.p, []
        talking_for = t - self.talk_start if self.user_vad else 0.0
        silence = 0.0 if self.user_vad else t - self.vad_t

        # 1. The agent has the floor: only question is whether the user is taking it back.
        if self._agent_active:
            if self.user_vad and talking_for >= p.barge_min:
                new = [norm(w) for w in words(self.user_text)]
                only_backchannel = 0 < len(new) <= 3 and all(w in BACKCHANNEL_WORDS for w in new)
                if (new and not only_backchannel) or talking_for >= p.barge_hard:
                    acts.append(Action("stop", {"draft": self.draft.id if self.draft else None,
                                                "reason": "user took the floor"}))
                    self.draft, self.agent_text, self.agent_playing = None, "", False
                    self.turn_open, self.verdict = True, None
            return acts

        if not self.turn_open or self.nwords == 0:
            return acts

        v = self._current_verdict()
        state = v.state if v else "continuing"

        # 2. Laugh with them: overlaps are fine for laughs.
        if (v and v.laugh and (v.seq, "laugh") not in self._verdict_used and t - self.last_laugh_t >= p.laugh_min_gap
                and t - self.last_bc_t >= 1.0):
            self._verdict_used.add((v.seq, "laugh"))
            acts.append(Action("backchannel", {"id": "laugh"}))
            self.last_laugh_t = t
            self.on_backchannel_played(t)

        # 3. Backchannel into a micro-pause while they're mid-thought.
        if (not self.user_vad and p.bc_pause <= silence < self._eot(state) and "bc" not in self._pause_acted
                and state in ("continuing", "hesitating") and t - self.last_bc_t >= p.bc_min_gap
                and self.nwords - self.bc_words_mark >= p.bc_min_words):
            self._pause_acted.add("bc")
            choice = v.backchannel if v and v.backchannel not in ("none", "", "laugh") else "mm-hmm"
            acts.append(Action("backchannel", {"id": choice}))
            self.on_backchannel_played(t)

        # 4. Finish their sentence when they're searching for the words.
        if (v and state == "hesitating" and v.completion and not self.user_vad and silence >= p.completion_pause
                and "complete" not in self._pause_acted and t - self.last_completion_t >= p.completion_min_gap):
            self._pause_acted.add("complete")
            self.last_completion_t = t
            acts.append(Action("complete", {"text": v.completion}))

        # 5. Draft a reply early (behind the gate), redraft if they kept going.
        d = self.draft
        if d and not d.released and self.nwords - d.nwords >= p.stale_words:
            acts.append(Action("cancel", {"draft": d.id, "reason": "user kept talking"}))
            self.draft = d = None
        # Coming in early needs a verdict that has heard THIS stretch of speech: a "nearly done" from before
        # they paused says nothing about what they started saying after it.
        finishing_now = (p.overlap_start and self.user_vad and state == "finishing" and v is not None
                         and v.based_on_words > self.words_at_talk_start
                         and v.remaining_words <= p.overlap_remaining + 1 and talking_for >= p.overlap_min_talk)
        want = (not self.user_vad and silence >= (p.spec_start if state in ("done", "finishing") else p.spec_unsure)
                ) or finishing_now
        if d is None and want:
            d = self.draft = Draft(next(self._ids), self.user_text, self.nwords)
            acts.append(Action("draft", {"draft": d.id, "user_text": d.user_text}))

        # 6. Open the gate.
        if d and not d.released:
            eot_reached = not self.user_vad and (silence >= self._eot(state) or silence >= p.eot_max)
            overlap = (finishing_now and d.ready and v is not None and v.remaining_words <= p.overlap_remaining)
            if eot_reached or overlap:
                d.released = True
                self.words_at_release = self.nwords
                user_text = self._consume_turn()
                acts.append(Action("release", {"draft": d.id, "user_text": user_text,
                                               "gap_ms": int(-1 if overlap else silence * 1000),
                                               "overlap": overlap}))
        return acts
