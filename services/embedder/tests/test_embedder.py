import pytest
import httpx
import time

BASE_URL = "http://127.0.0.1:8001"  # your embedder service


@pytest.fixture(scope="session")
def client():
    return httpx.Client(base_url=BASE_URL)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "cubert_src" in data
    assert "model_name" in data


def test_embed_and_filter(client):
    pem_id = "test-123"
    username = "testuser"
    pem_type = "SyntaxError"
    timestamp = int(time.time())

    # Step 1: Embed some text
    r = client.post("/embed", json={
        "text": "print('hello world')",
        "id": pem_id,
        "username": username,
        "pemType": pem_type,
        "timestamp": timestamp
    })
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == pem_id
    assert data["dim"] == 512
    assert len(data["vector"]) == 512

    # Step 2: Filter embeddings by username
    r = client.get("/filter", params={"username": username})
    assert r.status_code == 200
    results = r.json()["embeddings"]
    assert any(e["id"] == pem_id for e in results)

    # Step 3: Filter embeddings by pemType
    r = client.get("/filter", params={"pemType": pem_type})
    assert r.status_code == 200
    results = r.json()["embeddings"]
    assert any(e["id"] == pem_id for e in results)

    # Step 4: Filter embeddings by username + pemType
    r = client.get("/filter", params={"username": username, "pemType": pem_type})
    assert r.status_code == 200
    results = r.json()["embeddings"]
    assert len(results) > 0
    assert results[0]["username"] == username
    assert results[0]["pem_type"] == pem_type