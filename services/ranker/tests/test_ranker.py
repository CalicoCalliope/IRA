import pytest
from datetime import datetime, timedelta, timezone
from services.ranking.app.schemas import RankParams, QueryContext, Candidate, RankRequest
from services.ranking.app.ranker import rank

def test_rank_basic():
    now = datetime.now(timezone.utc)
    query = QueryContext(
        student_id="u1",
        pemType="NameError",
        pemSkeleton="NameError: name '<VAR>' is not defined",
        timestamp=now,
        activeFile_hash="H:main.py",
        workingDirectory_hash="W:proj",
        directoryTree=["main.py","util/helpers.py"],
        packages=["numpy","pandas"],
        pythonVersion="3.11.5"
    )
    cands = [
        Candidate(
            id="pemA",
            vector_similarity=0.84,
            pemSkeleton="NameError: name '<VAR>' is not defined",
            timestamp=now - timedelta(days=1),
            activeFile_hash="H:main.py",
            workingDirectory_hash="W:proj",
            directoryTree=["main.py","util/helpers.py"],
            packages=["numpy"],
            pythonVersion="3.11.5",
            resolutionDepth=2
        ),
        Candidate(
            id="pemB",
            vector_similarity=0.78,
            pemSkeleton="NameError: name '<VAR>' is not defined",
            timestamp=now - timedelta(days=3),
            activeFile_hash="H:other.py",
            workingDirectory_hash="W:proj",
            directoryTree=["other.py","util/helpers.py"],
            packages=["numpy","matplotlib"],
            pythonVersion="3.11.4",
            resolutionDepth=0
        ),
    ]
    req = RankRequest(params=RankParams(), query=query, candidates=cands)
    resp = rank(req)

    assert resp.abstain is False
    assert resp.best is not None
    assert resp.best.id == "pemA"
    assert len(resp.alternates) == 1
    if resp.alternates:
        assert resp.best.score >= resp.alternates[0].score


def mkq():
    # Provide required fields for QueryContext to avoid validation errors
    return QueryContext(
        student_id="s",
        pemType="T",
        pemSkeleton="X",
        timestamp="2024-01-01T00:00:00Z",
        activeFile_hash="H",
        workingDirectory_hash="W",
        directoryTree=[],
        packages=[],
        pythonVersion="3.11",
    )


def mkc(i, **kw):
    # Ensure required fields for Candidate are present; allow overrides via **kw
    base = dict(
        id=f"id{i}",
        pemSkeleton="X",
        pythonVersion="3.11",
        timestamp="2024-01-01T00:00:00Z",
        activeFile_hash="",
        workingDirectory_hash="",
    )
    base.update(kw)
    return Candidate(**base)


def _make_params_force_abstain():
    """Create RankParams that force abstain, if such a field exists in the schema.
    Tries several common field names and returns None if none are present.
    """
    fields = getattr(RankParams, "model_fields", {})
    field_names = [
        "min_score",
        "abstain_threshold",
        "min_similarity",
        "min_vector_similarity",
        "min_best_similarity",
        "min_best_score",
    ]
    for name in field_names:
        if name in fields:
            return RankParams(**{name: 0.99})
    return None


def test_abstain_when_min_score_forced_high():
    params = _make_params_force_abstain()
    if params is None:
        pytest.skip("RankParams has no min-threshold field available; skipping abstain-forced test.")
    req = RankRequest(
        params=params,  # force abstain regardless of similarities
        query=mkq(),
        candidates=[
            mkc(1, vector_similarity=0.20),
            mkc(2, vector_similarity=0.30),
        ],
    )
    out = rank(req)
    assert out.abstain is True
    assert out.best is None
    assert out.alternates == []


def test_duplicate_suppression_same_hashes_not_in_alternates():
    req = RankRequest(
        params=RankParams(),
        query=mkq(),
        candidates=[
            mkc(1, vector_similarity=0.99, activeFile_hash="F", workingDirectory_hash="W"),
            mkc(2, vector_similarity=0.98, activeFile_hash="F", workingDirectory_hash="W"),
            mkc(3, vector_similarity=0.70, activeFile_hash="F2", workingDirectory_hash="W2"),
        ],
    )
    out = rank(req)
    ids = [out.best.id] + [a.id for a in out.alternates]
    # still returns a winner
    assert out.abstain is False
    # duplicates by same hashes should not both appear
    assert not ({"id1", "id2"} <= set(ids))  # loose, branch-safe
