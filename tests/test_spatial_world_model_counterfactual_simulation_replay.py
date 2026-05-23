from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_simulation_bundle,
)
from microcosm_core.public_payload_boundary import SOURCE_OPEN_BODY_POLICY


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/spatial_world_model_counterfactual_simulation_replay/"
    "exported_spatial_world_model_simulation_bundle"
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


def test_spatial_world_model_counterfactual_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path
        / "receipts/first_wave/spatial_world_model_counterfactual_simulation_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "spatial_world_model_counterfactual_simulation_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["selected_route_id"] == "spatial_world_model_counterfactual_simulation_replay"
    assert result["simulation_summary"]["scene_state_count"] == 6
    assert result["simulation_summary"]["replay_count"] == 6
    assert result["simulation_summary"]["transition_diff_count"] == 6
    assert result["simulation_summary"]["oracle_state_check_count"] == 6
    assert result["simulation_summary"]["sensor_packet_ref_count"] == 12
    assert result["negative_case_summary"]["expected_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["observed_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["authority_ceiling"]["private_video_exported"] is False
    assert result["authority_ceiling"]["raw_sensor_data_exported"] is False
    assert result["authority_ceiling"]["live_robot_operation_authorized"] is False
    assert result["authority_ceiling"]["live_av_operation_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert result["unsafe_payload_bodies_in_receipt"] is False
    assert (
        result["payload_boundary"]["boundary_id"]
        == "spatial_world_model_counterfactual_simulation_replay_payload_boundary"
    )
    assert result["safe_to_show"]["unsafe_payload_bodies_absent"] is True
    assert all(
        row["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
        for row in result["counterfactual_replays"]
    )
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in result["counterfactual_replays"]
    )
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        assert result["negative_case_summary"]["observed_codes"][case_id] == codes


def test_spatial_world_model_counterfactual_replay_receipts_are_public_relative_and_payload_bounded(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay",
        public_root
        / "fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay/input",
        public_root
        / "receipts/first_wave/spatial_world_model_counterfactual_simulation_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        keys = _walk_keys(json.loads(text))
        assert "private_video_body" not in keys
        assert "raw_sensor_payload" not in keys
        assert "gps_trace_body" not in keys
        assert "body_redacted" not in keys
        assert "private_state_scan" not in keys


def test_spatial_world_model_counterfactual_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_simulation_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "spatial_world_model_counterfactual_simulation_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_spatial_world_model_simulation_bundle"
    assert result["selected_route_id"] == "spatial_world_model_counterfactual_simulation_replay"
    assert result["simulation_summary"]["replay_count"] == 6
    assert result["negative_case_summary"]["expected_negative_case_count"] == 0
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["finding_count"] == 0
    assert result["authority_ceiling"]["generated_video_authority_authorized"] is False
    assert result["authority_ceiling"]["benchmark_score_claim_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert result["unsafe_payload_bodies_in_receipt"] is False
    assert (
        result["payload_boundary"]["boundary_id"]
        == "spatial_world_model_counterfactual_simulation_replay_payload_boundary"
    )
    encoded = json.dumps(result, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "private_state_scan" not in encoded
