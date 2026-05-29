from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.validators import dependency_preflight
from microcosm_core.validators.dependency_preflight import run_dependency_preflight


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_SUPPORT = MICROCOSM_ROOT / "core/preflight_support"
READINESS = PREFLIGHT_SUPPORT / "organ_fixture_validator_readiness_v1.json"
NEGATIVE_MATRIX = PREFLIGHT_SUPPORT / "fixture_negative_case_matrix_v1.json"


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


def _copy_public_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "fixtures", public_root / "fixtures")
    shutil.copytree(
        MICROCOSM_ROOT / "receipts/runtime_shell",
        public_root / "receipts/runtime_shell",
    )
    return public_root


def _accepted_organs_from_registry(public_root: Path) -> list[str]:
    registry = json.loads((public_root / "core/organ_registry.json").read_text(encoding="utf-8"))
    return [
        str(row["organ_id"])
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]


def test_dependency_preflight_passes_with_public_manifest_inputs(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    out = public_root / "receipts/preflight/dependency_preflight.json"
    expected_organs = _accepted_organs_from_registry(public_root)
    demoted_organs = list(dependency_preflight.PRODUCT_PATH_DEMOTED_ORGAN_IDS)
    public_authority = json.loads(
        (public_root / "receipts/runtime_shell/public_authority_map.json").read_text(
            encoding="utf-8"
        )
    )

    receipt = run_dependency_preflight(
        READINESS,
        NEGATIVE_MATRIX,
        out,
        command="pytest",
    )

    assert receipt["status"] == "pass"
    assert receipt["checked_organs"] == expected_organs
    assert receipt["blocked_dependency_count"] == 0
    assert receipt["blocked_dependency_codes"] == []
    coverage = receipt["organ_lifecycle_coverage"]
    assert coverage["status"] == "pass"
    assert coverage["defect_count"] == 0
    assert coverage["coverage_counts"] == {
        "accepted_organ_count": len(expected_organs),
        "runtime_step_count": len(expected_organs),
        "acceptance_plan_organ_count": len(expected_organs),
        "evidence_class_row_count": len(expected_organs),
        "public_authority_expected_organ_count": len(expected_organs) - len(demoted_organs),
        "demoted_drilldown_organ_count": len(demoted_organs),
        "organ_authority_row_count": len(public_authority["organ_authority"]),
        "surface_authority_row_count": len(public_authority["surface_authority"]),
        "fixture_check_count": len(expected_organs),
    }
    convergence = coverage["organ_lifecycle_convergence"]
    assert convergence["schema_version"] == "organ_lifecycle_convergence_v1"
    assert convergence["status"] == "pass"
    assert convergence["demoted_drilldown_organ_ids"] == [
        "mathematical_strategy_atlas_hypothesis_scorer",
        "agent_benchmark_integrity_anti_gaming_replay",
        "agent_monitor_redteam_falsification_replay",
        "agent_sabotage_scheming_monitor_replay",
    ]
    assert convergence["affected_consumer_surfaces"] == []
    assert convergence["changed_organ_ids"] == []
    assert convergence["false_positive_guard_result"] == "pass"
    assert convergence["incidental_receipt_churn_excluded"] is True
    assert convergence["release_authority"] is False
    assert convergence["proof_authority"] is False
    assert convergence["source_body_exported"] is False
    consumer_by_id = {
        row["surface_id"]: row for row in convergence["consumer_surfaces"]
    }
    assert consumer_by_id["runtime_steps"]["status"] == "pass"
    assert consumer_by_id["public_command_lens_rows"]["status"] == "pass"
    assert (
        "certificate_kernel_execution_lab"
        in consumer_by_id["runtime_steps"]["observed_organ_ids"]
    )
    assert consumer_by_id["public_authority_organ_rows"]["required_for_organ_ids"] == [
        organ_id
        for organ_id in receipt["checked_organs"]
        if organ_id
        not in {
            "mathematical_strategy_atlas_hypothesis_scorer",
            "agent_benchmark_integrity_anti_gaming_replay",
            "agent_monitor_redteam_falsification_replay",
            "agent_sabotage_scheming_monitor_replay",
        }
    ]
    assert "missing_public_lens" not in {
        defect["defect_id"] for defect in coverage["defects"]
    }
    grammar_check = next(
        row
        for row in receipt["fixture_precondition_checks"]
        if row["organ_id"] == "executable_doctrine_grammar"
    )
    assert grammar_check["input_source"] == "public_fixture_manifest"
    assert grammar_check["missing_fixture_inputs"] == []
    assert receipt["private_state_scan"]["body_redacted"] is True
    assert receipt["private_state_scan"]["blocking_hit_count"] == 0
    text = out.read_text(encoding="utf-8")
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(receipt)
    assert "body" not in _walk_keys(receipt)


def test_dependency_preflight_blocks_unsatisfied_accepted_dependency(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    readiness_copy = tmp_path / "readiness.json"
    payload = json.loads(READINESS.read_text(encoding="utf-8"))
    for row in payload["organ_readiness"]:
        if row["organ_id"] == "pattern_binding_contract":
            row["build_dependencies"] = ["missing_public_root_dependency"]
            break
    readiness_copy.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    receipt = run_dependency_preflight(
        readiness_copy,
        NEGATIVE_MATRIX,
        public_root / "receipts/preflight/dependency_preflight.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert receipt["blocked_dependency_count"] == 1
    assert receipt["blocked_dependency_codes"] == ["MISSING_ACCEPTED_BUILD_DEPENDENCY"]


def test_dependency_preflight_blocks_missing_public_lens(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    authority_path = public_root / "receipts/runtime_shell/public_authority_map.json"
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    authority["surface_authority"] = [
        row
        for row in authority["surface_authority"]
        if row["surface_id"] != "public_verifier_lab_execution_spine_lens"
    ]
    authority_path.write_text(
        json.dumps(authority, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    receipt = run_dependency_preflight(
        READINESS,
        NEGATIVE_MATRIX,
        public_root / "receipts/preflight/dependency_preflight.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "ORGAN_LIFECYCLE_COVERAGE_DEFECT" in receipt["blocked_dependency_codes"]
    coverage = receipt["organ_lifecycle_coverage"]
    defect_ids = {defect["defect_id"] for defect in coverage["defects"]}
    assert "missing_public_lens" in defect_ids
    assert "stale_surface_authority_count" in defect_ids
    missing_public_lens = [
        defect
        for defect in coverage["defects"]
        if defect["defect_id"] == "missing_public_lens"
    ]
    assert missing_public_lens == [
        {
            "defect_id": "missing_public_lens",
            "organ_id": "verifier_lab_execution_spine",
        }
    ]
    convergence = coverage["organ_lifecycle_convergence"]
    public_lens_contract = next(
        row
        for row in convergence["consumer_surfaces"]
        if row["surface_id"] == "public_command_lens_rows"
    )
    assert public_lens_contract["status"] == "blocked"
    assert public_lens_contract["missing_organ_ids"] == [
        "verifier_lab_execution_spine"
    ]
    assert convergence["affected_consumer_surfaces"] == ["public_command_lens_rows"]
    assert convergence["changed_organ_ids"] == ["verifier_lab_execution_spine"]


def test_dependency_preflight_names_missing_runtime_step_contract(
    tmp_path: Path, monkeypatch: Any
) -> None:
    public_root = _copy_public_tree(tmp_path)
    runtime_without_certificate = [
        organ_id
        for organ_id in dependency_preflight.ACCEPTED_ORGAN_IDS
        if organ_id != "certificate_kernel_execution_lab"
    ]
    monkeypatch.setattr(
        dependency_preflight,
        "ACCEPTED_ORGAN_IDS",
        runtime_without_certificate,
    )

    receipt = run_dependency_preflight(
        READINESS,
        NEGATIVE_MATRIX,
        public_root / "receipts/preflight/dependency_preflight.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    coverage = receipt["organ_lifecycle_coverage"]
    runtime_defect = next(
        defect
        for defect in coverage["defects"]
        if defect["defect_id"] == "accepted_without_runtime_step"
    )
    assert runtime_defect["organ_id"] == "certificate_kernel_execution_lab"
    runtime_contract = next(
        row
        for row in coverage["organ_lifecycle_convergence"]["consumer_surfaces"]
        if row["surface_id"] == "runtime_steps"
    )
    assert runtime_contract["status"] == "blocked"
    assert runtime_contract["missing_organ_ids"] == [
        "certificate_kernel_execution_lab"
    ]
    assert (
        "runtime_steps"
        in coverage["organ_lifecycle_convergence"]["affected_consumer_surfaces"]
    )


def test_dependency_preflight_convergence_ignores_unrelated_public_note(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_tree(tmp_path)
    note = public_root / "notes/operator_note.md"
    note.parent.mkdir(parents=True)
    note.write_text("not part of the public organ lifecycle contract\n", encoding="utf-8")

    receipt = run_dependency_preflight(
        READINESS,
        NEGATIVE_MATRIX,
        public_root / "receipts/preflight/dependency_preflight.json",
        command="pytest",
    )

    convergence = receipt["organ_lifecycle_coverage"]["organ_lifecycle_convergence"]
    assert receipt["status"] == "pass"
    assert convergence["status"] == "pass"
    assert convergence["affected_consumer_surfaces"] == []
    assert convergence["changed_organ_ids"] == []
    assert convergence["false_positive_guard_result"] == "pass"
