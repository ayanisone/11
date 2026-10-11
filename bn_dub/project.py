"""Project state: the session file. Every stage reads and writes this, so the UI can edit between stages."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from .config import settings

SCHEMA_VERSION = 1


@dataclass
class Segment:
    id: int
    start: float
    end: float
    speaker: str
    source_text: str
    target_text: str = ""
    romanised: str = ""
    # Filled by the TTS / fit stages
    tts_path: Optional[str] = None  # raw TTS clip (as generated)
    fit_path: Optional[str] = None  # clip after time-stretch to the slot
    tts_duration: Optional[float] = None
    fit_ratio: Optional[float] = None  # tts_duration / slot
    status: str = "new"  # new | translated | generated | verified | warn | failed
    qa_similarity: Optional[float] = None
    qa_heard: str = ""
    notes: str = ""
    locked: bool = False  # user-approved; stages won't overwrite target_text / audio

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class Speaker:
    id: str
    voice_id: str = ""
    voice_name: str = ""
    label: str = ""


@dataclass
class Project:
    name: str
    source_path: str
    source_lang: str = "en"
    target_lang: str = settings.target_lang
    duration: float = 0.0
    has_video: bool = False
    audio_path: Optional[str] = None  # extracted full-mix wav
    vocals_path: Optional[str] = None
    background_path: Optional[str] = None
    background_mode: str = "isolate"  # isolate | demucs | duck | none
    segments: list[Segment] = field(default_factory=list)
    speakers: list[Speaker] = field(default_factory=list)
    # Mix settings (dB)
    vocal_gain_db: float = 0.0
    background_gain_db: float = -3.0
    duck_db: float = -12.0
    output_audio: Optional[str] = None
    output_video: Optional[str] = None
    schema_version: int = SCHEMA_VERSION

    # ----- persistence -----
    @property
    def dir(self) -> Path:
        return settings.projects_dir / self.name

    @property
    def file(self) -> Path:
        return self.dir / "project.json"

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, name: str) -> "Project":
        path = settings.projects_dir / name / "project.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["segments"] = [Segment(**s) for s in data.get("segments", [])]
        data["speakers"] = [Speaker(**s) for s in data.get("speakers", [])]
        return cls(**data)

    @classmethod
    def exists(cls, name: str) -> bool:
        return (settings.projects_dir / name / "project.json").exists()

    @classmethod
    def list_names(cls) -> list[str]:
        if not settings.projects_dir.exists():
            return []
        return sorted(p.name for p in settings.projects_dir.iterdir() if (p / "project.json").exists())

    # ----- helpers -----
    def segment(self, seg_id: int) -> Segment:
        for s in self.segments:
            if s.id == seg_id:
                return s
        raise KeyError(f"segment {seg_id} not found")

    def speaker(self, speaker_id: str) -> Speaker:
        for sp in self.speakers:
            if sp.id == speaker_id:
                return sp
        sp = Speaker(id=speaker_id, label=speaker_id)
        self.speakers.append(sp)
        return sp

    def next_start(self, seg: Segment) -> Optional[float]:
        """Start time of the following segment on the timeline, or None if this is the last one."""
        later = [s.start for s in self.segments if s.start > seg.start and s.id != seg.id]
        return min(later) if later else None
