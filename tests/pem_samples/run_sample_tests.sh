#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$here/../.." && pwd)"

# 0) Check CLI is runnable
if ! python "$repo_root/ira/scripts/pem_parser.py" --help >/dev/null 2>&1; then
  echo "pem_parser.py not runnable. Activate venv:  source .venv/bin/activate"
  exit 1
fi

# 1) Generate sample JSONLs (idempotent)
cat > "$here/pem_min.jsonl" <<'JSON'
{"text": "NameError: name 'foo' is not defined"}
{"pem": "ZeroDivisionError: division by zero"}
JSON

cat > "$here/pem_mixed.jsonl" <<'JSON'
{"text": "TypeError: unsupported operand type(s) for +: 'int' and 'str'"}
{"note": "ignored"}
{"pem": "IndexError: list index out of range"}
JSON

cat > "$here/pem_with_meta.jsonl" <<'JSON'
{"text": "KeyError: 'id'", "meta": {"file":"a.py", "user":"zi"}}
{"pem": "ValueError: invalid literal for int()", "origin": "unit-test"}
{"text": "AttributeError: object has no attribute 'x'", "line": 12}
JSON

# Empty file
: > "$here/empty.jsonl"

# Malformed lines: keep some non-JSON and broken JSON
cat > "$here/malformed.jsonl" <<'JSON'
{"text": "valid json line"}
not-json at all
{"pem": "NameError: name 'x' is not defined"}
{"text": "unterminated
{"unknown":"ignored-but-won't-crash"}
JSON

# Very long input (tests truncation to MAX_LENGTH)
python - "$here/long.jsonl" <<'PY'
import sys
long_code = "def f():\n    " + " + ".join("x" for _ in range(5000))
open(sys.argv[1],"w").write('{"text": %r}\n' % long_code)
PY

# Scale test (100 synthetic lines)
python - "$here/bulk100.jsonl" <<'PY'
import sys
with open(sys.argv[1],"w") as f:
    for i in range(100):
        f.write('{"text": "TypeError: unsupported operand type(s) for +: int and str #%d"}\n' % i)
PY

# Odd keys / blanks
cat > "$here/odd_keys.jsonl" <<'JSON'
{"message":"ignored key"}
{"pem":"ZeroDivisionError: division by zero"}
{"text":""}
{"text":"IndexError: list index out of range"}
JSON

# 2) Run them in order
run() {
  echo "===== $1 ====="
  python "$repo_root/ira/scripts/pem_parser.py" --input "$2"
  echo
}

run "Minimal"         "$here/pem_min.jsonl"
run "Mixed keys"      "$here/pem_mixed.jsonl"
run "With metadata"   "$here/pem_with_meta.jsonl"
run "Empty file"      "$here/empty.jsonl"
run "Malformed lines" "$here/malformed.jsonl"
run "Very long input" "$here/long.jsonl"

echo "===== Scale x100 (timed) ====="
# macOS: /usr/bin/time -l ; Linux: /usr/bin/time -v
if /usr/bin/time -l true >/dev/null 2>&1; then
  /usr/bin/time -l python "$repo_root/ira/scripts/pem_parser.py" --input "$here/bulk100.jsonl"
else
  /usr/bin/time -v python "$repo_root/ira/scripts/pem_parser.py" --input "$here/bulk100.jsonl"
fi
echo

run "Odd keys / blanks" "$here/odd_keys.jsonl"

echo "All sample tests completed."
