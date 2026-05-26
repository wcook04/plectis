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
    assert receipt["status"] == "pass"
    assert candidate["candidate_classification"] == "real_runtime_receipt_candidate"
    assert candidate["current_evidence_class"] == "fixture_echo_smoke"
    assert candidate["recommended_evidence_class"] == "semantic_validator"
    assert candidate["recommended_truth_accounting_bucket"] == "real_import_validation"
    evidence = candidate["evidence"]
    assert evidence["body_import_status"] == "real_runtime_receipt_landed"
    assert evidence["body_import_classification"] == "real_runtime_receipt"
    assert evidence["body_in_receipt"] is False
    assert evidence["secret_exclusion_scan_status"] == "pass"


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
    assert receipt["inspected_fixture_echo_row_count"] == 3


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
