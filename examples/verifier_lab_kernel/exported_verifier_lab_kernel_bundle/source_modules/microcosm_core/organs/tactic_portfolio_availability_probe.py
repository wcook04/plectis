"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.tactic_portfolio_availability_probe` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, CARD_OMITTED_FULL_PAYLOAD_KEYS, SOURCE_PATTERN_IDS, SOURCE_REFS, REAL_SUBSTRATE_REFS, RECEIPT_ANCHOR_REFS, SOURCE_TARGET_REFS, SOURCE_DIGESTS, PUBLIC_SAFE_SOURCE_DIGESTS, SOURCE_BODY_REL_BY_SOURCE_REF, SOURCE_BODY_REL_PATHS, PROBE_SOURCE_REL_PATHS, PROBE_SOURCE_REF_BY_REL, PROBE_SOURCE_DIGESTS, BODY_MATERIAL_STATUS, TACTIC_AVAILABILITY_STATUS, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, environment variables.
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
from microcosm_core.receipts import (
    normalize_public_receipt_paths,
    utc_now,
    write_json_atomic,
)
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "tactic_portfolio_availability_probe"
FIXTURE_ID = "first_wave.tactic_portfolio_availability_probe"
VALIDATOR_ID = "validator.microcosm.organs.tactic_portfolio_availability_probe"

RESULT_NAME = "tactic_portfolio_availability_result.json"
BOARD_NAME = "tactic_portfolio_availability_board.json"
VALIDATION_RECEIPT_NAME = "tactic_portfolio_availability_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "tactic_portfolio_availability_probe_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_tactic_portfolio_availability_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "tactic_portfolio_availability_command_card_v1"

CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "anti_claim",
    "available_tactic_ids",
    "error_codes",
    "expected_negative_cases",
    "findings",
    "known_tactic_ids",
    "mathlib_dependent_tactic_ids",
    "observed_negative_cases",
    "probe_source_digest_refs",
    "real_substrate_refs",
    "receipt_anchor_refs",
    "receipt_paths",
    "secret_exclusion_scan",
    "source_artifact_imports",
    "source_body_digest_refs",
    "source_digests",
    "source_pattern_ids",
    "source_refs",
    "source_target_refs",
    "tactic_latency_profile",
    "unavailable_tactic_ids",
)

SOURCE_PATTERN_IDS = ["tactic_portfolio_availability_probe"]
SOURCE_REFS = [
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/portfolio_core_v0/tactic_portfolio_availability.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json",
]
REAL_SUBSTRATE_REFS = SOURCE_REFS
RECEIPT_ANCHOR_REFS = [
    "receipts/first_wave/target_shape_tactic_routing_gate/target_shape_tactic_routing_result.json",
    "receipts/first_wave/target_shape_tactic_routing_gate/target_shape_tactic_routing_board.json",
    "receipts/first_wave/target_shape_tactic_routing_gate/target_shape_tactic_routing_validation_receipt.json",
]
SOURCE_TARGET_REFS = [
    "fixtures/first_wave/tactic_portfolio_availability_probe/input/tactic_portfolio_probe.json",
    "fixtures/first_wave/tactic_portfolio_availability_probe/input/environment_probe.json",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/tactic_portfolio_probe.json",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/environment_probe.json",
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_result.json",
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_board.json",
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_validation_receipt.json",
    ACCEPTANCE_RECEIPT_REL,
    "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle_validation_result.json",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/portfolio_core_v0/tactic_portfolio_availability.json",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/aesop.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/decide.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/grind.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/native_decide.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/omega.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/rfl.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp_all.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/mathlib_probe.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/trace_state_probe.lean",
]
SOURCE_DIGESTS = {
    SOURCE_REFS[0]: "sha256:20fdef8a53401f2bb21483002730895ca0295d2170bf148e8c328c041d8524c3",
    SOURCE_REFS[1]: "sha256:405efadd8045057279a4481c05cdea8e1d99fceee253809526fb37675889d712",
    SOURCE_REFS[2]: "sha256:c413608118229bea32062ce9b8b5af393bcd5f63bbf1030983e98ffa6d07778d",
}
PUBLIC_SAFE_SOURCE_DIGESTS = {
    SOURCE_REFS[0]: "sha256:b49fff153a69f22a52181496206a038ceea587f43ad38e3531d7ff2f35ec976f",
    SOURCE_REFS[1]: "sha256:b474704255b8462996562478732e36c60bb4e2f33c64a9fb81cf48032d1fa970",
}
SOURCE_BODY_REL_BY_SOURCE_REF = {
    source_ref: f"source_artifacts/{source_ref}" for source_ref in SOURCE_REFS
}
SOURCE_BODY_REL_PATHS = tuple(SOURCE_BODY_REL_BY_SOURCE_REF.values())
PROBE_SOURCE_REL_PATHS = (
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/aesop.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/decide.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/grind.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/native_decide.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/omega.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/rfl.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp_all.lean",
    "source_artifacts/tactic_affordance_probe/mathlib_probe.lean",
    "source_artifacts/tactic_affordance_probe/trace_state_probe.lean",
)
PROBE_SOURCE_REF_BY_REL = {
    rel: (
        "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/"
        f"{rel.removeprefix('source_artifacts/')}"
    )
    for rel in PROBE_SOURCE_REL_PATHS
}
PROBE_SOURCE_DIGESTS = {
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/aesop.lean"
    ]: "sha256:e7580aa35a0a746a518c9b76d20a7df29a8c9898803ffe68a8e08ec92afa9923",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/decide.lean"
    ]: "sha256:0385b2379d3391686132c7795e906ba4642b527328839cb8fca55210b0088668",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/grind.lean"
    ]: "sha256:10458d90f04bfcd8673f949448de6ac9d0600eff750c85bd4e3cbc015eb3586a",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/native_decide.lean"
    ]: "sha256:0969b1ae27f3adc066cc42272d6cefc4d0083e8eec42b53e4d7d6db98e61610d",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/omega.lean"
    ]: "sha256:03567efe4235543feb46e7eb06eb23e61d65cc69b93c05364d55bedf1f9c0548",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/rfl.lean"
    ]: "sha256:2d2b1800deb875c660693bd87af0715752316132da8a747c13487577feddc696",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp.lean"
    ]: "sha256:9ab68dcc2905806aac19e8b4e149c2641dc575947a42d45c8eb31491e6478c67",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp_all.lean"
    ]: "sha256:c049906a2d9e9f4583eb5a1f2cd690992650e0a125124cd7e412f5fc7316af52",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/mathlib_probe.lean"
    ]: "sha256:8c020f6884cda37338cb5216ded61722a9993fcd6d69aee1db655885738abbd1",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/trace_state_probe.lean"
    ]: "sha256:5a89050bfd0866cbc28f7c64e6115ea94dd690aa40073509bb6c55b7b4f20cf5",
}
BODY_MATERIAL_STATUS = "copied_non_secret_macro_body_with_provenance"
TACTIC_AVAILABILITY_STATUS = "real_lean_std_tactic_affordance_probe_rows"
PROBE_SOURCE_BODY_STATUS = "copied_non_secret_lean_probe_source_bodies_with_digest_verification"
SOURCE_BODY_STATUS = "copied_non_secret_macro_run_json_bodies_with_digest_verification"
LATENCY_PROFILE_STATUS = (
    "copied_probe_duration_rows_environment_scoped_not_benchmark_authority"
)
BODY_IN_RECEIPT = False

INPUT_NAMES = (
    "tactic_portfolio_probe.json",
    "environment_probe.json",
    "availability_policy.json",
)
NEGATIVE_INPUT_NAMES = (
    "missing_compile_status.json",
    "mathlib_claim_without_probe.json",
    "unprobed_tactic_referenced.json",
    "available_tactic_missing_duration.json",
    "proof_body_leakage.json",
    "authority_overclaim.json",
)
NEGATIVE_INPUT_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)

EXPECTED_NEGATIVE_CASES = {
    "missing_compile_status": ["TACTIC_PORTFOLIO_MISSING_COMPILE_STATUS"],
    "mathlib_claim_without_probe": ["TACTIC_PORTFOLIO_MATHLIB_CLAIM_WITHOUT_PROBE"],
    "unprobed_tactic_referenced": ["TACTIC_PORTFOLIO_UNPROBED_TACTIC_REFERENCED"],
    "available_tactic_missing_duration": [
        "TACTIC_PORTFOLIO_AVAILABLE_DURATION_MISSING"
    ],
    "proof_body_leakage": ["TACTIC_PORTFOLIO_PROOF_BODY_FORBIDDEN"],
    "authority_overclaim": ["TACTIC_PORTFOLIO_AUTHORITY_OVERCLAIM"],
}

PASS_STATUSES = {"compile_pass", "available", "pass"}
FAIL_STATUSES = {"environment_fail", "compile_fail", "unavailable"}
FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "lean_source_body",
    "provider_output_body",
    "raw_provider_response",
)
OVERCLAIM_KEYS = (
    "benchmark_performance_claimed",
    "formal_proof_authority",
    "lean_lake_execution_authorized",
    "provider_calls_authorized",
    "release_authorized",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "real_tactic_affordance_probe_not_proof_authority",
    "availability_is_environment_scoped": True,
    "mathlib_absence_is_probe_result": True,
    "lean_lake_execution_authorized": False,
    "formal_proof_authority": False,
    "provider_calls_authorized": False,
    "benchmark_performance_authority": False,
    "latency_profile_is_environment_scoped": True,
    "latency_profile_not_benchmark_authority": True,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Tactic portfolio availability validates copied non-secret Lean/Std tactic "
    "affordance probe rows from the 2026-05-11 proof-state curriculum smoke run. "
    "The public organ does not rerun Lean/Lake, prove any goal, authorize "
    "unavailable tactics, emit proof/provider bodies, claim benchmark "
    "performance, or authorize release."
)


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_display` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_rows` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return []
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return (
        [input_dir / name for name in names]
        + _source_body_paths(input_dir)
        + _probe_source_paths(input_dir)
    )


def _receipt_freshness_basis(
    *,
    command: str,
    receipt_path: Path,
    input_paths: list[Path],
    input_mode: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_receipt_freshness_basis` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    dependency_mtimes: list[int] = []
    missing_input_count = 0
    for path in input_paths:
        try:
            dependency_mtimes.append(path.stat().st_mtime_ns)
        except OSError:
            missing_input_count += 1
    return {
        "schema_version": "tactic_portfolio_availability_fresh_receipt_basis_v1",
        "cache_policy": "same_command_and_receipt_newer_than_inputs",
        "command": command,
        "input_mode": input_mode,
        "tracked_input_count": len(input_paths),
        "missing_input_count": missing_input_count,
        "latest_input_mtime_ns": max(dependency_mtimes) if dependency_mtimes else 0,
        "receipt_mtime_ns": (
            receipt_path.stat().st_mtime_ns if receipt_path.is_file() else None
        ),
    }


def _fresh_availability_bundle_receipt(
    input_dir: Path,
    out_dir: Path,
    *,
    command: str,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Implements `_fresh_availability_bundle_receipt` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    receipt_path = out_dir / BUNDLE_RESULT_NAME
    if not receipt_path.is_file():
        return None
    try:
        payload = read_json_strict(receipt_path)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if (
        payload.get("schema_version")
        != "exported_tactic_portfolio_availability_bundle_validation_result_v1"
    ):
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("input_mode") != "exported_tactic_portfolio_availability_bundle":
        return None
    normalized_command = normalize_public_receipt_paths({"command": command}).get(
        "command"
    )
    if payload.get("command") not in {command, normalized_command}:
        return None
    input_paths = _input_paths(input_dir, include_negative=False)
    basis = _receipt_freshness_basis(
        command=command,
        receipt_path=receipt_path,
        input_paths=input_paths,
        input_mode="exported_tactic_portfolio_availability_bundle",
    )
    receipt_mtime = basis["receipt_mtime_ns"]
    if receipt_mtime is None or basis["missing_input_count"]:
        return None
    if basis["latest_input_mtime_ns"] > receipt_mtime:
        return None
    return {
        **payload,
        "cache_status": "fresh_exported_bundle_receipt_reused",
        "freshness_basis": basis,
    }


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return {Path(name).stem: read_json_strict(input_dir / name) for name in names}


def _walk_dicts(value: object) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_walk_dicts` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        rows.append(value)
        for child in value.values():
            rows.extend(_walk_dicts(child))
    elif isinstance(value, list):
        for child in value:
            rows.extend(_walk_dicts(child))
    return rows


def _forbidden_body_keys(row: dict[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_forbidden_body_keys` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return sorted(key for key in FORBIDDEN_BODY_KEYS if key in row)


def _probe_source_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_probe_source_paths` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [input_dir / rel for rel in PROBE_SOURCE_REL_PATHS]


def _source_body_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_body_paths` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [input_dir / rel for rel in SOURCE_BODY_REL_PATHS]


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _dict_payload(value: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_dict_payload` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return value if isinstance(value, dict) else {}


def _load_source_payloads(input_dir: Path) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_load_source_payloads` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payloads: dict[str, dict[str, Any]] = {}
    for source_ref in SOURCE_REFS:
        target = input_dir / SOURCE_BODY_REL_BY_SOURCE_REF[source_ref]
        try:
            payload = read_json_strict(target)
        except (OSError, ValueError):
            payload = {}
        payloads[source_ref] = _dict_payload(payload)
    return payloads


def _source_portfolio_payload(source_payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_portfolio_payload` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _dict_payload(source_payloads.get(SOURCE_REFS[1]))


def _source_probe_payload(source_payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_probe_payload` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _dict_payload(source_payloads.get(SOURCE_REFS[0]))


def _source_corpus_payload(source_payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_corpus_payload` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _dict_payload(source_payloads.get(SOURCE_REFS[2]))


def _source_probe_portfolio_payload(
    source_payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_probe_portfolio_payload` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _dict_payload(_source_probe_payload(source_payloads).get("portfolio_core_v0"))


def _source_portfolio_rows(source_payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_source_portfolio_rows` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _rows(_source_portfolio_payload(source_payloads), "rows")


def _source_probe_rows(source_payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_source_probe_rows` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _rows(_source_probe_portfolio_payload(source_payloads), "rows")


def _source_body_imports(
    input_dir: Path,
    *,
    public_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    [ACTION]
    - Teleology: Implements `_source_body_imports` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    imports: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for source_ref in SOURCE_REFS:
        expected = SOURCE_DIGESTS[source_ref]
        rel = SOURCE_BODY_REL_BY_SOURCE_REF[source_ref]
        target = input_dir / rel
        target_ref = _display(target, public_root=public_root)
        if not target.is_file():
            imports.append(
                {
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "sha256": expected,
                    "actual_sha256": None,
                    "body_copied": False,
                    "copy_policy": "exact_public_safe_macro_run_json_body",
                    "body_material_status": "missing_public_macro_run_json_body",
                }
            )
            findings.append(
                _finding(
                    "TACTIC_PORTFOLIO_SOURCE_BODY_MISSING",
                    "A copied tactic portfolio macro JSON source body is missing.",
                    case_id="source_body_artifacts",
                    subject_id=target_ref,
                    subject_kind="source_artifact",
                )
            )
            continue
        actual = _sha256(target)
        public_safe_expected = PUBLIC_SAFE_SOURCE_DIGESTS.get(source_ref)
        source_digest_matches = actual == expected
        public_safe_digest_matches = actual == public_safe_expected
        body_copied = source_digest_matches or public_safe_digest_matches
        relation = (
            "exact_copy"
            if source_digest_matches
            else "verified_public_safe_private_path_rewrite"
            if public_safe_digest_matches
            else "digest_mismatch"
        )
        imports.append(
            {
                "source_ref": source_ref,
                "target_ref": target_ref,
                "sha256": expected,
                "source_sha256": expected,
                "public_safe_sha256": public_safe_expected,
                "actual_sha256": actual,
                "body_copied": body_copied,
                "digest_matches": body_copied,
                "source_digest_matches": source_digest_matches,
                "public_safe_digest_matches": public_safe_digest_matches,
                "source_to_target_relation": relation,
                "copy_policy": (
                    "exact_or_verified_public_safe_private_path_rewrite_macro_run_json_body"
                ),
                "body_material_status": SOURCE_BODY_STATUS,
            }
        )
        if not body_copied:
            findings.append(
                _finding(
                    "TACTIC_PORTFOLIO_SOURCE_BODY_DIGEST_MISMATCH",
                    "A copied tactic portfolio macro JSON source body digest does not match its macro source.",
                    case_id="source_body_artifacts",
                    subject_id=target_ref,
                    subject_kind="source_artifact",
                )
            )
    return imports, findings


def _probe_source_imports(
    input_dir: Path,
    *,
    public_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    [ACTION]
    - Teleology: Implements `_probe_source_imports` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    imports: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for rel in PROBE_SOURCE_REL_PATHS:
        source_ref = PROBE_SOURCE_REF_BY_REL[rel]
        expected = PROBE_SOURCE_DIGESTS[source_ref]
        target = input_dir / rel
        target_ref = _display(target, public_root=public_root)
        if not target.is_file():
            imports.append(
                {
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "sha256": expected,
                    "actual_sha256": None,
                    "body_copied": False,
                    "copy_policy": "exact_public_safe_lean_probe_source",
                    "body_material_status": "missing_public_probe_source_body",
                }
            )
            findings.append(
                _finding(
                    "TACTIC_PORTFOLIO_SOURCE_ARTIFACT_MISSING",
                    "A copied Lean tactic probe source artifact is missing.",
                    case_id="probe_source_artifacts",
                    subject_id=target_ref,
                    subject_kind="source_artifact",
                )
            )
            continue
        actual = _sha256(target)
        body_copied = actual == expected
        imports.append(
            {
                "source_ref": source_ref,
                "target_ref": target_ref,
                "sha256": expected,
                "actual_sha256": actual,
                "body_copied": body_copied,
                "copy_policy": "exact_public_safe_lean_probe_source",
                "body_material_status": PROBE_SOURCE_BODY_STATUS,
            }
        )
        if not body_copied:
            findings.append(
                _finding(
                    "TACTIC_PORTFOLIO_SOURCE_ARTIFACT_DIGEST_MISMATCH",
                    "A copied Lean tactic probe source artifact digest does not match its macro source.",
                    case_id="probe_source_artifacts",
                    subject_id=target_ref,
                    subject_kind="source_artifact",
                )
            )
    return imports, findings


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
    - Teleology: Implements `_finding` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_record` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
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


def _tactic_rows(payload: object) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_tactic_rows` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "tactics")
    if rows:
        return rows
    return _rows(payload, "rows")


def _status(row: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_status` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = row.get("compile_status") or row.get("availability_status") or row.get("status")
    return str(value or "")


def _duration_ms(row: dict[str, Any]) -> int | None:
    """
    [ACTION]
    - Teleology: Implements `_duration_ms` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = row.get("duration_ms")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value.is_integer():
        return int(value) if value >= 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _latency_band(duration_ms: int) -> str:
    """
    [ACTION]
    - Teleology: Implements `_latency_band` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if duration_ms <= 2500:
        return "fast"
    if duration_ms <= 5000:
        return "moderate"
    return "slow"


def _median_duration(values: list[int]) -> int | float | None:
    """
    [ACTION]
    - Teleology: Implements `_median_duration` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not values:
        return None
    midpoint = len(values) // 2
    ordered = sorted(values)
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _normalize_source_compile_status(row: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_normalize_source_compile_status` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(row.get("compile_status") or "").strip().upper()


def _source_row_view(row: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_row_view` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "tactic_id": str(row.get("tactic_id") or ""),
        "compile_status": _normalize_source_compile_status(row),
        "available": row.get("available") is True,
        "duration_ms": _duration_ms(row),
        "error_class": str(row.get("error_class") or ""),
    }


def _source_row_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_source_row_index` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        view["tactic_id"]: view
        for row in rows
        if (view := _source_row_view(row))["tactic_id"]
    }


def _projection_row_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_projection_row_index` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        tactic_id = str(row.get("tactic_id") or "")
        if tactic_id:
            index[tactic_id] = row
    return index


def _derived_public_status_from_source(
    source_row: dict[str, Any],
    *,
    requires_mathlib: bool,
    mathlib_available: bool,
) -> str:
    """
    [ACTION]
    - Teleology: Implements `_derived_public_status_from_source` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    status = source_row["compile_status"]
    if status == "PASS":
        return "compile_pass"
    if status == "FAIL":
        return "environment_fail" if requires_mathlib and not mathlib_available else "compile_fail"
    return status.lower()


def _failure_classifier_from_source(
    source_row: dict[str, Any],
    *,
    public_status: str,
    requires_mathlib: bool,
    mathlib_available: bool,
) -> str | None:
    """
    [ACTION]
    - Teleology: Implements `_failure_classifier_from_source` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if public_status not in FAIL_STATUSES:
        return None
    if requires_mathlib and not mathlib_available:
        return "MATHLIB_IMPORT_MISSING"
    return source_row["error_class"] or public_status


def _authoritative_environment_state(
    source_payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_authoritative_environment_state` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    probe_payload = _source_probe_payload(source_payloads)
    corpus_payload = _source_corpus_payload(source_payloads)
    mathlib = _dict_payload(probe_payload.get("mathlib"))
    probe_available = mathlib.get("available") is True
    lean_status = str(mathlib.get("lean_status") or "").strip().upper()
    corpus_mathlib_available = (
        corpus_payload.get("mathlib_lake_project_import_available") is True
    )
    return {
        "mathlib_probe_status": (
            "compile_pass" if probe_available and lean_status == "PASS" else "environment_fail"
        ),
        "mathlib_lake_project_import_available": probe_available or corpus_mathlib_available,
        "probe_available": probe_available,
        "probe_ref": str(mathlib.get("probe_path") or ""),
    }


def _availability_rows_from_source(
    source_rows: list[dict[str, Any]],
    *,
    projection_rows: list[dict[str, Any]],
    mathlib_available: bool,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_availability_rows_from_source` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    projection_index = _projection_row_index(projection_rows)
    availability_rows: list[dict[str, Any]] = []
    for tactic_id, source_row in sorted(_source_row_index(source_rows).items()):
        projection_row = projection_index.get(tactic_id, {})
        requires_mathlib = projection_row.get("requires_mathlib") is True
        public_status = _derived_public_status_from_source(
            source_row,
            requires_mathlib=requires_mathlib,
            mathlib_available=mathlib_available,
        )
        failure_classifier = _failure_classifier_from_source(
            source_row,
            public_status=public_status,
            requires_mathlib=requires_mathlib,
            mathlib_available=mathlib_available,
        )
        availability_rows.append(
            {
                "tactic_id": tactic_id,
                "compile_status": public_status,
                "source_compile_status": source_row["compile_status"],
                "source_error_class": source_row["error_class"],
                "duration_ms": source_row["duration_ms"],
                "requires_mathlib": requires_mathlib,
                "failure_classifier": failure_classifier,
                "source_probe_ref": str(
                    projection_row.get("source_probe_ref") or source_row.get("probe_path") or ""
                ),
            }
        )
    return availability_rows


def _source_artifact_findings(
    source_payloads: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_source_artifact_findings` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    portfolio_rows = _source_row_index(_source_portfolio_rows(source_payloads))
    probe_rows = _source_row_index(_source_probe_rows(source_payloads))
    for tactic_id in sorted(set(portfolio_rows) | set(probe_rows)):
        portfolio_row = portfolio_rows.get(tactic_id)
        probe_row = probe_rows.get(tactic_id)
        if portfolio_row is None or probe_row is None:
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_SOURCE_ARTIFACT_CONTRADICTION",
                "Copied source artifacts must expose the same tactic ids across the aggregate probe and portfolio slice.",
                case_id="source_artifacts",
                subject_id=tactic_id,
                subject_kind="tactic_id",
            )
            continue
        for field in ("compile_status", "available", "duration_ms", "error_class"):
            if portfolio_row[field] != probe_row[field]:
                _record(
                    findings,
                    observed,
                    "TACTIC_PORTFOLIO_SOURCE_ARTIFACT_CONTRADICTION",
                    "Copied source artifacts disagree on tactic availability evidence.",
                    case_id="source_artifacts",
                    subject_id=tactic_id,
                    subject_kind="tactic_id",
                )
                break
        if portfolio_row["compile_status"] == "PASS" and portfolio_row["available"] is not True:
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_SOURCE_ARTIFACT_CONTRADICTION",
                "A copied source row cannot report PASS while marking the tactic unavailable.",
                case_id="source_artifacts",
                subject_id=tactic_id,
                subject_kind="tactic_id",
            )
        if portfolio_row["compile_status"] == "FAIL" and portfolio_row["available"] is not False:
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_SOURCE_ARTIFACT_CONTRADICTION",
                "A copied source row cannot report FAIL while marking the tactic available.",
                case_id="source_artifacts",
                subject_id=tactic_id,
                subject_kind="tactic_id",
            )
    portfolio_payload = _source_portfolio_payload(source_payloads)
    available_from_rows = sorted(
        tactic_id for tactic_id, row in portfolio_rows.items() if row["available"] is True
    )
    unavailable_from_rows = sorted(
        tactic_id for tactic_id, row in portfolio_rows.items() if row["available"] is False
    )
    available_list = portfolio_payload.get("available_tactic_ids")
    normalized_available_list = (
        sorted(str(item) for item in available_list)
        if isinstance(available_list, list)
        else []
    )
    if normalized_available_list != available_from_rows:
        _record(
            findings,
            observed,
            "TACTIC_PORTFOLIO_SOURCE_ARTIFACT_CONTRADICTION",
            "The copied source portfolio available_tactic_ids list must match the copied source rows.",
            case_id="source_artifacts",
            subject_id="available_tactic_ids",
            subject_kind="source_artifact",
        )
    unavailable_list = portfolio_payload.get("unavailable_tactic_ids")
    normalized_unavailable_list = (
        sorted(str(item) for item in unavailable_list)
        if isinstance(unavailable_list, list)
        else []
    )
    if normalized_unavailable_list != unavailable_from_rows:
        _record(
            findings,
            observed,
            "TACTIC_PORTFOLIO_SOURCE_ARTIFACT_CONTRADICTION",
            "The copied source portfolio unavailable_tactic_ids list must match the copied source rows.",
            case_id="source_artifacts",
            subject_id="unavailable_tactic_ids",
            subject_kind="source_artifact",
        )
    return findings


def _public_projection_findings(
    projection_rows: list[dict[str, Any]],
    *,
    source_rows: list[dict[str, Any]],
    mathlib_available: bool,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_public_projection_findings` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    projection_index = _projection_row_index(projection_rows)
    source_index = _source_row_index(source_rows)
    for tactic_id in sorted(set(source_index) | set(projection_index)):
        source_row = source_index.get(tactic_id)
        projection_row = projection_index.get(tactic_id)
        if source_row is None or projection_row is None:
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION",
                "The public tactic portfolio projection must expose the same tactic ids as the copied source artifact rows.",
                case_id="public_projection",
                subject_id=tactic_id,
                subject_kind="tactic_id",
            )
            continue
        requires_mathlib = projection_row.get("requires_mathlib") is True
        expected_public_status = _derived_public_status_from_source(
            source_row,
            requires_mathlib=requires_mathlib,
            mathlib_available=mathlib_available,
        )
        if _status(projection_row) != expected_public_status:
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION",
                "The public tactic portfolio projection must preserve the copied source row compile result.",
                case_id="public_projection",
                subject_id=tactic_id,
                subject_kind="tactic_id",
            )
        if str(projection_row.get("source_compile_status") or "").strip().upper() != source_row["compile_status"]:
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION",
                "The public tactic portfolio projection must preserve the copied source compile status.",
                case_id="public_projection",
                subject_id=tactic_id,
                subject_kind="tactic_id",
            )
        if str(projection_row.get("source_error_class") or "") != source_row["error_class"]:
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION",
                "The public tactic portfolio projection must preserve the copied source error class.",
                case_id="public_projection",
                subject_id=tactic_id,
                subject_kind="tactic_id",
            )
        if _duration_ms(projection_row) != source_row["duration_ms"]:
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION",
                "The public tactic portfolio projection must preserve the copied source duration.",
                case_id="public_projection",
                subject_id=tactic_id,
                subject_kind="tactic_id",
            )
    return findings


def _public_projection_body_findings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_public_projection_body_findings` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        forbidden = _forbidden_body_keys(row)
        if forbidden:
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_PROOF_BODY_FORBIDDEN",
                "Availability fixtures may carry tactic metadata, not proof, Lean, or provider bodies.",
                case_id="positive_portfolio",
                subject_id=str(row.get("tactic_id") or "tactic"),
                subject_kind="tactic_id",
            )
    return findings


def _portfolio_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_portfolio_summary` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    known: list[str] = []
    available: list[str] = []
    unavailable: list[str] = []
    mathlib_dependent: list[str] = []
    status_counts: Counter[str] = Counter()
    unavailable_reason_counts: Counter[str] = Counter()
    missing_compile_status: list[str] = []
    unknown_status: list[str] = []
    latency_missing: list[str] = []
    latency_rows: list[dict[str, Any]] = []
    for row in rows:
        tactic_id = str(row.get("tactic_id") or "")
        if not tactic_id:
            continue
        known.append(tactic_id)
        status = _status(row)
        if not status:
            missing_compile_status.append(tactic_id)
            status = "missing"
        status_counts[status] += 1
        if row.get("requires_mathlib") is True:
            mathlib_dependent.append(tactic_id)
        if status in PASS_STATUSES:
            available.append(tactic_id)
            duration = _duration_ms(row)
            if duration is None:
                latency_missing.append(tactic_id)
            else:
                latency_rows.append(
                    {
                        "tactic_id": tactic_id,
                        "duration_ms": duration,
                        "latency_band": _latency_band(duration),
                        "compile_status": status,
                        "requires_mathlib": row.get("requires_mathlib") is True,
                        "source_probe_ref": str(row.get("source_probe_ref") or ""),
                    }
                )
        elif status in FAIL_STATUSES:
            unavailable.append(tactic_id)
            reason = (
                row.get("failure_classifier")
                or row.get("source_error_class")
                or status
            )
            unavailable_reason_counts[str(reason)] += 1
        else:
            unknown_status.append(tactic_id)
    latency_rows = sorted(
        latency_rows,
        key=lambda item: (item["duration_ms"], item["tactic_id"]),
    )
    latency_band_counts = Counter(
        str(row["latency_band"]) for row in latency_rows
    )
    durations = [int(row["duration_ms"]) for row in latency_rows]
    return {
        "tactic_count": len(known),
        "known_tactic_ids": sorted(known),
        "available_tactic_ids": sorted(available),
        "unavailable_tactic_ids": sorted(unavailable),
        "mathlib_dependent_tactic_ids": sorted(mathlib_dependent),
        "compile_status_counts": dict(sorted(status_counts.items())),
        "unavailable_reason_counts": dict(sorted(unavailable_reason_counts.items())),
        "missing_compile_status_tactic_ids": sorted(missing_compile_status),
        "unknown_status_tactic_ids": sorted(unknown_status),
        "latency_missing_tactic_ids": sorted(latency_missing),
        "tactic_latency_profile": latency_rows,
        "latency_profile_available_tactic_count": len(latency_rows),
        "latency_band_counts": dict(sorted(latency_band_counts.items())),
        "fastest_available_tactic_ids": [
            str(row["tactic_id"]) for row in latency_rows[:3]
        ],
        "slowest_available_tactic_ids": [
            str(row["tactic_id"]) for row in reversed(latency_rows[-3:])
        ],
        "available_tactic_duration_ms_min": min(durations) if durations else None,
        "available_tactic_duration_ms_max": max(durations) if durations else None,
        "available_tactic_duration_ms_median": _median_duration(durations),
    }


def _positive_findings(
    *,
    rows: list[dict[str, Any]],
    environment_probe: dict[str, Any],
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_positive_findings` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for tactic_id in summary["missing_compile_status_tactic_ids"]:
        _record(
            findings,
            observed,
            "TACTIC_PORTFOLIO_MISSING_COMPILE_STATUS",
            "Every tactic row must report a scoped compile/environment status.",
            case_id="positive_portfolio",
            subject_id=tactic_id,
            subject_kind="tactic_id",
        )
    for tactic_id in summary["unknown_status_tactic_ids"]:
        _record(
            findings,
            observed,
            "TACTIC_PORTFOLIO_UNKNOWN_COMPILE_STATUS",
            "Tactic compile status must be a declared pass or fail status.",
            case_id="positive_portfolio",
            subject_id=tactic_id,
            subject_kind="tactic_id",
        )
    for tactic_id in summary["latency_missing_tactic_ids"]:
        _record(
            findings,
            observed,
            "TACTIC_PORTFOLIO_AVAILABLE_DURATION_MISSING",
            "Available tactic rows must preserve their copied probe duration for bounded routing evidence.",
            case_id="positive_portfolio",
            subject_id=tactic_id,
            subject_kind="tactic_id",
        )
    mathlib_available = environment_probe.get("mathlib_lake_project_import_available")
    for row in rows:
        tactic_id = str(row.get("tactic_id") or "tactic")
        if (
            row.get("requires_mathlib") is True
            and _status(row) in PASS_STATUSES
            and mathlib_available is not True
        ):
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_MATHLIB_CLAIM_WITHOUT_PROBE",
                "Mathlib-dependent tactics cannot be marked available unless the Mathlib import probe passed.",
                case_id="positive_portfolio",
                subject_id=tactic_id,
                subject_kind="tactic_id",
            )
    return findings


def _environment_probe_findings(
    environment_probe: dict[str, Any],
    *,
    authoritative_environment: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_environment_probe_findings` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    mathlib_status = str(environment_probe.get("mathlib_probe_status") or "")
    mathlib_available = environment_probe.get("mathlib_lake_project_import_available")
    contradiction = (
        (mathlib_available is True and mathlib_status in FAIL_STATUSES)
        or (mathlib_available is False and mathlib_status in PASS_STATUSES)
    )
    if contradiction:
        _record(
            findings,
            observed,
            "TACTIC_PORTFOLIO_ENVIRONMENT_PROBE_CONTRADICTION",
            "Mathlib availability must agree with the copied environment probe status.",
            case_id="positive_environment_probe",
            subject_id="mathlib_lake_project_import_available",
            subject_kind="environment_probe",
        )
    if mathlib_status != authoritative_environment["mathlib_probe_status"]:
        _record(
            findings,
            observed,
            "TACTIC_PORTFOLIO_ENVIRONMENT_SOURCE_CONTRADICTION",
            "The public environment projection must preserve the copied source Mathlib probe status.",
            case_id="positive_environment_probe",
            subject_id="mathlib_probe_status",
            subject_kind="environment_probe",
        )
    if bool(mathlib_available) != authoritative_environment["mathlib_lake_project_import_available"]:
        _record(
            findings,
            observed,
            "TACTIC_PORTFOLIO_ENVIRONMENT_SOURCE_CONTRADICTION",
            "The public environment projection must preserve the copied source Mathlib availability result.",
            case_id="positive_environment_probe",
            subject_id="mathlib_lake_project_import_available",
            subject_kind="environment_probe",
        )
    return findings


def _negative_findings(payloads: dict[str, Any], *, known: set[str]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_negative_findings` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for stem in NEGATIVE_INPUT_STEMS:
        payload = payloads.get(stem)
        if not isinstance(payload, dict):
            continue
        case_id = str(payload.get("expected_negative_case_id") or stem)
        if stem == "missing_compile_status":
            for row in _tactic_rows(payload) or _walk_dicts(payload):
                tactic_id = str(row.get("tactic_id") or "tactic")
                if row.get("compile_status") in {None, ""}:
                    _record(
                        findings,
                        observed,
                        "TACTIC_PORTFOLIO_MISSING_COMPILE_STATUS",
                        "A tactic row omitted compile_status.",
                        case_id=case_id,
                        subject_id=tactic_id,
                        subject_kind="tactic_id",
                    )
        elif stem == "mathlib_claim_without_probe":
            mathlib_available = payload.get("mathlib_lake_project_import_available")
            for row in _tactic_rows(payload):
                tactic_id = str(row.get("tactic_id") or "tactic")
                if (
                    row.get("requires_mathlib") is True
                    and _status(row) in PASS_STATUSES
                    and mathlib_available is not True
                ):
                    _record(
                        findings,
                        observed,
                        "TACTIC_PORTFOLIO_MATHLIB_CLAIM_WITHOUT_PROBE",
                        "Mathlib-dependent tactic availability was claimed without a passing Mathlib probe.",
                        case_id=case_id,
                        subject_id=tactic_id,
                        subject_kind="tactic_id",
                    )
        elif stem == "unprobed_tactic_referenced":
            for row in _rows(payload, "consumer_requests") or _walk_dicts(payload):
                tactic_id = str(row.get("tactic_id") or "")
                if tactic_id and tactic_id not in known:
                    _record(
                        findings,
                        observed,
                        "TACTIC_PORTFOLIO_UNPROBED_TACTIC_REFERENCED",
                        "Consumers may only reference tactics present in the declared portfolio probe.",
                        case_id=case_id,
                        subject_id=tactic_id,
                        subject_kind="tactic_id",
                    )
        elif stem == "available_tactic_missing_duration":
            for row in _tactic_rows(payload) or _walk_dicts(payload):
                tactic_id = str(row.get("tactic_id") or "tactic")
                if _status(row) in PASS_STATUSES and _duration_ms(row) is None:
                    _record(
                        findings,
                        observed,
                        "TACTIC_PORTFOLIO_AVAILABLE_DURATION_MISSING",
                        "Available tactic rows must carry a copied probe duration.",
                        case_id=case_id,
                        subject_id=tactic_id,
                        subject_kind="tactic_id",
                    )
        elif stem == "proof_body_leakage":
            for row in _walk_dicts(payload):
                forbidden = _forbidden_body_keys(row)
                if forbidden:
                    _record(
                        findings,
                        observed,
                        "TACTIC_PORTFOLIO_PROOF_BODY_FORBIDDEN",
                        "Availability probe fixtures cannot carry proof, Lean, or provider bodies.",
                        case_id=case_id,
                        subject_id=str(row.get("tactic_id") or row.get("case_id") or "payload"),
                        subject_kind="payload",
                    )
        elif stem == "authority_overclaim":
            fields = [field for field in OVERCLAIM_KEYS if payload.get(field) is True]
            if fields:
                _record(
                    findings,
                    observed,
                    "TACTIC_PORTFOLIO_AUTHORITY_OVERCLAIM",
                    "Tactic availability cannot authorize proof authority, provider calls, benchmarks, or release.",
                    case_id=case_id,
                    subject_id=",".join(sorted(fields)),
                    subject_kind="authority_ceiling",
                )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _build_board(*, result: dict[str, Any], secret_scan: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_board` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    return {
        "schema_version": "tactic_portfolio_availability_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_contract": {
            "availability_probe_scoped_to_environment": True,
            "mathlib_absence_surfaces_as_environment_fail": True,
            "unprobed_tactics_rejected": True,
            "private_theorem_proof_bodies_excluded": True,
            "public_lean_probe_source_bodies_allowed": True,
            "lean_lake_not_run_by_public_organ": True,
            "macro_run_json_bodies_copied": True,
            "macro_run_json_bodies_digest_verified": result[
                "source_body_artifact_count"
            ]
            == result["copied_source_body_artifact_count"],
            "lean_probe_source_bodies_copied": True,
            "lean_probe_source_bodies_digest_verified": result[
                "source_artifact_count"
            ]
            == result["copied_source_artifact_count"],
            "body_in_receipt": BODY_IN_RECEIPT,
            "body_material_status": BODY_MATERIAL_STATUS,
            "probe_source_body_status": PROBE_SOURCE_BODY_STATUS,
        },
        "portfolio_projection": {
            "portfolio_id": result["portfolio_id"],
            "environment_id": result["environment_id"],
            "tactic_count": result["tactic_count"],
            "available_tactic_ids": result["available_tactic_ids"],
            "unavailable_tactic_ids": result["unavailable_tactic_ids"],
            "mathlib_dependent_tactic_ids": result["mathlib_dependent_tactic_ids"],
            "compile_status_counts": result["compile_status_counts"],
            "mathlib_probe_status": result["mathlib_probe_status"],
            "mathlib_lake_project_import_available": result[
                "mathlib_lake_project_import_available"
            ],
            "latency_profile_status": result["latency_profile_status"],
            "latency_band_counts": result["latency_band_counts"],
            "fastest_available_tactic_ids": result[
                "fastest_available_tactic_ids"
            ],
            "slowest_available_tactic_ids": result[
                "slowest_available_tactic_ids"
            ],
            "available_tactic_duration_ms_median": result[
                "available_tactic_duration_ms_median"
            ],
            "body_in_receipt": BODY_IN_RECEIPT,
            "tactic_availability_status": TACTIC_AVAILABILITY_STATUS,
        },
        "secret_exclusion_scan": secret_scan,
        "body_material_status": BODY_MATERIAL_STATUS,
        "tactic_availability_status": TACTIC_AVAILABILITY_STATUS,
        "real_substrate_refs": REAL_SUBSTRATE_REFS,
        "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
        "source_target_refs": SOURCE_TARGET_REFS,
        "source_digests": SOURCE_DIGESTS,
        "source_body_digest_refs": SOURCE_DIGESTS,
        "probe_source_digest_refs": PROBE_SOURCE_DIGESTS,
        "source_artifact_imports": result["source_artifact_imports"],
        "source_artifact_count": result["source_artifact_count"],
        "copied_source_artifact_count": result["copied_source_artifact_count"],
        "source_body_artifact_count": result["source_body_artifact_count"],
        "copied_source_body_artifact_count": result[
            "copied_source_body_artifact_count"
        ],
        "latency_profile_status": result["latency_profile_status"],
        "latency_profile_available_tactic_count": result[
            "latency_profile_available_tactic_count"
        ],
        "latency_band_counts": result["latency_band_counts"],
        "tactic_latency_profile": result["tactic_latency_profile"],
        "latency_missing_tactic_ids": result["latency_missing_tactic_ids"],
        "fastest_available_tactic_ids": result["fastest_available_tactic_ids"],
        "slowest_available_tactic_ids": result["slowest_available_tactic_ids"],
        "available_tactic_duration_ms_min": result[
            "available_tactic_duration_ms_min"
        ],
        "available_tactic_duration_ms_max": result[
            "available_tactic_duration_ms_max"
        ],
        "available_tactic_duration_ms_median": result[
            "available_tactic_duration_ms_median"
        ],
        "probe_source_body_status": PROBE_SOURCE_BODY_STATUS,
        "source_body_status": SOURCE_BODY_STATUS,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": BODY_IN_RECEIPT,
    }


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_common_receipt` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
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
        "tactic_availability_status",
        "body_in_receipt",
        "real_substrate_refs",
        "receipt_anchor_refs",
        "source_target_refs",
        "source_digests",
        "source_body_digest_refs",
        "probe_source_digest_refs",
        "source_artifact_imports",
        "source_artifact_count",
        "copied_source_artifact_count",
        "source_body_artifact_count",
        "copied_source_body_artifact_count",
        "probe_source_body_status",
        "source_body_status",
        "authority_ceiling",
        "anti_claim",
        "portfolio_id",
        "environment_id",
        "tactic_count",
        "available_tactic_ids",
        "unavailable_tactic_ids",
        "mathlib_dependent_tactic_ids",
        "compile_status_counts",
        "unavailable_reason_counts",
        "latency_profile_status",
        "latency_profile_available_tactic_count",
        "latency_band_counts",
        "tactic_latency_profile",
        "latency_missing_tactic_ids",
        "fastest_available_tactic_ids",
        "slowest_available_tactic_ids",
        "available_tactic_duration_ms_min",
        "available_tactic_duration_ms_max",
        "available_tactic_duration_ms_median",
        "mathlib_probe_status",
        "mathlib_lake_project_import_available",
        "mathlib_absence_gate_enforced",
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
    - Teleology: Implements `_relative_receipt_paths` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_list_count` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_dict_value` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `result_card` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    authority = _dict_value(result, "authority_ceiling")
    scan = _dict_value(result, "secret_exclusion_scan")
    compile_counts = _dict_value(result, "compile_status_counts")
    expected_cases = result.get("expected_negative_cases")
    observed_cases = result.get("observed_negative_cases")
    receipt_paths = result.get("receipt_paths")
    omitted = [
        key for key in CARD_OMITTED_FULL_PAYLOAD_KEYS if key in result
    ]
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "portfolio_id": result.get("portfolio_id"),
        "environment_id": result.get("environment_id"),
        "cache_status": result.get("cache_status", "fresh_run_executed"),
        "full_output_available": True,
        "full_output_drilldown": (
            "rerun without --card or inspect the written receipt files"
        ),
        "availability_summary": {
            "tactic_count": result.get("tactic_count", 0),
            "available_tactic_count": _list_count(result.get("available_tactic_ids")),
            "unavailable_tactic_count": _list_count(
                result.get("unavailable_tactic_ids")
            ),
            "mathlib_dependent_tactic_count": _list_count(
                result.get("mathlib_dependent_tactic_ids")
            ),
            "compile_status_counts": compile_counts,
            "mathlib_probe_status": result.get("mathlib_probe_status"),
            "mathlib_lake_project_import_available": result.get(
                "mathlib_lake_project_import_available"
            ),
            "mathlib_absence_gate_enforced": result.get(
                "mathlib_absence_gate_enforced"
            ),
            "latency_profile_status": result.get("latency_profile_status"),
            "latency_profile_available_tactic_count": result.get(
                "latency_profile_available_tactic_count", 0
            ),
            "latency_band_counts": result.get("latency_band_counts", {}),
            "fastest_available_tactic_ids": result.get(
                "fastest_available_tactic_ids", []
            ),
            "slowest_available_tactic_ids": result.get(
                "slowest_available_tactic_ids", []
            ),
            "available_tactic_duration_ms_median": result.get(
                "available_tactic_duration_ms_median"
            ),
            "profile_rows_exported": False,
            "body_material_status": result.get("body_material_status"),
            "tactic_availability_status": result.get(
                "tactic_availability_status"
            ),
        },
        "source_artifact_summary": {
            "source_artifact_count": result.get("source_artifact_count", 0),
            "copied_source_artifact_count": result.get(
                "copied_source_artifact_count", 0
            ),
            "source_body_artifact_count": result.get(
                "source_body_artifact_count", 0
            ),
            "copied_source_body_artifact_count": result.get(
                "copied_source_body_artifact_count", 0
            ),
            "probe_source_body_status": result.get("probe_source_body_status"),
            "source_body_status": result.get("source_body_status"),
            "source_artifact_rows_exported": False,
            "source_digest_maps_exported": False,
        },
        "negative_case_coverage": {
            "expected_negative_case_count": (
                len(expected_cases) if isinstance(expected_cases, dict) else 0
            ),
            "observed_negative_case_count": (
                len(observed_cases) if isinstance(observed_cases, dict) else 0
            ),
            "missing_negative_case_count": _list_count(
                result.get("missing_negative_cases")
            ),
            "error_code_count": _list_count(result.get("error_codes")),
            "finding_count": _list_count(result.get("findings")),
        },
        "secret_exclusion_summary": {
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
            "availability_is_environment_scoped": authority.get(
                "availability_is_environment_scoped"
            ),
            "mathlib_absence_is_probe_result": authority.get(
                "mathlib_absence_is_probe_result"
            ),
            "lean_lake_execution_authorized": authority.get(
                "lean_lake_execution_authorized"
            ),
            "formal_proof_authority": authority.get("formal_proof_authority"),
            "provider_calls_authorized": authority.get(
                "provider_calls_authorized"
            ),
            "benchmark_performance_authority": authority.get(
                "benchmark_performance_authority"
            ),
            "latency_profile_is_environment_scoped": authority.get(
                "latency_profile_is_environment_scoped"
            ),
            "latency_profile_not_benchmark_authority": authority.get(
                "latency_profile_not_benchmark_authority"
            ),
            "release_authorized": authority.get("release_authorized"),
        },
        "no_export_guards": {
            "source_refs_exported": False,
            "source_artifact_imports_exported": False,
            "source_digests_exported": False,
            "findings_exported": False,
            "secret_scan_hits_exported": False,
            "receipt_paths_exported": False,
            "anti_claim_exported": False,
            "proof_bodies_exported": False,
            "provider_payloads_exported": False,
        },
        "receipt_summary": {
            "result_receipt_name": (
                BUNDLE_RESULT_NAME
                if result.get("input_mode")
                == "exported_tactic_portfolio_availability_bundle"
                else RESULT_NAME
            ),
            "receipt_count": _list_count(receipt_paths),
            "full_receipts_written": bool(receipt_paths),
            "receipt_paths_exported": False,
        },
        "output_economy": {
            "output_profile": "compact_card",
            "omitted_full_payload_keys": omitted,
            "body_in_receipt": result.get("body_in_receipt"),
            "body_redacted": True,
        },
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
    - Teleology: Implements `_build_result` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    source_payloads = _load_source_payloads(input_dir)
    negative_payloads = {
        name: payloads[name] for name in NEGATIVE_INPUT_STEMS if name in payloads
    }
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    secret_scan["body_material_status"] = "secret_exclusion_scan_no_payload_body_export"
    source_body_imports, source_body_findings = _source_body_imports(
        input_dir,
        public_root=public_root,
    )
    probe_source_imports, probe_source_findings = _probe_source_imports(
        input_dir,
        public_root=public_root,
    )
    source_imports = [*source_body_imports, *probe_source_imports]
    source_findings = [*source_body_findings, *probe_source_findings]

    portfolio_payload = payloads["tactic_portfolio_probe"]
    environment_probe = payloads["environment_probe"]
    if not isinstance(portfolio_payload, dict):
        portfolio_payload = {}
    if not isinstance(environment_probe, dict):
        environment_probe = {}
    rows = _tactic_rows(portfolio_payload)
    authoritative_environment = _authoritative_environment_state(source_payloads)
    availability_rows = _availability_rows_from_source(
        _source_portfolio_rows(source_payloads),
        projection_rows=rows,
        mathlib_available=authoritative_environment[
            "mathlib_lake_project_import_available"
        ],
    )
    summary = _portfolio_summary(availability_rows)
    source_artifact_findings = _source_artifact_findings(source_payloads)
    public_projection_findings = _public_projection_findings(
        rows,
        source_rows=_source_portfolio_rows(source_payloads),
        mathlib_available=authoritative_environment[
            "mathlib_lake_project_import_available"
        ],
    )
    public_body_findings = _public_projection_body_findings(rows)
    positive_findings = _positive_findings(
        rows=availability_rows,
        environment_probe={
            **environment_probe,
            "mathlib_lake_project_import_available": authoritative_environment[
                "mathlib_lake_project_import_available"
            ],
        },
        summary=summary,
    )
    environment_findings = _environment_probe_findings(
        environment_probe,
        authoritative_environment=authoritative_environment,
    )
    negative = _negative_findings(negative_payloads, known=set(summary["known_tactic_ids"]))
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    observed = negative["observed_negative_cases"]
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = [
        *source_findings,
        *source_artifact_findings,
        *public_projection_findings,
        *public_body_findings,
        *positive_findings,
        *environment_findings,
        *negative["findings"],
    ]
    error_codes = sorted({finding["error_code"] for finding in findings})
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    source_portfolio_payload = _source_portfolio_payload(source_payloads)
    mathlib_available = authoritative_environment["mathlib_lake_project_import_available"]
    mathlib_failures = [
        tactic_id
        for tactic_id in summary["mathlib_dependent_tactic_ids"]
        if tactic_id in summary["unavailable_tactic_ids"]
    ]
    status = (
        PASS
        if not source_findings
        and not source_artifact_findings
        and not public_projection_findings
        and not public_body_findings
        and not positive_findings
        and not environment_findings
        and not missing
        and not secret_scan["blocking_hit_count"]
        else "blocked"
    )
    return {
        "schema_version": "tactic_portfolio_availability_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": SOURCE_REFS,
        "expected_negative_cases": expected,
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "body_material_status": BODY_MATERIAL_STATUS,
        "tactic_availability_status": TACTIC_AVAILABILITY_STATUS,
        "body_in_receipt": BODY_IN_RECEIPT,
        "real_substrate_refs": REAL_SUBSTRATE_REFS,
        "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
        "source_target_refs": SOURCE_TARGET_REFS,
        "source_digests": SOURCE_DIGESTS,
        "source_body_digest_refs": SOURCE_DIGESTS,
        "probe_source_digest_refs": PROBE_SOURCE_DIGESTS,
        "source_artifact_imports": source_imports,
        "source_artifact_count": len(source_imports),
        "copied_source_artifact_count": sum(
            1 for row in source_imports if row["body_copied"] is True
        ),
        "source_body_artifact_count": len(source_body_imports),
        "copied_source_body_artifact_count": sum(
            1 for row in source_body_imports if row["body_copied"] is True
        ),
        "probe_source_body_status": PROBE_SOURCE_BODY_STATUS,
        "source_body_status": SOURCE_BODY_STATUS,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "portfolio_id": str(
            portfolio_payload.get("portfolio_id")
            or source_portfolio_payload.get("portfolio_id")
            or ""
        ),
        "environment_id": str(environment_probe.get("environment_id") or ""),
        "tactic_count": summary["tactic_count"],
        "known_tactic_ids": summary["known_tactic_ids"],
        "available_tactic_ids": summary["available_tactic_ids"],
        "unavailable_tactic_ids": summary["unavailable_tactic_ids"],
        "mathlib_dependent_tactic_ids": summary["mathlib_dependent_tactic_ids"],
        "compile_status_counts": summary["compile_status_counts"],
        "unavailable_reason_counts": summary["unavailable_reason_counts"],
        "latency_profile_status": LATENCY_PROFILE_STATUS,
        "latency_profile_available_tactic_count": summary[
            "latency_profile_available_tactic_count"
        ],
        "latency_band_counts": summary["latency_band_counts"],
        "tactic_latency_profile": summary["tactic_latency_profile"],
        "latency_missing_tactic_ids": summary["latency_missing_tactic_ids"],
        "fastest_available_tactic_ids": summary["fastest_available_tactic_ids"],
        "slowest_available_tactic_ids": summary["slowest_available_tactic_ids"],
        "available_tactic_duration_ms_min": summary[
            "available_tactic_duration_ms_min"
        ],
        "available_tactic_duration_ms_max": summary[
            "available_tactic_duration_ms_max"
        ],
        "available_tactic_duration_ms_median": summary[
            "available_tactic_duration_ms_median"
        ],
        "mathlib_probe_status": authoritative_environment["mathlib_probe_status"],
        "mathlib_lake_project_import_available": bool(mathlib_available),
        "mathlib_absence_gate_enforced": mathlib_available is False
        and bool(mathlib_failures),
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_write_receipts` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    public_root = _public_root_for_path(out_dir)
    paths = {
        "result": out_dir / RESULT_NAME,
        "board": out_dir / BOARD_NAME,
        "validation": out_dir / VALIDATION_RECEIPT_NAME,
    }
    if acceptance_out is not None:
        paths["acceptance"] = acceptance_out
    relative_paths = _relative_receipt_paths(paths, public_root)
    board = _build_board(result=result, secret_scan=result["secret_exclusion_scan"])
    result_receipt = _common_receipt(
        result,
        schema_version="tactic_portfolio_availability_result_receipt_v1",
        receipt_paths=relative_paths,
    )
    board["receipt_paths"] = relative_paths
    validation = _common_receipt(
        result,
        schema_version="tactic_portfolio_availability_validation_receipt_v1",
        receipt_paths=relative_paths,
    )
    validation["board_ref"] = _display(paths["board"], public_root=public_root)
    validation["result_ref"] = _display(paths["result"], public_root=public_root)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(paths["result"], result_receipt)
    write_json_atomic(paths["board"], board)
    write_json_atomic(paths["validation"], validation)
    if acceptance_out is not None:
        acceptance = _common_receipt(
            result,
            schema_version="tactic_portfolio_availability_fixture_acceptance_v1",
            receipt_paths=relative_paths,
        )
        write_json_atomic(acceptance_out, acceptance)
    result["receipt_paths"] = relative_paths
    return result


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.tactic_portfolio_availability_probe run",
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    target = Path(out_dir)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    return _write_receipts(
        result,
        target,
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
    )


def run_availability_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.tactic_portfolio_availability_probe "
        "run-availability-bundle"
    ),
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_availability_bundle` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    input_path = Path(input_dir)
    target = Path(out_dir)
    public_root = _public_root_for_path(target)
    cached = _fresh_availability_bundle_receipt(
        input_path,
        target,
        command=command,
    )
    if cached is not None:
        return cached
    result = _build_result(
        input_path,
        command=command,
        input_mode="exported_tactic_portfolio_availability_bundle",
        include_negative=False,
    )
    result["cache_status"] = "rebuilt"
    result["freshness_basis"] = _receipt_freshness_basis(
        command=command,
        receipt_path=target / BUNDLE_RESULT_NAME,
        input_paths=_input_paths(input_path, include_negative=False),
        input_mode="exported_tactic_portfolio_availability_bundle",
    )
    path = target / BUNDLE_RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = _display(path, public_root=public_root)
    receipt = _common_receipt(
        result,
        schema_version="exported_tactic_portfolio_availability_bundle_validation_result_v1",
        receipt_paths=[receipt_path],
    )
    write_json_atomic(path, receipt)
    result["receipt_paths"] = [receipt_path]
    return result


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `_parser` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description="Validate public tactic availability probe fixtures")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-availability-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.tactic_portfolio_availability_probe` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    if args.command == "run":
        command = (
            "python -m microcosm_core.organs.tactic_portfolio_availability_probe run "
            f"--input {args.input} --out {args.out}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    else:
        command = (
            "python -m microcosm_core.organs.tactic_portfolio_availability_probe "
            f"run-availability-bundle --input {args.input} --out {args.out}"
        )
        result = run_availability_bundle(args.input, args.out, command=command)
    if args.card:
        print(
            json.dumps(
                result_card(result),
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
        )
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
