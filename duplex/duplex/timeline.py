"""Pure timeline maths: words from alignments, anchor resolution, interruptions, stems, mix, stats.

Nothing in here talks to an API, so all of it is unit-testable with synthetic clips.
"""

from __future__ import annotations

import difflib
import re
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

import numpy as np

from .score import Line

TAG_RE = re.compile(r"\[[^\]]*\]")


# ---------------------------------------------------------------- words


@dataclass
class Word:
    text: str
    start: float  # seconds, relative to clip start
    end: float


def strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", text)).strip()


def norm(token: str) -> str:
    return re.sub(r"[\W_]+", "", token.lower())


def words_from_chars(chars: list[str], starts: list[float], ends: list[float]) -> list[Word]:
    """Character-level alignment (as returned by TTS /with-timestamps) -> words, audio tags dropped."""
    keep = [True] * len(chars)
    depth = 0
    for i, c in enumerate(chars):
        if c == "[":
            depth += 1
        if depth:
            keep[i] = False
        if c == "]" and depth:
            depth -= 1
    words: list[Word] = []
    cur: list[int] = []

    def flush() -> None:
        if cur:
            text = "".join(chars[j] for j in cur)
            if norm(text):
                words.append(Word(text=text, start=float(starts[cur[0]]), end=float(ends[cur[-1]])))
            cur.clear()

    for i, c in enumerate(chars):
        if not keep[i] or c.isspace():
            flush()
        else:
            cur.append(i)
    flush()
    return words


def estimate_words(text: str, speech_start: float, speech_end: float) -> list[Word]:
    """Last-resort alignment: spread words over the speech span in proportion to their length."""
    toks = [t for t in strip_tags(text).split() if norm(t)]
    if not toks:
        return []
    weights = np.array([len(t) + 1 for t in toks], dtype=float)
    edges = speech_start + np.concatenate([[0], np.cumsum(weights)]) / weights.sum() * (speech_end - speech_start)
    return [Word(t, float(a), float(b)) for t, a, b in zip(toks, edges[:-1], edges[1:])]


def find_phrase(words: list[Word], phrase: str, occurrence: int = 1) -> Optional[tuple[Word, Word]]:
    """First/last word of the n-th occurrence of `phrase` in `words` (normalised match, fuzzy fallback)."""
    target = [norm(t) for t in strip_tags(phrase).split() if norm(t)]
    if not target:
        return None
    normed = [norm(w.text) for w in words]
    hits = [i for i in range(len(words) - len(target) + 1) if normed[i:i + len(target)] == target]
    if len(hits) >= occurrence:
        i = hits[occurrence - 1]
        return words[i], words[i + len(target) - 1]
    if len(target) == 1 and occurrence == 1:  # tolerate small spelling drift ("colour" vs "color")
        best = difflib.get_close_matches(target[0], normed, n=1, cutoff=0.75)
        if best:
            w = words[normed.index(best[0])]
            return w, w
    return None


# ---------------------------------------------------------------- clips & placement


@dataclass
class Clip:
    audio: np.ndarray  # float32 mono, -1..1
    rate: int
    words: list[Word]

    @property
    def duration(self) -> float:
        return len(self.audio) / self.rate

    def speech_bounds(self) -> tuple[float, float]:
        if self.words:
            return self.words[0].start, self.words[-1].end
        return energy_bounds(self.audio, self.rate)


def energy_bounds(audio: np.ndarray, rate: int, threshold_db: float = -40.0) -> tuple[float, float]:
    """Where sound starts/stops (for word-less clips like '[laughs]'), from 10 ms RMS frames."""
    hop = max(1, rate // 100)
    n = len(audio) // hop
    if n == 0:
        return 0.0, len(audio) / rate
    frames = audio[: n * hop].reshape(n, hop)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1) + 1e-12)
    loud = np.nonzero(20 * np.log10(rms) > threshold_db)[0]
    if len(loud) == 0:
        return 0.0, len(audio) / rate
    return loud[0] * hop / rate, (loud[-1] + 1) * hop / rate


@dataclass
class Placed:
    line: Line
    clip: Clip
    offset: float  # timeline time of the clip's first sample
    cut_at: Optional[float] = None  # timeline time where an interrupter shut this line down

    @property
    def onset(self) -> float:
        return self.offset + self.clip.speech_bounds()[0]

    @property
    def speech_end(self) -> float:
        end = self.offset + self.clip.speech_bounds()[1]
        return min(end, self.cut_at) if self.cut_at is not None else end

    def word_at(self, w: Word, edge: str) -> float:
        return self.offset + (w.start if edge == "start" else w.end)


@dataclass
class Timeline:
    placed: dict[str, Placed]
    warnings: list[str] = field(default_factory=list)

    @property
    def order(self) -> list[Placed]:
        return sorted(self.placed.values(), key=lambda p: p.onset)


def place(lines: list[Line], clips: dict[str, Clip], *, default_gap: float = 0.2, preroll: float = 0.5,
          cut_tail: float = 0.03) -> Timeline:
    """Resolve every line's anchor into an absolute position; apply interruptions."""
    tl = Timeline(placed={})
    for i, line in enumerate(lines):
        clip = clips[line.id]
        onset_rel = clip.speech_bounds()[0]
        a = line.start
        if a is None:
            t = 0.0 if i == 0 else tl.placed[lines[i - 1].id].speech_end + default_gap
        else:
            ref = tl.placed[a.ref]
            if a.at == "end":
                base = ref.speech_end
            elif a.at == "start":
                base = ref.onset
            else:
                hit = find_phrase(ref.clip.words, a.word or "", a.occurrence)
                if hit is None:
                    have = " ".join(w.text for w in ref.clip.words)
                    raise ValueError(f"line {line.id}: word {a.word!r} (#{a.occurrence}) not found in {a.ref}: {have!r}")
                w = hit[0] if a.edge == "start" else hit[1]
                base = ref.word_at(w, a.edge)
                if ref.cut_at is not None and base > ref.cut_at:
                    tl.warnings.append(f"{line.id}: anchor word {a.word!r} in {a.ref} falls after {a.ref} was cut off")
            t = base + a.offset_ms / 1000.0
        p = Placed(line=line, clip=clip, offset=t - onset_rel)
        tl.placed[line.id] = p

        if line.interrupts and a is not None:
            target = tl.placed[a.ref]
            cutoff = p.onset + line.yield_ms / 1000.0
            later = [w for w in target.clip.words if target.offset + w.end >= cutoff]
            if not later or target.offset + later[0].end >= target.speech_end - 1e-6:
                tl.warnings.append(f"{line.id}: interrupts {a.ref}, but {a.ref} is already finishing there; no cut")
            else:
                target.cut_at = target.offset + later[0].end + cut_tail

    _check_self_overlap(tl)
    lead = min(p.offset for p in tl.placed.values())
    shift = preroll - lead
    for p in tl.placed.values():
        p.offset += shift
        if p.cut_at is not None:
            p.cut_at += shift
    return tl


def _check_self_overlap(tl: Timeline, tolerance: float = 0.05) -> None:
    by_speaker: dict[str, list[Placed]] = {}
    for p in tl.placed.values():
        by_speaker.setdefault(p.line.speaker, []).append(p)
    for spk, ps in by_speaker.items():
        ps.sort(key=lambda p: p.onset)
        for a, b in zip(ps, ps[1:]):
            if b.onset < a.speech_end - tolerance:
                tl.warnings.append(f"speaker {spk} talks over themselves: {a.line.id} and {b.line.id} "
                                   f"overlap by {(a.speech_end - b.onset) * 1000:.0f} ms")


# ---------------------------------------------------------------- mixdown


def db_to_gain(db: float) -> float:
    return float(10 ** (db / 20))


def mixdown(tl: Timeline, *, tail: float = 0.6, fade_ms: float = 40.0, ceiling_db: float = -1.0
            ) -> tuple[dict[str, np.ndarray], np.ndarray, int, float]:
    """Sum each speaker onto their own stem; mix = sum of stems. Stems and mix share one safety gain."""
    rates = {p.clip.rate for p in tl.placed.values()}
    if len(rates) != 1:
        raise ValueError(f"clips have different sample rates: {sorted(rates)}")
    rate = rates.pop()
    end = max((p.cut_at + fade_ms / 1000 if p.cut_at else p.offset + p.clip.duration) for p in tl.placed.values())
    n = int(np.ceil((end + tail) * rate))
    stems: dict[str, np.ndarray] = {}
    for p in tl.placed.values():
        audio = p.clip.audio.astype(np.float32) * db_to_gain(p.line.gain_db)
        if p.cut_at is not None:
            cut = int(round((p.cut_at - p.offset) * rate))
            fade = int(round(fade_ms / 1000 * rate))
            audio = audio[: cut + fade].copy()
            ramp = np.linspace(1.0, 0.0, len(audio) - cut, dtype=np.float32)
            audio[cut:] *= ramp
        start = int(round(p.offset * rate))
        stem = stems.setdefault(p.line.speaker, np.zeros(n, dtype=np.float32))
        stem[start:start + len(audio)] += audio[: max(0, n - start)]
    mix = np.sum(list(stems.values()), axis=0)
    peak = float(np.max(np.abs(mix))) if len(mix) else 0.0
    ceiling = db_to_gain(ceiling_db)
    gain = ceiling / peak if peak > ceiling else 1.0
    if gain != 1.0:
        mix *= gain
        for s in stems.values():
            s *= gain
    return stems, mix, rate, gain


def write_wav(path: Path, audio: np.ndarray, rate: int, bits: int = 24) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.clip(audio, -1.0, 1.0 - 1e-7)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setframerate(rate)
        if bits == 16:
            w.setsampwidth(2)
            w.writeframes((x * 32767).round().astype("<i2").tobytes())
        elif bits == 24:
            w.setsampwidth(3)
            i32 = (x * 8388607).round().astype("<i4")
            w.writeframes(i32.view(np.uint8).reshape(-1, 4)[:, :3].tobytes())
        else:
            raise ValueError("bits must be 16 or 24")


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        rate, width, ch = w.getframerate(), w.getsampwidth(), w.getnchannels()
        raw = w.readframes(w.getnframes())
    if width == 2:
        x = np.frombuffer(raw, "<i2").astype(np.float32) / 32768
    elif width == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        i32 = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        i32 = np.where(i32 & 0x800000, i32 - 0x1000000, i32)
        x = i32.astype(np.float32) / 8388608
    else:
        raise ValueError(f"unsupported sample width {width}")
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, rate


# ---------------------------------------------------------------- reports


@dataclass
class Span:
    id: str
    speaker: str
    start: float
    end: float
    kind: str = "line"
    text: str = ""


def spans_from_timeline(tl: Timeline) -> list[Span]:
    return [Span(p.line.id, p.line.speaker, p.onset, p.speech_end, p.line.kind, p.line.text) for p in tl.order]


def timecode(t: float, fps: int) -> str:
    frames = int(round(t * fps))
    s, f = divmod(frames, fps)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def overlaps_of(span: Span, spans: Iterable[Span]) -> list[str]:
    return [o.id for o in spans if o.speaker != span.speaker and o.start < span.end and span.start < o.end]


def conversation_stats(spans: list[Span]) -> dict:
    """Turn-taking fingerprint: the numbers that make a dialogue feel overheard rather than read."""
    spans = sorted(spans, key=lambda s: s.start)
    if not spans:
        return {}
    duration = max(s.end for s in spans) - min(s.start for s in spans)
    turns = [s for s in spans if s.kind == "line"]
    ftos = [b.start - a.end for a, b in zip(turns, turns[1:]) if a.speaker != b.speaker]
    overlap = 0.0
    for i, a in enumerate(spans):
        for b in spans[i + 1:]:
            if b.speaker != a.speaker:
                overlap += max(0.0, min(a.end, b.end) - max(a.start, b.start))
    bcs = [s for s in spans if s.kind == "backchannel"]
    out = {
        "duration_s": round(duration, 2),
        "turns": len(turns),
        "speaker_changes": len(ftos),
        "backchannels": len(bcs),
        "backchannels_per_min": round(len(bcs) / (duration / 60), 1) if duration > 0 else 0.0,
        "overlapped_seconds": round(overlap, 2),
        "overlap_share_of_duration": round(overlap / duration, 3) if duration > 0 else 0.0,
    }
    if ftos:
        f = np.array(ftos) * 1000
        out.update({
            "gap_ms_median": int(np.median(f)),
            "gap_ms_p25": int(np.percentile(f, 25)),
            "gap_ms_p75": int(np.percentile(f, 75)),
            "changes_with_overlap_share": round(float(np.mean(f < 0)), 2),
            "changes_with_gap_over_700ms_share": round(float(np.mean(f > 700)), 2),
        })
    return out
