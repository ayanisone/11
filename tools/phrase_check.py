#!/usr/bin/env python3
"""Key-phrase transcript check: catches merged or dropped lines that the majority-vote scorer can miss.

Usage: python3 tools/phrase_check.py <qc_project_dir> <phrases.txt> [song_stem ...]
phrases.txt: one regex per line (lowercase; '|' for alternatives). A phrase counts as present when
at least 2 of the 3 Scribe runs (mix, vocals_1, vocals_2) contain it. Prints OK or the missing phrases per song.
"""
import json, re, sys, os
proj, pfile, only = sys.argv[1], sys.argv[2], set(sys.argv[3:])
phrases = [l.strip() for l in open(pfile) if l.strip() and not l.startswith('#')]
bad = 0
for f in sorted(os.listdir(os.path.join(proj, 'stt'))):
    stem = f[:-5]
    if only and stem not in only: continue
    d = json.load(open(os.path.join(proj, 'stt', f)))
    texts = [d[r]['text'].lower().replace("'round", "round").replace('-', ' ') for r in ('scribe_mix', 'scribe_vocals_1', 'scribe_vocals_2') if r in d]
    miss = [f"{p} ({sum(bool(re.search(p, t)) for t in texts)}/{len(texts)})" for p in phrases
            if sum(bool(re.search(p, t)) for t in texts) < 2]
    bad += bool(miss)
    print(f"{stem:32s}", 'OK' if not miss else 'MISSING: ' + '; '.join(miss))
sys.exit(1 if bad else 0)
