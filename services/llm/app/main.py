from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings
from .schemas import GuidanceRequest, GuidanceResponse
from .prompts import SYSTEM_PROMPT, build_user_prompt
import os
from .openai_client import OpenAIClient
from . import metrics
import time

import difflib, json

app = FastAPI(title="IRA LLM Guidance Service", version="0.1.0")
# metrics config
metrics.configure(settings.metrics_log_path, settings.metrics_file_log)

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
    for k in ("output", "result", "guidance", "response", "data"):
        if isinstance(data.get(k), dict):
            data = data[k]
            break
    # Ensure a dict at this point
    if not isinstance(data, dict):
        data = {}
    return data

def _pop_first(data: dict, keys: list[str]):
    for k in keys:
        if k in data:
            return data.pop(k)
    return None

def _normalize_aliases(data: dict, req: GuidanceRequest) -> None:
    # Map likely aliases to tier1 and tier2
    tier1_aliases = ["tier1", "Tier1", "tier_1", "tier-1", "definition", "hint", "summary"]
    tier2_aliases = ["tier2", "Tier2", "tier_2", "tier-2", "explanation", "reason", "why", "how_to_fix", "fix_hint"]

    t1 = _pop_first(data, tier1_aliases) or ""
    t2 = _pop_first(data, tier2_aliases) or ""

    # Build tier3 from existing object or scattered fields
    t3 = data.get("tier3")
    if not isinstance(t3, dict):
        t3 = {}

    # Gather scattered candidates into tier3
    for k in list(data.keys()):
        lk = k.lower()
        if lk in ("fix_explanation", "patched_code", "patch", "diff_unified", "diff", "unified_diff", "confidence"):
            if lk in ("diff", "unified_diff"):
                t3.setdefault("diff_unified", data.pop(k))
            elif lk == "patch":
                t3.setdefault("fix_explanation", data.pop(k))
            else:
                t3.setdefault(k, data.pop(k))

    # Defaults and best effort diff
    t3.setdefault("fix_explanation", "")
    t3.setdefault("patched_code", None)
    t3.setdefault("diff_unified", None)
    t3.setdefault("confidence", 0.5)
    if t3.get("patched_code") and not t3.get("diff_unified"):
        try:
            t3["diff_unified"] = _make_unified_diff(req.filename, req.user_code, t3["patched_code"])
        except Exception:
            pass

    data["tier1"] = t1
    data["tier2"] = t2
    data["tier3"] = t3

# Shared secret auth (enabled when IRA_SHARED_SECRET is set)
def require_token(ira_token: str | None = Header(None, alias=settings.ira_token_header)):
    if settings.ira_shared_secret:
        if not ira_token or ira_token != settings.ira_shared_secret:
            raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@app.post("/v1/guidance", response_model=GuidanceResponse, dependencies=[Depends(require_token)])
def guidance(req: GuidanceRequest):
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="LLM not configured")

    user_prompt = build_user_prompt(req)
    client = OpenAIClient()

    # start latency timer
    start = time.perf_counter()

    try:
        raw = client.get_json(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM upstream error: {e}")

    data = _coerce_and_unwrap(raw)
    _normalize_aliases(data, req)

    # Require minimally tier1/tier2/tier3 keys now that we've normalized
    required = {"tier1", "tier2", "tier3"}
    if not required.issubset(data.keys()):
        raise HTTPException(status_code=500, detail="LLM returned malformed JSON")

    try:
        resp = GuidanceResponse.model_validate(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Response validation failed: {e}")

    # record latency-only usage (token counts are added later in the client)
    try:
        latency_ms = int((time.perf_counter() - start) * 1000)
        metrics.record_usage(settings.openai_model, None, None, None, latency_ms, None, None)
    except Exception:
        pass

    return resp
@app.get("/metrics/usage")
def metrics_usage():
    return metrics.get_summary()
@app.post("/metrics/reset")
def metrics_reset():
    metrics.reset_summary()
    return {"status": "ok"}
