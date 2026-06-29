"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, SOURCE_MODULE_MANIFEST_NAME, SOURCE_MODULE_IMPORT_STATUS, CARD_SCHEMA_VERSION, LEAN_IMPORT_PROBE_TIMEOUT_SECONDS, LEAN_IMPORT_PROBE_SCHEMA_VERSION, RUNTIME_PROBE_INPUT_DIR_NAME, STD_IMPORT_PROBE_INPUT_NAME, MATHLIB_ABSENCE_PROBE_INPUT_NAME, DEFAULT_STD_IMPORT_PROBE_BODY, DEFAULT_MATHLIB_ABSENCE_PROBE_BODY, SOURCE_PATTERN_IDS, SOURCE_REFS, REAL_SUBSTRATE_REFS, RECEIPT_ANCHOR_REFS, SOURCE_TARGET_REFS, SOURCE_DIGESTS, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results, environment variables.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller and any explicit side effects performed by exported entry points.
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
import shutil
import subprocess
import tempfile
import re
from collections import defaultdict
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


ORGAN_ID = "corpus_readiness_mathlib_absence_gate"
FIXTURE_ID = "first_wave.corpus_readiness_mathlib_absence_gate"
VALIDATOR_ID = "validator.microcosm.organs.corpus_readiness_mathlib_absence_gate"

RESULT_NAME = "corpus_readiness_mathlib_absence_gate_result.json"
BOARD_NAME = "corpus_readiness_mathlib_absence_board.json"
VALIDATION_RECEIPT_NAME = "corpus_readiness_mathlib_absence_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "corpus_readiness_mathlib_absence_gate_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_corpus_readiness_bundle_validation_result.json"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_MODULE_IMPORT_STATUS = "copied_corpus_readiness_source_modules_verified"
CARD_SCHEMA_VERSION = "corpus_readiness_mathlib_absence_gate_command_card_v1"
LEAN_IMPORT_PROBE_TIMEOUT_SECONDS = 20
LEAN_IMPORT_PROBE_SCHEMA_VERSION = "corpus_readiness_runtime_lean_import_probe_v1"
RUNTIME_PROBE_INPUT_DIR_NAME = "runtime_lean_import_probe"
STD_IMPORT_PROBE_INPUT_NAME = "StdGood.lean"
MATHLIB_ABSENCE_PROBE_INPUT_NAME = "MathlibAbsent.lean"
DEFAULT_STD_IMPORT_PROBE_BODY = (
    "import Std\n\nexample : (2 : Nat) + 2 = 4 := by decide\n"
)
DEFAULT_MATHLIB_ABSENCE_PROBE_BODY = (
    "import Mathlib\n\nexample : (2 : Nat) + 2 = 4 := by norm_num\n"
)

SOURCE_PATTERN_IDS = [
    "corpus_readiness_mathlib_absence_gate",
]

SOURCE_REFS = [
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/mathlib_probe.lean",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/portfolio_core_v0/tactic_portfolio_availability.json",
]
REAL_SUBSTRATE_REFS = SOURCE_REFS
RECEIPT_ANCHOR_REFS = [
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_result.json",
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_board.json",
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_validation_receipt.json",
]
SOURCE_TARGET_REFS = [
    "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input/corpus_readiness.json",
    "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input/consumer_gate_cases.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/corpus_readiness.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/consumer_gate_cases.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_module_manifest.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/mathlib_probe.lean",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/portfolio_core_v0/tactic_portfolio_availability.json",
    "receipts/first_wave/corpus_readiness_mathlib_absence_gate/corpus_readiness_mathlib_absence_gate_result.json",
    "receipts/first_wave/corpus_readiness_mathlib_absence_gate/corpus_readiness_mathlib_absence_board.json",
    "receipts/first_wave/corpus_readiness_mathlib_absence_gate/corpus_readiness_mathlib_absence_validation_receipt.json",
    ACCEPTANCE_RECEIPT_REL,
    "receipts/runtime_shell/demo_project/organs/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle_validation_result.json",
]
SOURCE_DIGESTS = {
    SOURCE_REFS[0]: "sha256:c413608118229bea32062ce9b8b5af393bcd5f63bbf1030983e98ffa6d07778d",
    SOURCE_REFS[1]: "sha256:20fdef8a53401f2bb21483002730895ca0295d2170bf148e8c328c041d8524c3",
    SOURCE_REFS[2]: "sha256:8c020f6884cda37338cb5216ded61722a9993fcd6d69aee1db655885738abbd1",
    SOURCE_REFS[3]: "sha256:405efadd8045057279a4481c05cdea8e1d99fceee253809526fb37675889d712",
}
BODY_MATERIAL_STATUS = "copied_non_secret_macro_body_with_provenance"
CORPUS_READINESS_STATUS = "real_lean_std_corpus_readiness_and_mathlib_absence_boundary"
TOOLCHAIN_BOUNDARY_STATUS = "real_lean_cli_std_mathlib_absence_probe_with_lake_available"
RUNTIME_PROBE_STATUS = "real_runtime_lean_cli_std_good_mathlib_absent_lake_available_probe"
BODY_IN_RECEIPT = False
PUBLIC_SAFE_BODY_CLASSES = {
    "public_macro_pattern_body",
    "public_macro_tool_body",
    "public_macro_receipt_body",
    "public_macro_proof_body",
}
REPO_ROOT = Path(__file__).resolve().parents[4]
NON_EXAMPLE_HOME_RE = re.compile(r"/Users/(?!example(?:/|$))[^/\s\"']+")

FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "lean_source_body",
    "provider_output_body",
)
MATHLIB_PRESENT_ALIAS_FIELDS = (
    "available",
    "mathlib_available",
    "direct_mathlib_lane_available",
    "mathlib_direct_import_available",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "bounded_runtime_lean_lake_import_probe_not_mathlib_proof_or_benchmark_authority"
    ),
    "lean_lake_execution_authorized": "bounded_runtime_import_probe_only",
    "lean_lake_execution_scope": "temporary_lean_cli_import_probe_plus_lake_version_check_no_lake_build",
    "mathlib_lake_project_import_authorized": False,
    "mathlib_dependent_proof_authority": False,
    "formal_proof_authority": False,
    "benchmark_or_corpus_completeness_authority": False,
    "provider_calls_authorized": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Corpus readiness Mathlib absence gate validates copied non-secret corpus "
    "readiness rows from the 2026-05-11 proof-state curriculum smoke run, "
    "paired with a bounded runtime Lean/Lake import probe proving Std still imports "
    "and Mathlib remains absent in the current host environment. It does not "
    "run a Lake build, prove theorem correctness, claim Mathlib is available, "
    "expose proof/provider bodies, benchmark formal-math corpora, call "
    "providers, or authorize release."
)

EXPECTED_NEGATIVE_CASES = {
    "mathlib_available_without_probe": ["MATHLIB_AVAILABILITY_OVERCLAIM"],
    "consumer_skips_readiness_gate": ["CONSUMER_SKIPS_CORPUS_READINESS_GATE"],
    "private_corpus_source_ref": ["PRIVATE_CORPUS_SOURCE_REF_FORBIDDEN"],
    "proof_body_leakage": ["CORPUS_READINESS_PROOF_BODY_FORBIDDEN"],
    "release_overclaim": ["CORPUS_READINESS_RELEASE_OVERCLAIM"],
}

INPUT_NAMES = (
    "corpus_readiness.json",
    "consumer_gate_cases.json",
)

NEGATIVE_INPUT_NAMES = (
    "mathlib_available_without_probe.json",
    "consumer_skips_readiness_gate.json",
    "private_corpus_source_ref.json",
    "proof_body_leakage.json",
    "release_overclaim.json",
)


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_display` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_rows` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_source_module_manifest_path` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_read_source_module_manifest` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_source_module_rows` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _rows(manifest, "modules")


def _strip_microcosm_prefix(ref: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_strip_microcosm_prefix` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _source_module_target_path(input_dir: Path, row: dict[str, Any]) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_target_path` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    row_path = str(row.get("path") or "")
    if row_path:
        return input_dir / row_path
    target_ref = _strip_microcosm_prefix(str(row.get("target_ref") or ""))
    public_root = _public_root_for_path(input_dir)
    return public_root / target_ref if target_ref else input_dir


def _source_module_source_path(public_root: Path, row: dict[str, Any]) -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_source_module_source_path` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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


def _source_artifact_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_artifact_paths` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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


def _source_module_rows_by_ref(input_dir: Path) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_rows_by_ref` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows_by_ref: dict[str, dict[str, Any]] = {}
    for row in _source_module_rows(_read_source_module_manifest(input_dir)):
        source_ref = str(row.get("source_ref") or "")
        if source_ref:
            rows_by_ref[source_ref] = row
    return rows_by_ref


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _normalize_sha256(value: object) -> str:
    """
    [ACTION]
    - Teleology: Implements `_normalize_sha256` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_line_count` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_finding` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
        "body_in_receipt": BODY_IN_RECEIPT,
        "body_material_status": "negative_fixture_forbidden_material_excluded",
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
    - Teleology: Implements `_record` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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


def _forbidden_body_keys(row: dict[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_forbidden_body_keys` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return sorted(key for key in FORBIDDEN_BODY_KEYS if key in row)


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    """
    [ACTION]
    - Teleology: Implements `_merge_observed` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_merge_findings` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_unexpected_findings` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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


def _source_ref_is_private(ref: str) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_source_ref_is_private` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    lowered = ref.lower()
    return (
        ref.startswith("/")
        or ref.startswith("~")
        or "raw_seed" in lowered
        or "operator_thread" in lowered
        or lowered.startswith("private/")
        or "/private/" in lowered
    )


def _runtime_source_path(input_dir: Path, *, public_root: Path, source_ref: str) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_runtime_source_path` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if source_ref.startswith("microcosm-substrate/"):
        candidate = public_root / _strip_microcosm_prefix(source_ref)
        if candidate.is_file():
            return candidate
        repo_candidate = REPO_ROOT / source_ref
        if repo_candidate.is_file():
            return repo_candidate
    else:
        for candidate in (
            input_dir / "source_artifacts" / source_ref,
            public_root.parent / source_ref,
            REPO_ROOT / source_ref,
        ):
            if candidate.is_file():
                return candidate
    return public_root.parent / source_ref


def _runtime_corpus_rows(payload: object) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_runtime_corpus_rows` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "rows") or _rows(payload, "corpora")
    return {
        str(row.get("corpus_id") or "corpus"): row
        for row in rows
        if isinstance(row, dict)
    }


def _runtime_mathlib_probe_status(payload: object) -> str:
    """
    [ACTION]
    - Teleology: Implements `_runtime_mathlib_probe_status` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return "unknown"
    mathlib = payload.get("mathlib")
    if isinstance(mathlib, dict):
        if mathlib.get("lake_project_mathlib_lane_available") is True:
            return PASS
        for key in ("error_class", "lean_status"):
            value = str(mathlib.get(key) or "")
            if value:
                return value
    if payload.get("mathlib_lake_project_import_available") is True:
        return PASS
    return "unknown"


def _normalize_private_absolute_path_rewrite(text: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_normalize_private_absolute_path_rewrite` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return NON_EXAMPLE_HOME_RE.sub("/Users/example", text)


def _true_fields(payload: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_true_fields` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [field for field in fields if payload.get(field) is True]


def _command_result_card(
    argv: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_command_result_card` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return {
            "argv": [Path(argv[0]).name, *argv[1:]],
            "cwd_name": cwd.name,
            "return_code": completed.returncode,
            "stdout_line_count": len(stdout.splitlines()),
            "stderr_line_count": len(stderr.splitlines()),
            "stdout_has_unknown_mathlib": "unknown module prefix 'Mathlib'" in stdout,
            "stderr_has_unknown_mathlib": "unknown module prefix 'Mathlib'" in stderr,
            "timeout_seconds": timeout_seconds,
            "timed_out": False,
            "body_redacted": True,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        stdout = getattr(exc, "stdout", "") or ""
        stderr = getattr(exc, "stderr", "") or ""
        return {
            "argv": [Path(argv[0]).name, *argv[1:]],
            "cwd_name": cwd.name,
            "return_code": 124 if isinstance(exc, subprocess.TimeoutExpired) else None,
            "stdout_line_count": len(str(stdout).splitlines()),
            "stderr_line_count": len(str(stderr).splitlines()),
            "stdout_has_unknown_mathlib": "unknown module prefix 'Mathlib'" in str(stdout),
            "stderr_has_unknown_mathlib": "unknown module prefix 'Mathlib'" in str(stderr),
            "timeout_seconds": timeout_seconds,
            "timed_out": isinstance(exc, subprocess.TimeoutExpired),
            "body_redacted": True,
            "error_class": "TIMEOUT" if isinstance(exc, subprocess.TimeoutExpired) else "OS_ERROR",
        }


def _skipped_command_result_card(
    argv: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    skip_reason: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_skipped_command_result_card` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return {
        "argv": [Path(argv[0]).name, *argv[1:]],
        "cwd_name": cwd.name,
        "return_code": None,
        "stdout_line_count": 0,
        "stderr_line_count": 0,
        "stdout_has_unknown_mathlib": False,
        "stderr_has_unknown_mathlib": False,
        "timeout_seconds": timeout_seconds,
        "timed_out": False,
        "skipped": True,
        "skip_reason": skip_reason,
        "body_redacted": True,
    }


def _probe_input_file_card(path: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_probe_input_file_card` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "name": path.name,
        "sha256": _sha256(path),
        "line_count": _line_count(path),
        "body_in_receipt": BODY_IN_RECEIPT,
        "body_redacted": True,
    }


def _runtime_probe_input_sources(
    probe_input_dir: str | Path | None,
) -> tuple[str | None, str | None, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_runtime_probe_input_sources` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    if probe_input_dir is None:
        return (
            DEFAULT_STD_IMPORT_PROBE_BODY,
            DEFAULT_MATHLIB_ABSENCE_PROBE_BODY,
            {
                "probe_input_mode": "embedded_default_probe_sources",
                "probe_input_status": PASS,
                "probe_input_files": [],
                "body_in_receipt": BODY_IN_RECEIPT,
                "body_redacted": True,
            },
        )

    input_dir = Path(probe_input_dir)
    std_path = input_dir / STD_IMPORT_PROBE_INPUT_NAME
    mathlib_path = input_dir / MATHLIB_ABSENCE_PROBE_INPUT_NAME
    missing = [
        path.name for path in (std_path, mathlib_path) if not path.is_file()
    ]
    metadata = {
        "probe_input_mode": "supplied_probe_sources",
        "probe_input_status": PASS if not missing else "blocked",
        "probe_input_dir_name": input_dir.name,
        "probe_input_files": [
            _probe_input_file_card(path)
            for path in (std_path, mathlib_path)
            if path.is_file()
        ],
        "missing_probe_input_names": missing,
        "body_in_receipt": BODY_IN_RECEIPT,
        "body_redacted": True,
    }
    if missing:
        return None, None, metadata
    return (
        std_path.read_text(encoding="utf-8"),
        mathlib_path.read_text(encoding="utf-8"),
        metadata,
    )


def _runtime_probe_input_dir(input_dir: Path) -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_runtime_probe_input_dir` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    candidate = input_dir / RUNTIME_PROBE_INPUT_DIR_NAME
    return candidate if candidate.exists() else None


def runtime_lean_import_probe(
    probe_input_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `runtime_lean_import_probe` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text.
    """
    std_source, mathlib_source, probe_input_metadata = _runtime_probe_input_sources(
        probe_input_dir
    )
    if std_source is None or mathlib_source is None:
        return {
            "schema_version": LEAN_IMPORT_PROBE_SCHEMA_VERSION,
            "status": "blocked",
            "proof_class": "live_runtime_probe",
            "execution_mode": "lake_env_lean_import_probe_with_lake_availability_check",
            "lean_available": shutil.which("lean") is not None,
            "lake_available": shutil.which("lake") is not None,
            "std_import_passed": False,
            "mathlib_import_rejected": False,
            "mathlib_lake_project_import_available": False,
            "lake_build_ran": False,
            "body_in_receipt": BODY_IN_RECEIPT,
            "body_redacted": True,
            "blocked_by": "runtime_probe_input_missing",
            **probe_input_metadata,
        }

    lean_path = shutil.which("lean")
    lake_path = shutil.which("lake")
    if lean_path is None:
        return {
            "schema_version": LEAN_IMPORT_PROBE_SCHEMA_VERSION,
            "status": "blocked",
            "proof_class": "live_runtime_probe",
            "execution_mode": "lake_env_lean_import_probe_with_lake_availability_check",
            "lean_available": False,
            "lake_available": lake_path is not None,
            "std_import_passed": False,
            "mathlib_import_rejected": False,
            "mathlib_lake_project_import_available": False,
            "lake_build_ran": False,
            "body_in_receipt": BODY_IN_RECEIPT,
            "body_redacted": True,
            "blocked_by": "lean_unavailable",
            **probe_input_metadata,
        }
    if lake_path is None:
        return {
            "schema_version": LEAN_IMPORT_PROBE_SCHEMA_VERSION,
            "status": "blocked",
            "proof_class": "live_runtime_probe",
            "execution_mode": "lake_env_lean_import_probe_with_lake_availability_check",
            "lean_available": True,
            "lake_available": False,
            "std_import_passed": False,
            "mathlib_import_rejected": False,
            "mathlib_lake_project_import_available": False,
            "std_probe": _skipped_command_result_card(
                ["lake", "env", "lean", "StdGood.lean"],
                cwd=Path("/tmp"),
                timeout_seconds=LEAN_IMPORT_PROBE_TIMEOUT_SECONDS,
                skip_reason="lake_unavailable",
            ),
            "mathlib_probe": _skipped_command_result_card(
                ["lake", "env", "lean", "MathlibAbsent.lean"],
                cwd=Path("/tmp"),
                timeout_seconds=LEAN_IMPORT_PROBE_TIMEOUT_SECONDS,
                skip_reason="lake_unavailable",
            ),
            "body_in_receipt": BODY_IN_RECEIPT,
            "body_redacted": True,
            "blocked_by": "lake_unavailable",
            **probe_input_metadata,
        }

    with tempfile.TemporaryDirectory(
        prefix="microcosm_corpus_readiness_probe_",
        dir="/tmp",
    ) as temp_name:
        temp_root = Path(temp_name)
        std_probe = temp_root / "StdGood.lean"
        mathlib_probe = temp_root / "MathlibAbsent.lean"
        std_probe.write_text(std_source, encoding="utf-8")
        mathlib_probe.write_text(mathlib_source, encoding="utf-8")
        std_run = _command_result_card(
            [lake_path, "env", "lean", std_probe.name],
            cwd=temp_root,
            timeout_seconds=LEAN_IMPORT_PROBE_TIMEOUT_SECONDS,
        )
        mathlib_run = _command_result_card(
            [lake_path, "env", "lean", mathlib_probe.name],
            cwd=temp_root,
            timeout_seconds=LEAN_IMPORT_PROBE_TIMEOUT_SECONDS,
        )
        lake_version_run = _command_result_card(
            [lake_path, "--version"],
            cwd=temp_root,
            timeout_seconds=LEAN_IMPORT_PROBE_TIMEOUT_SECONDS,
        )

    std_passed = std_run.get("return_code") == 0
    mathlib_rejected = (
        mathlib_run.get("return_code") not in (0, None)
        and (
            mathlib_run.get("stdout_has_unknown_mathlib") is True
            or mathlib_run.get("stderr_has_unknown_mathlib") is True
        )
    )
    return {
        "schema_version": LEAN_IMPORT_PROBE_SCHEMA_VERSION,
        "status": (
            PASS
            if std_passed
            and mathlib_rejected
            and lake_version_run.get("return_code") == 0
            else "blocked"
        ),
        "proof_class": "live_runtime_probe",
        "execution_mode": "lake_env_lean_import_probe_with_lake_availability_check",
        "lean_available": True,
        "lake_available": lake_path is not None,
        "std_import_passed": std_passed,
        "mathlib_import_rejected": mathlib_rejected,
        "mathlib_lake_project_import_available": False,
        "std_probe": std_run,
        "mathlib_probe": mathlib_run,
        "lake_version_probe": lake_version_run,
        "lake_build_ran": False,
        "timeout_seconds": LEAN_IMPORT_PROBE_TIMEOUT_SECONDS,
        "temp_root_policy": "/tmp temporary directory cleaned before receipt write",
        "body_in_receipt": BODY_IN_RECEIPT,
        "body_redacted": True,
        **probe_input_metadata,
    }


def validate_runtime_source_artifacts(
    input_dir: Path,
    *,
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_runtime_source_artifacts` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    parsed_payloads: dict[str, Any] = {}
    source_module_rows = _source_module_rows_by_ref(input_dir)

    for source_ref in SOURCE_REFS:
        path = _runtime_source_path(input_dir, public_root=public_root, source_ref=source_ref)
        exists = path.is_file()
        actual_digest = _sha256(path) if exists else None
        expected_digest = SOURCE_DIGESTS.get(source_ref)
        bundle_artifact_path = input_dir / "source_artifacts" / source_ref
        if path == bundle_artifact_path:
            row = source_module_rows.get(source_ref, {})
            expected_digest = (
                _normalize_sha256(row.get("public_safe_sha256"))
                or _normalize_sha256(row.get("target_sha256"))
                or _normalize_sha256(row.get("sha256"))
                or expected_digest
            )
        target_ref = _display(path, public_root=public_root)
        artifacts.append(
            {
                "source_ref": source_ref,
                "target_ref": target_ref,
                "exists": exists,
                "expected_sha256": expected_digest,
                "actual_sha256": actual_digest,
                "digest_match": actual_digest == expected_digest if exists else False,
                "body_in_receipt": BODY_IN_RECEIPT,
                "body_material_status": BODY_MATERIAL_STATUS,
            }
        )
        if not exists:
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_ARTIFACT_MISSING",
                    "Runtime-derived corpus readiness validation requires the anchored source artifact body.",
                    case_id="positive_runtime_source_artifacts",
                    subject_id=source_ref,
                    subject_kind="source_ref",
                )
            )
            continue
        if expected_digest and actual_digest != expected_digest:
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_ARTIFACT_DIGEST_MISMATCH",
                    "Runtime-derived corpus readiness validation requires anchored source artifact digests to match the cited public-safe source body.",
                    case_id="positive_runtime_source_artifacts",
                    subject_id=source_ref,
                    subject_kind="source_ref",
                )
            )
        if path.suffix == ".json":
            payload = read_json_strict(path)
            parsed_payloads[source_ref] = payload if isinstance(payload, dict) else {}

    probe_input_dir = _runtime_probe_input_dir(input_dir)
    import_probe = (
        runtime_lean_import_probe(probe_input_dir)
        if probe_input_dir is not None
        else runtime_lean_import_probe()
    )
    if import_probe.get("status") != PASS:
        findings.append(
            _finding(
                "CORPUS_READINESS_RUNTIME_LEAN_IMPORT_PROBE_BLOCKED",
                "Runtime Lean import probe must show Std imports and Mathlib remains absent before the corpus readiness projection can pass.",
                case_id="positive_runtime_probe",
                subject_id="runtime_lean_import_probe",
                subject_kind="runtime_probe",
            )
        )

    corpus_payload = parsed_payloads.get(SOURCE_REFS[0], {})
    tactic_probe_payload = parsed_payloads.get(SOURCE_REFS[1], {})
    mathlib_available = False
    if isinstance(tactic_probe_payload, dict):
        mathlib = tactic_probe_payload.get("mathlib")
        if isinstance(mathlib, dict):
            mathlib_available = mathlib.get("lake_project_mathlib_lane_available") is True
            present_alias_fields = _true_fields(mathlib, MATHLIB_PRESENT_ALIAS_FIELDS)
            if present_alias_fields and not mathlib_available:
                findings.append(
                    _finding(
                        "CORPUS_READINESS_MATHLIB_PRESENT_ALIAS_UNSUPPORTED",
                        "Mathlib-present alias fields cannot substitute for a passing lake-project Mathlib lane probe.",
                        case_id="positive_runtime_probe",
                        subject_id=",".join(sorted(present_alias_fields)),
                        subject_kind="runtime_mathlib_probe",
                    )
                )
            if str(mathlib.get("lean_status") or "") == PASS and not mathlib_available:
                findings.append(
                    _finding(
                        "CORPUS_READINESS_MATHLIB_STATUS_ALIAS_UNSUPPORTED",
                        "A PASS lean_status is not Mathlib availability unless the lake-project Mathlib lane is available.",
                        case_id="positive_runtime_probe",
                        subject_id="lean_status",
                        subject_kind="runtime_mathlib_probe",
                    )
                )
    if isinstance(corpus_payload, dict):
        corpus_lake_available = (
            corpus_payload.get("mathlib_lake_project_import_available") is True
        )
        present_alias_fields = _true_fields(
            corpus_payload,
            MATHLIB_PRESENT_ALIAS_FIELDS,
        )
        if present_alias_fields and not corpus_lake_available:
            findings.append(
                _finding(
                    "CORPUS_READINESS_MATHLIB_PRESENT_ALIAS_UNSUPPORTED",
                    "Corpus readiness Mathlib-present alias fields cannot substitute for mathlib_lake_project_import_available evidence.",
                    case_id="positive_runtime_probe",
                    subject_id=",".join(sorted(present_alias_fields)),
                    subject_kind="runtime_corpus_readiness",
                )
            )
        if not mathlib_available:
            mathlib_available = corpus_lake_available

    return {
        "runtime_source_artifact_status": PASS if not findings else "blocked",
        "runtime_source_artifacts": artifacts,
        "runtime_source_artifact_count": len(artifacts),
        "runtime_corpus_rows": _runtime_corpus_rows(corpus_payload),
        "runtime_mathlib_probe_status": _runtime_mathlib_probe_status(
            tactic_probe_payload or corpus_payload
        ),
        "mathlib_lake_project_import_available": mathlib_available,
        "runtime_lean_import_probe": import_probe,
        "findings": findings,
    }


def validate_corpus_readiness(
    payload: object,
    *,
    negative_payloads: dict[str, Any],
    runtime_source_artifacts: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_corpus_readiness` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "corpora")
    corpus_rows: list[dict[str, Any]] = []
    blocked_capabilities: list[str] = []
    runtime_rows = runtime_source_artifacts.get("runtime_corpus_rows", {})
    runtime_mathlib_import_available = (
        runtime_source_artifacts.get("mathlib_lake_project_import_available") is True
    )
    runtime_mathlib_probe_status = str(
        runtime_source_artifacts.get("runtime_mathlib_probe_status") or "unknown"
    )
    translation_smoke_only_ids: list[str] = []
    absent_corpus_ids: list[str] = []
    source_refs: list[str] = []
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)

    if isinstance(payload, dict):
        source_refs.extend(str(ref) for ref in payload.get("source_refs", []) if isinstance(ref, str))
        claimed_top_level_availability = payload.get("mathlib_lake_project_import_available")
        if (
            isinstance(claimed_top_level_availability, bool)
            and claimed_top_level_availability != runtime_mathlib_import_available
        ):
            _record(
                findings,
                observed,
                "CORPUS_READINESS_RUNTIME_PROBE_CONTRADICTION",
                "Corpus readiness claims must agree with the anchored runtime Mathlib probe evidence.",
                case_id="positive_runtime_probe",
                subject_id="mathlib_lake_project_import_available",
                subject_kind="corpus_readiness",
            )
        present_alias_fields = _true_fields(payload, MATHLIB_PRESENT_ALIAS_FIELDS)
        if present_alias_fields and not runtime_mathlib_import_available:
            _record(
                findings,
                observed,
                "CORPUS_READINESS_RUNTIME_PROBE_CONTRADICTION",
                "Corpus readiness Mathlib-present aliases must agree with anchored runtime Mathlib probe evidence.",
                case_id="positive_runtime_probe",
                subject_id=",".join(sorted(present_alias_fields)),
                subject_kind="corpus_readiness",
            )

    for row in rows:
        corpus_id = str(row.get("corpus_id") or "corpus")
        runtime_row_present = corpus_id in runtime_rows
        runtime_row = runtime_rows.get(corpus_id, {})
        exists = runtime_row.get("exists")
        if not isinstance(exists, bool):
            exists = row.get("exists")
        has_lake_file = runtime_row.get("has_lake_file")
        if not isinstance(has_lake_file, bool):
            has_lake_file = row.get("has_lake_file")
        readiness_status = str(
            runtime_row.get("readiness_status") or row.get("readiness_status") or ""
        )
        corpus_status = (
            "absent"
            if readiness_status == "absent" or exists is False
            else str(
                runtime_row.get("corpus_status")
                or ("available" if runtime_row_present else row.get("corpus_status"))
                or "available"
            )
        )
        row_mathlib_available = (
            bool(exists)
            and bool(has_lake_file)
            and runtime_mathlib_import_available
        )
        mathlib_probe_status = (
            "NOT_PROBED_ABSENT_CORPUS"
            if corpus_status == "absent" and corpus_id != "mathlib"
            else runtime_mathlib_probe_status
        )
        claimed_probe_status = str(row.get("mathlib_probe_status") or "unknown")
        claimed_mathlib_available = row.get("mathlib_lake_project_import_available") is True
        if (
            claimed_mathlib_available != row_mathlib_available
            or claimed_probe_status != mathlib_probe_status
        ):
            _record(
                findings,
                observed,
                "CORPUS_READINESS_RUNTIME_PROBE_CONTRADICTION",
                "Corpus readiness claims must agree with the anchored runtime Mathlib probe evidence.",
                case_id="positive_runtime_probe",
                subject_id=corpus_id,
                subject_kind="corpus_readiness",
            )
        if not row_mathlib_available:
            blocked_capabilities.append(f"{corpus_id}:mathlib_lake_project_import")
        if row.get("translation_smoke_only") is True:
            translation_smoke_only_ids.append(corpus_id)
        if corpus_status == "absent":
            absent_corpus_ids.append(corpus_id)
            blocked_capabilities.append(f"{corpus_id}:corpus_absent")
        for ref in row.get("source_refs", []):
            if isinstance(ref, str):
                source_refs.append(ref)
        corpus_rows.append(
            {
                "corpus_id": corpus_id,
                "corpus_status": corpus_status,
                "lean_available": row.get("lean_available") is True,
                "exists": exists,
                "has_lake_file": has_lake_file,
                "local_path": runtime_row.get("local_path") or row.get("local_path"),
                "readiness_status": readiness_status,
                "selected_for_this_run": (
                    runtime_row.get("selected_for_this_run") is True
                    if "selected_for_this_run" in runtime_row
                    else row.get("selected_for_this_run") is True
                ),
                "mathlib_lake_project_import_available": row_mathlib_available,
                "mathlib_probe_status": mathlib_probe_status,
                "translation_smoke_only": row.get("translation_smoke_only") is True,
                "consumer_rule": row.get("consumer_rule"),
                "body_in_receipt": BODY_IN_RECEIPT,
                "body_material_status": BODY_MATERIAL_STATUS,
                "corpus_readiness_status": CORPUS_READINESS_STATUS,
            }
        )
    mathlib_negative = negative_payloads.get("mathlib_available_without_probe")
    if isinstance(mathlib_negative, dict):
        case_id = str(
            mathlib_negative.get("expected_negative_case_id")
            or "mathlib_available_without_probe"
        )
        probe_status = str(mathlib_negative.get("mathlib_probe_status") or "unknown")
        overclaims = (
            mathlib_negative.get("mathlib_lake_project_import_available") is True
            or mathlib_negative.get("claims_mathlib_available") is True
        ) and probe_status != PASS
        if overclaims:
            _record(
                findings,
                observed,
                "MATHLIB_AVAILABILITY_OVERCLAIM",
                "Mathlib availability was claimed without a passing import probe.",
                case_id=case_id,
                subject_id=str(mathlib_negative.get("corpus_id") or "mathlib"),
                subject_kind="corpus_readiness",
            )

    private_ref_negative = negative_payloads.get("private_corpus_source_ref")
    if isinstance(private_ref_negative, dict):
        case_id = str(
            private_ref_negative.get("expected_negative_case_id")
            or "private_corpus_source_ref"
        )
        refs = [
            str(ref)
            for ref in private_ref_negative.get("source_refs", [])
            if isinstance(ref, str)
        ]
        for ref in refs:
            if _source_ref_is_private(ref):
                _record(
                    findings,
                    observed,
                    "PRIVATE_CORPUS_SOURCE_REF_FORBIDDEN",
                    "Corpus readiness source refs must be public-safe metadata refs only.",
                    case_id=case_id,
                    subject_id=ref,
                    subject_kind="source_ref",
                )

    proof_negative = negative_payloads.get("proof_body_leakage")
    if isinstance(proof_negative, dict):
        case_id = str(
            proof_negative.get("expected_negative_case_id") or "proof_body_leakage"
        )
        for row in _rows(proof_negative, "corpora"):
            forbidden = _forbidden_body_keys(row)
            if forbidden:
                _record(
                    findings,
                    observed,
                    "CORPUS_READINESS_PROOF_BODY_FORBIDDEN",
                    "Corpus readiness metadata cannot carry proof or provider body fields.",
                    case_id=case_id,
                    subject_id=str(row.get("corpus_id") or "corpus"),
                    subject_kind="corpus_readiness",
                )

    return {
        "corpora": sorted(corpus_rows, key=lambda item: item["corpus_id"]),
        "corpus_count": len(corpus_rows),
        "blocked_capabilities": sorted(set(blocked_capabilities)),
        "mathlib_lake_project_import_available": runtime_mathlib_import_available,
        "runtime_mathlib_probe_status": runtime_mathlib_probe_status,
        "translation_smoke_only_ids": sorted(translation_smoke_only_ids),
        "absent_corpus_ids": sorted(absent_corpus_ids),
        "source_refs": sorted(set(source_refs)),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_consumer_gate_cases(
    payload: object,
    *,
    mathlib_available: bool,
    absent_corpus_ids: list[str],
    negative_payloads: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_consumer_gate_cases` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    cases: list[dict[str, Any]] = []
    allowed: list[str] = []
    blocked: list[str] = []
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    absent = set(absent_corpus_ids)

    for row in _rows(payload, "cases"):
        case_id = str(row.get("case_id") or "case")
        target_corpus = str(row.get("target_corpus_id") or "")
        requires_mathlib = row.get("requires_mathlib_lake_project_import") is True
        readiness_gate_checked = row.get("readiness_gate_checked") is True
        blocked_reasons: list[str] = []
        if requires_mathlib and not mathlib_available:
            blocked_reasons.append("mathlib_lake_project_import_unavailable")
        if target_corpus in absent:
            blocked_reasons.append("corpus_absent")
        if not readiness_gate_checked:
            _record(
                findings,
                observed,
                "CONSUMER_READINESS_GATE_UNCHECKED",
                "A real consumer case must prove it checked corpus readiness before a verdict is accepted.",
                case_id="positive_consumer_gate",
                subject_id=case_id,
                subject_kind="consumer_gate",
            )
        decision = "blocked" if blocked_reasons else "allowed"
        if decision == "allowed":
            allowed.append(case_id)
        else:
            blocked.append(case_id)
        cases.append(
            {
                "case_id": case_id,
                "target_corpus_id": target_corpus,
                "requested_capability": row.get("requested_capability"),
                "requires_mathlib_lake_project_import": requires_mathlib,
                "readiness_gate_checked": readiness_gate_checked,
                "decision": decision,
                "blocked_reasons": blocked_reasons,
                "body_in_receipt": BODY_IN_RECEIPT,
                "body_material_status": BODY_MATERIAL_STATUS,
                "corpus_readiness_status": CORPUS_READINESS_STATUS,
            }
        )

    skip_negative = negative_payloads.get("consumer_skips_readiness_gate")
    if isinstance(skip_negative, dict):
        case_id = str(
            skip_negative.get("expected_negative_case_id")
            or "consumer_skips_readiness_gate"
        )
        if (
            skip_negative.get("attempted_execution") is True
            and skip_negative.get("requires_mathlib_lake_project_import") is True
            and skip_negative.get("readiness_gate_checked") is not True
        ):
            _record(
                findings,
                observed,
                "CONSUMER_SKIPS_CORPUS_READINESS_GATE",
                "A consumer attempted Mathlib-dependent work without checking corpus readiness.",
                case_id=case_id,
                subject_id=str(skip_negative.get("case_id") or "consumer_case"),
                subject_kind="consumer_gate",
            )

    release_negative = negative_payloads.get("release_overclaim")
    if isinstance(release_negative, dict):
        case_id = str(release_negative.get("expected_negative_case_id") or "release_overclaim")
        overclaim_fields = [
            field
            for field in (
                "release_authorized",
                "publication_authorized",
                "formal_proof_authority",
                "mathlib_dependent_proof_authority",
            )
            if release_negative.get(field) is True
        ]
        if overclaim_fields:
            _record(
                findings,
                observed,
                "CORPUS_READINESS_RELEASE_OVERCLAIM",
                "Corpus readiness metadata attempted to authorize release or proof authority.",
                case_id=case_id,
                subject_id=",".join(sorted(overclaim_fields)),
                subject_kind="authority_ceiling",
            )

    return {
        "cases": sorted(cases, key=lambda item: item["case_id"]),
        "case_count": len(cases),
        "allowed_case_ids": sorted(allowed),
        "blocked_case_ids": sorted(blocked),
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
    - Teleology: Implements `validate_source_module_imports` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
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
                "CORPUS_READINESS_SOURCE_MODULE_MANIFEST_MISSING",
                "Exported corpus readiness bundle must include a source_module_manifest.json for copied macro corpus/toolchain bodies.",
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
                "CORPUS_READINESS_SOURCE_IMPORT_CLASS_UNSUPPORTED",
                "Corpus readiness source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if required and manifest_path.is_file() and not rows:
        findings.append(
            _finding(
                "CORPUS_READINESS_SOURCE_MODULE_ROWS_MISSING",
                "Exported corpus readiness bundle must carry at least one copied source module row.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )

    for row in rows:
        module_id = str(row.get("module_id") or "source_module")
        target = _source_module_target_path(input_dir, row)
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
        digest_match = actual_digest == target_digest
        source_to_target_relation = str(
            row.get("source_to_target_relation") or "exact_copy"
        )
        verification_mode = str(
            row.get("verification_mode") or "exact_source_digest_match"
        )
        public_safe_transform = str(row.get("public_safe_transform") or "")
        relation_pass: bool | None = None
        import_row = {
            "module_id": module_id,
            "source_ref": source_ref,
            "target_ref": target_ref,
            "material_class": material_class,
            "source_sha256": source_digest,
            "actual_source_sha256": actual_source_digest,
            "expected_target_sha256": target_digest,
            "target_sha256": actual_digest,
            "source_exists": source_exists,
            "exists": exists,
            "digest_match": digest_match,
            "source_digest_match": source_digest_match,
            "source_to_target_relation": source_to_target_relation,
            "verification_mode": verification_mode,
            "public_safe_transform": public_safe_transform or None,
            "source_line_count": _line_count(target) if exists else None,
            "target_line_count": _line_count(target) if exists else None,
            "relation_pass": relation_pass,
            "body_in_receipt": BODY_IN_RECEIPT,
            "body_material_status": BODY_MATERIAL_STATUS,
            "corpus_readiness_status": CORPUS_READINESS_STATUS,
            "toolchain_boundary_status": TOOLCHAIN_BOUNDARY_STATUS,
        }
        imports.append(import_row)

        if str(row.get("source_import_class") or "") != "copied_non_secret_macro_body":
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_MODULE_IMPORT_CLASS_UNSUPPORTED",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_BODY_CLASSES:
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_MODULE_CLASS_UNSUPPORTED",
                    "Source module rows must use a public-safe macro body material class.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if row.get("body_in_receipt") is True:
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_BODY_RECEIPT_EXPORT_FORBIDDEN",
                    "Copied corpus/toolchain source bodies may live in the bundle source_artifacts tree, not in generated receipts.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if not exists:
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_MODULE_TARGET_MISSING",
                    "Copied source module target file is missing from the exported bundle.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if source_digest_match is False:
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_MODULE_SOURCE_DIGEST_MISMATCH",
                    "Declared source module digest must match the live source digest when source_ref is available.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        elif not digest_match:
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Copied source module digest must match the manifest target digest.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        elif source_exists and exists:
            if source_to_target_relation == "exact_copy":
                relation_pass = actual_source_digest == actual_digest
                if not relation_pass:
                    findings.append(
                        _finding(
                            "CORPUS_READINESS_SOURCE_MODULE_EXACT_COPY_MISMATCH",
                            "Exact-copy source module rows must preserve source and target body equality.",
                            case_id="source_module_floor",
                            subject_id=module_id,
                            subject_kind="source_module",
                        )
                    )
            elif source_to_target_relation == "verified_public_safe_private_path_rewrite":
                relation_pass = (
                    verification_mode == "verified_light_edit_recipe"
                    and public_safe_transform == "private_absolute_path_rewrite_only"
                )
                if relation_pass:
                    source_text = source.read_text(encoding="utf-8")
                    target_text = target.read_text(encoding="utf-8")
                    relation_pass = (
                        _normalize_private_absolute_path_rewrite(source_text)
                        == target_text
                    )
                if not relation_pass:
                    findings.append(
                        _finding(
                            "CORPUS_READINESS_SOURCE_MODULE_PUBLIC_SAFE_REWRITE_MISMATCH",
                            "Public-safe rewrite rows must match the declared private-absolute-path rewrite recipe exactly.",
                            case_id="source_module_floor",
                            subject_id=module_id,
                            subject_kind="source_module",
                        )
                    )
            else:
                relation_pass = False
                findings.append(
                    _finding(
                        "CORPUS_READINESS_SOURCE_MODULE_RELATION_UNSUPPORTED",
                        "Source module rows must declare a supported source-to-target relation.",
                        case_id="source_module_floor",
                        subject_id=module_id,
                        subject_kind="source_module",
                    )
                )

        import_row["relation_pass"] = relation_pass

    copied_count = sum(
        1
        for row in imports
        if row["exists"]
        and row["digest_match"]
        and row.get("source_digest_match") is not False
        and row.get("relation_pass") is not False
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


def _build_board(
    *,
    result: dict[str, Any],
    secret_scan: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_board` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "corpus_readiness_mathlib_absence_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_contract": {
            "mathlib_probe_required_before_mathlib_proof_work": True,
            "mathlib_lake_project_import_available": result[
                "mathlib_lake_project_import_available"
            ],
            "runtime_mathlib_probe_status": result["runtime_mathlib_probe_status"],
            "consumer_gate_required": True,
            "translation_smoke_only_is_not_proof_authority": True,
            "body_in_receipt": BODY_IN_RECEIPT,
            "body_material_status": BODY_MATERIAL_STATUS,
        },
        "corpus_projection": {
            "corpus_count": result["corpus_count"],
            "blocked_capabilities": result["blocked_capabilities"],
            "translation_smoke_only_ids": result["translation_smoke_only_ids"],
            "absent_corpus_ids": result["absent_corpus_ids"],
            "source_refs": result["source_refs"],
            "source_ref_count": len(result["source_refs"]),
            "body_in_receipt": BODY_IN_RECEIPT,
            "corpus_readiness_status": CORPUS_READINESS_STATUS,
            "toolchain_boundary_status": TOOLCHAIN_BOUNDARY_STATUS,
        },
        "consumer_gate_projection": {
            "case_count": result["consumer_case_count"],
            "allowed_case_ids": result["allowed_case_ids"],
            "blocked_case_ids": result["blocked_case_ids"],
            "decision_rows": result["consumer_gate_cases"],
            "body_in_receipt": BODY_IN_RECEIPT,
            "corpus_readiness_status": CORPUS_READINESS_STATUS,
        },
        "secret_exclusion_scan": secret_scan,
        "body_material_status": BODY_MATERIAL_STATUS,
        "corpus_readiness_status": CORPUS_READINESS_STATUS,
        "toolchain_boundary_status": TOOLCHAIN_BOUNDARY_STATUS,
        "real_substrate_refs": REAL_SUBSTRATE_REFS,
        "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
        "source_target_refs": SOURCE_TARGET_REFS,
        "source_digests": SOURCE_DIGESTS,
        "source_module_manifest_ref": result.get("source_module_manifest_ref"),
        "source_module_import_status": result.get("source_module_import_status"),
        "source_module_import_count": result.get("source_module_import_count"),
        "copied_source_artifact_count": result.get("copied_source_artifact_count"),
        "source_modules_pass": result.get("source_modules_pass"),
        "source_module_imports": result.get("source_module_imports", []),
        "runtime_source_artifact_status": result.get("runtime_source_artifact_status"),
        "runtime_source_artifact_count": result.get("runtime_source_artifact_count"),
        "runtime_source_artifacts": result.get("runtime_source_artifacts", []),
        "runtime_lean_import_probe": result.get("runtime_lean_import_probe", {}),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": BODY_IN_RECEIPT,
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
    - Teleology: Implements `_build_result` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    negative_payloads = {name: payloads[name] for name in NEGATIVE_INPUT_NAMES_STEMS if name in payloads}
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    secret_scan["body_material_status"] = "secret_exclusion_scan_no_payload_body_export"
    runtime_source_artifacts = validate_runtime_source_artifacts(
        input_dir,
        public_root=public_root,
    )

    corpus = validate_corpus_readiness(
        payloads["corpus_readiness"],
        negative_payloads=negative_payloads,
        runtime_source_artifacts=runtime_source_artifacts,
    )
    consumer = validate_consumer_gate_cases(
        payloads["consumer_gate_cases"],
        mathlib_available=corpus["mathlib_lake_project_import_available"],
        absent_corpus_ids=corpus["absent_corpus_ids"],
        negative_payloads=negative_payloads,
    )
    source_imports = validate_source_module_imports(
        input_dir,
        required=input_mode == "exported_corpus_readiness_bundle",
        public_root=public_root,
    )
    observed = _merge_observed(corpus, consumer)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        runtime_source_artifacts,
        corpus,
        consumer,
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
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    result = {
        "schema_version": "corpus_readiness_mathlib_absence_gate_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": sorted(
            set([*SOURCE_REFS, *corpus["source_refs"], *source_imports["source_refs"]])
        ),
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "body_material_status": BODY_MATERIAL_STATUS,
        "corpus_readiness_status": CORPUS_READINESS_STATUS,
        "toolchain_boundary_status": TOOLCHAIN_BOUNDARY_STATUS,
        "body_in_receipt": BODY_IN_RECEIPT,
        "source_module_import_status": source_imports["source_module_import_status"],
        "source_module_manifest_ref": source_imports["source_module_manifest_ref"],
        "source_module_imports": source_imports["source_module_imports"],
        "source_module_import_count": source_imports["source_module_import_count"],
        "copied_source_artifact_count": source_imports["copied_source_artifact_count"],
        "source_modules_pass": source_imports["source_modules_pass"],
        "real_substrate_refs": REAL_SUBSTRATE_REFS,
        "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
        "source_target_refs": SOURCE_TARGET_REFS,
        "source_digests": SOURCE_DIGESTS,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "corpora": corpus["corpora"],
        "corpus_count": corpus["corpus_count"],
        "blocked_capabilities": corpus["blocked_capabilities"],
        "mathlib_lake_project_import_available": corpus[
            "mathlib_lake_project_import_available"
        ],
        "runtime_mathlib_probe_status": corpus["runtime_mathlib_probe_status"],
        "translation_smoke_only_ids": corpus["translation_smoke_only_ids"],
        "absent_corpus_ids": corpus["absent_corpus_ids"],
        "consumer_gate_cases": consumer["cases"],
        "consumer_case_count": consumer["case_count"],
        "allowed_case_ids": consumer["allowed_case_ids"],
        "blocked_case_ids": consumer["blocked_case_ids"],
        "runtime_source_artifact_status": runtime_source_artifacts[
            "runtime_source_artifact_status"
        ],
        "runtime_source_artifact_count": runtime_source_artifacts[
            "runtime_source_artifact_count"
        ],
        "runtime_source_artifacts": runtime_source_artifacts[
            "runtime_source_artifacts"
        ],
        "runtime_lean_import_probe": runtime_source_artifacts[
            "runtime_lean_import_probe"
        ],
    }
    result["readiness_board"] = _build_board(result=result, secret_scan=secret_scan)
    return result


NEGATIVE_INPUT_NAMES_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_common_receipt` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
        "source_pattern_ids",
        "source_refs",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "body_material_status",
        "corpus_readiness_status",
        "toolchain_boundary_status",
        "body_in_receipt",
        "source_module_import_status",
        "source_module_manifest_ref",
        "source_module_imports",
        "source_module_import_count",
        "copied_source_artifact_count",
        "source_modules_pass",
        "real_substrate_refs",
        "receipt_anchor_refs",
        "source_target_refs",
        "source_digests",
        "authority_ceiling",
        "anti_claim",
        "corpus_count",
        "blocked_capabilities",
        "mathlib_lake_project_import_available",
        "runtime_mathlib_probe_status",
        "translation_smoke_only_ids",
        "absent_corpus_ids",
        "consumer_case_count",
        "allowed_case_ids",
        "blocked_case_ids",
        "runtime_source_artifact_status",
        "runtime_source_artifact_count",
        "runtime_source_artifacts",
        "runtime_lean_import_probe",
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
    - Teleology: Implements `_relative_receipt_paths` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `write_receipts` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
        "result": target / RESULT_NAME,
        "board": target / BOARD_NAME,
        "validation_receipt": target / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = _relative_receipt_paths(paths, public_root_path)

    result_receipt = _common_receipt(
        result,
        schema_version="corpus_readiness_mathlib_absence_gate_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    result_receipt.update(
        {
            "corpora": result["corpora"],
            "consumer_gate_cases": result["consumer_gate_cases"],
            "readiness_board": result["readiness_board"],
        }
    )
    board_receipt = _common_receipt(
        result,
        schema_version="corpus_readiness_mathlib_absence_board_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board_payload = dict(result["readiness_board"])
    board_receipt["board_schema_version"] = board_payload.pop("schema_version")
    board_receipt.update(board_payload)
    validation = _common_receipt(
        result,
        schema_version="corpus_readiness_mathlib_absence_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "mathlib_absence_gate_retained": True,
            "consumer_gate_required": True,
            "proof_bodies_excluded": True,
            "lean_lake_execution_authorized": False,
            "mathlib_lake_project_import_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="corpus_readiness_mathlib_absence_gate_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "projection_status": "real_corpus_readiness_boundary_landed"
            if result["status"] == PASS
            else "blocked",
            "authority_boundary_retained": True,
        }
    )

    write_json_atomic(paths["result"], result_receipt)
    write_json_atomic(paths["board"], board_receipt)
    write_json_atomic(paths["validation_receipt"], validation)
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
    - Teleology: Implements `run` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.corpus_readiness_mathlib_absence_gate run "
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


def run_projection_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_projection_bundle` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.corpus_readiness_mathlib_absence_gate "
        f"run-projection-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_corpus_readiness_bundle",
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
        schema_version="corpus_readiness_mathlib_absence_exported_bundle_receipt_v1",
        receipt_paths=[receipt_ref],
    )
    receipt.update(
        {
            "corpora": result["corpora"],
            "consumer_gate_cases": result["consumer_gate_cases"],
            "readiness_board": result["readiness_board"],
        }
    )
    write_json_atomic(receipt_path, receipt)
    result["receipt_paths"] = [receipt_ref]
    return result


def _authority_ceiling_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_authority_ceiling_card` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
        "mathlib_lake_project_import_authorized": authority.get(
            "mathlib_lake_project_import_authorized"
        )
        is True,
        "mathlib_dependent_proof_authority": authority.get(
            "mathlib_dependent_proof_authority"
        )
        is True,
        "formal_proof_authority": authority.get("formal_proof_authority") is True,
        "provider_calls_authorized": authority.get("provider_calls_authorized")
        is True,
        "release_authorized": authority.get("release_authorized") is True,
    }


def _secret_scan_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_secret_scan_card` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_source_module_card` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `result_card` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
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
            "corpus_count": result.get("corpus_count"),
            "consumer_case_count": result.get("consumer_case_count"),
            "allowed_case_count": len(result.get("allowed_case_ids", [])),
            "blocked_case_count": len(result.get("blocked_case_ids", [])),
            "blocked_capability_count": len(result.get("blocked_capabilities", [])),
            "absent_corpus_count": len(result.get("absent_corpus_ids", [])),
            "source_ref_count": len(result.get("source_refs", [])),
        },
        "corpus_gate": {
            "mathlib_lake_project_import_available": result.get(
                "mathlib_lake_project_import_available"
            )
            is True,
            "runtime_mathlib_probe_status": result.get("runtime_mathlib_probe_status"),
            "translation_smoke_only_ids": result.get("translation_smoke_only_ids", []),
            "absent_corpus_ids": result.get("absent_corpus_ids", []),
            "allowed_case_ids": result.get("allowed_case_ids", []),
            "blocked_case_ids": result.get("blocked_case_ids", []),
            "corpus_readiness_status": result.get("corpus_readiness_status"),
            "toolchain_boundary_status": result.get("toolchain_boundary_status"),
        },
        "runtime_source_artifacts": {
            "status": result.get("runtime_source_artifact_status"),
            "count": result.get("runtime_source_artifact_count"),
        },
        "runtime_lean_import_probe": {
            "status": result.get("runtime_lean_import_probe", {}).get("status")
            if isinstance(result.get("runtime_lean_import_probe"), dict)
            else None,
            "proof_class": result.get("runtime_lean_import_probe", {}).get("proof_class")
            if isinstance(result.get("runtime_lean_import_probe"), dict)
            else None,
            "std_import_passed": result.get("runtime_lean_import_probe", {}).get(
                "std_import_passed"
            )
            if isinstance(result.get("runtime_lean_import_probe"), dict)
            else None,
            "mathlib_import_rejected": result.get("runtime_lean_import_probe", {}).get(
                "mathlib_import_rejected"
            )
            if isinstance(result.get("runtime_lean_import_probe"), dict)
            else None,
            "body_in_receipt": result.get("runtime_lean_import_probe", {}).get(
                "body_in_receipt"
            )
            if isinstance(result.get("runtime_lean_import_probe"), dict)
            else None,
        },
        "negative_case_coverage": {
            "expected_negative_cases": result.get("expected_negative_cases", []),
            "observed_negative_case_count": len(
                result.get("observed_negative_cases", {})
            ),
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
                "blocked_capabilities",
                "consumer_gate_cases",
                "corpora",
                "findings",
                "readiness_board",
                "real_substrate_refs",
                "receipt_anchor_refs",
                "source_digests",
                "source_module_imports",
                "source_target_refs",
            ],
        },
    }


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `_parser` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description="Validate corpus readiness Mathlib absence metadata")
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = subparsers.add_parser("run-projection-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.corpus_readiness_mathlib_absence_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    if args.action == "run":
        command = (
            "python -m microcosm_core.organs.corpus_readiness_mathlib_absence_gate "
            f"run --input {args.input} --out {args.out}"
            f"{' --card' if args.card else ''}"
        )
        result = run(args.input, args.out, command=command)
    elif args.action == "run-projection-bundle":
        command = (
            "python -m microcosm_core.organs.corpus_readiness_mathlib_absence_gate "
            f"run-projection-bundle --input {args.input} --out {args.out}"
            f"{' --card' if args.card else ''}"
        )
        result = run_projection_bundle(args.input, args.out, command=command)
    else:
        return 2
    payload = result_card(result) if args.card else result
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
