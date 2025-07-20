# install all dependencies at once by running
# pip install -r CuBERT/requirements.txt

from dotenv import load_dotenv
load_dotenv()
import os
# from transformers import AutoTokenizer, AutoModel
from transformers import AutoModel
import torch

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import uuid



import sys
sys.path.append("/Users/zi/Documents/UZH.ETH/IRA/dev/IRA/CuBERT")  # Add path to python_tokenizer.py
from python_tokenizer import tokenize_python  # Adjust import based on actual function/class name


# Load config from environment variables or fallback to defaults
# MODEL_NAME = os.getenv("MODEL_NAME", "claudios/cubert-20210711-Python-512")
# TOKENIZER_NAME = os.getenv("TOKENIZER_NAME", "google/cubert-base")

# MODEL_NAME = os.getenv("MODEL_NAME", "google/cubert-base")
# TOKENIZER_NAME = os.getenv("TOKENIZER_NAME", "google/cubert-base")

# MODEL_NAME = os.getenv("MODEL_NAME", "claudios/cubert-20210711-Python-512")
# TOKENIZER_NAME = os.getenv("TOKENIZER_NAME", "google/cubert-base")

# MODEL_NAME = "claudios/cubert-20210711-Python-512"
# TOKENIZER_NAME = "google/cubert-base"

MODEL_NAME = "claudios/cubert-20210711-Python-512"

model = AutoModel.from_pretrained(MODEL_NAME)
# TOKENIZER_NAME = "claudios/cubert-20210711-Python-512"
# TOKENIZER_NAME = "google-research/cubert/python_tokenizer.py"

# Qdrant settings
# Qdrant settings
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ira-pem-logs")
MAX_LENGTH = int(os.getenv("MAX_LENGTH", "512"))


# 1. Load CuBERT model and tokenizer
# tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)
# model = AutoModel.from_pretrained(MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)

# def get_cubert_embedding(code_snippet):
#     inputs = tokenizer(code_snippet, return_tensors="pt", truncation=True, max_length=MAX_LENGTH)
#     with torch.no_grad():
#         outputs = model(**inputs)
#     embedding = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()
#     return embedding

def get_cubert_embedding(code_snippet):
    tokens = tokenize_python(code_snippet)  # Use the custom tokenizer
    # Convert tokens to string or IDs as needed for the model
    # You may need to join tokens or map to vocab IDs
    inputs = ... # Prepare inputs for the model (this part depends on model requirements)
    with torch.no_grad():
        outputs = model(**inputs)
    embedding = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()
    return embedding

# ...existing code...
client = QdrantClient(QDRANT_HOST, port=QDRANT_PORT)
collection_name = COLLECTION_NAME
# ...existing code...