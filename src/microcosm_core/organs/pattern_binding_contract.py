from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.fixture_registry import load_pattern_binding_fixture, load_pattern_binding_substrate_bundle
from microcosm_core.secret_exclusion_scan import PASS, public_relative_path, scan_json_payload, scan_paths
from microcosm_core.receipts import AUTHORITY_CEILING, base_receipt, write_json_atomic


ORGAN_ID = "pattern_binding_contract"
FIXTURE_ID = "first_wave.pattern_binding_contract"
RESULT_NAME = "pattern_binding_validation_result.json"
CAPSULE_NAME = "source_capsules.json"
OMISSION_NAME = "omission_receipt.json"
REFERENCE_NAME = "reference_capsule_resolver_receipt.json"
AUTHORITY_CHAIN_NAME = "authority_chain_handle_resolver_receipt.json"
SUBSTRATE_BUNDLE_RESULT_NAME = "exported_substrate_bundle_validation_result.json"
RUNTIME_METADATA_ONLY_ANTI_CLAIM_REF = "anti_claim.pattern_binding.runtime_metadata_only"
REAL_PATTERN_LEDGER_ANTI_CLAIM_REF = "anti_claim.pattern_binding.real_pattern_ledger_source_faithful"
REAL_PATTERN_LEDGER_GOVERNING_STANDARD = "std_microcosm_pattern_binding_contract"
REAL_PATTERN_LEDGER_SOURCE_KEY = "real_pattern_ledger_source"

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


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finding(code: str, message: str, *, case_id: str | None = None, pattern_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error_code": code,
        "message": message,
        "body_in_receipt": False,
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


def _receipt_safe_scan_result(scan_result: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan_result)
    safe.pop("forbidden_output_fields", None)
    return safe


def _body_excluded_from_receipt(row: dict[str, Any]) -> bool:
    return row.get("body_in_receipt") is False and "body" not in row


def _runtime_refs(row: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in ("public_runtime_refs", "public_runtime_ref", "replacement_fixture_ref"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            refs.append(value.strip())
        elif isinstance(value, list):
            refs.extend(str(item).strip() for item in value if str(item).strip())
    return refs


def _source_capsule_runtime_refs(source_refs: list[str], source_capsules: dict[str, Any]) -> list[str]:
    capsules = _source_capsules_by_ref(source_capsules)
    refs: list[str] = []
    for source_ref in source_refs:
        refs.extend(_runtime_refs(capsules.get(source_ref, {})))
    return sorted(set(refs))


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


def _substrate_bundle_truth_accounting(
    manifest: dict[str, Any],
    accepted_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    bundle_id = str(manifest.get("bundle_id") or "")
    authority_ceiling = str(manifest.get("authority_ceiling") or "")
    runtime_example_bundle = (
        "runtime_example" in bundle_id or "runtime example" in authority_ceiling
    )
    runtime_metadata_only_count = sum(
        1
        for row in accepted_rows
        if str(row.get("anti_claim_ref") or "") == RUNTIME_METADATA_ONLY_ANTI_CLAIM_REF
    )
    all_rows_metadata_only = (
        bool(accepted_rows) and runtime_metadata_only_count == len(accepted_rows)
    )
    real_pattern_ledger_row_count = (
        0 if runtime_example_bundle else len(accepted_rows) - runtime_metadata_only_count
    )
    counts_as_real_substrate_progress = real_pattern_ledger_row_count > 0 and not all_rows_metadata_only
    if not accepted_rows:
        import_status = "no_accepted_pattern_rows"
    elif not counts_as_real_substrate_progress:
        import_status = "runtime_example_not_real_pattern_ledger_import"
    elif runtime_metadata_only_count:
        import_status = "mixed_runtime_metadata_and_real_pattern_ledger_import"
    else:
        import_status = "real_pattern_ledger_import"
    return {
        "schema_version": "pattern_binding_substrate_truth_accounting_v1",
        "accepted_count_is_product_progress": False,
        "counts_as_real_substrate_progress": counts_as_real_substrate_progress,
        "substrate_import_status": import_status,
        "runtime_example_bundle": runtime_example_bundle,
        "pattern_row_count": len(accepted_rows),
        "runtime_metadata_only_row_count": runtime_metadata_only_count,
        "real_pattern_ledger_row_count": real_pattern_ledger_row_count,
        "anti_claim_refs": sorted(
            {str(row.get("anti_claim_ref")) for row in accepted_rows if row.get("anti_claim_ref")}
        ),
    }


def _public_root_for_bundle(input_dir: str | Path) -> Path:
    input_path = Path(input_dir).resolve(strict=False)
    for candidate in (input_path, *input_path.parents):
        if (candidate / "examples").is_dir() and (candidate / "src/microcosm_core").is_dir():
            return candidate
    return input_path.parent


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path.as_posix()}:{line_number} is not a JSON object")
        rows.append(row)
    return rows


def _real_pattern_ledger_projection(input_dir: str | Path, manifest: dict[str, Any]) -> dict[str, Any] | None:
    spec = manifest.get(REAL_PATTERN_LEDGER_SOURCE_KEY)
    if not isinstance(spec, dict):
        return None

    source_ref = str(spec.get("path") or spec.get("source_ref") or "").strip()
    public_root = _public_root_for_bundle(input_dir)
    ledger_path = public_root / source_ref if source_ref else public_root
    findings: list[dict[str, Any]] = []
    if not source_ref:
        findings.append(_finding("MISSING_REAL_PATTERN_LEDGER_REF", "Real pattern ledger source path is missing."))
        rows: list[dict[str, Any]] = []
        digest = ""
    elif not ledger_path.is_file():
        findings.append(
            _finding(
                "REAL_PATTERN_LEDGER_NOT_FOUND",
                "Real pattern ledger source path does not resolve inside the public root.",
            )
        )
        rows = []
        digest = ""
    else:
        rows = _read_jsonl_rows(ledger_path)
        digest = _file_sha256(ledger_path)

    expected_digest = str(spec.get("sha256") or "").strip()
    expected_count = spec.get("row_count")
    if expected_digest and digest and digest != expected_digest:
        findings.append(_finding("REAL_PATTERN_LEDGER_DIGEST_MISMATCH", "Real pattern ledger digest mismatch."))
    if isinstance(expected_count, int) and rows and len(rows) != expected_count:
        findings.append(_finding("REAL_PATTERN_LEDGER_ROW_COUNT_MISMATCH", "Real pattern ledger row count mismatch."))

    pattern_rows: list[dict[str, Any]] = []
    source_capsules: list[dict[str, Any]] = []
    seen_pattern_ids: set[str] = set()
    for row in rows:
        pattern_id = str(row.get("pattern_id") or "").strip()
        if not pattern_id:
            findings.append(_finding("REAL_PATTERN_LEDGER_ROW_MISSING_PATTERN_ID", "Real pattern ledger row lacks pattern_id."))
            continue
        if pattern_id in seen_pattern_ids:
            findings.append(
                _finding(
                    "REAL_PATTERN_LEDGER_DUPLICATE_PATTERN_ID",
                    "Real pattern ledger row duplicates a pattern_id.",
                    pattern_id=pattern_id,
                )
            )
            continue
        seen_pattern_ids.add(pattern_id)
        capsule_ref = f"capsule.real_pattern_ledger.{pattern_id}"
        runtime_ref = f"{source_ref}::{pattern_id}"
        pattern_rows.append(
            {
                "pattern_id": pattern_id,
                "organ_id": ORGAN_ID,
                "title": str(row.get("title") or pattern_id),
                "governing_standard": REAL_PATTERN_LEDGER_GOVERNING_STANDARD,
                "source_refs": [capsule_ref],
                "public_projection_posture": "direct_public",
                "anti_claim_ref": REAL_PATTERN_LEDGER_ANTI_CLAIM_REF,
            }
        )
        source_capsules.append(
            {
                "source_ref": capsule_ref,
                "authority_class": "public_real_pattern_ledger_row",
                "body_in_receipt": False,
                "public_runtime_ref": runtime_ref,
                "source_sha256": _canonical_sha256(row),
            }
        )

    return {
        "status": PASS if not findings and pattern_rows else "blocked",
        "source_ref": source_ref,
        "path": ledger_path,
        "row_count": len(rows),
        "sha256": digest,
        "expected_sha256": expected_digest,
        "expected_row_count": expected_count,
        "pattern_rows": pattern_rows,
        "source_capsules": {
            "schema_version": "source_capsules_bundle_v1",
            "source_capsules": source_capsules,
            "anti_claim": (
                "Source capsules point at public real pattern-ledger rows by ref "
                "and digest; receipts do not inline ledger row bodies."
            ),
        },
        "findings": findings,
    }


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
            if not _body_excluded_from_receipt(capsule):
                _record(
                    findings,
                    observed,
                    "SOURCE_CAPSULE_BODY_IN_RECEIPT",
                    "Source capsule must keep source body out of JSON receipts.",
                    case_id=case_id,
                    pattern_id=pattern_id,
                )
            if not _runtime_refs(capsule):
                _record(
                    findings,
                    observed,
                    "SOURCE_CAPSULE_MISSING_RUNTIME_REF",
                    "Source capsule lacks a public runtime or regression-harness ref.",
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
        "secret_exclusion_scan": scan_result,
    }


def validate_source_capsules(source_capsules: dict[str, Any], forbidden_terms: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    capsules = _source_capsules_by_ref(source_capsules)
    for source_ref, capsule in capsules.items():
        case_id = capsule.get("expected_negative_case_id")
        if not _body_excluded_from_receipt(capsule):
            code = "SOURCE_CAPSULE_PRIVATE_BODY_LEAK" if case_id else "SOURCE_CAPSULE_BODY_IN_RECEIPT"
            _record(
                findings,
                observed,
                code,
                "Source capsule body is present in a receipt payload.",
                case_id=case_id,
                pattern_id=str(source_ref),
            )
        if not _runtime_refs(capsule):
            _record(
                findings,
                observed,
                "SOURCE_CAPSULE_MISSING_RUNTIME_REF",
                "Source capsule lacks a public runtime or regression-harness ref.",
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
        if scan["status"] != PASS or not _body_excluded_from_receipt(row):
            _record(
                findings,
                observed,
                "REFERENCE_BODY_LEAK",
                "Reference capsule body is present in a receipt payload.",
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
        capsule["body_in_receipt"] = False
        capsule.setdefault("source_sha256", _canonical_sha256(capsule))
        rows.append(capsule)
    return {
        "schema_version": "pattern_binding_source_capsules_receipt_v1",
        "status": PASS,
        "organ_id": ORGAN_ID,
        "source_capsules": rows,
        "source_capsule_count": len(rows),
        "body_in_receipt": False,
        "real_runtime_receipt": True,
        "synthetic_receipt_standin_allowed": False,
        "public_runtime_refs": sorted({ref for row in rows for ref in _runtime_refs(row)}),
        "anti_claim": (
            "Source capsules are provenance metadata over public runtime refs "
            "or regression-harness refs; JSON receipts do not inline source bodies."
        ),
    }


def _omission_receipt(redacted_count: int, scan_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pattern_binding_secret_exclusion_receipt_v1",
        "status": PASS,
        "organ_id": ORGAN_ID,
        "body_in_receipt": False,
        "real_runtime_receipt": True,
        "synthetic_receipt_standin_allowed": False,
        "non_inlined_source_ref_count": redacted_count,
        "omitted_edges": 0,
        "omitted_overlays": 0,
        "excluded_classes": [
            "secret_or_credential_body",
            "provider_payload_body",
            "operator_thread_body",
            "credential_equivalent_live_access_material",
        ]
        if redacted_count
        else [],
        "reason": (
            "Pattern-binding receipts carry public runtime/source refs and "
            "regression-harness refs; they do not inline body payloads."
        ),
        "secret_exclusion_scan": scan_result,
        "anti_claim": (
            "A non-inlined body is not product evidence. The real evidence is "
            "the public runtime refs, source refs, and command-owned receipts."
        ),
    }


def _write_substrate_bundle_receipt(out_dir: str | Path, validation_result: dict[str, Any]) -> str:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    path = target / SUBSTRATE_BUNDLE_RESULT_NAME
    payload = dict(validation_result)
    receipt_path = public_relative_path(path)
    if Path(receipt_path).is_absolute() and "receipts" in path.parts:
        receipts_index = len(path.parts) - 1 - list(reversed(path.parts)).index("receipts")
        receipt_path = Path(*path.parts[receipts_index:]).as_posix()
    payload["receipt_paths"] = [receipt_path]
    write_json_atomic(path, payload)
    return receipt_path


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
    scan_result = _receipt_safe_scan_result(scan_paths(input_paths, forbidden_classes=forbidden_terms))
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
        "body_in_receipt": False,
        "real_runtime_receipt": True,
        "synthetic_receipt_standin_allowed": False,
        "anti_claim": "Reference capsules are schema/runtime refs; no source body is inlined into receipts.",
    }
    authority_receipt = {
        "schema_version": "authority_chain_handle_resolver_receipt_v1",
        "status": authority_result["status"],
        "organ_id": ORGAN_ID,
        "authority_chain_resolution_status": authority_result["authority_chain_resolution_status"],
        "observed_negative_cases": authority_result["observed_negative_cases"],
        "findings": authority_result["findings"],
        "body_in_receipt": False,
        "real_runtime_receipt": True,
        "synthetic_receipt_standin_allowed": False,
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
            "secret_exclusion_scan": scan_result,
            "body_in_receipt": False,
            "real_runtime_receipt": True,
            "synthetic_receipt_standin_allowed": False,
            "fixture_role": "regression_negative_harness_with_positive_control",
            "public_runtime_refs": _source_capsule_runtime_refs(
                sorted({ref for row in accepted_rows for ref in _pattern_source_refs(row)}),
                fixture["source_capsules"],
            ),
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


def validate_substrate_bundle(input_dir: str | Path, out_dir: str | Path, command: str | None = None) -> dict[str, Any]:
    bundle = load_pattern_binding_substrate_bundle(input_dir)
    manifest = bundle["bundle_manifest"]
    real_ledger_projection = _real_pattern_ledger_projection(input_dir, manifest)
    uses_real_ledger = real_ledger_projection is not None and real_ledger_projection["status"] == PASS
    patterns = real_ledger_projection["pattern_rows"] if uses_real_ledger else bundle["patterns"]
    source_capsules = real_ledger_projection["source_capsules"] if uses_real_ledger else bundle["source_capsules"]
    input_paths = [Path(path) for path in bundle["input_paths"].values()]
    if real_ledger_projection is not None and real_ledger_projection["path"].is_file():
        input_paths.append(real_ledger_projection["path"])
    forbidden_terms = bundle["forbidden_terms"]
    scan_result = _receipt_safe_scan_result(scan_paths(input_paths, forbidden_classes=forbidden_terms))
    binding_result = validate_pattern_bindings(patterns, source_capsules, scan_result)
    capsule_result = validate_source_capsules(source_capsules, forbidden_terms)
    reference_result = validate_reference_capsules(bundle["reference_capsules"], forbidden_terms)
    authority_result = validate_authority_chain_handle_resolver(bundle["authority_chain_handles"])

    observed = _merge_observed(binding_result, capsule_result, reference_result, authority_result)
    all_findings: list[dict[str, Any]] = []
    for result in (binding_result, capsule_result, reference_result, authority_result):
        all_findings.extend(result.get("findings", []))
    if real_ledger_projection is not None:
        all_findings.extend(real_ledger_projection["findings"])

    error_codes = sorted({finding["error_code"] for finding in all_findings})
    accepted_rows = binding_result["accepted_rows"]
    bundle_id = str(manifest.get("bundle_id") or "pattern_binding_exported_substrate_bundle")
    status = PASS if scan_result["status"] == PASS and not all_findings and accepted_rows else "blocked"
    source_capsule_receipt = _source_capsule_receipt(accepted_rows, source_capsules)
    truth_accounting = _substrate_bundle_truth_accounting(manifest, accepted_rows)
    legacy_runtime_metadata_only_count = sum(
        1
        for row in bundle["patterns"]
        if str(row.get("anti_claim_ref") or "") == RUNTIME_METADATA_ONLY_ANTI_CLAIM_REF
    )
    result = base_receipt(ORGAN_ID, f"{FIXTURE_ID}.exported_substrate_bundle", command=command)
    result.update(
        {
            "status": status,
            "input_mode": "exported_substrate_bundle",
            "bundle_id": bundle_id,
            "bundle_manifest_schema_version": manifest.get("schema_version"),
            "accepted_count": len(accepted_rows),
            "rejected_count": len(binding_result["rejected_pattern_ids"]),
            "accepted_pattern_ids": sorted(str(row["pattern_id"]) for row in accepted_rows),
            "rejected_pattern_ids": binding_result["rejected_pattern_ids"],
            "duplicate_pattern_ids": binding_result["duplicate_pattern_ids"],
            "error_codes": error_codes,
            "expected_negative_cases": {},
            "observed_negative_cases": observed,
            "missing_negative_cases": [],
            "findings": all_findings,
            "secret_exclusion_scan": scan_result,
            "body_in_receipt": False,
            "real_runtime_receipt": status == PASS,
            "synthetic_receipt_standin_allowed": False,
            "accepted_count_is_product_progress": truth_accounting["accepted_count_is_product_progress"],
            "counts_as_real_substrate_progress": truth_accounting["counts_as_real_substrate_progress"],
            "substrate_import_status": truth_accounting["substrate_import_status"],
            "real_substrate_progress_count": truth_accounting["real_pattern_ledger_row_count"],
            "runtime_metadata_only_row_count": truth_accounting["runtime_metadata_only_row_count"],
            "truth_accounting": truth_accounting,
            "real_pattern_ledger_consumed": uses_real_ledger,
            "real_pattern_ledger_source": (
                {
                    "status": real_ledger_projection["status"],
                    "source_ref": real_ledger_projection["source_ref"],
                    "row_count": real_ledger_projection["row_count"],
                    "sha256": real_ledger_projection["sha256"],
                    "expected_sha256": real_ledger_projection["expected_sha256"],
                    "expected_row_count": real_ledger_projection["expected_row_count"],
                    "normalized_pattern_row_count": len(real_ledger_projection["pattern_rows"]),
                }
                if real_ledger_projection is not None
                else None
            ),
            "legacy_runtime_metadata_row_count": len(bundle["patterns"]),
            "legacy_runtime_metadata_only_row_count": legacy_runtime_metadata_only_count,
            "public_runtime_refs": _source_capsule_runtime_refs(
                sorted({ref for row in accepted_rows for ref in _pattern_source_refs(row)}),
                source_capsules,
            ),
            "authority_ceiling": {
                "status": PASS,
                "authority_ceiling": AUTHORITY_CEILING,
                "runtime_claim": (
                    "real pattern-ledger binding validation"
                    if uses_real_ledger
                    else "exported substrate bundle validation only"
                ),
            },
            "source_capsule_count": source_capsule_receipt["source_capsule_count"],
            "omission_receipt_count": len(bundle["omission_receipts"].get("omission_receipts", []))
            if isinstance(bundle["omission_receipts"], dict)
            else 0,
            "authority_chain_resolution_status": authority_result["authority_chain_resolution_status"],
            "reference_capsule_resolution_status": PASS if not reference_result["findings"] else "blocked",
            "anti_claim": (
                "An exported substrate bundle validates public pattern-ledger bindings. "
                "It does not inline secret, provider, operator, or source bodies or prove release readiness."
            ),
        }
    )
    receipt_path = _write_substrate_bundle_receipt(out_dir, result)
    result["receipt_paths"] = [receipt_path]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command_name")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("validate-substrate-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command_name == "validate":
        command = (
            "python -m microcosm_core.organs.pattern_binding_contract "
            f"validate --input {args.input} --out {args.out}"
        )
        result = validate(args.input, args.out, command=command)
    elif args.command_name == "validate-substrate-bundle":
        command = (
            "python -m microcosm_core.organs.pattern_binding_contract "
            f"validate-substrate-bundle --input {args.input} --out {args.out}"
        )
        result = validate_substrate_bundle(args.input, args.out, command=command)
    else:
        parser.error("expected subcommand: validate or validate-substrate-bundle")
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
