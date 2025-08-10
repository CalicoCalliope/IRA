### install all dependencies at once by running
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
import json
from python_tokenizer import PythonTokenizer # Make sure this matches the function name in python_tokenizer.py

# Add path to python_tokenizer.py and cubert module
# sys.path.append("/Users/zi/Documents/UZH.ETH/IRA/dev/IRA/CuBERT")
sys.path.append(os.path.join(os.path.dirname(__file__), "CuBERT"))

# Load config from environment variables or fallback to defaults
MODEL_NAME = "claudios/cubert-20210711-Python-512"

MAX_LENGTH = int(os.getenv("MAX_LENGTH", "512"))

# Load CuBERT model
model = AutoModel.from_pretrained(MODEL_NAME)

def get_cubert_embedding(code_snippet):
    # Use the PythonTokenizer class from python_tokenizer.py
    tokenizer = PythonTokenizer()
    tokens = tokenizer.tokenize_and_abstract(code_snippet)
    tokenized_code = " ".join(token.spelling for token in tokens)
    # had to change from: tokenized_code = " ".join(tokens)
    # bc it gave the error: [Embedding Error] sequence item 0: expected str instance, AbstractToken found
    # ASK IZIA: does this make sense? does it correctly tokenize the code snippet?


    # Prepare inputs for the model (you may need to map tokens to input_ids)
    # inputs = {
    #     "input_ids": torch.tensor([[model.config.vocab_size // 2] * min(MAX_LENGTH, len(tokens))])
    #     # This is still a placeholder!
    # }
    inputs = tokenizer.tokenize_and_abstract(code_snippet)
    with torch.no_grad():
        outputs = model(**inputs)
    embedding = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()
    return embedding

# Example usage:
# code_snippet = "def foo(x): return x + 1"
# embedding = get_cubert_embedding(code_snippet)


# def store_embedding_in_qdrant(embedding, payload):
#     point_id = str(uuid.uuid4())
#     point = PointStruct(
#         id=point_id,
#         vector=embedding.tolist(),
#         payload=payload
#     )
#     client.upsert(
#         collection_name=collection_name,
#         points=[point]
#     )
#     return point_id

# Example storing
# payload = {"code": code_snippet}
# point_id = store_embedding_in_qdrant(embedding, payload)

# ...rest of the code for interacting with Qdrant or other operations

# ----------------------------
# CLI ENTRYPOINT
# ----------------------------
if __name__ == "__main__":
    input_text = sys.stdin.read()
    try:
        embedding = get_cubert_embedding(input_text)
        print(json.dumps({"embedding": embedding.tolist()}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print(json.dumps({"error": "No code snippet provided"}))
#         sys.exit(1)

#     code_snippet = sys.argv[1]

#     try:
#         embedding = get_cubert_embedding(code_snippet)
#         print(json.dumps({"embedding": embedding.tolist()}))
#     except Exception as e:
#         print(json.dumps({"error": str(e)}))
#         sys.exit(1)