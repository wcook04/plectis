"""Navigation core contract, adapter boundary and production integration."""
import itertools

import pytest

from microcosm_core.engine_room.navigation_fitness_benchmark import NavigationFitnessTask, evaluate_task
from plectis.components.navigation_metrics import evaluate
import plectis.components.navigation_metrics as navigation_core


def payload(expected=(), selected=(), **overrides):
    value = {"expected": list(expected), "selected": list(selected), "timeout": False,
             "error": False, "scent_fail": False, "forbidden": False, "wall": 10, "budget": 100}
    value.update(overrides)
    return value


def test_overlap_and_prefix_units_are_selected_artifacts():
    result = evaluate(payload(["x", "*"], ["x"]))
    assert result["found_count"] == 2
    assert result["relevant_count"] == 1
    assert result["found"] == [True, True]
    result = evaluate(payload(["skills:*"], ["skills:a", "skills:b", "other"]))
    assert result["found_count"] == 1
    assert result["relevant_count"] == 2


def test_exact_wildcard_empty_unicode_and_empty_sets():
    result = evaluate(payload(["🟦*", "literal", "*"], ["🟦x", "literal", "z"]))
    assert result["found"] == [True, True, True]
    assert result["relevant_count"] == 3
    result = evaluate(payload(["x*"], []))
    assert result["found"] == [False]
    assert result["decision"] == 3
    assert evaluate(payload([], []))["decision"] == 0


def test_only_the_final_star_is_wildcard_and_empty_prefix_matches_empty_id():
    result = evaluate(payload(["a*b", "a**", "*", ""], ["a*b", "a*tail", ""]))
    assert result["found"] == [True, True, True, True]
    assert result["found_count"] == 4
    assert result["relevant_count"] == 3
    result = evaluate(payload(["a*b", "a**"], ["ab", "axxb", "atail"]))
    assert result["found"] == [False, False]
    assert result["relevant_count"] == 0


def test_decision_priority_and_independent_latency():
    for flags in itertools.product((False, True), repeat=4):
        timeout, error, scent, forbidden = flags
        result = evaluate(payload([], [], timeout=timeout, error=error,
                                  scent_fail=scent, forbidden=forbidden,
                                  wall=101, budget=100))
        expected = 1 if timeout else 2 if error else 4 if scent else 5 if forbidden else 0
        assert result["decision"] == expected
        assert result["latency"] == (2 if timeout else 1)
    assert evaluate(payload(["missing"], [], scent_fail=True, forbidden=True))["decision"] == 3


@pytest.mark.parametrize(("timeout", "wall", "budget", "code"), [
    (False, 100, 100, 0),
    (False, 101, 100, 1),
    (False, -2, -1, 0),
    (False, -1, -2, 1),
    (False, 10 ** 60, 10 ** 60 - 1, 1),
    (True, -1, 0, 2),
    (True, 101, 100, 2),
])
def test_latency_code_is_exact_at_integer_boundaries(timeout, wall, budget, code):
    result = evaluate(payload(timeout=timeout, wall=wall, budget=budget))
    assert result["latency"] == code
    assert result["latency"] in {0, 1, 2}


@pytest.mark.parametrize("change", [
    {"expected": ["x", "x"]}, {"selected": [1]}, {"timeout": 1},
    {"wall": True}, {"budget": 1.2}, {"unknown": 1},
])
def test_adapter_rejects_malformed_inputs(change):
    with pytest.raises((ValueError, RuntimeError)):
        evaluate(payload(**change))


def test_component_calls_verified_core(monkeypatch):
    calls = []
    original = navigation_core.evaluate

    def traced(data):
        calls.append(data)
        return original(data)

    monkeypatch.setattr(navigation_core, "evaluate", traced)
    task = NavigationFitnessTask("id", "family", "prompt", "route", ("s:*", "s:a"),
                                 (), 100, scent_terms=())
    result = evaluate_task(task, {"selected_artifacts": ["s:a", "s:b"], "wall_ms": 101})
    assert len(calls) == 1 and calls[0]["expected"] == ["s:*", "s:a"]
    assert result["precision_at_packet"] == 1.0
    assert result["recall_at_packet"] == 1.0
    assert result["sufficiency_status"] == "pass"
    assert result["latency_status"] == "fail"


def test_navigation_organ_fixture_route_calls_verified_core(monkeypatch):
    from pathlib import Path
    from microcosm_core.organs.navigation_fitness_benchmark import build_result

    calls = []
    original = navigation_core.evaluate

    def traced(data):
        calls.append(data)
        return original(data)

    monkeypatch.setattr(navigation_core, "evaluate", traced)
    fixture = Path(__file__).resolve().parents[1] / "fixtures/first_wave/navigation_fitness_benchmark/input"
    result = build_result(fixture)
    assert result["status"] == "pass"
    assert result["case_count"] == 4
    # The clean-fanout fixture contains two tasks; the other cases contain one.
    assert len(calls) == 5


def test_python_normalization_and_failure_precedence():
    task = NavigationFitnessTask("id", "family", "prompt", "route", ("x", "*") ,
                                 ("bad",), 100, scent_terms=("required",))
    result = evaluate_task(task, {"selected_artifacts": ["x", "x"],
                                  "first_contact_command": "bad", "wall_ms": 10,
                                  "timed_out": True, "error": "error"})
    assert result["selected_artifact_count"] == 1
    assert result["precision_at_packet"] == 1.0
    assert result["sufficiency_failure_kind"] == "route_timeout"
    assert result["latency_status"] == "timeout"


def test_production_metrics_failure_propagates_without_recomputation(monkeypatch):
    def failed(_payload):
        raise RuntimeError("verified metrics unavailable")

    monkeypatch.setattr(navigation_core, "evaluate", failed)
    task = NavigationFitnessTask("id", "family", "prompt", "route", ("x",))
    with pytest.raises(RuntimeError, match="verified metrics unavailable"):
        evaluate_task(task, {"selected_artifacts": ["x"]})


def test_long_packet_does_not_depend_on_python_recursion_limit():
    expected = [f"id:{i}" for i in range(1100)]
    result = evaluate(payload(expected, ["id:1099"]))
    assert result["found_count"] == 1
    assert result["relevant_count"] == 1
    assert result["decision"] == 3
