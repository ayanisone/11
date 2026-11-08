"""The overlap score: a two-track dialogue script where every line is hung off a moment in another line.

A normal script is a list. Real conversation is a timeline with two tracks: B's "mm-hmm" lands on A's
third word, B's answer starts 150 ms *before* A finishes, A trails off when B cuts in. The score encodes
that as anchors ("start 120 ms after the word 'Lonavala' in line l3") instead of absolute timecodes, so
the timing survives re-renders: if a new take of l3 is slower, everything hung off it moves with it.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class Anchor(BaseModel):
    """Where a line's first spoken word lands, relative to an earlier line."""

    ref: str = Field(description="id of an EARLIER line this line is timed against")
    at: Literal["end", "start", "word"] = Field(
        default="end",
        description="'end' = when ref's speech stops; 'start' = when ref's speech starts; "
                    "'word' = on a word inside ref (set `word`)")
    word: Optional[str] = Field(
        default=None,
        description="when at='word': the word (or short phrase) in ref's text to hang on, spelled as in ref")
    occurrence: int = Field(default=1, ge=1, description="which occurrence of `word` in ref, 1-based")
    edge: Literal["start", "end"] = Field(default="start", description="hang on the start or the end of `word`")
    offset_ms: int = Field(
        default=200,
        description="added to the anchor point. After at='end': +200 is a normal gap, 0 is a latch, "
                    "negative is an overlap (start before the other person finishes)")


class Line(BaseModel):
    id: str = Field(description="short unique id, e.g. l1, l2, b1")
    speaker: str = Field(description="speaker key, e.g. A or B")
    text: str = Field(description="exactly what is spoken; may contain Eleven v4 audio tags like [laughs]")
    kind: Literal["line", "backchannel", "reaction"] = Field(
        default="line",
        description="line = a real turn; backchannel = listener token (mm-hmm, yeah, right) under the other "
                    "speaker; reaction = laugh/gasp/sigh with no words")
    start: Optional[Anchor] = Field(
        default=None, description="omit only for the very first line (it starts at 0)")
    interrupts: bool = Field(
        default=False,
        description="true if this line cuts off start.ref: ref stops at the first word boundary "
                    "yield_ms after this line starts")
    yield_ms: int = Field(default=250, ge=0, description="how long the interrupted speaker keeps talking over")
    gain_db: float = Field(default=0.0, description="trim for this clip; backchannels usually sit -4 to -8 dB")


class SpeakerSpec(BaseModel):
    speaker: str
    casting: str = Field(description="who this person is and how they sound, for voice casting")
    voice_id: Optional[str] = Field(default=None, description="ElevenLabs voice id, if already cast")


class Score(BaseModel):
    title: str
    language: str = Field(default="en", description="ISO 639-1 code of the dialogue")
    speakers: list[SpeakerSpec]
    lines: list[Line]

    @model_validator(mode="after")
    def _check_refs(self) -> "Score":
        seen: set[str] = set()
        speakers = {s.speaker for s in self.speakers}
        for line in self.lines:
            if line.id in seen:
                raise ValueError(f"duplicate line id {line.id!r}")
            if line.speaker not in speakers:
                raise ValueError(f"line {line.id!r}: unknown speaker {line.speaker!r}")
            if line.start is not None:
                if line.start.ref not in seen:
                    raise ValueError(f"line {line.id!r} is anchored to {line.start.ref!r}, which is not an earlier line")
                if line.start.at == "word" and not line.start.word:
                    raise ValueError(f"line {line.id!r}: at='word' needs `word`")
            if line.interrupts and line.start is None:
                raise ValueError(f"line {line.id!r}: interrupts=true needs a start anchor naming who it cuts off")
            seen.add(line.id)
        return self
