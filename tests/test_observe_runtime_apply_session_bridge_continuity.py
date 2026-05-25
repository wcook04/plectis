from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent
FIXTURE = (
    MICROCOSM_ROOT
    / "fixtures/second_wave/bridge_phase_continuity_runtime/input/"
    "observe_apply_session_fixture.json"
)
BINDINGS = REPO_ROOT / "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json"
ROUTE_READINESS = (
    REPO_ROOT / "state/microcosm_portfolio/extracted_pattern_route_readiness_audit.json"
)
BRIDGE_MANIFEST = (
    REPO_ROOT
    / "state/microcosm_portfolio/reconstruction/fixture_manifests/"
    "bridge_phase_continuity_runtime.fixture_manifest.json"
)
OBSERVE_RUNTIME_MANIFEST = (
    MICROCOSM_ROOT
    / "examples/macro_projection_import_protocol/"
    "exported_projection_import_bundle/observe_runtime_source_module_manifest.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def _binding_for(pattern_id: str) -> dict[str, Any]:
    bindings = _load_json(BINDINGS)
    for row in bindings["pattern_bindings"]:
        if row["pattern_id"] == pattern_id:
            return row
    raise AssertionError(f"missing binding for {pattern_id}")


def _readiness_for(readiness_id: str) -> dict[str, Any]:
    readiness = _load_json(ROUTE_READINESS)
    for row in readiness["organ_readiness"]:
        if row["readiness_id"] == readiness_id:
            return row
    raise AssertionError(f"missing readiness row for {readiness_id}")


def test_observe_apply_fixture_is_bound_to_bridge_continuity_route() -> None:
    fixture = _load_json(FIXTURE)
    binding = _binding_for("observe_runtime_apply_session")
    readiness = _readiness_for("bridge_phase_continuity_runtime")
    bridge_manifest = _load_json(BRIDGE_MANIFEST)

    assert fixture["pattern_id"] == "observe_runtime_apply_session"
    assert fixture["organ_id"] == "bridge_phase_continuity_runtime"
    assert fixture["router_id"] == "bridge_autonomy_reaction_rows"
    assert fixture["binding_ref"].endswith("::observe_runtime_apply_session")
    assert fixture["fixture_manifest_ref"].endswith(
        "bridge_phase_continuity_runtime.fixture_manifest.json"
    )

    route = binding["route_readiness"]
    assert route["readiness_id"] == fixture["organ_id"]
    assert route["router_id"] == fixture["router_id"]
    assert route["status"] == "routed_to_organ_bundle"
    assert route["individual_row_selection"] == "forbidden"
    assert fixture["public_boundary"]["bridge_dispatch_authorized"] is False
    assert fixture["public_boundary"]["provider_call_authorized"] is False

    assert readiness["readiness_id"] == fixture["organ_id"]
    assert readiness["selection_allowed"] == "select_after_transaction_and_boundary_organs"
    assert readiness["individual_row_selection"] == "forbidden"
    assert "observe_runtime_apply_session" in bridge_manifest["source_pattern_ids"]
    assert bridge_manifest["future_organ_synthetic_fixture_acceptance_gate_v1"][
        "requires_synthetic_inputs_only"
    ] is True


def test_observe_apply_fixture_matches_landed_source_module_manifest() -> None:
    fixture = _load_json(FIXTURE)
    manifest = _load_json(OBSERVE_RUNTIME_MANIFEST)

    assert manifest["manifest_id"] == "observe_runtime_source_modules_import"
    assert manifest["classification"] == "copied_non_secret_macro_body"
    assert manifest["module_count"] == 5
    assert fixture["source_module_manifest_ref"].endswith(
        "observe_runtime_source_module_manifest.json"
    )

    fixture_refs = set(fixture["source_module_refs"])
    manifest_refs = {row["target_ref"] for row in manifest["modules"]}
    assert fixture_refs == manifest_refs

    for row in manifest["modules"]:
        target = REPO_ROOT / row["target_ref"]
        assert target.is_file()
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert digest == row["target_sha256"]
        assert row["source_sha256"] == row["target_sha256"]
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_observe_apply_fixture_carries_synthetic_runtime_and_rollback_floor() -> None:
    fixture = _load_json(FIXTURE)
    session = fixture["synthetic_observe_apply_session"]
    observe_manifest = session["observe_session_manifest"]
    status_packet = session["grouped_runtime_status_packet"]
    finalizer = session["apply_session_finalizer"]
    rollback = session["rollback_on_validation_failure"]
    boundary = fixture["public_boundary"]

    assert observe_manifest["observe_id"] == "OBS_SYNTHETIC_BRIDGE_CONTINUITY_001"
    assert observe_manifest["state"] == "dispatching"
    assert [group["label"] for group in observe_manifest["groups"]] == [
        "source_manifest_verified",
        "apply_target_review",
    ]
    assert status_packet["can_continue"] is True
    assert status_packet["continue_mode"] == "resume_pending"
    assert status_packet["pending_group_labels"] == ["apply_target_review"]
    assert status_packet["authority_ceiling"] == (
        "synthetic_status_packet_only_not_live_runtime_health"
    )
    assert finalizer["finalizer_status"] == "closed_with_receipts"
    assert finalizer["closeout_transition_path"].endswith("closeout_transition.json")
    assert "work_landed_without_closeout_transition" in finalizer["must_not_claim"]
    assert rollback == {
        "case_id": "apply_validation_failure_rolls_back_observe_promotion",
        "validation_status": "fail",
        "rollback_required": True,
        "writes_allowed_after_failure": False,
        "expected_error_code": "OBSERVE_APPLY_VALIDATION_FAILED",
    }
    assert boundary["payload_text_included"] is False
    assert boundary["private_live_state_included"] is False
    assert boundary["public_write_authorized"] is False


def test_observe_apply_fixture_public_boundary_excludes_private_payload_content() -> None:
    fixture = _load_json(FIXTURE)
    serialized = json.dumps(fixture, sort_keys=True).lower()

    forbidden_payload_markers = [
        "begin private key",
        "session_cookie=",
        "authorization: bearer",
        "raw_transcript_text",
        "provider_response_json",
        "operator_thread_text",
        "browser_storage_snapshot",
        "credential_value",
    ]
    for marker in forbidden_payload_markers:
        assert marker not in serialized

    keys = _walk_keys(fixture)
    assert "matched_excerpt" not in keys
    assert "payload" not in keys
    assert "private_text" not in keys
    assert "provider_response" not in keys
    assert fixture["anti_claim"].startswith(
        "This fixture makes observe_runtime_apply_session executable"
    )
