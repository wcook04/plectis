#!/usr/bin/env python3
"""Run Formal Problem Ladder Evaluation v0 over the provider receipt lane.

This runner compiles proof-withheld Lean problems into the existing
``std_transform_job`` provider plane, optionally dispatches those jobs through
``type_a_worker_harness``, reduces resulting receipts through Lean, and emits
aggregate Prover-Oracle/Foundry evidence. It does not add a provider stack.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import type_a_worker_harness
from system.lib.compliance import transform_job_adapter
from tools.meta.factory import reduce_prover_provider_receipts as reducer
from tools.meta.factory import run_prover_graph_benchmark as harness


RUN_ID = "PROVER_FORMAL_PROBLEM_LADDER_EVAL_20260511_v0"
DEFAULT_RUN_ROOT = Path("state/runs") / RUN_ID
CAP_ID = "cap_prover_formal_problem_ladder_eval_v0"
DEFAULT_RECIPES = ("minimal_4kb", "skill_32kb", "repair_32kb")
DEFAULT_PROVIDER_MODEL = "deepseek-ai/deepseek-v4-pro"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _toolchain_source_path() -> str:
    return harness._toolchain_source_path()


def _common_visible() -> tuple[str, ...]:
    return (
        "formal Lean statement",
        "required imports",
        "allowed premise index slice",
        "context recipe",
    )


def _common_withheld() -> tuple[str, ...]:
    return (
        "ideal proof body",
        "repair proof body",
        "oracle needed premise ids",
        "oracle critique",
        "test split truth beyond theorem statement",
    )


def _formal_problem(
    *,
    problem_id: str,
    split: str,
    domain: str,
    informal_statement: str,
    theorem_signature: str,
    candidate_body: tuple[str, ...],
    ideal_body: tuple[str, ...],
    needed: tuple[str, ...] = (),
    query_terms: tuple[str, ...] = (),
    allowed: tuple[str, ...] | None = None,
    expected_strategy: tuple[str, ...] = (),
    difficulty_tag: str = "formal_ladder_heldout",
) -> harness.ProverProblem:
    return harness.ProverProblem(
        problem_id=problem_id,
        source="lean_std_toolchain_formal_ladder_v0",
        split=split,
        mode="formal_statement_with_known_proof_oracle",
        domain=domain,
        informal_statement=informal_statement,
        theorem_name=problem_id,
        theorem_signature=theorem_signature,
        candidate_body=candidate_body,
        ideal_body=ideal_body,
        visible_to_lab=_common_visible(),
        withheld_until_oracle=_common_withheld(),
        context_recipe_id="formal_problem_ladder_eval_v0",
        expected_error_class_on_fail="PROOF_SYNTHESIS_FAIL",
        required_imports=("Std",),
        source_ref=f"{_toolchain_source_path()}/Init",
        source_family="lean_std_toolchain",
        difficulty_tag=difficulty_tag,
        repair_body=ideal_body,
        allowed_premise_ids=allowed if allowed is not None else needed,
        oracle_needed_premise_ids=needed,
        retrieval_query_terms=query_terms,
        expected_strategy_ids=expected_strategy,
    )


def formal_ladder_problem_set() -> list[harness.ProverProblem]:
    """A proof-withheld Lean/Std heldout set beyond the calibration triples."""

    return [
        _formal_problem(
            problem_id="formal_ladder_nat_succ_inj_a",
            split="train",
            domain="nat",
            informal_statement="Successor is injective on natural numbers.",
            theorem_signature=(
                "theorem formal_ladder_nat_succ_inj_a (m n : Nat) : "
                "Nat.succ m = Nat.succ n -> m = n := by"
            ),
            candidate_body=("  intro h", "  rfl"),
            ideal_body=("  intro h", "  exact Nat.succ.inj h"),
            needed=("premise_nat_succ_inj",),
            query_terms=("nat", "successor", "injective", "constructor"),
            expected_strategy=("constructor_injectivity",),
        ),
        _formal_problem(
            problem_id="formal_ladder_nat_succ_inj_b",
            split="dev",
            domain="nat",
            informal_statement="Constructor injectivity can be used after introducing an equality.",
            theorem_signature=(
                "theorem formal_ladder_nat_succ_inj_b (a b : Nat) "
                "(h : Nat.succ a = Nat.succ b) : a = b := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact Nat.succ.inj h",),
            needed=("premise_nat_succ_inj",),
            query_terms=("nat", "succ", "injective"),
            expected_strategy=("constructor_injectivity",),
        ),
        _formal_problem(
            problem_id="formal_ladder_nat_add_comm_a",
            split="train",
            domain="nat",
            informal_statement="Natural-number addition is commutative.",
            theorem_signature=(
                "theorem formal_ladder_nat_add_comm_a (m n : Nat) : "
                "m + n = n + m := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact Nat.add_comm m n",),
            needed=("premise_nat_add_comm",),
            query_terms=("nat", "addition", "commutative"),
            expected_strategy=("equality_normal_form",),
        ),
        _formal_problem(
            problem_id="formal_ladder_nat_add_comm_b",
            split="test",
            domain="nat",
            informal_statement="The commutativity theorem also proves the opposite variable order.",
            theorem_signature=(
                "theorem formal_ladder_nat_add_comm_b (m n : Nat) : "
                "n + m = m + n := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact Nat.add_comm n m",),
            needed=("premise_nat_add_comm",),
            query_terms=("nat", "addition", "commutative", "orientation"),
            expected_strategy=("symmetry_or_orientation", "equality_normal_form"),
        ),
        _formal_problem(
            problem_id="formal_ladder_nat_add_assoc_a",
            split="dev",
            domain="nat",
            informal_statement="Natural-number addition is associative.",
            theorem_signature=(
                "theorem formal_ladder_nat_add_assoc_a (a b c : Nat) : "
                "(a + b) + c = a + (b + c) := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact Nat.add_assoc a b c",),
            needed=("premise_nat_add_assoc",),
            query_terms=("nat", "addition", "associative"),
            expected_strategy=("equality_normal_form",),
        ),
        _formal_problem(
            problem_id="formal_ladder_nat_add_zero_a",
            split="train",
            domain="nat",
            informal_statement="Adding zero on the right leaves a natural number unchanged.",
            theorem_signature=(
                "theorem formal_ladder_nat_add_zero_a (n : Nat) : n + 0 = n := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact Nat.add_zero n",),
            needed=("premise_nat_add_zero",),
            query_terms=("nat", "zero", "addition", "recursive"),
            expected_strategy=("recursive_data_induction",),
        ),
        _formal_problem(
            problem_id="formal_ladder_nat_add_zero_symm_a",
            split="test",
            domain="nat",
            informal_statement="The right-zero addition theorem may need symmetric orientation.",
            theorem_signature=(
                "theorem formal_ladder_nat_add_zero_symm_a (n : Nat) : n = n + 0 := by"
            ),
            candidate_body=("  exact Nat.add_zero n",),
            ideal_body=("  exact Eq.symm (Nat.add_zero n)",),
            needed=("premise_nat_add_zero",),
            query_terms=("nat", "zero", "addition", "orientation"),
            expected_strategy=("symmetry_or_orientation",),
        ),
        _formal_problem(
            problem_id="formal_ladder_bool_not_not_a",
            split="train",
            domain="bool",
            informal_statement="Double Boolean negation returns the original Boolean.",
            theorem_signature=(
                "theorem formal_ladder_bool_not_not_a (b : Bool) : (!(!b)) = b := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact Bool.not_not b",),
            needed=("premise_bool_not_not",),
            query_terms=("bool", "double", "negation"),
            expected_strategy=("equality_normal_form",),
        ),
        _formal_problem(
            problem_id="formal_ladder_iff_intro_a",
            split="train",
            domain="propositional",
            informal_statement="Two implications assemble an iff.",
            theorem_signature=(
                "theorem formal_ladder_iff_intro_a (p q : Prop) : "
                "(p -> q) -> (q -> p) -> (p <-> q) := by"
            ),
            candidate_body=("  intro hpq hqp", "  exact Iff.rfl"),
            ideal_body=("  intro hpq hqp", "  exact Iff.intro hpq hqp"),
            needed=("premise_iff_intro",),
            query_terms=("iff", "implication", "intro"),
            expected_strategy=("iff_split",),
        ),
        _formal_problem(
            problem_id="formal_ladder_iff_mp_a",
            split="dev",
            domain="propositional",
            informal_statement="Use the forward direction of an iff.",
            theorem_signature=(
                "theorem formal_ladder_iff_mp_a (p q : Prop) : "
                "(p <-> q) -> p -> q := by"
            ),
            candidate_body=("  intro h hp", "  exact hp"),
            ideal_body=("  intro h hp", "  exact Iff.mp h hp"),
            needed=("premise_iff_intro",),
            query_terms=("iff", "forward", "mp", "implication"),
            expected_strategy=("iff_split",),
        ),
        _formal_problem(
            problem_id="formal_ladder_iff_mpr_a",
            split="test",
            domain="propositional",
            informal_statement="Use the reverse direction of an iff.",
            theorem_signature=(
                "theorem formal_ladder_iff_mpr_a (p q : Prop) : "
                "(p <-> q) -> q -> p := by"
            ),
            candidate_body=("  intro h hq", "  exact hq"),
            ideal_body=("  intro h hq", "  exact Iff.mpr h hq"),
            needed=("premise_iff_intro",),
            query_terms=("iff", "reverse", "mpr", "orientation"),
            expected_strategy=("iff_split", "symmetry_or_orientation"),
        ),
        _formal_problem(
            problem_id="formal_ladder_and_comm_a",
            split="train",
            domain="propositional",
            informal_statement="Conjunction can be swapped.",
            theorem_signature=(
                "theorem formal_ladder_and_comm_a (p q : Prop) : p ∧ q -> q ∧ p := by"
            ),
            candidate_body=("  intro h", "  exact And.intro h.left h.right"),
            ideal_body=("  intro h", "  exact And.intro h.right h.left"),
            needed=(),
            query_terms=("and", "commute", "split"),
            allowed=(),
            expected_strategy=("membership_decomposition",),
        ),
        _formal_problem(
            problem_id="formal_ladder_or_comm_a",
            split="dev",
            domain="propositional",
            informal_statement="Disjunction can be swapped by case analysis.",
            theorem_signature=(
                "theorem formal_ladder_or_comm_a (p q : Prop) : p ∨ q -> q ∨ p := by"
            ),
            candidate_body=("  intro h", "  exact Or.inl h"),
            ideal_body=(
                "  intro h",
                "  cases h with",
                "  | inl hp => exact Or.inr hp",
                "  | inr hq => exact Or.inl hq",
            ),
            needed=(),
            query_terms=("or", "case", "split"),
            allowed=(),
            expected_strategy=("membership_decomposition",),
        ),
        _formal_problem(
            problem_id="formal_ladder_exists_zero_a",
            split="test",
            domain="existential",
            informal_statement="Zero witnesses an existential over natural numbers.",
            theorem_signature=(
                "theorem formal_ladder_exists_zero_a : ∃ n : Nat, n = 0 := by"
            ),
            candidate_body=("  exact True.intro",),
            ideal_body=("  exact Exists.intro 0 rfl",),
            needed=(),
            query_terms=("exists", "witness", "zero"),
            allowed=(),
            expected_strategy=("membership_decomposition",),
        ),
        _formal_problem(
            problem_id="formal_ladder_false_elim_a",
            split="dev",
            domain="propositional",
            informal_statement="A contradiction hypothesis proves any proposition.",
            theorem_signature=(
                "theorem formal_ladder_false_elim_a (p : Prop) (h : False) : p := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact False.elim h",),
            needed=(),
            query_terms=("false", "contradiction", "elim"),
            allowed=(),
            expected_strategy=("contradiction_or_false_target",),
        ),
        _formal_problem(
            problem_id="formal_ladder_list_length_append_a",
            split="train",
            domain="list",
            informal_statement="The length of appended lists is the sum of lengths.",
            theorem_signature=(
                "theorem formal_ladder_list_length_append_a (Alpha : Type) "
                "(xs ys : List Alpha) : (xs ++ ys).length = xs.length + ys.length := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact List.length_append",),
            needed=("premise_list_length_append",),
            query_terms=("list", "length", "append"),
            expected_strategy=("equality_normal_form",),
        ),
        _formal_problem(
            problem_id="formal_ladder_list_length_append_symm_a",
            split="test",
            domain="list",
            informal_statement="The length append theorem may need the symmetric orientation.",
            theorem_signature=(
                "theorem formal_ladder_list_length_append_symm_a (Alpha : Type) "
                "(xs ys : List Alpha) : xs.length + ys.length = (xs ++ ys).length := by"
            ),
            candidate_body=("  exact List.length_append",),
            ideal_body=("  exact Eq.symm List.length_append",),
            needed=("premise_list_length_append",),
            query_terms=("list", "length", "append", "orientation"),
            expected_strategy=("symmetry_or_orientation",),
        ),
        _formal_problem(
            problem_id="formal_ladder_list_map_map_a",
            split="dev",
            domain="list",
            informal_statement="Two list maps fuse into one map over function composition.",
            theorem_signature=(
                "theorem formal_ladder_list_map_map_a (Alpha Beta Gamma : Type) "
                "(f : Alpha -> Beta) (g : Beta -> Gamma) (xs : List Alpha) : "
                "List.map g (List.map f xs) = List.map (g ∘ f) xs := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact List.map_map",),
            needed=("premise_list_map_map",),
            query_terms=("list", "map", "composition", "fusion"),
            expected_strategy=("composition_fusion",),
        ),
        _formal_problem(
            problem_id="formal_ladder_list_mem_append_a",
            split="test",
            domain="list",
            informal_statement="Membership in appended lists decomposes into a disjunction.",
            theorem_signature=(
                "theorem formal_ladder_list_mem_append_a (Alpha : Type) (a : Alpha) "
                "(xs ys : List Alpha) : "
                "List.Mem a (xs ++ ys) <-> List.Mem a xs \\/ List.Mem a ys := by"
            ),
            candidate_body=("  exact Iff.rfl",),
            ideal_body=("  exact List.mem_append",),
            needed=("premise_list_mem_append",),
            query_terms=("list", "membership", "append"),
            expected_strategy=("membership_decomposition",),
        ),
        _formal_problem(
            problem_id="formal_ladder_list_reverse_reverse_a",
            split="dev",
            domain="list",
            informal_statement="Reversing a list twice returns the original list.",
            theorem_signature=(
                "theorem formal_ladder_list_reverse_reverse_a (Alpha : Type) "
                "(xs : List Alpha) : xs.reverse.reverse = xs := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact List.reverse_reverse xs",),
            needed=("premise_list_reverse_reverse",),
            query_terms=("list", "reverse", "twice"),
            expected_strategy=("equality_normal_form",),
        ),
        _formal_problem(
            problem_id="formal_ladder_list_cons_length_a",
            split="train",
            domain="list",
            informal_statement="The length of a cons is one plus the tail length.",
            theorem_signature=(
                "theorem formal_ladder_list_cons_length_a (Alpha : Type) "
                "(x : Alpha) (xs : List Alpha) : (x :: xs).length = xs.length + 1 := by"
            ),
            candidate_body=("  exact List.length_append",),
            ideal_body=("  exact List.length_cons",),
            needed=("premise_list_length_cons",),
            query_terms=("list", "length", "cons"),
            expected_strategy=("recursive_data_induction",),
        ),
    ]


def _forward_safe_problem_row(problem: harness.ProverProblem) -> dict[str, Any]:
    return {
        "schema_version": "prover_formal_problem_row_v0",
        "problem_id": problem.problem_id,
        "source": problem.source,
        "split": problem.split,
        "mode": problem.mode,
        "domain": problem.domain,
        "informal_statement": problem.informal_statement,
        "theorem_name": problem.theorem_name,
        "theorem_signature": problem.theorem_signature,
        "required_imports": list(problem.required_imports),
        "source_ref": problem.source_ref,
        "source_family": problem.source_family,
        "difficulty_tag": problem.difficulty_tag,
        "allowed_premise_ids": list(problem.allowed_premise_ids),
        "retrieval_query_terms": list(problem.retrieval_query_terms),
        "visible_to_lab": list(problem.visible_to_lab),
        "withheld_until_oracle": list(problem.withheld_until_oracle),
        "context_recipe_id": problem.context_recipe_id,
        "proof_body_withheld_until_oracle": True,
    }


def _problem_source_manifest(problem_set: list[harness.ProverProblem]) -> dict[str, Any]:
    return {
        "schema_version": "prover_problem_source_manifest_v0",
        "source_id": "lean_std_toolchain_formal_ladder_v0",
        "source_kind": "installed_lean_toolchain_source",
        "local_or_annex_path": _toolchain_source_path(),
        "problem_count": len(problem_set),
        "problem_ids": [problem.problem_id for problem in problem_set],
        "split_policy": {
            "train": "Allowed for graph/process tuning.",
            "dev": "Allowed for graph variant selection.",
            "test": "Held out from tuning; report only.",
        },
        "leakage_policy": {
            "statement_visible_to_lab": True,
            "required_imports_visible_to_lab": True,
            "proof_body_withheld_until_oracle": True,
            "test_split_tuning": "forbidden",
        },
        "problems": [_forward_safe_problem_row(problem) for problem in problem_set],
    }


def _external_corpus_readiness_summary() -> dict[str, Any]:
    checks = {
        "ulamai_annex": REPO_ROOT / "annexes/ulamai",
        "ulamai_checkout": REPO_ROOT / "annexes/ulamai/repo",
        "frontiermath_solver_annex": REPO_ROOT / "annexes/frontiermath-solver",
        "frontiermath_solver_checkout": REPO_ROOT / "annexes/frontiermath-solver/repo",
        "formal_conjectures_checkout": REPO_ROOT / "annexes/formal-conjectures/repo",
        "leandojo_checkout": REPO_ROOT / "annexes/LeanDojo/repo",
        "minif2f_checkout": REPO_ROOT / "annexes/miniF2F/repo",
        "putnambench_checkout": REPO_ROOT / "annexes/PutnamBench/repo",
        "mathlib_checkout": REPO_ROOT / "annexes/mathlib/repo",
    }
    rows = []
    for key, path in checks.items():
        rows.append(
            {
                "corpus_id": key,
                "path": _rel(path),
                "exists": path.exists(),
                "runnable_in_this_wave": False,
                "reason": (
                    "metadata_or_checkout_present_but_not_selected_for_first_ladder_eval"
                    if path.exists()
                    else "not_present_locally"
                ),
            }
        )
    return {
        "schema_version": "prover_external_corpus_readiness_summary_v0",
        "created_at": _utc_now(),
        "selected_for_this_run": "lean_std_toolchain_formal_ladder_v0",
        "selection_reason": (
            "Lean 4 toolchain is local and deterministic; external theorem corpora are "
            "kept as readiness evidence until a small build/check subset is verified."
        ),
        "lean_cli": {
            "available": shutil.which("lean") is not None,
        },
        "corpora": rows,
    }


def compile_jobs(
    *,
    run_root: Path,
    provider: str,
    provider_model: str | None,
    live_probe: bool,
    context_recipes: tuple[str, ...],
    problem_limit: int,
    timeout_seconds: int,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    run_root = _repo_path(run_root)
    problem_set = formal_ladder_problem_set()[:problem_limit]
    premise_index = harness._premise_index()
    source_manifest = _problem_source_manifest(problem_set)
    availability = harness._provider_availability_report(
        requested_provider=provider,
        live_probe=live_probe,
    )
    selected_provider = str(availability["selected_provider"])
    run_root.mkdir(parents=True, exist_ok=True)
    _write_json(run_root / "problem_set_manifest.json", harness._problem_manifest(problem_set))
    _write_json(run_root / "formal_problem_ladder_manifest.json", source_manifest)
    _write_json(run_root / "problem_source_manifest.json", source_manifest)
    _write_json(run_root / "premise_index.json", premise_index)
    _write_json(run_root / "external_corpus_annex_readiness_summary.json", _external_corpus_readiness_summary())
    _write_json(run_root / "provider_availability_report.json", availability)

    baseline = harness.run_benchmark(
        run_root=run_root / "local_foundry_baseline",
        timeout_seconds=timeout_seconds,
        run_id=f"{RUN_ID}_local_foundry_baseline",
        problem_set=problem_set,
        problem_source_manifest=source_manifest,
        premise_index=premise_index,
        graph_variant_id=harness.SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT,
        cap_id=CAP_ID,
    )
    local_foundry_by_problem = {
        row["problem_id"]: row for row in baseline.get("problem_results", [])
    }

    transform_root = run_root / "transform_job_preview_state"
    rows: list[dict[str, Any]] = []
    for recipe_id in context_recipes:
        recipe = harness._provider_context_recipe(recipe_id)
        for problem in problem_set:
            context_pack, retrieval_report, skill_decision, allowed_premise_ids = (
                harness._provider_context_pack(
                    problem=problem,
                    recipe_id=recipe_id,
                    provider=selected_provider,
                    provider_model=provider_model,
                    premise_index=premise_index,
                    problem_set=problem_set,
                    local_foundry_by_problem=local_foundry_by_problem,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            )
            output_schema = {
                "type": "object",
                "required": [
                    "lean_proof_body",
                    "premise_ids_used",
                    "notes",
                    "confidence",
                    "omissions",
                ],
                "properties": {
                    "lean_proof_body": {"type": "string"},
                    "premise_ids_used": {"type": "array"},
                    "notes": {"type": "string"},
                    "confidence": {"type": "number"},
                    "omissions": {"type": "array"},
                },
                "additionalProperties": False,
            }
            formal_problem = _forward_safe_problem_row(problem)
            input_packet = {
                "schema_version": "prover_formal_problem_ladder_transform_input_v0",
                "formal_problem": formal_problem,
                "prover_context_pack": context_pack,
                "retrieval_report_ref": {
                    "retrieved_premise_ids": retrieval_report.get("retrieved_premise_ids", []),
                    "proof_body_visible": False,
                },
                "skill_decision_ref": {
                    "skill_cell_id": skill_decision.get("skill_cell_id"),
                    "applied": skill_decision.get("applied"),
                    "oracle_needed_premise_ids_visible": False,
                },
                "provider_task": {
                    "graph_role": recipe["graph_role"],
                    "deliverable_type": recipe["deliverable_type"],
                    "telos": recipe["telos"],
                    "success_contract": context_pack["success_contract"],
                    "response_rule": "Return exactly one JSON object matching output_schema. Do not include markdown.",
                },
                "allowed_premise_ids": allowed_premise_ids,
                "output_schema": output_schema,
            }
            transform_job = type_a_worker_harness.build_transform_job(
                REPO_ROOT,
                task_class=harness.PROVER_PROVIDER_TRANSFORM_TASK_CLASS,
                target_row_id=f"formal_problem:{problem.problem_id}:{recipe_id}",
                target_facet="lean_proof_hypothesis",
                target_band="formal_problem_ladder",
                input_packet=input_packet,
                output_schema=output_schema,
                source_paths=[
                    "tools/meta/factory/run_prover_formal_problem_ladder_eval.py",
                    "tools/meta/factory/run_prover_graph_benchmark.py",
                    "tools/meta/factory/reduce_prover_provider_receipts.py",
                    "codex/standards/std_transform_job.json",
                    str(run_root / "local_foundry_baseline" / "run_summary.json"),
                ],
                provider_selection_policy={
                    "prefer": [selected_provider],
                    "capacity_lane_id": f"provider:{selected_provider}",
                    "paid_gate": False,
                    "models": ({selected_provider: provider_model} if provider_model else {}),
                    "context_recipe_id": recipe_id,
                },
                validation_command=(
                    "./repo-python tools/meta/factory/run_prover_formal_problem_ladder_eval.py --check --json"
                ),
                promotion_target={
                    "state": "draft_candidate_only",
                    "surface": "formal_problem_ladder_receipt_reducer",
                    "run_root": str(run_root),
                    "lean_oracle_required_before_success": True,
                },
                created_by="prover_formal_problem_ladder_eval_transform_compiler",
            )
            transform_job["execution_profile"] = {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "provider_model": provider_model,
            }
            transform_job["failure_policy"] = {
                "timeout_s": 180,
                "on_provider_failure": "record_receipt_and_route_to_foundry_attribution",
            }
            written = type_a_worker_harness.write_transform_job(
                REPO_ROOT,
                transform_job,
                write_root=transform_root,
            )
            rows.append(
                {
                    "problem_id": problem.problem_id,
                    "source": problem.source,
                    "split": problem.split,
                    "recipe_id": recipe_id,
                    "graph_role": recipe["graph_role"],
                    "provider": selected_provider,
                    "model": provider_model,
                    "transform_job_id": written["id"],
                    "transform_job_ref": str(transform_root / written["artifact_path"]),
                    "target_row_id": written["target_row_id"],
                    "context_pack_id": context_pack["context_pack_id"],
                    "context_pack_kib": context_pack["context_budget"]["kib"],
                    "context_pack_bytes": context_pack["context_budget"]["bytes"],
                    "context_pack_approximate_tokens": context_pack["context_budget"]["approximate_tokens"],
                    "retrieved_premise_ids": retrieval_report.get("retrieved_premise_ids", []),
                    "allowed_premise_ids": allowed_premise_ids,
                    "skill_cell_id": skill_decision.get("skill_cell_id"),
                    "provider_dispatch": False,
                    "leakage_detected": context_pack["leakage_audit"]["status"] != "PASS",
                }
            )

    compliance = transform_job_adapter.scan_transform_jobs(transform_root)
    by_recipe: dict[str, dict[str, Any]] = {}
    for row in rows:
        bucket = by_recipe.setdefault(
            row["recipe_id"],
            {"transform_job_count": 0, "context_bytes": 0, "leakage_count": 0},
        )
        bucket["transform_job_count"] += 1
        bucket["context_bytes"] += int(row["context_pack_bytes"])
        bucket["leakage_count"] += 1 if row["leakage_detected"] else 0
    transform_manifest = {
        "schema_version": "prover_formal_problem_ladder_transform_job_manifest_v0",
        "task_class": harness.PROVER_PROVIDER_TRANSFORM_TASK_CLASS,
        "provider": selected_provider,
        "model": provider_model,
        "dispatch_posture": "not_dispatched",
        "transform_job_count": len(rows),
        "write_root": str(transform_root),
        "jobs": [
            {
                "transform_job_id": row["transform_job_id"],
                "problem_id": row["problem_id"],
                "source": row["source"],
                "split": row["split"],
                "recipe_id": row["recipe_id"],
                "graph_role": row["graph_role"],
                "target_row_id": row["target_row_id"],
                "artifact_path": row["transform_job_ref"],
            }
            for row in rows
        ],
    }
    context_manifest = {
        "schema_version": "provider_context_pack_manifest_v0",
        "context_pack_count": len(rows),
        "context_packs": [
            {
                "problem_id": row["problem_id"],
                "recipe_id": row["recipe_id"],
                "graph_role": row["graph_role"],
                "context_pack_id": row["context_pack_id"],
                "bytes_in": row["context_pack_bytes"],
                "context_pack_kib": row["context_pack_kib"],
            }
            for row in rows
        ],
    }
    compile_summary = {
        "schema_version": "prover_formal_problem_ladder_compile_summary_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "cap_id": CAP_ID,
        "problem_count": len(problem_set),
        "context_recipes": list(context_recipes),
        "transform_job_count": len(rows),
        "provider": selected_provider,
        "provider_model": provider_model,
        "dispatch_posture": "compiled_transform_jobs_not_dispatched",
        "provider_calls_by_compiler": 0,
        "provider_calls_by_reducer": 0,
        "harness_owned_provider_dispatch_added": False,
        "fake_provider_results_counted": 0,
        "open_problem_success_claimed": False,
        "truth_side_leakage_count": sum(1 for row in rows if row["leakage_detected"]),
        "by_recipe": by_recipe,
        "artifact_refs": {
            "problem_source_manifest": _rel(run_root / "problem_source_manifest.json"),
            "formal_problem_ladder_manifest": _rel(run_root / "formal_problem_ladder_manifest.json"),
            "premise_index": _rel(run_root / "premise_index.json"),
            "provider_availability_report": _rel(run_root / "provider_availability_report.json"),
            "external_corpus_annex_readiness_summary": _rel(
                run_root / "external_corpus_annex_readiness_summary.json"
            ),
            "local_foundry_baseline": _rel(run_root / "local_foundry_baseline" / "run_summary.json"),
            "transform_job_manifest": _rel(run_root / "transform_job_manifest.json"),
            "transform_job_compliance_report": _rel(run_root / "transform_job_compliance_report.json"),
            "context_pack_manifest": _rel(run_root / "context_pack_manifest.json"),
        },
    }
    _write_json(run_root / "transform_job_manifest.json", transform_manifest)
    _write_json(run_root / "transform_job_compliance_report.json", compliance)
    _write_json(run_root / "context_pack_manifest.json", context_manifest)
    _write_json(run_root / "compile_summary.json", compile_summary)
    _write_json(run_root / "run_summary.json", compile_summary)
    return compile_summary


def _iter_manifest_jobs(run_root: Path) -> list[dict[str, Any]]:
    manifest = _read_json(run_root / "transform_job_manifest.json")
    return [row for row in manifest.get("jobs", []) if isinstance(row, dict)]


def _dispatch_row_from_result(
    *,
    job: Mapping[str, Any],
    job_path: Path,
    result: type_a_worker_harness.HarnessResult,
    attempt_type: str,
    previous_receipt_status: str | None = None,
    resume_attempt_index: int | None = None,
) -> dict[str, Any]:
    refs = result.receipt.get("artifact_refs") or {}
    row = {
        "transform_job_id": job.get("transform_job_id"),
        "problem_id": job.get("problem_id"),
        "recipe_id": job.get("recipe_id"),
        "graph_role": job.get("graph_role"),
        "transform_job_ref": str(job_path),
        "receipt_id": result.receipt.get("receipt_id"),
        "receipt_status": result.receipt.get("status"),
        "receipt_ref": refs.get("receipt"),
        "row_patch_ref": refs.get("row_patch"),
        "provider_id": result.receipt.get("provider_id"),
        "model_id": result.receipt.get("model_id"),
        "latency_ms": result.receipt.get("latency_ms"),
        "validation_result": result.receipt.get("validation_result"),
        "attempt_type": attempt_type,
    }
    if previous_receipt_status is not None:
        row["previous_receipt_status"] = previous_receipt_status
    if resume_attempt_index is not None:
        row["resume_attempt_index"] = resume_attempt_index
    return row


def dispatch_jobs(
    *,
    run_root: Path,
    provider: str,
    provider_model: str | None,
    limit: int | None,
    force: bool,
) -> dict[str, Any]:
    run_root = _repo_path(run_root)
    rows: list[dict[str, Any]] = []
    for job in _iter_manifest_jobs(run_root)[: limit or None]:
        job_path = _repo_path(str(job["artifact_path"]))
        result = type_a_worker_harness.run_transform_job(
            REPO_ROOT,
            job_path=job_path,
            provider_id=provider,
            model_id=provider_model,
            force=force,
        )
        rows.append(
            _dispatch_row_from_result(
                job=job,
                job_path=job_path,
                result=result,
                attempt_type="initial_dispatch",
            )
        )
    dispatch = {
        "schema_version": "prover_formal_problem_ladder_dispatch_manifest_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "provider": provider,
        "provider_model": provider_model,
        "dispatch_owner": "system.lib.type_a_worker_harness",
        "requested_limit": limit,
        "receipt_count": len(rows),
        "fake_provider_results_counted": 0,
        "rows": rows,
    }
    _write_json(run_root / "provider_dispatch_manifest.json", dispatch)
    return dispatch


def _status_filter(raw: str | Iterable[str] | None) -> set[str]:
    if raw is None:
        return {"429", "missing"}
    if isinstance(raw, str):
        values = raw.split(",")
    else:
        values = list(raw)
    return {str(value).strip() for value in values if str(value).strip()}


def _latest_rows_by_job_id(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        job_id = str(row.get("transform_job_id") or "")
        if job_id:
            latest[job_id] = dict(row)
    return latest


def resume_rate_limited_jobs(
    *,
    run_root: Path,
    provider: str,
    provider_model: str | None,
    resume_statuses: str | Iterable[str] | None = None,
    limit: int | None = None,
    sleep_seconds: float = 5.0,
    max_consecutive_429: int = 3,
) -> dict[str, Any]:
    run_root = _repo_path(run_root)
    status_filter = _status_filter(resume_statuses)
    jobs = _iter_manifest_jobs(run_root)
    dispatch_path = run_root / "provider_dispatch_manifest.json"
    dispatch = _read_json(dispatch_path) if dispatch_path.exists() else {"rows": []}
    original_path = run_root / "provider_dispatch_original_manifest.json"
    if dispatch_path.exists() and not original_path.exists():
        _write_json(original_path, dispatch)

    existing_rows = [row for row in dispatch.get("rows", []) if isinstance(row, Mapping)]
    existing_by_job_id = _latest_rows_by_job_id(existing_rows)
    ok_job_ids = {
        job_id
        for job_id, row in existing_by_job_id.items()
        if str(row.get("receipt_status") or "") == "ok"
    }

    selected: list[dict[str, Any]] = []
    for job in jobs:
        job_id = str(job.get("transform_job_id") or "")
        if not job_id or job_id in ok_job_ids:
            continue
        previous_status = str(existing_by_job_id.get(job_id, {}).get("receipt_status") or "missing")
        if previous_status in status_filter:
            selected.append(job)
    if limit is not None:
        selected = selected[: max(int(limit), 0)]

    resume_rows: list[dict[str, Any]] = []
    consecutive_429 = 0
    stopped_reason = "completed_selected_jobs"
    for index, job in enumerate(selected, start=1):
        job_id = str(job.get("transform_job_id") or "")
        previous_status = str(existing_by_job_id.get(job_id, {}).get("receipt_status") or "missing")
        job_path = _repo_path(str(job["artifact_path"]))
        result = type_a_worker_harness.run_transform_job(
            REPO_ROOT,
            job_path=job_path,
            provider_id=provider,
            model_id=provider_model,
            force=True,
        )
        row = _dispatch_row_from_result(
            job=job,
            job_path=job_path,
            result=result,
            attempt_type="resume_rate_limited",
            previous_receipt_status=previous_status,
            resume_attempt_index=index,
        )
        resume_rows.append(row)
        status = str(row.get("receipt_status") or "")
        consecutive_429 = consecutive_429 + 1 if status == "429" else 0
        if max_consecutive_429 > 0 and consecutive_429 >= max_consecutive_429:
            stopped_reason = "max_consecutive_429"
            break
        if index < len(selected) and sleep_seconds > 0:
            time.sleep(float(sleep_seconds))

    resume_path = run_root / "provider_dispatch_resume_manifest.json"
    previous_resume = _read_json(resume_path) if resume_path.exists() else {}
    previous_resume_rows = [
        row for row in previous_resume.get("rows", []) if isinstance(row, Mapping)
    ]
    all_resume_rows = [*previous_resume_rows, *resume_rows]
    resume_manifest = {
        "schema_version": "prover_formal_problem_ladder_dispatch_resume_manifest_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "provider": provider,
        "provider_model": provider_model,
        "resume_statuses": sorted(status_filter),
        "requested_limit": limit,
        "sleep_seconds": sleep_seconds,
        "max_consecutive_429": max_consecutive_429,
        "skipped_ok_count": len(ok_job_ids),
        "candidate_count": len(selected),
        "latest_attempt_count": len(resume_rows),
        "attempted_count": len(all_resume_rows),
        "previous_attempted_count": len(previous_resume_rows),
        "stopped_reason": stopped_reason,
        "latest_rows": resume_rows,
        "rows": all_resume_rows,
    }
    _write_json(resume_path, resume_manifest)

    effective_by_job_id = dict(existing_by_job_id)
    effective_by_job_id.update(_latest_rows_by_job_id(all_resume_rows))
    effective_rows: list[dict[str, Any]] = []
    for job in jobs:
        job_id = str(job.get("transform_job_id") or "")
        row = effective_by_job_id.get(job_id)
        if row:
            effective_rows.append(row)

    effective_dispatch = {
        "schema_version": "prover_formal_problem_ladder_dispatch_manifest_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "provider": provider,
        "provider_model": provider_model,
        "dispatch_owner": "system.lib.type_a_worker_harness",
        "requested_limit": dispatch.get("requested_limit"),
        "receipt_count": len(effective_rows),
        "fake_provider_results_counted": 0,
        "resume_attempt_count": len(all_resume_rows),
        "resume_manifest_ref": _rel(resume_path),
        "original_manifest_ref": _rel(original_path) if original_path.exists() else None,
        "resume_stopped_reason": stopped_reason,
        "rows": effective_rows,
    }
    _write_json(dispatch_path, effective_dispatch)
    return resume_manifest


def reduce_dispatched_receipts(
    *,
    run_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    run_root = _repo_path(run_root)
    dispatch = _read_json(run_root / "provider_dispatch_manifest.json")
    rows: list[dict[str, Any]] = []
    for row in dispatch.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        receipt_ref = row.get("receipt_ref")
        row_patch_ref = row.get("row_patch_ref")
        if not receipt_ref or not row_patch_ref:
            rows.append({**dict(row), "reduction_status": "skipped_no_row_patch"})
            continue
        summary = reducer.reduce_receipt(
            receipt_path=_repo_path(str(receipt_ref)),
            row_patch_path=_repo_path(str(row_patch_ref)),
            transform_job_path=_repo_path(str(row["transform_job_ref"])),
            run_root=run_root,
            timeout_seconds=timeout_seconds,
            cap_id=CAP_ID,
        )
        latest = summary.get("latest_reduction") if isinstance(summary.get("latest_reduction"), Mapping) else {}
        rows.append(
            {
                **dict(row),
                "reduction_status": "reduced",
                "accepted_by_lean": latest.get("accepted_by_lean"),
                "recipe_policy_passed": latest.get("recipe_policy_passed"),
                "error_class": latest.get("error_class"),
                "receipt_reduction_report": latest.get("receipt_reduction_report"),
                "lean_check_result": latest.get("lean_check_result"),
                "provider_oracle_attribution": latest.get("provider_oracle_attribution"),
                "foundry_learning_row": latest.get("foundry_learning_row"),
                "row_patch_review": latest.get("row_patch_review"),
                "row_patch_review_outcome": latest.get("row_patch_review_outcome"),
            }
        )
    manifest = {
        "schema_version": "prover_formal_problem_ladder_reduction_manifest_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "reduced_count": sum(1 for row in rows if row.get("reduction_status") == "reduced"),
        "rows": rows,
    }
    _write_json(run_root / "receipt_reduction_manifest.json", manifest)
    return manifest


def _iter_reduction_reports(run_root: Path) -> Iterable[tuple[Path, dict[str, Any]]]:
    for path in sorted((run_root / "reductions").glob("*/receipt_reduction_report.json")):
        yield path, _read_json(path)


def _load_ref(ref: Any) -> dict[str, Any]:
    if not ref:
        return {}
    path = _repo_path(str(ref))
    return _read_json(path) if path.exists() else {}


def build_report(run_root: Path) -> dict[str, Any]:
    run_root = _repo_path(run_root)
    source_manifest = _read_json(run_root / "problem_source_manifest.json")
    transform_manifest = (
        _read_json(run_root / "transform_job_manifest.json")
        if (run_root / "transform_job_manifest.json").exists()
        else {}
    )
    dispatch_manifest = (
        _read_json(run_root / "provider_dispatch_manifest.json")
        if (run_root / "provider_dispatch_manifest.json").exists()
        else {}
    )
    reduction_manifest = (
        _read_json(run_root / "receipt_reduction_manifest.json")
        if (run_root / "receipt_reduction_manifest.json").exists()
        else {}
    )
    transform_jobs = [
        row for row in transform_manifest.get("jobs", []) if isinstance(row, Mapping)
    ]
    dispatch_rows = [
        row for row in dispatch_manifest.get("rows", []) if isinstance(row, Mapping)
    ]
    reduction_rows = [
        row for row in reduction_manifest.get("rows", []) if isinstance(row, Mapping)
    ]
    expected_transform_job_count = transform_manifest.get("transform_job_count") or len(
        transform_jobs
    )
    dispatch_status_counts = Counter(
        str(row.get("receipt_status")) for row in dispatch_rows if row.get("receipt_status")
    )
    reduction_status_counts = Counter(
        str(row.get("reduction_status"))
        for row in reduction_rows
        if row.get("reduction_status")
    )
    rows: list[dict[str, Any]] = []
    for report_path, report in _iter_reduction_reports(run_root):
        oracle = _load_ref(report.get("provider_oracle_attribution_ref"))
        lean = _load_ref(report.get("lean_check_result_ref"))
        foundry = _load_ref(report.get("foundry_learning_row_ref"))
        context = report.get("context_metrics") if isinstance(report.get("context_metrics"), Mapping) else {}
        budget = context.get("context_budget") if isinstance(context.get("context_budget"), Mapping) else {}
        premise_policy = (
            report.get("premise_policy_audit")
            if isinstance(report.get("premise_policy_audit"), Mapping)
            else {}
        )
        leakage = report.get("leakage_audit") if isinstance(report.get("leakage_audit"), Mapping) else {}
        problem_id = str(report.get("problem_id") or "")
        problem_row = next(
            (row for row in source_manifest.get("problems", []) if row.get("problem_id") == problem_id),
            {},
        )
        rows.append(
            {
                "receipt_id": report.get("receipt_id"),
                "problem_id": problem_id,
                "source": problem_row.get("source"),
                "split": problem_row.get("split"),
                "domain": problem_row.get("domain"),
                "provider_id": report.get("provider_id"),
                "model_id": report.get("model_id"),
                "recipe_id": report.get("recipe_id") or oracle.get("recipe_id"),
                "graph_role": report.get("graph_role") or oracle.get("graph_role"),
                "accepted_by_lean": bool(report.get("accepted_by_lean")),
                "recipe_policy_passed": bool(report.get("recipe_policy_passed")),
                "error_class": report.get("error_class"),
                "row_patch_review_outcome": report.get("row_patch_review_outcome"),
                "leakage_status": leakage.get("status"),
                "truth_side_leakage_hits": leakage.get("truth_side_leakage_hits") or [],
                "premise_policy_status": premise_policy.get("status"),
                "unallowed_premise_ids": premise_policy.get("unallowed_premise_ids") or [],
                "cited_unallowed_premise_ids": premise_policy.get("cited_unallowed_premise_ids") or [],
                "undeclared_library_prior_symbols": premise_policy.get("undeclared_library_prior_symbols") or [],
                "context_bytes": budget.get("bytes"),
                "context_kib": budget.get("kib"),
                "bytes_out": context.get("bytes_out"),
                "latency_ms": context.get("latency_ms"),
                "cost": context.get("cost"),
                "usage": context.get("usage"),
                "lean_compile_status": lean.get("compile_status"),
                "lean_duration_ms": lean.get("duration_ms"),
                "foundry_learning_class": foundry.get("learning_class"),
                "report_ref": _rel(report_path),
                "lean_check_result_ref": report.get("lean_check_result_ref"),
                "provider_oracle_attribution_ref": report.get("provider_oracle_attribution_ref"),
                "foundry_learning_row_ref": report.get("foundry_learning_row_ref"),
                "row_patch_review_ref": report.get("row_patch_review_ref"),
            }
        )

    by_recipe: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_recipe[str(row["recipe_id"])].append(row)
        by_source[str(row["source"])].append(row)

    def metric_bucket(bucket_rows: list[dict[str, Any]]) -> dict[str, Any]:
        errors = Counter(str(row["error_class"]) for row in bucket_rows)
        return {
            "receipt_count": len(bucket_rows),
            "lean_accepted_count": sum(1 for row in bucket_rows if row["accepted_by_lean"]),
            "recipe_policy_accepted_count": sum(1 for row in bucket_rows if row["recipe_policy_passed"]),
            "truth_side_leakage_count": sum(1 for row in bucket_rows if row["leakage_status"] != "PASS"),
            "premise_budget_violation_count": errors.get("PREMISE_BUDGET_VIOLATION", 0),
            "undeclared_library_prior_count": errors.get("UNDECLARED_LIBRARY_PRIOR", 0),
            "proof_synthesis_failure_count": errors.get("PROOF_SYNTHESIS_FAIL", 0),
            "provider_contract_failure_count": errors.get("PROVIDER_CONTRACT_FAIL", 0),
            "error_counts": dict(errors),
        }

    matrix = {
        "schema_version": "prover_formal_problem_ladder_reduction_matrix_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "rows": rows,
    }
    recipe_metrics = {
        "schema_version": "prover_formal_problem_ladder_recipe_policy_metrics_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "recipes": [
            {"recipe_id": recipe, **metric_bucket(recipe_rows)}
            for recipe, recipe_rows in sorted(by_recipe.items())
        ],
    }
    source_comparison = {
        "schema_version": "prover_formal_problem_ladder_source_comparison_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "sources": [
            {"source": source, **metric_bucket(source_rows)}
            for source, source_rows in sorted(by_source.items())
        ],
    }
    cost_latency = {
        "schema_version": "prover_formal_problem_ladder_cost_latency_usage_report_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "total_latency_ms": sum(int(row.get("latency_ms") or 0) for row in rows),
        "avg_latency_ms": (
            sum(int(row.get("latency_ms") or 0) for row in rows) / len(rows) if rows else 0
        ),
        "total_bytes_out": sum(int(row.get("bytes_out") or 0) for row in rows),
        "usage_entries": [row.get("usage") for row in rows],
        "cost_entries": [row.get("cost") for row in rows],
    }
    foundry_rows = {
        "schema_version": "prover_formal_problem_ladder_foundry_learning_rows_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "rows": [_load_ref(row.get("foundry_learning_row_ref")) for row in rows],
    }
    representative_success = next((row for row in rows if row["recipe_policy_passed"]), {})
    representative_failure = next((row for row in rows if row["error_class"] == "PROOF_SYNTHESIS_FAIL"), {})
    representative_policy = next(
        (row for row in rows if row["error_class"] == "PREMISE_BUDGET_VIOLATION"),
        {},
    )
    reduced_receipt_count = len(rows)
    completion_status = "complete"
    if expected_transform_job_count and reduced_receipt_count < int(expected_transform_job_count):
        completion_status = (
            "partial_provider_rate_limited"
            if dispatch_status_counts.get("429", 0)
            else "partial"
        )
    summary = {
        "schema_version": "prover_formal_problem_ladder_eval_run_summary_v0",
        "created_at": _utc_now(),
        "run_id": RUN_ID,
        "cap_id": CAP_ID,
        "problem_count": source_manifest.get("problem_count"),
        "expected_transform_job_count": expected_transform_job_count,
        "provider_dispatch_attempt_count": len(dispatch_rows),
        "provider_dispatch_resume_attempt_count": int(dispatch_manifest.get("resume_attempt_count") or 0),
        "provider_dispatch_resume_stopped_reason": dispatch_manifest.get("resume_stopped_reason"),
        "provider_dispatch_ok_count": dispatch_status_counts.get("ok", 0),
        "provider_dispatch_error_count": len(dispatch_rows) - dispatch_status_counts.get("ok", 0),
        "provider_dispatch_status_counts": dict(dispatch_status_counts),
        "receipt_reduction_row_count": len(reduction_rows),
        "reduction_status_counts": dict(reduction_status_counts),
        "completion_status": completion_status,
        "expected_recipe_ids": sorted(
            {str(row.get("recipe_id")) for row in transform_jobs if row.get("recipe_id")}
        ),
        "dispatch_attempted_recipe_ids": sorted(
            {str(row.get("recipe_id")) for row in dispatch_rows if row.get("recipe_id")}
        ),
        "reduced_recipe_ids": sorted(
            {str(row.get("recipe_id")) for row in rows if row.get("recipe_id")}
        ),
        "receipt_count": len(rows),
        "provider_counts": dict(Counter(str(row["provider_id"]) for row in rows)),
        "model_counts": dict(Counter(str(row["model_id"]) for row in rows)),
        "lean_accepted_count": sum(1 for row in rows if row["accepted_by_lean"]),
        "recipe_policy_accepted_count": sum(1 for row in rows if row["recipe_policy_passed"]),
        "truth_side_leakage_count": sum(1 for row in rows if row["leakage_status"] != "PASS"),
        "premise_policy_failure_count": sum(1 for row in rows if row["premise_policy_status"] != "PASS"),
        "error_counts": dict(Counter(str(row["error_class"]) for row in rows)),
        "provider_calls_by_reducer": 0,
        "harness_owned_provider_dispatch_added": False,
        "fake_provider_results_counted": 0,
        "open_problem_success_claimed": False,
        "artifact_refs": {
            "provider_receipt_reduction_matrix": _rel(run_root / "provider_receipt_reduction_matrix.json"),
            "recipe_policy_metrics": _rel(run_root / "recipe_policy_metrics.json"),
            "problem_source_comparison": _rel(run_root / "problem_source_comparison.json"),
            "foundry_provider_learning_rows": _rel(run_root / "foundry_provider_learning_rows.json"),
            "provider_cost_latency_usage_report": _rel(run_root / "provider_cost_latency_usage_report.json"),
            "representative_success": _rel(run_root / "representative_success.json"),
            "representative_failure": _rel(run_root / "representative_failure.json"),
            "representative_premise_budget_violation": _rel(
                run_root / "representative_premise_budget_violation.json"
            ),
        },
    }
    payloads = {
        "provider_receipt_reduction_matrix.json": matrix,
        "recipe_policy_metrics.json": recipe_metrics,
        "problem_source_comparison.json": source_comparison,
        "provider_cost_latency_usage_report.json": cost_latency,
        "foundry_provider_learning_rows.json": foundry_rows,
        "representative_success.json": {
            "schema_version": "prover_formal_problem_ladder_representative_case_v0",
            "case_type": "success",
            "row": representative_success,
        },
        "representative_failure.json": {
            "schema_version": "prover_formal_problem_ladder_representative_case_v0",
            "case_type": "proof_failure",
            "row": representative_failure,
        },
        "representative_premise_budget_violation.json": {
            "schema_version": "prover_formal_problem_ladder_representative_case_v0",
            "case_type": "premise_budget_violation",
            "row": representative_policy,
        },
        "formal_problem_ladder_run_summary.json": summary,
    }
    for filename, payload in payloads.items():
        _write_json(run_root / filename, payload)
    _write_json(run_root / "run_summary.json", summary)
    return summary


def _validate(run_root: Path, summary: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    problem_manifest = _read_json(run_root / "problem_source_manifest.json")
    transform_manifest = _read_json(run_root / "transform_job_manifest.json")
    if int(problem_manifest.get("problem_count") or 0) < 20:
        issues.append("formal ladder should include at least 20 Lean-checkable problems")
    if transform_manifest.get("task_class") != harness.PROVER_PROVIDER_TRANSFORM_TASK_CLASS:
        issues.append("transform jobs must use prover_context_hypothesis task class")
    if summary.get("truth_side_leakage_count", 0) != 0:
        issues.append("truth-side leakage count must remain zero")
    if summary.get("fake_provider_results_counted", 0) != 0:
        issues.append("fake provider results must not count as live evidence")
    if summary.get("harness_owned_provider_dispatch_added") is not False:
        issues.append("harness-owned provider dispatch must stay absent")
    return issues


def _load_check_summary(run_root: Path) -> dict[str, Any]:
    for filename in ("formal_problem_ladder_run_summary.json", "run_summary.json"):
        path = run_root / filename
        if path.is_file():
            return _read_json(path)
    raise FileNotFoundError(
        f"missing check summary under {run_root}; expected formal_problem_ladder_run_summary.json or run_summary.json"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--provider", default="nvidia_nim")
    parser.add_argument("--provider-model", default=DEFAULT_PROVIDER_MODEL)
    parser.add_argument("--context-recipes", default=",".join(DEFAULT_RECIPES))
    parser.add_argument("--problem-limit", type=int, default=20)
    parser.add_argument("--dispatch-limit", type=int)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--live-probe", action="store_true")
    parser.add_argument("--compile-jobs", action="store_true")
    parser.add_argument("--dispatch-live", action="store_true")
    parser.add_argument("--resume-rate-limited", action="store_true")
    parser.add_argument("--resume-status", default="429,missing")
    parser.add_argument("--resume-limit", type=int)
    parser.add_argument("--sleep-seconds", type=float, default=5.0)
    parser.add_argument("--max-consecutive-429", type=int, default=3)
    parser.add_argument("--reduce-receipts", action="store_true")
    parser.add_argument("--build-report", action="store_true")
    parser.add_argument("--force-provider", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    run_root = _repo_path(args.run_root)
    actions_selected = any(
        (
            args.compile_jobs,
            args.dispatch_live,
            args.resume_rate_limited,
            args.reduce_receipts,
            args.build_report,
        )
    )
    if args.check and not actions_selected:
        summary = _load_check_summary(run_root)
    elif not actions_selected:
        args.compile_jobs = True
        args.build_report = True
        actions_selected = True
    else:
        summary = {}
    recipes = tuple(
        recipe.strip() for recipe in str(args.context_recipes).split(",") if recipe.strip()
    )
    if actions_selected:
        if args.compile_jobs:
            summary = compile_jobs(
                run_root=run_root,
                provider=args.provider,
                provider_model=args.provider_model,
                live_probe=args.live_probe,
                context_recipes=recipes,
                problem_limit=args.problem_limit,
                timeout_seconds=args.timeout_seconds,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
        if args.dispatch_live:
            summary = dispatch_jobs(
                run_root=run_root,
                provider=args.provider,
                provider_model=args.provider_model,
                limit=args.dispatch_limit,
                force=args.force_provider,
            )
        if args.resume_rate_limited:
            summary = resume_rate_limited_jobs(
                run_root=run_root,
                provider=args.provider,
                provider_model=args.provider_model,
                resume_statuses=args.resume_status,
                limit=args.resume_limit,
                sleep_seconds=args.sleep_seconds,
                max_consecutive_429=args.max_consecutive_429,
            )
        if args.reduce_receipts:
            summary = reduce_dispatched_receipts(
                run_root=run_root,
                timeout_seconds=args.timeout_seconds,
            )
        if args.build_report or (run_root / "reductions").exists():
            if (run_root / "reductions").exists():
                summary = build_report(run_root)
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
            f"{RUN_ID}: problems={summary.get('problem_count')} "
            f"receipts={summary.get('receipt_count', 0)} "
            f"lean={summary.get('lean_accepted_count', 0)} "
            f"recipe={summary.get('recipe_policy_accepted_count', 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
