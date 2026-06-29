"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.batch5_authority_systems_capsule` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, BUNDLE_INPUT_MODE, EXERCISE_MANIFEST_NAME, EXPECTED_MECHANISMS, EXPECTED_MODULE_IDS, EXPECTED_NEGATIVE_CASES, CASE_VERDICT_AUTHORITY, NEGATIVE_CASE_PROBE_SCHEMA, NEGATIVE_CASE_COMPUTED_PATHS, AUTHORITY_CEILING, ANTI_CLAIM, SOURCE_REQUIRED_ANCHORS, SPEC, evaluate_negative_case, run, run_batch5_bundle, result_card, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.organs._crown_jewel_common, microcosm_core.receipts
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    load_json_object,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)
from microcosm_core.receipts import write_json_atomic


ORGAN_ID = "batch5_authority_systems_capsule"
FIXTURE_ID = "first_wave.batch5_authority_systems_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch5_authority_systems_capsule"

RESULT_NAME = "batch5_authority_systems_capsule_result.json"
BOARD_NAME = "batch5_authority_systems_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch5_authority_systems_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch5_authority_systems_capsule_validation_result.json"
CARD_SCHEMA_VERSION = "batch5_authority_systems_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch5_authority_systems_capsule_bundle"
EXERCISE_MANIFEST_NAME = "batch5_exercise_manifest.json"

EXPECTED_MECHANISMS: tuple[str, ...] = (
    "reasoning_execution_receipt_validator",
    "reasoning_execution_replay_scope_lineage",
    "lean_provider_repair_loop",
    "process_orphan_reaper",
    "generated_state_fixpoint_drainer",
    "agent_trace_tape_compactor",
    "system_blast_radius",
    "doctrine_graph_compiler",
)

EXPECTED_MODULE_IDS: tuple[str, ...] = (
    "reasoning_execution_receipt_validator",
    "reasoning_execution_replay_scope",
    "reasoning_execution_lineage",
    "reasoning_execution_schedule_preflight",
    "lean_provider_repair_loop",
    "process_orphan_reaper",
    "generated_state_fixpoint_drainer",
    "agent_trace_tape_compactor",
    "system_blast_radius",
    "doctrine_graph_compiler",
)

EXPECTED_NEGATIVE_CASES = {
    "receipt_provider_context_drift": ("BATCH5_RECEIPT_DRIFT_REJECTED",),
    "irrelevant_context_no_replay": ("BATCH5_REPLAY_IRRELEVANT_CONTEXT_NO_REPLAY",),
    "proof_contract_sorry": ("BATCH5_PROOF_CONTRACT_BAD_PROOF_REJECTED",),
    "live_descendant_never_signal": (
        "BATCH5_ORPHAN_REAPER_LIVE_DESCENDANT_NEVER_SIGNAL",
    ),
    "nonconverging_residual_classified": (
        "BATCH5_DRAINER_NONCONVERGING_RESIDUAL_CLASSIFIED",
    ),
    "trace_omission_receipt_required": (
        "BATCH5_TRACE_OMISSION_RECEIPT_REQUIRED",
    ),
    "blast_radius_leaf_empty": (
        "BATCH5_BLAST_RADIUS_EMPTY_LEAF_DOES_NOT_INVENT_COVERAGE",
    ),
    "doctrine_deleted_path_drift": (
        "BATCH5_DOCTRINE_DELETED_PATH_DRIFT_REPORTED",
    ),
}

CASE_VERDICT_AUTHORITY = (
    "computed_by_batch5_authority_systems_capsule_exercise_probe"
)
NEGATIVE_CASE_PROBE_SCHEMA = (
    "batch5_authority_systems_capsule_negative_probe_v1"
)
NEGATIVE_CASE_COMPUTED_PATHS = {
    "receipt_provider_context_drift": {
        "mechanism_id": "reasoning_execution_receipt_validator",
        "computed_path": "drifted_receipt_codes_present",
    },
    "irrelevant_context_no_replay": {
        "mechanism_id": "reasoning_execution_replay_scope_lineage",
        "computed_path": "irrelevant_context_classifies_no_replay",
    },
    "proof_contract_sorry": {
        "mechanism_id": "lean_provider_repair_loop",
        "computed_path": "plan_only_sorry_rejected_before_lean",
    },
    "live_descendant_never_signal": {
        "mechanism_id": "process_orphan_reaper",
        "computed_path": "live_session_descendant_requires_owner_check_no_signal",
    },
    "nonconverging_residual_classified": {
        "mechanism_id": "generated_state_fixpoint_drainer",
        "computed_path": "moved_residual_signature_classified",
    },
    "trace_omission_receipt_required": {
        "mechanism_id": "agent_trace_tape_compactor",
        "computed_path": "trace_budget_omission_receipt_emitted",
    },
    "blast_radius_leaf_empty": {
        "mechanism_id": "system_blast_radius",
        "computed_path": "empty_leaf_bucket_not_invented",
    },
    "doctrine_deleted_path_drift": {
        "mechanism_id": "doctrine_graph_compiler",
        "computed_path": "deleted_code_path_and_tombstone_reported",
    },
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch5_public_capsule_not_live_runtime_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "proof_authority_delta": "none",
    "launch_authorized": False,
    "model_dispatch": False,
    "provider_dispatch": False,
    "runtime_execution": False,
    "live_process_signal_authorized": False,
    "live_generated_state_mutation_authorized": False,
    "live_provider_repair_authorized": False,
    "source_mutation_authorized": False,
    "official_leaderboard_submission": False,
    "publication_authorized": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Batch 5 validates copied public macro source bodies and bounded synthetic "
    "negative exercises for post-execution authority checks, incremental replay "
    "scope, verifier-gated proof repair, process orphan classification, generated "
    "state fixpoint settlement, trace compaction, blast-radius static analysis, "
    "and doctrine graph compilation. It is not live provider dispatch, not proof "
    "success, not process management authority, not generated-state mutation "
    "authority, not private-root equivalence, and not release approval."
)

SOURCE_REQUIRED_ANCHORS = {
    "tools/meta/factory/validate_reasoning_execution_receipt.py": (
        "def validate_receipt_schema(",
        "forbidden_context_sent",
        "execution_claimed_without_runtime_grant",
    ),
    "tools/meta/factory/build_reasoning_execution_replay_scope.py": (
        "def build_replay_scope(",
        "no_replay",
        "def _downstream_closure(",
    ),
    "tools/meta/factory/build_reasoning_execution_lineage.py": (
        "def build_lineage(",
        "replay_identity",
        "availability",
    ),
    "tools/meta/factory/build_reasoning_execution_schedule_preflight.py": (
        "def build_schedule_preflight(",
        "skip_not_demanded",
        "deterministic_topological",
    ),
    "tools/meta/factory/run_verisoftbench_micro10_c_arm_provider_repair.py": (
        "def _proof_contract_gate",
        "def _identifier_resolution_gate",
        "estimated_cost_usd",
    ),
    "tools/meta/control/orphan_reaper.py": (
        "def build_tool_server_pressure_inventory",
        "requires_owner_check",
        "SIGKILL",
    ),
    "system/lib/generated_state_drainer.py": (
        "def settle_generated_projection_owners",
        "def _settlement_residual_signature",
        "settlement_residual_source_moved",
    ),
    "system/lib/agent_execution_trace.py": (
        "def render_trace_tape",
        "def build_trace_tape_artifacts",
        "omission_receipt",
    ),
    "system/lib/code_architecture_projection.py": (
        "def build_blast_radius_packet",
        "reverse",
        "risk_score",
    ),
    "system/lib/doctrine_graph.py": (
        "def build_doctrine_graph",
        "def build_doctrine_compiler_ir",
        "tombstone",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 5 Authority and Systems Capsule",
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
        "microcosm-substrate/examples/batch5_authority_systems_capsule/"
        "exported_batch5_authority_systems_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _set(value: object) -> set[str]:
    """
    [ACTION]
    - Teleology: Implements `_set` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value}


def _stable_json_digest(payload: Any) -> str:
    """
    [ACTION]
    - Teleology: Implements `_stable_json_digest` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _negative_case_payloads(input_path: Path) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_negative_case_payloads` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    payloads: dict[str, dict[str, Any]] = {}
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = input_path / f"{case_id}.json"
        if not case_path.is_file():
            continue
        try:
            payload = json.loads(case_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads[case_id] = payload
    return payloads


def _receipt_validator_exercise(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_receipt_validator_exercise` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    grant = payload.get("grant") if isinstance(payload.get("grant"), Mapping) else {}
    valid = (
        payload.get("valid_receipt")
        if isinstance(payload.get("valid_receipt"), Mapping)
        else {}
    )
    drifted = (
        payload.get("drifted_receipt")
        if isinstance(payload.get("drifted_receipt"), Mapping)
        else {}
    )
    allowed_context = _set(grant.get("allowed_context_classes"))
    valid_context = _set(valid.get("context_classes"))
    drift_context = _set(drifted.get("context_classes"))
    valid_passes = (
        valid.get("provider") == grant.get("provider")
        and valid_context.issubset(allowed_context)
        and valid.get("artifact_sha256") == grant.get("artifact_sha256")
        and bool(grant.get("runtime_grant_issued"))
    )
    drift_codes: list[str] = []
    if drifted.get("provider") != grant.get("provider"):
        drift_codes.append("provider_substitution")
    if not drift_context.issubset(allowed_context):
        drift_codes.append("forbidden_context_sent")
    if drifted.get("artifact_sha256") != grant.get("artifact_sha256"):
        drift_codes.append("output_artifact_divergence")
    if drifted.get("runtime_execution") and not grant.get("runtime_grant_issued"):
        drift_codes.append("execution_claimed_without_runtime_grant")
    return {
        "status": "pass" if valid_passes and drift_codes else "blocked",
        "valid_receipt_status": "accepted" if valid_passes else "blocked",
        "drifted_receipt_codes": drift_codes,
    }


def _replay_scope_exercise(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_replay_scope_exercise` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    consumed = _set(payload.get("consumed_context_classes"))
    changed = _set(payload.get("changed_context_classes"))
    classification = "no_replay" if consumed.isdisjoint(changed) else "partial"
    return {
        "status": "pass" if classification == payload.get("expected") else "blocked",
        "classification": classification,
        "changed_context_classes": sorted(changed),
        "consumed_context_classes": sorted(consumed),
    }


def _proof_contract_gate_exercise(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_proof_contract_gate_exercise` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    proof = str(payload.get("bad_proof") or "")
    failure_classes: list[str] = []
    lowered = proof.casefold()
    if "sorry" in lowered:
        failure_classes.append("sorry_token")
    if "i will" in lowered or "plan:" in lowered:
        failure_classes.append("plan_only")
    if str(payload.get("declared_theorem") or "") in proof and "exact" not in lowered:
        failure_classes.append("self_reference_risk")
    return {
        "status": "pass" if failure_classes else "blocked",
        "contract_gate": "rejected_before_lean" if failure_classes else "accepted",
        "failure_classes": failure_classes,
        "solve_rate_claim": "0/8 historical banked attempts; no proof-success claim",
    }


def _orphan_reaper_exercise(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_orphan_reaper_exercise` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    process = payload.get("process") if isinstance(payload.get("process"), Mapping) else {}
    live_descendant = bool(process.get("live_session_descendant"))
    action = "requires_owner_check" if live_descendant else "safe_close_candidate"
    return {
        "status": "pass" if live_descendant and action == "requires_owner_check" else "blocked",
        "classification": action,
        "signal_sent": False,
        "never_signal_live_session_descendant": live_descendant and action == "requires_owner_check",
    }


def _fixpoint_drainer_exercise(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_fixpoint_drainer_exercise` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    residuals = payload.get("residual_signatures")
    if not isinstance(residuals, list):
        residuals = []
    seen: dict[str, str] = {}
    classification = "settled"
    for item in residuals:
        if not isinstance(item, Mapping):
            continue
        residual_id = str(item.get("residual_id") or "")
        source_signature = str(item.get("source_signature") or "")
        previous = seen.get(residual_id)
        if previous is not None and previous != source_signature:
            classification = "settlement_residual_source_moved"
            break
        if previous == source_signature:
            classification = "settlement_residual_signature_repeated"
            break
        seen[residual_id] = source_signature
    return {
        "status": "pass"
        if classification == payload.get("expected_classification")
        else "blocked",
        "classification": classification,
        "mutation_authorized": False,
    }


def _trace_tape_exercise(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_trace_tape_exercise` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    spans = payload.get("spans") if isinstance(payload.get("spans"), list) else []
    max_chars = int(payload.get("max_chars") or 120)
    rendered = "\n".join(
        str(span.get("text") or "")
        for span in spans
        if isinstance(span, Mapping)
    )
    if len(rendered) <= max_chars:
        tape = rendered
        omitted = 0
    else:
        head_budget = max(0, max_chars - 48)
        tape = f"{rendered[:head_budget]}\n#r0001 omitted_trace_bytes"
        omitted = len(rendered) - head_budget
    return {
        "status": "pass" if omitted > 0 and "#r0001" in tape else "blocked",
        "density_strategy": "byte_budget_pointer_tape",
        "omission_receipt": {
            "omitted_byte_count": omitted,
            "pointer_count": 1 if omitted else 0,
        },
        "tape_preview": tape,
    }


def _blast_radius_exercise(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_blast_radius_exercise` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    graph = payload.get("graph") if isinstance(payload.get("graph"), Mapping) else {}
    target = str(payload.get("target") or "")
    leaf = str(payload.get("leaf_target") or "")
    reverse: dict[str, list[str]] = {}
    for source, deps in graph.items():
        for dep in deps if isinstance(deps, list) else []:
            reverse.setdefault(str(dep), []).append(str(source))

    def dependents(start: str) -> set[str]:
        """
        [ACTION]
        - Teleology: Implements `_blast_radius_exercise.dependents` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        seen: set[str] = set()
        stack = list(reverse.get(start, []))
        while stack:
            item = stack.pop()
            if item in seen:
                continue
            seen.add(item)
            stack.extend(reverse.get(item, []))
        return seen

    target_deps = dependents(target)
    leaf_deps = dependents(leaf)
    return {
        "status": "pass" if target_deps and not leaf_deps else "blocked",
        "target_transitive_dependents": sorted(target_deps),
        "leaf_transitive_dependents": sorted(leaf_deps),
        "honest_empty_leaf_bucket": not leaf_deps,
    }


def _doctrine_graph_exercise(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_doctrine_graph_exercise` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    drift_findings: list[dict[str, str]] = []
    tombstones: list[dict[str, str]] = []
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        if node.get("code_path_exists") is False:
            drift_findings.append(
                {
                    "node_id": str(node.get("id") or ""),
                    "finding": "authority_gap_deleted_code_path",
                }
            )
        if node.get("status") == "tombstone":
            tombstones.append(
                {
                    "node_id": str(node.get("id") or ""),
                    "replacement_id": str(node.get("replacement_id") or ""),
                }
            )
    return {
        "status": "pass" if drift_findings and tombstones else "blocked",
        "drift_findings": drift_findings,
        "tombstone_candidates": tombstones,
    }


def _probe_result(
    case_id: str,
    probe_input: Mapping[str, Any],
    *,
    computed_value: bool,
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_probe_result` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "case_id": case_id,
        "status": "pass" if computed_value else "blocked",
        "computed": computed_value,
        "computed_value": computed_value,
        "computed_path": NEGATIVE_CASE_COMPUTED_PATHS[case_id]["computed_path"],
        "fixture_probe_source": "negative_case_fixture_probe_input",
        "fixture_probe_input_digest": _stable_json_digest(probe_input),
        "observed": dict(observed),
        "body_in_receipt": False,
    }


def _missing_probe_result(case_id: str, reason: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_missing_probe_result` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "case_id": case_id,
        "status": "blocked",
        "computed": False,
        "computed_value": None,
        "computed_path": NEGATIVE_CASE_COMPUTED_PATHS[case_id]["computed_path"],
        "fixture_probe_source": "missing_or_invalid_negative_case_fixture_probe_input",
        "fixture_probe_input_digest": None,
        "observed": {"reason": reason},
        "body_in_receipt": False,
    }


def _compute_negative_case_probe(
    case_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_compute_negative_case_probe` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    probe_input = (
        payload.get("probe_input") if isinstance(payload.get("probe_input"), Mapping) else {}
    )
    if not probe_input:
        return _missing_probe_result(case_id, "missing_probe_input")

    if case_id == "receipt_provider_context_drift":
        result = _receipt_validator_exercise(probe_input)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=result["status"] == "pass"
            and bool(result["drifted_receipt_codes"]),
            observed={
                "status": result["status"],
                "valid_receipt_status": result["valid_receipt_status"],
                "drifted_receipt_codes": result["drifted_receipt_codes"],
            },
        )

    if case_id == "irrelevant_context_no_replay":
        result = _replay_scope_exercise(probe_input)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=result["status"] == "pass"
            and result["classification"] == "no_replay",
            observed={
                "status": result["status"],
                "classification": result["classification"],
                "changed_context_classes": result["changed_context_classes"],
                "consumed_context_classes": result["consumed_context_classes"],
            },
        )

    if case_id == "proof_contract_sorry":
        result = _proof_contract_gate_exercise(probe_input)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=result["contract_gate"] == "rejected_before_lean"
            and bool(result["failure_classes"]),
            observed={
                "status": result["status"],
                "contract_gate": result["contract_gate"],
                "failure_classes": result["failure_classes"],
            },
        )

    if case_id == "live_descendant_never_signal":
        result = _orphan_reaper_exercise(probe_input)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=result["status"] == "pass"
            and result["signal_sent"] is False
            and result["never_signal_live_session_descendant"] is True,
            observed={
                "status": result["status"],
                "classification": result["classification"],
                "signal_sent": result["signal_sent"],
                "never_signal_live_session_descendant": result[
                    "never_signal_live_session_descendant"
                ],
            },
        )

    if case_id == "nonconverging_residual_classified":
        result = _fixpoint_drainer_exercise(probe_input)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=result["status"] == "pass"
            and result["classification"] == "settlement_residual_source_moved",
            observed={
                "status": result["status"],
                "classification": result["classification"],
                "mutation_authorized": result["mutation_authorized"],
            },
        )

    if case_id == "trace_omission_receipt_required":
        result = _trace_tape_exercise(probe_input)
        omission = (
            result.get("omission_receipt")
            if isinstance(result.get("omission_receipt"), Mapping)
            else {}
        )
        return _probe_result(
            case_id,
            probe_input,
            computed_value=result["status"] == "pass"
            and int(omission.get("omitted_byte_count") or 0) > 0
            and int(omission.get("pointer_count") or 0) > 0,
            observed={
                "status": result["status"],
                "density_strategy": result["density_strategy"],
                "omission_receipt": omission,
            },
        )

    if case_id == "blast_radius_leaf_empty":
        result = _blast_radius_exercise(probe_input)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=result["status"] == "pass"
            and result["honest_empty_leaf_bucket"] is True
            and bool(result["target_transitive_dependents"]),
            observed={
                "status": result["status"],
                "target_transitive_dependent_count": len(
                    result["target_transitive_dependents"]
                ),
                "leaf_transitive_dependent_count": len(
                    result["leaf_transitive_dependents"]
                ),
                "honest_empty_leaf_bucket": result["honest_empty_leaf_bucket"],
            },
        )

    if case_id == "doctrine_deleted_path_drift":
        result = _doctrine_graph_exercise(probe_input)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=result["status"] == "pass"
            and bool(result["drift_findings"])
            and bool(result["tombstone_candidates"]),
            observed={
                "status": result["status"],
                "drift_finding_count": len(result["drift_findings"]),
                "tombstone_candidate_count": len(result["tombstone_candidates"]),
            },
        )

    return _missing_probe_result(case_id, "unknown_case_id")


def _semantic_negative_result(
    case_id: str,
    error_codes: tuple[str, ...],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_negative_result` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": list(error_codes),
        "body_in_receipt": False,
    }


def _semantic_negative_not_rejected(
    case_id: str,
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_negative_not_rejected` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "case_id": case_id,
        "status": "pass",
        "error_codes": [],
        "observed": dict(observed),
        "body_in_receipt": False,
    }


def _semantic_negative_error(case_id: str, exc: Exception) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_negative_error` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": [
            f"BATCH5_AUTHORITY_SEMANTIC_EVALUATOR_{type(exc).__name__.upper()}"
        ],
        "body_in_receipt": False,
    }


def _source_manifest_for_input(input_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_manifest_for_input` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = public_root_for_path(input_dir)
    return validate_source_manifest(input_dir, SPEC, public_root=public_root)


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_negative_case` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        source_manifest = _source_manifest_for_input(input_dir)
        payload = _negative_case_payloads(input_dir).get(case_id, {})
        probe = _compute_negative_case_probe(case_id, payload)
        if probe.get("computed_value") is True:
            return _semantic_negative_result(case_id, expected_codes)
        return _semantic_negative_not_rejected(
            case_id,
            {
                "source_manifest_status": source_manifest.get("status"),
                "probe": probe,
            },
        )
    except Exception as exc:  # pragma: no cover - receipt carries exact class.
        return _semantic_negative_error(case_id, exc)


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_evaluate` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest = load_json_object(
        input_path / EXERCISE_MANIFEST_NAME,
        [],
        label=EXERCISE_MANIFEST_NAME,
    )
    findings: list[dict[str, Any]] = []
    module_rows = source_manifest.get("modules")
    observed_source_refs = {
        str(row.get("source_ref") or "")
        for row in module_rows
        if isinstance(module_rows, list) and isinstance(row, Mapping)
    }
    missing_sources = [
        ref for ref in SOURCE_REQUIRED_ANCHORS if ref not in observed_source_refs
    ]
    if missing_sources:
        findings.append(
            finding(
                "BATCH5_SOURCE_MODULE_SET_INCOMPLETE",
                "Batch 5 source manifest is missing expected macro bodies.",
                expected=sorted(SOURCE_REQUIRED_ANCHORS),
                observed=sorted(observed_source_refs),
            )
        )

    exercises = {
        "reasoning_execution_receipt_validator": _receipt_validator_exercise(
            manifest.get("receipt_validator", {})
        ),
        "reasoning_execution_replay_scope_lineage": _replay_scope_exercise(
            manifest.get("replay_scope", {})
        ),
        "lean_provider_repair_loop": _proof_contract_gate_exercise(
            manifest.get("proof_repair", {})
        ),
        "process_orphan_reaper": _orphan_reaper_exercise(
            manifest.get("orphan_reaper", {})
        ),
        "generated_state_fixpoint_drainer": _fixpoint_drainer_exercise(
            manifest.get("fixpoint_drainer", {})
        ),
        "agent_trace_tape_compactor": _trace_tape_exercise(
            manifest.get("trace_tape", {})
        ),
        "system_blast_radius": _blast_radius_exercise(
            manifest.get("blast_radius", {})
        ),
        "doctrine_graph_compiler": _doctrine_graph_exercise(
            manifest.get("doctrine_graph", {})
        ),
    }
    for mechanism_id, result in exercises.items():
        if result.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH5_MECHANISM_EXERCISE_FAILED",
                    "A Batch 5 public-safe mechanism exercise did not pass.",
                    subject_id=mechanism_id,
                    observed=result,
                )
            )

    negative_case_payloads = _negative_case_payloads(input_path)
    negative_case_probes = [
        _compute_negative_case_probe(case_id, negative_case_payloads.get(case_id, {}))
        for case_id in sorted(EXPECTED_NEGATIVE_CASES)
    ]

    return {
        "status": "pass" if not findings else "blocked",
        "mechanism_count": len(EXPECTED_MECHANISMS),
        "mechanisms": [
            {"mechanism_id": key, "status": value.get("status")}
            for key, value in exercises.items()
        ],
        "runtime_exercises": exercises,
        "negative_case_probe_summary": {
            "schema_version": NEGATIVE_CASE_PROBE_SCHEMA,
            "probe_count": len(negative_case_probes),
            "computed_probe_count": sum(
                1 for row in negative_case_probes if row.get("computed_value") is True
            ),
            "fixture_verdict_echo_risk_count": sum(
                1
                for row in negative_case_probes
                if row.get("fixture_probe_source")
                != "negative_case_fixture_probe_input"
            ),
            "body_in_receipt": False,
        },
        "negative_case_probes": negative_case_probes,
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "source_manifest_ref": source_manifest.get("manifest_ref"),
        "authority_ceiling": AUTHORITY_CEILING,
        "error_codes": [],
        "findings": findings,
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
    - Teleology: Implements `run` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    result = run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )
    _write_enriched_acceptance(result, acceptance_out)
    return result


def run_batch5_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_batch5_bundle` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    result = run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )
    _write_enriched_acceptance(result, acceptance_out)
    return result


def _write_enriched_acceptance(
    result: Mapping[str, Any],
    acceptance_out: str | Path | None,
) -> None:
    """
    [ACTION]
    - Teleology: Implements `_write_enriched_acceptance` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not acceptance_out:
        return
    source = (
        result.get("source_module_manifest")
        if isinstance(result.get("source_module_manifest"), Mapping)
        else {}
    )
    modules = source.get("modules") if isinstance(source.get("modules"), list) else []
    source_refs = [
        str(row.get("source_ref"))
        for row in modules
        if isinstance(row, Mapping) and row.get("source_ref")
    ]
    module_count = int(source.get("module_count") or 0)
    observed_negative_cases = (
        result.get("observed_negative_cases")
        if isinstance(result.get("observed_negative_cases"), list)
        else []
    )
    exercise = (
        result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    )
    negative_case_probe_summary = (
        exercise.get("negative_case_probe_summary")
        if isinstance(exercise.get("negative_case_probe_summary"), Mapping)
        else {}
    )
    write_json_atomic(
        acceptance_out,
        {
            "schema_version": "microcosm_first_wave_fixture_acceptance_v1",
            "organ_id": ORGAN_ID,
            "fixture_id": FIXTURE_ID,
            "status": result.get("status"),
            "accepted": result.get("status") == "pass",
            "real_substrate_disposition": result.get("real_substrate_disposition"),
            "result_ref": result.get("receipt_paths", [None])[0],
            "validation_ref": result.get("receipt_paths", [None, None, None])[2],
            "anti_claim": ANTI_CLAIM,
            "body_in_receipt": False,
            "semantic_negative_case_evaluator_used": result.get(
                "semantic_negative_case_evaluator_used"
            )
            is True,
            "observed_negative_case_count": len(observed_negative_cases),
            "negative_case_probe_summary": dict(negative_case_probe_summary),
            "source_module_count": module_count,
            "verified_source_module_count": module_count
            if source.get("status") == "pass"
            else 0,
            "source_module_manifest_status": source.get("status"),
            "source_module_manifest_ref": source.get("manifest_ref"),
            "body_copied_material_count": module_count,
            "source_module_imports": {
                "status": source.get("status"),
                "source_module_import_status": source.get("status"),
                "module_count": module_count,
                "verified_module_count": module_count
                if source.get("status") == "pass"
                else 0,
                "source_refs": source_refs,
                "body_in_receipt": False,
            },
            "source_open_body_imports": {
                "status": source.get("status"),
                "body_material_count": module_count,
                "source_import_class": source.get("source_import_class"),
                "source_manifest_refs": [source.get("manifest_ref")],
                "body_in_receipt": False,
                "body_text_in_receipt": False,
            },
        },
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["mechanism_count"] = exercise.get("mechanism_count")
    card["copied_macro_source_module_count"] = exercise.get(
        "copied_macro_source_module_count"
    )
    card["real_substrate_disposition"] = result.get("real_substrate_disposition")
    return card


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.batch5_authority_systems_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="microcosm batch5-authority-systems")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-batch5-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    runner = run_batch5_bundle if args.action == "run-batch5-bundle" else run
    result = runner(
        args.input,
        args.out,
        acceptance_out=args.acceptance_out,
        command=f"{ORGAN_ID} {args.action}",
    )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
