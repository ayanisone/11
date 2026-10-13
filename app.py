"""bn-dub console — one page, in signal-flow order:

  file in → (stems · transcribe · translate · direct)  →  script you can edit  →  Generate dub  →  download

Run:  python app.py   (or  bn-dub ui)
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Optional

import gradio as gr

from bn_dub import media, pipeline, tts
from bn_dub.config import settings
from bn_dub.project import Project

HEADERS = ["id", "start", "end", "speaker", "original", "bengali (edit here)", "fit", "status", "lock"]
DTYPES = ["number", "number", "number", "str", "str", "str", "str", "str", "bool"]

CSS = """
:root, .gradio-container { --grad: linear-gradient(90deg, #7c3aed 0%, #c026d3 55%, #ec4899 100%); }
.gradio-container h1 { background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent;
                       font-weight: 800; letter-spacing: -0.01em; }
button.primary { background: var(--grad) !important; border: none !important; color: #fff !important; }
button.primary:hover { filter: brightness(1.08); }
input[type=range] { accent-color: #c026d3; }
input[type=range]::-webkit-slider-runnable-track { background: var(--grad); height: 6px; border-radius: 3px; }
input[type=range]::-moz-range-track { background: var(--grad); height: 6px; border-radius: 3px; }
.sim-note { background: rgba(124,58,237,.08); border-radius: 10px; padding: 10px 14px; }
"""

THEME = gr.themes.Soft(primary_hue="purple", secondary_hue="pink", neutral_hue="slate")


# ---------- helpers ----------

def _rows(p: Project) -> list[list]:
    return [[s.id, round(s.start, 2), round(s.end, 2), s.speaker, s.source_text, s.target_text,
             f"{s.fit_ratio:.2f}" if s.fit_ratio is not None else "", s.status, bool(s.locked)] for s in p.segments]


def _speaker_rows(p: Project) -> list[list]:
    rows = []
    for sp in p.speakers:
        if sp.is_clone:
            name = f"✅ clone of {sp.id}"
        elif sp.clone_error:
            name = f"❌ CLONE FAILED — {sp.clone_error}"
        else:
            name = sp.voice_name or "— not cloned yet —"
        rows.append([sp.id, name, sp.voice_id])
    return rows


def _clone_warning(p: Project) -> str:
    bad = [sp for sp in p.speakers if not sp.is_clone and not sp.voice_id]
    if not bad:
        return ""
    lines = "\n".join(f"- **{sp.id}**: {sp.clone_error or 'not cloned'}" for sp in bad)
    return ("\n\n❌ **Voice cloning failed — Generate is blocked until every speaker has a clone.** "
            "Fix the cause and press *Retry cloning*.\n" + lines)


def _summary(p: Project) -> str:
    by: dict[str, int] = {}
    for s in p.segments:
        by[s.status] = by.get(s.status, 0) + 1
    parts = " · ".join(f"{k} {v}" for k, v in sorted(by.items()))
    return (f"**{p.name}** — {p.duration:.1f}s {'video' if p.has_video else 'audio'} — detected **{p.source_lang}** → bn — "
            f"{len(p.segments)} lines ({parts or 'none'})")


def _load(name: str) -> Project:
    if not name or not Project.exists(name):
        raise gr.Error("Drop a file and press *Prepare script* first.")
    return Project.load(name)


def _guard(fn):
    def wrapped(*args):
        try:
            return fn(*args)
        except gr.Error:
            raise
        except Exception as e:  # noqa: BLE001
            raise gr.Error(f"{type(e).__name__}: {e}\n{traceback.format_exc()[-500:]}") from e
    return wrapped


def similarity_note(v: float) -> str:
    if v < 0.34:
        txt = "The dubbed voice sounds fully natural in Bengali; the original speaker's accent is not carried over."
    elif v < 0.67:
        txt = "The dubbed voice sounds natural in Bengali with light hints of the original speaker's accent coming through."
    else:
        txt = "The dubbed voice closely mimics the original speaker, including their accent and delivery quirks."
    return f'<div class="sim-note">{txt}</div>'


def key_status() -> str:
    e = "✅" if settings.elevenlabs_api_key else "❌"
    a = "✅" if settings.anthropic_api_key else "❌"
    return f"ElevenLabs {e} · Anthropic {a}"


# ---------- actions ----------

@_guard
def set_keys(eleven: str, anth: str):
    settings.set_keys(eleven or "", anth or "")
    return key_status(), "", ""


@_guard
def prepare(file, similarity: float, progress=gr.Progress()):
    """File → stems → transcript → translation → direction. Then auto-clone every speaker."""
    if not file:
        raise gr.Error("Drop a video or audio file first.")
    name = "".join(c if c.isalnum() or c in "-_" else "_" for c in Path(file).stem)[:40] or "project"
    progress(0.05, "ingesting")
    p = pipeline.create(name, file)
    p.speaker_similarity = float(similarity)
    steps = iter([0.15, 0.35, 0.6, 0.8])
    pipeline.prepare(p, progress=lambda m: progress(next(steps, 0.9), m))
    progress(0.9, "cloning speakers")
    _auto_clone(p)
    p.save()
    return p.name, _summary(p) + _clone_warning(p), _rows(p), _speaker_rows(p)


def _explain_clone_error(e: Exception) -> str:
    """Pull the useful sentence out of an ElevenLabs ApiError; otherwise the exception text."""
    body = getattr(e, "body", None)
    if isinstance(body, dict):
        detail = body.get("detail", body)
        if isinstance(detail, dict):
            msg = detail.get("message") or detail.get("status") or str(detail)
            code = detail.get("status") or detail.get("code") or ""
            if "voice_add" in str(code) or "cloning" in str(msg).lower() or "subscription" in str(msg).lower():
                msg += " — Instant Voice Cloning needs a paid ElevenLabs plan (Starter or above)."
            return str(msg)[:300]
    return f"{type(e).__name__}: {str(e)[:300]}"


def _auto_clone(p: Project, *, force: bool = False) -> None:
    """One instant clone per speaker from their own isolated lines. No stand-in voice: a failed clone leaves the
    speaker without a voice and Generate refuses to run until it's fixed."""
    for sp in p.speakers:
        if sp.is_clone or (sp.voice_id and not force and not sp.clone_error):
            continue
        try:
            segs = sorted((s for s in p.segments if s.speaker == sp.id), key=lambda s: -s.duration)
            if not segs:
                raise RuntimeError("no lines for this speaker")
            clip_dir = p.dir / "clone_samples"
            clip_dir.mkdir(exist_ok=True)
            paths, total = [], 0.0
            for s in segs:
                if total > 60:
                    break
                dst = clip_dir / f"{sp.id}_{s.id:04d}.wav"
                media.trim(p.vocals_path, dst, s.start, s.end)
                paths.append(dst)
                total += s.duration
            sp.voice_id = tts.clone_voice(f"{p.name}-{sp.id}", paths)
            sp.voice_name, sp.is_clone, sp.clone_error = f"clone of {sp.id}", True, ""
        except Exception as e:  # noqa: BLE001 — cloning is plan-gated; record why, leave the voice empty
            sp.clone_error = _explain_clone_error(e)
            sp.is_clone = False
            sp.voice_id, sp.voice_name = "", ""


@_guard
def retry_clone(name: str, progress=gr.Progress()):
    p = _load(name)
    progress(0.3, "cloning speakers")
    _auto_clone(p, force=True)
    for s in p.segments:  # new voice → previous takes are stale
        if not s.locked:
            s.tts_path = s.fit_path = None
    p.save()
    return _summary(p) + _clone_warning(p), _speaker_rows(p)


@_guard
def load_project(name: str):
    p = _load(name)
    return p.name, _summary(p) + _clone_warning(p), _rows(p), _speaker_rows(p), p.speaker_similarity


@_guard
def save_script(name: str, rows, speaker_rows):
    p = _load(name)
    for row in rows or []:
        try:
            seg = p.segment(int(row[0]))
        except (KeyError, ValueError, TypeError):
            continue
        new = str(row[5] or "")
        if new != seg.target_text:
            seg.target_text, seg.status = new, ("translated" if new else "new")
            seg.tts_path = seg.fit_path = None
        seg.start, seg.end = float(row[1]), float(row[2])
        seg.speaker = str(row[3] or seg.speaker)
        seg.locked = str(row[8]).lower() in {"true", "1", "yes"}
        p.speaker(seg.speaker)
    for row in speaker_rows or []:
        if row and row[0]:
            sp = p.speaker(str(row[0]))
            new_id = str(row[2] or "").strip()
            if new_id != sp.voice_id:  # user pasted their own voice_id: that's the voice now, no more warnings
                sp.voice_id, sp.voice_name = new_id, "custom"
                sp.is_clone, sp.clone_error = False, ""
    p.save()
    return _summary(p), _rows(p), _speaker_rows(p)


@_guard
def set_similarity(name: str, value: float):
    if name and Project.exists(name):
        p = Project.load(name)
        p.speaker_similarity = float(value)
        p.save()
    return similarity_note(value)


@_guard
def generate(name: str, rows, speaker_rows, progress=gr.Progress()):
    """Save edits, then speak → fit → verify → mix."""
    save_script(name, rows, speaker_rows)
    p = _load(name)
    missing = [sp for sp in p.speakers if not sp.voice_id]
    if missing:
        raise gr.Error("No cloned voice for: " + ", ".join(f"{sp.id} ({sp.clone_error or 'not cloned'})" for sp in missing)
                       + ". Press *Retry cloning* once the cause is fixed.")
    steps = iter([0.2, 0.6, 0.85])
    pipeline.produce(p, progress=lambda m: progress(next(steps, 0.9), m))
    warn = [s.id for s in p.segments if s.status in {"warn", "failed"}]
    note = _summary(p) + (f"\n\n⚠️ check lines {warn} (see *status*; audition them below)" if warn else "\n\n✅ dub rendered")
    return note, _rows(p), p.output_video, p.output_audio, [f for f in (p.output_video, p.output_audio) if f]


@_guard
def audition(name: str, seg_id: float):
    p = _load(name)
    seg = p.segment(int(seg_id))
    orig = p.dir / "audition" / f"{seg.id:04d}.orig.wav"
    orig.parent.mkdir(exist_ok=True)
    media.trim(p.vocals_path or p.audio_path, orig, seg.start, seg.end)
    info = (f"**Line {seg.id}** · {seg.speaker} · slot {seg.duration:.2f}s · dub {seg.tts_duration or 0:.2f}s · {seg.status}"
            f"{' · ' + seg.notes if seg.notes else ''}\n\n{seg.source_text}\n\n**{seg.target_text}**\n\n_{seg.romanised}_"
            + (f"\n\n🎬 {seg.direction}" if seg.direction else "")
            + (f"\n\n👂 heard: {seg.qa_heard} ({seg.qa_similarity})" if seg.qa_heard else ""))
    return str(orig), (seg.fit_path or None), info


# ---------- UI ----------

_GR6 = int(gr.__version__.split(".")[0]) >= 6
LAUNCH_STYLE = {"theme": THEME, "css": CSS}  # Gradio 6 takes these on launch(); 5 takes them on Blocks()


def build() -> gr.Blocks:
    with gr.Blocks(title="bn-dub", **({} if _GR6 else LAUNCH_STYLE)) as demo:
        gr.Markdown("# bn-dub · Bengali dubbing")
        project_name = gr.State("")

        with gr.Accordion("API keys", open=not (settings.elevenlabs_api_key and settings.anthropic_api_key)):
            with gr.Row():
                key_eleven = gr.Textbox(label="ELEVENLABS_API_KEY", type="password")
                key_anth = gr.Textbox(label="ANTHROPIC_API_KEY", type="password")
                key_btn = gr.Button("Set keys")
            key_md = gr.Markdown(key_status())

        # ----- 1 · input
        with gr.Row():
            with gr.Column(scale=2):
                src = gr.File(label="Video or audio", type="filepath")
            with gr.Column(scale=3):
                gr.Markdown("**Speaker similarity**  \nControls how closely the dubbed voice mimics the original speaker. "
                            "Higher values preserve the source accent; lower values sound more natural in the target language.")
                similarity = gr.Slider(0.0, 1.0, value=0.6, step=0.05, show_label=False)
                with gr.Row():
                    gr.Markdown("<small>Natural in target language</small>")
                    gr.Markdown("<small style='float:right'>More like the original speaker</small>")
                sim_note = gr.HTML(similarity_note(0.6))
        with gr.Row():
            prepare_btn = gr.Button("Prepare script  (separate · transcribe · translate · direct)", variant="primary", scale=3)
            existing = gr.Dropdown(label="or reopen", choices=Project.list_names(), allow_custom_value=True, scale=1)
            load_btn = gr.Button("Open", scale=0)
        summary = gr.Markdown("_Drop a file to start._")

        # ----- 2 · script
        gr.Markdown("### Script\nEdit the Bengali column freely — `[tags]` direct the delivery, `…` is a pause. "
                    "Tick **lock** on lines you're happy with. `fit` = dub length ÷ slot.")
        table = gr.Dataframe(headers=HEADERS, datatype=DTYPES, type="array", interactive=True, wrap=True,
                             column_widths=["4%", "7%", "7%", "9%", "26%", "30%", "5%", "7%", "5%"])
        with gr.Accordion("Voices (auto-cloned per speaker)", open=True):
            speakers = gr.Dataframe(headers=["speaker", "voice", "voice_id"],
                                    datatype=["str", "str", "str"], type="array", interactive=True)
            retry_btn = gr.Button("Retry cloning")
        with gr.Row():
            save_btn = gr.Button("Save edits")
            gen_btn = gr.Button("Generate dub  (speak · fit · verify · mix)", variant="primary", scale=3)

        # ----- 3 · output
        with gr.Row():
            out_video = gr.Video(label="Dubbed video")
            out_audio = gr.Audio(label="Dub mix", type="filepath")
        out_files = gr.File(label="Download", file_count="multiple")

        with gr.Accordion("Audition a line", open=False):
            with gr.Row():
                aud_id = gr.Number(label="Line", value=1, precision=0, scale=0)
                aud_btn = gr.Button("Play", scale=0)
                aud_orig = gr.Audio(label="Original", type="filepath")
                aud_dub = gr.Audio(label="Dub", type="filepath")
            aud_info = gr.Markdown()

        # ----- wiring
        key_btn.click(set_keys, [key_eleven, key_anth], [key_md, key_eleven, key_anth])
        similarity.change(set_similarity, [project_name, similarity], sim_note)
        prepare_btn.click(prepare, [src, similarity], [project_name, summary, table, speakers]) \
            .then(lambda: gr.update(choices=Project.list_names()), None, existing)
        load_btn.click(load_project, existing, [project_name, summary, table, speakers, similarity])
        save_btn.click(save_script, [project_name, table, speakers], [summary, table, speakers])
        retry_btn.click(retry_clone, project_name, [summary, speakers])
        gen_btn.click(generate, [project_name, table, speakers], [summary, table, out_video, out_audio, out_files])
        aud_btn.click(audition, [project_name, aud_id], [aud_orig, aud_dub, aud_info])
    return demo


def launch(demo: gr.Blocks, **kwargs):
    return demo.launch(show_error=True, **(LAUNCH_STYLE if _GR6 else {}), **kwargs)


def main(server_port: int = 7860, share: bool = False) -> None:
    launch(build(), server_port=server_port, share=share)


if __name__ == "__main__":
    main()
