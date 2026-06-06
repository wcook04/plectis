from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core.validators.evidence_truth_floor import audit_evidence_truth_floor


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _copy_truth_floor_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "receipts/first_wave",
        public_root / "receipts/first_wave",
    )
    return public_root


def _set_evidence_class(public_root: Path, organ_id: str, evidence_class: str) -> None:
    registry_path = public_root / "core/organ_evidence_classes.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for row in registry["organ_evidence_classes"]:
        if row["organ_id"] == organ_id:
            row["evidence_class"] = evidence_class
            row["classification_basis"] = "test-local stale registry row"
            break
    else:
        raise AssertionError(f"missing organ evidence-class row: {organ_id}")
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _set_fixture_echo_registry_disposition(public_root: Path, organ_id: str) -> None:
    registry_path = public_root / "core/organ_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for row in registry["implemented_organs"]:
        if row["organ_id"] == organ_id:
            row["evidence_class"] = "fixture_echo_smoke"
            row["real_substrate_disposition"] = "retained_regression_validator"
            row["truth_accounting_bucket"] = "regression_negative_fixture"
            row["counts_as_real_substrate_progress"] = False
            row["synthetic_acceptance_disposition"] = {
                "disposition": "retained_regression_validator",
                "reason": "test-local fixture echo disposition",
            }
            break
    else:
        raise AssertionError(f"missing organ registry row: {organ_id}")
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _stage_fixture_echo_row(public_root: Path, organ_id: str) -> None:
    _set_evidence_class(public_root, organ_id, "fixture_echo_smoke")
    _set_fixture_echo_registry_disposition(public_root, organ_id)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _issue_by_id(receipt: dict[str, object], organ_id: str) -> dict[str, object]:
    for issue in receipt["disposition_guard"]["issues"]:
        if issue["organ_id"] == organ_id:
            return issue
    raise AssertionError(f"missing disposition guard issue: {organ_id}")


def _candidate_by_id(receipt: dict[str, object], organ_id: str) -> dict[str, object]:
    for candidate in receipt["candidates"]:
        if candidate["organ_id"] == organ_id:
            return candidate
    raise AssertionError(f"missing evidence truth-floor candidate: {organ_id}")


def test_truth_floor_flags_fixture_echo_real_runtime_receipt_candidate(
    tmp_path: Path,
) -> None:
    public_root = _copy_truth_floor_tree(tmp_path)
    _set_evidence_class(
        public_root,
        "mechanistic_interpretability_circuit_attribution_replay",
        "fixture_echo_smoke",
    )

    receipt = audit_evidence_truth_floor(public_root)

    candidate = _candidate_by_id(
        receipt,
        "mechanistic_interpretability_circuit_attribution_replay",
    )
    assert receipt["status"] == "blocked"
    assert candidate["candidate_classification"] == "real_runtime_receipt_candidate"
    assert candidate["current_evidence_class"] == "fixture_echo_smoke"
    assert candidate["recommended_evidence_class"] == "semantic_validator"
    assert candidate["recommended_truth_accounting_bucket"] == "real_import_validation"
    evidence = candidate["evidence"]
    assert evidence["body_import_status"] == "real_runtime_receipt_landed"
    assert evidence["body_import_classification"] == "real_runtime_receipt"
    assert evidence["body_in_receipt"] is False
    assert evidence["secret_exclusion_scan_status"] == "pass"


def test_truth_floor_blocks_fixture_echo_progress_mismatch(
    tmp_path: Path,
) -> None:
    public_root = _copy_truth_floor_tree(tmp_path)
    organ_id = "mechanistic_interpretability_circuit_attribution_replay"
    _set_evidence_class(public_root, organ_id, "fixture_echo_smoke")

    receipt = audit_evidence_truth_floor(public_root)

    issue = _issue_by_id(receipt, organ_id)
    assert receipt["status"] == "blocked"
    assert receipt["blocking_issue_count"] == 1
    assert receipt["disposition_issue_counts_by_code"] == {
        "synthetic_acceptance_progress_flag_mismatch": 1
    }
    assert issue["code"] == "synthetic_acceptance_progress_flag_mismatch"
    assert "fixture_echo_smoke_counts_as_real_substrate_progress" in issue[
        "mismatch_reasons"
    ]
    assert "fixture_echo_smoke_disposition_claims_real_substrate" in issue[
        "mismatch_reasons"
    ]


def test_truth_floor_scans_nested_receipts_when_canonical_files_absent(
    tmp_path: Path,
) -> None:
    public_root = _copy_truth_floor_tree(tmp_path)
    organ_id = "mechanistic_interpretability_circuit_attribution_replay"
    _set_evidence_class(public_root, organ_id, "fixture_echo_smoke")
    receipt_dir = public_root / "receipts/first_wave" / organ_id
    for receipt_path in receipt_dir.glob("*.json"):
        receipt_path.unlink()
    nested_receipt = receipt_dir / "components/runtime/deep_validation_receipt.json"
    _write_json(
        nested_receipt,
        {
            "status": "pass",
            "body_import_verification": {
                "body_import_status": "real_runtime_receipt_landed",
                "classification": "real_runtime_receipt",
                "body_in_receipt": False,
                "source_ref": "src/mechanistic_interpretability.py",
                "target_ref": "src/microcosm_core/organs/mechanistic.py",
                "validation_refs": ["pytest"],
            },
            "secret_exclusion_scan": {"status": "pass"},
        },
    )

    receipt = audit_evidence_truth_floor(public_root)

    candidate = _candidate_by_id(receipt, organ_id)
    assert candidate["candidate_classification"] == "real_runtime_receipt_candidate"
    evidence = candidate["evidence"]
    assert evidence["receipt_ref"] == (
        "receipts/first_wave/"
        "mechanistic_interpretability_circuit_attribution_replay/"
        "components/runtime/deep_validation_receipt.json"
    )
    assert evidence["body_import_status"] == "real_runtime_receipt_landed"
    assert evidence["body_import_classification"] == "real_runtime_receipt"
    assert evidence["body_in_receipt"] is False
    assert evidence["source_ref_count"] == 1
    assert evidence["target_ref_count"] == 1
    assert evidence["validation_ref_count"] == 1


def test_truth_floor_blocks_receipt_only_fixture_promotion_candidate(
    tmp_path: Path,
) -> None:
    public_root = _copy_truth_floor_tree(tmp_path)
    organ_id = "agent_benchmark_integrity_anti_gaming_replay"
    _stage_fixture_echo_row(public_root, organ_id)
    receipt_dir = public_root / "receipts/first_wave" / organ_id
    shutil.rmtree(receipt_dir, ignore_errors=True)
    _write_json(
        receipt_dir / f"{organ_id}_result.json",
        {
            "status": "pass",
            "body_import_verification": {
                "body_import_status": "real_runtime_receipt_landed",
                "classification": "real_runtime_receipt",
                "body_in_receipt": False,
            },
            "secret_exclusion_scan": {"status": "pass"},
        },
    )

    receipt = audit_evidence_truth_floor(public_root)

    assert receipt["status"] == "blocked"
    assert receipt["candidate_count"] == 0
    assert receipt["blocking_issue_count"] == 1
    assert receipt["proof_gap_issue_counts_by_code"] == {
        "fixture_echo_receipt_without_public_body_proof": 1
    }
    guard = receipt["proof_gap_guard"]
    assert guard["issue_count"] == 1
    assert (
        guard[
            "candidate_receipts_reject_fixture_receipt_or_generated_projection_refs"
        ]
        is True
    )
    issue = guard["issues"][0]
    assert issue["organ_id"] == organ_id
    assert issue["code"] == "fixture_echo_receipt_without_public_body_proof"
    assert issue["missing_proof_fields"] == [
        "source_ref",
        "target_ref",
        "validation_ref",
    ]


def test_truth_floor_blocks_fixture_refs_as_public_body_proof(
    tmp_path: Path,
) -> None:
    public_root = _copy_truth_floor_tree(tmp_path)
    organ_id = "agent_benchmark_integrity_anti_gaming_replay"
    _stage_fixture_echo_row(public_root, organ_id)
    receipt_dir = public_root / "receipts/first_wave" / organ_id
    shutil.rmtree(receipt_dir, ignore_errors=True)
    _write_json(
        receipt_dir / f"{organ_id}_result.json",
        {
            "status": "pass",
            "body_import_verification": {
                "body_import_status": "real_runtime_receipt_landed",
                "classification": "real_runtime_receipt",
                "body_in_receipt": False,
                "source_ref": "fixtures/first_wave/agent_benchmark/input/case.json",
                "target_ref": "receipts/first_wave/agent_benchmark/result.json",
                "validation_refs": ["pytest microcosm-substrate/tests/test_x.py"],
            },
            "secret_exclusion_scan": {"status": "pass"},
        },
    )

    receipt = audit_evidence_truth_floor(public_root)

    assert receipt["status"] == "blocked"
    assert receipt["candidate_count"] == 0
    assert receipt["proof_gap_issue_counts_by_code"] == {
        "fixture_echo_receipt_without_public_body_proof": 1
    }
    issue = receipt["proof_gap_guard"]["issues"][0]
    assert issue["code"] == "fixture_echo_receipt_without_public_body_proof"
    assert issue["missing_proof_fields"] == [
        "source_ref_public_substrate_not_fixture_receipt_or_generated_projection",
        "target_ref_public_body_not_fixture_receipt_or_generated_projection",
    ]


def test_truth_floor_flags_fixture_echo_public_refactor_candidate(
    tmp_path: Path,
) -> None:
    public_root = _copy_truth_floor_tree(tmp_path)
    _set_evidence_class(
        public_root,
        "agentic_vulnerability_discovery_patch_proof_replay",
        "fixture_echo_smoke",
    )

    receipt = audit_evidence_truth_floor(public_root)

    candidate = _candidate_by_id(
        receipt,
        "agentic_vulnerability_discovery_patch_proof_replay",
    )
    assert candidate["candidate_classification"] == "source_faithful_refactor_candidate"
    assert candidate["current_evidence_class"] == "fixture_echo_smoke"
    assert candidate["recommended_evidence_class"] == "algorithmic_projection"
    assert (
        candidate["recommended_truth_accounting_bucket"]
        == "source_faithful_refactor"
    )
    evidence = candidate["evidence"]
    assert evidence["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert evidence["body_import_classification"] == "extension_of_existing_public_refactor"
    assert evidence["body_in_receipt"] is False


def test_truth_floor_flags_sandbox_policy_trace_refactor_candidate(
    tmp_path: Path,
) -> None:
    public_root = _copy_truth_floor_tree(tmp_path)
    _set_evidence_class(
        public_root,
        "agent_sandbox_policy_escape_replay",
        "fixture_echo_smoke",
    )

    receipt = audit_evidence_truth_floor(public_root)

    candidate = _candidate_by_id(receipt, "agent_sandbox_policy_escape_replay")
    assert candidate["candidate_classification"] == "source_faithful_refactor_candidate"
    assert candidate["recommended_evidence_class"] == "algorithmic_projection"
    evidence = candidate["evidence"]
    assert evidence["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert evidence["body_import_classification"] == "extension_of_existing_public_refactor"
    assert evidence["body_in_receipt"] is False


def test_current_registry_no_longer_flags_landed_truth_floor_rows() -> None:
    receipt = audit_evidence_truth_floor(MICROCOSM_ROOT)

    assert receipt["status"] == "pass"
    candidate_ids = {candidate["organ_id"] for candidate in receipt["candidates"]}
    assert "mechanistic_interpretability_circuit_attribution_replay" not in candidate_ids
    assert "agentic_vulnerability_discovery_patch_proof_replay" not in candidate_ids
    assert "agent_sandbox_policy_escape_replay" not in candidate_ids
    assert receipt["candidate_count"] == 0
    assert receipt["inspected_fixture_echo_row_count"] == 0
    assert receipt["blocking_issue_count"] == 0
    assert receipt["disposition_guard"]["issue_count"] == 0
    assert receipt["disposition_guard"]["issues"] == []
    assert receipt["proof_gap_guard"]["issue_count"] == 0
    assert receipt["proof_gap_guard"]["issues"] == []


def test_truth_floor_blocks_missing_fixture_echo_disposition(tmp_path: Path) -> None:
    public_root = _copy_truth_floor_tree(tmp_path)
    organ_id = "agent_benchmark_integrity_anti_gaming_replay"
    _stage_fixture_echo_row(public_root, organ_id)
    registry_path = public_root / "core/organ_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for row in registry["implemented_organs"]:
        if row["organ_id"] == organ_id:
            row.pop("synthetic_acceptance_disposition")
            break
    else:
        raise AssertionError(f"missing organ registry row: {organ_id}")
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

    receipt = audit_evidence_truth_floor(public_root)

    issue = _issue_by_id(receipt, organ_id)
    assert receipt["status"] == "blocked"
    assert receipt["disposition_issue_counts_by_code"] == {
        "missing_synthetic_acceptance_dispositions": 1
    }
    assert issue["code"] == "missing_synthetic_acceptance_dispositions"
    assert issue["missing_fields"] == ["synthetic_acceptance_disposition"]


def test_fixture_echo_profile_denies_score_and_progress_authority() -> None:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_evidence_classes.json").read_text(
            encoding="utf-8"
        )
    )
    profile = registry["class_profiles"]["fixture_echo_smoke"]
    ceiling = registry["authority_ceiling"]
    denied = ceiling["denied_authority"]

    assert registry["anti_claim"].startswith(
        "Evidence-class rows and truth-accounting buckets are read-model"
    )
    assert ceiling["classification_authority"] == (
        "evidence_strength_and_truth_accounting_read_model_only"
    )
    assert denied["accepted_status_is_product_progress"] is False
    assert denied["class_rank_is_score"] is False
    assert denied["complete_secret_detection_claim"] is False
    assert denied["private_data_equivalence_claim"] is False
    assert denied["product_completeness_claim"] is False
    assert denied["proof_correctness_claim"] is False
    assert denied["provider_calls_authorized"] is False
    assert denied["release_authorized"] is False
    assert denied["score_based_progress_authority"] is False
    assert denied["source_mutation_authorized"] is False
    assert denied["whole_system_correctness_claim"] is False
    assert any(
        "not a product-progress score" in guard for guard in ceiling["overread_guard"]
    )
    assert any("not a benchmark" in guard for guard in ceiling["overread_guard"])
    assert profile["counts_as_real_substrate_progress"] is False
    assert profile["truth_accounting_bucket"] == "regression_negative_fixture"
    assert "not behavioral validation" in profile["claim_ceiling"]
    assert "not benchmark scores" in profile["claim_ceiling"]
    assert "product progress evidence" in profile["claim_ceiling"]
    assert "fixture-supplied score-like fields" in profile["evaluator_basis"]
    assert "not benchmark scores" in profile["evaluator_basis"]
    assert "product progress evidence" in profile["evaluator_basis"]
