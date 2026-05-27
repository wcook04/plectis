from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.fixture_registry import load_pattern_binding_fixture, load_pattern_binding_substrate_bundle
from microcosm_core.macro_tools import pattern_route_readiness
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
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_BODY_STATUS = "copied_non_secret_pattern_binding_macro_body_with_provenance"
RUNTIME_METADATA_ONLY_ANTI_CLAIM_REF = "anti_claim.pattern_binding.runtime_metadata_only"
REAL_PATTERN_LEDGER_ANTI_CLAIM_REF = "anti_claim.pattern_binding.real_pattern_ledger_source_faithful"
REAL_PATTERN_LEDGER_GOVERNING_STANDARD = "std_microcosm_pattern_binding_contract"
REAL_PATTERN_LEDGER_SOURCE_KEY = "real_pattern_ledger_source"
REAL_PATTERN_SUBSTRATE_BINDINGS_SOURCE_KEY = "real_pattern_substrate_bindings_source"
REAL_PATTERN_ROUTE_READINESS_BUNDLE_KEY = "real_pattern_route_readiness_bundle"
REAL_PATTERN_SUBSTRATE_BINDINGS_SCHEMA = "extracted_pattern_substrate_bindings_v1"
CARD_SCHEMA_VERSION = "pattern_binding_contract_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "expected_negative_cases",
    "observed_negative_cases",
    "findings",
    "secret_exclusion_scan",
    "accepted_pattern_ids",
    "rejected_pattern_ids",
    "duplicate_pattern_ids",
    "source_module_imports",
    "source_open_body_imports",
    "public_runtime_refs",
    "real_pattern_ledger_source",
    "real_pattern_substrate_bindings_source",
    "real_pattern_route_readiness_source",
    "truth_accounting",
    "freshness_basis",
)
PUBLIC_SAFE_SOURCE_MODULE_CLASSES = {
    "public_macro_pattern_body",
    "public_macro_receipt_body",
    "public_macro_standard_body",
    "public_macro_tool_body",
}
SOURCE_MODULE_RELATIONS = {
    "exact_copy",
    "source_faithful_json_slice",
}

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


def _json_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


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


def _strip_microcosm_prefix(ref: str) -> str:
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _sha256(path: Path) -> str:
    return "sha256:" + _file_sha256(path)


def _json_rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _source_module_manifest_path(input_dir: str | Path) -> Path:
    return Path(input_dir) / SOURCE_MODULE_MANIFEST_NAME


def _source_module_target_path(
    row: dict[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> tuple[Path, str]:
    target_ref = _strip_microcosm_prefix(str(row.get("target_ref") or ""))
    row_path = str(row.get("path") or "")
    if target_ref:
        target = public_root / target_ref
        if target.exists() or not row_path:
            return target, target_ref
        relocated = manifest_path.parent / row_path
        return relocated, public_relative_path(relocated, display_root=public_root)
    if row_path:
        target = manifest_path.parent / row_path
        return target, public_relative_path(target, display_root=public_root)
    return public_root, ""


def _source_artifact_paths(input_dir: str | Path, *, public_root: Path) -> list[Path]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = [manifest_path]
    for row in _json_rows(manifest, "modules"):
        target_path, _target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        if target_path.is_file():
            paths.append(target_path)
    return paths


def _file_freshness_entry(path: Path, *, public_root: Path) -> dict[str, Any]:
    public_ref = public_relative_path(path, display_root=public_root)
    if not path.exists():
        return {
            "path": public_ref,
            "exists": False,
            "size_bytes": 0,
            "mtime_ns": 0,
        }
    stat = path.stat()
    return {
        "path": public_ref,
        "exists": path.is_file(),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _append_tree_files(paths: list[Path], path: Path) -> None:
    if path.is_dir():
        paths.extend(sorted(candidate for candidate in path.rglob("*") if candidate.is_file()))
    else:
        paths.append(path)


def _substrate_bundle_input_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    paths: list[Path] = [Path(__file__).resolve(strict=False)]
    paths.append(Path(pattern_route_readiness.__file__).resolve(strict=False))
    _append_tree_files(paths, input_dir)

    manifest_path = input_dir / "bundle_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        manifest = {}
    if isinstance(manifest, dict):
        for key in (
            REAL_PATTERN_LEDGER_SOURCE_KEY,
            REAL_PATTERN_SUBSTRATE_BINDINGS_SOURCE_KEY,
            REAL_PATTERN_ROUTE_READINESS_BUNDLE_KEY,
        ):
            spec = manifest.get(key)
            if not isinstance(spec, dict):
                continue
            source_ref = str(spec.get("path") or spec.get("source_ref") or "").strip()
            if source_ref:
                _append_tree_files(paths, public_root / source_ref)

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve(strict=False))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _substrate_bundle_freshness_basis(input_dir: Path, *, public_root: Path) -> list[dict[str, Any]]:
    return sorted(
        (
            _file_freshness_entry(path, public_root=public_root)
            for path in _substrate_bundle_input_paths(input_dir, public_root=public_root)
        ),
        key=lambda item: str(item["path"]),
    )


def _fresh_substrate_bundle_receipt(
    out_dir: str | Path,
    *,
    freshness_digest: str,
) -> dict[str, Any] | None:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    receipt_path = target / SUBSTRATE_BUNDLE_RESULT_NAME
    if not receipt_path.is_file():
        return None
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("card_schema_version") != CARD_SCHEMA_VERSION:
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("input_mode") != "exported_substrate_bundle":
        return None
    if payload.get("freshness_digest") != freshness_digest:
        return None
    result = dict(payload)
    result["receipt_reused"] = True
    result["freshness_status"] = "current"
    return result


def validate_source_module_imports(input_dir: str | Path, *, public_root: Path) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    manifest_ref = public_relative_path(manifest_path, display_root=public_root)
    findings: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        findings.append(
            _finding(
                "PATTERN_BINDING_SOURCE_MODULE_MANIFEST_MISSING",
                "Pattern-binding exported bundle requires source_module_manifest.json for copied macro source bodies.",
                case_id="source_module_manifest_floor",
                pattern_id=manifest_ref,
            )
        )
        return {
            "status": "blocked",
            "source_module_manifest_ref": manifest_ref,
            "module_count": 0,
            "modules": [],
            "findings": findings,
            "observed_negative_cases": {},
        }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module_rows = _json_rows(manifest, "modules")
    if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
        findings.append(
            _finding(
                "PATTERN_BINDING_SOURCE_IMPORT_CLASS_MISMATCH",
                "Source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_manifest_floor",
                pattern_id=manifest_ref,
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "PATTERN_BINDING_SOURCE_BODY_IN_RECEIPT_FORBIDDEN",
                "Copied pattern-binding macro bodies may live in source_artifacts, not in receipts.",
                case_id="source_module_manifest_floor",
                pattern_id=manifest_ref,
            )
        )
    if manifest.get("module_count") != len(module_rows):
        findings.append(
            _finding(
                "PATTERN_BINDING_SOURCE_MODULE_COUNT_MISMATCH",
                "Source module manifest module_count must equal its module rows.",
                case_id="source_module_manifest_floor",
                pattern_id=manifest_ref,
            )
        )

    for row in module_rows:
        module_id = str(row.get("module_id") or "")
        target_path, target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        material_class = str(row.get("material_class") or "")
        relation = str(row.get("source_to_target_relation") or "")
        expected_digest = str(row.get("sha256") or "")
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "PATTERN_BINDING_SOURCE_MODULE_IMPORT_CLASS_MISMATCH",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_manifest_floor",
                    pattern_id=module_id or target_ref or "source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_MODULE_CLASSES:
            findings.append(
                _finding(
                    "PATTERN_BINDING_SOURCE_MODULE_CLASS_FORBIDDEN",
                    "Pattern-binding body imports may include only public macro pattern, receipt, standard, and tool bodies.",
                    case_id="source_module_manifest_floor",
                    pattern_id=module_id or target_ref or "source_module",
                )
            )
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "PATTERN_BINDING_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
                    "Source module rows must set body_copied=true and body_in_receipt=false.",
                    case_id="source_module_manifest_floor",
                    pattern_id=module_id or target_ref or "source_module",
                )
            )
        if relation not in SOURCE_MODULE_RELATIONS:
            findings.append(
                _finding(
                    "PATTERN_BINDING_SOURCE_MODULE_RELATION_UNVERIFIED",
                    "Source module rows must state exact_copy or source_faithful_json_slice.",
                    case_id="source_module_manifest_floor",
                    pattern_id=module_id or target_ref or "source_module",
                )
            )
        if not target_path.is_file():
            findings.append(
                _finding(
                    "PATTERN_BINDING_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target must exist inside the public bundle.",
                    case_id="source_module_manifest_floor",
                    pattern_id=target_ref or module_id or "source_module",
                )
            )
            continue
        actual_digest = _sha256(target_path)
        if expected_digest != actual_digest:
            findings.append(
                _finding(
                    "PATTERN_BINDING_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module target digest must match source_module_manifest.json.",
                    case_id="source_module_manifest_floor",
                    pattern_id=target_ref or module_id or "source_module",
                )
            )
        modules.append(
            {
                "module_id": module_id,
                "source_ref": str(row.get("source_ref") or ""),
                "target_ref": target_ref,
                "material_class": material_class,
                "sha256": expected_digest,
                "actual_sha256": actual_digest,
                "line_count": row.get("line_count"),
                "source_to_target_relation": relation,
                "body_in_receipt": False,
            }
        )

    return {
        "status": PASS if not findings and modules else "blocked",
        "source_module_manifest_ref": manifest_ref,
        "module_count": len(modules),
        "modules": modules,
        "findings": findings,
        "observed_negative_cases": {},
    }


def _source_open_body_import_summary(source_imports: dict[str, Any]) -> dict[str, Any]:
    modules = _json_rows(source_imports, "modules")
    module_ids = [str(row.get("module_id")) for row in modules if row.get("module_id")]
    return {
        "schema_version": "pattern_binding_source_open_body_imports_v1",
        "status": source_imports.get("status"),
        "source_import_class": SOURCE_IMPORT_CLASS if modules else "",
        "body_material_status": SOURCE_BODY_STATUS if modules else "",
        "body_material_count": len(modules),
        "body_material_ids": module_ids,
        "material_classes": sorted(
            {str(row.get("material_class")) for row in modules if row.get("material_class")}
        ),
        "source_manifest_refs": [
            source_imports["source_module_manifest_ref"]
        ]
        if source_imports.get("source_module_manifest_ref")
        else [],
        "aggregate_floor_ref": (
            f"{source_imports['source_module_manifest_ref']}::modules"
            if source_imports.get("source_module_manifest_ref")
            else ""
        ),
        "body_in_receipt": False,
        "authority_ceiling": {
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
            "public_leaf_authority_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json and source_artifacts/ for copied "
            "pattern-binding macro bodies; receipts carry refs, digests, and status only."
        )
        if modules
        else "",
    }


def _real_pattern_ledger_projection(
    input_dir: str | Path,
    manifest: dict[str, Any],
    substrate_runtime_refs_by_pattern_id: dict[str, str] | None = None,
) -> dict[str, Any] | None:
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
        runtime_refs = [runtime_ref]
        if substrate_runtime_refs_by_pattern_id:
            substrate_runtime_ref = substrate_runtime_refs_by_pattern_id.get(pattern_id)
            if substrate_runtime_ref:
                runtime_refs.append(substrate_runtime_ref)
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
                "public_runtime_refs": runtime_refs,
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


def _real_pattern_substrate_bindings_projection(
    input_dir: str | Path,
    manifest: dict[str, Any],
    ledger_pattern_ids: set[str],
) -> dict[str, Any] | None:
    spec = manifest.get(REAL_PATTERN_SUBSTRATE_BINDINGS_SOURCE_KEY)
    if not isinstance(spec, dict):
        return None

    source_ref = str(spec.get("path") or spec.get("source_ref") or "").strip()
    public_root = _public_root_for_bundle(input_dir)
    binding_path = public_root / source_ref if source_ref else public_root
    findings: list[dict[str, Any]] = []
    payload: dict[str, Any] = {}
    digest = ""
    if not source_ref:
        findings.append(
            _finding(
                "MISSING_REAL_PATTERN_SUBSTRATE_BINDINGS_REF",
                "Real pattern substrate-bindings source path is missing.",
            )
        )
    elif not binding_path.is_file():
        findings.append(
            _finding(
                "REAL_PATTERN_SUBSTRATE_BINDINGS_NOT_FOUND",
                "Real pattern substrate-bindings source path does not resolve inside the public root.",
            )
        )
    else:
        payload = json.loads(binding_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            findings.append(
                _finding(
                    "REAL_PATTERN_SUBSTRATE_BINDINGS_NOT_OBJECT",
                    "Real pattern substrate-bindings source is not a JSON object.",
                )
            )
            payload = {}
        digest = _file_sha256(binding_path)

    expected_digest = str(spec.get("sha256") or "").strip()
    if expected_digest and digest and digest != expected_digest:
        findings.append(
            _finding(
                "REAL_PATTERN_SUBSTRATE_BINDINGS_DIGEST_MISMATCH",
                "Real pattern substrate-bindings digest mismatch.",
            )
        )

    schema_version = str(payload.get("schema_version") or "")
    if payload and schema_version != REAL_PATTERN_SUBSTRATE_BINDINGS_SCHEMA:
        findings.append(
            _finding(
                "REAL_PATTERN_SUBSTRATE_BINDINGS_SCHEMA_MISMATCH",
                "Real pattern substrate-bindings schema mismatch.",
            )
        )

    source_row_count = payload.get("source_row_count")
    expected_source_row_count = spec.get("source_row_count")
    if isinstance(expected_source_row_count, int) and source_row_count != expected_source_row_count:
        findings.append(
            _finding(
                "REAL_PATTERN_SUBSTRATE_BINDINGS_SOURCE_ROW_COUNT_MISMATCH",
                "Real pattern substrate-bindings declared source row count mismatch.",
            )
        )
    if ledger_pattern_ids and isinstance(source_row_count, int) and source_row_count != len(ledger_pattern_ids):
        findings.append(
            _finding(
                "REAL_PATTERN_SUBSTRATE_BINDINGS_LEDGER_COUNT_MISMATCH",
                "Real pattern substrate-bindings source row count does not match the consumed ledger.",
            )
        )

    pattern_bindings = payload.get("pattern_bindings", [])
    if not isinstance(pattern_bindings, list):
        findings.append(
            _finding(
                "REAL_PATTERN_SUBSTRATE_BINDINGS_ROWS_NOT_LIST",
                "Real pattern substrate-bindings pattern_bindings is not a list.",
            )
        )
        pattern_bindings = []

    expected_detailed_binding_count = spec.get("detailed_binding_count")
    if isinstance(expected_detailed_binding_count, int) and len(pattern_bindings) != expected_detailed_binding_count:
        findings.append(
            _finding(
                "REAL_PATTERN_SUBSTRATE_BINDINGS_DETAILED_COUNT_MISMATCH",
                "Real pattern substrate-bindings detailed binding count mismatch.",
            )
        )

    binding_category_counts: Counter[str] = Counter()
    runtime_refs_by_pattern_id: dict[str, str] = {}
    detailed_pattern_ids: list[str] = []
    for row in pattern_bindings:
        if not isinstance(row, dict):
            findings.append(
                _finding(
                    "REAL_PATTERN_SUBSTRATE_BINDINGS_ROW_NOT_OBJECT",
                    "Real pattern substrate-bindings row is not a JSON object.",
                )
            )
            continue
        pattern_id = str(row.get("pattern_id") or "").strip()
        if not pattern_id:
            findings.append(
                _finding(
                    "REAL_PATTERN_SUBSTRATE_BINDINGS_ROW_MISSING_PATTERN_ID",
                    "Real pattern substrate-bindings row lacks pattern_id.",
                )
            )
            continue
        detailed_pattern_ids.append(pattern_id)
        if ledger_pattern_ids and pattern_id not in ledger_pattern_ids:
            findings.append(
                _finding(
                    "REAL_PATTERN_SUBSTRATE_BINDINGS_PATTERN_NOT_IN_LEDGER",
                    "Real pattern substrate-bindings row is not present in the consumed ledger.",
                    pattern_id=pattern_id,
                )
            )
        substrate_bindings = row.get("substrate_bindings")
        if not isinstance(substrate_bindings, dict) or not substrate_bindings:
            findings.append(
                _finding(
                    "REAL_PATTERN_SUBSTRATE_BINDINGS_ROW_EMPTY_BINDINGS",
                    "Real pattern substrate-bindings row lacks concrete substrate_bindings.",
                    pattern_id=pattern_id,
                )
            )
            continue
        for category, refs in substrate_bindings.items():
            if isinstance(refs, list) and refs:
                binding_category_counts[str(category)] += len(refs)
        runtime_refs_by_pattern_id[pattern_id] = f"{source_ref}::pattern_bindings[{pattern_id}]"

    duplicate_detailed_ids = sorted(
        pattern_id for pattern_id, count in Counter(detailed_pattern_ids).items() if count > 1
    )
    for pattern_id in duplicate_detailed_ids:
        findings.append(
            _finding(
                "REAL_PATTERN_SUBSTRATE_BINDINGS_DUPLICATE_PATTERN_ID",
                "Real pattern substrate-bindings duplicates a pattern_id.",
                pattern_id=pattern_id,
            )
        )

    coverage_summary = payload.get("coverage_summary") if isinstance(payload.get("coverage_summary"), dict) else {}
    return {
        "status": PASS if not findings and pattern_bindings else "blocked",
        "source_ref": source_ref,
        "path": binding_path,
        "source_row_count": source_row_count,
        "sha256": digest,
        "expected_sha256": expected_digest,
        "expected_source_row_count": expected_source_row_count,
        "detailed_binding_count": len(pattern_bindings),
        "expected_detailed_binding_count": expected_detailed_binding_count,
        "runtime_refs_by_pattern_id": runtime_refs_by_pattern_id,
        "binding_category_counts": dict(sorted(binding_category_counts.items())),
        "strong_high_authority_count": len(payload.get("strong_high_authority_pattern_ids", []))
        if isinstance(payload.get("strong_high_authority_pattern_ids"), list)
        else 0,
        "load_bearing_cluster_root_count": len(payload.get("load_bearing_cluster_roots", []))
        if isinstance(payload.get("load_bearing_cluster_roots"), list)
        else 0,
        "foundation_combination_route_count": len(payload.get("foundation_combination_routes", []))
        if isinstance(payload.get("foundation_combination_routes"), list)
        else 0,
        "frontier_combination_route_count": len(payload.get("frontier_combination_routes", []))
        if isinstance(payload.get("frontier_combination_routes"), list)
        else 0,
        "coverage_summary": {
            "rows": coverage_summary.get("rows"),
            "grounding_class_counts": coverage_summary.get("grounding_class_counts", {}),
        },
        "detailed_binding_pattern_ids_sample": sorted(detailed_pattern_ids)[:25],
        "findings": findings,
    }


def _real_pattern_route_readiness_projection(
    input_dir: str | Path,
    manifest: dict[str, Any],
    out_dir: str | Path,
    command: str | None,
) -> dict[str, Any] | None:
    spec = manifest.get(REAL_PATTERN_ROUTE_READINESS_BUNDLE_KEY)
    if not isinstance(spec, dict):
        return None

    source_ref = str(spec.get("path") or spec.get("source_ref") or "").strip()
    public_root = _public_root_for_bundle(input_dir)
    route_bundle_path = public_root / source_ref if source_ref else public_root
    if not source_ref or not route_bundle_path.is_dir():
        return {
            "status": "blocked",
            "source_ref": source_ref,
            "path": route_bundle_path,
            "findings": [
                _finding(
                    "REAL_PATTERN_ROUTE_READINESS_BUNDLE_NOT_FOUND",
                    "Real pattern route-readiness bundle path does not resolve inside the public root.",
                )
            ],
            "public_runtime_refs": [],
            "receipt_paths": [],
        }

    result = pattern_route_readiness.validate_route_readiness_bundle(
        route_bundle_path,
        Path(out_dir) / "route_readiness",
        command=command,
    )
    return {
        "status": result["status"],
        "source_ref": source_ref,
        "path": route_bundle_path,
        "bundle_id": result.get("bundle_id"),
        "source_import_class": result.get("source_import_class"),
        "route_readiness_summary": result.get("route_readiness_summary", {}),
        "selection_contract": result.get("selection_contract", {}),
        "source_validation_report_summary": result.get("source_validation_report_summary", {}),
        "source_manifest": result.get("source_manifest", {}),
        "public_runtime_refs": result.get("public_runtime_refs", []),
        "receipt_paths": result.get("receipt_paths", []),
        "findings": result.get("route_readiness_report", {}).get("findings", []),
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
    extra_paths = [
        str(path)
        for path in validation_result.get("receipt_paths", [])
        if str(path) and str(path) != receipt_path
    ]
    payload["receipt_paths"] = [receipt_path, *extra_paths]
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


def validate_substrate_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_bundle(input_path)
    freshness_basis = _substrate_bundle_freshness_basis(input_path, public_root=public_root)
    freshness_digest = _json_digest(freshness_basis)
    if reuse_fresh_receipt:
        cached = _fresh_substrate_bundle_receipt(out_dir, freshness_digest=freshness_digest)
        if cached is not None:
            return cached

    bundle = load_pattern_binding_substrate_bundle(input_path)
    manifest = bundle["bundle_manifest"]
    source_imports = validate_source_module_imports(input_path, public_root=public_root)
    real_ledger_projection = _real_pattern_ledger_projection(input_path, manifest)
    uses_real_ledger = real_ledger_projection is not None and real_ledger_projection["status"] == PASS
    ledger_pattern_ids = (
        {str(row["pattern_id"]) for row in real_ledger_projection["pattern_rows"]}
        if real_ledger_projection is not None
        else set()
    )
    substrate_binding_projection = _real_pattern_substrate_bindings_projection(
        input_path,
        manifest,
        ledger_pattern_ids,
    )
    uses_substrate_bindings = (
        substrate_binding_projection is not None
        and substrate_binding_projection["status"] == PASS
    )
    if uses_real_ledger and uses_substrate_bindings:
        real_ledger_projection = _real_pattern_ledger_projection(
            input_path,
            manifest,
            substrate_binding_projection["runtime_refs_by_pattern_id"],
        )
    route_readiness_projection = _real_pattern_route_readiness_projection(
        input_path,
        manifest,
        out_dir,
        command,
    )
    uses_route_readiness = (
        route_readiness_projection is not None
        and route_readiness_projection["status"] == PASS
    )
    patterns = real_ledger_projection["pattern_rows"] if uses_real_ledger else bundle["patterns"]
    source_capsules = real_ledger_projection["source_capsules"] if uses_real_ledger else bundle["source_capsules"]
    input_paths = [Path(path) for path in bundle["input_paths"].values()]
    if real_ledger_projection is not None and real_ledger_projection["path"].is_file():
        input_paths.append(real_ledger_projection["path"])
    if substrate_binding_projection is not None and substrate_binding_projection["path"].is_file():
        input_paths.append(substrate_binding_projection["path"])
    input_paths.extend(_source_artifact_paths(input_path, public_root=public_root))
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
    all_findings.extend(source_imports["findings"])
    if real_ledger_projection is not None:
        all_findings.extend(real_ledger_projection["findings"])
    if substrate_binding_projection is not None:
        all_findings.extend(substrate_binding_projection["findings"])
    route_readiness_findings = (
        route_readiness_projection.get("findings", [])
        if route_readiness_projection is not None
        else []
    )
    route_readiness_error_rules = sorted(
        {
            str(finding.get("rule") or finding.get("error_code") or "")
            for finding in route_readiness_findings
            if isinstance(finding, dict)
            and (
                finding.get("severity") == "error"
                or finding.get("error_code")
            )
        }
        - {""}
    )

    error_codes = sorted({finding["error_code"] for finding in all_findings})
    accepted_rows = binding_result["accepted_rows"]
    bundle_id = str(manifest.get("bundle_id") or "pattern_binding_exported_substrate_bundle")
    status = (
        PASS
        if scan_result["status"] == PASS
        and not all_findings
        and not route_readiness_error_rules
        and accepted_rows
        and source_imports["status"] == PASS
        and (route_readiness_projection is None or uses_route_readiness)
        else "blocked"
    )
    source_capsule_receipt = _source_capsule_receipt(accepted_rows, source_capsules)
    truth_accounting = _substrate_bundle_truth_accounting(manifest, accepted_rows)
    source_open_body_imports = _source_open_body_import_summary(source_imports)
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
            "card_schema_version": CARD_SCHEMA_VERSION,
            "freshness_basis": freshness_basis,
            "freshness_digest": freshness_digest,
            "freshness_status": "current",
            "receipt_reused": False,
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
            "route_readiness_error_rules": route_readiness_error_rules,
            "secret_exclusion_scan": scan_result,
            "body_in_receipt": False,
            "real_runtime_receipt": status == PASS,
            "synthetic_receipt_standin_allowed": False,
            "source_module_imports": {
                "status": source_imports["status"],
                "source_module_manifest_ref": source_imports["source_module_manifest_ref"],
                "module_count": source_imports["module_count"],
                "modules": source_imports["modules"],
                "findings": source_imports["findings"],
            },
            "source_open_body_imports": source_open_body_imports,
            "body_material_status": source_open_body_imports["body_material_status"],
            "body_copied_material_count": source_open_body_imports["body_material_count"],
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
            "real_pattern_substrate_bindings_consumed": uses_substrate_bindings,
            "real_pattern_substrate_bindings_source": (
                {
                    "status": substrate_binding_projection["status"],
                    "source_ref": substrate_binding_projection["source_ref"],
                    "source_row_count": substrate_binding_projection["source_row_count"],
                    "sha256": substrate_binding_projection["sha256"],
                    "expected_sha256": substrate_binding_projection["expected_sha256"],
                    "expected_source_row_count": substrate_binding_projection["expected_source_row_count"],
                    "detailed_binding_count": substrate_binding_projection["detailed_binding_count"],
                    "expected_detailed_binding_count": substrate_binding_projection[
                        "expected_detailed_binding_count"
                    ],
                    "binding_category_counts": substrate_binding_projection["binding_category_counts"],
                    "strong_high_authority_count": substrate_binding_projection[
                        "strong_high_authority_count"
                    ],
                    "load_bearing_cluster_root_count": substrate_binding_projection[
                        "load_bearing_cluster_root_count"
                    ],
                    "foundation_combination_route_count": substrate_binding_projection[
                        "foundation_combination_route_count"
                    ],
                    "frontier_combination_route_count": substrate_binding_projection[
                        "frontier_combination_route_count"
                    ],
                    "coverage_summary": substrate_binding_projection["coverage_summary"],
                    "detailed_binding_pattern_ids_sample": substrate_binding_projection[
                        "detailed_binding_pattern_ids_sample"
                    ],
                }
                if substrate_binding_projection is not None
                else None
            ),
            "real_pattern_route_readiness_consumed": uses_route_readiness,
            "real_pattern_route_readiness_source": (
                {
                    "status": route_readiness_projection["status"],
                    "source_ref": route_readiness_projection["source_ref"],
                    "bundle_id": route_readiness_projection.get("bundle_id"),
                    "source_import_class": route_readiness_projection.get("source_import_class"),
                    "route_readiness_summary": route_readiness_projection.get(
                        "route_readiness_summary", {}
                    ),
                    "source_validation_report_summary": route_readiness_projection.get(
                        "source_validation_report_summary", {}
                    ),
                    "selection_contract": route_readiness_projection.get("selection_contract", {}),
                    "source_manifest": route_readiness_projection.get("source_manifest", {}),
                    "receipt_paths": route_readiness_projection.get("receipt_paths", []),
                }
                if route_readiness_projection is not None
                else None
            ),
            "legacy_runtime_metadata_row_count": len(bundle["patterns"]),
            "legacy_runtime_metadata_only_row_count": legacy_runtime_metadata_only_count,
            "public_runtime_refs": sorted(
                set(
                    _source_capsule_runtime_refs(
                        sorted({ref for row in accepted_rows for ref in _pattern_source_refs(row)}),
                        source_capsules,
                    )
                    + (
                        route_readiness_projection.get("public_runtime_refs", [])
                        if route_readiness_projection is not None
                        else []
                    )
                )
            ),
            "authority_ceiling": {
                "status": PASS,
                "authority_ceiling": AUTHORITY_CEILING,
                "runtime_claim": (
                    "real pattern-ledger, substrate-binding, and route-readiness validation"
                    if uses_substrate_bindings and uses_route_readiness
                    else "real pattern-ledger and substrate-binding validation"
                    if uses_substrate_bindings
                    else "real pattern-ledger binding validation"
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
                "An exported substrate bundle validates public pattern-ledger bindings "
                "and route-readiness overlays. It does not inline secret, provider, "
                "operator, or credential-equivalent bodies, make mined rows standalone "
                "leaves, or prove release readiness."
            ),
            "receipt_paths": (
                route_readiness_projection.get("receipt_paths", [])
                if route_readiness_projection is not None
                else []
            ),
        }
    )
    receipt_path = _write_substrate_bundle_receipt(out_dir, result)
    result["receipt_paths"] = [receipt_path] + (
        route_readiness_projection.get("receipt_paths", [])
        if route_readiness_projection is not None
        else []
    )
    return result


def _scan_card(scan: object) -> dict[str, Any]:
    if not isinstance(scan, dict):
        return {
            "status": None,
            "blocking_hit_count": 0,
            "hit_count": 0,
            "body_in_receipt": None,
        }
    hits = scan.get("hits", [])
    return {
        "status": scan.get("status"),
        "blocking_hit_count": scan.get("blocking_hit_count", 0),
        "hit_count": len(hits) if isinstance(hits, list) else 0,
        "body_in_receipt": scan.get("body_in_receipt"),
    }


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    receipt_paths = [
        Path(str(path)).name if Path(str(path)).is_absolute() else str(path)
        for path in result.get("receipt_paths", [])
    ]
    common = {
        "schema_version": CARD_SCHEMA_VERSION,
        "organ_id": result.get("organ_id", ORGAN_ID),
        "fixture_id": result.get("fixture_id"),
        "status": result.get("status"),
        "input_mode": result.get("input_mode", "fixture_regression"),
        "command": result.get("command"),
        "receipt_paths": receipt_paths,
        "receipt_reused": bool(result.get("receipt_reused")),
        "freshness_status": result.get("freshness_status", "rebuilt"),
    }
    if result.get("input_mode") == "exported_substrate_bundle":
        source_open = result.get("source_open_body_imports", {})
        if not isinstance(source_open, dict):
            source_open = {}
        source_modules = result.get("source_module_imports", {})
        if not isinstance(source_modules, dict):
            source_modules = {}
        route_readiness = result.get("real_pattern_route_readiness_source", {})
        if not isinstance(route_readiness, dict):
            route_readiness = {}
        route_summary = route_readiness.get("route_readiness_summary", {})
        if not isinstance(route_summary, dict):
            route_summary = {}
        return {
            **common,
            "bundle_id": result.get("bundle_id"),
            "accepted_count": result.get("accepted_count", 0),
            "real_substrate_progress_count": result.get("real_substrate_progress_count", 0),
            "runtime_metadata_only_row_count": result.get("runtime_metadata_only_row_count", 0),
            "legacy_runtime_metadata_row_count": result.get("legacy_runtime_metadata_row_count", 0),
            "real_pattern_ledger_consumed": result.get("real_pattern_ledger_consumed", False),
            "real_pattern_substrate_bindings_consumed": result.get(
                "real_pattern_substrate_bindings_consumed", False
            ),
            "real_pattern_route_readiness_consumed": result.get(
                "real_pattern_route_readiness_consumed", False
            ),
            "source_module_count": source_modules.get("module_count", 0),
            "body_copied_material_count": result.get("body_copied_material_count", 0),
            "source_open_body_import_summary": {
                "status": source_open.get("status"),
                "body_material_count": source_open.get("body_material_count", 0),
                "material_classes": source_open.get("material_classes", []),
                "body_in_receipt": source_open.get("body_in_receipt", False),
            },
            "route_readiness_summary": {
                "ledger_pattern_count": route_summary.get("ledger_pattern_count"),
                "route_card_count": route_summary.get("route_card_count"),
                "fixture_spec_count": route_summary.get("fixture_spec_count"),
                "standalone_pattern_leaf_candidate_count": route_summary.get(
                    "standalone_pattern_leaf_candidate_count"
                ),
            },
            "public_runtime_ref_count": len(result.get("public_runtime_refs", []))
            if isinstance(result.get("public_runtime_refs"), list)
            else 0,
            "secret_exclusion_scan": _scan_card(result.get("secret_exclusion_scan")),
            "error_code_count": len(result.get("error_codes", [])),
            "error_codes": result.get("error_codes", []),
            "finding_count": len(result.get("findings", [])),
            "freshness_digest": result.get("freshness_digest"),
            "omitted_full_payload_keys": [
                key for key in CARD_OMITTED_FULL_PAYLOAD_KEYS if key in result
            ],
        }

    expected_cases = result.get("expected_negative_cases", {})
    observed_cases = result.get("observed_negative_cases", {})
    return {
        **common,
        "bundle_id": result.get("bundle_id"),
        "expected_negative_case_count": len(expected_cases)
        if isinstance(expected_cases, dict)
        else 0,
        "observed_negative_case_count": len(observed_cases)
        if isinstance(observed_cases, dict)
        else 0,
        "missing_negative_case_count": len(result.get("missing_negative_cases", [])),
        "accepted_count": result.get("accepted_count", 0),
        "rejected_count": result.get("rejected_count", 0),
        "duplicate_pattern_count": len(result.get("duplicate_pattern_ids", [])),
        "error_code_count": len(result.get("error_codes", [])),
        "secret_exclusion_scan": _scan_card(result.get("secret_exclusion_scan")),
        "omitted_full_payload_keys": [
            key for key in CARD_OMITTED_FULL_PAYLOAD_KEYS if key in result
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command_name")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--out", required=True)
    validate_parser.add_argument("--card", action="store_true")
    bundle_parser = subparsers.add_parser("validate-substrate-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    route_readiness_parser = subparsers.add_parser("validate-route-readiness-bundle")
    route_readiness_parser.add_argument("--input", required=True)
    route_readiness_parser.add_argument("--out", required=True)
    route_readiness_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    if args.command_name == "validate":
        command = (
            "python -m microcosm_core.organs.pattern_binding_contract "
            f"validate --input {args.input} --out {args.out}"
        )
        if args.card:
            command += " --card"
        result = validate(args.input, args.out, command=command)
    elif args.command_name == "validate-substrate-bundle":
        command = (
            "python -m microcosm_core.organs.pattern_binding_contract "
            f"validate-substrate-bundle --input {args.input} --out {args.out}"
        )
        if args.card:
            command += " --card"
        result = validate_substrate_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    elif args.command_name == "validate-route-readiness-bundle":
        command = (
            "python -m microcosm_core.organs.pattern_binding_contract "
            f"validate-route-readiness-bundle --input {args.input} --out {args.out}"
        )
        if args.card:
            command += " --card"
        result = pattern_route_readiness.validate_route_readiness_bundle(
            args.input,
            args.out,
            command=command,
        )
    else:
        parser.error("expected subcommand: validate, validate-substrate-bundle, or validate-route-readiness-bundle")
    if args.card:
        print(json.dumps(result_card(result), ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
