"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.batch8_validator_checker_capsule` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, BUNDLE_INPUT_MODE, EXERCISE_MANIFEST_NAME, VALIDATORS_SOURCE_REF, EXPECTED_ENGINES, EXPECTED_NEGATIVE_CASES, NEGATIVE_CASE_ENGINES, AUTHORITY_CEILING, ANTI_CLAIM, SOURCE_REQUIRED_ANCHORS, SPEC, evaluate_negative_case, run, run_batch8_validator_checker_bundle, result_card, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.organs._crown_jewel_common
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import importlib
import json
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
    validate_source_manifest,
)


ORGAN_ID = "batch8_validator_checker_capsule"
FIXTURE_ID = "first_wave.batch8_validator_checker_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch8_validator_checker_capsule"

RESULT_NAME = "batch8_validator_checker_capsule_result.json"
BOARD_NAME = "batch8_validator_checker_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch8_validator_checker_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch8_validator_checker_capsule_validation_result.json"
CARD_SCHEMA_VERSION = "batch8_validator_checker_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch8_validator_checker_capsule_bundle"
EXERCISE_MANIFEST_NAME = "batch8_validator_checker_exercise_manifest.json"

VALIDATORS_SOURCE_REF = "self-indexing-cognitive-substrate/src/idea_microcosm/validators.py"

EXPECTED_ENGINES: tuple[str, ...] = (
    "validator_source_anchor_matrix",
    "status_policy_judge_matrix",
    "private_boundary_scanner_matrix",
    "specimen_checker_matrix",
    "release_gate_checker_matrix",
    "validate_entrypoint_witness",
)

EXPECTED_NEGATIVE_CASES = {
    "missing_validator_source": ("BATCH8_VALIDATOR_SOURCE_REQUIRED",),
    "policy_allows_poisoning": ("BATCH8_VALIDATOR_POLICY_POISONING_BLOCK_REQUIRED",),
    "private_boundary_blind": ("BATCH8_VALIDATOR_PRIVATE_BOUNDARY_REQUIRED",),
    "specimen_checker_missing": ("BATCH8_VALIDATOR_SPECIMEN_CHECKERS_REQUIRED",),
    "release_gate_missing": ("BATCH8_VALIDATOR_RELEASE_GATES_REQUIRED",),
    "validate_entrypoint_bypassed": ("BATCH8_VALIDATOR_ENTRYPOINT_REQUIRED",),
}

NEGATIVE_CASE_ENGINES = {
    "missing_validator_source": (
        "validator_source_anchor_matrix",
        "BATCH8_VALIDATOR_SOURCE_REQUIRED",
    ),
    "policy_allows_poisoning": (
        "status_policy_judge_matrix",
        "BATCH8_VALIDATOR_POLICY_POISONING_BLOCK_REQUIRED",
    ),
    "private_boundary_blind": (
        "private_boundary_scanner_matrix",
        "BATCH8_VALIDATOR_PRIVATE_BOUNDARY_REQUIRED",
    ),
    "specimen_checker_missing": (
        "specimen_checker_matrix",
        "BATCH8_VALIDATOR_SPECIMEN_CHECKERS_REQUIRED",
    ),
    "release_gate_missing": (
        "release_gate_checker_matrix",
        "BATCH8_VALIDATOR_RELEASE_GATES_REQUIRED",
    ),
    "validate_entrypoint_bypassed": (
        "validate_entrypoint_witness",
        "BATCH8_VALIDATOR_ENTRYPOINT_REQUIRED",
    ),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch8_validator_checker_capsule_not_release_or_full_validator_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "model_dispatch": False,
    "source_mutation_authorized": False,
    "full_validator_suite_freshness_claim": False,
    "public_clone_or_hosting_authority": False,
    "test_completeness_proof": False,
}

ANTI_CLAIM = (
    "Batch 8 Validator Checker imports the real idea_microcosm validators.py "
    "body and exercises individual checker functions for status collapse, "
    "specimen gates, release gates, private-boundary scanning, and the validate "
    "entrypoint. It is not a public release, not a hosted-public claim, not a "
    "complete validator-suite proof, and not source mutation authority."
)

SOURCE_REQUIRED_ANCHORS = {
    VALIDATORS_SOURCE_REF: (
        "def private_boundary_hits(root: Path)",
        "def policy_wellformedness_failures(",
        "def judge_status_request(",
        "def _status_collapse_suite_failures(root: Path)",
        "def _source_shuttle_specimen_failures(root: Path)",
        "def validate(root: Path",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 8 Validator Checker Capsule",
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
        "microcosm-substrate/examples/batch8_validator_checker_capsule/"
        "exported_batch8_validator_checker_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _repo_root(public_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_repo_root` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_root.parent


def _macro_root(public_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_macro_root` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _repo_root(public_root) / "self-indexing-cognitive-substrate"


def _copied_source(public_root: Path, source_ref: str = VALIDATORS_SOURCE_REF) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_copied_source` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (
        public_root
        / "examples/batch8_validator_checker_capsule/"
        "exported_batch8_validator_checker_capsule_bundle/source_modules"
        / source_ref
    )


def _read(public_root: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_read` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return _copied_source(public_root).read_text(encoding="utf-8")


def _macro_state_available(public_root: Path) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_macro_state_available` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (_macro_root(public_root) / "state/idea_graph.json").is_file()


def _import_validators(public_root: Path):
    """
    [ACTION]
    - Teleology: Implements `_import_validators` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source_root = _macro_root(public_root) / "src"
    if not source_root.is_dir():
        source_root = _copied_source(public_root).parents[2] / "src"
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))
    return importlib.import_module("idea_microcosm.validators")


def _validator_source_anchor_matrix(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validator_source_anchor_matrix` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    text = _read(public_root)
    checker_defs = [
        line for line in text.splitlines() if line.startswith("def _") and "failures(" in line
    ]
    anchors_present = all(anchor in text for anchor in SOURCE_REQUIRED_ANCHORS[VALIDATORS_SOURCE_REF])
    release_gate_anchors = all(
        token in text
        for token in (
            "_hosted_public_ci_workflow_gate_failures",
            "_release_artifact_integrity_witness_failures",
            "_actual_public_remote_clone_execution_failures",
            "_public_release_package_manifest_gate_failures",
        )
    )
    status_policy_anchors = all(
        token in text
        for token in ("def policy_wellformedness_failures(", "def judge_status_request(")
    )
    private_boundary_anchors = "def private_boundary_hits(root: Path)" in text
    specimen_checker_anchors = all(
        token in text
        for token in (
            "_status_collapse_suite_failures",
            "_source_shuttle_specimen_failures",
        )
    )
    validate_entrypoint_anchor = "def validate(root: Path" in text
    return {
        "status": "pass" if anchors_present and release_gate_anchors and len(checker_defs) >= 30 else "blocked",
        "engine_id": "validator_source_anchor_matrix",
        "checker_failure_function_count": len(checker_defs),
        "anchors_present": anchors_present,
        "status_policy_anchors_present": status_policy_anchors,
        "private_boundary_anchors_present": private_boundary_anchors,
        "specimen_checker_anchors_present": specimen_checker_anchors,
        "release_gate_anchors_present": release_gate_anchors,
        "validate_entrypoint_anchor_present": validate_entrypoint_anchor,
        "claim_ceiling": "Copied validators.py source shape only; not full validator-suite coverage.",
    }


def _status_policy_judge_matrix(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_status_policy_judge_matrix` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    mod = _import_validators(public_root)
    policy = {
        "policy_wellformedness": {
            "policy_poisoning_default": "malformed_policy_blocks_judgment"
        },
        "tier_model": {
            "model_type": "product_tiers_with_fixture_ordering_projection"
        },
        "allowed_transitions": [
            {
                "from": "fixture_constructed",
                "to": "fit_for_public_claim",
                "reason": "fixture has receipt refs",
            }
        ],
        "prohibited_upgrades": [
            {
                "from": "receipt_observed",
                "to": "truth_authority",
                "decision": "block",
                "reason": "receipt is not truth authority",
            }
        ],
        "required_evidence": [
            {
                "from": "fixture_constructed",
                "to": "fit_for_public_claim",
                "refs": ["receipt:validator"],
                "decision_if_missing": "downgrade",
                "reason": "public claim needs receipt evidence",
            }
        ],
        "required_gates": [],
        "downgrade_rules": [],
        "default_decision": {
            "decision": "block",
            "reason": "transition_not_in_policy",
        },
    }
    allowed = mod.judge_status_request(
        policy,
        {
            "from": "fixture_constructed",
            "to": "fit_for_public_claim",
            "evidence_refs": ["receipt:validator"],
        },
    )
    missing = mod.judge_status_request(
        policy,
        {"from": "fixture_constructed", "to": "fit_for_public_claim", "evidence_refs": []},
    )
    forbidden = mod.judge_status_request(
        policy,
        {"from": "receipt_observed", "to": "truth_authority"},
    )
    poisoned = mod.judge_status_request(
        {"policy_wellformedness": {"policy_poisoning_default": "allow"}},
        {"from": "receipt_observed", "to": "truth_authority"},
    )
    transition_failures: list[dict[str, Any]] = []
    mod._validate_transition(
        transition_failures,
        case_id="matrix",
        field="forbidden_transition",
        transition={"from": "known", "to": "unknown"},
        states={"known"},
    )
    return {
        "status": "pass"
        if allowed.get("decision") == "allow"
        and missing.get("decision") == "downgrade"
        and forbidden.get("decision") == "block"
        and poisoned.get("decision") == "block"
        and transition_failures
        else "blocked",
        "engine_id": "status_policy_judge_matrix",
        "allowed_decision": allowed.get("decision"),
        "missing_evidence_decision": missing.get("decision"),
        "forbidden_decision": forbidden.get("decision"),
        "poisoned_policy_decision": poisoned.get("decision"),
        "transition_failure_count": len(transition_failures),
        "claim_ceiling": "Status-judge and transition helper exercise only.",
    }


def _private_boundary_scanner_matrix(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_private_boundary_scanner_matrix` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    mod = _import_validators(public_root)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "fixture.txt").write_text(
            "home=" + "/" + "Users/" + "sample\nmail=" + "alpha" + "@" + "example.com\n",
            encoding="utf-8",
        )
        hits = mod.private_boundary_hits(root)
    patterns = {str(row.get("pattern")) for row in hits if isinstance(row, dict)}
    return {
        "status": "pass" if {"private_home_path", "private_email"}.issubset(patterns) else "blocked",
        "engine_id": "private_boundary_scanner_matrix",
        "observed_patterns": sorted(patterns),
        "hit_count": len(hits),
        "body_in_receipt": False,
        "claim_ceiling": "Private-boundary detector exercise only; no private body text is included in receipts.",
    }


def _zero_failure_matrix(public_root: Path, names: tuple[str, ...], engine_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_zero_failure_matrix` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    mod = _import_validators(public_root)
    root = _macro_root(public_root)
    rows: list[dict[str, Any]] = []
    for name in names:
        failures = getattr(mod, name)(root)
        rows.append({"checker": name, "failure_count": len(failures)})
    return {
        "status": "pass" if all(row["failure_count"] == 0 for row in rows) else "blocked",
        "engine_id": engine_id,
        "checker_count": len(rows),
        "checkers": rows,
        "claim_ceiling": "Existing macro fixture checker matrix only; not proof of hosted public release.",
    }


def _specimen_checker_matrix(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_specimen_checker_matrix` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _zero_failure_matrix(
        public_root,
        (
            "_status_collapse_suite_failures",
            "_status_preserving_control_plane_specimen_failures",
            "_correction_survival_loop_specimen_failures",
            "_self_comprehension_navigator_specimen_failures",
            "_task_ledger_specimen_failures",
            "_atlas_navigation_bands_failures",
        ),
        "specimen_checker_matrix",
    )


def _release_gate_checker_matrix(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_release_gate_checker_matrix` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _zero_failure_matrix(
        public_root,
        (
            "_release_standards_axiom_gate_failures",
            "_source_capsule_provenance_specimen_failures",
            "_source_shuttle_specimen_failures",
            "_concurrency_mission_control_failures",
            "_native_concurrency_guard_failures",
            "_release_root_compiler_failures",
        ),
        "release_gate_checker_matrix",
    )


def _validate_entrypoint_witness(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validate_entrypoint_witness` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    macro_root = _macro_root(public_root)
    if not _macro_state_available(public_root):
        source_anchor_present = "def validate(root: Path" in _read(public_root)
        return {
            "status": "pass" if source_anchor_present else "blocked",
            "engine_id": "validate_entrypoint_witness",
            "validator_status": "source_anchor_only_public_runtime",
            "check_count": 0,
            "write_receipt": False,
            "macro_state_available": False,
            "claim_ceiling": (
                "Public runtime bundle checks the copied validate entrypoint "
                "anchor only; full no-write validate execution requires macro state."
            ),
        }
    mod = _import_validators(public_root)
    result = mod.validate(macro_root, write_receipt=False)
    checks = result.get("checks") if isinstance(result.get("checks"), list) else []
    return {
        "status": "pass" if result.get("status") == "ok" and len(checks) >= 20 else "blocked",
        "engine_id": "validate_entrypoint_witness",
        "validator_status": result.get("status"),
        "check_count": len(checks),
        "write_receipt": False,
        "macro_state_available": True,
        "claim_ceiling": "No-write validate entrypoint witness only.",
    }


def _public_runtime_source_only_engine(engine_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_public_runtime_source_only_engine` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "status": "pass",
        "engine_id": engine_id,
        "public_runtime_source_only": True,
        "macro_state_available": False,
        "claim_ceiling": (
            "Copied source anchor and digest evidence only in public runtime "
            "bundle; full checker execution requires macro state."
        ),
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_evaluate` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
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
    if _macro_state_available(public_root) and not exported_bundle_input:
        engines = [
            _validator_source_anchor_matrix(public_root),
            _status_policy_judge_matrix(public_root),
            _private_boundary_scanner_matrix(public_root),
            _specimen_checker_matrix(public_root),
            _release_gate_checker_matrix(public_root),
            _validate_entrypoint_witness(public_root),
        ]
    else:
        engines = [
            _validator_source_anchor_matrix(public_root),
            *[
                _public_runtime_source_only_engine(engine_id)
                for engine_id in EXPECTED_ENGINES
                if engine_id != "validator_source_anchor_matrix"
            ],
        ]
    findings: list[dict[str, Any]] = []
    for engine in engines:
        if engine.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH8_VALIDATOR_CHECKER_ENGINE_BLOCKED",
                    "Validator checker engine exercise did not pass.",
                    subject_id=str(engine.get("engine_id")),
                    observed=engine.get("status"),
                )
            )
    if source_manifest.get("module_count", 0) != 1:
        findings.append(
            finding(
                "BATCH8_VALIDATOR_CHECKER_SOURCE_MODULE_COUNT_INVALID",
                "Validator checker capsule must copy validators.py as one required source body.",
                expected=1,
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
        "error_codes": [],
        "findings": findings,
        "body_in_receipt": False,
    }


@lru_cache(maxsize=8)
def _semantic_runtime_exercises(input_ref: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_runtime_exercises` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_ref)
    public_root = public_root_for_path(input_path)
    source_manifest = validate_source_manifest(input_path, SPEC, public_root=public_root)
    exercise = _evaluate(input_path, public_root, source_manifest)
    return {
        "source_manifest": {
            key: value
            for key, value in source_manifest.items()
            if key not in {"findings", "source_manifest_path"}
        },
        "exercise": exercise,
    }


def _engine_map(runtime: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_engine_map` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    exercise = runtime.get("exercise") if isinstance(runtime.get("exercise"), Mapping) else {}
    engines = exercise.get("engines") if isinstance(exercise.get("engines"), list) else []
    return {
        str(row.get("engine_id")): row
        for row in engines
        if isinstance(row, Mapping) and row.get("engine_id")
    }


def _observed_negative_case(case_id: str, runtime: Mapping[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_observed_negative_case` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    engines = _engine_map(runtime)
    source_manifest = (
        runtime.get("source_manifest")
        if isinstance(runtime.get("source_manifest"), Mapping)
        else {}
    )
    engine_id, _expected_code = NEGATIVE_CASE_ENGINES.get(case_id, ("", ""))
    engine = engines.get(engine_id, {})
    source_engine = engines.get("validator_source_anchor_matrix", {})
    source_only_witness = (
        engine.get("public_runtime_source_only") is True
        and source_engine.get("status") == "pass"
        and source_engine.get("anchors_present") is True
    )
    if case_id == "missing_validator_source":
        return (
            source_manifest.get("module_count") == 1
            and engine.get("anchors_present") is True
            and engine.get("release_gate_anchors_present") is True
            and int(engine.get("checker_failure_function_count") or 0) >= 30
        )
    if case_id == "policy_allows_poisoning":
        return (
            engine.get("poisoned_policy_decision") == "block"
            and engine.get("forbidden_decision") == "block"
            and int(engine.get("transition_failure_count") or 0) > 0
        ) or (
            source_only_witness
            and source_engine.get("status_policy_anchors_present") is True
        )
    if case_id == "private_boundary_blind":
        patterns = set(engine.get("observed_patterns") or [])
        return {"private_home_path", "private_email"}.issubset(patterns) or (
            source_only_witness
            and source_engine.get("private_boundary_anchors_present") is True
        )
    if case_id == "specimen_checker_missing":
        checkers = engine.get("checkers") if isinstance(engine.get("checkers"), list) else []
        return (
            engine.get("status") == "pass"
            and engine.get("checker_count") == 6
            and all(row.get("failure_count") == 0 for row in checkers if isinstance(row, Mapping))
        ) or (
            source_only_witness
            and source_engine.get("specimen_checker_anchors_present") is True
        )
    if case_id == "release_gate_missing":
        checkers = engine.get("checkers") if isinstance(engine.get("checkers"), list) else []
        return (
            engine.get("status") == "pass"
            and engine.get("checker_count") == 6
            and all(row.get("failure_count") == 0 for row in checkers if isinstance(row, Mapping))
        ) or (
            source_only_witness
            and source_engine.get("release_gate_anchors_present") is True
        )
    if case_id == "validate_entrypoint_bypassed":
        return (
            engine.get("status") == "pass"
            and engine.get("write_receipt") is False
            and engine.get("validator_status") in {"ok", "source_anchor_only_public_runtime"}
        ) or (
            source_only_witness
            and source_engine.get("validate_entrypoint_anchor_present") is True
        )
    return False


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_negative_case` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    _engine_id, expected_code = NEGATIVE_CASE_ENGINES.get(case_id, ("", ""))
    observed = _observed_negative_case(
        case_id,
        _semantic_runtime_exercises(str(Path(input_dir))),
    )
    return {
        "status": "blocked" if observed else "pass",
        "error_codes": [expected_code] if observed and expected_code else [],
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
    - Teleology: Implements `run` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
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


def run_batch8_validator_checker_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_batch8_validator_checker_bundle` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `result_card` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
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
        "full_validator_suite_freshness_claim": ceiling.get(
            "full_validator_suite_freshness_claim"
        ),
        "public_clone_or_hosting_authority": ceiling.get(
            "public_clone_or_hosting_authority"
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
    - Teleology: Implements `main` for `microcosm_core.organs.batch8_validator_checker_capsule` while keeping the callable contract visible to source-module readers.
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
