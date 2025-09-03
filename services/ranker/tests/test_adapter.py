import pytest
from src.adapter import rank_items, _cosine

def test_rank_items_minimal_cosine():
    current = [1.0, 0.0, 0.0]
    cands = [
        {"id": "A", "vector": [1.0, 0.0, 0.0]},  # cosine = 1.0
        {"id": "B", "vector": [0.0, 1.0, 0.0]},  # cosine = 0.0
        {"id": "C", "vector": [0.7071, 0.7071, 0.0]},  # cosine ~ 0.7071
    ]
    out = rank_items({"current_vector": current, "candidates": cands})
    assert out["ranked_ids"] == ["A", "C", "B"]
    assert out["scores"]["A"] > out["scores"]["C"] > out["scores"]["B"]

def test_rank_items_full_path_works_with_metadata():
    # Minimal metadata to trigger full scoring path
    current = [1.0, 0.0, 0.0]
    cands = [
        {"id": "pemA", "vector": [0.9, 0.1, 0.0], "pemSkeleton": "ZeroDivisionError at foo", "pythonVersion": "3.11.4"},
        {"id": "pemB", "vector": [0.8, 0.2, 0.0], "pemSkeleton": "ZeroDivisionError at foo", "pythonVersion": "3.11.4"},
    ]
    current_meta = {"skeleton": "ZeroDivisionError at foo", "pythonVersion": "3.11.4"}
    out = rank_items({"current_vector": current, "candidates": cands, "current_meta": current_meta})
    assert out["abstain"] is False
    ids = [out["best"]["id"]] + [a["id"] for a in out["alternates"]]
    assert "pemA" in ids and "pemB" in ids


def test_cosine_length_mismatch_raises():
    with pytest.raises(ValueError):
        _cosine([1,2,3], [1,2])

def test_cosine_zero_norm_returns_zero():
    assert _cosine([0,0,0], [1,2,3]) == 0.0

def test_minimal_path_rejects_bad_candidate_shape():
    with pytest.raises(ValueError):
        rank_items({"current_vector": [1,0], "candidates": [{"id": "x"}]})