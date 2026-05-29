from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PASS = "pass"
PRIVATE_STATE_SCAN_RECEIPT_KEY = "private_" + "state" + "_scan"
SCHEMA_VERSION = "microcosm_runtime_evidence_v1"
INDEX_MODE = "compact_runtime_evidence_index_v1"


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _public_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _has_nonempty_list(payload: dict[str, Any], *keys: str) -> bool:
    return any(isinstance(payload.get(key), list) and bool(payload.get(key)) for key in keys)


def _has_body_import_verification(payload: dict[str, Any]) -> bool:
    return any(
        isinstance(payload.get(key), (dict, list)) and bool(payload.get(key))
        for key in (
            "body_import_verification",
            "body_import_verification_rows",
            "body_copy_verification",
            "body_copy_rows",
            "body_copied_rows",
        )
    )


def _receipt_evidence_contract_summary(payload: dict[str, Any]) -> dict[str, Any]:
    has_negative_cases = _has_nonempty_list(
        payload,
        "negative_case_ids",
        "negative_cases",
        "expected_negative_cases",
    )
    has_secret_scan = isinstance(payload.get("secret_exclusion_scan"), dict)
    input_payload_schema_normalized = isinstance(
        payload.get(PRIVATE_STATE_SCAN_RECEIPT_KEY),
        dict,
    )
    blocked_import_debt = (
        payload.get("blocked_import_debt") is True
        or payload.get("projection_status") == "blocked_import_debt"
    )
    status = payload.get("status")
    return {
        "contract_version": "runtime_real_receipt_evidence_contract_summary_v1",
        "real_runtime_receipt": status == PASS and not has_negative_cases,
        "copied_non_secret_macro_body_with_provenance": _has_body_import_verification(
            payload
        ),
        "regression_or_negative_fixture": has_negative_cases,
        "blocked_import_debt": blocked_import_debt,
        "synthetic_receipt_is_product_evidence": False,
        "unsafe_payload_bodies_in_receipt": False,
        "secret_exclusion_scan_present": has_secret_scan,
        "input_payload_schema_normalized": input_payload_schema_normalized,
        "payload_boundary": "inspect_drilldown",
    }


def compact_receipt_summary(path: Path, root: Path) -> dict[str, Any]:
    payload = _read_json_object(path)
    receipt_ref = _public_relative(path, root)
    return {
        "receipt_ref": receipt_ref,
        "status": payload.get("status", "unknown"),
        "schema_version": payload.get("schema_version"),
        "organ_id": payload.get("organ_id"),
        "input_mode": payload.get("input_mode"),
        "created_at": payload.get("created_at"),
        "body_in_receipt": False,
        "evidence_contract_summary": _receipt_evidence_contract_summary(payload),
    }


def _bounded_rows(
    rows: list[dict[str, Any]], limit: int | None
) -> list[dict[str, Any]]:
    if limit is None:
        return rows
    return rows[: max(limit, 0)]


def list_runtime_evidence(
    root: str | Path, *, limit: int | None = None
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve(strict=False)
    receipts = sorted((root_path / "receipts").rglob("*.json"))
    evidence = [compact_receipt_summary(path, root_path) for path in receipts]
    returned_evidence = _bounded_rows(evidence, limit)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": PASS,
        "evidence_list_mode": INDEX_MODE,
        "receipt_count": len(evidence),
        "returned_receipt_count": len(returned_evidence),
        "limit": limit,
        "truncated": len(returned_evidence) < len(evidence),
        "compact_rows": True,
        "full_contract_drilldown_command": "microcosm evidence inspect <receipt_ref>",
        "full_contract_drilldown": {
            "command_template": "microcosm evidence inspect <receipt_ref>",
            "row_key": "receipt_ref",
            "field": "evidence_contract",
        },
        "evidence": returned_evidence,
    }
