#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRV="$ROOT/services/embedder"
VENV="$SRV/.venv"

# Prefer Python 3.12 for smoother torch wheels; fallback to python3
PY_BIN="${PY_BIN:-python3}"

if [ ! -d "$VENV" ]; then
  "$PY_BIN" -m venv "$VENV"
fi
source "$VENV/bin/activate"
pip install -U pip setuptools wheel
pip install -r "$SRV/requirements.txt"

# Ensure google-research is on PYTHONPATH
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/google-research"

# Load env overrides if present
set -a
[ -f "$SRV/.env" ] && source "$SRV/.env"
set +a

# Run service
python "$SRV/src/app.py"
