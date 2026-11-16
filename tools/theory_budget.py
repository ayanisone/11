#!/usr/bin/env python3
"""Theory -> song length + lyric budget calculator.

Usage:
    python3 tools/theory_budget.py theory.txt
    cat theory.txt | python3 tools/theory_budget.py

Rule (from the client):
    500 characters  -> 40 s of audio, scaling linearly
    500-1000  -> 0:40-1:20
    1000-1500 -> 1:20-2:00
    1500-2000 -> 2:00-2:40
    2000-2500 -> 2:40-3:20
    2500-3000 -> 3:20-4:00
i.e. 0.08 s per character, never shorter than 40 s.
Characters are counted with spaces and punctuation (the standard count).

Lyric budget comes from our ElevenLabs Music v2.5 runs:
    a melodic genre clearly sings about 3 syllables per second of vocal time
    (115-120 syllables in a 40 s song with a hook-first structure); rap carries
    about 3.8 per second. Instrumental breaks are subtracted before budgeting.
"""
import math
import re
import sys

SEC_PER_CHAR = 40 / 500          # 0.08 s per character
MIN_SEC, MAX_SEC = 40, 240       # client table covers 40 s .. 4:00
SYL_PER_SEC = {"universal": 2.5, "melodic": 3.0, "rap": 3.8}
# "universal" = one lyric sheet that fits all 10 working genres with no rushing (measured 2026-11-16:
# thermodynamics v3 at ~2.6 syl/s passed in 9/10 genres; v2 at ~3.4 syl/s failed in 7/11). USE THIS ONE.
END_TAIL_SEC = 2                 # last word should land ~2 s before the end


def duration_for(chars: int) -> int:
    return max(MIN_SEC, round(chars * SEC_PER_CHAR))


def structure_for(sec: int):
    """Section plan and instrumental seconds for a given length."""
    if sec <= 45:
        return (["Hook", "Verse 1", "Verse 2", "Chorus", "Hook"], 0)
    if sec <= 80:
        return (["Chorus (opens the song = the hook)", "Verse 1",
                 "Instrumental break (~4 s)", "Verse 2", "Final chorus"], 4)
    if sec <= 120:
        return (["Chorus (opens the song = the hook)", "Verse 1",
                 "Instrumental break (~4 s)", "Verse 2",
                 "Bridge (change of feel)", "Final chorus"], 4)
    if sec <= 180:
        return (["Chorus (opens the song = the hook)", "Verse 1",
                 "Instrumental break (~5 s)", "Verse 2", "Chorus", "Verse 3",
                 "Bridge (change of feel)", "Instrumental break (~5 s)", "Verse 4",
                 "Final chorus (key lift)"], 10)
    return (["Chorus (opens the song = the hook)", "Verse 1",
             "Instrumental break (~5 s)", "Verse 2", "Chorus", "Verse 3",
             "Bridge (change of feel)", "Instrumental break (~5 s)", "Verse 4",
             "Final chorus (key lift)"], 10)


def count_syllables(text: str) -> int:
    """Rough English syllable count (good enough for budgeting)."""
    total = 0
    for word in re.findall(r"[A-Za-z']+", text.lower()):
        groups = re.findall(r"[aeiouy]+", word)
        n = len(groups)
        if word.endswith("e") and n > 1 and not word.endswith(("le", "ee")):
            n -= 1
        total += max(1, n)
    return total


def fmt(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def main():
    text = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 \
        else sys.stdin.read()
    text = text.strip()
    chars = len(text)
    chars_no_space = len(re.sub(r"\s", "", text))
    words = len(text.split())
    sec = min(duration_for(chars), MAX_SEC)
    sections, inst = structure_for(sec)
    vocal_sec = sec - inst - END_TAIL_SEC

    print(f"Characters (with spaces): {chars}")
    print(f"Characters (no spaces):   {chars_no_space}")
    print(f"Words:                    {words}")
    print(f"Theory syllables (approx):{count_syllables(text):>5}")
    if chars > 3000:
        print("WARNING: over 3000 characters, beyond the client table; "
              f"capped at {fmt(MAX_SEC)}. Confirm with the client.")
    print(f"\nTarget audio length:      {fmt(sec)} ({sec} s)")
    print(f"Instrumental breaks:      {inst} s")
    print(f"Vocal time:               {vocal_sec} s")
    for style, rate in SYL_PER_SEC.items():
        lo, hi = math.floor(vocal_sec * rate * 0.9), math.floor(vocal_sec * rate)
        print(f"Lyric budget ({style:7s}):  {lo}-{hi} sung syllables "
              "(hook/chorus repeats count)")
    print("\nSuggested structure:")
    for i, s in enumerate(sections, 1):
        print(f"  {i:2d}. {s}")


if __name__ == "__main__":
    main()
