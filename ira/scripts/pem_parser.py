import os
import sys
import runpy

def _ensure_repo_root_on_syspath():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    return repo_root

def _try_call_entry(mod, argv):
    for name in ("main", "cli", "run", "entrypoint"):
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn(argv[1:])
    return None

def _run_fallback(script_path):
    return runpy.run_path(script_path, run_name="__main__")

def main(argv=None):
    if argv is None:
        argv = sys.argv
    repo_root = _ensure_repo_root_on_syspath()
    script_path = os.path.join(repo_root, "CuBERT", "PEM_matcher.py")
    # Run CuBERT/PEM_matcher.py as if executed directly, preserving CLI args
    old_argv = sys.argv
    sys.argv = argv
    try:
        _run_fallback(script_path)
    finally:
        sys.argv = old_argv
    return 0

if __name__ == "__main__":
    sys.exit(main())
