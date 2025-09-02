from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings
from .schemas import GuidanceRequest, GuidanceResponse
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .openai_client import OpenAIClient
import difflib, json

app = FastAPI(title="IRA LLM Guidance Service", version="0.1.0")

# CORS (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allow_origins.split(",") if o.strip()],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

def _make_unified_diff(filename: str | None, original: str, patched: str) -> str:
    a_name = f"a/{filename or 'user.py'}"
    b_name = f"b/{filename or 'user.py'}"
    a_lines = original.splitlines(keepends=True)
    b_lines = patched.splitlines(keepends=True)
    return "".join(difflib.unified_diff(a_lines, b_lines, fromfile=a_name, tofile=b_name))

def _coerce_and_unwrap(data) -> dict:
    # If it's a JSON string, parse it
    if not isinstance(data, dict):
        try:
            data = json.loads(str(data))
        except Exception:
            data = {}
    # Unwrap common wrappers
    for k in ("output", "result", "guidance", "response"):
        if isinstance(data.get(k), dict):
            data = data[k]
            break
    # Ensure a dict at this point
    if not isinstance(data, dict):
        data = {}
    return data

def _normalize_tier3(data: dict, req: GuidanceRequest) -> None:
    t3 = data.setdefault("tier3", {})
    if not isinstance(t3, dict):
        t3 = {}
        data["tier3"] = t3
    t3.setdefault("fix_explanation", "")
    t3.setdefault("patched_code", None)
    t3.setdefault("diff_unified", None)
    # Auto-generate diff if possible
    if t3.get("patched_code") and not t3.get("diff_unified"):
        try:
            t3["diff_unified"] = _make_unified_diff(req.filename, req.user_code, t3["patched_code"])
        except Exception:
            pass

@app.post("/v1/guidance", response_model=GuidanceResponse)
def guidance(req: GuidanceRequest):
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="LLM not configured")

    user_prompt = build_user_prompt(req)
    client = OpenAIClient()

    try:
        raw = client.get_json(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM upstream error: {e}")

    data = _coerce_and_unwrap(raw)
    _normalize_tier3(data, req)

    # Require minimally tier1/tier2/tier3 keys now that we've normalized
    required = {"tier1", "tier2", "tier3"}
    if not required.issubset(data.keys()):
        raise HTTPException(status_code=500, detail="LLM returned malformed JSON")

    try:
        return GuidanceResponse.model_validate(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Response validation failed: {e}")
