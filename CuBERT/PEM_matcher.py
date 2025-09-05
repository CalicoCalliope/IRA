import os
import sys
from typing import Optional, Callable


def _load_dotenv_if_present(repo_root: str) -> None:
    """Load environment variables from <repo>/.env if python-dotenv is available."""
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    env_path = os.path.join(repo_root, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)


def _maybe_call_local_entry(argv) -> Optional[int]:
    """Call a local entry function if one exists.

    We avoid any self-import or runpy indirection to prevent recursion. If a
    function like `cli`, `run`, `entrypoint`, `pipeline`, or `run_pipeline`
    exists in *this* module, we call it.
    """
    candidates = ("cli", "run", "entrypoint", "pipeline", "run_pipeline")
    for name in candidates:
        fn: Optional[Callable] = globals().get(name)  # type: ignore[assignment]
        if callable(fn):
            result = fn(argv[1:])  # pass through CLI args after program name
            return 0 if result in (None, True) else int(result)
    return None


def cli(argv):
    """CLI for the CuBERT PEM pipeline."""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        prog="pem_parser",
        description="Run CuBERT PEM pipeline.",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=os.environ.get("PEM_INPUT", ""),
        help="Path to input file (e.g., JSONL) or leave empty for a tiny built-in sample.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=int(os.environ.get("PEM_LIMIT", "0") or 0),
        help="Max number of items to process (0 = no limit).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.environ.get("PEM_BATCH_SIZE", "32") or 32),
        help="Batch size for embedding.",
    )

    # Mongo config
    parser.add_argument(
        "--mongo-uri",
        type=str,
        default=os.environ.get("MONGO_URI", ""),
        help="MongoDB connection string. Falls back to MONGO_URI env var.",
    )
    parser.add_argument(
        "--mongo-db",
        type=str,
        default=os.environ.get("MONGO_DB", ""),
        help="MongoDB database name. Falls back to MONGO_DB env var.",
    )
    parser.add_argument(
        "--mongo-collection",
        type=str,
        default=os.environ.get("MONGO_COLLECTION", ""),
        help="MongoDB collection name. Falls back to MONGO_COLLECTION env var.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse args and exit without executing the pipeline.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually write results to MongoDB. Without this, no DB writes occur.",
    )

    args = parser.parse_args(argv)

    if args.dry_run:
        print("PEM pipeline dry-run: arguments parsed; no execution.")
        return 0

    # Call the actual pipeline.
    return run_pipeline(args)


def run_pipeline(args) -> int:
    """Hook up CuBERT/MongoDB pipeline.

    This keeps behavior safe by default: we *do not* write to MongoDB unless
    the user passes --commit. You can wire in your actual tokenization and
    embedding where indicated below.
    """
    import json
    from pathlib import Path

    try:
        # 1) Load or synthesize input
        items = []
        if args.input:
            p = Path(args.input)
            if not p.exists():
                print(f"[PEM] Input not found: {p}")
                return 2
            # Assume JSONL for convenience; tweak as needed.
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Fallback: treat the whole line as a 'text' field.
                        items.append({"text": line})
        else:
            # Tiny built-in sample
            items = [
                {"text": "NameError: name 'foo' is not defined"},
                {"text": "ZeroDivisionError: division by zero"},
            ]

        if args.limit and args.limit > 0:
            items = items[: args.limit]

        print(f"[PEM] Loaded {len(items)} item(s). Batch size={args.batch_size}")

        # 2) Tokenize/Embed (STUB). Replace with your actual CuBERT logic.
        # For now, produce a trivial 'embedding' to prove plumbing works.
        processed = []
        for obj in items:
            text = obj.get("text", "")
            # TODO: replace with real tokenizer + CuBERT embedding inference
            embedding = [float(len(text))]  # placeholder
            processed.append(
                {
                    **obj,
                    "embedding": embedding,
                }
            )

        print(f"[PEM] Produced {len(processed)} embedding(s).")

        # 3) Optionally write to MongoDB if --commit is set
        if not args.commit:
            print("[PEM] --commit not provided; skipping MongoDB writes.")
            return 0

        if not args.mongo_uri or not args.mongo_db or not args.mongo_collection:
            print(
                "[PEM] Missing MongoDB config. Provide --mongo-uri, --mongo-db, and --mongo-collection "
                "or set MONGO_URI / MONGO_DB / MONGO_COLLECTION env vars."
            )
            return 3

        try:
            from pymongo import MongoClient  # type: ignore
        except Exception as exc:
            print(
                f"[PEM] pymongo is not installed: {type(exc).__name__}: {exc}\n"
                "      pip install pymongo"
            )
            return 4

        client = MongoClient(args.mongo_uri)
        coll = client[args.mongo_db][args.mongo_collection]

        # Upsert by a stable key if you have one; for now we just insert many.
        if processed:
            result = coll.insert_many(processed, ordered=False)
            print(f"[PEM] Inserted {len(result.inserted_ids)} document(s) into MongoDB.")
        else:
            print("[PEM] Nothing to write.")

        return 0

    except Exception as exc:
        # Show real exception messages (no placeholders).
        print(f"[PEM] pipeline failed: {type(exc).__name__}: {exc}")
        return 1


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv

    # Load optional env vars from repo root. This is safe and non-recursive.
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _load_dotenv_if_present(repo_root)

    # Try to call a local entry function if one exists; otherwise do nothing.
    ret = _maybe_call_local_entry(argv)
    return 0 if ret is None else ret


if __name__ == "__main__":
    sys.exit(main())