from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_lab_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/materials_chemistry_closed_loop_lab_safety_replay/"
    "exported_materials_lab_safety_bundle"
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


def test_materials_chemistry_lab_safety_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/materials_chemistry_closed_loop_lab_safety_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "materials_chemistry_closed_loop_lab_safety_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["selected_route_id"] == "materials_chemistry_closed_loop_lab_safety_replay"
    assert result["materials_lab_safety_summary"]["candidate_material_count"] == 4
    assert result["materials_lab_safety_summary"]["experiment_count"] == 4
    assert result["materials_lab_safety_summary"]["simulator_assay_count"] == 4
    assert result["materials_lab_safety_summary"]["active_learning_decision_count"] == 4
    assert result["materials_lab_safety_summary"]["wetlab_protocol_export_count"] == 0
    assert result["materials_lab_safety_summary"]["robot_command_count"] == 0
    assert result["negative_case_summary"]["expected_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["observed_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["authority_ceiling"]["wetlab_protocol_authorized"] is False
    assert result["authority_ceiling"]["hazardous_synthesis_authorized"] is False
    assert result["authority_ceiling"]["reagent_amounts_authorized"] is False
    assert result["authority_ceiling"]["robot_command_authorized"] is False
    assert result["authority_ceiling"]["discovery_claim_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        assert result["negative_case_summary"]["observed_codes"][case_id] == codes


def test_materials_chemistry_lab_safety_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay",
        public_root
        / "fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay/input",
        public_root / "receipts/first_wave/materials_chemistry_closed_loop_lab_safety_replay",
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
        assert "wetlab_step_body" not in keys
        assert "reagent_quantity_body" not in keys
        assert "robot_command_payload" not in keys
        assert "credential_secret" not in keys


def test_materials_chemistry_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_lab_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "materials_chemistry_closed_loop_lab_safety_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_materials_lab_safety_bundle"
    assert result["selected_route_id"] == "materials_chemistry_closed_loop_lab_safety_replay"
    assert result["materials_lab_safety_summary"]["experiment_count"] == 4
    assert result["negative_case_summary"]["expected_negative_case_count"] == 0
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["finding_count"] == 0
    assert result["authority_ceiling"]["simulator_only"] is True
    assert result["authority_ceiling"]["robot_command_authorized"] is False
    assert result["authority_ceiling"]["discovery_claim_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
