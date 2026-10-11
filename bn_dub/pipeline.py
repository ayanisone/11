"""Stage orchestration. Each stage is idempotent on the project file, so the UI can re-run any one of them."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Optional

from . import media, mix, separate, transcribe, translate, tts, verify
from .config import settings
from .project import Project

Progress = Callable[[str], None]


def _noop(_: str) -> None:
    pass


def create(name: str, source: str | Path, *, source_lang: str = "en", target_lang: Optional[str] = None,
           background_mode: str = "isolate") -> Project:
    """Ingest: copy the source into the project folder, extract the full mix as wav."""
    source = Path(source)
    project = Project(name=name, source_path="", source_lang=source_lang,
                      target_lang=target_lang or settings.target_lang, background_mode=background_mode)
    project.dir.mkdir(parents=True, exist_ok=True)
    dst = project.dir / ("source" + source.suffix.lower())
    if source.resolve() != dst.resolve():
        shutil.copy2(source, dst)
    project.source_path = str(dst)
    project.has_video = media.has_video(dst)
    project.duration = media.duration(dst)
    project.audio_path = str(media.extract_audio(dst, project.dir / "mix.wav"))
    project.save()
    return project


def run_all(project: Project, *, progress: Progress = _noop, do_verify: bool = True) -> Project:
    progress("separating vocals from background")
    separate.run(project)
    progress("transcribing")
    transcribe.run(project)
    progress(f"translating {len(project.segments)} lines")
    translate.run(project)
    progress("generating speech")
    tts.run(project)
    if do_verify:
        progress("verifying")
        verify.run(project)
    progress("mixing")
    mix.render(project)
    progress("done")
    return project
