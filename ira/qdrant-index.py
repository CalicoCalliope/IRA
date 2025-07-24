import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_KEY = os.getenv("QDRANT_KEY")

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_KEY,
)

# client.recreate_collection(
#     collection_name="pems_embeddings",
#     vectors_config=VectorParams(size=512, distance=Distance.COSINE)
# )

collection_info = client.get_collection("pems_embeddings")
print(collection_info)