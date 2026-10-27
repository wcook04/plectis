from __future__ import annotations

import json
import itertools

import pytest

import plectis.components.ownership_classification as ownership
from microcosm_core.organs.concurrency_mission_control import (
    classify_generated_surface_claim_lens,
    classify_concurrency_closure_state_lens,
)


def test_verified_core_partitions_and_selects_live_claim_over_earlier_stale():
    result = ownership.classify({
        "paths": [{"id": 7, "generated": True}, {"id": 8, "generated": True},
                  {"id": 9, "generated": False}, {"id": 10, "generated": True}],
        "claims": [{"path": 7, "live": False}, {"path": 7, "live": True},
                   {"path": 8, "live": True}],
    })
    assert result == {"rows": [{"owner_index": 1, "kind": 2},
                               {"owner_index": 2, "kind": 2},
                               {"owner_index": -1, "kind": 0},
                               {"owner_index": -1, "kind": 1}],
                      "classification": 2, "action": 11}


def test_production_classifier_calls_core_and_protects_later_live_claim(monkeypatch):
    real = ownership.classify
    calls = []

    def observed(payload):
        calls.append(payload)
        return real(payload)

    monkeypatch.setattr(ownership, "classify", observed)
    case = {"drift_paths": ["a", "b", "other"],
            "claim_rows": [{"path": "a", "session_id": "old", "freshness_state": "stale"},
                           {"path": "a", "session_id": "later", "freshness_state": "live"},
                           {"path": "b", "session_id": "current", "freshness_state": "live"}]}
    row = classify_generated_surface_claim_lens(case, generated_surfaces=("a", "b"))
    assert len(calls) == 1
    assert row["classification"] == "owned_live"
    assert row["allowed_action"] == "do_not_patch_from_sibling_lane"
    assert row["generated_surface_drift_paths"] == ["a", "b"]
    assert row["unrelated_drift_paths"] == ["other"]
    assert row["surface_owner_rows"][0]["owner_session_id"] == "later"
    assert row["surface_owner_rows"][0]["allowed_action"] == "do_not_patch_from_sibling_lane"
    assert row["owner_session_id"] == "later"


def test_strict_adapter_rejects_non_boolean_and_malformed_inputs():
    from plectis.components.ownership_classification._adapter import evaluate
    with pytest.raises(ValueError):
        evaluate({"paths": [{"id": True, "generated": True}], "claims": []}, None, None)
    with pytest.raises(ValueError):
        evaluate({"paths": [], "claims": [{"path": 1, "live": 1}]}, None, None)
    with pytest.raises(ValueError):
        evaluate({"paths": [], "claims": [], "extra": 1}, None, None)


@pytest.mark.parametrize(
    ("paths", "claims", "expected", "action"),
    [([], [], "clean", "continue"),
     (["other"], [], "unrelated_dirty_state", "route_to_owning_lane_or_capture"),
     (["a"], [], "unowned_generated_drift", "claim_builder_lane_then_regenerate_and_validate"),
     (["a"], [{"path": "a", "session_id": "s", "freshness_state": "stale"}],
      "owned_stale", "release_or_supersede_owner_claim_then_regenerate"),
     (["a"], [{"path": "a", "session_id": "s", "freshness_state": "live"}],
      "owned_live", "do_not_patch_from_sibling_lane"),
     (["a"], [{"path": "a", "session_id": "old", "freshness_state": "stale"},
              {"path": "a", "session_id": "current", "freshness_state": "live"}],
      "owned_live", "do_not_patch_from_sibling_lane")],
)
def test_production_decisions(paths, claims, expected, action):
    result = classify_generated_surface_claim_lens(
        {"drift_paths": paths, "claim_rows": claims}, generated_surfaces=("a",)
    )
    assert (result["classification"], result["allowed_action"]) == (expected, action)


def test_core_failure_does_not_fall_back(monkeypatch):
    def failed(_payload):
        raise RuntimeError("verified worker failed")

    monkeypatch.setattr(ownership, "classify", failed)
    with pytest.raises(RuntimeError, match="verified worker failed"):
        classify_generated_surface_claim_lens({"drift_paths": []})


def test_host_freshness_retains_live_card_and_claim_observations():
    result = classify_generated_surface_claim_lens(
        {"drift_paths": ["a", "b"],
         "session_cards": [{"session_id": "s", "freshness_state": "live"},
                           {"session_id": "s", "freshness_state": "stale"}],
         "claim_rows": [{"path": "a", "session_id": "s"},
                        {"path": "b", "session_id": "s", "claim_state": "live"}]},
        generated_surfaces=("a", "b"),
    )
    assert result["classification"] == "owned_live"
    assert [row["freshness_state"] for row in result["surface_owner_rows"]] == ["live", "live"]
    assert [row["reported_freshness_state"] for row in result["surface_owner_rows"]] == ["stale", "stale"]
    assert [row["allowed_action"] for row in result["surface_owner_rows"]] == [
        "do_not_patch_from_sibling_lane", "do_not_patch_from_sibling_lane"]
    assert all(row["freshness_conflict"] for row in result["matching_owner_rows"])


def test_large_valid_worker_request_keeps_earliest_live_representative():
    # This exceeds the removed 2 MB cap while the earliest live claim determines the
    # result. The shared worker still applies its execution timeout.
    payload = {
        "paths": [{"id": 0, "generated": True}],
        "claims": [{"path": 0, "live": True}] * 90_000,
    }
    assert len(json.dumps({"slug": "ownership_classification", "payload": payload},
                          separators=(",", ":")).encode("utf-8")) > 2_000_000
    assert ownership.classify(payload) == {
        "rows": [{"owner_index": 0, "kind": 2}],
        "classification": 2,
        "action": 11,
    }


def test_worker_rejects_unrecognized_payload_field():
    with pytest.raises(RuntimeError, match="invalid output"):
        ownership.classify({"paths": [], "claims": [], "unexpected": True})


def test_late_owner_and_absent_owner_use_iterative_claim_scan():
    claims = [{"path": i, "live": False} for i in range(1100)]
    claims.append({"path": 1100, "live": True})
    result = ownership.classify({
        "paths": [{"id": 1100, "generated": True}, {"id": 1101, "generated": True}],
        "claims": claims,
    })
    assert result == {
        "rows": [{"owner_index": 1100, "kind": 2}, {"owner_index": -1, "kind": 1}],
        "classification": 2, "action": 11,
    }


def test_long_path_packet_does_not_use_recursive_classification_scan():
    result = ownership.classify({
        "paths": [{"id": i, "generated": True} for i in range(1100)], "claims": [],
    })
    assert result == {
        "rows": [{"owner_index": -1, "kind": 1}] * 1100,
        "classification": 1, "action": 13,
    }


@pytest.mark.parametrize("states", itertools.permutations(("stale", "live", "unknown")))
def test_core_live_protection_is_independent_of_claim_order(states):
    result = ownership.classify({
        "paths": [{"id": 1, "generated": True}],
        "claims": [{"path": 1, "freshness": state} for state in states],
    })
    assert result == {"rows": [{"owner_index": states.index("live"), "kind": 2}],
                      "classification": 2, "action": 11}


@pytest.mark.parametrize("states", [("stale", "unknown"), ("unknown", "stale")])
def test_core_unknown_freshness_does_not_authorize_stale_reentry(states):
    result = ownership.classify({
        "paths": [{"id": 1, "generated": True}],
        "claims": [{"path": 1, "freshness": state} for state in states],
    })
    assert result == {"rows": [{"owner_index": states.index("unknown"), "kind": 5}],
                      "classification": 5, "action": 16}


@pytest.mark.parametrize("states", itertools.permutations(("stale", "live_a", "live_b")))
def test_all_matching_live_owners_are_retained_and_report_collision(states):
    claims = [{"path": "a", "session_id": state, "claim_id": state,
               "freshness_state": "live" if state.startswith("live") else "stale"}
              for state in states]
    row = classify_generated_surface_claim_lens(
        {"drift_paths": ["a"], "claim_rows": claims, "claim_collision_count": 0},
        generated_surfaces=("a",))
    first_live = next(state for state in states if state.startswith("live"))
    assert row["classification"] == "owned_live"
    assert row["owner_session_id"] == first_live
    assert row["live_owner_collision_count"] == 1
    assert row["live_owner_collisions"][0]["owner_session_ids"] == ["live_a", "live_b"]
    assert len(row["matching_owner_rows"]) == 3


def test_same_session_duplicate_claims_are_not_distinct_live_owner_collision():
    claim = {"path": "a", "session_id": "same", "freshness_state": "live"}
    row = classify_generated_surface_claim_lens(
        {"drift_paths": ["a"], "claim_rows": [claim, dict(claim)]}, generated_surfaces=("a",))
    assert row["classification"] == "owned_live"
    assert row["live_owner_collision_count"] == 0
    assert len(row["matching_owner_rows"]) == 2


@pytest.mark.parametrize("claim", [
    {"path": "a", "session_id": "s"},
    {"path": "a", "session_id": "s", "freshness_state": "unrecognized"},
    {"path": "a", "freshness_state": "live"},
])
def test_missing_or_unknown_owner_observation_blocks_reentry(claim):
    row = classify_generated_surface_claim_lens(
        {"drift_paths": ["a"], "claim_rows": [claim]}, generated_surfaces=("a",))
    assert row["classification"] == "owned_unresolved"
    assert row["allowed_action"] == "inspect_owner_freshness_before_reentry"


@pytest.mark.parametrize("reversed_claims", (False, True))
def test_actual_generated_and_closure_routes_protect_live_owner_in_both_orders(reversed_claims):
    path = "microcosm-substrate/AGENT_ROUTES.md"
    claims = [{"path": path, "session_id": "old", "claim_id": "old_claim", "claim_state": "stale"},
              {"path": path, "session_id": "active", "claim_id": "live_claim", "claim_state": "live"}]
    if reversed_claims:
        claims.reverse()
    case = {"drift_paths": [path], "claim_rows": claims,
            "claim_collision_count": 0, "claim_collisions": []}
    generated = classify_generated_surface_claim_lens(case)
    closure = classify_concurrency_closure_state_lens(case)
    assert generated["classification"] == "owned_live"
    assert generated["allowed_action"] == "do_not_patch_from_sibling_lane"
    assert closure["classification"] == "owned_live_handoff"
    assert closure["allowed_action"] == "handoff_to_live_owner_or_wait_for_release"
    for row in (generated, closure):
        assert row["owner_session_id"] == "active"
        assert row["owner_claim_id"] == "live_claim"
        assert row["owner_freshness_state"] == "live"


def test_live_handoff_representative_is_relevant_live_owner_across_paths():
    case = {"drift_paths": ["microcosm-substrate/AGENT_ROUTES.md", "microcosm-substrate/ARCHITECTURE.md"],
            "claim_rows": [
                {"path": "unrelated", "session_id": "unrelated", "claim_state": "live"},
                {"path": "microcosm-substrate/AGENT_ROUTES.md", "session_id": "old", "claim_state": "stale"},
                {"path": "microcosm-substrate/ARCHITECTURE.md", "session_id": "active", "claim_state": "live"}]}
    for row in (classify_generated_surface_claim_lens(case), classify_concurrency_closure_state_lens(case)):
        assert row["owner_session_id"] == "active"
        assert row["owner_freshness_state"] == "live"
        assert len(row["matching_owner_rows"]) == 2


@pytest.mark.parametrize("states", [("live", "stale"), ("stale", "live")])
def test_duplicate_session_card_live_observation_survives_both_orders(states):
    case = {"drift_paths": ["microcosm-substrate/AGENT_ROUTES.md"],
            "session_cards": [{"session_id": "s", "freshness_state": state} for state in states],
            "claim_rows": [{"path": "microcosm-substrate/AGENT_ROUTES.md", "session_id": "s"}]}
    for row in (classify_generated_surface_claim_lens(case), classify_concurrency_closure_state_lens(case)):
        assert row["owner_session_id"] == "s"
        assert row["owner_freshness_state"] == "live"
        assert row["matching_owner_rows"][0]["freshness_observations"] == ["live", "stale"]
        assert row["matching_owner_rows"][0]["freshness_conflict"] is True
    assert classify_concurrency_closure_state_lens(case)["classification"] == "owned_live_handoff"


@pytest.mark.parametrize("claim", [{"path": "scope", "claim_state": "live"},
                                   {"session_id": "s", "claim_state": "live"}])
def test_overbroad_missing_owner_identity_or_scope_cannot_fall_through_to_closed_success(claim):
    row = classify_concurrency_closure_state_lens({
        "path_scope_status": "overbroad", "product_closed": True,
        "validation_state": "complete", "scoped_commit_status": "committed",
        "claim_rows": [claim],
    })
    assert row["classification"] == "owned_unresolved"
    assert row["allowed_action"] == "inspect_owner_freshness_before_reentry"
    assert row["owner_session_id"] is None


def test_unresolved_generated_owner_blocks_closed_success():
    row = classify_concurrency_closure_state_lens({
        "drift_paths": ["microcosm-substrate/AGENT_ROUTES.md"],
        "product_closed": True, "validation_state": "complete", "scoped_commit_status": "committed",
        "claim_rows": [{"path": "microcosm-substrate/AGENT_ROUTES.md", "session_id": "s"}],
    })
    assert row["classification"] == "owned_unresolved"
    assert row["allowed_action"] == "inspect_owner_freshness_before_reentry"


def test_fixture_gates_recompute_live_protection_against_baked_stale_expectations():
    from pathlib import Path
    from microcosm_core.organs import concurrency_mission_control as organ

    manifest = json.loads((Path(__file__).resolve().parents[1] /
        "fixtures/first_wave/concurrency_mission_control/input/concurrency_mission_control_exercise_manifest.json").read_text())
    case = {"case_id": "adversarial_duplicate_owners",
            "drift_paths": ["microcosm-substrate/AGENT_ROUTES.md"],
            "claim_rows": [
                {"path": "microcosm-substrate/AGENT_ROUTES.md", "session_id": "old", "claim_state": "stale"},
                {"path": "microcosm-substrate/AGENT_ROUTES.md", "session_id": "active", "claim_state": "live"}],
            "expected_classification": "owned_stale",
            "expected_allowed_action": "release_or_supersede_owner_claim_then_regenerate"}
    manifest["generated_surface_claim_lens"]["cases"].append(case)
    closure_case = {**case, "expected_classification": "owned_stale_reentry",
                    "expected_allowed_action": "release_or_supersede_owner_claim_then_reenter"}
    manifest["closure_state_lens"]["cases"].append(closure_case)
    for gate, expected in ((organ._generated_surface_claim_lens_gate, "owned_live"),
                           (organ._closure_state_lens_gate, "owned_live_handoff")):
        result = gate(manifest)
        assert result["status"] == "blocked"
        row = next(row for row in result["rows"] if row["case_id"] == case["case_id"])
        assert row["classification"] == expected
        assert row["owner_session_id"] == "active"
