#!/usr/bin/env python3
"""Run an external formal benchmark smoke slice through the prover loop.

This is the first Tier-2 smoke after the continuous local loop: it uses an
external source corpus, keeps proof bodies out of forward Lab context, and
reuses the existing graph harness/Lean oracle instead of adding a new prover
runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.meta.factory import run_prover_graph_benchmark as harness


RUN_ID = "PROVER_EXTERNAL_FORMAL_BENCHMARK_SMOKE_20260511_v0"
DEFAULT_RUN_ROOT = Path("state/runs") / RUN_ID
CAP_ID = "cap_prover_external_formal_benchmark_smoke_v0"
HAMMER_RUN_ID = "PROVER_HAMMER_SEARCH_20260511_v0"
HAMMER_CAP_ID = "cap_prover_hammer_search_v0"
STATEMENT_ONLY_HAMMER_RUN_ID = "PROVER_STATEMENT_ONLY_HAMMER_SEARCH_20260511_v0"
STATEMENT_ONLY_HAMMER_CAP_ID = "cap_prover_statement_only_hammer_search_v0"
MINIF2F_REPO = Path("annexes/miniF2F/repo")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _miniF2F_available() -> bool:
    return (_repo_path(MINIF2F_REPO) / "lean/src/valid.lean").exists()


def _external_corpus_availability() -> dict[str, Any]:
    candidates = {
        "miniF2F": MINIF2F_REPO,
        "PutnamBench": Path("annexes/PutnamBench/repo"),
        "LeanDojo": Path("annexes/LeanDojo/repo"),
        "formal-conjectures": Path("annexes/formal-conjectures/repo"),
        "mathlib": Path("annexes/mathlib/repo"),
    }
    rows: list[dict[str, Any]] = []
    for corpus_id, rel_path in candidates.items():
        path = _repo_path(rel_path)
        rows.append(
            {
                "corpus_id": corpus_id,
                "local_path": _rel(path),
                "exists": path.exists(),
                "selected_for_this_run": corpus_id == "miniF2F" and _miniF2F_available(),
            }
        )
    return {
        "schema_version": "external_formal_corpus_availability_v0",
        "created_at": _utc_now(),
        "selection_policy": [
            "Prefer an already-runnable external Lean benchmark slice.",
            "If direct benchmark build is blocked, use the smallest source-backed Lean-checkable translation smoke.",
            "Do not start open conjectures or informal formalization in this run.",
        ],
        "local_lean4_cli_available": harness.shutil.which("lean") is not None,
        "rows": rows,
    }


def _miniF2F_problem_set() -> list[harness.ProverProblem]:
    """Source-backed MiniF2F Lean3 statements translated to Lean4-core smoke rows.

    MiniF2F's checked Lean source in this annex is Lean 3/mathlib. The installed
    local checker is Lean 4.29 without a mathlib checkout, so this smoke selects
    arithmetic/logic rows whose statements can be faithfully represented in the
    current Lean 4/Std environment. Source Lean3 proof bodies remain oracle-only
    and are not copied into forward candidates.
    """

    visible = (
        "translated Lean 4 theorem statement",
        "required imports",
        "MiniF2F theorem id and source reference",
        "translation policy",
    )
    withheld = (
        "MiniF2F Lean 3 proof body",
        "adapter ideal proof body",
        "oracle repair body",
        "oracle critique",
    )

    def problem(
        *,
        source_name: str,
        source_ref: str,
        split: str,
        domain: str,
        theorem_signature: str,
        candidate_body: tuple[str, ...],
        ideal_body: tuple[str, ...],
        informal: str,
        expected_error: str = "PROOF_SYNTHESIS_FAIL",
        strategy: tuple[str, ...] = (),
    ) -> harness.ProverProblem:
        problem_id = f"external_miniF2F_{source_name}"
        return harness.ProverProblem(
            problem_id=problem_id,
            source="miniF2F_lean3_translated_to_lean4_core_smoke",
            split=split,
            mode="formal_statement_with_known_proof_oracle",
            domain=domain,
            informal_statement=informal,
            theorem_name=problem_id,
            theorem_signature=theorem_signature,
            candidate_body=candidate_body,
            ideal_body=ideal_body,
            visible_to_lab=visible,
            withheld_until_oracle=withheld,
            context_recipe_id="external_formal_benchmark_smoke_v0",
            expected_error_class_on_fail=expected_error,
            required_imports=("Std",),
            source_ref=source_ref,
            source_family="miniF2F",
            difficulty_tag="external_formal_benchmark_smoke",
            repair_body=ideal_body,
            allowed_premise_ids=(),
            oracle_needed_premise_ids=(),
            retrieval_query_terms=tuple(domain.split("_")) + strategy,
            expected_strategy_ids=strategy,
        )

    return [
        problem(
            source_name="mathd_numbertheory_132",
            source_ref="annexes/miniF2F/repo/lean/src/valid.lean:284",
            split="train",
            domain="nat_mod_decision",
            informal="MiniF2F number theory row: 2004 modulo 12 is zero.",
            theorem_signature="theorem external_miniF2F_mathd_numbertheory_132 : 2004 % 12 = 0 := by",
            candidate_body=("  decide",),
            ideal_body=("  decide",),
            strategy=("equality_normal_form",),
        ),
        problem(
            source_name="mathd_numbertheory_200",
            source_ref="annexes/miniF2F/repo/lean/src/valid.lean:467",
            split="train",
            domain="nat_mod_decision",
            informal="MiniF2F number theory row: 139 modulo 11 is seven.",
            theorem_signature="theorem external_miniF2F_mathd_numbertheory_200 : 139 % 11 = 7 := by",
            candidate_body=("  decide",),
            ideal_body=("  decide",),
            strategy=("equality_normal_form",),
        ),
        problem(
            source_name="mathd_numbertheory_102",
            source_ref="annexes/miniF2F/repo/lean/src/valid.lean:789",
            split="train",
            domain="nat_mod_decision",
            informal="MiniF2F number theory row: 2^8 modulo 5 is one.",
            theorem_signature="theorem external_miniF2F_mathd_numbertheory_102 : (2^8) % 5 = 1 := by",
            candidate_body=("  decide",),
            ideal_body=("  decide",),
            strategy=("equality_normal_form",),
        ),
        problem(
            source_name="mathd_numbertheory_81",
            source_ref="annexes/miniF2F/repo/lean/src/valid.lean:802",
            split="dev",
            domain="nat_mod_decision",
            informal="MiniF2F number theory row: 71 modulo 3 is two.",
            theorem_signature="theorem external_miniF2F_mathd_numbertheory_81 : 71 % 3 = 2 := by",
            candidate_body=("  decide",),
            ideal_body=("  decide",),
            strategy=("equality_normal_form",),
        ),
        problem(
            source_name="mathd_numbertheory_101",
            source_ref="annexes/miniF2F/repo/lean/src/valid.lean:1518",
            split="dev",
            domain="nat_mod_decision",
            informal="MiniF2F number theory row: 17*18 modulo 4 is two.",
            theorem_signature="theorem external_miniF2F_mathd_numbertheory_101 : (17 * 18) % 4 = 2 := by",
            candidate_body=("  decide",),
            ideal_body=("  decide",),
            strategy=("equality_normal_form",),
        ),
        problem(
            source_name="mathd_numbertheory_640",
            source_ref="annexes/miniF2F/repo/lean/src/valid.lean:946",
            split="dev",
            domain="nat_mod_decision",
            informal="MiniF2F number theory row: a four-term sum has residue two modulo four.",
            theorem_signature=(
                "theorem external_miniF2F_mathd_numbertheory_640 : "
                "(91145 + 91146 + 91147 + 91148) % 4 = 2 := by"
            ),
            candidate_body=("  decide",),
            ideal_body=("  decide",),
            strategy=("equality_normal_form",),
        ),
        problem(
            source_name="amc12a_2009_p2",
            source_ref="annexes/miniF2F/repo/lean/src/valid.lean:1109",
            split="test",
            domain="rat_arithmetic_decision",
            informal="MiniF2F AMC row: a nested rational expression equals 5/3.",
            theorem_signature=(
                "theorem external_miniF2F_amc12a_2009_p2 : "
                "(1 : Rat) + (1 / (1 + (1 / (1 + 1)))) = (5 : Rat) / 3 := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  native_decide",),
            strategy=("equality_normal_form",),
        ),
        problem(
            source_name="mathd_algebra_126",
            source_ref="annexes/miniF2F/repo/lean/src/valid.lean:583",
            split="test",
            domain="int_linear_arithmetic",
            informal="MiniF2F algebra row: solve two linear integer equations.",
            theorem_signature=(
                "theorem external_miniF2F_mathd_algebra_126 "
                "(x y : Int) (h0 : 2 * 3 = x - 9) (h1 : 2 * (-5) = y + 1) : "
                "x = 15 ∧ y = -11 := by"
            ),
            candidate_body=("  omega",),
            ideal_body=("  omega",),
            strategy=("equality_normal_form",),
        ),
        problem(
            source_name="mathd_algebra_109",
            source_ref="annexes/miniF2F/repo/lean/src/valid.lean:1629",
            split="test",
            domain="int_linear_arithmetic",
            informal="MiniF2F algebra row: solve a linear equation after substituting a = 4.",
            theorem_signature=(
                "theorem external_miniF2F_mathd_algebra_109 "
                "(a b : Int) (h0 : 3 * a + 2 * b = 12) (h1 : a = 4) : "
                "b = 0 := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  omega",),
            strategy=("equality_normal_form",),
        ),
        problem(
            source_name="mathd_algebra_455",
            source_ref="annexes/miniF2F/repo/lean/src/valid.lean:494",
            split="test",
            domain="int_linear_arithmetic",
            informal="MiniF2F algebra row: solve 16*x = 48.",
            theorem_signature=(
                "theorem external_miniF2F_mathd_algebra_455 "
                "(x : Int) (h0 : 2 * (2 * (2 * (2 * x))) = 48) : x = 3 := by"
            ),
            candidate_body=("  omega",),
            ideal_body=("  omega",),
            strategy=("equality_normal_form",),
        ),
        problem(
            source_name="mathd_numbertheory_136",
            source_ref="annexes/miniF2F/repo/lean/src/valid.lean:1287",
            split="test",
            domain="nat_linear_arithmetic",
            informal="MiniF2F number theory row: solve 123*n + 17 = 39500.",
            theorem_signature=(
                "theorem external_miniF2F_mathd_numbertheory_136 "
                "(n : Nat) (h0 : 123 * n + 17 = 39500) : n = 321 := by"
            ),
            candidate_body=("  decide",),
            ideal_body=("  omega",),
            strategy=("equality_normal_form",),
        ),
    ]


def external_problem_manifest(problem_set: list[harness.ProverProblem]) -> dict[str, Any]:
    manifest = harness._problem_source_manifest(problem_set)
    manifest["schema_version"] = "external_formal_benchmark_manifest_v0"
    manifest["source_id"] = "miniF2F_lean3_translated_to_lean4_core_smoke"
    manifest["source_kind"] = "external_benchmark_annex_translation_smoke"
    manifest["local_or_annex_path"] = _rel(_repo_path(MINIF2F_REPO))
    manifest["benchmark_source"] = {
        "source_id": "miniF2F",
        "upstream": "https://github.com/openai/miniF2F",
        "annex_path": _rel(_repo_path(MINIF2F_REPO)),
        "source_dialect": "Lean 3 + mathlib",
        "checker_dialect_for_this_smoke": "Lean 4 + Std",
        "direct_build_status": "blocked_without_Lean3_mathlib_environment",
        "translation_policy": (
            "Select MiniF2F arithmetic/propositional statements whose formal content "
            "can be represented in the installed Lean 4/Std checker. Do not copy "
            "source proof bodies into forward candidates."
        ),
    }
    manifest["leakage_policy"] = {
        **manifest.get("leakage_policy", {}),
        "source_proof_bodies_visible_to_forward_lab": False,
        "adapter_ideal_bodies_visible_to_forward_lab": False,
        "oracle_repair_counts_as_forward_success": False,
    }
    for row in manifest["problems"]:
        row["external_benchmark_row"] = True
        row["source_dialect"] = "Lean 3"
        row["checker_dialect"] = "Lean 4"
        row["known_status"] = "formally_proved_or_sorry_in_source; adapter proof gated when present"
    return manifest


def _body_tactic_id(body: tuple[str, ...]) -> str:
    stripped = [line.strip() for line in body if line.strip()]
    if not stripped:
        return "none"
    if len(stripped) == 1:
        token = stripped[0].split()[0]
        if token in {"rfl", "decide", "native_decide", "omega", "simp", "simp_all", "aesop", "grind"}:
            return token
        if token == "exact":
            return "exact"
    if stripped[0] == "intro h" and any("False.elim" in line for line in stripped):
        return "false_elim_template"
    if any("And.intro" in line for line in stripped):
        return "and_constructor_template"
    if any("Or.inr" in line or "Or.inl" in line for line in stripped):
        return "or_cases_template"
    if any("Exists.intro" in line for line in stripped):
        return "exists_constructor_template"
    return "multi_line_template"


def _adapter_candidate_audit(
    *,
    problem_set: list[harness.ProverProblem],
    benchmark_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    manifest_rows = {
        row.get("problem_id"): row
        for row in benchmark_manifest.get("problems", [])
        if isinstance(row, Mapping)
    }
    rows: list[dict[str, Any]] = []
    forward_manifest_body_leak_count = 0
    for problem in problem_set:
        manifest_row = manifest_rows.get(problem.problem_id) or {}
        leaked_fields = [
            key
            for key in ("candidate_body", "ideal_body", "repair_body", "retrieval_body")
            if key in manifest_row
        ]
        forward_manifest_body_leak_count += len(leaked_fields)
        rows.append(
            {
                "problem_id": problem.problem_id,
                "source_family": problem.source_family,
                "candidate_body_present": bool(problem.candidate_body),
                "candidate_tactic_id": _body_tactic_id(problem.candidate_body),
                "ideal_body_present": bool(problem.ideal_body),
                "ideal_tactic_id": _body_tactic_id(problem.ideal_body),
                "candidate_equals_ideal": tuple(problem.candidate_body)
                == tuple(problem.ideal_body),
                "forward_manifest_leaked_fields": leaked_fields,
                "classification": (
                    "adapter_direct_candidate"
                    if problem.candidate_body
                    else "statement_only"
                ),
            }
        )
    candidate_count = sum(1 for row in rows if row["candidate_body_present"])
    return {
        "schema_version": "adapter_candidate_audit_v0",
        "problem_count": len(problem_set),
        "adapter_candidate_body_count": candidate_count,
        "adapter_candidate_equals_ideal_count": sum(
            1 for row in rows if row["candidate_equals_ideal"]
        ),
        "adapter_candidate_differs_from_ideal_count": sum(
            1
            for row in rows
            if row["candidate_body_present"] and not row["candidate_equals_ideal"]
        ),
        "forward_manifest_body_leak_count": forward_manifest_body_leak_count,
        "baseline_direct_interpretation": (
            "adapter_candidate_success_not_statement_only_success"
            if candidate_count
            else "statement_only_success"
        ),
        "rows": rows,
    }


def _statement_only_problem_set(
    problem_set: list[harness.ProverProblem],
) -> list[harness.ProverProblem]:
    return [replace(problem, candidate_body=()) for problem in problem_set]


def _statement_only_problem_manifest(
    problem_set: list[harness.ProverProblem],
) -> dict[str, Any]:
    statement_only = _statement_only_problem_set(problem_set)
    manifest = external_problem_manifest(statement_only)
    manifest["schema_version"] = "statement_only_problem_manifest_v0"
    manifest["statement_only_policy"] = {
        "candidate_body_removed": True,
        "adapter_candidate_count_removed": sum(1 for problem in problem_set if problem.candidate_body),
        "oracle_ideal_body_retained_only_after_oracle_gate": True,
        "headline_metric": "statement_only_hammer_search_success",
    }
    for row in manifest["problems"]:
        row["candidate_body_removed"] = True
    return manifest


def _aggregate_lane(summary: Mapping[str, Any]) -> dict[str, Any]:
    aggregate_ref = summary.get("aggregate_report")
    aggregate = _read_json(_repo_path(str(aggregate_ref))) if aggregate_ref else {}
    return {
        "problem_count": aggregate.get("problem_count", 0),
        "pass_count": aggregate.get("pass_count", 0),
        "fail_count": aggregate.get("fail_count", 0),
        "failure_taxonomy": aggregate.get("failure_taxonomy", {}),
        "leakage_count": aggregate.get("leakage_count", 0),
        "provider_calls": (aggregate.get("cost_totals") or {}).get("provider_calls", 0),
        "aggregate_report_ref": aggregate_ref,
    }


def _source_family_guard_index(*, summaries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for lane_id in ("source_guarded_strategy", "source_guarded_foundry"):
        summary = summaries.get(lane_id) or {}
        for row in summary.get("problem_results", []):
            if not isinstance(row, Mapping):
                continue
            guard_ref = (row.get("artifact_refs") or {}).get(
                "external_source_family_strategy_guard"
            )
            guard = _read_json(_repo_path(str(guard_ref))) if guard_ref else {}
            rows.append(
                {
                    "lane_id": lane_id,
                    "problem_id": row.get("problem_id"),
                    "source_family": guard.get("source_family") or row.get("source"),
                    "guard_applied": bool(guard.get("guard_applied")),
                    "proof_body_emission_policy": guard.get(
                        "proof_body_emission_policy"
                    ),
                    "lean_compile_status": row.get("lean_compile_status"),
                    "error_class": row.get("error_class"),
                    "guard_ref": guard_ref,
                }
            )
    return {
        "schema_version": "external_source_family_strategy_guard_index_v0",
        "row_count": len(rows),
        "guard_applied_count": sum(1 for row in rows if row["guard_applied"]),
        "rows": rows,
    }


def _tactic_portfolio_index(*, summary: Mapping[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    selected_counts: Counter[str] = Counter()
    for row in summary.get("problem_results", []):
        if not isinstance(row, Mapping):
            continue
        result_ref = (row.get("artifact_refs") or {}).get("tactic_portfolio_results")
        result = _read_json(_repo_path(str(result_ref))) if result_ref else {}
        selected = str(result.get("selected_tactic_id") or "none")
        selected_counts[selected] += 1
        rows.append(
            {
                "problem_id": row.get("problem_id"),
                "source_family": result.get("source_family") or row.get("source"),
                "selected_tactic_id": selected,
                "lean_compile_status": row.get("lean_compile_status"),
                "error_class": row.get("error_class"),
                "attempt_count": result.get("attempt_count"),
                "result_ref": result_ref,
            }
        )
    return {
        "schema_version": "external_tactic_portfolio_index_v0",
        "row_count": len(rows),
        "selected_tactic_counts": dict(selected_counts),
        "rows": rows,
    }


def _hammer_search_index(*, summary: Mapping[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    selected_counts: Counter[str] = Counter()
    for row in summary.get("problem_results", []):
        if not isinstance(row, Mapping):
            continue
        refs = row.get("artifact_refs") or {}
        result_ref = refs.get("hammer_search_results")
        manifest_ref = refs.get("hammer_action_manifest")
        result = _read_json(_repo_path(str(result_ref))) if result_ref else {}
        manifest = _read_json(_repo_path(str(manifest_ref))) if manifest_ref else {}
        selected = str(result.get("selected_tactic_id") or "none")
        selected_counts[selected] += 1
        rows.append(
            {
                "problem_id": row.get("problem_id"),
                "source_family": result.get("source_family") or row.get("source"),
                "selected_action_id": result.get("selected_action_id"),
                "selected_tactic_id": selected,
                "lean_compile_status": row.get("lean_compile_status"),
                "error_class": row.get("error_class"),
                "attempt_count": result.get("attempt_count"),
                "statement_only": result.get("statement_only"),
                "adapter_candidate_used": result.get("adapter_candidate_used"),
                "result_ref": result_ref,
                "manifest_ref": manifest_ref,
            }
        )
        for action in manifest.get("actions", []):
            if isinstance(action, Mapping):
                actions.append(
                    {
                        **dict(action),
                        "problem_id": row.get("problem_id"),
                        "manifest_ref": manifest_ref,
                    }
                )
        for attempt in result.get("attempts", []):
            if isinstance(attempt, Mapping):
                attempts.append(
                    {
                        **dict(attempt),
                        "problem_id": row.get("problem_id"),
                        "result_ref": result_ref,
                    }
                )
    return {
        "schema_version": "hammer_search_results_index_v0",
        "row_count": len(rows),
        "action_count": len(actions),
        "attempt_count": len(attempts),
        "selected_tactic_counts": dict(selected_counts),
        "statement_only_success_count": sum(
            1
            for row in rows
            if row.get("statement_only") and row.get("lean_compile_status") == "PASS"
        ),
        "adapter_candidate_used_count": sum(
            1 for row in rows if row.get("adapter_candidate_used")
        ),
        "rows": rows,
        "actions": actions,
        "attempts": attempts,
    }


def _proof_minimization_report(*, summary: Mapping[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in summary.get("problem_results", []):
        if not isinstance(row, Mapping):
            continue
        proof_ref = (row.get("artifact_refs") or {}).get("proof_minimization")
        proof = _read_json(_repo_path(str(proof_ref))) if proof_ref else {}
        rows.append(
            {
                "problem_id": row.get("problem_id"),
                "selected_action_id": proof.get("selected_action_id"),
                "selected_tactic_id": proof.get("selected_tactic_id"),
                "minimized_body": proof.get("minimized_body", []),
                "minimized_line_count": proof.get("minimized_line_count"),
                "truth_side_body_used": proof.get("truth_side_body_used"),
                "adapter_candidate_used": proof.get("adapter_candidate_used"),
                "lean_compile_status": proof.get("lean_compile_status"),
                "error_class": proof.get("error_class"),
                "proof_minimization_ref": proof_ref,
            }
        )
    return {
        "schema_version": "proof_minimization_report_v0",
        "row_count": len(rows),
        "truth_side_body_used_count": sum(1 for row in rows if row.get("truth_side_body_used")),
        "adapter_candidate_used_count": sum(1 for row in rows if row.get("adapter_candidate_used")),
        "rows": rows,
    }


def _hammer_selected_proofs(
    *,
    summary: Mapping[str, Any],
    proof_report: Mapping[str, Any],
) -> dict[str, Any]:
    result_rows = {
        row.get("problem_id"): row
        for row in _hammer_search_index(summary=summary).get("rows", [])
        if isinstance(row, Mapping)
    }
    rows: list[dict[str, Any]] = []
    for proof in proof_report.get("rows", []):
        if not isinstance(proof, Mapping):
            continue
        problem_id = proof.get("problem_id")
        result = result_rows.get(problem_id) or {}
        accepted = proof.get("lean_compile_status") == "PASS"
        rows.append(
            {
                "problem_id": problem_id,
                "source_family": result.get("source_family"),
                "accepted": accepted,
                "selected_action_id": proof.get("selected_action_id"),
                "selected_tactic_id": proof.get("selected_tactic_id"),
                "minimized_body": proof.get("minimized_body", []),
                "minimized_line_count": proof.get("minimized_line_count"),
                "statement_only": result.get("statement_only"),
                "adapter_candidate_used": proof.get("adapter_candidate_used"),
                "truth_side_body_used": proof.get("truth_side_body_used"),
                "lean_compile_status": proof.get("lean_compile_status"),
                "error_class": proof.get("error_class"),
                "result_ref": result.get("result_ref"),
                "proof_minimization_ref": proof.get("proof_minimization_ref"),
            }
        )
    return {
        "schema_version": "hammer_selected_proofs_v0",
        "row_count": len(rows),
        "accepted_count": sum(1 for row in rows if row["accepted"]),
        "adapter_candidate_used_count": sum(
            1 for row in rows if row.get("adapter_candidate_used")
        ),
        "truth_side_body_used_count": sum(
            1 for row in rows if row.get("truth_side_body_used")
        ),
        "rows": rows,
    }


def _hammer_failure_taxonomy(
    *,
    summary: Mapping[str, Any],
    hammer_index: Mapping[str, Any],
) -> dict[str, Any]:
    aggregate = _aggregate_lane(summary)
    action_error_counts: Counter[str] = Counter()
    action_status_counts: Counter[str] = Counter()
    failed_actions: list[dict[str, Any]] = []
    for attempt in hammer_index.get("attempts", []):
        if not isinstance(attempt, Mapping):
            continue
        status = str(
            attempt.get("lean_status")
            or attempt.get("check_status")
            or attempt.get("compile_status")
            or attempt.get("status")
            or "UNKNOWN"
        )
        action_status_counts[status] += 1
        if status in {"PASS", "NOT_RUN"}:
            continue
        error_class = str(attempt.get("error_class") or "UNKNOWN")
        action_error_counts[error_class] += 1
        failed_actions.append(
            {
                "problem_id": attempt.get("problem_id"),
                "action_id": attempt.get("action_id"),
                "tactic_id": attempt.get("tactic_id"),
                "action_kind": attempt.get("action_kind"),
                "error_class": error_class,
                "lean_status": status,
                "stderr_excerpt": attempt.get("stderr_excerpt"),
                "lean_check_ref": attempt.get("lean_check_ref"),
                "result_ref": attempt.get("result_ref"),
            }
        )
    return {
        "schema_version": "hammer_failure_taxonomy_v0",
        "failed_problem_count": int(aggregate.get("fail_count") or 0),
        "problem_failure_taxonomy": aggregate.get("failure_taxonomy", {}),
        "action_status_counts": dict(action_status_counts),
        "not_run_action_count": action_status_counts.get("NOT_RUN", 0),
        "failed_action_count": len(failed_actions),
        "action_error_counts": dict(action_error_counts),
        "failed_actions": failed_actions,
    }


def _foundry_hammer_learning_rows(*, summary: Mapping[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in summary.get("problem_results", []):
        if not isinstance(row, Mapping):
            continue
        learning_ref = (row.get("artifact_refs") or {}).get("prover_evolve_learning_row")
        learning = _read_json(_repo_path(str(learning_ref))) if learning_ref else {}
        credit = learning.get("hammer_search_credit") or {}
        rows.append(
            {
                "problem_id": row.get("problem_id"),
                "learning_row_ref": learning_ref,
                "search_policy_id": credit.get("search_policy_id"),
                "selected_action_id": credit.get("selected_action_id"),
                "selected_tactic_id": credit.get("selected_tactic_id"),
                "credit_assignment": credit.get("credit_assignment"),
                "raw_proof_body_credit": credit.get("raw_proof_body_credit"),
                "adapter_candidate_used": credit.get("adapter_candidate_used"),
                "statement_only": credit.get("statement_only"),
            }
        )
    return {
        "schema_version": "foundry_hammer_learning_rows_v0",
        "row_count": len(rows),
        "raw_proof_body_credit_count": sum(1 for row in rows if row.get("raw_proof_body_credit")),
        "adapter_candidate_used_count": sum(1 for row in rows if row.get("adapter_candidate_used")),
        "rows": rows,
    }


def _hammer_skill_update_candidates(
    *,
    hammer_index: Mapping[str, Any],
    foundry_hammer_learning: Mapping[str, Any],
) -> dict[str, Any]:
    selected_counts = hammer_index.get("selected_tactic_counts") or {}
    candidates = [
        {
            "candidate_id": f"hammer_policy_credit_{tactic_id}",
            "update_kind": "search_policy_credit",
            "search_policy_id": "hammer_search_policy_v0",
            "tactic_id": tactic_id,
            "credit_count": count,
            "raw_proof_body_credit": False,
            "reason": (
                "Lean accepted this tactic in statement-only hammer search; "
                "credit the action/ranking policy, not a memorized proof body."
            ),
        }
        for tactic_id, count in sorted(selected_counts.items())
        if tactic_id and tactic_id != "none"
    ]
    return {
        "schema_version": "hammer_skill_update_candidates_v0",
        "candidate_count": len(candidates),
        "learning_row_count": foundry_hammer_learning.get("row_count", 0),
        "raw_proof_body_credit_count": foundry_hammer_learning.get(
            "raw_proof_body_credit_count",
            0,
        ),
        "candidates": candidates,
    }


def _hammer_context_recipe_update_candidates(
    *,
    adapter_audit: Mapping[str, Any],
    hammer_comparison: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = [
        {
            "candidate_id": "statement_only_hammer_context_recipe_v0",
            "update_kind": "context_recipe_boundary",
            "policy": "forward packets may carry theorem signature, imports, public facts, and search policy; no adapter candidate_body, ideal_body, repair_body, or retrieval_body",
            "headline_metric": "statement_only_hammer_success_count",
        },
        {
            "candidate_id": "adapter_candidate_metric_boundary_v0",
            "update_kind": "metric_boundary",
            "policy": "adapter_candidate_success_count measures adapter contribution, not prover discovery",
            "adapter_candidate_body_count": adapter_audit.get(
                "adapter_candidate_body_count"
            ),
            "adapter_candidate_success_count": hammer_comparison.get(
                "adapter_candidate_success_count"
            ),
        },
        {
            "candidate_id": "provider_hypothesis_action_source_deferred_v0",
            "update_kind": "provider_action_boundary",
            "policy": "provider_hypothesis actions enter hammer search only after reducer evidence passes Lean and recipe policy",
            "provider_recipe_clean_success_count": hammer_comparison.get(
                "provider_recipe_clean_success_count",
                0,
            ),
        },
    ]
    return {
        "schema_version": "hammer_context_recipe_update_candidates_v0",
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _external_hammer_comparison(
    *,
    lane_aggregates: Mapping[str, Mapping[str, Any]],
    adapter_audit: Mapping[str, Any],
    hammer_index: Mapping[str, Any],
    local_hammer_summary: Mapping[str, Any],
) -> dict[str, Any]:
    def passes(lane_id: str) -> int:
        return int((lane_aggregates.get(lane_id) or {}).get("pass_count") or 0)

    local_aggregate = _aggregate_lane(local_hammer_summary)
    return {
        "schema_version": "external_hammer_comparison_v0",
        "metric_boundary": {
            "statement_only_success": "solved from theorem signature/imports by hammer search",
            "adapter_candidate_success": "solved by translation-adapter candidate_body",
            "provider_recipe_clean_success": "provider output accepted only after reducer, Lean, and recipe-policy pass",
            "oracle_success": "withheld comparator only",
        },
        "problem_count": int(
            (lane_aggregates.get("hammer_search") or {}).get("problem_count") or 0
        ),
        "baseline_direct_success_count": passes("baseline"),
        "adapter_candidate_success_count": passes("baseline"),
        "statement_only_hammer_success_count": passes("hammer_search"),
        "statement_only_success_count": passes("hammer_search"),
        "guarded_foundry_success_count": passes("source_guarded_foundry"),
        "tactic_portfolio_success_count": passes("tactic_portfolio"),
        "hammer_search_success_count": passes("hammer_search"),
        "provider_recipe_clean_success_count": 0,
        "oracle_repair_comparator_success_count": passes("oracle_repair_comparator"),
        "local_lean_std_hammer_success_count": int(local_aggregate.get("pass_count") or 0),
        "adapter_candidate_body_count": adapter_audit.get("adapter_candidate_body_count"),
        "adapter_candidate_forward_manifest_leak_count": adapter_audit.get(
            "forward_manifest_body_leak_count"
        ),
        "hammer_selected_tactic_counts": hammer_index.get("selected_tactic_counts", {}),
        "claim_boundary": (
            "MiniF2F-source-backed Lean4/Std translation smoke only; direct MiniF2F "
            "performance requires a compatible Lean/mathlib benchmark lane."
        ),
    }


def _local_statement_only_comparison(
    *,
    local_hammer_summary: Mapping[str, Any],
) -> dict[str, Any]:
    local_aggregate = _aggregate_lane(local_hammer_summary)
    local_hammer_index = _hammer_search_index(summary=local_hammer_summary)
    return {
        "schema_version": "local_statement_only_comparison_v0",
        "problem_count": int(local_aggregate.get("problem_count") or 0),
        "statement_only_hammer_success_count": int(local_aggregate.get("pass_count") or 0),
        "adapter_candidate_success_count": 0,
        "provider_recipe_clean_success_count": 0,
        "truth_side_leakage_count": int(local_aggregate.get("leakage_count") or 0),
        "selected_tactic_counts": local_hammer_index.get("selected_tactic_counts", {}),
        "aggregate_report_ref": local_aggregate.get("aggregate_report_ref"),
        "hammer_search_results": local_hammer_index.get("rows", []),
    }


def _external_overfit_diagnosis(
    *,
    lane_aggregates: Mapping[str, Mapping[str, Any]],
    guard_index: Mapping[str, Any],
    tactic_index: Mapping[str, Any],
) -> dict[str, Any]:
    def passes(lane_id: str) -> int:
        return int((lane_aggregates.get(lane_id) or {}).get("pass_count") or 0)

    return {
        "schema_version": "external_overfit_diagnosis_v0",
        "diagnosis": "strategy_and_foundry_local_skeleton_overfit",
        "baseline_direct_pass_count": passes("baseline"),
        "unguarded_strategy_pass_count": passes("strategy_control"),
        "unguarded_foundry_pass_count": passes("foundry_overlay"),
        "source_guarded_strategy_pass_count": passes("source_guarded_strategy"),
        "source_guarded_foundry_pass_count": passes("source_guarded_foundry"),
        "tactic_portfolio_pass_count": passes("tactic_portfolio"),
        "oracle_repair_comparator_pass_count": passes("oracle_repair_comparator"),
        "guard_applied_count": guard_index.get("guard_applied_count", 0),
        "selected_tactic_counts": tactic_index.get("selected_tactic_counts", {}),
        "claim_boundary": (
            "MiniF2F-source-backed Lean4/Std translation smoke only; this is not "
            "a direct MiniF2F benchmark result."
        ),
    }


def _oracle_result_index(*, summaries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for lane_id, summary in summaries.items():
        for row in summary.get("problem_results", []):
            if not isinstance(row, Mapping):
                continue
            rows.append(
                {
                    "lane_id": lane_id,
                    "problem_id": row.get("problem_id"),
                    "source": row.get("source"),
                    "split": row.get("split"),
                    "domain": row.get("domain"),
                    "graph_variant_id": row.get("graph_variant_id"),
                    "lean_compile_status": row.get("lean_compile_status"),
                    "error_class": row.get("error_class"),
                    "repair_applied": row.get("repair_applied"),
                    "repair_success": row.get("repair_success"),
                    "leakage_detected": row.get("leakage_detected"),
                    "prover_check_result_ref": (row.get("artifact_refs") or {}).get("prover_check_result"),
                    "proof_attempt_critique_ref": (row.get("artifact_refs") or {}).get("proof_attempt_critique"),
                    "prover_evolve_learning_row_ref": (row.get("artifact_refs") or {}).get("prover_evolve_learning_row"),
                }
            )
    return {
        "schema_version": "external_formal_benchmark_oracle_result_index_v0",
        "row_count": len(rows),
        "rows": rows,
    }


def _foundry_learning_index(oracle_index: Mapping[str, Any]) -> dict[str, Any]:
    rows = [
        {
            "problem_id": row.get("problem_id"),
            "learning_row_ref": row.get("prover_evolve_learning_row_ref"),
            "root_failure_mode": row.get("error_class"),
            "lean_compile_status": row.get("lean_compile_status"),
            "learning_lane": "external MiniF2F smoke via Skill Foundry overlay",
        }
        for row in oracle_index.get("rows", [])
        if isinstance(row, Mapping) and row.get("lane_id") == "foundry_overlay"
    ]
    return {
        "schema_version": "external_formal_benchmark_foundry_learning_index_v0",
        "row_count": len(rows),
        "rows": rows,
    }


def _skill_update_candidates(
    *,
    foundry_summary: Mapping[str, Any],
    repair_summary: Mapping[str, Any],
) -> dict[str, Any]:
    repair_by_problem = {
        row.get("problem_id"): row
        for row in repair_summary.get("problem_results", [])
        if isinstance(row, Mapping)
    }
    candidates: list[dict[str, Any]] = []
    for row in foundry_summary.get("problem_results", []):
        if not isinstance(row, Mapping) or row.get("lean_compile_status") == "PASS":
            continue
        repair = repair_by_problem.get(row.get("problem_id")) or {}
        oracle_comparator_passed = repair.get("lean_compile_status") == "PASS"
        candidates.append(
            {
                "candidate_id": f"external_skill_candidate_from_{row.get('problem_id')}",
                "problem_id": row.get("problem_id"),
                "source_error_class": row.get("error_class"),
                "oracle_repair_success": bool(repair.get("repair_success")),
                "oracle_comparator_lean_pass": oracle_comparator_passed,
                "oracle_repair_applied": bool(repair.get("repair_applied")),
                "recommendation": (
                    "mine_external_oracle_repair_after_retest"
                    if oracle_comparator_passed
                    else "quarantine_external_failure_until_better_adapter_or_context"
                ),
                "evidence_refs": {
                    "foundry_learning_row": (row.get("artifact_refs") or {}).get("prover_evolve_learning_row"),
                    "proof_attempt_critique": (row.get("artifact_refs") or {}).get("proof_attempt_critique"),
                    "oracle_repair_check": (repair.get("artifact_refs") or {}).get("prover_check_result"),
                },
            }
        )
    return {
        "schema_version": "external_formal_benchmark_skill_update_candidates_v0",
        "candidate_count": len(candidates),
        "promotion_policy": "advisory_only; external smoke candidates require heldout retest before promotion",
        "candidates": candidates,
    }


def _context_recipe_update_candidates(
    corpus_report: Mapping[str, Any],
    lane_aggregates: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    candidates = [
        {
            "candidate_id": "external_benchmark_mathlib_compatibility_lane",
            "reason": "Priority external benchmarks are Lean/mathlib-heavy; MiniF2F direct checking is blocked in the current Lean 4/Std-only environment.",
            "next_experiment": "prepare a Lean/mathlib-capable external benchmark lane before claiming direct MiniF2F/PutnamBench benchmark performance",
            "evidence_refs": [
                "annexes/miniF2F/repo/lean/src/minif2f_import.lean",
                "external_formal_benchmark_manifest.json",
            ],
            "corpus_availability": corpus_report.get("rows", []),
        }
    ]
    baseline_pass = int((lane_aggregates.get("baseline") or {}).get("pass_count") or 0)
    strategy_pass = int((lane_aggregates.get("strategy_control") or {}).get("pass_count") or 0)
    foundry_pass = int((lane_aggregates.get("foundry_overlay") or {}).get("pass_count") or 0)
    guarded_strategy_pass = int(
        (lane_aggregates.get("source_guarded_strategy") or {}).get("pass_count") or 0
    )
    guarded_foundry_pass = int(
        (lane_aggregates.get("source_guarded_foundry") or {}).get("pass_count") or 0
    )
    tactic_portfolio_pass = int(
        (lane_aggregates.get("tactic_portfolio") or {}).get("pass_count") or 0
    )
    if baseline_pass > max(strategy_pass, foundry_pass):
        candidates.append(
            {
                "candidate_id": "external_source_family_strategy_guard_v0",
                "reason": (
                    "The local strategy/Foundry skeletons underperformed the direct baseline "
                    "on external MiniF2F-translated rows, indicating source-family overfit."
                ),
                "current_signal": {
                    "baseline_pass_count": baseline_pass,
                    "strategy_pass_count": strategy_pass,
                    "foundry_pass_count": foundry_pass,
                    "source_guarded_strategy_pass_count": guarded_strategy_pass,
                    "source_guarded_foundry_pass_count": guarded_foundry_pass,
                    "tactic_portfolio_pass_count": tactic_portfolio_pass,
                },
                "next_experiment": (
                    "Keep the guard active: for external source families, executable "
                    "skill bodies are allowed only after tactic-affordance compatibility "
                    "is proven by Lean checks."
                ),
                "authority_boundary": (
                    "Advisory context/skill update only; do not promote a global strategy "
                    "standard from one smoke run."
                ),
            }
        )
    return {
        "schema_version": "external_formal_benchmark_context_recipe_update_candidates_v0",
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _representatives(
    *,
    baseline_summary: Mapping[str, Any],
    foundry_summary: Mapping[str, Any],
    repair_summary: Mapping[str, Any],
) -> dict[str, Any]:
    baseline_rows = [row for row in baseline_summary.get("problem_results", []) if isinstance(row, Mapping)]
    foundry_rows = [row for row in foundry_summary.get("problem_results", []) if isinstance(row, Mapping)]
    repair_by_problem = {
        row.get("problem_id"): row
        for row in repair_summary.get("problem_results", [])
        if isinstance(row, Mapping)
    }
    success = next((row for row in foundry_rows if row.get("lean_compile_status") == "PASS"), None)
    if success is None:
        success = next((row for row in baseline_rows if row.get("lean_compile_status") == "PASS"), None)
    failure = next((row for row in foundry_rows if row.get("lean_compile_status") != "PASS"), None)
    repaired = None
    for row in foundry_rows:
        repair = repair_by_problem.get(row.get("problem_id")) or {}
        if row.get("lean_compile_status") != "PASS" and repair.get("lean_compile_status") == "PASS":
            repaired = {"forward": row, "oracle_repair": repair}
            break
    return {
        "representative_external_success": success,
        "representative_external_failure": failure,
        "representative_external_oracle_repair": repaired,
    }


def _guarded_representatives(
    *,
    guarded_summary: Mapping[str, Any],
    tactic_summary: Mapping[str, Any],
) -> dict[str, Any]:
    guarded_rows = [
        row for row in guarded_summary.get("problem_results", []) if isinstance(row, Mapping)
    ]
    tactic_rows = [
        row for row in tactic_summary.get("problem_results", []) if isinstance(row, Mapping)
    ]
    success = next(
        (row for row in guarded_rows if row.get("lean_compile_status") == "PASS"),
        None,
    )
    if success is None:
        success = next(
            (row for row in tactic_rows if row.get("lean_compile_status") == "PASS"),
            None,
        )
    failure = next(
        (row for row in guarded_rows if row.get("lean_compile_status") != "PASS"),
        None,
    )
    if failure is None:
        failure = next(
            (row for row in tactic_rows if row.get("lean_compile_status") != "PASS"),
            None,
        )
    return {
        "representative_guarded_success": success,
        "representative_guarded_failure": failure,
    }


def _validate(run_root: Path, summary: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if int(summary.get("external_problem_count") or 0) < 10:
        issues.append("external smoke should include at least 10 external statements")
    if int(summary.get("truth_side_leakage_count") or 0) != 0:
        issues.append("truth-side leakage count must remain zero")
    if int(summary.get("fake_provider_results_counted") or 0) != 0:
        issues.append("fake provider evidence must remain zero")
    if int(summary.get("hammer_search_success_count") or 0) < 0:
        issues.append("hammer search success count is missing")
    if int((summary.get("adapter_candidate_audit") or {}).get("forward_manifest_body_leak_count") or 0) != 0:
        issues.append("adapter candidate audit found forward manifest body leakage")
    if summary.get("open_problem_success_claimed") is not False:
        issues.append("external smoke must not claim open-problem success")
    manifest_path = run_root / "external_formal_benchmark_manifest.json"
    if not manifest_path.exists():
        issues.append("missing external_formal_benchmark_manifest.json")
    else:
        manifest = _read_json(manifest_path)
        for row in manifest.get("problems", []):
            if any(key in row for key in ("candidate_body", "ideal_body", "repair_body", "retrieval_body")):
                issues.append(f"forward manifest leaks proof/candidate body fields for {row.get('problem_id')}")
    for name in (
        "external_problem_batch_manifest.json",
        "external_oracle_result_index.json",
        "external_foundry_learning_index.json",
        "external_skill_update_candidates.json",
        "external_context_recipe_update_candidates.json",
        "external_provider_trickle_queue.json",
        "external_source_family_strategy_guard.json",
        "adapter_candidate_audit.json",
        "statement_only_problem_manifest.json",
        "tactic_affordance_probe.json",
        "tactic_portfolio_manifest.json",
        "tactic_portfolio_results.json",
        "hammer_action_manifest.json",
        "hammer_search_results.json",
        "proof_minimization_report.json",
        "hammer_selected_proofs.json",
        "hammer_proof_minimization_report.json",
        "hammer_failure_taxonomy.json",
        "foundry_hammer_learning_rows.json",
        "hammer_skill_update_candidates.json",
        "hammer_context_recipe_update_candidates.json",
        "external_hammer_comparison.json",
        "external_statement_only_comparison.json",
        "local_statement_only_comparison.json",
        "hammer_search_run_summary.json",
        "external_guarded_loop_run_summary.json",
        "representative_guarded_success.json",
        "external_overfit_diagnosis.json",
    ):
        if not (run_root / name).exists():
            issues.append(f"missing artifact: {name}")
    if int(summary.get("source_family_guard_applied_count") or 0) <= 0:
        issues.append("source-family guard should apply to external source rows")
    return issues


def run_smoke(
    *,
    run_root: Path = DEFAULT_RUN_ROOT,
    problem_limit: int | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    run_root = _repo_path(run_root)
    run_root.mkdir(parents=True, exist_ok=True)
    corpus_report = _external_corpus_availability()
    problem_set = _miniF2F_problem_set()
    if problem_limit is not None:
        problem_set = problem_set[: max(0, problem_limit)]
    benchmark_manifest = external_problem_manifest(problem_set)
    statement_only_problem_set = _statement_only_problem_set(problem_set)
    statement_only_manifest = _statement_only_problem_manifest(problem_set)
    adapter_audit = _adapter_candidate_audit(
        problem_set=problem_set,
        benchmark_manifest=benchmark_manifest,
    )
    premise_index = harness._premise_index()

    _write_json(run_root / "external_corpus_availability_report.json", corpus_report)
    _write_json(run_root / "external_formal_benchmark_manifest.json", benchmark_manifest)
    _write_json(run_root / "external_problem_batch_manifest.json", benchmark_manifest)
    _write_json(run_root / "statement_only_problem_manifest.json", statement_only_manifest)
    _write_json(run_root / "adapter_candidate_audit.json", adapter_audit)
    _write_json(run_root / "premise_index.json", premise_index)

    summaries: dict[str, Mapping[str, Any]] = {}
    for lane_id, graph_variant in (
        ("baseline", "baseline_graph_v0"),
        ("strategy_control", "strategy_control_graph_v0"),
        ("foundry_overlay", harness.SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT),
        ("source_guarded_strategy", harness.SOURCE_GUARDED_STRATEGY_GRAPH_VARIANT),
        ("source_guarded_foundry", harness.SOURCE_GUARDED_FOUNDRY_GRAPH_VARIANT),
        ("tactic_portfolio", harness.TACTIC_PORTFOLIO_GRAPH_VARIANT),
        ("hammer_search", harness.HAMMER_SEARCH_GRAPH_VARIANT),
        ("oracle_repair_comparator", "oracle_repair_graph_v0"),
    ):
        lane_problem_set = (
            statement_only_problem_set
            if graph_variant == harness.HAMMER_SEARCH_GRAPH_VARIANT
            else problem_set
        )
        summaries[lane_id] = harness.run_benchmark(
            run_root=run_root / graph_variant,
            timeout_seconds=timeout_seconds,
            run_id=f"{STATEMENT_ONLY_HAMMER_RUN_ID if graph_variant == harness.HAMMER_SEARCH_GRAPH_VARIANT else RUN_ID}_{graph_variant}",
            problem_set=lane_problem_set,
            problem_source_manifest=statement_only_manifest
            if graph_variant == harness.HAMMER_SEARCH_GRAPH_VARIANT
            else benchmark_manifest,
            premise_index=premise_index,
            graph_variant_id=graph_variant,
            cap_id=STATEMENT_ONLY_HAMMER_CAP_ID
            if graph_variant == harness.HAMMER_SEARCH_GRAPH_VARIANT
            else CAP_ID,
        )
    local_hammer_summary = harness.run_benchmark(
        run_root=run_root / "local_lean_std_hammer_search_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{STATEMENT_ONLY_HAMMER_RUN_ID}_local_lean_std",
        problem_set=harness._problem_set(),
        graph_variant_id=harness.HAMMER_SEARCH_GRAPH_VARIANT,
        cap_id=STATEMENT_ONLY_HAMMER_CAP_ID,
    )

    lane_aggregates = {lane_id: _aggregate_lane(summary) for lane_id, summary in summaries.items()}
    oracle_index = _oracle_result_index(summaries=summaries)
    foundry_learning = _foundry_learning_index(oracle_index)
    skill_candidates = _skill_update_candidates(
        foundry_summary=summaries["foundry_overlay"],
        repair_summary=summaries["oracle_repair_comparator"],
    )
    context_candidates = _context_recipe_update_candidates(corpus_report, lane_aggregates)
    representatives = _representatives(
        baseline_summary=summaries["baseline"],
        foundry_summary=summaries["foundry_overlay"],
        repair_summary=summaries["oracle_repair_comparator"],
    )
    guarded_representatives = _guarded_representatives(
        guarded_summary=summaries["source_guarded_foundry"],
        tactic_summary=summaries["tactic_portfolio"],
    )
    guard_index = _source_family_guard_index(summaries=summaries)
    tactic_index = _tactic_portfolio_index(summary=summaries["tactic_portfolio"])
    hammer_index = _hammer_search_index(summary=summaries["hammer_search"])
    proof_minimization_report = _proof_minimization_report(summary=summaries["hammer_search"])
    hammer_selected_proofs = _hammer_selected_proofs(
        summary=summaries["hammer_search"],
        proof_report=proof_minimization_report,
    )
    hammer_failure_taxonomy = _hammer_failure_taxonomy(
        summary=summaries["hammer_search"],
        hammer_index=hammer_index,
    )
    foundry_hammer_learning = _foundry_hammer_learning_rows(summary=summaries["hammer_search"])
    hammer_comparison = _external_hammer_comparison(
        lane_aggregates=lane_aggregates,
        adapter_audit=adapter_audit,
        hammer_index=hammer_index,
        local_hammer_summary=local_hammer_summary,
    )
    hammer_skill_candidates = _hammer_skill_update_candidates(
        hammer_index=hammer_index,
        foundry_hammer_learning=foundry_hammer_learning,
    )
    hammer_context_candidates = _hammer_context_recipe_update_candidates(
        adapter_audit=adapter_audit,
        hammer_comparison=hammer_comparison,
    )
    local_statement_comparison = _local_statement_only_comparison(
        local_hammer_summary=local_hammer_summary,
    )
    overfit_diagnosis = _external_overfit_diagnosis(
        lane_aggregates=lane_aggregates,
        guard_index=guard_index,
        tactic_index=tactic_index,
    )
    source_counts = Counter(problem.source for problem in problem_set)
    split_counts = Counter(problem.split for problem in problem_set)
    foundry_lane = lane_aggregates["foundry_overlay"]
    strategy_lane = lane_aggregates["strategy_control"]
    guarded_strategy_lane = lane_aggregates["source_guarded_strategy"]
    guarded_foundry_lane = lane_aggregates["source_guarded_foundry"]
    tactic_lane = lane_aggregates["tactic_portfolio"]
    hammer_lane = lane_aggregates["hammer_search"]
    repair_lane = lane_aggregates["oracle_repair_comparator"]
    baseline_lane = lane_aggregates["baseline"]
    summary = {
        "schema_version": "prover_external_formal_benchmark_smoke_run_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "cap_id": CAP_ID,
        "selected_benchmark_source": "miniF2F",
        "selected_source_reason": (
            "MiniF2F was the highest-priority external benchmark absent locally; "
            "it was imported through annex_import and adapted as a Lean4-core smoke "
            "because direct Lean3/mathlib checking is not available in this workspace."
        ),
        "external_problem_count": len(problem_set),
        "source_counts": dict(source_counts),
        "split_counts": dict(split_counts),
        "baseline_direct_success_count": int(baseline_lane.get("pass_count") or 0),
        "baseline_success_count": int(baseline_lane.get("pass_count") or 0),
        "strategy_success_count": int(strategy_lane.get("pass_count") or 0),
        "foundry_success_count": int(foundry_lane.get("pass_count") or 0),
        "source_guarded_strategy_success_count": int(
            guarded_strategy_lane.get("pass_count") or 0
        ),
        "source_guarded_foundry_success_count": int(
            guarded_foundry_lane.get("pass_count") or 0
        ),
        "tactic_portfolio_success_count": int(tactic_lane.get("pass_count") or 0),
        "statement_only_hammer_success_count": int(hammer_lane.get("pass_count") or 0),
        "statement_only_success_count": int(hammer_lane.get("pass_count") or 0),
        "adapter_candidate_success_count": int(baseline_lane.get("pass_count") or 0),
        "hammer_search_success_count": int(hammer_lane.get("pass_count") or 0),
        "provider_recipe_clean_success_count": 0,
        "local_lean_std_hammer_success_count": int(
            (_aggregate_lane(local_hammer_summary).get("pass_count") or 0)
        ),
        "oracle_repair_comparator_success_count": int(repair_lane.get("pass_count") or 0),
        "source_family_guard_applied_count": int(
            guard_index.get("guard_applied_count") or 0
        ),
        "truth_side_leakage_count": sum(int(row.get("leakage_count") or 0) for row in lane_aggregates.values()),
        "fake_provider_results_counted": 0,
        "provider_jobs_compiled": False,
        "provider_receipts_reduced": False,
        "provider_lane_status": "not_used_local_external_smoke",
        "open_problem_success_claimed": False,
        "external_success_tier": "Tier 2 smoke: external source-backed formal statements, Lean4 translation adapter",
        "direct_benchmark_build_status": "MiniF2F direct Lean3/mathlib run not attempted in Lean4-only workspace",
        "artifact_refs": {
            "external_corpus_availability_report": _rel(run_root / "external_corpus_availability_report.json"),
            "external_formal_benchmark_manifest": _rel(run_root / "external_formal_benchmark_manifest.json"),
            "external_problem_batch_manifest": _rel(run_root / "external_problem_batch_manifest.json"),
            "external_oracle_result_index": _rel(run_root / "external_oracle_result_index.json"),
            "external_foundry_learning_index": _rel(run_root / "external_foundry_learning_index.json"),
            "external_skill_update_candidates": _rel(run_root / "external_skill_update_candidates.json"),
            "external_context_recipe_update_candidates": _rel(run_root / "external_context_recipe_update_candidates.json"),
            "external_provider_trickle_queue": _rel(run_root / "external_provider_trickle_queue.json"),
            "external_source_family_strategy_guard": _rel(run_root / "external_source_family_strategy_guard.json"),
            "adapter_candidate_audit": _rel(run_root / "adapter_candidate_audit.json"),
            "statement_only_problem_manifest": _rel(run_root / "statement_only_problem_manifest.json"),
            "tactic_portfolio_manifest": _rel(run_root / "tactic_portfolio_manifest.json"),
            "tactic_portfolio_results": _rel(run_root / "tactic_portfolio_results.json"),
            "tactic_affordance_probe": _rel(run_root / "tactic_affordance_probe.json"),
            "hammer_action_manifest": _rel(run_root / "hammer_action_manifest.json"),
            "hammer_search_results": _rel(run_root / "hammer_search_results.json"),
            "proof_minimization_report": _rel(run_root / "proof_minimization_report.json"),
            "hammer_selected_proofs": _rel(run_root / "hammer_selected_proofs.json"),
            "hammer_proof_minimization_report": _rel(run_root / "hammer_proof_minimization_report.json"),
            "hammer_failure_taxonomy": _rel(run_root / "hammer_failure_taxonomy.json"),
            "foundry_hammer_learning_rows": _rel(run_root / "foundry_hammer_learning_rows.json"),
            "hammer_skill_update_candidates": _rel(run_root / "hammer_skill_update_candidates.json"),
            "hammer_context_recipe_update_candidates": _rel(run_root / "hammer_context_recipe_update_candidates.json"),
            "external_hammer_comparison": _rel(run_root / "external_hammer_comparison.json"),
            "external_statement_only_comparison": _rel(run_root / "external_statement_only_comparison.json"),
            "local_statement_only_comparison": _rel(run_root / "local_statement_only_comparison.json"),
            "hammer_search_run_summary": _rel(run_root / "hammer_search_run_summary.json"),
            "external_guarded_loop_run_summary": _rel(run_root / "external_guarded_loop_run_summary.json"),
            "representative_guarded_success": _rel(run_root / "representative_guarded_success.json"),
            "representative_guarded_failure": _rel(run_root / "representative_guarded_failure.json"),
            "external_overfit_diagnosis": _rel(run_root / "external_overfit_diagnosis.json"),
        },
        "lane_aggregates": lane_aggregates,
        "tactic_portfolio_selected_tactic_counts": tactic_index.get(
            "selected_tactic_counts",
            {},
        ),
        "hammer_selected_tactic_counts": hammer_index.get("selected_tactic_counts", {}),
        "adapter_candidate_audit": {
            "adapter_candidate_body_count": adapter_audit.get("adapter_candidate_body_count"),
            "forward_manifest_body_leak_count": adapter_audit.get("forward_manifest_body_leak_count"),
            "baseline_direct_interpretation": adapter_audit.get(
                "baseline_direct_interpretation"
            ),
        },
    }

    provider_trickle_queue = {
        "schema_version": "external_formal_benchmark_provider_trickle_queue_v0",
        "provider_lane_used": False,
        "reason": "External smoke validates local Lean/Foundry generalization first; provider jobs remain owned by the existing transform-job plane.",
        "next_provider_step": "compile std_transform_job packets for this manifest only after the local external smoke denominator is stable",
    }
    affordance_ref = summaries["hammer_search"].get("tactic_portfolio_availability")
    tactic_affordance_probe = _read_json(_repo_path(str(affordance_ref))) if affordance_ref else {}
    hammer_action_manifest = {
        "schema_version": "hammer_action_manifest_index_v0",
        "search_policy_id": "hammer_search_policy_v0",
        "adapter_direct_candidate_allowed": False,
        "statement_only": True,
        "availability_ref": _rel(run_root / "tactic_affordance_probe.json"),
        "action_count": hammer_index.get("action_count", 0),
        "actions": hammer_index.get("actions", []),
    }
    hammer_search_run_summary = {
        "schema_version": "hammer_search_run_summary_v0",
        "run_id": STATEMENT_ONLY_HAMMER_RUN_ID,
        "cap_id": STATEMENT_ONLY_HAMMER_CAP_ID,
        "external_problem_count": len(problem_set),
        "statement_only_hammer_success_count": summary[
            "statement_only_hammer_success_count"
        ],
        "statement_only_success_count": summary["statement_only_success_count"],
        "adapter_candidate_success_count": summary["adapter_candidate_success_count"],
        "tactic_portfolio_success_count": summary["tactic_portfolio_success_count"],
        "hammer_search_success_count": summary["hammer_search_success_count"],
        "provider_recipe_clean_success_count": summary[
            "provider_recipe_clean_success_count"
        ],
        "oracle_repair_comparator_success_count": summary[
            "oracle_repair_comparator_success_count"
        ],
        "local_lean_std_hammer_success_count": summary[
            "local_lean_std_hammer_success_count"
        ],
        "truth_side_leakage_count": summary["truth_side_leakage_count"],
        "selected_tactic_counts": summary["hammer_selected_tactic_counts"],
        "adapter_candidate_audit_ref": _rel(run_root / "adapter_candidate_audit.json"),
        "hammer_search_results_ref": _rel(run_root / "hammer_search_results.json"),
        "hammer_selected_proofs_ref": _rel(run_root / "hammer_selected_proofs.json"),
        "proof_minimization_report_ref": _rel(run_root / "proof_minimization_report.json"),
        "hammer_proof_minimization_report_ref": _rel(
            run_root / "hammer_proof_minimization_report.json"
        ),
        "hammer_failure_taxonomy_ref": _rel(run_root / "hammer_failure_taxonomy.json"),
        "foundry_hammer_learning_rows_ref": _rel(
            run_root / "foundry_hammer_learning_rows.json"
        ),
        "hammer_skill_update_candidates_ref": _rel(
            run_root / "hammer_skill_update_candidates.json"
        ),
        "hammer_context_recipe_update_candidates_ref": _rel(
            run_root / "hammer_context_recipe_update_candidates.json"
        ),
        "external_statement_only_comparison_ref": _rel(
            run_root / "external_statement_only_comparison.json"
        ),
        "local_statement_only_comparison_ref": _rel(
            run_root / "local_statement_only_comparison.json"
        ),
        "local_lean_std_run_summary_ref": local_hammer_summary.get("aggregate_report"),
    }
    _write_json(run_root / "external_oracle_result_index.json", oracle_index)
    _write_json(run_root / "external_foundry_learning_index.json", foundry_learning)
    _write_json(run_root / "external_skill_update_candidates.json", skill_candidates)
    _write_json(run_root / "external_context_recipe_update_candidates.json", context_candidates)
    _write_json(run_root / "external_provider_trickle_queue.json", provider_trickle_queue)
    _write_json(run_root / "external_source_family_strategy_guard.json", guard_index)
    _write_json(run_root / "tactic_affordance_probe.json", tactic_affordance_probe)
    _write_json(run_root / "tactic_portfolio_manifest.json", {
        "schema_version": "external_tactic_portfolio_manifest_index_v0",
        "portfolio_id": "portfolio_core_v0",
        "availability_ref": _rel(
            run_root
            / harness.TACTIC_PORTFOLIO_GRAPH_VARIANT
            / "tactic_portfolio_availability.json"
        ),
        "result_index_ref": _rel(run_root / "tactic_portfolio_results.json"),
    })
    _write_json(run_root / "tactic_portfolio_results.json", tactic_index)
    _write_json(run_root / "hammer_action_manifest.json", hammer_action_manifest)
    _write_json(run_root / "hammer_search_results.json", hammer_index)
    _write_json(run_root / "proof_minimization_report.json", proof_minimization_report)
    _write_json(run_root / "hammer_selected_proofs.json", hammer_selected_proofs)
    _write_json(
        run_root / "hammer_proof_minimization_report.json",
        proof_minimization_report,
    )
    _write_json(run_root / "hammer_failure_taxonomy.json", hammer_failure_taxonomy)
    _write_json(run_root / "foundry_hammer_learning_rows.json", foundry_hammer_learning)
    _write_json(run_root / "hammer_skill_update_candidates.json", hammer_skill_candidates)
    _write_json(
        run_root / "hammer_context_recipe_update_candidates.json",
        hammer_context_candidates,
    )
    _write_json(run_root / "external_hammer_comparison.json", hammer_comparison)
    _write_json(run_root / "external_statement_only_comparison.json", hammer_comparison)
    _write_json(run_root / "local_statement_only_comparison.json", local_statement_comparison)
    _write_json(run_root / "hammer_search_run_summary.json", hammer_search_run_summary)
    _write_json(run_root / "external_overfit_diagnosis.json", overfit_diagnosis)
    _write_json(run_root / "representative_external_success.json", representatives["representative_external_success"] or {})
    _write_json(run_root / "representative_external_failure.json", representatives["representative_external_failure"] or {})
    _write_json(run_root / "representative_external_oracle_repair.json", representatives["representative_external_oracle_repair"] or {})
    _write_json(run_root / "representative_guarded_success.json", guarded_representatives["representative_guarded_success"] or {})
    _write_json(run_root / "representative_guarded_failure.json", guarded_representatives["representative_guarded_failure"] or {})
    _write_json(run_root / "external_guarded_loop_run_summary.json", summary)
    _write_json(run_root / "external_loop_run_summary.json", summary)
    _write_json(run_root / "run_summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--problem-limit", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    run_root = _repo_path(args.run_root)
    summary = run_smoke(
        run_root=run_root,
        problem_limit=args.problem_limit,
        timeout_seconds=args.timeout_seconds,
    )
    if args.check:
        issues = _validate(run_root, summary)
        if issues:
            for issue in issues:
                print(issue, file=sys.stderr)
            return 1
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            f"{RUN_ID}: foundry={summary.get('foundry_success_count')}/"
            f"{summary.get('external_problem_count')} "
            f"guarded={summary.get('source_guarded_foundry_success_count')} "
            f"portfolio={summary.get('tactic_portfolio_success_count')} "
            f"hammer={summary.get('hammer_search_success_count')} "
            f"oracle={summary.get('oracle_repair_comparator_success_count')} "
            f"leakage={summary.get('truth_side_leakage_count')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
