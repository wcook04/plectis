from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_computer_use_trace,
)
from microcosm_core.macro_tools.agent_session_attribution import (
    SCHEMA_VERSION as SESSION_ATTRIBUTION_SCHEMA_VERSION,
    attribute_sessions,
)
from microcosm_core.macro_tools.bridge_resume import (
    SCHEMA_VERSION as BRIDGE_DISPATCH_YIELD_RESUME_SCHEMA_VERSION,
    build_public_bridge_dispatch_yield_resume_view,
    load_public_bridge_dispatch_yield_resume_bundle,
)
from microcosm_core.macro_tools.continuation_packet import (
    SCHEMA_VERSION as CONTINUATION_PACKET_SCHEMA_VERSION,
    build_public_continuation_packet,
)
from microcosm_core.macro_tools.controller_heartbeat import (
    CONTROLLER_HEARTBEAT_FIELDS,
    CONTROLLER_HEARTBEAT_SCHEMA_VERSION,
    build_public_controller_heartbeat_view,
    count_sentences,
    load_public_controller_heartbeat_bundle,
)
from microcosm_core.organs.agent_route_observability_runtime import (
    COMPUTER_USE_EXPECTED_NEGATIVE_CASES,
    EXPORTED_COMPUTER_USE_ACTION_TRACE_BUNDLE_RECEIPT_PATH,
    EXPORTED_BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_RECEIPT_PATH,
    EXPORTED_CONTROLLER_HEARTBEAT_BUNDLE_RECEIPT_PATH,
    EXPORTED_MULTI_AGENT_FANIN_BUNDLE_RECEIPT_PATH,
    EXPORTED_OBSERVABILITY_BUNDLE_RECEIPT_PATH,
    EXPORTED_SESSION_ATTRIBUTION_BUNDLE_RECEIPT_PATH,
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    run,
    run_bridge_dispatch_yield_resume_bundle,
    run_computer_use_action_trace_bundle,
    run_controller_heartbeat_bundle,
    run_multi_agent_fanin_bundle,
    run_observability_bundle,
    run_session_attribution_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
OBS_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime/input"
OBS_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/exported_observability_bundle"
)
COMPUTER_USE_FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/agent_route_observability_runtime/"
    "computer_use_action_trace_replay_input"
)
COMPUTER_USE_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_computer_use_action_trace_bundle"
)
SESSION_ATTRIBUTION_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_session_attribution_bundle"
)
MULTI_AGENT_FANIN_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_multi_agent_fanin_replay_bundle"
)
BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_bridge_dispatch_yield_resume_bundle"
)
CONTROLLER_HEARTBEAT_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_controller_heartbeat_bundle"
)


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


def _field_floor() -> dict[str, list[str]]:
    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/agent_route_observability_runtime.fixture_manifest.json"
        ).read_text(encoding="utf-8")
    )
    return manifest["validator_contract_ratchet_v1"]["per_output_receipt_field_floor"]


def test_agent_route_observability_runtime_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    live_receipt_dir = MICROCOSM_ROOT / "receipts/first_wave/agent_route_observability_runtime"
    before = {
        path.name: path.read_text(encoding="utf-8")
        for path in live_receipt_dir.glob("*.json")
    } if live_receipt_dir.exists() else {}
    result = run(OBS_FIXTURE_INPUT, tmp_path / "receipts", command="pytest")

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert all(not Path(path).is_absolute() for path in result["receipt_paths"])
    assert result["route_compliance"]["actor_axis_mismatch_count"] == 1
    assert result["route_compliance"]["authority_rejection_count"] == 1
    assert result["hook_shadow_coverage"]["hook_shadow_case_count"] == 6
    assert result["hook_shadow_coverage"]["hook_shadow_repair_class_count"] == 6
    assert result["hook_shadow_coverage"]["missing_authority_count"] == 1
    assert result["hook_shadow_coverage"]["banned_route_intervention_count"] == 1
    assert result["hook_shadow_coverage"]["command_displacement_count"] == 1
    assert result["hook_shadow_coverage"]["live_state_read_denial_count"] == 1
    assert result["hook_shadow_coverage"]["over_budget_denial_count"] == 1
    assert result["hook_shadow_coverage"]["missing_hook_shadow_negative_cases"] == []
    assert result["route_lease_mode_control"]["kernel_bloat_before_direct_action_count"] == 1
    assert result["route_lease_mode_control"]["static_metadata_without_trace_feedback_count"] == 1
    assert result["debt_retirement"]["debt_retirement_count"] == 1
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]
    after = {
        path.name: path.read_text(encoding="utf-8")
        for path in live_receipt_dir.glob("*.json")
    } if live_receipt_dir.exists() else {}
    assert after == before


def test_agent_route_observability_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        public_root / "fixtures/first_wave/agent_route_observability_runtime",
    )

    result = run(
        public_root / "fixtures/first_wave/agent_route_observability_runtime/input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == EXPECTED_RECEIPT_PATHS
    for receipt_path in EXPECTED_RECEIPT_PATHS:
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "/private/var" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
        assert payload["missing_negative_cases"] == []
        assert set(payload["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
        for hit in payload["private_state_scan"]["hits"]:
            assert hit["body_redacted"] is True
            assert not Path(hit["path"]).is_absolute()


def test_agent_route_observability_receipts_satisfy_macro_field_floor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        public_root / "fixtures/first_wave/agent_route_observability_runtime",
    )
    run(
        public_root / "fixtures/first_wave/agent_route_observability_runtime/input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    for receipt_path, required_fields in _field_floor().items():
        payload = json.loads((public_root / receipt_path).read_text(encoding="utf-8"))
        missing = [field for field in required_fields if field not in payload]
        assert missing == []


def test_agent_route_observability_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_observability_bundle(
        OBS_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_observability_bundle"
    assert result["bundle_id"] == "public_agent_route_observability_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["metadata_projection_not_live_telemetry_authority"] is True
    assert result["authority_ceiling"]["live_operator_state_read"] is False
    assert result["authority_ceiling"]["provider_payload_read"] is False
    assert result["authority_ceiling"]["browser_hud_cockpit_state_read"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["route_event_count"] == 2
    assert result["agent_path_observation_count"] == 2
    assert result["session_diagnostic_count"] == 1
    assert result["hook_shadow_coverage"]["hook_shadow_coverage_status"] == (
        "public_metadata_coverage_only"
    )
    assert result["hook_shadow_coverage"]["hook_shadow_case_count"] == 4
    assert result["hook_shadow_coverage"]["hook_shadow_repair_class_count"] == 3
    assert result["hook_shadow_coverage"]["missing_authority_count"] == 1
    assert result["actor_axis_checks"]["actor_axis_check_count"] == 2
    assert result["debt_retirement"]["debt_retirement_count"] == 1
    assert result["process_audit_rows"]["process_audit_row_count"] == 2
    assert result["observability_policy"]["forbidden_authority_rejected"] is True
    assert result["consumed_route_lease_ids"] == [
        "lease_public_advisory_boundary",
        "lease_public_observability_runtime",
    ]
    assert all(not Path(path).is_absolute() for path in result["public_replacement_refs"])


def test_agent_route_observability_exported_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_observability_bundle(
        public_root
        / "examples/agent_route_observability_runtime/exported_observability_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [EXPORTED_OBSERVABILITY_BUNDLE_RECEIPT_PATH]
    receipt_file = public_root / EXPORTED_OBSERVABILITY_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    payload = json.loads(text)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_observability_bundle"
    assert payload["fixture_regression_required_elsewhere"] is True
    assert payload["private_state_scan"]["body_redacted"] is True
    assert payload["private_state_scan"]["blocking_hit_count"] == 0
    assert payload["expected_negative_cases"] == {}
    assert payload["metadata_projection_not_live_telemetry_authority"] is True
    assert payload["authority_ceiling"]["private_data_equivalence_claim"] is False
    assert payload["authority_ceiling"]["behavior_change_overclaims_allowed"] is False
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
    for hit in payload["private_state_scan"]["hits"]:
        assert hit["body_redacted"] is True
        assert not Path(hit["path"]).is_absolute()


def test_session_attribution_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_session_attribution_bundle(
        SESSION_ATTRIBUTION_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_session_attribution_bundle"
    assert result["bundle_id"] == "public_agent_session_attribution_runtime_example"
    assert result["session_attribution_view_schema"] == SESSION_ATTRIBUTION_SCHEMA_VERSION
    assert result["active_session_count"] == 5
    assert result["workledger_session_count"] == 4
    assert result["attributed_session_count"] == 6
    assert result["matched_session_count"] == 2
    assert result["self_session_id"] == "019dc1ab-cdef-7000-aaaa-000000000000"
    assert result["summary"]["by_attribution_status"] == {
        "matched": 2,
        "ats_only": 1,
        "workledger_only": 1,
        "unattributable": 1,
        "infrastructure": 1,
    }
    assert result["summary"]["by_liveness"] == {"live": 4, "recent": 2}
    assert result["authority_ceiling"]["live_home_session_logs_read"] is False
    assert result["authority_ceiling"]["raw_transcript_body_exported"] is False
    assert result["authority_ceiling"]["provider_payload_read"] is False
    assert result["authority_ceiling"]["account_session_state_exported"] is False
    assert result["private_state_scan"]["blocking_hit_count"] == 0
    assert result["session_input_validation"]["metadata_envelope_only"] is True
    assert result["attribution_policy"]["forbidden_authority_rejected"] is True
    assert result["expected_summary_validation"]["self_session_id"] == (
        "019dc1ab-cdef-7000-aaaa-000000000000"
    )
    assert all(row["raw_transcript_body_exported"] is False for row in result["session_rows"])
    assert all(row["transcript_path_exported"] is False for row in result["session_rows"])


def test_session_attribution_exported_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_session_attribution_bundle(
        public_root
        / "examples/agent_route_observability_runtime/exported_session_attribution_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [EXPORTED_SESSION_ATTRIBUTION_BUNDLE_RECEIPT_PATH]
    receipt_file = public_root / EXPORTED_SESSION_ATTRIBUTION_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "raw_transcript_body" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "account_session_state" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_session_attribution_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["raw_transcript_body_exported"] is False
    assert payload["provider_payload_exported"] is False
    assert payload["account_session_state_exported"] is False
    assert payload["private_state_scan"]["blocking_hit_count"] == 0
    assert payload["authority_ceiling"]["release_authorized"] is False
    for hit in payload["private_state_scan"]["hits"]:
        assert hit["body_redacted"] is True
        assert not Path(hit["path"]).is_absolute()


def test_multi_agent_fanin_replay_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_multi_agent_fanin_bundle(
        MULTI_AGENT_FANIN_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_multi_agent_fanin_replay_bundle"
    assert result["bundle_id"] == "public_multi_agent_fanin_replay_runtime_example"
    assert result["continuation_packet_schema"] == CONTINUATION_PACKET_SCHEMA_VERSION
    assert result["continuation_packet_count"] == 2
    assert result["worker_trace_count"] == 2
    assert result["fanin_join_count"] == 1
    assert result["wait_kinds"] == ["pipeline_signal", "resume_contract"]
    assert len(result["continuation_packet_fingerprints"]) == 2
    assert result["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    assert result["authority_ceiling"]["raw_worker_transcript_exported"] is False
    assert result["authority_ceiling"]["recipient_send_authorized"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["fanin_input_validation"]["metadata_envelope_only"] is True
    assert result["fanin_policy"]["forbidden_authority_rejected"] is True
    assert result["expected_summary_validation"]["actual_summary"][
        "continuation_packet_count"
    ] == 2
    assert result["body_import_verification"]["verification_mode"] == (
        "source_faithful_public_refactor"
    )
    assert result["body_import_verification"]["target_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/continuation_packet.py"
    )
    assert all(
        row["decision"] == "accepted" for row in result["worker_trace_decisions"]
    )


def test_multi_agent_fanin_replay_receipt_is_public_safe(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_multi_agent_fanin_bundle(
        public_root
        / "examples/agent_route_observability_runtime/exported_multi_agent_fanin_replay_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [EXPORTED_MULTI_AGENT_FANIN_BUNDLE_RECEIPT_PATH]
    receipt_file = public_root / EXPORTED_MULTI_AGENT_FANIN_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "raw_worker_transcript_body" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "account_session_state" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_multi_agent_fanin_replay_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["raw_worker_transcript_exported"] is False
    assert payload["provider_payload_exported"] is False
    assert payload["browser_hud_cockpit_state_exported"] is False
    assert payload["account_session_state_exported"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["authority_ceiling"]["release_authorized"] is False
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_bridge_dispatch_yield_resume_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_bridge_dispatch_yield_resume_bundle(
        BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_bridge_dispatch_yield_resume_bundle"
    assert result["bundle_id"] == "public_bridge_dispatch_yield_resume_runtime_example"
    assert result["bridge_resume_schema"] == BRIDGE_DISPATCH_YIELD_RESUME_SCHEMA_VERSION
    assert result["target_count"] == 2
    assert result["resume_job_count"] == 2
    assert result["trigger_written_count"] == 2
    assert result["no_send_trigger_count"] == 2
    assert result["skipped_dup_count"] == 1
    assert result["safe_to_inject_count"] == 1
    assert result["blocked_activity_count"] == 1
    assert result["controller_heartbeat_ref_count"] == 2
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["bridge_policy_validation"]["forbidden_authority_rejected"] is True
    assert result["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    assert result["authority_ceiling"]["host_app_auto_inject_authorized"] is False
    assert result["authority_ceiling"]["recipient_send_authorized"] is False
    assert all(row["submit"] is False for row in result["public_trigger_rows"])
    assert {
        row["reason"] for row in result["activity_reports"]
    } == {"already_injected", "no_delta"}
    assert result["body_import_verification"]["verification_mode"] == (
        "source_faithful_public_refactor"
    )
    assert result["body_import_verification"]["target_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/bridge_resume.py"
    )


def test_bridge_dispatch_yield_resume_receipt_is_public_safe(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_bridge_dispatch_yield_resume_bundle(
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_bridge_dispatch_yield_resume_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [
        EXPORTED_BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_RECEIPT_PATH
    ]
    receipt_file = public_root / EXPORTED_BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "raw_worker_transcript_body" not in _walk_keys(payload)
    assert "raw_bridge_transcript" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "account_session_state" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_bridge_dispatch_yield_resume_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["live_bridge_dispatch_authorized"] is False
    assert payload["host_app_auto_inject_authorized"] is False
    assert payload["recipient_send_authorized"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["authority_ceiling"]["release_authorized"] is False
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_bridge_resume_imports_public_macro_body_refactor() -> None:
    source = MICROCOSM_ROOT.parent / "tools/meta/bridge/bridge_resume.py"
    target = MICROCOSM_ROOT / "src/microcosm_core/macro_tools/bridge_resume.py"
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    view = build_public_bridge_dispatch_yield_resume_view(
        load_public_bridge_dispatch_yield_resume_bundle(
            BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT
        )
    )
    protocol = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/macro_projection_import_protocol/exported_projection_import_bundle/projection_protocol.json"
        ).read_text(encoding="utf-8")
    )
    by_material = {row["material_id"]: row for row in protocol["copied_material"]}
    material = by_material["bridge_resume_body_import"]

    assert target.is_file()
    assert source_digest != target_digest
    assert view["status"] == "pass"
    assert view["schema_version"] == BRIDGE_DISPATCH_YIELD_RESUME_SCHEMA_VERSION
    assert view["summary"]["trigger_written_count"] == 2
    assert view["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    assert material["body_import_verification"]["source_body_digest"] == (
        f"sha256:{source_digest}"
    )
    assert material["body_import_verification"]["target_body_digest"] == (
        f"sha256:{target_digest}"
    )
    assert material["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )


def test_controller_heartbeat_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_controller_heartbeat_bundle(
        CONTROLLER_HEARTBEAT_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_controller_heartbeat_bundle"
    assert result["bundle_id"] == "public_controller_heartbeat_runtime_example"
    assert result["controller_heartbeat_schema"] == CONTROLLER_HEARTBEAT_SCHEMA_VERSION
    assert result["heartbeat_count"] == 2
    assert result["valid_heartbeat_count"] == 2
    assert result["exact_5x5_count"] == 2
    assert result["heartbeat_ref_count"] == 2
    assert result["semantic_event_stable_count"] == 2
    assert result["semantic_event_changed_count"] == 2
    assert result["legacy_problem_regenerated_count"] == 1
    assert result["wrapped_schema_count"] == 2
    assert result["idempotent_wrap_count"] == 2
    assert result["dedupe_duplicate_count"] == 1
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["controller_heartbeat_policy"]["forbidden_authority_rejected"] is True
    assert result["authority_ceiling"]["seed_or_blackboard_read_authorized"] is False
    assert result["authority_ceiling"]["work_ledger_runtime_read_authorized"] is False
    assert result["authority_ceiling"]["provider_payload_read"] is False
    assert result["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert result["body_import_verification"]["target_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/controller_heartbeat.py"
    )


def test_controller_heartbeat_receipt_is_public_safe(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_controller_heartbeat_bundle(
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_controller_heartbeat_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [EXPORTED_CONTROLLER_HEARTBEAT_BUNDLE_RECEIPT_PATH]
    receipt_file = public_root / EXPORTED_CONTROLLER_HEARTBEAT_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "seed_body" not in _walk_keys(payload)
    assert "mission_blackboard_body" not in _walk_keys(payload)
    assert "work_ledger_runtime_body" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "account_session_state" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_controller_heartbeat_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["body_in_receipt"] is False
    assert payload["seed_or_blackboard_read_authorized"] is False
    assert payload["work_ledger_runtime_read_authorized"] is False
    assert payload["recipient_send_authorized"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["authority_ceiling"]["release_authorized"] is False
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_controller_heartbeat_imports_public_macro_body_refactor() -> None:
    source = MICROCOSM_ROOT.parent / "system/lib/controller_heartbeat.py"
    target = MICROCOSM_ROOT / "src/microcosm_core/macro_tools/controller_heartbeat.py"
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    view = build_public_controller_heartbeat_view(
        load_public_controller_heartbeat_bundle(CONTROLLER_HEARTBEAT_BUNDLE_INPUT)
    )
    protocol = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/macro_projection_import_protocol/exported_projection_import_bundle/projection_protocol.json"
        ).read_text(encoding="utf-8")
    )
    by_material = {row["material_id"]: row for row in protocol["copied_material"]}
    material = by_material["controller_heartbeat_body_import"]

    assert target.is_file()
    assert source_digest != target_digest
    assert view["status"] == "pass"
    assert view["controller_heartbeat_schema"] == CONTROLLER_HEARTBEAT_SCHEMA_VERSION
    assert view["summary"]["exact_5x5_count"] == 2
    assert view["summary"]["dedupe_duplicate_count"] == 1
    assert view["authority_ceiling"]["seed_or_blackboard_read_authorized"] is False
    for heartbeat in view["controller_heartbeats"]:
        assert all(
            count_sentences(heartbeat[field]) == 5
            for field in CONTROLLER_HEARTBEAT_FIELDS
        )
    assert material["body_import_verification"]["source_body_digest"] == (
        f"sha256:{source_digest}"
    )
    assert material["body_import_verification"]["target_body_digest"] == (
        f"sha256:{target_digest}"
    )
    assert material["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )


def test_continuation_packet_imports_public_macro_body_refactor() -> None:
    source = MICROCOSM_ROOT.parent / "system/lib/continuation_packet.py"
    target = MICROCOSM_ROOT / "src/microcosm_core/macro_tools/continuation_packet.py"
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()

    packet = build_public_continuation_packet(
        wait_kind="resume_contract",
        artifact_dir=(
            "examples/agent_route_observability_runtime/"
            "exported_multi_agent_fanin_replay_bundle/demo"
        ),
        source_context={
            "current_task_id": "multi_agent_handoff_fanin_replay_compound",
            "context_refs": [
                "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json#multi_agent_handoff_fanin_replay_compound"
            ],
        },
        generated_at="2026-05-24T03:55:00+00:00",
    )
    protocol = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/macro_projection_import_protocol/exported_projection_import_bundle/projection_protocol.json"
        ).read_text(encoding="utf-8")
    )
    by_material = {row["material_id"]: row for row in protocol["copied_material"]}
    material = by_material["continuation_packet_body_import"]

    assert target.is_file()
    assert source_digest != target_digest
    assert packet["schema_version"] == CONTINUATION_PACKET_SCHEMA_VERSION
    assert packet["wait_kind"] == "resume_contract"
    assert packet["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    assert material["body_import_verification"]["source_body_digest"] == (
        f"sha256:{source_digest}"
    )
    assert material["body_import_verification"]["target_body_digest"] == (
        f"sha256:{target_digest}"
    )
    assert material["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )


def test_computer_use_action_trace_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run_computer_use_action_trace_bundle(
        COMPUTER_USE_FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(
        COMPUTER_USE_EXPECTED_NEGATIVE_CASES
    )
    assert result["missing_negative_cases"] == []
    assert result["episode_count"] == 4
    assert result["observation_count"] == 6
    assert result["action_count"] == 8
    assert result["authority_verdict_count"] == 8
    assert result["state_transition_count"] == 8
    assert result["recovery_receipt_count"] == 1
    assert result["cold_replay_pass_count"] == 4
    assert result["block_count"] == 1
    assert result["authority_ceiling"]["live_browser_control_authorized"] is False
    assert result["authority_ceiling"]["credential_entry_authorized"] is False
    for codes in COMPUTER_USE_EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_computer_use_action_trace_receipt_is_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        public_root / "fixtures/first_wave/agent_route_observability_runtime",
    )

    result = run_computer_use_action_trace_bundle(
        public_root
        / "fixtures/first_wave/agent_route_observability_runtime/"
        "computer_use_action_trace_replay_input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    receipt_file = public_root / result["receipt_paths"][0]
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "raw_screenshot_body" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "hidden_screen_state" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
    redacted_findings = [
        finding for finding in payload["findings"] if finding.get("body_redacted") is True
    ]
    assert redacted_findings
    assert all(
        finding["subject_kind"] == "computer_use_negative_case"
        for finding in redacted_findings
    )
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_computer_use_action_trace_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_computer_use_action_trace_bundle(
        COMPUTER_USE_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_computer_use_action_trace_bundle"
    assert result["bundle_id"] == (
        "public_computer_use_action_trace_replay_runtime_example"
    )
    assert result["receipt_paths"][0].endswith(
        EXPORTED_COMPUTER_USE_ACTION_TRACE_BUNDLE_RECEIPT_PATH
    )
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["episode_count"] == 4
    assert result["action_count"] == 8
    assert set(result["action_kinds"]) == {
        "click",
        "edit_text_record",
        "navigate",
        "select",
        "type",
        "wait",
    }
    assert result["authority_ceiling"]["benchmark_score_claim_authorized"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "public_replacement_refs" not in result
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == result["action_count"]
    assert result["public_agent_execution_trace"]["summary"]["action_kind_counts"] == {
        "click": 2,
        "edit_text_record": 1,
        "navigate": 1,
        "select": 1,
        "type": 2,
        "wait": 1,
    }
    assert result["body_import_verification"]["verification_mode"] == (
        "source_faithful_public_refactor"
    )


def test_computer_use_action_trace_imports_public_agent_execution_trace_refactor() -> None:
    protocol = json.loads(
        (COMPUTER_USE_BUNDLE_INPUT / "projection_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    assert "body_redacted" not in protocol
    assert "public_replacement_refs" not in protocol
    assert "omitted_private_material" not in protocol
    assert protocol["body_import_status"] == "source_faithful_public_refactor_landed"
    assert protocol["body_import_verification"]["verification_mode"] == (
        "source_faithful_public_refactor"
    )
    assert "system/lib/agent_execution_trace.py" in protocol["source_refs"]
    assert (
        "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
        in protocol["target_refs"]
    )

    trace = build_public_computer_use_trace(COMPUTER_USE_BUNDLE_INPUT)
    assert trace["status"] == "pass"
    assert trace["source_faithful_refactor"]["source_ref"] == (
        "system/lib/agent_execution_trace.py"
    )
    assert trace["source_faithful_refactor"]["verification_mode"] == (
        "source_faithful_public_refactor"
    )
    assert trace["authority_ceiling"]["live_home_session_logs_read"] is False
    assert trace["authority_ceiling"]["provider_payload_read"] is False
    assert trace["audit"]["coverage"] == {
        "action_observation_coverage": True,
        "authority_verdict_coverage": True,
        "state_transition_coverage": True,
        "cold_replay_coverage": True,
        "body_in_receipt": False,
    }
    assert trace["span_count"] == 8
    assert all(
        span["source_ref"] == "computer_use_action_trace_bundle"
        for span in trace["spans"]
    )


def test_session_attribution_imports_exact_public_macro_body() -> None:
    source = MICROCOSM_ROOT.parent / "system/lib/agent_session_attribution.py"
    target = MICROCOSM_ROOT / "src/microcosm_core/macro_tools/agent_session_attribution.py"
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    ats = json.loads((SESSION_ATTRIBUTION_BUNDLE_INPUT / "ats_active_sessions.json").read_text())
    work_ledger = json.loads(
        (SESSION_ATTRIBUTION_BUNDLE_INPUT / "work_ledger_status.json").read_text()
    )

    view = attribute_sessions(
        ats_active_sessions=ats["active_sessions"],
        work_ledger_status=work_ledger,
    )

    assert target.is_file()
    assert source_digest == target_digest
    assert view["schema_version"] == SESSION_ATTRIBUTION_SCHEMA_VERSION
    assert view["summary"]["total"] >= 5
