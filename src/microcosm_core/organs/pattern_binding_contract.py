from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.fixture_registry import load_pattern_binding_fixture
from microcosm_core.private_state_scan import PASS, public_relative_path, scan_json_payload, scan_paths
from microcosm_core.receipts import AUTHORITY_CEILING, base_receipt, write_json_atomic


ORGAN_ID = "pattern_binding_contract"
FIXTURE_ID = "first_wave.pattern_binding_contract"
RESULT_NAME = "pattern_binding_validation_result.json"
CAPSULE_NAME = "source_capsules.json"
OMISSION_NAME = "omission_receipt.json"
REFERENCE_NAME = "reference_capsule_resolver_receipt.json"
AUTHORITY_CHAIN_NAME = "authority_chain_handle_resolver_receipt.json"

EXPECTED_NEGATIVE_CASES = {
    "missing_binding_contract_fields": [
        "MISSING_GOVERNING_STANDARD",
        "MISSING_ANTI_CLAIM_REF",
    ],
    "pattern_binding_projection_claims_source_authority": ["PROJECTION_NOT_SOURCE_AUTHORITY"],
    "source_capsule_private_body_leak": ["SOURCE_CAPSULE_PRIVATE_BODY_LEAK"],
    "duplicate_pattern_binding_conflict": ["DUPLICATE_PATTERN_BINDING_CONFLICT"],
    "binding_success_overclaims_public_leaf": ["BINDING_PASS_OVERCLAIMS_PUBLIC_LEAF"],
    "reference_capsule_unresolved_supported_kind": ["REFERENCE_CAPSULE_UNRESOLVED_SUPPORTED_KIND"],
    "reference_capsule_private_body_leak": ["REFERENCE_BODY_LEAK"],
    "authority_chain_unsupported_handle_implies_authority": [
        "UNSUPPORTED_AUTHORITY_HANDLE_IMPLIED_AUTHORITY"
    ],
}

VALID_POSTURES = {"direct_public", "synthetic_only", "schema_only", "forbidden"}


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _finding(code: str, message: str, *, case_id: str | None = None, pattern_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error_code": code,
        "message": message,
        "body_redacted": True,
    }
    if case_id:
        payload["negative_case_id"] = case_id
    if pattern_id:
        payload["pattern_id"] = pattern_id
    return payload


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str | None = None,
    pattern_id: str | None = None,
) -> None:
    findings.append(_finding(code, message, case_id=case_id, pattern_id=pattern_id))
    if case_id:
        observed[case_id].add(code)


def _source_capsules_by_ref(source_capsules: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = source_capsules.get("source_capsules", source_capsules)
    if isinstance(rows, dict):
        iterable = rows.values()
    elif isinstance(rows, list):
        iterable = rows
    else:
        iterable = []
    capsules: dict[str, dict[str, Any]] = {}
    for row in iterable:
        if not isinstance(row, dict):
            continue
        source_ref = str(row.get("source_ref") or "").strip()
        if source_ref:
            capsules[source_ref] = row
    return capsules


def _pattern_source_refs(row: dict[str, Any]) -> list[str]:
    refs = row.get("source_refs")
    if refs is None:
        refs = row.get("source_capsule_refs")
    if isinstance(refs, list):
        return [str(ref).strip() for ref in refs if str(ref).strip()]
    return []


def validate_pattern_bindings(
    patterns: list[dict[str, Any]],
    source_capsules: dict[str, Any],
    scan_result: dict[str, Any],
) -> dict[str, Any]:
    capsules = _source_capsules_by_ref(source_capsules)
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    accepted_rows: list[dict[str, Any]] = []
    rejected_ids: set[str] = set()

    counts = Counter(str(row.get("pattern_id") or "") for row in patterns if isinstance(row, dict))
    duplicate_pattern_ids = sorted(pattern_id for pattern_id, count in counts.items() if pattern_id and count > 1)
    for duplicate_id in duplicate_pattern_ids:
        _record(
            findings,
            observed,
            "DUPLICATE_PATTERN_BINDING_CONFLICT",
            "Duplicate pattern id rejected deterministically.",
            case_id="duplicate_pattern_binding_conflict",
            pattern_id=duplicate_id,
        )
        rejected_ids.add(duplicate_id)

    for row in patterns:
        pattern_id = str(row.get("pattern_id") or "").strip()
        case_id = row.get("expected_negative_case_id")
        if not pattern_id:
            _record(findings, observed, "MISSING_PATTERN_ID", "Pattern row is missing pattern_id.", case_id=case_id)
            continue
        row_errors_before = len(findings)
        if pattern_id in duplicate_pattern_ids:
            rejected_ids.add(pattern_id)
            continue
        if row.get("organ_id") != ORGAN_ID:
            _record(
                findings,
                observed,
                "UNEXPECTED_ORGAN_ID",
                "Pattern row belongs to a different organ.",
                case_id=case_id,
                pattern_id=pattern_id,
            )
        if not row.get("governing_standard") and not row.get("governing_standard_refs"):
            _record(
                findings,
                observed,
                "MISSING_GOVERNING_STANDARD",
                "Pattern row lacks governing standard binding.",
                case_id=case_id,
                pattern_id=pattern_id,
            )
        if not row.get("anti_claim_ref"):
            _record(
                findings,
                observed,
                "MISSING_ANTI_CLAIM_REF",
                "Pattern row lacks anti-claim reference.",
                case_id=case_id,
                pattern_id=pattern_id,
            )
        posture = str(row.get("public_projection_posture") or row.get("projection_mode") or "")
        if posture not in VALID_POSTURES:
            _record(
                findings,
                observed,
                "INVALID_PROJECTION_MODE",
                "Pattern row has an unsupported projection posture.",
                case_id=case_id,
                pattern_id=pattern_id,
            )
        if posture == "direct_public" and row.get("claims_source_authority"):
            _record(
                findings,
                observed,
                "PROJECTION_NOT_SOURCE_AUTHORITY",
                "Projection row claims source authority.",
                case_id=case_id or "pattern_binding_projection_claims_source_authority",
                pattern_id=pattern_id,
            )
        if row.get("claims_public_leaf_ready"):
            _record(
                findings,
                observed,
                "BINDING_PASS_OVERCLAIMS_PUBLIC_LEAF",
                "Binding row overclaims public leaf readiness.",
                case_id=case_id or "binding_success_overclaims_public_leaf",
                pattern_id=pattern_id,
            )
        source_refs = _pattern_source_refs(row)
        if not source_refs:
            _record(
                findings,
                observed,
                "MISSING_SOURCE_CAPSULE",
                "Pattern row lacks source capsule refs.",
                case_id=case_id,
                pattern_id=pattern_id,
            )
        for source_ref in source_refs:
            capsule = capsules.get(source_ref)
            if capsule is None:
                _record(
                    findings,
                    observed,
                    "MISSING_SOURCE_CAPSULE",
                    "Pattern row references an unknown source capsule.",
                    case_id=case_id,
                    pattern_id=pattern_id,
                )
                continue
            if capsule.get("body_redacted") is not True:
                _record(
                    findings,
                    observed,
                    "SOURCE_CAPSULE_BODY_NOT_REDACTED",
                    "Source capsule must be body-redacted.",
                    case_id=case_id,
                    pattern_id=pattern_id,
                )
            if not capsule.get("replacement_fixture_ref"):
                _record(
                    findings,
                    observed,
                    "SOURCE_CAPSULE_MISSING_REPLACEMENT_FIXTURE",
                    "Source capsule lacks synthetic replacement fixture ref.",
                    case_id=case_id,
                    pattern_id=pattern_id,
                )
        if len(findings) == row_errors_before and not case_id:
            accepted_rows.append(row)
        else:
            rejected_ids.add(pattern_id)

    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "accepted_rows": accepted_rows,
        "rejected_pattern_ids": sorted(pid for pid in rejected_ids if pid),
        "duplicate_pattern_ids": duplicate_pattern_ids,
        "private_state_scan": scan_result,
    }


def validate_source_capsules(source_capsules: dict[str, Any], forbidden_terms: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    capsules = _source_capsules_by_ref(source_capsules)
    for source_ref, capsule in capsules.items():
        case_id = capsule.get("expected_negative_case_id")
        if capsule.get("body_redacted") is not True:
            code = "SOURCE_CAPSULE_PRIVATE_BODY_LEAK" if case_id else "SOURCE_CAPSULE_BODY_NOT_REDACTED"
            _record(
                findings,
                observed,
                code,
                "Source capsule body is not redacted.",
                case_id=case_id,
                pattern_id=str(source_ref),
            )
        if not capsule.get("replacement_fixture_ref"):
            _record(
                findings,
                observed,
                "SOURCE_CAPSULE_MISSING_REPLACEMENT_FIXTURE",
                "Source capsule lacks replacement fixture ref.",
                case_id=case_id,
                pattern_id=str(source_ref),
            )
        scan = scan_json_payload(capsule, path=f"source_capsules.json::{source_ref}", forbidden_classes=forbidden_terms)
        if scan["status"] != PASS and case_id:
            _record(
                findings,
                observed,
                "SOURCE_CAPSULE_PRIVATE_BODY_LEAK",
                "Source capsule contains a forbidden body marker.",
                case_id=case_id,
                pattern_id=str(source_ref),
            )
    return {"findings": findings, "observed_negative_cases": {k: sorted(v) for k, v in observed.items()}}


def validate_reference_capsules(reference_capsules: object, forbidden_terms: dict[str, Any]) -> dict[str, Any]:
    rows = reference_capsules.get("reference_capsules", []) if isinstance(reference_capsules, dict) else []
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if not isinstance(row, dict):
            continue
        case_id = row.get("expected_negative_case_id")
        ref_id = str(row.get("reference_id") or row.get("source_ref") or "reference_capsule")
        if row.get("supported_kind") and not row.get("resolved"):
            _record(
                findings,
                observed,
                "REFERENCE_CAPSULE_UNRESOLVED_SUPPORTED_KIND",
                "Supported reference capsule kind did not resolve.",
                case_id=case_id,
                pattern_id=ref_id,
            )
        scan = scan_json_payload(row, path=f"reference_capsules.json::{ref_id}", forbidden_classes=forbidden_terms)
        if scan["status"] != PASS or row.get("body_redacted") is not True:
            _record(
                findings,
                observed,
                "REFERENCE_BODY_LEAK",
                "Reference capsule body is not redacted.",
                case_id=case_id,
                pattern_id=ref_id,
            )
    return {"findings": findings, "observed_negative_cases": {k: sorted(v) for k, v in observed.items()}}


def _authority_handle_rows(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("handles", payload.get("authority_chain_handles", []))
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def validate_authority_chain_handle_resolver(authority_chain_handles: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in _authority_handle_rows(authority_chain_handles):
        case_id = row.get("expected_negative_case_id")
        handle_id = str(row.get("handle_id") or "authority_handle")
        if row.get("supported") is False and row.get("implies_authority") is True:
            _record(
                findings,
                observed,
                "UNSUPPORTED_AUTHORITY_HANDLE_IMPLIED_AUTHORITY",
                "Unsupported authority-chain handle implied authority.",
                case_id=case_id,
                pattern_id=handle_id,
            )
    status = PASS if "authority_chain_unsupported_handle_implies_authority" in observed else "missing_negative_case"
    return {
        "status": status,
        "authority_chain_resolution_status": status,
        "findings": findings,
        "observed_negative_cases": {k: sorted(v) for k, v in observed.items()},
    }


def validate_authority_ceiling(validation_result: dict[str, Any]) -> dict[str, Any]:
    codes = set(validation_result.get("error_codes", []))
    return {
        "status": PASS,
        "authority_ceiling": AUTHORITY_CEILING,
        "projection_not_source_authority_observed": "PROJECTION_NOT_SOURCE_AUTHORITY" in codes,
        "public_leaf_overclaim_observed": "BINDING_PASS_OVERCLAIMS_PUBLIC_LEAF" in codes,
    }


def _source_capsule_receipt(accepted_rows: list[dict[str, Any]], source_capsules: dict[str, Any]) -> dict[str, Any]:
    capsules = _source_capsules_by_ref(source_capsules)
    accepted_refs = sorted({ref for row in accepted_rows for ref in _pattern_source_refs(row)})
    rows: list[dict[str, Any]] = []
    for source_ref in accepted_refs:
        capsule = dict(capsules[source_ref])
        capsule.pop("body", None)
        capsule["body_redacted"] = True
        capsule.setdefault("source_sha256", _canonical_sha256(capsule))
        rows.append(capsule)
    return {
        "schema_version": "pattern_binding_source_capsules_receipt_v1",
        "status": PASS,
        "organ_id": ORGAN_ID,
        "source_capsules": rows,
        "source_capsule_count": len(rows),
        "anti_claim": "Source capsules are redacted metadata over synthetic fixture rows, not source bodies.",
    }


def _omission_receipt(redacted_count: int, scan_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "omission_receipt_v1",
        "status": PASS,
        "organ_id": ORGAN_ID,
        "omitted_files": redacted_count,
        "omitted_edges": 0,
        "omitted_overlays": 0,
        "omitted_classes": ["forbidden_content_body", "non_public_evidence_body"] if redacted_count else [],
        "reason": "source bodies intentionally omitted; synthetic fixture metadata retained",
        "private_state_scan": scan_result,
        "anti_claim": "Omission counts are class-level metadata and do not expose omitted bodies.",
    }


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(code)
    return {key: sorted(value) for key, value in sorted(merged.items())}


def write_receipts(out_dir: str | Path, validation_result: dict[str, Any]) -> dict[str, str]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    paths = {
        "pattern_binding_validation_result": target / RESULT_NAME,
        "source_capsules": target / CAPSULE_NAME,
        "omission_receipt": target / OMISSION_NAME,
        "reference_capsule_resolver_receipt": target / REFERENCE_NAME,
        "authority_chain_handle_resolver_receipt": target / AUTHORITY_CHAIN_NAME,
    }
    write_json_atomic(paths["source_capsules"], validation_result["source_capsule_receipt"])
    write_json_atomic(paths["omission_receipt"], validation_result["omission_receipt"])
    write_json_atomic(paths["reference_capsule_resolver_receipt"], validation_result["reference_capsule_receipt"])
    write_json_atomic(paths["authority_chain_handle_resolver_receipt"], validation_result["authority_chain_receipt"])

    result_payload = dict(validation_result)
    for internal_key in (
        "source_capsule_receipt",
        "omission_receipt",
        "reference_capsule_receipt",
        "authority_chain_receipt",
    ):
        result_payload.pop(internal_key, None)
    result_payload["receipt_paths"] = [public_relative_path(path) for path in paths.values()]
    write_json_atomic(paths["pattern_binding_validation_result"], result_payload)
    return {key: public_relative_path(path) for key, path in paths.items()}


def validate(input_dir: str | Path, out_dir: str | Path, command: str | None = None) -> dict[str, Any]:
    fixture = load_pattern_binding_fixture(input_dir)
    input_paths = [Path(path) for path in fixture["input_paths"].values()]
    forbidden_terms = fixture["forbidden_terms"]
    scan_result = scan_paths(input_paths, forbidden_classes=forbidden_terms)
    binding_result = validate_pattern_bindings(fixture["patterns"], fixture["source_capsules"], scan_result)
    capsule_result = validate_source_capsules(fixture["source_capsules"], forbidden_terms)

    if "source_capsule_with_private_body" in fixture:
        leak_result = validate_source_capsules(
            {"source_capsules": [fixture["source_capsule_with_private_body"]]},
            forbidden_terms,
        )
    else:
        leak_result = {"findings": [], "observed_negative_cases": {}}

    if "duplicate_patterns" in fixture:
        duplicate_result = validate_pattern_bindings(fixture["duplicate_patterns"], fixture["source_capsules"], scan_result)
    else:
        duplicate_result = {"findings": [], "observed_negative_cases": {}, "duplicate_pattern_ids": []}

    if "valid_binding_overclaim_public_leaf" in fixture:
        overclaim_result = validate_pattern_bindings(
            [fixture["valid_binding_overclaim_public_leaf"]],
            fixture["source_capsules"],
            scan_result,
        )
    else:
        overclaim_result = {"findings": [], "observed_negative_cases": {}}

    reference_result = validate_reference_capsules(fixture.get("reference_capsules", {}), forbidden_terms)
    authority_result = validate_authority_chain_handle_resolver(fixture.get("authority_chain_handles", {}))

    observed = _merge_observed(
        binding_result,
        capsule_result,
        leak_result,
        duplicate_result,
        overclaim_result,
        reference_result,
        authority_result,
    )
    error_codes = sorted({code for codes in observed.values() for code in codes})
    missing_cases = sorted(set(EXPECTED_NEGATIVE_CASES) - set(observed))
    accepted_rows = binding_result["accepted_rows"]
    source_capsule_receipt = _source_capsule_receipt(accepted_rows, fixture["source_capsules"])
    omission_receipt = _omission_receipt(source_capsule_receipt["source_capsule_count"], scan_result)
    reference_receipt = {
        "schema_version": "reference_capsule_resolver_receipt_v1",
        "status": PASS if not {"reference_capsule_unresolved_supported_kind", "reference_capsule_private_body_leak"} - set(observed) else "missing_negative_case",
        "organ_id": ORGAN_ID,
        "reference_capsule_resolution_status": PASS,
        "observed_negative_cases": {
            key: value
            for key, value in observed.items()
            if key.startswith("reference_capsule")
        },
        "findings": reference_result["findings"],
        "anti_claim": "Reference capsules are schema-only or redacted metadata; no source body is emitted.",
    }
    authority_receipt = {
        "schema_version": "authority_chain_handle_resolver_receipt_v1",
        "status": authority_result["status"],
        "organ_id": ORGAN_ID,
        "authority_chain_resolution_status": authority_result["authority_chain_resolution_status"],
        "observed_negative_cases": authority_result["observed_negative_cases"],
        "findings": authority_result["findings"],
        "anti_claim": "Authority-chain handles are routing metadata and never upgrade unsupported handles to authority.",
    }

    all_findings: list[dict[str, Any]] = []
    for result in (
        binding_result,
        capsule_result,
        leak_result,
        duplicate_result,
        overclaim_result,
        reference_result,
        authority_result,
    ):
        all_findings.extend(result.get("findings", []))

    projection_mode_counts = Counter(
        str(row.get("public_projection_posture") or row.get("projection_mode") or "unknown")
        for row in fixture["patterns"]
        if isinstance(row, dict)
    )
    result = base_receipt(ORGAN_ID, FIXTURE_ID, command=command)
    result.update(
        {
            "status": PASS if not missing_cases and scan_result["status"] == PASS else "blocked",
            "accepted_count": len(accepted_rows),
            "rejected_count": len(set(binding_result["rejected_pattern_ids"]) | set(duplicate_result.get("rejected_pattern_ids", []))),
            "accepted_pattern_ids": sorted(str(row["pattern_id"]) for row in accepted_rows),
            "rejected_pattern_ids": sorted(set(binding_result["rejected_pattern_ids"]) | set(duplicate_result.get("rejected_pattern_ids", []))),
            "duplicate_pattern_ids": sorted(set(binding_result["duplicate_pattern_ids"]) | set(duplicate_result.get("duplicate_pattern_ids", []))),
            "error_codes": error_codes,
            "anti_claim_refs": sorted({str(row.get("anti_claim_ref")) for row in accepted_rows if row.get("anti_claim_ref")}),
            "private_state_scan": scan_result,
            "authority_ceiling": validate_authority_ceiling({"error_codes": error_codes}),
            "source_pattern_ids": sorted(str(row["pattern_id"]) for row in accepted_rows),
            "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
            "observed_negative_cases": observed,
            "missing_negative_cases": missing_cases,
            "findings": all_findings,
            "projection_mode_counts": dict(sorted(projection_mode_counts.items())),
            "source_capsule_count": source_capsule_receipt["source_capsule_count"],
            "omission_receipt_count": 1,
            "authority_chain_resolution_status": authority_receipt["authority_chain_resolution_status"],
            "reference_capsule_resolution_status": reference_receipt["reference_capsule_resolution_status"],
            "source_capsule_receipt": source_capsule_receipt,
            "omission_receipt": omission_receipt,
            "reference_capsule_receipt": reference_receipt,
            "authority_chain_receipt": authority_receipt,
        }
    )
    paths = write_receipts(out_dir, result)
    result["receipt_paths"] = list(paths.values())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command_name")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command_name != "validate":
        parser.error("expected subcommand: validate")
    command = (
        "python -m microcosm_core.organs.pattern_binding_contract "
        f"validate --input {args.input} --out {args.out}"
    )
    result = validate(args.input, args.out, command=command)
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
