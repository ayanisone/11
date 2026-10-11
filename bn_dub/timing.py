"""Pure timing math: how a generated clip gets fitted into its slot on the timeline. No I/O."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import settings


@dataclass
class FitPlan:
    slot: float          # seconds available (segment duration + borrowable gap)
    ratio: float         # tts_duration / slot; >1 means the clip is too long
    stretch: float       # atempo factor to apply (1.0 = none)
    action: str          # "ok" | "stretch" | "shorten" | "hard"
    shorten_pct: int     # when action == "shorten": how much shorter the line should be, in %


def slot_for(start: float, end: float, next_start: Optional[float], *, pad: Optional[float] = None,
             max_borrow: float = 1.5) -> float:
    """Time the dubbed line may occupy: its own duration plus the silence before the next line.

    We borrow at most `max_borrow` seconds of the following gap, minus a small pad so lines don't touch.
    """
    pad = settings.slot_pad if pad is None else pad
    base = max(0.0, end - start)
    if next_start is None:
        return base + max_borrow
    gap = max(0.0, next_start - end - pad)
    return base + min(gap, max_borrow)


def plan_fit(tts_duration: float, slot: float, *, max_stretch: Optional[float] = None,
             hard_stretch: Optional[float] = None) -> FitPlan:
    """Decide between stretching and re-translating.

    - Shorter than the slot: leave it (natural pauses are fine) unless it's absurdly short (<60%), then slow a touch.
    - Up to `max_stretch` too long: speed up to fit exactly.
    - Beyond that: ask for a shorter line. The caller retries, then falls back to `hard_stretch`.
    """
    max_stretch = settings.max_stretch if max_stretch is None else max_stretch
    hard_stretch = settings.hard_stretch if hard_stretch is None else hard_stretch
    if slot <= 0 or tts_duration <= 0:
        return FitPlan(slot=slot, ratio=0.0, stretch=1.0, action="ok", shorten_pct=0)
    ratio = tts_duration / slot
    if ratio <= 1.0:
        if ratio < 0.6:
            # Slow down only as far as max_stretch allows; a 0.4-ratio clip stays short rather than sounding drunk.
            stretch = max(ratio, 1.0 / max_stretch)
            return FitPlan(slot, ratio, stretch, "stretch", 0)
        return FitPlan(slot, ratio, 1.0, "ok", 0)
    if ratio <= max_stretch:
        return FitPlan(slot, ratio, ratio, "stretch", 0)
    # Too long even at max stretch: target a line that lands at max_stretch after stretching.
    target = slot * max_stretch
    pct = int(round((1.0 - target / tts_duration) * 100))
    return FitPlan(slot, ratio, min(ratio, hard_stretch), "shorten", max(5, pct))


def hard_fit(tts_duration: float, slot: float, *, hard_stretch: Optional[float] = None) -> FitPlan:
    """Last resort after shortening failed: clamp to the hard ceiling and let it spill."""
    hard_stretch = settings.hard_stretch if hard_stretch is None else hard_stretch
    ratio = tts_duration / slot if slot > 0 else 0.0
    return FitPlan(slot, ratio, min(max(ratio, 1.0), hard_stretch), "hard", 0)
