# Landscape label protocol

Step 1 of "What to do next" in `SFX_PIPELINE_HANDOFF.md`: get labelled landscape
data so the 3-way animation classifier can be fitted instead of hand-written.

One JSON object per line in `labels.jsonl`. Run `validate_labels.py` over it
before handing it to a fitter.

## Fields

| Field | Type | Notes |
|---|---|---|
| `project` | str | `LF1`, `LF2`, `LF3`, ... |
| `frame` | int | Native video frame index. The label of record. |
| `fps` | float | Read from the **video stream**. Not `SmpteFormat`. |
| `t_sec` | float | Must equal `frame / fps` within half a frame. |
| `anchor` | str | Which event definition `frame` refers to. See below. |
| `label` | str | `counter` \| `bar_fill` \| `card` \| `none` |
| `bbox` | [float×4] | `[x1, y1, x2, y2]`, **frame-relative**, each in `[0, 1]`. |
| `frame_w` | int | Native video width. |
| `frame_h` | int | Native video height. |
| `proc_w` | int | `PROCW` in force when the candidate was produced. |
| `source` | str | `detector` (pipeline proposed it) \| `human` (spotted by eye). |
| `note` | str | Optional. Free text. |

## Why these fields and not fewer

**`anchor` is mandatory.** The largest bug in this project was a 200-250 ms
pre-roll measured against `elem_growth_start` at 15 fps and applied to
`arr_boxes` first-appearance at 30 fps - a 400 ms error in the wrong direction on
every cue. The number was fine; the anchor was not. A label without its anchor
recorded cannot be reused when the detector changes, and silently reintroduces
that bug. Permitted values:

    elem_growth_start, arr_boxes_first_appearance, roll_start, roll_end,
    cell_ink_start, shot_change, manual

**`bbox` is frame-relative, never proc pixels.** `PROCW` is 480 for vertical and
720 for landscape, and the aspect flips 9:16 to 16:9, so the proc frame goes from
480x854 (409,920 px) to 720x404 (290,880 px) - `detect3.py:31` rounds each
dimension to even.

The detector's own area thresholds are already normalized (`0.0003*w*h`,
`0.02*w*h`, `0.0012*pw*ph`), so absolute pixel areas are not a live bug there.
The 129,328 px `Big_Whoosh` figure in the handoff is a descriptive statistic, not
a gate - it appears nowhere in the code. Geometry is still stored frame-relative
here because a label file outlives the `PROCW` it was collected under, and a
relabelling is far more expensive than a division. `frame_w`, `frame_h` and
`proc_w` are recorded so any label can be converted back if needed.

Scale-dependent constants that *do* exist in the code are one and two digit, and
invisible to a `[0-9]{3,}` grep: `classify_anim.py` hardcodes `pw2=480`,
`scenegate.py` hardcodes a 9/16 aspect, and `detect3.py` carries pixel jitter and
displacement gates (`jitter>2.5`, `abs(dx)<8`, `std<3.0`).

**`frame` is the label of record, `t_sec` is derived.** Storing seconds alone
loses which frame was meant once fps is in question. The validator recomputes
`frame / fps` and rejects disagreement beyond half a frame, and rejects a project
that declares more than one fps.

*Worked example, from a real error in this file's first draft:* LF3 is **25 fps**
(`ffprobe` reports `r_frame_rate=25/1`), not 30. Its two known presenter leaks at
24.0 s and 107.6 s are frames **600** and **2690**. Written at an assumed 30 fps
they became frames 720 and 3228 - 4.8 s and 20.2 s adrift, in the very file whose
purpose is to stop that. Read fps per project from the video stream before
labelling anything.

**`frame` is a NATIVE video frame index, not a detector sample index.**
`detect3.py` resamples every video to 30 fps regardless of native rate. On 25 fps
LF3 that makes roughly one sampled frame in six a byte-exact duplicate of the
previous one (measured: 100/600 over 20 s), which injects a hard zero into churn,
roll-span and shot detection. If the detector reports sampled indices, convert to
native before writing the label: `native = round(sampled * fps_native / 30)`.

## Negatives are required, not optional

`label: "none"` means "the detector proposed this and it is not one of the three
classes." Without negatives the classifier cannot learn to abstain, and a forced
3-way choice on ambiguous input is 33% by construction - which is what the
current classifier scores on LF3.

The hard rule is precision over recall. That needs an abstain path, and an
abstain path needs negatives to fit against.

**The 12 LF3 cases already checked by eye are 12 labels.** Eight of them are
negatives. If those timecodes were written down anywhere, they are the cheapest
labels in this project - recover them before labelling anything new.

## How many

Enforced by `validate_labels.py`:

- **>= 8 per class**, counting `none`. Below that a fit is memorising.
- **>= 6 negatives**, for the reason above.
- **>= 2 projects**, or leave-one-project-out cannot run and the number the
  harness prints is not a held-out number.

Three projects (LF1/LF2/LF3) at ~12 labels each clears all three bars.

## What to label

Sweep the detector over LF1/LF2/LF3 and label **what it proposes**, including
what it gets wrong - that yields matched positives and negatives for free. Then
add by eye any obvious counter/bar/card the detector missed entirely, marked
`source: "human"`, so recall is measurable and not just precision.

## Class definitions

Defined by mechanism, not appearance. The one detector in this project that hit
98% precision (`cells3.py`) worked because it found a literal mechanism - ink
appearing inside a white cell - rather than tuning a generic detector.

- **`counter`** - digits rolling. Box geometry holds still while the interior
  churns. A static list of numbers appearing is **not** a counter.
- **`bar_fill`** - a fill edge advancing monotonically along one axis inside a
  track whose outer extent holds still.
- **`card`** - a region arriving as a unit (cut, slide or scale in), interior
  static once it has landed.
- **`none`** - anything else, including presenter shots, disclaimers, and
  transitions.

When two fire on the same frame, label the one driving the SFX and say so in
`note`.
