"""Step 3: score the transcripts against each song's lyric sheet (rules: Vocals_Lyrics_STT_QA_Guide.md section 3).

Usage:  python scripts/song_qc_score.py <project_dir>
Reads:  <project>/songs.csv, <project>/<lyrics_file>, <project>/stt/<stem>.json (from song_stt.py)
Writes: <project>/song_qc_report.xlsx  (Consensus / Summary / Items / Transcripts sheets)
        <project>/song_qc_summary.md   (one verdict per song, ready to paste)
        <project>/song_qc_report.json  (everything, machine-readable)

Lyrics file: one line per sung line, [Section] tags ignored, '# protected: w1 w2 ...' lists protected words.
Classes: ALLOWED (vocables, repeats/harmonies of lyric words, stutters), REVIEW, FAIL.
Hindi in Devanagari and romanised Hindi are compared phonetically (ITRANS, folded) with fuzzy matching.
"""
import json, re, sys
from difflib import SequenceMatcher
from pathlib import Path
from indic_transliteration import sanscript
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_songs, num_words  # noqa: E402

NOT_SCORED = {"sarvam_verbatim_vocals"}   # kept for reading only (English words come out in Devanagari)
VOCABLES = set("""oh ooh ah aah uh uhh mm mmm hmm yeah yeh yea ya yo hey ho whoa woah wow na la da di do ba bam
ay ayy eh huh uhhuh okay ok alright haan arre aaja""".split())
FUNCTION = set("has the a and it is of to will an ke ka ki me men se hai".split())
SAME = {"equals": "equal", "squared": "square", "aur": "or", "our": "or", "remains": "remains"}
DEV = re.compile(r"[\u0900-\u097F]")


def fold(tok):
    """Phonetic key: Devanagari -> ITRANS, drop final schwa, collapse long vowels and nasal marks."""
    if DEV.search(tok):
        tok = sanscript.transliterate(tok, sanscript.DEVANAGARI, sanscript.ITRANS)
        tok = tok.replace(".N", "n").replace("M", "n").replace(".n", "n")
        tok = re.sub(r"a$", "", tok) if len(tok) > 2 else tok
    t = tok.lower()
    if t in ("aur", "aura"): t = "or"
    for a, b in [("aa", "a"), ("ee", "i"), ("oo", "u"), ("ii", "i"), ("uu", "u"), ("ei", "e"), ("ai", "e"),
                 ("w", "v"), ("sth", "s"), ("th", "t"), ("kh", "k"), ("gh", "g"), ("bh", "b"), ("dh", "d")]:
        t = t.replace(a, b)
    return t


def tokenize(text):
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", text)            # audio-event tags
    text = text.replace("²", " square").replace("=", " equals ").replace("+", " plus ")
    text = re.sub(r"(\w)-(?=\w)", r"\1 ", text)                    # twenty-five, re-e-est
    out = []
    for raw in re.findall(r"[\w\u0900-\u0963\u0966-\u097F']+", text):
        w = raw.lower().strip("'")
        if w.isdigit():
            out += num_words(w).split(); continue
        if w in ("ma",):                                           # F equals ma / MA
            out += ["m", "a"]; continue
        w = re.sub(r"(.)\1{2,}", r"\1", w)                         # ooooh -> oh
        w = w.replace("'s", "s")
        out.append(SAME.get(w, w))
    return out


def sim(a, b):
    fa, fb = fold(a), fold(b)
    if fa == fb: return 1.0
    if min(len(fa), len(fb)) <= 2: return 0.0                      # short words must match exactly
    return SequenceMatcher(None, fa, fb, autojunk=False).ratio()


def align(L, T):
    """Levenshtein alignment with fuzzy equality (sim >= .75). Returns list of (op, li, ti)."""
    n, m = len(L), len(T)
    subc = lambda i, j: 0 if eq[i][j] else (1 if S[i][j] >= .5 or (len(L[i]) <= 3 and len(T[j]) <= 3) else 2.1)
    S = [[sim(L[i], T[j]) for j in range(m)] for i in range(n)]
    eq = [[S[i][j] >= .65 for j in range(m)] for i in range(n)]
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): D[i][0] = i
    for j in range(m + 1): D[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i][j] = min(D[i-1][j-1] + subc(i-1, j-1), D[i-1][j] + 1, D[i][j-1] + 1)
    ops, i, j = [], n, m
    while i or j:
        if i and j and D[i][j] == D[i-1][j-1] + subc(i-1, j-1):
            ops.append(("match" if eq[i-1][j-1] else "sub", i-1, j-1)); i, j = i-1, j-1
        elif i and D[i][j] == D[i-1][j] + 1:
            ops.append(("del", i-1, None)); i -= 1
        else:
            ops.append(("ins", None, j-1)); j -= 1
    return ops[::-1]


def load_lyrics(p):
    lines, protected = [], set()
    for l in Path(p).read_text().splitlines():
        if l.startswith("# protected:"): protected = set(tokenize(l.split(":", 1)[1]))
        elif l.strip() and not l.startswith("#") and not re.match(r"^\s*\[.*\]\s*$", l): lines.append(l.strip())
    toks, line_of = [], []
    for k, l in enumerate(lines):
        for t in tokenize(l): toks.append(t); line_of.append(k)
    return lines, toks, line_of, {fold(w) for w in protected}


def transcript_tokens(eng):
    """[(token, start_sec or None)] - Scribe has word times; Sarvam only chunk starts."""
    if "words" in eng:
        out = []
        for w in eng["words"]:
            if w.get("type") == "audio_event": continue
            for t in tokenize(w["w"]): out.append((t, w["s"]))
        return out
    out = []
    for c in eng.get("chunks", []):
        out += [(t, c["start"]) for t in tokenize(c["text"])]
    return out


def score(lyr, eng):
    lines, L, line_of, PROT = lyr
    lyric_vocab = {fold(w) for w in L}
    raw = transcript_tokens(eng)
    allowed, items = [], []
    T = []
    for t, s in raw:                                               # 3.3 step 1: vocables
        if t in VOCABLES and fold(t) not in lyric_vocab: allowed.append(("vocable", t, s)); continue
        T.append((t, s))
    ops = align(L, [t for t, _ in T])
    tm = lambda j: T[j][1] if j is not None and j < len(T) else None
    # reorder detection: a deleted run of >=3 lyric words that also appears as an inserted run
    ins_text = " ".join(fold(T[j][0]) for op, _, j in ops if op == "ins")
    k = 0
    matched = 0
    while k < len(ops):
        op, i, j = ops[k]
        if op == "match":
            matched += 1; k += 1; continue
        if op == "del":
            run = [ops[x][1] for x in range(k, len(ops)) if ops[x][0] == "del"
                   and all(ops[y][0] == "del" for y in range(k, x + 1))]
            words = [L[x] for x in run]
            # nearest transcript time
            near = next((tm(ops[y][2]) for y in range(k, len(ops)) if ops[y][2] is not None), None)
            prot = [w for w in words if fold(w) in PROT]
            if len(run) >= 3 and " ".join(fold(w) for w in words) in ins_text:
                sung = next((tm(y) for o, _, y in ops if o == "ins" and fold(T[y][0]) == fold(words[0])), near)
                items.append(("REVIEW", "reorder (section sung elsewhere)", " ".join(words), "", sung,
                              lines[line_of[run[0]]]))
                matched += len(run)
            elif prot or len(run) >= 3:
                items.append(("FAIL", "omission" + (" (protected)" if prot else ""), " ".join(words), "", near,
                              lines[line_of[run[0]]]))
            else:
                items.append(("REVIEW", "single word dropped", " ".join(words), "", near, lines[line_of[run[0]]]))
            k += len(run); continue
        if op == "sub":
            lw, tw = L[i], T[j][0]
            s = sim(lw, tw)
            if fold(lw) in PROT and fold(tw) != fold(lw):
                cls, why = ("REVIEW", "sound-alike on protected term") if s >= .5 else ("FAIL", "protected term changed")
            elif s >= .5 or (len(lw) <= 3 and len(tw) <= 3) or fold(tw).startswith(fold(lw)[:4]) or fold(lw).startswith(fold(tw)[:4]):
                cls, why = "REVIEW", "inflection / sound-alike"
            else:
                cls, why = "FAIL", "substitution"
            items.append((cls, why, lw, tw, tm(j), lines[line_of[i]])); k += 1; continue
        # insertion
        tw = T[j][0]
        nxt = next((T[y][0] for y in range(j + 1, min(j + 4, len(T)))), "")
        if fold(tw) in lyric_vocab or any(sim(tw, w) >= .8 for w in set(L)):
            allowed.append(("repeat/harmony", tw, tm(j)))
        elif any(fold(T[y][0]).startswith(fold(tw)) and fold(T[y][0]) != fold(tw)
                 for y in range(j + 1, min(j + 8, len(T)))):
            allowed.append(("stutter", tw, tm(j)))
        elif tw in FUNCTION:
            items.append(("REVIEW", "function word inserted", "", tw, tm(j), ""))
        else:
            items.append(("FAIL", "new word inserted", "", tw, tm(j), ""))
        k += 1
    onset = None if "words" not in eng else next((tm(j) for op, _, j in ops if op == "match"), None)
    return {"coverage": matched / len(L), "fails": [x for x in items if x[0] == "FAIL"],
            "reviews": [x for x in items if x[0] == "REVIEW"], "allowed": allowed, "onset": onset,
            "text": eng.get("text", "")}


def main():
    qc = Path(sys.argv[1])
    report, texts = {}, {}
    for row in read_songs(qc):
        f = qc / "stt" / f"{row['stem']}.json"
        if not f.exists():
            print(f"skip {row['stem']}: no transcript yet (run song_stt.py)"); continue
        lyr = load_lyrics(qc / row["lyrics_file"])
        d = json.loads(f.read_text(encoding="utf-8"))
        for eng in d:
            if "error" in d[eng]: print(f"WARNING {row['stem']} {eng} failed: {d[eng]['error']}")
        report[row["stem"]] = {eng: score(lyr, d[eng]) for eng in d
                               if "error" not in d[eng] and eng not in NOT_SCORED}
        texts[row["stem"]] = {eng: d[eng].get("text", d[eng].get("error")) for eng in d}
    (qc / "song_qc_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str),
                                            encoding="utf-8")

    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Summary"
    hdr = ["Song", "Engine", "Lyric coverage", "FAIL", "REVIEW", "Allowed (ad-libs/repeats/stutters)",
           "Vocal onset (s)", "Verdict"]
    ws.append(hdr)
    det = wb.create_sheet("Items")
    det.append(["Song", "Engine", "Class", "Type", "Lyric word(s)", "Heard", "≈ time (s)", "Lyric line"])
    red, amber, green = (PatternFill("solid", fgColor=c) for c in ("F4CCCC", "FFF2CC", "D9EAD3"))
    for song, engs in report.items():
        for eng, r in engs.items():
            v = "FAIL" if r["fails"] or r["coverage"] < .95 else ("REVIEW" if r["reviews"] else "PASS")
            ws.append([song, eng, round(r["coverage"], 3), len(r["fails"]), len(r["reviews"]),
                       ", ".join(f"{t}:{w}" for t, w, _ in r["allowed"]) or "-",
                       r["onset"], v])
            ws.cell(ws.max_row, 8).fill = {"FAIL": red, "REVIEW": amber, "PASS": green}[v]
            for it in r["fails"] + r["reviews"]:
                det.append([song, eng, *it[:4], round(it[4], 2) if it[4] is not None else None, it[5]])
                det.cell(det.max_row, 3).fill = red if it[0] == "FAIL" else amber
    for s in (ws, det):
        for c in s[1]: c.font = Font(bold=True)
        for col, wdt in zip("ABCDEFGH", (40, 18, 12, 12, 30, 40, 14, 60)): s.column_dimensions[col].width = wdt
        for row in s.iter_rows():
            for c in row: c.alignment = Alignment(wrap_text=True, vertical="top")
    cs = wb.create_sheet("Consensus", 0)
    cs.append(["Song", "Class", "Type", "Lyric word(s)", "Heard", "≈ time (s, Scribe)", "Engine runs agreeing",
               "Lyric line"])
    for song, engs in report.items():
        groups = {}
        for eng, r in engs.items():
            for it in r["fails"] + r["reviews"]:
                key = (it[0], it[1].split(" (")[0], fold(it[2]) if it[2] else "+" + fold(it[3]))
                g = groups.setdefault(key, {"it": it, "engs": [], "t": None})
                if eng in g["engs"]: continue
                g["engs"].append(eng)
                if eng.startswith("scribe") and g["t"] is None: g["t"] = it[4]
        n = len(engs)
        for key, g in sorted(groups.items(), key=lambda kv: (-len(kv[1]["engs"]), kv[0][0])):
            it, k, agree = g["it"], len(g["engs"]), len(g["engs"]) * 2 > n
            cs.append([song, it[0] if agree else it[0] + " (minority: likely STT noise)", it[1], it[2], it[3],
                       round(g["t"], 2) if g["t"] is not None else None, f"{k}/{n}: " + ", ".join(g["engs"]), it[5]])
            cs.cell(cs.max_row, 2).fill = (red if it[0] == "FAIL" else amber) if agree else green
        if not groups:
            cs.append([song, "PASS", "no FAIL or REVIEW items in any engine", "", "", None, f"{n}/{n}", ""])
            cs.cell(cs.max_row, 2).fill = green
    for c in cs[1]: c.font = Font(bold=True)
    for col, wdt in zip("ABCDEFGH", (40, 30, 30, 30, 14, 12, 50, 60)): cs.column_dimensions[col].width = wdt
    for row in cs.iter_rows():
        for c in row: c.alignment = Alignment(wrap_text=True, vertical="top")
    ts = wb.create_sheet("Transcripts")
    ts.append(["Song", "Engine", "Transcript"])
    for song, engs in texts.items():
        for eng, t in engs.items(): ts.append([song, eng, t])
    for c in ts[1]: c.font = Font(bold=True)
    for col, wdt in zip("ABC", (40, 18, 120)): ts.column_dimensions[col].width = wdt
    for row in ts.iter_rows():
        for c in row: c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(qc / "song_qc_report.xlsx")
    write_summary(qc, report)

    for song, engs in report.items():
        print(f"\n===== {song}")
        for eng, r in engs.items():
            print(f"  {eng:16s} coverage {r['coverage']:.0%}  FAIL {len(r['fails'])}  REVIEW {len(r['reviews'])}  "
                  f"onset {r['onset']}  allowed: {[(t, w) for t, w, _ in r['allowed']]}")
            for it in r["fails"] + r["reviews"]:
                print(f"      {it[0]:6s} {it[1]:32s} lyric='{it[2]}' heard='{it[3]}' @{it[4]}")


def write_summary(qc, report):
    """Per-song verdict from the majority-agreed items only."""
    md = ["# Song lyric QC summary", "",
          "Verdict uses only items that more than half of the engine runs agree on. "
          "Minority items are listed separately: confirm them with slice_check.py before dismissing them.", "",
          "| Song | Verdict | Lyric coverage (vocal runs) | Vocal onset | Agreed items | Minority items |",
          "|---|---|---|---|---|---|"]
    for song, engs in report.items():
        n = len(engs)
        groups = {}
        for eng, r in engs.items():
            for it in r["fails"] + r["reviews"]:
                key = (it[0], it[1].split(" (")[0], fold(it[2]) if it[2] else "+" + fold(it[3]))
                g = groups.setdefault(key, {"it": it, "k": 0, "t": None, "e": set()})
                if eng in g["e"]: continue
                g["e"].add(eng); g["k"] += 1
                if eng.startswith("scribe") and g["t"] is None: g["t"] = it[4]
        fmt = lambda g: (f"{g['it'][0]} {g['it'][1]}: lyric '{g['it'][2]}' heard '{g['it'][3]}'"
                         + (f" @{g['t']:.1f}s" if g["t"] is not None else "") + f" ({g['k']}/{n})")
        agreed = [g for g in groups.values() if g["k"] * 2 > n]
        minority = [g for g in groups.values() if g["k"] * 2 <= n]
        verdict = ("FAIL" if any(g["it"][0] == "FAIL" for g in agreed)
                   else "REVIEW" if agreed else "PASS")
        cov = sorted(r["coverage"] for e, r in engs.items() if "vocals" in e)
        cov_s = f"{cov[0]:.0%}-{cov[-1]:.0%}" if cov else "-"
        onset = next((r["onset"] for e, r in engs.items() if e == "scribe_vocals_1"), None)
        md.append(f"| {song} | **{verdict}** | {cov_s} | {onset if onset is not None else '-'} s | "
                  f"{'<br>'.join(fmt(g) for g in agreed) or '-'} | {'<br>'.join(fmt(g) for g in minority) or '-'} |")
    (qc / "song_qc_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")


main()
