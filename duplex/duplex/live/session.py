"""One live conversation: wires the ears (Scribe), the listener + brain (Claude), the mouth (TTS) and the
browser together around the Floor. Every adapter is injected, so tests can swap in fakes.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import struct
import time
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Awaitable, Callable, Optional

from ..timeline import Span, conversation_stats
from .claude import clauses, merge_history, with_interjections
from .floor import Action, Floor, Params, Verdict, words


@dataclass
class Reply:
    id: int
    user_text: str
    gate: asyncio.Event = field(default_factory=asyncio.Event)
    task: Optional[asyncio.Task] = None
    clauses: list[list] = field(default_factory=list)  # [text, ms]
    released: bool = False
    audible_t: Optional[float] = None
    done: bool = False
    finished: bool = False  # history written
    is_completion: bool = False

    @property
    def text(self) -> str:
        return " ".join(c[0] for c in self.clauses)

    def heard(self, ms: float) -> str:
        """The part of the reply the user actually heard in `ms` of playback."""
        out, t = [], 0.0
        for text, dur in self.clauses:
            if t + dur <= ms:
                out.append(text)
            elif dur > 0 and ms > t:
                ws = words(text)
                out.append(" ".join(ws[: max(1, int(len(ws) * (ms - t) / dur))]))
                break
            t += dur
        return " ".join(out)


class Session:
    COMPLETION_IDS = itertools.count(1_000_000)

    def __init__(self, *, send_json: Callable[[dict], Awaitable[None]], send_bytes: Callable[[bytes], Awaitable[None]],
                 stt, claude, mouth, params: Optional[Params] = None, bank_ms: Optional[dict] = None,
                 log_dir: Optional[Path] = None, clock: Callable[[], float] = time.monotonic, tick: float = 0.04):
        self.send_json, self.send_bytes = send_json, send_bytes
        self.stt, self.claude, self.mouth = stt, claude, mouth
        self.floor = Floor(params)
        self.clock, self.tick_s = clock, tick
        self.bank_ms = bank_ms or {}
        self.log_dir = log_dir
        self.history: list[dict] = []
        self.interjections: list[tuple[int, str]] = []
        self.replies: dict[int, Reply] = {}
        self.spans: list[Span] = []
        self.events: list[dict] = []
        self._user_on: Optional[float] = None
        self._agent_on: dict[int, float] = {}
        self._last_user_off: Optional[float] = None
        self._listen_dirty = asyncio.Event()
        self._seq = 0
        self._tasks: list[asyncio.Task] = []
        self.t0 = clock()

    # ------------------------------------------------------------ lifecycle

    async def start(self, *, loops: bool = True) -> None:
        await self.stt.connect()
        self._tasks.append(asyncio.create_task(self._stt_loop()))
        self._tasks.append(asyncio.create_task(self._listen_loop()))
        if loops:
            self._tasks.append(asyncio.create_task(self._tick_loop()))
        await self._log("listening")

    async def close(self) -> dict:
        for r in self.replies.values():
            if r.task:
                r.task.cancel()
        for t in self._tasks:
            t.cancel()
        await self.stt.close()
        if hasattr(self.mouth, "close"):
            await self.mouth.close()
        stats = conversation_stats(self.spans)
        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            path = self.log_dir / time.strftime("session-%Y%m%d-%H%M%S.json")
            path.write_text(json.dumps({"stats": stats, "history": self.history, "events": self.events,
                                        "params": {f.name: getattr(self.floor.p, f.name) for f in fields(Params)}},
                                       indent=1, ensure_ascii=False))
        return stats

    def now(self) -> float:
        return self.clock()

    async def _log(self, text: str, **data) -> None:
        ev = {"t": round(self.now() - self.t0, 3), "text": text, **data}
        self.events.append(ev)
        await self.send_json({"type": "log", **ev})

    # ------------------------------------------------------------ inputs

    async def mic(self, pcm16: bytes) -> None:
        await self.stt.send_audio(pcm16)

    async def browser(self, msg: dict) -> None:
        kind, t = msg.get("type"), self.now()
        if kind == "vad":
            t -= msg.get("lag_ms", 0) / 1000
            speaking = bool(msg["speaking"])
            self.floor.on_vad(speaking, t)
            if speaking:
                self._user_on = t
            elif self._user_on is not None:
                self.spans.append(Span(f"u{len(self.spans)}", "user", self._user_on - self.t0, t - self.t0))
                self._user_on, self._last_user_off = None, t
                self._listen_dirty.set()
        elif kind == "playback":
            rid = int(msg.get("reply_id", 0))
            if msg.get("state") == "playing":
                t += msg.get("delay_ms", 0) / 1000
                self._agent_on[rid] = t
                r = self.replies.get(rid)
                if r and not r.is_completion:
                    self.floor.on_playback(True, t)
                    gap = None if self.floor.user_vad or self._last_user_off is None else int(
                        (t - self._last_user_off) * 1000)
                    await self.send_json({"type": "gap", "reply_id": rid, "gap_ms": gap})
            else:
                start = self._agent_on.pop(rid, None)
                if start is not None:
                    self.spans.append(Span(f"a{rid}", "agent", start - self.t0, t - self.t0))
                r = self.replies.get(rid)
                if r and r.is_completion:
                    self.replies.pop(rid, None)
                elif r and r.released:
                    self.floor.on_playback(False, t)
                    self._finish(r, r.text)
        elif kind == "params":
            for f in fields(Params):
                if f.name in msg:
                    setattr(self.floor.p, f.name, type(getattr(self.floor.p, f.name))(msg[f.name]))
            await self._log("knobs changed", params={k: v for k, v in msg.items() if k != "type"})

    async def _stt_loop(self) -> None:
        async for ev in self.stt.events():
            t = self.now()
            if ev["type"] == "partial":
                self.floor.on_partial(ev["text"], t)
            elif ev["type"] == "committed":
                self.floor.on_committed(ev["text"], t)
            elif ev["type"] == "error":
                await self._log(f"speech-to-text: {ev['text']}")
                continue
            else:
                continue
            await self.send_json({"type": "user", "text": self.floor.user_text, "final": ev["type"] == "committed"})
            self._listen_dirty.set()

    async def _listen_loop(self) -> None:
        while True:
            await self._listen_dirty.wait()
            self._listen_dirty.clear()
            f = self.floor
            if not f.turn_open or f.nwords == 0 or f._agent_active:
                continue
            self._seq += 1
            silence = 0 if f.user_vad else int((self.now() - f.vad_t) * 1000)
            try:
                v = await self.claude.listen(self.history, f.user_text, silence_ms=silence, seq=self._seq,
                                             nwords=f.nwords)
            except Exception as e:  # keep talking even if the listener is down: Floor falls back to timing
                await self._log(f"listener error: {e}")
                continue
            f.on_verdict(v)
            await self.send_json({"type": "verdict", "state": v.state, "remaining": v.remaining_words,
                                  "backchannel": v.backchannel, "laugh": v.laugh, "completion": v.completion})

    async def _tick_loop(self) -> None:
        while True:
            await self.tick()
            await asyncio.sleep(self.tick_s)

    async def tick(self) -> None:
        t = self.now()
        for a in self.floor.step(t):
            await self._do(a, t)

    # ------------------------------------------------------------ actions

    async def _do(self, a: Action, t: float) -> None:
        d = a.data
        if a.kind == "backchannel":
            await self.send_json({"type": "bc", "id": d["id"]})
            self.spans.append(Span(f"b{len(self.spans)}", "agent", t - self.t0,
                                   t - self.t0 + self.bank_ms.get(d["id"], 400) / 1000, "backchannel"))
            await self._log(f"backchannel: {d['id']}")
        elif a.kind == "draft":
            r = self.replies[d["draft"]] = Reply(d["draft"], d["user_text"])
            msgs = [dict(m) for m in self.history]
            merge_history(msgs, "user", with_interjections(d["user_text"], self.interjections))
            r.task = asyncio.create_task(self._run_reply(r, msgs))
            await self._log("drafting reply", based_on=d["user_text"])
        elif a.kind == "release":
            r = self.replies.get(d["draft"])
            merge_history(self.history, "user", with_interjections(d["user_text"], self.interjections))
            self.interjections = []
            if r:
                r.released = True
                r.gate.set()
                if r.done and not r.clauses:
                    self._abort(r)
            await self._log("overlap start: coming in before they finish" if d["overlap"]
                            else f"reply released after {d['gap_ms']} ms of silence")
        elif a.kind == "cancel":
            r = self.replies.pop(d["draft"], None)
            if r and r.task:
                r.task.cancel()
            await self._log(f"draft dropped: {d['reason']}")
        elif a.kind == "stop":
            r = self.replies.get(d["draft"]) if d["draft"] else None
            if r:
                if r.task:
                    r.task.cancel()
                heard_ms = (t - r.audible_t) * 1000 if r.audible_t else 0
                heard = r.heard(heard_ms)
                await self.send_json({"type": "stop", "reply_id": r.id})
                self._finish(r, f"{heard}—" if heard else "")
            await self._log("stopped talking: user took the floor")
        elif a.kind == "complete":
            rid = next(self.COMPLETION_IDS)
            r = self.replies[rid] = Reply(rid, "", is_completion=True, released=True)
            r.gate.set()
            self.interjections.append((self.floor.nwords, d["text"]))
            r.task = asyncio.create_task(self._speak(r, [d["text"]]))
            await self._log(f"finishing their sentence: {d['text']}")

    async def _run_reply(self, r: Reply, msgs: list[dict]) -> None:
        try:
            await self._speak(r, clauses(self.claude.reply(msgs)))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            await self._log(f"reply failed: {e}")
            self._abort(r)

    async def _speak(self, r: Reply, texts) -> None:
        prev = None
        ready = False

        async def each():
            if hasattr(texts, "__aiter__"):
                async for x in texts:
                    yield x
            else:
                for x in texts:
                    yield x

        async for clause in each():
            r.clauses.append([clause, 0.0])
            sent_text = False
            async for chunk in self.mouth.speak(clause, prev):
                if not ready:
                    ready = True
                    self.floor.on_draft_ready(r.id)
                await r.gate.wait()
                if r.audible_t is None:
                    r.audible_t = self.now()
                if not sent_text:
                    sent_text = True
                    if not r.is_completion:
                        self.floor.agent_text = r.text
                    await self.send_json({"type": "agent", "reply_id": r.id, "text": clause,
                                          "completion": r.is_completion})
                await self.send_bytes(struct.pack("<I", r.id) + chunk)
                r.clauses[-1][1] += len(chunk) / 2 / self.mouth.rate * 1000
            prev = clause
        r.done = True
        if not r.clauses or not any(ms for _, ms in r.clauses):
            self._abort(r)
            return
        await self.send_json({"type": "reply_end", "reply_id": r.id})

    def _abort(self, r: Reply) -> None:
        """A reply that produced no audio must not leave the floor thinking the agent is talking."""
        f = self.floor
        if f.draft and f.draft.id == r.id:
            if f.draft.released:
                f.on_playback(False, self.now())
            f.draft = None
        self.replies.pop(r.id, None)

    def _finish(self, r: Reply, heard: str) -> None:
        if r.finished:
            return
        r.finished = True
        if heard:
            merge_history(self.history, "assistant", heard)
        self.replies.pop(r.id, None)


def verdict_from_dict(d: dict, seq: int, nwords: int) -> Verdict:  # used by scripted fakes
    return Verdict(based_on_words=nwords, seq=seq, **d)
