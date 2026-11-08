"""Session wiring with fake ears / Claude / mouth: draft behind the gate, release, audio framing, barge-in."""

import asyncio
import struct

from duplex.live.floor import Params, Verdict
from duplex.live.session import Session


class FakeSTT:
    def __init__(self):
        self.q = asyncio.Queue()
        self.audio = 0

    async def connect(self):
        pass

    async def send_audio(self, b):
        self.audio += len(b)

    async def events(self):
        while True:
            yield await self.q.get()

    async def close(self):
        pass


class FakeClaude:
    def __init__(self, reply="Oh, that's good. The dad and the rangoli, love it."):
        self.reply_text = reply
        self.listened = []
        self.replied = []

    async def listen(self, history, user_text, *, silence_ms, seq, nwords):
        self.listened.append(user_text)
        done = user_text.rstrip().endswith("?")
        return Verdict(state="done" if done else "continuing", remaining_words=0 if done else 3,
                       backchannel="haan", based_on_words=nwords, seq=seq)

    async def reply(self, history):
        self.replied.append([dict(m) for m in history])
        for w in self.reply_text.split(" "):
            yield w + " "


class FakeMouth:
    rate = 24000

    async def speak(self, text, previous_text=None):
        for _ in range(3):  # 3 x 100 ms of silence per clause
            await asyncio.sleep(0)
            yield b"\x00\x00" * 2400


class Clock:
    t = 100.0

    def __call__(self):
        return self.t


async def settle():
    for _ in range(20):
        await asyncio.sleep(0)


async def make():
    sent, audio, clock = [], [], Clock()

    async def sj(d):
        sent.append(d)

    async def sb(b):
        audio.append(b)

    stt, claude = FakeSTT(), FakeClaude()
    s = Session(send_json=sj, send_bytes=sb, stt=stt, claude=claude, mouth=FakeMouth(),
                params=Params(), clock=clock)
    await s.start(loops=False)
    return s, stt, claude, sent, audio, clock


async def run_until(s, clock, t):
    while clock.t < t:
        clock.t = round(clock.t + 0.02, 3)
        await s.tick()
        await settle()


async def test_turn_reply_and_history():
    s, stt, claude, sent, audio, clock = await make()
    await s.mic(b"\x00" * 3200)
    assert stt.audio == 3200
    await s.browser({"type": "vad", "speaking": True, "lag_ms": 0})
    await stt.q.put({"type": "partial", "text": "what if the dad can't cook"})
    await settle()
    clock.t += 1.5
    await stt.q.put({"type": "partial", "text": "what if the dad can't cook?"})
    await s.browser({"type": "vad", "speaking": False, "lag_ms": 0})
    await settle()
    assert any(m["type"] == "verdict" and m["state"] == "done" for m in sent)
    await run_until(s, clock, clock.t + 0.5)

    assert claude.replied and claude.replied[0][-1] == {"role": "user", "content": "what if the dad can't cook?"}
    assert audio, "reply audio should flow once the gate opens"
    rid = struct.unpack("<I", audio[0][:4])[0]
    assert all(struct.unpack("<I", a[:4])[0] == rid for a in audio)
    assert [m["text"] for m in sent if m["type"] == "agent"][0] == "Oh, that's good."

    await s.browser({"type": "playback", "state": "playing", "reply_id": rid, "delay_ms": 30})
    assert any(m["type"] == "gap" for m in sent)
    await s.browser({"type": "playback", "state": "idle", "reply_id": rid})
    assert s.history[-1]["role"] == "assistant" and s.history[-1]["content"].startswith("Oh, that's good.")
    stats = await s.close()
    assert stats["turns"] >= 2


async def test_barge_in_truncates_what_was_heard():
    s, stt, claude, sent, audio, clock = await make()
    await s.browser({"type": "vad", "speaking": True, "lag_ms": 0})
    await stt.q.put({"type": "committed", "text": "give me a hook?"})
    await settle()
    clock.t += 1.0
    await s.browser({"type": "vad", "speaking": False, "lag_ms": 0})
    await settle()
    await run_until(s, clock, clock.t + 0.4)
    rid = struct.unpack("<I", audio[0][:4])[0]
    await s.browser({"type": "playback", "state": "playing", "reply_id": rid, "delay_ms": 0})
    clock.t += 0.15
    await s.browser({"type": "vad", "speaking": True, "lag_ms": 0})
    await stt.q.put({"type": "partial", "text": "no wait different idea"})
    await settle()
    await run_until(s, clock, clock.t + 0.4)
    assert any(m == {"type": "stop", "reply_id": rid} for m in sent)
    assert s.history[-1]["role"] == "assistant" and s.history[-1]["content"].endswith("—")
    await s.close()
