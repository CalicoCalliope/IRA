from transformers import AutoTokenizer, AutoModel
import torch
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import uuid

# 1. Load Claudio's CuBERT model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("claudios/cubert-20210711-Python-512")
model = AutoModel.from_pretrained("claudios/cubert-20210711-Python-512")

def get_cubert_embedding(code_snippet):
    inputs = tokenizer(code_snippet, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    # Take the [CLS] token embedding (first token)
    embedding = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()
    return embedding

# 2. Example: User's code and metadata
entry = {
    "timestamp": "2025-07-13T21:38:34.238Z",
    "pem": "[RUNTIME ERROR] Traceback (most recent call last):\r\n  File \"c:\\Users\\yaren\\OneDrive\\Masaüstü\\uzh\\master's project\\test.py\", line 3, in <module>\r\n    c = 1/0\r\n        ~^~\r\nZeroDivisionError: division by zero\r\n",
    "username": "yaren",
    "activeFile": "c:\\Users\\yaren\\OneDrive\\Masaüstü\\uzh\\master's project\\test.py",
    "workingDirectory": "c:\\Users\\yaren\\OneDrive\\Masaüstü\\uzh\\master's project",
    "directoryTree": [
      "test.py",
      "README.txt",
      ".pem-log.txt",
      "IRA/IRA/webpack.config.js"
    ],
    "pythonVersion": "Python 3.13.2",
    "packages": []
}

# Extract the relevant code snippet for embedding
code_snippet = "c = 1/0"  # Replace with user's actual code if available

# 3. Get CuBERT embedding
embedding = get_cubert_embedding(code_snippet)

# 4. Connect to Qdrant and create collection if needed
client = QdrantClient("localhost", port=6333)

collection_name = "ira-pem-logs"
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=len(embedding), distance=Distance.COSINE),
)

# 5. Upload the PEM log with embedding
point = PointStruct(
    id=str(uuid.uuid4()),
    vector=embedding.tolist(),
    payload=entry
)

client.upsert(collection_name=collection_name, points=[point])

print("PEM log entry uploaded to Qdrant :)")