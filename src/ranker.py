"""
Core ranking logic for IRA Ranker.

Implements:
- Feature extraction for each candidate (skeleton, vector, recency, project, file, packages, pyver, success)
- Adaptive linear scoring with reliability multipliers and renormalization
- Guardrails: skeleton hard filter, confidence floor -> abstain
- Duplicate suppression with a controlled repeat rule
- Diversity via Maximal Marginal Relevance (MMR)

Inputs and outputs use pydantic schemas from schemas.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
import re
from difflib import SequenceMatcher

from .schemas import (
    RankRequest, RankResponse, RankParams, QueryContext, Candidate, RankedItem
)

# -----------------------------
# Utilities
# -----------------------------

_WHITESPACE_RE = re.compile(r"\s+")
_NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_PATH_RE = re.compile(r"([A-Za-z]:\\\\[^\s]+|/(?:[^\s/]+/)+[^\s]+)")
_PLACEHOLDER_RE = re.compile(r"<[^>]{1,32}>")  # collapse <VAR>, <NUM>, <PATH> etc.


def _norm_text(s: str) -> str:
    """Normalize skeleton-like strings for robust comparison."""
    s = s.strip().lower()
    s = _PLACEHOLDER_RE.sub("<x>", s)
    s = _NUM_RE.sub("<n>", s)
    s = _PATH_RE.sub("<p>", s)
    s = _WHITESPACE_RE.sub(" ", s)
    return s


def skeleton_similarity(a: str, b: str) -> float:
    """Exact match -> 1.0, else fuzzy SequenceMatcher ratio on normalized strings."""
    a_n = _norm_text(a)
    b_n = _norm_text(b)
    if a_n == b_n:
        return 1.0
    return float(SequenceMatcher(None, a_n, b_n).ratio())


def jaccard(a: List[str] | set, b: List[str] | set) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def recency_score(now: datetime, then: datetime, half_life_days: float) -> float:
    """Exponential decay: 0.5 ** (delta_days / half_life). Never removes items."""
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    delta_days = max(0.0, (now - then).total_seconds() / 86400.0)
    return float(pow(0.5, delta_days / max(1e-6, half_life_days)))


def parse_pyver(v: str) -> Tuple[int, int]:
    m = re.match(r"^\s*(\d+)\.(\d+)", v or "")
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)))


def pyver_proximity(qv: str, cv: str) -> float:
    qM, qm = parse_pyver(qv)
    cM, cm = parse_pyver(cv)
    if qM == cM and qm == cm:
        return 1.0
    if qM == cM:
        return 0.8
    return 0.6


def file_affinity(query: QueryContext, cand: Candidate) -> float:
    """1.0 if same file hash. Extension based affinity can be added later."""
    if cand.activeFile_hash == query.activeFile_hash:
        return 1.0
    return 0.0


def project_fingerprint(query: QueryContext, cand: Candidate) -> float:
    if cand.workingDirectory_hash == query.workingDirectory_hash:
        return 1.0
    return jaccard(query.directoryTree, cand.directoryTree)


def package_overlap(query: QueryContext, cand: Candidate) -> float:
    return jaccard(query.packages, cand.packages)


def skeleton_informative(s: str) -> bool:
    """Apply hard filter only when skeleton has enough signal."""
    tokens = re.findall(r"[a-zA-Z_]+", _norm_text(s))
    return len(tokens) >= 4  # tunable minimal token count


def hours_between(now: datetime, then: datetime) -> float:
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - then).total_seconds() / 3600.0


# -----------------------------
# Scoring
# -----------------------------

BASE_WEIGHTS: Dict[str, float] = {
    "skeleton": 0.40,
    "vector":   0.35,
    "recency":  0.10,
    "project":  0.07,
    "file":     0.03,
    "packages": 0.03,
    "pyver":    0.02,
}

def depth_to_success(depth: Optional[int]) -> float:
    # depth 0 -> 0.0, 1 -> 0.5, 2 or 3 -> 1.0
    if depth is None:
        return 0.0
    return 1.0 if depth >= 2 else (0.5 if depth == 1 else 0.0)


def reliability_multipliers(features: Dict[str, float], query: QueryContext, cand: Candidate) -> Dict[str, float]:
    """Per candidate reliability scaling, then renormalize."""
    r = {k: 1.0 for k in BASE_WEIGHTS.keys()}
    s = features["skeleton"]
    if s >= 0.999:
        r["skeleton"] = 1.4
    elif s >= 0.9:
        r["skeleton"] = 1.2
    elif s >= 0.8:
        r["skeleton"] = 1.0
    elif s >= 0.6:
        r["skeleton"] = 0.7
    else:
        r["skeleton"] = 0.5

    proj = features["project"]
    if cand.workingDirectory_hash == query.workingDirectory_hash or proj >= 0.5:
        r["project"] = 1.2
    else:
        r["project"] = 0.9
    return r


def renorm(weights: Dict[str, float]) -> Dict[str, float]:
    s = sum(max(0.0, v) for v in weights.values())
    if s <= 0.0:
        n = len(weights)
        return {k: 1.0 / n for k in weights}
    return {k: max(0.0, v) / s for k, v in weights.items()}


@dataclass
class Scored:
    id: str
    features: Dict[str, float]
    score: float
    cand: Candidate


def compute_features(query: QueryContext, cand: Candidate, params: RankParams) -> Dict[str, float]:
    """Compute normalized feature vector for this candidate."""
    return {
        "skeleton": skeleton_similarity(query.pemSkeleton, cand.pemSkeleton),
        "vector": float(max(0.0, min(1.0, cand.vector_similarity))),
        "recency": recency_score(query.timestamp, cand.timestamp, params.recency_half_life_days),
        "project": project_fingerprint(query, cand),
        "file": file_affinity(query, cand),
        "packages": package_overlap(query, cand),
        "pyver": pyver_proximity(query.pythonVersion, cand.pythonVersion),
    }


def score_candidate(query: QueryContext, cand: Candidate, params: RankParams) -> Scored:
    f = compute_features(query, cand, params)

    # Hard filter: drop very low skeleton similarity if informative
    if f["skeleton"] < params.skeleton_filter_threshold and skeleton_informative(query.pemSkeleton):
        return Scored(id=cand.id, features=f, score=-1.0, cand=cand)

    # Adaptive weights
    r = reliability_multipliers(f, query, cand)
    wprime = renorm({k: BASE_WEIGHTS[k] * r.get(k, 1.0) for k in BASE_WEIGHTS})

    base = sum(wprime[k] * f[k] for k in BASE_WEIGHTS)
    success = depth_to_success(cand.resolutionDepth)
    score = base + params.success_bonus_alpha * success
    score = float(max(0.0, min(1.0, score)))  # clamp
    return Scored(id=cand.id, features=f, score=score, cand=cand)


# -----------------------------
# Duplicate suppression
# -----------------------------

def _dedup_key(cand: Candidate) -> Tuple[str, str]:
    return (_norm_text(cand.pemSkeleton), cand.activeFile_hash or "")


def dedup_scored(scored: List[Scored], query: QueryContext, params: RankParams) -> List[Scored]:
    """
    Collapse near duplicates (same skeleton and same file) within the result set,
    keeping the highest score, but allow one additional repeat if:
      - earlier instance (older timestamp) has resolutionDepth >= allow_repeat_depth
      - and is at least allow_repeat_min_hours older than the other instance
    """
    groups: Dict[Tuple[str, str], List[Scored]] = {}
    for s in scored:
        if s.score < 0:
            continue
        groups.setdefault(_dedup_key(s.cand), []).append(s)

    result: List[Scored] = []
    for key, items in groups.items():
        items.sort(key=lambda s: (s.score, s.cand.timestamp), reverse=True)
        if not items:
            continue
        primary = items[0]
        keep: List[Scored] = [primary]

        # Consider an allowed repeat from the same key
        allowed = None
        for s in items[1:]:
            age_hours = hours_between(primary.cand.timestamp, s.cand.timestamp)
            if s.cand.resolutionDepth is not None and s.cand.resolutionDepth >= params.allow_repeat_depth and age_hours >= params.allow_repeat_min_hours:
                allowed = s
                break
        if allowed is not None:
            keep.append(allowed)

        result.extend(keep)

    result.sort(key=lambda s: s.score, reverse=True)
    return result


# -----------------------------
# Diversity: MMR
# -----------------------------

def candidate_similarity(a: Scored, b: Scored) -> float:
    if a.cand.activeFile_hash and b.cand.activeFile_hash and a.cand.activeFile_hash == b.cand.activeFile_hash:
        return 1.0
    if _norm_text(a.cand.pemSkeleton) == _norm_text(b.cand.pemSkeleton):
        return 0.8
    return jaccard(a.cand.packages, b.cand.packages)


def mmr_select(scored: List[Scored], k: int, lamb: float) -> List[Scored]:
    """Greedy MMR selection."""
    if k <= 0 or not scored:
        return []
    selected: List[Scored] = []
    remaining = scored[:]
    while remaining and len(selected) < k:
        if not selected:
            selected.append(remaining.pop(0))
            continue
        best_idx = 0
        best_val = -1e9
        for i, s in enumerate(remaining):
            sim_to_selected = max(candidate_similarity(s, t) for t in selected) if selected else 0.0
            val = lamb * s.score - (1.0 - lamb) * sim_to_selected
            if val > best_val:
                best_val = val
                best_idx = i
        selected.append(remaining.pop(best_idx))
    return selected


# -----------------------------
# Public entrypoint
# -----------------------------

def rank(req: RankRequest) -> RankResponse:
    params = req.params
    query = req.query
    cands = req.candidates

    if not cands:
        return RankResponse(abstain=True, reason="no_candidates", best=None, alternates=[])

    scored = [score_candidate(query, c, params) for c in cands]
    scored = [s for s in scored if s.score >= 0.0]
    if not scored:
        return RankResponse(abstain=True, reason="all_filtered", best=None, alternates=[])

    scored = dedup_scored(scored, query, params)
    if not scored:
        return RankResponse(abstain=True, reason="all_deduped", best=None, alternates=[])

    if scored[0].score < params.confidence_floor:
        return RankResponse(abstain=True, reason="low_confidence", best=None, alternates=[])

    k = max(1, min(params.k, len(scored)))
    chosen = mmr_select(scored, k=k, lamb=params.mmr_lambda)
    chosen.sort(key=lambda s: s.score, reverse=True)

    def reasons_for(s: Scored) -> List[str]:
        r = []
        if s.features["skeleton"] >= 0.999:
            r.append("signature match")
        elif s.features["skeleton"] >= 0.8:
            r.append("signature similar")
        if s.features["file"] >= 0.999:
            r.append("same file")
        elif 0.25 <= s.features["file"] < 0.999:
            r.append("same filetype")
        if s.features["packages"] > 0.0:
            r.append("package overlap")
        days = max(0, int((query.timestamp - s.cand.timestamp).total_seconds() // 86400))
        r.append(f"recent: {days}d")
        if depth_to_success(s.cand.resolutionDepth) >= 0.5:
            r.append("success before")
        return r

    ranked_items: List[RankedItem] = [
        RankedItem(
            id=s.id,
            score=round(s.score, 6),
            features={k: round(float(v), 6) for k, v in s.features.items()},
            reasons=reasons_for(s),
        )
        for s in chosen
    ]

    best = ranked_items[0]
    alternates = ranked_items[1:] if len(ranked_items) > 1 else []

    return RankResponse(
        abstain=False,
        reason=None,
        best=best,
        alternates=alternates,
    )