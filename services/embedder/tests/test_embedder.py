import pytest
import httpx
import time
import uuid

BASE_URL = "http://127.0.0.1:8001"  # your embedder service


@pytest.fixture(scope="session")
def client():
    return httpx.Client(base_url=BASE_URL, timeout=60.0)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "cubert_src" in data
    assert "model_name" in data


def test_embed_and_filter(client):
    primary_key = str(uuid.uuid4())
    username = "testuser"
    pem_type = "SyntaxError"
    timestamp = int(time.time())

    # Step 1: Embed some text
    r = client.post("/embed", json={
        "text": "print('hello world')",
        "primary_key": primary_key,
        "username": username,
        "pem_type": pem_type,
        "timestamp": timestamp
    })
    assert r.status_code == 200
    data = r.json()
    assert data["primary_key"] == primary_key
    assert data["dim"] == 768
    assert len(data["vector"]) == 768

    time.sleep(0.5)  # wait for Milvus to be ready

    # Step 2: Filter embeddings by username
    r = client.get("/filter", params={"username": username})
    assert r.status_code == 200
    results = r.json()["embeddings"]
    assert any(e["primary_key"] == primary_key for e in results)  # <-- match new field name

    # Step 3: Filter embeddings by pem_type
    r = client.get("/filter", params={"pem_type": pem_type})
    assert r.status_code == 200
    results = r.json()["embeddings"]
    assert any(e["primary_key"] == primary_key for e in results)

    # Step 4: Filter embeddings by username + pem_type
    r = client.get("/filter", params={"username": username, "pem_type": pem_type})
    assert r.status_code == 200
    results = r.json()["embeddings"]
    assert len(results) > 0
    assert results[0]["username"] == username
    assert results[0]["pem_type"] == pem_type