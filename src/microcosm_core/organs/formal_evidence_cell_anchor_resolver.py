from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "formal_evidence_cell_anchor_resolver"
FIXTURE_ID = "first_wave.formal_evidence_cell_anchor_resolver"
VALIDATOR_ID = "validator.microcosm.organs.formal_evidence_cell_anchor_resolver"

RESULT_NAME = "formal_evidence_cell_anchor_resolver_result.json"
BOARD_NAME = "evidence_cell_anchor_board.json"
VALIDATION_RECEIPT_NAME = "formal_evidence_cell_anchor_resolver_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "formal_evidence_cell_anchor_resolver_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_evidence_cell_anchor_bundle_validation_result.json"

INPUT_NAMES = (
    "projection_protocol.json",
    "paper_claims.json",
    "evidence_cell_registry.json",
    "claim_boundary_policy.json",
)
NEGATIVE_INPUT_NAMES = (
    "unknown_cell_overclaim.json",
    "missing_source_anchor.json",
    "proof_language_without_cell.json",
    "private_source_ref_leakage.json",
    "proof_body_leakage.json",
    "theorem_correctness_overclaim.json",
    "human_approval_as_evidence_cell.json",
)

EXPECTED_NEGATIVE_CASES = {
    "unknown_cell_overclaim": ["EVIDENCE_CELL_UNKNOWN_OVERCLAIM"],
    "missing_source_anchor": ["EVIDENCE_CELL_MISSING_SOURCE_ANCHOR"],
    "proof_language_without_cell": ["EVIDENCE_CELL_PROOF_LANGUAGE_WITHOUT_CELL"],
    "private_source_ref_leakage": ["EVIDENCE_CELL_PRIVATE_SOURCE_REF_FORBIDDEN"],
    "proof_body_leakage": ["EVIDENCE_CELL_PROOF_BODY_FORBIDDEN"],
    "theorem_correctness_overclaim": ["EVIDENCE_CELL_THEOREM_CORRECTNESS_OVERCLAIM"],
    "human_approval_as_evidence_cell": [
        "EVIDENCE_CELL_HUMAN_APPROVAL_NOT_PROOF_AUTHORITY"
    ],
}

FORBIDDEN_PROOF_KEYS = (
    "proof_body",
    "candidate_proof_body",
    "private_proof_body",
    "ground_truth_proof",
)
PRIVATE_SOURCE_KEYS = (
    "private_source_ref",
    "private_source_refs",
    "raw_source_path",
    "oracle_source_ref",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "formal_evidence_cell_anchor_real_runtime_receipt_not_theorem_authority",
    "formal_proof_authority": False,
    "theorem_correctness_authority": False,
    "lean_lake_execution_authorized": False,
    "proof_bodies_allowed": False,
    "private_source_refs_allowed": False,
    "human_approval_as_proof_authority": False,
    "provider_calls_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Formal evidence cell anchor resolver emits real runtime receipts over "
    "claim-to-cell resolution, source-anchor refs, claim-strength boundaries, "
    "and negative-case leakage controls. It does not prove theorem correctness, "
    "run Lean or Lake, call providers, expose non-receipt proof bodies or "
    "credential-equivalent private source refs, treat human approval as proof "
    "authority, or authorize release."
)


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    bundle_manifest = input_dir / "bundle_manifest.json"
    if bundle_manifest.is_file():
        paths.append(bundle_manifest)
    return paths


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


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


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )


def _has_forbidden_key(row: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(key in row for key in keys)


def _private_ref_present(row: dict[str, Any]) -> bool:
    if _has_forbidden_key(row, PRIVATE_SOURCE_KEYS):
        return True
    refs = _strings(row.get("source_anchor_refs"))
    return any(ref.startswith(("private:", "macro-private:", "/Users/")) for ref in refs)


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    evidence_anchor_status = str(protocol.get("evidence_anchor_status") or "")
    source_refs = _strings(protocol.get("source_refs"))
    source_digests_payload = protocol.get("source_digests", {})
    source_digests = (
        {
            str(key): str(value)
            for key, value in sorted(source_digests_payload.items())
            if key and isinstance(value, str) and value
        }
        if isinstance(source_digests_payload, dict)
        else {}
    )
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    public_runtime_refs = _strings(protocol.get("public_runtime_refs"))
    excluded = _rows(protocol, "secret_exclusion_material")
    findings: list[dict[str, Any]] = []
    if len(source_refs) < 3 or len(source_pattern_ids) < 2 or len(public_runtime_refs) < 3:
        findings.append(
            _finding(
                "EVIDENCE_CELL_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Evidence-cell projection must cite source refs, pattern ids, and public runtime refs.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for row in excluded:
        if not row.get("exclusion_receipt_ref"):
            findings.append(
                _finding(
                    "EVIDENCE_CELL_SECRET_EXCLUSION_RECEIPT_MISSING",
                    "Secret or credential-equivalent material must carry an exclusion receipt.",
                    case_id="projection_protocol_floor",
                    subject_id=str(row.get("material_id") or "secret_exclusion_material"),
                    subject_kind="projection_protocol",
                )
            )
    return {
        "status": PASS
        if source_refs
        and source_pattern_ids
        and projection_receipts
        and public_runtime_refs
        and not findings
        else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "evidence_anchor_status": evidence_anchor_status,
        "source_refs": source_refs,
        "source_digests": source_digests,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "public_runtime_refs": public_runtime_refs,
        "secret_exclusion_material_count": len(excluded),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_cell_registry(payload: object) -> dict[str, Any]:
    cells = _rows(payload, "evidence_cells")
    findings: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for row in cells:
        cell_id = str(row.get("cell_id") or "")
        anchors = _strings(row.get("source_anchor_refs"))
        machine_anchor_class = str(row.get("machine_anchor_class") or "")
        allowed = _strings(row.get("allowed_claim_strengths"))
        if not anchors:
            findings.append(
                _finding(
                    "EVIDENCE_CELL_MISSING_SOURCE_ANCHOR",
                    "Evidence cells require at least one public source-anchor ref.",
                    case_id="registry_floor",
                    subject_id=cell_id or "evidence_cell",
                    subject_kind="evidence_cell",
                )
            )
        if _private_ref_present(row):
            findings.append(
                _finding(
                    "EVIDENCE_CELL_PRIVATE_SOURCE_REF_FORBIDDEN",
                    "Evidence cells cannot expose private source refs.",
                    case_id="registry_floor",
                    subject_id=cell_id or "evidence_cell",
                    subject_kind="evidence_cell",
                )
            )
        rows.append(
            {
                "cell_id": cell_id,
                "source_anchor_refs": anchors,
                "machine_anchor_class": machine_anchor_class,
                "allowed_claim_strengths": allowed,
                "public_status": row.get("public_status"),
                "body_in_receipt": False,
            }
        )
    return {
        "status": PASS if cells and not findings else "blocked",
        "evidence_cell_count": len(cells),
        "source_anchor_count": sum(len(row["source_anchor_refs"]) for row in rows),
        "machine_anchor_count": sum(1 for row in rows if row["machine_anchor_class"]),
        "evidence_cells": sorted(rows, key=lambda row: row["cell_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_claim_boundary_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    levels = _rows(policy, "claim_strength_levels")
    findings: list[dict[str, Any]] = []
    if policy.get("theorem_correctness_claims_allowed") is True:
        findings.append(
            _finding(
                "EVIDENCE_CELL_POLICY_THEOREM_CORRECTNESS_OVERCLAIM",
                "The public evidence-cell policy cannot authorize theorem correctness claims.",
                case_id="claim_boundary_policy_floor",
                subject_id=str(policy.get("policy_id") or "claim_boundary_policy"),
                subject_kind="claim_boundary_policy",
            )
        )
    return {
        "status": PASS
        if levels and policy.get("proof_language_requires_machine_anchor") is True and not findings
        else "blocked",
        "policy_id": policy.get("policy_id"),
        "claim_strength_levels": [
            {
                "strength_id": row.get("strength_id"),
                "requires_evidence_cell": row.get("requires_evidence_cell") is True,
                "claim_authority": row.get("claim_authority"),
                "body_in_receipt": False,
            }
            for row in levels
        ],
        "boundary_rule_count": len(levels),
        "proof_language_requires_machine_anchor": policy.get(
            "proof_language_requires_machine_anchor"
        )
        is True,
        "findings": findings,
        "observed_negative_cases": {},
    }


def _inspect_claim_row(
    row: dict[str, Any],
    *,
    cell_by_id: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    claim_id = str(row.get("claim_id") or row.get("case_id") or "claim")
    case_id = str(row.get("expected_negative_case_id") or claim_id)
    subject_kind = "negative_case" if negative else "paper_claim"
    cell_id = str(row.get("evidence_cell_id") or "")
    claim_strength = str(row.get("claim_strength") or "")
    uses_proof_language = row.get("uses_proof_language") is True
    cell = cell_by_id.get(cell_id)

    if _has_forbidden_key(row, FORBIDDEN_PROOF_KEYS):
        _record(
            findings,
            observed,
            "EVIDENCE_CELL_PROOF_BODY_FORBIDDEN",
            "Public claim rows may cite a cell id but may not expose proof bodies.",
            case_id=case_id,
            subject_id=claim_id,
            subject_kind=subject_kind,
        )
    if _private_ref_present(row):
        _record(
            findings,
            observed,
            "EVIDENCE_CELL_PRIVATE_SOURCE_REF_FORBIDDEN",
            "Public claim rows may not expose private source refs.",
            case_id=case_id,
            subject_id=claim_id,
            subject_kind=subject_kind,
        )
    if "source_anchor_refs" in row and not _strings(row.get("source_anchor_refs")):
        _record(
            findings,
            observed,
            "EVIDENCE_CELL_MISSING_SOURCE_ANCHOR",
            "Claim-local source-anchor refs cannot be empty when proof language is present.",
            case_id=case_id,
            subject_id=claim_id,
            subject_kind=subject_kind,
        )
    if row.get("claims_theorem_correctness") is True:
        _record(
            findings,
            observed,
            "EVIDENCE_CELL_THEOREM_CORRECTNESS_OVERCLAIM",
            "Evidence cells support claim-boundary metadata, not theorem correctness.",
            case_id=case_id,
            subject_id=claim_id,
            subject_kind=subject_kind,
        )
    if row.get("human_approval_claims_evidence_cell_authority") is True:
        _record(
            findings,
            observed,
            "EVIDENCE_CELL_HUMAN_APPROVAL_NOT_PROOF_AUTHORITY",
            "Human approval cannot substitute for machine-anchor evidence-cell authority.",
            case_id=case_id,
            subject_id=claim_id,
            subject_kind=subject_kind,
        )
    if uses_proof_language and not cell_id:
        _record(
            findings,
            observed,
            "EVIDENCE_CELL_PROOF_LANGUAGE_WITHOUT_CELL",
            "Proof-language claims require a resolved evidence cell.",
            case_id=case_id,
            subject_id=claim_id,
            subject_kind=subject_kind,
        )
    if cell_id and cell is None and (
        uses_proof_language or claim_strength == "formal_evidence_cell_present"
    ):
        _record(
            findings,
            observed,
            "EVIDENCE_CELL_UNKNOWN_OVERCLAIM",
            "Claim strength overclaims when the referenced evidence cell is unknown.",
            case_id=case_id,
            subject_id=claim_id,
            subject_kind=subject_kind,
        )
    if cell is not None:
        anchors = _strings(cell.get("source_anchor_refs"))
        if not anchors:
            _record(
                findings,
                observed,
                "EVIDENCE_CELL_MISSING_SOURCE_ANCHOR",
                "Resolved evidence cells require source-anchor refs before proof language is allowed.",
                case_id=case_id,
                subject_id=cell_id,
                subject_kind="evidence_cell",
            )
        allowed = _strings(cell.get("allowed_claim_strengths"))
        if claim_strength and claim_strength not in allowed:
            findings.append(
                _finding(
                    "EVIDENCE_CELL_CLAIM_STRENGTH_NOT_ALLOWED",
                    "Claim strength is not allowed by the resolved evidence cell.",
                    case_id="claim_floor",
                    subject_id=claim_id,
                    subject_kind="paper_claim",
                )
            )

    return {
        "claim_id": claim_id,
        "paper_module_slug": row.get("paper_module_slug"),
        "evidence_cell_id": cell_id,
        "resolution_status": "resolved" if cell is not None else "unresolved",
        "claim_strength": claim_strength,
        "uses_proof_language": uses_proof_language,
        "machine_anchor_class": cell.get("machine_anchor_class") if cell else None,
        "source_anchor_refs": _strings(cell.get("source_anchor_refs")) if cell else [],
        "body_in_receipt": False,
    }


def validate_claims(
    payload: object,
    registry: dict[str, Any],
    negative_payloads: dict[str, object],
) -> dict[str, Any]:
    cells = registry.get("evidence_cells", [])
    cell_by_id = {
        str(row.get("cell_id")): row
        for row in cells
        if isinstance(row, dict) and row.get("cell_id")
    }
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    claim_rows: list[dict[str, Any]] = []
    for row in _rows(payload, "claims"):
        claim_rows.append(
            _inspect_claim_row(
                row,
                cell_by_id=cell_by_id,
                findings=findings,
                observed=observed,
                negative=False,
            )
        )
    for payload in negative_payloads.values():
        rows = _rows(payload, "claims")
        if isinstance(payload, dict) and not rows:
            rows = [payload]
        for row in rows:
            _inspect_claim_row(
                row,
                cell_by_id=cell_by_id,
                findings=findings,
                observed=observed,
                negative=True,
            )
    floor_findings = [row for row in findings if row.get("negative_case_id") == "claim_floor"]
    return {
        "status": PASS
        if claim_rows
        and all(row["resolution_status"] == "resolved" for row in claim_rows)
        and not floor_findings
        else "blocked",
        "claim_count": len(claim_rows),
        "resolved_cell_count": sum(
            1 for row in claim_rows if row["resolution_status"] == "resolved"
        ),
        "unresolved_cell_count": sum(
            1 for row in claim_rows if row["resolution_status"] != "resolved"
        ),
        "claim_resolution_rows": sorted(claim_rows, key=lambda row: row["claim_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )

    projection = validate_projection_protocol(payloads["projection_protocol"])
    cells = validate_cell_registry(payloads["evidence_cell_registry"])
    boundary = validate_claim_boundary_policy(payloads["claim_boundary_policy"])
    claims = validate_claims(
        payloads["paper_claims"],
        payloads["evidence_cell_registry"]
        if isinstance(payloads["evidence_cell_registry"], dict)
        else {},
        {
            name: payloads[name]
            for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
            if name in payloads
        },
    )

    observed = _merge_observed(projection, cells, boundary, claims)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(projection, cells, boundary, claims)
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and cells["status"] == PASS
        and boundary["status"] == PASS
        and claims["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "formal_evidence_cell_anchor_resolver_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id") if isinstance(bundle_manifest, dict) else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "body_in_receipt": False,
        "real_runtime_receipt": status == PASS,
        "synthetic_receipt_standin_allowed": False,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "protocol_id": projection["protocol_id"],
        "evidence_anchor_status": projection["evidence_anchor_status"],
        "source_refs": projection["source_refs"],
        "source_digests": projection["source_digests"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "public_runtime_refs": projection["public_runtime_refs"],
        "evidence_cell_count": cells["evidence_cell_count"],
        "source_anchor_count": cells["source_anchor_count"],
        "machine_anchor_count": cells["machine_anchor_count"],
        "claim_count": claims["claim_count"],
        "resolved_cell_count": claims["resolved_cell_count"],
        "unresolved_cell_count": claims["unresolved_cell_count"],
        "boundary_rule_count": boundary["boundary_rule_count"],
        "evidence_cells": cells["evidence_cells"],
        "claim_resolution_rows": claims["claim_resolution_rows"],
        "claim_strength_levels": boundary["claim_strength_levels"],
        "proof_language_requires_machine_anchor": boundary[
            "proof_language_requires_machine_anchor"
        ],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "formal_evidence_cell_anchor_resolver_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "formal_evidence_cell_anchor_resolver_public_board",
        "input_mode": result["input_mode"],
        "evidence_anchor_status": result["evidence_anchor_status"],
        "source_refs": result["source_refs"],
        "source_digests": result["source_digests"],
        "source_pattern_ids": result["source_pattern_ids"],
        "projection_receipt_refs": result["projection_receipt_refs"],
        "public_runtime_refs": result["public_runtime_refs"],
        "mechanics": [
            {
                "mechanic_id": "claim_to_cell_resolution",
                "count": result["resolved_cell_count"],
                "authority": "cell_id_as_compressed_receipt_bundle",
            },
            {
                "mechanic_id": "source_anchor_floor",
                "count": result["source_anchor_count"],
                "authority": "proof_language_requires_machine_anchor",
            },
            {
                "mechanic_id": "claim_boundary_policy",
                "count": result["boundary_rule_count"],
                "authority": "claim_boundary_before_claim_strength",
            },
        ],
        "evidence_cells": result["evidence_cells"],
        "claim_resolution_rows": result["claim_resolution_rows"],
        "proof_language_requires_machine_anchor": result[
            "proof_language_requires_machine_anchor"
        ],
        "formal_proof_authority": False,
        "theorem_correctness_authority": False,
        "body_in_receipt": False,
        "real_runtime_receipt": result["status"] == PASS,
        "synthetic_receipt_standin_allowed": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    board = _board_from_result(result)
    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    result_receipt = {
        **result,
        "schema_version": "formal_evidence_cell_anchor_resolver_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**board, "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "formal_evidence_cell_anchor_resolver_validation_receipt_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "evidence_anchor_status": result["evidence_anchor_status"],
        "source_refs": result["source_refs"],
        "source_digests": result["source_digests"],
        "projection_receipt_refs": result["projection_receipt_refs"],
        "public_runtime_refs": result["public_runtime_refs"],
        "claim_count": result["claim_count"],
        "resolved_cell_count": result["resolved_cell_count"],
        "source_anchor_count": result["source_anchor_count"],
        "machine_anchor_count": result["machine_anchor_count"],
        "formal_proof_authority": False,
        "theorem_correctness_authority": False,
        "body_in_receipt": False,
        "real_runtime_receipt": result["status"] == PASS,
        "synthetic_receipt_standin_allowed": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "formal_evidence_cell_anchor_resolver_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "body_in_receipt": False,
        "real_runtime_receipt": result["status"] == PASS,
        "synthetic_receipt_standin_allowed": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "evidence_cell_anchor_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.formal_evidence_cell_anchor_resolver run",
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_anchor_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.formal_evidence_cell_anchor_resolver "
        "run-anchor-bundle"
    ),
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_evidence_cell_anchor_bundle",
        include_negative=False,
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_evidence_cell_anchor_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="formal_evidence_cell_anchor_resolver")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    bundle_parser = sub.add_parser("run-anchor-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(
            args.input,
            args.out,
            command=(
                "python -m microcosm_core.organs.formal_evidence_cell_anchor_resolver "
                f"run --input {args.input} --out {args.out}"
            ),
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-anchor-bundle":
        result = run_anchor_bundle(
            args.input,
            args.out,
            command=(
                "python -m microcosm_core.organs.formal_evidence_cell_anchor_resolver "
                f"run-anchor-bundle --input {args.input} --out {args.out}"
            ),
        )
    else:
        return 2
    print_json = __import__("json").dumps
    print(print_json(result, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
