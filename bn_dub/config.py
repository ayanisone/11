"""Runtime settings, read from the environment (and a local .env if present)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal .env loader so the app works without python-dotenv."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass
class Settings:
    tts_model: str = field(default_factory=lambda: os.environ.get("BN_DUB_TTS_MODEL", "eleven_v3"))
    stt_model: str = field(default_factory=lambda: os.environ.get("BN_DUB_STT_MODEL", "scribe_v1"))
    claude_model: str = field(default_factory=lambda: os.environ.get("BN_DUB_CLAUDE_MODEL", "claude-opus-5-5"))

    projects_dir: Path = field(default_factory=lambda: Path(os.environ.get("BN_DUB_PROJECTS_DIR", "projects")))

    target_lang: str = "bn"
    sample_rate: int = 44100

    # Timing: how far we let time-stretch go before asking the translator for a shorter line.
    # 1.15 means +/-15% (atempo 0.87..1.15). Past that, stretched speech starts to sound processed.
    max_stretch: float = 1.15
    # Hard ceiling applied after shortening attempts failed; audible but still intelligible.
    hard_stretch: float = 1.35
    # Pause between a segment's end and the next segment's start that we're allowed to borrow (s).
    slot_pad: float = 0.08

    # Segmenting
    max_segment_secs: float = 12.0
    max_segment_chars: int = 220
    split_gap_secs: float = 0.6

    # QA
    min_similarity: float = 0.72
    max_tts_attempts: int = 3

    # Keys are read live so they can be set after import (Colab secrets cell, UI key fields).
    @property
    def elevenlabs_api_key(self) -> str:
        return os.environ.get("ELEVENLABS_API_KEY", "").strip()

    @property
    def anthropic_api_key(self) -> str:
        return os.environ.get("ANTHROPIC_API_KEY", "").strip()

    def set_keys(self, elevenlabs: str = "", anthropic: str = "") -> None:
        if elevenlabs.strip():
            os.environ["ELEVENLABS_API_KEY"] = elevenlabs.strip()
        if anthropic.strip():
            os.environ["ANTHROPIC_API_KEY"] = anthropic.strip()
        from . import clients

        clients.elevenlabs.cache_clear()
        clients.anthropic.cache_clear()

    def require_elevenlabs(self) -> str:
        if not self.elevenlabs_api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not set (see .env.example).")
        return self.elevenlabs_api_key

    def require_anthropic(self) -> str:
        if not self.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set (see .env.example).")
        return self.anthropic_api_key


settings = Settings()
