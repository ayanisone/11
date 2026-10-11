"""Stage 2: Scribe speech-to-text with word timestamps and diarization, then group words into dub segments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .clients import elevenlabs
from .config import settings
from .project import Project, Segment


@dataclass
class Word:
    text: str
    start: float
    end: float
    speaker: str


def scribe_words(audio_path: Path, language: Optional[str] = None, *, diarize: bool = True) -> list[Word]:
    client = elevenlabs()
    with open(audio_path, "rb") as f:
        kwargs = dict(model_id=settings.stt_model, file=f, timestamps_granularity="word", diarize=diarize,
                      tag_audio_events=False)
        if language:
            kwargs["language_code"] = language
        result = client.speech_to_text.convert(**kwargs)
    words: list[Word] = []
    for w in getattr(result, "words", None) or []:
        if getattr(w, "type", "word") != "word" or w.start is None or w.end is None:
            continue
        words.append(Word(text=w.text, start=float(w.start), end=float(w.end), speaker=w.speaker_id or "speaker_0"))
    return words


_SENTENCE_END = (".", "?", "!", "।", "…")


def segment_words(words: list[Word], *, max_secs: Optional[float] = None, max_chars: Optional[int] = None,
                  split_gap: Optional[float] = None) -> list[Segment]:
    """Group words into lines a TTS voice can deliver in one breath.

    A new segment starts on: speaker change, a pause longer than `split_gap`, or when the current one
    would exceed `max_secs` / `max_chars` (preferring to cut at sentence punctuation).
    """
    max_secs = settings.max_segment_secs if max_secs is None else max_secs
    max_chars = settings.max_segment_chars if max_chars is None else max_chars
    split_gap = settings.split_gap_secs if split_gap is None else split_gap

    segments: list[Segment] = []
    cur: list[Word] = []

    def flush() -> None:
        if not cur:
            return
        text = " ".join(w.text for w in cur).strip()
        segments.append(Segment(id=len(segments) + 1, start=cur[0].start, end=cur[-1].end,
                                speaker=cur[0].speaker, source_text=text))
        cur.clear()

    for w in words:
        if cur:
            prev = cur[-1]
            dur = w.end - cur[0].start
            chars = sum(len(x.text) + 1 for x in cur) + len(w.text)
            gap = w.start - prev.end
            sentence_done = prev.text.endswith(_SENTENCE_END)
            if (w.speaker != prev.speaker or gap > split_gap or dur > max_secs or chars > max_chars
                    or (sentence_done and dur > max_secs * 0.5)):
                flush()
        cur.append(w)
    flush()
    return segments


def run(project: Project) -> Project:
    src = Path(project.vocals_path or project.audio_path)
    words = scribe_words(src, project.source_lang)
    project.segments = segment_words(words)
    for seg in project.segments:
        project.speaker(seg.speaker)
    project.save()
    return project
