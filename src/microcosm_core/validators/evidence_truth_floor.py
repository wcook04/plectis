from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.evidence_truth_floor"
EVIDENCE_CLASS_REGISTRY_REL = Path("core/organ_evidence_classes.json")
FIRST_WAVE_RECEIPTS_REL = Path("receipts/first_wave")
FIXTURE_ECHO_CLASS = "fixture_echo_smoke"
REAL_RUNTIME_STATUS = "real_runtime_receipt_landed"
REAL_RUNTIME_CLASSIFICATION = "real_runtime_receipt"
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
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)]


def _display(path: Path, *, public_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(public_root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


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
        return sorted(receipt_dir.glob("*.json"))
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
    return {
        "receipt_ref": _display(path, public_root=public_root),
        "status": status,
        "body_import_status": body_import_status,
        "body_import_classification": classification,
        "body_in_receipt": body_in_receipt,
        "source_ref_count": _list_count(verification.get("source_refs"))
        + int(bool(verification.get("source_ref"))),
        "target_ref_count": _list_count(verification.get("target_refs"))
        + int(bool(verification.get("target_ref"))),
        "validation_ref_count": _list_count(verification.get("validation_refs")),
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


def audit_evidence_truth_floor(public_root: str | Path) -> dict[str, Any]:
    root = _public_root_for_path(public_root)
    registry = read_json_strict(root / EVIDENCE_CLASS_REGISTRY_REL)
    if not isinstance(registry, dict):
        raise ValueError(f"{EVIDENCE_CLASS_REGISTRY_REL} must be a JSON object")

    candidates: list[dict[str, Any]] = []
    inspected_fixture_echo_rows = 0
    for row in _rows(registry, "organ_evidence_classes"):
        if row.get("evidence_class") != FIXTURE_ECHO_CLASS:
            continue
        organ_id = str(row.get("organ_id") or "")
        if not organ_id:
            continue
        inspected_fixture_echo_rows += 1
        for path in _receipt_paths(root, organ_id):
            evidence = _receipt_evidence(root, path)
            if evidence is None:
                continue
            candidate = _candidate_from_evidence(organ_id, row, evidence)
            if candidate is not None:
                candidates.append(candidate)
                break

    counts_by_classification: dict[str, int] = {}
    for candidate in candidates:
        key = str(candidate["candidate_classification"])
        counts_by_classification[key] = counts_by_classification.get(key, 0) + 1

    return {
        "schema_version": "microcosm_evidence_truth_floor_audit_v1",
        "checker_id": CHECKER_ID,
        "status": "pass",
        "source_ref": EVIDENCE_CLASS_REGISTRY_REL.as_posix(),
        "receipt_root_ref": FIRST_WAVE_RECEIPTS_REL.as_posix(),
        "inspected_fixture_echo_row_count": inspected_fixture_echo_rows,
        "candidate_count": len(candidates),
        "candidate_counts_by_classification": dict(sorted(counts_by_classification.items())),
        "blocking_issue_count": 0,
        "advisory_only": True,
        "candidates": sorted(
            candidates,
            key=lambda item: (
                str(item["candidate_classification"]),
                str(item["organ_id"]),
            ),
        ),
        "anti_claim": (
            "This audit is a truth-floor finder, not an automatic promotion. A row "
            "still needs owner review before fixture evidence can count as product progress."
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
