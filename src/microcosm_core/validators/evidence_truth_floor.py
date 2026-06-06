from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.evidence_truth_floor"
EVIDENCE_CLASS_REGISTRY_REL = Path("core/organ_evidence_classes.json")
ORGAN_REGISTRY_REL = Path("core/organ_registry.json")
FIRST_WAVE_RECEIPTS_REL = Path("receipts/first_wave")
FIXTURE_ECHO_CLASS = "fixture_echo_smoke"
REAL_RUNTIME_STATUS = "real_runtime_receipt_landed"
REAL_RUNTIME_CLASSIFICATION = "real_runtime_receipt"
ALLOWED_REAL_SUBSTRATE_DISPOSITIONS = frozenset(
    {
        "real_substrate_capsule",
        "retained_regression_validator",
        "deleted_or_demoted_historical_artifact",
        "blocked_secret_only",
    }
)
REAL_SUBSTRATE_DISPOSITION = "real_substrate_capsule"
RETAINED_REGRESSION_VALIDATOR_DISPOSITION = "retained_regression_validator"
SYNTHETIC_TRUTH_BUCKET = "regression_negative_fixture"
PUBLIC_REFACTOR_STATUS_MARKERS = (
    "public_refactor_landed",
    "source_faithful_refactor_landed",
    "extension_of_existing_public_refactor_landed",
)
PUBLIC_REFACTOR_CLASSIFICATION_MARKERS = (
    "public_refactor",
    "source_faithful_refactor",
)


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
            return candidate
    return Path.cwd().resolve(strict=False)


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)]


def _accepted_registry_rows_by_organ(public_root: Path) -> dict[str, dict[str, Any]]:
    registry = read_json_strict(public_root / ORGAN_REGISTRY_REL)
    if not isinstance(registry, dict):
        raise ValueError(f"{ORGAN_REGISTRY_REL} must be a JSON object")
    return {
        str(row.get("organ_id")): row
        for row in _rows(registry, "implemented_organs")
        if row.get("organ_id") and row.get("status") == "accepted_current_authority"
    }


def _synthetic_disposition_value(row: dict[str, Any]) -> str:
    value = row.get("synthetic_acceptance_disposition")
    if isinstance(value, dict):
        return str(value.get("disposition") or "")
    if isinstance(value, str):
        return value
    return ""


def _disposition_issue(
    organ_id: str,
    evidence_class_row: dict[str, Any],
    registry_row: dict[str, Any],
) -> dict[str, Any] | None:
    disposition = str(registry_row.get("real_substrate_disposition") or "")
    synthetic_disposition = _synthetic_disposition_value(registry_row)
    truth_bucket = str(registry_row.get("truth_accounting_bucket") or "")
    counts_as_progress = registry_row.get("counts_as_real_substrate_progress") is True
    evidence_class = str(evidence_class_row.get("evidence_class") or "")
    missing_fields: list[str] = []
    invalid_fields: list[str] = []
    mismatch_reasons: list[str] = []

    if not disposition:
        missing_fields.append("real_substrate_disposition")
    elif disposition not in ALLOWED_REAL_SUBSTRATE_DISPOSITIONS:
        invalid_fields.append("real_substrate_disposition")
    if not synthetic_disposition:
        missing_fields.append("synthetic_acceptance_disposition")
    elif synthetic_disposition != RETAINED_REGRESSION_VALIDATOR_DISPOSITION:
        invalid_fields.append("synthetic_acceptance_disposition")
    if counts_as_progress:
        mismatch_reasons.append("fixture_echo_smoke_counts_as_real_substrate_progress")
    if disposition and disposition != RETAINED_REGRESSION_VALIDATOR_DISPOSITION:
        mismatch_reasons.append("fixture_echo_smoke_disposition_claims_real_substrate")
    if truth_bucket != SYNTHETIC_TRUTH_BUCKET:
        mismatch_reasons.append("fixture_echo_smoke_truth_bucket_mismatch")

    if not missing_fields and not invalid_fields and not mismatch_reasons:
        return None
    if mismatch_reasons:
        code = "synthetic_acceptance_progress_flag_mismatch"
    elif invalid_fields:
        code = "invalid_synthetic_acceptance_disposition"
    else:
        code = "missing_synthetic_acceptance_dispositions"
    return {
        "organ_id": organ_id,
        "code": code,
        "current_evidence_class": evidence_class,
        "registry_evidence_class": registry_row.get("evidence_class"),
        "truth_accounting_bucket": truth_bucket,
        "counts_as_real_substrate_progress": counts_as_progress,
        "real_substrate_disposition": disposition,
        "synthetic_acceptance_disposition": synthetic_disposition,
        "missing_fields": missing_fields,
        "invalid_fields": invalid_fields,
        "mismatch_reasons": mismatch_reasons,
    }


def _display(path: Path, *, public_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(public_root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_json_receipt_files(root: Path):
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        yield from _iter_json_receipt_files(Path(entry.path))
                    elif (
                        entry.is_file(follow_symlinks=False)
                        and entry.name.endswith(".json")
                    ):
                        yield Path(entry.path)
                except OSError:
                    continue
    except OSError:
        return


def _receipt_paths(public_root: Path, organ_id: str) -> list[Path]:
    receipt_dir = public_root / FIRST_WAVE_RECEIPTS_REL / organ_id
    names = (
        f"{organ_id}_validation_receipt.json",
        f"{organ_id}_result.json",
        f"{organ_id}_board.json",
    )
    paths = [receipt_dir / name for name in names if (receipt_dir / name).is_file()]
    if paths:
        return paths
    if receipt_dir.is_dir():
        return sorted(_iter_json_receipt_files(receipt_dir))
    return []


def _verification(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("body_import_verification")
    return value if isinstance(value, dict) else {}


def _body_in_receipt(payload: dict[str, Any], verification: dict[str, Any]) -> bool | None:
    for source in (verification, payload):
        value = source.get("body_in_receipt")
        if isinstance(value, bool):
            return value
    return None


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _ref_values(verification: dict[str, Any], plural_key: str, singular_key: str) -> list[str]:
    refs: list[str] = []
    plural = verification.get(plural_key)
    if isinstance(plural, list):
        refs.extend(str(ref) for ref in plural if str(ref).strip())
    singular = verification.get(singular_key)
    if str(singular or "").strip():
        refs.append(str(singular))
    return list(dict.fromkeys(refs))


def _is_public_body_ref(ref: str) -> bool:
    normalized = ref.removeprefix("microcosm-substrate/")
    if normalized.startswith(("fixtures/", "receipts/")):
        return False
    generated_markers = (
        "/generated_",
        ".generated.",
        "generated_projection",
        "projection_receipt",
    )
    return not any(marker in normalized for marker in generated_markers)


def _receipt_evidence(public_root: Path, path: Path) -> dict[str, Any] | None:
    payload = read_json_strict(path)
    if not isinstance(payload, dict):
        return None
    verification = _verification(payload)
    body_import_status = str(
        payload.get("body_import_status")
        or verification.get("body_import_status")
        or ""
    )
    classification = str(verification.get("classification") or "")
    body_in_receipt = _body_in_receipt(payload, verification)
    status = str(payload.get("status") or verification.get("status") or "")
    source_refs = _ref_values(verification, "source_refs", "source_ref")
    target_refs = _ref_values(verification, "target_refs", "target_ref")
    validation_refs = _ref_values(verification, "validation_refs", "validation_ref")
    return {
        "receipt_ref": _display(path, public_root=public_root),
        "status": status,
        "body_import_status": body_import_status,
        "body_import_classification": classification,
        "body_in_receipt": body_in_receipt,
        "source_refs": source_refs,
        "target_refs": target_refs,
        "validation_refs": validation_refs,
        "source_ref_count": len(source_refs),
        "target_ref_count": len(target_refs),
        "validation_ref_count": len(validation_refs),
        "input_ref_count": _list_count(verification.get("input_refs")),
        "secret_exclusion_scan_status": (
            payload.get("secret_exclusion_scan", {}).get("status")
            if isinstance(payload.get("secret_exclusion_scan"), dict)
            else None
        ),
    }


def _candidate_from_evidence(
    organ_id: str,
    row: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    body_import_status = str(evidence.get("body_import_status") or "")
    classification = str(evidence.get("body_import_classification") or "")
    body_in_receipt = evidence.get("body_in_receipt")
    status = str(evidence.get("status") or "")
    eligible_body_free = body_in_receipt is False
    if (
        body_import_status == REAL_RUNTIME_STATUS
        and classification == REAL_RUNTIME_CLASSIFICATION
        and status == "pass"
        and eligible_body_free
    ):
        return {
            "organ_id": organ_id,
            "candidate_classification": "real_runtime_receipt_candidate",
            "current_evidence_class": row.get("evidence_class"),
            "recommended_evidence_class": "semantic_validator",
            "recommended_truth_accounting_bucket": "real_import_validation",
            "reason": (
                "fixture_echo_smoke row has a passing body-free real runtime receipt "
                "verification; it should be reviewed for product-progress reclassification."
            ),
            "evidence": evidence,
        }
    if (
        any(marker in body_import_status for marker in PUBLIC_REFACTOR_STATUS_MARKERS)
        and any(marker in classification for marker in PUBLIC_REFACTOR_CLASSIFICATION_MARKERS)
        and status == "pass"
        and eligible_body_free
    ):
        return {
            "organ_id": organ_id,
            "candidate_classification": "source_faithful_refactor_candidate",
            "current_evidence_class": row.get("evidence_class"),
            "recommended_evidence_class": "algorithmic_projection",
            "recommended_truth_accounting_bucket": "source_faithful_refactor",
            "reason": (
                "fixture_echo_smoke row has a passing body-free public refactor "
                "verification; it should be reviewed for product-progress reclassification."
            ),
            "evidence": evidence,
        }
    return None


def _proof_gap_from_evidence(
    organ_id: str,
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    body_import_status = str(evidence.get("body_import_status") or "")
    classification = str(evidence.get("body_import_classification") or "")
    status = str(evidence.get("status") or "")
    body_in_receipt = evidence.get("body_in_receipt")
    has_candidate_marker = (
        body_import_status == REAL_RUNTIME_STATUS
        and classification == REAL_RUNTIME_CLASSIFICATION
    ) or (
        any(marker in body_import_status for marker in PUBLIC_REFACTOR_STATUS_MARKERS)
        and any(
            marker in classification
            for marker in PUBLIC_REFACTOR_CLASSIFICATION_MARKERS
        )
    )
    if not has_candidate_marker:
        return None
    missing_proof_fields: list[str] = []
    if status != "pass":
        missing_proof_fields.append("status=pass")
    if body_in_receipt is not False:
        missing_proof_fields.append("body_in_receipt=false")
    if int(evidence.get("source_ref_count") or 0) <= 0:
        missing_proof_fields.append("source_ref")
    elif not any(_is_public_body_ref(ref) for ref in evidence.get("source_refs", [])):
        missing_proof_fields.append(
            "source_ref_public_substrate_not_fixture_receipt_or_generated_projection"
        )
    if int(evidence.get("target_ref_count") or 0) <= 0:
        missing_proof_fields.append("target_ref")
    elif not any(_is_public_body_ref(ref) for ref in evidence.get("target_refs", [])):
        missing_proof_fields.append(
            "target_ref_public_body_not_fixture_receipt_or_generated_projection"
        )
    if int(evidence.get("validation_ref_count") or 0) <= 0:
        missing_proof_fields.append("validation_ref")
    if evidence.get("secret_exclusion_scan_status") != "pass":
        missing_proof_fields.append("secret_exclusion_scan.status=pass")
    if not missing_proof_fields:
        return None
    return {
        "organ_id": organ_id,
        "code": "fixture_echo_receipt_without_public_body_proof",
        "receipt_ref": evidence.get("receipt_ref"),
        "body_import_status": body_import_status,
        "body_import_classification": classification,
        "missing_proof_fields": missing_proof_fields,
        "evidence": evidence,
    }


def audit_evidence_truth_floor(public_root: str | Path) -> dict[str, Any]:
    root = _public_root_for_path(public_root)
    registry = read_json_strict(root / EVIDENCE_CLASS_REGISTRY_REL)
    if not isinstance(registry, dict):
        raise ValueError(f"{EVIDENCE_CLASS_REGISTRY_REL} must be a JSON object")
    accepted_registry_rows = _accepted_registry_rows_by_organ(root)

    candidates: list[dict[str, Any]] = []
    disposition_issues: list[dict[str, Any]] = []
    proof_gap_issues: list[dict[str, Any]] = []
    inspected_fixture_echo_rows = 0
    for row in _rows(registry, "organ_evidence_classes"):
        if row.get("evidence_class") != FIXTURE_ECHO_CLASS:
            continue
        organ_id = str(row.get("organ_id") or "")
        if not organ_id:
            continue
        inspected_fixture_echo_rows += 1
        registry_row = accepted_registry_rows.get(organ_id)
        if registry_row is not None:
            issue = _disposition_issue(organ_id, row, registry_row)
            if issue is not None:
                disposition_issues.append(issue)
        for path in _receipt_paths(root, organ_id):
            evidence = _receipt_evidence(root, path)
            if evidence is None:
                continue
            proof_gap = _proof_gap_from_evidence(organ_id, evidence)
            if proof_gap is not None:
                proof_gap_issues.append(proof_gap)
                continue
            candidate = _candidate_from_evidence(organ_id, row, evidence)
            if candidate is not None:
                candidates.append(candidate)
                break

    counts_by_classification: dict[str, int] = {}
    for candidate in candidates:
        key = str(candidate["candidate_classification"])
        counts_by_classification[key] = counts_by_classification.get(key, 0) + 1
    disposition_issue_counts: dict[str, int] = {}
    for issue in disposition_issues:
        key = str(issue["code"])
        disposition_issue_counts[key] = disposition_issue_counts.get(key, 0) + 1
    proof_gap_issue_counts: dict[str, int] = {}
    for issue in proof_gap_issues:
        key = str(issue["code"])
        proof_gap_issue_counts[key] = proof_gap_issue_counts.get(key, 0) + 1
    blocking_issue_count = len(disposition_issues) + len(proof_gap_issues)

    return {
        "schema_version": "microcosm_evidence_truth_floor_audit_v1",
        "checker_id": CHECKER_ID,
        "status": "pass" if blocking_issue_count == 0 else "blocked",
        "source_ref": EVIDENCE_CLASS_REGISTRY_REL.as_posix(),
        "registry_ref": ORGAN_REGISTRY_REL.as_posix(),
        "receipt_root_ref": FIRST_WAVE_RECEIPTS_REL.as_posix(),
        "inspected_fixture_echo_row_count": inspected_fixture_echo_rows,
        "candidate_count": len(candidates),
        "candidate_counts_by_classification": dict(sorted(counts_by_classification.items())),
        "blocking_issue_count": blocking_issue_count,
        "disposition_issue_counts_by_code": dict(
            sorted(disposition_issue_counts.items())
        ),
        "proof_gap_issue_counts_by_code": dict(
            sorted(proof_gap_issue_counts.items())
        ),
        "advisory_only": blocking_issue_count == 0,
        "disposition_guard": {
            "schema_version": "microcosm_synthetic_acceptance_disposition_guard_v1",
            "allowed_dispositions": sorted(ALLOWED_REAL_SUBSTRATE_DISPOSITIONS),
            "required_synthetic_disposition": (
                RETAINED_REGRESSION_VALIDATOR_DISPOSITION
            ),
            "fixture_echo_smoke_must_not_count_as_real_progress": True,
            "issue_count": len(disposition_issues),
            "issues": sorted(
                disposition_issues,
                key=lambda item: (str(item["code"]), str(item["organ_id"])),
            ),
        },
        "proof_gap_guard": {
            "schema_version": "microcosm_fixture_receipt_public_body_proof_guard_v1",
            "candidate_receipts_require_source_target_validation_refs": True,
            "candidate_receipts_reject_fixture_receipt_or_generated_projection_refs": True,
            "candidate_receipts_require_secret_exclusion_scan_pass": True,
            "issue_count": len(proof_gap_issues),
            "issues": sorted(
                proof_gap_issues,
                key=lambda item: (str(item["code"]), str(item["organ_id"])),
            ),
        },
        "candidates": sorted(
            candidates,
            key=lambda item: (
                str(item["candidate_classification"]),
                str(item["organ_id"]),
            ),
        ),
        "anti_claim": (
            "This audit is a truth-floor finder, not an automatic promotion. A row "
            "still needs owner review and public body proof before fixture evidence can "
            "count as product progress."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Path inside the public microcosm-substrate root.",
    )
    parser.add_argument("--out", help="Optional JSON receipt path.")
    args = parser.parse_args(argv)

    receipt = audit_evidence_truth_floor(args.root)
    if args.out:
        write_json_atomic(args.out, receipt)
    else:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
