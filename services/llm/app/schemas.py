from pydantic import BaseModel, Field
from typing import Optional

class GuidanceRequest(BaseModel):
    error_type: str = Field(..., min_length=1)
    pem_text: str = Field(..., min_length=1)
    filename: Optional[str] = None
    user_code: str = Field(..., min_length=1)
    cursor_line: Optional[int] = Field(default=None, ge=1)
    prior_attempts: Optional[str] = None
    constraints: Optional[str] = None

class Tier3(BaseModel):
    fix_explanation: Optional[str] = Field(
        default="", 
        description="Concise, stepwise fix explanation (may be empty if model omitted)"
    )
    patched_code: Optional[str] = None
    diff_unified: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)

class GuidanceResponse(BaseModel):
    tier1: str = Field(..., min_length=1)
    tier2: str = Field(..., min_length=1)
    tier3: Tier3
    notes: Optional[str] = None
