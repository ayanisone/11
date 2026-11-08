"""The two Claude roles: the listener (judges the user's turn as it happens) and the brain (writes replies)."""

from __future__ import annotations

import os
import re
from typing import AsyncIterator, Literal, Optional

from pydantic import BaseModel, Field

from .floor import Verdict

MODEL = os.environ.get("DUPLEX_LIVE_MODEL", "claude-haiku-5-5")

BANK_IDS = ["mm-hmm", "mm", "yeah", "right", "okay", "oh", "really", "oh-no", "haan", "achha"]

LISTENER_SYSTEM = f"""You are the ears of a voice agent in a live spoken conversation. You get the recent \
conversation and the user's CURRENT turn as a live transcript that may stop mid-sentence or mid-word. \
Judge it the way an attentive friend listening would, in a split second.

state:
- continuing: mid-thought, clearly more coming (ends on "and", "but", "so", a preposition, an open list...)
- hesitating: stalled mid-thought, searching for a word or deciding ("it's like a... um", "the thing is—")
- finishing: on the last few words of their point; you can already tell how it ends
- done: the turn is complete (a question asked, a point landed); they now expect a response
remaining_words: your best guess of how many more words before they finish (0 when done).
backchannel: the token a good listener would murmur if they paused right now: one of {", ".join(BANK_IDS)}, \
or none. "oh-no" for bad news, "really" for surprising news, "oh" for news, "haan"/"achha" only if the user \
speaks Indian English or Hinglish. Use none when a backchannel would be odd.
laugh: true only if they JUST said something meant to be funny.
completion: only when hesitating and the next 1-5 words are obvious: those words, phrased as the listener \
would say them to help ("the wrong Goa?"). Otherwise empty."""

BRAIN_SYSTEM = """You are Riff, a quick, warm creative partner at an Indian ad agency, talking out loud with \
a colleague: brainstorming TV commercials, digital ads, hooks, taglines and dialogue. This is a live voice \
conversation; everything you write is spoken by a text-to-speech voice.

How you talk:
- Short turns: one or two sentences, then hand the floor back. Never lecture or list more than three things.
- React first, then add: "Oh, that's good.", "Hmm, wait—", "Ha, yes."
- Latch onto their words and build on them. If their sentence trailed off, finish it in a few words and keep going.
- You may already have murmured something while they talked (shown as [you said: ...]); don't repeat it.
- If a previous reply of yours ends in "—", they cut you off there: drop that thought and follow them.
- If the transcript seems cut short, respond to what they clearly meant.
- At most one audio tag per turn, only from: [laughs], [chuckles], [sighs], [excited], [curious], [softly].
- Plain spoken English with a natural Indian-English flavour; Hinglish words only if they use them first.
- No markdown, lists or headings. Never invent facts about real brands, prices, offers or claims."""


class ListenerOut(BaseModel):
    state: Literal["continuing", "hesitating", "finishing", "done"]
    remaining_words: int = Field(ge=0)
    backchannel: str
    laugh: bool
    completion: str


def _transcript(history: list[dict], limit: int = 6) -> str:
    lines = [f"{'User' if m['role'] == 'user' else 'Agent'}: {m['content']}" for m in history[-limit:]]
    return "\n".join(lines) or "(start of conversation)"


class Claude:
    def __init__(self, model: str = MODEL, client=None):
        import anthropic

        self.model = model
        self.client = client or anthropic.AsyncAnthropic()

    async def listen(self, history: list[dict], user_text: str, *, silence_ms: int, seq: int,
                     nwords: int) -> Verdict:
        prompt = (f"Conversation so far:\n{_transcript(history)}\n\n"
                  f"User's current turn (live): \"{user_text}\"\n"
                  f"They have been silent for {silence_ms} ms.")
        r = await self.client.messages.parse(
            model=self.model, max_tokens=200, system=LISTENER_SYSTEM, thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}], output_format=ListenerOut)
        out = r.parsed_output
        if out is None:
            return Verdict(based_on_words=nwords, seq=seq)
        bc = out.backchannel if out.backchannel in BANK_IDS else "none"
        return Verdict(state=out.state, remaining_words=out.remaining_words, backchannel=bc, laugh=out.laugh,
                       completion=out.completion.strip(), based_on_words=nwords, seq=seq)

    async def reply(self, history: list[dict]) -> AsyncIterator[str]:
        async with self.client.messages.stream(model=self.model, max_tokens=300, system=BRAIN_SYSTEM,
                                               thinking={"type": "disabled"}, messages=history) as stream:
            async for text in stream.text_stream:
                yield text


_CLAUSE_END = re.compile(r"([.!?…]+[\"')\]]?\s+|—\s*)")


async def clauses(deltas: AsyncIterator[str], *, min_words: int = 2, comma_words: int = 9) -> AsyncIterator[str]:
    """Group streamed text into speakable clauses: send the first clause to TTS as soon as it is complete."""
    buf = ""
    async for d in deltas:
        buf += d
        while True:
            cut = None
            for m in _CLAUSE_END.finditer(buf):
                if len(buf[:m.end()].split()) >= min_words:
                    cut = m.end()
                    break
            if cut is None:
                comma = buf.rfind(", ")
                if comma > 0 and len(buf[:comma].split()) >= comma_words:
                    cut = comma + 2
            if cut is None:
                break
            clause, buf = buf[:cut].strip(), buf[cut:]
            if clause:
                yield clause
    if buf.strip():
        yield buf.strip()


def merge_history(history: list[dict], role: str, content: str) -> None:
    """Append, keeping roles strictly alternating (consecutive same-role turns are merged)."""
    content = content.strip()
    if not content:
        return
    if history and history[-1]["role"] == role:
        history[-1]["content"] = f"{history[-1]['content']} {content}"
    elif not history and role == "assistant":
        history.append({"role": "user", "content": "(the call connects)"})
        history.append({"role": role, "content": content})
    else:
        history.append({"role": role, "content": content})


def with_interjections(user_text: str, interjections: list[tuple[int, str]]) -> str:
    """Splice what the agent murmured mid-turn back into the user's words at the right place."""
    ws = user_text.split()
    for pos, said in sorted(interjections, reverse=True):
        ws.insert(min(pos, len(ws)), f"[you said: {said}]")
    return " ".join(ws)


def first_words(text: str, n: Optional[int]) -> str:
    return text if n is None else " ".join(text.split()[:n])
