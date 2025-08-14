# requirements:
# python-dotenv, transformers, torch, qdrant-client, sentencepiece

import os
import sys
import uuid
from pathlib import Path

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

# Path to google-research/cubert folder that contains python_tokenizer.py
CUBERT_SRC = os.getenv("CUBERT_SRC", "./google-research/cubert")
if not Path(CUBERT_SRC).exists():
    raise FileNotFoundError(f"CUBERT_SRC not found at {CUBERT_SRC}. Set env CUBERT_SRC to the cubert folder.")

sys.path.append(str(Path(CUBERT_SRC).resolve()))
from python_tokenizer import PythonTokenizer  # provided by google-research

MODEL_NAME = os.getenv("MODEL_NAME", "claudios/cubert-20210711-Python-512")
SPM_PATH   = os.getenv("CUBERT_SPM", "./cubert_python_tokenizer.spm")  # SentencePiece model file

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ira-pem-logs")
MAX_LENGTH = int(os.getenv("MAX_LENGTH", "512"))

# ----------------------------
# Load model and SPM
# ----------------------------
model = AutoModel.from_pretrained(MODEL_NAME)
model.eval()

sp = spm.SentencePieceProcessor()
if not Path(SPM_PATH).exists():
    raise FileNotFoundError(f"SentencePiece model not found at {SPM_PATH}. Set env CUBERT_SPM.")
sp.load(SPM_PATH)

# ----------------------------
# Tokenization pipeline
# ----------------------------
_tok = PythonTokenizer()

def tokenize_code(code: str):
    # google-research tokenizer returns token objects; we take .text
    tokens = [t.text for t in _tok.tokenize(code)]
    return tokens

def tokens_to_ids(tokens):
    # Join tokens with spaces then SPM-encode to ids
    # If your SPM requires BOS/EOS, you can add them by:
    # ids = [sp.bos_id()] + sp.encode(" ".join(tokens), out_type=int) + [sp.eos_id()]
    ids = sp.encode(" ".join(tokens), out_type=int)
    return ids

def pad_truncate(ids, max_len):
    # Truncate
    ids = ids[:max_len]
    # Pad with SPM pad id if available, else 0
    pad_id = sp.pad_id() if sp.pad_id() >= 0 else 0
    attention = [1] * len(ids)
    if len(ids) < max_len:
        ids = ids + [pad_id] * (max_len - len(ids))
        attention = attention + [0] * (max_len - len(attention))
    return ids, attention

@torch.inference_mode()
def get_cubert_embedding(code_snippet: str) -> np.ndarray:
    tokens = tokenize_code(code_snippet)
    ids = tokens_to_ids(tokens)
    ids, attn = pad_truncate(ids, MAX_LENGTH)

    input_ids = torch.tensor([ids], dtype=torch.long)
    attention_mask = torch.tensor([attn], dtype=torch.long)

    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
    # CLS embedding at position 0
    cls = outputs.last_hidden_state[:, 0, :].squeeze(0).cpu().numpy().astype(np.float32)
    return cls

# ----------------------------
# Qdrant utilities
# ----------------------------
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

def ensure_collection(name: str, dim: int):
    # Create or recreate as needed; switch to get+create if you prefer non-destructive behavior
    try:
        client.get_collection(name)
        # Optionally validate dim; recreate if mismatch
    except Exception:
        client.recreate_collection(
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
# Example
# ----------------------------
if __name__ == "__main__":
    code_snippet = "c = 1/0"
    emb = get_cubert_embedding(code_snippet)
    ensure_collection(COLLECTION_NAME, dim=emb.shape[-1])

    payload = {
        "timestamp": "2025-07-13T21:38:34.238Z",
        "pem": "[RUNTIME ERROR] ... ZeroDivisionError: division by zero",
        "username": "yaren",
        "activeFile": "test.py",
        "pythonVersion": "Python 3.13.2",
    }
    point_id = store_embedding_in_qdrant(emb, payload)
    print("Stored point:", point_id)### install all dependencies at once by running
### pip install -r CuBERT/requirements.txt

from dotenv import load_dotenv
load_dotenv()
import os
import torch
from transformers import AutoModel
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import uuid
import sys

# Add path to python_tokenizer.py and cubert module
# sys.path.append("/Users/zi/Documents/UZH.ETH/IRA/dev/IRA/CuBERT")
sys.path.append(os.path.join(os.path.dirname(__file__), "CuBERT"))

# from cubert import cubert_tokenizer
from python_tokenizer import PythonTokenizer # Make sure this matches the function name in python_tokenizer.py

# Load config from environment variables or fallback to defaults
MODEL_NAME = "claudios/cubert-20210711-Python-512"

# Qdrant settings
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ira-pem-logs")
MAX_LENGTH = int(os.getenv("MAX_LENGTH", "512"))

# Load CuBERT model
model = AutoModel.from_pretrained(MODEL_NAME)

def get_cubert_embedding(code_snippet):
    # Use the PythonTokenizer class from python_tokenizer.py
    tokenizer = PythonTokenizer()
    tokens = tokenizer.tokenize_and_abstract(code_snippet)
    tokenized_code = " ".join(tokens)
    # Prepare inputs for the model (you may need to map tokens to input_ids)
    inputs = {
        "input_ids": torch.tensor([[model.config.vocab_size // 2] * min(MAX_LENGTH, len(tokens))])
        # This is still a placeholder!
    }
    with torch.no_grad():
        outputs = model(**inputs)
    embedding = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()
    return embedding

# Example usage:
# code_snippet = "def foo(x): return x + 1"
# embedding = get_cubert_embedding(code_snippet)

client = QdrantClient(QDRANT_HOST, port=QDRANT_PORT)
collection_name = COLLECTION_NAME

def store_embedding_in_qdrant(embedding, payload):
    point_id = str(uuid.uuid4())
    point = PointStruct(
        id=point_id,
        vector=embedding.tolist(),
        payload=payload
    )
    client.upsert(
        collection_name=collection_name,
        points=[point]
    )
    return point_id

# Example storing
# payload = {"code": code_snippet}
# point_id = store_embedding_in_qdrant(embedding, payload)

# ...rest of the code for interacting with Qdrant or other operations