"""Command line for batch runs and scripting. The Gradio app (`bn-dub ui`) is the interactive route."""

from __future__ import annotations

import argparse
import sys

from . import mix, pipeline, separate, transcribe, translate, tts, verify
from .project import Project

STAGES = {
    "separate": lambda p, a: separate.run(p, a.background),
    "transcribe": lambda p, a: transcribe.run(p),
    "translate": lambda p, a: translate.run(p, a.ids),
    "tts": lambda p, a: tts.run(p, a.ids),
    "verify": lambda p, a: verify.run(p, a.ids, fix=not a.no_fix),
    "mix": lambda p, a: mix.render(p),
}


def _ids(text: str | None):
    return [int(x) for x in text.split(",")] if text else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bn-dub", description="Bengali dubbing chain")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="ingest a file into a new project")
    c.add_argument("name")
    c.add_argument("source")
    c.add_argument("--source-lang", default="en")
    c.add_argument("--target-lang", default=None)
    c.add_argument("--background", default="isolate", choices=["isolate", "demucs", "duck", "none"])

    v = sub.add_parser("voice", help="assign a voice_id to a speaker")
    v.add_argument("name")
    v.add_argument("speaker")
    v.add_argument("voice_id")

    r = sub.add_parser("run", help="run every stage after create")
    r.add_argument("name")
    r.add_argument("--no-verify", action="store_true")

    s = sub.add_parser("stage", help="run one stage")
    s.add_argument("name")
    s.add_argument("stage", choices=sorted(STAGES))
    s.add_argument("--ids", help="comma-separated line ids")
    s.add_argument("--background", default=None)
    s.add_argument("--no-fix", action="store_true")

    sub.add_parser("voices", help="list voices on the ElevenLabs account")
    sub.add_parser("list", help="list projects")

    u = sub.add_parser("ui", help="launch the Gradio console")
    u.add_argument("--port", type=int, default=7860)
    u.add_argument("--share", action="store_true")

    a = ap.parse_args(argv)

    if a.cmd == "create":
        p = pipeline.create(a.name, a.source, source_lang=a.source_lang, target_lang=a.target_lang,
                            background_mode=a.background)
        print(f"created {p.name}: {p.duration:.1f}s, video={p.has_video}")
    elif a.cmd == "voice":
        p = Project.load(a.name)
        sp = p.speaker(a.speaker)
        sp.voice_id, sp.voice_name = a.voice_id, a.voice_id
        p.save()
        print(f"{a.speaker} -> {a.voice_id}")
    elif a.cmd == "run":
        p = Project.load(a.name)
        pipeline.run_all(p, progress=lambda m: print(f"[{p.name}] {m}", file=sys.stderr), do_verify=not a.no_verify)
        print(p.output_video or p.output_audio)
    elif a.cmd == "stage":
        p = Project.load(a.name)
        a.ids = _ids(a.ids)
        STAGES[a.stage](p, a)
        print(f"{a.stage} done: {len(p.segments)} lines")
    elif a.cmd == "voices":
        for label, vid in tts.list_voices():
            print(f"{vid}\t{label}")
    elif a.cmd == "list":
        for n in Project.list_names():
            print(n)
    elif a.cmd == "ui":
        from app import main as ui_main

        ui_main(server_port=a.port, share=a.share)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
