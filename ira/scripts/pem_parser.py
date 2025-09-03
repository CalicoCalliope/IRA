import os
import sys
import argparse
import json
from typing import Iterable, Dict, Any, List

# Ensure the repo root is on sys.path so `ira` package is importable when
# running this file directly (python ira/scripts/pem_parser.py ...)
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import os, sys
from pathlib import Path

# Ensure repo root is importable so we can import the service pipeline directly in dev
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    # Dev-only local import; prefer calling the embedder service in production.
    from services.embedder.src.cubert_pipeline import get_cubert_embedding  # type: ignore
except Exception:
    # Fallback: call the embedder service over HTTP (via coordinator or direct)
    import json, urllib.request
    EMBEDDER_URL = os.getenv("EMBEDDER_URL", "http://127.0.0.1:8001")
    def get_cubert_embedding(text: str):
        payload = {"id":"adhoc","username":"local","pemType":"code","timestamp":0,"text":text}
        req = urllib.request.Request(
            f"{EMBEDDER_URL}/embed",
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type":"application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["vector"]



def _iter_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # Be forgiving: treat the whole line as a raw text sample
                yield {"text": line}


def _load_items(input_path: str | None, limit: int | None) -> List[Dict[str, Any]]:
    if not input_path:
        # Tiny built-in sample
        samples = [
            {"text": "NameError: name 'foo' is not defined"},
            {"text": "ZeroDivisionError: division by zero"},
        ]
        return samples[: limit or len(samples)]

    if not os.path.exists(input_path):
        print(f"[PEM] Input not found: {input_path}")
        return []

    items: List[Dict[str, Any]] = []
    for obj in _iter_jsonl(input_path):
        # Accept either {"text": ...} or {"pem": ...}; prefer explicit text
        text = obj.get("text") or obj.get("pem")
        if not text:
            continue
        items.append({"text": text, "meta": {k: v for k, v in obj.items() if k not in ("text", "pem")}})
        if limit and len(items) >= limit:
            break
    return items


def run_pipeline(args: argparse.Namespace) -> int:
    items = _load_items(args.input, args.limit)
    if not items:
        # Already printed a friendly message if path was missing; otherwise silent.
        return 1 if args.input else 0

    batch_size = int(args.batch_size)
    produced = 0

    print(f"[PEM] Loaded {len(items)} item(s). Batch size={batch_size}")

    # Simple sequential loop; swap for real batching later if needed
    for it in items:
        text = it["text"]
        _ = get_cubert_embedding(text)
        produced += 1

    print(f"[PEM] Produced {produced} embedding(s).")

    if not args.commit:
        print("[PEM] --commit not provided; skipping MongoDB writes.")
    else:
        # Placeholder for future DB writes
        print("[PEM] --commit provided, but DB integration is not enabled in this script yet.")

    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pem_parser",
        description="Run CuBERT/CodeBERT PEM pipeline to produce embeddings.",
    )
    p.add_argument("--input", help="Path to input JSONL with {text: ...} (or {pem: ...}).", default=None)
    p.add_argument("--limit", type=int, default=0, help="Max number of items to process (0 = no limit).")
    p.add_argument("--batch-size", type=int, default=32, help="Batch size (reserved; current loop is sequential).")
    p.add_argument("--dry-run", action="store_true", help="Parse args and exit without executing the pipeline.")
    p.add_argument("--commit", action="store_true", help="Future: write results to DB (currently no-op).")
    return p


def main(argv: List[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.dry_run:
        print("PEM pipeline dry-run: arguments parsed; no execution.")
        return 0

    # Normalize limit
    if args.limit and args.limit < 0:
        args.limit = 0

    return run_pipeline(args)


if __name__ == "__main__":
    raise SystemExit(main())
