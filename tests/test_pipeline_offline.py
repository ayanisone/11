"""End-to-end without any API: ingest a synthetic video, fit fake TTS clips, render, mux."""

import subprocess

import numpy as np
import pytest

from bn_dub import media, mix, pipeline, tts
from bn_dub.config import settings
from bn_dub.project import Segment


@pytest.fixture
def synthetic_video(tmp_path):
    out = tmp_path / "test.mp4"
    subprocess.run([media.FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=6",
                    "-f", "lavfi", "-i", "color=c=blue:s=160x120:d=6", "-map", "1:v", "-map", "0:a",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)], check=True)
    return out


def test_ingest_fit_render_mux(tmp_path, synthetic_video, monkeypatch):
    monkeypatch.setattr(settings, "projects_dir", tmp_path / "projects")
    p = pipeline.create("e2e", synthetic_video)
    assert p.has_video and abs(p.duration - 6.0) < 0.1
    p.background_path = p.audio_path  # stand in for the separation stage

    seg_dir = p.dir / "segments"
    seg_dir.mkdir()
    t = np.arange(int(1.2 * settings.sample_rate)) / settings.sample_rate
    clip = (0.3 * np.sin(2 * np.pi * 880 * t)).astype(np.float32)
    for i, (s, e) in enumerate([(0.5, 1.5), (3.0, 4.0)], start=1):
        path = media.write_wav(seg_dir / f"{i:04d}.tts.wav", clip)
        p.segments.append(Segment(id=i, start=s, end=e, speaker="A", source_text="x", target_text="y",
                                  tts_path=str(path), tts_duration=1.2))

    for seg in p.segments:
        plan = tts.fit_segment(p, seg)
        # 1.2 s clip in a 2.5 s slot (1 s + borrowed gap) -> ratio 0.48 -> slowed to the tolerance floor
        assert plan.action == "stretch" and abs(plan.stretch - 1 / settings.max_stretch) < 1e-6
        assert seg.fit_path and abs(media.duration(seg.fit_path) - 1.2 * settings.max_stretch) < 0.05

    mix.render(p)
    assert p.output_audio and p.output_video
    assert abs(media.duration(p.output_video) - 6.0) < 0.15
    out = media.decode(p.output_audio, channels=1)
    assert media.peak(out) <= media.db_to_gain(-1.0) + 1e-3
    # the dub is audible where the clips were placed
    assert media.rms_db(out[int(0.6 * settings.sample_rate):int(1.4 * settings.sample_rate)]) > -30
