"""Stage 7: lay the fitted clips on the timeline, sit them over the background stem, print the mix."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import media
from .config import settings
from .project import Project


def render(project: Project) -> Project:
    rate = settings.sample_rate
    clips = [(s.start, media.decode(s.fit_path, channels=1)) for s in project.segments if s.fit_path]
    total = project.duration or max((s.end for s in project.segments), default=0.0)
    # Let the last line spill past the original end if it had to.
    for start, clip in clips:
        total = max(total, start + len(clip) / rate)

    vocals = media.assemble(clips, total, rate=rate) * media.db_to_gain(project.vocal_gain_db)
    out = media.to_stereo(vocals)

    if project.background_path:
        bg = media.decode(project.background_path, channels=2)
        if len(bg) < len(out):
            bg = np.pad(bg, ((0, len(out) - len(bg)), (0, 0)))
        bg = bg[:len(out)] * media.db_to_gain(project.background_gain_db)
        if project.background_mode == "duck":
            bg = media.duck(bg, vocals, rate=rate, amount_db=project.duck_db)
        elif project.background_mode == "isolate" and project.slot_duck_db < 0:
            regions = [(s.start, s.end) for s in project.segments]
            bg = media.attenuate_regions(bg, regions, rate=rate, amount_db=project.slot_duck_db)
        out = out + bg

    out = media.limit(out, ceiling_db=-1.0)
    out_dir = project.dir / "out"
    audio_path = media.write_wav(out_dir / "dub.wav", out)
    project.output_audio = str(audio_path)
    if project.has_video:
        project.output_video = str(media.mux(project.source_path, audio_path, out_dir / "dubbed.mp4"))
    else:
        project.output_video = None
    project.save()
    return project
