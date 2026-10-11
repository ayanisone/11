"""Stage 3: translate each line into spoken Bengali that fits its time slot, via Claude structured output."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from . import timing
from .clients import anthropic
from .config import settings
from .project import Project, Segment

LANG_NAMES = {"bn": "Bengali", "hi": "Hindi", "mr": "Marathi", "as": "Assamese", "ta": "Tamil", "te": "Telugu",
              "kn": "Kannada", "ml": "Malayalam", "gu": "Gujarati", "pa": "Punjabi", "or": "Odia", "en": "English"}


class Line(BaseModel):
    id: int
    target: str
    romanised: str


class Translation(BaseModel):
    lines: list[Line]


SYSTEM = """You translate spoken dialogue for voice dubbing. The output is read aloud by a text-to-speech voice,
so write the way people actually talk, not the way they write.

Rules:
- Match the meaning AND the spoken length of each line. Each line has a time slot in seconds; a natural
  {lang} reading must fit it. {lang} often runs longer than English, so prefer short everyday words and
  drop filler rather than compress grammar. When a line is marked SHORTEN BY N%, cut it by that much.
- Colloquial, spoken, gender neutral. One line in, one line out; never merge or split lines.
- Campaign names and non-clinical terms (heart health, check-up, risk factors) are translated colloquially.
- Clinical terms people say in English (diabetes, blood pressure, BP, sugar, cholesterol) stay in Latin
  script inside the {lang} sentence; do not transliterate them.
- Numbers, dates and units: write them the way a {lang} speaker says them aloud.
- Punctuate for breath: commas where the speaker pauses, a full stop at the end. Avoid very long words.
- `romanised` is a plain Latin-script rendering of the {lang} line for the engineer to follow along.
Return every input id exactly once."""


def _lang(code: str) -> str:
    return LANG_NAMES.get(code, code)


def _slot(project: Project, seg: Segment) -> float:
    return timing.slot_for(seg.start, seg.end, project.next_start(seg))


def _format_lines(project: Project, segs: list[Segment], shorten: dict[int, int]) -> str:
    rows = []
    for s in segs:
        tag = f" SHORTEN BY {shorten[s.id]}%" if s.id in shorten else ""
        rows.append(f"[{s.id}] slot={_slot(project, s):.1f}s speaker={s.speaker}{tag}\n{s.source_text}")
    return "\n\n".join(rows)


def translate_segments(project: Project, segs: list[Segment], shorten: Optional[dict[int, int]] = None) -> dict[int, Line]:
    """One call for a batch of lines so the translator keeps context across them."""
    if not segs:
        return {}
    shorten = shorten or {}
    client = anthropic()
    system = SYSTEM.format(lang=_lang(project.target_lang))
    user = (f"Source language: {_lang(project.source_lang)}. Target: {_lang(project.target_lang)}.\n"
            f"Lines:\n\n{_format_lines(project, segs, shorten)}")
    response = client.messages.parse(
        model=settings.claude_model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=Translation,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"translation refused: {getattr(response.stop_details, 'explanation', '')}")
    parsed: Translation = response.parsed_output
    return {line.id: line for line in parsed.lines}


def tighten_for_tts(project: Project, seg: Segment) -> str:
    """v3 hallucination fix: punctuation-first, minimal change. Used after a QA failure, never as a rewrite."""
    client = anthropic()
    prompt = (f"This {_lang(project.target_lang)} line made a text-to-speech voice stumble (repeats or false starts).\n"
              "Fix it with the smallest possible change: add commas where a speaker would breathe, or break one long "
              "sentence into short fragments. Split a very long word in two only as a last resort. Do not change the "
              "wording otherwise. Return only the fixed line.\n\n" + seg.target_text)
    response = client.messages.create(model=settings.claude_model, max_tokens=1024,
                                      messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text or seg.target_text


def run(project: Project, ids: Optional[list[int]] = None, *, batch_size: int = 40) -> Project:
    todo = [s for s in project.segments if (ids is None or s.id in ids) and not s.locked]
    for i in range(0, len(todo), batch_size):
        batch = todo[i:i + batch_size]
        lines = translate_segments(project, batch)
        for s in batch:
            line = lines.get(s.id)
            if not line:
                s.notes = "translator returned no line"
                continue
            s.target_text, s.romanised = line.target, line.romanised
            s.status = "translated"
            s.tts_path = s.fit_path = None
        project.save()
    return project
