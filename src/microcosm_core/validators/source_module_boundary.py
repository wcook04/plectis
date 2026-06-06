from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.source_module_boundary"
SCHEMA_VERSION = "source_module_boundary_card_v1"
PASS = "pass"
BLOCKED = "blocked"

REF_FIELD_KEYS = frozenset(
    {
        "path",
        "paths",
        "public_replacement_refs",
        "projection_receipt_refs",
        "provenance_ref",
        "provenance_refs",
        "repo_path",
        "repo_paths",
        "source_artifact_ref",
        "source_artifact_refs",
        "source_module_manifest_ref",
        "source_module_manifest_refs",
        "source_module_ref",
        "source_module_refs",
        "source_path",
        "source_paths",
        "source_ref",
        "source_refs",
        "target_path",
        "target_paths",
        "target_ref",
        "target_refs",
        "validation_ref",
        "validation_refs",
    }
)

REF_FIELD_SUFFIXES = ("_ref", "_refs", "_path", "_paths")

SOURCE_REF_FIELD_KEYS = frozenset(
    {
        "source_ref",
        "source_refs",
        "source_path",
        "source_paths",
    }
)

TARGET_REF_FIELD_KEYS = frozenset(
    {
        "path",
        "paths",
        "target_ref",
        "target_refs",
        "target_path",
        "target_paths",
    }
)

SOURCE_MODULE_CLAIM_MARKER_KEYS = frozenset(
    {
        "artifact_id",
        "body_copied",
        "body_in_receipt",
        "copy_policy",
        "material_class",
        "module_id",
        "source_import_class",
        "source_to_target_relation",
    }
)

NON_REF_KEYS = frozenset(
    {
        "anti_claim",
        "body_storage_policy",
        "public_runtime_policy",
        "receipt_body_policy",
        "required_anchors",
        "secret_exclusion_boundary",
        "source_open_payload_boundary",
        "source_role",
    }
)

ROW_ID_KEYS = (
    "module_id",
    "material_id",
    "cell_id",
    "witness_id",
    "manifest_id",
    "bundle_id",
)

FORBIDDEN_COMPONENTS = {
    ".env",
    ".env.local",
    ".env.production",
    "account_state",
    "account_session",
    "browser_hud",
    "cookie",
    "cookies",
    "credential",
    "credentials",
    "live_access",
    "operator_chrome_hud",
    "private_prover_lab",
    "provider_payload",
    "provider_payloads",
    "provider_request_payload",
    "provider_request_payloads",
    "provider_response_payload",
    "provider_response_payloads",
    "raw_operator_voice",
    "session_cookie",
    "session_cookies",
    "session_state",
    "secrets",
}

FORBIDDEN_SUBSTRINGS = (
    "api_key",
    "browser/hud",
    "credential-equivalent",
    "credential_bearing",
    "live browser",
    "live hud",
    "operator_thread_body",
    "private live sandbox",
    "provider payload",
    "provider_payload",
    "recipient_send",
    "refresh_token",
    "session cookie",
    "session_secret",
)

ANTI_CLAIM = (
    "This read-only card checks source-module refs before exact-copy refresh. "
    "It does not certify secret absence, authorize source mutation, authorize "
    "release, or inspect live provider, account, browser/HUD, git index, or "
    "operator-state payloads."
)


def _normalize_ref(ref: object) -> str:
    value = str(ref or "").strip()
    while value.startswith("./"):
        value = value[2:]
    return value


def _path_portion(ref: str) -> str:
    path = ref.split("#", 1)[0]
    if "::" in path:
        first, _rest = path.split("::", 1)
        if "/" in first or first.endswith((".json", ".jsonl", ".py", ".md", ".lean")):
            path = first
    return path.strip()


def _path_parts(ref: str) -> list[str]:
    path = _path_portion(ref).replace("\\", "/")
    return [part for part in path.split("/") if part]


def _row_id(row: dict[str, Any], fallback: str) -> str:
    for key in ROW_ID_KEYS:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return fallback


def _is_ref_field(key: str) -> bool:
    if key in NON_REF_KEYS:
        return False
    return key in REF_FIELD_KEYS or key.endswith(REF_FIELD_SUFFIXES)


def _string_ref_values(value: object, *, field_path: str) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        normalized = _normalize_ref(value)
        if normalized:
            yield field_path, normalized
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _string_ref_values(item, field_path=f"{field_path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _string_ref_values(item, field_path=f"{field_path}.{key}")


def _has_nonempty_value(row: dict[str, Any], keys: Iterable[str]) -> bool:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and _normalize_ref(value):
            return True
        if isinstance(value, list) and any(_normalize_ref(item) for item in value):
            return True
    return False


def _first_source_ref(row: dict[str, Any]) -> str:
    for key in SOURCE_REF_FIELD_KEYS:
        value = row.get(key)
        if isinstance(value, str) and _normalize_ref(value):
            return _normalize_ref(value)
        if isinstance(value, list):
            for item in value:
                normalized = _normalize_ref(item)
                if normalized:
                    return normalized
    return ""


def _source_modules_tail(ref: object) -> str:
    parts = _path_parts(_normalize_ref(ref))
    try:
        source_modules_index = parts.index("source_modules")
    except ValueError:
        return ""
    tail = parts[source_modules_index + 1 :]
    return "/".join(tail)


def _looks_like_source_module_claim(row: dict[str, Any]) -> bool:
    return _has_nonempty_value(row, SOURCE_REF_FIELD_KEYS) and any(
        key in row for key in SOURCE_MODULE_CLAIM_MARKER_KEYS
    )


def extract_source_module_claim_rows(
    payload: object,
    *,
    manifest_ref: str = "<memory>",
    prefix: str = "",
    inherited_row_id: str = "",
) -> list[dict[str, Any]]:
    """Extract source-module claim rows that can overstate import authority."""

    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        current_row_id = _row_id(payload, inherited_row_id)
        if _looks_like_source_module_claim(payload):
            body_in_receipt = payload.get("body_in_receipt") is True
            relation = str(
                payload.get("source_to_target_relation")
                or payload.get("copy_policy")
                or ""
            ).strip()
            claims_body_material = payload.get("body_copied") is True or bool(relation)
            has_target = _has_nonempty_value(payload, TARGET_REF_FIELD_KEYS)
            source_ref = _first_source_ref(payload)
            path_tail = _source_modules_tail(payload.get("path"))
            target_tail = _source_modules_tail(payload.get("target_ref"))
            if body_in_receipt:
                rows.append(
                    {
                        "manifest_ref": manifest_ref,
                        "field_path": prefix or "<root>",
                        "row_id": current_row_id,
                        "ref": source_ref or current_row_id,
                        "error_code": "source_module_body_in_receipt_claim",
                        "reason": (
                            "source-module bodies must stay in source_modules targets, "
                            "not in public receipts"
                        ),
                        "body_in_receipt": True,
                        "coordination_action": (
                            "move_body_to_source_module_target_and_keep_receipt_body_false"
                        ),
                    }
                )
            if claims_body_material and not has_target:
                rows.append(
                    {
                        "manifest_ref": manifest_ref,
                        "field_path": prefix or "<root>",
                        "row_id": current_row_id,
                        "ref": source_ref or current_row_id,
                        "error_code": "source_module_target_ref_missing",
                        "reason": (
                            "source-module rows that claim copied or source-faithful "
                            "body material must name a public target ref/path"
                        ),
                        "body_in_receipt": body_in_receipt,
                        "coordination_action": (
                            "add_public_source_module_target_or_demote_body_claim"
                        ),
                    }
                )
            if (
                claims_body_material
                and path_tail
                and target_tail
                and path_tail != target_tail
            ):
                rows.append(
                    {
                        "manifest_ref": manifest_ref,
                        "field_path": prefix or "<root>",
                        "row_id": current_row_id,
                        "ref": source_ref or current_row_id,
                        "error_code": "source_module_path_target_ref_mismatch",
                        "reason": (
                            "source-module path and target_ref must identify "
                            "the same source_modules body"
                        ),
                        "body_in_receipt": body_in_receipt,
                        "path_tail": path_tail,
                        "target_tail": target_tail,
                        "coordination_action": (
                            "align_path_and_target_ref_to_same_source_modules_body"
                        ),
                    }
                )
        for key, value in payload.items():
            field_path = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(
                extract_source_module_claim_rows(
                    value,
                    manifest_ref=manifest_ref,
                    prefix=field_path,
                    inherited_row_id=current_row_id,
                )
            )
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            rows.extend(
                extract_source_module_claim_rows(
                    item,
                    manifest_ref=manifest_ref,
                    prefix=f"{prefix}[{index}]" if prefix else f"[{index}]",
                    inherited_row_id=inherited_row_id,
                )
            )
    return rows


def extract_source_ref_rows(
    payload: object,
    *,
    manifest_ref: str = "<memory>",
    prefix: str = "",
    inherited_row_id: str = "",
) -> list[dict[str, str]]:
    """Extract path-like source-module refs without reading referenced bodies."""

    rows: list[dict[str, str]] = []
    if isinstance(payload, dict):
        current_row_id = _row_id(payload, inherited_row_id)
        for key, value in payload.items():
            key_text = str(key)
            field_path = f"{prefix}.{key_text}" if prefix else key_text
            if _is_ref_field(key_text):
                for nested_field_path, ref in _string_ref_values(
                    value,
                    field_path=field_path,
                ):
                    rows.append(
                        {
                            "manifest_ref": manifest_ref,
                            "field_path": nested_field_path,
                            "row_id": current_row_id,
                            "ref": ref,
                        }
                    )
            else:
                rows.extend(
                    extract_source_ref_rows(
                        value,
                        manifest_ref=manifest_ref,
                        prefix=field_path,
                        inherited_row_id=current_row_id,
                    )
                )
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            rows.extend(
                extract_source_ref_rows(
                    item,
                    manifest_ref=manifest_ref,
                    prefix=f"{prefix}[{index}]" if prefix else f"[{index}]",
                    inherited_row_id=inherited_row_id,
                )
            )
    return rows


def _classify_source_ref(ref: str) -> dict[str, str] | None:
    value = _normalize_ref(ref)
    if not value:
        return None
    path = _path_portion(value)
    path_lower = path.lower().replace("\\", "/")
    parts = _path_parts(path_lower)
    filename = parts[-1] if parts else ""

    if path.startswith(("~", "/")) or path_lower.startswith(("users/", "private/")):
        return {
            "error_code": "source_ref_absolute_or_home_private_root",
            "reason": "source refs must be relative public macro paths, not host-private roots",
        }
    if ".." in parts:
        return {
            "error_code": "source_ref_parent_traversal",
            "reason": "source refs cannot escape the declared public source boundary",
        }
    if filename == "raw_seed.md":
        return {
            "error_code": "source_ref_raw_operator_voice",
            "reason": "raw seed/operator voice bodies are excluded from public body import",
        }
    component_aliases = {
        alias
        for part in parts
        for alias in (part, part.rsplit(".", 1)[0])
        if alias
    }
    forbidden_component = next(
        (part for part in component_aliases if part in FORBIDDEN_COMPONENTS),
        "",
    )
    if forbidden_component:
        return {
            "error_code": f"source_ref_forbidden_component:{forbidden_component}",
            "reason": (
                "source refs cannot point at credential, account/session, provider "
                "payload, browser/HUD, or live-access material"
            ),
        }
    forbidden_substring = next(
        (token for token in FORBIDDEN_SUBSTRINGS if token in path_lower),
        "",
    )
    if forbidden_substring:
        return {
            "error_code": f"source_ref_forbidden_boundary_text:{forbidden_substring}",
            "reason": (
                "source refs cannot describe private, credential-equivalent, provider "
                "payload, browser/HUD, operator, or recipient-send material"
            ),
        }
    return None


def _dedupe_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (
            row.get("manifest_ref", ""),
            row.get("field_path", ""),
            row.get("ref", ""),
            row.get("error_code", ""),
        )
        unique.setdefault(key, dict(row))
    return [unique[key] for key in sorted(unique)]


def evaluate_source_module_boundary(
    payloads: Iterable[object] = (),
    *,
    direct_refs: Iterable[str] = (),
) -> dict[str, Any]:
    ref_rows: list[dict[str, str]] = []
    blocked_claim_rows: list[dict[str, Any]] = []
    for payload in payloads:
        if isinstance(payload, tuple) and len(payload) == 2:
            manifest_ref, manifest_payload = payload
            ref_rows.extend(
                extract_source_ref_rows(
                    manifest_payload,
                    manifest_ref=str(manifest_ref),
                )
            )
            blocked_claim_rows.extend(
                extract_source_module_claim_rows(
                    manifest_payload,
                    manifest_ref=str(manifest_ref),
                )
            )
        else:
            ref_rows.extend(extract_source_ref_rows(payload))
            blocked_claim_rows.extend(extract_source_module_claim_rows(payload))
    ref_rows.extend(
        {
            "manifest_ref": "<direct>",
            "field_path": f"source_ref[{index}]",
            "row_id": "direct_source_ref",
            "ref": _normalize_ref(ref),
        }
        for index, ref in enumerate(direct_refs)
        if _normalize_ref(ref)
    )
    ref_rows = _dedupe_rows(ref_rows)

    blocked_refs: list[dict[str, Any]] = []
    safe_refs: list[dict[str, str]] = []
    for row in ref_rows:
        finding = _classify_source_ref(row["ref"])
        if finding:
            blocked_refs.append(
                {
                    **row,
                    **finding,
                    "body_in_receipt": False,
                    "coordination_action": "exclude_ref_or_replace_with_public_non_secret_source_module",
                }
            )
        else:
            safe_refs.append(row)

    blocked_refs.extend(_dedupe_rows(blocked_claim_rows))

    status = PASS if not blocked_refs else BLOCKED
    next_action = (
        "refresh_or_import_may_continue_to_digest_and_claim_gates"
        if status == PASS
        else "exclude_blocked_source_refs_before_exact_copy_refresh_write"
    )
    manifest_refs = sorted(
        {
            row["manifest_ref"]
            for row in ref_rows
            if row.get("manifest_ref") and row["manifest_ref"] != "<direct>"
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "checker_id": CHECKER_ID,
        "status": status,
        "input_manifest_count": len(manifest_refs),
        "input_manifest_refs": manifest_refs,
        "source_ref_count": len(ref_rows),
        "safe_ref_count": len(safe_refs),
        "blocked_ref_count": len(blocked_refs),
        "blocked_source_module_claim_count": len(blocked_claim_rows),
        "blocked_refs": blocked_refs,
        "safe_refs": safe_refs,
        "body_in_receipt": False,
        "boundary_policy": (
            "source-open by default for relative non-secret macro source refs; "
            "exclude secrets, credentials, raw operator voice, provider payloads, "
            "account/session state, browser/HUD live-access material, recipient-send "
            "state, host-private absolute roots, parent traversal, receipt-body "
            "claims, and copied/refactored body claims without public target refs"
        ),
        "next_action": next_action,
        "reentry_condition": (
            "All exact-copy source-module refs are relative public macro refs and "
            "none match credential, provider-payload, raw-seed, browser/HUD, "
            "account/session, private-root, or traversal boundaries."
        ),
        "anti_claim": ANTI_CLAIM,
    }


def _load_manifest_rows(paths: Iterable[str]) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for path in paths:
        payload = read_json_strict(Path(path))
        rows.append((path, payload))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render a read-only source-module boundary card before exact-copy refresh."
        )
    )
    parser.add_argument(
        "--manifest",
        action="append",
        default=[],
        help="Source module manifest JSON to inspect. Repeatable.",
    )
    parser.add_argument(
        "--source-ref",
        action="append",
        default=[],
        help="Direct source ref to inspect. Repeatable.",
    )
    parser.add_argument("--check", action="store_true", help="Exit nonzero if blocked.")
    args = parser.parse_args(argv)

    card = evaluate_source_module_boundary(
        _load_manifest_rows(args.manifest),
        direct_refs=args.source_ref,
    )
    print(json.dumps(card, indent=2, sort_keys=True))
    return 0 if card["status"] == PASS or not args.check else 1


if __name__ == "__main__":
    raise SystemExit(main())
