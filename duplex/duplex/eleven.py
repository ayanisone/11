"""Thin ElevenLabs REST calls: TTS with character timestamps, forced alignment, Scribe diarization."""

from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Optional

import numpy as np
import requests

API = os.environ.get("ELEVENLABS_API_BASE", "https://api.elevenlabs.io")


class ElevenError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"ElevenLabs HTTP {status}: {body[:500]}")
        self.status = status


def _key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SystemExit("ELEVENLABS_API_KEY is not set")
    return key


def _post(path: str, *, params=None, json=None, files=None, data=None, timeout=180, tries=4) -> requests.Response:
    delay = 2.0
    for attempt in range(tries):
        r = requests.post(f"{API}{path}", params=params, json=json, files=files, data=data, timeout=timeout,
                          headers={"xi-api-key": _key()})
        if r.status_code < 400:
            return r
        if r.status_code in (429, 500, 502, 503, 504) and attempt < tries - 1:
            time.sleep(delay)
            delay *= 2
            continue
        raise ElevenError(r.status_code, r.text)
    raise AssertionError("unreachable")


def pcm_rate(output_format: str) -> int:
    if not output_format.startswith("pcm_"):
        raise ValueError("use a pcm_* output format (e.g. pcm_44100) so clips can be placed sample-accurately")
    return int(output_format.split("_")[1])


def tts_with_timestamps(text: str, voice_id: str, *, model_id: str, output_format: str = "pcm_44100",
                        previous_text: Optional[str] = None, next_text: Optional[str] = None,
                        seed: Optional[int] = None, language_code: Optional[str] = None,
                        voice_settings: Optional[dict] = None) -> tuple[np.ndarray, int, Optional[dict]]:
    """One line of speech plus its character alignment. Returns (float32 mono audio, rate, alignment|None)."""
    body: dict = {"text": text, "model_id": model_id}
    for k, v in (("previous_text", previous_text), ("next_text", next_text), ("seed", seed),
                 ("language_code", language_code), ("voice_settings", voice_settings)):
        if v is not None:
            body[k] = v
    r = _post(f"/v1/text-to-speech/{voice_id}/with-timestamps", params={"output_format": output_format}, json=body)
    payload = r.json()
    raw = base64.b64decode(payload["audio_base64"])
    audio = np.frombuffer(raw, "<i2").astype(np.float32) / 32768
    return audio, pcm_rate(output_format), payload.get("alignment") or payload.get("normalized_alignment")


def forced_alignment(wav_path: Path, text: str) -> list[dict]:
    """Word timings for known text in a file: [{text, start, end, loss}]."""
    with open(wav_path, "rb") as f:
        r = _post("/v1/forced-alignment", files={"file": (wav_path.name, f, "audio/wav")}, data={"text": text})
    return [w for w in r.json().get("words", []) if w.get("text", "").strip()]


def scribe(path: Path, *, model_id: str = "scribe_v1", diarize: bool = True, num_speakers: Optional[int] = None,
           language_code: Optional[str] = None) -> dict:
    """Speech-to-text with word timestamps and speaker ids (raw JSON)."""
    data = {"model_id": model_id, "diarize": str(diarize).lower(), "timestamps_granularity": "word",
            "tag_audio_events": "true"}
    if num_speakers:
        data["num_speakers"] = str(num_speakers)
    if language_code:
        data["language_code"] = language_code
    with open(path, "rb") as f:
        r = _post("/v1/speech-to-text", files={"file": (path.name, f)}, data=data, timeout=600)
    return r.json()
