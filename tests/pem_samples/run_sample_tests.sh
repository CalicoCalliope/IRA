#!/usr/bin/env bash
set -euo pipefail

# Pick a Python binary: prefer $PY_BIN, else python, else python3
PY_BIN="${PY_BIN:-}"
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then
    PY_BIN="python"
  elif command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
  else
    echo "No python or python3 found on PATH. Activate your venv first: source .venv/bin/activate"
    exit 127
  fi
fi

here="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$here/../.." && pwd)"

# Sanity check
if ! "$PY_BIN" "$repo_root/ira/scripts/pem_parser.py" --help >/dev/null 2>&1; then
  echo "pem_parser.py not runnable. Are you in the right repo and venv?"
  echo "Try:  source .venv/bin/activate"
  exit 1
fi

n=1
for f in "$here"/pem_min.jsonl "$here"/pem_mixed.jsonl "$here"/pem_with_meta.jsonl; do
  echo "===== Test $n: $(basename "$f") ====="
  "$PY_BIN" "$repo_root/ira/scripts/pem_parser.py" --input "$f"
  echo
  n=$((n+1))
done

echo "All sample tests completed."
