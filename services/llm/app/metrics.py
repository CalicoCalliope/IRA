from __future__ import annotations
import threading, json, datetime as dt
from pathlib import Path
from typing import Dict, Any, Optional
_lock = threading.Lock()
_totals: Dict[str, Any] = {
    "total_requests": 0, "prompt_tokens": 0, "completion_tokens": 0,
    "total_tokens": 0, "total_cost_usd": 0.0, "total_latency_ms": 0, "by_model": {},
}
_log_path: Optional[Path] = None
_file_logging_enabled: bool = True
def configure(log_path: str, enable_file_log: bool) -> None:
    global _log_path, _file_logging_enabled
    _file_logging_enabled = bool(enable_file_log)
    _log_path = Path(log_path)
    if _file_logging_enabled:
        _log_path.parent.mkdir(parents=True, exist_ok=True)
        if not _log_path.exists(): _log_path.touch()
def record_usage(model: str, prompt_tokens, completion_tokens, total_tokens,
                 latency_ms, request_id, estimated_cost_usd) -> None:
    pt = int(prompt_tokens or 0); ct = int(completion_tokens or 0)
    tt = int(total_tokens or (pt + ct)); lm = int(latency_ms or 0)
    cost = float(estimated_cost_usd or 0.0)
    now_iso = dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00","Z")
    with _lock:
        _totals["total_requests"] += 1
        _totals["prompt_tokens"] += pt; _totals["completion_tokens"] += ct
        _totals["total_tokens"] += tt; _totals["total_cost_usd"] = round(_totals["total_cost_usd"] + cost, 6)
        _totals["total_latency_ms"] += lm
        bm = _totals["by_model"].setdefault(model, {
            "requests": 0, "prompt_tokens": 0, "completion_tokens": 0,
            "total_tokens": 0, "total_cost_usd": 0.0, "total_latency_ms": 0,
        })
        bm["requests"] += 1; bm["prompt_tokens"] += pt; bm["completion_tokens"] += ct
        bm["total_tokens"] += tt; bm["total_cost_usd"] = round(bm["total_cost_usd"] + cost, 6)
        bm["total_latency_ms"] += lm
    if _file_logging_enabled and _log_path:
        rec = {"ts": now_iso, "model": model, "prompt_tokens": pt, "completion_tokens": ct,
               "total_tokens": tt, "latency_ms": lm, "estimated_cost_usd": cost, "request_id": request_id}
        try:
            with _log_path.open("a", encoding="utf-8") as f: f.write(json.dumps(rec) + "\n")
        except Exception: pass
def get_summary() -> Dict[str, Any]:
    with _lock:
        avg_latency = int(_totals["total_latency_ms"] / _totals["total_requests"]) if _totals["total_requests"] else 0
        return {"since_process_start": {
            "requests": _totals["total_requests"], "prompt_tokens": _totals["prompt_tokens"],
            "completion_tokens": _totals["completion_tokens"], "total_tokens": _totals["total_tokens"],
            "total_cost_usd": round(_totals["total_cost_usd"], 6), "avg_latency_ms": avg_latency,
            "by_model": _totals["by_model"],
        }}
def reset_summary() -> None:
    global _totals
    with _lock:
        _totals = { "total_requests": 0, "prompt_tokens": 0, "completion_tokens": 0,
                    "total_tokens": 0, "total_cost_usd": 0.0, "total_latency_ms": 0, "by_model": {} }
