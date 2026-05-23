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
    assert receipt["inspected_fixture_echo_row_count"] == 5
