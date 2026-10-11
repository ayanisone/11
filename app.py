"""Gradio console for the Bengali dubbing chain.

Three tabs, in signal-flow order:
  1. Session  — load media, split stems, transcribe, assign a voice per speaker
  2. Script   — the editable cue sheet: review/edit translations, generate, verify, audition per line
  3. Mix      — gains, ducking, render, download

Run:  python app.py   (or  bn-dub ui)
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Optional

import gradio as gr

from bn_dub import mix, pipeline, separate, transcribe, translate, tts, verify
from bn_dub import media
from bn_dub.config import settings
from bn_dub.project import Project

HEADERS = ["id", "start", "end", "speaker", "source", "target", "romanised", "ratio", "status", "locked", "notes"]
SPEAKER_HEADERS = ["speaker", "voice_id", "voice_name"]


# ---------- helpers ----------

def _rows(p: Project) -> list[list]:
    return [[s.id, round(s.start, 2), round(s.end, 2), s.speaker, s.source_text, s.target_text, s.romanised,
             s.fit_ratio if s.fit_ratio is not None else "", s.status, bool(s.locked), s.notes] for s in p.segments]


def _speaker_rows(p: Project) -> list[list]:
    return [[sp.id, sp.voice_id, sp.voice_name] for sp in p.speakers]


def _ids(text: str) -> Optional[list[int]]:
    text = (text or "").strip()
    if not text:
        return None
    out: list[int] = []
    for part in text.replace(";", ",").split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def _summary(p: Project) -> str:
    n = len(p.segments)
    by = {}
    for s in p.segments:
        by[s.status] = by.get(s.status, 0) + 1
    parts = ", ".join(f"{k}: {v}" for k, v in sorted(by.items()))
    voices = ", ".join(f"{sp.id}→{sp.voice_name or sp.voice_id or '∅'}" for sp in p.speakers)
    return (f"**{p.name}** · {p.duration:.1f}s · {'video' if p.has_video else 'audio'} · {p.source_lang}→{p.target_lang} · "
            f"bg: {p.background_mode}\n\n{n} lines ({parts or 'none'})\n\nVoices: {voices or '—'}")


def _load(name: str) -> Project:
    if not name or not Project.exists(name):
        raise gr.Error("Load or create a project first.")
    return Project.load(name)


def _guard(fn):
    """Turn exceptions into a readable log line instead of a red toast with no detail."""
    def wrapped(*args):
        try:
            return fn(*args)
        except gr.Error:
            raise
        except Exception as e:  # noqa: BLE001
            raise gr.Error(f"{type(e).__name__}: {e}\n{traceback.format_exc()[-600:]}") from e
    return wrapped


def _refresh(p: Project):
    return p.name, _summary(p), _rows(p), _speaker_rows(p)


# ---------- tab 1: session ----------

@_guard
def create_project(name: str, file, source_lang: str, bg_mode: str, progress=gr.Progress()):
    if not name or not file:
        raise gr.Error("Give the project a name and upload a file.")
    name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name.strip())
    progress(0.05, "ingesting")
    p = pipeline.create(name, file, source_lang=source_lang, background_mode=bg_mode)
    progress(0.25, "separating stems")
    separate.run(p)
    progress(0.6, "transcribing")
    transcribe.run(p)
    progress(1.0, "done")
    return _refresh(p)


@_guard
def load_project(name: str):
    return _refresh(_load(name))


@_guard
def refresh_voices():
    choices = tts.list_voices()
    return gr.update(choices=choices, value=choices[0][1] if choices else None)


@_guard
def assign_voice(name: str, speaker: str, voice_id: str, voice_choices_state):
    p = _load(name)
    if not speaker or not voice_id:
        raise gr.Error("Pick a speaker and a voice.")
    sp = p.speaker(speaker)
    sp.voice_id = voice_id
    sp.voice_name = next((lbl for lbl, vid in (voice_choices_state or []) if vid == voice_id), voice_id)
    p.save()
    return _summary(p), _speaker_rows(p)


@_guard
def save_speakers(name: str, rows):
    p = _load(name)
    for row in rows or []:
        if not row or not row[0]:
            continue
        sp = p.speaker(str(row[0]))
        sp.voice_id = str(row[1] or "").strip()
        sp.voice_name = str(row[2] or "").strip() or sp.voice_id
    p.save()
    return _summary(p), _speaker_rows(p)


@_guard
def clone_speaker(name: str, speaker: str, progress=gr.Progress()):
    """Instant voice clone from up to ~60s of the speaker's own isolated lines."""
    p = _load(name)
    if not speaker:
        raise gr.Error("Pick a speaker.")
    segs = sorted((s for s in p.segments if s.speaker == speaker), key=lambda s: -s.duration)
    if not segs:
        raise gr.Error(f"No lines for {speaker}.")
    clip_dir = p.dir / "clone_samples"
    clip_dir.mkdir(exist_ok=True)
    paths, total = [], 0.0
    for s in segs:
        if total > 60:
            break
        dst = clip_dir / f"{speaker}_{s.id:04d}.wav"
        media.trim(p.vocals_path, dst, s.start, s.end)
        paths.append(dst)
        total += s.duration
    progress(0.5, "cloning")
    voice_id = tts.clone_voice(f"{p.name}-{speaker}", paths, description=f"IVC from {p.name}")
    sp = p.speaker(speaker)
    sp.voice_id, sp.voice_name = voice_id, f"clone:{speaker}"
    p.save()
    return _summary(p), _speaker_rows(p)


def speaker_choices(name: str):
    if not name or not Project.exists(name):
        return gr.update(choices=[])
    p = Project.load(name)
    ids = [sp.id for sp in p.speakers]
    return gr.update(choices=ids, value=ids[0] if ids else None)


# ---------- tab 2: script ----------

@_guard
def save_edits(name: str, rows):
    """Write the cue sheet back. Only text, times, speaker, lock are user-editable; the rest is derived."""
    p = _load(name)
    for row in rows or []:
        try:
            seg = p.segment(int(row[0]))
        except (KeyError, ValueError, TypeError):
            continue
        new_target = str(row[5] or "")
        if new_target != seg.target_text:
            seg.target_text = new_target
            seg.status = "translated" if new_target else "new"
            seg.tts_path = seg.fit_path = None
        seg.romanised = str(row[6] or "")
        seg.start, seg.end = float(row[1]), float(row[2])
        seg.speaker = str(row[3] or seg.speaker)
        seg.locked = str(row[9]).lower() in {"true", "1", "yes"}
        p.speaker(seg.speaker)
    p.save()
    return _summary(p), _rows(p), _speaker_rows(p)


@_guard
def do_translate(name: str, ids_text: str, progress=gr.Progress()):
    p = _load(name)
    progress(0.1, "translating")
    translate.run(p, _ids(ids_text))
    return _summary(p), _rows(p)


@_guard
def do_generate(name: str, ids_text: str, progress=gr.Progress()):
    p = _load(name)
    ids = _ids(ids_text)
    todo = [s for s in p.segments if ids is None or s.id in ids]
    for i, s in enumerate(todo):
        progress(i / max(1, len(todo)), f"line {s.id}")
        if s.locked and s.fit_path:
            continue
        tts.generate_segment(p, s)
        p.save()
    return _summary(p), _rows(p)


@_guard
def do_verify(name: str, ids_text: str, fix: bool, progress=gr.Progress()):
    p = _load(name)
    progress(0.1, "back-transcribing")
    verify.run(p, _ids(ids_text), fix=fix)
    return _summary(p), _rows(p)


@_guard
def audition(name: str, seg_id: float):
    """Original slot vs. fitted dub for one line, side by side."""
    p = _load(name)
    seg = p.segment(int(seg_id))
    orig = p.dir / "audition" / f"{seg.id:04d}.orig.wav"
    orig.parent.mkdir(exist_ok=True)
    media.trim(p.vocals_path or p.audio_path, orig, seg.start, seg.end)
    info = (f"**{seg.id}** {seg.speaker} · slot {seg.duration:.2f}s · tts {seg.tts_duration or 0:.2f}s · "
            f"ratio {seg.fit_ratio or '—'} · {seg.status}\n\n{seg.source_text}\n\n**{seg.target_text}**\n\n"
            f"_{seg.romanised}_\n\nQA heard: {seg.qa_heard or '—'} ({seg.qa_similarity if seg.qa_similarity is not None else '—'})")
    return str(orig), (seg.fit_path or None), info


# ---------- tab 3: mix ----------

@_guard
def set_background(name: str, bg_mode: str, progress=gr.Progress()):
    p = _load(name)
    progress(0.2, f"re-separating ({bg_mode})")
    separate.run(p, bg_mode)
    return _summary(p)


@_guard
def do_render(name: str, vocal_db: float, bg_db: float, duck_db: float, progress=gr.Progress()):
    p = _load(name)
    p.vocal_gain_db, p.background_gain_db, p.duck_db = float(vocal_db), float(bg_db), float(duck_db)
    missing = [s.id for s in p.segments if not s.fit_path]
    progress(0.2, "rendering")
    mix.render(p)
    note = f"Rendered. {len(p.segments) - len(missing)} lines placed." + (f" Missing audio for: {missing}" if missing else "")
    return note, p.output_audio, p.output_video, [f for f in (p.output_audio, p.output_video) if f]


@_guard
def do_run_all(name: str, progress=gr.Progress()):
    p = _load(name)
    steps = iter([0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
    pipeline.run_all(p, progress=lambda msg: progress(next(steps, 1.0), msg))
    return _summary(p), _rows(p), p.output_audio, p.output_video


# ---------- UI ----------

def build() -> gr.Blocks:
    with gr.Blocks(title="bn-dub · Bengali dubbing console") as demo:
        gr.Markdown("# bn-dub — Bengali dubbing console\n"
                    "Separate → transcribe → translate → speak → fit → verify → mix. Edit the cue sheet between any two stages.")
        project_name = gr.State("")
        voice_choices = gr.State([])

        with gr.Row():
            summary = gr.Markdown("_No project loaded._")

        with gr.Tabs():
            # ----- tab 1
            with gr.Tab("1 · Session"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### New project")
                        new_name = gr.Textbox(label="Project name", placeholder="ep01_heart_health")
                        new_file = gr.File(label="Source video or audio", type="filepath")
                        src_lang = gr.Dropdown(label="Source language", choices=["en", "hi", "mr", "as", "ta", "te", "kn",
                                               "ml", "gu", "pa", "or"], value="en")
                        bg_mode = gr.Radio(label="Background stem", choices=["isolate", "demucs", "duck", "none"], value="isolate",
                                           info="isolate: ElevenLabs voice isolator, background = mix − vocals · demucs: local, "
                                                "cleaner · duck: keep original mix, duck under new VO · none: VO only")
                        create_btn = gr.Button("Create → separate → transcribe", variant="primary")
                    with gr.Column():
                        gr.Markdown("### Existing project")
                        existing = gr.Dropdown(label="Project", choices=Project.list_names(), allow_custom_value=True)
                        load_btn = gr.Button("Load")
                        run_all_btn = gr.Button("Run everything (translate → speak → verify → mix)", variant="secondary")

                gr.Markdown("### Voices per speaker")
                with gr.Row():
                    speaker_dd = gr.Dropdown(label="Speaker", choices=[])
                    voice_dd = gr.Dropdown(label="Voice", choices=[], allow_custom_value=True)
                    voices_btn = gr.Button("Fetch voices")
                    assign_btn = gr.Button("Assign")
                    clone_btn = gr.Button("Clone this speaker (IVC)")
                speaker_table = gr.Dataframe(headers=SPEAKER_HEADERS, datatype=["str", "str", "str"], type="array",
                                             interactive=True, label="Speakers (voice_id editable)")
                save_speakers_btn = gr.Button("Save speaker table")

            # ----- tab 2
            with gr.Tab("2 · Script"):
                gr.Markdown("Edit **target**, **romanised**, **start/end**, **speaker**, **locked**; then *Save edits*. "
                            "Locked lines are never re-translated or regenerated. `ratio` = TTS length ÷ slot "
                            f"(≤ {settings.max_stretch} is fitted by time-stretch; above that the translator is asked for a shorter line).")
                table = gr.Dataframe(headers=HEADERS,
                                     datatype=["number", "number", "number", "str", "str", "str", "str", "str", "str", "bool", "str"],
                                     type="array", interactive=True, wrap=True, label="Cue sheet",
                                     column_widths=["4%", "6%", "6%", "8%", "18%", "18%", "14%", "5%", "7%", "5%", "9%"])
                with gr.Row():
                    save_btn = gr.Button("Save edits", variant="primary")
                    ids_box = gr.Textbox(label="Line ids (blank = all; e.g. 3, 7-9)", scale=2)
                    translate_btn = gr.Button("Translate")
                    generate_btn = gr.Button("Generate")
                    fix_chk = gr.Checkbox(label="auto-fix on QA miss", value=True)
                    verify_btn = gr.Button("Verify")
                gr.Markdown("### Audition")
                with gr.Row():
                    aud_id = gr.Number(label="Line id", value=1, precision=0)
                    aud_btn = gr.Button("Load line")
                with gr.Row():
                    aud_orig = gr.Audio(label="Original (isolated vocal)", type="filepath")
                    aud_dub = gr.Audio(label="Dub (fitted)", type="filepath")
                aud_info = gr.Markdown()

            # ----- tab 3
            with gr.Tab("3 · Mix"):
                with gr.Row():
                    bg_mode2 = gr.Radio(label="Background stem", choices=["isolate", "demucs", "duck", "none"], value="isolate")
                    bg_btn = gr.Button("Re-separate")
                with gr.Row():
                    vocal_db = gr.Slider(-12, 12, value=0, step=0.5, label="Dub vocal gain (dB)")
                    bg_db = gr.Slider(-30, 6, value=-3, step=0.5, label="Background gain (dB)")
                    duck_db = gr.Slider(-30, 0, value=-12, step=1, label="Duck amount (dB, 'duck' mode only)")
                render_btn = gr.Button("Render", variant="primary")
                render_note = gr.Markdown()
                out_audio = gr.Audio(label="Dub mix", type="filepath")
                out_video = gr.Video(label="Dubbed video")
                out_files = gr.File(label="Download", file_count="multiple")

        # ----- wiring
        refresh_outputs = [project_name, summary, table, speaker_table]
        create_btn.click(create_project, [new_name, new_file, src_lang, bg_mode], refresh_outputs) \
            .then(speaker_choices, project_name, speaker_dd) \
            .then(lambda: gr.update(choices=Project.list_names()), None, existing)
        load_btn.click(load_project, existing, refresh_outputs).then(speaker_choices, project_name, speaker_dd)
        voices_btn.click(refresh_voices, None, voice_dd).then(lambda: tts.list_voices(), None, voice_choices)
        assign_btn.click(assign_voice, [project_name, speaker_dd, voice_dd, voice_choices], [summary, speaker_table])
        save_speakers_btn.click(save_speakers, [project_name, speaker_table], [summary, speaker_table])
        clone_btn.click(clone_speaker, [project_name, speaker_dd], [summary, speaker_table])
        run_all_btn.click(do_run_all, project_name, [summary, table, out_audio, out_video])

        save_btn.click(save_edits, [project_name, table], [summary, table, speaker_table])
        translate_btn.click(do_translate, [project_name, ids_box], [summary, table])
        generate_btn.click(do_generate, [project_name, ids_box], [summary, table])
        verify_btn.click(do_verify, [project_name, ids_box, fix_chk], [summary, table])
        aud_btn.click(audition, [project_name, aud_id], [aud_orig, aud_dub, aud_info])

        bg_btn.click(set_background, [project_name, bg_mode2], summary)
        render_btn.click(do_render, [project_name, vocal_db, bg_db, duck_db], [render_note, out_audio, out_video, out_files])
    return demo


def main(server_port: int = 7860, share: bool = False) -> None:
    build().launch(server_port=server_port, share=share, show_error=True)


if __name__ == "__main__":
    main()
