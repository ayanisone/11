#!/usr/bin/env bash
# Idempotent setup for the NE-TTS model. Safe to re-run: each stage is skipped
# if it is already done, so a warm checkout reaches ready in a couple of seconds.
set -euo pipefail

cd "$(dirname "$0")"

PY="${PYTHON:-python3.12}"
VENV=".venv"
MODEL_DIR="model"
STAMP="$VENV/.deps-installed"

command -v "$PY" >/dev/null 2>&1 || {
  echo "error: $PY not found. This model's pins require Python 3.12." >&2
  echo "       Set PYTHON=/path/to/python3.12 and re-run." >&2
  exit 1
}

if [ ! -d "$VENV" ]; then
  echo "==> creating venv ($($PY -V 2>&1))"
  "$PY" -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
fi

if [ ! -f "$STAMP" ] || [ requirements.txt -nt "$STAMP" ]; then
  echo "==> installing dependencies (several minutes on a cold cache)"
  "$VENV/bin/pip" install --quiet -r requirements.txt
  touch "$STAMP"
else
  echo "==> dependencies already installed"
fi

if [ ! -f "$MODEL_DIR/model.pth" ]; then
  echo "==> downloading checkpoint (346 MB)"
  "$VENV/bin/python" - <<'PYEOF'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="sulabhkatiyar/indian-ne-multilingual-tts",
    local_dir="model",
    allow_patterns=["model.pth", "config.json", "speakers.pth",
                    "language_ids.json", "tts_release_meta.json"],
)
PYEOF
else
  echo "==> checkpoint already present"
fi

echo "==> ready. try:  ./.venv/bin/python tts.py --list-voices"
