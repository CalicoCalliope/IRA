import os
from pymilvus import MilvusClient, DataType, FieldSchema, CollectionSchema
from dotenv import load_dotenv
import numpy as np

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

MILVUS_URI = os.getenv("MILVUS_HOST").strip()
MILVUS_TOKEN = os.getenv("MILVUS_API").strip()
COLLECTION_NAME = "embeddings"

# -----------------------------
# Connect to Milvus Cloud
# -----------------------------
client = MilvusClient(uri=MILVUS_URI, token=MILVUS_TOKEN)

# -----------------------------
# Ensure collection exists
# -----------------------------
if COLLECTION_NAME not in client.list_collections():
    fields = [
        FieldSchema(name="PK", dtype=DataType.VARCHAR, is_primary=True, max_length=50),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="timestamp", dtype=DataType.INT64),
        FieldSchema(name="username", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="pem_type", dtype=DataType.VARCHAR, max_length=100),
    ]
    schema = CollectionSchema(fields, description="PEM embeddings collection")
    client.create_collection(name=COLLECTION_NAME, schema=schema)
    print(f"Collection '{COLLECTION_NAME}' created successfully.")

# -----------------------------
# Insert an embedding
# -----------------------------
def insert_embedding(vector, pem_id: str, username: str, pem_type: str, timestamp: int):
    vec = np.array(vector, dtype=np.float32)
    print("VECTOR DIM:", len(vector))
    print("VECTOR TYPE:", type(vector), type(vector[0]))
    print("PK TYPE:", type(pem_id))
    print("USERNAME TYPE:", type(username))
    print("PEM_TYPE TYPE:", type(pem_type))
    print("TIMESTAMP TYPE:", type(timestamp))
    client.insert(COLLECTION_NAME, [
        [pem_id],        # PK
        [list(vector)],        # embedding
        [timestamp],     # INT64
        [username],      # VARCHAR
        [pem_type]       # VARCHAR
    ])
    client.flush(COLLECTION_NAME)
    return pem_id

# -----------------------------
# Query embeddings
# -----------------------------
def filter_entries(username: str = None, pem_type: str = None, n_results: int = 100):
    filter_expr = None
    if username and pem_type:
        filter_expr = f"username == '{username}' AND pem_type == '{pem_type}'"
    elif username:
        filter_expr = f"username == '{username}'"
    elif pem_type:
        filter_expr = f"pem_type == '{pem_type}'"

    results = client.query(
        COLLECTION_NAME,
        filter=filter_expr,
        output_fields=["PK", "embedding", "timestamp", "username", "pem_type"],
        limit=n_results
    )
    return [
        {
            "id": entry.get("PK"),
            "embedding": entry.get("embedding"),
            "timestamp": entry.get("timestamp"),
            "username": entry.get("username"),
            "pem_type": entry.get("pem_type")
        }
        for entry in results
    ]