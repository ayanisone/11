"""Score -> per-line ElevenLabs takes (cached) -> timeline -> speaker stems, mix, cue sheet, report."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from . import eleven
from .score import Score
from .timeline import (TAG_RE, Clip, Word, conversation_stats, energy_bounds, estimate_words, mixdown, overlaps_of, place,
                       read_wav, spans_from_timeline, speakable, strip_tags, timecode, words_from_chars, write_wav)


def _clip_key(**parts) -> str:
    return hashlib.sha1(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def synth_line(text: str, voice_id: str, *, model_id: str, output_format: str, previous_text: Optional[str],
               seed: Optional[int], cache: Path, log: list[str]) -> Clip:
    """One take, cached by everything that affects it, so re-timing a score never re-spends credits."""
    key = _clip_key(text=text, voice=voice_id, model=model_id, fmt=output_format, prev=previous_text, seed=seed)
    wav, meta = cache / f"{key}.wav", cache / f"{key}.json"
    if wav.exists() and meta.exists():
        audio, rate = read_wav(wav)
        return Clip(audio, rate, [Word(**w) for w in json.loads(meta.read_text())["words"]])

    try:
        audio, rate, align = eleven.tts_with_timestamps(text, voice_id, model_id=model_id, output_format=output_format,
                                                        previous_text=previous_text, seed=seed)
    except eleven.ElevenError as e:
        if previous_text is None or e.status != 400:
            raise
        log.append(f"{model_id} rejected previous_text context ({e}); rendering without it")
        audio, rate, align = eleven.tts_with_timestamps(text, voice_id, model_id=model_id,
                                                        output_format=output_format, seed=seed)
    source = "tts"
    words = words_from_chars(align["characters"], align["character_start_times_seconds"],
                             align["character_end_times_seconds"]) if align else []
    spoken = strip_tags(text)
    cache.mkdir(parents=True, exist_ok=True)
    write_wav(wav, audio, rate, bits=16)
    if spoken and not words:
        try:
            words = [Word(w["text"], float(w["start"]), float(w["end"])) for w in eleven.forced_alignment(wav, spoken)]
            source = "forced_alignment"
        except eleven.ElevenError as e:
            log.append(f"forced alignment failed for {text[:40]!r}: {e}")
        if not words:
            words = estimate_words(text, *energy_bounds(audio, rate))
            source = "estimated"
            log.append(f"word timings for {text[:40]!r} are estimated from loudness, anchors on it are approximate")
    meta.write_text(json.dumps({"text": text, "source": source, "words": [asdict(w) for w in words]},
                               ensure_ascii=False, indent=1))
    return Clip(audio, rate, words)


TIMING_TAGS = ("interrupting", "jumping in", "overlapping")


def tag_warnings(score: Score, tl) -> list[str]:
    """v4 tag hygiene: hyphenated tags, and lines that start over someone without a dialogue-timing tag."""
    out = []
    for line in score.lines:
        tags = [t.strip("[]").lower() for t in TAG_RE.findall(line.text)]
        out += [f"{line.id}: tag [{t}] has a hyphen; v4 reads plain words better" for t in tags if "-" in t]
        if line.kind != "line" or any(t in TIMING_TAGS for t in tags):
            continue
        p = tl.placed[line.id]
        talking = [o.line.id for o in tl.placed.values()
                   if o.line.speaker != line.speaker and o.line.kind == "line" and o.onset < p.onset < o.speech_end]
        if talking:
            out.append(f"{line.id}: starts over {', '.join(talking)} but has no [jumping in] / [interrupting] / "
                       f"[overlapping] tag, so the take may sound like a solo read")
    return out


def render(score: Score, out_dir: Path, *, voices: dict[str, str], model_id: str = "eleven_v4",
           output_format: str = "pcm_44100", context: bool = True, seed: Optional[int] = None,
           cache: Optional[Path] = None, fps: int = 25, bits: int = 24) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = cache or out_dir / ".takes"
    log: list[str] = []
    cast = {s.speaker: voices.get(s.speaker) or s.voice_id for s in score.speakers}
    missing = [k for k, v in cast.items() if not v]
    if missing:
        raise SystemExit(f"no voice id for speaker(s) {missing}; pass --voice {missing[0]}=<voice_id>")

    clips: dict[str, Clip] = {}
    prev_text: Optional[str] = None
    for line in score.lines:
        text = speakable(line.text)
        if text != line.text:
            log.append(f"{line.id}: tag-only line rendered as {text!r} (v4 needs at least one spoken sound)")
        clips[line.id] = synth_line(text, cast[line.speaker], model_id=model_id, output_format=output_format,
                                    previous_text=prev_text if context else None, seed=seed, cache=cache, log=log)
        if line.kind == "line":
            prev_text = strip_tags(line.text) or prev_text

    tl = place(score.lines, clips)
    stems, mix, rate, gain = mixdown(tl)
    for spk, stem in stems.items():
        write_wav(out_dir / "stems" / f"{spk}.wav", stem, rate, bits)
    write_wav(out_dir / "mix.wav", mix, rate, bits)

    spans = spans_from_timeline(tl)
    with open(out_dir / "cues.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "speaker", "kind", "start_tc", "end_tc", "start_s", "end_s", "overlaps", "cut_off", "text"])
        for s in spans:
            p = tl.placed[s.id]
            w.writerow([s.id, s.speaker, s.kind, timecode(s.start, fps), timecode(s.end, fps), f"{s.start:.3f}",
                        f"{s.end:.3f}", " ".join(overlaps_of(s, spans)), "yes" if p.cut_at else "", s.text])
    with open(out_dir / "labels.txt", "w", encoding="utf-8") as f:  # Audacity / Reaper-importable region list
        for s in spans:
            f.write(f"{s.start:.3f}\t{s.end:.3f}\t{s.speaker}: {strip_tags(s.text) or s.text}\n")

    report = {"title": score.title, "sample_rate": rate, "bits": bits, "model_id": model_id,
              "voices": cast, "safety_gain_db": round(20 * math.log10(gain), 2),
              "stats": conversation_stats(spans), "warnings": tl.warnings + tag_warnings(score, tl) + log}
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report
