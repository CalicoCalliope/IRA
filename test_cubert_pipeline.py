import os
import sys
from pathlib import Path
import numpy as np
import torch

from transformers import AutoModel
import sentencepiece as spm

# Optional: Qdrant test
QDRANT_ENABLED = True
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance
except Exception:
    QDRANT_ENABLED = False

# ----------------------------
# Config via env vars
# ----------------------------
MODEL_NAME = os.getenv("MODEL_NAME", "claudios/cubert-20210711-Python-512")
CUBERT_SRC = os.getenv("CUBERT_SRC", "./google-research/cubert")
SPM_PATH   = os.getenv("CUBERT_SPM", "./cubert_python_tokenizer.spm")
MAX_LENGTH = int(os.getenv("MAX_LENGTH", "512"))

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION  = os.getenv("COLLECTION_NAME", "ira-pem-logs-test")

# ----------------------------
# Imports from CuBERT
# ----------------------------
if not Path(CUBERT_SRC).exists():
    raise FileNotFoundError(f"CUBERT_SRC not found at {CUBERT_SRC}. Set env CUBERT_SRC to the cubert folder.")
sys.path.append(str(Path(CUBERT_SRC).resolve()))
from python_tokenizer import PythonTokenizer  # from google-research

# ----------------------------
# Load model and SentencePiece
# ----------------------------
print("Loading model:", MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
model.eval()

sp = spm.SentencePieceProcessor()
if not Path(SPM_PATH).exists():
    raise FileNotFoundError(f"SentencePiece model not found at {SPM_PATH}. Set env CUBERT_SPM.")
sp.load(SPM_PATH)
print("Loaded SentencePiece vocab with size:", sp.get_piece_size())

# ----------------------------
# Tokenization helpers
# ----------------------------
_tok = PythonTokenizer()

def tokenize_code(code: str):
    tokens = [t.text for t in _tok.tokenize(code)]
    return tokens

def tokens_to_ids(tokens):
    ids = sp.encode(" ".join(tokens), out_type=int)
    return ids

def pad_truncate(ids, max_len):
    ids = ids[:max_len]
    pad_id = sp.pad_id() if sp.pad_id() >= 0 else 0
    attn = [1] * len(ids)
    if len(ids) < max_len:
        pad_count = max_len - len(ids)
        ids = ids + [pad_id] * pad_count
        attn = attn + [0] * pad_count
    return ids, attn

@torch.inference_mode()
def embed(code: str) -> np.ndarray:
    tokens = tokenize_code(code)
    ids = tokens_to_ids(tokens)
    ids, attn = pad_truncate(ids, MAX_LENGTH)

    input_ids = torch.tensor([ids], dtype=torch.long)
    attention_mask = torch.tensor([attn], dtype=torch.long)

    out = model(input_ids=input_ids, attention_mask=attention_mask)
    vec = out.last_hidden_state[:, 0, :].squeeze(0).cpu().numpy().astype(np.float32)  # CLS
    return vec

def cosine(u: np.ndarray, v: np.ndarray) -> float:
    nu = np.linalg.norm(u)
    nv = np.linalg.norm(v)
    if nu == 0 or nv == 0:
        return 0.0
    return float(np.dot(u, v) / (nu * nv))

# ----------------------------
# Qdrant helpers (optional)
# ----------------------------
def qdrant_roundtrip(vectors, payloads):
    if not QDRANT_ENABLED:
        print("Qdrant not installed. Skipping Qdrant test.")
        return
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        dim = vectors[0].shape[-1]
        # Recreate test collection for a clean run
        client.recreate_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        points = [
            PointStruct(id=str(i), vector=v.astype(np.float32).tolist(), payload=payloads[i])
            for i, v in enumerate(vectors)
        ]
        client.upsert(collection_name=COLLECTION, points=points)
        print(f"Inserted {len(points)} points into Qdrant collection '{COLLECTION}'.")
    except Exception as e:
        print("Qdrant test skipped due to error:", repr(e))

# ----------------------------
# Main tests
# ----------------------------
if __name__ == "__main__":
    # A few simple code snippets
    snippets = {
        "zero_div": "c = 1/0",
        "zero_div_variant": "def f():\n    x = 1/0\n    return x",
        "different_op": "c = 1+0",
        "function_add": "def add(a, b):\n    return a + b",
    }

    # Show tokenization and IDs for the first one
    print("\n=== Tokenization sanity check ===")
    tks = tokenize_code(snippets["zero_div"])
    ids = tokens_to_ids(tks)
    print("Tokens:", tks[:30])
    print("First 30 IDs:", ids[:30])
    print("Total tokens:", len(tks), "Total ids:", len(ids))

    # Embed all
    print("\n=== Embedding each snippet ===")
    embs = {}
    for name, code in snippets.items():
        vec = embed(code)
        embs[name] = vec
        print(f"{name:>16}: shape={vec.shape}, dtype={vec.dtype}")

    # Cosine similarities
    print("\n=== Cosine similarities ===")
    pairs = [
        ("zero_div", "zero_div_variant"),
        ("zero_div", "different_op"),
        ("zero_div", "function_add"),
        ("different_op", "function_add"),
    ]
    for a, b in pairs:
        sim = cosine(embs[a], embs[b])
        print(f"cos({a}, {b}) = {sim:.4f}")

    # Optional Qdrant round-trip
    print("\n=== Qdrant round-trip (optional) ===")
    payloads = [{"name": k, "code": snippets[k]} for k in snippets.keys()]
    qdrant_roundtrip(list(embs.values()), payloads)

    print("\nAll tests finished.")