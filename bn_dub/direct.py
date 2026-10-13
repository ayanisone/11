"""Stage 3b: voice direction. Measure how the original speaker delivered each line, then have Claude
transcode that delivery into ElevenLabs performance tags + punctuation on the Bengali line, words untouched.

Why measure instead of asking a model to listen: a model describing a delivery from audio alone will confidently
invent one. The numbers below come from the waveform (pauses, rate, pitch, emphasis) and outrank impressions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from pydantic import BaseModel

from . import media
from .clients import anthropic
from .config import settings
from .project import Project, Segment

TAGS = ["warm", "confident", "intimate", "urgent", "calm", "reflective", "grounded", "charged", "quiet intensity",
        "soft", "sharp", "reverent", "curious", "hesitant", "resolved", "sincere", "measured", "excited", "sad",
        "whispers", "laughs", "sighs"]


@dataclass
class Measurement:
    duration: float
    speech_secs: float
    words_per_sec: float
    pauses: list[tuple[str, float]]        # (word the pause follows, length in seconds)
    loud_db: float                         # median frame RMS, dBFS
    dynamic_range_db: float                # p90 - p10 of frame RMS
    f0_median_hz: float
    f0_range_st: float                     # p10..p90 pitch range in semitones
    terminal: str                          # rising | falling | flat
    emphasised: list[str]                  # words hit noticeably harder than the rest of the line
    stretched: list[str]                   # words held noticeably longer than their neighbours


def _frames(x: np.ndarray, rate: int, ms: float = 20.0) -> tuple[np.ndarray, int]:
    hop = max(1, int(rate * ms / 1000))
    n = len(x) // hop
    if n == 0:
        return np.zeros((0, hop), dtype=np.float32), hop
    return x[:n * hop].reshape(n, hop), hop


def _rms_db(frames: np.ndarray) -> np.ndarray:
    r = np.sqrt(np.mean(np.square(frames, dtype=np.float64), axis=1))
    return 20.0 * np.log10(np.maximum(r, 1e-6))


def _f0_track(frames: np.ndarray, rate: int, voiced_mask: np.ndarray, fmin: float = 70.0, fmax: float = 400.0) -> np.ndarray:
    """Autocorrelation pitch per frame; NaN where unvoiced/unsure. Coarse but enough for median/range/contour."""
    lo, hi = int(rate / fmax), int(rate / fmin)
    out = np.full(len(frames), np.nan)
    for i, (fr, v) in enumerate(zip(frames, voiced_mask)):
        if not v or hi >= len(fr):
            continue
        fr = fr - fr.mean()
        ac = np.correlate(fr, fr, mode="full")[len(fr) - 1:]
        if ac[0] <= 0:
            continue
        seg = ac[lo:hi]
        k = int(np.argmax(seg)) + lo
        if ac[k] / ac[0] > 0.3:
            out[i] = rate / k
    return out


def measure(audio: np.ndarray, rate: int, words: list[dict]) -> Measurement:
    """`words`: [{text, start, end}] with times relative to the clip start."""
    x = media.to_mono(audio).astype(np.float32)
    frames, hop = _frames(x, rate, 40.0)
    if len(frames) == 0:
        return Measurement(0, 0, 0, [], -120, 0, 0, 0, "flat", [], [])
    db = _rms_db(frames)
    floor = float(np.percentile(db, 10))
    gate = max(floor + 10.0, -45.0)
    voiced = db > gate
    t = np.arange(len(frames)) * hop / rate

    # pauses from the waveform, labelled by the word they follow
    pauses: list[tuple[str, float]] = []
    i = 0
    while i < len(voiced):
        if not voiced[i]:
            j = i
            while j < len(voiced) and not voiced[j]:
                j += 1
            length = (j - i) * hop / rate
            if length >= 0.18 and i > 0 and j < len(voiced):
                start_t = t[i]
                before = [w for w in words if w["end"] <= start_t + 0.05]
                if before:
                    pauses.append((before[-1]["text"], round(length, 2)))
            i = j
        else:
            i += 1

    speech_secs = float(voiced.sum() * hop / rate)
    wps = len(words) / speech_secs if speech_secs > 0 else 0.0
    vdb = db[voiced] if voiced.any() else db
    loud = float(np.median(vdb))
    dyn = float(np.percentile(vdb, 90) - np.percentile(vdb, 10))

    f0 = _f0_track(frames, rate, voiced)
    f0v = f0[~np.isnan(f0)]
    if len(f0v) >= 3:
        f0_med = float(np.median(f0v))
        f0_range = float(12 * np.log2(np.percentile(f0v, 90) / np.percentile(f0v, 10)))
        tail = f0[-max(3, int(0.3 * rate / hop)):]
        tail = tail[~np.isnan(tail)]
        if len(tail) >= 2:
            slope = 12 * np.log2(tail[-1] / tail[0])
            terminal = "rising" if slope > 1.5 else "falling" if slope < -1.5 else "flat"
        else:
            terminal = "flat"
    else:
        f0_med, f0_range, terminal = 0.0, 0.0, "flat"

    # per-word loudness / length z-scores
    emph, stretched = [], []
    if len(words) >= 3:
        wl, wd = [], []
        for w in words:
            a, b = int(w["start"] * rate / hop), max(int(w["start"] * rate / hop) + 1, int(w["end"] * rate / hop))
            wl.append(float(np.max(db[a:b])) if b <= len(db) and a < b else loud)
            wd.append((w["end"] - w["start"]) / max(1, len(w["text"])))
        wl, wd = np.array(wl), np.array(wd)
        zl = (wl - wl.mean()) / (wl.std() + 1e-6)
        zd = (wd - wd.mean()) / (wd.std() + 1e-6)
        emph = [w["text"] for w, z in zip(words, zl) if z > 1.2]
        stretched = [w["text"] for w, z in zip(words, zd) if z > 1.5]

    return Measurement(round(len(x) / rate, 2), round(speech_secs, 2), round(wps, 2), pauses, round(loud, 1),
                       round(dyn, 1), round(f0_med, 1), round(f0_range, 1), terminal, emph, stretched)


class Directed(BaseModel):
    line: str
    why: str


SYSTEM = """You are a voice director preparing lines for ElevenLabs text-to-speech. You receive a translated line
plus measurements of how the ORIGINAL actor delivered it. Transcode that delivery into performance tags and
punctuation on the translated line.

Hard rules:
- Do not add, remove, reorder or respell any word of the translated line. Only tags and punctuation change.
- Tags are square-bracketed, placed before the words they govern, from this list only: {tags}.
  Use at most two per line; none if the delivery is plain. A tag has to be earned by the measurements.
- Pauses: put an ellipsis … where the original speaker paused (match the position via the word it followed);
  a comma for shorter beats. Keep the sentence-final punctuation consistent with the terminal contour
  (rising → question mark only if the source is a question, otherwise keep a full stop).
- Faster/louder than the speaker's average → more energy ([urgent], [charged], [sharp]); slower/quieter →
  [calm], [soft], [measured], [intimate]; wide pitch range → expressive; narrow → [grounded]/[measured].
- Return the line as a single line, no line breaks."""


def _prompt(seg: Segment, m: Measurement, rel: dict) -> str:
    pauses = ", ".join(f'{m.pauses[i][1]}s after "{m.pauses[i][0]}"' for i in range(len(m.pauses))) or "none"
    return (f"Source line: {seg.source_text}\n"
            f"Translated line (words are fixed): {seg.target_text}\n\n"
            f"Measured delivery of the original:\n"
            f"- speaking rate: {m.words_per_sec} words/s ({rel['rate']} this speaker's average)\n"
            f"- loudness: {m.loud_db} dBFS ({rel['loud']} this speaker's average), dynamic range {m.dynamic_range_db} dB\n"
            f"- pitch: median {m.f0_median_hz} Hz, range {m.f0_range_st} semitones, ends {m.terminal}\n"
            f"- pauses: {pauses}\n"
            f"- words hit harder: {', '.join(m.emphasised) or 'none'}; words stretched: {', '.join(m.stretched) or 'none'}\n")


def direct_line(seg: Segment, m: Measurement, rel: dict) -> Directed:
    client = anthropic()
    r = client.messages.parse(model=settings.claude_model, max_tokens=2048,
                              system=SYSTEM.format(tags=", ".join(TAGS)),
                              messages=[{"role": "user", "content": _prompt(seg, m, rel)}], output_format=Directed)
    if r.stop_reason == "refusal":
        return Directed(line=seg.target_text, why="refused")
    return r.parsed_output


def _relative(value: float, mean: float, std: float, up: str, down: str) -> str:
    if std < 1e-6:
        return "about"
    z = (value - mean) / std
    return up if z > 0.7 else down if z < -0.7 else "about"


def run(project: Project, ids: Optional[list[int]] = None) -> Project:
    """Measure every line (so speaker averages are real), direct the requested ones."""
    if not project.vocals_path:
        raise RuntimeError("run the separate stage first")
    rate = settings.sample_rate
    vocals = media.decode(project.vocals_path, channels=1)
    measured: dict[int, Measurement] = {}
    for seg in project.segments:
        a, b = int(seg.start * rate), int(seg.end * rate)
        rel_words = [{"text": w["text"], "start": w["start"] - seg.start, "end": w["end"] - seg.start} for w in seg.words]
        measured[seg.id] = measure(vocals[a:b], rate, rel_words)

    by_speaker: dict[str, list[Measurement]] = {}
    for seg in project.segments:
        by_speaker.setdefault(seg.speaker, []).append(measured[seg.id])

    for seg in project.segments:
        if ids is not None and seg.id not in ids:
            continue
        if seg.locked or not seg.target_text:
            continue
        m = measured[seg.id]
        peers = by_speaker[seg.speaker]
        rates = np.array([p.words_per_sec for p in peers if p.words_per_sec > 0] or [m.words_per_sec])
        louds = np.array([p.loud_db for p in peers if p.loud_db > -100] or [m.loud_db])
        rel = {"rate": _relative(m.words_per_sec, rates.mean(), rates.std(), "faster than", "slower than"),
               "loud": _relative(m.loud_db, louds.mean(), louds.std(), "louder than", "quieter than")}
        d = direct_line(seg, m, rel)
        seg.target_text = d.line
        seg.direction = d.why
        seg.tts_path = seg.fit_path = None
        project.save()
    return project
