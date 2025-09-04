"""
This module moved to the embedder service.

Prefer using the HTTP API via the coordinator:
  POST /embed  (coordinator forwards to the embedder service)

If you truly need the direct function for local scripts/tests:
  from services.embedder.src.cubert_pipeline import get_cubert_embedding
"""
raise RuntimeError(
    "cubert_pipeline moved under services/embedder. "
    "Call the service (/embed) via the coordinator, "
    "or import from services.embedder.src.cubert_pipeline for local-only use."
)
