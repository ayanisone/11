"""Stage 4: speak each Bengali line with ElevenLabs, then stage 5: fit it to its slot."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import media, timing, translate
from .clients import elevenlabs
from .config import settings
from .project import Project, Segment

# Models that accept `language_code`. v3/v4 auto-detect from the script; the SDK rejects the field on some.
_LANG_ENFORCING = {"eleven_turbo_v2_5", "eleven_flash_v2_5"}


def _voice_settings(stability: float = 0.5):
    from elevenlabs.types import VoiceSettings

    return VoiceSettings(stability=stability, similarity_boost=0.8, style=0.0, use_speaker_boost=True)


def synthesize(text: str, voice_id: str, dst: Path, *, language: Optional[str] = None,
               model_id: Optional[str] = None, stability: float = 0.5) -> Path:
    """Generate one clip. Returns a mono wav at the project sample rate."""
    client = elevenlabs()
    model_id = model_id or settings.tts_model
    kwargs = dict(text=text, model_id=model_id, output_format="mp3_44100_128", voice_settings=_voice_settings(stability))
    if language and model_id in _LANG_ENFORCING:
        kwargs["language_code"] = language
    audio = client.text_to_speech.convert(voice_id, **kwargs)
    tmp = dst.with_suffix(".mp3")
    with open(tmp, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    media.write_wav(dst, media.decode(tmp, channels=1))
    tmp.unlink(missing_ok=True)
    return dst


def clone_voice(name: str, sample_paths: list[Path], description: str = "") -> str:
    """Instant voice clone from the speaker's own isolated audio. Needs a plan that includes IVC."""
    client = elevenlabs()
    files = [(p.name, p.read_bytes(), "audio/wav") for p in sample_paths]
    resp = client.voices.ivc.create(name=name, files=files, description=description or None,
                                   remove_background_noise=True)
    return resp.voice_id


def list_voices() -> list[tuple[str, str]]:
    """(label, voice_id) pairs for the UI dropdown."""
    client = elevenlabs()
    voices = client.voices.get_all().voices
    out = []
    for v in voices:
        labels = v.labels or {}
        lang = labels.get("language", "")
        out.append((f"{v.name} [{v.category or ''}{' ' + lang if lang else ''}]", v.voice_id))
    return out


def fit_segment(project: Project, seg: Segment) -> timing.FitPlan:
    """Stretch the raw TTS clip into the slot. Caller decides what to do with a `shorten` verdict."""
    slot = timing.slot_for(seg.start, seg.end, project.next_start(seg))
    plan = timing.plan_fit(seg.tts_duration or 0.0, slot)
    if plan.action == "shorten":
        return plan
    _apply(project, seg, plan)
    return plan


def _apply(project: Project, seg: Segment, plan: timing.FitPlan) -> None:
    fit_path = project.dir / "segments" / f"{seg.id:04d}.fit.wav"
    if abs(plan.stretch - 1.0) < 0.01:
        media.write_wav(fit_path, media.decode(seg.tts_path, channels=1))
    else:
        media.time_stretch(seg.tts_path, fit_path, plan.stretch)
    seg.fit_path = str(fit_path)
    seg.fit_ratio = round(plan.ratio, 3)


def generate_segment(project: Project, seg: Segment, *, allow_reshorten: bool = True) -> Segment:
    """TTS + fit for one line, re-translating shorter when the clip can't be stretched into the slot."""
    if not seg.target_text:
        seg.status, seg.notes = "failed", "no target text"
        return seg
    voice = project.speaker(seg.speaker).voice_id
    if not voice:
        seg.status, seg.notes = "failed", f"no voice set for {seg.speaker}"
        return seg
    seg_dir = project.dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    attempts = settings.max_tts_attempts if allow_reshorten else 1
    for attempt in range(attempts):
        raw = synthesize(seg.target_text, voice, seg_dir / f"{seg.id:04d}.tts.wav", language=project.target_lang)
        seg.tts_path = str(raw)
        seg.tts_duration = round(media.duration(raw), 3)
        plan = fit_segment(project, seg)
        if plan.action != "shorten":
            seg.status = "generated"
            seg.notes = "" if plan.action == "ok" else f"stretched x{plan.stretch:.2f}"
            return seg
        if attempt == attempts - 1 or seg.locked:
            break
        # Too long: ask for a tighter line and try again.
        lines = translate.translate_segments(project, [seg], shorten={seg.id: plan.shorten_pct})
        if seg.id in lines:
            seg.target_text, seg.romanised = lines[seg.id].target, lines[seg.id].romanised
    # Could not get it short enough; clamp to the hard ceiling and flag it.
    slot = timing.slot_for(seg.start, seg.end, project.next_start(seg))
    plan = timing.hard_fit(seg.tts_duration or 0.0, slot)
    _apply(project, seg, plan)
    seg.status = "warn"
    seg.notes = f"over slot: x{plan.stretch:.2f} stretch, spills {max(0.0, (seg.tts_duration or 0) / plan.stretch - slot):.1f}s"
    return seg


def run(project: Project, ids: Optional[list[int]] = None) -> Project:
    for seg in project.segments:
        if ids is not None and seg.id not in ids:
            continue
        if seg.locked and seg.fit_path:
            continue
        generate_segment(project, seg)
        project.save()
    return project
