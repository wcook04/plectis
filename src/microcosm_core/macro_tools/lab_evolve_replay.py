"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.macro_tools.lab_evolve_replay` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: PASS, BLOCKED, SOURCE_REFS, SOURCE_SYMBOL_REFS, TARGET_REFS, TARGET_SYMBOL_REFS, GRAPH_NODES, GRAPH_EDGES, AUTHORITY_CEILING, build_materials_lab_evolve_replay, build_materials_lab_evolve_replay_from_dir, main
- Reads: call arguments, module constants, imported helpers.
- Writes: return values, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.schemas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from microcosm_core.schemas import read_json_strict

PASS = "pass"
BLOCKED = "blocked"

SOURCE_REFS = [
    "self-indexing-cognitive-substrate/src/idea_microcosm/lab_evolve_failure_replay_specimen.py",
    "self-indexing-cognitive-substrate/microcosms/lab_evolve_failure_replay/replay_graph.json",
    "self-indexing-cognitive-substrate/microcosms/lab_evolve_failure_replay/receipt.json",
    "codex/doctrine/paper_modules/lab_oracle_evolve_pipeline.md",
    "codex/standards/std_laboratory.json",
]
SOURCE_SYMBOL_REFS = [
    "idea_microcosm.lab_evolve_failure_replay_specimen::GRAPH_NODES",
    "idea_microcosm.lab_evolve_failure_replay_specimen::_case_result",
    "idea_microcosm.lab_evolve_failure_replay_specimen::_global_teaching_ledger",
    "idea_microcosm.lab_evolve_failure_replay_specimen::_source_capsule_provenance",
    "idea_microcosm.lab_evolve_failure_replay_specimen::_grammar_bridge_case",
]
TARGET_REFS = [
    "microcosm-substrate/src/microcosm_core/macro_tools/lab_evolve_replay.py",
]
TARGET_SYMBOL_REFS = [
    "microcosm_core.macro_tools.lab_evolve_replay::build_materials_lab_evolve_replay",
    "microcosm_core.macro_tools.lab_evolve_replay::build_materials_lab_evolve_replay_from_dir",
    "microcosm_core.macro_tools.lab_evolve_replay::main",
]
GRAPH_NODES = [
    {
        "node_id": "candidate_material",
        "node_type": "source",
        "contract": "Accept body-free public candidate metadata and literature capsule refs.",
        "restartable": False,
    },
    {
        "node_id": "safety_screen_gate",
        "node_type": "boundary",
        "contract": "Reject wetlab, controlled-target, credential, robot, notebook, and discovery authority.",
        "restartable": True,
    },
    {
        "node_id": "simulator_experiment_plan",
        "node_type": "transform",
        "contract": "Bind candidates to simulator-only experiment refs and cold replay refs.",
        "restartable": True,
    },
    {
        "node_id": "simulator_assay",
        "node_type": "evaluator",
        "contract": "Evaluate only public simulator proxy rows, never live assay data.",
        "restartable": False,
    },
    {
        "node_id": "active_learning_decision",
        "node_type": "decision",
        "contract": "Choose the next simulator-only action class without robot execution.",
        "restartable": True,
    },
    {
        "node_id": "classify_failure",
        "node_type": "failure_classifier",
        "contract": "Localize a blocked row to the nearest authority boundary.",
        "restartable": False,
    },
    {
        "node_id": "choose_restart_point",
        "node_type": "restart",
        "contract": "Restart from the nearest body-free public row rather than replaying the whole graph.",
        "restartable": False,
    },
    {
        "node_id": "record_teaching",
        "node_type": "teaching",
        "contract": "Carry the source clip hash, restart point, and anti-claim together.",
        "restartable": False,
    },
]
GRAPH_EDGES = [
    ["candidate_material", "safety_screen_gate"],
    ["safety_screen_gate", "simulator_experiment_plan"],
    ["simulator_experiment_plan", "simulator_assay"],
    ["simulator_assay", "active_learning_decision"],
    ["active_learning_decision", "classify_failure"],
    ["classify_failure", "choose_restart_point"],
    ["choose_restart_point", "record_teaching"],
]
AUTHORITY_CEILING = {
    "simulator_only": True,
    "wetlab_protocol_authorized": False,
    "hazardous_synthesis_authorized": False,
    "reagent_amounts_authorized": False,
    "controlled_substance_target_authorized": False,
    "bioactivity_target_authorized": False,
    "live_lab_credentials_authorized": False,
    "robot_command_authorized": False,
    "private_lab_notebook_exported": False,
    "live_assay_data_exported": False,
    "discovery_claim_authorized": False,
    "benchmark_score_claim_authorized": False,
    "release_authorized": False,
}


def _json_sha256(payload: object) -> str:
    """
    [ACTION]
    - Teleology: Implements `_json_sha256` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    stable = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_rows` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _by_ref(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_by_ref` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {str(row[field]): row for row in rows if row.get(field)}


def _source_clip(case: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_clip` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "case_id": case["case_id"],
        "candidate_material_ref": case.get("candidate_material_ref"),
        "experiment_ref": case.get("experiment_ref"),
        "assay_ref": case.get("assay_ref"),
        "decision_ref": case.get("decision_ref"),
        "safety_screen_ref": case.get("safety_screen_ref"),
        "cold_replay_ref": case.get("cold_replay_ref"),
        "failure_class": case.get("failure_class"),
        "restart_point": case.get("restart_point"),
        "teaching_rule": case.get("teaching_rule"),
    }


def _capsule(case: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_capsule` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    clip = _source_clip(case)
    return {
        "capsule_id": f"source_capsule.{case['case_id']}",
        "status": PASS,
        "source_class": "public_materials_lab_evolve_replay_case",
        "source_ref": case.get("source_ref"),
        "clip_hash_algorithm": "sha256",
        "clip_hash": _json_sha256(clip),
        "source_clip": clip,
        "semantic_carryforward": {
            "case_id": case["case_id"],
            "failure_class": case.get("failure_class"),
            "restart_point": case.get("restart_point"),
            "teaching_ref": case.get("teaching_id"),
            "source_clip_hash": _json_sha256(clip),
            "body_in_receipt": False,
        },
        "authority_boundary": (
            "Capsule hashes prove deterministic public replay carryforward only; "
            "they are not chemistry safety proof, wetlab authority, benchmark evidence, "
            "publication permission, or release authorization."
        ),
    }


def _positive_case(
    experiment: dict[str, Any],
    *,
    candidate_by_id: dict[str, dict[str, Any]],
    assay_by_id: dict[str, dict[str, Any]],
    decision_by_experiment: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_positive_case` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    experiment_id = str(experiment.get("experiment_id") or "unknown_experiment")
    candidate_id = str(experiment.get("candidate_material_ref") or "")
    assay_id = str(experiment.get("assay_ref") or "")
    candidate = candidate_by_id.get(candidate_id, {})
    assay = assay_by_id.get(assay_id, {})
    decision = decision_by_experiment.get(experiment_id, {})
    valid_boundary = (
        candidate.get("controlled_substance_target") is False
        and candidate.get("bioactivity_target") is False
        and candidate.get("discovery_claim") is False
        and experiment.get("simulator_only") is True
        and experiment.get("wetlab_protocol_exported") is False
        and experiment.get("hazardous_synthesis_steps_exported") is False
        and experiment.get("reagent_amounts_included") is False
        and experiment.get("robot_command_authorized") is False
        and experiment.get("live_lab_credentials_present") is False
        and experiment.get("private_lab_notebook_exported") is False
        and assay.get("live_assay_data_exported") is False
        and assay.get("discovery_claim") is False
        and decision.get("live_robot_command_emitted") is False
        and decision.get("discovery_claim") is False
    )
    case = {
        "case_id": f"materials_lab_case.{experiment_id}",
        "source_ref": f"experiment_dag.experiments[{experiment_id}]",
        "candidate_material_ref": candidate_id,
        "experiment_ref": experiment_id,
        "assay_ref": assay_id,
        "decision_ref": decision.get("decision_id"),
        "safety_screen_ref": experiment.get("safety_screen_ref") or candidate.get("safety_screen_ref"),
        "cold_replay_ref": experiment.get("cold_replay_ref") or decision.get("cold_replay_ref"),
        "failure_class": None if valid_boundary else "authority_boundary_violation",
        "restart_point": None if valid_boundary else "safety_screen_gate",
        "status": PASS if valid_boundary else BLOCKED,
        "teaching_id": f"teaching.{experiment_id}.simulator_boundary",
        "teaching_rule": (
            "When the candidate, safety screen, simulator assay, decision, and cold "
            "replay refs are valid, freeze those public refs and keep wetlab, robot, "
            "credential, and discovery authority outside the replay graph."
        ),
    }
    return {**case, "source_capsule": _capsule(case)}


def _restart_point(subject_kind: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_restart_point` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "candidate_material": "candidate_material",
        "experiment": "simulator_experiment_plan",
        "simulator_assay": "simulator_assay",
        "active_learning_decision": "active_learning_decision",
        "protocol": "safety_screen_gate",
        "policy": "safety_screen_gate",
    }.get(subject_kind, "safety_screen_gate")


def _boundary_case(finding: dict[str, Any], index: int) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_boundary_case` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    subject_kind = str(finding.get("subject_kind") or "unknown")
    error_code = str(finding.get("error_code") or "unknown_error")
    subject_id = str(finding.get("subject_id") or f"finding_{index}")
    negative_case_id = str(finding.get("negative_case_id") or "positive_fixture")
    restart_point = _restart_point(subject_kind)
    case = {
        "case_id": f"materials_lab_boundary.{negative_case_id}.{index}",
        "source_ref": f"negative_case_findings[{negative_case_id}:{subject_id}]",
        "candidate_material_ref": subject_id if subject_kind == "candidate_material" else None,
        "experiment_ref": subject_id if subject_kind == "experiment" else None,
        "assay_ref": subject_id if subject_kind == "simulator_assay" else None,
        "decision_ref": subject_id if subject_kind == "active_learning_decision" else None,
        "safety_screen_ref": None,
        "cold_replay_ref": None,
        "failure_class": error_code,
        "restart_point": restart_point,
        "status": BLOCKED,
        "teaching_id": f"teaching.{negative_case_id}.{error_code.lower()}",
        "teaching_rule": (
            "When this authority boundary fires, keep only the body-free finding "
            "metadata, restart from the nearest public row, and rerun the validator "
            "before any accepted receipt can be treated as product substrate."
        ),
    }
    return {**case, "source_capsule": _capsule(case)}


def _teaching_ledger(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_teaching_ledger` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = [
        {
            "teaching_id": case["teaching_id"],
            "case_id": case["case_id"],
            "status": case["status"],
            "failure_class": case.get("failure_class"),
            "restart_point": case.get("restart_point"),
            "source_capsule_ref": case["source_capsule"]["capsule_id"],
        }
        for case in cases
    ]
    restart_counts = Counter(str(row.get("restart_point") or "none") for row in rows)
    failure_counts = Counter(str(row.get("failure_class") or "none") for row in rows)
    return {
        "kind": "materials_lab_evolve_teaching_ledger",
        "schema_version": "materials_lab_evolve_teaching_ledger_v0",
        "local_teachings": rows,
        "summary": {
            "teaching_count": len(rows),
            "restart_point_counts": dict(sorted(restart_counts.items())),
            "failure_class_counts": dict(sorted(failure_counts.items())),
        },
        "global_rule_candidates": [
            {
                "rule_id": "rule.materials_public_replay_boundary_restart",
                "status": "candidate_global_rule_local_public_replay_only",
                "observed_case_count": len(rows),
                "rule": (
                    "A public science replay can carry candidate, simulator, decision, "
                    "failure, restart, and teaching refs as product substrate only when "
                    "source clips are body-free and wetlab, credential, robot, private "
                    "notebook, discovery, benchmark, publication, and release authority stay false."
                ),
                "evidence_refs": [case["source_capsule"]["capsule_id"] for case in cases],
            }
        ],
    }


def build_materials_lab_evolve_replay(
    payloads: dict[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_materials_lab_evolve_replay` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    candidates = _rows(payloads.get("candidate_materials", {}), "candidate_materials")
    experiments = _rows(payloads.get("experiment_dag", {}), "experiments")
    assays = _rows(payloads.get("simulator_assays", {}), "simulator_assays")
    decisions = _rows(
        payloads.get("active_learning_decisions", {}),
        "active_learning_decisions",
    )
    candidate_by_id = _by_ref(candidates, "candidate_material_id")
    assay_by_id = _by_ref(assays, "assay_id")
    decision_by_experiment = {
        str(row["experiment_ref"]): row for row in decisions if row.get("experiment_ref")
    }
    positive_cases = [
        _positive_case(
            experiment,
            candidate_by_id=candidate_by_id,
            assay_by_id=assay_by_id,
            decision_by_experiment=decision_by_experiment,
        )
        for experiment in experiments
    ]
    boundary_cases = [
        _boundary_case(finding, index)
        for index, finding in enumerate(findings, start=1)
        if isinstance(finding, dict)
    ]
    cases = [*positive_cases, *boundary_cases]
    capsules = [case["source_capsule"] for case in cases]
    summary = {
        "candidate_material_count": len(candidates),
        "experiment_count": len(experiments),
        "simulator_assay_count": len(assays),
        "active_learning_decision_count": len(decisions),
        "replay_case_count": len(positive_cases),
        "boundary_case_count": len(boundary_cases),
        "source_capsule_count": len(capsules),
        "semantic_carryforward_count": sum(1 for capsule in capsules if capsule.get("semantic_carryforward")),
        "public_safe_source_count": sum(
            1
            for capsule in capsules
            if capsule.get("source_class") == "public_materials_lab_evolve_replay_case"
        ),
        "wetlab_protocol_export_count": 0,
        "robot_command_count": 0,
        "discovery_claim_count": 0,
    }
    status = PASS if all(case["status"] == PASS for case in positive_cases) else BLOCKED
    return {
        "schema_version": "materials_lab_evolve_replay_refactor_v0",
        "status": status,
        "source_refs": list(SOURCE_REFS),
        "source_symbols": list(SOURCE_SYMBOL_REFS),
        "target_refs": list(TARGET_REFS),
        "target_symbols": list(TARGET_SYMBOL_REFS),
        "graph": {
            "graph_id": "materials_lab_evolve_failure_replay_graph",
            "nodes": GRAPH_NODES,
            "edges": GRAPH_EDGES,
        },
        "cases": cases,
        "global_teaching_ledger": _teaching_ledger(cases),
        "source_capsule_provenance": {
            "kind": "source_capsule_provenance",
            "schema_version": "source_capsule_provenance_v0",
            "status": PASS,
            "hash_algorithm": "sha256",
            "capsule_count": len(capsules),
            "source_capsules": capsules,
            "carryforward_contract": {
                "required_fields": [
                    "case_id",
                    "failure_class",
                    "restart_point",
                    "teaching_ref",
                    "source_clip_hash",
                    "body_in_receipt",
                ],
                "rule": (
                    "Every reusable teaching must carry its body-free source clip, "
                    "deterministic hash, restart point, and authority anti-claim."
                ),
            },
            "summary": {
                "capsule_count": len(capsules),
                "semantic_carryforward_count": summary["semantic_carryforward_count"],
                "hashed_source_clip_count": len([capsule for capsule in capsules if capsule.get("clip_hash")]),
                "public_safe_source_count": summary["public_safe_source_count"],
            },
        },
        "summary": summary,
        "source_faithful_refactor": {
            "source_ref": SOURCE_REFS[0],
            "target_ref": TARGET_REFS[0],
            "verification_mode": "source_faithful_public_refactor",
            "preserved_semantics": [
                "graph_nodes_and_edges",
                "failure_classification",
                "restart_point_selection",
                "bounded_replay_cases",
                "teaching_ledger",
                "source_capsule_hash_carryforward",
                "anti_claim_authority_boundary",
            ],
            "omitted_live_material": [
                "wetlab protocol bodies",
                "hazardous synthesis steps",
                "reagent quantities",
                "live lab credentials",
                "robot commands",
                "private notebooks",
                "live assay data",
                "provider payload bodies",
            ],
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "body_in_receipt": False,
    }


def _load_input_dir(input_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_input_dir` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        name: read_json_strict(input_dir / f"{name}.json")
        for name in (
            "candidate_materials",
            "experiment_dag",
            "simulator_assays",
            "active_learning_decisions",
        )
    }


def build_materials_lab_evolve_replay_from_dir(input_dir: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_materials_lab_evolve_replay_from_dir` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return build_materials_lab_evolve_replay(_load_input_dir(Path(input_dir)), [])


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `_parser` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="lab_evolve_replay")
    parser.add_argument("input", help="Directory with materials replay JSON inputs.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.macro_tools.lab_evolve_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    payload = build_materials_lab_evolve_replay_from_dir(args.input)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
