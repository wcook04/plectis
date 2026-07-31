"""Refresh source-module manifest rows from declared source refs.

This script is the custody repair lane for source-module manifests: it resolves
each manifest row's source_ref and target_ref, copies or public-safe-normalizes
the source body when requested, and rewrites digest/line-count metadata so the
manifest describes the bytes actually present on disk. It does not authorize a
release, private source export, or source mutation outside declared targets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from microcosm_core.public_reference_sanitizer import (
    MACRO_ROOT_NAME,
    PUBLIC_SAFE_PATH_NORMALIZED_MODE,
    PUBLIC_SAFE_PATH_NORMALIZED_RELATION,
    public_safe_transform_receipt,
    sanitize_public_reference_text,
)
from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict
from microcosm_core.validators.source_module_boundary import (
    evaluate_source_module_boundary,
)


HASH_CHUNK_SIZE = 1024 * 1024
PASS = "pass"
PUBLIC_MACRO_SOURCE_DISPLAY_ROOT = "private-macro-source"
PUBLIC_EXAMPLE_HOME = "/Users/example"
PUBLIC_OPERATOR_HOME = "/Users/operator"
PUBLIC_LIGHT_EDIT_PRIVATE_PATH_REDACTION_RELATION = (
    "public_light_edit_private_path_redaction"
)
PUBLIC_LIGHT_EDIT_PRIVATE_PATH_REDACTION_MODE = "direct_verified_macro_body"
PUBLIC_LIGHT_EDIT_PRIVATE_PATH_RE = re.compile(re.escape(PUBLIC_OPERATOR_HOME))
SUBSTRATE_LOCAL_SOURCE_PREFIXES = frozenset(
    {
        "atlas",
        "core",
        "examples",
        "fixtures",
        "paper_modules",
        "receipts",
        "schemas",
        "src",
        "standards",
    }
)
PUBLIC_SAFE_NORMALIZABLE_RELATIONS = frozenset(
    {
        "exact_copy",
        PUBLIC_LIGHT_EDIT_PRIVATE_PATH_REDACTION_RELATION,
        PUBLIC_SAFE_PATH_NORMALIZED_RELATION,
        "public_bound_sanitized_source_authority_self_ref",
        "verified_public_safe_private_path_rewrite",
    }
)


def _public_root_for_path(path: str | Path) -> Path:
    """
    Produce the public root for path value used by `scripts.refresh_source_module_manifest`.

    Inputs are `path`; notable helpers are `resolve`, `is_dir`, `Path`, `cwd`, and 1 more.
    """
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


def _display(path: Path, *, public_root: Path) -> str:
    """
    Compute display from `path` and `public_root`.

    Inputs are `path` and `public_root`; notable helpers are `relative_to`.
    """
    try:
        return str(path.relative_to(public_root))
    except ValueError:
        try:
            return str(path.relative_to(public_root.parent))
        except ValueError:
            return str(path)


def _sha256_hex(path: Path) -> str:
    """
    Return the stable digest computed by
    `scripts.refresh_source_module_manifest._sha256_hex`.

    The input is `path`; the body uses deterministic JSON encoding or chunked file reads
    before formatting the hash.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_hex_bytes(data: bytes) -> str:
    """
    Return the stable digest computed by
    `scripts.refresh_source_module_manifest._sha256_hex_bytes`.

    The input is `data`; the body uses deterministic JSON encoding or chunked file reads
    before formatting the hash.
    """
    return hashlib.sha256(data).hexdigest()


def _uses_prefixed_digest_style(rows: list[dict[str, Any]], field: str) -> bool:
    """
    Return a stable SHA-256 digest for `rows` and `field`.

    The body uses deterministic encoding or chunked file reads so receipts can compare the
    value across runs.
    """
    values = [str(row.get(field) or "") for row in rows if row.get(field)]
    return bool(values) and all(value.startswith("sha256:") for value in values)


def _styled_sha256(hex_digest: str, *, prefixed: bool) -> str:
    """
    Return a stable SHA-256 digest for `hex_digest` and `prefixed`.

    The body uses deterministic encoding or chunked file reads so receipts can compare the
    value across runs.
    """
    if prefixed:
        return f"sha256:{hex_digest}"
    return hex_digest


def _line_count(path: Path) -> int:
    """
    Return line count for `scripts.refresh_source_module_manifest`.

    Inputs are `path`; notable helpers are `open`.
    """
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for count, _line in enumerate(handle, start=1):
            pass
    return count or 1


def _line_count_text(text: str) -> int:
    """
    Derive line count text without touching module import state.

    Inputs are `text`; notable helpers are `count` and `endswith`.
    """
    return text.count("\n") + (0 if text.endswith("\n") else 1) or 1


def _manifest_target_path(public_root: Path, row: dict[str, Any]) -> Path:
    """
    Return manifest target path for the scripts refresh source module manifest flow.

    Inputs are `public_root` and `row`; notable helpers are `removeprefix`, `Path`,
    `is_absolute`, and `get`.
    """
    target_ref = str(row.get("target_ref") or row.get("path") or "")
    target_ref = target_ref.removeprefix("microcosm-substrate/")
    target = Path(target_ref)
    if not target_ref or target.is_absolute() or ".." in target.parts:
        return public_root / "__invalid_source_module_target__"
    return public_root / target


def _private_lookup_source_ref(source_ref: str) -> str:
    """
    Derive private lookup source ref without touching module import state.

    Inputs are `source_ref`; notable helpers are `startswith`.
    """
    display_prefix = f"{PUBLIC_MACRO_SOURCE_DISPLAY_ROOT}/"
    if source_ref == PUBLIC_MACRO_SOURCE_DISPLAY_ROOT:
        return MACRO_ROOT_NAME
    if source_ref.startswith(display_prefix):
        return f"{MACRO_ROOT_NAME}/{source_ref[len(display_prefix):]}"
    return source_ref


def _macro_source_path(public_root: Path, row: dict[str, Any]) -> Path:
    """
    Return macro source path for the scripts refresh source module manifest flow.

    Inputs are `public_root` and `row`; notable helpers are `_private_lookup_source_ref`,
    `removeprefix`, `Path`, `is_absolute`, and 1 more.
    """
    source_ref = _private_lookup_source_ref(str(row.get("source_ref") or ""))
    source_ref = source_ref.removeprefix("microcosm-substrate/")
    source = Path(source_ref)
    if not source_ref or source.is_absolute() or ".." in source.parts:
        return public_root.parent / "__invalid_source_module_source__"
    if source.parts and source.parts[0] in SUBSTRATE_LOCAL_SOURCE_PREFIXES:
        return public_root / source
    return public_root.parent / source


def _source_ref_for_refresh(row: dict[str, Any]) -> tuple[str, dict[str, str]]:
    """
    Return source ref for refresh for the scripts refresh source module manifest flow.

    Inputs are `row`; notable helpers are `get`.
    """
    source_ref = str(row.get("source_ref") or "")
    original_source_ref = str(row.get("original_source_ref") or "")
    target_ref = str(row.get("target_ref") or "")
    path_ref = str(row.get("path") or "")
    stale_self_refs = {
        target_ref,
        path_ref,
        f"microcosm-substrate/{path_ref}" if path_ref else "",
    }
    if source_ref and original_source_ref and source_ref in stale_self_refs:
        return original_source_ref, {
            "source_ref_repaired_from": source_ref,
            "source_ref_repair_basis": "original_source_ref_for_stale_copied_target_self_reference",
        }
    return source_ref, {}


def _inferred_module_id(row: dict[str, Any], *, source_ref: str) -> str:
    """
    Compute inferred module ID from `row` and `source_ref`.

    Inputs are `row` and `source_ref`; notable helpers are `strip`, `Path`, `join`, `get`,
    and 1 more.
    """
    stem = Path(source_ref or str(row.get("path") or "") or "source_module").stem
    slug = "".join(char if char.isalnum() else "_" for char in stem).strip("_")
    return f"{slug or 'source_module'}_public_safe_body_import"


def _public_safety_transform_descriptions(transform: dict[str, Any]) -> list[str]:
    """
    Produce the public safety transform descriptions value used by
    `scripts.refresh_source_module_manifest`.

    Inputs are `transform`; notable helpers are `add`, `append`, and `get`.
    """
    classes = [
        str(row.get("treatment_class") or "")
        for row in transform.get("replacements", [])
        if isinstance(row, dict)
    ]
    descriptions = {
        "private_raw_seed_root_transform": (
            "private raw-seed or vault roots replaced with <private-raw-seed-root> "
            "public-safe boundary tokens"
        ),
        "private_macro_source_ref_transform": (
            "dangling private macro source-root references replaced with "
            "private-macro-source/ provenance labels"
        ),
        "private_browser_transport_symbol_transform": (
            "private browser transport symbols replaced with "
            "<private-browser-transport-symbol> public-safe boundary tokens"
        ),
        "browser_provider_symbol_transform": (
            "private browser transport symbols replaced with "
            "<private-browser-transport-symbol> public-safe boundary tokens"
        ),
    }
    seen: set[str] = set()
    rows: list[str] = []
    for class_id in classes:
        if not class_id or class_id in seen:
            continue
        seen.add(class_id)
        rows.append(descriptions.get(class_id, f"{class_id} public-safe transform applied"))
    return rows


def _public_safe_ref_transform(ref: str) -> tuple[str, dict[str, Any]]:
    """
    Produce the public safe ref transform value used by
    `scripts.refresh_source_module_manifest`.

    Inputs are `ref`; notable helpers are `sanitize_public_reference_text` and
    `public_safe_transform_receipt`.
    """
    if not ref:
        return ref, {}
    sanitization = sanitize_public_reference_text(ref, path=ref)
    if sanitization.blockers:
        return ref, {"status": "blocked", "public_safe": False}
    if sanitization.replacements:
        return sanitization.text, public_safe_transform_receipt(sanitization)
    return ref, {}


def _bundle_manifest_source_root_transform(
    manifest_path: str | Path,
    *,
    write: bool,
    public_safe_normalize: bool,
) -> dict[str, Any]:
    """
    Serialize
    `scripts.refresh_source_module_manifest._bundle_manifest_source_root_transform` into the
    payload shape expected by scripts refresh source module manifest.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    bundle_manifest_path = Path(manifest_path).parent / "bundle_manifest.json"
    if not public_safe_normalize:
        return {"status": "not_requested", "write_applied": False}
    if not bundle_manifest_path.is_file():
        return {"status": "missing", "write_applied": False}
    bundle_manifest = read_json_strict(bundle_manifest_path)
    if not isinstance(bundle_manifest, dict):
        return {
            "status": "blocked",
            "write_applied": False,
            "findings": ["bundle_manifest_not_json_object"],
        }
    source_root = str(bundle_manifest.get("source_root") or "")
    public_safe_source_root, public_safe_transform = _public_safe_ref_transform(source_root)
    if public_safe_transform.get("status") == "blocked":
        return {
            "status": "blocked",
            "field": "source_root",
            "write_applied": False,
            "findings": ["bundle_manifest_source_root_normalization_blocked"],
        }
    if not public_safe_transform:
        return {
            "status": "unchanged",
            "field": "source_root",
            "source_root": source_root,
            "write_applied": False,
        }
    if write:
        bundle_manifest["source_root"] = public_safe_source_root
        bundle_manifest["source_root_public_safe_transform"] = public_safe_transform
        write_json_atomic(bundle_manifest_path, bundle_manifest)
    return {
        "status": "transformed",
        "field": "source_root",
        "source_root": public_safe_source_root,
        "public_safe_transform": public_safe_transform,
        "write_applied": write,
    }


def refresh_manifest(
    manifest_path: str | Path,
    *,
    module_ids: set[str],
    write: bool,
    public_safe_normalize: bool = False,
    target_metadata_only: bool = False,
) -> dict[str, Any]:
    """
    Serialize `scripts.refresh_source_module_manifest.refresh_manifest` into the payload
    shape expected by scripts refresh source module manifest.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    manifest = read_json_strict(Path(manifest_path))
    if not isinstance(manifest, dict):
        raise ValueError("source module manifest must be a JSON object")
    public_root = _public_root_for_path(manifest_path)
    rows = [row for row in manifest.get("modules", []) if isinstance(row, dict)]
    if target_metadata_only:
        refreshed_rows: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []
        for row in rows:
            module_id = str(row.get("module_id") or "")
            if module_ids and module_id not in module_ids:
                continue
            target = _manifest_target_path(public_root, row)
            row_findings: list[str] = []
            if row.get("body_copied") is not True:
                row_findings.append("body_copied_not_true")
            if not target.is_file():
                row_findings.append("target_missing_or_not_file")
            if row_findings:
                findings.append(
                    {
                        "module_id": module_id,
                        "target_ref": row.get("target_ref"),
                        "findings": row_findings,
                    }
                )
                continue

            target_bytes = target.read_bytes()
            target_digest_hex = _sha256_hex_bytes(target_bytes)
            target_digest = _styled_sha256(
                target_digest_hex,
                prefixed=str(row.get("target_sha256") or "").startswith("sha256:"),
            )
            target_line_count = _line_count(target)
            if write:
                row["byte_count"] = len(target_bytes)
                row["line_count"] = target_line_count
                if "target_byte_count" in row:
                    row["target_byte_count"] = len(target_bytes)
                if "target_line_count" in row:
                    row["target_line_count"] = target_line_count
                row["sha256"] = _styled_sha256(
                    target_digest_hex,
                    prefixed=str(row.get("sha256") or "").startswith("sha256:"),
                )
                row["target_sha256"] = target_digest
                if "sha256_match" in row:
                    row["sha256_match"] = True
                if "target_expected_digest_match" in row:
                    row["target_expected_digest_match"] = True
            refreshed_rows.append(
                {
                    "module_id": module_id,
                    "target_ref": row.get("target_ref"),
                    "target_sha256": target_digest,
                    "target_line_count": target_line_count,
                    "target_byte_count": len(target_bytes),
                    "write_applied": write,
                }
            )

        status = PASS if refreshed_rows and not findings else "blocked"
        if write and status == PASS:
            write_json_atomic(Path(manifest_path), manifest)
        return {
            "schema_version": "source_module_manifest_refresh_result_v1",
            "status": status,
            "manifest_ref": _display(Path(manifest_path), public_root=public_root),
            "boundary": {
                "status": "not_run_target_metadata_only",
                "authority_ceiling": (
                    "Public target size and digest currentness only; source "
                    "availability, source-to-target correspondence, and release "
                    "authority are not checked."
                ),
            },
            "write_applied": write,
            "requested_module_ids": sorted(module_ids),
            "public_safe_normalize": False,
            "target_metadata_only": True,
            "refreshed_count": len(refreshed_rows),
            "finding_count": len(findings),
            "findings": findings,
            "rows": refreshed_rows,
            "anti_claim": (
                "This mode refreshes metadata from already-public target files. "
                "It does not read private or unavailable sources, prove source "
                "correspondence, mutate target bodies, or authorize release."
            ),
        }
    declared_omissions = [
        row
        for row in manifest.get("release_substitution_omissions", [])
        if isinstance(row, dict)
    ]
    boundary_manifest = dict(manifest)
    # Release substitutions are explicit non-import records. Revalidating their
    # private source refs as if they were copied module claims makes the safe
    # exact-copy rows in the same manifest impossible to refresh. The omitted
    # rows remain untouched in the written manifest; the boundary still checks
    # every declared module and all of its source/target refs.
    boundary_manifest.pop("release_substitution_omissions", None)
    boundary = evaluate_source_module_boundary(
        [(str(Path(manifest_path)), boundary_manifest)],
    )
    if boundary["status"] != PASS:
        return {
            "schema_version": "source_module_manifest_refresh_result_v1",
            "status": "blocked",
            "manifest_ref": _display(Path(manifest_path), public_root=public_root),
            "boundary": boundary,
            "refreshed_count": 0,
            "rows": [],
        }

    bundle_manifest_transform = _bundle_manifest_source_root_transform(
        manifest_path,
        write=write,
        public_safe_normalize=public_safe_normalize,
    )
    digest_style = {
        "sha256": _uses_prefixed_digest_style(rows, "sha256"),
        "source_sha256": _uses_prefixed_digest_style(rows, "source_sha256"),
        "target_sha256": _uses_prefixed_digest_style(rows, "target_sha256"),
    }
    refreshed_rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    if bundle_manifest_transform["status"] == "blocked":
        findings.append(
            {
                "module_id": "__bundle_manifest__",
                "source_ref": "bundle_manifest.json::source_root",
                "target_ref": "bundle_manifest.json",
                "findings": bundle_manifest_transform.get("findings", []),
            }
        )
    for row in rows:
        module_id = str(row.get("module_id") or "")
        if module_ids and module_id not in module_ids:
            continue
        source_ref, source_ref_repair = _source_ref_for_refresh(row)
        if not module_id and source_ref_repair:
            module_id = _inferred_module_id(row, source_ref=source_ref)
        source_row = dict(row)
        source_row["source_ref"] = source_ref
        source = _macro_source_path(public_root, source_row)
        target = _manifest_target_path(public_root, row)
        row_findings: list[str] = []
        if not source.is_file():
            row_findings.append("source_missing")
        if target.exists() and not target.is_file():
            row_findings.append("target_not_file")
        relation = str(row.get("source_to_target_relation") or "")
        if public_safe_normalize:
            if relation not in PUBLIC_SAFE_NORMALIZABLE_RELATIONS:
                row_findings.append("source_to_target_relation_not_public_safe_normalizable")
        elif relation != "exact_copy":
            row_findings.append("source_to_target_relation_not_exact_copy")
        if row_findings:
            findings.append(
                {
                    "module_id": module_id,
                    "source_ref": row.get("source_ref"),
                    "target_ref": row.get("target_ref"),
                    "findings": row_findings,
                }
            )
            continue

        source_bytes = source.read_bytes()
        expected_target_bytes = source_bytes
        target_relation = relation
        public_safe_transform: dict[str, Any] = {}
        public_safe_source_ref = source_ref
        public_safe_source_ref_transform: dict[str, Any] = {}
        public_safe_mode = ""
        source_line_count = _line_count(source)
        target_line_count: int | None = None
        if (
            public_safe_normalize
            and relation == PUBLIC_LIGHT_EDIT_PRIVATE_PATH_REDACTION_RELATION
        ):
            try:
                source_text = source_bytes.decode("utf-8")
            except UnicodeDecodeError:
                findings.append(
                    {
                        "module_id": module_id,
                        "source_ref": row.get("source_ref"),
                        "target_ref": row.get("target_ref"),
                        "findings": ["public_light_edit_redaction_requires_utf8_source"],
                    }
                )
                continue
            redacted_text, _redaction_count = PUBLIC_LIGHT_EDIT_PRIVATE_PATH_RE.subn(
                PUBLIC_EXAMPLE_HOME,
                source_text,
            )
            expected_target_bytes = redacted_text.encode("utf-8")
            target_relation = PUBLIC_LIGHT_EDIT_PRIVATE_PATH_REDACTION_RELATION
            public_safe_mode = str(
                row.get("public_safe_mode")
                or PUBLIC_LIGHT_EDIT_PRIVATE_PATH_REDACTION_MODE
            )
            target_line_count = _line_count_text(redacted_text)
        elif public_safe_normalize:
            public_safe_source_ref, public_safe_source_ref_transform = (
                _public_safe_ref_transform(public_safe_source_ref)
            )
            if public_safe_source_ref_transform.get("status") == "blocked":
                findings.append(
                    {
                        "module_id": module_id,
                        "source_ref": row.get("source_ref"),
                        "target_ref": row.get("target_ref"),
                        "findings": ["public_safety_source_ref_normalization_blocked"],
                    }
                )
                continue
            try:
                source_text = source_bytes.decode("utf-8")
            except UnicodeDecodeError:
                findings.append(
                    {
                        "module_id": module_id,
                        "source_ref": row.get("source_ref"),
                        "target_ref": row.get("target_ref"),
                        "findings": ["public_safety_normalization_requires_utf8_source"],
                    }
                )
                continue
            sanitization = sanitize_public_reference_text(
                source_text,
                path=str(row.get("source_ref") or ""),
            )
            public_safe_transform = public_safe_transform_receipt(sanitization)
            if sanitization.blockers:
                findings.append(
                    {
                        "module_id": module_id,
                        "source_ref": row.get("source_ref"),
                        "target_ref": row.get("target_ref"),
                        "findings": ["public_safety_normalization_blocked"],
                        "public_safety_blockers": [
                            blocker.to_json() for blocker in sanitization.blockers
                        ],
                    }
                )
                continue
            if sanitization.replacements:
                expected_target_bytes = sanitization.text.encode("utf-8")
                target_relation = PUBLIC_SAFE_PATH_NORMALIZED_RELATION
                public_safe_mode = PUBLIC_SAFE_PATH_NORMALIZED_MODE
                target_line_count = _line_count_text(sanitization.text)
            else:
                public_safe_transform = {}

        if write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(expected_target_bytes)

        source_digest_hex = _sha256_hex_bytes(source_bytes)
        expected_target_digest_hex = _sha256_hex_bytes(expected_target_bytes)
        target_digest_hex = _sha256_hex(target) if target.is_file() else ""
        if target_line_count is None:
            target_line_count = _line_count(target) if target.is_file() else None
        source_target_digest_match = bool(
            target_digest_hex and source_digest_hex == target_digest_hex
        )
        target_expected_digest_match = bool(
            target_digest_hex and expected_target_digest_hex == target_digest_hex
        )
        source_digest = _styled_sha256(
            source_digest_hex,
            prefixed=digest_style["source_sha256"],
        )
        target_digest = _styled_sha256(
            target_digest_hex,
            prefixed=digest_style["target_sha256"],
        )
        expected_target_digest = _styled_sha256(
            expected_target_digest_hex,
            prefixed=digest_style["target_sha256"],
        )
        if write:
            row["byte_count"] = len(expected_target_bytes)
            row["line_count"] = target_line_count
            if "source_byte_count" in row:
                row["source_byte_count"] = len(source_bytes)
            if "source_line_count" in row:
                row["source_line_count"] = source_line_count
            if "target_byte_count" in row:
                row["target_byte_count"] = len(expected_target_bytes)
            if "target_line_count" in row:
                row["target_line_count"] = target_line_count
            row["sha256"] = _styled_sha256(
                expected_target_digest_hex,
                prefixed=digest_style["sha256"],
            )
            row["source_sha256"] = source_digest
            row["target_sha256"] = target_digest
            row["sha256_match"] = target_expected_digest_match
            row["source_target_sha256_match"] = source_target_digest_match
            row["target_expected_digest_match"] = target_expected_digest_match
            row["source_to_target_relation"] = target_relation
            if not row.get("module_id") and module_id:
                row["module_id"] = module_id
            if source_ref_repair:
                row.update(source_ref_repair)
            if public_safe_source_ref != row.get("source_ref"):
                row["source_ref"] = public_safe_source_ref
            if public_safe_source_ref_transform:
                row["source_ref_public_safe_transform"] = public_safe_source_ref_transform
            if public_safe_mode:
                row["public_safe_mode"] = public_safe_mode
            if public_safe_transform:
                row["public_safe_transform"] = public_safe_transform
                row["public_safety_transformations"] = _public_safety_transform_descriptions(
                    public_safe_transform
                )

        refreshed_rows.append(
            {
                "module_id": module_id,
                "source_ref": public_safe_source_ref,
                "declared_source_ref": row.get("source_ref"),
                "source_ref_repair": source_ref_repair,
                "target_ref": row.get("target_ref"),
                "source_sha256": source_digest,
                "target_sha256": target_digest,
                "expected_target_sha256": expected_target_digest,
                "source_line_count": source_line_count,
                "target_line_count": target_line_count,
                "digest_match": target_expected_digest_match,
                "source_target_digest_match": source_target_digest_match,
                "target_expected_digest_match": target_expected_digest_match,
                "source_to_target_relation": target_relation,
                "public_safe_transform": public_safe_transform,
                "write_applied": write,
            }
        )

    status = (
        PASS
        if refreshed_rows
        and not findings
        and all(row["target_expected_digest_match"] for row in refreshed_rows)
        and bundle_manifest_transform["status"] != "blocked"
        and (
            bundle_manifest_transform["status"] != "transformed"
            or bundle_manifest_transform.get("write_applied")
        )
        else "blocked"
    )
    if write and status == PASS:
        write_json_atomic(Path(manifest_path), manifest)
    return {
        "schema_version": "source_module_manifest_refresh_result_v1",
        "status": status,
        "manifest_ref": _display(Path(manifest_path), public_root=public_root),
        "boundary": {
            "status": boundary["status"],
            "safe_ref_count": boundary["safe_ref_count"],
            "blocked_ref_count": boundary["blocked_ref_count"],
            "declared_release_substitution_omission_count": len(
                declared_omissions
            ),
        },
        "write_applied": write,
        "requested_module_ids": sorted(module_ids),
        "public_safe_normalize": public_safe_normalize,
        "bundle_manifest_public_safe_transform": bundle_manifest_transform,
        "refreshed_count": len(refreshed_rows),
        "finding_count": len(findings),
        "findings": findings,
        "rows": refreshed_rows,
        "anti_claim": (
            "This helper only refreshes declared exact-copy source-module files "
            "from relative public macro refs and normalizes sibling bundle manifest "
            "source-root provenance after source-module boundary checks. "
            "It does not authorize private source export, source mutation outside "
            "declared targets, release, or provider access."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    """
    Run `scripts.refresh_source_module_manifest` as a command-line entry point.

    The command parses argv, calls this module's builders or validators, and returns the
    status code used by the process wrapper.
    """
    parser = argparse.ArgumentParser(
        description="Refresh declared exact-copy source module manifest rows."
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--module-id", action="append", default=[])
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--public-safe-normalize",
        action="store_true",
        help=(
            "When writing UTF-8 source modules, apply the canonical public-safety "
            "reference sanitizer and mark transformed targets as public-safe "
            "path-normalized copies instead of exact copies."
        ),
    )
    parser.add_argument(
        "--target-metadata-only",
        action="store_true",
        help=(
            "refresh sizes and digests from already-public target files without "
            "claiming source correspondence"
        ),
    )
    args = parser.parse_args(argv)

    result = refresh_manifest(
        args.manifest,
        module_ids=set(args.module_id),
        write=args.write,
        public_safe_normalize=args.public_safe_normalize,
        target_metadata_only=args.target_metadata_only,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
