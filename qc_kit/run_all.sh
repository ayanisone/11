#!/usr/bin/env bash
# One command for steps 1-3 (+ lyric docs).  Usage:  ./run_all.sh <project_dir>
set -euo pipefail
P="${1:?usage: ./run_all.sh <project_dir>}"
KIT="$(cd "$(dirname "$0")" && pwd)"
PY="$KIT/.venv/bin/python"
[ -x "$PY" ] || PY=python3
start=$(date +%s)

echo "== Step 1: separate vocals (demucs)"
FILES=()
while IFS= read -r f; do FILES+=("$P/input/$f"); done < <("$PY" -c "
import sys; sys.path.insert(0, '$KIT/scripts'); from common import read_songs
for r in read_songs('$P'): print(r['song_file'])")
"$PY" -m demucs --two-stems=vocals -n htdemucs -o "$P/stems" "${FILES[@]}"

echo "== Step 2: transcribe (Scribe x3 + Sarvam)"
"$PY" "$KIT/scripts/song_stt.py" "$P" "${@:2}"

echo "== Step 3: score against lyrics"
"$PY" "$KIT/scripts/song_qc_score.py" "$P"

echo "== Lyric documents"
"$PY" "$KIT/scripts/make_lyric_docs.py" "$P"

echo "Done in $(( $(date +%s) - start )) s. Open $P/song_qc_summary.md and $P/song_qc_report.xlsx"
