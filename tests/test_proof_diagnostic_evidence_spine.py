from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core import cli
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


def _finding_for(result: dict[str, Any], subject_id: str) -> dict[str, Any]:
    return next(
        finding for finding in result["findings"] if finding["subject_id"] == subject_id
    )


def _copy_public_fixture_tree(public_root: Path) -> None:
    repo_root = MICROCOSM_ROOT.parent
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/proof_diagnostic_evidence_spine",
        public_root / "fixtures/first_wave/proof_diagnostic_evidence_spine",
    )
    checks_payload = json.loads((PROOF_FIXTURE_INPUT / "checks.json").read_text(encoding="utf-8"))
    provider_payload = json.loads(
        (PROOF_FIXTURE_INPUT / "provider_advisory_payloads.json").read_text(encoding="utf-8")
    )
    diagnostic_payload = json.loads(
        (PROOF_FIXTURE_INPUT / "diagnostic_rows.json").read_text(encoding="utf-8")
    )
    refs = {
        ref
        for row in checks_payload["checks"]
        for ref in [*row.get("source_refs", []), *row.get("receipt_anchor_refs", [])]
        if isinstance(ref, str) and ref
    }
    refs.update(
        ref
        for row in provider_payload["payloads"]
        for ref in row.get("premise_refs", [])
        if isinstance(ref, str) and ref
    )
    refs.update(
        ref
        for row in diagnostic_payload["diagnostic_rows"]
        for ref in (row.get("source_ref"), row.get("receipt_ref"))
        if isinstance(ref, str) and ref
    )
    for ref in sorted(refs):
        ref = ref.split("::", 1)[0]
        source_path = MICROCOSM_ROOT / ref
        if not source_path.is_file():
            source_path = repo_root / ref
        if not source_path.is_file():
            continue
        target_root = public_root if (MICROCOSM_ROOT / ref).is_file() else public_root.parent
        target_path = target_root / ref
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _copy_public_evidence_bundle_tree(public_root: Path) -> None:
    repo_root = MICROCOSM_ROOT.parent
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/proof_diagnostic_evidence_spine",
        public_root / "examples/proof_diagnostic_evidence_spine",
    )
    checks_payload = json.loads(
        (PROOF_EXPORTED_BUNDLE_INPUT / "checks.json").read_text(encoding="utf-8")
    )
    provider_payload = json.loads(
        (PROOF_EXPORTED_BUNDLE_INPUT / "provider_advisory_payloads.json").read_text(
            encoding="utf-8"
        )
    )
    diagnostic_payload = json.loads(
        (PROOF_EXPORTED_BUNDLE_INPUT / "diagnostic_rows.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (PROOF_EXPORTED_BUNDLE_INPUT / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    refs = {
        ref
        for row in checks_payload["checks"]
        for ref in [*row.get("source_refs", []), *row.get("receipt_anchor_refs", [])]
        if isinstance(ref, str) and ref
    }
    refs.update(ref for ref in manifest.get("source_refs", []) if isinstance(ref, str) and ref)
    refs.update(
        ref
        for row in provider_payload["payloads"]
        for ref in row.get("premise_refs", [])
        if isinstance(ref, str) and ref
    )
    refs.update(
        ref
        for row in diagnostic_payload["diagnostic_rows"]
        for ref in (row.get("source_ref"), row.get("receipt_ref"))
        if isinstance(ref, str) and ref
    )
    for ref in sorted(refs):
        ref = ref.split("::", 1)[0]
        source_path = MICROCOSM_ROOT / ref
        if not source_path.is_file():
            source_path = repo_root / ref
        if not source_path.is_file():
            continue
        target_root = public_root if (MICROCOSM_ROOT / ref).is_file() else public_root.parent
        target_path = target_root / ref
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


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
    assert result["observed_negative_cases"] == {
        case_id: sorted(codes)
        for case_id, codes in EXPECTED_NEGATIVE_CASES.items()
    }
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


def test_proof_diagnostic_evidence_spine_derives_check_verdicts_from_real_evidence() -> None:
    payload = json.loads((PROOF_FIXTURE_INPUT / "checks.json").read_text(encoding="utf-8"))

    baseline = proof_spine.validate_evidence_receipts(payload, public_root=MICROCOSM_ROOT)
    assert baseline["accepted_check_ids"] == [
        "ring2_failure_taxonomy_receipt_anchor",
        "ring2_graph_update_candidate_anchor",
    ]
    assert baseline["rejected_check_ids"] == ["regression_negative_missing_source_digest"]
    baseline_row = next(
        row
        for row in baseline["proof_receipts"]
        if row["check_id"] == "ring2_failure_taxonomy_receipt_anchor"
    )
    assert baseline_row["source_refs_not_backed_by_receipts"] == []
    assert baseline_row["source_digest_refs_not_backed_by_receipts"] == []
    assert baseline_row["source_digest_basis_by_ref"][
        "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "premise_retrieval_graph_v0/failure_taxonomy_report.json"
    ] == "receipt_anchor"

    bad_digest_payload = json.loads(json.dumps(payload))
    bad_digest_payload["checks"][0]["expected_result"] = "pass"
    bad_digest_payload["checks"][0]["source_digest_refs"] = ["sha256:" + "0" * 64]
    bad_digest = proof_spine.validate_evidence_receipts(
        bad_digest_payload,
        public_root=MICROCOSM_ROOT,
    )
    bad_digest_row = next(
        row
        for row in bad_digest["proof_receipts"]
        if row["check_id"] == "ring2_failure_taxonomy_receipt_anchor"
    )

    assert "ring2_failure_taxonomy_receipt_anchor" not in bad_digest["accepted_check_ids"]
    assert "ring2_failure_taxonomy_receipt_anchor" in bad_digest["rejected_check_ids"]
    assert "expected_result_declared" not in bad_digest_row
    assert bad_digest_row["legacy_expected_result_label_present"] is True
    assert bad_digest_row["legacy_expected_result_label_authority"] == (
        "ignored_non_authoritative_fixture_label"
    )
    assert bad_digest_row["semantic_check_status"] == "blocked"
    assert "source_digest_mismatch" in bad_digest_row["semantic_rejection_reasons"]
    assert bad_digest_row["evidence_sha256"] != baseline_row["evidence_sha256"]
    bad_digest_finding = _finding_for(bad_digest, "ring2_failure_taxonomy_receipt_anchor")
    assert bad_digest_finding["error_code"] == "EVIDENCE_RECEIPT_ANCHOR_RECOMPUTE_FAILED"
    assert bad_digest_finding["semantic_rejection_reasons"] == [
        "source_digest_mismatch"
    ]
    assert bad_digest_finding["verdict_basis"] == "receipt_source_anchor_recompute"

    missing_anchor_payload = json.loads(json.dumps(payload))
    missing_anchor_payload["checks"][1]["expected_result"] = "pass"
    missing_anchor_payload["checks"][1]["receipt_anchor_refs"] = [
        "receipts/first_wave/formal_evidence_cell_anchor_resolver/missing_anchor.json"
    ]
    missing_anchor = proof_spine.validate_evidence_receipts(
        missing_anchor_payload,
        public_root=MICROCOSM_ROOT,
    )
    missing_anchor_row = next(
        row
        for row in missing_anchor["proof_receipts"]
        if row["check_id"] == "ring2_graph_update_candidate_anchor"
    )

    assert "ring2_graph_update_candidate_anchor" not in missing_anchor["accepted_check_ids"]
    assert "ring2_graph_update_candidate_anchor" in missing_anchor["rejected_check_ids"]
    assert "expected_result_declared" not in missing_anchor_row
    assert missing_anchor_row["semantic_check_status"] == "blocked"
    assert "missing_receipt_anchor_ref" in missing_anchor_row["semantic_rejection_reasons"]
    missing_anchor_finding = _finding_for(
        missing_anchor,
        "ring2_graph_update_candidate_anchor",
    )
    assert missing_anchor_finding["semantic_rejection_reasons"] == [
        "missing_receipt_anchor_ref",
        "missing_graph_update_anchor",
    ]

    wrong_receipt_payload = json.loads(json.dumps(payload))
    wrong_receipt_payload["checks"][0]["expected_result"] = "pass"
    wrong_receipt_payload["checks"][0]["receipt_anchor_refs"] = [
        "receipts/first_wave/formal_evidence_cell_anchor_resolver/"
        "formal_evidence_cell_anchor_resolver_result.json"
    ]
    wrong_receipt = proof_spine.validate_evidence_receipts(
        wrong_receipt_payload,
        public_root=MICROCOSM_ROOT,
    )
    wrong_receipt_row = next(
        row
        for row in wrong_receipt["proof_receipts"]
        if row["check_id"] == "ring2_failure_taxonomy_receipt_anchor"
    )

    assert "ring2_failure_taxonomy_receipt_anchor" not in wrong_receipt["accepted_check_ids"]
    assert "ring2_failure_taxonomy_receipt_anchor" in wrong_receipt["rejected_check_ids"]
    assert "expected_result_declared" not in wrong_receipt_row
    assert wrong_receipt_row["semantic_check_status"] == "blocked"
    assert "missing_failure_mode_ledger" in wrong_receipt_row[
        "semantic_rejection_reasons"
    ]
    wrong_receipt_finding = _finding_for(
        wrong_receipt,
        "ring2_failure_taxonomy_receipt_anchor",
    )
    assert wrong_receipt_finding["semantic_rejection_reasons"] == [
        "missing_failure_mode_ledger"
    ]

    wrong_graph_source_payload = json.loads(json.dumps(payload))
    wrong_graph_source_payload["checks"][1]["expected_result"] = "pass"
    wrong_graph_source_payload["checks"][1]["source_refs"] = [
        "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "premise_retrieval_graph_v0/failure_taxonomy_report.json"
    ]
    wrong_graph_source_payload["checks"][1]["source_digest_refs"] = [
        SOURCE_DIGESTS[
            "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
            "premise_retrieval_graph_v0/failure_taxonomy_report.json"
        ]
    ]
    wrong_graph_source = proof_spine.validate_evidence_receipts(
        wrong_graph_source_payload,
        public_root=MICROCOSM_ROOT,
    )
    wrong_graph_row = next(
        row
        for row in wrong_graph_source["proof_receipts"]
        if row["check_id"] == "ring2_graph_update_candidate_anchor"
    )

    assert "ring2_graph_update_candidate_anchor" not in wrong_graph_source["accepted_check_ids"]
    assert "ring2_graph_update_candidate_anchor" in wrong_graph_source["rejected_check_ids"]
    assert "expected_result_declared" not in wrong_graph_row
    assert wrong_graph_row["semantic_check_status"] == "blocked"
    assert "missing_graph_update_candidates" in wrong_graph_row["semantic_rejection_reasons"]
    assert "missing_graph_update_candidate_ids" in wrong_graph_row["semantic_rejection_reasons"]
    wrong_graph_finding = _finding_for(
        wrong_graph_source,
        "ring2_graph_update_candidate_anchor",
    )
    assert wrong_graph_finding["semantic_rejection_reasons"] == [
        "missing_graph_update_candidate_ids",
        "missing_graph_update_candidates",
    ]


def test_proof_diagnostic_evidence_spine_ignores_legacy_expected_result_labels() -> None:
    payload = json.loads((PROOF_FIXTURE_INPUT / "checks.json").read_text(encoding="utf-8"))

    hostile_label_payload = json.loads(json.dumps(payload))
    hostile_label_payload["checks"][0]["expected_result"] = "fail"
    hostile_label_payload["checks"][0]["body_material_status"] = "hostile_label_only"
    hostile_label_payload["checks"][0]["evidence_anchor_status"] = "hostile_label_only"
    hostile_label_result = proof_spine.validate_evidence_receipts(
        hostile_label_payload,
        public_root=MICROCOSM_ROOT,
    )
    hostile_label_row = next(
        row
        for row in hostile_label_result["proof_receipts"]
        if row["check_id"] == "ring2_failure_taxonomy_receipt_anchor"
    )
    baseline_result = proof_spine.validate_evidence_receipts(payload, public_root=MICROCOSM_ROOT)
    baseline_row = next(
        row
        for row in baseline_result["proof_receipts"]
        if row["check_id"] == "ring2_failure_taxonomy_receipt_anchor"
    )

    assert "ring2_failure_taxonomy_receipt_anchor" in hostile_label_result["accepted_check_ids"]
    assert "expected_result_declared" not in hostile_label_row
    assert "legacy_expected_result_label_value" not in hostile_label_row
    assert hostile_label_row["legacy_expected_result_label_present"] is True
    assert hostile_label_row["legacy_expected_result_label_authority"] == (
        "ignored_non_authoritative_fixture_label"
    )
    assert hostile_label_row["verdict_basis"] == "receipt_source_anchor_recompute"
    assert hostile_label_row["semantic_check_status"] == "pass"
    assert hostile_label_row["evidence_sha256"] == baseline_row["evidence_sha256"]
    assert hostile_label_row["body_material_status"] == (
        "real_ring2_diagnostic_receipt_refs"
    )
    assert hostile_label_row["evidence_anchor_status"] == (
        "real_ring2_failure_taxonomy_and_evidence_cell_receipt_refs"
    )
    assert hostile_label_row["declared_body_material_status"] == "hostile_label_only"
    assert hostile_label_row["declared_evidence_anchor_status"] == "hostile_label_only"

    label_only_payload = {
        "checks": [
            {
                "check_id": "legacy_label_only_acceptance",
                "expected_result": "pass",
                "validator_id": "validator.microcosm.organs.proof_diagnostic_evidence_spine",
            }
        ]
    }
    label_only_result = proof_spine.validate_evidence_receipts(
        label_only_payload,
        public_root=MICROCOSM_ROOT,
    )
    label_only_row = label_only_result["proof_receipts"][0]

    assert label_only_result["accepted_check_ids"] == []
    assert label_only_result["rejected_check_ids"] == ["legacy_label_only_acceptance"]
    assert [_finding["subject_id"] for _finding in label_only_result["findings"]] == [
        "legacy_label_only_acceptance"
    ]
    assert "expected_result_declared" not in label_only_row
    assert label_only_row["legacy_expected_result_label_present"] is True
    assert label_only_row["semantic_check_status"] == "blocked"
    assert label_only_row["verdict_basis"] == "receipt_source_anchor_recompute"
    assert set(label_only_row["semantic_rejection_reasons"]) == {
        "missing_receipt_anchor_ref",
        "missing_source_digest_ref",
        "missing_source_ref",
    }


def test_proof_diagnostic_evidence_spine_recomputes_provider_payload_anchors() -> None:
    payload = json.loads(
        (PROOF_FIXTURE_INPUT / "provider_advisory_payloads.json").read_text(encoding="utf-8")
    )

    baseline = proof_spine.validate_provider_payload_policy(
        payload,
        public_root=MICROCOSM_ROOT,
    )
    assert baseline["advisory_payload_ids"] == ["ring2_failure_taxonomy_advisory_ref"]
    advisory_row = next(
        row
        for row in baseline["payload_rows"]
        if row["payload_id"] == "ring2_failure_taxonomy_advisory_ref"
    )
    assert advisory_row["anchor_status"] == "pass"

    mutated_payload = json.loads(json.dumps(payload))
    mutated_payload["payloads"][0]["premise_refs"] = [
        "receipts/first_wave/formal_evidence_cell_anchor_resolver/"
        "evidence_cell_anchor_board.json::missing.evidence.cell"
    ]
    mutated = proof_spine.validate_provider_payload_policy(
        mutated_payload,
        public_root=MICROCOSM_ROOT,
    )
    mutated_row = next(
        row
        for row in mutated["payload_rows"]
        if row["payload_id"] == "ring2_failure_taxonomy_advisory_ref"
    )

    assert mutated["advisory_payload_ids"] == []
    assert set(mutated["provider_policy_rejection_ids"]) == {
        "regression_provider_payload_with_forbidden_body_keys",
        "ring2_failure_taxonomy_advisory_ref",
    }
    assert mutated_row["anchor_status"] == "blocked"
    assert "missing_provider_premise_anchor_marker" in mutated_row[
        "semantic_rejection_reasons"
    ]
    assert "PROVIDER_ADVISORY_ANCHOR_RECOMPUTE_FAILED" in [
        finding["error_code"] for finding in mutated["findings"]
    ]


def test_proof_diagnostic_evidence_spine_recomputes_diagnostic_row_anchors() -> None:
    payload = json.loads(
        (PROOF_EXPORTED_BUNDLE_INPUT / "diagnostic_rows.json").read_text(encoding="utf-8")
    )

    baseline = proof_spine.validate_diagnostic_rows(payload, public_root=MICROCOSM_ROOT)
    assert baseline["status"] == "pass"
    assert baseline["accepted_diagnostic_row_ids"] == [
        "ring2_failure_taxonomy_exported_anchor_retained"
    ]

    mutated_payload = json.loads(json.dumps(payload))
    mutated_payload["diagnostic_rows"][0]["receipt_ref"] = (
        "receipts/first_wave/formal_math_verifier_trace_repair_loop/"
        "verifier_trace_repair_board.json::missing_failure_mode"
    )
    mutated = proof_spine.validate_diagnostic_rows(
        mutated_payload,
        public_root=MICROCOSM_ROOT,
    )
    mutated_row = mutated["diagnostic_rows"][0]

    assert mutated["status"] == "blocked"
    assert mutated["accepted_diagnostic_row_ids"] == []
    assert mutated["rejected_diagnostic_row_ids"] == [
        "ring2_failure_taxonomy_exported_anchor_retained"
    ]
    assert "missing_diagnostic_receipt_anchor_marker" in mutated_row[
        "semantic_rejection_reasons"
    ]
    assert [finding["error_code"] for finding in mutated["findings"]] == [
        "DIAGNOSTIC_ROW_ANCHOR_RECOMPUTE_FAILED"
    ]


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
    assert result["source_body_floor_artifact_count"] == 1
    assert result["source_body_floor_digest_status"] == "pass"
    assert result["source_body_floor_missing_paths"] == []
    assert result["source_body_floor_digest_mismatches"] == []
    assert result["source_target_refs"][-len(PUBLIC_RING2_ARTIFACT_TARGET_REFS) :] == (
        PUBLIC_RING2_ARTIFACT_TARGET_REFS
    )
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["authority_ceiling"]["formal_prover_execution_authorized"] is False
    assert len(result["receipt_paths"]) == 1
    assert result["receipt_paths"][0].endswith(
        "receipts/exported_evidence_bundle_validation_result.json"
    )
    assert not Path(result["receipt_paths"][0]).is_absolute()

    receipt = json.loads((tmp_path / "receipts/exported_evidence_bundle_validation_result.json").read_text(encoding="utf-8"))
    assert receipt["input_mode"] == "exported_evidence_bundle"
    assert all(
        path.endswith("receipts/exported_evidence_bundle_validation_result.json")
        for path in receipt["receipt_paths"]
    )
    assert all(not Path(path).is_absolute() for path in receipt["receipt_paths"])
    text = json.dumps(receipt, sort_keys=True)
    assert "matched_excerpt" not in text
    assert '"proof_body"' not in text
    assert '"provider_output_body"' not in text
    assert "provider output body" not in text


def test_proof_diagnostic_evidence_spine_rejects_nested_provider_payload_laundering(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    _copy_public_evidence_bundle_tree(public_root)
    bundle_input = (
        public_root / "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle"
    )
    provider_path = bundle_input / "provider_advisory_payloads.json"
    payload = json.loads(provider_path.read_text(encoding="utf-8"))
    hidden_body_value = "NESTED_PROVIDER_PROOF_BODY_SHOULD_NOT_SURFACE"
    payload["payloads"][0]["expected_negative_case_id"] = (
        "provider_proof_body_payload_rejected"
    )
    payload["payloads"][0]["metadata"] = {
        "provider_output_body": hidden_body_value,
    }
    provider_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_evidence_bundle(
        bundle_input,
        tmp_path / "receipts",
        command="pytest",
    )
    provider_row = result["provider_payload_policy"][0]

    assert result["status"] == "blocked"
    assert result["advisory_payload_ids"] == []
    assert result["provider_policy_rejection_ids"] == [
        "ring2_provider_advisory_receipt_refs"
    ]
    assert provider_row["forbidden_keys_detected"] == ["provider_output_body"]
    assert provider_row["forbidden_key_paths_detected"] == [
        "metadata.provider_output_body"
    ]
    assert result["observed_negative_cases"] == {
        "provider_proof_body_payload_rejected": [
            "FORBIDDEN_PROOF_BODY",
            "PROVIDER_PAYLOAD_NOT_AUTHORITY",
        ]
    }
    receipt_text = (
        tmp_path / "receipts/exported_evidence_bundle_validation_result.json"
    ).read_text(encoding="utf-8")
    assert hidden_body_value not in receipt_text


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
        assert artifact["copy_policy"] in {
            "exact_public_safe_runtime_artifact",
            "source_faithful_public_light_edit",
        }
        assert _sha256_file(target_path) == artifact["sha256"]
        if artifact["copy_policy"] == "source_faithful_public_light_edit":
            assert artifact["target_sha256"] == artifact["sha256"]
            assert artifact["source_sha256"] == SOURCE_DIGESTS[source_ref]
            assert artifact["rewrite_recipe_ref"].endswith("::_strong_private_path_hits")
        else:
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


def test_proof_diagnostic_evidence_spine_rejects_mutated_real_ring2_source_anchor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    _copy_public_evidence_bundle_tree(public_root)
    bundle_input = (
        public_root / "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle"
    )
    checks_path = bundle_input / "checks.json"
    checks_payload = json.loads(checks_path.read_text(encoding="utf-8"))
    source_ref = (
        "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "premise_retrieval_graph_v0/failure_taxonomy_report.json"
    )
    source_path = proof_spine._resolve_public_ref(public_root, source_ref)
    assert source_path is not None
    source_payload = json.loads(source_path.read_text(encoding="utf-8"))
    source_payload["representative_failures"].append(
        {
            "failure_id": "mutated_real_ring2_anchor",
            "failure_kind": "mutation_probe",
            "public_status": "test_only_mutation",
        }
    )
    source_path.write_text(json.dumps(source_payload, indent=2, sort_keys=True), encoding="utf-8")
    checks_payload["checks"][0]["source_digest_refs"] = [_sha256_file(source_path)]
    checks_path.write_text(json.dumps(checks_payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_evidence_bundle(
        bundle_input,
        tmp_path / "receipts",
        command="pytest",
    )
    row = result["proof_receipts"][0]

    assert result["status"] == "blocked"
    assert result["accepted_check_ids"] == []
    assert result["rejected_check_ids"] == ["ring2_failure_taxonomy_exported_anchor_check"]
    assert "source_digest_mismatch" in row["semantic_rejection_reasons"]
    finding = _finding_for(result, "ring2_failure_taxonomy_exported_anchor_check")
    assert finding["error_code"] == "EVIDENCE_RECEIPT_ANCHOR_RECOMPUTE_FAILED"
    assert finding["semantic_rejection_reasons"] == ["source_digest_mismatch"]
    assert row["actual_source_digest_mismatches"] == [
        {
            "source_ref": source_ref,
            "expected_sha256": SOURCE_DIGESTS[source_ref],
            "actual_sha256": _sha256_file(source_path),
        }
    ]


def test_proof_diagnostic_evidence_spine_rejects_removed_failure_taxonomy_semantics(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    _copy_public_evidence_bundle_tree(public_root)
    bundle_input = (
        public_root / "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle"
    )
    checks_path = bundle_input / "checks.json"
    checks_payload = json.loads(checks_path.read_text(encoding="utf-8"))
    source_ref = (
        "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "premise_retrieval_graph_v0/failure_taxonomy_report.json"
    )
    source_path = proof_spine._resolve_public_ref(public_root, source_ref)
    assert source_path is not None
    source_payload = json.loads(source_path.read_text(encoding="utf-8"))
    source_payload["failure_taxonomy"] = {}
    source_payload.pop("representative_failures", None)
    source_path.write_text(json.dumps(source_payload, indent=2, sort_keys=True), encoding="utf-8")
    checks_payload["checks"][0]["source_digest_refs"] = [_sha256_file(source_path)]
    checks_path.write_text(json.dumps(checks_payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_evidence_bundle(
        bundle_input,
        tmp_path / "receipts",
        command="pytest",
    )
    row = result["proof_receipts"][0]
    finding = _finding_for(result, "ring2_failure_taxonomy_exported_anchor_check")

    assert result["status"] == "blocked"
    assert result["accepted_check_ids"] == []
    assert result["rejected_check_ids"] == ["ring2_failure_taxonomy_exported_anchor_check"]
    assert row["semantic_floor"]["missing_source_semantics"] == [
        "failure_taxonomy_report",
        "failure_taxonomy_representative_failures",
    ]
    assert row["semantic_rejection_reasons"] == [
        "source_digest_mismatch",
        "missing_failure_taxonomy_report",
        "missing_failure_taxonomy_representative_failures",
    ]
    assert finding["error_code"] == "EVIDENCE_RECEIPT_ANCHOR_RECOMPUTE_FAILED"
    assert finding["semantic_rejection_reasons"] == row["semantic_rejection_reasons"]
    assert row["legacy_expected_result_label_present"] is True
    assert row["legacy_expected_result_label_authority"] == (
        "ignored_non_authoritative_fixture_label"
    )


def test_proof_diagnostic_evidence_spine_rejects_mutated_real_receipt_anchor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    _copy_public_evidence_bundle_tree(public_root)
    bundle_input = (
        public_root / "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle"
    )
    receipt_ref = (
        "receipts/first_wave/formal_math_verifier_trace_repair_loop/"
        "verifier_trace_repair_board.json"
    )
    receipt_path = proof_spine._resolve_public_ref(public_root, receipt_ref)
    assert receipt_path is not None
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_payload["failure_mode_ledger"] = []
    receipt_path.write_text(
        json.dumps(receipt_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = run_evidence_bundle(
        bundle_input,
        tmp_path / "receipts",
        command="pytest",
    )
    row = result["proof_receipts"][0]

    assert result["status"] == "blocked"
    assert result["accepted_check_ids"] == []
    assert result["rejected_check_ids"] == ["ring2_failure_taxonomy_exported_anchor_check"]
    assert "missing_failure_mode_ledger" in row["semantic_rejection_reasons"]
    finding = _finding_for(result, "ring2_failure_taxonomy_exported_anchor_check")
    assert finding["error_code"] == "EVIDENCE_RECEIPT_ANCHOR_RECOMPUTE_FAILED"
    assert finding["semantic_rejection_reasons"] == [
        "missing_failure_mode_ledger"
    ]


def test_proof_diagnostic_evidence_spine_rejects_unbacked_real_source_receipt_anchor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    _copy_public_evidence_bundle_tree(public_root)
    bundle_input = (
        public_root / "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle"
    )
    source_ref = (
        "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "premise_retrieval_graph_v0/failure_taxonomy_report.json"
    )
    receipt_ref = (
        "receipts/first_wave/formal_evidence_cell_anchor_resolver/"
        "evidence_cell_anchor_board.json"
    )
    receipt_path = proof_spine._resolve_public_ref(public_root, receipt_ref)
    assert receipt_path is not None
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_payload["source_refs"] = [
        ref for ref in receipt_payload["source_refs"] if ref != source_ref
    ]
    receipt_payload["source_digests"].pop(source_ref)
    receipt_path.write_text(
        json.dumps(receipt_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = run_evidence_bundle(
        bundle_input,
        tmp_path / "receipts",
        command="pytest",
    )
    row = result["proof_receipts"][0]

    assert result["status"] == "blocked"
    assert result["accepted_check_ids"] == []
    assert result["rejected_check_ids"] == ["ring2_failure_taxonomy_exported_anchor_check"]
    assert row["source_refs_not_backed_by_receipts"] == [source_ref]
    assert row["source_digest_refs_not_backed_by_receipts"] == [source_ref]
    assert row["source_digest_basis_by_ref"][source_ref] == (
        "module_floor_unbacked_by_selected_receipts"
    )
    finding = _finding_for(result, "ring2_failure_taxonomy_exported_anchor_check")
    assert finding["error_code"] == "EVIDENCE_RECEIPT_ANCHOR_RECOMPUTE_FAILED"
    assert finding["semantic_rejection_reasons"] == [
        "source_digest_not_receipt_backed",
        "source_ref_not_backed_by_receipt_anchor",
    ]


def test_proof_diagnostic_evidence_spine_rejects_tampered_copied_ring2_artifact(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    _copy_public_evidence_bundle_tree(public_root)
    artifact = PUBLIC_RING2_ARTIFACT_IMPORTS[0]
    target_path = public_root / artifact["target_ref"]
    target_path.write_text(
        target_path.read_text(encoding="utf-8") + "\n{\"tamper\": true}\n",
        encoding="utf-8",
    )

    result = run_evidence_bundle(
        public_root / "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle",
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["copied_macro_body_digest_status"] == "blocked"
    assert result["copied_macro_body_missing_target_refs"] == []
    assert result["copied_macro_body_missing_files"] == []
    assert result["copied_macro_body_digest_mismatches"] == [
        {
            "artifact_id": artifact["artifact_id"],
            "source_ref": artifact["source_ref"],
            "target_ref": artifact["target_ref"],
            "expected_sha256": artifact["sha256"],
            "actual_sha256": _sha256_file(target_path),
            "source_sha256": SOURCE_DIGESTS[artifact["source_ref"]],
        }
    ]


def test_proof_diagnostic_evidence_spine_rejects_manifest_relabelled_copied_ring2_artifact(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    _copy_public_evidence_bundle_tree(public_root)
    bundle_input = public_root / "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle"
    manifest_path = bundle_input / "bundle_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = next(
        row
        for row in PUBLIC_RING2_ARTIFACT_IMPORTS
        if row["copy_policy"] == "source_faithful_public_light_edit"
    )
    target_path = public_root / artifact["target_ref"]
    target_payload = json.loads(target_path.read_text(encoding="utf-8"))
    target_payload["mutation_probe"] = "manifest_relabel_should_not_authorize_artifact"
    target_path.write_text(
        json.dumps(target_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    mutated_sha256 = _sha256_file(target_path)
    for row in manifest["copied_macro_body_artifacts"]:
        if row["target_ref"] == artifact["target_ref"]:
            row["sha256"] = mutated_sha256
            row["target_sha256"] = mutated_sha256
            break
    else:
        raise AssertionError("expected artifact row in copied_macro_body_artifacts")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    result = run_evidence_bundle(
        bundle_input,
        tmp_path / "receipts",
        command="pytest",
    )
    copied_by_id = {
        row["artifact_id"]: row for row in result["copied_macro_body_artifacts"]
    }

    assert result["status"] == "blocked"
    assert result["copied_macro_body_digest_status"] == "blocked"
    assert copied_by_id[artifact["artifact_id"]]["manifest_sha256"] == mutated_sha256
    assert copied_by_id[artifact["artifact_id"]]["sha256"] == artifact["sha256"]
    assert copied_by_id[artifact["artifact_id"]]["manifest_matches_expected_import"] is False
    assert result["copied_macro_body_digest_mismatches"] == [
        {
            "artifact_id": artifact["artifact_id"],
            "source_ref": artifact["source_ref"],
            "target_ref": artifact["target_ref"],
            "expected_sha256": artifact["sha256"],
            "actual_sha256": mutated_sha256,
            "source_sha256": SOURCE_DIGESTS[artifact["source_ref"]],
        }
    ]


def test_proof_diagnostic_evidence_spine_rejects_tampered_source_body_floor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    _copy_public_evidence_bundle_tree(public_root)
    bundle_input = public_root / "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle"
    manifest_path = bundle_input / "source_body_floor/source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module = manifest["modules"][0]
    target_path = bundle_input / "source_body_floor" / module["path"]
    target_path.write_text(
        target_path.read_text(encoding="utf-8")
        + "\n# mutation probe: source body floor changed\n",
        encoding="utf-8",
    )

    result = run_evidence_bundle(
        bundle_input,
        tmp_path / "receipts",
        command="pytest",
    )
    row = result["source_body_floor_artifacts"][0]

    assert result["status"] == "blocked"
    assert result["source_body_floor_digest_status"] == "blocked"
    assert row["digest_status"] == "blocked"
    assert row["actual_sha256"] != row["sha256"]
    assert result["source_body_floor_digest_mismatches"] == [
        {
            "module_id": module["module_id"],
            "source_ref": module["source_ref"],
            "target_ref": module["target_ref"],
            "expected_sha256": module["sha256"],
            "actual_sha256": row["actual_sha256"],
            "missing_anchors": [],
            "line_count": str(row["line_count"]),
            "byte_count": str(row["byte_count"]),
        }
    ]


def test_proof_diagnostic_evidence_spine_rejects_manifest_relabelled_source_body_floor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    _copy_public_evidence_bundle_tree(public_root)
    bundle_input = public_root / "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle"
    manifest_path = bundle_input / "source_body_floor/source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module = manifest["modules"][0]
    target_path = bundle_input / "source_body_floor" / module["path"]
    target_path.write_text(
        target_path.read_text(encoding="utf-8")
        + "\n# mutation probe: source body manifest relabel\n",
        encoding="utf-8",
    )
    mutated_sha256 = _sha256_file(target_path)
    module["sha256"] = mutated_sha256
    module["target_sha256"] = mutated_sha256
    module["line_count"] = len(target_path.read_text(encoding="utf-8").splitlines())
    module["target_line_count"] = module["line_count"]
    module["byte_count"] = len(target_path.read_text(encoding="utf-8").encode("utf-8"))
    module["target_byte_count"] = module["byte_count"]
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    result = run_evidence_bundle(
        bundle_input,
        tmp_path / "receipts",
        command="pytest",
    )
    row = result["source_body_floor_artifacts"][0]

    assert result["status"] == "blocked"
    assert result["source_body_floor_digest_status"] == "blocked"
    assert row["manifest_sha256"] == mutated_sha256
    assert row["sha256"] == module["source_sha256"]
    assert row["manifest_matches_expected_import"] is False
    assert result["source_body_floor_digest_mismatches"] == [
        {
            "module_id": module["module_id"],
            "source_ref": module["source_ref"],
            "target_ref": module["target_ref"],
            "expected_sha256": module["source_sha256"],
            "actual_sha256": mutated_sha256,
            "missing_anchors": [],
            "line_count": str(row["line_count"]),
            "byte_count": str(row["byte_count"]),
        }
    ]


def test_proof_diagnostic_evidence_spine_diagnostic_overclaim_moves_bundle_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    _copy_public_evidence_bundle_tree(public_root)
    bundle_input = public_root / "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle"
    diagnostic_path = bundle_input / "diagnostic_rows.json"
    payload = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    payload["diagnostic_rows"][0]["claims_runtime_correctness"] = True
    diagnostic_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_evidence_bundle(
        bundle_input,
        tmp_path / "receipts",
        command="pytest",
    )
    row = result["diagnostic_rows"][0]

    assert result["status"] == "blocked"
    assert result["accepted_check_ids"] == ["ring2_failure_taxonomy_exported_anchor_check"]
    assert result["rejected_check_ids"] == []
    assert result["accepted_diagnostic_row_ids"] == []
    assert result["rejected_diagnostic_row_ids"] == [
        "ring2_failure_taxonomy_exported_anchor_retained"
    ]
    assert row["semantic_rejection_reasons"] == [
        "diagnostic_row_claims_runtime_correctness"
    ]
    assert result["error_codes"] == ["DIAGNOSTIC_ROW_ANCHOR_RECOMPUTE_FAILED"]


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


def test_proof_diagnostic_evidence_spine_card_is_available_from_top_level_cli(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "receipts"

    assert (
        cli.main(
            [
                "proof-diagnostic-evidence-spine",
                "run",
                "--input",
                str(PROOF_FIXTURE_INPUT),
                "--out",
                str(out_dir),
                "--card",
            ]
        )
        == 0
    )
    card = json.loads(capsys.readouterr().out)

    assert card["schema_version"] == "proof_diagnostic_evidence_spine_card_v1"
    assert card["status"] == "pass"
    assert card["organ_id"] == "proof_diagnostic_evidence_spine"
    assert card["input_mode"] == "fixture_regression"
    assert card["source_fingerprint_status"] == "stale"
    assert card["source_fingerprint_interpretation"]["status"] == "stale"
    assert (
        "retained as expected diagnostic evidence"
        in card["source_fingerprint_interpretation"]["meaning"]
    )
    assert "proof_receipts" in card["omitted_full_payload_keys"]


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
    _copy_public_fixture_tree(public_root)

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
        assert "/Users/example" not in text
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
            "forbidden_key_paths": ["ground_truth_proof", "proof_body", "provider_output_body"],
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
    _copy_public_fixture_tree(public_root)
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
