"""
Implements validators source module boundary for the public Plectis package.

Callers enter through `extract_source_module_claim_rows`, `extract_source_ref_rows`,
`source_module_refresh_policy_fingerprint`, `load_source_module_refresh_policy`,
`compile_source_module_refresh_policy`, `evaluate_source_module_refresh_authority`, and 2
more; constants such as `CHECKER_ID`, `SCHEMA_VERSION`, `REFRESH_AUTHORITY_CHECKER_ID`,
`REFRESH_AUTHORITY_SCHEMA_VERSION`, and 24 more pin local fixture names; dependencies
include `argparse`, `hashlib`, `json`, `collections`, and 3 more. Validator outputs stay
structured so release checks can consume findings without scraping prose.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.source_module_boundary"
SCHEMA_VERSION = "source_module_boundary_card_v1"
REFRESH_AUTHORITY_CHECKER_ID = (
    "checker.microcosm.validators.source_module_refresh_authority"
)
REFRESH_AUTHORITY_SCHEMA_VERSION = "source_module_refresh_authority_card_v1"
REFRESH_POLICY_VALIDATION_SCHEMA_VERSION = "source_module_refresh_policy_validation_v1"
SOURCE_MODULE_REFRESH_POLICY_SCHEMA_VERSION = "source_module_refresh_policy_v0"
SOURCE_MODULE_REFRESH_POLICY_REF = "core/source_module_refresh_policy_v0.json"
EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION = "exact_copy_source_module_refresh"
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

RESTRICTED_PRIVATE_SOURCE_PREFIXES = (
    ".claude/",
    ".codex/",
    "apps/",
    "codex/ledger/",
    "obsidian/",
    "state/",
    "system/control/",
    "system/lib/",
    "system/server/",
    "tools/agent_trace_structurer/",
    "tools/meta/",
)

RESTRICTED_PRIVATE_SOURCE_FILENAMES = {
    "kernel.py",
    "pipeline_codex_handoff.py",
    "pipeline_overnight.py",
    "pipeline_signal_watcher.py",
}

REFRESH_POLICY_TOP_LEVEL_KEYS = frozenset(
    {
        "_policy_ref",
        "authority_boundary",
        "authority_source",
        "field_contract",
        "grant_contract",
        "grants",
        "operation",
        "policy_id",
        "policy_ref",
        "policy_revision",
        "provenance_refs",
        "schema_version",
    }
)

REFRESH_GRANT_KEYS = frozenset(
    {
        "anti_claim",
        "authority_boundary",
        "authority_revision",
        "classification_override_scope",
        "field_contract",
        "grant_id",
        "material_ids",
        "operation",
        "provenance_refs",
        "source_ref",
        "source_to_target_relation",
        "source_to_target_relations",
        "status",
        "target_ref",
        "target_ref_prefixes",
        "target_refs",
    }
)

REFRESH_GRANT_STATUSES = frozenset({"active", "inactive", "revoked"})
REFRESH_GRANT_ACTIVE_STATUS = "active"
REFRESH_GRANT_CLASSIFICATION_OVERRIDE_SCOPES = frozenset(
    {"restricted_private_control_plane_only"}
)
REFRESH_POLICY_GRANT_CONTRACT = {
    "hard_denies_dominate_grants": True,
    "classification_retained": True,
    "operation_required": True,
    "target_scope_required": True,
    "source_to_target_relation_required": True,
    "release_publicity_not_sufficient": True,
}

ANTI_CLAIM = (
    "This read-only card checks source-module refs before exact-copy refresh. "
    "It does not certify secret absence, authorize source mutation, authorize "
    "release, or inspect live provider, account, browser/HUD, git index, or "
    "operator-state payloads."
)


def _normalize_ref(ref: object) -> str:
    """
    Return normalize ref for the validators source module boundary flow.

    Inputs are `ref`; notable helpers are `strip` and `startswith`.
    """
    value = str(ref or "").strip()
    while value.startswith("./"):
        value = value[2:]
    return value


def _path_portion(ref: str) -> str:
    """
    Derive path portion without touching module import state.

    Inputs are `ref`; notable helpers are `strip`, `split`, and `endswith`.
    """
    path = ref.split("#", 1)[0]
    if "::" in path:
        first, _rest = path.split("::", 1)
        if "/" in first or first.endswith((".json", ".jsonl", ".py", ".md", ".lean")):
            path = first
    return path.strip()


def _path_parts(ref: str) -> list[str]:
    """
    Compute path parts from `ref`.

    Inputs are `ref`; notable helpers are `replace`, `_path_portion`, and `split`.
    """
    path = _path_portion(ref).replace("\\", "/")
    return [part for part in path.split("/") if part]


def _row_id(row: dict[str, Any], fallback: str) -> str:
    """
    Return row ID for the validators source module boundary flow.

    Inputs are `row` and `fallback`; notable helpers are `strip` and `get`.
    """
    for key in ROW_ID_KEYS:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return fallback


def _is_ref_field(key: str) -> bool:
    """
    Return whether is ref field holds for the validators source module boundary flow.

    The result is derived from `key` with `endswith`; failing evidence is returned or raised
    exactly where the body says so.
    """
    if key in NON_REF_KEYS:
        return False
    return key in REF_FIELD_KEYS or key.endswith(REF_FIELD_SUFFIXES)


def _string_ref_values(value: object, *, field_path: str) -> Iterator[tuple[str, str]]:
    """
    Temporarily apply string ref values for callers using a `with` block.

    The previous state is restored after the yielded block exits, including exceptional
    exits.
    """
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
    """
    Return whether has nonempty value holds for the validators source module boundary flow.

    The result is derived from `row` and `keys` with `get` and `_normalize_ref`; failing
    evidence is returned or raised exactly where the body says so.
    """
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and _normalize_ref(value):
            return True
        if isinstance(value, list) and any(_normalize_ref(item) for item in value):
            return True
    return False


def _first_source_ref(row: dict[str, Any]) -> str:
    """
    Return first source ref for the validators source module boundary flow.

    Inputs are `row`; notable helpers are `get` and `_normalize_ref`.
    """
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
    """
    Derive source modules tail without touching module import state.

    Inputs are `ref`; notable helpers are `_path_parts`, `join`, `_normalize_ref`, and
    `index`.
    """
    parts = _path_parts(_normalize_ref(ref))
    try:
        source_modules_index = parts.index("source_modules")
    except ValueError:
        return ""
    tail = parts[source_modules_index + 1 :]
    return "/".join(tail)


def _restricted_private_source_match(ref: str) -> str:
    """
    Return restricted private source match for the validators source module boundary flow.

    Inputs are `ref`; notable helpers are `lstrip`, `_source_modules_tail`, `append`,
    `startswith`, and 4 more.
    """
    candidates: list[str] = []
    path = _path_portion(ref).replace("\\", "/").lstrip("/")
    if path:
        candidates.append(path)
    source_modules_tail = _source_modules_tail(ref)
    if source_modules_tail:
        candidates.append(source_modules_tail)
    expanded: list[str] = []
    for candidate in candidates:
        expanded.append(candidate)
        if candidate.startswith("ai_workflow/"):
            expanded.append(candidate.removeprefix("ai_workflow/"))
    for candidate in expanded:
        if candidate in RESTRICTED_PRIVATE_SOURCE_FILENAMES:
            return candidate
        match = next(
            (
                prefix
                for prefix in RESTRICTED_PRIVATE_SOURCE_PREFIXES
                if candidate.startswith(prefix)
            ),
            "",
        )
        if match:
            return match
    return ""


def _looks_like_source_module_claim(row: dict[str, Any]) -> bool:
    """
    Return whether looks like source module claim holds for the validators source module
    boundary flow.

    The result is derived from `row` with `_has_nonempty_value`; failing evidence is
    returned or raised exactly where the body says so.
    """
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
    """
    Return extract source module claim rows for the validators source module boundary flow.

    Inputs are `payload`, `manifest_ref`, `prefix`, and `inherited_row_id`; notable helpers
    are `_row_id`, `_looks_like_source_module_claim`, `items`, `strip`, and 7 more.
    """

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
    """
    Produce the extract source ref rows value used by
    `microcosm_core.validators.source_module_boundary`.

    Inputs are `payload`, `manifest_ref`, `prefix`, and `inherited_row_id`; notable helpers
    are `_row_id`, `items`, `_is_ref_field`, `_string_ref_values`, and 3 more.
    """

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
    """
    Serialize `microcosm_core.validators.source_module_boundary._classify_source_ref` into
    the payload shape expected by validators source module boundary.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
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
    restricted_private_source = _restricted_private_source_match(value)
    if restricted_private_source:
        return {
            "error_code": (
                "source_ref_restricted_private_control_plane:"
                f"{restricted_private_source}"
            ),
            "reason": (
                "source-module imports cannot expose private control-plane, "
                "runtime, hook, app, ledger, state, or meta-tooling bodies; "
                "use a public-safe copy, synthetic stub, fixture, card, or omission"
            ),
        }
    return None


def _source_ref_match_variants(ref: object) -> set[str]:
    """
    Produce the source ref match variants value used by
    `microcosm_core.validators.source_module_boundary`.

    Inputs are `ref`; notable helpers are `_normalize_ref`, `lstrip`,
    `_source_modules_tail`, `add`, and 4 more.
    """
    value = _normalize_ref(ref)
    variants = {value} if value else set()
    path = _path_portion(value).replace("\\", "/").lstrip("/")
    if path:
        variants.add(path)
    tail = _source_modules_tail(value)
    if tail:
        variants.add(tail)
    for item in list(variants):
        if item.startswith("ai_workflow/"):
            variants.add(item.removeprefix("ai_workflow/"))
        if item.startswith("microcosm-substrate/"):
            variants.add(item.removeprefix("microcosm-substrate/"))
    return {item for item in variants if item}


def _target_ref_match_variants(ref: object) -> set[str]:
    """
    Compute target ref match variants from `ref`.

    Inputs are `ref`; notable helpers are `_normalize_ref`, `startswith`, `add`, and
    `removeprefix`.
    """
    value = _normalize_ref(ref)
    variants = {value} if value else set()
    for item in list(variants):
        if item.startswith("microcosm-substrate/"):
            variants.add(item.removeprefix("microcosm-substrate/"))
    return {item for item in variants if item}


def _canonical_refresh_ref(ref: object) -> str:
    """
    Return canonical refresh ref for the validators source module boundary flow.

    Inputs are `ref`; notable helpers are `replace`, `startswith`, `removeprefix`, and
    `_normalize_ref`.
    """
    value = _normalize_ref(ref).replace("\\", "/")
    if value.startswith("microcosm-substrate/"):
        value = value.removeprefix("microcosm-substrate/")
    return value


def _ref_is_canonical_segment_path(ref: str) -> bool:
    """
    Return whether ref is canonical segment path holds for the validators source module
    boundary flow.

    The result is derived from `ref` with `startswith` and `_normalize_ref`; failing
    evidence is returned or raised exactly where the body says so.
    """
    if not ref:
        return False
    if ref.startswith(("/", "../")) or "/../" in f"/{ref}/":
        return False
    if "\\" in ref or "//" in ref or ref.startswith("./"):
        return False
    return ref == _normalize_ref(ref)


def _target_ref_matches_prefix(target: str, prefix: str) -> bool:
    """
    Return whether target ref matches prefix holds for the validators source module boundary
    flow.

    The result is derived from `target` and `prefix` with `rstrip`,
    `_canonical_refresh_ref`, and `startswith`; failing evidence is returned or raised
    exactly where the body says so.
    """
    target_value = _canonical_refresh_ref(target).rstrip("/")
    prefix_value = _canonical_refresh_ref(prefix).rstrip("/")
    return bool(
        target_value
        and prefix_value
        and (target_value == prefix_value or target_value.startswith(f"{prefix_value}/"))
    )


def _as_string_list(value: object) -> list[str]:
    """
    Compute as string list from `value`.

    Inputs are `value`.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item or "")]
    return [str(value)] if str(value or "") else []


def _default_refresh_policy(policy_ref: str = "<missing>") -> dict[str, Any]:
    """
    Serialize `microcosm_core.validators.source_module_boundary._default_refresh_policy`
    into the payload shape expected by validators source module boundary.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "schema_version": SOURCE_MODULE_REFRESH_POLICY_SCHEMA_VERSION,
        "policy_id": "missing_source_module_refresh_policy",
        "policy_revision": "missing_policy_empty_grant_default_v0",
        "policy_ref": policy_ref,
        "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
        "authority_boundary": (
            "empty fallback: no restricted source-module refresh grants; "
            "public relative non-secret sources may still refresh"
        ),
        "grants": [],
    }


def _policy_for_fingerprint(policy: dict[str, Any]) -> dict[str, Any]:
    """
    Produce the policy for fingerprint value used by
    `microcosm_core.validators.source_module_boundary`.

    Inputs are `policy`; notable helpers are `items` and `startswith`.
    """
    return {key: value for key, value in policy.items() if not key.startswith("_")}


def source_module_refresh_policy_fingerprint(policy: dict[str, Any]) -> str:
    """
    Compute source module refresh policy fingerprint from `policy`.

    Inputs are `policy`; notable helpers are `encode`, `dumps`, `hexdigest`,
    `_policy_for_fingerprint`, and 1 more.
    """
    payload = json.dumps(
        _policy_for_fingerprint(policy),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def load_source_module_refresh_policy(
    *,
    public_root: str | Path | None = None,
    policy_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Load load source module refresh policy for
    `microcosm_core.validators.source_module_boundary`.

    Input comes from `public_root` and `policy_path`; malformed or missing data follows the
    exceptions and checks visible in the body.
    """
    resolved_policy_path: Path | None = Path(policy_path) if policy_path else None
    if resolved_policy_path is None and public_root is not None:
        resolved_policy_path = Path(public_root) / SOURCE_MODULE_REFRESH_POLICY_REF
    if resolved_policy_path is None or not resolved_policy_path.is_file():
        return _default_refresh_policy(
            str(resolved_policy_path or SOURCE_MODULE_REFRESH_POLICY_REF)
        )
    payload = read_json_strict(resolved_policy_path)
    if not isinstance(payload, dict):
        return _default_refresh_policy(str(resolved_policy_path))
    policy = dict(payload)
    policy["_policy_ref"] = str(resolved_policy_path)
    return policy


def _source_finding_disposition(finding: dict[str, str] | None) -> str:
    """
    Build a structured finding row for source finding disposition.

    The row carries machine-readable codes and subject identifiers so validators can report
    failures without parsing text.
    """
    if not finding:
        return "public_open"
    if str(finding.get("error_code") or "").startswith(
        "source_ref_restricted_private_control_plane:"
    ):
        return "grantable_restricted_private_control_plane"
    return "hard_denied"


def _is_hard_denied_source_finding(finding: dict[str, str] | None) -> bool:
    """
    Build a structured finding row for is hard denied source finding.

    The row carries machine-readable codes and subject identifiers so validators can report
    failures without parsing text.
    """
    return _source_finding_disposition(finding) == "hard_denied"


def _policy_finding(
    code: str,
    *,
    path: str,
    message: str,
    severity: str = BLOCKED,
) -> dict[str, str]:
    """
    Serialize `microcosm_core.validators.source_module_boundary._policy_finding` into the
    payload shape expected by validators source module boundary.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "finding_code": code,
        "path": path,
        "message": message,
        "severity": severity,
    }


def _grant_target_exact_values(grant: dict[str, Any]) -> set[str]:
    """
    Return grant target exact values for the validators source module boundary flow.

    Inputs are `grant`; notable helpers are `_as_string_list`, `update`,
    `_canonical_refresh_ref`, `get`, and 1 more.
    """
    targets: set[str] = set()
    for ref in _as_string_list(grant.get("target_refs") or grant.get("target_ref")):
        targets.update(_target_ref_match_variants(ref))
    return {_canonical_refresh_ref(item) for item in targets if item}


def _grant_target_prefix_values(grant: dict[str, Any]) -> set[str]:
    """
    Return grant target prefix values for the validators source module boundary flow.

    Inputs are `grant`; notable helpers are `_as_string_list`, `get`, `update`, `rstrip`,
    and 2 more.
    """
    prefixes: set[str] = set()
    for ref in _as_string_list(grant.get("target_ref_prefixes")):
        prefixes.update(_target_ref_match_variants(ref))
    return {_canonical_refresh_ref(item).rstrip("/") for item in prefixes if item}


def _grant_matches_target_scope(row_targets: set[str], grant: dict[str, Any]) -> bool:
    """
    Return whether grant matches target scope holds for the validators source module
    boundary flow.

    The result is derived from `row_targets` and `grant` with `_grant_target_exact_values`,
    `_grant_target_prefix_values`, `_canonical_refresh_ref`, `intersection`, and 1 more;
    failing evidence is returned or raised exactly where the body says so.
    """
    canonical_row_targets = {
        _canonical_refresh_ref(target) for target in row_targets if target
    }
    exact_targets = _grant_target_exact_values(grant)
    if exact_targets and canonical_row_targets.intersection(exact_targets):
        return True
    prefixes = _grant_target_prefix_values(grant)
    return any(
        _target_ref_matches_prefix(target, prefix)
        for target in canonical_row_targets
        for prefix in prefixes
    )


def _grant_overlap_signature(grant: dict[str, Any]) -> tuple[Any, ...]:
    """
    Compute grant overlap signature from `grant`.

    Inputs are `grant`; notable helpers are `_source_ref_match_variants`, `_as_string_list`,
    `_grant_target_exact_values`, `_grant_target_prefix_values`, and 1 more.
    """
    source_variants = tuple(sorted(_source_ref_match_variants(grant.get("source_ref"))))
    relations = tuple(
        sorted(
            _as_string_list(
                grant.get("source_to_target_relations")
                or grant.get("source_to_target_relation")
            )
        )
    )
    material_ids = tuple(sorted(_as_string_list(grant.get("material_ids"))))
    exact_targets = tuple(sorted(_grant_target_exact_values(grant)))
    prefixes = tuple(sorted(_grant_target_prefix_values(grant)))
    return (source_variants, relations, material_ids, exact_targets, prefixes)


def compile_source_module_refresh_policy(
    policy: dict[str, Any],
    *,
    operation: str = EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
) -> dict[str, Any]:
    """
    Serialize
    `microcosm_core.validators.source_module_boundary.compile_source_module_refresh_policy`
    into the payload shape expected by validators source module boundary.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    findings: list[dict[str, str]] = []
    if not isinstance(policy, dict):
        return {
            "schema_version": REFRESH_POLICY_VALIDATION_SCHEMA_VERSION,
            "status": BLOCKED,
            "finding_count": 1,
            "findings": [
                _policy_finding(
                    "refresh_policy_not_object",
                    path="$",
                    message="source-module refresh policy must be a JSON object",
                )
            ],
            "active_grants": [],
            "active_grant_count": 0,
        }

    unknown_top = sorted(set(policy) - REFRESH_POLICY_TOP_LEVEL_KEYS)
    for key in unknown_top:
        findings.append(
            _policy_finding(
                "refresh_policy_unknown_top_level_field",
                path=f"$.{key}",
                message="top-level policy fields must be enforced or explicitly informational",
            )
        )

    required_top = ("schema_version", "policy_id", "policy_revision", "operation", "grants")
    for key in required_top:
        if key not in policy or policy.get(key) in ("", None):
            findings.append(
                _policy_finding(
                    "refresh_policy_missing_required_field",
                    path=f"$.{key}",
                    message=f"missing required policy field: {key}",
                )
            )

    if policy.get("schema_version") != SOURCE_MODULE_REFRESH_POLICY_SCHEMA_VERSION:
        findings.append(
            _policy_finding(
                "refresh_policy_unknown_schema_version",
                path="$.schema_version",
                message="unknown source-module refresh policy schema version",
            )
        )
    if str(policy.get("operation") or "") != operation:
        findings.append(
            _policy_finding(
                "refresh_policy_wrong_operation",
                path="$.operation",
                message=(
                    "document operation must match the evaluator operation; "
                    "release/publication policies are not refresh authority"
                ),
            )
        )

    grant_contract = policy.get("grant_contract")
    if grant_contract is not None:
        if not isinstance(grant_contract, dict):
            findings.append(
                _policy_finding(
                    "refresh_policy_grant_contract_not_object",
                    path="$.grant_contract",
                    message="grant_contract must be an object",
                )
            )
        else:
            unknown_contract_keys = sorted(
                set(grant_contract) - set(REFRESH_POLICY_GRANT_CONTRACT)
            )
            for key in unknown_contract_keys:
                findings.append(
                    _policy_finding(
                        "refresh_policy_unknown_grant_contract_field",
                        path=f"$.grant_contract.{key}",
                        message="grant_contract fields must be compiler-known",
                    )
                )
            for key, expected in REFRESH_POLICY_GRANT_CONTRACT.items():
                if grant_contract.get(key) is not expected:
                    findings.append(
                        _policy_finding(
                            "refresh_policy_grant_contract_not_enforced",
                            path=f"$.grant_contract.{key}",
                            message=(
                                "grant_contract must declare the enforced compiler "
                                f"value {expected!r}"
                            ),
                        )
                    )

    grants = policy.get("grants")
    if not isinstance(grants, list):
        findings.append(
            _policy_finding(
                "refresh_policy_grants_not_list",
                path="$.grants",
                message="grants must be a list",
            )
        )
        grants = []

    active_grants: list[dict[str, Any]] = []
    grant_ids_seen: set[str] = set()
    active_signatures: dict[tuple[Any, ...], str] = {}
    for index, grant in enumerate(grants):
        path = f"$.grants[{index}]"
        if not isinstance(grant, dict):
            findings.append(
                _policy_finding(
                    "refresh_policy_grant_not_object",
                    path=path,
                    message="grant entries must be objects",
                )
            )
            continue
        unknown_grant_keys = sorted(set(grant) - REFRESH_GRANT_KEYS)
        for key in unknown_grant_keys:
            findings.append(
                _policy_finding(
                    "refresh_policy_unknown_grant_field",
                    path=f"{path}.{key}",
                    message="grant fields must be compiler-known",
                )
            )

        grant_id = str(grant.get("grant_id") or "")
        if not grant_id:
            findings.append(
                _policy_finding(
                    "refresh_policy_grant_missing_id",
                    path=f"{path}.grant_id",
                    message="grant_id is required",
                )
            )
        elif grant_id in grant_ids_seen:
            findings.append(
                _policy_finding(
                    "refresh_policy_duplicate_grant_id",
                    path=f"{path}.grant_id",
                    message=f"duplicate grant_id: {grant_id}",
                )
            )
        grant_ids_seen.add(grant_id)

        if "status" not in grant:
            findings.append(
                _policy_finding(
                    "refresh_policy_grant_missing_status",
                    path=f"{path}.status",
                    message="grant status is required; absent status is not active",
                )
            )
            status = ""
        else:
            status = str(grant.get("status") or "")
            if status not in REFRESH_GRANT_STATUSES:
                findings.append(
                    _policy_finding(
                        "refresh_policy_grant_unknown_status",
                        path=f"{path}.status",
                        message="grant status must be active, inactive, or revoked",
                    )
                )

        if str(grant.get("operation") or "") != operation:
            findings.append(
                _policy_finding(
                    "refresh_policy_grant_wrong_operation",
                    path=f"{path}.operation",
                    message="grant operation must match document and evaluator operation",
                )
            )

        source_ref = _canonical_refresh_ref(grant.get("source_ref"))
        if not _ref_is_canonical_segment_path(source_ref):
            findings.append(
                _policy_finding(
                    "refresh_policy_grant_noncanonical_source_ref",
                    path=f"{path}.source_ref",
                    message="source_ref must be a canonical relative segment path",
                )
            )

        relations = _as_string_list(
            grant.get("source_to_target_relations")
            or grant.get("source_to_target_relation")
        )
        if not relations:
            findings.append(
                _policy_finding(
                    "refresh_policy_grant_missing_relation",
                    path=f"{path}.source_to_target_relation",
                    message="operation grants must declare a source_to_target_relation",
                )
            )
        material_ids = _as_string_list(grant.get("material_ids"))
        if not material_ids:
            findings.append(
                _policy_finding(
                    "refresh_policy_grant_missing_material_ids",
                    path=f"{path}.material_ids",
                    message="operation grants must declare target material ids",
                )
            )

        target_refs = _as_string_list(grant.get("target_refs") or grant.get("target_ref"))
        target_prefixes = _as_string_list(grant.get("target_ref_prefixes"))
        if not target_refs and not target_prefixes:
            findings.append(
                _policy_finding(
                    "refresh_policy_grant_missing_target_scope",
                    path=f"{path}.target_refs",
                    message="operation grants must declare exact target refs or prefixes",
                )
            )
        for ref_index, ref in enumerate(target_refs):
            canonical = _canonical_refresh_ref(ref)
            if not _ref_is_canonical_segment_path(canonical):
                findings.append(
                    _policy_finding(
                        "refresh_policy_grant_noncanonical_target_ref",
                        path=f"{path}.target_refs[{ref_index}]",
                        message="target refs must be canonical relative segment paths",
                    )
                )
        for ref_index, ref in enumerate(target_prefixes):
            canonical = _canonical_refresh_ref(ref).rstrip("/")
            if not _ref_is_canonical_segment_path(canonical):
                findings.append(
                    _policy_finding(
                        "refresh_policy_grant_noncanonical_target_prefix",
                        path=f"{path}.target_ref_prefixes[{ref_index}]",
                        message="target prefixes must be canonical relative segment paths",
                    )
                )

        override_scope = str(grant.get("classification_override_scope") or "")
        if (
            override_scope
            and override_scope not in REFRESH_GRANT_CLASSIFICATION_OVERRIDE_SCOPES
        ):
            findings.append(
                _policy_finding(
                    "refresh_policy_grant_invalid_override_scope",
                    path=f"{path}.classification_override_scope",
                    message="classification override scope is not compiler-known",
                )
            )

        if status == REFRESH_GRANT_ACTIVE_STATUS:
            signature = _grant_overlap_signature(grant)
            previous_grant_id = active_signatures.get(signature)
            if previous_grant_id:
                findings.append(
                    _policy_finding(
                        "refresh_policy_overlapping_active_grants",
                        path=path,
                        message=(
                            "active grants overlap exactly; ambiguous ordering is "
                            f"not authority ({previous_grant_id}, {grant_id})"
                        ),
                    )
                )
            active_signatures[signature] = grant_id
            active_grants.append(grant)

    return {
        "schema_version": REFRESH_POLICY_VALIDATION_SCHEMA_VERSION,
        "status": PASS if not findings else BLOCKED,
        "finding_count": len(findings),
        "findings": findings,
        "active_grant_count": len(active_grants),
        "active_grant_ids": [
            str(grant.get("grant_id") or "") for grant in active_grants
        ],
        "active_grants": active_grants,
    }


def _matches_refresh_grant(
    row: dict[str, Any],
    grant: dict[str, Any],
    *,
    operation: str,
) -> bool:
    """
    Return whether matches refresh grant holds for the validators source module boundary
    flow.

    The result is derived from `row`, `grant`, and `operation` with
    `_source_ref_match_variants`, `_as_string_list`, `_target_ref_match_variants`,
    `_grant_matches_target_scope`, and 2 more; failing evidence is returned or raised
    exactly where the body says so.
    """
    if str(grant.get("status") or "") != REFRESH_GRANT_ACTIVE_STATUS:
        return False
    if str(grant.get("operation") or "") != operation:
        return False

    row_source_variants = _source_ref_match_variants(row.get("source_ref"))
    grant_source_variants = _source_ref_match_variants(grant.get("source_ref"))
    if not row_source_variants or row_source_variants.isdisjoint(grant_source_variants):
        return False

    row_relation = str(row.get("source_to_target_relation") or "")
    grant_relations = _as_string_list(
        grant.get("source_to_target_relations")
        or grant.get("source_to_target_relation")
    )
    if grant_relations and row_relation not in grant_relations:
        return False

    row_material_id = str(row.get("material_id") or row.get("row_id") or "")
    grant_material_ids = set(_as_string_list(grant.get("material_ids")))
    if grant_material_ids and row_material_id not in grant_material_ids:
        return False

    row_targets = _target_ref_match_variants(row.get("target_ref"))
    return _grant_matches_target_scope(row_targets, grant)


def _matching_refresh_grants(
    row: dict[str, Any],
    grants: Iterable[dict[str, Any]],
    *,
    operation: str,
) -> list[dict[str, Any]]:
    """
    Return matching refresh grants for the validators source module boundary flow.

    Inputs are `row`, `grants`, and `operation`; notable helpers are
    `_matches_refresh_grant`.
    """
    return [
        grant
        for grant in grants
        if isinstance(grant, dict)
        and _matches_refresh_grant(row, grant, operation=operation)
    ]


def evaluate_source_module_refresh_authority(
    rows: Iterable[dict[str, Any]],
    *,
    public_root: str | Path | None = None,
    policy: dict[str, Any] | None = None,
    policy_path: str | Path | None = None,
    operation: str = EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
) -> dict[str, Any]:
    """
    Serialize
    `microcosm_core.validators.source_module_boundary.evaluate_source_module_refresh_authority`
    into the payload shape expected by validators source module boundary.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    refresh_policy = (
        load_source_module_refresh_policy(public_root=public_root, policy_path=policy_path)
        if policy is None
        else dict(policy)
    )
    fingerprint = source_module_refresh_policy_fingerprint(refresh_policy)
    policy_ref = str(
        refresh_policy.get("_policy_ref")
        or refresh_policy.get("policy_ref")
        or policy_path
        or SOURCE_MODULE_REFRESH_POLICY_REF
    )
    policy_validation = compile_source_module_refresh_policy(
        refresh_policy,
        operation=operation,
    )
    active_grants = list(policy_validation.get("active_grants") or [])

    decisions: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        source_ref = _normalize_ref(row.get("source_ref"))
        target_ref = _normalize_ref(row.get("target_ref"))
        relation = str(row.get("source_to_target_relation") or "")
        material_id = str(row.get("material_id") or row.get("row_id") or f"row_{index}")
        finding = _classify_source_ref(source_ref)
        base_decision: dict[str, Any] = {
            "material_id": material_id,
            "source_ref": source_ref,
            "target_ref": target_ref,
            "source_to_target_relation": relation,
            "source_sha256": row.get("source_sha256"),
            "target_sha256": row.get("target_sha256"),
            "operation": operation,
            "policy_ref": policy_ref,
            "policy_fingerprint": fingerprint,
            "body_in_receipt": False,
        }
        if policy_validation.get("status") != PASS:
            decisions.append(
                {
                    **base_decision,
                    "classification_status": "not_evaluated_policy_invalid",
                    "authorization_status": "blocked_invalid_refresh_policy",
                    "authorized": False,
                    "grant_id": None,
                    "policy_validation_status": policy_validation.get("status"),
                    "policy_validation_finding_count": policy_validation.get(
                        "finding_count"
                    ),
                    "coordination_action": (
                        "repair_source_module_refresh_policy_before_refresh"
                    ),
                }
            )
            continue

        if finding is None:
            decisions.append(
                {
                    **base_decision,
                    "classification_status": "public_open",
                    "authorization_status": "allow_open_source",
                    "authorized": True,
                    "grant_id": None,
                }
            )
            continue

        classification_error_code = str(finding.get("error_code") or "")
        source_disposition = _source_finding_disposition(finding)
        if source_disposition == "hard_denied":
            decisions.append(
                {
                    **base_decision,
                    "classification_status": "hard_denied",
                    "source_disposition": source_disposition,
                    "classification_error_code": classification_error_code,
                    "classification_reason": finding.get("reason"),
                    "authorization_status": "blocked_hard_denial",
                    "authorized": False,
                    "grant_id": None,
                    "coordination_action": (
                        "exclude_hard_denied_source_before_exact_copy_refresh"
                    ),
                }
            )
            continue

        matching_grants = _matching_refresh_grants(
            {
                **row,
                "source_ref": source_ref,
                "target_ref": target_ref,
                "source_to_target_relation": relation,
                "material_id": material_id,
            },
            active_grants,
            operation=operation,
        )
        if not matching_grants:
            decisions.append(
                {
                    **base_decision,
                    "classification_status": "restricted_private_control_plane",
                    "source_disposition": source_disposition,
                    "classification_error_code": classification_error_code,
                    "classification_reason": finding.get("reason"),
                    "authorization_status": "blocked_missing_refresh_grant",
                    "authorized": False,
                    "grant_id": None,
                    "coordination_action": (
                        "add_operation_scoped_refresh_grant_or_demote_body_import"
                    ),
                }
            )
            continue
        if len(matching_grants) != 1:
            decisions.append(
                {
                    **base_decision,
                    "classification_status": "restricted_private_control_plane",
                    "source_disposition": source_disposition,
                    "classification_error_code": classification_error_code,
                    "classification_reason": finding.get("reason"),
                    "authorization_status": "blocked_ambiguous_refresh_grant",
                    "authorized": False,
                    "grant_id": None,
                    "matching_grant_ids": [
                        str(grant.get("grant_id") or "") for grant in matching_grants
                    ],
                    "coordination_action": (
                        "make_refresh_grants_exactly_one_match_for_this_request"
                    ),
                }
            )
            continue

        grant = matching_grants[0]

        decisions.append(
            {
                **base_decision,
                "classification_status": "restricted_private_control_plane",
                "source_disposition": source_disposition,
                "classification_error_code": classification_error_code,
                "classification_reason": finding.get("reason"),
                "authorization_status": "allow_with_authority",
                "authorized": True,
                "grant_id": str(grant.get("grant_id") or ""),
                "grant_status": str(grant.get("status") or ""),
                "authority_revision": str(
                    grant.get("authority_revision")
                    or refresh_policy.get("policy_revision")
                    or ""
                ),
                "classification_retained": True,
            }
        )

    blocked_decisions = [row for row in decisions if row.get("authorized") is not True]
    allowed_with_authority = [
        row for row in decisions if row.get("authorization_status") == "allow_with_authority"
    ]
    return {
        "schema_version": REFRESH_AUTHORITY_SCHEMA_VERSION,
        "checker_id": REFRESH_AUTHORITY_CHECKER_ID,
        "status": PASS if not blocked_decisions else BLOCKED,
        "operation": operation,
        "policy_schema_version": refresh_policy.get("schema_version"),
        "policy_ref": policy_ref,
        "policy_id": refresh_policy.get("policy_id"),
        "policy_revision": refresh_policy.get("policy_revision"),
        "policy_fingerprint": fingerprint,
        "policy_validation": {
            key: value
            for key, value in policy_validation.items()
            if key != "active_grants"
        },
        "decision_count": len(decisions),
        "allowed_decision_count": len(decisions) - len(blocked_decisions),
        "allow_with_authority_count": len(allowed_with_authority),
        "blocked_decision_count": len(blocked_decisions),
        "blocked_decisions": blocked_decisions,
        "decisions": decisions,
        "hard_denies_dominate_grants": True,
        "body_in_receipt": False,
        "authority_boundary": (
            "operation-scoped exact-copy refresh authorization only; not release, "
            "publication, source mutation, provider, account/session, or "
            "private-root equivalence authority"
        ),
    }


def _dedupe_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """
    Return dedupe rows for the validators source module boundary flow.

    Inputs are `rows`; notable helpers are `setdefault` and `get`.
    """
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
    """
    Serialize
    `microcosm_core.validators.source_module_boundary.evaluate_source_module_boundary` into
    the payload shape expected by validators source module boundary.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
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
            "claims, copied/refactored body claims without public target refs, and "
            "restricted private control-plane/runtime/meta-tooling source bodies"
        ),
        "next_action": next_action,
        "reentry_condition": (
            "All exact-copy source-module refs are relative public macro refs and "
            "none match credential, provider-payload, raw-seed, browser/HUD, "
            "account/session, private-root, traversal, or restricted private "
            "control-plane/runtime/meta-tooling boundaries."
        ),
        "anti_claim": ANTI_CLAIM,
    }


def _load_manifest_rows(paths: Iterable[str]) -> list[tuple[str, Any]]:
    """
    Load load manifest rows for `microcosm_core.validators.source_module_boundary`.

    Input comes from `paths`; malformed or missing data follows the exceptions and checks
    visible in the body.
    """
    rows: list[tuple[str, Any]] = []
    for path in paths:
        payload = read_json_strict(Path(path))
        rows.append((path, payload))
    return rows


def main(argv: list[str] | None = None) -> int:
    """
    Run `microcosm_core.validators.source_module_boundary` as a command-line entry point.

    The command parses argv, calls this module's builders or validators, and returns the
    status code used by the process wrapper.
    """
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
