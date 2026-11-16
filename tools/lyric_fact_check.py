#!/usr/bin/env python3
"""Pre-generation Lyric Fact QC: mechanical checks of a lyric sheet against its source theory.

Usage:
    python3 tools/lyric_fact_check.py theory.txt lyrics.txt [--allow "word word ..."]

Checks (all automatic; the claim-by-claim science check is done by a reviewer in the report):
  1. NUMBERS  - every number in the theory appears in the lyrics (sung form is parsed:
                "five point five" = 5.5, "one hundred twenty" = 120, "twelve to sixteen" = 12, 16),
                and every number sung in the lyrics exists in the theory. A lyric number that is not
                in the theory is a FAIL (possible wrong fact).
  2. TERMS    - content words of the theory (technical terms) that never appear in the lyrics.
                Each is either covered by another wording or is a coverage gap: REVIEW.
  3. OUTSIDE  - lyric words that are not in the theory (the "only theory words" rule). Spoken
                forms of symbols/units/numbers are allowed automatically; anything else is REVIEW.
Exit code 1 if any FAIL.
"""
import argparse
import re
import sys

ONES = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
NUM_WORDS = set(ONES) | set(TENS) | {"hundred", "thousand", "point"}

# spoken readings of symbols/units/abbreviations: always allowed in lyrics
SPOKEN_FORMS = set("""per cubic square squared millimetre millimeter millimetres metre meter litre liter
millilitre milliliter ml m l gram grams kilogram percent degree degrees celsius plus minus equals equal
times divided over into point hundred thousand million millions""".split())
# British/American spelling pairs treated as the same word
SPELLING = {"hemoglobin": "haemoglobin", "colored": "coloured", "color": "colour", "center": "centre",
            "meter": "metre", "liter": "litre", "milliliter": "millilitre", "millimeter": "millimetre",
            "gms": "grams", "gm": "grams", "g": "grams"}
STOP = set("""a an the of in on at to is are was were be been has have had and or but for by with as from
it its this that these those which who whom what when where after before than then there their they them
he she his her we our you your i my me not no so if into most all every each any hence also called""".split())


def norm(w):
    w = w.lower().strip("'")
    return SPELLING.get(w, w)


def words(text):
    text = re.sub(r"^#.*$|\[[^\]]*\]", " ", text, flags=re.M)
    text = re.sub(r"\b((?:[A-Za-z]-)+[A-Za-z]s?)\b", lambda m: m.group(1).replace("-", ""), text)  # R-B-Cs -> RBCs
    return [norm(w) for w in re.findall(r"[A-Za-z']+", text)]


def theory_numbers(text):
    """Numbers written with digits in the theory. '12-16' -> 12, 16; '5.5' -> 5.5; ignores mm-3 style exponents."""
    text = re.sub(r"(?<=[A-Za-z])\s*[–-]\s*\d+", " ", text)    # mm–3, cm-1: unit exponents, not facts
    return sorted({float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)})


def lyric_numbers(text):
    """Parse sung numbers ('five point five', 'one hundred twenty') and digit numbers."""
    text = re.sub(r"^#.*$|\[[^\]]*\]", " ", text, flags=re.M)
    found = {float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)}
    toks = re.findall(r"[a-z]+", text.lower())
    i = 0
    while i < len(toks):
        if toks[i] in ONES or toks[i] in TENS or toks[i] == "hundred":
            total, cur, j = 0, 0, i
            while j < len(toks) and (toks[j] in ONES or toks[j] in TENS or toks[j] in ("hundred", "thousand")):
                t = toks[j]
                if t in ONES: cur += ONES[t]
                elif t in TENS: cur += TENS[t]
                elif t == "hundred": cur = (cur or 1) * 100
                elif t == "thousand": total += (cur or 1) * 1000; cur = 0
                j += 1
            val = total + cur
            if j + 1 < len(toks) and toks[j] == "point" and toks[j + 1] in ONES:
                val += ONES[toks[j + 1]] / 10
                j += 2
            found.add(float(val))
            i = j
        else:
            i += 1
    return sorted(found)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("theory")
    ap.add_argument("lyrics")
    ap.add_argument("--allow", default="", help="extra words allowed outside the theory")
    a = ap.parse_args()
    theory, lyrics = open(a.theory, encoding="utf-8").read(), open(a.lyrics, encoding="utf-8").read()
    tw, lw = words(theory), words(lyrics)
    tset, lset = set(tw), set(lw)
    allow = SPOKEN_FORMS | NUM_WORDS | {norm(w) for w in a.allow.split()}
    fails = 0

    print("## 1. Numbers")
    # numbers the theory states with digits OR words ("from one form into another" counts as 1)
    tn, ln = sorted(set(theory_numbers(theory)) | set(lyric_numbers(theory))), lyric_numbers(lyrics)
    fmt = lambda x: f"{x:g}"
    print("| Number | In theory | In lyrics | Result |\n|---|---|---|---|")
    for n in sorted(set(tn) | set(ln)):
        it, il = n in tn, n in ln
        res = "OK" if it and il else ("REVIEW: not sung (coverage)" if it else "**FAIL: not in theory**")
        fails += res.startswith("**FAIL")
        print(f"| {fmt(n)} | {'yes' if it else '-'} | {'yes' if il else '-'} | {res} |")

    print("\n## 2. Theory terms not in the lyrics")
    missing = sorted({w for w in tset - lset if w not in STOP and len(w) > 2 and w not in NUM_WORDS
                      and not any(w.rstrip('s') == x.rstrip('s') for x in lset)})
    print(", ".join(missing) if missing else "None: every content word of the theory is sung.")

    print("\n## 3. Lyric words not in the theory")
    outside = sorted({w for w in lset - tset if w not in allow and not any(w.rstrip('s') == x.rstrip('s') for x in tset)})
    print(", ".join(outside) if outside else "None: every lyric word comes from the theory (or is a spoken symbol/number).")

    print(f"\nAutomatic result: {'FAIL' if fails else 'no automatic FAIL'} "
          f"({len(missing)} theory terms to confirm, {len(outside)} outside words to confirm)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
