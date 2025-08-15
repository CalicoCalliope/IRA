# PEM Sample Tests

Tiny JSONL datasets to exercise the `pem_parser.py` CLI without touching MongoDB.

## What each test covers

1. **Minimal** – two short lines.
2. **Mixed keys** – accepts either `{text: ...}` or `{pem: ...}`; blank lines allowed.
3. **With metadata** – extra fields ride along in `meta` (CLI ignores them).
4. **Empty file** – no-op, no crashes.
5. **Malformed lines** – non-JSON or broken JSON become raw text samples.
6. **Very long input** – ensures tokenizer truncation to `MAX_LENGTH` doesn’t crash.
7. **Scale x100** – quick throughput sanity check (prints wall-clock & peak memory).
8. **Odd keys / blanks** – unknown keys ignored; empty `text` skipped.

## Prereqs

- Activate the virtualenv:  
  `source .venv/bin/activate`

- Set `.env` for HF-only mode (example):

```bash
MODEL_NAME=microsoft/codebert-base
USE_HF_ONLY=1
MAX_LENGTH=512
TORCH_DEVICE=cpu
```

## Run all samples

```bash
./tests/pem_samples/run_sample_tests.sh
```

If you see messages like:

[PEM] Loaded N item(s). Batch size=32  
[PEM] Produced N embedding(s).  
[PEM] --commit not provided; skipping MongoDB writes.

…you’re good!