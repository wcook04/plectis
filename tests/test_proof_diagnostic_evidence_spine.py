from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.proof_diagnostic_evidence_spine import (
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    run,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PROOF_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/proof_diagnostic_evidence_spine/input"
PER_OUTPUT_RECEIPT_FIELD_FLOOR = {
    "receipts/first_wave/proof_diagnostic_evidence_spine/proof_receipts.json": [
        "source_fingerprints",
        "source_fingerprint_status",
        "claim_ceiling",
    ],
    "receipts/first_wave/proof_diagnostic_evidence_spine/provider_payload_policy_result.json": [
        "provider_payload_authority_rejected",
        "body_redacted",
        "public_replacement_refs",
    ],
    "receipts/first_wave/proof_diagnostic_evidence_spine/diagnostic_board.json": [
        "diagnostic_board_source_authority_rejected",
    ],
    "receipts/first_wave/proof_diagnostic_evidence_spine/proof_evidence_validation_receipt.json": [
        "accepted_count",
        "rejected_count",
        "authority_rejection_count",
        "forbidden_key_scan",
        "provider_payload_authority_rejected",
        "runtime_correctness_claim_rejected",
        "diagnostic_board_source_authority_rejected",
    ],
}


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


def test_proof_diagnostic_evidence_spine_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        PROOF_FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["accepted_check_ids"] == ["toy_schema_check"]
    assert result["rejected_check_ids"] == ["toy_schema_check_broken"]
    assert result["advisory_payload_ids"] == ["provider_advisory_metadata_only"]
    assert result["provider_policy_rejection_ids"] == ["provider_payload_with_forbidden_body_keys"]
    assert result["diagnostic_board_source_authority_rejected"] is True
    assert result["runtime_correctness_claim_rejected"] is True
    assert result["source_fingerprint_status"] == "stale"
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_proof_diagnostic_evidence_spine_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/proof_diagnostic_evidence_spine",
        public_root / "fixtures/first_wave/proof_diagnostic_evidence_spine",
    )

    result = run(
        public_root / "fixtures/first_wave/proof_diagnostic_evidence_spine/input",
        public_root / "receipts/first_wave/proof_diagnostic_evidence_spine",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == EXPECTED_RECEIPT_PATHS
    for receipt_path in EXPECTED_RECEIPT_PATHS:
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "/Users/willcook" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        payload = json.loads(text)
        for key in (
            "schema_version",
            "organ_id",
            "fixture_id",
            "validator_id",
            "command",
            "status",
            "expected_negative_cases",
            "observed_negative_cases",
            "missing_negative_cases",
            "error_codes",
            "anti_claim",
            "private_state_scan",
            "authority_ceiling",
            "receipt_paths",
        ):
            assert key in payload
        assert payload["status"] == "pass"
        assert payload["missing_negative_cases"] == []
        assert set(payload["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
        assert payload["private_state_scan"]["body_redacted"] is True
        for hit in payload["private_state_scan"]["hits"]:
            assert hit["body_redacted"] is True
            assert not Path(hit["path"]).is_absolute()


def test_proof_diagnostic_evidence_spine_does_not_echo_forbidden_body_values(
    tmp_path: Path,
) -> None:
    provider_payloads = json.loads(
        (PROOF_FIXTURE_INPUT / "provider_advisory_payloads.json").read_text(encoding="utf-8")
    )
    forbidden_values = [
        row[key]
        for row in provider_payloads["payloads"]
        for key in ("proof_body", "ground_truth_proof", "provider_output_body")
        if key in row
    ]
    result = run(
        PROOF_FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    for receipt_file in sorted((tmp_path / "receipts").glob("*.json")) + [tmp_path / "acceptance.json"]:
        text = receipt_file.read_text(encoding="utf-8")
        for value in forbidden_values:
            assert value not in text
    assert result["proof_body_forbidden_key_hits"] == [
        {
            "payload_id": "provider_payload_with_forbidden_body_keys",
            "forbidden_keys": ["ground_truth_proof", "proof_body", "provider_output_body"],
            "body_redacted": True,
        }
    ]


def test_proof_diagnostic_evidence_spine_diagnostic_board_keeps_weak_edges(
    tmp_path: Path,
) -> None:
    result = run(
        PROOF_FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )
    diagnostic_board = json.loads(
        (tmp_path / "receipts/diagnostic_board.json").read_text(encoding="utf-8")
    )

    assert diagnostic_board["accepted_evidence"] == ["toy_schema_check"]
    assert diagnostic_board["rejected_evidence"] == ["toy_schema_check_broken"]
    assert diagnostic_board["source_authority_claim_rejected"] is True
    assert diagnostic_board["runtime_correctness_claim_rejected"] is True
    assert len(diagnostic_board["validator_asserted_feeds_patterns"]) == 3
    assert result["body_safe_lineage_status"]["status"] == "pass"


def test_proof_diagnostic_evidence_spine_receipts_satisfy_macro_field_floor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/proof_diagnostic_evidence_spine",
        public_root / "fixtures/first_wave/proof_diagnostic_evidence_spine",
    )
    run(
        public_root / "fixtures/first_wave/proof_diagnostic_evidence_spine/input",
        public_root / "receipts/first_wave/proof_diagnostic_evidence_spine",
        command="pytest",
    )

    for receipt_path, required_fields in PER_OUTPUT_RECEIPT_FIELD_FLOOR.items():
        payload = json.loads((public_root / receipt_path).read_text(encoding="utf-8"))
        missing = [field for field in required_fields if field not in payload]
        assert missing == []

    validation_receipt = json.loads(
        (
            public_root
            / "receipts/first_wave/proof_diagnostic_evidence_spine/proof_evidence_validation_receipt.json"
        ).read_text(encoding="utf-8")
    )
    assert validation_receipt["accepted_count"] == 1
    assert validation_receipt["rejected_count"] == 1
    assert validation_receipt["forbidden_key_scan"]["body_redacted"] is True
    assert validation_receipt["provider_payload_authority_rejected"] is True
    assert validation_receipt["runtime_correctness_claim_rejected"] is True
    assert validation_receipt["diagnostic_board_source_authority_rejected"] is True
