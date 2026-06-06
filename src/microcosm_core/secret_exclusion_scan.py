from __future__ import annotations

from pathlib import Path
from typing import Any

from . import private_state_scan as _legacy
from .private_state_scan import (
    BLOCKED_CASE_REVIEW,
    BLOCKED_PRIVATE,
    BLOCKED_PUBLIC_WRITE,
    PASS,
    TEXT_FILENAMES as _TEXT_FILENAMES,
    is_text_scan_candidate,
    load_forbidden_classes,
    public_relative_path,
)

BLOCKED_SECRET_EXCLUSION = BLOCKED_PRIVATE
TEXT_SUFFIXES = frozenset(_legacy.TEXT_SUFFIXES)
TEXT_FILENAMES = frozenset(_TEXT_FILENAMES)
RECEIPT_BODY_FIELD_KEYS = frozenset(
    {
        "body",
        "matched_excerpt",
        "source_body",
        "source_text",
        "payload_body",
        "provider_payload",
        "session_payload",
        "operator_thread_body",
        "credential_payload",
    }
)
EXPECTED_NEGATIVE_MARKER_KEYS = frozenset(
    {
        "expected_negative_case",
        "expected_negative_case_id",
        "negative_case_id",
        "synthetic_negative_fixture",
    }
)


def _without_legacy_body_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in {"body_redacted", "matched_excerpt", "body"}
    }


def _refresh_scan_counts(scan: dict[str, Any]) -> dict[str, Any]:
    hits = [dict(hit) for hit in scan.get("hits", []) if isinstance(hit, dict)]
    blocking_hits = [hit for hit in hits if not hit.get("expected_negative_case")]
    if any(hit.get("forbidden_class") == "target_only_not_source" for hit in blocking_hits):
        status = BLOCKED_PUBLIC_WRITE
    elif blocking_hits:
        status = BLOCKED_SECRET_EXCLUSION
    else:
        status = PASS
    scan["status"] = status
    scan["hits"] = hits
    scan["hit_count"] = len(hits)
    scan["blocking_hit_count"] = len(blocking_hits)
    return scan


def normalize_secret_exclusion_scan(raw_scan: dict[str, Any]) -> dict[str, Any]:
    """Return the receipt-facing secret-exclusion shape.

    Legacy scanner internals still know how to find sentinel terms, but the
    public receipt contract is source-open by default: the scanner proves that
    secrets/account-bound payload bodies are excluded, not that ordinary macro
    substrate was redacted.
    """

    legacy_scan_keys = {
        "body_redacted",
        "forbidden_output_fields",
        "redacted_output_field_labels_omitted",
    }
    scan = {key: value for key, value in raw_scan.items() if key not in legacy_scan_keys}
    scan["scan_purpose"] = "credential_account_bound_and_operator_payload_exclusion"
    scan["omitted_output_fields"] = ["source_excerpt", "body"]
    scan["body_in_receipt"] = False
    scan["real_substrate_default"] = True
    scan["synthetic_receipt_policy"] = (
        "Synthetic receipts are admissible only as regression or negative-case "
        "harness artifacts, or as named blocked-import debt. They are not "
        "substitutes for non-secret macro substrate, real runtime receipts, "
        "real copied bodies, or source-faithful refactors."
    )
    scan["exclusion_policy"] = (
        "Open-source macro substrate by default; exclude only secrets, "
        "credentials, operator conversation bodies, provider payloads, "
        "account/session state, and credential-equivalent live-access material."
    )
    scan["hits"] = [
        _without_legacy_body_fields(dict(hit)) | {"body_in_receipt": False}
        for hit in raw_scan.get("hits", [])
        if isinstance(hit, dict)
    ]
    return _refresh_scan_counts(scan)


def _payload_has_expected_negative_marker(payload: object) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in EXPECTED_NEGATIVE_MARKER_KEYS:
                return True
            if _payload_has_expected_negative_marker(value):
                return True
    elif isinstance(payload, list):
        return any(_payload_has_expected_negative_marker(item) for item in payload)
    return False


def _receipt_payload_field_hits(
    payload: object,
    *,
    path: str,
    expected_negative: bool,
    prefix: str = "",
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            field_path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in RECEIPT_BODY_FIELD_KEYS:
                hit = {
                    "path": path,
                    "forbidden_class": "receipt_payload_body_field",
                    "term_id": f"receipt_payload_field:{key_text}",
                    "field_path": field_path,
                    "body_in_receipt": False,
                    "remediation": (
                        "Move raw payload material to public source modules or fixtures "
                        "and keep receipts to public refs, hashes, counts, and anchors."
                    ),
                }
                if expected_negative:
                    hit["expected_negative_case"] = True
                hits.append(hit)
                continue
            hits.extend(
                _receipt_payload_field_hits(
                    value,
                    path=path,
                    expected_negative=expected_negative,
                    prefix=field_path,
                )
            )
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            field_path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            hits.extend(
                _receipt_payload_field_hits(
                    item,
                    path=path,
                    expected_negative=expected_negative,
                    prefix=field_path,
                )
            )
    return hits


def _merge_receipt_payload_boundary(
    scan: dict[str, Any],
    payload: object,
    *,
    path: str,
) -> dict[str, Any]:
    expected_negative = _payload_has_expected_negative_marker(payload)
    hits = _receipt_payload_field_hits(
        payload,
        path=path,
        expected_negative=expected_negative,
    )
    blocking_count = len([hit for hit in hits if not hit.get("expected_negative_case")])
    scan.setdefault("hits", [])
    scan["hits"].extend(hits)
    scan["receipt_payload_field_guard"] = {
        "status": PASS if blocking_count == 0 else BLOCKED_SECRET_EXCLUSION,
        "forbidden_field_count": len(hits),
        "blocking_field_count": blocking_count,
        "body_in_receipt": False,
    }
    return _refresh_scan_counts(scan)


def classify_public_safe_macro_import(
    row: dict[str, Any],
    *,
    forbidden_classes: dict[str, Any],
) -> dict[str, Any]:
    raw = _legacy.classify_public_safe_macro_import(
        row,
        forbidden_classes=forbidden_classes,
    )
    result = _without_legacy_body_fields(dict(raw))
    result["body_in_receipt"] = False
    result["real_substrate_default"] = True
    result["synthetic_receipt_policy"] = "not_a_substitute_for_available_real_substrate"
    result["findings"] = [
        _without_legacy_body_fields(dict(finding)) | {"body_in_receipt": False}
        for finding in raw.get("findings", [])
        if isinstance(finding, dict)
    ]
    return result


def scan_text(
    text: str,
    *,
    path: str,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
) -> dict[str, Any]:
    return normalize_secret_exclusion_scan(
        _legacy.scan_text(
            text,
            path=path,
            forbidden_classes=forbidden_classes,
            source_context=source_context,
        )
    )


def scan_paths(
    paths: list[str | Path],
    *,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
    display_root: str | Path | None = None,
) -> dict[str, Any]:
    return normalize_secret_exclusion_scan(
        _legacy.scan_paths(
            paths,
            forbidden_classes=forbidden_classes,
            source_context=source_context,
            display_root=display_root,
        )
    )


def scan_json_payload(
    payload: object,
    *,
    path: str,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
) -> dict[str, Any]:
    scan = normalize_secret_exclusion_scan(
        _legacy.scan_json_payload(
            payload,
            path=path,
            forbidden_classes=forbidden_classes,
            source_context=source_context,
        )
    )
    return _merge_receipt_payload_boundary(scan, payload, path=path)


__all__ = [
    "BLOCKED_CASE_REVIEW",
    "BLOCKED_PRIVATE",
    "BLOCKED_PUBLIC_WRITE",
    "BLOCKED_SECRET_EXCLUSION",
    "PASS",
    "TEXT_FILENAMES",
    "TEXT_SUFFIXES",
    "classify_public_safe_macro_import",
    "is_text_scan_candidate",
    "load_forbidden_classes",
    "normalize_secret_exclusion_scan",
    "public_relative_path",
    "scan_json_payload",
    "scan_paths",
    "scan_text",
]
