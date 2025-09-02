import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from app.main import app
from app.openai_client import OpenAIClient
from app.settings import settings

def test_guidance_returns_structured_json(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "dummy", raising=False)
    def fake_json(system_prompt: str, user_prompt: str) -> dict:
        return {
            "tier1": "NameError occurs when a name is used before being defined.",
            "tier2": "Your code prints 'total' before it exists. Define it or print 'count'. A quick scan for where a variable is set is a reusable debugging step.",
            "tier3": {
                "fix_explanation": "Use the correct variable name that exists.",
                "patched_code": "count = 3\nprint(count)\n",
                "diff_unified": "--- a/example.py\n+++ b/example.py\n@@\n-count = 3\n-print(total)\n+count = 3\n+print(count)\n",
                "confidence": 0.95
            },
            "notes": None
        }

    monkeypatch.setattr(OpenAIClient, "get_json", staticmethod(fake_json))

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
    assert "tier1" in data and isinstance(data["tier1"], str)
    assert "tier2" in data and isinstance(data["tier2"], str)
    assert "tier3" in data and isinstance(data["tier3"], dict)
    assert 0.0 <= data["tier3"]["confidence"] <= 1.0
