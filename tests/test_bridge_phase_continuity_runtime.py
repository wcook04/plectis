from __future__ import annotations

import json
from pathlib import Path

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
    assert result["authority_ceiling"]["live_bridge_transport_authorized"] is False

    for receipt_rel in bridge_runtime.EXPECTED_RECEIPT_PATHS:
        receipt = _load_json(out_dir / Path(receipt_rel).name)
        assert REQUIRED_RECEIPT_FIELDS <= set(receipt)
        assert receipt["status"] == "pass"
        assert receipt["receipt_path"] == receipt_rel
        assert receipt["receipt_paths"] == bridge_runtime.EXPECTED_RECEIPT_PATHS
        assert receipt["private_state_scan"]["forbidden_output_fields_omitted"] is True


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
