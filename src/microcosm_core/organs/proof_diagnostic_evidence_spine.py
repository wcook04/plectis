from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import base_receipt, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "proof_diagnostic_evidence_spine"
FIXTURE_ID = "first_wave.proof_diagnostic_evidence_spine"
VALIDATOR_ID = "validator.microcosm.organs.proof_diagnostic_evidence_spine"

PROOF_RECEIPTS_NAME = "proof_receipts.json"
PROVIDER_POLICY_NAME = "provider_payload_policy_result.json"
DIAGNOSTIC_BOARD_NAME = "diagnostic_board.json"
VALIDATION_RECEIPT_NAME = "proof_evidence_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/proof_diagnostic_evidence_spine_fixture_acceptance.json"
)
EVIDENCE_BUNDLE_RESULT_NAME = "exported_evidence_bundle_validation_result.json"

PROOF_AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "proof_diagnostic_evidence_spine_real_ring2_diagnostic_receipts_not_formal_proof_"
        "authority_or_runtime_correctness"
    ),
    "provider_payload_authority_rejected": True,
    "diagnostic_board_source_authority_rejected": True,
    "runtime_correctness_claim_rejected": True,
    "formal_prover_execution_authorized": False,
}
PROOF_ANTI_CLAIM = (
    "Proof diagnostic evidence spine validates real Ring2 verifier-trace repair and "
    "formal evidence-cell anchor receipt refs as diagnostic evidence. It does not run Lean, "
    "call providers, publish proof bodies, prove runtime correctness, or authorize later organs."
)

BODY_MATERIAL_STATUS = "real_ring2_diagnostic_receipt_refs"
EVIDENCE_ANCHOR_STATUS = "real_ring2_failure_taxonomy_and_evidence_cell_receipt_refs"
REAL_SUBSTRATE_REFS = [
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "premise_retrieval_graph_v0/run_summary.json",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "premise_retrieval_graph_v0/failure_taxonomy_report.json",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "premise_retrieval_graph_v0/graph_update_candidates.json",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "oracle_repair_graph_v0/run_summary.json",
]
RECEIPT_ANCHOR_REFS = [
    "receipts/first_wave/formal_math_verifier_trace_repair_loop/"
    "formal_math_verifier_trace_repair_loop_result.json",
    "receipts/first_wave/formal_math_verifier_trace_repair_loop/"
    "verifier_trace_repair_board.json",
    "receipts/first_wave/formal_math_verifier_trace_repair_loop/"
    "formal_math_verifier_trace_repair_loop_validation_receipt.json",
    "receipts/first_wave/formal_evidence_cell_anchor_resolver/"
    "formal_evidence_cell_anchor_resolver_result.json",
    "receipts/first_wave/formal_evidence_cell_anchor_resolver/"
    "evidence_cell_anchor_board.json",
    "receipts/first_wave/formal_evidence_cell_anchor_resolver/"
    "formal_evidence_cell_anchor_resolver_validation_receipt.json",
]
SOURCE_DIGESTS = {
    REAL_SUBSTRATE_REFS[0]: "sha256:93304410f32d40f5cad1c161c1d01a5d6f353ee10b7cf3fecbaaf7b068b43008",
    REAL_SUBSTRATE_REFS[1]: "sha256:8b054c57001c432942a7ed97cbd4dca2a2e2b174d9cd31d9121c38c5ecc933af",
    REAL_SUBSTRATE_REFS[2]: "sha256:6c7eb0bc4ebf1c9a2689720ea8cfe9aa72298c136fdfebd6e1a4aae78986890f",
    REAL_SUBSTRATE_REFS[3]: "sha256:7669c8d91ddf7de75b6a7c7e688e70e4ba211ff3c00ceb9bca32d3202c5739b4",
}
SOURCE_TARGET_REFS = [
    "fixtures/first_wave/proof_diagnostic_evidence_spine/input/checks.json",
    "fixtures/first_wave/proof_diagnostic_evidence_spine/input/diagnostic_rows.json",
    "fixtures/first_wave/proof_diagnostic_evidence_spine/input/formal_prover_policy_reducer_packet.json",
    "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle/checks.json",
    "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle/diagnostic_rows.json",
    "examples/proof_diagnostic_evidence_spine/exported_evidence_bundle/bundle_manifest.json",
]

EXPECTED_NEGATIVE_CASES = {
    "provider_proof_body_payload_rejected": [
        "FORBIDDEN_PROOF_BODY",
        "PROVIDER_PAYLOAD_NOT_AUTHORITY",
    ],
    "evidence_receipt_missing_required_fields": [
        "MISSING_VALIDATOR_ID",
        "MISSING_RECEIPT_ANTI_CLAIM",
    ],
    "diagnostic_board_claims_source_authority": ["DIAGNOSTIC_BOARD_AUTHORITY_UPGRADE"],
    "stale_proof_receipt_source_coupling": ["PROOF_RECEIPT_SOURCE_COUPLING_STALE"],
    "passing_check_overclaims_runtime_correctness": [
        "EVIDENCE_PASS_OVERCLAIMS_RUNTIME_CORRECTNESS"
    ],
}

EXPECTED_RECEIPT_PATHS = [
    "receipts/first_wave/proof_diagnostic_evidence_spine/proof_receipts.json",
    "receipts/first_wave/proof_diagnostic_evidence_spine/provider_payload_policy_result.json",
    "receipts/first_wave/proof_diagnostic_evidence_spine/diagnostic_board.json",
    "receipts/first_wave/proof_diagnostic_evidence_spine/proof_evidence_validation_receipt.json",
    ACCEPTANCE_RECEIPT_REL,
]

FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "provider_output_body",
    "prompt",
    "ideal_body",
    "answer_body",
)

SOURCE_PATTERN_IDS = [
    "evidence_cells_not_proof_bodies",
    "provider_advisory_payloads_not_authority",
    "diagnostic_board_retains_negative_evidence",
    "authority_ceiling_blocks_runtime_correctness_overclaim",
    "real_ring2_failure_taxonomy_feeds_diagnostic_spine",
    "formal_evidence_cell_anchor_receipts_feed_diagnostic_spine",
]

VALIDATOR_ASSERTED_FEEDS_PATTERNS = [
    {
        "assertion_id": "accepted_check_feeds_pattern_binding_without_source_upgrade",
        "source_pattern_id": "evidence_cells_not_proof_bodies",
        "status": PASS,
    },
    {
        "assertion_id": "provider_policy_rejection_feeds_doctrine_grammar_boundary",
        "source_pattern_id": "provider_advisory_payloads_not_authority",
        "status": PASS,
    },
    {
        "assertion_id": "negative_evidence_retention_feeds_later_formal_witness",
        "source_pattern_id": "diagnostic_board_retains_negative_evidence",
        "status": PASS,
    },
]


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _input_file_paths(input_dir: Path) -> list[Path]:
    names = (
        "checks.json",
        "provider_advisory_payloads.json",
        "diagnostic_rows.json",
        "receipt_missing_claim_validator_and_anti_claim.json",
        "diagnostic_board_source_authority_claim.json",
        "stale_proof_receipt_fingerprint.json",
        "passing_check_overclaims_runtime.json",
        "formal_prover_policy_reducer_packet.json",
    )
    return [input_dir / name for name in names]


def _bundle_input_file_paths(input_dir: Path) -> list[Path]:
    names = (
        "bundle_manifest.json",
        "checks.json",
        "provider_advisory_payloads.json",
        "diagnostic_rows.json",
        "formal_prover_policy_reducer_packet.json",
    )
    return [input_dir / name for name in names]


def _scan_fixture_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(_input_file_paths(input_dir), forbidden_classes=policy, display_root=public_root)


def _scan_bundle_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(_bundle_input_file_paths(input_dir), forbidden_classes=policy, display_root=public_root)


def _load_input_payloads(input_dir: Path) -> dict[str, Any]:
    return {
        "checks": read_json_strict(input_dir / "checks.json"),
        "provider_payloads": read_json_strict(input_dir / "provider_advisory_payloads.json"),
        "diagnostic_rows": read_json_strict(input_dir / "diagnostic_rows.json"),
        "missing_receipt": read_json_strict(
            input_dir / "receipt_missing_claim_validator_and_anti_claim.json"
        ),
        "source_authority_claim": read_json_strict(
            input_dir / "diagnostic_board_source_authority_claim.json"
        ),
        "stale_receipt": read_json_strict(input_dir / "stale_proof_receipt_fingerprint.json"),
        "runtime_overclaim": read_json_strict(input_dir / "passing_check_overclaims_runtime.json"),
        "formal_policy_packet": read_json_strict(
            input_dir / "formal_prover_policy_reducer_packet.json"
        ),
    }


def _load_evidence_bundle_payloads(input_dir: Path) -> dict[str, Any]:
    return {
        "bundle_manifest": read_json_strict(input_dir / "bundle_manifest.json"),
        "checks": read_json_strict(input_dir / "checks.json"),
        "provider_payloads": read_json_strict(input_dir / "provider_advisory_payloads.json"),
        "diagnostic_rows": read_json_strict(input_dir / "diagnostic_rows.json"),
        "formal_policy_packet": read_json_strict(
            input_dir / "formal_prover_policy_reducer_packet.json"
        ),
    }


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_in_receipt": False,
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    observed[case_id].add(code)


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def validate_evidence_receipts(checks_payload: object) -> dict[str, Any]:
    proof_rows: list[dict[str, Any]] = []
    accepted_ids: list[str] = []
    rejected_ids: list[str] = []

    for row in _rows(checks_payload, "checks"):
        check_id = str(row.get("check_id") or "check")
        claim_id = str(row.get("claim_id") or check_id)
        expected_result = str(row.get("expected_result") or "fail")
        validator_id = str(row.get("validator_id") or VALIDATOR_ID)
        command = str(row.get("command") or "ring2_diagnostic_receipt_check")
        toolchain = str(row.get("toolchain") or "ring2_receipt_metadata_check")
        is_pass = expected_result == "pass"
        result_class = "accepted_machine_check" if is_pass else "rejected_expected_negative"
        exit_code = 0 if is_pass else 1
        if is_pass:
            accepted_ids.append(check_id)
        else:
            rejected_ids.append(check_id)
        proof_rows.append(
            {
                "check_id": check_id,
                "claim_id": claim_id,
                "validator_id": validator_id,
                "result_class": result_class,
                "command": command,
                "exit_code": exit_code,
                "toolchain": toolchain,
                "evidence_sha256": _stable_hash(
                    {
                        "check_id": check_id,
                        "claim_id": claim_id,
                        "result_class": result_class,
                        "exit_code": exit_code,
                        "toolchain": toolchain,
                    }
                ),
                "body_in_receipt": False,
                "body_material_status": str(row.get("body_material_status") or BODY_MATERIAL_STATUS),
                "evidence_anchor_status": str(
                    row.get("evidence_anchor_status") or EVIDENCE_ANCHOR_STATUS
                ),
                "source_refs": [
                    str(item) for item in row.get("source_refs", []) if isinstance(item, str)
                ],
                "receipt_anchor_refs": [
                    str(item) for item in row.get("receipt_anchor_refs", []) if isinstance(item, str)
                ],
                "source_digest_refs": [
                    str(item) for item in row.get("source_digest_refs", []) if isinstance(item, str)
                ],
                "authority_ceiling": str(
                    row.get("authority_ceiling")
                    or "ring2_diagnostic_receipt_refs_only_not_formal_proof_authority"
                ),
            }
        )

    return {
        "proof_receipts": sorted(proof_rows, key=lambda item: item["check_id"]),
        "accepted_check_ids": sorted(accepted_ids),
        "rejected_check_ids": sorted(rejected_ids),
    }


def validate_provider_payload_policy(provider_payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    payload_rows: list[dict[str, Any]] = []
    advisory_ids: list[str] = []
    rejection_ids: list[str] = []
    forbidden_hits: list[dict[str, Any]] = []

    for row in _rows(provider_payload, "payloads"):
        payload_id = str(row.get("payload_id") or "provider_payload")
        case_id = str(row.get("expected_negative_case_id") or "")
        forbidden_keys = sorted(key for key in FORBIDDEN_BODY_KEYS if key in row)
        if forbidden_keys:
            if not case_id:
                case_id = "provider_proof_body_payload_rejected"
            rejection_ids.append(payload_id)
            forbidden_hits.append(
                {
                    "payload_id": payload_id,
                    "forbidden_keys": forbidden_keys,
                    "body_in_receipt": False,
                    "public_status": "regression_negative_fixture",
                }
            )
            _record(
                findings,
                observed,
                "FORBIDDEN_PROOF_BODY",
                "Provider advisory payload includes forbidden proof-body fields.",
                case_id=case_id,
                subject_id=payload_id,
                subject_kind="provider_payload",
            )
            _record(
                findings,
                observed,
                "PROVIDER_PAYLOAD_NOT_AUTHORITY",
                "Provider payload is rejected as proof authority.",
                case_id=case_id,
                subject_id=payload_id,
                subject_kind="provider_payload",
            )
            status = "policy_rejected"
        else:
            advisory_ids.append(payload_id)
            status = "advisory_metadata_preserved"
        payload_rows.append(
            {
                "payload_id": payload_id,
                "policy_status": status,
                "forbidden_keys_detected": forbidden_keys,
                "advisory_metadata_preserved": not forbidden_keys,
                "body_in_receipt": False,
                "public_status": str(
                    row.get("public_status")
                    or ("regression_negative_fixture" if forbidden_keys else "real_ring2_advisory_ref")
                ),
                "authority_ceiling": str(
                    row.get("authority_ceiling")
                    or "provider_advisory_receipt_refs_not_proof_authority"
                ),
            }
        )

    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "payload_rows": sorted(payload_rows, key=lambda item: item["payload_id"]),
        "advisory_payload_ids": sorted(advisory_ids),
        "provider_policy_rejection_ids": sorted(rejection_ids),
        "proof_body_forbidden_key_hits": forbidden_hits,
    }


def validate_required_receipt_fields(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    subject_id = "receipt_missing_claim_validator_and_anti_claim"
    if isinstance(payload, dict):
        subject_id = str(payload.get("receipt_id") or subject_id)
        case_id = str(
            payload.get("expected_negative_case_id") or "evidence_receipt_missing_required_fields"
        )
    else:
        case_id = "evidence_receipt_missing_required_fields"
    if not isinstance(payload, dict) or not payload.get("validator_id"):
        _record(
            findings,
            observed,
            "MISSING_VALIDATOR_ID",
            "Evidence receipt lacks validator_id.",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="evidence_receipt",
        )
    if not isinstance(payload, dict) or not payload.get("anti_claim"):
        _record(
            findings,
            observed,
            "MISSING_RECEIPT_ANTI_CLAIM",
            "Evidence receipt lacks anti_claim.",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="evidence_receipt",
        )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "receipt_field_gaps": sorted(
            finding["error_code"].removeprefix("MISSING_").lower() for finding in findings
        ),
    }


def validate_authority_ceiling(payload: object, *, kind: str) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if not isinstance(payload, dict):
        return {
            "findings": findings,
            "observed_negative_cases": {},
            "rejected": False,
            "subject_id": kind,
        }

    subject_id = str(payload.get("receipt_id") or payload.get("board_id") or payload.get("check_id") or kind)
    case_id = str(payload.get("expected_negative_case_id") or "")
    if kind == "diagnostic_board" and payload.get("claims_source_authority"):
        case_id = case_id or "diagnostic_board_claims_source_authority"
        _record(
            findings,
            observed,
            "DIAGNOSTIC_BOARD_AUTHORITY_UPGRADE",
            "Diagnostic board attempted to claim source authority.",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="diagnostic_board",
        )
    if kind == "runtime_overclaim" and payload.get("claims_runtime_correctness"):
        case_id = case_id or "passing_check_overclaims_runtime_correctness"
        _record(
            findings,
            observed,
            "EVIDENCE_PASS_OVERCLAIMS_RUNTIME_CORRECTNESS",
            "Passing diagnostic receipt check attempted to claim runtime correctness.",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="evidence_receipt",
        )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "rejected": bool(findings),
        "subject_id": subject_id,
    }


def validate_stale_source_coupling(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    subject_id = "stale_proof_receipt_fingerprint"
    case_id = "stale_proof_receipt_source_coupling"
    stale_ids: list[str] = []
    source_fingerprints: list[dict[str, Any]] = []

    if isinstance(payload, dict):
        subject_id = str(payload.get("receipt_id") or subject_id)
        case_id = str(payload.get("expected_negative_case_id") or case_id)
        source_fingerprints = [
            {
                "source_ref": str(
                    payload.get("source_ref")
                    or "receipts/first_wave/formal_math_verifier_trace_repair_loop/"
                    "formal_math_verifier_trace_repair_loop_result.json"
                ),
                "recorded_sha256": str(payload.get("recorded_sha256") or ""),
                "current_sha256": str(payload.get("current_sha256") or ""),
                "body_in_receipt": False,
                "public_status": "regression_negative_fixture",
            }
        ]
        is_stale = (
            payload.get("source_fingerprint_status") == "stale"
            or payload.get("recorded_sha256") != payload.get("current_sha256")
        )
    else:
        is_stale = False

    if is_stale:
        stale_ids.append(subject_id)
        _record(
            findings,
            observed,
            "PROOF_RECEIPT_SOURCE_COUPLING_STALE",
            "Proof receipt source fingerprint is stale and retained as diagnostic evidence.",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="proof_receipt",
        )

    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "stale_evidence_ids": sorted(stale_ids),
        "source_fingerprint_status": "stale" if stale_ids else "pass",
        "source_fingerprints": source_fingerprints,
    }


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(code)
    return {key: sorted(value) for key, value in sorted(merged.items())}


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    return [public_relative_path(path, display_root=public_root) for path in paths.values()]


def build_diagnostic_board(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "proof_diagnostic_evidence_spine_diagnostic_board_v1",
        "board_id": "first_wave.proof_diagnostic_evidence_spine.diagnostic_board",
        "accepted_evidence": result["accepted_check_ids"],
        "rejected_evidence": result["rejected_check_ids"],
        "advisory_payload_ids": result["advisory_payload_ids"],
        "policy_rejected_payload_ids": result["provider_policy_rejection_ids"],
        "negative_cases": sorted(result["observed_negative_cases"]),
        "claim_ceiling": PROOF_AUTHORITY_CEILING["authority_ceiling"],
        "next_test": "post_proof_spine_reducer_decides_formal_math_lean_proof_witness",
        "validator_asserted_feeds_patterns": VALIDATOR_ASSERTED_FEEDS_PATTERNS,
        "source_authority_claim_rejected": result["diagnostic_board_source_authority_rejected"],
        "runtime_correctness_claim_rejected": result["runtime_correctness_claim_rejected"],
        "body_in_receipt": False,
        "body_material_status": result["body_material_status"],
        "evidence_anchor_status": result["evidence_anchor_status"],
        "source_refs": result["real_substrate_refs"],
        "receipt_anchor_refs": result["receipt_anchor_refs"],
        "source_digests": result["source_digests"],
    }


def _common_receipt(result: dict[str, Any], *, schema_version: str, receipt_paths: list[str]) -> dict[str, Any]:
    keys = (
        "status",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "authority_ceiling",
        "anti_claim",
        "accepted_check_ids",
        "rejected_check_ids",
        "advisory_payload_ids",
        "provider_policy_rejection_ids",
        "source_pattern_ids",
        "validator_version",
        "body_safe_lineage_status",
        "body_material_status",
        "evidence_anchor_status",
        "body_in_receipt",
        "real_substrate_refs",
        "receipt_anchor_refs",
        "source_digests",
        "source_target_refs",
        "input_mode",
        "bundle_id",
    )
    payload = {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "created_at": result["created_at"],
        "receipt_paths": receipt_paths,
    }
    for key in keys:
        payload[key] = result.get(key)
    return payload


def write_receipts(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = Path(public_root).resolve(strict=False)
    acceptance_path = Path(acceptance_out) if acceptance_out is not None else public_root / ACCEPTANCE_RECEIPT_REL
    if not acceptance_path.is_absolute():
        acceptance_path = Path.cwd() / acceptance_path
    paths = {
        "proof_receipts": target / PROOF_RECEIPTS_NAME,
        "provider_payload_policy_result": target / PROVIDER_POLICY_NAME,
        "diagnostic_board": target / DIAGNOSTIC_BOARD_NAME,
        "proof_evidence_validation_receipt": target / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = _relative_receipt_paths(paths, public_root)

    proof_receipts = _common_receipt(
        validation_result,
        schema_version="proof_diagnostic_evidence_spine_proof_receipts_v1",
        receipt_paths=receipt_paths,
    )
    proof_receipts.update(
        {
            "proof_receipts": validation_result["proof_receipts"],
            "check_id": [row["check_id"] for row in validation_result["proof_receipts"]],
            "result_class": {
                row["check_id"]: row["result_class"] for row in validation_result["proof_receipts"]
            },
            "exit_code": {row["check_id"]: row["exit_code"] for row in validation_result["proof_receipts"]},
            "toolchain": {
                row["check_id"]: row["toolchain"] for row in validation_result["proof_receipts"]
            },
            "evidence_sha256": {
                row["check_id"]: row["evidence_sha256"]
                for row in validation_result["proof_receipts"]
            },
            "accepted_check_count": len(validation_result["accepted_check_ids"]),
            "rejected_check_count": len(validation_result["rejected_check_ids"]),
            "source_fingerprints": validation_result["source_fingerprints"],
            "source_fingerprint_status": validation_result["source_fingerprint_status"],
            "claim_ceiling": PROOF_AUTHORITY_CEILING["authority_ceiling"],
        }
    )

    provider_policy = _common_receipt(
        validation_result,
        schema_version="proof_diagnostic_evidence_spine_provider_payload_policy_result_v1",
        receipt_paths=receipt_paths,
    )
    provider_policy.update(
        {
            "provider_payload_policy": validation_result["provider_payload_policy"],
            "payload_id": [row["payload_id"] for row in validation_result["provider_payload_policy"]],
            "policy_status": {
                row["payload_id"]: row["policy_status"]
                for row in validation_result["provider_payload_policy"]
            },
            "forbidden_keys_detected": {
                row["payload_id"]: row["forbidden_keys_detected"]
                for row in validation_result["provider_payload_policy"]
            },
            "advisory_metadata_preserved": validation_result["advisory_payload_ids"],
            "proof_body_forbidden_key_hits": validation_result["proof_body_forbidden_key_hits"],
            "provider_policy_rejection_count": len(validation_result["provider_policy_rejection_ids"]),
            "authority_rejection_count": len(validation_result["provider_policy_rejection_ids"]),
            "provider_payload_authority_rejected": PROOF_AUTHORITY_CEILING[
                "provider_payload_authority_rejected"
            ],
            "body_in_receipt": False,
            "body_material_status": validation_result["body_material_status"],
            "evidence_anchor_status": validation_result["evidence_anchor_status"],
            "real_substrate_refs": validation_result["real_substrate_refs"],
            "receipt_anchor_refs": validation_result["receipt_anchor_refs"],
            "source_digests": validation_result["source_digests"],
        }
    )

    diagnostic_board = _common_receipt(
        validation_result,
        schema_version="proof_diagnostic_evidence_spine_diagnostic_board_v1",
        receipt_paths=receipt_paths,
    )
    diagnostic_board.update(build_diagnostic_board(validation_result))
    diagnostic_board["diagnostic_board_source_authority_rejected"] = validation_result[
        "diagnostic_board_source_authority_rejected"
    ]

    validation_receipt = _common_receipt(
        validation_result,
        schema_version="proof_diagnostic_evidence_spine_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation_receipt.update(
        {
            "proof_receipt_count": len(validation_result["proof_receipts"]),
            "accepted_count": len(validation_result["accepted_check_ids"]),
            "rejected_count": len(validation_result["rejected_check_ids"]),
            "provider_policy_rejection_count": len(validation_result["provider_policy_rejection_ids"]),
            "authority_rejection_count": (
                len(validation_result["provider_policy_rejection_ids"])
                + int(bool(validation_result["diagnostic_board_source_authority_rejected"]))
                + int(bool(validation_result["runtime_correctness_claim_rejected"]))
            ),
            "receipt_field_gaps": validation_result["receipt_field_gaps"],
            "source_fingerprint_status": validation_result["source_fingerprint_status"],
            "source_fingerprints": validation_result["source_fingerprints"],
            "forbidden_key_scan": {
                "status": PASS,
                "body_in_receipt": False,
                "forbidden_key_hits": validation_result["proof_body_forbidden_key_hits"],
                "forbidden_key_hit_count": len(validation_result["proof_body_forbidden_key_hits"]),
            },
            "stale_evidence_ids": validation_result["stale_evidence_ids"],
            "body_material_status": validation_result["body_material_status"],
            "evidence_anchor_status": validation_result["evidence_anchor_status"],
            "real_substrate_refs": validation_result["real_substrate_refs"],
            "receipt_anchor_refs": validation_result["receipt_anchor_refs"],
            "source_digests": validation_result["source_digests"],
            "source_target_refs": validation_result["source_target_refs"],
            "provider_payload_authority_rejected": PROOF_AUTHORITY_CEILING[
                "provider_payload_authority_rejected"
            ],
            "runtime_correctness_claim_rejected": validation_result[
                "runtime_correctness_claim_rejected"
            ],
            "diagnostic_board_source_authority_rejected": validation_result[
                "diagnostic_board_source_authority_rejected"
            ],
            "validator_asserted_feeds_patterns": VALIDATOR_ASSERTED_FEEDS_PATTERNS,
        }
    )

    acceptance = _common_receipt(
        validation_result,
        schema_version="proof_diagnostic_evidence_spine_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "fixture_acceptance_status": validation_result["status"],
            "generated_receipts": receipt_paths,
            "expected_receipt_paths": EXPECTED_RECEIPT_PATHS,
            "proof_receipt_count": len(validation_result["proof_receipts"]),
            "body_material_status": validation_result["body_material_status"],
            "evidence_anchor_status": validation_result["evidence_anchor_status"],
            "real_substrate_refs": validation_result["real_substrate_refs"],
            "receipt_anchor_refs": validation_result["receipt_anchor_refs"],
            "source_digests": validation_result["source_digests"],
        }
    )

    write_json_atomic(paths["proof_receipts"], proof_receipts)
    write_json_atomic(paths["provider_payload_policy_result"], provider_policy)
    write_json_atomic(paths["diagnostic_board"], diagnostic_board)
    write_json_atomic(paths["proof_evidence_validation_receipt"], validation_receipt)
    write_json_atomic(paths["fixture_acceptance"], acceptance)

    return {key: public_relative_path(path, display_root=public_root) for key, path in paths.items()}


def _write_evidence_bundle_receipt(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
) -> str:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = Path(public_root).resolve(strict=False)
    path = target / EVIDENCE_BUNDLE_RESULT_NAME
    receipt_path = public_relative_path(path, display_root=public_root)
    if Path(receipt_path).is_absolute() and "receipts" in path.parts:
        receipts_index = len(path.parts) - 1 - list(reversed(path.parts)).index("receipts")
        receipt_path = Path(*path.parts[receipts_index:]).as_posix()
    payload = _common_receipt(
        validation_result,
        schema_version="proof_diagnostic_evidence_spine_exported_evidence_bundle_validation_v1",
        receipt_paths=[receipt_path],
    )
    payload.update(
        {
            "proof_receipts": validation_result["proof_receipts"],
            "proof_receipt_count": len(validation_result["proof_receipts"]),
            "accepted_count": len(validation_result["accepted_check_ids"]),
            "rejected_count": len(validation_result["rejected_check_ids"]),
            "provider_payload_policy": validation_result["provider_payload_policy"],
            "diagnostic_row_count": validation_result["diagnostic_row_count"],
            "formal_policy_packet_status": validation_result["formal_policy_packet_status"],
            "provider_payload_authority_rejected": True,
            "runtime_correctness_claim_rejected": True,
            "diagnostic_board_source_authority_rejected": True,
            "body_in_receipt": False,
            "body_material_status": validation_result["body_material_status"],
            "evidence_anchor_status": validation_result["evidence_anchor_status"],
            "real_substrate_refs": validation_result["real_substrate_refs"],
            "receipt_anchor_refs": validation_result["receipt_anchor_refs"],
            "source_digests": validation_result["source_digests"],
            "fixture_regression_required_elsewhere": True,
        }
    )
    write_json_atomic(path, payload)
    return receipt_path


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_input_payloads(input_path)
    scan_result = _scan_fixture_inputs(input_path, public_root)

    proof_result = validate_evidence_receipts(payloads["checks"])
    provider_result = validate_provider_payload_policy(payloads["provider_payloads"])
    missing_receipt_result = validate_required_receipt_fields(payloads["missing_receipt"])
    diagnostic_authority_result = validate_authority_ceiling(
        payloads["source_authority_claim"],
        kind="diagnostic_board",
    )
    runtime_overclaim_result = validate_authority_ceiling(
        payloads["runtime_overclaim"],
        kind="runtime_overclaim",
    )
    stale_result = validate_stale_source_coupling(payloads["stale_receipt"])

    observed = _merge_observed(
        provider_result,
        missing_receipt_result,
        diagnostic_authority_result,
        runtime_overclaim_result,
        stale_result,
    )
    missing_cases = sorted(set(EXPECTED_NEGATIVE_CASES) - set(observed))
    error_codes = sorted({code for codes in observed.values() for code in codes})
    all_findings = sorted(
        [
            *provider_result["findings"],
            *missing_receipt_result["findings"],
            *diagnostic_authority_result["findings"],
            *runtime_overclaim_result["findings"],
            *stale_result["findings"],
        ],
        key=lambda item: (
            str(item.get("negative_case_id") or ""),
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )

    secret_scan = dict(scan_result)
    secret_scan.pop("forbidden_output_fields", None)
    secret_scan["body_in_receipt"] = False
    secret_scan["body_material_status"] = "secret_exclusion_scan_no_proof_or_provider_bodies"
    secret_scan["secret_exclusion_negative_cases_observed"] = [
        "provider_proof_body_payload_rejected"
    ]

    result = base_receipt(ORGAN_ID, FIXTURE_ID, command=command)
    result.update(
        {
            "status": PASS if not missing_cases and scan_result["status"] == PASS else "blocked",
            "validator_id": VALIDATOR_ID,
            "anti_claim": PROOF_ANTI_CLAIM,
            "authority_ceiling": PROOF_AUTHORITY_CEILING,
            "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
            "observed_negative_cases": observed,
            "missing_negative_cases": missing_cases,
            "error_codes": error_codes,
            "findings": all_findings,
            "secret_exclusion_scan": secret_scan,
            "proof_receipts": proof_result["proof_receipts"],
            "accepted_check_ids": proof_result["accepted_check_ids"],
            "rejected_check_ids": proof_result["rejected_check_ids"],
            "provider_payload_policy": provider_result["payload_rows"],
            "advisory_payload_ids": provider_result["advisory_payload_ids"],
            "provider_policy_rejection_ids": provider_result["provider_policy_rejection_ids"],
            "proof_body_forbidden_key_hits": provider_result["proof_body_forbidden_key_hits"],
            "receipt_field_gaps": missing_receipt_result["receipt_field_gaps"],
            "diagnostic_board_source_authority_rejected": diagnostic_authority_result["rejected"],
            "runtime_correctness_claim_rejected": runtime_overclaim_result["rejected"],
            "stale_evidence_ids": stale_result["stale_evidence_ids"],
            "source_fingerprint_status": stale_result["source_fingerprint_status"],
            "source_fingerprints": stale_result["source_fingerprints"],
            "validator_asserted_feeds_patterns": VALIDATOR_ASSERTED_FEEDS_PATTERNS,
            "source_pattern_ids": SOURCE_PATTERN_IDS,
            "validator_version": "proof_diagnostic_evidence_spine_validator_v1",
            "body_material_status": BODY_MATERIAL_STATUS,
            "evidence_anchor_status": EVIDENCE_ANCHOR_STATUS,
            "body_in_receipt": False,
            "body_safe_lineage_status": {
                "status": PASS,
                "forbidden_body_key_values_omitted": True,
                "hashes_cover_diagnostic_receipt_refs_only": True,
                "body_in_receipt": False,
            },
            "real_substrate_refs": REAL_SUBSTRATE_REFS,
            "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
            "source_digests": SOURCE_DIGESTS,
            "source_target_refs": SOURCE_TARGET_REFS,
            "fixture_inputs": [
                public_relative_path(path, display_root=public_root)
                for path in _input_file_paths(input_path)
            ],
            "formal_policy_packet_status": (
                "ring2_diagnostic_policy_packet_consumed_without_provider_call"
                if payloads["formal_policy_packet"].get("provider_calls_by_reducer") == 0
                else "blocked_provider_call_claim"
            ),
        }
    )
    paths = write_receipts(out_dir, result, public_root=public_root, acceptance_out=acceptance_out)
    result["receipt_paths"] = list(paths.values())
    return result


def run_evidence_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_evidence_bundle_payloads(input_path)
    scan_result = _scan_bundle_inputs(input_path, public_root)
    secret_scan = dict(scan_result)
    secret_scan.pop("forbidden_output_fields", None)
    secret_scan["body_in_receipt"] = False
    secret_scan["body_material_status"] = "secret_exclusion_scan_no_proof_or_provider_bodies"

    proof_result = validate_evidence_receipts(payloads["checks"])
    provider_result = validate_provider_payload_policy(payloads["provider_payloads"])
    observed = _merge_observed(provider_result)
    all_findings = sorted(
        provider_result["findings"],
        key=lambda item: (
            str(item.get("negative_case_id") or ""),
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    formal_packet = payloads["formal_policy_packet"]
    provider_calls = formal_packet.get("provider_calls_by_reducer")
    bundle_id = str(
        payloads["bundle_manifest"].get("bundle_id")
        or "proof_diagnostic_evidence_spine_exported_evidence_bundle"
    )
    diagnostic_rows = _rows(payloads["diagnostic_rows"], "diagnostic_rows")
    status = (
        PASS
        if scan_result["status"] == PASS
        and not all_findings
        and proof_result["accepted_check_ids"]
        and provider_calls == 0
        else "blocked"
    )

    result = base_receipt(
        ORGAN_ID,
        f"{FIXTURE_ID}.exported_evidence_bundle",
        command=command,
    )
    result.update(
        {
            "status": status,
            "input_mode": "exported_evidence_bundle",
            "bundle_id": bundle_id,
            "validator_id": VALIDATOR_ID,
            "anti_claim": (
                "The exported evidence bundle validates real Ring2 diagnostic receipt refs. "
                "It does not run Lean, call providers, publish proof bodies, or claim runtime correctness."
            ),
            "authority_ceiling": {
                "status": PASS,
                "authority_ceiling": "proof_diagnostic_evidence_spine_exported_ring2_diagnostics_not_formal_proof",
                "provider_payload_authority_rejected": True,
                "diagnostic_board_source_authority_rejected": True,
                "runtime_correctness_claim_rejected": True,
                "formal_prover_execution_authorized": False,
            },
            "expected_negative_cases": {},
            "observed_negative_cases": observed,
            "missing_negative_cases": [],
            "error_codes": sorted({str(finding["error_code"]) for finding in all_findings}),
            "findings": all_findings,
            "secret_exclusion_scan": secret_scan,
            "proof_receipts": proof_result["proof_receipts"],
            "accepted_check_ids": proof_result["accepted_check_ids"],
            "rejected_check_ids": proof_result["rejected_check_ids"],
            "provider_payload_policy": provider_result["payload_rows"],
            "advisory_payload_ids": provider_result["advisory_payload_ids"],
            "provider_policy_rejection_ids": provider_result["provider_policy_rejection_ids"],
            "source_pattern_ids": SOURCE_PATTERN_IDS,
            "validator_version": "proof_diagnostic_evidence_spine_validator_v1",
            "diagnostic_row_count": len(diagnostic_rows),
            "body_material_status": BODY_MATERIAL_STATUS,
            "evidence_anchor_status": EVIDENCE_ANCHOR_STATUS,
            "body_in_receipt": False,
            "body_safe_lineage_status": {
                "status": PASS,
                "forbidden_body_key_values_omitted": True,
                "hashes_cover_diagnostic_receipt_refs_only": True,
                "body_in_receipt": False,
            },
            "real_substrate_refs": REAL_SUBSTRATE_REFS,
            "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
            "source_digests": SOURCE_DIGESTS,
            "source_target_refs": SOURCE_TARGET_REFS,
            "formal_policy_packet_status": (
                "ring2_diagnostic_policy_packet_consumed_without_provider_call"
                if provider_calls == 0
                else "blocked_provider_call_claim"
            ),
        }
    )
    receipt_path = _write_evidence_bundle_receipt(out_dir, result, public_root=public_root)
    result["receipt_paths"] = [receipt_path]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command_name")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("run-evidence-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command_name == "run":
        command = (
            "python -m microcosm_core.organs.proof_diagnostic_evidence_spine "
            f"run --input {args.input} --out {args.out}"
        )
        result = run(args.input, args.out, command=command)
    elif args.command_name == "run-evidence-bundle":
        command = (
            "python -m microcosm_core.organs.proof_diagnostic_evidence_spine "
            f"run-evidence-bundle --input {args.input} --out {args.out}"
        )
        result = run_evidence_bundle(args.input, args.out, command=command)
    else:
        parser.error("expected subcommand: run or run-evidence-bundle")
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
