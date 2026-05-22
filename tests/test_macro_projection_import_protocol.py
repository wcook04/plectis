from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.macro_projection_import_protocol import (
    EXPECTED_NEGATIVE_CASES,
    preview_import_plan,
    run,
    run_projection_bundle,
    validate_import_plan,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/macro_projection_import_protocol/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
)
DEPENDENCY_PREFLIGHT_RECEIPT = (
    MICROCOSM_ROOT / "receipts/preflight/dependency_preflight.json"
)


def _copy_dependency_preflight_receipt(public_root: Path) -> Path:
    receipt = public_root / "receipts/preflight/dependency_preflight.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEPENDENCY_PREFLIGHT_RECEIPT, receipt)
    return receipt


def _align_organ_registry_to_dependency_preflight(public_root: Path) -> None:
    receipt = json.loads(
        (public_root / "receipts/preflight/dependency_preflight.json").read_text(
            encoding="utf-8"
        )
    )
    expected_count = receipt["organ_lifecycle_coverage"]["coverage_counts"][
        "accepted_organ_count"
    ]
    registry_path = public_root / "core/organ_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    accepted_rows = [
        row
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]
    keep_ids = {row["organ_id"] for row in accepted_rows[:expected_count]}
    registry["implemented_organs"] = [
        row
        for row in registry["implemented_organs"]
        if row.get("status") != "accepted_current_authority" or row["organ_id"] in keep_ids
    ]
    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _copy_macro_projection_public_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/macro_projection_import_protocol",
        public_root / "fixtures/first_wave/macro_projection_import_protocol",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/macro_projection_import_protocol",
        public_root / "examples/macro_projection_import_protocol",
    )
    _copy_dependency_preflight_receipt(public_root)
    _align_organ_registry_to_dependency_preflight(public_root)
    return public_root


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


def test_macro_projection_import_protocol_observes_negative_cases(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        tmp_path / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/macro_projection_import_protocol_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["projection_cell_count"] == 3
    assert result["ready_projection_cell_count"] == 3
    assert result["blocked_projection_cell_count"] == 0
    assert result["source_ref_count"] >= 2
    assert result["public_replacement_ref_count"] >= 2
    assert result["validation_ref_count"] >= 2
    assert result["public_safe_body_material_count"] == 2
    assert result["public_safe_body_import_status"] == "pass"
    assert result["standalone_release_status"] == "pass"
    assert result["runtime_dependency_status"] == "pass"
    assert result["dependency_preflight_gate_status"] == "pass"
    assert result["dependency_preflight_receipt_ref"] == (
        "receipts/preflight/dependency_preflight.json"
    )
    assert result["organ_lifecycle_coverage_status"] == "pass"
    assert result["organ_lifecycle_coverage_counts"]["accepted_organ_count"] == 45
    assert result["private_runtime_dependency_count"] == 0
    assert result["flagship_tranche_status"] == "pass"
    assert result["flagship_tranche_lane_count"] == 6
    assert result["flagship_tranche_pattern_count"] >= 20
    assert result["authority_ceiling"]["private_source_bodies_exported"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["projection_board"]["next_best_lane"] == "real_substrate_import_tranche"
    assert result["projection_board"]["intake_board_ref"] == "projection_import_intake_board.json"
    assert result["projection_board"]["standalone_release_board_embedded"] is True
    assert result["projection_board"]["flagship_tranche_board_embedded"] is True
    assert result["projection_intake_board"]["ready_cell_count"] == 3
    assert result["projection_intake_board"]["blocked_cell_count"] == 0
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_intake_board"]["landed_cell_count"] == 3
    assert result["projection_intake_board"]["projection_status_counts"] == {
        "public_replacement_landed": 1,
        "runtime_bridge_landed": 1,
        "self_hosted_status_protocol_landed": 1,
    }
    assert result["projection_intake_board"]["omitted_material_count"] == 2
    assert "public_macro_tool_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_proof_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 2
    assert result["projection_intake_board"]["public_safe_body_import_routes"] == {
        "public_safe_with_light_edits": 2
    }
    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    assert by_material["work_landing_tool_body_import"]["material_class"] == "public_macro_tool_body"
    assert by_material["lean_certificate_kernel_body_import"]["material_class"] == (
        "public_macro_proof_body"
    )
    assert by_material["work_landing_tool_body_import"]["classification_status"] == "pass"
    assert by_material["lean_certificate_kernel_body_import"]["classification_status"] == "pass"
    assert by_material["work_landing_tool_body_import"]["body_text_in_receipt_redacted"] is True
    assert by_material["lean_certificate_kernel_body_import"]["body_text_in_receipt_redacted"] is True
    assert result["projection_intake_board"]["negative_case_coverage_status"] == "pass"
    assert (
        result["projection_intake_board"]["projection_status_protocol"]["status_field"]
        == "projection_status"
    )
    by_cell = {
        row["cell_id"]: row for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["formal_math_readiness_extensions"]["copy_policy"] == (
        "public_safe_body_with_provenance_and_claim_ceiling"
    )
    assert by_cell["formal_math_readiness_extensions"]["public_safe_body_material_ids"] == [
        "lean_certificate_kernel_body_import"
    ]
    assert by_cell["projection_protocol_self_host"]["projection_status"] == (
        "self_hosted_status_protocol_landed"
    )
    assert by_cell["projection_protocol_self_host"]["action_required"] is False
    assert by_cell["projection_protocol_self_host"]["copy_policy"] == (
        "public_safe_body_with_provenance_and_claim_ceiling"
    )
    assert by_cell["projection_protocol_self_host"]["public_safe_body_material_ids"] == [
        "work_landing_tool_body_import"
    ]
    assert by_cell["runtime_reveal_import_bridge"]["projection_status"] == "runtime_bridge_landed"
    assert by_cell["runtime_reveal_import_bridge"]["copy_policy"] == (
        "metadata_fixture_receipt_ref_only"
    )
    release_board = result["standalone_release_board"]
    assert release_board["standalone_release_candidate"] is True
    assert release_board["dependency_preflight_gate_status"] == "pass"
    assert release_board["dependency_preflight_gate"]["status"] == "pass"
    assert release_board["dependency_preflight_gate"]["defect_count"] == 0
    assert release_board["organ_lifecycle_coverage_status"] == "pass"
    assert release_board["organ_lifecycle_coverage_counts"]["runtime_step_count"] == 45
    assert {
        row["check_id"]: row["status"]
        for row in release_board["severance_checks"]
    }["organ_lifecycle_coverage_preflight_passes"] == "pass"
    assert release_board["macro_origin_ref_policy"] == (
        "macro_origin_refs_are_provenance_only_not_runtime_dependencies"
    )
    assert release_board["macro_origin_refs_runtime_required"] is False
    assert release_board["private_runtime_dependency_count"] == 0
    assert release_board["blocked_runtime_dependencies"] == []
    assert "tools/meta/control/work_landing.py" in release_board["macro_origin_refs"]
    assert (
        "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/"
        "CertificateKernel.lean"
        in release_board["macro_origin_refs"]
    )
    assert all(not ref.startswith("state/") for ref in release_board["runtime_dependency_refs"])
    assert all(not ref.startswith("formal_math/") for ref in release_board["runtime_dependency_refs"])
    assert all(not ref.startswith("tools/meta/") for ref in release_board["runtime_dependency_refs"])
    assert any(
        receipt_ref.endswith("projection_import_intake_board.json")
        for receipt_ref in result["receipt_paths"]
    )
    flagship_board = result["flagship_tranche_board"]
    assert flagship_board["status"] == "pass"
    assert flagship_board["lane_ids"] == [
        "navigation_option_surface",
        "observatory_provenance_diagnostics",
        "pattern_doctrine_compiler",
        "proof_formal_kernel",
        "prover_evaluator_lab",
        "work_landing_governance",
    ]
    assert set(flagship_board["public_safe_body_material_ids"]) == {
        "lean_certificate_kernel_body_import",
        "work_landing_tool_body_import",
    }
    assert set(flagship_board["selected_pattern_ids"]) >= {
        "formal_math_verifier_trace_repair_loop_compound",
        "durable_agent_work_landing_replay_compound",
        "navigation_hologram_unified_route_plane",
        "pattern_deliverables_registry",
        "workingness_instrument",
    }
    assert flagship_board["private_runtime_dependency_count"] == 0
    assert flagship_board["macro_origin_refs_runtime_required"] is False
    assert flagship_board["cold_reader_answers"]["local_run_surface"].startswith("microcosm intake")
    for ref in flagship_board["release_artifact_refs"]:
        assert (MICROCOSM_ROOT / ref.split("::", 1)[0]).exists()


def test_macro_projection_import_protocol_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)

    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        public_root / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["standalone_release_board"]["standalone_release_candidate"] is True
    assert result["standalone_release_board"]["private_runtime_dependency_count"] == 0
    assert result["flagship_tranche_board"]["flagship_tranche_status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_macro_projection_release_severance_requires_lifecycle_preflight(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    receipt = public_root / "receipts/preflight/dependency_preflight.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    lifecycle = payload["organ_lifecycle_coverage"]
    lifecycle["status"] = "blocked"
    lifecycle["defect_count"] = 1
    lifecycle["defects"] = [
        {
            "defect_code": "missing_public_lens",
            "organ_id": "verifier_lab_execution_spine",
        }
    ]
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        public_root / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["runtime_dependency_status"] == "pass"
    assert result["standalone_release_status"] == "blocked"
    assert result["dependency_preflight_gate_status"] == "blocked"
    assert result["organ_lifecycle_coverage_status"] == "blocked"
    assert "MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_BLOCKED" in result["error_codes"]
    release_board = result["standalone_release_board"]
    assert release_board["dependency_preflight_gate"]["defects"][0]["defect_code"] == (
        "organ_lifecycle_coverage_blocked"
    )
    assert {
        row["check_id"]: row["status"]
        for row in release_board["severance_checks"]
    }["organ_lifecycle_coverage_preflight_passes"] == "blocked"


def test_macro_projection_release_severance_blocks_stale_lifecycle_counts(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    receipt = public_root / "receipts/preflight/dependency_preflight.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["organ_lifecycle_coverage"]["coverage_counts"]["surface_authority_row_count"] -= 1
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        public_root / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["dependency_preflight_gate_status"] == "blocked"
    assert result["organ_lifecycle_coverage_status"] == "pass"
    assert "MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_STALE" in result["error_codes"]
    defects = result["standalone_release_board"]["dependency_preflight_gate"]["defects"]
    assert {
        row["subject_id"]
        for row in defects
        if row["defect_code"] == "organ_lifecycle_coverage_stale_count"
    } == {"surface_authority_row_count"}


def test_macro_projection_exported_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_projection_import_bundle"
    assert result["bundle_id"] == "macro_projection_import_protocol_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["projection_cell_count"] == 3
    assert result["projection_intake_board"]["ready_cell_count"] == 3
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_board"]["release_authorized"] is False
    assert result["projection_board"]["private_data_equivalence_claim"] is False
    assert result["public_safe_body_material_count"] == 2
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 2
    assert result["standalone_release_status"] == "pass"
    assert result["standalone_release_board"]["macro_origin_refs_runtime_required"] is False
    assert result["standalone_release_board"]["private_runtime_dependency_count"] == 0
    assert result["flagship_tranche_board"]["lane_count"] == 6
    assert result["flagship_tranche_board"]["selected_pattern_count"] >= 20
    assert {
        row["material_id"]
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    } == {"work_landing_tool_body_import", "lean_certificate_kernel_body_import"}


def test_macro_projection_import_plan_preview_is_non_writing(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = preview_import_plan(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["schema_version"] == "macro_projection_import_intake_preview_v1"
    assert result["input_mode"] == "exported_projection_import_bundle"
    assert result["projection_intake_board"]["ready_cell_count"] == 3
    assert result["projection_intake_board"]["blocked_cell_count"] == 0
    assert result["projection_intake_board"]["projection_status_counts"][
        "self_hosted_status_protocol_landed"
    ] == 1
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_intake_board"]["release_authorized"] is False
    assert "pattern_metadata" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_tool_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_proof_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 2
    assert result["projection_intake_board"]["public_safe_body_import_classes"] == {
        "public_macro_proof_body": 1,
        "public_macro_tool_body": 1,
    }
    assert result["standalone_release_board"]["runtime_dependency_status"] == "pass"
    assert result["standalone_release_board"]["macro_origin_refs_runtime_required"] is False
    assert result["flagship_tranche_board"]["status"] == "pass"
    assert result["flagship_tranche_board"]["standalone_release_status"] == "pass"
    assert result["flagship_tranche_board"]["selected_pattern_count"] >= 20
    assert all(
        row["selected_pattern_ids"]
        for row in result["projection_intake_board"]["projection_cells"]
    )
    assert "receipt_paths" not in result


def test_public_safe_macro_tool_and_proof_bodies_are_importable_with_provenance(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["public_safe_body_material_count"] == 2
    assert result["public_safe_body_import_status"] == "pass"
    assert "MACRO_PROJECTION_PRIVATE_BODY_FORBIDDEN" not in result["error_codes"]
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["authority_ceiling"]["private_data_equivalence_claim"] is False
    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    assert by_material["work_landing_tool_body_import"]["route"] == "public_safe_with_light_edits"
    assert by_material["lean_certificate_kernel_body_import"]["route"] == (
        "public_safe_with_light_edits"
    )
    assert by_material["work_landing_tool_body_import"]["source_refs"][0] == (
        "tools/meta/control/work_landing.py"
    )
    assert by_material["lean_certificate_kernel_body_import"]["source_refs"] == [
        "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/CertificateKernel.lean"
    ]
    assert result["standalone_release_board"]["standalone_release_status"] == "pass"
    assert (
        "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/"
        "CertificateKernel.lean"
        not in result["standalone_release_board"]["runtime_dependency_refs"]
    )


def test_import_plan_rejects_missing_public_safe_body_material_id() -> None:
    result = validate_import_plan(
        {
            "plan_id": "missing_public_safe_body_material",
            "next_best_lane": "real_substrate_import_tranche",
            "proposed_cells": [
                {
                    "cell_id": "cell_with_missing_material",
                    "source_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
                    "target_refs": ["fixtures/example.json"],
                    "validation_refs": ["receipts/example.json"],
                    "public_safe_body_material_ids": ["missing_body_material"],
                },
                {
                    "cell_id": "cell_two",
                    "source_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
                    "target_refs": ["fixtures/example-two.json"],
                    "validation_refs": ["receipts/example-two.json"],
                },
                {
                    "cell_id": "cell_three",
                    "source_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
                    "target_refs": ["fixtures/example-three.json"],
                    "validation_refs": ["receipts/example-three.json"],
                },
            ],
        },
        public_safe_material_ids={"known_body_material"},
    )

    assert result["status"] == "blocked"
    assert result["blocking_finding_count"] == 1
    assert result["findings"][0]["error_code"] == (
        "MACRO_PROJECTION_PUBLIC_SAFE_BODY_MATERIAL_MISSING"
    )
