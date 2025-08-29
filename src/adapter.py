from __future__ import annotations
from typing import Any, Dict, List, Tuple
import math
from datetime import datetime, timezone

def _cosine(a: List[float], b: List[float]) -> float:
    dot = 0.0
    na = 0.0
    nb = 0.0
    if len(a) != len(b):
        raise ValueError(f"vector length mismatch: {len(a)} vs {len(b)}")
    for ai, bi in zip(a, b):
        ai = float(ai); bi = float(bi)
        dot += ai * bi
        na += ai * ai
        nb += bi * bi
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)

def rank_items(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Final importable function for teammates.

    Minimal input:
      {
        "current_vector": [float, ...],
        "candidates": [{"id": "pem123", "vector": [float, ...]}, ...]
      }

    Optional for full scoring (if provided, uses full ranker):
      - "current_meta": {...}
      - "params": {...}
      - candidates may carry extra metadata fields, too
    """
    curr = input_data.get("current_vector")
    cands = input_data.get("candidates", [])
    if not isinstance(curr, list) or not cands:
        raise ValueError("rank_items requires 'current_vector' (list[float]) and non-empty 'candidates'.")

    current_meta = input_data.get("current_meta") or {}
    params = input_data.get("params")
    meta_flag = bool(current_meta or params) or any(set(c.keys()) - {"id", "vector"} for c in cands)

    # ---- Minimal cosine-only path
    if not meta_flag:
        scores: List[Tuple[str, float]] = []
        for c in cands:
            cid = c.get("id")
            vec = c.get("vector")
            if cid is None or not isinstance(vec, list):
                raise ValueError("Each candidate needs 'id' (str) and 'vector' (list[float]).")
            scores.append((cid, _cosine(curr, vec)))
        scores.sort(key=lambda x: x[1], reverse=True)
        return {"ranked_ids": [cid for cid, _ in scores],
                "scores": {cid: float(s) for cid, s in scores}}

    # ---- Full path (Pydantic models + our ranker)
    from src.schemas import RankParams, QueryContext, Candidate, RankRequest
    from src.ranker import rank as rank_impl

    # Build QueryContext: only include supported fields, fill safe defaults.
    q_fields = getattr(QueryContext, "model_fields", {})
    qdata: Dict[str, Any] = {}
    meta_map = {
        "student_id": current_meta.get("student_id") or "unknown",
        "pemType": current_meta.get("pemType") or "unknown",
        "pemSkeleton": current_meta.get("skeleton") or current_meta.get("pemSkeleton") or "",
        "timestamp": current_meta.get("timestamp") or datetime.now(timezone.utc),
        "activeFile_hash": current_meta.get("activeFile_hash") or "",
        "workingDirectory_hash": current_meta.get("workingDirectory_hash") or "",
        "directoryTree": current_meta.get("directoryTree") or [],
        "packages": current_meta.get("packages") or [],
        "pythonVersion": current_meta.get("pythonVersion") or "",
        "resolutionDepth": current_meta.get("resolutionDepth"),
        "code_slice": current_meta.get("code_slice"),
    }
    for k, v in meta_map.items():
        if k in q_fields and v is not None:
            qdata[k] = v
    if "current_vector" in q_fields:
        qdata["current_vector"] = curr
    qctx = QueryContext(**qdata)

    # Build Candidate models: add required fields with defaults if missing.
    c_fields = getattr(Candidate, "model_fields", {})
    cand_models: List[Candidate] = []
    for c in cands:
        payload: Dict[str, Any] = {}
        payload["id"] = c["id"]

        if "vector" in c_fields and "vector" in c:
            payload["vector"] = c["vector"]

        if "vector_similarity" in c_fields:
            v = c.get("vector")
            try:
                vs = _cosine(curr, v) if isinstance(v, list) and isinstance(curr, list) and len(v) == len(curr) else 0.0
            except ValueError:
                vs = 0.0
            payload["vector_similarity"] = vs

        if "timestamp" in c_fields:
            payload["timestamp"] = c.get("timestamp") or datetime.now(timezone.utc)
        if "activeFile_hash" in c_fields:
            payload["activeFile_hash"] = c.get("activeFile_hash") or ""
        if "workingDirectory_hash" in c_fields:
            payload["workingDirectory_hash"] = c.get("workingDirectory_hash") or ""

        for opt in ("pemType","pemSkeleton","directoryTree","packages","pythonVersion","resolutionDepth"):
            if opt in c_fields and c.get(opt) is not None:
                payload[opt] = c[opt]

        cand_models.append(Candidate(**payload))

    # Ask the ranker for alternates if the schema supports it.
    rp_fields = getattr(RankParams, "model_fields", {})
    desired_alts = max(0, len(cand_models) - 1)
    rp_kwargs: Dict[str, Any] = dict(params) if isinstance(params, dict) else {}

    for key in ("max_alternates", "alternates_k", "num_alternates", "n_alternates", "return_top_k", "top_k"):
        if key in rp_fields and key not in rp_kwargs:
            # For top_k-style fields, include best+alts; for alternates fields, just alts count.
            rp_kwargs[key] = desired_alts + (1 if "top_k" in key or "return_top_k" in key else 0)

    if "return_alternates" in rp_fields and "return_alternates" not in rp_kwargs:
        rp_kwargs["return_alternates"] = True

    rank_params = RankParams(**rp_kwargs)
    req = RankRequest(params=rank_params, query=qctx, candidates=cand_models)
    resp = rank_impl(req)

    # Pydantic v2 prefers model_dump()
    out = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()

    # Safety fallback: if alternates came back empty but we had more than one candidate,
    # add the next-best by cosine so tests (and teammates) get a stable list.
    if isinstance(out, Dict) and out.get("best") and not out.get("alternates"):
        best_id = out["best"].get("id")
        scored = sorted(
            [(c["id"], _cosine(curr, c.get("vector") or [])) for c in cands],
            key=lambda x: x[1],
            reverse=True,
        )
        alternates = [{"id": cid} for cid, _ in scored if cid != best_id]
        out["alternates"] = alternates

    return out