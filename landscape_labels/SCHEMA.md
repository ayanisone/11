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
480x853 (409,440 px) to 720x405 (291,600 px). Any threshold in absolute proc
pixels changes meaning across that move - the `Big_Whoosh` area cut of 129,328 px
is 31.6% of a vertical frame but 44.4% of a landscape one. Storing geometry as a
fraction of the frame makes labels survive a `PROCW` change. `frame_w`,
`frame_h` and `proc_w` are recorded so any label can be converted back if needed.

**`frame` is the label of record, `t_sec` is derived.** Storing seconds alone
loses which frame was meant once fps is in question. The validator recomputes
`frame / fps` and rejects disagreement beyond half a frame, which catches an
fps mismatch at labelling time rather than after a fit.

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
