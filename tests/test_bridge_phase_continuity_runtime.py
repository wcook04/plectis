from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from microcosm_core import cli
from microcosm_core.organs import bridge_phase_continuity_runtime as bridge_runtime


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/second_wave/bridge_phase_continuity_runtime/input"

REQUIRED_RECEIPT_FIELDS = {
    "schema_version",
    "checker_id",
    "organ_id",
    "fixture_id",
    "validator_id",
    "command",
    "status",
    "source_pattern_ids",
    "continuation_packet_status",
    "heartbeat_status",
    "resource_pressure_decision",
    "resume_once_status",
    "duplicate_resume_rejection",
    "closeout_transition_path",
    "expected_negative_cases",
    "observed_negative_cases",
    "error_codes",
    "acceptance_scope",
    "manifest_ref",
    "readiness_contract_ref",
    "negative_case_contract_ref",
    "required_parent_acceptance_refs",
    "dependency_preflight_receipt_ref",
    "synthetic_input_refs",
    "synthetic_fixture_gate_status",
    "fake_transport_fixture_summary",
    "worker_skip_receipt_status",
    "private_state_scan",
    "anti_claim",
    "authority_ceiling",
    "receipt_paths",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_keys(payload: object) -> list[str]:
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


def test_bridge_phase_continuity_runner_consumes_observe_apply_fixture(tmp_path: Path) -> None:
    out_dir = tmp_path / "bridge_phase_continuity_runtime"
    result = bridge_runtime.run(FIXTURE_INPUT, out_dir, command="pytest bridge continuity")

    assert result["status"] == "pass"
    assert result["organ_id"] == bridge_runtime.ORGAN_ID
    assert result["fixture_id"] == bridge_runtime.FIXTURE_ID
    assert result["observed_fixture_id"] == "observe_runtime_apply_session_bridge_continuity_v0"
    assert result["acceptance_scope"] == "observe_apply_fixture_consumption_only"
    assert result["receipt_paths"] == bridge_runtime.EXPECTED_RECEIPT_PATHS
    assert result["written_receipt_count"] == 5
    assert result["missing_negative_cases"] == []
    assert set(result["expected_negative_cases"]) == set(bridge_runtime.EXPECTED_NEGATIVE_CASES)
    assert result["private_state_scan"]["status"] == "pass"
    assert result["private_state_scan"]["blocking_hit_count"] == 0
    assert result["private_state_scan"]["scanned_path_count"] == 7
    assert result["authority_ceiling"]["live_bridge_transport_authorized"] is False

    for receipt_rel in bridge_runtime.EXPECTED_RECEIPT_PATHS:
        receipt = _load_json(out_dir / Path(receipt_rel).name)
        assert REQUIRED_RECEIPT_FIELDS <= set(receipt)
        assert receipt["status"] == "pass"
        assert receipt["receipt_path"] == receipt_rel
        assert receipt["receipt_paths"] == bridge_runtime.EXPECTED_RECEIPT_PATHS
        assert receipt["private_state_scan"]["forbidden_output_fields_omitted"] is True


def test_bridge_phase_continuity_runner_consumes_manifest_fake_transport_files(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "bridge_phase_continuity_runtime"
    result = bridge_runtime.run(FIXTURE_INPUT, out_dir, command="pytest bridge continuity")
    summary = result["fake_transport_fixture_summary"]

    assert summary["status"] == "pass"
    assert summary["input_file_count"] == 6
    assert summary["detached_job_count"] == 4
    assert summary["continuation_packet_count"] == 3
    assert summary["heartbeat_row_count"] == 3
    assert summary["resource_pressure_row_count"] == 2
    assert summary["worker_skip_receipt_count"] == 1
    assert summary["valid_job"] == {
        "status": "pass",
        "job_id": "synthetic_detached_job_001",
        "packet_id": "synthetic_packet_001",
        "transport": "fake_transport",
    }
    assert summary["missing_packet_rejected"] is True
    assert summary["missing_required_fields_rejected"] is True
    assert summary["duplicate_resume_rejected"] is True
    assert summary["heartbeat_fresh_count"] == 2
    assert summary["heartbeat_stale_count"] == 1
    assert summary["heartbeat_resume_authority_rejected"] is True
    assert summary["stale_heartbeat_rejected"] is True
    assert summary["resource_pressure_blocked"] is True
    assert summary["worker_skip_deduped_no_closeout"] is True
    assert summary["forbidden_class_ids_only"] is True
    assert set(summary["error_codes"]) >= {
        "CONTINUATION_PACKET_ALREADY_CONSUMED",
        "HEARTBEAT_NOT_RESUME_AUTHORITY",
        "MISSING_CONTINUATION_PACKET",
        "MISSING_CONTINUATION_PACKET_FIELDS",
        "RESOURCE_PRESSURE_DISPATCH_BLOCKED",
        "STALE_HEARTBEAT_LIVENESS_CLAIM",
    }

    continuation = _load_json(out_dir / "continuation_packet.json")
    heartbeat = _load_json(out_dir / "heartbeat.json")
    pressure = _load_json(out_dir / "resource_pressure.json")
    closeout = _load_json(out_dir / "closeout_transition.json")

    assert continuation["continuation_packet_status"]["fake_transport_job_id"] == (
        "synthetic_detached_job_001"
    )
    assert continuation["continuation_packet_status"]["missing_packet_rejected"] is True
    assert continuation["continuation_packet_status"][
        "missing_required_fields_rejected"
    ] is True
    assert heartbeat["heartbeat_status"]["fresh_count"] == 2
    assert heartbeat["heartbeat_status"]["stale_count"] == 1
    assert pressure["resource_pressure_decision"]["blocked_reason"] == (
        "capacity_budget_exceeded"
    )
    assert closeout["worker_skip_receipt_status"] == {
        "status": "pass",
        "claim_closeout_authorized": False,
        "deduped_noop_receipt": True,
    }


def test_bridge_phase_continuity_receipts_stay_public_safe(tmp_path: Path) -> None:
    out_dir = tmp_path / "bridge_phase_continuity_runtime"
    bridge_runtime.run(FIXTURE_INPUT, out_dir, command="pytest bridge continuity")

    serialized = "\n".join(
        (out_dir / Path(receipt_rel).name).read_text(encoding="utf-8")
        for receipt_rel in bridge_runtime.EXPECTED_RECEIPT_PATHS
    )
    keys = _walk_keys(json.loads((out_dir / "closeout_transition.json").read_text(encoding="utf-8")))

    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "matched_excerpt" not in serialized
    assert "provider_response_json" not in serialized
    assert "operator_thread_text" not in serialized
    assert "browser_storage_snapshot" not in serialized
    assert "body" not in keys
    assert "matched_excerpt" not in keys


def test_bridge_phase_continuity_cli_route_runs(tmp_path: Path) -> None:
    out_dir = tmp_path / "cli_receipts"
    exit_code = cli.main(
        [
            "bridge-phase-continuity-runtime",
            "run",
            "--input",
            FIXTURE_INPUT.as_posix(),
            "--out",
            out_dir.as_posix(),
        ]
    )

    assert exit_code == 0
    assert (out_dir / "continuation_packet.json").is_file()
    assert (out_dir / "heartbeat.json").is_file()
    assert (out_dir / "resource_pressure.json").is_file()
    assert (out_dir / "resume_receipt.json").is_file()
    assert (out_dir / "closeout_transition.json").is_file()


def test_bridge_phase_continuity_card_stdout_is_compact_and_keeps_full_receipts(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "card_receipts"

    exit_code = bridge_runtime.main(
        [
            "run",
            "--input",
            FIXTURE_INPUT.as_posix(),
            "--out",
            out_dir.as_posix(),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)
    full_receipt = _load_json(out_dir / "closeout_transition.json")

    assert exit_code == 0
    assert len(captured.encode("utf-8")) < 6000
    assert card["schema_version"] == bridge_runtime.CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["organ_id"] == bridge_runtime.ORGAN_ID
    assert card["fixture_id"] == bridge_runtime.FIXTURE_ID
    assert card["receipt_summary"]["written_receipt_count"] == 5
    assert card["receipt_summary"]["receipt_count"] == len(bridge_runtime.EXPECTED_RECEIPT_PATHS)
    assert card["receipt_summary"]["receipt_paths_exported"] is False
    assert card["bridge_continuity_summary"]["heartbeat_fresh_count"] == 2
    assert card["bridge_continuity_summary"]["heartbeat_stale_count"] == 1
    assert card["bridge_continuity_summary"]["resource_pressure_blocked"] is True
    assert card["bridge_continuity_summary"]["resource_dispatch_allowed"] is False
    assert card["bridge_continuity_summary"]["worker_skip_deduped_no_closeout"] is True
    assert card["fake_transport_summary"]["input_file_count"] == 6
    assert card["fake_transport_summary"]["manifest_input_refs_exported"] is False
    assert card["negative_case_coverage"]["expected_case_count"] == len(
        bridge_runtime.EXPECTED_NEGATIVE_CASES
    )
    assert card["negative_case_coverage"]["observed_case_count"] == len(
        bridge_runtime.EXPECTED_NEGATIVE_CASES
    )
    assert card["negative_case_coverage"]["missing_negative_cases"] == []
    assert card["private_state_scan_summary"]["blocking_hit_count"] == 0
    assert card["private_state_scan_summary"]["hits_exported"] is False
    assert card["authority_ceiling"]["live_bridge_transport_authorized"] is False
    assert card["no_export_guards"]["source_module_digest_results_exported"] is False

    card_keys = set(_walk_keys(card))
    assert "findings" not in card_keys
    assert "observed_negative_cases" not in card_keys
    assert "source_pattern_ids" not in card_keys
    assert "source_module_digest_results" not in card_keys
    assert "synthetic_input_refs" not in card_keys
    assert "receipt_paths" not in card_keys
    assert "receipt_path_map" not in card_keys
    assert "anti_claim" not in card_keys
    assert "hits" not in card_keys
    assert "scan_scope" not in card_keys

    assert full_receipt["status"] == "pass"
    assert full_receipt["receipt_paths"] == bridge_runtime.EXPECTED_RECEIPT_PATHS
    assert len(full_receipt["source_module_digest_results"]) == 5
    assert full_receipt["command"].endswith("--card")
