from __future__ import annotations

import random

import pytest

from plectis.components.tactic_selection import select
from plectis.components.tactic_selection._adapter import evaluate
from microcosm_core.organs import target_shape_tactic_routing_gate as routing


def _candidate(name, known=True, available=True, allowed=True):
    return {"id": name, "known": known, "available": available, "allowed": allowed}


@pytest.mark.parametrize(
    "preferences,candidates,expected",
    [
        (["a", "b"], [_candidate("b"), _candidate("a")], [1, 0]),
        (["a", "b"], [_candidate("a", available=False), _candidate("b")], [1, 1]),
        (["a"], [_candidate("a", known=False), _candidate("z")], [1, -1]),
        (["a"], [_candidate("a", allowed=False)], [-1, -1]),
        ([], [_candidate("x"), _candidate("x")], [0, -1]),
        (["x", "x"], [_candidate("x")], [0, 0]),
        (["x"], [_candidate("x", known=False), _candidate("x")], [1, 0]),
        (["x", "y"], [_candidate("y"), _candidate("x"), _candidate("x")], [1, 0]),
        (["", "é"], [_candidate("é"), _candidate("")], [1, 0]),
        (["missing"], [], [-1, -1]),
    ],
)
def test_verified_selection_precedence_and_fallback(preferences, candidates, expected):
    assert select({"preferences": preferences, "candidates": candidates}) == expected


def test_selection_matches_independent_preference_product_order():
    rng = random.Random(14173)
    identities = ["", "a", "b", "é"]
    for _ in range(10):
        preferences = [rng.choice(identities) for _ in range(rng.randrange(6))]
        candidates = [
            _candidate(rng.choice(identities), *(bool(rng.randrange(2)) for _ in range(3)))
            for _ in range(15)
        ]
        eligible = [i for i, row in enumerate(candidates)
                    if all(row[key] for key in ("known", "available", "allowed"))]
        matches = [(preference, index)
                   for preference, identity in enumerate(preferences)
                   for index in eligible if candidates[index]["id"] == identity]
        expected = ([min(matches)[1], min(matches)[0]] if matches else
                    [eligible[0], -1] if eligible else [-1, -1])
        assert select({"preferences": preferences, "candidates": candidates}) == expected


@pytest.mark.parametrize("payload", [
    {"preferences": "x", "candidates": []},
    {"preferences": [], "candidates": [{"id": "x", "known": 1, "available": True, "allowed": True}]},
    {"preferences": [], "candidates": [{"id": "x", "known": True, "available": True}]},
    {"preferences": [False], "candidates": []},
])
def test_adapter_rejects_untyped_observations(payload):
    with pytest.raises(ValueError):
        evaluate(payload, None, None)


def test_actual_route_calls_verified_selector(monkeypatch):
    from plectis.components import tactic_selection
    real = tactic_selection.select
    seen = []
    def spy(payload):
        seen.append(payload)
        return real(payload)
    monkeypatch.setattr(tactic_selection, "select", spy)
    row = {"route_case_id": "test", "target_shape": "bool_decision_goal",
           "candidate_tactic_ids": ["rfl", "decide"],
           "allowed_tactic_ids": ["rfl", "decide"], "selected_tactic_id": "decide"}
    result = routing._score_case(row, known={"rfl", "decide"},
                                 available={"rfl", "decide"}, unavailable=set())
    assert seen and seen[0]["candidates"][1] == _candidate("decide")
    assert result["computed_selected_tactic_id"] == "decide"
    assert result["selection_basis"] == "shape_preferred_available"
    assert result["expectation_met"] is True


def test_runtime_has_no_python_fallback(monkeypatch):
    from plectis.components import tactic_selection
    def fail(_payload):
        raise RuntimeError("verified selector unavailable")
    monkeypatch.setattr(tactic_selection, "select", fail)
    with pytest.raises(RuntimeError, match="verified selector unavailable"):
        routing._score_case({"candidate_tactic_ids": ["rfl"], "allowed_tactic_ids": ["rfl"]},
                            known={"rfl"}, available={"rfl"}, unavailable=set())


def test_runtime_records_skipped_preference_and_fallback():
    row = {"route_case_id": "fallback", "target_shape": "mathlib_search_goal",
           "candidate_tactic_ids": ["aesop", "rfl", "simp_all"],
           "allowed_tactic_ids": ["rfl", "simp_all"], "selected_tactic_id": "simp_all"}
    result = routing._score_case(row, known={"aesop", "rfl", "simp_all"},
                                 available={"rfl", "simp_all"}, unavailable={"aesop"})
    assert result["computed_selected_tactic_id"] == "simp_all"
    assert result["selection_basis"] == "preferred_tactic_fallback"
    assert result["preferred_unavailable_tactic_ids"] == ["aesop"]
    assert result["expectation_met"] is True


def test_runtime_unknown_shape_uses_default_before_candidate_order():
    row = {"route_case_id": "unknown", "target_shape": "not_in_map",
           "candidate_tactic_ids": ["simp", "rfl"],
           "allowed_tactic_ids": ["simp", "rfl"], "selected_tactic_id": "rfl"}
    result = routing._score_case(row, known={"simp", "rfl"},
                                 available={"simp", "rfl"}, unavailable=set())
    assert result["computed_selected_tactic_id"] == "rfl"
    assert result["selection_basis"] == "unknown_shape_default_preference"
    assert result["unknown_shape_default_used"] is True
