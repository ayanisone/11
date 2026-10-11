"""Stage 1: split the full mix into a vocal stem and a background (music + effects) stem."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import media
from .clients import elevenlabs
from .config import settings
from .project import Project


def isolate_vocals(audio_path: Path, dst: Path) -> Path:
    """ElevenLabs Voice Isolator: returns speech only. Output is mp3, so we decode and re-save as wav."""
    client = elevenlabs()
    with open(audio_path, "rb") as f:
        chunks = client.audio_isolation.convert(audio=(audio_path.name, f.read(), "audio/wav"))
    tmp = dst.with_suffix(".isolated.mp3")
    with open(tmp, "wb") as out:
        for chunk in chunks:
            out.write(chunk)
    vocals = media.decode(tmp, channels=2)
    media.write_wav(dst, vocals)
    tmp.unlink(missing_ok=True)
    return dst


def demucs_split(audio_path: Path, out_dir: Path) -> tuple[Path, Path]:
    """Optional local separation with demucs (pip install demucs). Better background, needs a GPU to be quick."""
    if not shutil.which("demucs"):
        raise RuntimeError("demucs is not installed; pip install demucs, or choose another background mode")
    subprocess.run(["demucs", "--two-stems", "vocals", "-o", str(out_dir), str(audio_path)], check=True)
    # demucs writes <out>/<model>/<track>/{vocals,no_vocals}.wav
    track = next(out_dir.glob("*/" + audio_path.stem))
    return track / "vocals.wav", track / "no_vocals.wav"


def run(project: Project, mode: str | None = None) -> Project:
    mode = mode or project.background_mode
    project.background_mode = mode
    audio = Path(project.audio_path)
    vocals_path = project.dir / "vocals.wav"
    bg_path = project.dir / "background.wav"

    if mode == "demucs":
        v, b = demucs_split(audio, project.dir / "demucs")
        media.write_wav(vocals_path, media.decode(v, channels=2))
        media.write_wav(bg_path, media.decode(b, channels=2))
    elif mode == "isolate":
        isolate_vocals(audio, vocals_path)
        full = media.decode(audio, channels=2)
        voc = media.decode(vocals_path, channels=2)
        media.write_wav(bg_path, media.subtract_aligned(full, voc, rate=settings.sample_rate))
    elif mode == "duck":
        # Keep the original mix as the bed; the mix stage ducks it under the new vocals.
        media.write_wav(vocals_path, media.decode(audio, channels=1))
        media.write_wav(bg_path, media.decode(audio, channels=2))
    elif mode == "none":
        media.write_wav(vocals_path, media.decode(audio, channels=1))
        bg_path = None
    else:
        raise ValueError(f"unknown background mode: {mode}")

    project.vocals_path = str(vocals_path)
    project.background_path = str(bg_path) if bg_path else None
    project.save()
    return project
