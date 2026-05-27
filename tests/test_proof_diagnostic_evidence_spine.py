from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import proof_diagnostic_evidence_spine as proof_spine
from microcosm_core.organs.proof_diagnostic_evidence_spine import (
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    PUBLIC_RING2_ARTIFACT_IMPORTS,
    PUBLIC_RING2_ARTIFACT_TARGET_REFS,
    SOURCE_DIGESTS,
    result_card,
    run,
    run_evidence_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PROOF_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/proof_diagnostic_evidence_spine/input"
PROOF_EXPORTED_BUNDLE_INPUT = MICROCOSM_ROOT / "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle"
PER_OUTPUT_RECEIPT_FIELD_FLOOR = {
    "receipts/first_wave/proof_diagnostic_evidence_spine/proof_receipts.json": [
        "private_state_scan",
        "body_redacted",
        "public_replacement_refs",
        "upstream_reference_capsule_receipt_refs",
        "upstream_authority_chain_receipt_refs",
        "source_fingerprints",
        "source_fingerprint_status",
        "source_digest_sha256_by_ref",
        "claim_ceiling",
    ],
    "receipts/first_wave/proof_diagnostic_evidence_spine/provider_payload_policy_result.json": [
        "private_state_scan",
        "provider_payload_authority_rejected",
        "body_redacted",
        "public_replacement_refs",
        "body_in_receipt",
        "real_substrate_refs",
        "receipt_anchor_refs",
        "source_digests",
    ],
    "receipts/first_wave/proof_diagnostic_evidence_spine/diagnostic_board.json": [
        "private_state_scan",
        "upstream_reference_capsule_receipt_refs",
        "upstream_authority_chain_receipt_refs",
        "accepted_count",
        "rejected_count",
        "authority_rejection_count",
        "diagnostic_board_source_authority_rejected",
        "claim_ceiling",
    ],
    "receipts/first_wave/proof_diagnostic_evidence_spine/proof_evidence_validation_receipt.json": [
        "private_state_scan",
        "upstream_reference_capsule_receipt_refs",
        "upstream_authority_chain_receipt_refs",
        "omission_reversal_inputs",
        "proof_evidence_authority_ceilings_compatible",
        "source_digest_sha256_by_ref",
        "accepted_count",
        "rejected_count",
        "authority_rejection_count",
        "forbidden_key_scan",
        "provider_payload_authority_rejected",
        "runtime_correctness_claim_rejected",
        "diagnostic_board_source_authority_rejected",
        "claim_ceiling",
        "body_material_status",
        "evidence_anchor_status",
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


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
    assert result["accepted_check_ids"] == [
        "ring2_failure_taxonomy_receipt_anchor",
        "ring2_graph_update_candidate_anchor",
    ]
    assert result["rejected_check_ids"] == ["regression_negative_missing_source_digest"]
    assert result["advisory_payload_ids"] == ["ring2_failure_taxonomy_advisory_ref"]
    assert result["provider_policy_rejection_ids"] == [
        "regression_provider_payload_with_forbidden_body_keys"
    ]
    assert result["diagnostic_board_source_authority_rejected"] is True
    assert result["runtime_correctness_claim_rejected"] is True
    assert result["source_fingerprint_status"] == "stale"
    assert result["body_material_status"] == "real_ring2_diagnostic_receipt_refs"
    assert (
        result["evidence_anchor_status"]
        == "real_ring2_failure_taxonomy_and_evidence_cell_receipt_refs"
    )
    assert "failure_taxonomy_report.json" in " ".join(result["real_substrate_refs"])
    assert "formal_evidence_cell_anchor_resolver_result.json" in " ".join(
        result["receipt_anchor_refs"]
    )
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_proof_diagnostic_evidence_spine_accepts_exported_evidence_bundle(
    tmp_path: Path,
) -> None:
    result = run_evidence_bundle(
        PROOF_EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_evidence_bundle"
    assert result["bundle_id"] == "ring2_proof_diagnostic_evidence_runtime_example"
    assert result["accepted_check_ids"] == ["ring2_failure_taxonomy_exported_anchor_check"]
    assert result["rejected_check_ids"] == []
    assert result["advisory_payload_ids"] == ["ring2_provider_advisory_receipt_refs"]
    assert result["provider_policy_rejection_ids"] == []
    assert (
        result["formal_policy_packet_status"]
        == "ring2_diagnostic_policy_packet_consumed_without_provider_call"
    )
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["copied_macro_body_artifact_count"] == len(PUBLIC_RING2_ARTIFACT_IMPORTS)
    assert result["copied_macro_body_digest_status"] == "pass"
    assert result["copied_macro_body_missing_target_refs"] == []
    assert result["copied_macro_body_digest_mismatches"] == []
    assert result["source_target_refs"][-len(PUBLIC_RING2_ARTIFACT_TARGET_REFS) :] == (
        PUBLIC_RING2_ARTIFACT_TARGET_REFS
    )
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["authority_ceiling"]["formal_prover_execution_authorized"] is False
    assert result["receipt_paths"] == [
        "receipts/exported_evidence_bundle_validation_result.json"
    ]

    receipt = json.loads((tmp_path / "receipts/exported_evidence_bundle_validation_result.json").read_text(encoding="utf-8"))
    assert receipt["input_mode"] == "exported_evidence_bundle"
    assert all(path.startswith("receipts/") for path in receipt["receipt_paths"])
    text = json.dumps(receipt, sort_keys=True)
    assert "matched_excerpt" not in text
    assert '"proof_body"' not in text
    assert '"provider_output_body"' not in text
    assert "provider output body" not in text


def test_proof_diagnostic_evidence_spine_exported_bundle_copies_ring2_artifacts(
    tmp_path: Path,
) -> None:
    manifest = json.loads(
        (PROOF_EXPORTED_BUNDLE_INPUT / "bundle_manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["copied_macro_body_artifacts"] == PUBLIC_RING2_ARTIFACT_IMPORTS
    for artifact in manifest["copied_macro_body_artifacts"]:
        target_ref = artifact["target_ref"]
        target_path = MICROCOSM_ROOT / target_ref
        source_ref = artifact["source_ref"]
        assert target_ref in PUBLIC_RING2_ARTIFACT_TARGET_REFS
        assert target_path.is_file()
        assert artifact["body_copied"] is True
        assert artifact["copy_policy"] == "exact_public_safe_runtime_artifact"
        assert _sha256_file(target_path) == artifact["sha256"]
        assert _sha256_file(target_path) == SOURCE_DIGESTS[source_ref]

    result = run_evidence_bundle(
        PROOF_EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )
    copied_by_id = {
        row["artifact_id"]: row for row in result["copied_macro_body_artifacts"]
    }
    assert set(copied_by_id) == {
        artifact["artifact_id"] for artifact in PUBLIC_RING2_ARTIFACT_IMPORTS
    }
    assert all(row["digest_status"] == "pass" for row in copied_by_id.values())
    assert all(row["body_copied"] is True for row in copied_by_id.values())


def test_proof_diagnostic_evidence_spine_card_reuses_fresh_bundle_receipt(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    out_dir = tmp_path / "receipts"
    result = run_evidence_bundle(
        PROOF_EXPORTED_BUNDLE_INPUT,
        out_dir,
        command="pytest --card",
        reuse_fresh_receipt=True,
    )

    assert result["status"] == "pass"
    assert result["receipt_reused"] is False
    assert result["card_schema_version"] == "proof_diagnostic_evidence_spine_card_v1"
    card = result_card(result)
    assert card["receipt_reused"] is False
    assert card["copied_macro_body_artifact_count"] == len(PUBLIC_RING2_ARTIFACT_IMPORTS)
    assert card["copied_macro_body_digest_status"] == "pass"
    assert card["freshness_digest"] == result["freshness_digest"]
    assert "copied_macro_body_artifacts" in card["omitted_full_payload_keys"]
    assert "proof_receipts" in card["omitted_full_payload_keys"]
    card_text = json.dumps(card, sort_keys=True)
    assert "copied_macro_body_artifacts" not in card
    assert "proof_receipts" not in card
    assert str(tmp_path) not in card_text

    def fail_if_rebuilt(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the full receipt")

    monkeypatch.setattr(
        proof_spine,
        "validate_copied_macro_body_artifacts",
        fail_if_rebuilt,
    )

    cached = run_evidence_bundle(
        PROOF_EXPORTED_BUNDLE_INPUT,
        out_dir,
        command="pytest --card",
        reuse_fresh_receipt=True,
    )
    cached_card = result_card(cached)

    assert cached["status"] == "pass"
    assert cached["receipt_reused"] is True
    assert cached["freshness_digest"] == result["freshness_digest"]
    assert cached_card["receipt_reused"] is True
    assert cached_card["copied_macro_body_artifact_count"] == len(
        PUBLIC_RING2_ARTIFACT_IMPORTS
    )


def test_proof_diagnostic_fixture_manifest_exposes_ring2_body_floor() -> None:
    fixture_manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/proof_diagnostic_evidence_spine.fixture_manifest.json"
        ).read_text(encoding="utf-8")
    )
    body_imports = fixture_manifest["source_open_body_imports"]
    expected_ids = [
        artifact["artifact_id"] for artifact in PUBLIC_RING2_ARTIFACT_IMPORTS
    ]

    assert fixture_manifest["body_copied_material_count"] == len(
        PUBLIC_RING2_ARTIFACT_IMPORTS
    )
    assert body_imports["status"] == "pass"
    assert body_imports["body_material_count"] == len(PUBLIC_RING2_ARTIFACT_IMPORTS)
    assert body_imports["body_material_ids"] == expected_ids
    assert body_imports["source_manifest_refs"] == [
        "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle/bundle_manifest.json"
    ]
    assert (
        body_imports["aggregate_floor_ref"]
        == "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle/bundle_manifest.json::copied_macro_body_artifacts"
    )
    assert body_imports["body_in_receipt"] is False
    assert body_imports["authority_ceiling"] == {
        "body_text_in_receipt": False,
        "proof_body_or_oracle_proof_text_exported": False,
        "provider_payload_exported": False,
        "lean_lake_execution_authorized": False,
        "formal_proof_authority": False,
        "runtime_correctness_claim": False,
        "release_authorized": False,
    }


def test_proof_diagnostic_evidence_spine_receipts_are_public_relative_and_body_free(
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
            "secret_exclusion_scan",
            "authority_ceiling",
            "receipt_paths",
            "body_material_status",
            "evidence_anchor_status",
            "real_substrate_refs",
            "receipt_anchor_refs",
            "source_digests",
        ):
            assert key in payload
        assert payload["status"] == "pass"
        assert payload["missing_negative_cases"] == []
        assert set(payload["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        for hit in payload["secret_exclusion_scan"]["hits"]:
            assert hit["body_in_receipt"] is False
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
            "payload_id": "regression_provider_payload_with_forbidden_body_keys",
            "forbidden_keys": ["ground_truth_proof", "proof_body", "provider_output_body"],
            "body_in_receipt": False,
            "public_status": "regression_negative_fixture",
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

    assert diagnostic_board["accepted_evidence"] == [
        "ring2_failure_taxonomy_receipt_anchor",
        "ring2_graph_update_candidate_anchor",
    ]
    assert diagnostic_board["rejected_evidence"] == ["regression_negative_missing_source_digest"]
    assert diagnostic_board["source_authority_claim_rejected"] is True
    assert diagnostic_board["runtime_correctness_claim_rejected"] is True
    assert diagnostic_board["body_in_receipt"] is False
    assert "failure_taxonomy_report.json" in " ".join(diagnostic_board["source_refs"])
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
    assert validation_receipt["accepted_count"] == 2
    assert validation_receipt["rejected_count"] == 1
    assert validation_receipt["forbidden_key_scan"]["body_in_receipt"] is False
    assert validation_receipt["provider_payload_authority_rejected"] is True
    assert validation_receipt["runtime_correctness_claim_rejected"] is True
    assert validation_receipt["diagnostic_board_source_authority_rejected"] is True
    assert validation_receipt["body_material_status"] == "real_ring2_diagnostic_receipt_refs"
    assert validation_receipt["private_state_scan"]["status"] == "pass"
    assert validation_receipt["private_state_scan"]["compatibility_alias_for"] == (
        "secret_exclusion_scan"
    )
    assert validation_receipt["proof_evidence_authority_ceilings_compatible"] is True
    assert validation_receipt["omission_reversal_inputs"]["body_in_receipt"] is False
    assert validation_receipt["omission_reversal_inputs"][
        "proof_or_provider_bodies_recovered"
    ] is False
    assert (
        "receipts/first_wave/pattern_binding_contract/reference_capsule_resolver_receipt.json"
        in validation_receipt["upstream_reference_capsule_receipt_refs"]
    )
