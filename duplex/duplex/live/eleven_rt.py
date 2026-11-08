"""Real-time ElevenLabs I/O: Scribe v2 Realtime (ears), streaming TTS (mouth), and the backchannel bank."""

from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path
from typing import AsyncIterator, Optional
from urllib.parse import urlencode

import aiohttp
import numpy as np

API = os.environ.get("ELEVENLABS_API_BASE", "https://api.elevenlabs.io")
WS_API = API.replace("https://", "wss://").replace("http://", "ws://")

# id -> v4 text. Rendered once per voice with eleven_v4 (not Turbo: quality matters, latency doesn't),
# trimmed tight, and played from the browser's memory with zero synthesis delay.
BANK = {
    "mm-hmm": "[softly] mm-hmm.",
    "mm": "[softly] mm.",
    "yeah": "[softly] yeah.",
    "right": "right, right.",
    "okay": "okay...",
    "oh": "[surprised] oh!",
    "really": "[surprised] really?",
    "oh-no": "[softly] oh no.",
    "haan": "haan.",
    "achha": "[curious] achha?",
    "laugh": "[laughs] haha.",  # v4 rejects tag-only text
}


def api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SystemExit("ELEVENLABS_API_KEY is not set")
    return key


def http() -> aiohttp.ClientSession:
    # trust_env: honour HTTPS_PROXY where one is configured
    return aiohttp.ClientSession(trust_env=True, headers={"xi-api-key": api_key()})


class Scribe:
    """Scribe v2 Realtime over a WebSocket: PCM16 16 kHz in, partial / committed transcripts out."""

    def __init__(self, *, language: Optional[str] = None, vad_silence: float = 0.6,
                 model_id: str = "scribe_v2_realtime"):
        q = [("model_id", model_id), ("audio_format", "pcm_16000"), ("commit_strategy", "vad"),
             ("vad_silence_threshold_secs", str(vad_silence))]
        if language:
            q.append(("language_code", language))
        self.url = f"{WS_API}/v1/speech-to-text/realtime?{urlencode(q)}"
        self._http: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None

    async def connect(self) -> None:
        # Mint a single-use token over REST and authenticate the socket with it: the API key itself never
        # rides on the WebSocket (and proxies that inject the key into HTTPS requests work too).
        async with http() as h:
            async with h.post(f"{API}/v1/single-use-token/realtime_scribe") as r:
                if r.status >= 400:
                    raise RuntimeError(f"Scribe token HTTP {r.status}: {(await r.text())[:300]}")
                token = (await r.json())["token"]
        self._http = aiohttp.ClientSession(trust_env=True)
        self._ws = await self._http.ws_connect(f"{self.url}&{urlencode({'token': token})}", heartbeat=20)

    async def send_audio(self, pcm16: bytes) -> None:
        if self._ws is None or self._ws.closed:
            return
        await self._ws.send_str(json.dumps({"message_type": "input_audio_chunk", "commit": False,
                                            "sample_rate": 16000,
                                            "audio_base_64": base64.b64encode(pcm16).decode()}))

    async def events(self) -> AsyncIterator[dict]:
        assert self._ws is not None
        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                kind = data.get("message_type", "")
                text = data.get("text", data.get("transcript", ""))
                if kind == "partial_transcript":
                    yield {"type": "partial", "text": text}
                elif kind == "committed_transcript":
                    yield {"type": "committed", "text": text}
                elif kind == "session_started":
                    yield {"type": "started"}
                elif "error" in kind or kind in ("quota_exceeded", "rate_limited", "session_time_limit_exceeded"):
                    yield {"type": "error", "text": f"{kind}: {data.get('error') or data.get('message') or data}"}
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                break

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
        if self._http is not None:
            await self._http.close()


class Mouth:
    """Streaming TTS, one clause per request: PCM16 24 kHz chunks as they are synthesised."""

    def __init__(self, voice_id: str, *, model_id: str = "eleven_v4_turbo", output_format: str = "pcm_24000"):
        self.voice_id, self.model_id, self.output_format = voice_id, model_id, output_format
        self.rate = int(output_format.split("_")[1])
        self._http: Optional[aiohttp.ClientSession] = None

    async def speak(self, text: str, previous_text: Optional[str] = None) -> AsyncIterator[bytes]:
        if self._http is None or self._http.closed:
            self._http = http()
        body = {"text": text, "model_id": self.model_id}
        if previous_text:
            body["previous_text"] = previous_text
        url = f"{API}/v1/text-to-speech/{self.voice_id}/stream"
        async with self._http.post(url, params={"output_format": self.output_format}, json=body) as r:
            if r.status >= 400:
                raise RuntimeError(f"TTS HTTP {r.status}: {(await r.text())[:300]}")
            carry = b""
            async for chunk in r.content.iter_chunked(4800):
                chunk = carry + chunk
                cut = len(chunk) - len(chunk) % 2  # keep 16-bit samples whole
                carry = chunk[cut:]
                if cut:
                    yield chunk[:cut]

    async def close(self) -> None:
        if self._http is not None:
            await self._http.close()


def build_bank(voice_id: str, out: Path, *, model_id: str = "eleven_v4", takes: int = 2,
               only: Optional[list[str]] = None) -> dict:
    """Render each backchannel `takes` times, trim to the sound, peak-normalise, write a manifest."""
    from ..eleven import tts_with_timestamps
    from ..timeline import energy_bounds, write_wav

    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if manifest.get("voice_id") not in (None, voice_id):
        manifest = {}
    manifest.update({"voice_id": voice_id, "model_id": model_id, "rate": 24000})
    items = manifest.setdefault("items", {})
    for bid, text in BANK.items():
        if (only and bid not in only) or len(items.get(bid, [])) >= takes:
            continue
        files = []
        for take in range(takes):
            audio, rate, _ = tts_with_timestamps(text, voice_id, model_id=model_id, output_format="pcm_24000",
                                                 seed=take + 1)
            a, b = energy_bounds(audio, rate, threshold_db=-45)
            pad = int(0.02 * rate)
            clip = audio[max(0, int(a * rate) - pad): int(b * rate) + pad]
            peak = float(np.max(np.abs(clip))) or 1.0
            clip = clip * (10 ** (-6 / 20) / peak)
            name = f"{bid}-{take + 1}.wav"
            write_wav(out / name, clip, rate, bits=16)
            files.append({"file": name, "ms": int(len(clip) / rate * 1000)})
        items[bid] = files
        manifest_path.write_text(json.dumps(manifest, indent=1))
    return manifest


async def stream_wav_realtime(scribe: Scribe, pcm16: bytes, *, chunk_ms: int = 100, speed: float = 1.0) -> None:
    """Test helper: feed a 16 kHz PCM16 buffer to Scribe at (roughly) real time."""
    step = 16000 * 2 * chunk_ms // 1000
    for i in range(0, len(pcm16), step):
        await scribe.send_audio(pcm16[i:i + step])
        await asyncio.sleep(chunk_ms / 1000 / speed)
