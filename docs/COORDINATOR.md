# Coordinator quickstart - embeddings runtime

Goal: run embeddings locally without asking users to install anything.

## What the coordinator must do
1) Create and reuse a managed venv in the repo, then install deps from `requirements.txt`.
2) Run a health check before use and show a friendly status.
3) Call a one-shot Python snippet to compute embeddings, or run a tiny Python service later.

## Requirements to pin in requirements.txt
```
torch
transformers
sentencepiece
absl-py
regex
python-dotenv
qdrant-client
```
## Minimal coordinator code (Node/TS)

```ts
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import * as fs from "node:fs";

export function ensureVenv(repoRoot: string) {
  const py = process.env.IRA_PY || "python3";
  const venvDir = join(repoRoot, ".ira", ".venv");
  const vpy = process.platform === "win32"
    ? join(venvDir, "Scripts", "python.exe")
    : join(venvDir, "bin", "python");

  if (!fs.existsSync(vpy)) {
    fs.mkdirSync(venvDir, { recursive: true });
    spawnSync(py, ["-m", "venv", venvDir], { stdio: "inherit" });
  }
  spawnSync(vpy, ["-m", "pip", "install", "-U", "pip", "setuptools", "wheel"], { stdio: "inherit" });
  spawnSync(vpy, ["-m", "pip", "install", "-r", join(repoRoot, "requirements.txt")], { stdio: "inherit" });
  return vpy;
}

export function healthCheck(vpy: string, repoRoot: string) {
  const env = { ...process.env, PYTHONPATH: join(repoRoot, "google-research") };
  const code = `
import json, pathlib, ira.cubert_pipeline as m
print(json.dumps({
  "cubert_src": str(m.CUBERT_SRC),
  "cubert_src_exists": pathlib.Path(m.CUBERT_SRC).exists(),
  "spm_path": str(m.SPM_PATH),
  "spm_exists": pathlib.Path(m.SPM_PATH).exists(),
  "use_hf_only": m.USE_HF_ONLY,
  "model_name": m.MODEL_NAME
}))
`;
  const r = spawnSync(vpy, ["-c", code], { env, cwd: repoRoot });
  return { ok: r.status === 0, out: r.stdout.toString(), err: r.stderr.toString() };
}

export function embedOnce(vpy: string, repoRoot: string, code: string) {
  const env = { ...process.env, PYTHONPATH: join(repoRoot, "google-research") };
  const py = `
import json, sys
from ira.cubert_pipeline import get_cubert_embedding
src = sys.stdin.read()
vec = get_cubert_embedding(src)
print(json.dumps(vec.tolist()))
`;
  const r = spawnSync(vpy, ["-c", py], { env, cwd: repoRoot, input: code });
  if (r.status !== 0) throw new Error(r.stderr.toString() || "embedding failed");
  return JSON.parse(r.stdout.toString());
}

## Assets and paths

- Repo layout expected:
  - `google-research/cubert/` vendor folder is committed. Our pipeline auto-adds `google-research` to `sys.path`.
  - `cubert_python_tokenizer.spm` should exist at repo root. Set `CUBERT_SPM` if you store it elsewhere.
- Fallback: set `USE_HF_ONLY=1` to bypass CuBERT if assets are missing.

## Runtime note

`get_cubert_embedding` needs **PyTorch** and **Transformers** at runtime. Make sure the coordinator installs them in the managed venv. If PyTorch wheels for your Python are tricky, prefer **Python 3.12** for the venv.
