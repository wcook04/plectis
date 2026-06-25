from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict
from microcosm_core.validators.source_module_boundary import (
    evaluate_source_module_boundary,
)
from tools.meta.plectis_public_safety.public_reference_sanitizer import (
    MACRO_ROOT_NAME,
    PUBLIC_SAFE_PATH_NORMALIZED_MODE,
    PUBLIC_SAFE_PATH_NORMALIZED_RELATION,
    public_safe_transform_receipt,
    sanitize_public_reference_text,
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
    try:
        return str(path.relative_to(public_root))
    except ValueError:
        try:
            return str(path.relative_to(public_root.parent))
        except ValueError:
            return str(path)


def _sha256_hex(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _uses_prefixed_digest_style(rows: list[dict[str, Any]], field: str) -> bool:
    values = [str(row.get(field) or "") for row in rows if row.get(field)]
    return bool(values) and all(value.startswith("sha256:") for value in values)


def _styled_sha256(hex_digest: str, *, prefixed: bool) -> str:
    if prefixed:
        return f"sha256:{hex_digest}"
    return hex_digest


def _line_count(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for count, _line in enumerate(handle, start=1):
            pass
    return count or 1


def _line_count_text(text: str) -> int:
    return text.count("\n") + (0 if text.endswith("\n") else 1) or 1


def _manifest_target_path(public_root: Path, row: dict[str, Any]) -> Path:
    target_ref = str(row.get("target_ref") or row.get("path") or "")
    target_ref = target_ref.removeprefix("microcosm-substrate/")
    target = Path(target_ref)
    if not target_ref or target.is_absolute() or ".." in target.parts:
        return public_root / "__invalid_source_module_target__"
    return public_root / target


def _private_lookup_source_ref(source_ref: str) -> str:
    display_prefix = f"{PUBLIC_MACRO_SOURCE_DISPLAY_ROOT}/"
    if source_ref == PUBLIC_MACRO_SOURCE_DISPLAY_ROOT:
        return MACRO_ROOT_NAME
    if source_ref.startswith(display_prefix):
        return f"{MACRO_ROOT_NAME}/{source_ref[len(display_prefix):]}"
    return source_ref


def _macro_source_path(public_root: Path, row: dict[str, Any]) -> Path:
    source_ref = _private_lookup_source_ref(str(row.get("source_ref") or ""))
    source_ref = source_ref.removeprefix("microcosm-substrate/")
    source = Path(source_ref)
    if not source_ref or source.is_absolute() or ".." in source.parts:
        return public_root.parent / "__invalid_source_module_source__"
    if source.parts and source.parts[0] in SUBSTRATE_LOCAL_SOURCE_PREFIXES:
        return public_root / source
    return public_root.parent / source


def _source_ref_for_refresh(row: dict[str, Any]) -> tuple[str, dict[str, str]]:
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
    stem = Path(source_ref or str(row.get("path") or "") or "source_module").stem
    slug = "".join(char if char.isalnum() else "_" for char in stem).strip("_")
    return f"{slug or 'source_module'}_public_safe_body_import"


def _public_safety_transform_descriptions(transform: dict[str, Any]) -> list[str]:
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
    """Run the canonical public-safety sanitizer over one source/provenance ref string.

    - Teleology: single-ref custody normalizer that routes a source_ref through the public reference sanitizer so private roots never leak into refreshed manifest rows.
    - Guarantee: returns (text, receipt); on a clean ref returns (ref, {}); on replacements returns (sanitized_text, public_safe_transform_receipt); on a blocker returns (ref, {"status": "blocked", "public_safe": False}) leaving the ref unchanged.
    - Fails: never raises; sanitizer blockers surface as the {"status": "blocked", "public_safe": False} receipt, not an exception; empty ref short-circuits to (ref, {}).
    - When-needed: inspect when deciding whether a single source/provenance ref is public-safe before folding it into a refreshed manifest row.
    - Reads: only the in-memory `ref` argument (no filesystem read).
    - Escalates-to: tools.meta.plectis_public_safety.public_reference_sanitizer (sanitize_public_reference_text / public_safe_transform_receipt) for the authoritative blocker/replacement rules.
    - Non-goal: does not authorize source export, release, or assert public-safety beyond what the sanitizer's replacement/blocker rules cover.
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
    """Normalize the sibling bundle_manifest.json `source_root` provenance to a public-safe ref.

    - Teleology: source-ref custody helper that strips private macro/vault roots from the bundle manifest's source_root so the refresh stays public-safe.
    - Guarantee: returns a status dict ('not_requested' | 'missing' | 'blocked' | 'unchanged' | 'transformed'); only on 'transformed' with write=True is bundle_manifest.json rewritten (source_root + source_root_public_safe_transform) via write_json_atomic.
    - Fails: never raises; non-JSON-object bundle manifest -> {"status": "blocked", findings: ["bundle_manifest_not_json_object"]}; sanitizer blocker on source_root -> {"status": "blocked", ...}.
    - When-needed: inspect when a public-safe refresh must rewrite or verify the bundle manifest's declared source_root provenance label.
    - Reads: the sibling bundle_manifest.json `source_root` field.
    - Writes: with write=True on a transform, bundle_manifest.json's source_root and source_root_public_safe_transform.
    - Escalates-to: public_reference_sanitizer.sanitize_public_reference_text / public_safe_transform_receipt; the bundle_manifest.json is the artifact this rewrites.
    - Non-goal: does not authorize source export, release, or treat the rewritten provenance label as authority over the real private root.
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
) -> dict[str, Any]:
    """Refresh declared exact-copy source-module rows: re-copy bodies, recompute digests, fold provenance.

    - Teleology: source-custody engine that re-binds each manifest row's target body/sha256 to its declared macro source ref, after the source-module boundary gate passes, optionally applying public-safe normalization.
    - Guarantee: returns a `source_module_manifest_refresh_result_v1` dict; status is 'pass' only when rows refreshed, no findings, every target_expected_digest_match true, and bundle-manifest transform not blocked; with write+pass the manifest and target bytes are persisted via write_json_atomic.
    - Fails: non-object manifest -> raises ValueError; boundary status != 'pass', missing/non-file source, or non-public-safe-normalizable / non-exact_copy relation -> status 'blocked' with per-row findings (never raises).
    - When-needed: inspect when a manifest row's target body or digest drifts from its macro source, or when verifying the exact-copy custody contract before release.
    - Reads: the `--manifest` JSON, each declared macro source file body, and the sibling bundle_manifest.json source_root.
    - Writes: with write=True, refreshed target files plus the manifest itself (digests, byte/line counts, relation, public-safe transforms).
    - Escalates-to: microcosm_core.validators.source_module_boundary.evaluate_source_module_boundary and the public_reference_sanitizer; the manifest is the source-of-record this projection re-derives.
    - Non-goal: does not authorize private source export, source mutation outside declared targets, public-safe equivalence beyond the sanitizer's checks, release, or provider access.
    """
    manifest = read_json_strict(Path(manifest_path))
    if not isinstance(manifest, dict):
        raise ValueError("source module manifest must be a JSON object")
    public_root = _public_root_for_path(manifest_path)
    boundary = evaluate_source_module_boundary(
        [(str(Path(manifest_path)), manifest)],
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

    rows = [row for row in manifest.get("modules", []) if isinstance(row, dict)]
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
    """Parse args, refresh the source-module manifest, print the result, and return its exit code.

    - Teleology: CLI front door for refreshing declared exact-copy source-module bodies/digests from public macro refs.
    - Guarantee: prints the refresh result JSON; with --write applied changes only when the run reaches status 'pass'.
    - Fails: boundary block, missing/mismatched source, or non-normalizable relation -> result status 'blocked' -> returns exit code 1.
    - Reads: --manifest JSON and the declared macro source files.
    - Writes: stdout always; with --write, refreshed target files and the manifest itself.
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
    args = parser.parse_args(argv)

    result = refresh_manifest(
        args.manifest,
        module_ids=set(args.module_id),
        write=args.write,
        public_safe_normalize=args.public_safe_normalize,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
