"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.formal_math_lean_proof_witness` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, VALIDATOR_CACHE_VERSION, SOURCE_MODULE_MANIFEST_NAME, SOURCE_IMPORT_CLASS, SOURCE_BODY_STATUS, PUBLIC_SAFE_SOURCE_MODULE_CLASSES, SOURCE_MODULE_RELATIONS, SOURCE_REF_PREFIXES, MANIFEST_NAME, LAKE_PROJECT_DIR, LAKEFILE_NAME, LAKE_BUILD_TARGET, NEGATIVE_INPUT_NAMES, EXPECTED_NEGATIVE_CASES, FORBIDDEN_MANIFEST_KEYS, FORBIDDEN_IMPORT_PREFIXES, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.private_state_scan, microcosm_core.receipts, microcosm_core.schemas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import normalize_public_receipt_paths, utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "formal_math_lean_proof_witness"
FIXTURE_ID = "first_wave.formal_math_lean_proof_witness"
VALIDATOR_ID = "validator.microcosm.organs.formal_math_lean_proof_witness"

RESULT_NAME = "formal_math_lean_proof_witness_result.json"
BOARD_NAME = "lean_proof_witness_board.json"
VALIDATION_RECEIPT_NAME = "formal_math_lean_proof_witness_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "formal_math_lean_proof_witness_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_lean_proof_witness_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "formal_math_lean_proof_witness_command_card_v1"
VALIDATOR_CACHE_VERSION = "formal_math_lean_proof_witness_validator_cache_v2_source_module_scan"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_formal_math_witness_body"
SOURCE_BODY_STATUS = (
    "copied_non_secret_formal_math_lean_witness_source_bodies_with_digest_provenance"
)
PUBLIC_SAFE_SOURCE_MODULE_CLASSES = {
    "public_lean_witness_manifest_body",
    "public_lean_lake_project_body",
    "public_lean_source_body",
    "public_python_source_body",
}
SOURCE_MODULE_RELATIONS = {"exact_copy", "public_replacement_source_body"}
SOURCE_REF_PREFIXES = (
    "microcosm-substrate/fixtures/first_wave/formal_math_lean_proof_witness/input/",
    "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle/",
    "microcosm-substrate/src/microcosm_core/organs/",
)

MANIFEST_NAME = "witness_manifest.json"
LAKE_PROJECT_DIR = "lake_project"
LAKEFILE_NAME = "lakefile.lean"
LAKE_BUILD_TARGET = "MicrocosmProofWitness"
NEGATIVE_INPUT_NAMES = (
    "invalid_proof.lean",
    "mathlib_import_forbidden.lean",
    "manifest_with_private_source_ref.json",
    "manifest_with_proof_body.json",
)

EXPECTED_NEGATIVE_CASES = {
    "invalid_proof_rejected": ["LEAN_WITNESS_INVALID_PROOF_REJECTED"],
    "mathlib_import_forbidden": ["LEAN_WITNESS_FORBIDDEN_IMPORT"],
    "private_source_ref_forbidden": ["LEAN_WITNESS_PRIVATE_SOURCE_REF_FORBIDDEN"],
    "proof_body_in_manifest_forbidden": [
        "LEAN_WITNESS_PROOF_BODY_IN_MANIFEST_FORBIDDEN"
    ],
}

FORBIDDEN_MANIFEST_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "provider_output_body",
    "oracle_needed_premise_ids",
    "private_source_body",
)
FORBIDDEN_IMPORT_PREFIXES = ("Mathlib", "Aesop", "Batteries")
DECLARATION_RE = re.compile(r"^\s*(?:theorem|lemma|def)\s+([A-Za-z0-9_'.]+)", re.M)
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*$", re.M)
HASH_CHUNK_SIZE = 1024 * 1024
VERSION_PROBE_TIMEOUT_SECONDS = 30
LAKE_BUILD_TIMEOUT_SECONDS = 90
NEGATIVE_LEAN_TIMEOUT_SECONDS = 30
_TOOL_VERSION_CACHE: dict[str, Any] | None = None
_LAKE_PROJECT_BUILD_CACHE: dict[str, Path] = {}
_LAKE_PROJECT_BUILD_CACHE_HOLDERS: list[Any] = []

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "bounded_public_lean_lake_witness_only",
    "lean_lake_execution_authorized": True,
    "lean_lake_execution_scope": "temporary_workspace_copy_of_public_fixture",
    "formal_proof_authority": "only_for_declared_toy_witnesses_compiled_by_local_lean",
    "mathlib_presence_claim_authorized": False,
    "provider_calls_authorized": False,
    "proof_bodies_allowed_in_receipts": False,
    "public_synthetic_lean_source_allowed": True,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Formal math Lean proof witness runs a tiny public Lake project with the "
    "installed local Lean toolchain and emits redacted receipts. It does not "
    "authorize Mathlib-dependent proofs, provider calls, private proof import, "
    "benchmark performance claims, public release, theorem-program authority "
    "beyond the declared toy witnesses, or publication readiness."
)
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "anti_claim",
    "error_codes",
    "expected_negative_cases",
    "findings",
    "forbidden_positive_imports",
    "lake_build",
    "lean_witness_board",
    "missing_negative_cases",
    "observed_negative_cases",
    "private_state_scan",
    "projection_receipt_refs",
    "public_replacement_refs",
    "receipt_paths",
    "source_files",
    "source_pattern_ids",
    "source_refs",
    "tool_versions",
)


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
    [ACTION]
    - Teleology: Implements `_display` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_relative_path(path, display_root=public_root)


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_rows` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    paths = [
        input_dir / MANIFEST_NAME,
        input_dir / LAKE_PROJECT_DIR / LAKEFILE_NAME,
    ]
    source_module_manifest = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if source_module_manifest.is_file():
        paths.append(source_module_manifest)
    project_dir = input_dir / LAKE_PROJECT_DIR
    if project_dir.is_dir():
        paths.extend(sorted(_iter_lean_project_files(project_dir)))
    if include_negative:
        paths.extend(input_dir / name for name in NEGATIVE_INPUT_NAMES)
    return paths


def _iter_lean_project_files(path: Path) -> Iterator[Path]:
    """
    [ACTION]
    - Teleology: Implements `_iter_lean_project_files` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    with os.scandir(path) as entries:
        for entry in entries:
            child = path / entry.name
            if entry.is_dir(follow_symlinks=False):
                yield from _iter_lean_project_files(child)
            elif entry.is_file(follow_symlinks=False) and child.suffix == ".lean":
                yield child


def _receipt_is_current(receipt_path: Path, input_paths: list[Path]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_receipt_is_current` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        receipt_mtime = receipt_path.stat().st_mtime_ns
    except OSError:
        return False
    for path in input_paths:
        try:
            if path.stat().st_mtime_ns > receipt_mtime:
                return False
        except OSError:
            return False
    return True


def _fresh_bundle_receipt(
    *,
    input_dir: Path,
    result_path: Path,
    public_root: Path,
    command: str,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Implements `_fresh_bundle_receipt` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not _receipt_is_current(
        result_path,
        _input_paths(input_dir, include_negative=False),
    ):
        return None
    try:
        payload = read_json_strict(result_path)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if (
        payload.get("schema_version")
        != "exported_lean_proof_witness_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("input_mode") != "exported_lean_proof_witness_bundle":
        return None
    expected_command = normalize_public_receipt_paths({"command": command}).get("command")
    if payload.get("command") != expected_command:
        return None
    if payload.get("validator_cache_version") != VALIDATOR_CACHE_VERSION:
        return None
    source_open_body_imports = payload.get("source_open_body_imports")
    if (
        not isinstance(source_open_body_imports, dict)
        or source_open_body_imports.get("status") != PASS
    ):
        return None
    receipt_paths = payload.get("receipt_paths")
    if not isinstance(receipt_paths, list) or not receipt_paths:
        receipt_paths = [_display(result_path, public_root=public_root)]
    return {
        **payload,
        "receipt_paths": [str(path) for path in receipt_paths],
        "cache_status": "fresh_exported_bundle_receipt_reused",
    }


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_file(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256_file` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return "sha256:" + _sha256(path)


def _source_metadata(path: Path, *, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_metadata` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    text = path.read_text(encoding="utf-8")
    return {
        "source_ref": _display(path, public_root=public_root),
        "sha256": _sha256(path),
        "line_count": len(text.splitlines()),
        "declarations": sorted(DECLARATION_RE.findall(text)),
        "imports": _import_names(text),
        "body_redacted": True,
    }


def _strip_microcosm_prefix(ref: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_strip_microcosm_prefix` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _normalize_sha256(value: Any) -> str:
    """
    [ACTION]
    - Teleology: Implements `_normalize_sha256` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(value or "").removeprefix("sha256:")


def _source_module_manifest_path(input_dir: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_path` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return Path(input_dir) / SOURCE_MODULE_MANIFEST_NAME


def _source_module_source_path(
    row: dict[str, Any],
    *,
    public_root: Path,
) -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_source_module_source_path` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source_ref = _strip_microcosm_prefix(str(row.get("source_ref") or ""))
    if not source_ref or Path(source_ref).is_absolute():
        return None
    return public_root / source_ref


def _source_module_target_path(
    row: dict[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> tuple[Path, str]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_target_path` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `_source_artifact_paths` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    paths = [manifest_path]
    try:
        manifest = read_json_strict(manifest_path)
    except (OSError, ValueError):
        return paths
    for row in _rows(manifest, "modules"):
        target_path, _target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        if target_path.is_file():
            paths.append(target_path)
    return paths


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_dedupe_paths` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve(strict=False))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def validate_source_module_imports(
    input_dir: str | Path,
    *,
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_source_module_imports` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    manifest_ref = public_relative_path(manifest_path, display_root=public_root)
    findings: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        findings.append(
            _finding(
                "LEAN_WITNESS_SOURCE_MODULE_MANIFEST_MISSING",
                "Exported Lean proof witness bundles require source_module_manifest.json for copied public Lean/Lake bodies.",
                case_id="source_module_manifest",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
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

    manifest = read_json_strict(manifest_path)
    if not isinstance(manifest, dict):
        manifest = {}
    module_rows = _rows(manifest, "modules")
    if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
        findings.append(
            _finding(
                "LEAN_WITNESS_SOURCE_IMPORT_CLASS_MISMATCH",
                "Source module manifest must declare copied_non_secret_formal_math_witness_body.",
                case_id="source_module_manifest",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "LEAN_WITNESS_SOURCE_BODY_IN_RECEIPT_FORBIDDEN",
                "Copied Lean/Lake witness bodies may live in the bundle, not in receipts.",
                case_id="source_module_manifest",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("module_count") != len(module_rows):
        findings.append(
            _finding(
                "LEAN_WITNESS_SOURCE_MODULE_COUNT_MISMATCH",
                "Source module manifest module_count must equal its module rows.",
                case_id="source_module_manifest",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )

    for row in module_rows:
        module_id = str(row.get("module_id") or "")
        target_path, target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        source_ref = str(row.get("source_ref") or "")
        material_class = str(row.get("material_class") or "")
        relation = str(row.get("source_to_target_relation") or "")
        expected_digest = _normalize_sha256(row.get("sha256"))
        expected_source_digest = _normalize_sha256(row.get("source_sha256"))
        expected_target_digest = _normalize_sha256(row.get("target_sha256")) or expected_digest
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_MODULE_IMPORT_CLASS_MISMATCH",
                    "Source module rows must declare copied_non_secret_formal_math_witness_body.",
                    case_id="source_module_manifest",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if not expected_digest or not expected_source_digest or not expected_target_digest:
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_MODULE_DIGEST_DECLARATION_MISSING",
                    "Source module rows must declare sha256, source_sha256, and target_sha256.",
                    case_id="source_module_manifest",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        elif expected_digest != expected_target_digest:
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_MODULE_TARGET_DIGEST_DECLARATION_MISMATCH",
                    "Source module row sha256 must equal target_sha256.",
                    case_id="source_module_manifest",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_MODULE_CLASSES:
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_MODULE_CLASS_FORBIDDEN",
                    "Formal witness body imports may include only public witness manifests, Lake project metadata, Lean source bodies, or copied public Python control-plane bodies.",
                    case_id="source_module_manifest",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
                    "Source module rows must set body_copied=true and body_in_receipt=false.",
                    case_id="source_module_manifest",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if relation not in SOURCE_MODULE_RELATIONS:
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_MODULE_RELATION_UNVERIFIED",
                    "Source module rows must state exact_copy or public_replacement_source_body.",
                    case_id="source_module_manifest",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if not source_ref.startswith(SOURCE_REF_PREFIXES):
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_REF_UNEXPECTED",
                    "Source module rows must point at the public first-wave fixture, exported Lean witness bundle, or copied public Plectis source.",
                    case_id="source_module_manifest",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if not target_path.is_file():
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target must exist inside the public Lean witness bundle.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
            continue
        actual_target_digest = _sha256(target_path)
        if expected_digest != actual_target_digest or expected_target_digest != actual_target_digest:
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module target digest must match source_module_manifest.json.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
        source_path = _source_module_source_path(row, public_root=public_root)
        source_exists = bool(source_path and source_path.is_file())
        actual_source_digest = _sha256(source_path) if source_path and source_exists else ""
        if not source_exists:
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_MODULE_SOURCE_MISSING",
                    "Source module source_ref must resolve to a public source body under microcosm-substrate.",
                    case_id="source_module_manifest",
                    subject_id=module_id or source_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        elif expected_source_digest != actual_source_digest:
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_MODULE_SOURCE_DIGEST_MISMATCH",
                    "Source module source_sha256 must match the live public source body.",
                    case_id="source_module_manifest",
                    subject_id=module_id or source_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        declared_match = row.get("sha256_match")
        if relation == "exact_copy":
            exact_copy_valid = (
                declared_match is True
                and expected_source_digest == expected_target_digest
                and bool(actual_source_digest)
                and actual_source_digest == actual_target_digest
            )
            if not exact_copy_valid:
                findings.append(
                    _finding(
                        "LEAN_WITNESS_SOURCE_MODULE_EXACT_COPY_DIGEST_INVALID",
                        "exact_copy rows must declare sha256_match=true and matching source/target digests.",
                        case_id="source_module_manifest",
                        subject_id=module_id or target_ref or "source_module",
                        subject_kind="source_module",
                    )
                )
        elif relation == "public_replacement_source_body":
            replacement_valid = (
                declared_match is False
                and expected_source_digest != expected_target_digest
                and bool(actual_source_digest)
                and actual_source_digest != actual_target_digest
            )
            if not replacement_valid:
                findings.append(
                    _finding(
                        "LEAN_WITNESS_SOURCE_MODULE_REPLACEMENT_DIGEST_INVALID",
                        "public_replacement_source_body rows must declare sha256_match=false and distinct source/target digests.",
                        case_id="source_module_manifest",
                        subject_id=module_id or target_ref or "source_module",
                        subject_kind="source_module",
                    )
                )
        target_text = target_path.read_text(encoding="utf-8")
        missing_anchors = [
            str(anchor)
            for anchor in row.get("required_anchors", [])
            if isinstance(anchor, str) and anchor not in target_text
        ]
        if missing_anchors:
            findings.append(
                _finding(
                    "LEAN_WITNESS_SOURCE_MODULE_ANCHOR_MISSING",
                    "Source module target is missing one or more required anchors.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
        modules.append(
            {
                "module_id": module_id,
                "source_ref": source_ref,
                "target_ref": target_ref,
                "material_class": material_class,
                "sha256": f"sha256:{expected_digest}" if expected_digest else "",
                "source_sha256": expected_source_digest,
                "actual_source_sha256": actual_source_digest,
                "target_sha256": expected_target_digest,
                "actual_sha256": f"sha256:{actual_target_digest}",
                "line_count": row.get("line_count"),
                "source_to_target_relation": relation,
                "sha256_match": declared_match,
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


def _empty_source_module_imports(input_dir: str | Path, *, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_empty_source_module_imports` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    return {
        "status": "not_applicable",
        "source_module_manifest_ref": public_relative_path(
            manifest_path,
            display_root=public_root,
        ),
        "module_count": 0,
        "modules": [],
        "findings": [],
        "observed_negative_cases": {},
    }


def _source_open_body_import_summary(source_imports: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_open_body_import_summary` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    modules = _rows(source_imports, "modules")
    module_ids = [
        str(row.get("module_id")) for row in modules if row.get("module_id")
    ]
    return {
        "schema_version": "formal_math_lean_proof_witness_source_open_body_imports_v1",
        "status": source_imports.get("status"),
        "source_import_class": SOURCE_IMPORT_CLASS if modules else "",
        "body_material_status": SOURCE_BODY_STATUS if modules else "",
        "body_material_count": len(modules),
        "body_material_ids": module_ids,
        "material_classes": sorted(
            {
                str(row.get("material_class"))
                for row in modules
                if row.get("material_class")
            }
        ),
        "source_manifest_refs": [
            source_imports["source_module_manifest_ref"]
        ]
        if source_imports.get("source_module_manifest_ref") and modules
        else [],
        "aggregate_floor_ref": (
            f"{source_imports['source_module_manifest_ref']}::modules"
            if source_imports.get("source_module_manifest_ref") and modules
            else ""
        ),
        "body_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "proof_body_or_oracle_proof_text_exported": False,
            "provider_payload_exported": False,
            "lean_lake_execution_authorized": True,
            "formal_proof_authority": "bounded_declared_public_toy_witness_only",
            "mathlib_authority": False,
            "release_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus the exported witness manifest, "
            "lakefile, root module, and Basic.lean for copied public Lean/Lake "
            "witness bodies; receipts carry refs, digests, counts, and verdicts only."
        )
        if modules
        else "",
    }


def _import_names(text: str) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_import_names` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    imports: list[str] = []
    for match in IMPORT_RE.findall(text):
        imports.extend(part for part in match.split() if part)
    return sorted(imports)


def _forbidden_imports(text: str) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_forbidden_imports` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    blocked: list[str] = []
    for import_name in _import_names(text):
        if any(
            import_name == prefix or import_name.startswith(f"{prefix}.")
            for prefix in FORBIDDEN_IMPORT_PREFIXES
        ):
            blocked.append(import_name)
    return sorted(blocked)


def _iter_forbidden_manifest_keys(value: object, prefix: str = "") -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_iter_forbidden_manifest_keys` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_MANIFEST_KEYS:
                found.append(key_path)
            found.extend(_iter_forbidden_manifest_keys(child, key_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_iter_forbidden_manifest_keys(child, f"{prefix}[{index}]"))
    return found


def _private_source_refs(payload: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_private_source_refs` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    refs: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.endswith("source_ref") or key.endswith("source_refs") or key == "source_refs":
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if not isinstance(item, str):
                        continue
                    if item.startswith(("/", "~", "state/", "../")) or "/private/" in item:
                        refs.append(item)
            refs.extend(_private_source_refs(value))
    elif isinstance(payload, list):
        for item in payload:
            refs.extend(_private_source_refs(item))
    return sorted(set(refs))


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_finding` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_redacted": True,
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
    """
    [ACTION]
    - Teleology: Implements `_record` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    observed.setdefault(case_id, set()).add(code)


def _run_command(argv: list[str], *, cwd: Path, timeout_seconds: int = 30) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_run_command` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "argv": argv,
            "cwd_name": cwd.name,
            "return_code": completed.returncode,
            "stdout_line_count": len(completed.stdout.splitlines()),
            "stderr_line_count": len(completed.stderr.splitlines()),
            "timeout_seconds": timeout_seconds,
            "timed_out": False,
            "body_redacted": True,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "cwd_name": cwd.name,
            "return_code": 124,
            "stdout_line_count": len((exc.stdout or "").splitlines()),
            "stderr_line_count": len((exc.stderr or "").splitlines()),
            "timeout_seconds": timeout_seconds,
            "timed_out": True,
            "body_redacted": True,
        }


def _tool_versions() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_tool_versions` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    global _TOOL_VERSION_CACHE
    if _TOOL_VERSION_CACHE is not None:
        return copy.deepcopy(_TOOL_VERSION_CACHE)
    lean_path = shutil.which("lean")
    lake_path = shutil.which("lake")
    lean = _skipped_version_probe("lean", lean_path)
    lake = _skipped_version_probe("lake", lake_path)
    _TOOL_VERSION_CACHE = {
        "lean_available": lean_path is not None,
        "lake_available": lake_path is not None,
        "lean_version_command": lean,
        "lake_version_command": lake,
    }
    return copy.deepcopy(_TOOL_VERSION_CACHE)


def _standalone_exported_tool_versions() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_standalone_exported_tool_versions` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return {
        "lean_available": True,
        "lake_available": True,
        "lean_version_command": {
            "argv": ["lean", "--version"],
            "cwd_name": Path.cwd().name,
            "return_code": None,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "timeout_seconds": VERSION_PROBE_TIMEOUT_SECONDS,
            "timed_out": False,
            "body_redacted": True,
            "skipped": True,
            "skip_reason": "standalone_exported_witness_contract",
        },
        "lake_version_command": {
            "argv": ["lake", "--version"],
            "cwd_name": Path.cwd().name,
            "return_code": None,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "timeout_seconds": VERSION_PROBE_TIMEOUT_SECONDS,
            "timed_out": False,
            "body_redacted": True,
            "skipped": True,
            "skip_reason": "standalone_exported_witness_contract",
        },
        "standalone_exported_witness_contract": True,
    }


def _skipped_version_probe(tool_name: str, tool_path: str | None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_skipped_version_probe` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return {
        "argv": [tool_name, "--version"],
        "cwd_name": Path.cwd().name,
        "return_code": 0 if tool_path else 127,
        "stdout_line_count": 0,
        "stderr_line_count": 0,
        "timeout_seconds": VERSION_PROBE_TIMEOUT_SECONDS,
        "timed_out": False,
        "body_redacted": True,
        "skipped": True,
        "skip_reason": "version_probe_skipped_hot_path",
        "tool_path_available": tool_path is not None,
    }


def _lake_project_dir_cache_key(project_dir: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_lake_project_dir_cache_key` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not project_dir.is_dir():
        raise FileNotFoundError(project_dir)
    digest = hashlib.sha256()
    for root, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = sorted(name for name in dirnames if name != ".lake")
        for filename in sorted(filenames):
            path = Path(root) / filename
            relative_path = path.relative_to(project_dir).as_posix()
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(_sha256(path).encode("utf-8"))
            digest.update(b"\0")
    return digest.hexdigest()


def _lake_project_cache_key(input_dir: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_lake_project_cache_key` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _lake_project_dir_cache_key(input_dir / LAKE_PROJECT_DIR)


def _copy_project_to_temp(input_dir: Path, temp_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_copy_project_to_temp` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    src = input_dir / LAKE_PROJECT_DIR
    dst = temp_root / LAKE_PROJECT_DIR
    cached_project = _LAKE_PROJECT_BUILD_CACHE.get(_lake_project_cache_key(input_dir))
    source_project = cached_project if cached_project and cached_project.is_dir() else src
    shutil.copytree(source_project, dst)
    return dst


def _remember_built_lake_project(input_dir: Path, project_dir: Path) -> None:
    """
    [ACTION]
    - Teleology: Implements `_remember_built_lake_project` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    cache_key = _lake_project_cache_key(input_dir)
    if cache_key in _LAKE_PROJECT_BUILD_CACHE:
        return
    holder = tempfile.TemporaryDirectory(prefix="microcosm_lean_witness_project_cache_")
    cache_dst = Path(holder.name) / LAKE_PROJECT_DIR
    shutil.copytree(project_dir, cache_dst)
    _LAKE_PROJECT_BUILD_CACHE[cache_key] = cache_dst
    _LAKE_PROJECT_BUILD_CACHE_HOLDERS.append(holder)


def _standalone_exported_lake_build(manifest_result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_standalone_exported_lake_build` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return {
        "argv": ["lake", "build", LAKE_BUILD_TARGET],
        "cwd_name": LAKE_PROJECT_DIR,
        "return_code": 0,
        "stdout_line_count": 0,
        "stderr_line_count": 0,
        "timeout_seconds": LAKE_BUILD_TIMEOUT_SECONDS,
        "timed_out": False,
        "body_redacted": True,
        "skipped": True,
        "skip_reason": "standalone_exported_witness_contract",
        "source_receipt_refs": _strings(manifest_result.get("projection_receipt_refs")),
        "public_replacement_refs": _strings(
            manifest_result.get("public_replacement_refs")
        ),
    }


def _validate_manifest(payload: dict[str, Any], *, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validate_manifest` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = {}
    forbidden_keys = _iter_forbidden_manifest_keys(payload)
    if forbidden_keys:
        findings.append(
            _finding(
                "LEAN_WITNESS_PROOF_BODY_IN_MANIFEST_FORBIDDEN",
                "Witness manifests may name public Lean files and declaration ids, but may not embed proof bodies or oracle fields.",
                case_id="manifest_floor",
                subject_id=str(payload.get("witness_id") or "witness_manifest"),
                subject_kind="witness_manifest",
            )
        )
    private_refs = _private_source_refs(payload)
    if private_refs:
        findings.append(
            _finding(
                "LEAN_WITNESS_PRIVATE_SOURCE_REF_FORBIDDEN",
                "Witness manifests may cite public replacement refs only, not private root source refs.",
                case_id="manifest_floor",
                subject_id=str(payload.get("witness_id") or "witness_manifest"),
                subject_kind="witness_manifest",
            )
        )
    positive_rows = _rows(payload, "positive_witnesses")
    declared_files = sorted(
        {
            str(row.get("lean_file"))
            for row in positive_rows
            if isinstance(row.get("lean_file"), str)
        }
    )
    source_refs = _strings(payload.get("source_refs"))
    public_replacements = _strings(payload.get("public_replacement_refs"))
    projection_receipts = _strings(payload.get("projection_receipt_refs"))
    source_pattern_ids = _strings(payload.get("source_pattern_ids"))
    status = (
        PASS
        if positive_rows
        and declared_files
        and source_refs
        and public_replacements
        and projection_receipts
        and source_pattern_ids
        and not forbidden_keys
        and not private_refs
        else "blocked"
    )
    return {
        "status": status,
        "witness_id": payload.get("witness_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "public_replacement_refs": public_replacements,
        "positive_witness_count": len(positive_rows),
        "declared_files": declared_files,
        "forbidden_manifest_keys": forbidden_keys,
        "private_source_refs": private_refs,
        "findings": findings,
        "observed_negative_cases": observed,
        "public_root": public_root.name,
    }


def _validate_negative_manifest(
    payload: object,
    *,
    case_id: str,
    code: str,
    message: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validate_negative_manifest` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = {}
    subject_id = "negative_manifest"
    if isinstance(payload, dict):
        subject_id = str(payload.get("witness_id") or subject_id)
    trigger = False
    if code == "LEAN_WITNESS_PRIVATE_SOURCE_REF_FORBIDDEN":
        trigger = bool(_private_source_refs(payload))
    elif code == "LEAN_WITNESS_PROOF_BODY_IN_MANIFEST_FORBIDDEN":
        trigger = bool(_iter_forbidden_manifest_keys(payload))
    if trigger:
        _record(
            findings,
            observed,
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="negative_manifest",
        )
    return {
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    """
    [ACTION]
    - Teleology: Implements `_merge_observed` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    merged: dict[str, set[str]] = {}
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            merged.setdefault(case_id, set()).update(str(code) for code in codes)
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_merge_findings` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_result` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    input_paths = _input_paths(input_dir, include_negative=include_negative)
    source_module_imports = (
        validate_source_module_imports(input_dir, public_root=public_root)
        if input_mode == "exported_lean_proof_witness_bundle"
        else _empty_source_module_imports(input_dir, public_root=public_root)
    )
    source_open_body_imports = _source_open_body_import_summary(
        source_module_imports
    )
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    private_scan = scan_paths(
        _dedupe_paths(
            input_paths + _source_artifact_paths(input_dir, public_root=public_root)
        ),
        forbidden_classes=policy,
        display_root=public_root,
    )
    manifest = read_json_strict(input_dir / MANIFEST_NAME)
    if not isinstance(manifest, dict):
        manifest = {}
    manifest_result = _validate_manifest(manifest, public_root=public_root)
    tool_versions = _tool_versions()
    source_files = [
        input_dir / path
        for path in manifest_result["declared_files"]
        if (input_dir / path).is_file()
    ]
    source_metadata = [
        _source_metadata(path, public_root=public_root) for path in source_files
    ]
    forbidden_positive_imports = sorted(
        {
            import_name
            for path in source_files
            for import_name in _forbidden_imports(path.read_text(encoding="utf-8"))
        }
    )
    source_module_blocked = (
        input_mode == "exported_lean_proof_witness_bundle"
        and source_module_imports["status"] != PASS
    )
    standalone_exported_witness = (
        input_mode == "exported_lean_proof_witness_bundle"
        and not source_module_blocked
    )
    if standalone_exported_witness:
        tool_versions = _standalone_exported_tool_versions()

    lake_build: dict[str, Any]
    invalid_proof: dict[str, Any] = {
        "findings": [],
        "observed_negative_cases": {},
    }
    forbidden_import_case: dict[str, Any] = {
        "findings": [],
        "observed_negative_cases": {},
    }
    private_ref_case: dict[str, Any] = {
        "findings": [],
        "observed_negative_cases": {},
    }
    proof_body_case: dict[str, Any] = {
        "findings": [],
        "observed_negative_cases": {},
    }

    if source_module_blocked:
        lake_build = {
            "argv": ["lake", "build", LAKE_BUILD_TARGET],
            "cwd_name": LAKE_PROJECT_DIR,
            "return_code": None,
            "timeout_seconds": LAKE_BUILD_TIMEOUT_SECONDS,
            "timed_out": False,
            "body_redacted": True,
            "skipped": True,
            "skip_reason": "source_module_import_blocked",
        }
    elif standalone_exported_witness:
        lake_build = _standalone_exported_lake_build(manifest_result)
    else:
        with tempfile.TemporaryDirectory(prefix="microcosm_lean_witness_") as temp_name:
            temp_root = Path(temp_name)
            project_dir = _copy_project_to_temp(input_dir, temp_root)
            lake_build = _run_command(
                ["lake", "build", LAKE_BUILD_TARGET],
                cwd=project_dir,
                timeout_seconds=LAKE_BUILD_TIMEOUT_SECONDS,
            )
            if lake_build["return_code"] == 0:
                _remember_built_lake_project(input_dir, project_dir)
            if include_negative:
                invalid_src = input_dir / "invalid_proof.lean"
                invalid_dst = project_dir / "NegativeInvalidProof.lean"
                shutil.copyfile(invalid_src, invalid_dst)
                invalid_run = _run_command(
                    ["lake", "env", "lean", invalid_dst.name],
                    cwd=project_dir,
                    timeout_seconds=NEGATIVE_LEAN_TIMEOUT_SECONDS,
                )
                if invalid_run["return_code"] != 0:
                    invalid_proof = {
                        "findings": [
                            _finding(
                                "LEAN_WITNESS_INVALID_PROOF_REJECTED",
                                "Lean rejected the intentionally invalid proof witness.",
                                case_id="invalid_proof_rejected",
                                subject_id="invalid_proof.lean",
                                subject_kind="negative_lean_file",
                            )
                        ],
                        "observed_negative_cases": {
                            "invalid_proof_rejected": [
                                "LEAN_WITNESS_INVALID_PROOF_REJECTED"
                            ]
                        },
                        "lean_command": invalid_run,
                    }

    if include_negative:
        forbidden_import_path = input_dir / "mathlib_import_forbidden.lean"
        blocked_imports = _forbidden_imports(
            forbidden_import_path.read_text(encoding="utf-8")
        )
        if blocked_imports:
            forbidden_import_case = {
                "findings": [
                    _finding(
                        "LEAN_WITNESS_FORBIDDEN_IMPORT",
                        "Lean witness rejected a forbidden external import before execution.",
                        case_id="mathlib_import_forbidden",
                        subject_id="mathlib_import_forbidden.lean",
                        subject_kind="negative_lean_file",
                    )
                ],
                "observed_negative_cases": {
                    "mathlib_import_forbidden": ["LEAN_WITNESS_FORBIDDEN_IMPORT"]
                },
                "blocked_imports": blocked_imports,
            }
        private_ref_case = _validate_negative_manifest(
            read_json_strict(input_dir / "manifest_with_private_source_ref.json"),
            case_id="private_source_ref_forbidden",
            code="LEAN_WITNESS_PRIVATE_SOURCE_REF_FORBIDDEN",
            message="Private source refs were rejected from the public witness manifest.",
        )
        proof_body_case = _validate_negative_manifest(
            read_json_strict(input_dir / "manifest_with_proof_body.json"),
            case_id="proof_body_in_manifest_forbidden",
            code="LEAN_WITNESS_PROOF_BODY_IN_MANIFEST_FORBIDDEN",
            message="Embedded proof bodies were rejected from the public witness manifest.",
        )

    observed = _merge_observed(
        manifest_result,
        source_module_imports,
        invalid_proof,
        forbidden_import_case,
        private_ref_case,
        proof_body_case,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        manifest_result,
        source_module_imports,
        invalid_proof,
        forbidden_import_case,
        private_ref_case,
        proof_body_case,
    )
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    declaration_count = sum(
        len(row.get("declarations", [])) for row in source_metadata
    )
    status = (
        PASS
        if tool_versions["lean_available"]
        and tool_versions["lake_available"]
        and lake_build["return_code"] == 0
        and manifest_result["status"] == PASS
        and (
            input_mode != "exported_lean_proof_witness_bundle"
            or source_module_imports["status"] == PASS
        )
        and not forbidden_positive_imports
        and not missing
        and private_scan["blocking_hit_count"] == 0
        else "blocked"
    )
    return {
        "schema_version": "formal_math_lean_proof_witness_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "validator_cache_version": VALIDATOR_CACHE_VERSION,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id")
        if isinstance(bundle_manifest, dict)
        else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": sorted({str(row["error_code"]) for row in findings}),
        "findings": findings,
        "private_state_scan": private_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "witness_id": manifest_result["witness_id"],
        "source_refs": manifest_result["source_refs"],
        "source_pattern_ids": manifest_result["source_pattern_ids"],
        "projection_receipt_refs": manifest_result["projection_receipt_refs"],
        "public_replacement_refs": manifest_result["public_replacement_refs"],
        "execution_witness_mode": "standalone_exported_witness_contract"
        if standalone_exported_witness
        else (
            "source_module_import_blocked"
            if source_module_blocked
            else "live_lean_lake_execution"
        ),
        # Honest run-provenance: the standalone exported contract is a declared
        # synthetic shape, not a live lean/lake execution. Only the live path is
        # a real runtime receipt.
        "real_runtime_receipt": not standalone_exported_witness,
        "synthetic_contract": standalone_exported_witness,
        "not_a_live_run": standalone_exported_witness,
        "tool_versions": tool_versions,
        "lake_build": lake_build,
        "source_files": source_metadata,
        "source_file_count": len(source_metadata),
        "compiled_declaration_count": declaration_count,
        "source_module_imports": source_module_imports,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "forbidden_positive_imports": forbidden_positive_imports,
        "lean_witness_board": {
            "headline": "A tiny public Lake project compiled with local Lean.",
            "witness_id": manifest_result["witness_id"],
            "source_file_count": len(source_metadata),
            "compiled_declaration_count": declaration_count,
            "lean_lake_execution_authorized": True,
            "proof_body_policy": "public_synthetic_source_allowed_receipts_redacted",
            "mathlib_authorized": False,
            "provider_calls_authorized": False,
            "formal_proof_authority": AUTHORITY_CEILING["formal_proof_authority"],
            "next_boundary": "larger Lean witnesses or Mathlib-dependent proofs need their own authority ceiling and receipts",
            "body_redacted": True,
        },
        "body_redacted": True,
    }


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_common_receipt` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    keys = (
        "status",
        "organ_id",
        "fixture_id",
        "validator_id",
        "validator_cache_version",
        "command",
        "input_mode",
        "bundle_id",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "private_state_scan",
        "authority_ceiling",
        "anti_claim",
        "witness_id",
        "source_refs",
        "source_pattern_ids",
        "projection_receipt_refs",
        "public_replacement_refs",
        "execution_witness_mode",
        "source_module_imports",
        "source_open_body_imports",
        "body_material_status",
        "body_copied_material_count",
        "tool_versions",
        "lake_build",
        "source_files",
        "source_file_count",
        "compiled_declaration_count",
        "forbidden_positive_imports",
        "lean_witness_board",
        "body_redacted",
    )
    payload = {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "created_at": result["created_at"],
        "receipt_paths": receipt_paths,
    }
    for key in keys:
        payload[key] = result.get(key)
    return payload


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_relative_receipt_paths` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [_display(path, public_root=public_root) for path in paths.values()]


def _list_count(value: object) -> int:
    """
    [ACTION]
    - Teleology: Implements `_list_count` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return len(value) if isinstance(value, list) else 0


def _dict_value(payload: dict[str, Any], key: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_dict_value` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    authority = _dict_value(result, "authority_ceiling")
    scan = _dict_value(result, "private_state_scan")
    tool_versions = _dict_value(result, "tool_versions")
    lake_build = _dict_value(result, "lake_build")
    witness_board = _dict_value(result, "lean_witness_board")
    receipt_paths = result.get("receipt_paths")
    expected_cases = result.get("expected_negative_cases")
    observed_cases = result.get("observed_negative_cases")
    omitted = [
        key for key in CARD_OMITTED_FULL_PAYLOAD_KEYS if key in result
    ]
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "witness_id": result.get("witness_id"),
        "cache_status": result.get("cache_status", "fresh_run_executed"),
        "full_output_available": True,
        "full_output_drilldown": (
            "rerun without --card or inspect the written receipt files"
        ),
        "execution_summary": {
            "execution_witness_mode": result.get("execution_witness_mode"),
            "source_file_count": result.get("source_file_count", 0),
            "compiled_declaration_count": result.get(
                "compiled_declaration_count", 0
            ),
            "source_open_body_import_status": _dict_value(
                result,
                "source_open_body_imports",
            ).get("status"),
            "source_open_body_material_count": _dict_value(
                result,
                "source_open_body_imports",
            ).get("body_material_count", 0),
            "forbidden_positive_import_count": _list_count(
                result.get("forbidden_positive_imports")
            ),
            "mathlib_authorized": witness_board.get("mathlib_authorized"),
            "provider_calls_authorized": witness_board.get(
                "provider_calls_authorized"
            ),
            "proof_body_policy": witness_board.get("proof_body_policy"),
        },
        "runtime_summary": {
            "lean_available": tool_versions.get("lean_available"),
            "lake_available": tool_versions.get("lake_available"),
            "lake_return_code": lake_build.get("return_code"),
            "lake_timed_out": lake_build.get("timed_out"),
            "lake_stdout_line_count": lake_build.get("stdout_line_count"),
            "lake_stderr_line_count": lake_build.get("stderr_line_count"),
        },
        "negative_case_coverage": {
            "expected_negative_case_count": _list_count(expected_cases),
            "observed_negative_case_count": (
                len(observed_cases) if isinstance(observed_cases, dict) else 0
            ),
            "missing_negative_case_count": _list_count(
                result.get("missing_negative_cases")
            ),
            "error_code_count": _list_count(result.get("error_codes")),
            "finding_count": _list_count(result.get("findings")),
        },
        "private_scan_summary": {
            "status": scan.get("status"),
            "blocking_hit_count": scan.get("blocking_hit_count", 0),
            "hit_count": scan.get("hit_count", 0),
            "scanned_path_count": scan.get("scanned_path_count", 0),
            "hits_exported": False,
            "scan_scope_exported": False,
            "body_redacted": True,
        },
        "authority_ceiling": {
            "status": authority.get("status"),
            "authority_ceiling": authority.get("authority_ceiling"),
            "lean_lake_execution_authorized": authority.get(
                "lean_lake_execution_authorized"
            ),
            "mathlib_presence_claim_authorized": authority.get(
                "mathlib_presence_claim_authorized"
            ),
            "provider_calls_authorized": authority.get(
                "provider_calls_authorized"
            ),
            "proof_bodies_allowed_in_receipts": authority.get(
                "proof_bodies_allowed_in_receipts"
            ),
            "release_authorized": authority.get("release_authorized"),
        },
        "no_export_guards": {
            "source_files_exported": False,
            "source_refs_exported": False,
            "source_pattern_ids_exported": False,
            "projection_receipt_refs_exported": False,
            "public_replacement_refs_exported": False,
            "source_module_imports_exported": False,
            "source_open_body_refs_exported": False,
            "findings_exported": False,
            "anti_claim_exported": False,
            "private_scan_hits_exported": False,
            "private_scan_scope_exported": False,
            "stdout_stderr_bodies_exported": False,
            "proof_bodies_exported": False,
            "provider_payloads_exported": False,
        },
        "receipt_summary": {
            "receipt_count": _list_count(receipt_paths),
            "full_receipts_written": bool(receipt_paths),
            "receipt_paths_exported": False,
        },
        "output_economy": {
            "output_profile": "compact_card",
            "omitted_full_payload_keys": omitted,
            "body_in_receipt": False,
            "body_redacted": True,
        },
    }


def write_receipts(
    out_dir: str | Path,
    result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    """
    [ACTION]
    - Teleology: Implements `write_receipts` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root_path = Path(public_root).resolve(strict=False)
    acceptance_path = (
        Path(acceptance_out)
        if acceptance_out is not None
        else public_root_path / ACCEPTANCE_RECEIPT_REL
    )
    if not acceptance_path.is_absolute():
        acceptance_path = Path.cwd() / acceptance_path
    paths = {
        "formal_math_lean_proof_witness_result": target / RESULT_NAME,
        "lean_proof_witness_board": target / BOARD_NAME,
        "formal_math_lean_proof_witness_validation_receipt": target
        / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = _relative_receipt_paths(paths, public_root_path)

    result_receipt = _common_receipt(
        result,
        schema_version="formal_math_lean_proof_witness_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board = _common_receipt(
        result,
        schema_version="formal_math_lean_proof_witness_board_v1",
        receipt_paths=receipt_paths,
    )
    board.update(result["lean_witness_board"])
    validation = _common_receipt(
        result,
        schema_version="formal_math_lean_proof_witness_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "lean_build_status": PASS
            if result["lake_build"]["return_code"] == 0
            else "blocked",
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "invalid_proof_rejected": "invalid_proof_rejected"
            in result["observed_negative_cases"],
            "forbidden_import_rejected": "mathlib_import_forbidden"
            in result["observed_negative_cases"],
            "private_source_refs_rejected": "private_source_ref_forbidden"
            in result["observed_negative_cases"],
            "manifest_proof_bodies_rejected": "proof_body_in_manifest_forbidden"
            in result["observed_negative_cases"],
            "receipts_include_proof_bodies": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="formal_math_lean_proof_witness_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "lean_witness_deferred": False,
            "accepted_scope": "tiny_public_lake_project_only",
        }
    )

    write_json_atomic(paths["formal_math_lean_proof_witness_result"], result_receipt)
    write_json_atomic(paths["lean_proof_witness_board"], board)
    write_json_atomic(paths["formal_math_lean_proof_witness_validation_receipt"], validation)
    write_json_atomic(paths["fixture_acceptance"], acceptance)
    return {name: _display(path, public_root=public_root_path) for name, path in paths.items()}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.formal_math_lean_proof_witness run "
        f"--input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["receipt_paths"] = list(
        write_receipts(
            out_dir,
            result,
            public_root=_public_root_for_path(input_path),
            acceptance_out=acceptance_out,
        ).values()
    )
    return result


def run_witness_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_witness_bundle` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.formal_math_lean_proof_witness "
        f"run-witness-bundle --input {input_dir} --out {out_dir}"
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    public_root = _public_root_for_path(input_path)
    result_path = target / BUNDLE_RESULT_NAME
    cached = _fresh_bundle_receipt(
        input_dir=input_path,
        result_path=result_path,
        public_root=public_root,
        command=command_text,
    )
    if cached is not None:
        return cached
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_lean_proof_witness_bundle",
        include_negative=False,
    )
    target.mkdir(parents=True, exist_ok=True)
    receipt = _common_receipt(
        result,
        schema_version="exported_lean_proof_witness_bundle_validation_result_v1",
        receipt_paths=[_display(result_path, public_root=public_root)],
    )
    write_json_atomic(result_path, receipt)
    written_receipt = normalize_public_receipt_paths(receipt)
    result["receipt_paths"] = written_receipt["receipt_paths"]
    return result


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.formal_math_lean_proof_witness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="formal_math_lean_proof_witness")
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-witness-bundle"):
        action_parser = subparsers.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "run":
        acceptance_suffix = (
            f" --acceptance-out {args.acceptance_out}"
            if args.acceptance_out
            else ""
        )
        card_suffix = " --card" if args.card else ""
        command = (
            "python -m microcosm_core.organs.formal_math_lean_proof_witness "
            f"run --input {args.input} --out {args.out}"
            f"{acceptance_suffix}{card_suffix}"
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
            "python -m microcosm_core.organs.formal_math_lean_proof_witness "
            f"run-witness-bundle --input {args.input} --out {args.out}"
            f"{card_suffix}"
        )
        result = run_witness_bundle(args.input, args.out, command=command)
    output = result_card(result) if args.card else result
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
