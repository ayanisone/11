"""Reference-track analysis: measure how a real two-person recording takes turns, and lift its timing into a score.

Feed it a Dessa demo, a podcast clip, or two actors improvising on a phone. You get the turn-taking
fingerprint (gaps, overlaps, backchannel rate) and, optionally, an overlap score that re-creates the same
timing with any voices.
"""

from __future__ import annotations

from dataclasses import dataclass

from .score import Anchor, Line, Score, SpeakerSpec
from .timeline import Span, conversation_stats, norm


@dataclass
class SWord:
    text: str
    start: float
    end: float
    speaker: str


def words_from_scribe(payload: dict) -> list[SWord]:
    out = []
    for w in payload.get("words", []):
        if w.get("type", "word") != "word" or w.get("start") is None or w.get("end") is None:
            continue
        out.append(SWord(w["text"].strip(), float(w["start"]), float(w["end"]), w.get("speaker_id") or "speaker_0"))
    return sorted(out, key=lambda w: w.start)


@dataclass
class Turn:
    speaker: str
    words: list[SWord]
    kind: str = "line"

    @property
    def start(self) -> float:
        return self.words[0].start

    @property
    def end(self) -> float:
        return self.words[-1].end

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


def segment(words: list[SWord], *, split_gap: float = 1.0, bc_max_words: int = 3, bc_max_secs: float = 1.2,
            merge_gap: float = 1.5, slack: float = 0.3) -> list[Turn]:
    """Words -> turns and backchannels.

    Words are grouped per speaker first (a speaker's stretch runs while their own pauses stay under
    `split_gap`), so overlapping speech whose words interleave in time doesn't shred either side into
    fragments. A short stretch (<= bc_max_words, <= bc_max_secs) that sits inside a longer stretch of
    another speaker is a backchannel: the floor never changed hands.
    """
    stretches: list[Turn] = []
    open_: dict[str, Turn] = {}
    for w in sorted(words, key=lambda w: w.start):
        cur = open_.get(w.speaker)
        if cur is not None and w.start - cur.end <= split_gap:
            cur.words.append(w)
        else:
            cur = Turn(w.speaker, [w])
            stretches.append(cur)
            open_[w.speaker] = cur
    stretches.sort(key=lambda t: t.start)
    for s in stretches:
        if len(s.words) <= bc_max_words and s.end - s.start <= bc_max_secs and any(
                o.speaker != s.speaker and len(o.words) > len(s.words) and o.start < s.start <= s.end <= o.end + slack
                for o in stretches):
            s.kind = "backchannel"
    lines: list[Turn] = []
    for s in stretches:
        if s.kind != "line":
            continue
        if lines and lines[-1].speaker == s.speaker and s.start - lines[-1].end <= merge_gap:
            lines[-1].words.extend(s.words)
        else:
            lines.append(s)
    return sorted(lines + [s for s in stretches if s.kind == "backchannel"], key=lambda t: t.start)


def spans(turns: list[Turn]) -> list[Span]:
    return [Span(f"t{i + 1}", t.speaker, t.start, t.end, t.kind, t.text) for i, t in enumerate(turns)]


def _word_anchor(ref_id: str, ref: Turn, t: float) -> Anchor:
    """Anchor on the last word of `ref` that starts at or before t."""
    idx = max([i for i, w in enumerate(ref.words) if w.start <= t] or [0])
    w = ref.words[idx]
    occ = sum(1 for x in ref.words[: idx + 1] if norm(x.text) == norm(w.text))
    return Anchor(ref=ref_id, at="word", word=w.text, occurrence=occ, edge="start",
                  offset_ms=int(round((t - w.start) * 1000)))


def to_score(turns: list[Turn], title: str = "Lifted from reference") -> Score:
    """Re-express the reference's timing as anchors so it survives being re-voiced."""
    speakers = sorted({t.speaker for t in turns})
    keys = {s: chr(ord("A") + i) for i, s in enumerate(speakers)}
    ids: list[str] = []
    lines: list[Line] = []
    n_line = n_bc = 0
    for i, t in enumerate(turns):
        if t.kind == "backchannel":
            n_bc += 1
            lid = f"b{n_bc}"
        else:
            n_line += 1
            lid = f"l{n_line}"
        anchor = None
        if i:
            # the most recent line (not backchannel) still sounding when this starts, else the last one to end
            prior = [(j, turns[j]) for j in range(i) if turns[j].kind == "line"] or [(i - 1, turns[i - 1])]
            live = [(j, p) for j, p in prior if p.start <= t.start < p.end and p.speaker != t.speaker]
            if live:
                j, p = live[-1]
                anchor = _word_anchor(ids[j], p, t.start)
            else:
                j, p = max(prior, key=lambda jp: jp[1].end)
                anchor = Anchor(ref=ids[j], at="end", offset_ms=int(round((t.start - p.end) * 1000)))
        lines.append(Line(id=lid, speaker=keys[t.speaker], text=t.text, kind=t.kind, start=anchor,
                          gain_db=-6.0 if t.kind == "backchannel" else 0.0))
        ids.append(lid)
    return Score(title=title, speakers=[SpeakerSpec(speaker=keys[s], casting=f"as heard in reference ({s})")
                                        for s in speakers], lines=lines)


def analyze(payload: dict) -> tuple[dict, list[Turn]]:
    turns = segment(words_from_scribe(payload))
    return conversation_stats(spans(turns)), turns
