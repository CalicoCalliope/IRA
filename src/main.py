"""
FastAPI wiring for the IRA Ranker service.

Endpoints
- GET /health -> quick liveness
- POST /rank -> accepts RankRequest, returns RankResponse

This module keeps no global state. All tuning happens in the request payload.
"""

from __future__ import annotations

import time
from fastapi import FastAPI, Response
from src.schemas import RankRequest, RankResponse
from src.ranker import rank as rank_impl

app = FastAPI(title="IRA Ranker", version="0.1.0")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/rank", response_model=RankResponse)
def rank_endpoint(req: RankRequest, response: Response) -> RankResponse:
    t0 = time.perf_counter()
    out = rank_impl(req)
    dt_ms = int((time.perf_counter() - t0) * 1000)
    # Add a simple timing header for observability
    response.headers["X-Ranker-Latency-ms"] = str(dt_ms)
    return out