"""Lazy API clients so the offline parts (tests, timeline math, UI load) never need keys."""

from __future__ import annotations

from functools import lru_cache

from .config import settings


@lru_cache(maxsize=1)
def elevenlabs():
    from elevenlabs.client import ElevenLabs

    return ElevenLabs(api_key=settings.require_elevenlabs())


@lru_cache(maxsize=1)
def anthropic():
    import anthropic as _anthropic

    return _anthropic.Anthropic(api_key=settings.require_anthropic())
