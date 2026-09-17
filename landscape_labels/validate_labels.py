#!/usr/bin/env python3
"""Validate a landscape label file before it is used to fit classify_anim.

Encodes the hard-won rules from SFX_PIPELINE_HANDOFF.md as executable checks,
so they fail at labelling time rather than after a fit:

  * every label carries the anchor it was measured against (the 400 ms offset
    bug was an anchor mismatch, not a bad number)
  * geometry is frame-relative, never proc pixels (PROCW 480 vertical ->
    720 landscape changes what any absolute pixel threshold means)
  * frame/fps/t_sec agree, catching an fps mismatch before it reaches a model
  * negatives are present, so the classifier can be fitted with an abstain path
  * enough per class and enough projects to fit and to run leave-one-project-out

Usage:  python3 validate_labels.py labels.jsonl
Exit:   0 = fit-ready, 1 = not fit-ready, 2 = could not read the file
"""

import json
import signal
import sys
from collections import Counter, defaultdict

ANCHORS = {
    "elem_growth_start",
    "arr_boxes_first_appearance",
    "roll_start",
    "roll_end",
    "cell_ink_start",
    "shot_change",
    "manual",
}
LABELS = {"counter", "bar_fill", "card", "none"}
SOURCES = {"detector", "human"}

REQUIRED = {
    "project": str,
    "frame": int,
    "fps": (int, float),
    "t_sec": (int, float),
    "anchor": str,
    "label": str,
    "bbox": list,
    "frame_w": int,
    "frame_h": int,
    "proc_w": int,
    "source": str,
}

MIN_PER_CLASS = 8
MIN_NEGATIVES = 6
MIN_PROJECTS = 2


def check_row(row, ln, errs):
    """Field-level checks for one label. Appends '<line>: <message>' to errs."""
    def err(msg):
        errs.append(f"line {ln}: {msg}")

    for key, typ in REQUIRED.items():
        if key not in row:
            err(f"missing required field {key!r}")
        elif not isinstance(row[key], typ) or isinstance(row[key], bool):
            got = type(row[key]).__name__
            err(f"{key!r} must be {getattr(typ, '__name__', 'number')}, got {got}")
    if errs and any(f"line {ln}:" in e for e in errs[-len(REQUIRED):]):
        # Missing or mistyped fields make the remaining checks meaningless.
        if any(k not in row for k in REQUIRED):
            return

    if row.get("anchor") not in ANCHORS:
        err(f"anchor {row.get('anchor')!r} not in {sorted(ANCHORS)}")
    if row.get("label") not in LABELS:
        err(f"label {row.get('label')!r} not in {sorted(LABELS)}")
    if row.get("source") not in SOURCES:
        err(f"source {row.get('source')!r} not in {sorted(SOURCES)}")

    fps = row.get("fps")
    if isinstance(fps, (int, float)) and fps > 0:
        frame, t_sec = row.get("frame"), row.get("t_sec")
        if isinstance(frame, int) and isinstance(t_sec, (int, float)):
            drift = abs(t_sec - frame / fps)
            if drift > 0.5 / fps:
                err(
                    f"t_sec {t_sec} disagrees with frame/fps "
                    f"({frame}/{fps} = {frame / fps:.4f}) by {drift * 1000:.1f} ms "
                    f"- more than half a frame; check the fps came from the video stream"
                )
    else:
        err(f"fps must be > 0, got {fps!r}")

    if isinstance(row.get("frame"), int) and row["frame"] < 0:
        err(f"frame must be >= 0, got {row['frame']}")

    bbox = row.get("bbox")
    if isinstance(bbox, list):
        if len(bbox) != 4:
            err(f"bbox needs 4 values [x1,y1,x2,y2], got {len(bbox)}")
        elif not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in bbox):
            err("bbox values must all be numbers")
        else:
            x1, y1, x2, y2 = bbox
            if not all(0.0 <= v <= 1.0 for v in bbox):
                err(
                    f"bbox {bbox} is not frame-relative - every value must be in [0,1]. "
                    f"Proc pixels do not survive PROCW 480 -> 720"
                )
            if x1 >= x2 or y1 >= y2:
                err(f"bbox {bbox} is degenerate - need x1 < x2 and y1 < y2")


def main(path):
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print(f"could not read {path}: {exc}", file=sys.stderr)
        return 2

    errs = []
    rows = []
    for ln, raw in enumerate(lines, 1):
        raw = raw.strip()
        if not raw or raw.startswith("//"):
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            errs.append(f"line {ln}: not valid JSON ({exc.msg})")
            continue
        if not isinstance(row, dict):
            errs.append(f"line {ln}: expected a JSON object")
            continue
        check_row(row, ln, errs)
        rows.append((ln, row))

    seen = defaultdict(list)
    for ln, row in rows:
        if isinstance(row.get("frame"), int):
            seen[(row.get("project"), row["frame"], row.get("anchor"))].append(ln)
    for (proj, frame, anchor), lns in sorted(seen.items(), key=lambda kv: kv[1]):
        if len(lns) > 1:
            errs.append(
                f"lines {lns}: duplicate label for {proj} frame {frame} "
                f"on anchor {anchor!r}"
            )

    by_class = Counter(r.get("label") for _, r in rows if r.get("label") in LABELS)
    by_project = Counter(r.get("project") for _, r in rows)
    by_anchor = Counter(r.get("anchor") for _, r in rows)
    by_source = Counter(r.get("source") for _, r in rows)

    print(f"{path}: {len(rows)} labels read, {len(errs)} error(s)\n")
    if by_class:
        print("  per class:")
        for cls in sorted(LABELS):
            n = by_class.get(cls, 0)
            flag = "" if n >= MIN_PER_CLASS else f"  <- under {MIN_PER_CLASS}"
            print(f"    {cls:<10} {n:>4}{flag}")
    if by_project:
        print("\n  per project:")
        for proj, n in sorted(by_project.items(), key=lambda kv: str(kv[0])):
            print(f"    {str(proj):<10} {n:>4}")
    if by_anchor:
        print("\n  per anchor:   " + ", ".join(f"{a}={n}" for a, n in sorted(by_anchor.items(), key=lambda kv: str(kv[0]))))
    if by_source:
        print("  per source:   " + ", ".join(f"{s}={n}" for s, n in sorted(by_source.items(), key=lambda kv: str(kv[0]))))

    blockers = []
    for cls in sorted(LABELS):
        n = by_class.get(cls, 0)
        if n < MIN_PER_CLASS:
            blockers.append(f"class {cls!r} has {n} labels, need >= {MIN_PER_CLASS}")
    if by_class.get("none", 0) < MIN_NEGATIVES:
        blockers.append(
            f"only {by_class.get('none', 0)} negatives, need >= {MIN_NEGATIVES} - "
            f"without them the classifier cannot be fitted with an abstain path"
        )
    if len(by_project) < MIN_PROJECTS:
        blockers.append(
            f"only {len(by_project)} project(s), need >= {MIN_PROJECTS} - "
            f"leave-one-project-out cannot run, so any score is not held out"
        )

    if errs:
        print(f"\nERRORS ({len(errs)}):")
        for e in errs[:40]:
            print(f"  {e}")
        if len(errs) > 40:
            print(f"  ... and {len(errs) - 40} more")

    if blockers:
        print(f"\nNOT FIT-READY ({len(blockers)} blocker(s)):")
        for b in blockers:
            print(f"  {b}")

    if errs or blockers:
        return 1

    print("\nFIT-READY: schema clean, classes balanced, LOPO possible.")
    return 0


if __name__ == "__main__":
    # Behave like a normal unix tool under `| head` / `| less q` instead of
    # dumping a BrokenPipeError traceback.
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
