"""The generated walkthrough decision is on the public validator path."""
from copy import deepcopy
import json
import math
from pathlib import Path

import pytest

from microcosm_core.organs.public_reveal_walkthrough import validate_evidence_map, validate_walkthrough
from plectis.components.walkthrough_validation import validate

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/first_wave/public_reveal_walkthrough/input/reveal_walkthrough.json"


def test_fixture_calls_generated_decision(monkeypatch):
    import plectis.components.walkthrough_validation as component
    original = component.validate
    calls = []

    def capture(steps, time_budget_minutes=10):
        calls.append((steps, time_budget_minutes))
        return original(steps, time_budget_minutes)

    monkeypatch.setattr(component, "validate", capture)
    payload = json.loads(FIXTURE.read_text())
    result = validate_walkthrough(payload)
    assert result["status"] == "pass"
    assert len(calls) == 1 and len(calls[0][0]) == 5 and calls[0][1] == 10
    assert result["command_count"] == len({x for step in calls[0][0] for x in step["commands"]})
    assert result["evidence_ref_count"] == len({x for step in calls[0][0] for x in step["evidence_refs"]})


@pytest.mark.parametrize("field,code", [
    ("commands", "PUBLIC_REVEAL_RUNTIME_COMMAND_MISSING"),
    ("inspect_refs", "PUBLIC_REVEAL_STEP_EVIDENCE_MISSING"),
    ("evidence_refs", "PUBLIC_REVEAL_STEP_EVIDENCE_MISSING"),
])
def test_missing_one_step_field_blocks_despite_aggregate_floor(field, code):
    payload = json.loads(FIXTURE.read_text())
    payload["steps"][0][field] = ["", "   ", 12]
    result = validate_walkthrough(payload)
    assert result["command_count"] >= 4 and result["evidence_ref_count"] >= 4
    assert result["status"] == "blocked"
    assert any(f["error_code"] == code and f["subject_id"] == "install_and_compile"
               for f in result["findings"])


def test_duplicate_references_do_not_meet_distinct_floor_and_optional_fields_stay_optional():
    steps = [{"commands": ["one"], "inspect_refs": ["ref"], "evidence_refs": ["evidence"]}
             for _ in range(5)]
    result = validate(steps)
    assert result == {"accepted": False, "command_count": 1, "evidence_count": 1}
    payload = {"steps": deepcopy(steps), "time_budget_minutes": 10}
    for i, step in enumerate(payload["steps"]):
        step["commands"] = [f"command-{i}"]
        step["evidence_refs"] = [f"evidence-{i}"]
    assert validate_walkthrough(payload)["status"] == "pass"


def test_adapter_rejects_malformed_and_empty_values():
    with pytest.raises(RuntimeError):
        validate([{"commands": [" "], "inspect_refs": ["r"], "evidence_refs": ["e"]}])
    with pytest.raises(RuntimeError):
        validate([{"commands": [1], "inspect_refs": ["r"], "evidence_refs": ["e"]}])


@pytest.mark.parametrize("invalid_step", [None, [], "not a step", 12])
def test_malformed_positive_step_cannot_disappear_before_verified_decision(invalid_step):
    payload = json.loads(FIXTURE.read_text())
    payload["steps"].append(invalid_step)
    result = validate_walkthrough(payload)
    assert result["status"] == "blocked"
    assert result["step_count"] == 6
    assert result["steps"][-1]["commands"] == []
    assert {finding["error_code"] for finding in result["findings"]} >= {
        "PUBLIC_REVEAL_RUNTIME_COMMAND_MISSING", "PUBLIC_REVEAL_STEP_EVIDENCE_MISSING",
    }


def test_large_walkthrough_does_not_recurse_on_steps():
    steps = [{"commands": [f"command-{i % 4}"], "inspect_refs": ["ref"],
              "evidence_refs": [f"evidence-{i % 4}"]} for i in range(1500)]
    assert validate(steps) == {"accepted": True, "command_count": 4, "evidence_count": 4}


@pytest.mark.parametrize("budget", [100, 10.1, 0, -1, None, True, "10", float("inf"), float("nan")])
def test_host_enforces_the_standard_ten_minute_budget(budget):
    payload = json.loads(FIXTURE.read_text())
    payload["time_budget_minutes"] = budget
    normalized_budget = budget if type(budget) is int or (type(budget) is float and math.isfinite(budget)) else 0
    assert validate([{key: step[key] for key in ("commands", "inspect_refs", "evidence_refs")}
                     for step in payload["steps"]], normalized_budget)["accepted"] is False
    result = validate_walkthrough(payload)
    assert result["status"] == "blocked"
    assert any(f["error_code"] == "PUBLIC_REVEAL_TIME_BUDGET_INVALID" for f in result["findings"])


@pytest.mark.parametrize("minute_range", ["0-100", "9-11", "4-3", "not a range", [0, 2], True])
def test_declared_step_times_must_fit_the_budget(minute_range):
    payload = json.loads(FIXTURE.read_text())
    payload["steps"][0]["minute_range"] = minute_range
    result = validate_walkthrough(payload)
    assert result["status"] == "blocked"
    assert any(f["error_code"] == "PUBLIC_REVEAL_STEP_TIME_INVALID" for f in result["findings"])


@pytest.mark.parametrize("ref", ["../private.json", "/etc/passwd", "C:\\private\\data.json",
                                  "https://example.com/evidence", "http://localhost.example.com/evidence",
                                  "file:///etc/passwd", "a/%2e%2e/private.json"])
def test_host_enforces_public_relative_or_explicit_localhost_references(ref):
    payload = json.loads(FIXTURE.read_text())
    payload["steps"][0]["evidence_refs"] = [ref]
    result = validate_walkthrough(payload)
    assert result["status"] == "blocked"
    assert any(f["error_code"] == "PUBLIC_REVEAL_REFERENCE_BOUNDARY_INVALID" for f in result["findings"])


def test_future_project_outputs_and_nonexistent_public_refs_are_plans_not_file_proofs():
    payload = json.loads(FIXTURE.read_text())
    payload["steps"][0]["evidence_refs"] = ["future/public-evidence.json"]
    payload["steps"][0]["inspect_refs"] = [".microcosm/future-output.json", "http://localhost:8765/project/observatory"]
    assert not (ROOT / "future/public-evidence.json").exists()
    assert validate_walkthrough(payload)["status"] == "pass"


@pytest.mark.parametrize("budget", [5, 5.5, 10])
def test_positive_budget_at_or_below_ten_accepts_declared_ranges_that_fit(budget):
    payload = json.loads(FIXTURE.read_text())
    payload["time_budget_minutes"] = budget
    for index, step in enumerate(payload["steps"]):
        step["minute_range"] = f"{index}-{index + 1}"
    assert validate_walkthrough(payload)["status"] == "pass"


@pytest.mark.parametrize("ref,accepted", [("future/evidence.json", True),
                                         ("http://[::1]:8765/project/evidence", True),
                                         ("../outside.json", False),
                                         ("https://example.com/evidence", False)])
def test_evidence_map_uses_the_same_reference_boundary_without_requiring_existence(ref, accepted):
    result = validate_evidence_map({"evidence": [
        {"evidence_id": "planned", "ref": ref, "projection_not_authority": True},
    ]})
    assert result["status"] == ("pass" if accepted else "blocked")
    if not accepted:
        assert result["findings"][0]["error_code"] == "PUBLIC_REVEAL_REFERENCE_BOUNDARY_INVALID"


@pytest.mark.parametrize("budget,accepted", [(10, True), (5.5, True), (0.1, True),
                                           (100, False), (0, False), (-1, False),
                                           (math.nextafter(10, math.inf), False)])
def test_generated_acceptance_uses_the_actual_numeric_budget(budget, accepted):
    payload = json.loads(FIXTURE.read_text())
    steps = [{key: step[key] for key in ("commands", "inspect_refs", "evidence_refs")}
             for step in payload["steps"]]
    assert validate(steps, budget)["accepted"] is accepted


@pytest.mark.parametrize("budget", [None, True, "10", [], {}])
def test_direct_budget_adapter_rejects_malformed_numeric_values(budget):
    with pytest.raises((RuntimeError, ValueError)):
        validate([], budget)


def test_adapter_supplies_exact_observed_number_ratio_to_generated_method():
    from plectis.components.walkthrough_validation._adapter import evaluate as adapter

    observed = []

    class Kernel:
        class default__:
            @staticmethod
            def Evaluate(steps, numerator, denominator):
                observed.append((numerator, denominator))
                return False, 0, 0

    class Dafny:
        Seq = list

    cases = [(0.1, (3602879701896397, 36028797018963968)),
             (5.5, (11, 2)), (10, (10, 1)),
             (math.nextafter(10, math.inf), (5629499534213121, 562949953421312))]
    for value, expected in cases:
        adapter({"steps": [], "time_budget_minutes": value}, Kernel, Dafny)
        assert observed[-1] == expected


@pytest.mark.parametrize("budget,expected_status", [(5.5, "pass"), (100, "blocked")])
def test_production_forwards_observed_budget_to_verified_core(monkeypatch, budget, expected_status):
    import plectis.components.walkthrough_validation as component
    original = component.validate
    seen = []

    def capture(steps, time_budget_minutes=10):
        seen.append(time_budget_minutes)
        return original(steps, time_budget_minutes)

    monkeypatch.setattr(component, "validate", capture)
    payload = json.loads(FIXTURE.read_text())
    payload["time_budget_minutes"] = budget
    for index, step in enumerate(payload["steps"]):
        step["minute_range"] = f"{index}-{index + 1}"
    assert validate_walkthrough(payload)["status"] == expected_status
    assert seen == [budget]


def test_local_browser_route_needs_explicit_localhost_context_in_its_step():
    payload = json.loads(FIXTURE.read_text())
    result = validate_walkthrough(payload)
    assert "http://127.0.0.1:8765/project/observatory" in result["steps"][2]["inspect_refs"]
    payload["steps"][2]["inspect_refs"] = ["/project/observatory"]
    result = validate_walkthrough(payload)
    assert result["status"] == "blocked"
    assert any(f["error_code"] == "PUBLIC_REVEAL_REFERENCE_BOUNDARY_INVALID" for f in result["findings"])


def test_missing_required_budget_reaches_generated_rejection_and_host_diagnostic(monkeypatch):
    import plectis.components.walkthrough_validation as component
    original = component.validate
    seen = []

    def capture(steps, time_budget_minutes=10):
        decision = original(steps, time_budget_minutes)
        seen.append((time_budget_minutes, decision["accepted"]))
        return decision

    monkeypatch.setattr(component, "validate", capture)
    payload = json.loads(FIXTURE.read_text())
    del payload["time_budget_minutes"]
    result = validate_walkthrough(payload)
    assert seen == [(0, False)]
    assert result["status"] == "blocked"
    assert any(f["error_code"] == "PUBLIC_REVEAL_TIME_BUDGET_INVALID" for f in result["findings"])
