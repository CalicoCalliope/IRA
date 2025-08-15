"""
CuBERT embedding pipeline (cleaned).

Key changes vs previous version:
- Removed duplicate/placeholder second half of the file.
- Lazy-loads heavy resources (model, SentencePiece) only when called.
- Safer path handling for google-research/cubert and PythonTokenizer.
- Clear env var usage with sensible defaults relative to repo root.
- Utility funcs for Qdrant; non-destructive collection creation by default.
- Minimal __main__ example guarded to avoid side effects on import.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Tuple, List

import numpy as np
import torch
from dotenv import load_dotenv
from transformers import AutoModel
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import sentencepiece as spm

# ----------------------------
# Env and paths
# ----------------------------
load_dotenv()

# Compute repo root from this file location: <repo>/ira/cubert_pipeline.py
REPO_ROOT = Path(__file__).resolve().parents[1]

# Path to google-research/cubert folder that contains python_tokenizer.py
CUBERT_SRC = os.getenv("CUBERT_SRC", str(REPO_ROOT / "google-research" / "cubert"))
MODEL_NAME = os.getenv("MODEL_NAME", "claudios/cubert-20210711-Python-512")
SPM_PATH   = os.getenv("CUBERT_SPM", str(REPO_ROOT / "cubert_python_tokenizer.spm"))  # SentencePiece model file

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ira-pem-logs")
MAX_LENGTH = int(os.getenv("MAX_LENGTH", "512"))

# ----------------------------
# Lazy loaders
# ----------------------------
_python_tokenizer_cls = None
_sp_model: spm.SentencePieceProcessor | None = None
_model: AutoModel | None = None
_device = os.getenv("TORCH_DEVICE", "cpu")


def _ensure_cubert_on_path() -> None:
    cubert_path = Path(CUBERT_SRC)
    if not cubert_path.exists():
        raise FileNotFoundError(
            f"CUBERT_SRC not found at {cubert_path}. Set env CUBERT_SRC to your google-research/cubert folder."
        )
    p = str(cubert_path.resolve())
    if p not in sys.path:
        sys.path.insert(0, p)


def load_python_tokenizer():
    global _python_tokenizer_cls
    if _python_tokenizer_cls is None:
        _ensure_cubert_on_path()
        try:
            from python_tokenizer import PythonTokenizer  # type: ignore
        except Exception as e:
            raise ImportError(
                "Failed to import PythonTokenizer from google-research/cubert."
            ) from e
        _python_tokenizer_cls = PythonTokenizer
    return _python_tokenizer_cls


def load_sp() -> spm.SentencePieceProcessor:
    global _sp_model
    if _sp_model is None:
        if not Path(SPM_PATH).exists():
            raise FileNotFoundError(
                f"SentencePiece model not found at {SPM_PATH}. Set env CUBERT_SPM."
            )
        sp = spm.SentencePieceProcessor()
        sp.load(SPM_PATH)
        _sp_model = sp
    return _sp_model


def load_model() -> AutoModel:
    global _model
    if _model is None:
        m = AutoModel.from_pretrained(MODEL_NAME)
        m.eval()
        try:
            m.to(_device)
        except Exception:
            # Fallback to CPU silently if invalid device provided
            m.to("cpu")
        _model = m
    return _model

# ----------------------------
# Tokenization helpers
# ----------------------------

def tokenize_code(code: str) -> List[str]:
    Tok = load_python_tokenizer()
    tok = Tok()
    # The CuBERT PythonTokenizer returns objects with `.text`; keep token strings
    tokens = [t.text for t in tok.tokenize(code)]
    return tokens


def tokens_to_ids(tokens: List[str]) -> List[int]:
    sp = load_sp()
    # Join tokens with spaces then SPM-encode to ids
    # If your SPM requires BOS/EOS:
    # ids = [sp.bos_id()] + sp.encode(" ".join(tokens), out_type=int) + [sp.eos_id()]
    ids = sp.encode(" ".join(tokens), out_type=int)
    return ids


def pad_truncate(ids: List[int], max_len: int) -> Tuple[List[int], List[int]]:
    sp = load_sp()
    # Truncate
    ids = ids[:max_len]
    # Pad with SPM pad id if available, else 0
    pad_id = sp.pad_id() if sp.pad_id() >= 0 else 0
    attention = [1] * len(ids)
    if len(ids) < max_len:
        pad_n = max_len - len(ids)
        ids = ids + [pad_id] * pad_n
        attention = attention + [0] * pad_n
    return ids, attention


@torch.inference_mode()
def get_cubert_embedding(code_snippet: str) -> np.ndarray:
    model = load_model()
    tokens = tokenize_code(code_snippet)
    ids = tokens_to_ids(tokens)
    ids, attn = pad_truncate(ids, MAX_LENGTH)

    input_ids = torch.tensor([ids], dtype=torch.long, device=next(model.parameters()).device)
    attention_mask = torch.tensor([attn], dtype=torch.long, device=next(model.parameters()).device)

    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
    # CLS embedding at position 0
    cls = outputs.last_hidden_state[:, 0, :].squeeze(0).detach().cpu().numpy().astype(np.float32)
    return cls

# ----------------------------
# Qdrant utilities
# ----------------------------
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection(name: str, dim: int):
    """Create the collection if it doesn't exist; don't drop existing data."""
    try:
        info = client.get_collection(name)
        # Optionally validate vector size; if mismatch, you may recreate deliberately.
        # Skipping destructive changes by default.
        _ = info
    except Exception:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def store_embedding_in_qdrant(embedding: np.ndarray, payload: dict) -> str:
    # Qdrant expects float32
    vec = np.asarray(embedding, dtype=np.float32).tolist()
    pid = str(uuid.uuid4())
    point = PointStruct(id=pid, vector=vec, payload=payload)
    client.upsert(collection_name=COLLECTION_NAME, points=[point])
    return pid


# ----------------------------
# Example (safe to run)
# ----------------------------
if __name__ == "__main__":
    try:
        code_snippet = "c = 1/0"  # simple snippet
        emb = get_cubert_embedding(code_snippet)
        ensure_collection(COLLECTION_NAME, dim=emb.shape[-1])

        payload = {
            "timestamp": "2025-08-14T21:38:34.238Z",
            "pem": "[RUNTIME ERROR] ZeroDivisionError: division by zero",
            "username": os.getenv("USER", "unknown"),
            "activeFile": "example.py",
            "pythonVersion": sys.version.split()[0],
        }
        point_id = store_embedding_in_qdrant(emb, payload)
        print("Stored point:", point_id)
    except Exception as e:
        # Provide a clear, actionable message; do not mask the real error
        print(f"[CuBERT] Failed to run example: {type(e).__name__}: {e}")