"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.undeclared_library_prior_symbol_classifier` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, CARD_OMITTED_FULL_PAYLOAD_KEYS, SOURCE_REFS, RECEIPT_ANCHOR_REFS, SOURCE_TARGET_REFS, SOURCE_DIGESTS, BODY_MATERIAL_STATUS, SYMBOL_BOUNDARY_STATUS, TOOLCHAIN_BOUNDARY_STATUS, BODY_IN_RECEIPT, SOURCE_MODULE_MANIFEST_REF, SOURCE_MODULE_REFS, SOURCE_MODULE_IMPORT_CLASSES, SOURCE_MODULE_RELATIONS, SOURCE_MODULE_MATERIAL_CLASSES, SOURCE_MODULE_BODY_MATERIAL_STATUS, ...
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


ORGAN_ID = "undeclared_library_prior_symbol_classifier"
FIXTURE_ID = "first_wave.undeclared_library_prior_symbol_classifier"
VALIDATOR_ID = "validator.microcosm.organs.undeclared_library_prior_symbol_classifier"

RESULT_NAME = "undeclared_library_prior_symbol_classifier_result.json"
BOARD_NAME = "undeclared_library_prior_symbol_classifier_board.json"
VALIDATION_RECEIPT_NAME = (
    "undeclared_library_prior_symbol_classifier_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "undeclared_library_prior_symbol_classifier_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_symbol_classifier_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "undeclared_library_prior_symbol_classifier_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "expected_negative_cases",
    "observed_negative_cases",
    "missing_negative_cases",
    "error_codes",
    "findings",
    "secret_exclusion_scan",
    "authority_ceiling",
    "anti_claim",
    "source_refs",
    "source_pattern_ids",
    "projection_receipt_refs",
    "receipt_anchor_refs",
    "source_target_refs",
    "source_digests",
    "real_substrate_refs",
    "source_modules",
    "source_open_body_imports",
    "premises",
    "classification_rows",
    "symbol_classifier_board",
)

SOURCE_REFS = [
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_index.json",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_retrieval_graph_v0/run_summary.json",
    "microcosm-substrate/fixtures/first_wave/lean_std_premise_index/input/premise_index.json",
    "microcosm-substrate/receipts/first_wave/corpus_readiness_mathlib_absence_gate/corpus_readiness_mathlib_absence_gate_result.json",
    "microcosm-substrate/receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_result.json",
    "tools/meta/factory/reduce_prover_provider_receipts.py",
    "tools/meta/factory/build_prover_provider_batch_context_calibration_report.py",
    "state/runs/PROVER_PROVIDER_BATCH_CONTEXT_CALIBRATION_20260511_v0/recipe_policy_metrics.json",
    "state/runs/PROVER_PROVIDER_BATCH_CONTEXT_CALIBRATION_20260511_v0/provider_receipt_reduction_matrix.json",
]
RECEIPT_ANCHOR_REFS = [
    "microcosm-substrate/receipts/first_wave/lean_std_premise_index/lean_std_premise_index_result.json",
    "microcosm-substrate/receipts/first_wave/corpus_readiness_mathlib_absence_gate/corpus_readiness_mathlib_absence_gate_result.json",
    "microcosm-substrate/receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_result.json",
]
SOURCE_TARGET_REFS = [
    "microcosm-substrate/fixtures/first_wave/undeclared_library_prior_symbol_classifier/input/premise_index.json",
    "microcosm-substrate/fixtures/first_wave/undeclared_library_prior_symbol_classifier/input/symbol_observations.json",
    "microcosm-substrate/examples/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle/premise_index.json",
    "microcosm-substrate/examples/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle/symbol_observations.json",
    "microcosm-substrate/receipts/first_wave/undeclared_library_prior_symbol_classifier/undeclared_library_prior_symbol_classifier_result.json",
    "microcosm-substrate/receipts/first_wave/undeclared_library_prior_symbol_classifier/undeclared_library_prior_symbol_classifier_board.json",
    "microcosm-substrate/receipts/first_wave/undeclared_library_prior_symbol_classifier/undeclared_library_prior_symbol_classifier_validation_receipt.json",
    ACCEPTANCE_RECEIPT_REL,
    "microcosm-substrate/receipts/runtime_shell/demo_project/organs/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle_validation_result.json",
]
SOURCE_DIGESTS = {
    SOURCE_REFS[0]: "sha256:c78b176388a5e81bd8a785950e7db0c9a65fd38e556515134146163b48604df1",
    SOURCE_REFS[1]: "sha256:93304410f32d40f5cad1c161c1d01a5d6f353ee10b7cf3fecbaaf7b068b43008",
    SOURCE_REFS[2]: "sha256:0be36ba5b75b40d2ede2d90cefa5181829420df7abbae216d18282b92a30f869",
    SOURCE_REFS[3]: "sha256:ff2a6ee61993dc2e848bec3afa692a6f21950d3c9d92d9ec11e311c0a97da9ba",
    SOURCE_REFS[4]: "sha256:2a2ea1ff7379d58673d414bc055996384b1fadd63f747aa56e1be818225b79eb",
    SOURCE_REFS[5]: "sha256:1302a9b92b971371bdc3f6264140205f6111490d4140a30be076c2994a7576c6",
    SOURCE_REFS[6]: "sha256:076b27360b623dd27e7e391a0d2e3c52aa2c9df9fc5db01aaf93418d30bc473a",
    SOURCE_REFS[7]: "sha256:9c221eb32eeba32a1a1c9814f6c4091b6d791835152be7e76bb6778ab869659f",
    SOURCE_REFS[8]: "sha256:bc6aa128fcb98e29cc7b3f6ac594c9aaf022dc45059a5e1101695bd20660817a",
}
BODY_MATERIAL_STATUS = "copied_non_secret_macro_body_with_provenance"
SYMBOL_BOUNDARY_STATUS = "real_lean_std_symbol_boundary_and_mathlib_absence_context"
TOOLCHAIN_BOUNDARY_STATUS = "real_lean_4_29_1_std_mathlib_absence_probe"
BODY_IN_RECEIPT = False
SOURCE_MODULE_MANIFEST_REF = (
    "examples/undeclared_library_prior_symbol_classifier/"
    "exported_symbol_classifier_bundle/source_module_manifest.json"
)
SOURCE_MODULE_REFS = [
    "tools/meta/factory/reduce_prover_provider_receipts.py",
    "tools/meta/factory/build_prover_provider_batch_context_calibration_report.py",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_index.json",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_retrieval_graph_v0/run_summary.json",
    "state/runs/PROVER_PROVIDER_BATCH_CONTEXT_CALIBRATION_20260511_v0/recipe_policy_metrics.json",
    "state/runs/PROVER_PROVIDER_BATCH_CONTEXT_CALIBRATION_20260511_v0/provider_receipt_reduction_matrix.json",
]
SOURCE_MODULE_IMPORT_CLASSES = {
    "copied_non_secret_macro_body",
    "source_faithful_public_safe_macro_body",
}
SOURCE_MODULE_RELATIONS = {
    "source_faithful_public_safe_exact_copy",
    "source_faithful_public_safe_path_normalized_copy",
}
SOURCE_MODULE_MATERIAL_CLASSES = {
    "public_macro_tool_body",
    "public_macro_receipt_body",
    "public_macro_pattern_body",
}
SOURCE_MODULE_BODY_MATERIAL_STATUS = (
    "source_faithful_public_safe_undeclared_library_prior_symbol_classifier_"
    "macro_bodies_with_digest_provenance"
)
RUN_SUMMARY_SOURCE_MODULE_ID = "ring2_premise_retrieval_run_summary_body_import"

INPUT_NAMES = (
    "projection_protocol.json",
    "premise_index.json",
    "symbol_observations.json",
    "classifier_policy.json",
)
NEGATIVE_INPUT_NAMES = (
    "proof_body_leakage.json",
    "private_source_ref_leakage.json",
    "missing_escalation_for_undeclared_symbol.json",
    "premise_budget_precedence_violation.json",
    "allowed_symbol_false_positive.json",
    "unqualified_symbol_overclaim.json",
    "theorem_correctness_overclaim.json",
)

EXPECTED_NEGATIVE_CASES = {
    "proof_body_leakage": ["SYMBOL_CLASSIFIER_PROOF_BODY_FORBIDDEN"],
    "private_source_ref_leakage": ["SYMBOL_CLASSIFIER_PRIVATE_SOURCE_REF_FORBIDDEN"],
    "missing_escalation_for_undeclared_symbol": [
        "SYMBOL_CLASSIFIER_UNDECLARED_LIBRARY_PRIOR_NOT_ESCALATED"
    ],
    "premise_budget_precedence_violation": [
        "SYMBOL_CLASSIFIER_PREMISE_BUDGET_PRECEDENCE"
    ],
    "allowed_symbol_false_positive": ["SYMBOL_CLASSIFIER_ALLOWED_SYMBOL_FALSE_POSITIVE"],
    "unqualified_symbol_overclaim": ["SYMBOL_CLASSIFIER_UNQUALIFIED_SYMBOL_OVERCLAIM"],
    "theorem_correctness_overclaim": ["SYMBOL_CLASSIFIER_THEOREM_CORRECTNESS_OVERCLAIM"],
}
ASSERTION_MISMATCH_CASE_ID = "symbol_observation_assertion_floor"

QUALIFIED_SYMBOL_RE = re.compile(r"\b(?:Nat|List|Bool|Iff|Eq)\.[A-Za-z0-9_.'+]+")
FORBIDDEN_PROOF_KEYS = (
    "proof_body",
    "candidate_proof_body",
    "ground_truth_proof",
    "private_proof_body",
)
PRIVATE_SOURCE_KEYS = (
    "private_source_ref",
    "private_source_refs",
    "raw_source_path",
    "oracle_source_ref",
)

UNDECLARED_CLASS = "UNDECLARED_LIBRARY_PRIOR"
PREMISE_BUDGET_CLASS = "PREMISE_BUDGET_VIOLATION"
BRIDGE_OUTCOME = "bridge_escalate"
RETRY_OUTCOME = "retry"

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "real_lean_std_symbol_boundary_not_theorem_authority",
    "formal_proof_authority": False,
    "theorem_correctness_authority": False,
    "lean_lake_execution_authorized": False,
    "mathlib_absence_is_probe_result": True,
    "proof_bodies_allowed": False,
    "private_source_refs_allowed": False,
    "provider_calls_authorized": False,
    "premise_budget_retry_authority": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Undeclared library prior symbol classifier validates copied non-secret "
    "Lean/Std premise rows and Ring2 symbol-boundary observations with a "
    "Mathlib-absent toolchain boundary. It does not run Lean or Lake, prove "
    "theorem correctness, expose proof bodies or private source refs, call "
    "providers, turn the whole library into an allowlist, or authorize release."
)


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_display` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_rows` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
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


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    bundle_manifest = input_dir / "bundle_manifest.json"
    if bundle_manifest.is_file():
        paths.append(bundle_manifest)
    source_module_manifest = _source_module_manifest_path(input_dir)
    if source_module_manifest.is_file():
        paths.append(source_module_manifest)
    return paths


def _source_module_manifest_path(input_dir: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_path` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return input_dir / "source_module_manifest.json"


def _target_path_from_module(input_dir: Path, row: dict[str, Any]) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_target_path_from_module` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    raw = str(row.get("path") or "")
    candidate = Path(raw)
    return candidate if candidate.is_absolute() else input_dir / candidate


def _source_module_scan_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_scan_paths` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    manifest = read_json_strict(manifest_path)
    return [
        _target_path_from_module(input_dir, row)
        for row in _rows(manifest, "modules")
    ]


def _source_module_payload_by_id(input_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_payload_by_id` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return {}
    manifest = read_json_strict(manifest_path)
    payloads: dict[str, Any] = {}
    for row in _rows(manifest, "modules"):
        module_id = str(row.get("module_id") or "")
        if not module_id:
            continue
        target = _target_path_from_module(input_dir, row)
        if target.is_file() and target.suffix == ".json":
            payloads[module_id] = read_json_strict(target)
    return payloads


def _sha256_file(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256_file` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _freshness_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_paths` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    return [
        *_input_paths(source, include_negative=include_negative),
        *_source_module_scan_paths(source),
        public_root / "core/private_state_forbidden_classes.json",
    ]


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_basis` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source = Path(input_dir)
    if not source.is_absolute():
        source = Path.cwd() / source
    public_root = _public_root_for_path(source)

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[Path] = set()
    for path in _freshness_paths(source, include_negative=include_negative):
        key = path.resolve(strict=False)
        if key in seen:
            continue
        seen.add(key)
        display = _display(path, public_root=public_root)
        if path.is_file():
            rows.append(
                {
                    "path": display,
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            missing.append(display)

    validator_schema_version = (
        "undeclared_library_prior_symbol_classifier_result_v1"
        if include_negative
        else "exported_symbol_classifier_bundle_validation_result_v1"
    )
    basis_digest = hashlib.sha256(
        json.dumps(
            {
                "card_schema_version": CARD_SCHEMA_VERSION,
                "include_negative": include_negative,
                "inputs": rows,
                "missing_inputs": missing,
                "validator_schema_version": validator_schema_version,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": (
            "undeclared_library_prior_symbol_classifier_freshness_basis_v1"
        ),
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_symbol_classifier_bundle_receipt(
    input_dir: Path,
    out_dir: Path,
    *,
    command: str,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Implements `_fresh_symbol_classifier_bundle_receipt` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    path = out_dir / BUNDLE_RESULT_NAME
    if not path.is_file():
        return None
    try:
        payload = read_json_strict(path)
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != (
        "exported_symbol_classifier_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("input_mode") != "exported_symbol_classifier_bundle":
        return None
    if payload.get("command") != command:
        return None
    basis = _freshness_basis(input_dir, include_negative=False)
    existing_basis = payload.get("freshness_basis")
    if not isinstance(existing_basis, dict):
        return None
    if existing_basis.get("basis_digest") != basis["basis_digest"]:
        return None
    if basis["missing_path_count"]:
        return None
    reused = dict(payload)
    reused["freshness_basis"] = basis
    reused["receipt_reused"] = True
    return reused


def _line_count(path: Path) -> int:
    """
    [ACTION]
    - Teleology: Implements `_line_count` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    data = path.read_bytes()
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


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
    - Teleology: Implements `_finding` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_record` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
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


def _has_forbidden_key(row: dict[str, Any], keys: tuple[str, ...]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_has_forbidden_key` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return any(key in row for key in keys)


def _private_ref_present(row: dict[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_private_ref_present` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if _has_forbidden_key(row, PRIVATE_SOURCE_KEYS):
        return True
    refs = _strings(row.get("source_refs")) + _strings(row.get("source_anchor_refs"))
    return any(ref.startswith(("private:", "macro-private:", "/Users/")) for ref in refs)


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    """
    [ACTION]
    - Teleology: Implements `_merge_observed` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_merge_findings` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
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


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_projection_protocol` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    source_targets = _strings(protocol.get("source_target_refs"))
    receipt_anchors = _strings(protocol.get("receipt_anchor_refs"))
    source_digests = protocol.get("source_digests", {})
    omitted = _rows(protocol, "omitted_material")
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 3
        or len(source_pattern_ids) < 3
        or len(source_targets) < 3
        or not isinstance(source_digests, dict)
        or not source_digests
    ):
        findings.append(
            _finding(
                "SYMBOL_CLASSIFIER_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Symbol classifier projection must cite real source refs, pattern ids, target refs, and source digests.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for row in omitted:
        if not row.get("omission_receipt_ref"):
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_OMISSION_RECEIPT_MISSING",
                    "Omitted proof/private/provider material must carry an omission receipt.",
                    case_id="projection_protocol_floor",
                    subject_id=str(row.get("material_id") or "omitted_material"),
                    subject_kind="projection_protocol",
                )
            )
    return {
        "status": PASS
        if source_refs
        and source_pattern_ids
        and projection_receipts
        and source_targets
        and isinstance(source_digests, dict)
        and source_digests
        and not findings
        else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "source_target_refs": source_targets,
        "receipt_anchor_refs": receipt_anchors,
        "source_digests": {str(key): str(value) for key, value in sorted(source_digests.items())}
        if isinstance(source_digests, dict)
        else {},
        "omitted_material_count": len(omitted),
        "findings": findings,
        "observed_negative_cases": {},
    }


def _premise_maps(payload: object) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """
    [ACTION]
    - Teleology: Implements `_premise_maps` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    by_id: dict[str, dict[str, Any]] = {}
    by_symbol: dict[str, dict[str, Any]] = {}
    for row in _rows(payload, "premises"):
        premise_id = str(row.get("premise_id") or "")
        symbol = str(row.get("theorem_or_def_name") or "")
        if premise_id:
            by_id[premise_id] = row
        if symbol:
            by_symbol[symbol] = row
    return by_id, by_symbol


def validate_premise_index(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_premise_index` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "premises")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        premise_id = str(row.get("premise_id") or "")
        symbol = str(row.get("theorem_or_def_name") or "")
        namespace = str(row.get("namespace") or "")
        source_ref = str(row.get("source_ref") or "")
        if not premise_id or not symbol or "." not in symbol:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_PREMISE_ID_OR_SYMBOL_MISSING",
                    "Premise index rows require a premise id and qualified theorem_or_def_name.",
                    case_id="premise_index_floor",
                    subject_id=premise_id or symbol or "premise",
                    subject_kind="premise_index",
                )
            )
        if not source_ref:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_PREMISE_SOURCE_REF_MISSING",
                    "Premise index rows require a public source ref.",
                    case_id="premise_index_floor",
                    subject_id=premise_id or symbol or "premise",
                    subject_kind="premise_index",
                )
            )
        exported.append(
            {
                "premise_id": premise_id,
                "theorem_or_def_name": symbol,
                "namespace": namespace,
                "source_ref": source_ref,
                "allowed_for_split": _strings(row.get("allowed_for_split")),
                "body_in_receipt": BODY_IN_RECEIPT,
                "body_material_status": str(
                    row.get("body_material_status") or "imported_premise_index_row"
                ),
            }
        )
    return {
        "status": PASS if rows and not findings else "blocked",
        "premise_count": len(rows),
        "namespace_count": len({row["namespace"] for row in exported if row["namespace"]}),
        "premises": sorted(exported, key=lambda row: row["premise_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_classifier_policy(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_classifier_policy` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    policy = payload if isinstance(payload, dict) else {}
    findings: list[dict[str, Any]] = []
    if policy.get("proof_bodies_allowed") is True:
        findings.append(
            _finding(
                "SYMBOL_CLASSIFIER_POLICY_PROOF_BODY_ALLOWED",
                "The public classifier policy cannot allow proof bodies.",
                case_id="classifier_policy_floor",
                subject_id=str(policy.get("policy_id") or "classifier_policy"),
                subject_kind="classifier_policy",
            )
        )
    return {
        "status": PASS
        if policy.get("qualified_symbol_regex") == QUALIFIED_SYMBOL_RE.pattern
        and policy.get("undeclared_review_outcome") == BRIDGE_OUTCOME
        and policy.get("premise_budget_review_outcome") == RETRY_OUTCOME
        and not findings
        else "blocked",
        "policy_id": policy.get("policy_id"),
        "qualified_symbol_regex": policy.get("qualified_symbol_regex"),
        "undeclared_review_outcome": policy.get("undeclared_review_outcome"),
        "premise_budget_review_outcome": policy.get("premise_budget_review_outcome"),
        "proof_bodies_allowed": bool(policy.get("proof_bodies_allowed")),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_source_module_manifest(
    input_dir: Path,
    *,
    public_root: Path,
    required: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_source_module_manifest` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return {
            "status": "blocked" if required else "not_present",
            "source_modules_pass": not required,
            "source_module_manifest_ref": "",
            "manifest_id": None,
            "module_count": 0,
            "verified_module_count": 0,
            "modules": [],
            "findings": []
            if not required
            else [
                _finding(
                    "SYMBOL_CLASSIFIER_SOURCE_MODULE_MANIFEST_MISSING",
                    "Exported symbol-classifier bundles must include source_module_manifest.json for copied macro bodies.",
                    case_id="source_module_manifest_floor",
                    subject_id=SOURCE_MODULE_MANIFEST_REF,
                    subject_kind="source_module_manifest",
                )
            ],
            "observed_negative_cases": {},
            "source_open_body_imports": {},
        }

    manifest = read_json_strict(manifest_path)
    modules = _rows(manifest, "modules")
    findings: list[dict[str, Any]] = []
    if manifest.get("source_import_class") not in SOURCE_MODULE_IMPORT_CLASSES:
        findings.append(
            _finding(
                "SYMBOL_CLASSIFIER_SOURCE_MODULE_IMPORT_CLASS_INVALID",
                "Source-module manifest must classify symbol-classifier bodies as copied or source-faithful public-safe macro bodies.",
                case_id="source_module_manifest_floor",
                subject_id=str(manifest.get("manifest_id") or SOURCE_MODULE_MANIFEST_REF),
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "SYMBOL_CLASSIFIER_SOURCE_MODULE_BODY_IN_RECEIPT_FORBIDDEN",
                "Copied macro source bodies must stay in source_modules, not receipt bodies.",
                case_id="source_module_manifest_floor",
                subject_id=str(manifest.get("manifest_id") or SOURCE_MODULE_MANIFEST_REF),
                subject_kind="source_module_manifest",
            )
        )

    module_source_refs = {str(row.get("source_ref") or "") for row in modules}
    missing_source_refs = sorted(set(SOURCE_MODULE_REFS) - module_source_refs)
    unknown_source_refs = sorted(module_source_refs - set(SOURCE_MODULE_REFS))
    if required and missing_source_refs:
        findings.append(
            _finding(
                "SYMBOL_CLASSIFIER_SOURCE_MODULE_SOURCE_REF_MISSING",
                "Source-module manifest must account for every declared symbol-classifier macro owner ref.",
                case_id="source_module_manifest_floor",
                subject_id=",".join(missing_source_refs),
                subject_kind="source_module_manifest",
            )
        )
    for source_ref in unknown_source_refs:
        findings.append(
            _finding(
                "SYMBOL_CLASSIFIER_SOURCE_MODULE_UNKNOWN_SOURCE_REF",
                "Source-module rows must cite one of the declared symbol-classifier macro owner refs.",
                case_id="source_module_manifest_floor",
                subject_id=source_ref or "source_module",
                subject_kind="source_module",
            )
        )

    module_results: list[dict[str, Any]] = []
    verified_ids: list[str] = []
    material_classes: set[str] = set()
    for row in modules:
        source_ref = str(row.get("source_ref") or "")
        material_id = str(row.get("module_id") or source_ref or "source_module")
        material_class = str(row.get("material_class") or "")
        material_classes.add(material_class)
        target = _target_path_from_module(input_dir, row)
        exists = target.is_file()
        expected_digest = str(
            row.get("target_sha256") or row.get("sha256") or ""
        ).removeprefix("sha256:")
        actual_digest = _sha256_file(target) if exists else ""
        expected_line_count = row.get("target_line_count", row.get("line_count"))
        actual_line_count = _line_count(target) if exists else None
        expected_byte_count = row.get("target_byte_count", row.get("byte_count"))
        actual_byte_count = target.stat().st_size if exists else None
        digest_matches = bool(expected_digest) and actual_digest == expected_digest
        line_count_matches = (
            isinstance(expected_line_count, int)
            and actual_line_count == expected_line_count
        )
        byte_count_matches = (
            isinstance(expected_byte_count, int)
            and actual_byte_count == expected_byte_count
        )
        source_import_class = str(row.get("source_import_class") or "")
        source_to_target_relation = str(row.get("source_to_target_relation") or "")
        body_in_receipt = row.get("body_in_receipt") is True
        required_anchors = _strings(row.get("required_anchors"))
        target_text = target.read_text(encoding="utf-8") if exists else ""
        missing_anchors = [
            anchor for anchor in required_anchors if anchor not in target_text
        ]

        if source_import_class not in SOURCE_MODULE_IMPORT_CLASSES:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_SOURCE_MODULE_ROW_IMPORT_CLASS_INVALID",
                    "Each source-module row must use a public-safe macro body import class.",
                    case_id="source_module_manifest_floor",
                    subject_id=material_id,
                    subject_kind="source_module",
                )
            )
        if source_to_target_relation not in SOURCE_MODULE_RELATIONS:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_SOURCE_MODULE_RELATION_INVALID",
                    "Each source-module row must declare exact-copy or path-normalized public-safe relation.",
                    case_id="source_module_manifest_floor",
                    subject_id=material_id,
                    subject_kind="source_module",
                )
            )
        if material_class not in SOURCE_MODULE_MATERIAL_CLASSES:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_SOURCE_MODULE_MATERIAL_CLASS_INVALID",
                    "Each source-module row must declare a public macro body material class.",
                    case_id="source_module_manifest_floor",
                    subject_id=material_id,
                    subject_kind="source_module",
                )
            )
        if body_in_receipt:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_SOURCE_MODULE_ROW_BODY_IN_RECEIPT_FORBIDDEN",
                    "Copied source-module bodies must not be embedded in receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=material_id,
                    subject_kind="source_module",
                )
            )
        if not exists:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_SOURCE_MODULE_TARGET_MISSING",
                    "Declared symbol-classifier source module target is missing.",
                    case_id="source_module_manifest_floor",
                    subject_id=material_id,
                    subject_kind="source_module",
                )
            )
        elif not digest_matches:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Copied symbol-classifier source module target digest differs from the manifest.",
                    case_id="source_module_manifest_floor",
                    subject_id=material_id,
                    subject_kind="source_module",
                )
            )
        elif not line_count_matches or not byte_count_matches:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_SOURCE_MODULE_SIZE_MISMATCH",
                    "Copied symbol-classifier source module target line or byte count differs from the manifest.",
                    case_id="source_module_manifest_floor",
                    subject_id=material_id,
                    subject_kind="source_module",
                )
            )
        elif missing_anchors:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_SOURCE_MODULE_REQUIRED_ANCHOR_MISSING",
                    "Copied symbol-classifier source module is missing required owner anchors.",
                    case_id="source_module_manifest_floor",
                    subject_id=material_id,
                    subject_kind="source_module",
                )
            )
        else:
            verified_ids.append(material_id)

        module_results.append(
            {
                "module_id": material_id,
                "source_ref": source_ref,
                "target_ref": _display(target, public_root=public_root),
                "material_class": material_class,
                "source_import_class": source_import_class,
                "body_copied": exists,
                "body_in_receipt": False,
                "expected_digest": f"sha256:{expected_digest}" if expected_digest else "",
                "source_digest": f"sha256:{row.get('source_sha256') or ''}"
                if row.get("source_sha256")
                else "",
                "actual_digest": f"sha256:{actual_digest}" if actual_digest else "",
                "digest_matches": digest_matches,
                "line_count": actual_line_count,
                "line_count_matches": line_count_matches,
                "byte_count": actual_byte_count,
                "byte_count_matches": byte_count_matches,
                "required_anchor_count": len(required_anchors),
                "missing_required_anchors": missing_anchors,
                "source_to_target_relation": source_to_target_relation,
            }
        )

    status = PASS if not findings and len(verified_ids) == len(SOURCE_MODULE_REFS) else "blocked"
    source_open_body_imports = {
        "status": status,
        "body_material_status": SOURCE_MODULE_BODY_MATERIAL_STATUS,
        "body_material_count": len(verified_ids),
        "body_material_ids": sorted(verified_ids),
        "material_classes": sorted(material_classes),
        "aggregate_floor_ref": (
            "examples/undeclared_library_prior_symbol_classifier/"
            "exported_symbol_classifier_bundle/"
            "bundle_manifest.json::source_open_body_imports"
        ),
        "source_manifest_refs": [SOURCE_MODULE_MANIFEST_REF],
        "body_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "proof_body_or_oracle_proof_text_exported": False,
            "provider_payload_exported": False,
            "lean_lake_execution_authorized": False,
            "formal_proof_authority": False,
            "theorem_correctness_authority": False,
            "runtime_correctness_claim": False,
            "release_authorized": False,
        },
    }
    return {
        "status": status,
        "source_modules_pass": status == PASS,
        "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
        "manifest_id": manifest.get("manifest_id"),
        "module_count": len(modules),
        "verified_module_count": len(verified_ids),
        "modules": module_results,
        "findings": findings,
        "observed_negative_cases": {},
        "source_open_body_imports": source_open_body_imports,
    }


def _qualified_refs(row: dict[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_qualified_refs` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    values: list[str] = []
    for key in (
        "proof_symbol_refs",
        "observed_symbol_refs",
        "library_priors_used",
        "undeclared_library_prior_symbols",
    ):
        values.extend(_strings(row.get(key)))
    return sorted(set(symbol for symbol in values if QUALIFIED_SYMBOL_RE.fullmatch(symbol)))


def _unqualified_refs(row: dict[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_unqualified_refs` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    values: list[str] = []
    for key in (
        "proof_symbol_refs",
        "observed_symbol_refs",
        "library_priors_used",
        "undeclared_library_prior_symbols",
    ):
        values.extend(_strings(row.get(key)))
    return sorted(
        set(
            symbol
            for symbol in values
            if symbol and not QUALIFIED_SYMBOL_RE.fullmatch(symbol)
        )
    )


def _problem_result_by_id(run_summary: object) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_problem_result_by_id` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    results: dict[str, dict[str, Any]] = {}
    for row in _rows(run_summary, "problem_results"):
        problem_id = str(row.get("problem_id") or "")
        if problem_id:
            results[problem_id] = row
    return results


def _symbols_for_premise_ids(
    premise_ids: list[str],
    premise_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_symbols_for_premise_ids` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return sorted(
        {
            str(premise_by_id[premise_id].get("theorem_or_def_name") or "")
            for premise_id in premise_ids
            if premise_id in premise_by_id
            and premise_by_id[premise_id].get("theorem_or_def_name")
        }
    )


def _source_observation_check(
    row: dict[str, Any],
    *,
    input_dir: Path | None,
    premise_by_id: dict[str, dict[str, Any]],
    source_payloads: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_observation_check` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    ref = row.get("source_observation_ref")
    if not isinstance(ref, dict):
        return {
            "source_observation_backed": False,
            "source_observation_status": "not_declared",
            "source_observation_ref": None,
            "source_observation_mismatches": [],
        }

    module_id = str(ref.get("module_id") or RUN_SUMMARY_SOURCE_MODULE_ID)
    problem_id = str(ref.get("problem_id") or row.get("problem_id") or "")
    allowed_field = str(
        ref.get("allowed_premise_ids_from") or "extra_retrieved_premise_ids"
    )
    source_payload = source_payloads.get(module_id)
    mismatches: list[dict[str, Any]] = []
    source_status = "pass"
    if input_dir is None or not isinstance(source_payload, dict):
        source_status = "blocked"
        mismatches.append(
            {
                "field": "source_module",
                "expected": module_id,
                "actual": "missing",
            }
        )
        result_row: dict[str, Any] = {}
        retrieval: dict[str, Any] = {}
    else:
        result_row = _problem_result_by_id(source_payload).get(problem_id, {})
        retrieval_payload = result_row.get("premise_retrieval", {})
        retrieval = retrieval_payload if isinstance(retrieval_payload, dict) else {}
        if not result_row:
            source_status = "blocked"
            mismatches.append(
                {
                    "field": "problem_id",
                    "expected": problem_id,
                    "actual": "missing",
                }
            )

    candidate_ids = _strings(retrieval.get("candidate_premise_ids_used"))
    expected_symbols = _symbols_for_premise_ids(candidate_ids, premise_by_id)
    expected_allowed_ids = _strings(retrieval.get(allowed_field))
    expected_candidate_sha = str(
        result_row.get("candidate_artifact_sha256")
        or result_row.get("final_candidate_artifact_sha256")
        or ""
    )
    expected_lean_status = str(
        result_row.get("lean_compile_status")
        or retrieval.get("lean_compile_status")
        or ""
    )

    comparisons = (
        ("proof_symbol_refs", expected_symbols, _strings(row.get("proof_symbol_refs"))),
        (
            "allowed_premise_ids",
            expected_allowed_ids,
            _strings(row.get("allowed_premise_ids")),
        ),
        (
            "candidate_artifact_sha256",
            [expected_candidate_sha],
            [str(row.get("candidate_artifact_sha256") or "")],
        ),
        ("lean_status", [expected_lean_status], [str(row.get("lean_status") or "")]),
    )
    for field, expected, actual in comparisons:
        if expected and sorted(expected) != sorted(actual):
            source_status = "blocked"
            mismatches.append(
                {
                    "field": field,
                    "expected": sorted(expected),
                    "actual": sorted(actual),
                }
            )

    return {
        "source_observation_backed": source_status == "pass",
        "source_observation_status": source_status,
        "source_observation_ref": {
            "module_id": module_id,
            "problem_id": problem_id,
            "allowed_premise_ids_from": allowed_field,
            "proof_symbol_refs_from": "premise_retrieval.candidate_premise_ids_used",
            "candidate_artifact_sha256_from": "candidate_artifact_sha256",
        },
        "source_observation_mismatches": mismatches,
    }


def _classify_row(
    row: dict[str, Any],
    *,
    premise_by_id: dict[str, dict[str, Any]],
    premise_by_symbol: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_classify_row` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    receipt_id = str(row.get("receipt_id") or row.get("case_id") or "symbol_observation")
    case_id = str(row.get("expected_negative_case_id") or receipt_id)
    subject_kind = "negative_case" if negative else "symbol_observation"

    if _has_forbidden_key(row, FORBIDDEN_PROOF_KEYS):
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_PROOF_BODY_FORBIDDEN",
            "Public symbol observations may carry hashes and extracted refs, not proof bodies.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )
    if _private_ref_present(row):
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_PRIVATE_SOURCE_REF_FORBIDDEN",
            "Public symbol observations may not expose private source refs.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )
    if row.get("claims_theorem_correctness") is True:
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_THEOREM_CORRECTNESS_OVERCLAIM",
            "A library-prior classifier is not theorem correctness authority.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )

    allowed_ids = _strings(row.get("allowed_premise_ids"))
    cited_unallowed_ids = _strings(row.get("cited_unallowed_premise_ids"))
    allowed_symbols = {
        str(premise_by_id[premise_id].get("theorem_or_def_name"))
        for premise_id in allowed_ids
        if premise_id in premise_by_id
    }
    cited_unallowed_symbols = {
        str(premise_by_id[premise_id].get("theorem_or_def_name"))
        for premise_id in cited_unallowed_ids
        if premise_id in premise_by_id
    }
    observed_symbols = _qualified_refs(row)
    known_symbols = [symbol for symbol in observed_symbols if symbol in premise_by_symbol]
    undeclared = sorted(
        symbol
        for symbol in known_symbols
        if symbol not in allowed_symbols and symbol not in cited_unallowed_symbols
    )
    unqualified = _unqualified_refs(row)

    computed_class = "NONE"
    computed_outcome = "accept_as_advisory"
    if cited_unallowed_ids:
        computed_class = PREMISE_BUDGET_CLASS
        computed_outcome = RETRY_OUTCOME
    elif undeclared:
        computed_class = UNDECLARED_CLASS
        computed_outcome = BRIDGE_OUTCOME

    asserted_class = str(row.get("classified_failure_class") or computed_class)
    asserted_outcome = str(row.get("review_outcome") or computed_outcome)
    if undeclared and (
        asserted_class != UNDECLARED_CLASS or asserted_outcome != BRIDGE_OUTCOME
    ):
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_UNDECLARED_LIBRARY_PRIOR_NOT_ESCALATED",
            "Undeclared known library symbols must classify as UNDECLARED_LIBRARY_PRIOR and bridge-escalate.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )
    if cited_unallowed_ids and (
        asserted_class == UNDECLARED_CLASS or asserted_outcome == BRIDGE_OUTCOME
    ):
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_PREMISE_BUDGET_PRECEDENCE",
            "cited_unallowed_premise_ids short-circuit the residual symbol classifier.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )
    if allowed_symbols.intersection(set(observed_symbols)) and asserted_class == UNDECLARED_CLASS:
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_ALLOWED_SYMBOL_FALSE_POSITIVE",
            "Symbols already admitted by allowed_premise_ids cannot be quarantined as undeclared library priors.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )
    if not negative and (
        asserted_class != computed_class or asserted_outcome != computed_outcome
    ):
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_ASSERTED_CLASSIFICATION_MISMATCH",
            "Public symbol-observation assertions must match the recomputed premise-index symbol classification.",
            case_id=ASSERTION_MISMATCH_CASE_ID,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )
    if unqualified and asserted_class == UNDECLARED_CLASS:
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_UNQUALIFIED_SYMBOL_OVERCLAIM",
            "Unqualified tokens cannot support the qualified library-prior class.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )

    return {
        "receipt_id": receipt_id,
        "expected_negative_case_id": case_id if negative else None,
        "observed_qualified_symbols": observed_symbols,
        "observed_known_symbols": known_symbols,
        "allowed_premise_ids": allowed_ids,
        "cited_unallowed_premise_ids": cited_unallowed_ids,
        "allowed_symbols": sorted(allowed_symbols),
        "cited_unallowed_symbols": sorted(cited_unallowed_symbols),
        "undeclared_library_prior_symbols": undeclared,
        "computed_failure_class": computed_class,
        "computed_review_outcome": computed_outcome,
        "asserted_failure_class": asserted_class,
        "asserted_review_outcome": asserted_outcome,
        "body_in_receipt": BODY_IN_RECEIPT,
        "body_material_status": BODY_MATERIAL_STATUS,
        "symbol_boundary_status": SYMBOL_BOUNDARY_STATUS,
    }


def validate_symbol_observations(
    payload: object,
    premise_index: object,
    negative_payloads: dict[str, object],
    input_dir: Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_symbol_observations` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    premise_by_id, premise_by_symbol = _premise_maps(premise_index)
    source_payloads = _source_module_payload_by_id(input_dir) if input_dir else {}
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    for row in _rows(payload, "symbol_observations"):
        source_check = _source_observation_check(
            row,
            input_dir=input_dir,
            premise_by_id=premise_by_id,
            source_payloads=source_payloads,
        )
        if source_check["source_observation_mismatches"]:
            _record(
                findings,
                observed,
                "SYMBOL_CLASSIFIER_SOURCE_OBSERVATION_DERIVATION_MISMATCH",
                "Source-backed symbol observations must match the copied public run-summary and premise-index rows.",
                case_id="source_observation_derivation_floor",
                subject_id=str(row.get("receipt_id") or "symbol_observation"),
                subject_kind="symbol_observation",
            )
        classified = _classify_row(
            row,
            premise_by_id=premise_by_id,
            premise_by_symbol=premise_by_symbol,
            findings=findings,
            observed=observed,
            negative=False,
        )
        classified.update(source_check)
        rows.append(classified)
    for payload in negative_payloads.values():
        negative_rows = _rows(payload, "symbol_observations")
        if isinstance(payload, dict) and not negative_rows:
            negative_rows = [payload]
        for row in negative_rows:
            _classify_row(
                row,
                premise_by_id=premise_by_id,
                premise_by_symbol=premise_by_symbol,
                findings=findings,
                observed=observed,
                negative=True,
            )

    source_derivation_findings = [
        row
        for row in findings
        if row.get("negative_case_id")
        in {"symbol_observation_floor", "source_observation_derivation_floor"}
    ]
    blocking_findings = [
        row
        for row in findings
        if row.get("negative_case_id")
        in {
            "symbol_observation_floor",
            "source_observation_derivation_floor",
            ASSERTION_MISMATCH_CASE_ID,
        }
    ]
    undeclared_rows = [
        row for row in rows if row["computed_failure_class"] == UNDECLARED_CLASS
    ]
    budget_rows = [
        row for row in rows if row["computed_failure_class"] == PREMISE_BUDGET_CLASS
    ]
    source_backed_rows = [row for row in rows if row["source_observation_backed"]]
    return {
        "status": PASS if rows and undeclared_rows and budget_rows and not blocking_findings else "blocked",
        "classification_count": len(rows),
        "source_backed_observation_count": len(source_backed_rows),
        "source_observation_derivation_status": PASS
        if not source_derivation_findings
        else "blocked",
        "undeclared_library_prior_count": len(undeclared_rows),
        "premise_budget_precedence_count": len(budget_rows),
        "bridge_escalation_count": sum(
            1 for row in rows if row["computed_review_outcome"] == BRIDGE_OUTCOME
        ),
        "retry_count": sum(
            1 for row in rows if row["computed_review_outcome"] == RETRY_OUTCOME
        ),
        "classification_rows": sorted(rows, key=lambda row: row["receipt_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
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
    - Teleology: Implements `_build_result` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan_targets = [
        *_input_paths(input_dir, include_negative=include_negative),
        *_source_module_scan_paths(input_dir),
    ]
    secret_scan = scan_paths(
        scan_targets,
        forbidden_classes=policy,
        display_root=public_root,
    )
    secret_scan["body_material_status"] = "secret_exclusion_scan_no_proof_or_provider_bodies"

    projection = validate_projection_protocol(payloads["projection_protocol"])
    premise_index = validate_premise_index(payloads["premise_index"])
    classifier_policy = validate_classifier_policy(payloads["classifier_policy"])
    observations = validate_symbol_observations(
        payloads["symbol_observations"],
        payloads["premise_index"],
        {
            name: payloads[name]
            for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
            if name in payloads
        },
        input_dir=input_dir,
    )
    source_modules = validate_source_module_manifest(
        input_dir,
        public_root=public_root,
        required=input_mode == "exported_symbol_classifier_bundle",
    )

    observed = _merge_observed(
        projection,
        premise_index,
        classifier_policy,
        observations,
        source_modules,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        projection,
        premise_index,
        classifier_policy,
        observations,
        source_modules,
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and premise_index["status"] == PASS
        and classifier_policy["status"] == PASS
        and observations["status"] == PASS
        and source_modules["source_modules_pass"]
        else "blocked"
    )
    return {
        "schema_version": "undeclared_library_prior_symbol_classifier_result_v1",
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
        "body_material_status": BODY_MATERIAL_STATUS,
        "symbol_boundary_status": SYMBOL_BOUNDARY_STATUS,
        "toolchain_boundary_status": TOOLCHAIN_BOUNDARY_STATUS,
        "body_in_receipt": BODY_IN_RECEIPT,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "receipt_anchor_refs": projection["receipt_anchor_refs"],
        "source_target_refs": projection["source_target_refs"],
        "source_digests": projection["source_digests"],
        "real_substrate_refs": projection["source_refs"],
        "source_modules_pass": source_modules["source_modules_pass"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_count": source_modules["module_count"],
        "verified_source_module_count": source_modules["verified_module_count"],
        "source_modules": source_modules["modules"],
        "source_open_body_imports": source_modules["source_open_body_imports"],
        "premise_count": premise_index["premise_count"],
        "namespace_count": premise_index["namespace_count"],
        "classification_count": observations["classification_count"],
        "source_backed_observation_count": observations[
            "source_backed_observation_count"
        ],
        "source_observation_derivation_status": observations[
            "source_observation_derivation_status"
        ],
        "undeclared_library_prior_count": observations["undeclared_library_prior_count"],
        "premise_budget_precedence_count": observations["premise_budget_precedence_count"],
        "bridge_escalation_count": observations["bridge_escalation_count"],
        "retry_count": observations["retry_count"],
        "qualified_symbol_regex": classifier_policy["qualified_symbol_regex"],
        "premises": premise_index["premises"],
        "classification_rows": observations["classification_rows"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_board_from_result` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "undeclared_library_prior_symbol_classifier_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "undeclared_library_prior_symbol_classifier_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "body_material_status": result["body_material_status"],
        "symbol_boundary_status": result["symbol_boundary_status"],
        "toolchain_boundary_status": result["toolchain_boundary_status"],
        "body_in_receipt": BODY_IN_RECEIPT,
        "mechanics": [
            {
                "mechanic_id": "closed_premise_boundary",
                "count": result["premise_count"],
                "authority": "sanctioned_library_prior_is_explicit_not_implicit",
            },
            {
                "mechanic_id": "undeclared_prior_quarantine",
                "count": result["undeclared_library_prior_count"],
                "authority": "undeclared_priors_quarantined_not_rejected",
            },
            {
                "mechanic_id": "premise_budget_precedence",
                "count": result["premise_budget_precedence_count"],
                "authority": "cited_unallowed_takes_precedence_over_symbol_regex",
            },
        ],
        "classification_rows": result["classification_rows"],
        "qualified_symbol_regex": result["qualified_symbol_regex"],
        "formal_proof_authority": False,
        "theorem_correctness_authority": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "real_substrate_refs": result["real_substrate_refs"],
        "receipt_anchor_refs": result["receipt_anchor_refs"],
        "source_target_refs": result["source_target_refs"],
        "source_digests": result["source_digests"],
        "source_modules_pass": result["source_modules_pass"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_module_count": result["source_module_count"],
        "verified_source_module_count": result["verified_source_module_count"],
        "source_open_body_imports": result["source_open_body_imports"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_write_receipts` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    board = _board_from_result(result)
    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    result_receipt = {
        **result,
        "schema_version": "undeclared_library_prior_symbol_classifier_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**board, "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "undeclared_library_prior_symbol_classifier_validation_receipt_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "premise_count": result["premise_count"],
        "classification_count": result["classification_count"],
        "undeclared_library_prior_count": result["undeclared_library_prior_count"],
        "premise_budget_precedence_count": result[
            "premise_budget_precedence_count"
        ],
        "bridge_escalation_count": result["bridge_escalation_count"],
        "retry_count": result["retry_count"],
        "formal_proof_authority": False,
        "theorem_correctness_authority": False,
        "body_material_status": result["body_material_status"],
        "symbol_boundary_status": result["symbol_boundary_status"],
        "toolchain_boundary_status": result["toolchain_boundary_status"],
        "body_in_receipt": BODY_IN_RECEIPT,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "real_substrate_refs": result["real_substrate_refs"],
        "receipt_anchor_refs": result["receipt_anchor_refs"],
        "source_target_refs": result["source_target_refs"],
        "source_digests": result["source_digests"],
        "source_modules_pass": result["source_modules_pass"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_module_count": result["source_module_count"],
        "verified_source_module_count": result["verified_source_module_count"],
        "source_modules": result["source_modules"],
        "source_open_body_imports": result["source_open_body_imports"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "undeclared_library_prior_symbol_classifier_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "body_material_status": result["body_material_status"],
        "symbol_boundary_status": result["symbol_boundary_status"],
        "toolchain_boundary_status": result["toolchain_boundary_status"],
        "body_in_receipt": BODY_IN_RECEIPT,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "real_substrate_refs": result["real_substrate_refs"],
        "source_digests": result["source_digests"],
        "source_modules_pass": result["source_modules_pass"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_module_count": result["source_module_count"],
        "verified_source_module_count": result["verified_source_module_count"],
        "source_open_body_imports": result["source_open_body_imports"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "symbol_classifier_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.undeclared_library_prior_symbol_classifier run",
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source = Path(input_dir)
    result = _build_result(
        source,
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_symbol_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.undeclared_library_prior_symbol_classifier "
        "run-symbol-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_symbol_bundle` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_symbol_classifier_bundle_receipt(source, out, command=command)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_symbol_classifier_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_symbol_classifier_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    secret_scan = result.get("secret_exclusion_scan")
    scan = secret_scan if isinstance(secret_scan, dict) else {}
    source_imports = result.get("source_open_body_imports")
    imports = source_imports if isinstance(source_imports, dict) else {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": freshness.get("basis_digest"),
            "freshness_input_count": freshness.get("input_count"),
            "freshness_missing_path_count": freshness.get("missing_path_count"),
        },
        "symbol_classifier": {
            "premise_count": result.get("premise_count"),
            "namespace_count": result.get("namespace_count"),
            "classification_count": result.get("classification_count"),
            "undeclared_library_prior_count": result.get(
                "undeclared_library_prior_count"
            ),
            "premise_budget_precedence_count": result.get(
                "premise_budget_precedence_count"
            ),
            "bridge_escalation_count": result.get("bridge_escalation_count"),
            "retry_count": result.get("retry_count"),
            "source_modules_pass": result.get("source_modules_pass"),
            "source_module_count": result.get("source_module_count"),
            "verified_source_module_count": result.get(
                "verified_source_module_count"
            ),
        },
        "source_body_floor": {
            "status": imports.get("status"),
            "body_material_count": imports.get("body_material_count"),
            "body_material_id_count": len(imports.get("body_material_ids") or []),
        },
        "validation": {
            "expected_negative_case_count": len(
                result.get("expected_negative_cases") or []
            ),
            "missing_negative_case_count": len(
                result.get("missing_negative_cases") or []
            ),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "secret_exclusion_blocking_hit_count": scan.get("blocking_hit_count"),
        },
        "body_floor": {
            "body_in_receipt": False,
            "secret_exclusion_scan_in_card": False,
            "authority_ceiling_in_card": False,
            "anti_claim_in_card": False,
            "source_refs_in_card": False,
            "real_substrate_refs_in_card": False,
            "receipt_anchor_refs_in_card": False,
            "source_target_refs_in_card": False,
            "source_digests_in_card": False,
            "source_modules_in_card": False,
            "source_open_body_imports_in_card": False,
            "premise_rows_in_card": False,
            "classification_rows_in_card": False,
            "symbol_classifier_board_in_card": False,
        },
        "authority_boundary": {
            "formal_proof_authority": False,
            "theorem_correctness_authority": False,
            "lean_lake_execution_authorized": False,
            "mathlib_absence_is_probe_result": True,
            "proof_bodies_allowed": False,
            "private_source_refs_allowed": False,
            "provider_calls_authorized": False,
            "premise_budget_retry_authority": False,
            "release_authorized": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `_parser` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="undeclared_library_prior_symbol_classifier")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-symbol-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.undeclared_library_prior_symbol_classifier` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        acceptance_suffix = (
            f" --acceptance-out {args.acceptance_out}" if args.acceptance_out else ""
        )
        command = (
            "python -m microcosm_core.organs."
            "undeclared_library_prior_symbol_classifier "
            f"run --input {args.input} --out {args.out}{acceptance_suffix}"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-symbol-bundle":
        command = (
            "python -m microcosm_core.organs."
            "undeclared_library_prior_symbol_classifier "
            f"run-symbol-bundle --input {args.input} --out {args.out}"
            f"{card_suffix}"
        )
        result = run_symbol_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    else:  # pragma: no cover
        raise ValueError(args.action)
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
