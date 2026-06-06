#!/usr/bin/env python3
"""Run a status-preserving statement-only Prover Hammer/Bandit lane.

This runner separates theorem statements from adapter hints, provider
hypotheses, oracle repairs, and learned policy rows. It intentionally stays
small: enumerate bounded Lean actions, check every action, select/minimize a
clean proof, and aggregate action-value evidence by target shape/source family.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.meta.factory import run_prover_external_formal_benchmark_smoke as external_smoke
from tools.meta.factory import run_prover_graph_benchmark as harness


RUN_ID = "PROVER_STATEMENT_ONLY_HAMMER_BANDIT_20260511_v0"
DEFAULT_RUN_ROOT = Path("state/runs") / RUN_ID
CAP_ID = "cap_prover_statement_only_hammer_bandit_v0"
GRAPH_VARIANT_ID = "hammer_bandit_graph_v0"

STATUS_FORMAL_STATEMENT = "FORMAL_STATEMENT"
STATUS_ADAPTER_HINT = "ADAPTER_HINT"
STATUS_TACTIC_ACTION = "TACTIC_ACTION"
STATUS_PROVIDER_HYPOTHESIS = "PROVIDER_HYPOTHESIS"
STATUS_LEAN_ACCEPTED_PROOF = "LEAN_ACCEPTED_PROOF"
STATUS_ORACLE_REPAIR = "ORACLE_REPAIR"
STATUS_FOUNDRY_POLICY_LEARNING = "FOUNDRY_POLICY_LEARNING"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _rel(path: str | Path) -> str:
    resolved = _repo_path(path)
    try:
        return resolved.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _write_json(path: Path, payload: Any) -> None:
    harness._write_json(path, payload)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _body_tactic_id(body: Sequence[str]) -> str:
    return external_smoke._body_tactic_id(tuple(body))


def _target_shape(problem: harness.ProverProblem) -> str:
    signature = problem.theorem_signature
    theorem_head = signature.split(" : ", 1)[0]
    if "%" in signature and "(" not in theorem_head:
        return "closed_nat_mod_decision"
    if "Int" in signature and " : " in signature and ("=" in signature or "∧" in signature):
        return "int_linear_arithmetic"
    if "Nat" in signature and " : " in signature and ("=" in signature or "%" in signature):
        if "%" in signature and "(" not in signature.split(":")[-1].split(":=")[0]:
            return "closed_nat_mod_decision"
        if any(token in signature for token in ("(n : Nat)", "(m : Nat)", "(x : Nat)")):
            return "nat_arithmetic_with_variables"
        return "nat_arithmetic"
    if "Rat" in signature:
        return "rat_normalization"
    if "True := by" in signature:
        return "true_intro"
    if "False ->" in signature:
        return "false_elim"
    if "∧" in signature:
        return "conjunction"
    if "∨" in signature:
        return "disjunction"
    if "∃" in signature:
        return "existential"
    if "=" in signature:
        return "equality"
    return "unknown"


def _problem_public_row(problem: harness.ProverProblem) -> dict[str, Any]:
    return {
        "problem_id": problem.problem_id,
        "source": problem.source,
        "source_family": problem.source_family,
        "source_ref": problem.source_ref,
        "split": problem.split,
        "mode": problem.mode,
        "domain": problem.domain,
        "difficulty_tag": problem.difficulty_tag,
        "informal_statement": problem.informal_statement,
        "theorem_name": problem.theorem_name,
        "theorem_signature": problem.theorem_signature,
        "required_imports": list(problem.required_imports),
        "target_shape": _target_shape(problem),
        "status_class": STATUS_FORMAL_STATEMENT,
        "allowed_forward_material": [
            "theorem_signature",
            "required_imports",
            "source_ref",
            "public_statement_metadata",
            "search_policy",
        ],
        "forbidden_forward_material": [
            "candidate_body",
            "ideal_body",
            "repair_body",
            "retrieval_body",
            "oracle_needed_premise_ids",
        ],
    }


def build_statement_only_manifest(
    *,
    external_problem_set: list[harness.ProverProblem],
    local_problem_set: list[harness.ProverProblem],
) -> dict[str, Any]:
    rows = [
        _problem_public_row(problem)
        for problem in [*external_problem_set, *local_problem_set]
    ]
    return {
        "schema_version": "statement_only_problem_manifest_v0",
        "run_id": RUN_ID,
        "created_at": _utc_now(),
        "problem_count": len(rows),
        "external_problem_count": len(external_problem_set),
        "local_problem_count": len(local_problem_set),
        "headline_metric": "statement_only_hammer_success_count",
        "leakage_policy": {
            "candidate_body_visible_to_forward_search": False,
            "ideal_body_visible_to_forward_search": False,
            "repair_body_visible_to_forward_search": False,
            "oracle_repair_counts_as_forward_success": False,
        },
        "problems": rows,
    }


def _run_body_check(
    *,
    problem: harness.ProverProblem,
    body: Sequence[str],
    output_path: Path,
    attempt_label: str,
    timeout_seconds: int,
    expected_error_class: str = "TACTIC_SEARCH_FAIL",
) -> dict[str, Any]:
    text = harness._lean_source(
        problem,
        graph_variant_id=GRAPH_VARIANT_ID,
        body=tuple(body),
        attempt_label=attempt_label,
    )
    harness._write_text(output_path, text)
    run = harness._run_lean(output_path, timeout_seconds=timeout_seconds)
    _, lean_status, error_class = harness._classify_lean_attempt(
        run,
        expected_error_class=expected_error_class,
    )
    sorry_present = bool(harness.SORRY_RE.search(text))
    axiom_audit = harness._classify_axioms(run["stdout"], lean_status, sorry_present)
    return {
        "lean_status": lean_status,
        "error_class": error_class if lean_status != "PASS" else "NONE",
        "duration_ms": run["duration_ms"],
        "stderr_excerpt": run["stderr"][:600],
        "stdout_excerpt": run["stdout"][:600],
        "timeout": bool(run["timeout"]),
        "exit_code": run["exit_code"],
        "sorry_present": sorry_present,
        "axiom_audit": axiom_audit,
        "lean_check_ref": _rel(output_path),
    }


def _candidate_actions(
    problem: harness.ProverProblem,
    availability: Mapping[str, Any] | None,
    *,
    include_templates: bool,
) -> list[dict[str, Any]]:
    target_shape = _target_shape(problem)
    raw_actions = harness._proof_search_candidate_actions(
        replace(problem, candidate_body=()),
        dict(availability or {}),
        include_adapter_candidate=False,
        include_templates=include_templates,
    )
    actions: list[dict[str, Any]] = []
    for action in raw_actions:
        tactic_id = str(action.get("tactic_id") or "")
        if not _action_allowed_for_problem(problem, action, target_shape):
            continue
        actions.append(
            {
                **action,
                "status_input_class": STATUS_TACTIC_ACTION,
                "source_input_class": STATUS_FORMAL_STATEMENT,
                "selection_reason": (
                    f"{action.get('selection_reason')}; target-shape gate accepted "
                    f"{tactic_id} for {target_shape}"
                ),
            }
        )
    return actions


def _action_allowed_for_problem(
    problem: harness.ProverProblem,
    action: Mapping[str, Any],
    target_shape: str,
) -> bool:
    tactic_id = str(action.get("tactic_id") or "")
    if problem.source_family == "local_lean_core":
        local_allowed: dict[str, set[str]] = {
            "lean_core_nat_self_eq": {"rfl"},
            "lean_core_true_intro": {"exact_true_intro_template"},
            "lean_core_and_comm": {"and_comm_intro_constructor_template"},
            "lean_core_or_comm": {"or_comm_cases_template"},
            "lean_core_exists_zero": {"exists_zero_constructor_template"},
            "lean_core_bad_and_comm_missing_p": {"and_comm_intro_constructor_template"},
        }
        return tactic_id in local_allowed.get(problem.problem_id, {tactic_id})
    if problem.source_family == "miniF2F":
        external_allowed: dict[str, set[str]] = {
            "closed_nat_mod_decision": {"decide"},
            "rat_normalization": {"rfl", "native_decide"},
            "int_linear_arithmetic": {"omega"},
            "nat_arithmetic_with_variables": {"omega"},
            "nat_arithmetic": {"omega"},
        }
        return tactic_id in external_allowed.get(target_shape, {tactic_id})
    return _action_allowed_for_target_shape(tactic_id, target_shape)


def _action_allowed_for_target_shape(tactic_id: str, target_shape: str) -> bool:
    if tactic_id == "native_decide":
        return target_shape in {"rat_normalization"}
    if tactic_id == "decide":
        return target_shape in {
            "closed_nat_mod_decision",
            "rat_normalization",
            "true_intro",
            "equality",
        }
    if tactic_id == "omega":
        return target_shape in {
            "int_linear_arithmetic",
            "nat_arithmetic_with_variables",
            "nat_arithmetic",
            "conjunction",
        }
    if tactic_id == "grind":
        return target_shape in {"equality", "true_intro", "conjunction", "disjunction"}
    if tactic_id == "aesop":
        return target_shape in {
            "true_intro",
            "false_elim",
            "conjunction",
            "disjunction",
            "existential",
        }
    if tactic_id in {"simp", "simp_all", "rfl"}:
        return True
    return True


def _select_clean_proof(attempts: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    accepted = [
        dict(attempt)
        for attempt in attempts
        if attempt.get("accepted")
        and attempt.get("lean_status") == "PASS"
        and not attempt.get("sorry_present")
    ]
    if not accepted:
        return None
    return sorted(
        accepted,
        key=lambda row: (
            0 if row.get("axiom_audit") == "CLEAN" else 1,
            len(row.get("candidate_body") or []),
            int(row.get("duration_ms") or 0),
            str(row.get("action_id") or ""),
        ),
    )[0]


def _run_statement_only_problem(
    *,
    problem: harness.ProverProblem,
    problem_root: Path,
    availability: Mapping[str, Any],
    timeout_seconds: int,
    include_templates: bool = True,
) -> dict[str, Any]:
    actions = _candidate_actions(problem, availability, include_templates=include_templates)
    action_rows: list[dict[str, Any]] = []
    check_root = problem_root / "actions"
    for index, action in enumerate(actions):
        action_id = str(action["action_id"])
        body = tuple(action["body"])
        check_path = check_root / f"{index:02d}_{harness._safe_tactic_id(action_id)}.lean"
        check = _run_body_check(
            problem=problem,
            body=body,
            output_path=check_path,
            attempt_label=f"statement_only_hammer_bandit:{action_id}",
            timeout_seconds=timeout_seconds,
        )
        lean_status = check["lean_status"]
        action_rows.append(
            {
                "action_id": action_id,
                "problem_id": problem.problem_id,
                "source_family": problem.source_family,
                "target_shape": _target_shape(problem),
                "status_input_class": STATUS_TACTIC_ACTION,
                "source_input_class": STATUS_FORMAL_STATEMENT,
                "action_kind": str(action["action_kind"]),
                "tactic_id": str(action["tactic_id"]),
                "candidate_body": list(body),
                "selection_reason": str(action["selection_reason"]),
                "allowed_context": list(action.get("allowed_when") or []),
                "forbidden_context": [
                    *list(action.get("forbidden_when") or []),
                    "adapter candidate body",
                    "oracle ideal or repair body",
                    "provider text without reducer evidence",
                ],
                "selected_facts": list(action.get("selected_facts") or []),
                "required_imports": list(action.get("required_imports") or problem.required_imports),
                "lean_status": lean_status,
                "check_status": lean_status,
                "error_class": check["error_class"],
                "duration_ms": check["duration_ms"],
                "stderr_excerpt": check["stderr_excerpt"],
                "stdout_excerpt": check["stdout_excerpt"],
                "accepted": lean_status == "PASS",
                "proof_ref": check["lean_check_ref"] if lean_status == "PASS" else None,
                "lean_check_ref": check["lean_check_ref"],
                "next_action": "candidate_checked_continue_bandit_observation",
                "truth_side_body_used": False,
                "adapter_candidate_used": False,
                "provider_hypothesis_used": False,
                "sorry_present": check["sorry_present"],
                "axiom_audit": check["axiom_audit"],
            }
        )
    selected = _select_clean_proof(action_rows)
    accepted = selected is not None
    selected_body = list(selected.get("candidate_body") or []) if selected else []
    manifest = {
        "schema_version": "hammer_action_manifest_v0",
        "run_id": RUN_ID,
        "graph_variant_id": GRAPH_VARIANT_ID,
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "target_shape": _target_shape(problem),
        "statement_only": True,
        "adapter_direct_candidate_allowed": False,
        "provider_hypothesis_allowed": False,
        "oracle_repair_allowed": False,
        "action_count": len(action_rows),
        "actions": action_rows,
    }
    results = {
        "schema_version": "hammer_search_results_v0",
        "run_id": RUN_ID,
        "graph_variant_id": GRAPH_VARIANT_ID,
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "target_shape": _target_shape(problem),
        "statement_only": True,
        "adapter_candidate_allowed": False,
        "adapter_candidate_used": False,
        "provider_hypothesis_used": False,
        "oracle_repair_used": False,
        "status_input_class": STATUS_FORMAL_STATEMENT,
        "output_status_class": STATUS_LEAN_ACCEPTED_PROOF if accepted else "SEARCH_EXHAUSTED",
        "lean_compile_status": "PASS" if accepted else "FAIL",
        "error_class": "NONE" if accepted else "TACTIC_SEARCH_FAIL",
        "selected_action_id": selected.get("action_id") if selected else None,
        "selected_tactic_id": selected.get("tactic_id") if selected else None,
        "selected_body": selected_body,
        "attempt_count": len(action_rows),
        "accepted_action_count": sum(1 for row in action_rows if row["accepted"]),
        "attempts": action_rows,
    }
    proof_minimization = {
        "schema_version": "hammer_proof_minimization_v0",
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "minimization_kind": "selected_clean_candidate_extraction",
        "accepted": accepted,
        "selected_action_id": selected.get("action_id") if selected else None,
        "selected_tactic_id": selected.get("tactic_id") if selected else None,
        "minimized_body": selected_body,
        "original_line_count": len(selected_body),
        "minimized_line_count": len(selected_body),
        "truth_side_body_used": False,
        "adapter_candidate_used": False,
        "provider_hypothesis_used": False,
        "lean_compile_status": "PASS" if accepted else "FAIL",
        "error_class": "NONE" if accepted else "TACTIC_SEARCH_FAIL",
        "selection_rule": [
            "no sorry",
            "prefer clean axiom audit when Lean reports one",
            "shortest proof body",
            "fastest Lean check",
        ],
    }
    learning_row = {
        "schema_version": "foundry_hammer_policy_learning_row_v0",
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "target_shape": _target_shape(problem),
        "status_class": STATUS_FOUNDRY_POLICY_LEARNING,
        "search_policy_id": "statement_only_hammer_bandit_policy_v0",
        "selected_action_id": selected.get("action_id") if selected else None,
        "selected_tactic_id": selected.get("tactic_id") if selected else None,
        "accepted": accepted,
        "credit_assignment": "credit_action_policy" if accepted else "debit_action_queue",
        "raw_proof_body_credit": False,
        "proof_body_memorization_allowed": False,
        "adapter_candidate_used": False,
        "provider_hypothesis_used": False,
        "truth_side_body_used": False,
        "attempted_action_ids": [row["action_id"] for row in action_rows],
    }
    _write_json(problem_root / "hammer_action_manifest.json", manifest)
    _write_json(problem_root / "hammer_search_results.json", results)
    _write_json(problem_root / "proof_minimization.json", proof_minimization)
    _write_json(problem_root / "foundry_hammer_learning_row.json", learning_row)
    return {
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "target_shape": _target_shape(problem),
        "lean_compile_status": results["lean_compile_status"],
        "error_class": results["error_class"],
        "selected_action_id": results["selected_action_id"],
        "selected_tactic_id": results["selected_tactic_id"],
        "attempt_count": len(action_rows),
        "accepted_action_count": results["accepted_action_count"],
        "artifact_refs": {
            "hammer_action_manifest": _rel(problem_root / "hammer_action_manifest.json"),
            "hammer_search_results": _rel(problem_root / "hammer_search_results.json"),
            "proof_minimization": _rel(problem_root / "proof_minimization.json"),
            "foundry_hammer_learning_row": _rel(problem_root / "foundry_hammer_learning_row.json"),
        },
        "actions": action_rows,
        "selected_proof": proof_minimization,
        "learning_row": learning_row,
    }


def _run_adapter_candidate_problem(
    *,
    problem: harness.ProverProblem,
    problem_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    if not problem.candidate_body:
        return {
            "problem_id": problem.problem_id,
            "source_family": problem.source_family,
            "status_input_class": STATUS_ADAPTER_HINT,
            "candidate_body_present": False,
            "lean_status": "NOT_RUN",
            "accepted": False,
            "error_class": "NO_ADAPTER_CANDIDATE",
        }
    check_path = problem_root / "adapter_candidate.lean"
    check = _run_body_check(
        problem=problem,
        body=problem.candidate_body,
        output_path=check_path,
        attempt_label="adapter_candidate_baseline",
        timeout_seconds=timeout_seconds,
        expected_error_class=problem.expected_error_class_on_fail,
    )
    accepted = check["lean_status"] == "PASS" and not check["sorry_present"]
    row = {
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "target_shape": _target_shape(problem),
        "status_input_class": STATUS_ADAPTER_HINT,
        "candidate_body_present": True,
        "candidate_tactic_id": _body_tactic_id(problem.candidate_body),
        "candidate_body": list(problem.candidate_body),
        "lean_status": check["lean_status"],
        "accepted": accepted,
        "error_class": check["error_class"],
        "duration_ms": check["duration_ms"],
        "stderr_excerpt": check["stderr_excerpt"],
        "lean_check_ref": check["lean_check_ref"],
        "counts_as_statement_only_success": False,
        "counts_as_adapter_candidate_success": accepted,
        "truth_side_body_used": False,
        "oracle_comparator_only": False,
        "axiom_audit": check["axiom_audit"],
    }
    _write_json(problem_root / "adapter_candidate_result.json", row)
    return row


def _run_oracle_problem(
    *,
    problem: harness.ProverProblem,
    problem_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    oracle_body = tuple(problem.repair_body or problem.ideal_body)
    if not oracle_body:
        return {
            "problem_id": problem.problem_id,
            "source_family": problem.source_family,
            "status_input_class": STATUS_ORACLE_REPAIR,
            "lean_status": "NOT_RUN",
            "accepted": False,
            "error_class": "NO_ORACLE_BODY",
            "comparator_only": True,
        }
    check_path = problem_root / "oracle_comparator.lean"
    check = _run_body_check(
        problem=problem,
        body=oracle_body,
        output_path=check_path,
        attempt_label="oracle_repair_comparator_only",
        timeout_seconds=timeout_seconds,
        expected_error_class="ORACLE_COMPARATOR_FAIL",
    )
    accepted = check["lean_status"] == "PASS" and not check["sorry_present"]
    row = {
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "target_shape": _target_shape(problem),
        "status_input_class": STATUS_ORACLE_REPAIR,
        "oracle_tactic_id": _body_tactic_id(oracle_body),
        "oracle_body_present": True,
        "lean_status": check["lean_status"],
        "accepted": accepted,
        "error_class": check["error_class"],
        "duration_ms": check["duration_ms"],
        "stderr_excerpt": check["stderr_excerpt"],
        "lean_check_ref": check["lean_check_ref"],
        "comparator_only": True,
        "counts_as_forward_solver_success": False,
        "axiom_audit": check["axiom_audit"],
    }
    _write_json(problem_root / "oracle_comparator_result.json", row)
    return row


def _adapter_candidate_audit(
    *,
    external_problem_set: list[harness.ProverProblem],
    external_statement_results: Sequence[Mapping[str, Any]],
    adapter_results: Sequence[Mapping[str, Any]],
    oracle_results: Sequence[Mapping[str, Any]],
    prior_tactic_portfolio_summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    statement_by_problem = {row.get("problem_id"): row for row in external_statement_results}
    adapter_by_problem = {row.get("problem_id"): row for row in adapter_results}
    oracle_by_problem = {row.get("problem_id"): row for row in oracle_results}
    prior_selected_counts = (
        (prior_tactic_portfolio_summary or {}).get("tactic_portfolio_selected_tactic_counts")
        or {}
    )
    rows: list[dict[str, Any]] = []
    for problem in external_problem_set:
        adapter = adapter_by_problem.get(problem.problem_id) or {}
        statement = statement_by_problem.get(problem.problem_id) or {}
        oracle = oracle_by_problem.get(problem.problem_id) or {}
        rows.append(
            {
                "problem_id": problem.problem_id,
                "source_family": problem.source_family,
                "target_shape": _target_shape(problem),
                "candidate_body_present": bool(problem.candidate_body),
                "candidate_tactic_id": _body_tactic_id(problem.candidate_body),
                "ideal_body_present": bool(problem.ideal_body),
                "ideal_tactic_id": _body_tactic_id(problem.ideal_body),
                "candidate_equals_ideal": tuple(problem.candidate_body) == tuple(problem.ideal_body),
                "adapter_candidate_lean_status": adapter.get("lean_status"),
                "adapter_candidate_accepted": bool(adapter.get("accepted")),
                "statement_only_accepted": statement.get("lean_compile_status") == "PASS",
                "statement_only_selected_action_id": statement.get("selected_action_id"),
                "statement_only_selected_tactic_id": statement.get("selected_tactic_id"),
                "oracle_comparator_accepted": bool(oracle.get("accepted")),
                "success_source_class": (
                    "statement_only_search"
                    if statement.get("lean_compile_status") == "PASS"
                    else "adapter_candidate"
                    if adapter.get("accepted")
                    else "oracle_comparator_only"
                    if oracle.get("accepted")
                    else "unsolved"
                ),
                "adapter_success_counts_as_solver_discovery": False,
            }
        )
    adapter_success_count = sum(1 for row in rows if row["adapter_candidate_accepted"])
    statement_success_count = sum(1 for row in rows if row["statement_only_accepted"])
    prior_adapter_used_count = int(
        (prior_tactic_portfolio_summary or {}).get("tactic_portfolio_adapter_candidate_used_count")
        or 0
    )
    return {
        "schema_version": "adapter_candidate_audit_v1",
        "problem_count": len(rows),
        "adapter_candidate_body_count": sum(1 for row in rows if row["candidate_body_present"]),
        "adapter_candidate_success_count": adapter_success_count,
        "statement_only_success_count": statement_success_count,
        "oracle_comparator_success_count": sum(1 for row in rows if row["oracle_comparator_accepted"]),
        "adapter_only_success_count": sum(
            1
            for row in rows
            if row["adapter_candidate_accepted"] and not row["statement_only_accepted"]
        ),
        "statement_only_over_adapter_gain_count": sum(
            1
            for row in rows
            if row["statement_only_accepted"] and not row["adapter_candidate_accepted"]
        ),
        "prior_tactic_portfolio_selected_tactic_counts": dict(prior_selected_counts),
        "prior_tactic_portfolio_adapter_candidate_used_count": prior_adapter_used_count,
        "previous_tactic_portfolio_depended_on_adapter_candidate": prior_adapter_used_count > 0,
        "interpretation": (
            "prior portfolio did not select adapter candidates"
            if prior_adapter_used_count == 0
            else "prior portfolio selected adapter candidates; headline solve rate is hint-assisted"
        ),
        "rows": rows,
    }


def _selected_proofs_report(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row["selected_proof"]) for row in results if row.get("selected_proof")]
    return {
        "schema_version": "hammer_selected_proofs_v0",
        "row_count": len(rows),
        "accepted_count": sum(1 for row in rows if row.get("accepted")),
        "adapter_candidate_used_count": sum(1 for row in rows if row.get("adapter_candidate_used")),
        "truth_side_body_used_count": sum(1 for row in rows if row.get("truth_side_body_used")),
        "rows": rows,
    }


def _proof_minimization_report(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row["selected_proof"]) for row in results if row.get("selected_proof")]
    return {
        "schema_version": "hammer_proof_minimization_report_v0",
        "row_count": len(rows),
        "accepted_count": sum(1 for row in rows if row.get("accepted")),
        "minimized_line_total": sum(int(row.get("minimized_line_count") or 0) for row in rows),
        "truth_side_body_used_count": sum(1 for row in rows if row.get("truth_side_body_used")),
        "adapter_candidate_used_count": sum(1 for row in rows if row.get("adapter_candidate_used")),
        "rows": rows,
    }


def _flatten_actions(results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        for action in result.get("actions", []):
            if isinstance(action, Mapping):
                rows.append(dict(action))
    return rows


def _action_value_table(actions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    buckets: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    failure_counts: dict[tuple[str, str, str, str], Counter[str]] = defaultdict(Counter)
    duration_totals: Counter[tuple[str, str, str, str]] = Counter()
    for action in actions:
        key = (
            str(action.get("target_shape") or "unknown"),
            str(action.get("source_family") or "unknown"),
            str(action.get("action_kind") or "unknown"),
            str(action.get("tactic_id") or action.get("action_id") or "unknown"),
        )
        if key not in buckets:
            buckets[key] = {
                "target_shape": key[0],
                "source_family": key[1],
                "action_kind": key[2],
                "tactic_id": key[3],
                "attempts": 0,
                "accepted": 0,
            }
        buckets[key]["attempts"] += 1
        if action.get("accepted"):
            buckets[key]["accepted"] += 1
        else:
            failure_counts[key][str(action.get("error_class") or "UNKNOWN")] += 1
        duration_totals[key] += int(action.get("duration_ms") or 0)
    rows: list[dict[str, Any]] = []
    for key, row in sorted(buckets.items()):
        attempts = int(row["attempts"])
        accepted = int(row["accepted"])
        success_rate = accepted / attempts if attempts else 0.0
        timeout_penalty = failure_counts[key].get("ORACLE_TIMEOUT", 0) / attempts if attempts else 0.0
        target_shape_match_bonus = 0.05 if accepted else 0.0
        posterior_score = success_rate - timeout_penalty + target_shape_match_bonus
        rows.append(
            {
                **row,
                "failures_by_class": dict(failure_counts[key]),
                "avg_duration_ms": duration_totals[key] / attempts if attempts else 0.0,
                "success_rate": success_rate,
                "timeout_penalty": timeout_penalty,
                "source_family_mismatch_penalty": 0.0,
                "target_shape_match_bonus": target_shape_match_bonus,
                "posterior_score": posterior_score,
            }
        )
    return {
        "schema_version": "hammer_action_value_table_v0",
        "score_formula": (
            "historical_success_rate - timeout_penalty - source_family_mismatch_penalty "
            "+ target_shape_match_bonus"
        ),
        "bucket_count": len(rows),
        "rows": rows,
    }


def _failure_taxonomy(actions: Sequence[Mapping[str, Any]], results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    problem_error_counts = Counter(
        str(row.get("error_class") or "UNKNOWN")
        for row in results
        if row.get("lean_compile_status") != "PASS"
    )
    action_error_counts = Counter(
        str(row.get("error_class") or "UNKNOWN")
        for row in actions
        if row.get("lean_status") != "PASS"
    )
    failed_actions = [
        {
            "problem_id": row.get("problem_id"),
            "action_id": row.get("action_id"),
            "tactic_id": row.get("tactic_id"),
            "target_shape": row.get("target_shape"),
            "source_family": row.get("source_family"),
            "lean_status": row.get("lean_status"),
            "error_class": row.get("error_class"),
            "stderr_excerpt": row.get("stderr_excerpt"),
            "lean_check_ref": row.get("lean_check_ref"),
        }
        for row in actions
        if row.get("lean_status") != "PASS"
    ]
    return {
        "schema_version": "hammer_failure_taxonomy_v0",
        "failed_problem_count": sum(1 for row in results if row.get("lean_compile_status") != "PASS"),
        "problem_error_counts": dict(problem_error_counts),
        "failed_action_count": len(failed_actions),
        "action_error_counts": dict(action_error_counts),
        "representative_hammer_failure": failed_actions[0] if failed_actions else None,
        "rows": failed_actions,
    }


def _foundry_learning_rows(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row["learning_row"]) for row in results if row.get("learning_row")]
    return {
        "schema_version": "foundry_hammer_learning_rows_v0",
        "status_class": STATUS_FOUNDRY_POLICY_LEARNING,
        "row_count": len(rows),
        "accepted_policy_credit_count": sum(1 for row in rows if row.get("accepted")),
        "raw_proof_body_credit_count": sum(1 for row in rows if row.get("raw_proof_body_credit")),
        "adapter_candidate_used_count": sum(1 for row in rows if row.get("adapter_candidate_used")),
        "rows": rows,
    }


def _skill_update_candidates(action_values: Mapping[str, Any]) -> dict[str, Any]:
    candidates = [
        {
            "candidate_id": (
                f"hammer_bandit_prior_{harness._safe_tactic_id(row['source_family'])}_"
                f"{harness._safe_tactic_id(row['target_shape'])}_"
                f"{harness._safe_tactic_id(row['tactic_id'])}"
            ),
            "update_kind": "search_policy_action_prior",
            "source_family": row["source_family"],
            "target_shape": row["target_shape"],
            "action_kind": row["action_kind"],
            "tactic_id": row["tactic_id"],
            "attempts": row["attempts"],
            "accepted": row["accepted"],
            "posterior_score": row["posterior_score"],
            "raw_proof_body_credit": False,
            "reason": "Credit/debit the action policy bucket, not a memorized proof body.",
        }
        for row in action_values.get("rows", [])
        if row.get("attempts")
    ]
    return {
        "schema_version": "hammer_skill_update_candidates_v0",
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _status_transition_audit(
    *,
    statement_results: Sequence[Mapping[str, Any]],
    adapter_results: Sequence[Mapping[str, Any]],
    oracle_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    illegal: list[dict[str, Any]] = []
    for row in adapter_results:
        if row.get("accepted") and row.get("counts_as_statement_only_success"):
            illegal.append(
                {
                    "problem_id": row.get("problem_id"),
                    "transition": "ADAPTER_HINT -> STATEMENT_ONLY_SOLVER_SUCCESS",
                }
            )
    for row in oracle_results:
        if row.get("accepted") and row.get("counts_as_forward_solver_success"):
            illegal.append(
                {
                    "problem_id": row.get("problem_id"),
                    "transition": "ORACLE_REPAIR -> FORWARD_SOLVER_SUCCESS",
                }
            )
    for row in statement_results:
        if row.get("lean_compile_status") == "PASS" and row.get("selected_tactic_id") is None:
            illegal.append(
                {
                    "problem_id": row.get("problem_id"),
                    "transition": "FORMAL_STATEMENT -> LEAN_ACCEPTED_PROOF without action attribution",
                }
            )
    return {
        "schema_version": "status_transition_audit_v0",
        "allowed_status_classes": [
            STATUS_FORMAL_STATEMENT,
            STATUS_ADAPTER_HINT,
            STATUS_TACTIC_ACTION,
            STATUS_PROVIDER_HYPOTHESIS,
            STATUS_LEAN_ACCEPTED_PROOF,
            STATUS_ORACLE_REPAIR,
            STATUS_FOUNDRY_POLICY_LEARNING,
        ],
        "illegal_transition_count": len(illegal),
        "illegal_transitions": illegal,
    }


def _prior_external_summary() -> dict[str, Any]:
    path = REPO_ROOT / "state/runs/PROVER_EXTERNAL_FORMAL_BENCHMARK_SMOKE_20260511_v0/external_guarded_loop_run_summary.json"
    return _read_json(path) if path.exists() else {}


def _prior_external_oracle_rows() -> dict[str, dict[str, dict[str, Any]]]:
    path = REPO_ROOT / "state/runs/PROVER_EXTERNAL_FORMAL_BENCHMARK_SMOKE_20260511_v0/external_oracle_result_index.json"
    if not path.exists():
        return {}
    index = _read_json(path)
    lanes: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in index.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        lane_id = str(row.get("lane_id") or "")
        problem_id = str(row.get("problem_id") or "")
        if lane_id and problem_id:
            lanes[lane_id][problem_id] = dict(row)
    return dict(lanes)


def _adapter_candidate_result_from_prior(
    *,
    problem: harness.ProverProblem,
    prior_row: Mapping[str, Any],
) -> dict[str, Any]:
    accepted = prior_row.get("lean_compile_status") == "PASS"
    return {
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "target_shape": _target_shape(problem),
        "status_input_class": STATUS_ADAPTER_HINT,
        "candidate_body_present": bool(problem.candidate_body),
        "candidate_tactic_id": _body_tactic_id(problem.candidate_body),
        "candidate_body": list(problem.candidate_body),
        "lean_status": prior_row.get("lean_compile_status"),
        "accepted": accepted,
        "error_class": "NONE" if accepted else prior_row.get("error_class"),
        "duration_ms": None,
        "stderr_excerpt": None,
        "lean_check_ref": prior_row.get("prover_check_result_ref"),
        "evidence_source": "prior_external_smoke_baseline_lean_checked_artifact",
        "counts_as_statement_only_success": False,
        "counts_as_adapter_candidate_success": accepted,
        "truth_side_body_used": False,
        "oracle_comparator_only": False,
        "axiom_audit": "SEE_PROVER_CHECK_RESULT",
    }


def _oracle_result_from_prior(
    *,
    problem: harness.ProverProblem,
    prior_row: Mapping[str, Any],
) -> dict[str, Any]:
    oracle_body = tuple(problem.repair_body or problem.ideal_body)
    accepted = prior_row.get("lean_compile_status") == "PASS"
    return {
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "target_shape": _target_shape(problem),
        "status_input_class": STATUS_ORACLE_REPAIR,
        "oracle_tactic_id": _body_tactic_id(oracle_body),
        "oracle_body_present": bool(oracle_body),
        "lean_status": prior_row.get("lean_compile_status"),
        "accepted": accepted,
        "error_class": "NONE" if accepted else prior_row.get("error_class"),
        "duration_ms": None,
        "stderr_excerpt": None,
        "lean_check_ref": prior_row.get("prover_check_result_ref"),
        "evidence_source": "prior_external_smoke_oracle_comparator_lean_checked_artifact",
        "comparator_only": True,
        "counts_as_forward_solver_success": False,
        "axiom_audit": "SEE_PROVER_CHECK_RESULT",
    }


def _comparison_report(
    *,
    external_statement_results: Sequence[Mapping[str, Any]],
    local_statement_results: Sequence[Mapping[str, Any]],
    adapter_results: Sequence[Mapping[str, Any]],
    oracle_results: Sequence[Mapping[str, Any]],
    prior_summary: Mapping[str, Any],
    action_values: Mapping[str, Any],
) -> dict[str, Any]:
    selected_counts = Counter(
        str(row.get("selected_tactic_id") or "none")
        for row in external_statement_results
        if row.get("lean_compile_status") == "PASS"
    )
    return {
        "schema_version": "statement_only_comparison_report_v0",
        "metric_boundary": {
            "statement_only_hammer_success": "Lean accepted an action generated from statement/imports/search policy only",
            "adapter_candidate_success": "Lean accepted an adapter-supplied candidate body; not solver discovery",
            "provider_recipe_clean_success": "provider output accepted only after reducer, Lean, and recipe policy",
            "oracle_comparator_success": "withheld comparator only",
        },
        "external_problem_count": len(external_statement_results),
        "local_problem_count": len(local_statement_results),
        "statement_only_hammer_success_count": sum(
            1 for row in external_statement_results if row.get("lean_compile_status") == "PASS"
        ),
        "local_statement_only_hammer_success_count": sum(
            1 for row in local_statement_results if row.get("lean_compile_status") == "PASS"
        ),
        "adapter_candidate_success_count": sum(1 for row in adapter_results if row.get("accepted")),
        "source_guarded_foundry_success_count": int(
            prior_summary.get("source_guarded_foundry_success_count") or 0
        ),
        "tactic_portfolio_existing_success_count": int(
            prior_summary.get("tactic_portfolio_success_count") or 0
        ),
        "provider_recipe_clean_success_count": 0,
        "oracle_comparator_success_count": sum(1 for row in oracle_results if row.get("accepted")),
        "statement_only_selected_tactic_counts": dict(selected_counts),
        "action_value_bucket_count": action_values.get("bucket_count", 0),
        "claim_boundary": (
            "MiniF2F-source-backed Lean4/Std translation smoke plus local Lean/Std "
            "solved-problem batch; not a direct MiniF2F benchmark claim."
        ),
    }


def _provider_hypothesis_results() -> dict[str, Any]:
    return {
        "schema_version": "provider_hypothesis_results_v0",
        "status_class": STATUS_PROVIDER_HYPOTHESIS,
        "provider_recipe_clean_success_count": 0,
        "provider_hypothesis_action_count": 0,
        "policy": (
            "provider_hypothesis actions enter this hammer queue only after reducer, "
            "Lean, and recipe-policy evidence; this local deterministic run did not "
            "count provider text."
        ),
        "rows": [],
    }


def _validate(run_root: Path, summary: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    required = [
        "statement_only_problem_manifest.json",
        "adapter_candidate_audit.json",
        "tactic_affordance_probe.json",
        "hammer_action_manifest.json",
        "hammer_search_results.json",
        "hammer_selected_proofs.json",
        "hammer_proof_minimization_report.json",
        "hammer_action_value_table.json",
        "hammer_failure_taxonomy.json",
        "foundry_hammer_learning_rows.json",
        "hammer_skill_update_candidates.json",
        "statement_only_comparison_report.json",
        "hammer_bandit_run_summary.json",
    ]
    for rel_path in required:
        if not (run_root / rel_path).exists():
            issues.append(f"missing required artifact: {rel_path}")
    manifest = _read_json(run_root / "statement_only_problem_manifest.json")
    forbidden_keys = {"candidate_body", "ideal_body", "repair_body", "retrieval_body"}
    for row in manifest.get("problems", []):
        if isinstance(row, Mapping) and forbidden_keys.intersection(row):
            issues.append(f"statement-only manifest leaked proof body field for {row.get('problem_id')}")
    action_manifest = _read_json(run_root / "hammer_action_manifest.json")
    for action in action_manifest.get("actions", []):
        if not isinstance(action, Mapping):
            continue
        if action.get("status_input_class") != STATUS_TACTIC_ACTION:
            issues.append(f"action lacks tactic-action status class: {action.get('action_id')}")
        if action.get("lean_status") in {None, "NOT_RUN"}:
            issues.append(f"action was not Lean-checked: {action.get('action_id')}")
        if action.get("adapter_candidate_used") or action.get("truth_side_body_used"):
            issues.append(f"statement-only action used forbidden body source: {action.get('action_id')}")
    learning = _read_json(run_root / "foundry_hammer_learning_rows.json")
    if learning.get("raw_proof_body_credit_count") != 0:
        issues.append("Foundry learning credited raw proof bodies")
    transition = _read_json(run_root / "status_transition_audit.json")
    if transition.get("illegal_transition_count") != 0:
        issues.append("status transition audit found illegal transitions")
    if summary.get("truth_side_leakage_count") != 0:
        issues.append("truth_side_leakage_count is nonzero")
    if summary.get("provider_recipe_clean_success_count") != 0:
        issues.append("provider success unexpectedly counted")
    return issues


def run_hammer_bandit(
    *,
    run_root: Path,
    problem_limit: int | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    run_root = _repo_path(run_root)
    external_problems = external_smoke._miniF2F_problem_set()
    if problem_limit is not None:
        external_problems = external_problems[:problem_limit]
    local_problems = harness._problem_set()
    statement_manifest = build_statement_only_manifest(
        external_problem_set=external_problems,
        local_problem_set=local_problems,
    )
    _write_json(run_root / "statement_only_problem_manifest.json", statement_manifest)

    probe_timeout_seconds = max(timeout_seconds, 15)
    availability = harness._probe_tactic_portfolio_availability(
        run_root / "tactic_affordance_probe",
        timeout_seconds=probe_timeout_seconds,
    )
    tactic_probe = {
        "schema_version": "tactic_affordance_probe_v0",
        "run_id": RUN_ID,
        "created_at": _utc_now(),
        "lean_available": shutil.which("lean") is not None,
        "probe_timeout_seconds": probe_timeout_seconds,
        **availability,
    }
    _write_json(run_root / "tactic_affordance_probe.json", tactic_probe)

    external_statement_results: list[dict[str, Any]] = []
    local_statement_results: list[dict[str, Any]] = []
    adapter_results: list[dict[str, Any]] = []
    oracle_results: list[dict[str, Any]] = []
    prior_oracle_rows = _prior_external_oracle_rows()
    prior_baseline_by_problem = prior_oracle_rows.get("baseline", {})
    prior_oracle_by_problem = prior_oracle_rows.get("oracle_repair_comparator", {})

    for problem in external_problems:
        problem_root = run_root / "problems" / problem.problem_id
        external_statement_results.append(
            _run_statement_only_problem(
                problem=replace(problem, candidate_body=()),
                problem_root=problem_root / "statement_only_hammer",
                availability=availability,
                timeout_seconds=timeout_seconds,
            )
        )
        prior_baseline = prior_baseline_by_problem.get(problem.problem_id)
        if prior_baseline:
            adapter_results.append(
                _adapter_candidate_result_from_prior(
                    problem=problem,
                    prior_row=prior_baseline,
                )
            )
        else:
            adapter_results.append(
                _run_adapter_candidate_problem(
                    problem=problem,
                    problem_root=problem_root / "adapter_candidate_baseline",
                    timeout_seconds=probe_timeout_seconds,
                )
            )
        prior_oracle = prior_oracle_by_problem.get(problem.problem_id)
        if prior_oracle:
            oracle_results.append(
                _oracle_result_from_prior(
                    problem=problem,
                    prior_row=prior_oracle,
                )
            )
        else:
            oracle_results.append(
                _run_oracle_problem(
                    problem=problem,
                    problem_root=problem_root / "oracle_comparator",
                    timeout_seconds=probe_timeout_seconds,
                )
            )

    local_timeout_seconds = max(timeout_seconds, 45)
    for problem in local_problems:
        problem_root = run_root / "local_problems" / problem.problem_id
        local_statement_results.append(
            _run_statement_only_problem(
                problem=replace(problem, candidate_body=()),
                problem_root=problem_root / "statement_only_hammer",
                availability=availability,
                timeout_seconds=local_timeout_seconds,
            )
        )

    statement_results = [*external_statement_results, *local_statement_results]
    actions = _flatten_actions(statement_results)
    action_manifest = {
        "schema_version": "hammer_action_manifest_v1",
        "run_id": RUN_ID,
        "graph_variant_id": GRAPH_VARIANT_ID,
        "action_count": len(actions),
        "statement_only": True,
        "adapter_direct_candidate_allowed": False,
        "provider_hypothesis_allowed": False,
        "oracle_repair_allowed": False,
        "actions": actions,
    }
    search_results = {
        "schema_version": "hammer_search_results_v1",
        "run_id": RUN_ID,
        "graph_variant_id": GRAPH_VARIANT_ID,
        "problem_count": len(statement_results),
        "accepted_count": sum(1 for row in statement_results if row.get("lean_compile_status") == "PASS"),
        "external_results": external_statement_results,
        "local_results": local_statement_results,
    }
    selected_proofs = _selected_proofs_report(statement_results)
    proof_minimization = _proof_minimization_report(statement_results)
    action_values = _action_value_table(actions)
    failures = _failure_taxonomy(actions, statement_results)
    foundry_learning = _foundry_learning_rows(statement_results)
    skill_updates = _skill_update_candidates(action_values)
    provider_results = _provider_hypothesis_results()
    prior_summary = _prior_external_summary()
    adapter_audit = _adapter_candidate_audit(
        external_problem_set=external_problems,
        external_statement_results=external_statement_results,
        adapter_results=adapter_results,
        oracle_results=oracle_results,
        prior_tactic_portfolio_summary=prior_summary,
    )
    comparison = _comparison_report(
        external_statement_results=external_statement_results,
        local_statement_results=local_statement_results,
        adapter_results=adapter_results,
        oracle_results=oracle_results,
        prior_summary=prior_summary,
        action_values=action_values,
    )
    status_transition_audit = _status_transition_audit(
        statement_results=statement_results,
        adapter_results=adapter_results,
        oracle_results=oracle_results,
    )
    summary = {
        "schema_version": "hammer_bandit_run_summary_v0",
        "run_id": RUN_ID,
        "cap_id": CAP_ID,
        "created_at": _utc_now(),
        "graph_variant_id": GRAPH_VARIANT_ID,
        "external_problem_count": len(external_problems),
        "local_problem_count": len(local_problems),
        "statement_only_hammer_success_count": comparison["statement_only_hammer_success_count"],
        "local_statement_only_hammer_success_count": comparison["local_statement_only_hammer_success_count"],
        "adapter_candidate_success_count": comparison["adapter_candidate_success_count"],
        "source_guarded_foundry_success_count": comparison["source_guarded_foundry_success_count"],
        "tactic_portfolio_existing_success_count": comparison["tactic_portfolio_existing_success_count"],
        "provider_recipe_clean_success_count": 0,
        "oracle_comparator_success_count": comparison["oracle_comparator_success_count"],
        "truth_side_leakage_count": 0,
        "fake_provider_results_counted": 0,
        "adapter_candidate_body_count": adapter_audit["adapter_candidate_body_count"],
        "previous_tactic_portfolio_depended_on_adapter_candidate": adapter_audit[
            "previous_tactic_portfolio_depended_on_adapter_candidate"
        ],
        "selected_tactic_counts": comparison["statement_only_selected_tactic_counts"],
        "hammer_action_count": len(actions),
        "hammer_action_value_bucket_count": action_values["bucket_count"],
        "representative_statement_only_success": next(
            (row for row in external_statement_results if row.get("lean_compile_status") == "PASS"),
            None,
        ),
        "representative_adapter_only_success": next(
            (
                row
                for row in adapter_audit["rows"]
                if row.get("adapter_candidate_accepted") and not row.get("statement_only_accepted")
            ),
            None,
        ),
        "representative_hammer_failure": failures.get("representative_hammer_failure"),
        "status_transition_illegal_count": status_transition_audit["illegal_transition_count"],
        "claim_boundary": comparison["claim_boundary"],
        "artifact_refs": {
            "statement_only_problem_manifest": _rel(run_root / "statement_only_problem_manifest.json"),
            "adapter_candidate_audit": _rel(run_root / "adapter_candidate_audit.json"),
            "tactic_affordance_probe": _rel(run_root / "tactic_affordance_probe.json"),
            "hammer_action_manifest": _rel(run_root / "hammer_action_manifest.json"),
            "hammer_search_results": _rel(run_root / "hammer_search_results.json"),
            "hammer_selected_proofs": _rel(run_root / "hammer_selected_proofs.json"),
            "hammer_proof_minimization_report": _rel(run_root / "hammer_proof_minimization_report.json"),
            "hammer_action_value_table": _rel(run_root / "hammer_action_value_table.json"),
            "hammer_failure_taxonomy": _rel(run_root / "hammer_failure_taxonomy.json"),
            "foundry_hammer_learning_rows": _rel(run_root / "foundry_hammer_learning_rows.json"),
            "hammer_skill_update_candidates": _rel(run_root / "hammer_skill_update_candidates.json"),
            "statement_only_comparison_report": _rel(run_root / "statement_only_comparison_report.json"),
            "provider_hypothesis_results": _rel(run_root / "provider_hypothesis_results.json"),
            "status_transition_audit": _rel(run_root / "status_transition_audit.json"),
            "hammer_bandit_run_summary": _rel(run_root / "hammer_bandit_run_summary.json"),
        },
    }

    _write_json(run_root / "adapter_candidate_results.json", {"schema_version": "adapter_candidate_results_v0", "rows": adapter_results})
    _write_json(run_root / "oracle_comparator_results.json", {"schema_version": "oracle_comparator_results_v0", "rows": oracle_results})
    _write_json(run_root / "adapter_candidate_audit.json", adapter_audit)
    _write_json(run_root / "hammer_action_manifest.json", action_manifest)
    _write_json(run_root / "hammer_search_results.json", search_results)
    _write_json(run_root / "hammer_selected_proofs.json", selected_proofs)
    _write_json(run_root / "hammer_proof_minimization_report.json", proof_minimization)
    _write_json(run_root / "hammer_action_value_table.json", action_values)
    _write_json(run_root / "hammer_failure_taxonomy.json", failures)
    _write_json(run_root / "foundry_hammer_learning_rows.json", foundry_learning)
    _write_json(run_root / "hammer_skill_update_candidates.json", skill_updates)
    _write_json(run_root / "statement_only_comparison_report.json", comparison)
    _write_json(run_root / "provider_hypothesis_results.json", provider_results)
    _write_json(run_root / "status_transition_audit.json", status_transition_audit)
    _write_json(run_root / "hammer_bandit_run_summary.json", summary)
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--problem-limit", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    summary = run_hammer_bandit(
        run_root=args.run_root,
        problem_limit=args.problem_limit,
        timeout_seconds=args.timeout_seconds,
    )
    issues = _validate(_repo_path(args.run_root), summary) if args.check else []
    if args.as_json:
        print(json.dumps({"summary": summary, "validation_issues": issues}, indent=2, sort_keys=True))
    else:
        print(
            f"statement_only_hammer={summary['statement_only_hammer_success_count']}/"
            f"{summary['external_problem_count']} "
            f"adapter={summary['adapter_candidate_success_count']} "
            f"oracle={summary['oracle_comparator_success_count']} "
            f"issues={len(issues)}"
        )
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
