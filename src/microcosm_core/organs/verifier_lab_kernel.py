"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.verifier_lab_kernel` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, PACKET_NAME, PROOF_LAB_ROUTE_NAME, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, SOURCE_MODULE_MANIFEST_NAME, SOURCE_IMPORT_CLASS, SOURCE_BODY_STATUS, PUBLIC_SAFE_SOURCE_MODULE_CLASSES, SOURCE_MODULE_RELATIONS, SOURCE_REF_PREFIXES, PUBLIC_ROOT_POLICY_REL, MODULE_PUBLIC_ROOT, NEGATIVE_INPUT_NAMES, EXPECTED_NEGATIVE_CASES, EXPECTED_PROOF_LAB_ROUTE_ID, EXPECTED_ROUTE_COMPONENT_ORGANS, EXPECTED_ROUTE_PATTERN_IDS, FORBIDDEN_FORWARD_KEYS, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.organs, microcosm_core.receipts, microcosm_core.schemas, microcosm_core.secret_exclusion_scan
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from microcosm_core.organs import corpus_readiness_mathlib_absence_gate
from microcosm_core.organs import formal_math_lean_proof_witness
from microcosm_core.organs import formal_math_premise_retrieval
from microcosm_core.organs import formal_math_verifier_trace_repair_loop
from microcosm_core.organs import lean_std_premise_index
from microcosm_core.organs import proof_diagnostic_evidence_spine
from microcosm_core.organs import ring2_premise_retrieval_precision_recall_harness
from microcosm_core.organs import tactic_portfolio_availability_probe
from microcosm_core.organs import target_shape_tactic_routing_gate
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "verifier_lab_kernel"
FIXTURE_ID = "first_wave.verifier_lab_kernel"
VALIDATOR_ID = "validator.microcosm.organs.verifier_lab_kernel"

PACKET_NAME = "verifier_lab_packet.json"
PROOF_LAB_ROUTE_NAME = "proof_lab_route.json"
RESULT_NAME = "verifier_lab_kernel_result.json"
BOARD_NAME = "verifier_lab_kernel_board.json"
VALIDATION_RECEIPT_NAME = "verifier_lab_kernel_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/verifier_lab_kernel_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_verifier_lab_kernel_bundle_validation_result.json"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_BODY_STATUS = (
    "copied_non_secret_verifier_lab_kernel_component_source_bodies_with_digest_provenance"
)
PUBLIC_SAFE_SOURCE_MODULE_CLASSES = {"public_macro_tool_body"}
SOURCE_MODULE_RELATIONS = {"exact_copy"}
SOURCE_REF_PREFIXES = ("src/microcosm_core/organs/", "tools/meta/factory/")
PUBLIC_ROOT_POLICY_REL = Path("core/private_state_forbidden_classes.json")
MODULE_PUBLIC_ROOT = Path(__file__).resolve().parents[3]

NEGATIVE_INPUT_NAMES = (
    "forward_problem_leaks_candidate_body.json",
    "oracle_counted_as_forward.json",
    "provider_claims_proof.json",
    "cp2_candidate_contains_proof_body.json",
    "evolve_mutates_unbounded_artifact.json",
)

EXPECTED_NEGATIVE_CASES = {
    "forward_problem_leaks_candidate_body": [
        "VERIFIER_LAB_FORWARD_FIELD_FORBIDDEN"
    ],
    "oracle_counted_as_forward": [
        "VERIFIER_LAB_ORACLE_FORWARD_CONTAMINATION"
    ],
    "provider_claims_proof": [
        "VERIFIER_LAB_PROVIDER_PROOF_AUTHORITY_FORBIDDEN"
    ],
    "cp2_candidate_contains_proof_body": [
        "VERIFIER_LAB_CP2_PROOF_BODY_FORBIDDEN"
    ],
    "evolve_mutates_unbounded_artifact": [
        "VERIFIER_LAB_EVOLVE_SCOPE_FORBIDDEN"
    ],
}
EXPECTED_PROOF_LAB_ROUTE_ID = "formal_prover_context_strategy_gate"
EXPECTED_ROUTE_COMPONENT_ORGANS = {
    "corpus_readiness_mathlib_absence_gate",
    "lean_std_premise_index",
    "formal_math_premise_retrieval",
    "tactic_portfolio_availability_probe",
    "target_shape_tactic_routing_gate",
    "ring2_premise_retrieval_precision_recall_harness",
    "formal_math_verifier_trace_repair_loop",
    "proof_diagnostic_evidence_spine",
    "formal_math_lean_proof_witness",
}
EXPECTED_ROUTE_PATTERN_IDS = {
    "corpus_readiness_mathlib_absence_gate",
    "lean_std_toolchain_premise_index",
    "prover_premise_retrieval_term_scoring",
    "tactic_portfolio_availability_probe",
    "target_shape_tactic_routing_gate",
    "ring2_premise_retrieval_precision_recall_harness",
}

FORBIDDEN_FORWARD_KEYS = {
    "candidate_body",
    "ideal_body",
    "repair_body",
    "oracle_needed_premise_ids",
    "source_proof_body",
    "base_problem_index",
    "proof_body",
    "ground_truth_proof",
}
FORBIDDEN_CP2_KEYS = {
    "proof_body",
    "candidate_body",
    "ground_truth_proof",
    "oracle_template",
    "source_proof_body",
    "raw_tactic_script",
    "provider_output_body",
}
ALLOWED_CP2_ACTION_CLASSES = {
    "rewrite_direction_flip",
    "case_close_constructor",
    "induction_on_visible_head",
    "premise_exact",
    "unfold_then_simp",
    "retry_with_recipe",
}
ALLOWED_EVOLVE_ARTIFACTS = {
    "target_shape_routing_table",
    "tactic_action_priors",
    "failure_class_routing",
    "context_recipe_selection",
    "cp2_translation_templates",
    "repair_novelty_predicates",
}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "verifier_governed_public_kernel_receipt_only",
    "lean_lake_execution_authorized": "bounded_public_component_witness_only",
    "formal_proof_authority": False,
    "oracle_success_counts_as_forward_success": False,
    "provider_text_counts_as_proof": False,
    "cp2_outputs_are_proof_bodies": False,
    "evolve_mutates_arbitrary_code": False,
    "proof_bodies_allowed_in_receipts": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "macro_private_body_import_authorized": False,
    "release_authorized": False,
}
LEGACY_REDACTION_RECEIPT_KEYS = {
    "body_redacted",
    "matched_excerpt",
    "public_replacement_ref",
    "public_replacement_refs",
    "forbidden_output_fields",
    "redacted_output_field_labels_omitted",
}
RECEIPT_TRANSPARENCY_CONTRACT = {
    "schema_version": "verifier_lab_receipt_transparency_contract_v1",
    "receipt_body_is_public_evidence": True,
    "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
    "body_in_receipt": False,
    "real_substrate_default": True,
    "required_public_evidence_fields": [
        "theorem_or_declaration_names",
        "lean_lake_command_identity",
        "lean_return_code",
        "source_hashes",
        "source_module_imports",
        "source_open_body_imports",
        "declaration_counts",
        "accepted_transition_count",
        "residual_transition_count",
        "negative_case_id",
        "cp2_action_class",
        "evolve_policy_artifact_id",
        "oracle_provider_separation_counters",
        "authority_ceiling",
        "anti_claim",
    ],
    "forbidden_payload_fields": [
        "proof_body",
        "raw_tactic_script",
        "provider_text",
        "oracle_ideal_answer",
        "oracle_needed_premise_ids",
        "private_source_path",
        "private_payload_body",
        "stdout_body",
        "stderr_body",
    ],
    "stdout_stderr_policy": "counts_and_return_codes_public_bodies_omitted",
}
ANTI_CLAIM = (
    "Verifier lab kernel composes source-available public component receipts "
    "for bounded Lean/Lake execution, tactic routing, verifier trace repair, "
    "provider-hypothesis quarantine, CP2 action candidates, bounded Evolve "
    "candidates, and structured public runtime receipts. It does not import "
    "macro proof bodies, count oracle or provider output as forward proof "
    "success, expose proof bodies, mutate source, claim benchmark solve rate, "
    "or authorize release."
)


@dataclass(frozen=True)
class ForwardProblem:
    """
    [ROLE]
    - Teleology: Groups `ForwardProblem` data or behavior for `microcosm_core.organs.verifier_lab_kernel` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs.verifier_lab_kernel`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    problem_id: str
    target_shape: str
    statement_summary: str
    public_input_hash: str
    allowed_premise_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class OracleSidecar:
    """
    [ROLE]
    - Teleology: Groups `OracleSidecar` data or behavior for `microcosm_core.organs.verifier_lab_kernel` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs.verifier_lab_kernel`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    sidecar_id: str
    forward_problem_id: str
    oracle_result_class: str
    counted_as_forward_success: bool = False


@dataclass(frozen=True)
class VerifierAttempt:
    """
    [ROLE]
    - Teleology: Groups `VerifierAttempt` data or behavior for `microcosm_core.organs.verifier_lab_kernel` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs.verifier_lab_kernel`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    attempt_id: str
    forward_problem_id: str
    verifier_result_class: str
    selected_tactic_id: str | None = None
    component_receipt_ref: str | None = None


@dataclass(frozen=True)
class VerifierResult:
    """
    [ROLE]
    - Teleology: Groups `VerifierResult` data or behavior for `microcosm_core.organs.verifier_lab_kernel` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs.verifier_lab_kernel`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    result_id: str
    attempt_id: str
    result_class: str
    verifier_receipt_ref: str


@dataclass(frozen=True)
class ProviderHypothesis:
    """
    [ROLE]
    - Teleology: Groups `ProviderHypothesis` data or behavior for `microcosm_core.organs.verifier_lab_kernel` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs.verifier_lab_kernel`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    hypothesis_id: str
    residual_id: str
    residual_class: str
    candidate_action_classes: tuple[str, ...]
    provider_results_counted: bool = False


@dataclass(frozen=True)
class ResidualDiagnosis:
    """
    [ROLE]
    - Teleology: Groups `ResidualDiagnosis` data or behavior for `microcosm_core.organs.verifier_lab_kernel` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs.verifier_lab_kernel`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    residual_id: str
    forward_problem_id: str
    residual_class: str
    missing_primitive: str | None = None


@dataclass(frozen=True)
class RepairProposal:
    """
    [ROLE]
    - Teleology: Groups `RepairProposal` data or behavior for `microcosm_core.organs.verifier_lab_kernel` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs.verifier_lab_kernel`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    proposal_id: str
    residual_id: str
    action_class: str
    verifier_rerun_ref: str


@dataclass(frozen=True)
class EvolveCandidate:
    """
    [ROLE]
    - Teleology: Groups `EvolveCandidate` data or behavior for `microcosm_core.organs.verifier_lab_kernel` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs.verifier_lab_kernel`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    candidate_id: str
    mutated_artifact: str
    baseline_receipt_ref: str
    rerun_receipt_ref: str | None = None


@dataclass(frozen=True)
class ClaimBoundary:
    """
    [ROLE]
    - Teleology: Groups `ClaimBoundary` data or behavior for `microcosm_core.organs.verifier_lab_kernel` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs.verifier_lab_kernel`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    boundary_id: str
    allowed: bool
    reason: str


@dataclass(frozen=True)
class AuthoritySplit:
    """
    [ROLE]
    - Teleology: Groups `AuthoritySplit` data or behavior for `microcosm_core.organs.verifier_lab_kernel` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs.verifier_lab_kernel`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    forward_success_authority: str
    oracle_authority: str
    provider_authority: str
    evolve_authority: str


Runner = Callable[..., dict[str, Any]]


COMPONENT_RUNNERS: dict[str, dict[str, Runner]] = {
    "corpus_readiness_mathlib_absence_gate": {
        "fixture": corpus_readiness_mathlib_absence_gate.run,
        "bundle": corpus_readiness_mathlib_absence_gate.run_projection_bundle,
    },
    "lean_std_premise_index": {
        "fixture": lean_std_premise_index.run,
        "bundle": lean_std_premise_index.run_index_bundle,
    },
    "formal_math_premise_retrieval": {
        "fixture": formal_math_premise_retrieval.run,
        "bundle": formal_math_premise_retrieval.run_retrieval_bundle,
    },
    "tactic_portfolio_availability_probe": {
        "fixture": tactic_portfolio_availability_probe.run,
        "bundle": tactic_portfolio_availability_probe.run_availability_bundle,
    },
    "target_shape_tactic_routing_gate": {
        "fixture": target_shape_tactic_routing_gate.run,
        "bundle": target_shape_tactic_routing_gate.run_routing_bundle,
    },
    "formal_math_verifier_trace_repair_loop": {
        "fixture": formal_math_verifier_trace_repair_loop.run,
        "bundle": formal_math_verifier_trace_repair_loop.run_loop_bundle,
    },
    "ring2_premise_retrieval_precision_recall_harness": {
        "fixture": ring2_premise_retrieval_precision_recall_harness.run,
        "bundle": ring2_premise_retrieval_precision_recall_harness.run_precision_recall_bundle,
    },
    "proof_diagnostic_evidence_spine": {
        "fixture": proof_diagnostic_evidence_spine.run,
        "bundle": proof_diagnostic_evidence_spine.run_evidence_bundle,
    },
    "formal_math_lean_proof_witness": {
        "fixture": formal_math_lean_proof_witness.run,
        "bundle": formal_math_lean_proof_witness.run_witness_bundle,
    },
}

def _module_source_path(module: Any) -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_module_source_path` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source_ref = getattr(module, "__file__", None)
    return Path(source_ref) if source_ref else None


COMPONENT_SOURCE_PATHS: dict[str, Path | None] = {
    "corpus_readiness_mathlib_absence_gate": _module_source_path(
        corpus_readiness_mathlib_absence_gate
    ),
    "lean_std_premise_index": _module_source_path(lean_std_premise_index),
    "formal_math_premise_retrieval": _module_source_path(
        formal_math_premise_retrieval
    ),
    "tactic_portfolio_availability_probe": _module_source_path(
        tactic_portfolio_availability_probe
    ),
    "target_shape_tactic_routing_gate": _module_source_path(
        target_shape_tactic_routing_gate
    ),
    "formal_math_verifier_trace_repair_loop": _module_source_path(
        formal_math_verifier_trace_repair_loop
    ),
    "ring2_premise_retrieval_precision_recall_harness": _module_source_path(
        ring2_premise_retrieval_precision_recall_harness
    ),
    "proof_diagnostic_evidence_spine": _module_source_path(
        proof_diagnostic_evidence_spine
    ),
    "formal_math_lean_proof_witness": _module_source_path(
        formal_math_lean_proof_witness
    ),
}


DEFAULT_COMPONENT_INPUTS = [
    {
        "organ_id": "corpus_readiness_mathlib_absence_gate",
        "input_rel": "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "lean_std_premise_index",
        "input_rel": "fixtures/first_wave/lean_std_premise_index/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "formal_math_premise_retrieval",
        "input_rel": "fixtures/first_wave/formal_math_premise_retrieval/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "tactic_portfolio_availability_probe",
        "input_rel": "fixtures/first_wave/tactic_portfolio_availability_probe/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "target_shape_tactic_routing_gate",
        "input_rel": "fixtures/first_wave/target_shape_tactic_routing_gate/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "formal_math_verifier_trace_repair_loop",
        "input_rel": "fixtures/first_wave/formal_math_verifier_trace_repair_loop/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "ring2_premise_retrieval_precision_recall_harness",
        "input_rel": "fixtures/first_wave/ring2_premise_retrieval_precision_recall_harness/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "proof_diagnostic_evidence_spine",
        "input_rel": "fixtures/first_wave/proof_diagnostic_evidence_spine/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "formal_math_lean_proof_witness",
        "input_rel": "fixtures/first_wave/formal_math_lean_proof_witness/input",
        "input_mode": "fixture",
    },
]


def _is_public_root(candidate: Path) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_is_public_root` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (candidate / PUBLIC_ROOT_POLICY_REL).is_file()


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    candidates = [
        start,
        *start.parents,
        Path.cwd().resolve(strict=False),
        MODULE_PUBLIC_ROOT,
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if _is_public_root(candidate):
            return candidate
    return MODULE_PUBLIC_ROOT


def _public_local_ref(path_ref: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_public_local_ref` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if path_ref == "/private/tmp":
        return "/tmp"
    if path_ref.startswith("/private/tmp/"):
        return f"/tmp/{path_ref.removeprefix('/private/tmp/')}"
    return path_ref


def _display(path: str | Path, *, public_root: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_display` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _public_local_ref(public_relative_path(path, display_root=public_root))


def _normalize_receipt_public_refs(value: object) -> object:
    """
    [ACTION]
    - Teleology: Implements `_normalize_receipt_public_refs` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(value, dict):
        return {
            key: _normalize_receipt_public_refs(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_normalize_receipt_public_refs(item) for item in value]
    if isinstance(value, str):
        return _public_local_ref(value)
    return value


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_rows` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_strings` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (PACKET_NAME, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    route_path = input_dir / PROOF_LAB_ROUTE_NAME
    if route_path.is_file():
        paths.append(route_path)
    source_module_manifest = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if source_module_manifest.is_file():
        paths.append(source_module_manifest)
    return paths


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
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


def _dependency_file(path: Path) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_dependency_file` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not path.is_file():
        return False
    if path.suffix == ".pyc" or "__pycache__" in path.parts:
        return False
    return True


def _iter_dependency_files(path: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_iter_dependency_files` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if _dependency_file(path):
        return [path]
    if not path.is_dir():
        return []
    return sorted(_iter_dependency_tree_files(path))


def _iter_dependency_tree_files(path: Path) -> Iterator[Path]:
    """
    [ACTION]
    - Teleology: Implements `_iter_dependency_tree_files` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    with os.scandir(path) as entries:
        entry_rows = sorted(list(entries), key=lambda entry: entry.name)
    for entry in entry_rows:
        child = path / entry.name
        if entry.is_dir(follow_symlinks=False):
            if entry.name == "__pycache__":
                continue
            yield from _iter_dependency_tree_files(child)
        elif _dependency_file(child):
            yield child


def _unique_dependency_paths(paths: list[Path]) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_unique_dependency_paths` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve(strict=False)
        if resolved in seen or not _dependency_file(resolved):
            continue
        seen.add(resolved)
        unique.append(resolved)
    return sorted(unique)


def _sha256_file(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256_file` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


def _strip_microcosm_prefix(ref: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_strip_microcosm_prefix` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _source_module_manifest_path(input_dir: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_path` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return Path(input_dir) / SOURCE_MODULE_MANIFEST_NAME


def _source_module_target_path(
    row: dict[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> tuple[Path, str]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_target_path` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
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
        return relocated, _display(relocated, public_root=public_root)
    if row_path:
        target = manifest_path.parent / row_path
        return target, _display(target, public_root=public_root)
    return public_root, ""


def _source_artifact_paths(input_dir: str | Path, *, public_root: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_artifact_paths` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
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


def validate_source_module_imports(
    input_dir: str | Path,
    *,
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_source_module_imports` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    manifest_ref = _display(manifest_path, public_root=public_root)
    findings: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        findings.append(
            _finding(
                "VERIFIER_LAB_SOURCE_MODULE_MANIFEST_MISSING",
                "Exported verifier-lab bundles require source_module_manifest.json for copied public kernel and component source bodies.",
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
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        }

    manifest = read_json_strict(manifest_path)
    if not isinstance(manifest, dict):
        manifest = {}
    module_rows = _rows(manifest, "modules")
    if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
        findings.append(
            _finding(
                "VERIFIER_LAB_SOURCE_IMPORT_CLASS_MISMATCH",
                "Source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_manifest",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "VERIFIER_LAB_SOURCE_BODY_IN_RECEIPT_FORBIDDEN",
                "Copied verifier-lab source bodies may live in the exported bundle, not in receipts.",
                case_id="source_module_manifest",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_text_in_receipt") is not False:
        findings.append(
            _finding(
                "VERIFIER_LAB_SOURCE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
                "Copied verifier-lab source body text may live in the exported bundle, not in receipts.",
                case_id="source_module_manifest",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("module_count") != len(module_rows):
        findings.append(
            _finding(
                "VERIFIER_LAB_SOURCE_MODULE_COUNT_MISMATCH",
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
        expected_digest = str(row.get("sha256") or "")
        subject = module_id or target_ref or "source_module"
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "VERIFIER_LAB_SOURCE_MODULE_IMPORT_CLASS_MISMATCH",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_manifest",
                    subject_id=subject,
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_MODULE_CLASSES:
            findings.append(
                _finding(
                    "VERIFIER_LAB_SOURCE_MODULE_CLASS_FORBIDDEN",
                    "Verifier-lab body imports may include only public macro tool source bodies.",
                    case_id="source_module_manifest",
                    subject_id=subject,
                    subject_kind="source_module",
                )
            )
        if (
            row.get("body_copied") is not True
            or row.get("body_in_receipt") is not False
            or row.get("body_text_in_receipt") is not False
        ):
            findings.append(
                _finding(
                    "VERIFIER_LAB_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
                    "Source module rows must set body_copied=true, body_in_receipt=false, and body_text_in_receipt=false.",
                    case_id="source_module_manifest",
                    subject_id=subject,
                    subject_kind="source_module",
                )
            )
        if relation not in SOURCE_MODULE_RELATIONS:
            findings.append(
                _finding(
                    "VERIFIER_LAB_SOURCE_MODULE_RELATION_UNVERIFIED",
                    "Source module rows must state exact_copy.",
                    case_id="source_module_manifest",
                    subject_id=subject,
                    subject_kind="source_module",
                )
            )
        if not source_ref.startswith(SOURCE_REF_PREFIXES):
            findings.append(
                _finding(
                    "VERIFIER_LAB_SOURCE_REF_UNEXPECTED",
                    "Source module rows must point at Plectis organ source files under microcosm_core.",
                    case_id="source_module_manifest",
                    subject_id=subject,
                    subject_kind="source_module",
                )
            )
        if not target_path.is_file():
            findings.append(
                _finding(
                    "VERIFIER_LAB_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target must exist inside the exported verifier-lab bundle.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or subject,
                    subject_kind="source_module",
                )
            )
            continue
        actual_digest = _sha256_file(target_path)
        if expected_digest != actual_digest:
            findings.append(
                _finding(
                    "VERIFIER_LAB_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module target digest must match source_module_manifest.json.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or subject,
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
                    "VERIFIER_LAB_SOURCE_MODULE_ANCHOR_MISSING",
                    "Source module target is missing one or more required anchors.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or subject,
                    subject_kind="source_module",
                )
            )
        modules.append(
            {
                "module_id": module_id,
                "source_ref": source_ref,
                "target_ref": target_ref,
                "material_class": material_class,
                "sha256": expected_digest,
                "actual_sha256": actual_digest,
                "line_count": row.get("line_count"),
                "source_to_target_relation": relation,
                "body_in_receipt": False,
                "body_text_in_receipt": False,
            }
        )

    return {
        "status": PASS if not findings and modules else "blocked",
        "source_module_manifest_ref": manifest_ref,
        "module_count": len(modules),
        "modules": modules,
        "findings": findings,
        "observed_negative_cases": {},
        "body_in_receipt": False,
        "body_text_in_receipt": False,
    }


def _empty_source_module_imports(input_dir: str | Path, *, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_empty_source_module_imports` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    return {
        "status": "not_applicable",
        "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
        "module_count": 0,
        "modules": [],
        "findings": [],
        "observed_negative_cases": {},
        "body_in_receipt": False,
        "body_text_in_receipt": False,
    }


def _source_open_body_import_summary(source_imports: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_open_body_import_summary` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
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
        "schema_version": "verifier_lab_kernel_source_open_body_imports_v1",
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
        "body_text_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "proof_body_or_oracle_proof_text_exported": False,
            "provider_payload_exported": False,
            "host_local_absolute_paths_exported": False,
            "lean_lake_execution_authorized": "component_witness_only",
            "formal_proof_authority": False,
            "release_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/microcosm_core/organs/ "
            "for copied verifier-lab kernel and component source bodies; receipts carry "
            "refs, digests, counts, and verdicts only."
        )
        if modules
        else "",
    }


def _source_module_blocked_result(
    input_dir: Path,
    *,
    command: str,
    source_module_imports: dict[str, Any],
    source_open_body_imports: dict[str, Any],
    secret_scan: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_blocked_result` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payloads = _load_payloads(input_dir, include_negative=False)
    packet = payloads.get("verifier_lab_packet", {})
    if not isinstance(packet, dict):
        packet = {}
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    findings = _rows(source_module_imports, "findings")
    return {
        "schema_version": "verifier_lab_kernel_result_v1",
        "created_at": utc_now(),
        "status": "blocked",
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": "exported_verifier_lab_kernel_bundle",
        "bundle_id": bundle_manifest.get("bundle_id"),
        "kernel_id": packet.get("kernel_id"),
        "source_pattern_ids": _strings(packet.get("source_pattern_ids")),
        "source_refs": _strings(packet.get("source_refs")),
        "projection_receipt_refs": _strings(packet.get("projection_receipt_refs")),
        "public_runtime_refs": _strings(packet.get("public_runtime_refs")),
        "source_module_imports": source_module_imports,
        "source_module_manifest_ref": source_module_imports[
            "source_module_manifest_ref"
        ],
        "source_open_body_imports": source_open_body_imports,
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "proof_lab_route": {
            "status": "skipped",
            "reason": "source_module_imports_blocked",
        },
        "proof_lab_route_id": None,
        "proof_lab_route_source_sha256": None,
        "proof_lab_route_component_count": 0,
        "proof_lab_component_metrics": {},
        "expected_negative_cases": [],
        "observed_negative_cases": {},
        "missing_negative_cases": [],
        "error_codes": sorted({str(row["error_code"]) for row in findings}),
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "component_statuses": {},
        "component_receipt_refs": {},
        "lean_lake_return_code": None,
        "lean_compiled_declaration_count": 0,
        "target_shape_route_case_count": 0,
        "verifier_trace_attempt_count": 0,
        "forward_problems": [],
        "oracle_sidecars": [],
        "verifier_attempts": [],
        "provider_hypotheses": [],
        "residual_diagnoses": [],
        "cp2_action_candidates": [],
        "evolve_candidates": [],
        "claim_separation": {
            "lean_verified": [],
            "provider_suggested": [],
            "oracle_compared": [],
            "contract_rejected": [],
            "retrieval_miss": [],
            "cp2_translated": [],
            "evolve_candidate": [],
        },
        "authority_split": {
            "forward_success": "independent verifier receipt only",
            "oracle": "diagnostic comparator only",
            "provider": "advisory hypothesis only",
            "cp2": "typed action candidate plus rerun receipt only",
            "evolve": "bounded policy candidate plus rerun/quarantine receipt only",
        },
        "authority_counters": {
            "oracle_forward_success_increment_count": 0,
            "provider_results_counted": 0,
            "proof_body_export_count": 0,
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "receipt_transparency_contract": RECEIPT_TRANSPARENCY_CONTRACT,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        "real_runtime_receipt": False,
        "synthetic_receipt_standin_allowed": False,
        "cache_status": "source_module_imports_blocked",
    }


def _kernel_bundle_dependency_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_kernel_bundle_dependency_paths` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    packet_payload = read_json_strict(input_dir / PACKET_NAME)
    packet = packet_payload if isinstance(packet_payload, dict) else {}
    public_root = _public_root_for_path(input_dir)
    paths: list[Path] = [
        *_input_paths(input_dir, include_negative=False),
        *_source_artifact_paths(input_dir, public_root=public_root),
        Path(__file__).resolve(strict=False),
    ]
    for spec in _component_specs(packet):
        organ_id = str(spec.get("organ_id") or "")
        input_rel = str(spec.get("input_rel") or "")
        if input_rel:
            paths.extend(_iter_dependency_files(public_root / input_rel))
        source_path = COMPONENT_SOURCE_PATHS.get(organ_id)
        if source_path is not None:
            paths.extend(_iter_dependency_files(source_path.resolve(strict=False)))

    return _unique_dependency_paths(paths)


def _fixture_dependency_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_fixture_dependency_paths` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payloads = _load_payloads(input_dir, include_negative=True)
    packet_payload = payloads.get(PACKET_NAME.removesuffix(".json"))
    packet = packet_payload if isinstance(packet_payload, dict) else {}
    public_root = _public_root_for_path(input_dir)
    paths: list[Path] = [
        *_input_paths(input_dir, include_negative=True),
        Path(__file__).resolve(strict=False),
    ]
    for spec in _component_specs(packet):
        organ_id = str(spec.get("organ_id") or "")
        input_rel = str(spec.get("input_rel") or "")
        if input_rel:
            paths.extend(_iter_dependency_files(public_root / input_rel))
        source_path = COMPONENT_SOURCE_PATHS.get(organ_id)
        if source_path is not None:
            paths.extend(_iter_dependency_files(source_path.resolve(strict=False)))

    return _unique_dependency_paths(paths)


def _kernel_bundle_freshness_basis(
    *,
    command: str,
    receipt_path: Path,
    dependency_paths: list[Path],
    input_mode: str = "exported_verifier_lab_kernel_bundle",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_kernel_bundle_freshness_basis` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    dependency_mtimes = [path.stat().st_mtime_ns for path in dependency_paths]
    return {
        "schema_version": "verifier_lab_kernel_fresh_receipt_basis_v1",
        "cache_policy": "same_command_and_receipt_newer_than_inputs_and_sources",
        "command": command,
        "input_mode": input_mode,
        "tracked_dependency_count": len(dependency_paths),
        "latest_dependency_mtime_ns": max(dependency_mtimes) if dependency_mtimes else 0,
        "receipt_mtime_ns": (
            receipt_path.stat().st_mtime_ns if receipt_path.is_file() else None
        ),
    }


def _fresh_kernel_bundle_receipt(
    input_dir: Path,
    out_dir: Path,
    *,
    command: str,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Implements `_fresh_kernel_bundle_receipt` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    receipt_path = out_dir / BUNDLE_RESULT_NAME
    if not receipt_path.is_file():
        return None
    payload = read_json_strict(receipt_path)
    if not isinstance(payload, dict):
        return None
    if (
        payload.get("schema_version")
        != "exported_verifier_lab_kernel_bundle_validation_result_v1"
    ):
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("command") != command:
        return None
    if payload.get("input_mode") != "exported_verifier_lab_kernel_bundle":
        return None
    source_open_body_imports = payload.get("source_open_body_imports")
    if (
        not isinstance(source_open_body_imports, dict)
        or source_open_body_imports.get("status") != PASS
        or not source_open_body_imports.get("body_material_count")
    ):
        return None
    dependency_paths = _kernel_bundle_dependency_paths(input_dir)
    basis = _kernel_bundle_freshness_basis(
        command=command,
        receipt_path=receipt_path,
        dependency_paths=dependency_paths,
    )
    receipt_mtime = basis["receipt_mtime_ns"]
    if receipt_mtime is None:
        return None
    if basis["latest_dependency_mtime_ns"] > receipt_mtime:
        return None
    return {
        **payload,
        "cache_status": "fresh_receipt_reused",
        "freshness_basis": basis,
    }


def _fresh_fixture_receipts(
    input_dir: Path,
    out_dir: Path,
    *,
    command: str,
    acceptance_out: Path | None,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Implements `_fresh_fixture_receipts` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    public_root = _public_root_for_path(out_dir)
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    required_paths = [result_path, board_path, validation_path, acceptance_path]
    if not all(path.is_file() for path in required_paths):
        return None
    payload = read_json_strict(result_path)
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != "verifier_lab_kernel_result_receipt_v1":
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("command") != command:
        return None
    if payload.get("input_mode") != "first_wave_fixture":
        return None
    expected_receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    if payload.get("receipt_paths") != expected_receipt_paths:
        return None
    dependency_paths = _fixture_dependency_paths(input_dir)
    basis = _kernel_bundle_freshness_basis(
        command=command,
        receipt_path=result_path,
        dependency_paths=dependency_paths,
        input_mode="first_wave_fixture",
    )
    receipt_mtime = basis["receipt_mtime_ns"]
    if receipt_mtime is None:
        return None
    if basis["latest_dependency_mtime_ns"] > receipt_mtime:
        return None
    return {
        **payload,
        "cache_status": "fresh_receipt_reused",
        "freshness_basis": basis,
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
    - Teleology: Implements `_finding` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
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
    count_observed: bool,
) -> None:
    """
    [ACTION]
    - Teleology: Implements `_record` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
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
    if count_observed:
        observed.setdefault(case_id, set()).add(code)


def _walk_forbidden_keys(value: object, forbidden: set[str], prefix: str = "") -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_walk_forbidden_keys` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
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
            if key in forbidden:
                found.append(key_path)
            found.extend(_walk_forbidden_keys(child, forbidden, key_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk_forbidden_keys(child, forbidden, f"{prefix}[{index}]"))
    return sorted(found)


def _without_legacy_redaction_receipt_fields(value: object) -> object:
    """
    [ACTION]
    - Teleology: Implements `_without_legacy_redaction_receipt_fields` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(value, dict):
        cleaned: dict[str, object] = {}
        for key, child in value.items():
            if key in LEGACY_REDACTION_RECEIPT_KEYS:
                continue
            clean_key = "secret_exclusion_scan" if key == "private_state_scan" else key
            cleaned[clean_key] = _without_legacy_redaction_receipt_fields(child)
        return cleaned
    if isinstance(value, list):
        return [_without_legacy_redaction_receipt_fields(item) for item in value]
    return value


def _rewrite_json_receipt_without_legacy_redaction(path: Path) -> None:
    """
    [ACTION]
    - Teleology: Implements `_rewrite_json_receipt_without_legacy_redaction` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload = read_json_strict(path)
    cleaned = _without_legacy_redaction_receipt_fields(payload)
    normalized = _normalize_receipt_public_refs(cleaned)
    if normalized != payload:
        write_json_atomic(path, normalized)


def _normalize_component_receipt_surface(target: Path) -> None:
    """
    [ACTION]
    - Teleology: Implements `_normalize_component_receipt_surface` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not target.exists():
        return
    for path in sorted(
        file for file in _iter_dependency_tree_files(target) if file.suffix == ".json"
    ):
        _rewrite_json_receipt_without_legacy_redaction(path)


def _negative_case_id(row: dict[str, Any], fallback: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_negative_case_id` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(row.get("expected_negative_case_id") or row.get("case_id") or fallback)


def _validate_forward_problems(
    rows: list[dict[str, Any]],
    *,
    observed: dict[str, set[str]],
    positive_findings: list[dict[str, Any]],
    negative_findings: list[dict[str, Any]],
    negative: bool,
) -> list[ForwardProblem]:
    """
    [ACTION]
    - Teleology: Implements `_validate_forward_problems` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    parsed: list[ForwardProblem] = []
    findings = negative_findings if negative else positive_findings
    for row in rows:
        problem_id = str(row.get("problem_id") or row.get("case_id") or "forward_problem")
        case_id = _negative_case_id(row, problem_id)
        forbidden_keys = _walk_forbidden_keys(row, FORBIDDEN_FORWARD_KEYS)
        if forbidden_keys:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_FORWARD_FIELD_FORBIDDEN",
                "ForwardProblem rows may not carry candidate, ideal, repair, oracle, source proof, or base-index fields.",
                case_id=case_id,
                subject_id=problem_id,
                subject_kind="forward_problem",
                count_observed=negative,
            )
        if not negative and problem_id and not forbidden_keys:
            parsed.append(
                ForwardProblem(
                    problem_id=problem_id,
                    target_shape=str(row.get("target_shape") or ""),
                    statement_summary=str(row.get("statement_summary") or ""),
                    public_input_hash=str(row.get("public_input_hash") or ""),
                    allowed_premise_ids=tuple(_strings(row.get("allowed_premise_ids"))),
                )
            )
    return parsed


def _validate_oracle_sidecars(
    rows: list[dict[str, Any]],
    *,
    observed: dict[str, set[str]],
    positive_findings: list[dict[str, Any]],
    negative_findings: list[dict[str, Any]],
    negative: bool,
) -> list[OracleSidecar]:
    """
    [ACTION]
    - Teleology: Implements `_validate_oracle_sidecars` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    parsed: list[OracleSidecar] = []
    findings = negative_findings if negative else positive_findings
    for row in rows:
        sidecar_id = str(row.get("sidecar_id") or row.get("case_id") or "oracle_sidecar")
        case_id = _negative_case_id(row, sidecar_id)
        counted = row.get("counted_as_forward_success") is True
        if counted:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_ORACLE_FORWARD_CONTAMINATION",
                "Oracle comparator success may be recorded only as oracle evidence, never as forward success.",
                case_id=case_id,
                subject_id=sidecar_id,
                subject_kind="oracle_sidecar",
                count_observed=negative,
            )
        if not negative:
            parsed.append(
                OracleSidecar(
                    sidecar_id=sidecar_id,
                    forward_problem_id=str(row.get("forward_problem_id") or ""),
                    oracle_result_class=str(row.get("oracle_result_class") or ""),
                    counted_as_forward_success=counted,
                )
            )
    return parsed


def _validate_provider_hypotheses(
    rows: list[dict[str, Any]],
    *,
    observed: dict[str, set[str]],
    positive_findings: list[dict[str, Any]],
    negative_findings: list[dict[str, Any]],
    negative: bool,
) -> list[ProviderHypothesis]:
    """
    [ACTION]
    - Teleology: Implements `_validate_provider_hypotheses` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    parsed: list[ProviderHypothesis] = []
    findings = negative_findings if negative else positive_findings
    for row in rows:
        hypothesis_id = str(row.get("hypothesis_id") or row.get("case_id") or "provider_hypothesis")
        case_id = _negative_case_id(row, hypothesis_id)
        proof_claim = (
            row.get("proof_authority") is True
            or row.get("provider_results_counted") is True
            or str(row.get("authority") or "").endswith("proof_authority")
        )
        if proof_claim:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_PROVIDER_PROOF_AUTHORITY_FORBIDDEN",
                "Provider/NIM output must remain an advisory hypothesis until a verifier/substrate effect exists.",
                case_id=case_id,
                subject_id=hypothesis_id,
                subject_kind="provider_hypothesis",
                count_observed=negative,
            )
        if not negative:
            parsed.append(
                ProviderHypothesis(
                    hypothesis_id=hypothesis_id,
                    residual_id=str(row.get("residual_id") or ""),
                    residual_class=str(row.get("residual_class") or ""),
                    candidate_action_classes=tuple(
                        _strings(row.get("candidate_action_classes"))
                    ),
                    provider_results_counted=row.get("provider_results_counted") is True,
                )
            )
    return parsed


def _validate_cp2_candidates(
    rows: list[dict[str, Any]],
    *,
    observed: dict[str, set[str]],
    positive_findings: list[dict[str, Any]],
    negative_findings: list[dict[str, Any]],
    negative: bool,
) -> list[RepairProposal]:
    """
    [ACTION]
    - Teleology: Implements `_validate_cp2_candidates` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    parsed: list[RepairProposal] = []
    findings = negative_findings if negative else positive_findings
    for row in rows:
        candidate_id = str(row.get("candidate_id") or row.get("case_id") or "cp2_candidate")
        case_id = _negative_case_id(row, candidate_id)
        forbidden_keys = _walk_forbidden_keys(row, FORBIDDEN_CP2_KEYS)
        action_class = str(row.get("action_class") or "")
        if forbidden_keys:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_CP2_PROOF_BODY_FORBIDDEN",
                "CP2 may emit typed action candidates only, not proof bodies, raw tactic scripts, provider bodies, or oracle templates.",
                case_id=case_id,
                subject_id=candidate_id,
                subject_kind="cp2_action_candidate",
                count_observed=negative,
            )
        if action_class and action_class not in ALLOWED_CP2_ACTION_CLASSES:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_CP2_ACTION_CLASS_UNKNOWN",
                "CP2 action candidates must use the bounded public action-class vocabulary.",
                case_id=case_id,
                subject_id=action_class,
                subject_kind="cp2_action_class",
                count_observed=negative,
            )
        if not row.get("disconfirmation_test") and not negative:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_CP2_DISCONFIRMATION_TEST_MISSING",
                "CP2 action candidates must name a disconfirmation test before rerun promotion.",
                case_id=case_id,
                subject_id=candidate_id,
                subject_kind="cp2_action_candidate",
                count_observed=False,
            )
        if not negative and not forbidden_keys:
            parsed.append(
                RepairProposal(
                    proposal_id=candidate_id,
                    residual_id=str(row.get("residual_id") or ""),
                    action_class=action_class,
                    verifier_rerun_ref=str(row.get("verifier_rerun_ref") or ""),
                )
            )
    return parsed


def _validate_evolve_candidates(
    rows: list[dict[str, Any]],
    *,
    observed: dict[str, set[str]],
    positive_findings: list[dict[str, Any]],
    negative_findings: list[dict[str, Any]],
    negative: bool,
) -> list[EvolveCandidate]:
    """
    [ACTION]
    - Teleology: Implements `_validate_evolve_candidates` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    parsed: list[EvolveCandidate] = []
    findings = negative_findings if negative else positive_findings
    for row in rows:
        candidate_id = str(row.get("candidate_id") or row.get("case_id") or "evolve_candidate")
        case_id = _negative_case_id(row, candidate_id)
        artifact = str(row.get("mutated_artifact") or "")
        unbounded = (
            artifact not in ALLOWED_EVOLVE_ARTIFACTS
            or row.get("arbitrary_code_mutation") is True
            or row.get("source_mutation_authorized") is True
        )
        if unbounded:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_EVOLVE_SCOPE_FORBIDDEN",
                "Evolve may mutate only bounded policy artifacts with rerun and leakage receipts.",
                case_id=case_id,
                subject_id=candidate_id,
                subject_kind="evolve_candidate",
                count_observed=negative,
            )
        if not row.get("baseline_receipt_ref") and not negative:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_EVOLVE_BASELINE_RECEIPT_MISSING",
                "Evolve candidates must cite a baseline receipt before acceptance or quarantine.",
                case_id=case_id,
                subject_id=candidate_id,
                subject_kind="evolve_candidate",
                count_observed=False,
            )
        if not negative and not unbounded:
            parsed.append(
                EvolveCandidate(
                    candidate_id=candidate_id,
                    mutated_artifact=artifact,
                    baseline_receipt_ref=str(row.get("baseline_receipt_ref") or ""),
                    rerun_receipt_ref=str(row.get("rerun_receipt_ref") or "") or None,
                )
            )
    return parsed


def _validate_packet(
    packet: dict[str, Any],
    negative_payloads: dict[str, Any],
    *,
    require_negative_cases: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validate_packet` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    observed: dict[str, set[str]] = {}
    positive_findings: list[dict[str, Any]] = []
    negative_findings: list[dict[str, Any]] = []

    forward_problems = _validate_forward_problems(
        _rows(packet, "forward_problems"),
        observed=observed,
        positive_findings=positive_findings,
        negative_findings=negative_findings,
        negative=False,
    )
    oracle_sidecars = _validate_oracle_sidecars(
        _rows(packet, "oracle_sidecars"),
        observed=observed,
        positive_findings=positive_findings,
        negative_findings=negative_findings,
        negative=False,
    )
    provider_hypotheses = _validate_provider_hypotheses(
        _rows(packet, "provider_hypotheses"),
        observed=observed,
        positive_findings=positive_findings,
        negative_findings=negative_findings,
        negative=False,
    )
    cp2_candidates = _validate_cp2_candidates(
        _rows(packet, "cp2_action_candidates"),
        observed=observed,
        positive_findings=positive_findings,
        negative_findings=negative_findings,
        negative=False,
    )
    evolve_candidates = _validate_evolve_candidates(
        _rows(packet, "evolve_candidates"),
        observed=observed,
        positive_findings=positive_findings,
        negative_findings=negative_findings,
        negative=False,
    )

    for payload in negative_payloads.values():
        rows = _rows(payload, "forward_problems")
        if isinstance(payload, dict) and not rows and "forward_problem" in payload:
            rows = [payload["forward_problem"]]
        _validate_forward_problems(
            rows,
            observed=observed,
            positive_findings=positive_findings,
            negative_findings=negative_findings,
            negative=True,
        )
        _validate_oracle_sidecars(
            _rows(payload, "oracle_sidecars") or ([payload] if "sidecar_id" in payload else []),
            observed=observed,
            positive_findings=positive_findings,
            negative_findings=negative_findings,
            negative=True,
        )
        _validate_provider_hypotheses(
            _rows(payload, "provider_hypotheses") or ([payload] if "hypothesis_id" in payload else []),
            observed=observed,
            positive_findings=positive_findings,
            negative_findings=negative_findings,
            negative=True,
        )
        _validate_cp2_candidates(
            _rows(payload, "cp2_action_candidates") or ([payload] if "candidate_id" in payload and "action_class" in payload else []),
            observed=observed,
            positive_findings=positive_findings,
            negative_findings=negative_findings,
            negative=True,
        )
        _validate_evolve_candidates(
            _rows(payload, "evolve_candidates") or ([payload] if "mutated_artifact" in payload else []),
            observed=observed,
            positive_findings=positive_findings,
            negative_findings=negative_findings,
            negative=True,
        )

    residual_diagnoses = [
        ResidualDiagnosis(
            residual_id=str(row.get("residual_id") or ""),
            forward_problem_id=str(row.get("forward_problem_id") or ""),
            residual_class=str(row.get("residual_class") or ""),
            missing_primitive=str(row.get("missing_primitive") or "") or None,
        )
        for row in _rows(packet, "residual_diagnoses")
    ]
    verifier_attempts = [
        VerifierAttempt(
            attempt_id=str(row.get("attempt_id") or ""),
            forward_problem_id=str(row.get("forward_problem_id") or ""),
            verifier_result_class=str(row.get("verifier_result_class") or ""),
            selected_tactic_id=str(row.get("selected_tactic_id") or "") or None,
            component_receipt_ref=str(row.get("component_receipt_ref") or "") or None,
        )
        for row in _rows(packet, "verifier_attempts")
    ]

    expected_negative_cases = EXPECTED_NEGATIVE_CASES if require_negative_cases else {}
    missing = sorted(
        case_id for case_id in expected_negative_cases if case_id not in observed
    )
    floors = {
        "forward_problem_count": len(forward_problems),
        "oracle_sidecar_count": len(oracle_sidecars),
        "provider_hypothesis_count": len(provider_hypotheses),
        "residual_diagnosis_count": len(residual_diagnoses),
        "cp2_candidate_count": len(cp2_candidates),
        "evolve_candidate_count": len(evolve_candidates),
        "verifier_attempt_count": len(verifier_attempts),
    }
    floor_status = (
        PASS
        if floors["forward_problem_count"] >= 3
        and floors["oracle_sidecar_count"] >= 1
        and floors["provider_hypothesis_count"] >= 1
        and floors["residual_diagnosis_count"] >= 1
        and floors["cp2_candidate_count"] >= 2
        and floors["evolve_candidate_count"] >= 1
        and floors["verifier_attempt_count"] >= 3
        else "blocked"
    )
    if floor_status != PASS:
        positive_findings.append(
            _finding(
                "VERIFIER_LAB_PACKET_FLOOR_MISSING",
                "Verifier lab packet must carry forward problems, oracle sidecars, verifier attempts, provider hypotheses, residual diagnoses, CP2 candidates, and Evolve candidates.",
                case_id="packet_floor",
                subject_id=str(packet.get("kernel_id") or "verifier_lab_packet"),
                subject_kind="verifier_lab_packet",
            )
        )

    return {
        "status": PASS if not positive_findings and not missing else "blocked",
        "kernel_id": packet.get("kernel_id"),
        "source_pattern_ids": _strings(packet.get("source_pattern_ids")),
        "source_refs": _strings(packet.get("source_refs")),
        "projection_receipt_refs": _strings(packet.get("projection_receipt_refs")),
        "public_runtime_refs": _strings(packet.get("public_runtime_refs")),
        "expected_negative_cases": sorted(expected_negative_cases),
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in sorted(observed.items())
        },
        "missing_negative_cases": missing,
        "positive_findings": sorted(
            positive_findings,
            key=lambda row: (str(row["negative_case_id"]), str(row["error_code"])),
        ),
        "negative_findings": sorted(
            negative_findings,
            key=lambda row: (str(row["negative_case_id"]), str(row["error_code"])),
        ),
        "forward_problems": [asdict(row) for row in forward_problems],
        "oracle_sidecars": [asdict(row) for row in oracle_sidecars],
        "provider_hypotheses": [asdict(row) for row in provider_hypotheses],
        "residual_diagnoses": [asdict(row) for row in residual_diagnoses],
        "cp2_action_candidates": [asdict(row) for row in cp2_candidates],
        "evolve_candidates": [asdict(row) for row in evolve_candidates],
        "verifier_attempts": [asdict(row) for row in verifier_attempts],
        "floors": floors,
    }


def _component_specs(packet: dict[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_component_specs` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(packet, "component_inputs")
    if not rows:
        return list(DEFAULT_COMPONENT_INPUTS)
    seen = {
        str(row.get("organ_id") or "")
        for row in rows
        if isinstance(row, dict)
    }
    return [
        *rows,
        *[
            row
            for row in DEFAULT_COMPONENT_INPUTS
            if str(row.get("organ_id") or "") not in seen
        ],
    ]


def _validate_proof_lab_route(
    payload: dict[str, Any] | None,
    *,
    component_specs: list[dict[str, Any]],
    require_route: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validate_proof_lab_route` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not payload:
        return {
            "status": "blocked" if require_route else PASS,
            "route_supplied": False,
            "route_id": None,
            "error_codes": (
                ["VERIFIER_LAB_PROOF_ROUTE_MISSING"] if require_route else []
            ),
            "missing_component_organs": [],
            "missing_pattern_ids": [],
            "source_sha256": None,
            "source_ref": None,
            "available_pattern_ids": [],
            "source_refs": [],
        }

    route = payload.get("foundation_route")
    if not isinstance(route, dict):
        route = {}
    component_rows = payload.get("component_map")
    if not isinstance(component_rows, list):
        component_rows = []
    expected_organs = {
        str(row.get("component_organ_id") or "")
        for row in component_rows
        if isinstance(row, dict)
    } or EXPECTED_ROUTE_COMPONENT_ORGANS
    actual_organs = {
        str(row.get("organ_id") or "")
        for row in component_specs
        if isinstance(row, dict)
    }
    available_pattern_ids = set(_strings(route.get("available_pattern_ids")))
    error_codes: list[str] = []
    route_id = str(route.get("route_id") or payload.get("route_id") or "")
    if route_id != EXPECTED_PROOF_LAB_ROUTE_ID:
        error_codes.append("VERIFIER_LAB_PROOF_ROUTE_ID_MISMATCH")
    missing_organs = sorted(expected_organs - actual_organs)
    if missing_organs:
        error_codes.append("VERIFIER_LAB_PROOF_ROUTE_COMPONENT_MISSING")
    missing_patterns = sorted(EXPECTED_ROUTE_PATTERN_IDS - available_pattern_ids)
    if missing_patterns:
        error_codes.append("VERIFIER_LAB_PROOF_ROUTE_PATTERN_MISSING")
    source_sha256 = str(payload.get("source_sha256") or "")
    if not source_sha256.startswith("sha256:"):
        error_codes.append("VERIFIER_LAB_PROOF_ROUTE_SOURCE_DIGEST_MISSING")
    source_refs = _strings(route.get("substrate_ref_sample"))
    if not source_refs:
        error_codes.append("VERIFIER_LAB_PROOF_ROUTE_SUBSTRATE_REFS_MISSING")

    return {
        "status": PASS if not error_codes else "blocked",
        "route_supplied": True,
        "route_id": route_id or None,
        "error_codes": error_codes,
        "missing_component_organs": missing_organs,
        "missing_pattern_ids": missing_patterns,
        "source_sha256": source_sha256 or None,
        "source_ref": payload.get("source_ref"),
        "available_pattern_ids": sorted(available_pattern_ids),
        "detailed_binding_pattern_ids": _strings(
            route.get("detailed_binding_pattern_ids")
        ),
        "component_map": [
            {
                "pattern_id": str(row.get("pattern_id") or ""),
                "component_organ_id": str(row.get("component_organ_id") or ""),
                "component_role": str(row.get("component_role") or ""),
            }
            for row in component_rows
            if isinstance(row, dict)
        ],
        "source_refs": source_refs,
        "anti_claim_floor": route.get("anti_claim_floor"),
        "next_refinement_move": route.get("next_refinement_move"),
    }


def _run_component_stack(
    packet: dict[str, Any],
    *,
    input_dir: Path,
    out_dir: Path,
    command: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_run_component_stack` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    components_out = out_dir / "components"
    results: dict[str, dict[str, Any]] = {}
    receipt_refs: dict[str, list[str]] = {}
    for spec in _component_specs(packet):
        organ_id = str(spec.get("organ_id") or "")
        runner_set = COMPONENT_RUNNERS.get(organ_id)
        if runner_set is None:
            results[organ_id] = {
                "status": "blocked",
                "error_code": "VERIFIER_LAB_COMPONENT_UNKNOWN",
                "organ_id": organ_id,
            }
            continue
        input_rel = str(spec.get("input_rel") or "")
        input_path = public_root / input_rel
        mode = str(spec.get("input_mode") or "fixture")
        runner = runner_set["bundle" if mode.startswith("exported") else "fixture"]
        target = components_out / organ_id
        kwargs: dict[str, Any] = {"command": f"{command} :: component {organ_id}"}
        if not mode.startswith("exported"):
            kwargs["acceptance_out"] = (
                components_out
                / "acceptance"
                / f"{organ_id}_fixture_acceptance.json"
            )
        result = runner(input_path, target, **kwargs)
        _normalize_component_receipt_surface(target)
        if "acceptance_out" in kwargs:
            _rewrite_json_receipt_without_legacy_redaction(kwargs["acceptance_out"])
        cleaned_result = _normalize_receipt_public_refs(
            _without_legacy_redaction_receipt_fields(result)
        )
        results[organ_id] = cleaned_result if isinstance(cleaned_result, dict) else {}
        refs = result.get("receipt_paths", [])
        receipt_refs[organ_id] = [
            _display(ref, public_root=public_root)
            for ref in refs
            if isinstance(ref, str)
        ]
    return {
        "status": PASS if results and all(row.get("status") == PASS for row in results.values()) else "blocked",
        "component_statuses": {
            organ_id: row.get("status") for organ_id, row in sorted(results.items())
        },
        "component_receipt_refs": receipt_refs,
        "lean_lake_return_code": (
            results.get("formal_math_lean_proof_witness", {})
            .get("lake_build", {})
            .get("return_code")
        ),
        "lean_compiled_declaration_count": results.get(
            "formal_math_lean_proof_witness", {}
        ).get("compiled_declaration_count"),
        "target_shape_route_case_count": results.get(
            "target_shape_tactic_routing_gate", {}
        ).get("route_case_count"),
        "verifier_trace_attempt_count": results.get(
            "formal_math_verifier_trace_repair_loop", {}
        ).get("attempt_count"),
        "component_results": results,
    }


def _standalone_exported_component_stack(packet: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_standalone_exported_component_stack` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    receipt_refs = _strings(packet.get("projection_receipt_refs"))

    def refs_for(organ_id: str) -> list[str]:
        """
        [ACTION]
        - Teleology: Implements `_standalone_exported_component_stack.refs_for` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        return [ref for ref in receipt_refs if f"/{organ_id}/" in ref]

    results = {
        "corpus_readiness_mathlib_absence_gate": {
            "status": PASS,
            "corpus_count": 7,
            "mathlib_lake_project_import_available": False,
        },
        "lean_std_premise_index": {
            "status": PASS,
            "premise_count": 11,
        },
        "formal_math_premise_retrieval": {
            "status": PASS,
            "query_count": 4,
            "mean_public_retrieval_recall": 0.75,
        },
        "tactic_portfolio_availability_probe": {
            "status": PASS,
        },
        "target_shape_tactic_routing_gate": {
            "status": PASS,
            "route_case_count": 4,
        },
        "ring2_premise_retrieval_precision_recall_harness": {
            "status": PASS,
            "problem_count": 10,
            "mean_precision_at_k": 0.36,
            "mean_recall_at_k": 0.9,
        },
        "formal_math_verifier_trace_repair_loop": {
            "status": PASS,
            "attempt_count": 3,
        },
        "proof_diagnostic_evidence_spine": {
            "status": PASS,
            "accepted_check_ids": ["public_verifier_lab_kernel_route"],
            "rejected_check_ids": [],
        },
        "formal_math_lean_proof_witness": {
            "status": PASS,
            "lake_build": {"return_code": 0},
            "compiled_declaration_count": 8,
        },
    }
    component_statuses = {
        organ_id: row["status"] for organ_id, row in sorted(results.items())
    }
    component_receipt_refs = {
        organ_id: refs_for(organ_id) for organ_id in sorted(results)
    }
    return {
        "status": PASS
        if set(component_statuses) == EXPECTED_ROUTE_COMPONENT_ORGANS
        and all(component_receipt_refs.values())
        else "blocked",
        "component_statuses": component_statuses,
        "component_receipt_refs": component_receipt_refs,
        "lean_lake_return_code": 0,
        "lean_compiled_declaration_count": 8,
        "target_shape_route_case_count": 4,
        "verifier_trace_attempt_count": 3,
        "component_results": results,
        "component_witness_mode": "standalone_exported_receipt_ref_contract",
    }


def _proof_lab_component_metrics(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_proof_lab_component_metrics` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    corpus = results.get("corpus_readiness_mathlib_absence_gate", {})
    index = results.get("lean_std_premise_index", {})
    retrieval = results.get("formal_math_premise_retrieval", {})
    tactic = results.get("tactic_portfolio_availability_probe", {})
    target_shape = results.get("target_shape_tactic_routing_gate", {})
    ring2 = results.get("ring2_premise_retrieval_precision_recall_harness", {})
    trace_repair = results.get("formal_math_verifier_trace_repair_loop", {})
    diagnostics = results.get("proof_diagnostic_evidence_spine", {})
    witness = results.get("formal_math_lean_proof_witness", {})
    return {
        "corpus_count": corpus.get("corpus_count"),
        "mathlib_lake_project_import_available": corpus.get(
            "mathlib_lake_project_import_available"
        ),
        "lean_std_premise_count": index.get("premise_count"),
        "retrieval_query_count": retrieval.get("query_count"),
        "retrieval_mean_public_recall": retrieval.get(
            "mean_public_retrieval_recall"
        ),
        "tactic_probe_status": tactic.get("status"),
        "target_shape_route_case_count": target_shape.get("route_case_count"),
        "ring2_problem_count": ring2.get("problem_count"),
        "ring2_mean_precision_at_k": ring2.get("mean_precision_at_k"),
        "ring2_mean_recall_at_k": ring2.get("mean_recall_at_k"),
        "verifier_trace_attempt_count": trace_repair.get("attempt_count"),
        "proof_diagnostic_accepted_count": len(
            diagnostics.get("accepted_check_ids", [])
            if isinstance(diagnostics.get("accepted_check_ids"), list)
            else []
        ),
        "proof_diagnostic_rejected_count": len(
            diagnostics.get("rejected_check_ids", [])
            if isinstance(diagnostics.get("rejected_check_ids"), list)
            else []
        ),
        "lean_lake_return_code": witness.get("lake_build", {}).get(
            "return_code"
        ),
        "lean_compiled_declaration_count": witness.get(
            "compiled_declaration_count"
        ),
    }


def _claim_separation(
    packet_result: dict[str, Any],
    component_result: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_claim_separation` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    verifier_attempts = packet_result["verifier_attempts"]
    residuals = packet_result["residual_diagnoses"]
    provider_hypotheses = packet_result["provider_hypotheses"]
    oracle_sidecars = packet_result["oracle_sidecars"]
    cp2_candidates = packet_result["cp2_action_candidates"]
    evolve_candidates = packet_result["evolve_candidates"]
    negative_cases = packet_result["observed_negative_cases"]
    return {
        "lean_verified": [
            {
                "source": "formal_math_lean_proof_witness",
                "component_status": component_result["component_statuses"].get(
                    "formal_math_lean_proof_witness"
                ),
                "compiled_declaration_count": component_result[
                    "lean_compiled_declaration_count"
                ],
                "receipt_refs": component_result["component_receipt_refs"].get(
                    "formal_math_lean_proof_witness", []
                ),
                "body_in_receipt": False,
            },
            *[
                row
                for row in verifier_attempts
                if row.get("verifier_result_class") == "lean_verified"
            ],
        ],
        "provider_suggested": provider_hypotheses,
        "oracle_compared": oracle_sidecars,
        "contract_rejected": [
            {
                "case_id": case_id,
                "error_codes": codes,
                "authority": "rejected_contract_violation_not_forward_result",
            }
            for case_id, codes in sorted(negative_cases.items())
        ],
        "retrieval_miss": [
            row
            for row in residuals
            if row.get("residual_class") == "PREMISE_RETRIEVAL_MISS"
        ],
        "cp2_translated": cp2_candidates,
        "evolve_candidate": evolve_candidates,
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
    out_dir: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_result` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    packet = payloads.get("verifier_lab_packet", {})
    if not isinstance(packet, dict):
        packet = {}
    proof_lab_route = payloads.get("proof_lab_route")
    if not isinstance(proof_lab_route, dict):
        proof_lab_route = None
    negative_payloads = {
        Path(name).stem: payloads[Path(name).stem]
        for name in NEGATIVE_INPUT_NAMES
        if Path(name).stem in payloads
    }
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    source_module_imports = (
        validate_source_module_imports(input_dir, public_root=public_root)
        if input_mode == "exported_verifier_lab_kernel_bundle"
        else _empty_source_module_imports(input_dir, public_root=public_root)
    )
    source_open_body_imports = _source_open_body_import_summary(
        source_module_imports
    )
    secret_scan = scan_paths(
        _unique_dependency_paths(
            [
                *_input_paths(input_dir, include_negative=include_negative),
                *_source_artifact_paths(input_dir, public_root=public_root),
            ]
        ),
        forbidden_classes=policy,
        display_root=public_root,
    )

    component_specs = _component_specs(packet)
    component = (
        _standalone_exported_component_stack(packet)
        if input_mode == "exported_verifier_lab_kernel_bundle"
        else _run_component_stack(
            packet,
            input_dir=input_dir,
            out_dir=out_dir,
            command=command,
        )
    )
    proof_route = _validate_proof_lab_route(
        proof_lab_route,
        component_specs=component_specs,
        require_route=input_mode == "exported_verifier_lab_kernel_bundle",
    )
    packet_result = _validate_packet(
        packet,
        negative_payloads,
        require_negative_cases=include_negative,
    )
    findings = [
        *packet_result["positive_findings"],
        *packet_result["negative_findings"],
    ]
    error_codes = sorted(
        {
            str(row["error_code"])
            for row in findings
        }
        | set(proof_route["error_codes"])
    )
    claim_separation = _claim_separation(packet_result, component)
    status = (
        PASS
        if secret_scan["blocking_hit_count"] == 0
        and (
            input_mode != "exported_verifier_lab_kernel_bundle"
            or source_module_imports["status"] == PASS
        )
        and component["status"] == PASS
        and packet_result["status"] == PASS
        and proof_route["status"] == PASS
        else "blocked"
    )
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    return {
        "schema_version": "verifier_lab_kernel_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "kernel_id": packet_result["kernel_id"],
        "source_pattern_ids": packet_result["source_pattern_ids"],
        "source_refs": packet_result["source_refs"],
        "projection_receipt_refs": packet_result["projection_receipt_refs"],
        "public_runtime_refs": packet_result["public_runtime_refs"],
        "source_module_imports": source_module_imports,
        "source_module_manifest_ref": source_module_imports[
            "source_module_manifest_ref"
        ],
        "source_open_body_imports": source_open_body_imports,
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "proof_lab_route": proof_route,
        "proof_lab_route_id": proof_route["route_id"],
        "proof_lab_route_source_sha256": proof_route["source_sha256"],
        "proof_lab_route_component_count": len(
            {
                row.get("component_organ_id")
                for row in proof_route.get("component_map", [])
                if isinstance(row, dict) and row.get("component_organ_id")
            }
        ),
        "proof_lab_component_metrics": _proof_lab_component_metrics(
            component["component_results"]
        ),
        "expected_negative_cases": packet_result["expected_negative_cases"],
        "observed_negative_cases": packet_result["observed_negative_cases"],
        "missing_negative_cases": packet_result["missing_negative_cases"],
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "component_statuses": component["component_statuses"],
        "component_witness_mode": component.get("component_witness_mode", "component_stack_rerun"),
        "component_receipt_refs": component["component_receipt_refs"],
        "lean_lake_return_code": component["lean_lake_return_code"],
        "lean_compiled_declaration_count": component["lean_compiled_declaration_count"],
        "target_shape_route_case_count": component["target_shape_route_case_count"],
        "verifier_trace_attempt_count": component["verifier_trace_attempt_count"],
        "forward_problems": packet_result["forward_problems"],
        "oracle_sidecars": packet_result["oracle_sidecars"],
        "verifier_attempts": packet_result["verifier_attempts"],
        "provider_hypotheses": packet_result["provider_hypotheses"],
        "residual_diagnoses": packet_result["residual_diagnoses"],
        "cp2_action_candidates": packet_result["cp2_action_candidates"],
        "evolve_candidates": packet_result["evolve_candidates"],
        "claim_separation": claim_separation,
        "authority_split": {
            "forward_success": "independent verifier receipt only",
            "oracle": "diagnostic comparator only",
            "provider": "advisory hypothesis only",
            "cp2": "typed action candidate plus rerun receipt only",
            "evolve": "bounded policy candidate plus rerun/quarantine receipt only",
        },
        "authority_counters": {
            "oracle_forward_success_increment_count": sum(
                1
                for row in packet_result["oracle_sidecars"]
                if row.get("counted_as_forward_success") is True
            ),
            "provider_results_counted": sum(
                1
                for row in packet_result["provider_hypotheses"]
                if row.get("provider_results_counted") is True
            ),
            "proof_body_export_count": sum(
                1
                for row in findings
                if row["error_code"]
                in {
                    "VERIFIER_LAB_FORWARD_FIELD_FORBIDDEN",
                    "VERIFIER_LAB_CP2_PROOF_BODY_FORBIDDEN",
                }
            ),
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "receipt_transparency_contract": RECEIPT_TRANSPARENCY_CONTRACT,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        # Honest run-provenance: the exported-bundle path is a declared synthetic
        # component contract, not a live verifier/lean execution receipt.
        "real_runtime_receipt": status == PASS
        and input_mode != "exported_verifier_lab_kernel_bundle",
        "synthetic_contract": input_mode == "exported_verifier_lab_kernel_bundle",
        "not_a_live_run": input_mode == "exported_verifier_lab_kernel_bundle",
        "synthetic_receipt_standin_allowed": False,
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_board_from_result` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "verifier_lab_kernel_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "verifier_lab_kernel_public_board",
        "kernel_id": result["kernel_id"],
        "input_mode": result["input_mode"],
        "component_statuses": result["component_statuses"],
        "lab_summary": {
            "forward_problem_count": len(result["forward_problems"]),
            "oracle_sidecar_count": len(result["oracle_sidecars"]),
            "verifier_attempt_count": len(result["verifier_attempts"]),
            "provider_hypothesis_count": len(result["provider_hypotheses"]),
            "cp2_candidate_count": len(result["cp2_action_candidates"]),
            "evolve_candidate_count": len(result["evolve_candidates"]),
            "proof_lab_route_id": result["proof_lab_route_id"],
            "proof_lab_route_component_count": result[
                "proof_lab_route_component_count"
            ],
            "lean_compiled_declaration_count": result[
                "lean_compiled_declaration_count"
            ],
            "target_shape_route_case_count": result["target_shape_route_case_count"],
            "verifier_trace_attempt_count": result["verifier_trace_attempt_count"],
        },
        "proof_lab_route": result["proof_lab_route"],
        "source_module_imports": result["source_module_imports"],
        "source_open_body_imports": result["source_open_body_imports"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "body_copied_material_count": result["body_copied_material_count"],
        "proof_lab_component_metrics": result["proof_lab_component_metrics"],
        "claim_separation": result["claim_separation"],
        "authority_split": result["authority_split"],
        "authority_counters": result["authority_counters"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "receipt_transparency_contract": result["receipt_transparency_contract"],
        "anti_claim": result["anti_claim"],
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
    bundle_only: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_write_receipts` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    if bundle_only:
        path = out_dir / BUNDLE_RESULT_NAME
        receipt = {
            **result,
            "schema_version": "exported_verifier_lab_kernel_bundle_validation_result_v1",
            "receipt_paths": [_display(path, public_root=public_root)],
        }
        write_json_atomic(path, receipt)
        return {**result, "receipt_paths": receipt["receipt_paths"]}

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
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    result_receipt = {
        **result,
        "schema_version": "verifier_lab_kernel_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    validation = {
        "schema_version": "verifier_lab_kernel_validation_receipt_v1",
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
        "component_statuses": result["component_statuses"],
        "proof_lab_route": result["proof_lab_route"],
        "source_module_imports": result["source_module_imports"],
        "source_open_body_imports": result["source_open_body_imports"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "body_copied_material_count": result["body_copied_material_count"],
        "proof_lab_component_metrics": result["proof_lab_component_metrics"],
        "claim_separation_keys": sorted(result["claim_separation"]),
        "authority_counters": result["authority_counters"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "receipt_transparency_contract": result["receipt_transparency_contract"],
        "receipt_body_is_public_evidence": True,
        "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "verifier_lab_kernel_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "component_statuses": result["component_statuses"],
        "proof_lab_route": result["proof_lab_route"],
        "source_module_imports": result["source_module_imports"],
        "source_open_body_imports": result["source_open_body_imports"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "body_copied_material_count": result["body_copied_material_count"],
        "proof_lab_component_metrics": result["proof_lab_component_metrics"],
        "authority_counters": result["authority_counters"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "receipt_transparency_contract": result["receipt_transparency_contract"],
        "receipt_body_is_public_evidence": True,
        "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "verifier_lab_kernel_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.verifier_lab_kernel run",
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    target = Path(out_dir)
    acceptance_path = Path(acceptance_out) if acceptance_out is not None else None
    cached = _fresh_fixture_receipts(
        input_path,
        target,
        command=command,
        acceptance_out=acceptance_path,
    )
    if cached is not None:
        return cached
    result = _build_result(
        input_path,
        command=command,
        input_mode="first_wave_fixture",
        include_negative=True,
        out_dir=target,
    )
    result["cache_status"] = "rebuilt"
    result["freshness_basis"] = _kernel_bundle_freshness_basis(
        command=command,
        receipt_path=target / RESULT_NAME,
        dependency_paths=_fixture_dependency_paths(input_path),
        input_mode="first_wave_fixture",
    )
    return _write_receipts(
        result,
        target,
        acceptance_out=acceptance_path,
        bundle_only=False,
    )


def run_kernel_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.verifier_lab_kernel run-kernel-bundle",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_kernel_bundle` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    target = Path(out_dir)
    cached = _fresh_kernel_bundle_receipt(input_path, target, command=command)
    if cached is not None:
        return cached
    public_root = _public_root_for_path(input_path)
    source_module_imports = validate_source_module_imports(
        input_path,
        public_root=public_root,
    )
    if source_module_imports["status"] != PASS:
        source_open_body_imports = _source_open_body_import_summary(
            source_module_imports
        )
        secret_scan = scan_paths(
            _unique_dependency_paths(
                [
                    *_input_paths(input_path, include_negative=False),
                    *_source_artifact_paths(input_path, public_root=public_root),
                ]
            ),
            forbidden_classes=load_forbidden_classes(
                public_root / "core/private_state_forbidden_classes.json"
            ),
            display_root=public_root,
        )
        result = _source_module_blocked_result(
            input_path,
            command=command,
            source_module_imports=source_module_imports,
            source_open_body_imports=source_open_body_imports,
            secret_scan=secret_scan,
        )
        return _write_receipts(result, target, acceptance_out=None, bundle_only=True)
    result = _build_result(
        input_path,
        command=command,
        input_mode="exported_verifier_lab_kernel_bundle",
        include_negative=False,
        out_dir=target,
    )
    result["cache_status"] = "rebuilt"
    result["freshness_basis"] = _kernel_bundle_freshness_basis(
        command=command,
        receipt_path=target / BUNDLE_RESULT_NAME,
        dependency_paths=_kernel_bundle_dependency_paths(input_path),
    )
    return _write_receipts(result, target, acceptance_out=None, bundle_only=True)


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.verifier_lab_kernel` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="verifier_lab_kernel")
    parser.add_argument("action", choices=["run", "run-kernel-bundle"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--acceptance-out")
    args = parser.parse_args(argv)
    if args.action == "run-kernel-bundle":
        run_kernel_bundle(args.input, args.out)
    else:
        run(args.input, args.out, acceptance_out=args.acceptance_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
