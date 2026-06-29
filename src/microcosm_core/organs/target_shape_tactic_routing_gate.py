"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.target_shape_tactic_routing_gate` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, SOURCE_PATTERN_IDS, SOURCE_REFS, REAL_SUBSTRATE_REFS, RECEIPT_ANCHOR_REFS, SOURCE_DIGESTS, PUBLIC_SAFE_SOURCE_DIGESTS, SOURCE_MODULE_MANIFEST_REF, SOURCE_MATERIAL_IDS, BODY_MATERIAL_STATUS, SOURCE_ARTIFACT_STATUS, ROUTING_EVIDENCE_STATUS, BODY_IN_RECEIPT, FORBIDDEN_BODY_KEYS, AUTHORITY_CEILING, ANTI_CLAIM, ...
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


ORGAN_ID = "target_shape_tactic_routing_gate"
FIXTURE_ID = "first_wave.target_shape_tactic_routing_gate"
VALIDATOR_ID = "validator.microcosm.organs.target_shape_tactic_routing_gate"

RESULT_NAME = "target_shape_tactic_routing_result.json"
BOARD_NAME = "target_shape_tactic_routing_board.json"
VALIDATION_RECEIPT_NAME = "target_shape_tactic_routing_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "target_shape_tactic_routing_gate_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_target_shape_tactic_routing_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "target_shape_tactic_routing_gate_command_card_v1"

SOURCE_PATTERN_IDS = ["target_shape_tactic_routing_gate"]
SOURCE_REFS = [
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "premise_retrieval_graph_v0/run_summary.json",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "premise_retrieval_graph_v0/failure_taxonomy_report.json",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "premise_retrieval_graph_v0/graph_update_candidates.json",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "oracle_repair_graph_v0/run_summary.json",
    "receipts/first_wave/formal_math_verifier_trace_repair_loop/"
    "formal_math_verifier_trace_repair_loop_result.json",
    "receipts/first_wave/formal_evidence_cell_anchor_resolver/"
    "formal_evidence_cell_anchor_resolver_result.json",
    "receipts/first_wave/proof_diagnostic_evidence_spine/"
    "proof_evidence_validation_receipt.json",
]
REAL_SUBSTRATE_REFS = SOURCE_REFS[:4]
RECEIPT_ANCHOR_REFS = SOURCE_REFS[4:]
SOURCE_DIGESTS = {
    REAL_SUBSTRATE_REFS[0]: "sha256:93304410f32d40f5cad1c161c1d01a5d6f353ee10b7cf3fecbaaf7b068b43008",
    REAL_SUBSTRATE_REFS[1]: "sha256:8b054c57001c432942a7ed97cbd4dca2a2e2b174d9cd31d9121c38c5ecc933af",
    REAL_SUBSTRATE_REFS[2]: "sha256:6c7eb0bc4ebf1c9a2689720ea8cfe9aa72298c136fdfebd6e1a4aae78986890f",
    REAL_SUBSTRATE_REFS[3]: "sha256:7669c8d91ddf7de75b6a7c7e688e70e4ba211ff3c00ceb9bca32d3202c5739b4",
}
PUBLIC_SAFE_SOURCE_DIGESTS = {
    REAL_SUBSTRATE_REFS[0]: "sha256:be17ba7aacb24d1a554873c84c2559c8f4b326ba4ff49a7cc73f8753efb3c016",
    REAL_SUBSTRATE_REFS[1]: "sha256:fd59902165ae1174e57bab94cae459fa4f70d76b9a9060d78a2050b71b3265b6",
    REAL_SUBSTRATE_REFS[3]: "sha256:f357cf19a4816901d23cbdd085831e164baf8948070bd4288ed924e880b02f43",
}
SOURCE_MODULE_MANIFEST_REF = (
    "examples/target_shape_tactic_routing_gate/"
    "exported_target_shape_tactic_routing_bundle/source_module_manifest.json"
)
SOURCE_MATERIAL_IDS = {
    REAL_SUBSTRATE_REFS[0]: "ring2_target_shape_premise_retrieval_run_summary_body_import",
    REAL_SUBSTRATE_REFS[1]: "ring2_target_shape_premise_retrieval_failure_taxonomy_body_import",
    REAL_SUBSTRATE_REFS[2]: "ring2_target_shape_premise_retrieval_graph_update_candidates_body_import",
    REAL_SUBSTRATE_REFS[3]: "ring2_target_shape_oracle_repair_run_summary_body_import",
}
BODY_MATERIAL_STATUS = "real_ring2_target_shape_routing_refs"
SOURCE_ARTIFACT_STATUS = "copied_ring2_target_shape_routing_source_bodies"
ROUTING_EVIDENCE_STATUS = "real_ring2_problem_domain_failure_class_route_refs"
BODY_IN_RECEIPT = False

FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "lean_source_body",
    "provider_output_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "target_shape_ring2_route_refs_not_proof_authority",
    "lean_lake_execution_authorized": False,
    "mathlib_dependent_proof_authority": False,
    "formal_proof_authority": False,
    "provider_calls_authorized": False,
    "post_execution_routing_authorized": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Target-shape tactic routing validates real Ring2 problem-domain, "
    "failure-class, and graph-update route references before proof execution. "
    "It rejects unavailable, unprobed, or shape-inadmissible tactics before any "
    "Lean call; it does not run Lean/Lake, prove the goal, emit proof bodies, "
    "call providers, or authorize release."
)

EXPECTED_NEGATIVE_CASES = {
    "unavailable_tactic_admitted": ["TARGET_SHAPE_UNAVAILABLE_TACTIC_ADMITTED"],
    "unprobed_tactic_allowed": ["TARGET_SHAPE_UNPROBED_TACTIC_ALLOWED"],
    "shape_preferred_tactic_overridden": [
        "TARGET_SHAPE_DECLARED_SELECTION_NOT_SHAPE_PREFERRED"
    ],
    "unknown_shape_fallback": ["TARGET_SHAPE_UNKNOWN_SHAPE_FALLBACK_REQUIRED"],
    "preferred_unavailable_fallback": [
        "TARGET_SHAPE_PREFERRED_UNAVAILABLE_FALLBACK_REQUIRED"
    ],
    "proof_body_leakage": ["TARGET_SHAPE_PROOF_BODY_FORBIDDEN"],
    "post_execution_route": ["TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN"],
    "release_overclaim": ["TARGET_SHAPE_RELEASE_OVERCLAIM"],
}

INPUT_NAMES = (
    "tactic_portfolio_availability.json",
    "target_shape_routes.json",
)

NEGATIVE_INPUT_NAMES = (
    "unavailable_tactic_admitted.json",
    "unprobed_tactic_allowed.json",
    "shape_preferred_tactic_overridden.json",
    "unknown_shape_fallback.json",
    "preferred_unavailable_fallback.json",
    "proof_body_leakage.json",
    "post_execution_route.json",
    "release_overclaim.json",
)

NEGATIVE_INPUT_NAMES_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)

PREFERRED_TACTICS_BY_TARGET_SHAPE: dict[str, tuple[str, ...]] = {
    "closed_nat_mod_decision": ("decide",),
    "rat_normalization": ("native_decide", "rfl", "decide"),
    "int_linear_arithmetic": ("omega",),
    "nat_arithmetic_with_variables": ("omega", "decide"),
    "nat_arithmetic": ("omega", "decide"),
    "true_intro": ("decide", "simp", "grind"),
    "false_elim": ("simp_all", "grind"),
    "conjunction": ("simp_all", "grind", "omega"),
    "disjunction": ("simp_all", "grind"),
    "existential": ("simp_all", "grind"),
    "equality": ("rfl", "simp", "grind", "decide"),
    "unknown": ("rfl", "simp", "simp_all", "grind"),
    "nat_injective_goal": ("omega", "simp_all", "decide"),
    "bool_decision_goal": ("decide", "simp_all", "rfl"),
    "propositional_intro_goal": ("rfl", "simp_all", "grind"),
    "list_length_rewrite_goal": ("simp_all", "rfl", "omega"),
    "list_map_index_rewrite_goal": ("simp_all", "rfl", "omega"),
    "mathlib_search_goal": ("aesop", "simp_all", "rfl"),
}
DEFAULT_PREFERRED_TACTICS = ("rfl", "simp", "simp_all", "grind")


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_display` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_rows` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return {Path(name).stem: read_json_strict(input_dir / name) for name in names}


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names] + _source_artifact_paths(input_dir)


def _source_artifact_rel_path(source_ref: str) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_artifact_rel_path` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return Path("source_artifacts") / source_ref


def _source_artifact_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_artifact_paths` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [input_dir / _source_artifact_rel_path(ref) for ref in REAL_SUBSTRATE_REFS]


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _source_artifact_imports(
    input_dir: Path,
    *,
    public_root: Path,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_source_artifact_imports` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    imports: list[dict[str, Any]] = []
    for source_ref in REAL_SUBSTRATE_REFS:
        target = input_dir / _source_artifact_rel_path(source_ref)
        body_copied = target.is_file()
        actual_digest = _sha256(target) if body_copied else None
        expected_digest = SOURCE_DIGESTS[source_ref]
        public_safe_expected_digest = PUBLIC_SAFE_SOURCE_DIGESTS.get(source_ref)
        source_digest_matches = actual_digest == expected_digest
        public_safe_digest_matches = actual_digest == public_safe_expected_digest
        digest_matches = source_digest_matches or public_safe_digest_matches
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
                "target_ref": _display(target, public_root=public_root),
                "body_copied": body_copied,
                "body_in_receipt": BODY_IN_RECEIPT,
                "expected_digest": expected_digest,
                "public_safe_expected_digest": public_safe_expected_digest,
                "actual_digest": actual_digest,
                "digest_matches": digest_matches,
                "source_digest_matches": source_digest_matches,
                "public_safe_digest_matches": public_safe_digest_matches,
                "source_to_target_relation": relation,
                "source_artifact_status": SOURCE_ARTIFACT_STATUS,
            }
        )
    return imports


def _source_artifact_findings(
    source_artifact_imports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_source_artifact_findings` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    for row in source_artifact_imports:
        source_ref = row["source_ref"]
        if not row["body_copied"]:
            findings.append(
                _finding(
                    "TARGET_SHAPE_SOURCE_ARTIFACT_MISSING",
                    "Required Ring2 target-shape source artifact was not copied into the public substrate input.",
                    case_id="source_artifact_import",
                    subject_id=source_ref,
                    subject_kind="source_ref",
                )
            )
        elif not row["digest_matches"]:
            findings.append(
                _finding(
                    "TARGET_SHAPE_SOURCE_ARTIFACT_DIGEST_MISMATCH",
                    "Copied Ring2 target-shape source artifact digest differs from the macro source digest.",
                    case_id="source_artifact_import",
                    subject_id=source_ref,
                    subject_kind="source_ref",
                )
            )
    return findings


def _source_open_body_import_summary(
    source_artifact_imports: list[dict[str, Any]],
    *,
    bundle_manifest: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_open_body_import_summary` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_summary = bundle_manifest.get("source_open_body_imports")
    if isinstance(manifest_summary, dict) and manifest_summary:
        return manifest_summary
    return {
        "status": PASS,
        "body_material_status": (
            "exact_copied_public_safe_ring2_target_shape_routing_bodies_with_digest_provenance"
        ),
        "body_material_count": sum(
            1
            for row in source_artifact_imports
            if row["body_copied"] and row["digest_matches"]
        ),
        "body_material_ids": [
            SOURCE_MATERIAL_IDS[row["source_ref"]]
            for row in source_artifact_imports
            if row["body_copied"] and row["digest_matches"]
        ],
        "material_classes": ["public_macro_receipt_body"],
        "aggregate_floor_ref": (
            "examples/target_shape_tactic_routing_gate/"
            "exported_target_shape_tactic_routing_bundle/"
            "bundle_manifest.json::copied_macro_body_artifacts"
        ),
        "source_manifest_refs": [SOURCE_MODULE_MANIFEST_REF],
        "body_in_receipt": BODY_IN_RECEIPT,
        "body_text_exported_in_receipts": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "proof_body_or_oracle_proof_text_exported": False,
            "provider_payload_exported": False,
            "lean_lake_execution_authorized": False,
            "formal_proof_authority": False,
            "runtime_correctness_claim": False,
            "release_authorized": False,
        },
    }


def _strings(value: Any) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _availability_status(row: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_availability_status` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for key in ("availability_status", "compile_status", "status"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return "unknown"


def _tactic_rows(payload: object) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_tactic_rows` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
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


def _portfolio(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_portfolio` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _tactic_rows(payload)
    available: list[str] = []
    unavailable: list[str] = []
    known: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        tactic_id = str(row.get("tactic_id") or "")
        if not tactic_id:
            continue
        known.append(tactic_id)
        by_id[tactic_id] = row
        status = _availability_status(row)
        if status in {"available", "pass", "compiled", "compile_pass"}:
            available.append(tactic_id)
        else:
            unavailable.append(tactic_id)
    return {
        "tactic_count": len(known),
        "known_tactic_ids": sorted(known),
        "available_tactic_ids": sorted(available),
        "unavailable_tactic_ids": sorted(unavailable),
        "tactics_by_id": by_id,
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
    - Teleology: Implements `_finding` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_record` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_forbidden_body_keys` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return sorted(key for key in FORBIDDEN_BODY_KEYS if key in row)


def _route_cases(payload: object) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_route_cases` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _rows(payload, "route_cases")


def _decision_for_tactic(
    tactic_id: str,
    *,
    allowed: set[str],
    known: set[str],
    available: set[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_decision_for_tactic` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    if tactic_id not in known:
        return {
            "tactic_id": tactic_id,
            "decision": "reject",
            "classifier": "UNPROBED_TACTIC",
            "reason": "tactic is not present in the declared public probe portfolio",
        }
    if tactic_id not in available:
        return {
            "tactic_id": tactic_id,
            "decision": "reject",
            "classifier": "UNAVAILABLE_TACTIC",
            "reason": "tactic is known but unavailable in the declared environment",
        }
    if tactic_id not in allowed:
        return {
            "tactic_id": tactic_id,
            "decision": "reject",
            "classifier": "TARGET_SHAPE_ADMISSIBILITY_REJECTED",
            "reason": "tactic is available but not admissible for this target shape",
        }
    return {
        "tactic_id": tactic_id,
        "decision": "allow",
        "classifier": "TARGET_SHAPE_ADMISSIBLE",
        "reason": "tactic is probed, available, and listed for this target shape",
    }


def _preferred_tactic_ids(target_shape: str) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_preferred_tactic_ids` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return list(
        PREFERRED_TACTICS_BY_TARGET_SHAPE.get(
            target_shape,
            DEFAULT_PREFERRED_TACTICS,
        )
    )


def _shape_preferred_selection(
    *,
    target_shape: str,
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_shape_preferred_selection` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    preferred_tactic_ids = _preferred_tactic_ids(target_shape)
    known_shape = target_shape in PREFERRED_TACTICS_BY_TARGET_SHAPE
    decision_by_tactic = {str(decision["tactic_id"]): decision for decision in decisions}
    allow_by_tactic = {
        str(decision["tactic_id"]): decision
        for decision in decisions
        if decision.get("decision") == "allow"
    }

    skipped_preferred: list[dict[str, Any]] = []
    for tactic_id in preferred_tactic_ids:
        if tactic_id in allow_by_tactic:
            fallback_reason = ""
            selection_basis = "shape_preferred_available"
            if not known_shape:
                selection_basis = "unknown_shape_default_preference"
                fallback_reason = (
                    "target shape has no specific preference map; used the default "
                    "safe tactic order"
                )
            elif skipped_preferred:
                selection_basis = "preferred_tactic_fallback"
                fallback_reason = (
                    "earlier preferred tactics were not selectable; used the next "
                    "available allowed tactic"
                )
            return {
                "computed_selected_tactic_id": tactic_id,
                "selection_basis": selection_basis,
                "fallback_reason": fallback_reason,
                "unknown_shape_default_used": not known_shape,
                "skipped_preferred_tactic_ids": [
                    str(row["tactic_id"]) for row in skipped_preferred
                ],
                "preferred_unavailable_tactic_ids": [
                    str(row["tactic_id"])
                    for row in skipped_preferred
                    if row.get("classifier") == "UNAVAILABLE_TACTIC"
                ],
                "preferred_unprobed_tactic_ids": [
                    str(row["tactic_id"])
                    for row in skipped_preferred
                    if row.get("classifier") == "UNPROBED_TACTIC"
                ],
                "preferred_not_allowed_tactic_ids": [
                    str(row["tactic_id"])
                    for row in skipped_preferred
                    if row.get("classifier") == "TARGET_SHAPE_ADMISSIBILITY_REJECTED"
                ],
            }
        decision = decision_by_tactic.get(tactic_id)
        if decision is not None:
            skipped_preferred.append(decision)

    first_allowed = next(iter(allow_by_tactic), "")
    return {
        "computed_selected_tactic_id": first_allowed,
        "selection_basis": "no_preferred_available_candidate_order_fallback"
        if first_allowed
        else "no_available_allowed_tactic",
        "fallback_reason": (
            "no preferred tactic was selectable; used the first available allowed "
            "candidate"
            if first_allowed
            else "no candidate was both available and allowed"
        ),
        "unknown_shape_default_used": not known_shape,
        "skipped_preferred_tactic_ids": [
            str(row["tactic_id"]) for row in skipped_preferred
        ],
        "preferred_unavailable_tactic_ids": [
            str(row["tactic_id"])
            for row in skipped_preferred
            if row.get("classifier") == "UNAVAILABLE_TACTIC"
        ],
        "preferred_unprobed_tactic_ids": [
            str(row["tactic_id"])
            for row in skipped_preferred
            if row.get("classifier") == "UNPROBED_TACTIC"
        ],
        "preferred_not_allowed_tactic_ids": [
            str(row["tactic_id"])
            for row in skipped_preferred
            if row.get("classifier") == "TARGET_SHAPE_ADMISSIBILITY_REJECTED"
        ],
    }


def _score_case(
    row: dict[str, Any],
    *,
    known: set[str],
    available: set[str],
    unavailable: set[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_score_case` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    route_case_id = str(row.get("route_case_id") or "route_case")
    target_shape = str(row.get("target_shape") or "")
    allowed = set(_strings(row.get("allowed_tactic_ids")))
    candidates = _strings(row.get("candidate_tactic_ids"))
    if not candidates:
        candidates = sorted(
            allowed
            | set(_strings(row.get("rejected_tactic_ids")))
            | set(_preferred_tactic_ids(target_shape))
        )
    decisions = [
        _decision_for_tactic(
            tactic_id,
            allowed=allowed,
            known=known,
            available=available,
        )
        for tactic_id in candidates
    ]
    declared_selected = str(row.get("selected_tactic_id") or "")
    selection = _shape_preferred_selection(
        target_shape=target_shape,
        decisions=decisions,
    )
    computed_selected = str(selection["computed_selected_tactic_id"])
    selected = computed_selected
    expected = str(row.get("expected_tactic_id") or selected)
    blocked_unavailable = sorted(allowed & unavailable)
    unprobed_allowed = sorted(allowed - known)
    route_stage = str(row.get("route_stage") or "pre_execution")
    integrity_codes: list[str] = []
    if blocked_unavailable:
        integrity_codes.append("TARGET_SHAPE_UNAVAILABLE_TACTIC_ADMITTED")
    if unprobed_allowed:
        integrity_codes.append("TARGET_SHAPE_UNPROBED_TACTIC_ALLOWED")
    if route_stage.startswith("post") or row.get("post_execution") is True:
        integrity_codes.append("TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN")
    if declared_selected and declared_selected != computed_selected:
        integrity_codes.append("TARGET_SHAPE_DECLARED_SELECTION_NOT_SHAPE_PREFERRED")
        if selection["unknown_shape_default_used"]:
            integrity_codes.append("TARGET_SHAPE_UNKNOWN_SHAPE_FALLBACK_REQUIRED")
        if declared_selected in selection["preferred_unavailable_tactic_ids"]:
            integrity_codes.append(
                "TARGET_SHAPE_PREFERRED_UNAVAILABLE_FALLBACK_REQUIRED"
            )
    return {
        "route_case_id": route_case_id,
        "target_shape": target_shape,
        "source_problem_id": row.get("source_problem_id"),
        "source_problem_ids": _strings(row.get("source_problem_ids")),
        "split": row.get("split"),
        "domain": row.get("domain"),
        "baseline_error_class": row.get("baseline_error_class"),
        "graph_candidate_id": row.get("graph_candidate_id"),
        "source_refs": _strings(row.get("source_refs")) or REAL_SUBSTRATE_REFS,
        "receipt_anchor_refs": _strings(row.get("receipt_anchor_refs"))
        or RECEIPT_ANCHOR_REFS,
        "source_digests": {
            key: SOURCE_DIGESTS[key]
            for key in _strings(row.get("source_digest_refs")) or REAL_SUBSTRATE_REFS
            if key in SOURCE_DIGESTS
        },
        "allowed_tactic_ids": sorted(allowed),
        "candidate_tactic_ids": sorted(candidates),
        "shape_preferred_tactic_ids": _preferred_tactic_ids(target_shape),
        "selection_basis": selection["selection_basis"],
        "fallback_reason": selection["fallback_reason"],
        "unknown_shape_default_used": selection["unknown_shape_default_used"],
        "skipped_preferred_tactic_ids": selection["skipped_preferred_tactic_ids"],
        "preferred_unavailable_tactic_ids": selection[
            "preferred_unavailable_tactic_ids"
        ],
        "preferred_unprobed_tactic_ids": selection["preferred_unprobed_tactic_ids"],
        "preferred_not_allowed_tactic_ids": selection[
            "preferred_not_allowed_tactic_ids"
        ],
        "declared_selected_tactic_id": declared_selected,
        "computed_selected_tactic_id": computed_selected,
        "selected_tactic_id": selected,
        "expected_tactic_id": expected,
        "expectation_met": selected == expected and not integrity_codes,
        "decisions": decisions,
        "blocked_unavailable_tactic_ids": blocked_unavailable,
        "unprobed_allowed_tactic_ids": unprobed_allowed,
        "integrity_codes": sorted(integrity_codes),
        "pre_execution": not integrity_codes
        or "TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN" not in integrity_codes,
        "body_in_receipt": BODY_IN_RECEIPT,
        "body_material_status": BODY_MATERIAL_STATUS,
        "routing_evidence_status": ROUTING_EVIDENCE_STATUS,
    }


def _route_integrity_findings(scored_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_route_integrity_findings` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    for case in scored_cases:
        case_id = str(case["route_case_id"])
        for tactic_id in case["blocked_unavailable_tactic_ids"]:
            findings.append(
                _finding(
                    "TARGET_SHAPE_UNAVAILABLE_TACTIC_ADMITTED",
                    "Route admitted a tactic marked unavailable by the public probe.",
                    case_id=case_id,
                    subject_id=tactic_id,
                    subject_kind="tactic_id",
                )
            )
        for tactic_id in case["unprobed_allowed_tactic_ids"]:
            findings.append(
                _finding(
                    "TARGET_SHAPE_UNPROBED_TACTIC_ALLOWED",
                    "Route admitted a tactic that is absent from the public probe portfolio.",
                    case_id=case_id,
                    subject_id=tactic_id,
                    subject_kind="tactic_id",
                )
            )
        if "TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN" in case["integrity_codes"]:
            findings.append(
                _finding(
                    "TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN",
                    "Target-shape routing must happen before Lean/proof execution evidence.",
                    case_id=case_id,
                    subject_id=case_id,
                    subject_kind="route_stage",
                )
            )
        if (
            "TARGET_SHAPE_DECLARED_SELECTION_NOT_SHAPE_PREFERRED"
            in case["integrity_codes"]
        ):
            findings.append(
                _finding(
                    "TARGET_SHAPE_DECLARED_SELECTION_NOT_SHAPE_PREFERRED",
                    "Declared tactic selection must match the computed shape-preferred available tactic.",
                    case_id=case_id,
                    subject_id=str(case["declared_selected_tactic_id"]),
                    subject_kind="selected_tactic_id",
                )
            )
        if "TARGET_SHAPE_UNKNOWN_SHAPE_FALLBACK_REQUIRED" in case["integrity_codes"]:
            findings.append(
                _finding(
                    "TARGET_SHAPE_UNKNOWN_SHAPE_FALLBACK_REQUIRED",
                    "Unknown target shapes must use the default safe tactic order rather than declared selection.",
                    case_id=case_id,
                    subject_id=str(case["declared_selected_tactic_id"]),
                    subject_kind="selected_tactic_id",
                )
            )
        if (
            "TARGET_SHAPE_PREFERRED_UNAVAILABLE_FALLBACK_REQUIRED"
            in case["integrity_codes"]
        ):
            findings.append(
                _finding(
                    "TARGET_SHAPE_PREFERRED_UNAVAILABLE_FALLBACK_REQUIRED",
                    "Unavailable preferred tactics must fall back to the next available allowed tactic.",
                    case_id=case_id,
                    subject_id=str(case["declared_selected_tactic_id"]),
                    subject_kind="selected_tactic_id",
                )
            )
    return findings


def _negative_findings(
    negative_payloads: dict[str, Any],
    *,
    known: set[str],
    available: set[str],
    unavailable: set[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_negative_findings` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)

    unavailable_negative = negative_payloads.get("unavailable_tactic_admitted")
    if isinstance(unavailable_negative, dict):
        case_id = str(
            unavailable_negative.get("expected_negative_case_id")
            or "unavailable_tactic_admitted"
        )
        for row in _route_cases(unavailable_negative) or [unavailable_negative]:
            for tactic_id in _strings(row.get("allowed_tactic_ids")):
                if tactic_id in unavailable:
                    _record(
                        findings,
                        observed,
                        "TARGET_SHAPE_UNAVAILABLE_TACTIC_ADMITTED",
                        "Route admitted an unavailable tactic before execution.",
                        case_id=case_id,
                        subject_id=tactic_id,
                        subject_kind="tactic_id",
                    )

    unprobed_negative = negative_payloads.get("unprobed_tactic_allowed")
    if isinstance(unprobed_negative, dict):
        case_id = str(
            unprobed_negative.get("expected_negative_case_id")
            or "unprobed_tactic_allowed"
        )
        for row in _route_cases(unprobed_negative) or [unprobed_negative]:
            for tactic_id in _strings(row.get("allowed_tactic_ids")):
                if tactic_id not in known:
                    _record(
                        findings,
                        observed,
                        "TARGET_SHAPE_UNPROBED_TACTIC_ALLOWED",
                        "Route admitted a tactic absent from the public probe portfolio.",
                        case_id=case_id,
                        subject_id=tactic_id,
                        subject_kind="tactic_id",
                    )

    shape_preference_negative = negative_payloads.get(
        "shape_preferred_tactic_overridden"
    )
    if isinstance(shape_preference_negative, dict):
        case_id = str(
            shape_preference_negative.get("expected_negative_case_id")
            or "shape_preferred_tactic_overridden"
        )
        for row in _route_cases(shape_preference_negative) or [
            shape_preference_negative
        ]:
            case = _score_case(
                row,
                known=known,
                available=available,
                unavailable=unavailable,
            )
            if (
                "TARGET_SHAPE_DECLARED_SELECTION_NOT_SHAPE_PREFERRED"
                in case["integrity_codes"]
            ):
                _record(
                    findings,
                    observed,
                    "TARGET_SHAPE_DECLARED_SELECTION_NOT_SHAPE_PREFERRED",
                    "Declared tactic selection did not match the computed target-shape preference.",
                    case_id=case_id,
                    subject_id=str(case["declared_selected_tactic_id"]),
                    subject_kind="selected_tactic_id",
                )

    unknown_shape_negative = negative_payloads.get("unknown_shape_fallback")
    if isinstance(unknown_shape_negative, dict):
        case_id = str(
            unknown_shape_negative.get("expected_negative_case_id")
            or "unknown_shape_fallback"
        )
        for row in _route_cases(unknown_shape_negative) or [unknown_shape_negative]:
            case = _score_case(
                row,
                known=known,
                available=available,
                unavailable=unavailable,
            )
            if "TARGET_SHAPE_UNKNOWN_SHAPE_FALLBACK_REQUIRED" in case["integrity_codes"]:
                _record(
                    findings,
                    observed,
                    "TARGET_SHAPE_UNKNOWN_SHAPE_FALLBACK_REQUIRED",
                    "Unknown target shape did not respect the computed default fallback.",
                    case_id=case_id,
                    subject_id=str(case["declared_selected_tactic_id"]),
                    subject_kind="selected_tactic_id",
                )

    unavailable_fallback_negative = negative_payloads.get(
        "preferred_unavailable_fallback"
    )
    if isinstance(unavailable_fallback_negative, dict):
        case_id = str(
            unavailable_fallback_negative.get("expected_negative_case_id")
            or "preferred_unavailable_fallback"
        )
        for row in _route_cases(unavailable_fallback_negative) or [
            unavailable_fallback_negative
        ]:
            case = _score_case(
                row,
                known=known,
                available=available,
                unavailable=unavailable,
            )
            if (
                "TARGET_SHAPE_PREFERRED_UNAVAILABLE_FALLBACK_REQUIRED"
                in case["integrity_codes"]
            ):
                _record(
                    findings,
                    observed,
                    "TARGET_SHAPE_PREFERRED_UNAVAILABLE_FALLBACK_REQUIRED",
                    "Unavailable preferred tactic did not fall back to the next available allowed tactic.",
                    case_id=case_id,
                    subject_id=str(case["declared_selected_tactic_id"]),
                    subject_kind="selected_tactic_id",
                )

    proof_negative = negative_payloads.get("proof_body_leakage")
    if isinstance(proof_negative, dict):
        case_id = str(
            proof_negative.get("expected_negative_case_id") or "proof_body_leakage"
        )
        for row in _route_cases(proof_negative) or [proof_negative]:
            if _forbidden_body_keys(row):
                _record(
                    findings,
                    observed,
                    "TARGET_SHAPE_PROOF_BODY_FORBIDDEN",
                    "Routing fixtures cannot carry proof, provider, or Lean body fields.",
                    case_id=case_id,
                    subject_id=str(row.get("route_case_id") or "route_case"),
                    subject_kind="route_case",
                )

    post_negative = negative_payloads.get("post_execution_route")
    if isinstance(post_negative, dict):
        case_id = str(
            post_negative.get("expected_negative_case_id") or "post_execution_route"
        )
        for row in _route_cases(post_negative) or [post_negative]:
            route_stage = str(row.get("route_stage") or "pre_execution")
            post_markers = (
                route_stage.startswith("post")
                or row.get("post_execution") is True
                or "lean_receipt_ref" in row
                or "execution_result" in row
            )
            if post_markers:
                _record(
                    findings,
                    observed,
                    "TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN",
                    "Routing must be selected before proof execution evidence exists.",
                    case_id=case_id,
                    subject_id=str(row.get("route_case_id") or "route_case"),
                    subject_kind="route_stage",
                )

    release_negative = negative_payloads.get("release_overclaim")
    if isinstance(release_negative, dict):
        case_id = str(
            release_negative.get("expected_negative_case_id") or "release_overclaim"
        )
        overclaim_fields = [
            field
            for field in (
                "release_authorized",
                "publication_authorized",
                "formal_proof_authority",
                "provider_calls_authorized",
                "lean_lake_execution_authorized",
            )
            if release_negative.get(field) is True
        ]
        if overclaim_fields:
            _record(
                findings,
                observed,
                "TARGET_SHAPE_RELEASE_OVERCLAIM",
                "Target-shape routing attempted to authorize release, proof authority, providers, or Lean execution.",
                case_id=case_id,
                subject_id=",".join(sorted(overclaim_fields)),
                subject_kind="authority_ceiling",
            )

    return {
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def _build_board(*, result: dict[str, Any], secret_scan: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_board` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "target_shape_tactic_routing_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_contract": {
            "routing_pre_execution": True,
            "shape_admissibility_before_search": True,
            "shape_preferred_tactic_computed": True,
            "unknown_shape_default_fallback_computed": True,
            "preferred_unavailable_fallback_computed": True,
            "declared_selection_must_match_computed_preference": True,
            "unavailable_tactics_rejected": True,
            "unprobed_tactics_rejected": True,
            "source_artifact_digest_verification_required": True,
            "source_artifacts_copied": result["source_artifacts_pass"],
            "proof_bodies_excluded": True,
            "lean_lake_not_run": True,
            "body_in_receipt": BODY_IN_RECEIPT,
            "body_material_status": BODY_MATERIAL_STATUS,
            "source_artifact_status": SOURCE_ARTIFACT_STATUS,
        },
        "routing_projection": {
            "tactic_count": result["tactic_count"],
            "available_tactic_ids": result["available_tactic_ids"],
            "unavailable_tactic_ids": result["unavailable_tactic_ids"],
            "route_case_count": result["route_case_count"],
            "target_shapes": result["target_shapes"],
            "selected_tactic_ids": result["selected_tactic_ids"],
            "shape_decisions": result["scored_route_cases"],
            "body_in_receipt": BODY_IN_RECEIPT,
            "routing_evidence_status": ROUTING_EVIDENCE_STATUS,
        },
        "secret_exclusion_scan": secret_scan,
        "body_material_status": BODY_MATERIAL_STATUS,
        "source_artifact_status": SOURCE_ARTIFACT_STATUS,
        "source_artifact_count": result["source_artifact_count"],
        "copied_source_artifact_count": result["copied_source_artifact_count"],
        "source_artifacts_pass": result["source_artifacts_pass"],
        "source_artifact_imports": result["source_artifact_imports"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "routing_evidence_status": ROUTING_EVIDENCE_STATUS,
        "real_substrate_refs": REAL_SUBSTRATE_REFS,
        "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
        "source_digests": SOURCE_DIGESTS,
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
    - Teleology: Implements `_common_receipt` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
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
        "source_artifact_status",
        "source_artifact_count",
        "copied_source_artifact_count",
        "source_artifacts_pass",
        "source_artifact_imports",
        "source_module_manifest_ref",
        "source_open_body_imports",
        "routing_evidence_status",
        "body_in_receipt",
        "real_substrate_refs",
        "receipt_anchor_refs",
        "source_digests",
        "authority_ceiling",
        "anti_claim",
        "tactic_count",
        "available_tactic_ids",
        "unavailable_tactic_ids",
        "route_case_count",
        "target_shapes",
        "selected_tactic_ids",
        "all_expectations_met",
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


def _shape_decision_card(row: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_shape_decision_card` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    card = {
        "route_case_id": row.get("route_case_id"),
        "target_shape": row.get("target_shape"),
        "selected_tactic_id": row.get("selected_tactic_id"),
        "computed_selected_tactic_id": row.get("computed_selected_tactic_id"),
    }
    if row.get("declared_selected_tactic_id") != row.get("computed_selected_tactic_id"):
        card["declared_selected_tactic_id"] = row.get("declared_selected_tactic_id")
    if row.get("selection_basis") != "shape_preferred_available":
        card["shape_preferred_tactic_ids"] = row.get("shape_preferred_tactic_ids", [])
        card["selection_basis"] = row.get("selection_basis")
    skipped = row.get("skipped_preferred_tactic_ids", [])
    if skipped:
        card["skipped_preferred_tactic_ids"] = skipped
    unavailable = row.get("preferred_unavailable_tactic_ids", [])
    if unavailable:
        card["preferred_unavailable_tactic_ids"] = unavailable
    if row.get("unknown_shape_default_used"):
        card["unknown_shape_default_used"] = True
    return card


def _result_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_result_card` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    secret_scan = result.get("secret_exclusion_scan")
    scan_summary = secret_scan if isinstance(secret_scan, dict) else {}
    source_open = result.get("source_open_body_imports")
    source_open_summary = source_open if isinstance(source_open, dict) else {}
    action = (
        "run-routing-bundle"
        if result.get("input_mode") == "exported_target_shape_tactic_routing_bundle"
        else "run"
    )
    card_id = (
        "target_shape_tactic_routing_bundle_card"
        if action == "run-routing-bundle"
        else "target_shape_tactic_routing_fixture_card"
    )
    scored_cases = result.get("scored_route_cases", [])
    if not isinstance(scored_cases, list):
        scored_cases = []
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "command": result.get("command"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "card_id": card_id,
        "output_profile": "compact_card_no_full_routing_board_or_route_rows",
        "full_output_available": True,
        "full_output_command": (
            "python -m microcosm_core.organs.target_shape_tactic_routing_gate "
            f"{action} --input <input> --out <out>"
        ),
        "receipt_paths": result.get("receipt_paths", []),
        "expected_negative_cases": result.get("expected_negative_cases", []),
        "missing_negative_cases": result.get("missing_negative_cases", []),
        "error_codes": result.get("error_codes", []),
        "routing_evidence_status": result.get("routing_evidence_status"),
        "body_material_status": result.get("body_material_status"),
        "body_in_receipt": result.get("body_in_receipt"),
        "route_case_count": result.get("route_case_count"),
        "target_shape_count": len(result.get("target_shapes", [])),
        "selected_tactic_ids": result.get("selected_tactic_ids", []),
        "tactic_portfolio": {
            "tactic_count": result.get("tactic_count"),
            "known_tactic_ids": result.get("known_tactic_ids", []),
            "available_tactic_ids": result.get("available_tactic_ids", []),
            "unavailable_tactic_ids": result.get("unavailable_tactic_ids", []),
        },
        "shape_decision_summary": [
            _shape_decision_card(row)
            for row in scored_cases
            if isinstance(row, dict)
        ],
        "source_artifact_summary": {
            "status": result.get("source_artifact_status"),
            "source_artifact_count": result.get("source_artifact_count"),
            "copied_source_artifact_count": result.get("copied_source_artifact_count"),
            "source_artifacts_pass": result.get("source_artifacts_pass"),
            "source_module_manifest_ref": result.get("source_module_manifest_ref"),
            "real_substrate_ref_count": len(result.get("real_substrate_refs", [])),
            "receipt_anchor_ref_count": len(result.get("receipt_anchor_refs", [])),
            "digest_ref_count": len(result.get("source_digests", {})),
        },
        "source_open_body_imports_summary": {
            "status": source_open_summary.get("status"),
            "body_material_count": source_open_summary.get("body_material_count"),
            "body_in_receipt": source_open_summary.get("body_in_receipt"),
            "body_text_exported_in_receipts": source_open_summary.get(
                "body_text_exported_in_receipts"
            ),
            "body_material_status": source_open_summary.get("body_material_status"),
        },
        "secret_exclusion_scan_summary": {
            "status": scan_summary.get("status"),
            "scanned_path_count": scan_summary.get("scanned_path_count"),
            "hit_count": scan_summary.get("hit_count"),
            "blocking_hit_count": scan_summary.get("blocking_hit_count"),
            "body_in_receipt": scan_summary.get("body_in_receipt"),
            "body_material_status": scan_summary.get("body_material_status"),
        },
        "authority_ceiling": result.get("authority_ceiling"),
        "all_expectations_met": result.get("all_expectations_met"),
        "anti_claim_summary": (
            "pre_execution_shape_route_check_not_lean_lake_proof_or_release_authority"
        ),
        "output_economy": {
            "full_routing_board_omitted": True,
            "full_scored_route_cases_omitted": True,
            "source_artifact_import_rows_omitted": True,
            "secret_scan_hits_omitted": True,
            "full_payload_drilldown": "rerun without --card",
        },
    }


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_relative_receipt_paths` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [_display(path, public_root=public_root) for path in paths.values()]


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_result` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    negative_payloads = {
        name: payloads[name] for name in NEGATIVE_INPUT_NAMES_STEMS if name in payloads
    }
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    secret_scan["body_material_status"] = "secret_exclusion_scan_no_payload_body_export"

    portfolio = _portfolio(payloads["tactic_portfolio_availability"])
    known = set(portfolio["known_tactic_ids"])
    available = set(portfolio["available_tactic_ids"])
    unavailable = set(portfolio["unavailable_tactic_ids"])
    scored_cases = [
        _score_case(
            row,
            known=known,
            available=available,
            unavailable=unavailable,
        )
        for row in _route_cases(payloads["target_shape_routes"])
    ]
    route_findings = _route_integrity_findings(scored_cases)
    source_artifact_imports = _source_artifact_imports(
        input_dir,
        public_root=public_root,
    )
    source_artifact_findings = _source_artifact_findings(source_artifact_imports)
    copied_source_artifact_count = sum(
        1
        for row in source_artifact_imports
        if row["body_copied"] and row["digest_matches"]
    )
    source_artifacts_pass = copied_source_artifact_count == len(REAL_SUBSTRATE_REFS)
    negative = _negative_findings(
        negative_payloads,
        known=known,
        available=available,
        unavailable=unavailable,
    )
    observed = negative["observed_negative_cases"]
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = [*route_findings, *negative["findings"], *source_artifact_findings]
    error_codes = sorted({finding["error_code"] for finding in findings})
    all_expectations_met = all(row["expectation_met"] for row in scored_cases)
    status = (
        PASS
        if not missing
        and not route_findings
        and not source_artifact_findings
        and all_expectations_met
        and not secret_scan["blocking_hit_count"]
        else "blocked"
    )
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    source_module_manifest_path = input_dir / "source_module_manifest.json"
    source_module_manifest_ref = (
        _display(source_module_manifest_path, public_root=public_root)
        if source_module_manifest_path.is_file()
        else SOURCE_MODULE_MANIFEST_REF
    )
    source_open_body_imports = _source_open_body_import_summary(
        source_artifact_imports,
        bundle_manifest=bundle_manifest,
    )
    result = {
        "schema_version": "target_shape_tactic_routing_gate_result_v1",
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
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "body_material_status": BODY_MATERIAL_STATUS,
        "source_artifact_status": SOURCE_ARTIFACT_STATUS,
        "source_artifact_imports": source_artifact_imports,
        "source_artifact_count": len(source_artifact_imports),
        "copied_source_artifact_count": copied_source_artifact_count,
        "source_artifacts_pass": source_artifacts_pass,
        "source_module_manifest_ref": source_module_manifest_ref,
        "source_open_body_imports": source_open_body_imports,
        "routing_evidence_status": ROUTING_EVIDENCE_STATUS,
        "body_in_receipt": BODY_IN_RECEIPT,
        "real_substrate_refs": REAL_SUBSTRATE_REFS,
        "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
        "source_digests": SOURCE_DIGESTS,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "tactic_count": portfolio["tactic_count"],
        "known_tactic_ids": portfolio["known_tactic_ids"],
        "available_tactic_ids": portfolio["available_tactic_ids"],
        "unavailable_tactic_ids": portfolio["unavailable_tactic_ids"],
        "route_case_count": len(scored_cases),
        "target_shapes": sorted({row["target_shape"] for row in scored_cases}),
        "selected_tactic_ids": sorted(
            {row["selected_tactic_id"] for row in scored_cases if row["selected_tactic_id"]}
        ),
        "scored_route_cases": sorted(
            scored_cases,
            key=lambda item: item["route_case_id"],
        ),
        "all_expectations_met": all_expectations_met,
    }
    result["routing_board"] = _build_board(result=result, secret_scan=secret_scan)
    return result


def write_receipts(
    out_dir: str | Path,
    result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    """
    [ACTION]
    - Teleology: Implements `write_receipts` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
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
        schema_version="target_shape_tactic_routing_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    result_receipt.update(
        {
            "scored_route_cases": result["scored_route_cases"],
            "routing_board": result["routing_board"],
        }
    )
    board_receipt = _common_receipt(
        result,
        schema_version="target_shape_tactic_routing_board_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board_payload = dict(result["routing_board"])
    board_receipt["board_schema_version"] = board_payload.pop("schema_version")
    board_receipt.update(board_payload)
    validation = _common_receipt(
        result,
        schema_version="target_shape_tactic_routing_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "routing_pre_execution": True,
            "shape_preferred_tactic_computed": True,
            "unknown_shape_default_fallback_computed": True,
            "preferred_unavailable_fallback_computed": True,
            "declared_selection_must_match_computed_preference": True,
            "unavailable_tactics_rejected": True,
            "unprobed_tactics_rejected": True,
            "proof_bodies_excluded": True,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="target_shape_tactic_routing_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "projection_status": "real_ring2_target_shape_routing_landed"
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
    - Teleology: Implements `run` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.target_shape_tactic_routing_gate run "
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


def run_routing_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_routing_bundle` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.target_shape_tactic_routing_gate "
        f"run-routing-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_target_shape_tactic_routing_bundle",
        include_negative=False,
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    receipt_path = target / BUNDLE_RESULT_NAME
    receipt_ref = _display(receipt_path, public_root=public_root)
    receipt_in_public_root = receipt_path.resolve(strict=False).is_relative_to(
        public_root.resolve(strict=False)
    )
    if not receipt_in_public_root and "receipts" in receipt_path.parts:
        receipts_index = len(receipt_path.parts) - 1 - list(reversed(receipt_path.parts)).index("receipts")
        receipt_ref = Path(*receipt_path.parts[receipts_index:]).as_posix()
    receipt = _common_receipt(
        result,
        schema_version="target_shape_tactic_routing_exported_bundle_receipt_v1",
        receipt_paths=[receipt_ref],
    )
    receipt.update(
        {
            "scored_route_cases": result["scored_route_cases"],
            "routing_board": result["routing_board"],
        }
    )
    write_json_atomic(receipt_path, receipt)
    result["receipt_paths"] = [receipt_ref]
    return result


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `_parser` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(
        description="Validate target-shape tactic routing before proof execution"
    )
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact first-screen card instead of the full result payload.",
    )
    bundle_parser = subparsers.add_parser("run-routing-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact first-screen card instead of the full result payload.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.target_shape_tactic_routing_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    card_suffix = " --card" if getattr(args, "card", False) else ""
    if args.action == "run":
        command = (
            "python -m microcosm_core.organs.target_shape_tactic_routing_gate run "
            f"--input {args.input} --out {args.out}{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-routing-bundle":
        command = (
            "python -m microcosm_core.organs.target_shape_tactic_routing_gate "
            f"run-routing-bundle --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run_routing_bundle(args.input, args.out, command=command)
    else:
        return 2
    output = _result_card(result) if getattr(args, "card", False) else result
    print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
