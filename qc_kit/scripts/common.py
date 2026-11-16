"""Shared helpers: API keys, songs.csv, number words."""
import csv
import os
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent


def load_env():
    """Keys come from the shell environment first, then <cwd>/.env, then <kit>/.env."""
    env = dict(os.environ)
    for p in (Path.cwd() / ".env", KIT / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def read_songs(project):
    """songs.csv columns: song_file, lyrics_file, title, language, style, model (model optional)."""
    path = Path(project) / "songs.csv"
    if not path.exists():
        raise SystemExit(f"Missing {path}. Copy templates/songs.csv into the project and fill it in.")
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
            if not r.get("song_file"):
                continue
            r["stem"] = Path(r["song_file"]).stem
            r["language"] = r.get("language") or "en"
            rows.append(r)
    return rows


SARVAM_LANG = {"hi": "hi-IN", "en": "en-IN", "bn": "bn-IN", "kn": "kn-IN", "ml": "ml-IN", "mr": "mr-IN",
               "or": "od-IN", "od": "od-IN", "pa": "pa-IN", "ta": "ta-IN", "te": "te-IN", "gu": "gu-IN"}

_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen " \
        "sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def num_words(n):
    """0-9999 -> English words ('25' -> 'twenty five'). Larger numbers are returned as digits."""
    n = int(n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else " " + _ONES[n % 10])
    if n < 1000:
        return _ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + num_words(n % 100))
    if n < 10000:
        return num_words(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + num_words(n % 1000))
    return str(n)
