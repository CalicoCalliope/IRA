from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}

def test_rank_endpoint():
    payload = {
        "params": {
            "k": 3,
            "mmr_lambda": 0.7,
            "confidence_floor": 0.5,
            "recency_half_life_days": 14.0,
            "skeleton_filter_threshold": 0.6,
            "allow_repeat_depth": 3,
            "allow_repeat_min_hours": 24.0,
            "success_bonus_alpha": 0.03
        },
        "query": {
            "student_id": "u1",
            "pemType": "NameError",
            "pemSkeleton": "NameError: name '<VAR>' is not defined",
            "timestamp": "2025-08-23T10:00:00Z",
            "activeFile_hash": "H:main.py",
            "workingDirectory_hash": "W:proj",
            "directoryTree": ["main.py","util/helpers.py"],
            "packages": ["numpy","pandas"],
            "pythonVersion": "3.11.5"
        },
        "candidates": [
            {
                "id": "pemA",
                "vector_similarity": 0.84,
                "pemSkeleton": "NameError: name '<VAR>' is not defined",
                "timestamp": "2025-08-22T10:00:00Z",
                "activeFile_hash": "H:main.py",
                "workingDirectory_hash": "W:proj",
                "directoryTree": ["main.py","util/helpers.py"],
                "packages": ["numpy"],
                "pythonVersion": "3.11.5",
                "resolutionDepth": 2
            },
            {
                "id": "pemB",
                "vector_similarity": 0.78,
                "pemSkeleton": "NameError: name '<VAR>' is not defined",
                "timestamp": "2025-08-20T10:00:00Z",
                "activeFile_hash": "H:other.py",
                "workingDirectory_hash": "W:proj",
                "directoryTree": ["other.py","util/helpers.py"],
                "packages": ["numpy","matplotlib"],
                "pythonVersion": "3.11.4",
                "resolutionDepth": 0
            }
        ]
    }
    r = client.post("/rank", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["abstain"] is False
    assert body["best"]["id"] == "pemA"
    assert len(body["alternates"]) == 1