"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.batch8_compliance_pipeline_capsule` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, BUNDLE_INPUT_MODE, EXERCISE_MANIFEST_NAME, EXPECTED_ENGINES, EXPECTED_NEGATIVE_CASES, NEGATIVE_CASE_CODES, AUTHORITY_CEILING, ANTI_CLAIM, SOURCE_REQUIRED_ANCHORS, SPEC, evaluate_negative_case, run, run_batch8_compliance_pipeline_bundle, result_card, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.organs._crown_jewel_common, system.lib.compliance, system.lib.compliance.standard_baseline_adapter, system.lib.pipeline.stage_compile, system.lib.pipeline.stage_process
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch8_compliance_pipeline_capsule"
FIXTURE_ID = "first_wave.batch8_compliance_pipeline_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch8_compliance_pipeline_capsule"

RESULT_NAME = "batch8_compliance_pipeline_capsule_result.json"
BOARD_NAME = "batch8_compliance_pipeline_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch8_compliance_pipeline_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch8_compliance_pipeline_capsule_validation_result.json"
CARD_SCHEMA_VERSION = "batch8_compliance_pipeline_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch8_compliance_pipeline_capsule_bundle"
EXERCISE_MANIFEST_NAME = "batch8_compliance_pipeline_exercise_manifest.json"

EXPECTED_ENGINES: tuple[str, ...] = (
    "compliance_registry_runtime_witness",
    "compliance_coverage_bounded_check",
    "baseline_companion_scanner_contract",
    "pipeline_digest_and_shard_normalization",
    "pipeline_observe_compile_helpers",
    "pipeline_dispatch_process_boundary_contract",
)

EXPECTED_NEGATIVE_CASES = {
    "missing_compliance_registry": ("BATCH8_COMPLIANCE_REGISTRY_REQUIRED",),
    "bounded_check_failed": ("BATCH8_COMPLIANCE_BOUNDED_CHECK_REQUIRED",),
    "baseline_missing_standard": ("BATCH8_BASELINE_STANDARD_FILE_REQUIRED",),
    "digest_loses_directive": ("BATCH8_PIPELINE_DIGEST_DIRECTIVE_REQUIRED",),
    "compile_helper_empty_mentions": ("BATCH8_PIPELINE_COMPILE_HELPERS_REQUIRED",),
    "pipeline_boundary_missing": ("BATCH8_PIPELINE_BOUNDARY_CONTRACT_REQUIRED",),
}

NEGATIVE_CASE_CODES = {
    case_id: codes[0] for case_id, codes in EXPECTED_NEGATIVE_CASES.items()
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch8_compliance_pipeline_capsule_not_full_ledger_or_pipeline_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "model_dispatch": False,
    "source_mutation_authorized": False,
    "full_compliance_ledger_freshness_claim": False,
    "full_pipeline_dispatch_authority": False,
    "raw_seed_mutation_authorized": False,
    "test_completeness_proof": False,
}

ANTI_CLAIM = (
    "Batch 8 imports and exercises public-safe macro bodies for the compliance "
    "adapter registry, scanner coverage self-audit, baseline scanner, "
    "Microcosm compliance adapter, compliance ledger builder, and the observe "
    "pipeline extract/select/emit/compile/execute/process stages. It is not a "
    "full compliance-ledger refresh, not provider dispatch, not raw-seed "
    "mutation authority, not public release approval, and not proof that every "
    "standard or pipeline branch is covered."
)

SOURCE_REQUIRED_ANCHORS = {
    "system/lib/compliance/__init__.py": (
        "ADAPTERS: dict[standard_id, callable]",
        "_STATIC_ADAPTERS",
        "BASELINE_ADAPTER_STANDARD_IDS",
        "def scan_all(repo_root: Path)",
    ),
    "system/lib/compliance/compliance_coverage_adapter.py": (
        "def scan_compliance_coverage(repo_root: Path)",
        "_baseline_companion_finding",
        "domain_scanner_coverage",
    ),
    "system/lib/compliance/standard_baseline_adapter.py": (
        "def scan_standard_baseline(repo_root: Path, standard_id: str)",
        "baseline_standard_file_only",
        "make_standard_baseline_scanner",
    ),
    "system/lib/compliance/microcosm_adapter.py": (
        "def scan_microcosm(repo_root: Path)",
        "_scan_doctrine_lattice",
        "_MICROCOSM_REQUIRED_STANDARD_FIELDS",
    ),
    "tools/meta/factory/build_compliance_ledger.py": (
        "def _adapter_registry_snapshot(repo_root: Path)",
        "--standard-id",
        "projection_self_audit",
        "ratchet_next_command",
    ),
    "system/lib/pipeline/stage_extract.py": (
        "def extract_shards(state: dict",
        "def digest_raw_seed(raw_text: str",
        "def _normalize_shards_payload(payload: dict)",
        "def _extract_synthesis_json(text: str)",
    ),
    "system/lib/pipeline/stage_select.py": (
        "def select_shards(state: dict",
        "constrain_shard_candidates",
        "active_task_dag_layer",
        "_find_meta_ledger",
    ),
    "system/lib/pipeline/stage_emit.py": (
        "def emit_synth_seed(state: dict",
        "write_controller_artifacts",
        "source_shards",
    ),
    "system/lib/pipeline/stage_compile.py": (
        "def compile_observe_plan(state: dict",
        "def _probe_questions_for_plan_path",
        "def _priority_followup_files",
        "Do not return a descriptive edit inventory",
    ),
    "system/lib/pipeline/stage_execute.py": (
        "def execute_observe(",
        "observe_dispatch_skipped",
        "run_once",
        "save_state_if_not_stale",
    ),
    "system/lib/pipeline/stage_process.py": (
        "def process_results(state: dict)",
        "def _select_primary_receipt(",
        "def _apply_synthesis_updates_to_shards",
        "carry_forward_context",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 8 Compliance Pipeline Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(EXERCISE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "microcosm-substrate/examples/batch8_compliance_pipeline_capsule/"
        "exported_batch8_compliance_pipeline_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _repo_root(public_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_repo_root` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_root.parent


def _copied_source(public_root: Path, source_ref: str) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_copied_source` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (
        public_root
        / "examples/batch8_compliance_pipeline_capsule/"
        "exported_batch8_compliance_pipeline_capsule_bundle/source_modules"
        / source_ref
    )


def _read(public_root: Path, source_ref: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_read` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return _copied_source(public_root, source_ref).read_text(encoding="utf-8")


def _copy_public_bundle(public_root: Path, temp_public_root: Path) -> None:
    """
    [ACTION]
    - Teleology: Implements `_copy_public_bundle` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    shutil.copytree(
        public_root / "examples/batch8_compliance_pipeline_capsule",
        temp_public_root / "examples/batch8_compliance_pipeline_capsule",
    )


def _replace_copied_source_token(
    public_root: Path,
    source_ref: str,
    old: str,
    new: str,
) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_replace_copied_source_token` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values, declared filesystem outputs.
    """
    source_path = _copied_source(public_root, source_ref)
    text = source_path.read_text(encoding="utf-8")
    if old not in text:
        return False
    source_path.write_text(text.replace(old, new), encoding="utf-8")
    return True


def _load_copied_source_module(public_root: Path, source_ref: str) -> Any:
    """
    [ACTION]
    - Teleology: Implements `_load_copied_source_module` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    source_path = _copied_source(public_root, source_ref)
    module_name = f"_microcosm_{ORGAN_ID}_{source_ref.replace('/', '_').replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load copied source module: {source_ref}")
    module = importlib.util.module_from_spec(spec)
    source_modules_root = source_path.parents[len(Path(source_ref).parts) - 1]
    inserted = False
    if str(source_modules_root) not in sys.path:
        sys.path.insert(0, str(source_modules_root))
        inserted = True
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(str(source_modules_root))
    return module


def _run_public_witness(
    command: list[str],
    *,
    cwd: Path,
    timeout: int = 120,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_run_public_witness` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH8_COMPLIANCE_WITNESS_COMMAND_MISSING",
            "error_type": type(exc).__name__,
            "body_in_receipt": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH8_COMPLIANCE_WITNESS_TIMEOUT",
            "body_in_receipt": False,
        }
    parsed: dict[str, Any] | None = None
    if completed.stdout.strip().startswith("{"):
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "status": "pass" if completed.returncode == 0 else "blocked",
        "returncode": completed.returncode,
        "stdout_byte_count": len(completed.stdout.encode("utf-8")),
        "stderr_byte_count": len(completed.stderr.encode("utf-8")),
        "parsed_summary": parsed,
        "body_in_receipt": False,
    }


def _mutated_source_negative(
    public_root: Path,
    *,
    case_id: str,
    source_ref: str,
    old: str,
    new: str,
    engine: Any,
    observed_flag: str,
    observed_value: Any,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_mutated_source_negative` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_{case_id}_") as tmp:
        temp_public_root = Path(tmp) / "microcosm-substrate"
        _copy_public_bundle(public_root, temp_public_root)
        mutation_applied = _replace_copied_source_token(
            temp_public_root,
            source_ref,
            old,
            new,
        )
        result = engine(temp_public_root)
    observed = result.get("status") == "blocked" and result.get(observed_flag) == observed_value
    return {
        "status": "blocked" if observed else "pass",
        "case_id": case_id,
        "engine_id": result.get("engine_id"),
        "mutation_applied": mutation_applied,
        "wrong_input_observed": observed,
        "negative_condition_observed": observed,
        observed_flag: result.get(observed_flag),
        "body_in_receipt": False,
    }


def _missing_compliance_registry_negative(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_missing_compliance_registry_negative` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _mutated_source_negative(
        public_root,
        case_id="missing_compliance_registry",
        source_ref="system/lib/compliance/__init__.py",
        old="_LazyComplianceAdapters",
        new="RemovedLazyComplianceAdapters",
        engine=lambda root: _compliance_registry_runtime_witness(
            root,
            standalone_only=True,
        ),
        observed_flag="registry_contract_present",
        observed_value=False,
    )


def _bounded_check_failed_negative(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_bounded_check_failed_negative` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _mutated_source_negative(
        public_root,
        case_id="bounded_check_failed",
        source_ref="tools/meta/factory/build_compliance_ledger.py",
        old="_bounded_check_command",
        new="removedBoundedCheckCommand",
        engine=lambda root: _compliance_coverage_bounded_check(
            root,
            standalone_only=True,
        ),
        observed_flag="check_status",
        observed_value=None,
    )


def _baseline_missing_standard_negative(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_baseline_missing_standard_negative` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _mutated_source_negative(
        public_root,
        case_id="baseline_missing_standard",
        source_ref="system/lib/compliance/standard_baseline_adapter.py",
        old="baseline_inventory_only",
        new="baseline_inventory_missing",
        engine=lambda root: _baseline_companion_scanner_contract(
            root,
            standalone_only=True,
        ),
        observed_flag="baseline_contract_present",
        observed_value=False,
    )


def _digest_loses_directive_negative(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_digest_loses_directive_negative` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _mutated_source_negative(
        public_root,
        case_id="digest_loses_directive",
        source_ref="system/lib/pipeline/stage_extract.py",
        old='"need to", "should ", "must ", "the entire point", "the critical"',
        new='"removed_need_to", "should ", "must ", "the entire point", "the critical"',
        engine=_pipeline_digest_and_shard_normalization,
        observed_flag="directive_preserved",
        observed_value=False,
    )


def _compile_helper_empty_mentions_negative(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_compile_helper_empty_mentions_negative` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _mutated_source_negative(
        public_root,
        case_id="compile_helper_empty_mentions",
        source_ref="system/lib/pipeline/stage_compile.py",
        old="resolve_observe_apply_standards_bundle",
        new="removedResolveObserveApplyStandardsBundle",
        engine=lambda root: _pipeline_observe_compile_helpers(
            root,
            standalone_only=True,
        ),
        observed_flag="source_contract_present",
        observed_value=False,
    )


def _pipeline_boundary_missing_negative(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_pipeline_boundary_missing_negative` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _mutated_source_negative(
        public_root,
        case_id="pipeline_boundary_missing",
        source_ref="system/lib/pipeline/stage_execute.py",
        old="observe_dispatch_skipped",
        new="removedObserveDispatchSkipped",
        engine=lambda root: _pipeline_dispatch_process_boundary_contract(
            root,
            standalone_only=True,
        ),
        observed_flag="dispatch_boundary_present",
        observed_value=False,
    )


@lru_cache(maxsize=16)
def _semantic_runtime_exercises(input_ref: str) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_runtime_exercises` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = public_root_for_path(Path(input_ref))
    return {
        "negative_exercises": {
            "missing_compliance_registry": _missing_compliance_registry_negative(public_root),
            "bounded_check_failed": _bounded_check_failed_negative(public_root),
            "baseline_missing_standard": _baseline_missing_standard_negative(public_root),
            "digest_loses_directive": _digest_loses_directive_negative(public_root),
            "compile_helper_empty_mentions": _compile_helper_empty_mentions_negative(public_root),
            "pipeline_boundary_missing": _pipeline_boundary_missing_negative(public_root),
        },
        "body_in_receipt": False,
    }


def _negative_exercise(runtime: Mapping[str, Any], case_id: str) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_negative_exercise` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    cases = (
        runtime.get("negative_exercises")
        if isinstance(runtime.get("negative_exercises"), Mapping)
        else {}
    )
    case = cases.get(case_id)
    return case if isinstance(case, Mapping) else {}


def _observed_negative_case(case_id: str, runtime: Mapping[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_observed_negative_case` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    exercise = _negative_exercise(runtime, case_id)
    return (
        exercise.get("status") == "blocked"
        and exercise.get("negative_condition_observed") is True
    )


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_negative_case` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    expected_code = NEGATIVE_CASE_CODES.get(case_id, "")
    observed = _observed_negative_case(
        case_id,
        _semantic_runtime_exercises(str(Path(input_dir))),
    )
    return {
        "status": "blocked" if observed else "pass",
        "error_codes": [expected_code] if observed and expected_code else [],
        "body_in_receipt": False,
    }


def _compliance_registry_runtime_witness(
    public_root: Path,
    *,
    standalone_only: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_compliance_registry_runtime_witness` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    registry_text = _read(public_root, "system/lib/compliance/__init__.py")
    coverage_text = _read(public_root, "system/lib/compliance/compliance_coverage_adapter.py")
    builder_text = _read(public_root, "tools/meta/factory/build_compliance_ledger.py")
    registry_contract_present = all(
        token in registry_text
        for token in (
            "_LazyComplianceAdapters",
            "DOMAIN_ADAPTER_STANDARD_IDS",
            "BASELINE_ADAPTER_STANDARD_IDS",
            "def scan_all(repo_root: Path)",
        )
    )
    coverage_self_audit_present = all(
        token in coverage_text
        for token in (
            "scanner_coverage_self_audit",
            "ledger_row_coverage",
            "domain_scanner_coverage",
        )
    )
    bounded_builder_present = all(
        token in builder_text
        for token in (
            "_adapter_registry_snapshot",
            "_bounded_check_command",
            "_choose_next_missing_registered_standard",
        )
    )
    if standalone_only:
        return {
            "status": "pass"
            if registry_contract_present
            and coverage_self_audit_present
            and bounded_builder_present
            else "blocked",
            "engine_id": "compliance_registry_runtime_witness",
            "witness_mode": "standalone_copied_source_contract",
            "repo_witness_available": False,
            "registry_contract_present": registry_contract_present,
            "coverage_self_audit_present": coverage_self_audit_present,
            "bounded_builder_present": bounded_builder_present,
            "claim_ceiling": (
                "Copied-source registry shape witness only; not a live adapter "
                "registry count or full compliance-ledger freshness claim."
            ),
        }

    from system.lib.compliance import (
        ADAPTERS,
        BASELINE_ADAPTER_STANDARD_IDS,
        DOMAIN_ADAPTER_STANDARD_IDS,
    )

    adapter_count = len(ADAPTERS)
    domain_count = len(set(DOMAIN_ADAPTER_STANDARD_IDS))
    baseline_count = len(set(BASELINE_ADAPTER_STANDARD_IDS))
    return {
        "status": "pass"
        if adapter_count >= 190
        and domain_count >= 45
        and baseline_count >= 100
        and registry_contract_present
        and coverage_self_audit_present
        and bounded_builder_present
        else "blocked",
        "engine_id": "compliance_registry_runtime_witness",
        "adapter_count": adapter_count,
        "domain_adapter_count": domain_count,
        "baseline_adapter_count": baseline_count,
        "registry_contract_present": registry_contract_present,
        "coverage_self_audit_present": coverage_self_audit_present,
        "bounded_builder_present": bounded_builder_present,
        "claim_ceiling": "Registry and scanner shape witness only; not a full compliance-ledger freshness claim.",
    }


def _standalone_compliance_coverage_contract(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_standalone_compliance_coverage_contract` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, subprocess side effects requested by the caller.
    """
    builder_text = _read(public_root, "tools/meta/factory/build_compliance_ledger.py")
    copied_source_contract_present = all(
        token in builder_text
        for token in (
            "_bounded_check_command",
            "check_status",
            "wrote_ledger",
            "--standard-id",
        )
    )
    return {
        "status": "pass" if copied_source_contract_present else "blocked",
        "engine_id": "compliance_coverage_bounded_check",
        "command": (
            "./repo-python tools/meta/factory/build_compliance_ledger.py "
            "--check --report --standard-id std_compliance_coverage --standard-id std_microcosm"
        ),
        "original_witness": {
            "status": "pass" if copied_source_contract_present else "blocked",
            "returncode": None,
            "witness_mode": "standalone_copied_source_contract",
            "repo_witness_available": False,
            "body_in_receipt": False,
        },
        "check_status": "ok" if copied_source_contract_present else None,
        "wrote_ledger": False,
        "refreshed_standard_ids": ["std_compliance_coverage", "std_microcosm"],
        "scanner_depth_ratchet_status": "standalone_copied_source_contract",
        "ratchet_next_standard_id": "std_agent_bootstrap",
        "partial_projection": True,
        "claim_ceiling": (
            "Standalone copied-source contract witness only; the full bounded "
            "compliance-ledger subprocess witness requires the parent repo."
        ),
    }


def _compliance_coverage_bounded_check(
    public_root: Path,
    *,
    standalone_only: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_compliance_coverage_bounded_check` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    repo_root = _repo_root(public_root)
    command = [
        "./repo-python",
        "tools/meta/factory/build_compliance_ledger.py",
        "--check",
        "--report",
        "--standard-id",
        "std_compliance_coverage",
        "--standard-id",
        "std_microcosm",
    ]
    repo_witness_available = (
        (repo_root / "repo-python").is_file()
        and (repo_root / "tools/meta/factory/build_compliance_ledger.py").is_file()
    )
    if standalone_only or not repo_witness_available:
        return _standalone_compliance_coverage_contract(public_root)

    witness = _run_public_witness(
        command,
        cwd=repo_root,
        timeout=120,
    )
    parsed = witness.get("parsed_summary") if isinstance(witness.get("parsed_summary"), dict) else {}
    refreshed_ids = set(parsed.get("refreshed_standard_ids") or [])
    failure_reasons = parsed.get("check_failure_reasons") or []
    check_status = parsed.get("check_status")
    error_findings = int(parsed.get("error_findings") or 0)
    bounded_no_write_projection = (
        parsed.get("wrote_ledger") is False
        and {"std_compliance_coverage", "std_microcosm"}.issubset(refreshed_ids)
        and parsed.get("bounded_check_partial") is True
        and parsed.get("partial_projection") is True
        and parsed.get("scanner_depth_ratchet_status") == "ready_next_row"
        and bool(parsed.get("ratchet_next_standard_id"))
        and bool(parsed.get("ratchet_next_command"))
    )
    check_truthful = (
        check_status == "ok"
        and witness.get("status") == "pass"
        and error_findings == 0
    ) or (
        check_status == "failed"
        and witness.get("status") == "blocked"
        and error_findings > 0
        and failure_reasons == ["error_findings"]
    )
    return {
        "status": "pass" if bounded_no_write_projection and check_truthful else "blocked",
        "engine_id": "compliance_coverage_bounded_check",
        "command": (
            "./repo-python tools/meta/factory/build_compliance_ledger.py "
            "--check --report --standard-id std_compliance_coverage --standard-id std_microcosm"
        ),
        "original_witness": {
            key: value
            for key, value in witness.items()
            if key != "parsed_summary"
        },
        "check_status": check_status,
        "error_findings": error_findings,
        "check_failure_reasons": failure_reasons,
        "wrote_ledger": parsed.get("wrote_ledger"),
        "refreshed_standard_ids": sorted(refreshed_ids),
        "bounded_check_partial": parsed.get("bounded_check_partial"),
        "scanner_depth_ratchet_status": parsed.get("scanner_depth_ratchet_status"),
        "ratchet_next_standard_id": parsed.get("ratchet_next_standard_id"),
        "ratchet_next_command": parsed.get("ratchet_next_command"),
        "partial_projection": parsed.get("partial_projection"),
        "claim_ceiling": "Bounded no-write compliance check only; stale unselected ledger rows remain outside this claim.",
    }


def _baseline_companion_scanner_contract(
    public_root: Path,
    *,
    standalone_only: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_baseline_companion_scanner_contract` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    baseline_text = _read(public_root, "system/lib/compliance/standard_baseline_adapter.py")
    coverage_text = _read(public_root, "system/lib/compliance/compliance_coverage_adapter.py")
    if standalone_only:
        baseline_contract_present = all(
            token in baseline_text
            for token in (
                "baseline_inventory_only",
                "baseline_standard_file_only",
                "missing_domain_specific_adapter",
                "baseline_companion",
            )
        )
        coverage_contract_present = all(
            token in coverage_text
            for token in (
                "_baseline_companion_finding",
                "domain_scanner_coverage",
                "baseline_adapter",
            )
        )
        return {
            "status": "pass"
            if baseline_contract_present and coverage_contract_present
            else "blocked",
            "engine_id": "baseline_companion_scanner_contract",
            "scan_input_mode": "standalone_copied_source_contract",
            "coverage_row_kind": "baseline_inventory_only",
            "coverage_depth": "baseline_standard_file_only",
            "domain_scanner_status": "missing_domain_specific_adapter",
            "standard_file_status": "json_parseable",
            "baseline_companion": True,
            "baseline_contract_present": baseline_contract_present,
            "coverage_contract_present": coverage_contract_present,
            "claim_ceiling": (
                "Copied-source baseline scanner shape witness only; not a live "
                "repo standard inventory scan."
            ),
        }

    from system.lib.compliance.standard_baseline_adapter import scan_standard_baseline

    repo_root = _repo_root(public_root)
    sample_standard_id = "std_apply"
    if (repo_root / "codex/standards/std_apply.json").is_file():
        row = scan_standard_baseline(repo_root, sample_standard_id)
        scan_input_mode = "parent_repo_standard_inventory"
    else:
        with tempfile.TemporaryDirectory() as tmp:
            scratch_root = Path(tmp)
            standards_dir = scratch_root / "codex/standards"
            standards_dir.mkdir(parents=True)
            standards_dir.joinpath("std_apply.json").write_text(
                json.dumps(
                    {
                        "id": sample_standard_id,
                        "schema_version": "batch8_standalone_baseline_fixture_v1",
                        "purpose": (
                            "Standalone public fixture for exercising the copied "
                            "baseline scanner contract without the parent repo."
                        ),
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            row = scan_standard_baseline(scratch_root, sample_standard_id)
        scan_input_mode = "standalone_public_standard_fixture"
    baseline_row_truthful = all(
        (
            row.get("coverage_row_kind") == "baseline_inventory_only",
            row.get("coverage_depth") == "baseline_standard_file_only",
            row.get("domain_scanner_status") == "missing_domain_specific_adapter",
            row.get("standard_file_status") == "json_parseable",
            row.get("baseline_companion") is True,
        )
    )
    source_contract_present = all(
        token in baseline_text
        for token in (
            "compliance_claim_status",
            "no_compliance_claim",
            "baseline_standard_file_only",
        )
    ) and "baseline_companion_only" in coverage_text
    return {
        "status": "pass" if baseline_row_truthful and source_contract_present else "blocked",
        "engine_id": "baseline_companion_scanner_contract",
        "sample_standard_id": "std_apply",
        "scan_input_mode": scan_input_mode,
        "coverage_path": row.get("coverage_path"),
        "coverage_row_kind": row.get("coverage_row_kind"),
        "domain_scanner_status": row.get("domain_scanner_status"),
        "standard_file_status": row.get("standard_file_status"),
        "source_contract_present": source_contract_present,
        "finding_count": len(row.get("findings") or []),
        "claim_ceiling": "Baseline companion scanner only; does not validate std_apply governed artifacts.",
    }


def _pipeline_digest_and_shard_normalization(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_pipeline_digest_and_shard_normalization` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    stage_extract = _load_copied_source_module(
        public_root,
        "system/lib/pipeline/stage_extract.py",
    )

    raw_seed = "\n".join(
        [
            "# Phase Seed",
            "ordinary narrative line",
            "need to preserve this directive before bridge extraction",
            *("low-signal line" for _ in range(80)),
        ]
    )
    digest = stage_extract.digest_raw_seed(raw_seed, max_chars=240)
    shards_data, changed = stage_extract._normalize_shards_payload(
        {
            "shards": [
                {"id": "s1", "status": "weird", "concept_group": "alpha"},
                {"id": "s2", "status": "selected", "concept_group": "alpha"},
                {"id": "s3", "status": "pending", "concept_group": "beta"},
                {"id": "s4", "status": "pending", "concept_group": "beta"},
                {"id": "s5", "status": "pending", "concept_group": "gamma"},
            ]
        }
    )
    group_counts: dict[str, int] = {}
    selected_ids: set[str] = set()
    chosen = stage_extract._pick_diverse_shards(
        shards_data["shards"],
        count=4,
        group_counts=group_counts,
        selected_ids=selected_ids,
    )
    directive_preserved = "need to preserve this directive" in digest
    status_normalized = shards_data["shards"][0]["status"] == "pending"
    variant_preserved = shards_data["shards"][0].get("status_variant") == "weird"
    diversity_cap_applied = group_counts.get("alpha") == 2 and len(chosen) == 4
    copied_source_anchors = all(
        token in _read(public_root, "system/lib/pipeline/stage_extract.py")
        for token in (
            "MAX_PROBE_TARGET_FILES",
            "NEW_SHARD_EXISTING_SIMILARITY",
            "_extract_synthesis_json",
        )
    )
    return {
        "status": "pass"
        if directive_preserved
        and changed
        and status_normalized
        and variant_preserved
        and diversity_cap_applied
        and copied_source_anchors
        else "blocked",
        "engine_id": "pipeline_digest_and_shard_normalization",
        "digest_char_count": len(digest),
        "directive_preserved": directive_preserved,
        "normalization_changed": changed,
        "status_normalized": status_normalized,
        "status_variant_preserved": variant_preserved,
        "chosen_shard_count": len(chosen),
        "group_counts": dict(group_counts),
        "copied_source_anchors_present": copied_source_anchors,
        "claim_ceiling": "Pure helper exercise only; no raw seed or shard ledger writes.",
    }


def _pipeline_observe_compile_helpers(
    public_root: Path,
    *,
    standalone_only: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_pipeline_observe_compile_helpers` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values, declared filesystem outputs.
    """
    if standalone_only:
        def _dedupe_strings(values: list[str]) -> list[str]:
            """
            [ACTION]
            - Teleology: Implements `_pipeline_observe_compile_helpers._dedupe_strings` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
            - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
            - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
            - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
            - Reads: call arguments, module constants, imported helpers.
            - Writes: return values.
            """
            return list(dict.fromkeys(values))

        def _flatten_text_entries(values: Any) -> list[str]:
            """
            [ACTION]
            - Teleology: Implements `_pipeline_observe_compile_helpers._flatten_text_entries` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
            - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
            - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
            - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
            - Reads: call arguments, module constants, imported helpers.
            - Writes: return values.
            """
            output: list[str] = []
            for item in values if isinstance(values, list) else []:
                if isinstance(item, Mapping):
                    text = str(item.get("text") or item.get("summary") or "").strip()
                else:
                    text = str(item or "").strip()
                if text:
                    output.append(text)
            return _dedupe_strings(output)

        def _extract_known_file_mentions(
            texts: list[str],
            known_files: list[str],
        ) -> list[str]:
            """
            [ACTION]
            - Teleology: Implements `_pipeline_observe_compile_helpers._extract_known_file_mentions` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
            - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
            - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
            - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
            - Reads: call arguments, module constants, imported helpers.
            - Writes: return values.
            """
            normalized_texts = [
                str(text or "").strip().lower()
                for text in texts
                if str(text or "").strip()
            ]
            normalized_known = _dedupe_strings(
                [str(path or "").strip() for path in known_files if str(path or "").strip()]
            )
            return _dedupe_strings(
                [
                    path
                    for text in normalized_texts
                    for path in sorted(normalized_known, key=len, reverse=True)
                    if path.lower() in text
                ]
            )

        def _priority_followup_files(
            *,
            known_files: list[str],
            active_scope_files: list[str],
            missing_evidence: Any = None,
        ) -> list[str]:
            """
            [ACTION]
            - Teleology: Implements `_pipeline_observe_compile_helpers._priority_followup_files` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
            - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
            - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
            - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
            - Reads: call arguments, module constants, imported helpers.
            - Writes: return values.
            """
            known = _dedupe_strings(
                [str(path).strip() for path in known_files if str(path).strip()]
            )
            active_scope = set(
                _dedupe_strings(
                    [
                        str(path).strip()
                        for path in active_scope_files
                        if str(path).strip()
                    ]
                )
            )
            mentioned = _extract_known_file_mentions(
                _flatten_text_entries(missing_evidence),
                known,
            )
            outside_active = [path for path in mentioned if path not in active_scope]
            inside_active = [path for path in mentioned if path in active_scope]
            return _dedupe_strings([*outside_active, *inside_active])

        def _probe_questions_for_plan_path(plan_path: Path | None) -> list[str]:
            """
            [ACTION]
            - Teleology: Implements `_pipeline_observe_compile_helpers._probe_questions_for_plan_path` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
            - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
            - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
            - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
            - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
            - Writes: return values.
            """
            if plan_path is None or not plan_path.exists():
                return []
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            questions: list[str] = []
            for group in plan.get("groups", []):
                if not isinstance(group, Mapping):
                    continue
                role = str(group.get("role") or "probe").strip().lower() or "probe"
                question = str(group.get("question") or "").strip()
                if question and role not in {"synthesis", "summary"}:
                    questions.append(question)
            return _dedupe_strings(questions)
    else:
        from system.lib.pipeline.stage_compile import (
            _extract_known_file_mentions,
            _flatten_text_entries,
            _priority_followup_files,
            _probe_questions_for_plan_path,
        )
    texts = _flatten_text_entries(
        [
            {"summary": "Inspect system/lib/pipeline/stage_compile.py next."},
            "Then confirm system/lib/compliance/__init__.py registry wiring.",
        ]
    )
    known_files = [
        "system/lib/pipeline/stage_compile.py",
        "system/lib/compliance/__init__.py",
        "system/lib/pipeline/stage_execute.py",
    ]
    mentions = _extract_known_file_mentions(texts, known_files)
    priority = _priority_followup_files(
        known_files=known_files,
        active_scope_files=["system/lib/pipeline/stage_execute.py"],
        missing_evidence=texts,
    )
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = Path(tmp) / "observe_plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "groups": [
                        {"role": "probe", "question": "What pipeline helper is next?"},
                        {"role": "synthesis", "question": "Ignored"},
                        {"role": "advisory", "question": "Which compliance scanner is missing?"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        questions = _probe_questions_for_plan_path(plan_path)
    source_contract_present = all(
        token in _read(public_root, "system/lib/pipeline/stage_compile.py")
        for token in (
            "compile_observe_plan",
            "_bounded_target_specs",
            "_sanitize_synthesis_payload",
            "resolve_observe_apply_standards_bundle",
        )
    )
    return {
        "status": "pass"
        if len(texts) == 2
        and set(mentions) == set(known_files[:2])
        and priority[:2] == known_files[:2]
        and questions == [
            "What pipeline helper is next?",
            "Which compliance scanner is missing?",
        ]
        and source_contract_present
        else "blocked",
        "engine_id": "pipeline_observe_compile_helpers",
        "flattened_text_count": len(texts),
        "mentioned_files": mentions,
        "priority_files": priority,
        "probe_questions": questions,
        "source_contract_present": source_contract_present,
        "claim_ceiling": "Compile helper exercise only; no observe plan is dispatched.",
    }


def _pipeline_dispatch_process_boundary_contract(
    public_root: Path,
    *,
    standalone_only: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_pipeline_dispatch_process_boundary_contract` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if standalone_only:
        def _receipt_selection_meta(
            phase: str,
            group: dict[str, Any] | None,
            source: str,
        ) -> tuple[str, dict[str, Any]]:
            """
            [ACTION]
            - Teleology: Implements `_pipeline_dispatch_process_boundary_contract._receipt_selection_meta` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
            - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
            - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
            - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
            - Reads: call arguments, module constants, imported helpers.
            - Writes: return values.
            """
            label = str((group or {}).get("label") or "").strip()
            role = str((group or {}).get("role") or "").strip().lower() or ""
            if phase == "scope":
                selection_kind = "scope"
            elif phase == "plan":
                selection_kind = "plan"
            elif label == "router" or role in {"synthesis", "evaluation"}:
                selection_kind = "router"
            else:
                selection_kind = "probe_fallback"
            normalized_source = (
                f"{selection_kind}_{source}" if source not in {"", "none"} else "none"
            )
            return normalized_source, {
                "selected_group_label": label or None,
                "selected_group_role": role or None,
                "selection_kind": selection_kind,
                "is_fallback": selection_kind == "probe_fallback",
                "source": normalized_source,
            }
    else:
        from system.lib.pipeline.stage_process import _receipt_selection_meta

    source, meta = _receipt_selection_meta(
        "scope",
        {"label": "router", "role": "synthesis"},
        "typed_receipt",
    )
    execute_text = _read(public_root, "system/lib/pipeline/stage_execute.py")
    process_text = _read(public_root, "system/lib/pipeline/stage_process.py")
    select_text = _read(public_root, "system/lib/pipeline/stage_select.py")
    emit_text = _read(public_root, "system/lib/pipeline/stage_emit.py")
    dispatch_boundary_present = all(
        token in execute_text
        for token in (
            "observe_dispatch_skipped",
            "observe_dispatch_started",
            "save_state_if_not_stale",
        )
    )
    processing_boundary_present = all(
        token in process_text
        for token in (
            "_select_primary_receipt",
            "_apply_synthesis_updates_to_shards",
            "carry_forward_context",
            "cycle_assimilation",
        )
    )
    select_emit_boundary_present = all(
        (
            "constrain_shard_candidates" in select_text,
            "write_controller_artifacts" in select_text,
            "write_controller_artifacts" in emit_text,
            "synth_seed_emitted" in emit_text,
        )
    )
    receipt_meta_truthful = (
        source == "scope_typed_receipt"
        and meta.get("selection_kind") == "scope"
        and meta.get("is_fallback") is False
    )
    return {
        "status": "pass"
        if dispatch_boundary_present
        and processing_boundary_present
        and select_emit_boundary_present
        and receipt_meta_truthful
        else "blocked",
        "engine_id": "pipeline_dispatch_process_boundary_contract",
        "dispatch_boundary_present": dispatch_boundary_present,
        "processing_boundary_present": processing_boundary_present,
        "select_emit_boundary_present": select_emit_boundary_present,
        "receipt_selection_source": source,
        "receipt_selection_kind": meta.get("selection_kind"),
        "claim_ceiling": "Static and pure process-boundary exercise only; bridge dispatch stays disabled.",
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_evaluate` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    exported_bundle_input = (
        (input_path / "source_module_manifest.json").is_file()
        and (input_path / "source_modules").is_dir()
    )
    engines = [
        _compliance_registry_runtime_witness(
            public_root,
            standalone_only=exported_bundle_input,
        ),
        _compliance_coverage_bounded_check(
            public_root,
            standalone_only=exported_bundle_input,
        ),
        _baseline_companion_scanner_contract(
            public_root,
            standalone_only=exported_bundle_input,
        ),
        _pipeline_digest_and_shard_normalization(public_root),
        _pipeline_observe_compile_helpers(
            public_root,
            standalone_only=exported_bundle_input,
        ),
        _pipeline_dispatch_process_boundary_contract(
            public_root,
            standalone_only=exported_bundle_input,
        ),
    ]
    findings: list[dict[str, Any]] = []
    for engine in engines:
        if engine.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH8_COMPLIANCE_PIPELINE_ENGINE_BLOCKED",
                    "Compliance/pipeline engine exercise did not pass.",
                    subject_id=str(engine.get("engine_id")),
                    observed=engine.get("status"),
                )
            )
    if source_manifest.get("module_count", 0) < len(SOURCE_REQUIRED_ANCHORS):
        findings.append(
            finding(
                "BATCH8_COMPLIANCE_PIPELINE_SOURCE_MODULE_COUNT_LOW",
                "Compliance/pipeline capsule must copy every required source body.",
                expected=len(SOURCE_REQUIRED_ANCHORS),
                observed=source_manifest.get("module_count"),
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "input_manifest_schema": input_path.joinpath(EXERCISE_MANIFEST_NAME).name,
        "engine_count": len(engines),
        "engine_ids": [str(engine.get("engine_id")) for engine in engines],
        "engines": engines,
        "copied_macro_source_module_count": source_manifest.get("module_count"),
        "error_codes": [
            str(engine["original_witness"].get("error_code"))
            for engine in engines
            if isinstance(engine.get("original_witness"), Mapping)
            and engine["original_witness"].get("error_code")
        ],
        "findings": findings,
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch8_compliance_pipeline_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_batch8_compliance_pipeline_bundle` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    source = (
        result.get("source_module_manifest")
        if isinstance(result.get("source_module_manifest"), Mapping)
        else {}
    )
    ceiling = (
        result.get("authority_ceiling")
        if isinstance(result.get("authority_ceiling"), Mapping)
        else {}
    )
    card["engine_count"] = exercise.get("engine_count")
    card["engine_ids"] = exercise.get("engine_ids", [])
    card["authority_floor"] = {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "real_substrate_disposition": ceiling.get("real_substrate_disposition"),
        "release_authorized": ceiling.get("release_authorized"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "provider_dispatch": ceiling.get("provider_dispatch"),
        "model_dispatch": ceiling.get("model_dispatch"),
        "source_mutation_authorized": ceiling.get("source_mutation_authorized"),
        "raw_seed_mutation_authorized": ceiling.get("raw_seed_mutation_authorized"),
        "full_compliance_ledger_freshness_claim": ceiling.get(
            "full_compliance_ledger_freshness_claim"
        ),
        "full_pipeline_dispatch_authority": ceiling.get(
            "full_pipeline_dispatch_authority"
        ),
        "test_completeness_proof": ceiling.get("test_completeness_proof"),
    }
    card["body_floor"] = {
        "body_in_receipt": result.get("body_in_receipt"),
        "source_module_body_in_receipt": source.get("body_in_receipt"),
        "receipt_body_scan_status": (
            result.get("receipt_body_scan", {}).get("status")
            if isinstance(result.get("receipt_body_scan"), Mapping)
            else None
        ),
        "source_bodies_in_card": False,
        "secret_scan_scope_in_card": False,
    }
    return card


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.batch8_compliance_pipeline_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "validate-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    result = run_crown_jewel_organ(
        SPEC,
        args.input,
        args.out,
        command=f"{ORGAN_ID} {args.action}",
        acceptance_out=args.acceptance_out,
        input_mode=BUNDLE_INPUT_MODE if args.action == "validate-bundle" else "fixture_input",
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )
    print(json.dumps(result_card(result) if args.card else result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
