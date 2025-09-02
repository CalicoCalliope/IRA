import os, sys, pytest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from app.main import app

skip_no_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
)

@skip_no_key
def test_guidance_live_calls_openai():
    c = TestClient(app)
    payload = {
        "error_type": "NameError",
        "pem_text": "NameError: name 'total' is not defined",
        "filename": "example.py",
        "user_code": "count = 3\nprint(total)\n"
    }
    r = c.post("/v1/guidance", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data["tier1"], str) and len(data["tier1"]) > 0
    assert isinstance(data["tier2"], str) and len(data["tier2"]) > 0
    assert isinstance(data["tier3"], dict)
    assert 0.0 <= data["tier3"]["confidence"] <= 1.0
