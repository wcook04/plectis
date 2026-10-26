"""Contracts for the generated premise ranker and its actual consumer."""
from __future__ import annotations

import importlib.util
import os
import random
import shutil
from pathlib import Path

import pytest

from microcosm_core.organs.formal_math_premise_retrieval import _score_query
from plectis.components import premise_ranking


ADAPTER = Path(__file__).resolve().parents[1] / "src/plectis/components/premise_ranking/_adapter.py"
spec = importlib.util.spec_from_file_location("premise_ranking_test_adapter", ADAPTER)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def test_normalized_rankings_match_independent_lexicographic_reference():
    rng = random.Random(14171)
    for width in range(6):
        query = [rng.randrange(7) for _ in range(width)]
        candidates = [
            {"eligible": bool(rng.randrange(2)), "id_rank": rng.randrange(4),
             "counts": [rng.randrange(7) for _ in range(width)],
             "bonus": bool(rng.randrange(2))}
            for _ in range(18)
        ]
        expected = [
            [index, sum(min(q, p) for q, p in zip(query, row["counts"])) + int(row["bonus"])]
            for index, row in enumerate(candidates) if row["eligible"]
        ]
        expected.sort(key=lambda entry: (-entry[1], candidates[entry[0]]["id_rank"], entry[0]))
        assert premise_ranking.rank({"query_counts": query, "candidates": candidates}) == expected


def test_empty_ineligible_and_arbitrary_precision_counts():
    assert premise_ranking.rank({"query_counts": [], "candidates": []}) == []
    assert premise_ranking.rank({"query_counts": [], "candidates": [
        {"eligible": False, "id_rank": 0, "counts": [], "bonus": True},
    ]}) == []
    huge = 10 ** 100
    candidates = [
        {"eligible": True, "id_rank": huge, "counts": [huge], "bonus": True},
        {"eligible": True, "id_rank": huge, "counts": [huge], "bonus": True},
        {"eligible": True, "id_rank": 0, "counts": [huge], "bonus": False},
    ]
    assert premise_ranking.rank({"query_counts": [huge], "candidates": candidates}) == [
        [0, huge + 1], [1, huge + 1], [2, huge],
    ]


def test_score_query_uses_generated_core_and_preserves_stable_order(monkeypatch):
    seen = []
    original = premise_ranking.rank

    def observe(payload):
        seen.append(payload)
        return original(payload)

    monkeypatch.setattr(premise_ranking, "rank", observe)
    query = {"query_terms": ["needle"], "split": "train", "strategy_id": "s"}
    premises = [
        {"premise_id": "b", "allowed_for_split": ["train"], "statement_excerpt": "needle needle", "strategy_tags": []},
        {"premise_id": "a", "allowed_for_split": ["train"], "statement_excerpt": "needle", "strategy_tags": []},
        {"premise_id": "a", "allowed_for_split": ["train"], "statement_excerpt": "needle", "strategy_tags": [], "source_ref": "second"},
        {"premise_id": "hidden", "allowed_for_split": ["test"], "statement_excerpt": "needle needle needle", "strategy_tags": ["s"]},
    ]
    result = _score_query(query, premises)
    assert len(seen) == 1
    assert list(result[0])[:2] == ["premise_id", "score"]
    assert [(row["premise_id"], row["score"], row["source_ref"]) for row in result] == [
        ("a", 1, None), ("a", 1, "second"), ("b", 1, None)
    ]
    assert seen[0]["candidates"][-1]["eligible"] is False


def test_bonus_and_empty_query():
    result = _score_query({"query_terms": [], "strategy_id": "s"}, [
        {"premise_id": "z", "allowed_for_split": ["train"], "strategy_tags": []},
        {"premise_id": "é", "allowed_for_split": ["train"], "strategy_tags": ["s"]},
    ])
    assert [(r["premise_id"], r["score"]) for r in result] == [("é", 1), ("z", 0)]


def test_host_string_id_order_and_equal_key_occurrences():
    premises = [
        {"premise_id": value, "allowed_for_split": ["train"], "source_ref": str(index)}
        for index, value in enumerate(["é", "z", 2, "10", "2", ""])
    ]
    result = _score_query({"query_terms": []}, premises)
    assert [(row["premise_id"], row["source_ref"], row["score"]) for row in result] == [
        ("", "5", 0), ("10", "3", 0), (2, "2", 0), ("2", "4", 0),
        ("z", "1", 0), ("é", "0", 0),
    ]


@pytest.mark.parametrize("payload", [
    {}, {"query_counts": [True], "candidates": []},
    {"query_counts": [1], "candidates": [{"eligible": True, "id_rank": 0, "counts": [], "bonus": False}]},
    {"query_counts": [1], "candidates": [{"eligible": 1, "id_rank": 0, "counts": [1], "bonus": False}]},
    {"query_counts": [1], "candidates": [{"eligible": True, "id_rank": -1, "counts": [1], "bonus": False}]},
])
def test_adapter_rejects_invalid_normalized_observations(payload):
    with pytest.raises(ValueError):
        adapter.evaluate(payload, None, None)


def test_runtime_does_not_fall_back_on_kernel_failure(monkeypatch):
    def fail(_payload):
        raise RuntimeError("unavailable")
    monkeypatch.setattr(premise_ranking, "rank", fail)
    with pytest.raises(RuntimeError, match="unavailable"):
        _score_query({}, [])


def test_overlap_uses_minimum_multiplicity_and_split():
    result = _score_query({"query_terms": ["needle needle needle"], "split": "train", "strategy_id": "s"}, [
        {"premise_id": "test-only", "allowed_for_split": ["test"], "statement_excerpt": "needle needle needle needle", "strategy_tags": ["s"]},
        {"premise_id": "candidate", "allowed_for_split": ["train"], "statement_excerpt": "needle needle", "strategy_tags": ["s"]},
    ])
    assert [(r["premise_id"], r["score"]) for r in result] == [("candidate", 3)]


def test_host_normalizes_query_and_maps_verified_occurrences(monkeypatch):
    observed = []
    def certified_result(payload):
        observed.append(payload)
        return [[2, 3], [0, 1]]
    monkeypatch.setattr(premise_ranking, "rank", certified_result)
    result = _score_query({"query_terms": ["needle needle"], "strategy_id": "s"}, [
        {"premise_id": "z", "allowed_for_split": ["train"], "statement_excerpt": "needle", "strategy_tags": []},
        {"premise_id": "hidden", "allowed_for_split": ["test"]},
        {"premise_id": "a", "allowed_for_split": ["train"], "statement_excerpt": "needle needle needle", "strategy_tags": ["s"]},
    ])
    assert observed == [{"query_counts": [2], "candidates": [
        {"eligible": True, "id_rank": 1, "counts": [1], "bonus": False},
        {"eligible": False, "id_rank": 0, "counts": [0], "bonus": False},
        {"eligible": True, "id_rank": 0, "counts": [3], "bonus": True},
    ]}]
    assert [(row["premise_id"], row["score"]) for row in result] == [("a", 3), ("z", 1)]
    assert result[0]["field_hits"] == [{"field": "statement_excerpt", "hit_terms": ["needle"]}]


@pytest.fixture
def cached_retrieval_with_copied_kernel(tmp_path, monkeypatch):
    """Exercise real identity checks without altering the shared source tree."""
    from microcosm_core.organs import formal_math_premise_retrieval as retrieval
    from plectis.components import _bridge

    original = Path(_bridge.__file__).resolve().parent
    copied = tmp_path / "plectis/components"
    shutil.copytree(original / "premise_ranking", copied / "premise_ranking",
                    ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("__init__.py", "_bridge.py", "_worker.py", "_registry.py"):
        shutil.copyfile(original / name, copied / name)
    shutil.copyfile(original.parent / "_sealed_kernel.py", copied.parent / "_sealed_kernel.py")
    monkeypatch.setattr(_bridge, "__file__", str(copied / "_bridge.py"))
    calls = []

    def build_result(*args, **kwargs):
        calls.append((args, kwargs))
        return {"created_at": "2026-10-26T00:00:00Z", "status": "pass",
                "organ_id": retrieval.ORGAN_ID,
                "input_mode": "exported_premise_retrieval_bundle", "retrievals": []}

    monkeypatch.setattr(retrieval, "_build_result", build_result)
    input_dir = tmp_path / "microcosm-substrate/input"
    input_dir.mkdir(parents=True)
    out_dir = tmp_path / "microcosm-substrate/receipts"

    def run():
        return retrieval.run_retrieval_bundle(input_dir, out_dir, reuse_fresh_receipt=True)

    first = run()
    assert first["receipt_reused"] is False
    assert run()["receipt_reused"] is True
    assert len(calls) == 1
    return copied, calls, first, run


def test_cached_retrieval_rebuilds_when_ranking_adapter_changes(cached_retrieval_with_copied_kernel):
    copied, calls, first, run = cached_retrieval_with_copied_kernel
    path = copied / "premise_ranking/_adapter.py"
    previous_stat = path.stat()
    data = path.read_bytes()
    # Keep size and timestamp unchanged: the new dependency is content-bound.
    path.write_bytes(data.replace(b"Strictly", b"StrictLy", 1))
    os.utime(path, ns=(previous_stat.st_atime_ns, previous_stat.st_mtime_ns))
    rebuilt = run()
    assert rebuilt["receipt_reused"] is False
    assert rebuilt["freshness_digest"] != first["freshness_digest"]
    assert len(calls) == 2


@pytest.mark.parametrize("relative", ["PremiseRanking.py", "GENERATED_SHA256.json"])
def test_cached_retrieval_refuses_tampered_kernel(cached_retrieval_with_copied_kernel, relative):
    copied, calls, _first, run = cached_retrieval_with_copied_kernel
    path = copied / "premise_ranking/_generated" / relative
    previous_stat = path.stat()
    data = path.read_bytes()
    path.write_bytes(data[:-1] + (b" " if data[-1:] != b" " else b"\n"))
    os.utime(path, ns=(previous_stat.st_atime_ns, previous_stat.st_mtime_ns))
    with pytest.raises(ValueError, match="reviewed bytes|manifest"):
        run()
    assert len(calls) == 1
