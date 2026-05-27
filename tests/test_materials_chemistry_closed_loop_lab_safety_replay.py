from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import materials_chemistry_closed_loop_lab_safety_replay
from microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
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
    assert result["body_import_status"] == "source_faithful_refactor_landed"
    assert result["body_import_classification"] == "source_faithful_refactor"
    assert result["body_import_verification"]["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["status"] == "pass"
    replay = result["public_lab_evolve_replay"]
    assert replay["status"] == "pass"
    assert replay["summary"]["replay_case_count"] == 4
    assert replay["summary"]["boundary_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert replay["summary"]["source_capsule_count"] == 12
    assert (
        "self-indexing-cognitive-substrate/src/idea_microcosm/"
        "lab_evolve_failure_replay_specimen.py"
    ) in replay["source_refs"]
    assert replay["body_in_receipt"] is False
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
        assert "private_state_scan" not in keys


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
    assert result["public_lab_evolve_replay"]["summary"]["replay_case_count"] == 4
    assert result["public_lab_evolve_replay"]["summary"]["boundary_case_count"] == 0
    assert result["body_import_status"] == "source_faithful_refactor_landed"
    assert result["body_import_verification"]["body_in_receipt"] is False
    assert result["negative_case_summary"]["expected_negative_case_count"] == 0
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["finding_count"] == 0
    assert result["authority_ceiling"]["simulator_only"] is True
    assert result["authority_ceiling"]["robot_command_authorized"] is False
    assert result["authority_ceiling"]["discovery_claim_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False


def test_materials_chemistry_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "materials_chemistry_closed_loop_lab_safety_replay"
    )
    args = [
        "run-lab-bundle",
        "--input",
        str(BUNDLE_INPUT),
        "--out",
        str(out),
        "--card",
    ]

    assert main(args) == 0
    first_card = json.loads(capsys.readouterr().out)
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["command_speed"]["receipt_reused"] is False
    assert first_card["command_speed"]["freshness_missing_path_count"] == 0
    assert first_card["command_speed"]["freshness_input_count"] == 10
    assert first_card["materials_lab_safety"]["candidate_material_count"] == 4
    assert first_card["materials_lab_safety"]["experiment_count"] == 4
    assert first_card["materials_lab_safety"]["simulator_assay_count"] == 4
    assert first_card["materials_lab_safety"]["wetlab_protocol_export_count"] == 0
    assert first_card["materials_lab_safety"]["robot_command_count"] == 0
    assert first_card["public_lab_evolve_replay"]["replay_case_count"] == 4
    assert first_card["public_lab_evolve_replay"]["boundary_case_count"] == 0
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["secret_exclusion_blocking_hit_count"] == 0
    assert "candidate_materials" not in _walk_keys(first_card)
    assert "experiments" not in _walk_keys(first_card)
    assert "simulator_assays" not in _walk_keys(first_card)
    assert "active_learning_decisions" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "authority_ceiling" not in _walk_keys(first_card)
    assert "anti_claim" not in _walk_keys(first_card)
    assert "wetlab_step_body" not in _walk_keys(first_card)
    assert "robot_command_payload" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        materials_chemistry_closed_loop_lab_safety_replay,
        "_build_result",
        fail_if_rebuilt,
    )

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
