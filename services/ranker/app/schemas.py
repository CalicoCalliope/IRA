"""
Pydantic schemas for the IRA Ranker Service.

These models define the request and response contract between the Coordinator
and the Ranker. They target Pydantic v2.

Core ideas:
- Ranker is stateless. The Coordinator prepares the candidate pool (same pemType)
  and a cosine similarity feature named vector_similarity.
- Ranker computes features, scores candidates, applies guardrails and diversity,
  then returns Top K with human friendly reasons. UI shows 1 by default.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator


# -------------------------
# Request models
# -------------------------

class RankParams(BaseModel):
    """Controls for selection and diversity. All are tunable per request."""
    model_config = ConfigDict(extra="forbid")

    k: int = Field(3, ge=1, le=10, description="How many items to select. Service computes up to K.")
    mmr_lambda: float = Field(0.7, ge=0.0, le=1.0, description="MMR tradeoff between score and novelty.")
    confidence_floor: float = Field(0.5, ge=0.0, le=1.0, description="Abstain if best score is below this.")
    recency_half_life_days: float = Field(14.0, gt=0.0, description="Half-life for recency decay.")
    skeleton_filter_threshold: float = Field(0.6, ge=0.0, le=1.0, description="Drop when skeleton similarity is very low and informative.")
    allow_repeat_depth: int = Field(3, ge=0, le=3, description="Min resolutionDepth to allow a repeat from same file and skeleton.")
    allow_repeat_min_hours: float = Field(24.0, ge=0.0, description="Min hours since prior occurrence to allow a repeat.")
    success_bonus_alpha: float = Field(0.03, ge=0.0, le=0.2, description="Cap for success bonus contribution.")


class QueryContext(BaseModel):
    """Context about the current PEM."""
    model_config = ConfigDict(extra="forbid")

    student_id: str
    pemType: str
    pemSkeleton: str
    timestamp: datetime
    activeFile_hash: str
    workingDirectory_hash: str
    directoryTree: List[str] = Field(default_factory=list)
    packages: List[str] = Field(default_factory=list)
    pythonVersion: str
    resolutionDepth: Optional[int] = Field(default=None, ge=0, le=3)
    # Optional helper fields that the ranker will ignore but allow:
    current_pem_point_id: Optional[str] = None
    code_slice: Optional[str] = Field(default=None, description="Masked local code window; not required by the ranker.")

    @field_validator("packages", mode="before")
    @classmethod
    def _normalize_packages(cls, v):
        # Lowercase, drop versions like "numpy==1.26.4" -> "numpy"
        if v is None:
            return []
        norm = []
        for x in v:
            x = (x or "").strip().lower()
            if not x:
                continue
            x = x.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0]
            norm.append(x)
        # unique while preserving order
        seen = set()
        out = []
        for p in norm:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out


class Candidate(BaseModel):
    """One past PEM candidate prepared by the Coordinator."""
    model_config = ConfigDict(extra="forbid")

    id: str
    vector_similarity: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity of local code slices.")
    pemSkeleton: str
    timestamp: datetime
    activeFile_hash: str
    workingDirectory_hash: str
    directoryTree: List[str] = Field(default_factory=list)
    packages: List[str] = Field(default_factory=list)
    pythonVersion: str
    resolutionDepth: Optional[int] = Field(default=None, ge=0, le=3)

    # Optional: if Coordinator knows the extension for affinity
    activeFile_ext: Optional[str] = Field(default=None, description="File extension like .py if available.")

    @field_validator("packages", mode="before")
    @classmethod
    def _normalize_packages(cls, v):
        return QueryContext._normalize_packages(v)


class RankRequest(BaseModel):
    """Top-level request payload to /rank."""
    model_config = ConfigDict(extra="forbid")

    params: RankParams
    query: QueryContext
    candidates: List[Candidate]


# -------------------------
# Response models
# -------------------------

class RankedItem(BaseModel):
    """A re-ranked result with transparent feature breakdown."""
    model_config = ConfigDict(extra="forbid")

    id: str
    score: float = Field(..., ge=0.0, le=1.0)
    features: Dict[Literal["skeleton","vector","recency","project","file","packages","pyver"], float]
    reasons: List[str] = Field(default_factory=list)


class RankResponse(BaseModel):
    """Ranker response. If abstain is true, best and alternates may be empty."""
    model_config = ConfigDict(extra="forbid")

    abstain: bool = False
    reason: Optional[str] = Field(default=None, description="Why we abstained or filtered.")
    best: Optional[RankedItem] = None
    alternates: List[RankedItem] = Field(default_factory=list)