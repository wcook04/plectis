from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "lean_std_premise_index"
FIXTURE_ID = "first_wave.lean_std_premise_index"
VALIDATOR_ID = "validator.microcosm.organs.lean_std_premise_index"

CARD_SCHEMA_VERSION = "lean_std_premise_index_command_card_v1"
RESULT_NAME = "lean_std_premise_index_result.json"
BOARD_NAME = "lean_std_premise_index_board.json"
VALIDATION_RECEIPT_NAME = "lean_std_premise_index_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/lean_std_premise_index_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_lean_std_premise_index_bundle_validation_result.json"

SOURCE_PATTERN_IDS = [
    "lean_std_toolchain_premise_index",
    "closed_premise_admission_boundary",
    "formal_math_premise_retrieval",
]
SOURCE_REFS = [
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_index.json",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/problem_source_manifest.json",
    "microcosm-substrate/src/microcosm_core/organs/formal_math_premise_retrieval.py",
]
SOURCE_SHA256 = "sha256:c78b176388a5e81bd8a785950e7db0c9a65fd38e556515134146163b48604df1"
PUBLIC_LEAN_TOOLCHAIN_PREFIX = "lean-toolchain://leanprover/lean4/v4.29.1/src/lean/"
HASH_CHUNK_SIZE = 1024 * 1024

INPUT_NAMES = ("projection_protocol.json", "premise_index.json", "index_policy.json")
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
NEGATIVE_INPUT_NAMES = (
    "mathlib_premise_forbidden.json",
    "proof_body_leakage.json",
    "oracle_needed_ids_leakage.json",
    "test_split_tuning_attempt.json",
    "namespace_without_source_ref.json",
)

EXPECTED_NEGATIVE_CASES = {
    "mathlib_premise_forbidden": ["LEAN_STD_INDEX_MATHLIB_FORBIDDEN"],
    "proof_body_leakage": ["LEAN_STD_INDEX_PROOF_BODY_FORBIDDEN"],
    "oracle_needed_ids_leakage": ["LEAN_STD_INDEX_ORACLE_IDS_FORBIDDEN"],
    "test_split_tuning_attempt": ["LEAN_STD_INDEX_TEST_SPLIT_TUNING_FORBIDDEN"],
    "namespace_without_source_ref": ["LEAN_STD_INDEX_SOURCE_REF_REQUIRED"],
}

REQUIRED_NAMESPACES = {"Nat", "Bool", "List", "Iff"}
ALLOWED_SPLITS = {"train", "dev", "test"}
FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "provider_payload_body",
    "oracle_needed_premise_ids",
    "private_source_body",
)
OVERCLAIM_KEYS = (
    "mathlib_allowed",
    "proof_bodies_allowed",
    "oracle_needed_ids_public",
    "test_split_tuning_authorized",
    "provider_calls_authorized",
    "release_authorized",
)
SOURCE_BODY_MATERIAL_CLASSES = {
    "public_lean_std_premise_descriptor_index",
    "public_macro_receipt_body",
    "public_macro_pattern_body",
}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "lean_std_premise_index_copied_macro_descriptor_index_only",
    "index_authority": "copied_non_secret_lean_std_descriptor_index_only",
    "mathlib_allowed": False,
    "formal_proof_authority": False,
    "proof_bodies_allowed": False,
    "oracle_needed_ids_public": False,
    "test_split_tuning_authorized": False,
    "provider_calls_authorized": False,
    "lean_lake_execution_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "The Lean/Std premise index validates copied non-secret Lean/Std premise "
    "descriptors imported from the macro premise-index run with public path "
    "normalization. It does not import Mathlib, run Lean or Lake, expose proof "
    "bodies or oracle-needed premise ids, tune on test split truth, call providers, "
    "prove theorem correctness, or authorize release."
)
BODY_MATERIAL_STATUS = "copied_non_secret_macro_body_with_provenance"
BODY_MATERIAL_CONTRACT = {
    "status": PASS,
    "body_material_status": BODY_MATERIAL_STATUS,
    "copied_material_required": True,
    "source_sha256": SOURCE_SHA256,
    "secret_exclusion_scan_field": "secret_exclusion_scan",
    "excluded_body_classes": [
        "proof_body",
        "ground_truth_proof",
        "provider_payload_body",
        "oracle_needed_premise_ids",
        "private_source_body",
    ],
}


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
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names]


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    payloads = {Path(name).stem: read_json_strict(input_dir / name) for name in names}
    bundle_manifest = input_dir / "bundle_manifest.json"
    if bundle_manifest.is_file():
        payloads["bundle_manifest"] = read_json_strict(bundle_manifest)
    source_module_manifest = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if source_module_manifest.is_file():
        payloads["source_module_manifest"] = read_json_strict(source_module_manifest)
    return payloads


def _sha256_hex(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line_count(path: Path) -> int:
    line_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_count, _line in enumerate(handle, start=1):
            pass
    return line_count or 1


def _strip_sha256_prefix(value: object) -> str:
    text = str(value or "")
    return text.removeprefix("sha256:")


def _manifest_rows(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key in ("modules", "source_faithful_modules"):
        rows.extend(_rows(payload, key))
    return rows


def _target_refs(row: dict[str, Any]) -> list[str]:
    refs = _strings(row.get("target_refs"))
    target_ref = row.get("target_ref")
    if isinstance(target_ref, str) and target_ref:
        refs.append(target_ref)
    path = row.get("path")
    if isinstance(path, str) and path:
        refs.append(path)
    deduped: list[str] = []
    for ref in refs:
        if ref not in deduped:
            deduped.append(ref)
    return deduped


def _candidate_target_paths(ref: str, *, input_dir: Path, public_root: Path) -> list[Path]:
    path = Path(ref)
    if path.is_absolute():
        return [path]
    if ref.startswith("microcosm-substrate/"):
        return [public_root / Path(*path.parts[1:])]
    if ref.startswith("source_modules/"):
        return [input_dir / path]
    return [input_dir / path, public_root / path]


def _resolve_target_path(
    row: dict[str, Any],
    *,
    input_dir: Path,
    public_root: Path,
) -> Path | None:
    input_root = input_dir.resolve(strict=False)
    fallback: Path | None = None
    for ref in _target_refs(row):
        for candidate in _candidate_target_paths(ref, input_dir=input_dir, public_root=public_root):
            if fallback is None:
                fallback = candidate
            if candidate.is_file() and candidate.resolve(strict=False).is_relative_to(input_root):
                return candidate
    for ref in _target_refs(row):
        for candidate in _candidate_target_paths(ref, input_dir=input_dir, public_root=public_root):
            if candidate.is_file():
                return candidate
    return fallback


def _source_module_target_paths(
    payload: object,
    *,
    input_dir: Path,
    public_root: Path,
) -> list[Path]:
    paths: list[Path] = []
    for row in _manifest_rows(payload):
        target = _resolve_target_path(row, input_dir=input_dir, public_root=public_root)
        if target is not None and target.is_file():
            paths.append(target)
    return paths


def _source_module_manifest_result(
    payload: object,
    *,
    input_dir: Path,
    public_root: Path,
    require_manifest: bool,
) -> dict[str, Any]:
    manifest_ref = _display(input_dir / SOURCE_MODULE_MANIFEST_NAME, public_root=public_root)
    if not isinstance(payload, dict):
        status = "blocked" if require_manifest else "not_present"
        findings = []
        if require_manifest:
            findings.append(
                _finding(
                    "LEAN_STD_INDEX_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported Lean/Std premise-index bundle must include a source module manifest.",
                    case_id="source_module_manifest",
                    subject_id=manifest_ref,
                    subject_kind="source_module_manifest",
                )
            )
        return {
            "status": status,
            "findings": findings,
            "source_module_manifest_ref": manifest_ref,
            "source_module_count": 0,
            "verified_source_module_count": 0,
            "source_module_imports": [],
        }

    findings: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    rows = _manifest_rows(payload)
    declared_count = payload.get("module_count")
    if isinstance(declared_count, int) and declared_count != len(rows):
        findings.append(
            _finding(
                "LEAN_STD_INDEX_SOURCE_MODULE_COUNT_MISMATCH",
                "Source module manifest module_count must equal the number of module rows.",
                case_id="source_module_manifest",
                subject_id=str(payload.get("manifest_id") or "source_module_manifest"),
                subject_kind="source_module_manifest",
            )
        )
    for row in rows:
        module_id = str(row.get("module_id") or "")
        material_class = str(row.get("material_class") or "")
        target = _resolve_target_path(row, input_dir=input_dir, public_root=public_root)
        if not module_id:
            findings.append(
                _finding(
                    "LEAN_STD_INDEX_SOURCE_MODULE_ID_REQUIRED",
                    "Every source module import row must carry a stable module_id.",
                    case_id="source_module_manifest",
                    subject_id="missing_module_id",
                    subject_kind="source_module",
                )
            )
            continue
        if material_class not in SOURCE_BODY_MATERIAL_CLASSES:
            findings.append(
                _finding(
                    "LEAN_STD_INDEX_SOURCE_MODULE_CLASS_INVALID",
                    "Source module material_class must be one of the public body material classes.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "LEAN_STD_INDEX_SOURCE_MODULE_BODY_POLICY_INVALID",
                    "Source module imports must be copied body files while receipts keep body_in_receipt false.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if target is None or not target.is_file():
            findings.append(
                _finding(
                    "LEAN_STD_INDEX_SOURCE_MODULE_TARGET_MISSING",
                    "Source module import target file is missing.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
            continue
        digest = _sha256_hex(target)
        expected_digest = _strip_sha256_prefix(row.get("target_sha256") or row.get("sha256"))
        if expected_digest and digest != expected_digest:
            findings.append(
                _finding(
                    "LEAN_STD_INDEX_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module target file digest does not match the manifest.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        lines = _line_count(target)
        bytes_count = target.stat().st_size
        expected_lines = row.get("target_line_count", row.get("line_count"))
        expected_bytes = row.get("target_byte_count", row.get("byte_count"))
        if isinstance(expected_lines, int) and lines != expected_lines:
            findings.append(
                _finding(
                    "LEAN_STD_INDEX_SOURCE_MODULE_LINE_COUNT_MISMATCH",
                    "Source module target file line count does not match the manifest.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if isinstance(expected_bytes, int) and bytes_count != expected_bytes:
            findings.append(
                _finding(
                    "LEAN_STD_INDEX_SOURCE_MODULE_BYTE_COUNT_MISMATCH",
                    "Source module target file byte count does not match the manifest.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        imports.append(
            {
                "module_id": module_id,
                "material_class": material_class,
                "source_ref": row.get("source_ref"),
                "target_ref": _display(target, public_root=public_root),
                "target_sha256": f"sha256:{digest}",
                "target_line_count": lines,
                "target_byte_count": bytes_count,
                "body_copied": row.get("body_copied") is True,
                "body_in_receipt": row.get("body_in_receipt") is True,
                "source_to_target_relation": row.get("source_to_target_relation"),
            }
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "source_module_manifest_ref": manifest_ref,
        "source_module_count": len(rows),
        "verified_source_module_count": len(imports) if not findings else 0,
        "source_module_imports": imports,
    }


def _walk_dicts(value: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        rows.append(value)
        for child in value.values():
            rows.extend(_walk_dicts(child))
    elif isinstance(value, list):
        for child in value:
            rows.extend(_walk_dicts(child))
    return rows


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_material_status": "forbidden_body_excluded",
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    observed[case_id].add(code)


def _has_mathlib(value: object) -> bool:
    if isinstance(value, str):
        return "mathlib" in value.lower()
    if isinstance(value, dict):
        return any(_has_mathlib(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_mathlib(child) for child in value)
    return False


def _entry_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "premises")
    if rows:
        return rows
    return _rows(payload, "entries")


def _forbidden_keys(row: dict[str, Any]) -> list[str]:
    return sorted(key for key in FORBIDDEN_BODY_KEYS if key in row)


def _validate_entries(
    payload: object,
    *,
    case_id: str,
    require_density: bool,
) -> dict[str, Any]:
    entries = _entry_rows(payload)
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    namespaces: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    seen_ids: list[str] = []
    for row in entries:
        premise_id = str(row.get("premise_id") or row.get("declaration_name") or "premise")
        seen_ids.append(premise_id)
        namespace = str(row.get("namespace") or "")
        if namespace:
            namespaces[namespace] += 1
        source_ref = str(row.get("source_ref") or "")
        if not source_ref or not (
            source_ref.startswith("Init/")
            or source_ref.startswith(f"{PUBLIC_LEAN_TOOLCHAIN_PREFIX}Init/")
        ):
            _record(
                findings,
                observed,
                "LEAN_STD_INDEX_SOURCE_REF_REQUIRED",
                "Every public Lean/Std premise row must cite an Init/ Lean toolchain source ref.",
                case_id=case_id,
                subject_id=premise_id,
                subject_kind="source_ref",
            )
        if require_density and row.get("body_copied") is not True:
            _record(
                findings,
                observed,
                "LEAN_STD_INDEX_COPIED_BODY_PROVENANCE_REQUIRED",
                "Positive Lean/Std premise rows must be copied non-secret macro descriptors.",
                case_id=case_id,
                subject_id=premise_id,
                subject_kind="copied_material",
            )
        if _has_mathlib(row):
            _record(
                findings,
                observed,
                "LEAN_STD_INDEX_MATHLIB_FORBIDDEN",
                "The public Lean/Std premise index must not include Mathlib refs.",
                case_id=case_id,
                subject_id=premise_id,
                subject_kind="premise",
            )
        forbidden = _forbidden_keys(row)
        if forbidden:
            _record(
                findings,
                observed,
                "LEAN_STD_INDEX_PROOF_BODY_FORBIDDEN",
                "Public premise rows must not include proof bodies or private payload bodies.",
                case_id=case_id,
                subject_id=premise_id,
                subject_kind="premise",
            )
        if "oracle_needed_premise_ids" in row:
            _record(
                findings,
                observed,
                "LEAN_STD_INDEX_ORACLE_IDS_FORBIDDEN",
                "Oracle-needed premise ids stay out of public premise-index inputs.",
                case_id=case_id,
                subject_id=premise_id,
                subject_kind="oracle_ids",
            )
        retrieval_terms = _strings(row.get("retrieval_terms"))
        if not retrieval_terms:
            _record(
                findings,
                observed,
                "LEAN_STD_INDEX_RETRIEVAL_TERMS_REQUIRED",
                "Every public Lean/Std premise row must carry retrieval terms.",
                case_id=case_id,
                subject_id=premise_id,
                subject_kind="retrieval_terms",
            )
        splits = set(_strings(row.get("allowed_for_split")))
        split_counts.update(splits)
        if not splits or not splits <= ALLOWED_SPLITS:
            _record(
                findings,
                observed,
                "LEAN_STD_INDEX_SPLIT_BOUNDARY_INVALID",
                "allowed_for_split must be a nonempty subset of train/dev/test.",
                case_id=case_id,
                subject_id=premise_id,
                subject_kind="split_policy",
            )
    duplicate_ids = sorted(pid for pid in set(seen_ids) if seen_ids.count(pid) > 1)
    for premise_id in duplicate_ids:
        _record(
            findings,
            observed,
            "LEAN_STD_INDEX_DUPLICATE_PREMISE_ID",
            "Premise ids must be unique inside the closed public index.",
            case_id=case_id,
            subject_id=premise_id,
            subject_kind="premise_id",
        )
    if require_density:
        missing_namespaces = sorted(REQUIRED_NAMESPACES - set(namespaces))
        if len(entries) < 10:
            _record(
                findings,
                observed,
                "LEAN_STD_INDEX_DENSITY_MISSING",
                "The public Lean/Std premise index must carry at least ten entries.",
                case_id=case_id,
                subject_id="premise_index",
                subject_kind="index_density",
            )
        for namespace in missing_namespaces:
            _record(
                findings,
                observed,
                "LEAN_STD_INDEX_NAMESPACE_MISSING",
                "The public Lean/Std premise index must cover Nat, Bool, List, and Iff.",
                case_id=case_id,
                subject_id=namespace,
                subject_kind="namespace",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(values) for key, values in sorted(observed.items())
        },
        "entry_count": len(entries),
        "namespace_counts": dict(sorted(namespaces.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "premise_ids": sorted(seen_ids),
    }


def _validate_policy(payload: object, *, case_id: str) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for key in OVERCLAIM_KEYS:
        if policy.get(key) is True:
            code = "LEAN_STD_INDEX_TEST_SPLIT_TUNING_FORBIDDEN" if key == "test_split_tuning_authorized" else "LEAN_STD_INDEX_AUTHORITY_OVERCLAIM"
            _record(
                findings,
                observed,
                code,
                "Lean/Std premise-index policy must keep authority ceilings false.",
                case_id=case_id,
                subject_id=key,
                subject_kind="policy",
            )
    if policy.get("closed_index_only") is not True:
        _record(
            findings,
            observed,
            "LEAN_STD_INDEX_CLOSED_SET_REQUIRED",
            "The public premise index must be declared as a closed set.",
            case_id=case_id,
            subject_id="closed_index_only",
            subject_kind="policy",
        )
    allowed = set(_strings(policy.get("allowed_splits")))
    if allowed != ALLOWED_SPLITS:
        _record(
            findings,
            observed,
            "LEAN_STD_INDEX_SPLIT_POLICY_MISSING",
            "Policy must explicitly name train/dev/test as the only public split labels.",
            case_id=case_id,
            subject_id="allowed_splits",
            subject_kind="policy",
        )
    return {
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(values) for key, values in sorted(observed.items())
        },
    }


def _validate_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    public_runtime_refs = _strings(protocol.get("public_runtime_refs"))
    receipts = _strings(protocol.get("projection_receipt_refs"))
    source_patterns = _strings(protocol.get("source_pattern_ids"))
    copied_material = _rows(protocol, "copied_material")
    omitted = _rows(protocol, "omitted_material")
    findings: list[dict[str, Any]] = []
    body_copied_material = [
        row
        for row in copied_material
        if row.get("body_copied") is True
        and row.get("source_ref")
        and row.get("source_sha256")
        and _strings(row.get("target_refs"))
        and _strings(row.get("validation_refs"))
    ]
    stale_body_false = [row for row in copied_material if row.get("body_copied") is False]
    if len(source_refs) < 3 or len(public_runtime_refs) < 3 or len(receipts) < 1:
        findings.append(
            _finding(
                "LEAN_STD_INDEX_PROTOCOL_DENSITY_MISSING",
                "Lean/Std premise index must cite macro refs, public runtime refs, and projection receipts.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    if not body_copied_material or stale_body_false:
        findings.append(
            _finding(
                "LEAN_STD_INDEX_REAL_SUBSTRATE_IMPORT_MISSING",
                "Lean/Std premise index must copy at least one non-secret macro body with source, target, digest, and validation refs; stale body_copied=false rows are blocked.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for row in omitted:
        if not row.get("omission_receipt_ref"):
            findings.append(
                _finding(
                    "LEAN_STD_INDEX_OMISSION_RECEIPT_MISSING",
                    "Omitted formal-math material must carry an omission receipt.",
                    case_id="projection_protocol_floor",
                    subject_id=str(row.get("material_id") or "omitted_material"),
                    subject_kind="projection_protocol",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_patterns,
        "projection_receipt_refs": receipts,
        "public_runtime_refs": public_runtime_refs,
        "copied_material": copied_material,
        "copied_material_count": len(copied_material),
        "body_copied_material_count": len(body_copied_material),
        "omitted_material_count": len(omitted),
    }


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )


def _secret_exclusion_scan(scan: dict[str, Any]) -> dict[str, Any]:
    payload = dict(scan)
    payload.pop("body_redacted", None)
    payload.pop("forbidden_output_fields", None)
    payload["excluded_output_field_count"] = 2
    payload["excluded_output_field_labels_omitted"] = True
    payload["body_material_status"] = "secret_exclusion_scan_no_payload_body_export"
    hits: list[dict[str, Any]] = []
    for hit in payload.get("hits", []):
        if not isinstance(hit, dict):
            continue
        cleaned = dict(hit)
        cleaned.pop("body_redacted", None)
        cleaned["body_material_status"] = "forbidden_material_excluded"
        hits.append(cleaned)
    payload["hits"] = hits
    return payload


def _scan_inputs(
    input_dir: Path,
    *,
    include_negative: bool,
    source_module_manifest: object,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    paths = _input_paths(input_dir, include_negative=include_negative)
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if manifest_path.is_file():
        paths.append(manifest_path)
    paths.extend(
        _source_module_target_paths(
            source_module_manifest,
            input_dir=input_dir,
            public_root=public_root,
        )
    )
    return _secret_exclusion_scan(
        scan_paths(
            paths,
            forbidden_classes=policy,
            display_root=public_root,
        )
    )


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    protocol = _validate_protocol(payloads.get("projection_protocol"))
    index = _validate_entries(
        payloads.get("premise_index"),
        case_id="positive_premise_index",
        require_density=True,
    )
    policy = _validate_policy(payloads.get("index_policy"), case_id="positive_policy")
    negative_results: list[dict[str, Any]] = []
    if include_negative:
        for name in NEGATIVE_INPUT_NAMES:
            stem = Path(name).stem
            payload = payloads.get(stem)
            entry_result = _validate_entries(payload, case_id=stem, require_density=False)
            policy_result = _validate_policy(payload, case_id=stem)
            negative_results.extend([entry_result, policy_result])
    observed = _merge_observed(*negative_results)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = [
        case_id
        for case_id, codes in expected.items()
        if not set(codes) <= set(observed.get(case_id, []))
    ]
    source_module_manifest = _source_module_manifest_result(
        payloads.get("source_module_manifest"),
        input_dir=input_dir,
        public_root=public_root,
        require_manifest=input_mode == "exported_lean_std_premise_index_bundle",
    )
    positive_findings = _merge_findings(protocol, index, policy, source_module_manifest)
    negative_findings = _merge_findings(*negative_results)
    error_codes = sorted({row["error_code"] for row in positive_findings + negative_findings})
    secret_scan = _scan_inputs(
        input_dir,
        include_negative=include_negative,
        source_module_manifest=payloads.get("source_module_manifest"),
    )
    bundle_manifest = payloads.get("bundle_manifest", {})
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    status = (
        PASS
        if not positive_findings
        and not missing
        and not secret_scan["blocking_hit_count"]
        else "blocked"
    )
    return {
        "schema_version": "lean_std_premise_index_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": protocol.get("source_refs", []),
        "protocol_id": protocol.get("protocol_id"),
        "projection_receipt_refs": protocol.get("projection_receipt_refs", []),
        "public_runtime_refs": protocol.get("public_runtime_refs", []),
        "copied_material": protocol.get("copied_material", []),
        "copied_material_count": protocol.get("copied_material_count", 0),
        "body_copied_material_count": max(
            protocol.get("body_copied_material_count", 0),
            source_module_manifest.get("verified_source_module_count", 0),
        ),
        "omitted_material_count": protocol.get("omitted_material_count", 0),
        "source_module_manifest_status": source_module_manifest.get("status"),
        "source_module_manifest_ref": source_module_manifest.get("source_module_manifest_ref"),
        "source_module_count": source_module_manifest.get("source_module_count", 0),
        "verified_source_module_count": source_module_manifest.get(
            "verified_source_module_count",
            0,
        ),
        "source_module_imports": source_module_manifest.get("source_module_imports", []),
        "expected_negative_cases": expected,
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": positive_findings + negative_findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_material_contract": BODY_MATERIAL_CONTRACT,
        "body_material_status": BODY_MATERIAL_STATUS,
        "premise_count": index["entry_count"],
        "namespace_counts": index["namespace_counts"],
        "split_counts": index["split_counts"],
        "premise_ids": index["premise_ids"],
        "closed_index_only": True,
    }


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    return [_display(path, public_root=public_root) for path in paths.values()]


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "created_at": result["created_at"],
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": result["command"],
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "source_pattern_ids": result["source_pattern_ids"],
        "source_refs": result["source_refs"],
        "protocol_id": result.get("protocol_id"),
        "projection_receipt_refs": result["projection_receipt_refs"],
        "public_runtime_refs": result["public_runtime_refs"],
        "copied_material": result["copied_material"],
        "copied_material_count": result["copied_material_count"],
        "body_copied_material_count": result["body_copied_material_count"],
        "omitted_material_count": result["omitted_material_count"],
        "source_module_manifest_status": result.get("source_module_manifest_status"),
        "source_module_manifest_ref": result.get("source_module_manifest_ref"),
        "source_module_count": result.get("source_module_count"),
        "verified_source_module_count": result.get("verified_source_module_count"),
        "source_module_imports": result.get("source_module_imports", []),
        "premise_count": result["premise_count"],
        "namespace_counts": result["namespace_counts"],
        "split_counts": result["split_counts"],
        "expected_negative_cases": result["expected_negative_cases"],
        "observed_negative_cases": result["observed_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "findings": result["findings"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "body_material_contract": result["body_material_contract"],
        "body_material_status": result["body_material_status"],
        "receipt_paths": receipt_paths,
    }


def _build_board(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "lean_std_premise_index_board_v1",
        "created_at": result["created_at"],
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "public_claim": "A closed Lean/Std premise index is available as copied non-secret macro descriptors for retrieval and explanation.",
        "premise_count": result["premise_count"],
        "namespace_counts": result["namespace_counts"],
        "split_counts": result["split_counts"],
        "closed_index_only": True,
        "mathlib_allowed": False,
        "proof_bodies_allowed": False,
        "oracle_needed_ids_public": False,
        "test_split_tuning_authorized": False,
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "body_material_status": result["body_material_status"],
        "body_copied_material_count": result["body_copied_material_count"],
        "source_module_manifest_status": result.get("source_module_manifest_status"),
        "verified_source_module_count": result.get("verified_source_module_count"),
    }


def _secret_scan_card(result: dict[str, Any]) -> dict[str, Any]:
    scan = result.get("secret_exclusion_scan")
    payload = scan if isinstance(scan, dict) else {}
    return {
        "status": payload.get("status"),
        "scanned_path_count": payload.get("scanned_path_count"),
        "hit_count": payload.get("hit_count"),
        "blocking_hit_count": payload.get("blocking_hit_count"),
        "body_material_status": payload.get("body_material_status"),
        "body_text_exported": False,
    }


def _authority_ceiling_card(result: dict[str, Any]) -> dict[str, Any]:
    ceiling = result.get("authority_ceiling")
    payload = ceiling if isinstance(ceiling, dict) else {}
    return {
        "authority_ceiling": payload.get("authority_ceiling"),
        "mathlib_allowed": payload.get("mathlib_allowed") is True,
        "formal_proof_authority": payload.get("formal_proof_authority") is True,
        "proof_bodies_allowed": payload.get("proof_bodies_allowed") is True,
        "oracle_needed_ids_public": payload.get("oracle_needed_ids_public") is True,
        "test_split_tuning_authorized": payload.get("test_split_tuning_authorized") is True,
        "provider_calls_authorized": payload.get("provider_calls_authorized") is True,
        "lean_lake_execution_authorized": payload.get("lean_lake_execution_authorized") is True,
        "release_authorized": payload.get("release_authorized") is True,
    }


def _source_summary_card(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_id": result.get("protocol_id"),
        "source_pattern_count": len(result.get("source_pattern_ids", [])),
        "source_ref_count": len(result.get("source_refs", [])),
        "projection_receipt_ref_count": len(result.get("projection_receipt_refs", [])),
        "public_runtime_ref_count": len(result.get("public_runtime_refs", [])),
        "copied_material_count": result.get("copied_material_count"),
        "body_copied_material_count": result.get("body_copied_material_count"),
        "omitted_material_count": result.get("omitted_material_count"),
        "source_module_manifest_status": result.get("source_module_manifest_status"),
        "source_module_count": result.get("source_module_count"),
        "verified_source_module_count": result.get("verified_source_module_count"),
        "body_material_status": result.get("body_material_status"),
        "source_refs_exported": False,
        "copied_material_rows_exported": False,
    }


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    input_mode = result.get("input_mode")
    action = (
        "run-index-bundle"
        if input_mode == "exported_lean_std_premise_index_bundle"
        else "run"
    )
    card_id = (
        "lean_std_premise_index_bundle_card"
        if action == "run-index-bundle"
        else "lean_std_premise_index_fixture_card"
    )
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "input_mode": input_mode,
        "bundle_id": result.get("bundle_id"),
        "card_id": card_id,
        "output_profile": "compact_card_no_premise_ids_or_copied_material_rows",
        "full_output_available": True,
        "full_output_drilldown": f"rerun {action} without --card",
        "receipt_paths": result.get("receipt_paths", []),
        "premise_count": result.get("premise_count"),
        "namespace_counts": result.get("namespace_counts", {}),
        "split_counts": result.get("split_counts", {}),
        "closed_index_only": result.get("closed_index_only"),
        "negative_case_coverage": {
            "expected_case_count": len(result.get("expected_negative_cases", {})),
            "observed_case_count": len(result.get("observed_negative_cases", {})),
            "missing_negative_cases": result.get("missing_negative_cases", []),
            "error_code_count": len(result.get("error_codes", [])),
        },
        "source_summary": _source_summary_card(result),
        "secret_exclusion_scan_summary": _secret_scan_card(result),
        "authority_ceiling": _authority_ceiling_card(result),
        "no_export_guards": {
            "mathlib_refs_exported": False,
            "proof_bodies_exported": False,
            "oracle_needed_ids_exported": False,
            "provider_payloads_exported": False,
            "private_source_bodies_exported": False,
        },
        "output_economy": {
            "stdout_mode": "card",
            "full_payload_drilldown": "rerun without --card",
            "omitted_full_payload_keys": [
                "source_refs",
                "copied_material",
                "findings",
                "premise_ids",
                "secret_exclusion_scan.scan_scope",
            ],
        },
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    public_root = _public_root_for_path(out_dir)
    paths = {
        "result": out_dir / RESULT_NAME,
        "board": out_dir / BOARD_NAME,
        "validation": out_dir / VALIDATION_RECEIPT_NAME,
    }
    if acceptance_out is not None:
        paths["acceptance"] = acceptance_out
    receipt_paths = _relative_receipt_paths(paths, public_root)
    result_receipt = _common_receipt(
        result,
        schema_version="lean_std_premise_index_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board = _build_board(result)
    board["receipt_paths"] = receipt_paths
    validation = _common_receipt(
        result,
        schema_version="lean_std_premise_index_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation["negative_case_coverage_status"] = (
        PASS if not result["missing_negative_cases"] else "blocked"
    )
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(paths["result"], result_receipt)
    write_json_atomic(paths["board"], board)
    write_json_atomic(paths["validation"], validation)
    if acceptance_out is not None:
        acceptance = _common_receipt(
            result,
            schema_version="lean_std_premise_index_fixture_acceptance_v1",
            receipt_paths=receipt_paths,
        )
        acceptance["acceptance_status"] = (
            "accepted_current_authority" if result["status"] == PASS else "blocked"
        )
        acceptance["accepted_organ_id"] = ORGAN_ID
        write_json_atomic(acceptance_out, acceptance)
    result["receipt_paths"] = receipt_paths
    return result


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.lean_std_premise_index run",
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
    )


def run_index_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.lean_std_premise_index run-index-bundle",
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_lean_std_premise_index_bundle",
        include_negative=False,
    )
    target = Path(out_dir)
    path = target / BUNDLE_RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt_ref = _display(path, public_root=public_root)
    receipt = _common_receipt(
        result,
        schema_version="exported_lean_std_premise_index_bundle_validation_result_v1",
        receipt_paths=[receipt_ref],
    )
    write_json_atomic(path, receipt)
    result["receipt_paths"] = [receipt_ref]
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public Lean/Std premise index")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact command card; write the full receipt to --out.",
    )
    bundle_parser = sub.add_parser("run-index-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact command card; write the full receipt to --out.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "run":
        card_suffix = " --card" if args.card else ""
        command = (
            "python -m microcosm_core.organs.lean_std_premise_index run "
            f"--input {args.input} --out {args.out}{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    else:
        card_suffix = " --card" if args.card else ""
        command = (
            "python -m microcosm_core.organs.lean_std_premise_index "
            f"run-index-bundle --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run_index_bundle(args.input, args.out, command=command)
    output = result_card(result) if args.card else result
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
