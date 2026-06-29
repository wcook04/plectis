"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.formal_math_readiness_gate` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, READINESS_RESULT_NAME, READINESS_BOARD_NAME, READINESS_EXTENSION_BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, SOURCE_MODULE_MANIFEST_NAME, BODY_MATERIAL_STATUS, SOURCE_MODULE_IMPORT_STATUS, CARD_SCHEMA_VERSION, TACTIC_PORTFOLIO_EVIDENCE_REF, PUBLIC_SAFE_BODY_CLASSES, HASH_CHUNK_SIZE, FORBIDDEN_BODY_KEYS, AUTHORITY_CEILING, ANTI_CLAIM, EXTENSION_CELL_ID, EXTENSION_SOURCE_INTAKE_REF, SELECTED_PATTERN_IDS, EXTENSION_TARGET_REFS, EXPECTED_NEGATIVE_CASES, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.receipts, microcosm_core.schemas, microcosm_core.secret_exclusion_scan
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "formal_math_readiness_gate"
FIXTURE_ID = "first_wave.formal_math_readiness_gate"
VALIDATOR_ID = "validator.microcosm.organs.formal_math_readiness_gate"

READINESS_RESULT_NAME = "readiness_gate_result.json"
READINESS_BOARD_NAME = "formal_math_readiness_board.json"
READINESS_EXTENSION_BOARD_NAME = "formal_math_readiness_extension_board.json"
VALIDATION_RECEIPT_NAME = "formal_math_readiness_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/formal_math_readiness_gate_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_formal_math_readiness_bundle_validation_result.json"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
BODY_MATERIAL_STATUS = "copied_non_secret_macro_readiness_probe_body_with_provenance"
SOURCE_MODULE_IMPORT_STATUS = "copied_formal_readiness_source_modules_verified"
CARD_SCHEMA_VERSION = "formal_math_readiness_gate_command_card_v1"
TACTIC_PORTFOLIO_EVIDENCE_REF = (
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/"
    "tactic_affordance_probe/portfolio_core_v0/tactic_portfolio_availability.json"
)
PUBLIC_SAFE_BODY_CLASSES = {
    "public_macro_pattern_body",
    "public_macro_tool_body",
    "public_macro_receipt_body",
    "public_macro_proof_body",
}
HASH_CHUNK_SIZE = 1024 * 1024

FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "provider_output_body",
    "oracle_needed_premise_ids",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "formal_math_readiness_real_runtime_receipt_not_lean_or_formal_proof_authority",
    "lean_lake_execution_authorized": False,
    "mathlib_presence_claim_authorized": False,
    "formal_proof_authority": False,
    "provider_calls_authorized": False,
    "copied_public_probe_bodies_allowed": True,
    "private_theorem_proof_bodies_allowed": False,
    "proof_bodies_allowed": False,
}
ANTI_CLAIM = (
    "Formal math readiness gate emits a real runtime receipt over imported readiness "
    "fixtures and source refs. It does not run Lean or Lake, call providers, expose "
    "private theorem proof bodies, prove theorem correctness, authorize "
    "Mathlib-dependent proofs, or widen the bounded formal_math_lean_proof_witness "
    "boundary."
)

EXTENSION_CELL_ID = "formal_math_readiness_extensions"
EXTENSION_SOURCE_INTAKE_REF = (
    "receipts/first_wave/macro_projection_import_protocol/"
    "projection_import_intake_board.json#formal_math_readiness_extensions"
)
SELECTED_PATTERN_IDS = [
    "lean_std_toolchain_premise_index",
    "tactic_portfolio_availability_probe",
    "target_shape_tactic_routing_gate",
]
EXTENSION_TARGET_REFS = [
    "fixtures/first_wave/formal_math_readiness_gate/input/premise_index.json",
    "fixtures/first_wave/formal_math_readiness_gate/input/tactic_portfolio_availability.json",
    "fixtures/first_wave/formal_math_readiness_gate/input/target_shape_tactic_routing.json",
    "receipts/first_wave/formal_math_readiness_gate/formal_math_readiness_extension_board.json",
]

EXPECTED_NEGATIVE_CASES = {
    "corpus_readiness_overclaims_mathlib": ["MATHLIB_AVAILABILITY_OVERCLAIM"],
    "tactic_availability_without_probe": ["TACTIC_AVAILABILITY_UNPROBED"],
    "premise_index_proof_body_forbidden": ["PREMISE_INDEX_PROOF_BODY_FORBIDDEN"],
    "routing_allows_unavailable_tactic": ["ROUTING_ALLOWS_UNAVAILABLE_TACTIC"],
    "provider_context_recipe_overclaim": [
        "PROVIDER_RECIPE_BUDGET_EXCEEDED",
        "PROVIDER_RECIPE_PROOF_BODY_FORBIDDEN",
    ],
}

INPUT_NAMES = (
    "corpus_readiness.json",
    "tactic_portfolio_availability.json",
    "premise_index.json",
    "target_shape_tactic_routing.json",
    "provider_context_recipes.json",
)

NEGATIVE_INPUT_NAMES = (
    "corpus_readiness_overclaims_mathlib.json",
    "tactic_claims_availability_without_probe.json",
    "premise_index_with_proof_body.json",
    "routing_allows_unavailable_tactic.json",
    "provider_context_recipe_overclaim.json",
)


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_display` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_rows` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
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


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return {Path(name).stem: read_json_strict(input_dir / name) for name in names}


def _source_module_manifest_path(input_dir: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_path` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return input_dir / SOURCE_MODULE_MANIFEST_NAME


def _read_source_module_manifest(input_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_read_source_module_manifest` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return {}
    payload = read_json_strict(manifest_path)
    return payload if isinstance(payload, dict) else {}


def _source_module_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_rows` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _rows(manifest, "modules")


def _source_module_target_path(input_dir: Path, row: dict[str, Any]) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_target_path` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    path_target = _source_module_path_target(input_dir, row)
    if path_target is not None:
        return path_target
    target_ref_target = _source_module_target_ref_path(input_dir, row)
    return target_ref_target if target_ref_target is not None else input_dir


def _source_module_path_target(input_dir: Path, row: dict[str, Any]) -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_source_module_path_target` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    row_path = str(row.get("path") or "")
    return input_dir / row_path if row_path else None


def _source_module_target_ref_path(input_dir: Path, row: dict[str, Any]) -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_source_module_target_ref_path` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    target_ref = _strip_microcosm_prefix(str(row.get("target_ref") or ""))
    if not target_ref:
        return None
    public_root = _public_root_for_path(input_dir)
    return public_root / target_ref


def _source_module_source_path(public_root: Path, row: dict[str, Any]) -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_source_module_source_path` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source_ref = str(row.get("source_ref") or "")
    if not source_ref:
        return None
    if source_ref.startswith("microcosm-substrate/"):
        return public_root / _strip_microcosm_prefix(source_ref)
    return public_root.parent / source_ref


def _public_ref_path(public_root: Path, ref: object) -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_public_ref_path` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = str(ref or "")
    if not value:
        return None
    return public_root / _strip_microcosm_prefix(value)


def _source_artifact_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_artifact_paths` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest = _read_source_module_manifest(input_dir)
    return [
        _source_module_target_path(input_dir, row)
        for row in _source_module_rows(manifest)
    ]


def _fixture_manifest_source_binding(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_fixture_manifest_source_binding` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = (
        public_root
        / "core/fixture_manifests/formal_math_readiness_gate.fixture_manifest.json"
    )
    if not manifest_path.is_file():
        return {}
    fixture_manifest = read_json_strict(manifest_path)
    source_open = fixture_manifest.get("source_open_body_imports", {})
    if not isinstance(source_open, dict):
        return {}
    raw_manifest_refs = source_open.get("source_manifest_refs", [])
    manifest_refs = (
        [str(ref) for ref in raw_manifest_refs if ref]
        if isinstance(raw_manifest_refs, list)
        else []
    )
    source_refs = source_open.get("source_refs", [])
    target_refs = source_open.get("target_refs", [])
    body_count = int(
        fixture_manifest.get("body_copied_material_count")
        or source_open.get("body_material_count")
        or 0
    )
    status = str(source_open.get("status") or PASS)
    return {
        "body_copied_material_count": body_count,
        "source_module_count": body_count,
        "verified_source_module_count": body_count if status == PASS else 0,
        "source_module_manifest_status": status,
        "source_module_manifest_ref": manifest_refs[0] if manifest_refs else None,
        "source_manifest_refs": manifest_refs,
        "source_module_imports": {
            "status": status,
            "source_module_import_status": status,
            "module_count": body_count,
            "verified_module_count": body_count if status == PASS else 0,
            "source_module_manifest_ref": manifest_refs[0] if manifest_refs else None,
            "source_refs": [str(ref) for ref in source_refs]
            if isinstance(source_refs, list)
            else [],
            "target_refs": [str(ref) for ref in target_refs]
            if isinstance(target_refs, list)
            else [],
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        },
        "source_open_body_imports": {
            **source_open,
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        },
    }


def _local_lean_lake_mathlib_evidence(
    *,
    public_root: Path,
    source_manifest_refs: list[str],
    target_refs: list[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_local_lean_lake_mathlib_evidence` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    manifest_paths = [
        path
        for ref in source_manifest_refs
        if (path := _public_ref_path(public_root, ref)) is not None
    ]
    target_paths = [
        path for ref in target_refs if (path := _public_ref_path(public_root, ref)) is not None
    ]
    existing_target_refs: list[str] = []
    missing_target_refs: list[str] = []
    for ref, path in zip(target_refs, target_paths, strict=False):
        if path.is_file():
            existing_target_refs.append(str(ref))
        else:
            missing_target_refs.append(str(ref))

    corpus_path = next(
        (
            path
            for ref, path in zip(target_refs, target_paths, strict=False)
            if str(ref).endswith("/corpus_readiness.json")
        ),
        None,
    )
    tactic_path = next(
        (
            path
            for ref, path in zip(target_refs, target_paths, strict=False)
            if str(ref).endswith(TACTIC_PORTFOLIO_EVIDENCE_REF)
        ),
        None,
    )
    mathlib_probe_paths = [
        path
        for ref, path in zip(target_refs, target_paths, strict=False)
        if str(ref).endswith("/mathlib_probe.lean")
    ]
    lean_probe_paths = [
        path
        for path in target_paths
        if path.suffix == ".lean" and path.is_file()
    ]
    corpus_payload = (
        read_json_strict(corpus_path)
        if corpus_path is not None and corpus_path.is_file()
        else {}
    )
    tactic_payload = (
        read_json_strict(tactic_path)
        if tactic_path is not None and tactic_path.is_file()
        else {}
    )
    lean_cli = corpus_payload.get("lean_cli", {}) if isinstance(corpus_payload, dict) else {}
    tactic_rows = _rows(tactic_payload, "rows")
    mathlib_probe_import_seen = any(
        path.is_file() and "import Mathlib" in path.read_text(encoding="utf-8")
        for path in mathlib_probe_paths
    )
    std_probe_file_count = sum(
        1
        for path in lean_probe_paths
        if path.name != "mathlib_probe.lean"
        and "import Std" in path.read_text(encoding="utf-8")
    )
    available_tactic_ids = sorted(
        str(row.get("tactic_id"))
        for row in tactic_rows
        if row.get("available") is True and row.get("tactic_id")
    )
    unavailable_tactic_ids = sorted(
        str(row.get("tactic_id"))
        for row in tactic_rows
        if row.get("available") is False and row.get("tactic_id")
    )
    manifest_refs_exist = bool(manifest_paths) and all(
        path.is_file() for path in manifest_paths
    )
    corpus_bound = (
        isinstance(corpus_payload, dict)
        and corpus_payload.get("mathlib_available") is False
        and isinstance(lean_cli, dict)
        and lean_cli.get("lean_available") is True
        and lean_cli.get("lake_available") is True
    )
    tactic_bound = bool(available_tactic_ids) and "aesop" in unavailable_tactic_ids
    bound = (
        manifest_refs_exist
        and bool(target_refs)
        and not missing_target_refs
        and corpus_bound
        and tactic_bound
        and mathlib_probe_import_seen
        and std_probe_file_count > 0
    )
    return {
        "schema_version": "formal_math_readiness_local_lean_lake_mathlib_evidence_v1",
        "local_evidence_bound": bound,
        "manifest_refs_exist": manifest_refs_exist,
        "source_manifest_refs": source_manifest_refs,
        "target_ref_count": len(target_refs),
        "existing_target_ref_count": len(existing_target_refs),
        "missing_target_refs": missing_target_refs,
        "corpus_readiness_ref": _display(corpus_path, public_root=public_root)
        if corpus_path
        else None,
        "tactic_portfolio_ref": _display(tactic_path, public_root=public_root)
        if tactic_path
        else None,
        "lean_available": (
            lean_cli.get("lean_available") is True if isinstance(lean_cli, dict) else False
        ),
        "lake_available": (
            lean_cli.get("lake_available") is True if isinstance(lean_cli, dict) else False
        ),
        "mathlib_available": (
            corpus_payload.get("mathlib_available") is True
            if isinstance(corpus_payload, dict)
            else False
        ),
        "mathlib_probe_import_seen": mathlib_probe_import_seen,
        "lean_probe_file_count": len(lean_probe_paths),
        "std_probe_file_count": std_probe_file_count,
        "available_tactic_ids": available_tactic_ids,
        "unavailable_tactic_ids": unavailable_tactic_ids,
        "body_in_receipt": False,
    }


def _ref_matches_suffix(ref: object, suffix: str) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_ref_matches_suffix` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(ref or "").endswith(suffix)


def _has_tactic_probe_evidence_refs(binding: dict[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_has_tactic_probe_evidence_refs` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source_refs = _strings(binding.get("source_refs"))
    target_refs = _strings(binding.get("target_refs"))
    return any(
        _ref_matches_suffix(ref, TACTIC_PORTFOLIO_EVIDENCE_REF) for ref in source_refs
    ) or any(
        _ref_matches_suffix(ref, TACTIC_PORTFOLIO_EVIDENCE_REF)
        for ref in target_refs
    )


def _source_import_tactic_probe_evidence(
    source_imports: dict[str, Any],
    *,
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_import_tactic_probe_evidence` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source_refs = _strings(source_imports.get("source_refs"))
    target_refs = _strings(source_imports.get("target_refs"))
    manifest_ref = str(source_imports.get("source_module_manifest_ref") or "")
    local_evidence = _local_lean_lake_mathlib_evidence(
        public_root=public_root,
        source_manifest_refs=[manifest_ref] if manifest_ref else [],
        target_refs=target_refs,
    )
    bound = (
        source_imports.get("source_modules_pass") is True
        and bool(int(source_imports.get("copied_source_artifact_count") or 0))
        and local_evidence["local_evidence_bound"] is True
        and (
            any(
                _ref_matches_suffix(ref, TACTIC_PORTFOLIO_EVIDENCE_REF)
                for ref in source_refs
            )
            or any(
                _ref_matches_suffix(ref, TACTIC_PORTFOLIO_EVIDENCE_REF)
                for ref in target_refs
            )
        )
    )
    return {
        "source": "source_module_imports",
        "tactic_probe_evidence_bound": bound,
        "source_modules_pass": source_imports.get("source_modules_pass") is True,
        "copied_source_artifact_count": int(
            source_imports.get("copied_source_artifact_count") or 0
        ),
        "required_evidence_ref": TACTIC_PORTFOLIO_EVIDENCE_REF,
        "source_refs": source_refs,
        "target_refs": target_refs,
        "local_lean_lake_mathlib_evidence": local_evidence,
    }


def _fixture_manifest_tactic_probe_evidence(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_fixture_manifest_tactic_probe_evidence` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    binding = _fixture_manifest_source_binding(public_root)
    source_imports = binding.get("source_module_imports", {})
    source_refs = (
        _strings(source_imports.get("source_refs"))
        if isinstance(source_imports, dict)
        else []
    )
    target_refs = (
        _strings(source_imports.get("target_refs"))
        if isinstance(source_imports, dict)
        else []
    )
    source_manifest_refs = _strings(binding.get("source_manifest_refs"))
    local_evidence = _local_lean_lake_mathlib_evidence(
        public_root=public_root,
        source_manifest_refs=source_manifest_refs,
        target_refs=target_refs,
    )
    bound = (
        binding.get("source_module_manifest_status") == PASS
        and int(binding.get("body_copied_material_count") or 0) > 0
        and local_evidence["local_evidence_bound"] is True
        and _has_tactic_probe_evidence_refs(
            {"source_refs": source_refs, "target_refs": target_refs}
        )
    )
    return {
        "source": "fixture_manifest_source_open_body_imports",
        "tactic_probe_evidence_bound": bound,
        "source_module_manifest_status": binding.get("source_module_manifest_status"),
        "body_copied_material_count": int(
            binding.get("body_copied_material_count") or 0
        ),
        "required_evidence_ref": TACTIC_PORTFOLIO_EVIDENCE_REF,
        "source_refs": source_refs,
        "target_refs": target_refs,
        "source_manifest_refs": source_manifest_refs,
        "local_lean_lake_mathlib_evidence": local_evidence,
    }


def _tactic_probe_realness_evidence(
    *,
    input_mode: str,
    source_imports: dict[str, Any],
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_tactic_probe_realness_evidence` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    candidates = [
        _source_import_tactic_probe_evidence(
            source_imports,
            public_root=public_root,
        )
    ]
    if input_mode.startswith("first_wave_fixture"):
        candidates.append(_fixture_manifest_tactic_probe_evidence(public_root))
    bound = any(row["tactic_probe_evidence_bound"] for row in candidates)
    return {
        "schema_version": "formal_math_readiness_realness_evidence_v1",
        "tactic_probe_evidence_bound": bound,
        "synthetic_probe_labels_allowed": bound,
        "required_evidence_ref": TACTIC_PORTFOLIO_EVIDENCE_REF,
        "candidate_bindings": candidates,
    }


def _is_synthetic_probe_ref(ref: object) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_is_synthetic_probe_ref` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(ref or "").startswith("synthetic_probe:")


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest_path = _source_module_manifest_path(input_dir)
    if manifest_path.is_file():
        paths.append(manifest_path)
    paths.extend(_source_artifact_paths(input_dir))
    return paths


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _strip_microcosm_prefix(ref: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_strip_microcosm_prefix` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
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
    return f"sha256:{digest.hexdigest()}"


def _normalize_sha256(value: object) -> str:
    """
    [ACTION]
    - Teleology: Implements `_normalize_sha256` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    digest = str(value or "")
    if digest and not digest.startswith("sha256:"):
        return f"sha256:{digest}"
    return digest


def _line_count(path: Path) -> int:
    """
    [ACTION]
    - Teleology: Implements `_line_count` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    line_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_count, _line in enumerate(handle, start=1):
            pass
    return line_count or 1


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
    - Teleology: Implements `_finding` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
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
        "body_in_receipt": False,
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
    - Teleology: Implements `_record` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
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
    observed[case_id].add(code)


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    """
    [ACTION]
    - Teleology: Implements `_merge_observed` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_merge_findings` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return findings


def _unexpected_findings(
    findings: list[dict[str, Any]],
    expected: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_unexpected_findings` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    expected_codes = {case_id: set(codes) for case_id, codes in expected.items()}
    unexpected: list[dict[str, Any]] = []
    for finding in findings:
        case_id = str(finding.get("negative_case_id") or "")
        code = str(finding.get("error_code") or "")
        if code not in expected_codes.get(case_id, set()):
            unexpected.append(finding)
    return unexpected


def _forbidden_body_keys(row: dict[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_forbidden_body_keys` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return sorted(key for key in FORBIDDEN_BODY_KEYS if key in row)


def validate_corpus_readiness(
    payload: object,
    negative_payload: object | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_corpus_readiness` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "corpora")
    blocked_capabilities: list[str] = []
    corpus_rows: list[dict[str, Any]] = []
    for row in rows:
        corpus_id = str(row.get("corpus_id") or "corpus")
        mathlib_available = row.get("mathlib_available") is True
        mathlib_probe_status = str(row.get("mathlib_probe_status") or "unknown")
        if not mathlib_available:
            blocked_capabilities.append(f"{corpus_id}:mathlib")
        corpus_rows.append(
            {
                "corpus_id": corpus_id,
                "lean_available": row.get("lean_available") is True,
                "mathlib_available": mathlib_available,
                "mathlib_probe_status": mathlib_probe_status,
                "translation_smoke_only": row.get("translation_smoke_only") is True,
                "consumer_rule": row.get("consumer_rule"),
                "body_in_receipt": False,
            }
        )

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        corpus_id = str(row.get("corpus_id") or "corpus")
        if row.get("mathlib_available") is True and row.get("mathlib_probe_status") != PASS:
            _record(
                findings,
                observed,
                "MATHLIB_AVAILABILITY_OVERCLAIM",
                "Corpus readiness attempted to claim Mathlib availability without a passing probe.",
                case_id=f"{corpus_id}:positive_corpus_readiness",
                subject_id=corpus_id,
                subject_kind="corpus_readiness",
            )
    if isinstance(negative_payload, dict):
        subject_id = str(negative_payload.get("corpus_id") or "corpus_readiness")
        case_id = str(
            negative_payload.get("expected_negative_case_id")
            or "corpus_readiness_overclaims_mathlib"
        )
        overclaims = (
            negative_payload.get("claims_mathlib_available") is True
            or (
                negative_payload.get("mathlib_available") is True
                and negative_payload.get("mathlib_probe_status") != "PASS"
            )
        )
        if overclaims:
            _record(
                findings,
                observed,
                "MATHLIB_AVAILABILITY_OVERCLAIM",
                "Corpus readiness attempted to claim Mathlib availability without a passing probe.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="corpus_readiness",
            )
    return {
        "corpora": sorted(corpus_rows, key=lambda item: item["corpus_id"]),
        "blocked_capabilities": sorted(blocked_capabilities),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_tactic_portfolio(
    payload: object,
    negative_payload: object | None = None,
    *,
    realness_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_tactic_portfolio` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    tactics: list[dict[str, Any]] = []
    available: list[str] = []
    unavailable: list[str] = []
    for row in _rows(payload, "tactics"):
        tactic_id = str(row.get("tactic_id") or "")
        status = str(row.get("availability_status") or "unknown")
        if status == PASS:
            available.append(tactic_id)
        else:
            unavailable.append(tactic_id)
        tactics.append(
            {
                "tactic_id": tactic_id,
                "availability_status": status,
                "probe_receipt_ref": row.get("probe_receipt_ref"),
                "failure_class": row.get("failure_class"),
                "body_in_receipt": False,
            }
        )

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in _rows(payload, "tactics"):
        tactic_id = str(row.get("tactic_id") or "tactic")
        probe_receipt_ref = row.get("probe_receipt_ref")
        if (
            str(row.get("availability_status") or "unknown") == PASS
            and not probe_receipt_ref
        ):
            _record(
                findings,
                observed,
                "TACTIC_AVAILABILITY_UNPROBED",
                "Tactic availability was claimed without a probe receipt.",
                case_id=f"{tactic_id}:positive_tactic_availability",
                subject_id=tactic_id,
                subject_kind="tactic_availability",
            )
        if _is_synthetic_probe_ref(probe_receipt_ref) and not (
            realness_evidence
            and realness_evidence.get("tactic_probe_evidence_bound") is True
        ):
            _record(
                findings,
                observed,
                "TACTIC_PROBE_SYNTHETIC_UNBOUND",
                "Synthetic tactic probe labels require a copied source body or "
                "fixture-manifest evidence binding.",
                case_id=f"{tactic_id}:positive_tactic_probe_realness",
                subject_id=tactic_id,
                subject_kind="tactic_availability",
            )
    if isinstance(negative_payload, dict):
        subject_id = str(negative_payload.get("tactic_id") or "tactic")
        case_id = str(
            negative_payload.get("expected_negative_case_id")
            or "tactic_availability_without_probe"
        )
        if negative_payload.get("claims_available") is True and not negative_payload.get(
            "probe_receipt_ref"
        ):
            _record(
                findings,
                observed,
                "TACTIC_AVAILABILITY_UNPROBED",
                "Tactic availability was claimed without a probe receipt.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="tactic_availability",
            )
    return {
        "tactics": sorted(tactics, key=lambda item: item["tactic_id"]),
        "available_tactic_ids": sorted(tactic for tactic in available if tactic),
        "unavailable_tactic_ids": sorted(tactic for tactic in unavailable if tactic),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "realness_evidence": realness_evidence or {},
    }


def validate_premise_index(
    payload: object,
    negative_payload: object | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_premise_index` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    entries: list[dict[str, Any]] = []
    for row in _rows(payload, "premises"):
        entries.append(
            {
                "premise_id": row.get("premise_id"),
                "namespace": row.get("namespace"),
                "retrieval_term_count": len(row.get("retrieval_terms", []))
                if isinstance(row.get("retrieval_terms"), list)
                else 0,
                "allowed_for_split": row.get("allowed_for_split", []),
                "source_ref": row.get("source_ref"),
                "body_in_receipt": False,
            }
        )

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in _rows(payload, "premises"):
        premise_id = str(row.get("premise_id") or "premise")
        forbidden = _forbidden_body_keys(row)
        if forbidden:
            _record(
                findings,
                observed,
                "PREMISE_INDEX_PROOF_BODY_FORBIDDEN",
                "Premise index included forbidden proof/oracle body fields.",
                case_id=f"{premise_id}:positive_premise_index",
                subject_id=premise_id,
                subject_kind="premise_index",
            )
    if isinstance(negative_payload, dict):
        case_id = str(
            negative_payload.get("expected_negative_case_id")
            or "premise_index_proof_body_forbidden"
        )
        for row in _rows(negative_payload, "premises"):
            premise_id = str(row.get("premise_id") or "premise")
            forbidden = _forbidden_body_keys(row)
            if forbidden:
                _record(
                    findings,
                    observed,
                    "PREMISE_INDEX_PROOF_BODY_FORBIDDEN",
                    "Premise index included forbidden proof/oracle body fields.",
                    case_id=case_id,
                    subject_id=premise_id,
                    subject_kind="premise_index",
                )
    return {
        "premise_count": len(entries),
        "premises": sorted(entries, key=lambda item: str(item["premise_id"])),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_target_shape_routing(
    payload: object,
    *,
    unavailable_tactic_ids: list[str],
    negative_payload: object | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_target_shape_routing` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    unavailable = set(unavailable_tactic_ids)
    cases: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)

    def add_case(row: dict[str, Any], *, negative: bool) -> None:
        """
        [ACTION]
        - Teleology: Implements `validate_target_shape_routing.add_case` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        route_case_id = str(row.get("route_case_id") or "route_case")
        allowed = [str(item) for item in row.get("allowed_tactic_ids", []) if isinstance(item, str)]
        blocked = sorted(set(allowed) & unavailable)
        cases.append(
            {
                "route_case_id": route_case_id,
                "target_shape": row.get("target_shape"),
                "allowed_tactic_ids": allowed,
                "blocked_unavailable_tactic_ids": blocked,
                "body_in_receipt": False,
            }
        )
        if blocked:
            _record(
                findings,
                observed,
                "ROUTING_ALLOWS_UNAVAILABLE_TACTIC",
                "Target-shape routing allowed a tactic marked unavailable by the portfolio probe.",
                case_id=str(
                    row.get("expected_negative_case_id")
                    or (
                        "routing_allows_unavailable_tactic"
                        if negative
                        else f"{route_case_id}:positive_target_shape_routing"
                    )
                ),
                subject_id=route_case_id,
                subject_kind="target_shape_routing",
            )

    for row in _rows(payload, "route_cases"):
        add_case(row, negative=False)
    if isinstance(negative_payload, dict):
        for row in _rows(negative_payload, "route_cases"):
            add_case(row, negative=True)
    return {
        "route_case_count": len(cases),
        "route_cases": sorted(cases, key=lambda item: item["route_case_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_provider_context_recipes(
    payload: object,
    negative_payload: object | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_provider_context_recipes` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    recipes: list[dict[str, Any]] = []
    for row in _rows(payload, "recipes"):
        recipes.append(
            {
                "recipe_id": row.get("recipe_id"),
                "byte_budget": row.get("byte_budget"),
                "deliverable_type": row.get("deliverable_type"),
                "section_count": len(row.get("sections", []))
                if isinstance(row.get("sections"), list)
                else 0,
                "proof_bodies_allowed": row.get("proof_bodies_allowed") is True,
                "provider_calls_authorized": row.get("provider_calls_authorized") is True,
                "body_in_receipt": False,
            }
        )

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in _rows(payload, "recipes"):
        recipe_id = str(row.get("recipe_id") or "recipe")
        if int(row.get("byte_budget") or 0) > 32768:
            _record(
                findings,
                observed,
                "PROVIDER_RECIPE_BUDGET_EXCEEDED",
                "Provider context recipe exceeded the public readiness byte ceiling.",
                case_id=f"{recipe_id}:positive_provider_context_recipe",
                subject_id=recipe_id,
                subject_kind="provider_context_recipe",
            )
        if row.get("proof_bodies_allowed") is True or _forbidden_body_keys(row):
            _record(
                findings,
                observed,
                "PROVIDER_RECIPE_PROOF_BODY_FORBIDDEN",
                "Provider context recipe allowed or embedded proof body material.",
                case_id=f"{recipe_id}:positive_provider_context_recipe",
                subject_id=recipe_id,
                subject_kind="provider_context_recipe",
            )
    if isinstance(negative_payload, dict):
        case_id = str(
            negative_payload.get("expected_negative_case_id")
            or "provider_context_recipe_overclaim"
        )
        for row in _rows(negative_payload, "recipes"):
            recipe_id = str(row.get("recipe_id") or "recipe")
            if int(row.get("byte_budget") or 0) > 32768:
                _record(
                    findings,
                    observed,
                    "PROVIDER_RECIPE_BUDGET_EXCEEDED",
                    "Provider context recipe exceeded the public readiness byte ceiling.",
                    case_id=case_id,
                    subject_id=recipe_id,
                    subject_kind="provider_context_recipe",
                )
            if row.get("proof_bodies_allowed") is True or _forbidden_body_keys(row):
                _record(
                    findings,
                    observed,
                    "PROVIDER_RECIPE_PROOF_BODY_FORBIDDEN",
                    "Provider context recipe allowed or embedded proof body material.",
                    case_id=case_id,
                    subject_id=recipe_id,
                    subject_kind="provider_context_recipe",
                )
    return {
        "recipes": sorted(recipes, key=lambda item: str(item["recipe_id"])),
        "recipe_count": len(recipes),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_source_module_imports(
    input_dir: Path,
    *,
    required: bool,
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_source_module_imports` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    manifest = _read_source_module_manifest(input_dir)
    rows = _source_module_rows(manifest)
    findings: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []

    manifest_ref = _display(manifest_path, public_root=public_root)
    if required and not manifest_path.is_file():
        findings.append(
            _finding(
                "FORMAL_READINESS_SOURCE_MODULE_MANIFEST_MISSING",
                "Exported formal readiness bundle must include a source_module_manifest.json for copied macro readiness/probe bodies.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if manifest_path.is_file() and manifest.get("source_import_class") != (
        "copied_non_secret_macro_body"
    ):
        findings.append(
            _finding(
                "FORMAL_READINESS_SOURCE_IMPORT_CLASS_UNSUPPORTED",
                "Formal readiness source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if required and manifest_path.is_file() and not rows:
        findings.append(
            _finding(
                "FORMAL_READINESS_SOURCE_MODULE_ROWS_MISSING",
                "Exported formal readiness bundle must carry at least one copied source module row.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )

    for row in rows:
        module_id = str(row.get("module_id") or "source_module")
        path_target = _source_module_path_target(input_dir, row)
        target_ref_target = _source_module_target_ref_path(input_dir, row)
        target = path_target or target_ref_target or input_dir
        source = _source_module_source_path(public_root, row)
        source_digest = _normalize_sha256(row.get("source_sha256")) or _normalize_sha256(
            row.get("sha256")
        )
        target_digest = _normalize_sha256(row.get("target_sha256")) or _normalize_sha256(
            row.get("sha256")
        )
        exists = target.is_file()
        actual_digest = _sha256(target) if exists else None
        source_exists = bool(source and source.is_file())
        actual_source_digest = _sha256(source) if source_exists and source else None
        source_digest_match = (
            actual_source_digest == source_digest
            if source_exists and source_digest
            else None
        )
        material_class = str(row.get("material_class") or "")
        source_ref = str(row.get("source_ref") or "")
        target_ref = _display(target, public_root=public_root)
        path_target_ref = (
            _display(path_target, public_root=public_root) if path_target else ""
        )
        declared_target_ref = (
            _display(target_ref_target, public_root=public_root)
            if target_ref_target
            else ""
        )
        target_ref_matches_path = not (
            path_target
            and target_ref_target
            and path_target.resolve(strict=False)
            != target_ref_target.resolve(strict=False)
        )
        digest_match = actual_digest == target_digest
        row_body_in_receipt = row.get("body_in_receipt") is True
        import_row = {
            "module_id": module_id,
            "source_ref": source_ref,
            "target_ref": target_ref,
            "path_target_ref": path_target_ref,
            "declared_target_ref": declared_target_ref,
            "target_ref_matches_path": target_ref_matches_path,
            "material_class": material_class,
            "source_sha256": source_digest,
            "actual_source_sha256": actual_source_digest,
            "expected_target_sha256": target_digest,
            "target_sha256": actual_digest,
            "source_exists": source_exists,
            "exists": exists,
            "digest_match": digest_match,
            "source_digest_match": source_digest_match,
            "source_to_target_relation": str(
                row.get("source_to_target_relation") or "exact_copy"
            ),
            "verification_mode": str(
                row.get("verification_mode") or "exact_source_digest_match"
            ),
            "public_safe_transform": row.get("public_safe_transform"),
            "source_line_count": _line_count(target) if exists else None,
            "target_line_count": _line_count(target) if exists else None,
            "body_in_receipt": False,
            "body_material_status": BODY_MATERIAL_STATUS,
        }
        imports.append(import_row)

        if str(row.get("source_import_class") or "") != "copied_non_secret_macro_body":
            findings.append(
                _finding(
                    "FORMAL_READINESS_SOURCE_MODULE_IMPORT_CLASS_UNSUPPORTED",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_BODY_CLASSES:
            findings.append(
                _finding(
                    "FORMAL_READINESS_SOURCE_MODULE_CLASS_UNSUPPORTED",
                    "Source module rows must use a public-safe macro body material class.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if row_body_in_receipt:
            findings.append(
                _finding(
                    "FORMAL_READINESS_SOURCE_BODY_RECEIPT_EXPORT_FORBIDDEN",
                    "Copied source module bodies may live in the bundle source_artifacts tree, not in generated receipts.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if not exists:
            findings.append(
                _finding(
                    "FORMAL_READINESS_SOURCE_MODULE_TARGET_MISSING",
                    "Copied source module target file is missing from the exported bundle.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if not target_ref_matches_path:
            findings.append(
                _finding(
                    "FORMAL_READINESS_SOURCE_MODULE_TARGET_REF_PATH_MISMATCH",
                    "Source module manifest path and target_ref must resolve to the same copied bundle body.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if source_digest_match is False:
            findings.append(
                _finding(
                    "FORMAL_READINESS_SOURCE_MODULE_SOURCE_DIGEST_MISMATCH",
                    "Declared source module digest must match the live source digest when source_ref is available.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        elif not digest_match:
            findings.append(
                _finding(
                    "FORMAL_READINESS_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Copied source module digest must match the manifest target digest.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )

    copied_count = sum(
        1
        for row in imports
        if row["exists"]
        and row["digest_match"]
        and row["target_ref_matches_path"]
        and row.get("source_digest_match") is not False
    )
    source_modules_pass = not findings
    return {
        "source_module_manifest_ref": manifest_ref,
        "source_module_import_status": SOURCE_MODULE_IMPORT_STATUS,
        "body_material_status": BODY_MATERIAL_STATUS,
        "source_module_imports": imports,
        "source_module_import_count": len(imports),
        "copied_source_artifact_count": copied_count,
        "source_modules_pass": source_modules_pass,
        "source_refs": sorted({row["source_ref"] for row in imports if row["source_ref"]}),
        "target_refs": [row["target_ref"] for row in imports],
        "material_classes": sorted(
            {row["material_class"] for row in imports if row["material_class"]}
        ),
        "findings": findings,
    }


def _count_values(values: list[Any]) -> dict[str, int]:
    """
    [ACTION]
    - Teleology: Implements `_count_values` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    counter = Counter(str(value) for value in values if value is not None)
    return {key: counter[key] for key in sorted(counter)}


def _count_split_eligibility(premises: list[dict[str, Any]]) -> dict[str, int]:
    """
    [ACTION]
    - Teleology: Implements `_count_split_eligibility` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    counts: Counter[str] = Counter()
    for premise in premises:
        for split in premise.get("allowed_for_split", []):
            if isinstance(split, str) and split:
                counts[split] += 1
    return {key: counts[key] for key in sorted(counts)}


def _build_extension_board(
    *,
    corpus: dict[str, Any],
    tactics: dict[str, Any],
    premise_index: dict[str, Any],
    routing: dict[str, Any],
    recipes: dict[str, Any],
    source_imports: dict[str, Any],
    input_mode: str,
    bundle_id: Any,
    secret_scan: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_extension_board` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    premises = premise_index["premises"]
    tactic_rows = tactics["tactics"]
    route_cases = routing["route_cases"]
    recipe_rows = recipes["recipes"]
    blocked_routes = [
        row["route_case_id"] for row in route_cases if row["blocked_unavailable_tactic_ids"]
    ]
    source_refs = sorted(
        {
            str(row.get("source_ref"))
            for row in premises
            if isinstance(row.get("source_ref"), str) and row.get("source_ref")
        }
    )
    tactic_status_counts = _count_values(
        [row.get("availability_status") for row in tactic_rows]
    )
    unavailable_mathlib_tactics = sorted(
        str(row["tactic_id"])
        for row in tactic_rows
        if row.get("failure_class") == "mathlib_import_absent"
    )
    copied_source_count = int(source_imports.get("copied_source_artifact_count") or 0)
    source_body_target_refs = _strings(source_imports.get("target_refs"))
    return {
        "schema_version": "formal_math_readiness_extension_board_v1",
        "cell_id": EXTENSION_CELL_ID,
        "projection_status": "public_runtime_import_landed" if status == PASS else "blocked",
        "source_intake_ref": EXTENSION_SOURCE_INTAKE_REF,
        "selected_pattern_ids": SELECTED_PATTERN_IDS,
        "input_mode": input_mode,
        "bundle_id": bundle_id,
        "source_refs": [
            "state/microcosm_portfolio/extracted_patterns_ledger.jsonl",
            "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json",
        ],
        "target_refs": [*EXTENSION_TARGET_REFS, *source_body_target_refs],
        "validation_refs": [
            "receipts/first_wave/formal_math_readiness_gate/formal_math_readiness_validation_receipt.json",
            "receipts/first_wave/formal_math_readiness_gate/formal_math_readiness_extension_board.json",
        ],
        "projection_contract": {
            "copy_policy": "real_runtime_receipt_with_secret_exclusion",
            "body_copied": copied_source_count > 0,
            "body_in_receipt": False,
            "real_substrate_receipt": True,
            "synthetic_receipt_standin_allowed": False,
            "credential_or_account_bound_bodies_allowed": False,
            "authority_ceiling": AUTHORITY_CEILING["authority_ceiling"],
        },
        "premise_index_projection": {
            "premise_count": premise_index["premise_count"],
            "namespace_counts": _count_values([row.get("namespace") for row in premises]),
            "split_eligibility_counts": _count_split_eligibility(premises),
            "source_ref_count": len(source_refs),
            "source_refs": source_refs,
            "retrieval_term_total": sum(
                int(row.get("retrieval_term_count") or 0) for row in premises
            ),
            "proof_bodies_excluded": True,
            "oracle_needed_premise_ids_excluded": True,
        },
        "tactic_portfolio_projection": {
            "available_tactic_count": len(tactics["available_tactic_ids"]),
            "available_tactic_ids": tactics["available_tactic_ids"],
            "unavailable_tactic_count": len(tactics["unavailable_tactic_ids"]),
            "unavailable_tactic_ids": tactics["unavailable_tactic_ids"],
            "availability_status_counts": tactic_status_counts,
            "mathlib_dependent_unavailable_tactic_ids": unavailable_mathlib_tactics,
            "probe_receipt_required": True,
        },
        "target_shape_routing_projection": {
            "route_case_count": routing["route_case_count"],
            "admissible_route_case_count": len(route_cases) - len(blocked_routes),
            "blocked_route_case_count": len(blocked_routes),
            "blocked_route_case_ids": sorted(blocked_routes),
            "routing_precedes_lean_calls": True,
            "routes": [
                {
                    "route_case_id": row["route_case_id"],
                    "target_shape": row.get("target_shape"),
                    "allowed_tactic_ids": row.get("allowed_tactic_ids", []),
                    "blocked_unavailable_tactic_ids": row.get(
                        "blocked_unavailable_tactic_ids", []
                    ),
                    "body_in_receipt": False,
                }
                for row in route_cases
            ],
        },
        "provider_context_projection": {
            "recipe_count": recipes["recipe_count"],
            "byte_budgets": {
                str(row.get("recipe_id")): row.get("byte_budget") for row in recipe_rows
            },
            "deliverable_types": {
                str(row.get("recipe_id")): row.get("deliverable_type")
                for row in recipe_rows
            },
            "proof_bodies_allowed": False,
            "provider_calls_authorized": False,
        },
        "corpus_projection": {
            "blocked_capabilities": corpus["blocked_capabilities"],
            "mathlib_available": not corpus["blocked_capabilities"],
            "lean_lake_execution_authorized": False,
        },
        "source_body_import_projection": {
            "source_module_manifest_ref": source_imports.get(
                "source_module_manifest_ref"
            ),
            "body_material_status": source_imports.get("body_material_status"),
            "source_module_import_status": source_imports.get(
                "source_module_import_status"
            ),
            "source_module_import_count": source_imports.get(
                "source_module_import_count"
            ),
            "copied_source_artifact_count": copied_source_count,
            "source_modules_pass": source_imports.get("source_modules_pass") is True,
            "source_refs": source_imports.get("source_refs", []),
            "target_refs": source_body_target_refs,
            "material_classes": source_imports.get("material_classes", []),
            "body_in_receipt": False,
        },
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_result` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )

    corpus = validate_corpus_readiness(
        payloads["corpus_readiness"],
        payloads.get("corpus_readiness_overclaims_mathlib"),
    )
    source_imports = validate_source_module_imports(
        input_dir,
        required=input_mode == "exported_formal_math_readiness_bundle",
        public_root=public_root,
    )
    realness_evidence = _tactic_probe_realness_evidence(
        input_mode=input_mode,
        source_imports=source_imports,
        public_root=public_root,
    )
    tactics = validate_tactic_portfolio(
        payloads["tactic_portfolio_availability"],
        payloads.get("tactic_claims_availability_without_probe"),
        realness_evidence=realness_evidence,
    )
    premise_index = validate_premise_index(
        payloads["premise_index"],
        payloads.get("premise_index_with_proof_body"),
    )
    routing = validate_target_shape_routing(
        payloads["target_shape_tactic_routing"],
        unavailable_tactic_ids=tactics["unavailable_tactic_ids"],
        negative_payload=payloads.get("routing_allows_unavailable_tactic"),
    )
    recipes = validate_provider_context_recipes(
        payloads["provider_context_recipes"],
        payloads.get("provider_context_recipe_overclaim"),
    )
    observed = _merge_observed(corpus, tactics, premise_index, routing, recipes)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        corpus,
        tactics,
        premise_index,
        routing,
        recipes,
        source_imports,
    )
    error_codes = sorted({finding["error_code"] for finding in findings})
    unexpected_findings = _unexpected_findings(findings, expected)
    status = (
        PASS
        if not missing
        and not secret_scan["blocking_hit_count"]
        and source_imports["source_modules_pass"]
        and not unexpected_findings
        else "blocked"
    )
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    extension_board = _build_extension_board(
        corpus=corpus,
        tactics=tactics,
        premise_index=premise_index,
        routing=routing,
        recipes=recipes,
        source_imports=source_imports,
        input_mode=input_mode,
        bundle_id=bundle_manifest.get("bundle_id") if isinstance(bundle_manifest, dict) else None,
        secret_scan=secret_scan,
        status=status,
    )
    return {
        "schema_version": "formal_math_readiness_gate_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id") if isinstance(bundle_manifest, dict) else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "realness_evidence": realness_evidence,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_material_status": BODY_MATERIAL_STATUS,
        "source_module_import_status": source_imports["source_module_import_status"],
        "source_module_manifest_ref": source_imports["source_module_manifest_ref"],
        "source_module_imports": source_imports["source_module_imports"],
        "source_module_import_count": source_imports["source_module_import_count"],
        "copied_source_artifact_count": source_imports["copied_source_artifact_count"],
        "source_modules_pass": source_imports["source_modules_pass"],
        "corpus_readiness": corpus["corpora"],
        "blocked_capabilities": corpus["blocked_capabilities"],
        "available_tactic_ids": tactics["available_tactic_ids"],
        "unavailable_tactic_ids": tactics["unavailable_tactic_ids"],
        "premise_count": premise_index["premise_count"],
        "route_case_count": routing["route_case_count"],
        "recipe_count": recipes["recipe_count"],
        "projection_cell_id": EXTENSION_CELL_ID,
        "selected_pattern_ids": SELECTED_PATTERN_IDS,
        "readiness_extension_status": extension_board["projection_status"],
        "readiness_extension_board": extension_board,
        "readiness_board": {
            "realness_evidence": realness_evidence,
            "mathlib_available": not corpus["blocked_capabilities"],
            "lean_lake_execution_authorized": False,
            "formal_proof_authority": False,
            "provider_calls_authorized": False,
            "blocked_capabilities": corpus["blocked_capabilities"],
            "available_tactic_ids": tactics["available_tactic_ids"],
            "unavailable_tactic_ids": tactics["unavailable_tactic_ids"],
            "body_material_status": BODY_MATERIAL_STATUS,
            "source_module_manifest_ref": source_imports["source_module_manifest_ref"],
            "source_module_import_count": source_imports[
                "source_module_import_count"
            ],
            "copied_source_artifact_count": source_imports[
                "copied_source_artifact_count"
            ],
            "source_modules_pass": source_imports["source_modules_pass"],
            "route_case_count": routing["route_case_count"],
            "premise_count": premise_index["premise_count"],
            "next_boundary": "formal_math_lean_proof_witness now carries the bounded public witness; readiness still does not run Lean/Lake itself",
            "body_in_receipt": False,
        },
        "body_in_receipt": False,
    }


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_common_receipt` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
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
        "command",
        "input_mode",
        "bundle_id",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "realness_evidence",
        "authority_ceiling",
        "anti_claim",
        "body_material_status",
        "source_module_import_status",
        "source_module_manifest_ref",
        "source_module_import_count",
        "copied_source_artifact_count",
        "source_modules_pass",
        "blocked_capabilities",
        "available_tactic_ids",
        "unavailable_tactic_ids",
        "premise_count",
        "route_case_count",
        "recipe_count",
        "projection_cell_id",
        "selected_pattern_ids",
        "readiness_extension_status",
        "body_in_receipt",
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
    - Teleology: Implements `_relative_receipt_paths` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [_display(path, public_root=public_root) for path in paths.values()]


def write_receipts(
    out_dir: str | Path,
    result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    """
    [ACTION]
    - Teleology: Implements `write_receipts` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
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
        "readiness_gate_result": target / READINESS_RESULT_NAME,
        "formal_math_readiness_board": target / READINESS_BOARD_NAME,
        "formal_math_readiness_extension_board": target / READINESS_EXTENSION_BOARD_NAME,
        "formal_math_readiness_validation_receipt": target / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = _relative_receipt_paths(paths, public_root_path)

    gate_result = _common_receipt(
        result,
        schema_version="formal_math_readiness_gate_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    gate_result.update(
        {
            "corpus_readiness": result["corpus_readiness"],
            "readiness_board": result["readiness_board"],
            "readiness_extension_board": result["readiness_extension_board"],
        }
    )
    board = _common_receipt(
        result,
        schema_version="formal_math_readiness_gate_board_v1",
        receipt_paths=receipt_paths,
    )
    board.update(result["readiness_board"])
    extension_board = _common_receipt(
        result,
        schema_version="formal_math_readiness_extension_board_receipt_v1",
        receipt_paths=receipt_paths,
    )
    extension_board_payload = dict(result["readiness_extension_board"])
    extension_board["board_schema_version"] = extension_board_payload.pop("schema_version")
    extension_board.update(extension_board_payload)
    validation = _common_receipt(
        result,
        schema_version="formal_math_readiness_gate_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "authority_boundary_retained": True,
            "proof_bodies_excluded": True,
            "lean_lake_execution_authorized": False,
            "provider_calls_authorized": False,
            "projection_cell_id": EXTENSION_CELL_ID,
            "selected_pattern_ids": SELECTED_PATTERN_IDS,
            "readiness_extension_board_ref": _display(
                paths["formal_math_readiness_extension_board"],
                public_root=public_root_path,
            ),
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="formal_math_readiness_gate_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "bounded_witness_organ_id": "formal_math_lean_proof_witness",
            "lean_witness_deferred": False,
            "lean_witness_authority": "bounded_public_witness_owned_by_formal_math_lean_proof_witness",
        }
    )
    acceptance.update(_fixture_manifest_source_binding(public_root_path))

    write_json_atomic(paths["readiness_gate_result"], gate_result)
    write_json_atomic(paths["formal_math_readiness_board"], board)
    write_json_atomic(paths["formal_math_readiness_extension_board"], extension_board)
    write_json_atomic(paths["formal_math_readiness_validation_receipt"], validation)
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
    - Teleology: Implements `run` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.formal_math_readiness_gate run "
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


def run_readiness_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_readiness_bundle` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.formal_math_readiness_gate "
        f"run-readiness-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_formal_math_readiness_bundle",
        include_negative=False,
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    receipt_path = target / BUNDLE_RESULT_NAME
    receipt_ref = _display(receipt_path, public_root=public_root)
    if "receipts" in receipt_path.parts:
        receipts_index = len(receipt_path.parts) - 1 - list(
            reversed(receipt_path.parts)
        ).index("receipts")
        receipt_ref = Path(*receipt_path.parts[receipts_index:]).as_posix()
    receipt = _common_receipt(
        result,
        schema_version="formal_math_readiness_gate_exported_bundle_receipt_v1",
        receipt_paths=[receipt_ref],
    )
    receipt.update(
        {
            "readiness_board": result["readiness_board"],
            "readiness_extension_board": result["readiness_extension_board"],
            "corpus_readiness": result["corpus_readiness"],
            "source_module_imports": result["source_module_imports"],
        }
    )
    write_json_atomic(receipt_path, receipt)
    result["receipt_paths"] = [receipt_ref]
    return result


def _authority_ceiling_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_authority_ceiling_card` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    authority = result.get("authority_ceiling", {})
    if not isinstance(authority, dict):
        authority = {}
    return {
        "status": authority.get("status"),
        "authority_ceiling": authority.get("authority_ceiling"),
        "lean_lake_execution_authorized": authority.get(
            "lean_lake_execution_authorized"
        )
        is True,
        "mathlib_presence_claim_authorized": authority.get(
            "mathlib_presence_claim_authorized"
        )
        is True,
        "formal_proof_authority": authority.get("formal_proof_authority") is True,
        "provider_calls_authorized": authority.get("provider_calls_authorized")
        is True,
        "proof_bodies_allowed": authority.get("proof_bodies_allowed") is True,
    }


def _secret_scan_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_secret_scan_card` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    scan = result.get("secret_exclusion_scan", {})
    if not isinstance(scan, dict):
        scan = {}
    return {
        "status": scan.get("status"),
        "hit_count": scan.get("hit_count"),
        "blocking_hit_count": scan.get("blocking_hit_count"),
        "scanned_path_count": scan.get("scanned_path_count"),
        "body_in_receipt": scan.get("body_in_receipt") is True,
        "real_substrate_default": scan.get("real_substrate_default") is True,
        "omitted_output_fields": scan.get("omitted_output_fields", []),
    }


def _source_module_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_card` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    imports = result.get("source_module_imports", [])
    import_rows = imports if isinstance(imports, list) else []
    digest_match_count = sum(
        1
        for row in import_rows
        if isinstance(row, dict) and row.get("digest_match") is True
    )
    material_classes = sorted(
        {
            str(row.get("material_class"))
            for row in import_rows
            if isinstance(row, dict) and row.get("material_class")
        }
    )
    return {
        "status": result.get("source_module_import_status"),
        "manifest_ref": result.get("source_module_manifest_ref"),
        "source_modules_pass": result.get("source_modules_pass") is True,
        "source_module_import_count": result.get("source_module_import_count"),
        "copied_source_artifact_count": result.get("copied_source_artifact_count"),
        "digest_match_count": digest_match_count,
        "material_classes": material_classes,
    }


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    readiness_board = result.get("readiness_board", {})
    if not isinstance(readiness_board, dict):
        readiness_board = {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "created_at": result.get("created_at"),
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": result.get("command"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "receipt_paths": result.get("receipt_paths", []),
        "counts": {
            "premise_count": result.get("premise_count"),
            "route_case_count": result.get("route_case_count"),
            "recipe_count": result.get("recipe_count"),
            "available_tactic_count": len(result.get("available_tactic_ids", [])),
            "unavailable_tactic_count": len(result.get("unavailable_tactic_ids", [])),
            "blocked_capability_count": len(result.get("blocked_capabilities", [])),
            "expected_negative_case_count": len(
                result.get("expected_negative_cases", [])
            ),
            "observed_negative_case_count": len(
                result.get("observed_negative_cases", {})
            ),
            "missing_negative_case_count": len(result.get("missing_negative_cases", [])),
        },
        "readiness_gate": {
            "projection_cell_id": result.get("projection_cell_id"),
            "readiness_extension_status": result.get("readiness_extension_status"),
            "selected_pattern_ids": result.get("selected_pattern_ids", []),
            "blocked_capabilities": result.get("blocked_capabilities", []),
            "available_tactic_ids": result.get("available_tactic_ids", []),
            "unavailable_tactic_ids": result.get("unavailable_tactic_ids", []),
            "mathlib_available": readiness_board.get("mathlib_available") is True,
            "lean_lake_execution_authorized": readiness_board.get(
                "lean_lake_execution_authorized"
            )
            is True,
            "formal_proof_authority": readiness_board.get("formal_proof_authority")
            is True,
            "provider_calls_authorized": readiness_board.get(
                "provider_calls_authorized"
            )
            is True,
        },
        "negative_case_coverage": {
            "expected_negative_cases": result.get("expected_negative_cases", []),
            "missing_negative_cases": result.get("missing_negative_cases", []),
            "error_codes": result.get("error_codes", []),
        },
        "source_module_import": _source_module_card(result),
        "secret_exclusion_scan": _secret_scan_card(result),
        "authority_ceiling": _authority_ceiling_card(result),
        "body_material_status": result.get("body_material_status"),
        "body_in_receipt": result.get("body_in_receipt") is True,
        "output_economy": {
            "full_receipt_written": bool(result.get("receipt_paths")),
            "stdout_mode": "card",
            "omitted_fields": [
                "anti_claim",
                "corpus_readiness",
                "findings",
                "readiness_board",
                "readiness_extension_board",
                "secret_exclusion_scan.scan_scope",
                "source_module_imports",
                "source_refs",
                "target_refs",
                "target_shape_routing_projection.routes",
            ],
            "full_payload_drilldown": "rerun without --card",
        },
    }


def plan_readiness_extensions(
    input_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `plan_readiness_extensions` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    include_negative = all((input_path / name).is_file() for name in NEGATIVE_INPUT_NAMES)
    command_text = command or (
        "python -m microcosm_core.organs.formal_math_readiness_gate "
        f"plan --input {input_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode=(
            "first_wave_fixture_plan"
            if include_negative
            else "exported_formal_math_readiness_bundle_plan"
        ),
        include_negative=include_negative,
    )
    return {
        "schema_version": "formal_math_readiness_extension_preview_v1",
        "status": result["status"],
        "created_at": result["created_at"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command_text,
        "input_mode": result["input_mode"],
        "projection_cell_id": result["projection_cell_id"],
        "selected_pattern_ids": result["selected_pattern_ids"],
        "readiness_extension_board": result["readiness_extension_board"],
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `_parser` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description="Validate formal math readiness metadata")
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = subparsers.add_parser("run-readiness-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--input", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.formal_math_readiness_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    if args.action == "run":
        command = (
            "python -m microcosm_core.organs.formal_math_readiness_gate "
            f"run --input {args.input} --out {args.out}"
            f"{' --card' if args.card else ''}"
        )
        result = run(args.input, args.out, command=command)
    elif args.action == "run-readiness-bundle":
        command = (
            "python -m microcosm_core.organs.formal_math_readiness_gate "
            f"run-readiness-bundle --input {args.input} --out {args.out}"
            f"{' --card' if args.card else ''}"
        )
        result = run_readiness_bundle(args.input, args.out, command=command)
    elif args.action == "plan":
        result = plan_readiness_extensions(args.input)
    else:
        return 2
    payload = result_card(result) if getattr(args, "card", False) else result
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
