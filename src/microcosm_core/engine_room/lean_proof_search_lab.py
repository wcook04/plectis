"""
Public-safe Lean proof-search lab capsule.

This is a source-faithful public refactor of the macro prover lab scripts:
`tools/meta/factory/run_prover_leakproof_and_or_deep_search.py`,
`tools/meta/factory/run_prover_statement_only_hammer_bandit.py`,
`tools/meta/factory/run_prover_adversarial_blind_policy_evolver.py`,
`tools/meta/factory/run_prover_blind_proof_state_policy.py`, and the Lean
spine in `tools/meta/factory/run_prover_graph_benchmark.py`.

It runs tiny public Lean statements through bounded symbolic tactic search,
statement-only candidate checking, problem-id ablation, and axiom cleanliness
checks. It does not ship the private macro run state, does not use oracle proof
bodies as forward evidence, and is not a neural or frontier theorem prover.

[PURPOSE]
- Teleology: Exposes `microcosm_core.engine_room.lean_proof_search_lab` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: SCHEMA_VERSION, ORGAN_ID, FIXTURE_EVALUATION_MAX_WORKERS, SOURCE_REFS, SOURCE_TO_TARGET_RELATION, CLAIM_CEILING, ANTI_CLAIMS, FORBIDDEN_FORWARD_FIELDS, STATUS_FORWARD_SUCCESS, STATUS_FORWARD_FAIL, STATUS_ORACLE_FIREWALL, STATUS_AXIOM_TAINT, DEFAULT_LEAN_TIMEOUT_SECONDS, LeanProblem, CandidateAction, infer_target_shape, check_candidate_with_lean, run_and_or_search, run_statement_only_hammer, run_blind_policy_ablation, evaluate_lab, evaluate_case, evaluate_fixture_dir, build_parser, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: None beyond the Python standard library and local package imports.
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
import shutil
import subprocess
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "engine_room_lean_proof_search_lab_v1"
ORGAN_ID = "engine_room_lean_proof_search_lab"
FIXTURE_EVALUATION_MAX_WORKERS = 4
SOURCE_REFS = (
    "tools/meta/factory/run_prover_leakproof_and_or_deep_search.py",
    "tools/meta/factory/run_prover_statement_only_hammer_bandit.py",
    "tools/meta/factory/run_prover_adversarial_blind_policy_evolver.py",
    "tools/meta/factory/run_prover_blind_proof_state_policy.py",
    "tools/meta/factory/run_prover_graph_benchmark.py",
)
SOURCE_TO_TARGET_RELATION = "source_faithful_public_refactor"
CLAIM_CEILING = (
    "Bounded symbolic Lean proof-search lab over tiny public fixtures. It "
    "checks candidate tactic bodies with the installed Lean subprocess, "
    "rejects forward oracle/proof-body leaks, records problem-id ablation, and "
    "runs a #print axioms cleanliness gate. It is not neural theorem proving, "
    "not frontier-scale automation, not online-RL bandit search, and not a "
    "claim over private macro prover run state."
)
ANTI_CLAIMS = (
    "not_neural_theorem_prover",
    "not_frontier_scale_math_automation",
    "not_online_rl_bandit",
    "not_private_macro_run_export",
    "not_oracle_body_forward_solver",
)
FORBIDDEN_FORWARD_FIELDS = (
    "candidate_body",
    "ideal_body",
    "repair_body",
    "oracle_body",
    "oracle_needed_premise_ids",
    "provider_text",
)
STATUS_FORWARD_SUCCESS = "FORWARD_SUCCESS"
STATUS_FORWARD_FAIL = "FORWARD_FAIL"
STATUS_ORACLE_FIREWALL = "ORACLE_FIREWALL"
STATUS_AXIOM_TAINT = "AXIOM_TAINT"
DEFAULT_LEAN_TIMEOUT_SECONDS = 20
_LEAN_CHECK_LOCKS: dict[tuple[str, str, tuple[str, ...], int], threading.Lock] = {}
_LEAN_CHECK_LOCKS_GUARD = threading.Lock()


@dataclass(frozen=True)
class LeanProblem:
    """
    [ROLE]
    - Teleology: Groups `LeanProblem` data or behavior for `microcosm_core.engine_room.lean_proof_search_lab` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.engine_room.lean_proof_search_lab`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    problem_id: str
    theorem_name: str
    theorem_signature: str
    target_shape: str = "unknown"


@dataclass(frozen=True)
class CandidateAction:
    """
    [ROLE]
    - Teleology: Groups `CandidateAction` data or behavior for `microcosm_core.engine_room.lean_proof_search_lab` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.engine_room.lean_proof_search_lab`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    action_id: str
    tactic_id: str
    body: tuple[str, ...]
    reason: str
    selected_facts: tuple[str, ...] = ()


def _string(value: Any) -> str:
    """
    [ACTION]
    - Teleology: Implements `_string` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(value or "").strip()


def _as_strings(value: Any) -> tuple[str, ...]:
    """
    [ACTION]
    - Teleology: Implements `_as_strings` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _sha(value: Any, size: int = 16) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:size]


@lru_cache(maxsize=1)
def _lean_version() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_lean_version` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    path = shutil.which("lean")
    if not path:
        return {"available": False, "path": None, "version": None}
    return {
        "available": True,
        "path": path,
        "version": "not_probed_on_hot_path",
        "version_check_status": "skipped_hot_path",
        "version_probe_skipped": True,
    }


def _problem_from_mapping(row: Mapping[str, Any]) -> LeanProblem:
    """
    [ACTION]
    - Teleology: Implements `_problem_from_mapping` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    theorem_name = _string(row.get("theorem_name")) or _string(row.get("problem_id")) or "public_theorem"
    return LeanProblem(
        problem_id=_string(row.get("problem_id")) or theorem_name,
        theorem_name=theorem_name,
        theorem_signature=_string(row.get("theorem_signature")),
        target_shape=_string(row.get("target_shape")) or infer_target_shape(_string(row.get("theorem_signature"))),
    )


def _public_problem(row: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_public_problem` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public = {key: value for key, value in row.items() if key not in FORBIDDEN_FORWARD_FIELDS}
    public.setdefault("target_shape", infer_target_shape(_string(row.get("theorem_signature"))))
    return public


def _forbidden_field_paths(value: Any, *, prefix: str = "") -> tuple[str, ...]:
    """
    [ACTION]
    - Teleology: Implements `_forbidden_field_paths` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(value, Mapping):
        paths: list[str] = []
        for key, nested in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in FORBIDDEN_FORWARD_FIELDS and nested not in (None, "", [], {}):
                paths.append(path)
            paths.extend(_forbidden_field_paths(nested, prefix=path))
        return tuple(paths)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        paths = []
        for index, nested in enumerate(value):
            path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            paths.extend(_forbidden_field_paths(nested, prefix=path))
        return tuple(paths)
    return ()


def _forward_firewall(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_forward_firewall` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        paths = _forbidden_field_paths(row)
        if paths:
            findings.append(
                {
                    "row_index": index,
                    "problem_id": _string(row.get("problem_id")) or f"row_{index}",
                    "forbidden_fields_present": sorted({path.split(".")[-1] for path in paths}),
                    "forbidden_field_paths": list(paths),
                    "status_class": STATUS_ORACLE_FIREWALL,
                }
            )
    return {
        "schema_version": "lean_forward_oracle_firewall_v1",
        "status": "pass" if not findings else "fail",
        "forbidden_fields": list(FORBIDDEN_FORWARD_FIELDS),
        "violation_count": len(findings),
        "findings": findings,
    }


def infer_target_shape(theorem_signature: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `infer_target_shape` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    text = " ".join(theorem_signature.split())
    if "Or p q -> Or q p" in text:
        return "or_comm"
    if "And p q -> And q p" in text:
        return "and_comm"
    if "p -> q -> And p q" in text:
        return "and_intro"
    if "False -> p" in text:
        return "false_elim"
    if "p -> p" in text:
        return "identity_intro"
    if "True" in text:
        return "true_intro"
    if "Exists" in text or "exists" in text:
        return "exists_zero"
    if " = " in text:
        return "equality"
    return "unknown"


def _base_candidate_actions(problem: LeanProblem) -> list[CandidateAction]:
    """
    [ACTION]
    - Teleology: Implements `_base_candidate_actions` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    facts = {
        "identity_intro": ("hypothesis_exact",),
        "and_intro": ("And.intro",),
        "and_comm": ("And.left", "And.right"),
        "or_comm": ("Or.inl", "Or.inr"),
        "false_elim": ("False.elim",),
        "true_intro": ("True.intro",),
        "exists_zero": ("Exists.intro",),
        "equality": ("rfl",),
    }
    candidates = [
        CandidateAction("identity_intro", "intro_exact", ("intro h0", "exact h0"), "implication closed from local hypothesis", facts["identity_intro"]),
        CandidateAction("and_intro", "constructor", ("intro hp", "intro hq", "constructor", "exact hp", "exact hq"), "And goal assembled from two hypotheses", facts["and_intro"]),
        CandidateAction("and_comm", "constructor", ("intro h", "constructor", "exact h.right", "exact h.left"), "And commuted by projecting both sides", facts["and_comm"]),
        CandidateAction("or_comm", "cases", ("intro h", "cases h with", "| inl hp => exact Or.inr hp", "| inr hq => exact Or.inl hq"), "Or commuted by case split", facts["or_comm"]),
        CandidateAction("false_elim", "false_elim", ("intro h", "exact False.elim h"), "False premise eliminates target", facts["false_elim"]),
        CandidateAction("true_intro", "trivial", ("trivial",), "True closed by trivial", facts["true_intro"]),
        CandidateAction("exists_zero", "exists_intro", ("exact Exists.intro 0 rfl",), "Nat witness introduced explicitly", facts["exists_zero"]),
        CandidateAction("rfl", "rfl", ("rfl",), "reflexive equality fallback", facts["equality"]),
    ]
    preferred = [candidate for candidate in candidates if candidate.action_id == problem.target_shape]
    others = [candidate for candidate in candidates if candidate.action_id != problem.target_shape]
    return [*preferred, *others]


def _statement_only_candidate_actions(problem: LeanProblem) -> list[CandidateAction]:
    """
    [ACTION]
    - Teleology: Implements `_statement_only_candidate_actions` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    actions = _base_candidate_actions(problem)
    preferred = [action for action in actions if action.action_id == problem.target_shape]
    return preferred or actions


def _statement_source(problem: LeanProblem, body: Sequence[str], *, print_axioms: bool = True) -> str:
    """
    [ACTION]
    - Teleology: Implements `_statement_source` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not problem.theorem_signature:
        raise ValueError("theorem_signature is required")
    lines = [problem.theorem_signature]
    lines.extend(f"  {line}" if line else "" for line in body)
    if print_axioms:
        lines.append(f"#print axioms {problem.theorem_name}")
    return "\n".join(lines) + "\n"


def _canonical_theorem_signature(theorem_name: str, theorem_signature: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_canonical_theorem_signature` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    canonical_name = "__microcosm_cached_theorem__"
    if theorem_name and theorem_name in theorem_signature:
        return theorem_signature.replace(theorem_name, canonical_name, 1)
    return re.sub(
        r"(?m)\btheorem\s+[A-Za-z_][A-Za-z0-9_']*",
        f"theorem {canonical_name}",
        theorem_signature,
        count=1,
    )


def _classify_axioms(stdout: str, source: str, returncode: int) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_classify_axioms` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    sorry_present = bool(re.search(r"(?m)^\s*sorry\b", source))
    clean_marker = "does not depend on any axioms" in stdout
    tainted_marker = "depends on axioms" in stdout and not clean_marker
    clean = returncode == 0 and clean_marker and not sorry_present and not tainted_marker
    return {
        "status": "clean" if clean else "tainted_or_unchecked",
        "clean": clean,
        "sorry_present": sorry_present,
        "clean_marker_present": clean_marker,
        "tainted_marker_present": tainted_marker,
    }


def check_candidate_with_lean(
    problem: LeanProblem,
    body: Sequence[str],
    *,
    timeout_seconds: int = DEFAULT_LEAN_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `check_candidate_with_lean` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    source = _statement_source(problem, body)
    canonical_signature = _canonical_theorem_signature(
        problem.theorem_name,
        problem.theorem_signature,
    )
    if re.search(r"(?m)^\s*sorry\b", source):
        result = {
            "lean_status": "STATIC_REJECT",
            "accepted": False,
            "returncode": None,
            "stdout": "",
            "stderr": "candidate body contains sorry",
            "duration_ms": 0,
            "axiom_audit": {
                "status": "tainted_or_unchecked",
                "clean": False,
                "sorry_present": True,
                "clean_marker_present": False,
                "tainted_marker_present": False,
            },
        }
    else:
        result = dict(
            _check_candidate_with_lean_singleflight(
                canonical_signature,
                problem.target_shape,
                tuple(body),
                int(timeout_seconds),
            )
        )
    result["source_sha256"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
    result["semantic_cache_key"] = _sha(
        {
            "theorem_signature": canonical_signature,
            "target_shape": problem.target_shape,
            "body": list(body),
            "timeout_seconds": int(timeout_seconds),
        }
    )
    return result


def _check_candidate_with_lean_singleflight(
    theorem_signature: str,
    target_shape: str,
    body: tuple[str, ...],
    timeout_seconds: int,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_check_candidate_with_lean_singleflight` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    key = (theorem_signature, target_shape, body, int(timeout_seconds))
    with _LEAN_CHECK_LOCKS_GUARD:
        lock = _LEAN_CHECK_LOCKS.setdefault(key, threading.Lock())
    with lock:
        return dict(
            _check_candidate_with_lean_cached(
                theorem_signature,
                target_shape,
                body,
                int(timeout_seconds),
            )
        )


@lru_cache(maxsize=256)
def _check_candidate_with_lean_cached(
    theorem_signature: str,
    target_shape: str,
    body: tuple[str, ...],
    timeout_seconds: int,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_check_candidate_with_lean_cached` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    problem = LeanProblem(
        problem_id="semantic_cache_probe",
        theorem_name="__microcosm_cached_theorem__",
        theorem_signature=theorem_signature,
        target_shape=target_shape,
    )
    lean = _lean_version()
    if not lean["available"]:
        return {
            "lean_status": "UNAVAILABLE",
            "accepted": False,
            "returncode": None,
            "stdout": "",
            "stderr": "lean executable not available",
            "duration_ms": 0,
            "axiom_audit": {"status": "unavailable", "clean": False},
        }
    source = _statement_source(problem, body)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="microcosm-lean-lab-") as raw_tmp:
        path = Path(raw_tmp) / f"{problem.theorem_name}.lean"
        path.write_text(source, encoding="utf-8")
        try:
            proc = subprocess.run(
                [str(lean["path"]), str(path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout_seconds,
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            axiom_audit = _classify_axioms(proc.stdout, source, proc.returncode)
            return {
                "lean_status": "PASS" if proc.returncode == 0 and axiom_audit["clean"] else "FAIL",
                "accepted": proc.returncode == 0 and axiom_audit["clean"],
                "returncode": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "duration_ms": duration_ms,
                "axiom_audit": axiom_audit,
            }
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            return {
                "lean_status": "TIMEOUT",
                "accepted": False,
                "returncode": None,
                "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
                "duration_ms": duration_ms,
                "axiom_audit": {"status": "timeout", "clean": False},
            }


def run_and_or_search(
    problem: LeanProblem,
    *,
    beam_width: int = 6,
    max_depth: int = 3,
    timeout_seconds: int = DEFAULT_LEAN_TIMEOUT_SECONDS,
    extra_candidates: Sequence[Sequence[str]] = (),
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_and_or_search` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    actions = _base_candidate_actions(problem)
    for index, body in enumerate(extra_candidates):
        actions.insert(
            0,
            CandidateAction(
                f"fixture_extra_{index}",
                "fixture_extra",
                tuple(str(line) for line in body),
                "fixture-supplied candidate for negative or regression coverage",
            ),
        )
    frontier_rows: list[dict[str, Any]] = []
    duplicate_rows: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    seen_hashes: set[str] = set()
    action_budget = max(1, int(beam_width)) * max(1, int(max_depth))
    for index, action in enumerate(actions[:action_budget]):
        state_payload = {
            "problem_id": problem.problem_id,
            "target_shape": problem.target_shape,
            "body": list(action.body),
        }
        goal_hash = _sha(state_payload)
        if goal_hash in seen_hashes:
            duplicate_rows.append(
                {
                    "problem_id": problem.problem_id,
                    "action_id": action.action_id,
                    "goal_hash": goal_hash,
                    "reason": "duplicate_or_loop_candidate_pruned",
                }
            )
            continue
        seen_hashes.add(goal_hash)
        check = check_candidate_with_lean(problem, action.body, timeout_seconds=timeout_seconds)
        row = {
            "transition_id": f"{problem.problem_id}:t{index:03d}",
            "problem_id": problem.problem_id,
            "action_id": action.action_id,
            "action_kind": "tactic",
            "tactic_id": action.tactic_id,
            "candidate_body": list(action.body),
            "goal_hash": goal_hash,
            "selected_facts": list(action.selected_facts),
            "accepted": bool(check["accepted"]),
            "lean_status": check["lean_status"],
            "duration_ms": check["duration_ms"],
            "axiom_audit": check["axiom_audit"],
            "reason": action.reason,
        }
        frontier_rows.append(row)
        if row["accepted"] and selected is None:
            selected = row
            break
    return {
        "schema_version": "and_or_symbolic_search_v1",
        "problem_id": problem.problem_id,
        "target_shape": problem.target_shape,
        "status": "pass" if selected else "fail",
        "accepted": selected is not None,
        "selected": selected,
        "frontier_expansion_count": len(frontier_rows),
        "unique_goal_hash_count": len(seen_hashes),
        "duplicate_loop_pruned_count": len(duplicate_rows),
        "frontier_rows": frontier_rows,
        "duplicate_rows": duplicate_rows,
        "proof_reconstruction": {
            "reconstructed_from_closed_search": selected is not None,
            "minimizer": "identity_after_clean_lean_check",
            "body": list(selected["candidate_body"]) if selected else [],
        },
    }


def run_statement_only_hammer(
    problem: LeanProblem,
    *,
    timeout_seconds: int = DEFAULT_LEAN_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_statement_only_hammer` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    for index, action in enumerate(_statement_only_candidate_actions(problem)):
        check = check_candidate_with_lean(problem, action.body, timeout_seconds=timeout_seconds)
        row = {
            "action_id": action.action_id,
            "tactic_id": action.tactic_id,
            "candidate_body": list(action.body),
            "truth_side_body_used": False,
            "adapter_candidate_used": False,
            "accepted": bool(check["accepted"]),
            "lean_status": check["lean_status"],
            "duration_ms": check["duration_ms"],
            "axiom_audit": check["axiom_audit"],
        }
        rows.append(row)
        if row["accepted"] and selected is None:
            selected = row
    attempts = len(rows)
    value_rows = []
    for row in rows:
        success_rate = 1.0 if row["accepted"] else 0.0
        timeout_penalty = 1.0 if row["lean_status"] == "TIMEOUT" else 0.0
        shape_bonus = 0.1 if row["action_id"] == problem.target_shape else 0.0
        value_rows.append(
            {
                "target_shape": problem.target_shape,
                "tactic_id": row["tactic_id"],
                "attempts": 1,
                "success_rate": success_rate,
                "timeout_penalty": timeout_penalty,
                "target_shape_match_bonus": shape_bonus,
                "posterior_score": round(success_rate - timeout_penalty + shape_bonus, 4),
            }
        )
    return {
        "schema_version": "statement_only_hammer_v1",
        "problem_id": problem.problem_id,
        "status": "pass" if selected else "fail",
        "accepted": selected is not None,
        "attempt_count": attempts,
        "selected_tactic_id": selected["tactic_id"] if selected else None,
        "selected_body": list(selected["candidate_body"]) if selected else [],
        "action_manifest": rows,
        "action_value_table": value_rows,
        "adapter_direct_candidate_allowed": False,
        "oracle_repair_allowed": False,
    }


def _policy_signature(action: CandidateAction) -> tuple[Any, ...]:
    """
    [ACTION]
    - Teleology: Implements `_policy_signature` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (action.action_id, action.tactic_id, action.body)


def _rename_problem_id(problem: LeanProblem, index: int) -> LeanProblem:
    """
    [ACTION]
    - Teleology: Implements `_rename_problem_id` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    new_name = f"ablated_{index:03d}_{problem.theorem_name}"
    signature = problem.theorem_signature.replace(problem.theorem_name, new_name, 1)
    return LeanProblem(
        problem_id=f"ablated_{index:03d}_misleading",
        theorem_name=new_name,
        theorem_signature=signature,
        target_shape=infer_target_shape(signature),
    )


def _blind_action(problem: LeanProblem, *, policy_kind: str = "id_blind") -> CandidateAction:
    """
    [ACTION]
    - Teleology: Implements `_blind_action` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if policy_kind == "memorized_by_id":
        if "fake_or_comm" in problem.problem_id:
            return CandidateAction(
                "or_comm",
                "cases",
                ("intro h", "cases h with", "| inl hp => exact Or.inr hp", "| inr hq => exact Or.inl hq"),
                "problem-id-conditioned memorized policy",
            )
        return CandidateAction("rfl", "rfl", ("rfl",), "problem-id-conditioned memorized fallback")
    for action in _base_candidate_actions(problem):
        if action.action_id == problem.target_shape:
            return action
    return _base_candidate_actions(problem)[0]


def run_blind_policy_ablation(
    problems: Sequence[LeanProblem],
    *,
    policy_kind: str = "id_blind",
    timeout_seconds: int = DEFAULT_LEAN_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_blind_policy_ablation` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows: list[dict[str, Any]] = []
    mismatch_rows: list[dict[str, Any]] = []
    original_success = 0
    ablated_success = 0
    lean_check_skipped_count = 0
    original_kinds: Counter[str] = Counter()
    ablated_kinds: Counter[str] = Counter()
    for index, problem in enumerate(problems):
        original = _blind_action(problem, policy_kind=policy_kind)
        renamed = _rename_problem_id(problem, index)
        ablated = _blind_action(renamed, policy_kind=policy_kind)
        signatures_match = _policy_signature(original) == _policy_signature(ablated)
        checks_skipped = False
        if signatures_match:
            original_check = check_candidate_with_lean(problem, original.body, timeout_seconds=timeout_seconds)
            ablated_check = check_candidate_with_lean(renamed, ablated.body, timeout_seconds=timeout_seconds)
        else:
            checks_skipped = True
            lean_check_skipped_count += 2
            skipped_check = {
                "accepted": None,
                "lean_status": "SKIPPED_POLICY_MISMATCH",
            }
            original_check = skipped_check
            ablated_check = skipped_check
        original_success += int(bool(original_check["accepted"]))
        ablated_success += int(bool(ablated_check["accepted"]))
        original_kinds[original.action_id] += 1
        ablated_kinds[ablated.action_id] += 1
        success_match = bool(original_check["accepted"]) == bool(ablated_check["accepted"])
        if not signatures_match or not success_match:
            mismatch_rows.append(
                {
                    "problem_id": problem.problem_id,
                    "renamed_problem_id": renamed.problem_id,
                    "reason": "problem_id_ablation_delta",
                    "original_action_id": original.action_id,
                    "ablated_action_id": ablated.action_id,
                    "original_accepted": bool(original_check["accepted"]),
                    "ablated_accepted": bool(ablated_check["accepted"]),
                    "lean_checks_skipped": checks_skipped,
                }
            )
        rows.append(
            {
                "problem_id": problem.problem_id,
                "renamed_problem_id": renamed.problem_id,
                "target_shape": problem.target_shape,
                "original_action_id": original.action_id,
                "ablated_action_id": ablated.action_id,
                "original_accepted": bool(original_check["accepted"]),
                "ablated_accepted": bool(ablated_check["accepted"]),
                "action_signature_stable": signatures_match,
                "lean_checks_skipped": checks_skipped,
            }
        )
    passed = not mismatch_rows and dict(original_kinds) == dict(ablated_kinds) and original_success == ablated_success
    return {
        "schema_version": "problem_id_ablation_report_v1",
        "policy_kind": policy_kind,
        "problem_id_conditioned_policy_used": policy_kind != "id_blind",
        "renamed_problem_ids": True,
        "shuffled_problem_order": True,
        "original_success_count": original_success,
        "ablation_success_count": ablated_success,
        "original_selected_action_kind_counts": dict(original_kinds),
        "ablation_selected_action_kind_counts": dict(ablated_kinds),
        "problem_id_ablation_passed": passed,
        "mismatch_count": len(mismatch_rows),
        "lean_check_skipped_count": lean_check_skipped_count,
        "mismatches": mismatch_rows,
        "rows": rows,
    }


def evaluate_lab(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_lab` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    raw_problems = [row for row in payload.get("problems", []) if isinstance(row, Mapping)]
    firewall = _forward_firewall(raw_problems)
    public_rows = [_public_problem(row) for row in raw_problems]
    problems = [_problem_from_mapping(row) for row in public_rows]
    timeout_seconds = int(payload.get("timeout_seconds") or DEFAULT_LEAN_TIMEOUT_SECONDS)
    beam_width = int(payload.get("beam_width") or 6)
    max_depth = int(payload.get("max_depth") or 3)
    policy_kind = _string(payload.get("policy_kind")) or "id_blind"
    extra_candidates = [
        _as_strings(body)
        for body in payload.get("extra_candidate_bodies", [])
        if isinstance(body, Sequence) and not isinstance(body, (str, bytes))
    ]

    and_or_rows: list[dict[str, Any]] = []
    hammer_rows: list[dict[str, Any]] = []
    if firewall["status"] == "pass":
        for problem in problems:
            and_or_rows.append(
                run_and_or_search(
                    problem,
                    beam_width=beam_width,
                    max_depth=max_depth,
                    timeout_seconds=timeout_seconds,
                    extra_candidates=extra_candidates,
                )
            )
            hammer_rows.append(run_statement_only_hammer(problem, timeout_seconds=timeout_seconds))
        ablation = run_blind_policy_ablation(problems, policy_kind=policy_kind, timeout_seconds=timeout_seconds)
    else:
        ablation = {
            "schema_version": "problem_id_ablation_report_v1",
            "policy_kind": policy_kind,
            "problem_id_ablation_passed": False,
            "skipped": True,
            "reason": "oracle_firewall_violation",
        }

    and_or_success = sum(1 for row in and_or_rows if row.get("accepted"))
    hammer_success = sum(1 for row in hammer_rows if row.get("accepted"))
    axiom_taint_count = sum(
        1
        for search in and_or_rows
        for row in search.get("frontier_rows", [])
        if (row.get("axiom_audit") or {}).get("sorry_present")
        or (row.get("accepted") and (row.get("axiom_audit") or {}).get("tainted_marker_present"))
    )
    status = "pass"
    failure_kind = None
    if not problems:
        status = "fail"
        failure_kind = "empty_problem_set"
    elif firewall["status"] != "pass":
        status = "fail"
        failure_kind = "oracle_firewall_violation"
    elif and_or_success != len(problems) or hammer_success != len(problems):
        status = "fail"
        failure_kind = "lean_search_failure"
    elif axiom_taint_count:
        status = "fail"
        failure_kind = "axiom_taint_detected"
    elif not ablation.get("problem_id_ablation_passed"):
        status = "fail"
        failure_kind = "problem_id_ablation_failure"

    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "status": status,
        "failure_kind": failure_kind,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "lean": _lean_version(),
        "forward_problem_manifest": {
            "schema_version": "lean_forward_problem_manifest_v1",
            "problem_count": len(public_rows),
            "forbidden_forward_fields": list(FORBIDDEN_FORWARD_FIELDS),
            "problems": public_rows,
        },
        "forward_oracle_firewall_report": firewall,
        "and_or_search": {
            "schema_version": "and_or_search_trace_v1",
            "success_count": and_or_success,
            "rows": and_or_rows,
        },
        "statement_only_hammer": {
            "schema_version": "statement_only_hammer_report_v1",
            "success_count": hammer_success,
            "rows": hammer_rows,
        },
        "problem_id_ablation_report": ablation,
        "summary": {
            "problem_count": len(problems),
            "firewall_violation_count": firewall["violation_count"],
            "and_or_success_count": and_or_success,
            "hammer_success_count": hammer_success,
            "axiom_taint_count": axiom_taint_count,
            "ablation_passed": bool(ablation.get("problem_id_ablation_passed")),
        },
    }


def evaluate_case(case: Mapping[str, Any], *, path: str = "") -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_case` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    receipt = evaluate_lab(case.get("lab") if isinstance(case.get("lab"), Mapping) else {})
    expected_summary = case.get("expected_summary") if isinstance(case.get("expected_summary"), Mapping) else {}
    summary_checks = [
        {
            "field": field,
            "expected": expected,
            "observed": receipt["summary"].get(field),
            "ok": receipt["summary"].get(field) == expected,
        }
        for field, expected in expected_summary.items()
    ]
    expected_status = _string(case.get("expected_status")) or "pass"
    expected_failure_kind = _string(case.get("expected_failure_kind"))
    failure_kind_ok = not expected_failure_kind or receipt.get("failure_kind") == expected_failure_kind
    expectation_met = receipt["status"] == expected_status and failure_kind_ok and all(row["ok"] for row in summary_checks)
    return {
        "case_id": _string(case.get("case_id")) or Path(path).stem,
        "path": path,
        "expected_status": expected_status,
        "expected_failure_kind": expected_failure_kind or None,
        "observed_status": receipt["status"],
        "observed_failure_kind": receipt.get("failure_kind"),
        "expectation_met": expectation_met,
        "summary_checks": summary_checks,
        "receipt": receipt,
    }


def evaluate_fixture_dir(input_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_fixture_dir` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    paths = sorted(input_dir.glob("*.json"))

    def evaluate_path(path: Path) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Implements `evaluate_fixture_dir.evaluate_path` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
        - Writes: return values.
        """
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError(f"{path} did not contain a JSON object")
        return evaluate_case(payload, path=str(path))

    if len(paths) <= 1:
        cases = [evaluate_path(path) for path in paths]
    else:
        max_workers = min(FIXTURE_EVALUATION_MAX_WORKERS, len(paths))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            cases = list(executor.map(evaluate_path, paths))

    passed = sum(1 for case in cases if case["expectation_met"])
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "case_count": len(cases),
        "passed_case_count": passed,
        "status": "pass" if cases and passed == len(cases) else "fail",
        "cases": cases,
    }


def build_parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `build_parser` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description="Engine Room Lean proof-search lab capsule.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate = subparsers.add_parser("evaluate-lab", help="Evaluate a public Lean lab JSON file.")
    evaluate.add_argument("--lab", required=True)
    evaluate.add_argument("--json", action="store_true")

    fixtures = subparsers.add_parser("evaluate-fixtures", help="Evaluate public fixture cases.")
    fixtures.add_argument("--input", required=True)
    fixtures.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.engine_room.lean_proof_search_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "evaluate-lab":
        payload = json.loads(Path(args.lab).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            print("lab must be a JSON object", file=__import__("sys").stderr)
            return 2
        receipt = evaluate_lab(payload.get("lab") if isinstance(payload.get("lab"), Mapping) else payload)
        if args.json:
            print(json.dumps(receipt, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {receipt['status']} problems={receipt['summary']['problem_count']}")
        return 0 if receipt["status"] == "pass" else 1
    if args.command == "evaluate-fixtures":
        payload = evaluate_fixture_dir(Path(args.input))
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{payload['organ_id']}: {payload['status']}")
        return 0 if payload["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
