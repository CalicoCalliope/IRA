import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure repo root is importable so we can import `ira.*`
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI
from pydantic import BaseModel, Field

# Import your existing pipeline (has its own google-research path shim)
import ira.cubert_pipeline as pipe  # type: ignore

app = FastAPI(title="Embedder Service", version="0.1.0")

class EmbedRequest(BaseModel):
    text: str = Field(..., description="Source text to embed")

class EmbedResponse(BaseModel):
    vector: List[float]
    dim: int

class HealthResponse(BaseModel):
    cubert_src: str
    cubert_src_exists: bool
    spm_path: str
    spm_exists: bool
    use_hf_only: bool
    model_name: str

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    # Build a simple health payload without loading heavy models
    cubert_src = str(pipe.CUBERT_SRC)
    spm_path = str(pipe.SPM_PATH)
    return HealthResponse(
        cubert_src=cubert_src,
        cubert_src_exists=pipe.CUBERT_SRC.exists(),
        spm_path=spm_path,
        spm_exists=pipe.SPM_PATH.exists(),
        use_hf_only=bool(pipe.USE_HF_ONLY),
        model_name=str(pipe.MODEL_NAME),
    )

@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    vec = pipe.get_cubert_embedding(req.text)
    # vec is a numpy array per your pipeline; convert to list for JSON
    lst = [float(x) for x in vec.tolist()]
    return EmbedResponse(vector=lst, dim=len(lst))

# Dev entrypoint: uvicorn app:app
if __name__ == "__main__":
    import uvicorn
    # Ensure google-research is on PYTHONPATH for safety if run directly
    gr = REPO_ROOT / "google-research"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{env.get('PYTHONPATH','')}:{gr}"
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=False)
