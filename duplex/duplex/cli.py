"""duplex write | render | analyze"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .score import Score


def _voices(pairs: list[str]) -> dict[str, str]:
    out = {}
    for p in pairs or []:
        k, _, v = p.partition("=")
        if not v:
            raise SystemExit(f"--voice expects SPEAKER=VOICE_ID, got {p!r}")
        out[k] = v
    return out


def cmd_write(a: argparse.Namespace) -> None:
    from .writer import write_score

    brief = Path(a.brief[1:]).read_text() if a.brief.startswith("@") else a.brief
    score = write_score(brief, seconds=a.seconds, language=a.language, model=a.model)
    Path(a.out).write_text(score.model_dump_json(indent=2, exclude_none=True))
    print(f"wrote {a.out}: {len(score.lines)} lines")


def cmd_render(a: argparse.Namespace) -> None:
    from .render import render

    score = Score.model_validate_json(Path(a.score).read_text())
    report = render(score, Path(a.out), voices=_voices(a.voice), model_id=a.model, output_format=a.format,
                    context=not a.no_context, seed=a.seed, fps=a.fps, bits=a.bits)
    print(json.dumps(report, indent=2, ensure_ascii=False))


def cmd_analyze(a: argparse.Namespace) -> None:
    from .analyze import analyze, to_score

    src = Path(a.input)
    if src.suffix.lower() == ".json":
        payload = json.loads(src.read_text())
    else:
        from .eleven import scribe

        payload = scribe(src, num_speakers=a.speakers, language_code=a.language)
        cache = src.with_suffix(".scribe.json")
        cache.write_text(json.dumps(payload, ensure_ascii=False))
        print(f"transcript saved to {cache} (re-run on that file to skip Scribe)", file=sys.stderr)
    stats, turns = analyze(payload)
    print(json.dumps(stats, indent=2))
    for t in turns:
        mark = "   ~" if t.kind == "backchannel" else ""
        print(f"{t.start:7.2f}-{t.end:6.2f} {t.speaker}{mark} {t.text}", file=sys.stderr)
    if a.score:
        Path(a.score).write_text(to_score(turns, title=src.stem).model_dump_json(indent=2, exclude_none=True))
        print(f"score with the reference's timing written to {a.score}", file=sys.stderr)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="duplex", description="Natural, overlapping two-person dialogue for ads.")
    sub = ap.add_subparsers(required=True)

    w = sub.add_parser("write", help="Claude writes an overlap score from a brief")
    w.add_argument("brief", help="brief text, or @path/to/brief.txt")
    w.add_argument("-o", "--out", default="score.json")
    w.add_argument("--seconds", type=int, default=30)
    w.add_argument("--language", default="en")
    w.add_argument("--model", default=None, help="Claude model id (default claude-opus-5-5)")
    w.set_defaults(fn=cmd_write)

    r = sub.add_parser("render", help="render a score to speaker stems + mix + cue sheet")
    r.add_argument("score")
    r.add_argument("-o", "--out", default="out")
    r.add_argument("--voice", action="append", help="SPEAKER=VOICE_ID (repeat per speaker)")
    r.add_argument("--model", default="eleven_v4", help="ElevenLabs TTS model (eleven_v4, eleven_v4_turbo, ...)")
    r.add_argument("--format", default="pcm_44100", help="pcm_* output format; pcm_44100/48000 need a paid tier")
    r.add_argument("--no-context", action="store_true", help="don't send the previous line as previous_text")
    r.add_argument("--seed", type=int, default=None)
    r.add_argument("--fps", type=int, default=25, help="cue sheet timecode frame rate")
    r.add_argument("--bits", type=int, default=24, choices=(16, 24))
    r.set_defaults(fn=cmd_render)

    z = sub.add_parser("analyze", help="turn-taking fingerprint of a real two-person recording")
    z.add_argument("input", help="audio file (sent to Scribe) or a saved Scribe JSON")
    z.add_argument("--speakers", type=int, default=2)
    z.add_argument("--language", default=None)
    z.add_argument("--score", help="also write an overlap score that reproduces this recording's timing")
    z.set_defaults(fn=cmd_analyze)

    a = ap.parse_args(argv)
    if getattr(a, "model", "") is None:
        from .writer import DEFAULT_MODEL

        a.model = DEFAULT_MODEL
    a.fn(a)


if __name__ == "__main__":
    main()
