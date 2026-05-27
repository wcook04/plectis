"""Build the Lab/Evolve failure replay graph specimen.

[PURPOSE]
Demonstrate how a local failure becomes restart-point classification, bounded replay, and teaching.

[INTERFACE]
Expose a builder that emits the replay graph artifact and optional receipt.

[FLOW]
Normalize synthetic tasks, run solver variants, evaluate answers, classify failures, and record repairs.

[DEPENDENCIES]
Uses local JSON fixtures, regex number extraction, counters, timestamps, and pathlib writes.

[CONSTRAINTS]
Models public-safe fixture replay only; it is not benchmark proof or private runtime evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SPECIMEN_ID = "lab_evolve_failure_replay_graph_microcosm"
DEFAULT_OUTPUT_PATH = "microcosms/lab_evolve_failure_replay/replay_graph.json"
DEFAULT_RECEIPT_PATH = "microcosms/lab_evolve_failure_replay/receipt.json"
README_PATH = "microcosms/lab_evolve_failure_replay/README.md"
EXECUTABLE_GRAMMAR_BOARD_PATH = "microcosms/executable_grammar_metabolism/grammar_board.json"
EXECUTABLE_GRAMMAR_RECEIPT_PATH = "microcosms/executable_grammar_metabolism/receipt.json"
GLOBAL_RULE_ID = "rule.valid_ir_solver_variant_mismatch"
GLOBAL_PATTERN_ID = "pattern.valid_ir_solver_variant_mismatch"
GRAMMAR_REPLAY_BRIDGE_RULE_ID = "rule.executable_grammar_failure_replay"
GRAMMAR_REPLAY_BRIDGE_PATTERN_ID = "pattern.executable_grammar_failure_to_teaching"


FIXTURE_CASES = (
    {
        "case_id": "case.sum_small_list",
        "native_input": "Find the total of the numbers 1, 2, and 3.",
        "numbers": [1, 2, 3],
        "expected_answer": 6,
    },
    {
        "case_id": "case.sum_two_item_list",
        "native_input": "Find the total of the numbers 4 and 5.",
        "numbers": [4, 5],
        "expected_answer": 9,
    },
)

GRAPH_NODES = (
    {
        "node_id": "native_input",
        "node_type": "source",
        "contract": "Accept a public-safe synthetic task in native prose.",
        "restartable": False,
    },
    {
        "node_id": "normalize_to_operation_ir",
        "node_type": "transform",
        "contract": "Extract operation intent and operands into a small JSON IR.",
        "restartable": False,
    },
    {
        "node_id": "solve_operation",
        "node_type": "reason",
        "contract": "Produce an answer from the operation IR.",
        "restartable": True,
    },
    {
        "node_id": "evaluate_answer",
        "node_type": "evaluator",
        "contract": "Compare the answer with the fixture expectation.",
        "restartable": False,
    },
    {
        "node_id": "classify_failure",
        "node_type": "failure_classifier",
        "contract": "Localize the first bad node without blaming the whole graph.",
        "restartable": False,
    },
    {
        "node_id": "choose_restart_point",
        "node_type": "restart",
        "contract": "Restart from the nearest safe point instead of replaying the full graph.",
        "restartable": False,
    },
    {
        "node_id": "replay_variants",
        "node_type": "replay",
        "contract": "Try bounded public-safe variants from the restart point.",
        "restartable": False,
    },
    {
        "node_id": "record_teaching",
        "node_type": "teaching",
        "contract": "Convert the local repair into a reusable graph-design teaching.",
        "restartable": False,
    },
)

GRAPH_EDGES = (
    ["native_input", "normalize_to_operation_ir"],
    ["normalize_to_operation_ir", "solve_operation"],
    ["solve_operation", "evaluate_answer"],
    ["evaluate_answer", "classify_failure"],
    ["classify_failure", "choose_restart_point"],
    ["choose_restart_point", "replay_variants"],
    ["replay_variants", "record_teaching"],
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_sha256(payload: dict[str, Any]) -> str:
    stable_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()


def _normalize(native_input: str) -> dict[str, Any]:
    numbers = [int(value) for value in re.findall(r"\d+", native_input)]
    return {
        "operation": "sum",
        "operands": numbers,
        "ir_id": "operation_ir",
    }


def _solve(ir: dict[str, Any], variant_id: str) -> int:
    operands = [int(value) for value in ir.get("operands", [])]
    if variant_id == "solver_count_items_v1":
        return len(operands)
    if variant_id == "normalizer_restart_noise_v1":
        return len(sorted(operands, reverse=True))
    if variant_id == "solver_sum_v2":
        return sum(operands)
    raise ValueError(f"unknown replay variant: {variant_id}")


def _evaluate(answer: int, expected: int) -> dict[str, Any]:
    passed = answer == expected
    return {
        "status": "pass" if passed else "fail",
        "observed_answer": answer,
        "expected_answer": expected,
    }


def _baseline_trace(case: dict[str, Any], ir: dict[str, Any], answer: int, evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "node_id": "native_input",
            "status": "pass",
            "output_ref": f"{case['case_id']}:native_input",
        },
        {
            "node_id": "normalize_to_operation_ir",
            "status": "pass",
            "output": ir,
        },
        {
            "node_id": "solve_operation",
            "status": "produced_output_pending_evaluator",
            "variant_id": "solver_count_items_v1",
            "output": answer,
        },
        {
            "node_id": "evaluate_answer",
            "status": evaluation["status"],
            "observed_answer": evaluation["observed_answer"],
            "expected_answer": evaluation["expected_answer"],
        },
    ]


def _variant_result(case: dict[str, Any], ir: dict[str, Any], variant_id: str) -> dict[str, Any]:
    answer = _solve(ir, variant_id)
    evaluation = _evaluate(answer, int(case["expected_answer"]))
    return {
        "variant_id": variant_id,
        "restart_point": "operation_ir",
        "mutated_node_id": "solve_operation" if variant_id == "solver_sum_v2" else "normalize_to_operation_ir",
        "observed_answer": answer,
        "status": evaluation["status"],
        "evaluator_ref": "evaluate_answer",
    }


def _case_result(case: dict[str, Any]) -> dict[str, Any]:
    ir = _normalize(str(case["native_input"]))
    baseline_answer = _solve(ir, "solver_count_items_v1")
    baseline_evaluation = _evaluate(baseline_answer, int(case["expected_answer"]))
    variants = [
        _variant_result(case, ir, "normalizer_restart_noise_v1"),
        _variant_result(case, ir, "solver_sum_v2"),
    ]
    winner = next((row for row in variants if row["status"] == "pass"), None)
    if baseline_evaluation["status"] == "pass":
        failure_origin_node = None
        restart_point = None
    elif ir.get("operation") == "sum" and ir.get("operands") == case["numbers"]:
        failure_origin_node = "solve_operation"
        restart_point = "operation_ir"
    else:
        failure_origin_node = "normalize_to_operation_ir"
        restart_point = "native_input"

    teaching_id = f"teaching.{case['case_id'].split('.', 1)[1]}.solver_variant_after_valid_ir"
    return {
        "case_id": case["case_id"],
        "native_input": case["native_input"],
        "expected_answer": case["expected_answer"],
        "baseline_variant_id": "solver_count_items_v1",
        "baseline_trace": _baseline_trace(case, ir, baseline_answer, baseline_evaluation),
        "failure_origin_node": failure_origin_node,
        "failure_signature": "valid_operation_ir_answer_mismatch",
        "restart_point": restart_point,
        "variants_tried": variants,
        "winner_variant": winner["variant_id"] if winner else None,
        "teaching": {
            "teaching_id": teaching_id,
            "local_rule": "When the operation IR is valid and only the answer fails, mutate the solver node and keep the normalized IR fixed.",
            "global_pattern_candidate_ref": GLOBAL_PATTERN_ID,
            "evidence_refs": [
                DEFAULT_OUTPUT_PATH,
                f"{case['case_id']}:baseline_trace",
                f"{case['case_id']}:variants_tried",
            ],
        },
    }


def _global_teaching_ledger(cases: list[dict[str, Any]]) -> dict[str, Any]:
    teaching_rows = []
    for case in cases:
        teaching = case.get("teaching", {})
        teaching_rows.append(
            {
                "teaching_id": teaching.get("teaching_id"),
                "case_id": case.get("case_id"),
                "failure_signature": case.get("failure_signature"),
                "failure_origin_node": case.get("failure_origin_node"),
                "restart_point": case.get("restart_point"),
                "winner_variant": case.get("winner_variant"),
                "global_pattern_candidate_ref": teaching.get("global_pattern_candidate_ref"),
                "evidence_refs": teaching.get("evidence_refs", []),
            }
        )

    pattern_ids = sorted(
        {
            str(row["global_pattern_candidate_ref"])
            for row in teaching_rows
            if row.get("global_pattern_candidate_ref")
        }
    )
    global_rule_candidates: list[dict[str, Any]] = []
    for pattern_id in pattern_ids:
        pattern_rows = [row for row in teaching_rows if row.get("global_pattern_candidate_ref") == pattern_id]
        failure_signatures = sorted({str(row.get("failure_signature")) for row in pattern_rows if row.get("failure_signature")})
        origin_nodes = sorted({str(row.get("failure_origin_node")) for row in pattern_rows if row.get("failure_origin_node")})
        restart_points = sorted({str(row.get("restart_point")) for row in pattern_rows if row.get("restart_point")})
        winner_variants = sorted({str(row.get("winner_variant")) for row in pattern_rows if row.get("winner_variant")})
        repeated = len(pattern_rows) >= 2
        global_rule_candidates.append(
            {
                "rule_id": GLOBAL_RULE_ID if pattern_id == GLOBAL_PATTERN_ID else f"rule.{pattern_id}",
                "pattern_id": pattern_id,
                "status": "candidate_global_rule_local_fixture_only" if repeated else "local_pattern_only",
                "observed_case_count": len(pattern_rows),
                "promotion_threshold": 2,
                "failure_signatures": failure_signatures,
                "failure_origin_nodes": origin_nodes,
                "safe_restart_points": restart_points,
                "winning_variants": winner_variants,
                "rule": "If a validated operation IR repeatedly produces evaluator answer mismatches, freeze upstream normalization, mutate the solver node first, rerun the evaluator, and only escalate upstream after solver variants fail.",
                "action_order": [
                    "reuse_passing_operation_ir",
                    "mutate_solver_variant",
                    "rerun_evaluator",
                    "record_teaching",
                    "promote_candidate_rule_after_repeated_fixture_evidence",
                ],
                "evidence_refs": [
                    DEFAULT_OUTPUT_PATH,
                    f"{DEFAULT_OUTPUT_PATH}:global_teaching_ledger.local_teachings",
                    *[f"{row['case_id']}:teaching" for row in pattern_rows if row.get("case_id")],
                ],
                "anti_claims": [
                    "candidate rule is private Lab/Evolve authority",
                    "candidate rule is benchmark performance evidence",
                    "candidate rule grants public release permission",
                ],
            }
        )

    return {
        "kind": "lab_evolve_teaching_ledger",
        "schema_version": "lab_evolve_teaching_ledger_v0",
        "local_teachings": teaching_rows,
        "global_rule_candidates": global_rule_candidates,
        "candidate_global_rule_count": len(
            [
                row
                for row in global_rule_candidates
                if row.get("status") == "candidate_global_rule_local_fixture_only"
            ]
        ),
    }


def _source_capsule(case: dict[str, Any]) -> dict[str, Any]:
    teaching = case.get("teaching", {})
    source_clip = {
        "case_id": case.get("case_id"),
        "native_input": case.get("native_input"),
        "expected_answer": case.get("expected_answer"),
        "baseline_variant_id": case.get("baseline_variant_id"),
        "baseline_trace": case.get("baseline_trace", []),
        "failure_signature": case.get("failure_signature"),
        "failure_origin_node": case.get("failure_origin_node"),
        "restart_point": case.get("restart_point"),
        "variants_tried": case.get("variants_tried", []),
        "winner_variant": case.get("winner_variant"),
        "teaching": teaching,
    }
    teaching_id = str(teaching.get("teaching_id", ""))
    case_id = str(case.get("case_id", "unknown_case"))
    return {
        "capsule_id": f"source_capsule.{case_id}",
        "status": "ok",
        "source_class": "public_safe_synthetic_fixture_case",
        "source_ref": f"{DEFAULT_OUTPUT_PATH}:cases.{case_id}",
        "clip_hash_algorithm": "sha256",
        "clip_hash": _json_sha256(source_clip),
        "source_clip": source_clip,
        "semantic_carryforward": {
            "case_id": case_id,
            "failure_signature": case.get("failure_signature"),
            "first_bad_node": case.get("failure_origin_node"),
            "restart_point": case.get("restart_point"),
            "winning_variant": case.get("winner_variant"),
            "teaching_ref": teaching_id,
            "carryforward_rule": "Preserve the validated source clip, restart point, replay evidence, and teaching ref together; do not promote a teaching when its source clip or hash is missing.",
        },
        "replay_variant_refs": [
            variant.get("variant_id")
            for variant in case.get("variants_tried", [])
            if isinstance(variant, dict) and variant.get("variant_id")
        ],
        "omission_boundary": "Capsule contains only the public-safe fixture clip required to replay the teaching; no private Lab/Evolve trace, provider transcript, benchmark row, or hidden corpus is included.",
        "authority_boundary": "A capsule hash proves deterministic fixture carryforward only; it is not private lab authority, benchmark proof, or publication permission.",
        "anti_claims": [
            "source capsule is not private Lab/Evolve trace authority",
            "source capsule is not benchmark evidence",
            "source capsule is not public release approval",
        ],
    }


def _source_capsule_provenance(cases: list[dict[str, Any]]) -> dict[str, Any]:
    capsules = [_source_capsule(case) for case in cases]
    return {
        "kind": "source_capsule_provenance",
        "schema_version": "source_capsule_provenance_v0",
        "status": "ok",
        "hash_algorithm": "sha256",
        "capsule_count": len(capsules),
        "source_capsules": capsules,
        "carryforward_contract": {
            "required_fields": [
                "case_id",
                "failure_signature",
                "first_bad_node",
                "restart_point",
                "winning_variant",
                "teaching_ref",
            ],
            "rule": "Every reusable teaching must carry its replay source clip, deterministic hash, restart point, replay result, and anti-claim boundary.",
        },
        "summary": {
            "capsule_count": len(capsules),
            "semantic_carryforward_count": len(
                [capsule for capsule in capsules if capsule.get("semantic_carryforward")]
            ),
            "hashed_source_clip_count": len([capsule for capsule in capsules if capsule.get("clip_hash")]),
            "public_safe_source_count": len(
                [
                    capsule
                    for capsule in capsules
                    if capsule.get("source_class") == "public_safe_synthetic_fixture_case"
                ]
            ),
        },
        "anti_claims": [
            "local source capsules only",
            "not private system provenance",
            "not benchmark proof",
            "not public release approval",
        ],
    }


def _grammar_restart_point(rule_ids: list[str], worker_action: dict[str, Any]) -> str:
    if worker_action.get("restart_from"):
        return str(worker_action["restart_from"])
    target_fields = [
        str(field)
        for field in worker_action.get("target_fields", [])
        if isinstance(field, str) and field
    ]
    if target_fields:
        return f"candidate.{target_fields[0]}"
    if "source_refs_required" in rule_ids:
        return "candidate.source_refs"
    if "required_improvement_delta" in rule_ids:
        return "candidate.improvement_delta"
    if "allowed_projection_strategy" in rule_ids:
        return "candidate.projection_strategy"
    if "no_publication_before_gates" in rule_ids:
        return "candidate.next_action"
    return "grammar_case_source_clip"


def _grammar_failure_class(rule_ids: list[str], evaluation: dict[str, Any]) -> str:
    if rule_ids:
        return "+".join(rule_ids)
    status = evaluation.get("status")
    return f"grammar_{status or 'unknown'}"


def _grammar_bridge_case(grammar_case: dict[str, Any]) -> dict[str, Any] | None:
    evaluation = grammar_case.get("evaluation")
    worker_action = grammar_case.get("worker_action")
    if not isinstance(evaluation, dict) or not isinstance(worker_action, dict):
        return None
    if evaluation.get("status") == "pass":
        return None

    rule_ids = [
        str(rule_id)
        for rule_id in evaluation.get("observed_rule_ids", [])
        if isinstance(rule_id, str) and rule_id
    ]
    if not rule_ids:
        rule_ids = sorted(
            {
                str(row.get("rule_id"))
                for row in evaluation.get("repair_rows", [])
                if isinstance(row, dict) and row.get("rule_id")
            }
        )
    source_case_id = str(grammar_case.get("case_id", "unknown_grammar_case"))
    restart_point = _grammar_restart_point(rule_ids, worker_action)
    failure_class = _grammar_failure_class(rule_ids, evaluation)
    source_clip = {
        "source_case_id": source_case_id,
        "mutation": grammar_case.get("mutation"),
        "evaluation": {
            "status": evaluation.get("status"),
            "observed_rule_ids": rule_ids,
            "grammar_failures": evaluation.get("grammar_failures", []),
            "repair_rows": evaluation.get("repair_rows", []),
            "status_authority": evaluation.get("status_authority"),
            "provider_or_artifact_self_status_used_as_authority": evaluation.get(
                "provider_or_artifact_self_status_used_as_authority"
            ),
        },
        "worker_action": worker_action,
    }
    bridge_case_id = f"grammar_replay_bridge.{source_case_id}"
    teaching_rule = (
        "When executable grammar blocks a row, preserve the failed source clip, "
        "restart from the owning field or status lane, apply the repair contract, "
        "and rerun the grammar evaluator before any projection or publication path can reuse it."
    )
    return {
        "bridge_case_id": bridge_case_id,
        "source_case_id": source_case_id,
        "source_case_ref": f"{EXECUTABLE_GRAMMAR_BOARD_PATH}:cases[{source_case_id}]",
        "source_clip": source_clip,
        "source_clip_hash": _json_sha256(source_clip),
        "source_clip_hash_algorithm": "sha256",
        "semantic_carryforward": {
            "failure_class": failure_class,
            "rule_ids": rule_ids,
            "restart_point": restart_point,
            "repair_route": worker_action.get("action_id"),
            "evaluator_authority": evaluation.get("status_authority"),
            "projection_not_authority": True,
        },
        "failure_class": failure_class,
        "replay_seed": {
            "source_clip_hash": _json_sha256(source_clip),
            "restart_point": restart_point,
            "rule_ids": rule_ids,
            "rerun_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-executable-grammar-metabolism-specimen --root . --write-receipt",
        },
        "restart_point": restart_point,
        "repair_route": {
            "route_id": f"repair_route.{bridge_case_id}",
            "worker_action_ref": worker_action.get("action_id"),
            "action_type": worker_action.get("action_type"),
            "target_fields": worker_action.get("target_fields", []),
            "transaction_status": worker_action.get("transaction_status"),
            "authority_rule": worker_action.get("authority_rule"),
        },
        "evaluator_result": {
            "status": evaluation.get("status"),
            "authority": evaluation.get("status_authority"),
            "provider_or_artifact_self_status_used_as_authority": evaluation.get(
                "provider_or_artifact_self_status_used_as_authority"
            ),
        },
        "teaching_rule": teaching_rule,
        "evidence_refs": [
            EXECUTABLE_GRAMMAR_BOARD_PATH,
            f"{EXECUTABLE_GRAMMAR_BOARD_PATH}:cases[{source_case_id}]",
            DEFAULT_OUTPUT_PATH,
            f"{DEFAULT_OUTPUT_PATH}:executable_grammar_replay_bridge",
        ],
        "anti_claims": [
            "grammar projection is not its own validator",
            "failed grammar case is not publication permission",
            "repair route is not public release approval",
            "source clip hash is not private-root equivalence",
        ],
        "next_case": "rerun_executable_grammar_after_repair_contract",
    }


def _executable_grammar_replay_bridge(root: Path, generated_at: str) -> dict[str, Any]:
    grammar_board_path = root / EXECUTABLE_GRAMMAR_BOARD_PATH
    if not grammar_board_path.exists():
        return {
            "kind": "executable_grammar_failure_replay_bridge",
            "schema_version": "executable_grammar_failure_replay_bridge_v0",
            "generated_at": generated_at,
            "status": "blocked_missing_source",
            "source_refs": [EXECUTABLE_GRAMMAR_BOARD_PATH],
            "bridge_cases": [],
            "failures": [{"reason": "missing executable grammar board", "path": EXECUTABLE_GRAMMAR_BOARD_PATH}],
            "summary": {
                "case_count": 0,
                "source_capsule_count": 0,
                "semantic_carryforward_count": 0,
                "repair_route_count": 0,
                "teaching_rule_count": 0,
                "blocked_claim_count": 0,
                "evaluator_authority_count": 0,
                "self_attestation_authority_count": 0,
            },
        }

    grammar_board = _load_json(grammar_board_path)
    bridge_cases = [
        bridge_case
        for bridge_case in (_grammar_bridge_case(case) for case in grammar_board.get("cases", []))
        if isinstance(bridge_case, dict)
    ]
    failures: list[dict[str, Any]] = []
    if grammar_board.get("status") != "ok":
        failures.append({"reason": "executable grammar source board is not ok", "status": grammar_board.get("status")})
    if len(bridge_cases) < 3:
        failures.append({"reason": "expected at least three blocked executable grammar cases for replay teaching"})
    if any((case.get("evaluator_result") or {}).get("provider_or_artifact_self_status_used_as_authority") for case in bridge_cases):
        failures.append({"reason": "bridge case used provider or artifact self status as authority"})
    if any(not case.get("repair_route") for case in bridge_cases):
        failures.append({"reason": "every bridge case must carry a repair route"})
    if any(not case.get("teaching_rule") for case in bridge_cases):
        failures.append({"reason": "every bridge case must carry a teaching rule"})

    status = "ok" if not failures else "failed"
    return {
        "kind": "executable_grammar_failure_replay_bridge",
        "schema_version": "executable_grammar_failure_replay_bridge_v0",
        "generated_at": generated_at,
        "status": status,
        "selected_native_pattern": "executable grammar failure becomes replayable teaching",
        "pattern_ref": GRAMMAR_REPLAY_BRIDGE_PATTERN_ID,
        "rule_ref": GRAMMAR_REPLAY_BRIDGE_RULE_ID,
        "source_owner": "idea_microcosm.executable_grammar_specimen",
        "generated_by": {
            "source_refs": [
                EXECUTABLE_GRAMMAR_BOARD_PATH,
                EXECUTABLE_GRAMMAR_RECEIPT_PATH,
                "src/idea_microcosm/executable_grammar_specimen.py",
                "src/idea_microcosm/lab_evolve_failure_replay_specimen.py",
            ],
            "projection_not_authority": True,
        },
        "source_refs": [
            EXECUTABLE_GRAMMAR_BOARD_PATH,
            EXECUTABLE_GRAMMAR_RECEIPT_PATH,
            "src/idea_microcosm/executable_grammar_specimen.py",
            "src/idea_microcosm/lab_evolve_failure_replay_specimen.py",
        ],
        "bridge_cases": bridge_cases,
        "authority": {
            "authority_class": "grammar_evaluator_and_receipt_gate_only",
            "self_attestation_authority_count": 0,
            "evaluator_authority_count": len(bridge_cases),
            "forbidden_promotions": [
                "grammar projection self-validates",
                "failed grammar case can be hidden from replay",
                "local replay bridge grants publication permission",
            ],
            "fail_closed_gates": [
                "missing executable grammar board",
                "grammar board status not ok",
                "bridge case missing repair route",
                "bridge case missing teaching rule",
            ],
            "public_release_claim_count": 0,
            "publication_claim_count": 0,
            "private_root_equivalence_claim_count": 0,
            "benchmark_win_claim_count": 0,
            "public_claims_blocked": [
                "executable grammar fixture proves public release readiness",
                "grammar repair route authorizes publication",
                "source clip hash proves private-root equivalence",
            ],
        },
        "route": {
            "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-lab-evolve-failure-replay-specimen --root . --write-receipt",
            "expected_output": DEFAULT_OUTPUT_PATH,
            "first_evidence": f"{DEFAULT_OUTPUT_PATH}:executable_grammar_replay_bridge",
            "next_artifact": "microcosms/executable_grammar_metabolism/grammar_board.json",
            "next_microcosm": "executable_grammar_metabolism_microcosm",
            "cold_agent_instruction": "Open the bridge cases, recompute the source_clip_hash for one grammar failure, then verify its repair_route points back to the grammar worker action.",
        },
        "cross_links": {
            "portfolio_ref": "state/release_candidate_portfolio.json::microcosm_route_to_command_index.route.executable_grammar_to_failure_teaching",
            "pattern_transfer_ref": "microcosms/demo_receipt_storyboard/storyboard.json::pattern.executable_grammar_to_runtime_board",
            "receipt_ref": DEFAULT_RECEIPT_PATH,
            "related_microcosms": [
                "executable_grammar_metabolism_microcosm",
                "provider_harness_evaluator_authority_split_microcosm",
                "verisoftbench_diagnostic_specimen_microcosm",
            ],
            "next_refinement": "Carry grammar replay bridge rows into demo pattern routes without making the demo storyboard an authority surface.",
        },
        "failures": failures,
        "summary": {
            "case_count": len(bridge_cases),
            "source_capsule_count": len(bridge_cases),
            "semantic_carryforward_count": len(
                [case for case in bridge_cases if case.get("semantic_carryforward")]
            ),
            "repair_route_count": len([case for case in bridge_cases if case.get("repair_route")]),
            "teaching_rule_count": len([case for case in bridge_cases if case.get("teaching_rule")]),
            "blocked_claim_count": sum(len(case.get("anti_claims", [])) for case in bridge_cases),
            "evaluator_authority_count": len(bridge_cases),
            "self_attestation_authority_count": 0,
            "public_release_claim_count": 0,
            "publication_claim_count": 0,
            "private_root_equivalence_claim_count": 0,
            "benchmark_win_claim_count": 0,
        },
    }


def _evolution_cycle() -> list[dict[str, Any]]:
    return [
        {
            "step": "observe",
            "node_ref": "native_input",
            "artifact": "public-safe synthetic arithmetic prompt",
        },
        {
            "step": "project",
            "node_ref": "normalize_to_operation_ir",
            "artifact": "operation_ir",
        },
        {
            "step": "fail",
            "node_ref": "solve_operation",
            "artifact": "baseline answer mismatch from solver_count_items_v1",
        },
        {
            "step": "localize",
            "node_ref": "classify_failure",
            "artifact": "first bad node is solve_operation because operation_ir passed validation",
        },
        {
            "step": "restart",
            "node_ref": "choose_restart_point",
            "artifact": "operation_ir",
        },
        {
            "step": "replay",
            "node_ref": "replay_variants",
            "artifact": "solver_sum_v2 passes evaluator",
        },
        {
            "step": "teach",
            "node_ref": "record_teaching",
            "artifact": "local teaching plus candidate global rule when the pattern repeats",
        },
    ]


def _readme() -> str:
    return "\n".join(
        [
            "# Lab/Evolve Failure Replay",
            "",
            "This specimen is a public-safe toy analogue of a failure-replay graph.",
            "It is not the private Lab/Evolve engine, not a benchmark result, and not a publication claim.",
            "",
            "Run it from the release root:",
            "",
            "```bash",
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-lab-evolve-failure-replay-specimen --root . --write-receipt",
            "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
            "```",
            "",
            "The fixture intentionally starts with a bad solver variant, localizes the failure to `solve_operation`, restarts from `operation_ir`, replays bounded variants, records a winning variant, and emits a teaching.",
            "Repeated local teachings are folded into `global_teaching_ledger.global_rule_candidates`, which remains a local-fixture-only candidate rule until stronger evidence exists.",
            "Each teaching now carries `source_capsule_provenance`: a hashed public-safe source clip, semantic carryforward fields, replay variant refs, and anti-claims so a later agent can see exactly what evidence may travel forward.",
            "The graph also consumes the executable grammar board through `executable_grammar_replay_bridge`: blocked grammar cases keep their source clip hash, evaluator authority, restart point, repair route, teaching rule, and anti-claims instead of being treated as disposable diagnostics.",
            "The point is not arithmetic difficulty; the point is status-preserving failure localization, restart discipline, replay evidence, and rule-candidate capture.",
            "",
            "The boundary is fail-closed: no Lean, provider state, private benchmark trace, or private root material is included.",
            "",
        ]
    )


def build_lab_evolve_failure_replay_specimen(
    root: Path,
    *,
    output_path: str = DEFAULT_OUTPUT_PATH,
    receipt_path: str = DEFAULT_RECEIPT_PATH,
    write_receipt: bool = False,
    at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    generated_at = at or _utc_now()
    cases = [_case_result(case) for case in FIXTURE_CASES]
    failures: list[dict[str, Any]] = []
    if not all(case.get("failure_origin_node") == "solve_operation" for case in cases):
        failures.append({"reason": "all fixture failures must localize to solve_operation"})
    if not all(case.get("restart_point") == "operation_ir" for case in cases):
        failures.append({"reason": "all fixture failures must restart from operation_ir"})
    if not all(case.get("winner_variant") == "solver_sum_v2" for case in cases):
        failures.append({"reason": "all fixture cases must find solver_sum_v2 as winning variant"})

    pattern_counts = Counter(row["teaching"]["global_pattern_candidate_ref"] for row in cases)
    teaching_ledger = _global_teaching_ledger(cases)
    source_capsule_provenance = _source_capsule_provenance(cases)
    executable_grammar_replay_bridge = _executable_grammar_replay_bridge(root, generated_at)
    global_patterns = [
        {
            "pattern_id": str(pattern_id),
            "case_count": count,
            "status": "global_graph_design_pressure" if count >= 2 else "local_only",
            "rule_ref": GLOBAL_RULE_ID if pattern_id == GLOBAL_PATTERN_ID else f"rule.{pattern_id}",
            "teaching_refs": [
                case["teaching"]["teaching_id"]
                for case in cases
                if case["teaching"].get("global_pattern_candidate_ref") == pattern_id
            ],
        }
        for pattern_id, count in sorted(pattern_counts.items())
    ]
    if teaching_ledger["candidate_global_rule_count"] < 1:
        failures.append({"reason": "repeated fixture failures must emit a candidate global rule"})
    if source_capsule_provenance["summary"]["semantic_carryforward_count"] != len(cases):
        failures.append({"reason": "every fixture case must emit source capsule semantic carryforward"})
    if executable_grammar_replay_bridge.get("status") != "ok":
        failures.append(
            {
                "reason": "executable grammar replay bridge must be ok",
                "bridge_failures": executable_grammar_replay_bridge.get("failures", []),
            }
        )
    status = "ok" if not failures else "failed"
    replay_graph = {
        "kind": "lab_evolve_failure_replay_graph_specimen",
        "schema_version": "lab_evolve_failure_replay_graph_specimen_v0",
        "generated_at": generated_at,
        "status": status,
        "candidate_id": SPECIMEN_ID,
        "authority_posture": "public_safe_synthetic_failure_replay_fixture_not_private_lab_or_benchmark_authority",
        "source_refs": [
            "registry/release_candidates.json",
            "microcosms/lab_evolve_failure_replay/README.md",
            "src/idea_microcosm/lab_evolve_failure_replay_specimen.py",
        ],
        "improvement_delta": "The release specimen makes failure localization, restart-point choice, replay variants, winner selection, and teaching capture visible in one deterministic fixture.",
        "graph": {
            "nodes": list(GRAPH_NODES),
            "edges": [{"from": start, "to": end} for start, end in GRAPH_EDGES],
            "restart_policy": "Restart from the nearest artifact whose producing node passed validation; do not mutate upstream nodes without evidence.",
        },
        "evolution_cycle": _evolution_cycle(),
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "baseline_failure_count": len([case for case in cases if case.get("failure_origin_node")]),
            "replay_success_count": len([case for case in cases if case.get("winner_variant")]),
            "teaching_count": len([case for case in cases if case.get("teaching")]),
            "global_pattern_candidate_count": len(global_patterns),
            "candidate_global_rule_count": teaching_ledger["candidate_global_rule_count"],
            "source_capsule_count": source_capsule_provenance["summary"]["capsule_count"],
            "semantic_carryforward_count": source_capsule_provenance["summary"]["semantic_carryforward_count"],
            "executable_grammar_replay_bridge_case_count": executable_grammar_replay_bridge["summary"]["case_count"],
            "executable_grammar_replay_bridge_source_capsule_count": executable_grammar_replay_bridge["summary"]["source_capsule_count"],
            "executable_grammar_replay_bridge_semantic_carryforward_count": executable_grammar_replay_bridge["summary"]["semantic_carryforward_count"],
            "executable_grammar_replay_bridge_repair_route_count": executable_grammar_replay_bridge["summary"]["repair_route_count"],
            "executable_grammar_replay_bridge_teaching_rule_count": executable_grammar_replay_bridge["summary"]["teaching_rule_count"],
            "executable_grammar_replay_bridge_blocked_claim_count": executable_grammar_replay_bridge["summary"]["blocked_claim_count"],
            "executable_grammar_replay_bridge_evaluator_authority_count": executable_grammar_replay_bridge["summary"]["evaluator_authority_count"],
            "executable_grammar_replay_bridge_self_attestation_authority_count": executable_grammar_replay_bridge["summary"]["self_attestation_authority_count"],
            "public_release_claim_count": 0,
            "publication_claim_count": 0,
            "private_root_equivalence_claim_count": 0,
            "benchmark_win_claim_count": 0,
        },
        "global_pattern_candidates": global_patterns,
        "global_teaching_ledger": teaching_ledger,
        "source_capsule_provenance": source_capsule_provenance,
        "executable_grammar_replay_bridge": executable_grammar_replay_bridge,
        "public_safety_boundary": "Synthetic public-safe arithmetic fixtures only; no private Lab/Evolve engine, provider output, benchmark trace, private root path, or hidden corpus is included.",
        "claim_boundary": "Fixture-level proof of restartable failure localization and teaching capture; not a formal-proof benchmark win, hosted result, novelty proof, or private-root equivalence claim.",
        "publication_boundary": "No website card or public release may outrun registry records, receipt refs, fail-closed publication gate, and fresh clean-run or clone probes.",
        "failures": failures,
    }

    _write_json(root / output_path, replay_graph)
    readme_file = root / README_PATH
    readme_file.parent.mkdir(parents=True, exist_ok=True)
    readme_file.write_text(_readme(), encoding="utf-8")

    result: dict[str, Any] = {
        "kind": "lab_evolve_failure_replay_graph_build",
        "schema_version": "lab_evolve_failure_replay_graph_build_v0",
        "generated_at": generated_at,
        "status": status,
        "output": output_path,
        "case_count": len(cases),
        "baseline_failure_count": replay_graph["summary"]["baseline_failure_count"],
        "replay_success_count": replay_graph["summary"]["replay_success_count"],
        "teaching_count": replay_graph["summary"]["teaching_count"],
        "global_pattern_candidate_count": replay_graph["summary"]["global_pattern_candidate_count"],
        "candidate_global_rule_count": replay_graph["summary"]["candidate_global_rule_count"],
        "source_capsule_count": replay_graph["summary"]["source_capsule_count"],
        "semantic_carryforward_count": replay_graph["summary"]["semantic_carryforward_count"],
        "executable_grammar_replay_bridge_case_count": executable_grammar_replay_bridge["summary"]["case_count"],
        "executable_grammar_replay_bridge_source_capsule_count": executable_grammar_replay_bridge["summary"]["source_capsule_count"],
        "executable_grammar_replay_bridge_repair_route_count": executable_grammar_replay_bridge["summary"]["repair_route_count"],
        "executable_grammar_replay_bridge_teaching_rule_count": executable_grammar_replay_bridge["summary"]["teaching_rule_count"],
        "failure_count": len(failures),
        "failures": failures,
    }
    if write_receipt:
        receipt = {
            "kind": "receipt",
            "schema_version": "receipt_v0",
            "id": "receipt.lab_evolve_failure_replay_graph",
            "generated_at": generated_at,
            "owner": "idea_microcosm.lab_evolve_failure_replay_specimen",
            "claim_ref": f"candidate.{SPECIMEN_ID}",
            "claim_tier": "fixture_validated",
            "command": "python -m idea_microcosm.cli build-lab-evolve-failure-replay-specimen --root . --write-receipt",
            "result": status,
            "status": status,
            "evidence_refs": [
                output_path,
                f"{output_path}:global_teaching_ledger",
                f"{output_path}:source_capsule_provenance",
                f"{output_path}:executable_grammar_replay_bridge",
                EXECUTABLE_GRAMMAR_BOARD_PATH,
                EXECUTABLE_GRAMMAR_RECEIPT_PATH,
                README_PATH,
                "registry/release_candidates.json",
                "src/idea_microcosm/lab_evolve_failure_replay_specimen.py",
            ],
            "omissions": [
                "This receipt validates a synthetic public-safe replay fixture only; it does not expose private Lab/Evolve internals, provider traces, Lean artifacts, or benchmark data.",
                "Imaginations and private-system doctrine may inspire the graph shape, but this receipt only proves the included deterministic fixture.",
            ],
            "summary": replay_graph["summary"],
        }
        _write_json(root / receipt_path, receipt)
        result["receipt_written"] = receipt_path
    return result
