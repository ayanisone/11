"""Claude writes the overlap score from a creative brief."""

from __future__ import annotations

import os
from typing import Optional

from pydantic import ValidationError

from .score import Score

DEFAULT_MODEL = os.environ.get("DUPLEX_CLAUDE_MODEL", "claude-opus-5-5")

SYSTEM = """You write dialogue for TV and digital ads that sounds OVERHEARD, not performed: two real people \
talking, on a timeline, not a script read in turns.

You output an "overlap score". Every line after the first is hung off a moment in an earlier line via `start`:
- at="end", offset_ms=+150..+300: a normal handover. Real conversations hand over in ~200 ms on average.
- at="end", offset_ms=0..+80: a latch: answering the instant they stop (agreement, excitement).
- at="end", offset_ms=-400..-100: overlap: starting before they finish because you already know where \
they're going. Use for agreement, finishing their sentence, excitement.
- at="word": land exactly on a word inside the other person's line. Use for backchannels ("mm", "haan", \
"right", "yeah yeah") placed on a content word, for laughs on the punchline word, and for cut-ins.
- interrupts=true: this line shuts the other person down; they stop at the next word boundary after \
yield_ms. Write the interrupted line in full anyway (the cut is done in the edit), but make sure its first \
part still works when cut.
- at="end", offset_ms=+500..+1200: a deliberate beat (hesitation, a realisation, comic timing). Sparingly.

What makes it feel real (do these):
- The listener is never silent for long: 1 backchannel every ~5-10 s from the non-speaking person, \
kind="backchannel", gain_db -4 to -8, 1-3 words, often with a tag like [softly]. Never two in a row from \
the same person.
- People finish each other's sentences, repeat the other's last words back, agree before the point lands.
- Turns are short and uneven. Fragments. False starts with an em-dash ("I was going to— no wait").
- At least one interruption and at least two real overlaps in a 30 s spot.
- A speaker never overlaps THEMSELVES: their next line must start after their previous line ends.
- Audio tags are Eleven v4 delivery tags, placed right before the words they colour, at most one or two per \
line: [laughs], [chuckles], [sighs], [gasps], [excited], [curious], [sarcastic], [surprised], [softly], \
[whispers], [jumping in], [interrupting], [overlapping], [warmly], [nervous]. They describe how a line is \
spoken, not stage directions. Reactions with no words use kind="reaction" (e.g. text "[laughs]").
- In Indian-English or Hinglish dialogue, natural fillers like "haan", "achha", "arre", "yaar" are welcome \
when the brief's audience speaks that way.

Craft rules: one idea per spot, the product moment lands in the dialogue rather than a pasted tagline, \
nothing a viewer could fact-check that the brief didn't give you (no invented prices, offers, claims or \
statistics). Time the whole thing to the requested length at a natural pace (~2.5-3 words/s per voice, \
but overlaps save time). Line ids: l1, l2... for turns, b1, b2... for backchannels, r1... for reactions; \
lines must be listed in the order they START, and anchors may only point to earlier lines."""


def write_score(brief: str, *, seconds: int = 30, language: str = "en", model: str = DEFAULT_MODEL,
                speakers: Optional[list[str]] = None) -> Score:
    import anthropic

    client = anthropic.Anthropic()
    who = ", ".join(speakers) if speakers else "two people the brief implies (speaker keys A and B)"
    messages = [{"role": "user", "content": (
        f"Brief:\n{brief}\n\nLength: {seconds} seconds. Language: {language}. Speakers: {who}.\n"
        "Write the overlap score.")}]
    for attempt in range(2):
        try:
            r = client.messages.parse(model=model, max_tokens=16000, system=SYSTEM, messages=messages,
                                      output_format=Score)
        except ValidationError as e:  # e.g. an anchor pointing forward; give Claude one chance to fix it
            if attempt:
                raise
            messages += [{"role": "assistant", "content": "(score failed validation)"},
                         {"role": "user", "content": f"That score is invalid: {e}. Write it again, fixed."}]
            continue
        if r.stop_reason == "refusal" or r.parsed_output is None:
            raise RuntimeError(f"no score returned (stop_reason={r.stop_reason})")
        return r.parsed_output
    raise AssertionError("unreachable")
