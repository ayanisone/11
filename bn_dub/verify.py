"""Stage 6: QA gate. Transcribe each generated clip back and compare with the script that was sent."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from . import translate, tts
from .config import settings
from .project import Project, Segment
from .transcribe import scribe_words

_PUNCT = re.compile(r"[\s\.,!?;:।\-–—\"'()\[\]…]+")
_TAG = re.compile(r"\[[^\]]*\]")


def strip_tags(text: str) -> str:
    """Remove [performance tags] so QA compares spoken words only."""
    return " ".join(_TAG.sub(" ", text).split())


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", strip_tags(text)).lower()
    return " ".join(t for t in _PUNCT.split(text) if t)


def similarity(expected: str, heard: str) -> float:
    a, b = normalise(expected), normalise(heard)
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def hear(seg: Segment, language: str) -> str:
    words = scribe_words(Path(seg.tts_path), language, diarize=False)
    return " ".join(w.text for w in words)


def verify_segment(project: Project, seg: Segment, *, fix: bool = True) -> Segment:
    """Back-transcribe. On a miss, apply the punctuation-first fix and regenerate once or twice."""
    if not seg.tts_path:
        return seg
    for attempt in range(settings.max_tts_attempts if fix else 1):
        heard = hear(seg, project.target_lang)
        score = similarity(seg.target_text, heard)
        seg.qa_similarity, seg.qa_heard = round(score, 3), heard
        if score >= settings.min_similarity:
            if seg.status != "warn":
                seg.status = "verified"
            return seg
        if not fix or seg.locked or attempt == settings.max_tts_attempts - 1:
            break
        seg.target_text = translate.tighten_for_tts(project, seg)
        tts.generate_segment(project, seg, allow_reshorten=False)
    seg.status = "warn"
    seg.notes = (seg.notes + "; " if seg.notes else "") + f"QA {seg.qa_similarity:.2f} < {settings.min_similarity}"
    return seg


def run(project: Project, ids: Optional[list[int]] = None, *, fix: bool = True) -> Project:
    for seg in project.segments:
        if ids is not None and seg.id not in ids:
            continue
        if seg.tts_path and seg.status in {"generated", "warn", "verified"}:
            verify_segment(project, seg, fix=fix)
            project.save()
    return project
