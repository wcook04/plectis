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


def _without_legacy_body_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in {"body_redacted", "matched_excerpt", "body"}
    }


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
    return scan


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


def _has_public_root_ancestor(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    start = resolved if path.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == _legacy.PUBLIC_ROOT_DIR_NAME or _legacy._looks_like_public_root(candidate):
            return True
    return False


def scan_paths(
    paths: list[str | Path],
    *,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
    display_root: str | Path | None = None,
) -> dict[str, Any]:
    raw_scan = _legacy.scan_paths(
        paths,
        forbidden_classes=forbidden_classes,
        source_context=source_context,
        display_root=display_root,
    )
    scan = normalize_secret_exclusion_scan(raw_scan)
    if display_root is None:
        absolute_paths = {
            _legacy.public_relative_path(Path(raw_path), display_root=None): str(
                Path(raw_path).resolve(strict=False)
            )
            for raw_path in paths
            if Path(raw_path).is_absolute()
            and not _has_public_root_ancestor(Path(raw_path))
        }
        scan["hits"] = [
            {**hit, "path": absolute_paths.get(str(hit.get("path")), hit.get("path"))}
            if isinstance(hit, dict)
            else hit
            for hit in scan.get("hits", [])
        ]
    return scan


def scan_json_payload(
    payload: object,
    *,
    path: str,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
) -> dict[str, Any]:
    return normalize_secret_exclusion_scan(
        _legacy.scan_json_payload(
            payload,
            path=path,
            forbidden_classes=forbidden_classes,
            source_context=source_context,
        )
    )


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
