from __future__ import annotations

from collections import Counter
import hashlib
import json
import shutil
from pathlib import Path

from microcosm_core.validators.acceptance import _sha256_file
from microcosm_core.validators.fixture_freshness import run_fixture_freshness


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_SUPPORT = MICROCOSM_ROOT / "core/preflight_support"
READINESS = PREFLIGHT_SUPPORT / "organ_fixture_validator_readiness_v1.json"
NEGATIVE_MATRIX = PREFLIGHT_SUPPORT / "fixture_negative_case_matrix_v1.json"
MISSION_DAG = PREFLIGHT_SUPPORT / "microcosm_rebuild_mission_graph_v1.json"
RECEIPT_COVERAGE = PREFLIGHT_SUPPORT / "validator_receipt_coverage_map_v1.json"


def _accepted_registry_rows(root: Path = MICROCOSM_ROOT) -> list[dict[str, object]]:
    registry = json.loads((root / "core/organ_registry.json").read_text(encoding="utf-8"))
    return [
        row
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]


def _accepted_organs_from_registry(root: Path = MICROCOSM_ROOT) -> list[str]:
    return [str(row["organ_id"]) for row in _accepted_registry_rows(root)]


def _expected_disposition_counts(
    rows: list[dict[str, object]],
) -> Counter[str]:
    return Counter(str(row["real_substrate_disposition"]) for row in rows)


def _source_body_import_expectations(
    public_root: Path,
    accepted_rows: list[dict[str, object]],
) -> dict[str, object]:
    organ_ids: list[str] = []
    body_material_count = 0
    source_manifest_ref_count = 0
    for row in accepted_rows:
        organ_id = str(row["organ_id"])
        manifest_path = (
            public_root
            / "core/fixture_manifests"
            / f"{organ_id}.fixture_manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_open = manifest.get("source_open_body_imports")
        if not isinstance(source_open, dict):
            continue
        organ_ids.append(organ_id)
        body_count = source_open.get("body_material_count") or manifest.get(
            "body_copied_material_count"
        )
        if not isinstance(body_count, int):
            body_count = len(source_open.get("body_material_ids", []))
        body_material_count += body_count
        source_manifest_refs = source_open.get("source_manifest_refs", [])
        source_manifest_ref_count += (
            len(source_manifest_refs) if isinstance(source_manifest_refs, list) else 0
        )
    return {
        "organ_ids": organ_ids,
        "body_material_count": body_material_count,
        "source_manifest_ref_count": source_manifest_ref_count,
    }


def _copy_public_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "examples", public_root / "examples")
    shutil.copytree(MICROCOSM_ROOT / "fixtures", public_root / "fixtures")
    shutil.copytree(MICROCOSM_ROOT / "receipts", public_root / "receipts")
    return public_root


def test_acceptance_sha256_file_streams_without_path_read_bytes(
    tmp_path: Path, monkeypatch
) -> None:
    fixture_file = tmp_path / "large_target.py"
    body = (b"public-source-line\n" * 2048) + b"tail\n"
    fixture_file.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path) -> bytes:
        if self == fixture_file:
            raise AssertionError("acceptance digest should stream the target file")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert _sha256_file(fixture_file) == hashlib.sha256(body).hexdigest()


def test_first_wave_acceptance_plan_records_bounded_lean_and_prediction_witnesses() -> None:
    acceptance = json.loads(
        (MICROCOSM_ROOT / "core/acceptance/first_wave_acceptance.json").read_text(
            encoding="utf-8"
        )
    )
    expected_organs = _accepted_organs_from_registry()

    assert acceptance["status"] == "accepted_runtime_spine_verifier_lab_kernel_bound"
    assert len(acceptance["accepted_current_authority_organs"]) == len(expected_organs)
    assert [
        row["organ_id"] for row in acceptance["accepted_current_authority_organs"]
    ] == expected_organs
    assert all(
        row.get("real_substrate_disposition")
        in {
            "real_substrate_capsule",
            "retained_regression_validator",
        }
        for row in acceptance["accepted_current_authority_organs"]
    )
    synthetic_rows = [
        row
        for row in acceptance["accepted_current_authority_organs"]
        if row.get("real_substrate_disposition") == "retained_regression_validator"
    ]
    assert [row["organ_id"] for row in synthetic_rows] == [
        "agent_benchmark_integrity_anti_gaming_replay",
        "agent_monitor_redteam_falsification_replay",
        "agent_sabotage_scheming_monitor_replay",
    ]
    assert all(
        row["synthetic_acceptance_disposition"]["disposition"]
        == "retained_regression_validator"
        for row in synthetic_rows
    )
    assert acceptance["deferred_organs"] == []
    assert acceptance["lean_lake_authorized"] == "bounded_public_witness_only"
    assert acceptance["release_authorized"] is False
    assert acceptance["hosted_public_authorized"] is False
    assert acceptance["publication_authorized"] is False
    assert acceptance["recipient_work_authorized"] is False
    assert acceptance["provider_calls_authorized"] is False
    assert acceptance["trading_or_financial_advice_authorized"] is False
    assert acceptance["private_data_equivalence_authorized"] is False
    assert "./bootstrap.sh" in acceptance["acceptance_commands"]
    assert (
        "./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe.json"
        not in acceptance["acceptance_commands"]
    )


def test_acceptance_summary_records_runtime_spine_with_bounded_lean_authority(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    accepted_rows = _accepted_registry_rows(public_root)
    expected_organs = [str(row["organ_id"]) for row in accepted_rows]
    expected_evidence_counts = dict(
        Counter(str(row["evidence_class"]) for row in accepted_rows)
    )
    expected_truth_counts = Counter(
        str(row["truth_accounting_bucket"]) for row in accepted_rows
    )
    expected_disposition_counts = _expected_disposition_counts(accepted_rows)
    expected_source_bodies = _source_body_import_expectations(public_root, accepted_rows)
    expected_progress_count = sum(
        1 for row in accepted_rows if row.get("counts_as_real_substrate_progress")
    )
    run_fixture_freshness(
        READINESS,
        NEGATIVE_MATRIX,
        MISSION_DAG,
        RECEIPT_COVERAGE,
        public_root / "receipts/preflight/fixture_runner_freshness.json",
        command="pytest",
    )
    summary = json.loads(
        (public_root / "receipts/first_wave/acceptance_summary.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["status"] == "pass"
    assert summary["acceptance_summary_blockers"] == []
    assert summary["accepted_count"] == len(expected_organs)
    assert summary["accepted_current_authority_count"] == len(expected_organs)
    assert summary["accepted_count_is_product_progress"] is False
    assert summary["truth_accounting"]["accepted_count_is_product_progress"] is False
    assert (
        summary["truth_accounting"]["accepted_current_authority_is_evidence_strength"]
        is False
    )
    assert summary["truth_accounting"]["real_substrate_progress_count"] == (
        expected_progress_count
    )
    assert summary["truth_accounting"]["non_progress_accepted_count"] == (
        len(expected_organs) - expected_progress_count
    )
    assert summary["truth_accounting"]["real_runtime_receipt_count"] == (
        expected_truth_counts.get("real_runtime_receipt", 0)
    )
    assert summary["truth_accounting"]["copied_non_secret_macro_body_count"] == (
        expected_truth_counts.get("copied_non_secret_macro_body", 0)
    )
    assert summary["truth_accounting"]["source_faithful_refactor_count"] == (
        expected_truth_counts.get("source_faithful_refactor", 0)
    )
    assert summary["truth_accounting"]["real_import_validation_count"] == (
        expected_truth_counts.get("real_import_validation", 0)
    )
    assert summary["truth_accounting"]["regression_negative_fixture_count"] == (
        expected_truth_counts.get("regression_negative_fixture", 0)
    )
    assert summary["truth_accounting"]["evidence_class_counts"] == (
        expected_evidence_counts
    )
    disposition_coverage = summary["disposition_coverage"]
    assert disposition_coverage == summary["truth_accounting"][
        "disposition_coverage"
    ]
    assert disposition_coverage["status"] == "pass"
    assert disposition_coverage["covered_count"] == len(expected_organs)
    assert disposition_coverage["synthetic_accepted_count"] == 3
    assert disposition_coverage["disposition_counts"] == dict(
        sorted(expected_disposition_counts.items())
    )
    assert (
        disposition_coverage["missing_synthetic_acceptance_dispositions"] == []
    )
    assert (
        disposition_coverage["invalid_synthetic_acceptance_disposition"] == []
    )
    assert (
        disposition_coverage["synthetic_acceptance_progress_flag_mismatch"] == []
    )
    source_body_imports = summary["source_body_imports"]
    assert source_body_imports == summary["truth_accounting"]["source_body_imports"]
    assert source_body_imports["status"] == "pass"
    assert source_body_imports["source_body_import_organ_count"] == len(
        expected_source_bodies["organ_ids"]
    )
    assert source_body_imports["body_material_count"] == expected_source_bodies[
        "body_material_count"
    ]
    assert source_body_imports["source_manifest_ref_count"] == expected_source_bodies[
        "source_manifest_ref_count"
    ]
    assert source_body_imports["missing_source_manifest_refs"] == []
    assert source_body_imports["body_in_receipt"] is False
    source_rows = {row["organ_id"]: row for row in source_body_imports["rows"]}
    assert source_rows["agent_route_observability_runtime"][
        "body_material_count"
    ] == 8
    assert source_rows["macro_projection_import_protocol"][
        "body_material_count"
    ] == 177
    assert summary["source_module_manifest_coverage"][
        "source_manifest_ref_count"
    ] == source_body_imports["source_manifest_ref_count"]
    evidence_by_organ = {
        row["organ_id"]: row["truth_accounting_bucket"]
        for row in summary["truth_accounting"]["accepted_current_authority_evidence"]
    }
    assert (
        evidence_by_organ["research_replication_rubric_artifact_replay"]
        == "source_faithful_refactor"
    )
    assert evidence_by_organ["world_model_projection_drift_control_room"] == (
        "real_import_validation"
    )
    assert evidence_by_organ["spatial_world_model_counterfactual_simulation_replay"] == (
        "real_runtime_receipt"
    )
    assert evidence_by_organ[
        "mechanistic_interpretability_circuit_attribution_replay"
    ] == "real_import_validation"
    assert (
        evidence_by_organ["agentic_vulnerability_discovery_patch_proof_replay"]
        == "source_faithful_refactor"
    )
    assert evidence_by_organ["mcp_tool_authority_replay"] == "source_faithful_refactor"
    assert (
        evidence_by_organ["belief_state_process_reward_replay"]
        == "source_faithful_refactor"
    )
    assert (
        evidence_by_organ["agent_sandbox_policy_escape_replay"]
        == "source_faithful_refactor"
    )
    assert evidence_by_organ["mission_transaction_work_spine"] == "source_faithful_refactor"
    assert evidence_by_organ["bridge_phase_continuity_runtime"] == (
        "real_import_validation"
    )
    assert evidence_by_organ["macro_projection_import_protocol"] == (
        "copied_non_secret_macro_body"
    )
    assert evidence_by_organ["formal_math_lean_proof_witness"] == "real_runtime_receipt"
    assert summary["accepted_current_authority_organs"] == expected_organs
    assert summary["deferred_organs"] == []
    assert summary["lean_lake_authorized"] == "bounded_public_witness_only"
    assert summary["release_authorized"] is False
    assert summary["trading_or_financial_advice_authorized"] is False
    assert summary["private_data_equivalence_authorized"] is False
