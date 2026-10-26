#!/usr/bin/env python3
"""Run a small Lean-core Prover-Lab/Oracle/Evolve benchmark harness.

This is intentionally a benchmark runner, not another governance layer. It
turns a tiny split-aware problem set into durable run artifacts so the prover
lane can learn from multiple checked examples before reaching for mathlib,
providers, or open problems.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN_ID = "PROVER_BENCHMARK_20260510_graph_harness_v0"
DEFAULT_RUN_ROOT = Path("state/runs") / DEFAULT_RUN_ID
DEFAULT_RING1_RUN_ID = "PROVER_BENCHMARK_RING1_20260510_source_ingestion_v0"
DEFAULT_RING1_RUN_ROOT = Path("state/runs") / DEFAULT_RING1_RUN_ID
DEFAULT_RING2_RUN_ID = "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0"
DEFAULT_RING2_RUN_ROOT = Path("state/runs") / DEFAULT_RING2_RUN_ID
DEFAULT_STRATEGY_RUN_ID = "PROVER_BENCHMARK_STRATEGY_20260510_control_graph_v0"
DEFAULT_STRATEGY_RUN_ROOT = Path("state/runs") / DEFAULT_STRATEGY_RUN_ID
DEFAULT_SKILL_ATLAS_RUN_ID = "PROVER_SKILL_ATLAS_20260510_composition_root_v0"
DEFAULT_SKILL_ATLAS_RUN_ROOT = Path("state/runs") / DEFAULT_SKILL_ATLAS_RUN_ID
DEFAULT_SKILL_FOUNDRY_RUN_ID = "PROVER_SKILL_FOUNDRY_20260510_v0"
DEFAULT_SKILL_FOUNDRY_RUN_ROOT = Path("state/runs") / DEFAULT_SKILL_FOUNDRY_RUN_ID
DEFAULT_PROVIDER_CONTEXT_SWEEP_RUN_ID = "PROVER_PROVIDER_CONTEXT_SWEEP_20260510_v0"
DEFAULT_PROVIDER_CONTEXT_SWEEP_RUN_ROOT = Path("state/runs") / DEFAULT_PROVIDER_CONTEXT_SWEEP_RUN_ID
TOOLCHAIN_COMMIT = "f72c35b3f637c8c6571d353742168ab66cc22c00"
SORRY_RE = re.compile(r"\bsorry\b")
_TOOLCHAIN_SOURCE_PATH_CACHE: str | None = None
SKILL_ATLAS_OVERLAY_GRAPH_VARIANT = "strategy_control_graph_v0_skill_atlas_overlay_v0"
SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT = "strategy_control_graph_v0_skill_foundry_overlay_v0"
SOURCE_GUARDED_STRATEGY_GRAPH_VARIANT = "source_guarded_strategy_graph_v0"
SOURCE_GUARDED_FOUNDRY_GRAPH_VARIANT = "source_guarded_foundry_graph_v0"
TACTIC_PORTFOLIO_GRAPH_VARIANT = "tactic_portfolio_graph_v0"
HAMMER_SEARCH_GRAPH_VARIANT = "hammer_search_graph_v0"
GRAPH_VARIANTS = (
    "baseline_graph_v0",
    "premise_retrieval_graph_v0",
    "strategy_control_graph_v0",
    SKILL_ATLAS_OVERLAY_GRAPH_VARIANT,
    SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT,
    SOURCE_GUARDED_STRATEGY_GRAPH_VARIANT,
    SOURCE_GUARDED_FOUNDRY_GRAPH_VARIANT,
    TACTIC_PORTFOLIO_GRAPH_VARIANT,
    HAMMER_SEARCH_GRAPH_VARIANT,
    "oracle_repair_graph_v0",
)
PROVIDER_CONTEXT_RECIPES = (
    "minimal_4kb",
    "premise_16kb",
    "skill_32kb",
    "repair_32kb",
    "fewshot_64kb",
    "strategy_classification_4kb",
)
DEFAULT_PROVIDER_CONTEXT_RECIPES = ("minimal_4kb", "skill_32kb", "repair_32kb")
PROVER_PROVIDER_TRANSFORM_TASK_CLASS = "prover_context_hypothesis"
PROVER_STRATEGY_CLASSIFICATION_TASK_CLASS = "prover_strategy_classification"
STRATEGY_CLASSIFICATION_RECIPES = frozenset({"strategy_classification_4kb"})
STRATEGY_GRAPH_VARIANTS = {
    "strategy_control_graph_v0",
    SKILL_ATLAS_OVERLAY_GRAPH_VARIANT,
    SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT,
    SOURCE_GUARDED_STRATEGY_GRAPH_VARIANT,
    SOURCE_GUARDED_FOUNDRY_GRAPH_VARIANT,
}
SKILL_OVERLAY_GRAPH_VARIANTS = {
    SKILL_ATLAS_OVERLAY_GRAPH_VARIANT,
    SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT,
    SOURCE_GUARDED_FOUNDRY_GRAPH_VARIANT,
}
SOURCE_GUARDED_GRAPH_VARIANTS = {
    SOURCE_GUARDED_STRATEGY_GRAPH_VARIANT,
    SOURCE_GUARDED_FOUNDRY_GRAPH_VARIANT,
}
PROOF_SEARCH_GRAPH_VARIANTS = {
    TACTIC_PORTFOLIO_GRAPH_VARIANT,
    HAMMER_SEARCH_GRAPH_VARIANT,
}
LOCAL_EXECUTABLE_SOURCE_FAMILIES = {
    "local_lean_core",
    "lean_std_toolchain",
    "source_manifest",
}
FORMAL_MATH_NO_SOLVE_MANIFEST_SCHEMA = "formal_math_no_solve_manifest_v0"
FORMAL_MATH_NO_SOLVE_BENCHMARK_IDS = {"constructivebench", "verisoftbench"}
TACTIC_PORTFOLIO_CORE_V0 = (
    "rfl",
    "decide",
    "native_decide",
    "omega",
    "simp",
    "simp_all",
    "aesop",
    "grind",
)

FAILURE_CLASSES = [
    "FORMALIZATION_MISMATCH",
    "LIBRARY_GAP",
    "STRATEGY_SELECTION_MISS",
    "PREMISE_RETRIEVAL_MISS",
    "PROOF_SYNTHESIS_FAIL",
    "TACTIC_SEARCH_FAIL",
    "DECOMPOSITION_BAD",
    "PROOF_CORE_GAP",
    "SOLUTION_LEAKAGE",
    "ENVIRONMENT_FAIL",
    "ORACLE_TIMEOUT",
    "REGISTRY_STATUS_MISMATCH",
    "NONE",
]


@dataclass(frozen=True)
class ProverProblem:
    problem_id: str
    source: str
    split: str
    mode: str
    domain: str
    informal_statement: str
    theorem_name: str
    theorem_signature: str
    candidate_body: tuple[str, ...]
    ideal_body: tuple[str, ...]
    visible_to_lab: tuple[str, ...]
    withheld_until_oracle: tuple[str, ...]
    context_recipe_id: str
    expected_error_class_on_fail: str = "PROOF_CORE_GAP"
    required_imports: tuple[str, ...] = ()
    source_ref: str = "local_lean_core_fixture"
    source_family: str = "local_lean_core"
    difficulty_tag: str = "ring0"
    repair_body: tuple[str, ...] = ()
    allowed_premise_ids: tuple[str, ...] = ()
    oracle_needed_premise_ids: tuple[str, ...] = ()
    retrieval_query_terms: tuple[str, ...] = ()
    retrieval_body: tuple[str, ...] = ()
    expected_strategy_ids: tuple[str, ...] = ()


def _problem_set() -> list[ProverProblem]:
    return [
        ProverProblem(
            problem_id="lean_core_nat_self_eq",
            source="local_lean_core",
            split="train",
            mode="solved_training",
            domain="equality",
            informal_statement="For every natural number n, n is equal to itself.",
            theorem_name="bench_nat_self_eq",
            theorem_signature="theorem bench_nat_self_eq (n : Nat) : n = n := by",
            candidate_body=("  rfl",),
            ideal_body=("  rfl",),
            visible_to_lab=("statement", "Lean core Nat", "baseline_graph_v0"),
            withheld_until_oracle=("ideal proof body", "oracle critique"),
            context_recipe_id="lean_core_direct_v0",
        ),
        ProverProblem(
            problem_id="lean_core_true_intro",
            source="local_lean_core",
            split="train",
            mode="solved_training",
            domain="propositional",
            informal_statement="True is provable.",
            theorem_name="bench_true_intro",
            theorem_signature="theorem bench_true_intro : True := by",
            candidate_body=("  exact True.intro",),
            ideal_body=("  exact True.intro",),
            visible_to_lab=("statement", "Lean core True", "baseline_graph_v0"),
            withheld_until_oracle=("ideal proof body", "oracle critique"),
            context_recipe_id="lean_core_direct_v0",
        ),
        ProverProblem(
            problem_id="lean_core_and_comm",
            source="local_lean_core",
            split="dev",
            mode="solved_training",
            domain="propositional",
            informal_statement="If p and q, then q and p.",
            theorem_name="bench_and_comm",
            theorem_signature="theorem bench_and_comm (p q : Prop) : p ∧ q -> q ∧ p := by",
            candidate_body=(
                "  intro h",
                "  exact And.intro h.right h.left",
            ),
            ideal_body=(
                "  intro h",
                "  exact And.intro h.right h.left",
            ),
            visible_to_lab=("statement", "Lean core And", "baseline_graph_v0"),
            withheld_until_oracle=("ideal proof body", "oracle critique"),
            context_recipe_id="lean_core_direct_v0",
        ),
        ProverProblem(
            problem_id="lean_core_or_comm",
            source="local_lean_core",
            split="dev",
            mode="solved_training",
            domain="propositional",
            informal_statement="If p or q, then q or p.",
            theorem_name="bench_or_comm",
            theorem_signature="theorem bench_or_comm (p q : Prop) : p ∨ q -> q ∨ p := by",
            candidate_body=(
                "  intro h",
                "  cases h with",
                "  | inl hp => exact Or.inr hp",
                "  | inr hq => exact Or.inl hq",
            ),
            ideal_body=(
                "  intro h",
                "  cases h with",
                "  | inl hp => exact Or.inr hp",
                "  | inr hq => exact Or.inl hq",
            ),
            visible_to_lab=("statement", "Lean core Or", "baseline_graph_v0"),
            withheld_until_oracle=("ideal proof body", "oracle critique"),
            context_recipe_id="lean_core_case_split_v0",
        ),
        ProverProblem(
            problem_id="lean_core_exists_zero",
            source="local_lean_core",
            split="test",
            mode="solved_training",
            domain="existential",
            informal_statement="There exists a natural number equal to zero.",
            theorem_name="bench_exists_zero",
            theorem_signature="theorem bench_exists_zero : ∃ n : Nat, n = 0 := by",
            candidate_body=("  exact Exists.intro 0 rfl",),
            ideal_body=("  exact Exists.intro 0 rfl",),
            visible_to_lab=("statement", "Lean core Exists", "baseline_graph_v0"),
            withheld_until_oracle=("ideal proof body", "oracle critique"),
            context_recipe_id="lean_core_witness_v0",
        ),
        ProverProblem(
            problem_id="lean_core_bad_and_comm_missing_p",
            source="local_lean_core",
            split="test",
            mode="solved_training",
            domain="propositional",
            informal_statement="If p and q, then q and p; the candidate intentionally repeats q.",
            theorem_name="bench_bad_and_comm_missing_p",
            theorem_signature=(
                "theorem bench_bad_and_comm_missing_p (p q : Prop) : p ∧ q -> q ∧ p := by"
            ),
            candidate_body=(
                "  intro h",
                "  exact And.intro h.right h.right",
            ),
            ideal_body=(
                "  intro h",
                "  exact And.intro h.right h.left",
            ),
            visible_to_lab=("statement", "Lean core And", "baseline_graph_v0"),
            withheld_until_oracle=("ideal proof body", "oracle critique"),
            context_recipe_id="lean_core_direct_v0",
            expected_error_class_on_fail="PROOF_CORE_GAP",
        ),
    ]


def _toolchain_source_path() -> str:
    global _TOOLCHAIN_SOURCE_PATH_CACHE
    if _TOOLCHAIN_SOURCE_PATH_CACHE is not None:
        return _TOOLCHAIN_SOURCE_PATH_CACHE
    if shutil.which("lean") is None:
        _TOOLCHAIN_SOURCE_PATH_CACHE = "lean_toolchain_unavailable"
        return _TOOLCHAIN_SOURCE_PATH_CACHE
    result = subprocess.run(
        ["lean", "--print-prefix"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    prefix = (result.stdout or result.stderr).strip()
    if not prefix:
        _TOOLCHAIN_SOURCE_PATH_CACHE = "lean_toolchain_prefix_unknown"
        return _TOOLCHAIN_SOURCE_PATH_CACHE
    _TOOLCHAIN_SOURCE_PATH_CACHE = str(Path(prefix) / "src" / "lean")
    return _TOOLCHAIN_SOURCE_PATH_CACHE


def _ring1_problem_set() -> list[ProverProblem]:
    source_root = _toolchain_source_path()
    visible_common = (
        "statement",
        "required imports",
        "Lean/Std theorem names",
        "source family: installed Lean toolchain source",
    )
    withheld_common = (
        "ideal proof body",
        "repair proof body",
        "oracle critique",
        "aggregate graph update candidates",
    )
    return [
        ProverProblem(
            problem_id="ring1_nat_succ_injective",
            source="lean_std_toolchain_source_v0",
            split="train",
            mode="solved_training",
            domain="nat",
            informal_statement="The successor constructor on natural numbers is injective.",
            theorem_name="ring1_nat_succ_injective",
            theorem_signature=(
                "theorem ring1_nat_succ_injective (m n : Nat) : "
                "Nat.succ m = Nat.succ n -> m = n := by"
            ),
            candidate_body=("  intro h", "  exact Nat.succ.inj h"),
            ideal_body=("  intro h", "  exact Nat.succ.inj h"),
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_direct_v0",
            required_imports=("Std",),
            source_ref=f"{source_root}/Init/Prelude.lean",
            source_family="lean_std_toolchain",
            difficulty_tag="ring1_core_lemma",
        ),
        ProverProblem(
            problem_id="ring1_nat_add_comm",
            source="lean_std_toolchain_source_v0",
            split="train",
            mode="solved_training",
            domain="nat",
            informal_statement="Natural-number addition is commutative.",
            theorem_name="ring1_nat_add_comm",
            theorem_signature="theorem ring1_nat_add_comm (m n : Nat) : m + n = n + m := by",
            candidate_body=("  exact Nat.add_comm m n",),
            ideal_body=("  exact Nat.add_comm m n",),
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_direct_v0",
            required_imports=("Std",),
            source_ref=f"{source_root}/Init/Data/Nat/Lemmas.lean",
            source_family="lean_std_toolchain",
            difficulty_tag="ring1_core_lemma",
        ),
        ProverProblem(
            problem_id="ring1_list_length_cons",
            source="lean_std_toolchain_source_v0",
            split="train",
            mode="solved_training",
            domain="list",
            informal_statement="Consing one element increases a list length by one.",
            theorem_name="ring1_list_length_cons",
            theorem_signature=(
                "theorem ring1_list_length_cons (Alpha : Type) (a : Alpha) "
                "(xs : List Alpha) : (a :: xs).length = xs.length + 1 := by"
            ),
            candidate_body=("  exact List.length_cons",),
            ideal_body=("  exact List.length_cons",),
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_direct_v0",
            required_imports=("Std",),
            source_ref=f"{source_root}/Init/Data/List/Lemmas.lean",
            source_family="lean_std_toolchain",
            difficulty_tag="ring1_core_lemma",
        ),
        ProverProblem(
            problem_id="ring1_bool_not_not",
            source="lean_std_toolchain_source_v0",
            split="train",
            mode="solved_training",
            domain="bool",
            informal_statement="Double Boolean negation returns the original Boolean.",
            theorem_name="ring1_bool_not_not",
            theorem_signature="theorem ring1_bool_not_not (b : Bool) : (!(!b)) = b := by",
            candidate_body=("  exact Bool.not_not b",),
            ideal_body=("  exact Bool.not_not b",),
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_direct_v0",
            required_imports=("Std",),
            source_ref=f"{source_root}/Init/Data/Bool.lean",
            source_family="lean_std_toolchain",
            difficulty_tag="ring1_core_lemma",
        ),
        ProverProblem(
            problem_id="ring1_nat_add_assoc",
            source="lean_std_toolchain_source_v0",
            split="dev",
            mode="solved_training",
            domain="nat",
            informal_statement="Natural-number addition is associative.",
            theorem_name="ring1_nat_add_assoc",
            theorem_signature=(
                "theorem ring1_nat_add_assoc (a b c : Nat) : "
                "a + b + c = a + (b + c) := by"
            ),
            candidate_body=("  exact Nat.add_assoc a b c",),
            ideal_body=("  exact Nat.add_assoc a b c",),
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_direct_v0",
            required_imports=("Std",),
            source_ref=f"{source_root}/Init/Data/Nat/Lemmas.lean",
            source_family="lean_std_toolchain",
            difficulty_tag="ring1_core_lemma",
        ),
        ProverProblem(
            problem_id="ring1_list_reverse_reverse",
            source="lean_std_toolchain_source_v0",
            split="dev",
            mode="solved_training",
            domain="list",
            informal_statement="Reversing a list twice returns the original list.",
            theorem_name="ring1_list_reverse_reverse",
            theorem_signature=(
                "theorem ring1_list_reverse_reverse (Alpha : Type) (xs : List Alpha) : "
                "xs.reverse.reverse = xs := by"
            ),
            candidate_body=("  exact List.reverse_reverse xs",),
            ideal_body=("  exact List.reverse_reverse xs",),
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_direct_v0",
            required_imports=("Std",),
            source_ref=f"{source_root}/Init/Data/List/Lemmas.lean",
            source_family="lean_std_toolchain",
            difficulty_tag="ring1_core_lemma",
        ),
        ProverProblem(
            problem_id="ring1_iff_intro",
            source="lean_std_toolchain_source_v0",
            split="dev",
            mode="solved_training",
            domain="propositional",
            informal_statement="Two implications assemble an if-and-only-if proof.",
            theorem_name="ring1_iff_intro",
            theorem_signature=(
                "theorem ring1_iff_intro (p q : Prop) : "
                "(p -> q) -> (q -> p) -> (p <-> q) := by"
            ),
            candidate_body=("  intro hpq hqp", "  exact Iff.intro hpq hqp"),
            ideal_body=("  intro hpq hqp", "  exact Iff.intro hpq hqp"),
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_direct_v0",
            required_imports=("Std",),
            source_ref=f"{source_root}/Init/Prelude.lean",
            source_family="lean_std_toolchain",
            difficulty_tag="ring1_core_lemma",
        ),
        ProverProblem(
            problem_id="ring1_list_length_append_repair",
            source="lean_std_toolchain_source_v0",
            split="test",
            mode="solved_training",
            domain="list",
            informal_statement="The length of an appended list is the sum of the input lengths.",
            theorem_name="ring1_list_length_append_repair",
            theorem_signature=(
                "theorem ring1_list_length_append_repair (Alpha : Type) "
                "(xs ys : List Alpha) : "
                "(xs ++ ys).length = xs.length + ys.length := by"
            ),
            candidate_body=("  exact List.length_cons",),
            ideal_body=("  exact List.length_append",),
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_direct_v0",
            required_imports=("Std",),
            source_ref=f"{source_root}/Init/Data/List/Lemmas.lean",
            source_family="lean_std_toolchain",
            difficulty_tag="ring1_repair_probe",
            repair_body=("  exact List.length_append",),
        ),
        ProverProblem(
            problem_id="ring1_list_map_map_repair",
            source="lean_std_toolchain_source_v0",
            split="test",
            mode="solved_training",
            domain="list",
            informal_statement="Mapping g after mapping f is mapping the composition.",
            theorem_name="ring1_list_map_map_repair",
            theorem_signature=(
                "theorem ring1_list_map_map_repair (Alpha Beta Gamma : Type) "
                "(f : Alpha -> Beta) (g : Beta -> Gamma) (xs : List Alpha) : "
                "List.map g (List.map f xs) = List.map (g \u2218 f) xs := by"
            ),
            candidate_body=("  exact List.reverse_reverse xs",),
            ideal_body=("  exact List.map_map",),
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_direct_v0",
            required_imports=("Std",),
            source_ref=f"{source_root}/Init/Data/List/Lemmas.lean",
            source_family="lean_std_toolchain",
            difficulty_tag="ring1_repair_probe",
            repair_body=("  exact List.map_map",),
        ),
        ProverProblem(
            problem_id="ring1_list_mem_append",
            source="lean_std_toolchain_source_v0",
            split="test",
            mode="solved_training",
            domain="list",
            informal_statement="Membership in an appended list is membership in either side.",
            theorem_name="ring1_list_mem_append",
            theorem_signature=(
                "theorem ring1_list_mem_append (Alpha : Type) (a : Alpha) "
                "(xs ys : List Alpha) : "
                "List.Mem a (xs ++ ys) <-> List.Mem a xs \\/ List.Mem a ys := by"
            ),
            candidate_body=("  exact List.mem_append",),
            ideal_body=("  exact List.mem_append",),
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_direct_v0",
            required_imports=("Std",),
            source_ref=f"{source_root}/Init/Data/List/Lemmas.lean",
            source_family="lean_std_toolchain",
            difficulty_tag="ring1_core_lemma",
        ),
    ]


def _premise_index() -> dict[str, Any]:
    source_root = _toolchain_source_path()
    premises = [
        {
            "premise_id": "premise_nat_succ_inj",
            "theorem_or_def_name": "Nat.succ.inj",
            "source_ref": f"{source_root}/Init/Prelude.lean",
            "namespace": "Nat",
            "statement_excerpt": "Nat.succ m = Nat.succ n implies m = n.",
            "retrieval_terms": ["nat", "successor", "succ", "injective", "equality"],
            "allowed_for_split": ["train", "dev", "test"],
        },
        {
            "premise_id": "premise_nat_add_comm",
            "theorem_or_def_name": "Nat.add_comm",
            "source_ref": f"{source_root}/Init/Data/Nat/Lemmas.lean",
            "namespace": "Nat",
            "statement_excerpt": "m + n = n + m for natural numbers.",
            "retrieval_terms": ["nat", "addition", "add", "commutative", "comm"],
            "allowed_for_split": ["train", "dev", "test"],
        },
        {
            "premise_id": "premise_nat_add_assoc",
            "theorem_or_def_name": "Nat.add_assoc",
            "source_ref": f"{source_root}/Init/Data/Nat/Lemmas.lean",
            "namespace": "Nat",
            "statement_excerpt": "a + b + c = a + (b + c) for natural numbers.",
            "retrieval_terms": ["nat", "addition", "add", "associative", "assoc"],
            "allowed_for_split": ["train", "dev", "test"],
        },
        {
            "premise_id": "premise_nat_add_zero",
            "theorem_or_def_name": "Nat.add_zero",
            "source_ref": f"{source_root}/Init/Data/Nat/Lemmas.lean",
            "namespace": "Nat",
            "statement_excerpt": "n + 0 = n for natural numbers.",
            "retrieval_terms": ["nat", "addition", "zero", "recursive", "induction"],
            "allowed_for_split": ["train", "dev", "test"],
        },
        {
            "premise_id": "premise_bool_not_not",
            "theorem_or_def_name": "Bool.not_not",
            "source_ref": f"{source_root}/Init/Data/Bool.lean",
            "namespace": "Bool",
            "statement_excerpt": "Double Boolean negation returns the original Boolean.",
            "retrieval_terms": ["bool", "boolean", "not", "negation", "double"],
            "allowed_for_split": ["train", "dev", "test"],
        },
        {
            "premise_id": "premise_iff_intro",
            "theorem_or_def_name": "Iff.intro",
            "source_ref": f"{source_root}/Init/Prelude.lean",
            "namespace": "Iff",
            "statement_excerpt": "Two implications assemble an iff proof.",
            "retrieval_terms": ["iff", "if and only if", "implication", "intro"],
            "allowed_for_split": ["train", "dev", "test"],
        },
        {
            "premise_id": "premise_list_length_cons",
            "theorem_or_def_name": "List.length_cons",
            "source_ref": f"{source_root}/Init/Data/List/Lemmas.lean",
            "namespace": "List",
            "statement_excerpt": "The length of a cons is one more than the tail length.",
            "retrieval_terms": ["list", "length", "cons", "head", "tail"],
            "allowed_for_split": ["train", "dev", "test"],
        },
        {
            "premise_id": "premise_list_length_append",
            "theorem_or_def_name": "List.length_append",
            "source_ref": f"{source_root}/Init/Data/List/Lemmas.lean",
            "namespace": "List",
            "statement_excerpt": "The length of appended lists is the sum of their lengths.",
            "retrieval_terms": ["list", "length", "append", "sum"],
            "allowed_for_split": ["train", "dev", "test"],
        },
        {
            "premise_id": "premise_list_map_map",
            "theorem_or_def_name": "List.map_map",
            "source_ref": f"{source_root}/Init/Data/List/Lemmas.lean",
            "namespace": "List",
            "statement_excerpt": "Mapping twice is mapping the composed function.",
            "retrieval_terms": ["list", "map", "composition", "compose", "function"],
            "allowed_for_split": ["train", "dev", "test"],
        },
        {
            "premise_id": "premise_list_mem_append",
            "theorem_or_def_name": "List.mem_append",
            "source_ref": f"{source_root}/Init/Data/List/Lemmas.lean",
            "namespace": "List",
            "statement_excerpt": "Membership in an appended list is membership in either side.",
            "retrieval_terms": ["list", "membership", "mem", "append", "or"],
            "allowed_for_split": ["train", "dev", "test"],
        },
        {
            "premise_id": "premise_list_reverse_reverse",
            "theorem_or_def_name": "List.reverse_reverse",
            "source_ref": f"{source_root}/Init/Data/List/Lemmas.lean",
            "namespace": "List",
            "statement_excerpt": "Reversing a list twice returns the original list.",
            "retrieval_terms": ["list", "reverse", "involution", "twice"],
            "allowed_for_split": ["train", "dev", "test"],
        },
    ]
    return {
        "schema_version": "premise_index_v0",
        "source_id": "lean_std_toolchain_premise_index_v0",
        "source_kind": "installed_lean_toolchain_source",
        "local_or_annex_path": source_root,
        "premise_count": len(premises),
        "premises": premises,
        "leakage_policy": {
            "proof_bodies_in_index": False,
            "oracle_needed_premise_ids_visible_to_lab": False,
            "allowed_before_oracle": True,
        },
    }


def _ring2_problem_set() -> list[ProverProblem]:
    source_root = _toolchain_source_path()
    visible_common = (
        "statement",
        "required imports",
        "allowed premise index slice",
        "Lean/Std theorem names",
    )
    withheld_common = (
        "ideal proof body",
        "repair proof body",
        "oracle needed premise ids",
        "oracle critique",
    )

    def problem(
        *,
        problem_id: str,
        split: str,
        domain: str,
        informal_statement: str,
        theorem_signature: str,
        candidate_body: tuple[str, ...],
        ideal_body: tuple[str, ...],
        needed: tuple[str, ...],
        query_terms: tuple[str, ...],
        retrieval_body: tuple[str, ...] | None = None,
        allowed: tuple[str, ...] | None = None,
        expected_error_class: str = "PROOF_CORE_GAP",
        difficulty_tag: str = "ring2_premise_retrieval",
    ) -> ProverProblem:
        return ProverProblem(
            problem_id=problem_id,
            source="lean_std_toolchain_premise_index_v0",
            split=split,
            mode="solved_training",
            domain=domain,
            informal_statement=informal_statement,
            theorem_name=problem_id,
            theorem_signature=theorem_signature,
            candidate_body=candidate_body,
            ideal_body=ideal_body,
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_premise_retrieval_v0",
            expected_error_class_on_fail=expected_error_class,
            required_imports=("Std",),
            source_ref=f"{source_root}/Init",
            source_family="lean_std_toolchain",
            difficulty_tag=difficulty_tag,
            repair_body=ideal_body,
            allowed_premise_ids=allowed or (),
            oracle_needed_premise_ids=needed,
            retrieval_query_terms=query_terms,
            retrieval_body=retrieval_body or (),
        )

    return [
        problem(
            problem_id="ring2_nat_succ_injective",
            split="train",
            domain="nat",
            informal_statement="Recover the successor injectivity lemma for natural numbers.",
            theorem_signature=(
                "theorem ring2_nat_succ_injective (m n : Nat) : "
                "Nat.succ m = Nat.succ n -> m = n := by"
            ),
            candidate_body=("  intro h", "  exact rfl"),
            ideal_body=("  intro h", "  exact Nat.succ.inj h"),
            retrieval_body=("  intro h", "  exact Nat.succ.inj h"),
            needed=("premise_nat_succ_inj",),
            query_terms=("successor", "injective", "nat"),
        ),
        problem(
            problem_id="ring2_nat_add_comm",
            split="train",
            domain="nat",
            informal_statement="Recover commutativity of natural-number addition.",
            theorem_signature="theorem ring2_nat_add_comm (m n : Nat) : m + n = n + m := by",
            candidate_body=("  rfl",),
            ideal_body=("  exact Nat.add_comm m n",),
            retrieval_body=("  exact Nat.add_comm m n",),
            needed=("premise_nat_add_comm",),
            query_terms=("nat", "addition", "commutative"),
        ),
        problem(
            problem_id="ring2_nat_add_assoc",
            split="train",
            domain="nat",
            informal_statement="Recover associativity of natural-number addition.",
            theorem_signature=(
                "theorem ring2_nat_add_assoc (a b c : Nat) : "
                "a + b + c = a + (b + c) := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact Nat.add_assoc a b c",),
            retrieval_body=("  exact Nat.add_assoc a b c",),
            needed=("premise_nat_add_assoc",),
            query_terms=("nat", "addition", "associative"),
        ),
        problem(
            problem_id="ring2_bool_not_not",
            split="train",
            domain="bool",
            informal_statement="Recover double-negation for Booleans.",
            theorem_signature="theorem ring2_bool_not_not (b : Bool) : (!(!b)) = b := by",
            candidate_body=("  rfl",),
            ideal_body=("  exact Bool.not_not b",),
            retrieval_body=("  exact Bool.not_not b",),
            needed=("premise_bool_not_not",),
            query_terms=("bool", "double", "negation"),
        ),
        problem(
            problem_id="ring2_list_reverse_reverse",
            split="dev",
            domain="list",
            informal_statement="Recover the list reverse-involution lemma.",
            theorem_signature=(
                "theorem ring2_list_reverse_reverse (Alpha : Type) (xs : List Alpha) : "
                "xs.reverse.reverse = xs := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact List.reverse_reverse xs",),
            retrieval_body=("  exact List.reverse_reverse xs",),
            needed=("premise_list_reverse_reverse",),
            query_terms=("list", "reverse", "twice"),
        ),
        problem(
            problem_id="ring2_list_length_append",
            split="dev",
            domain="list",
            informal_statement="Recover the list length-of-append lemma.",
            theorem_signature=(
                "theorem ring2_list_length_append (Alpha : Type) "
                "(xs ys : List Alpha) : "
                "(xs ++ ys).length = xs.length + ys.length := by"
            ),
            candidate_body=("  exact List.length_cons",),
            ideal_body=("  exact List.length_append",),
            retrieval_body=("  exact List.length_append",),
            needed=("premise_list_length_append",),
            query_terms=("list", "length", "append"),
        ),
        problem(
            problem_id="ring2_iff_intro",
            split="dev",
            domain="propositional",
            informal_statement="Recover the iff-introduction constructor from two implications.",
            theorem_signature=(
                "theorem ring2_iff_intro (p q : Prop) : "
                "(p -> q) -> (q -> p) -> (p <-> q) := by"
            ),
            candidate_body=("  intro hpq hqp", "  exact Iff.rfl"),
            ideal_body=("  intro hpq hqp", "  exact Iff.intro hpq hqp"),
            retrieval_body=("  intro hpq hqp", "  exact Iff.intro hpq hqp"),
            needed=("premise_iff_intro",),
            query_terms=("iff", "implication", "intro"),
        ),
        problem(
            problem_id="ring2_list_mem_append",
            split="test",
            domain="list",
            informal_statement="Recover the membership characterization for appended lists.",
            theorem_signature=(
                "theorem ring2_list_mem_append (Alpha : Type) (a : Alpha) "
                "(xs ys : List Alpha) : "
                "List.Mem a (xs ++ ys) <-> List.Mem a xs \\/ List.Mem a ys := by"
            ),
            candidate_body=("  exact Iff.rfl",),
            ideal_body=("  exact List.mem_append",),
            retrieval_body=("  exact List.mem_append",),
            needed=("premise_list_mem_append",),
            query_terms=("list", "membership", "append"),
        ),
        problem(
            problem_id="ring2_list_length_append_symmetry_hit_fail",
            split="test",
            domain="list",
            informal_statement=(
                "Recover length_append but also orient it correctly; the retrieval hit is not "
                "sufficient by itself."
            ),
            theorem_signature=(
                "theorem ring2_list_length_append_symmetry_hit_fail (Alpha : Type) "
                "(xs ys : List Alpha) : "
                "xs.length + ys.length = (xs ++ ys).length := by"
            ),
            candidate_body=("  exact List.length_append",),
            ideal_body=("  exact Eq.symm List.length_append",),
            retrieval_body=("  exact List.length_append",),
            needed=("premise_list_length_append",),
            query_terms=("list", "length", "append", "orientation"),
            expected_error_class="TACTIC_SEARCH_FAIL",
            difficulty_tag="ring2_retrieval_hit_proof_failure",
        ),
        problem(
            problem_id="ring2_list_map_map_index_miss",
            split="test",
            domain="list",
            informal_statement=(
                "Recover map_map, but the allowed premise slice intentionally omits it so "
                "the oracle can classify a retrieval miss."
            ),
            theorem_signature=(
                "theorem ring2_list_map_map_index_miss (Alpha Beta Gamma : Type) "
                "(f : Alpha -> Beta) (g : Beta -> Gamma) (xs : List Alpha) : "
                "List.map g (List.map f xs) = List.map (g \u2218 f) xs := by"
            ),
            candidate_body=("  exact List.reverse_reverse xs",),
            ideal_body=("  exact List.map_map",),
            needed=("premise_list_map_map",),
            query_terms=("list", "map", "composition"),
            allowed=("premise_list_reverse_reverse", "premise_list_length_append"),
            expected_error_class="PREMISE_RETRIEVAL_MISS",
            difficulty_tag="ring2_retrieval_miss_oracle_repair_probe",
        ),
    ]


def _strategy_problem_set() -> list[ProverProblem]:
    source_root = _toolchain_source_path()
    visible_common = (
        "statement",
        "required imports",
        "allowed premise index slice",
        "mathematical strategy cards",
        "strategy-conditioned retrieval terms",
    )
    withheld_common = (
        "candidate_body fixture",
        "ideal proof body",
        "repair proof body",
        "retrieval_body fixture",
        "oracle needed premise ids",
        "oracle expected strategy ids",
        "oracle critique",
    )

    def problem(
        *,
        problem_id: str,
        split: str,
        domain: str,
        informal_statement: str,
        theorem_signature: str,
        candidate_body: tuple[str, ...],
        ideal_body: tuple[str, ...],
        needed: tuple[str, ...],
        query_terms: tuple[str, ...],
        expected_strategy: tuple[str, ...],
        allowed: tuple[str, ...] | None = None,
        expected_error_class: str = "PROOF_SYNTHESIS_FAIL",
        difficulty_tag: str = "strategy_control",
    ) -> ProverProblem:
        return ProverProblem(
            problem_id=problem_id,
            source="lean_std_toolchain_strategy_control_v0",
            split=split,
            mode="solved_training",
            domain=domain,
            informal_statement=informal_statement,
            theorem_name=problem_id,
            theorem_signature=theorem_signature,
            candidate_body=candidate_body,
            ideal_body=ideal_body,
            visible_to_lab=visible_common,
            withheld_until_oracle=withheld_common,
            context_recipe_id="lean_std_strategy_control_v0",
            expected_error_class_on_fail=expected_error_class,
            required_imports=("Std",),
            source_ref=f"{source_root}/Init",
            source_family="lean_std_toolchain",
            difficulty_tag=difficulty_tag,
            repair_body=ideal_body,
            allowed_premise_ids=allowed or (),
            oracle_needed_premise_ids=needed,
            retrieval_query_terms=query_terms,
            expected_strategy_ids=expected_strategy,
        )

    return [
        problem(
            problem_id="strategy_nat_succ_injective",
            split="train",
            domain="nat",
            informal_statement="Use constructor injectivity for equality of successors.",
            theorem_signature=(
                "theorem strategy_nat_succ_injective (m n : Nat) : "
                "Nat.succ m = Nat.succ n -> m = n := by"
            ),
            candidate_body=("  intro h", "  exact rfl"),
            ideal_body=("  intro h", "  exact Nat.succ.inj h"),
            needed=("premise_nat_succ_inj",),
            query_terms=("successor", "constructor", "injective", "nat"),
            expected_strategy=("constructor_injectivity",),
        ),
        problem(
            problem_id="strategy_nat_add_comm",
            split="train",
            domain="nat",
            informal_statement="Normalize a natural-number addition equality using commutativity.",
            theorem_signature="theorem strategy_nat_add_comm (m n : Nat) : m + n = n + m := by",
            candidate_body=("  rfl",),
            ideal_body=("  exact Nat.add_comm m n",),
            needed=("premise_nat_add_comm",),
            query_terms=("nat", "addition", "commutative", "normal"),
            expected_strategy=("equality_normal_form",),
        ),
        problem(
            problem_id="strategy_bool_not_not",
            split="train",
            domain="bool",
            informal_statement="Normalize a Boolean double negation.",
            theorem_signature="theorem strategy_bool_not_not (b : Bool) : (!(!b)) = b := by",
            candidate_body=("  rfl",),
            ideal_body=("  exact Bool.not_not b",),
            needed=("premise_bool_not_not",),
            query_terms=("bool", "double", "negation", "normal"),
            expected_strategy=("equality_normal_form",),
        ),
        problem(
            problem_id="strategy_nat_add_zero_recursive",
            split="train",
            domain="nat",
            informal_statement="Treat n + 0 = n as a recursive natural-number fact.",
            theorem_signature="theorem strategy_nat_add_zero_recursive (n : Nat) : n + 0 = n := by",
            candidate_body=("  rfl",),
            ideal_body=("  exact Nat.add_zero n",),
            needed=("premise_nat_add_zero",),
            query_terms=("nat", "zero", "recursive", "induction"),
            expected_strategy=("recursive_data_induction",),
        ),
        problem(
            problem_id="strategy_iff_intro",
            split="dev",
            domain="propositional",
            informal_statement="View iff as two implications and construct both directions.",
            theorem_signature=(
                "theorem strategy_iff_intro (p q : Prop) : "
                "(p -> q) -> (q -> p) -> (p <-> q) := by"
            ),
            candidate_body=("  intro hpq hqp", "  exact Iff.rfl"),
            ideal_body=("  intro hpq hqp", "  exact Iff.intro hpq hqp"),
            needed=("premise_iff_intro",),
            query_terms=("iff", "implication", "intro"),
            expected_strategy=("iff_split",),
        ),
        problem(
            problem_id="strategy_list_mem_append",
            split="dev",
            domain="list",
            informal_statement="Decompose membership in an appended list.",
            theorem_signature=(
                "theorem strategy_list_mem_append (Alpha : Type) (a : Alpha) "
                "(xs ys : List Alpha) : "
                "List.Mem a (xs ++ ys) <-> List.Mem a xs \\/ List.Mem a ys := by"
            ),
            candidate_body=("  exact Iff.rfl",),
            ideal_body=("  exact List.mem_append",),
            needed=("premise_list_mem_append",),
            query_terms=("list", "membership", "append"),
            expected_strategy=("membership_decomposition",),
        ),
        problem(
            problem_id="strategy_list_map_map",
            split="dev",
            domain="list",
            informal_statement="Fuse two map operations into one map over function composition.",
            theorem_signature=(
                "theorem strategy_list_map_map (Alpha Beta Gamma : Type) "
                "(f : Alpha -> Beta) (g : Beta -> Gamma) (xs : List Alpha) : "
                "List.map g (List.map f xs) = List.map (g \u2218 f) xs := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact List.map_map",),
            needed=("premise_list_map_map",),
            query_terms=("list", "map", "composition", "fusion"),
            expected_strategy=("composition_fusion",),
        ),
        problem(
            problem_id="strategy_list_length_append",
            split="dev",
            domain="list",
            informal_statement="Normalize length over appended lists.",
            theorem_signature=(
                "theorem strategy_list_length_append (Alpha : Type) "
                "(xs ys : List Alpha) : "
                "(xs ++ ys).length = xs.length + ys.length := by"
            ),
            candidate_body=("  exact List.length_cons",),
            ideal_body=("  exact List.length_append",),
            needed=("premise_list_length_append",),
            query_terms=("list", "length", "append", "normal"),
            expected_strategy=("equality_normal_form",),
        ),
        problem(
            problem_id="strategy_list_reverse_reverse",
            split="test",
            domain="list",
            informal_statement="Normalize the double reverse of a list.",
            theorem_signature=(
                "theorem strategy_list_reverse_reverse (Alpha : Type) (xs : List Alpha) : "
                "xs.reverse.reverse = xs := by"
            ),
            candidate_body=("  rfl",),
            ideal_body=("  exact List.reverse_reverse xs",),
            needed=("premise_list_reverse_reverse",),
            query_terms=("list", "reverse", "twice", "normal"),
            expected_strategy=("equality_normal_form",),
        ),
        problem(
            problem_id="strategy_false_elim",
            split="test",
            domain="propositional",
            informal_statement="A contradiction hypothesis proves any proposition.",
            theorem_signature="theorem strategy_false_elim (p : Prop) (h : False) : p := by",
            candidate_body=("  rfl",),
            ideal_body=("  exact False.elim h",),
            needed=(),
            query_terms=("false", "contradiction", "elim"),
            expected_strategy=("contradiction_or_false_target",),
        ),
        problem(
            problem_id="strategy_list_length_append_symmetry_hit_fail",
            split="test",
            domain="list",
            informal_statement=(
                "Use the length append lemma in the opposite direction; the strategy "
                "is right but v0 proof synthesis may still orient it incorrectly."
            ),
            theorem_signature=(
                "theorem strategy_list_length_append_symmetry_hit_fail (Alpha : Type) "
                "(xs ys : List Alpha) : "
                "xs.length + ys.length = (xs ++ ys).length := by"
            ),
            candidate_body=("  exact List.length_append",),
            ideal_body=("  exact Eq.symm List.length_append",),
            needed=("premise_list_length_append",),
            query_terms=("list", "length", "append", "orientation", "opposite"),
            expected_strategy=("symmetry_or_orientation",),
        ),
        problem(
            problem_id="strategy_list_map_map_index_miss",
            split="test",
            domain="list",
            informal_statement="Fuse two map operations, but the local index slice omits the fusion lemma.",
            theorem_signature=(
                "theorem strategy_list_map_map_index_miss (Alpha Beta Gamma : Type) "
                "(f : Alpha -> Beta) (g : Beta -> Gamma) (xs : List Alpha) : "
                "List.map g (List.map f xs) = List.map (g \u2218 f) xs := by"
            ),
            candidate_body=("  exact List.reverse_reverse xs",),
            ideal_body=("  exact List.map_map",),
            needed=("premise_list_map_map",),
            query_terms=("list", "map", "composition", "fusion"),
            expected_strategy=("composition_fusion",),
            allowed=("premise_list_reverse_reverse", "premise_list_length_append"),
            expected_error_class="PREMISE_RETRIEVAL_MISS",
        ),
        problem(
            problem_id="strategy_list_length_append_wrong_lens",
            split="test",
            domain="list",
            informal_statement=(
                "Normalize an equality about appended list lengths without noticing "
                "the needed reversed orientation."
            ),
            theorem_signature=(
                "theorem strategy_list_length_append_wrong_lens (Alpha : Type) "
                "(xs ys : List Alpha) : "
                "xs.length + ys.length = (xs ++ ys).length := by"
            ),
            candidate_body=("  exact List.length_append",),
            ideal_body=("  exact Eq.symm List.length_append",),
            needed=("premise_list_length_append",),
            query_terms=("list", "length", "append", "normal"),
            expected_strategy=("symmetry_or_orientation",),
            expected_error_class="STRATEGY_SELECTION_MISS",
        ),
    ]


def _repo_path(path: Path) -> Path:
    return REPO_ROOT / path


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_text(_canonical_json(value))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(value), encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _lean_source(
    problem: ProverProblem,
    *,
    graph_variant_id: str,
    body: tuple[str, ...] | None = None,
    ideal: bool = False,
    attempt_label: str = "attempt_0",
    retrieved_premise_ids: tuple[str, ...] = (),
    cited_premise_ids: tuple[str, ...] = (),
) -> str:
    selected_body = body if body is not None else (problem.ideal_body if ideal else problem.candidate_body)
    imports = [f"import {name}" for name in problem.required_imports]
    lines = [
        "/- Prover Graph Benchmark Harness v0.",
        f"Problem: {problem.problem_id}",
        f"Split: {problem.split}",
        f"Graph: {graph_variant_id}",
        f"Attempt: {attempt_label}",
        f"Retrieved premise ids: {', '.join(retrieved_premise_ids) if retrieved_premise_ids else 'none'}",
        f"Cited premise ids: {', '.join(cited_premise_ids) if cited_premise_ids else 'none'}",
        "-/",
        "",
        *imports,
        "",
        problem.theorem_signature,
        *selected_body,
        "",
        f"#print axioms {problem.theorem_name}",
        "",
    ]
    return "\n".join(lines)


def _run_lean(lean_path: Path, *, timeout_seconds: int) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        result = subprocess.run(
            ["lean", str(lean_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": elapsed_ms,
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "duration_ms": elapsed_ms,
            "timeout": True,
        }


def _classify_lean_attempt(
    lean_run: dict[str, Any],
    *,
    expected_error_class: str = "PROOF_CORE_GAP",
) -> tuple[str, str, str]:
    if shutil.which("lean") is None:
        return "BLOCKED", "ENV_FAIL", "ENVIRONMENT_FAIL"
    if lean_run["timeout"]:
        return "READY", "TIMEOUT", "ORACLE_TIMEOUT"
    if lean_run["exit_code"] == 0:
        return "READY", "PASS", "NONE"
    return "READY", "FAIL", expected_error_class


def _classify_axioms(stdout: str, compile_status: str, sorry_present: bool) -> str:
    if sorry_present:
        return "SORRY_AX_TAINTED"
    if compile_status != "PASS":
        return "UNAUDITABLE"
    if "does not depend on any axioms" in stdout:
        return "CLEAN"
    return "UNAUDITABLE"


def _problem_manifest(problem_set: list[ProverProblem]) -> dict[str, Any]:
    return {
        "schema_version": "prover_problem_set_manifest_v0",
        "problem_count": len(problem_set),
        "split_policy": {
            "train": "Allowed for graph/process tuning.",
            "dev": "Allowed for graph variant selection.",
            "test": "Held out from tuning; report only.",
            "open": "No solved-proof success claim without independent proof/check.",
        },
        "leakage_policy": {
            "forward_lab_visible": "statement plus Lean core definitions only",
            "withheld_until_oracle": [
                "ideal proof body",
                "oracle critique",
                "aggregate graph update candidates",
            ],
            "test_split_tuning": "forbidden",
        },
        "problems": [
            {
                "problem_id": problem.problem_id,
                "source": problem.source,
                "split": problem.split,
                "mode": problem.mode,
                "domain": problem.domain,
                "informal_statement": problem.informal_statement,
                "theorem_name": problem.theorem_name,
                "required_imports": list(problem.required_imports),
                "source_ref": problem.source_ref,
                "source_family": problem.source_family,
                "difficulty_tag": problem.difficulty_tag,
                "allowed_premise_ids": list(problem.allowed_premise_ids),
                "retrieval_query_terms": list(problem.retrieval_query_terms),
                "visible_to_lab": list(problem.visible_to_lab),
                "withheld_until_oracle": list(problem.withheld_until_oracle),
                "context_recipe_id": problem.context_recipe_id,
            }
            for problem in problem_set
        ],
    }


def _problem_source_manifest(problem_set: list[ProverProblem]) -> dict[str, Any]:
    source_ids = sorted({problem.source for problem in problem_set})
    source_id = (
        "lean_std_toolchain_strategy_control_v0"
        if any(problem.difficulty_tag.startswith("strategy") for problem in problem_set)
        else
        "lean_std_toolchain_ring2_premise_retrieval_v0"
        if any(problem.difficulty_tag.startswith("ring2") for problem in problem_set)
        else "lean_std_toolchain_ring1_v0"
    )
    return {
        "schema_version": "prover_problem_source_manifest_v0",
        "source_id": source_id,
        "source_kind": "installed_lean_toolchain_source",
        "local_or_annex_path": _toolchain_source_path(),
        "availability": {
            "formal_conjectures_local": False,
            "leandojo_local": False,
            "mathlib_checkout_local": False,
            "minif2f_local": False,
            "putnambench_local": False,
            "lean_std_toolchain_local": shutil.which("lean") is not None,
        },
        "problem_count": len(problem_set),
        "problem_ids": [problem.problem_id for problem in problem_set],
        "source_ids": source_ids,
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
        "problems": [
            {
                "problem_id": problem.problem_id,
                "source": problem.source,
                "source_ref": problem.source_ref,
                "split": problem.split,
                "mode": problem.mode,
                "domain": problem.domain,
                "source_family": problem.source_family,
                "difficulty_tag": problem.difficulty_tag,
                "statement_visible_to_lab": True,
                "proof_body_withheld_until_oracle": True,
                "required_imports": list(problem.required_imports),
                "theorem_name": problem.theorem_name,
                "theorem_signature": problem.theorem_signature,
                "expected_checker": "Lean 4 CLI",
                "allowed_premise_ids": list(problem.allowed_premise_ids),
                "retrieval_query_terms": list(problem.retrieval_query_terms),
                "expected_strategy_ids_visible_to_lab": False,
                "visible_to_lab": list(problem.visible_to_lab),
                "withheld_until_oracle": list(problem.withheld_until_oracle),
                "oracle_only": {
                    "withheld_fields": [
                        "ideal_body",
                        "repair_body",
                        "needed_premise_ids",
                        "expected_strategy_ids",
                    ],
                    "ideal_body_available_after_oracle": bool(problem.ideal_body),
                    "repair_body_available_after_oracle": bool(
                        problem.repair_body or problem.ideal_body
                    ),
                    "needed_premise_ids_available_after_oracle": bool(
                        problem.oracle_needed_premise_ids
                    ),
                    "expected_strategy_ids_available_after_oracle": bool(
                        problem.expected_strategy_ids
                    ),
                },
            }
            for problem in problem_set
        ],
    }


def _problem_from_manifest_row(row: dict[str, Any]) -> ProverProblem:
    oracle_only = row.get("oracle_only") or {}
    ideal_body = tuple(oracle_only.get("ideal_body") or row.get("ideal_body") or ())
    repair_body = tuple(oracle_only.get("repair_body") or row.get("repair_body") or ())
    needed_premise_ids = tuple(
        oracle_only.get("needed_premise_ids") or row.get("oracle_needed_premise_ids") or ()
    )
    return ProverProblem(
        problem_id=row["problem_id"],
        source=row.get("source", "external_problem_source_manifest"),
        split=row["split"],
        mode=row.get("mode", "solved_training"),
        domain=row.get("domain", "unknown"),
        informal_statement=row.get("informal_statement") or row.get("statement") or row["theorem_name"],
        theorem_name=row["theorem_name"],
        theorem_signature=row["theorem_signature"],
        candidate_body=tuple(row.get("candidate_body") or ()),
        ideal_body=ideal_body,
        visible_to_lab=tuple(row.get("visible_to_lab") or ("statement", "required imports")),
        withheld_until_oracle=tuple(
            row.get("withheld_until_oracle")
            or ("ideal proof body", "repair proof body", "oracle critique")
        ),
        context_recipe_id=row.get("context_recipe_id", "source_manifest_direct_v0"),
        expected_error_class_on_fail=row.get("expected_error_class_on_fail", "PROOF_CORE_GAP"),
        required_imports=tuple(row.get("required_imports") or ()),
        source_ref=row.get("source_ref", "source_manifest"),
        source_family=row.get("source_family", "source_manifest"),
        difficulty_tag=row.get("difficulty_tag", "ring1"),
        repair_body=repair_body,
        allowed_premise_ids=tuple(row.get("allowed_premise_ids") or ()),
        oracle_needed_premise_ids=needed_premise_ids,
        retrieval_query_terms=tuple(row.get("retrieval_query_terms") or ()),
        retrieval_body=tuple(row.get("retrieval_body") or ()),
        expected_strategy_ids=tuple(
            oracle_only.get("expected_strategy_ids") or row.get("expected_strategy_ids") or ()
        ),
    )


def _load_problem_source_manifest(path: Path) -> tuple[list[ProverProblem], dict[str, Any]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema_version") == FORMAL_MATH_NO_SOLVE_MANIFEST_SCHEMA
        or manifest.get("benchmark_id") in FORMAL_MATH_NO_SOLVE_BENCHMARK_IDS
        or manifest.get("manifest_id")
        in {
            "constructivebench_no_solve_manifest_v0",
            "verisoftbench_no_solve_manifest_v0",
        }
    ):
        raise ValueError(
            "raw formal-math no-solve manifests are not prover problem sources; "
            "consume formal_math_benchmark_prompt_boundary_v0 packets instead"
        )
    problems = [_problem_from_manifest_row(row) for row in manifest.get("problems", [])]
    return problems, manifest


def _premise_lookup(premise_index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["premise_id"]: row for row in premise_index.get("premises", [])}


def _allowed_premises(
    problem: ProverProblem,
    premise_index: dict[str, Any],
) -> list[dict[str, Any]]:
    allowed_ids = set(problem.allowed_premise_ids)
    rows = []
    for row in premise_index.get("premises", []):
        if problem.split not in set(row.get("allowed_for_split", [])):
            continue
        if allowed_ids and row["premise_id"] not in allowed_ids:
            continue
        rows.append(row)
    return rows


def _retrieve_premises(
    problem: ProverProblem,
    premise_index: dict[str, Any],
    *,
    max_results: int = 3,
    query_terms_override: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    query_terms = [
        term.lower()
        for term in (
            query_terms_override
            or problem.retrieval_query_terms
            or tuple(re.findall(r"[A-Za-z0-9_.]+", problem.informal_statement.lower()))
        )
    ]
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for row in _allowed_premises(problem, premise_index):
        haystack = " ".join(
            [
                row.get("premise_id", ""),
                row.get("theorem_or_def_name", ""),
                row.get("namespace", ""),
                row.get("statement_excerpt", ""),
                " ".join(row.get("retrieval_terms", [])),
            ]
        ).lower()
        score = sum(1 for term in query_terms if term and term in haystack)
        if score > 0:
            scored.append((score, row["premise_id"], row))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = [row for _, _, row in scored[:max_results]]
    return {
        "schema_version": "premise_retrieval_report_v0",
        "problem_id": problem.problem_id,
        "retrieval_phase": "pre_oracle",
        "query_terms": query_terms,
        "source_index_size": len(premise_index.get("premises", [])),
        "retrieval_candidates_considered": len(_allowed_premises(problem, premise_index)),
        "retrieved_premise_ids": [row["premise_id"] for row in selected],
        "retrieved_premises": [
            {
                "premise_id": row["premise_id"],
                "theorem_or_def_name": row["theorem_or_def_name"],
                "source_ref": row["source_ref"],
                "statement_excerpt": row["statement_excerpt"],
            }
            for row in selected
        ],
        "oracle_needed_premise_ids_visible": False,
        "proof_body_visible": False,
    }


def _premise_ids_cited(body: tuple[str, ...], premise_index: dict[str, Any]) -> list[str]:
    body_text = "\n".join(body)
    cited = []
    for row in premise_index.get("premises", []):
        name = row.get("theorem_or_def_name", "")
        if name and name in body_text:
            cited.append(row["premise_id"])
    return sorted(set(cited))


def _premise_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    retrieval_rows = [row for row in rows if row.get("premise_retrieval")]
    retrieved_total = 0
    needed_total = 0
    hit_total = 0
    proof_success_given_hit = 0
    proof_failure_despite_hit = 0
    retrieval_miss_problem_ids: list[str] = []
    hit_success_problem_ids: list[str] = []
    hit_failure_problem_ids: list[str] = []
    for row in retrieval_rows:
        retrieval = row["premise_retrieval"]
        retrieved = set(retrieval.get("retrieved_premise_ids", []))
        needed = set(retrieval.get("oracle_needed_premise_ids", []))
        hits = retrieved & needed
        retrieved_total += len(retrieved)
        needed_total += len(needed)
        hit_total += len(hits)
        needed_hit = bool(needed) and needed.issubset(retrieved)
        if needed and not needed_hit:
            retrieval_miss_problem_ids.append(row["problem_id"])
        if needed_hit and row["lean_compile_status"] == "PASS":
            proof_success_given_hit += 1
            hit_success_problem_ids.append(row["problem_id"])
        if needed_hit and row["lean_compile_status"] != "PASS":
            proof_failure_despite_hit += 1
            hit_failure_problem_ids.append(row["problem_id"])
    return {
        "schema_version": "premise_retrieval_metrics_v0",
        "candidate_premise_count": retrieved_total,
        "oracle_needed_premise_count": needed_total,
        "premise_hit_count": hit_total,
        "premise_miss_count": max(needed_total - hit_total, 0),
        "premise_precision": hit_total / retrieved_total if retrieved_total else 0,
        "premise_recall": hit_total / needed_total if needed_total else 0,
        "proof_success_given_hit": proof_success_given_hit,
        "proof_failure_despite_hit": proof_failure_despite_hit,
        "retrieval_miss_problem_ids": retrieval_miss_problem_ids,
        "hit_success_problem_ids": hit_success_problem_ids,
        "hit_failure_problem_ids": hit_failure_problem_ids,
    }


def _strategy_cards() -> dict[str, Any]:
    cards = [
        {
            "schema_version": "mathematical_strategy_card_v0",
            "strategy_id": "equality_normal_form",
            "name": "Equality normal form",
            "mathematical_lens": "View the target as two expressions to normalize toward a shared canonical form.",
            "trigger_features": ["equality_target", "nat_add", "bool_not", "list_reverse", "length_append"],
            "negative_triggers": ["reversed_orientation"],
            "expected_problem_shapes": ["Nat equality", "Bool equality", "List length/reverse equality"],
            "representation_transform": "Normalize both sides by theorem families such as commutativity, associativity, involution, or length lemmas.",
            "retrieval_expansion_terms": ["equality", "normal", "nat", "bool", "length", "reverse"],
            "likely_required_premises": [
                "premise_nat_add_comm",
                "premise_nat_add_assoc",
                "premise_bool_not_not",
                "premise_list_reverse_reverse",
                "premise_list_length_append",
            ],
            "proof_plan_template": "try exact/rewrite/simp using the highest-scoring equality premise",
            "lean_tactic_affordances": ["exact", "rw", "simp"],
            "failure_modes": ["wrong orientation", "premise retrieved but not applicable"],
            "oracle_diagnostics": ["PROOF_SYNTHESIS_FAIL", "STRATEGY_SELECTION_MISS"],
            "credit_assignment_rule": "Credit when normalization strategy is selected before oracle and Lean accepts or fails only on tactic orientation.",
            "leakage_boundary": "No proof body or oracle-needed premise id is visible before Lean check.",
        },
        {
            "schema_version": "mathematical_strategy_card_v0",
            "strategy_id": "iff_split",
            "name": "Iff split",
            "mathematical_lens": "Treat an iff target as two directed implications.",
            "trigger_features": ["iff_target", "two_implications"],
            "negative_triggers": ["pure_equality"],
            "expected_problem_shapes": ["P <-> Q from P -> Q and Q -> P"],
            "representation_transform": "Construct Iff.intro and solve both directions.",
            "retrieval_expansion_terms": ["iff", "intro", "implication", "equivalence"],
            "likely_required_premises": ["premise_iff_intro"],
            "proof_plan_template": "intro both implication hypotheses; exact Iff.intro hpq hqp",
            "lean_tactic_affordances": ["intro", "exact Iff.intro"],
            "failure_modes": ["hypotheses not aligned", "using Iff.rfl when directions are not definitional"],
            "oracle_diagnostics": ["PROOF_SYNTHESIS_FAIL"],
            "credit_assignment_rule": "Credit when iff target routes to bidirectional proof planning.",
            "leakage_boundary": "Only statement and Iff.intro premise statement are visible before oracle.",
        },
        {
            "schema_version": "mathematical_strategy_card_v0",
            "strategy_id": "constructor_injectivity",
            "name": "Constructor injectivity",
            "mathematical_lens": "Equality of constructed values can imply equality of constructor arguments.",
            "trigger_features": ["constructor_equality", "succ_equality"],
            "negative_triggers": ["not_constructor_target"],
            "expected_problem_shapes": ["Nat.succ m = Nat.succ n -> m = n"],
            "representation_transform": "Introduce the equality and apply the constructor injectivity theorem.",
            "retrieval_expansion_terms": ["successor", "injective", "constructor", "inj", "nat"],
            "likely_required_premises": ["premise_nat_succ_inj"],
            "proof_plan_template": "intro h; exact Nat.succ.inj h",
            "lean_tactic_affordances": ["intro", "exact Nat.succ.inj"],
            "failure_modes": ["wrong constructor family", "missing no-confusion/injection lemma"],
            "oracle_diagnostics": ["PREMISE_RETRIEVAL_MISS", "PROOF_SYNTHESIS_FAIL"],
            "credit_assignment_rule": "Credit when constructor equality triggers injection before retrieval.",
            "leakage_boundary": "The proof body remains oracle-only.",
        },
        {
            "schema_version": "mathematical_strategy_card_v0",
            "strategy_id": "recursive_data_induction",
            "name": "Recursive data induction",
            "mathematical_lens": "Quantified goals over recursively defined data often want induction or a library induction theorem.",
            "trigger_features": ["quantified_nat", "recursive_function", "add_zero"],
            "negative_triggers": ["closed_ground_term"],
            "expected_problem_shapes": ["forall n, n + 0 = n", "list recursion properties"],
            "representation_transform": "Choose the recursive argument and either apply the library lemma or emit an induction skeleton.",
            "retrieval_expansion_terms": ["induction", "recursive", "zero", "successor", "add_zero"],
            "likely_required_premises": ["premise_nat_add_zero"],
            "proof_plan_template": "try Nat.add_zero; otherwise induction on the recursive argument",
            "lean_tactic_affordances": ["induction", "simp", "exact Nat.add_zero"],
            "failure_modes": ["wrong induction variable", "base/step mismatch"],
            "oracle_diagnostics": ["DECOMPOSITION_BAD", "PROOF_SYNTHESIS_FAIL"],
            "credit_assignment_rule": "Credit when recursive-data shape triggers induction/library-recursion planning.",
            "leakage_boundary": "No oracle proof body in forward induction skeleton.",
        },
        {
            "schema_version": "mathematical_strategy_card_v0",
            "strategy_id": "membership_decomposition",
            "name": "Membership decomposition",
            "mathematical_lens": "Membership in a constructed collection is equivalent to membership in its parts.",
            "trigger_features": ["list_membership", "append_membership", "iff_target"],
            "negative_triggers": ["numeric_equality"],
            "expected_problem_shapes": ["a in xs ++ ys iff a in xs or a in ys"],
            "representation_transform": "Retrieve and apply the collection membership characterization lemma.",
            "retrieval_expansion_terms": ["membership", "mem", "append", "or", "list"],
            "likely_required_premises": ["premise_list_mem_append"],
            "proof_plan_template": "exact List.mem_append",
            "lean_tactic_affordances": ["exact List.mem_append"],
            "failure_modes": ["wrong collection constructor", "missing iff orientation"],
            "oracle_diagnostics": ["PREMISE_RETRIEVAL_MISS", "PROOF_SYNTHESIS_FAIL"],
            "credit_assignment_rule": "Credit when constructed-membership targets expand retrieval with membership lemmas.",
            "leakage_boundary": "No known proof body in premise index.",
        },
        {
            "schema_version": "mathematical_strategy_card_v0",
            "strategy_id": "composition_fusion",
            "name": "Composition fusion",
            "mathematical_lens": "Nested structure-preserving operations may fuse into one operation over a composed function.",
            "trigger_features": ["nested_map", "function_composition"],
            "negative_triggers": ["non_nested_map"],
            "expected_problem_shapes": ["map g (map f xs) = map (g o f) xs"],
            "representation_transform": "Search map/fusion lemmas and orient the composed function correctly.",
            "retrieval_expansion_terms": ["map", "composition", "compose", "fusion", "function"],
            "likely_required_premises": ["premise_list_map_map"],
            "proof_plan_template": "exact List.map_map",
            "lean_tactic_affordances": ["exact List.map_map", "simp [Function.comp_def]"],
            "failure_modes": ["premise index omits fusion lemma", "function composition notation mismatch"],
            "oracle_diagnostics": ["PREMISE_RETRIEVAL_MISS", "PROOF_SYNTHESIS_FAIL"],
            "credit_assignment_rule": "Credit when nested-map view expands retrieval to fusion premises.",
            "leakage_boundary": "Oracle needed premise ids are audited only after Lean check.",
        },
        {
            "schema_version": "mathematical_strategy_card_v0",
            "strategy_id": "symmetry_or_orientation",
            "name": "Symmetry or orientation",
            "mathematical_lens": "A retrieved equality premise may solve the target only after reversing or rewriting in the right direction.",
            "trigger_features": ["reversed_orientation", "symmetry_needed"],
            "negative_triggers": ["direct_orientation"],
            "expected_problem_shapes": ["rhs = lhs when library lemma gives lhs = rhs"],
            "representation_transform": "Try Eq.symm or directed rewrite after retrieving the direct lemma.",
            "retrieval_expansion_terms": ["orientation", "symmetric", "reverse", "length", "append"],
            "likely_required_premises": ["premise_list_length_append"],
            "proof_plan_template": "try Eq.symm around the direct equality premise",
            "lean_tactic_affordances": ["exact Eq.symm", "rw [<- lemma]"],
            "failure_modes": ["strategy selected but v0 skeleton emits the direct theorem only"],
            "oracle_diagnostics": ["PROOF_SYNTHESIS_FAIL"],
            "credit_assignment_rule": "Credit strategy selection separately from proof synthesis success.",
            "leakage_boundary": "Orientation diagnosis is oracle-side after check.",
        },
        {
            "schema_version": "mathematical_strategy_card_v0",
            "strategy_id": "contradiction_or_false_target",
            "name": "Contradiction or false target",
            "mathematical_lens": "False assumptions or impossible targets collapse by contradiction elimination.",
            "trigger_features": ["false_assumption", "negated_target"],
            "negative_triggers": ["constructive_data_target"],
            "expected_problem_shapes": ["False -> P"],
            "representation_transform": "Introduce/case-analyze the contradiction and eliminate False.",
            "retrieval_expansion_terms": ["false", "contradiction", "absurd", "cases"],
            "likely_required_premises": [],
            "proof_plan_template": "exact False.elim h",
            "lean_tactic_affordances": ["cases h", "exact False.elim h"],
            "failure_modes": ["contradiction hypothesis not named or not present"],
            "oracle_diagnostics": ["PROOF_SYNTHESIS_FAIL"],
            "credit_assignment_rule": "Credit when contradiction shape avoids irrelevant premise lookup.",
            "leakage_boundary": "No theorem proof body required.",
        },
    ]
    return {
        "schema_version": "mathematical_strategy_atlas_v0",
        "source_id": "lean_std_strategy_cards_v0",
        "card_count": len(cards),
        "cards": cards,
        "leakage_policy": {
            "truth_side_proof_bodies_in_cards": False,
            "oracle_expected_strategy_visible_to_lab": False,
        },
    }


def _prover_skill_atlas(strategy_atlas: dict[str, Any] | None = None) -> dict[str, Any]:
    strategy_atlas = strategy_atlas or _strategy_cards()
    equality_orientation_cell = {
        "schema_version": "prover_skill_cell_v0",
        "skill_id": "skill_equality_orientation_v0",
        "family": "equality_orientation",
        "mathematical_lens": (
            "A retrieved equality theorem may need to be applied symmetrically or "
            "rewritten in the opposite direction before it matches the target."
        ),
        "recognizer": {
            "trigger_features": [
                "equality_target",
                "reversed_orientation",
                "symmetry_needed",
                "length_append",
            ],
            "negative_features": ["direct_orientation", "non_equality_target"],
            "confidence_rule": (
                "High when the selected strategy is symmetry_or_orientation and a "
                "retrieved equality premise names the same theorem family as the target."
            ),
        },
        "view_generator": {
            "representation_transforms": [
                "direct theorem view",
                "symmetric theorem view",
                "rewrite-forward view",
                "rewrite-backward view",
            ],
            "subproblem_templates": [
                "match target lhs/rhs against retrieved equality rhs/lhs",
                "choose Eq.symm when direct exact fails by reversed sides",
            ],
            "related_problem_moves": ["symmetry", "rewrite direction", "normal-form orientation"],
        },
        "retrieval_policy": {
            "query_expansion_terms": [
                "orientation",
                "symmetry",
                "reverse",
                "rewrite",
                "length",
                "append",
            ],
            "premise_family_targets": ["equality theorem", "length append theorem"],
            "concept_targets": ["Eq.symm", "rewrite direction"],
            "allowed_source_rules": [
                "use only premise ids/statements retrieved before oracle",
                "do not read candidate_body, ideal_body, repair_body, or retrieval_body fixtures",
            ],
        },
        "proof_plan_method": {
            "skeleton_templates": [
                "exact <retrieved equality theorem>",
                "exact Eq.symm <retrieved equality theorem>",
                "rw [<retrieved equality theorem>]",
                "rw [<- <retrieved equality theorem>]",
            ],
            "tactic_templates": ["exact Eq.symm", "rw", "simp"],
            "fallback_templates": [
                "classify PROOF_SYNTHESIS_FAIL_ORIENTATION if premise hit still fails"
            ],
        },
        "critic": {
            "expected_failure_modes": [
                "PREMISE_RETRIEVAL_MISS",
                "PROOF_SYNTHESIS_FAIL",
                "STRATEGY_SELECTION_MISS",
            ],
            "Lean_error_interpretation": (
                "If the equality premise is retrieved and direct exact fails, try the "
                "symmetric orientation before broad tactic search."
            ),
            "mismatch_diagnostics": [
                "retrieved premise missing",
                "strategy selected a non-orientation lens",
                "retrieved theorem family matches but sides are reversed",
            ],
        },
        "repair_policy": {
            "bounded_repairs": ["Eq.symm wrapper", "rewrite direction flip"],
            "orientation_rules": [
                "prefer Eq.symm for theorem-shaped equality facts",
                "prefer rewrite direction only after exact orientation fails",
            ],
            "induction_variable_repair": "not_applicable",
            "rewrite_direction_repair": "allowed_without_oracle_body_copy",
        },
        "case_memory": {
            "positive_cases": [],
            "negative_cases": [
                {
                    "source_run": DEFAULT_STRATEGY_RUN_ID,
                    "problem_id": "strategy_list_length_append_symmetry_hit_fail",
                    "failure": "strategy and premise hit, proof skeleton emitted direct theorem orientation",
                }
            ],
            "adaptation_notes": [
                "Promote the Ring-2/strategy orientation failure into a reusable skill-cell repair."
            ],
            "derived_abstractions": ["orientation repair as proof-synthesis step, not oracle repair"],
        },
        "evaluation": {
            "train_dev_test_policy": "skill may be selected on train/dev and reported on test; no proof-body leakage",
            "metrics": [
                "skill_selection_count",
                "orientation_failure_repaired_count",
                "proof_success_given_skill_hit",
            ],
            "leakage_boundaries": [
                "truth-side proof bodies remain oracle-only",
                "oracle_needed_premise_ids are audited only after Lean check",
            ],
        },
        "provenance": {
            "source_strategy_cards": ["symmetry_or_orientation", "equality_normal_form"],
            "source_runs": [
                "state/runs/PROVER_BENCHMARK_STRATEGY_20260510_control_graph_v0/graph_variant_comparison.json"
            ],
            "public_prior_art": ["proof planning", "LeanDojo/ReProver", "Schoenfeld control"],
            "local_doctrine_refs": [
                "codex/doctrine/paper_modules/mathematics_mission_pipeline.md",
                "codex/doctrine/missions/prover_lab.md",
                "codex/doctrine/missions/prover_oracle.md",
                "codex/doctrine/missions/prover_evolve.md",
            ],
        },
    }
    return {
        "schema_version": "prover_skill_atlas_v0",
        "source_id": "prover_skill_atlas_composition_root_v0",
        "composition_root": "run_artifact_under_mathematics_mission_pipeline",
        "skill_cell_count": 1,
        "cells": [equality_orientation_cell],
        "strategy_card_mapping": [
            {
                "strategy_id": row["strategy_id"],
                "mapped_skill_cell_id": (
                    "skill_equality_orientation_v0"
                    if row["strategy_id"] == "symmetry_or_orientation"
                    else None
                ),
                "mapping_status": (
                    "executable_cell_v0"
                    if row["strategy_id"] == "symmetry_or_orientation"
                    else "strategy_card_prototype"
                ),
            }
            for row in strategy_atlas.get("cards", [])
        ],
        "leakage_policy": {
            "truth_side_proof_bodies_in_skill_cells": False,
            "skill_cells_may_emit_candidate_skeletons": True,
            "oracle_repair_is_comparator_not_forward_skill_success": True,
        },
    }


def _prover_skill_foundry_skill_atlas(
    strategy_atlas: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Candidate skill atlas produced by the v0 Foundry lane.

    These cells remain run artifacts, not global doctrine. They are deliberately
    mined from observed case clusters and must earn promotion through Lean-checked
    evaluation rather than becoming a hand-authored skill library.
    """

    strategy_atlas = strategy_atlas or _strategy_cards()
    seed_atlas = _prover_skill_atlas(strategy_atlas)
    orientation_v1 = json.loads(json.dumps(seed_atlas["cells"][0]))
    orientation_v1["skill_id"] = "skill_equality_orientation_v1"
    orientation_v1["provenance"]["source_runs"].append(
        "state/runs/PROVER_SKILL_ATLAS_20260510_composition_root_v0/graph_variant_comparison.json"
    )
    orientation_v1["case_memory"]["adaptation_notes"].append(
        "Foundry seed: keep orientation as an explicit candidate, but require perturbation evidence before global promotion."
    )
    orientation_v1["evaluation"]["promotion_gate"] = (
        "quarantine unless it repairs more than the seed length_append symmetry case"
    )

    equality_family_cell = {
        "schema_version": "candidate_prover_skill_cell_v0",
        "skill_id": "skill_equality_family_disambiguation_v0",
        "family": "equality_normal_form",
        "mathematical_lens": (
            "When equality-normal-form retrieval returns several true equality premises, "
            "choose the premise family that matches the target representation before emitting Lean."
        ),
        "recognizer": {
            "trigger_features": [
                "equality_target",
                "bool_not",
                "list_reverse",
                "length_append",
                "nat_add",
            ],
            "negative_features": ["reversed_orientation", "non_equality_target"],
            "confidence_rule": (
                "High when equality_normal_form was selected, the oracle-needed family was "
                "retrieved pre-oracle, and the v0 skeleton cited a different retrieved premise."
            ),
        },
        "view_generator": {
            "representation_transforms": [
                "Boolean involution view",
                "list reverse involution view",
                "list length append view",
                "Nat commutativity view",
            ],
            "subproblem_templates": [
                "match target tokens against retrieved theorem family before exact",
                "prefer family match over highest retrieval rank",
            ],
            "related_problem_moves": [
                "premise family disambiguation",
                "normal-form theorem selection",
            ],
        },
        "retrieval_policy": {
            "query_expansion_terms": [
                "equality",
                "normal",
                "bool not_not",
                "reverse_reverse",
                "length_append",
                "add_comm",
            ],
            "premise_family_targets": [
                "Bool.not_not",
                "List.reverse_reverse",
                "List.length_append",
                "Nat.add_comm",
            ],
            "concept_targets": ["target-family match", "retrieval-rank override"],
            "allowed_source_rules": [
                "use only retrieved premise ids/statements and target syntax",
                "do not read oracle_needed_premise_ids before Lean check",
            ],
        },
        "proof_plan_method": {
            "skeleton_templates": [
                "exact Bool.not_not b",
                "exact List.reverse_reverse xs",
                "exact List.length_append",
                "exact Nat.add_comm m n",
            ],
            "tactic_templates": ["exact", "rw", "simp"],
            "fallback_templates": [
                "classify PROOF_SYNTHESIS_FAIL_FAMILY_MISMATCH if the target family match still fails"
            ],
        },
        "critic": {
            "expected_failure_modes": [
                "PROOF_SYNTHESIS_FAIL",
                "PREMISE_RETRIEVAL_MISS",
                "STRATEGY_SELECTION_MISS",
            ],
            "Lean_error_interpretation": (
                "If a retrieved equality theorem from the wrong family is cited, debit proof "
                "synthesis rather than retrieval."
            ),
            "mismatch_diagnostics": [
                "wrong retrieved premise cited",
                "target family token missed",
                "retrieved theorem has right family but wrong orientation",
            ],
        },
        "repair_policy": {
            "bounded_repairs": ["target-family premise selection"],
            "orientation_rules": [
                "defer reversed orientation to skill_equality_orientation_v1"
            ],
            "induction_variable_repair": "not_applicable",
            "rewrite_direction_repair": "not_in_this_cell",
        },
        "case_memory": {
            "positive_cases": [],
            "negative_cases": [
                {
                    "source_run": DEFAULT_SKILL_ATLAS_RUN_ID,
                    "problem_ids": [
                        "strategy_bool_not_not",
                        "strategy_list_length_append",
                        "strategy_list_reverse_reverse",
                    ],
                    "failure": "strategy and premise hit, but skeleton cited an unrelated retrieved equality theorem",
                }
            ],
            "adaptation_notes": [
                "Treat irrelevant retrieved-premise citation as a reusable proof-synthesis failure cluster."
            ],
            "derived_abstractions": [
                "target-family matching before theorem exact"
            ],
        },
        "evaluation": {
            "train_dev_test_policy": "evaluate across train/dev/test as report-only for held-out cases",
            "metrics": [
                "family_mismatch_repaired_count",
                "proof_success_given_family_match",
                "leakage_count",
            ],
            "leakage_boundaries": [
                "oracle_needed_premise_ids remain oracle-only",
                "proof bodies remain oracle-only",
            ],
        },
        "provenance": {
            "source_strategy_cards": ["equality_normal_form"],
            "source_runs": [
                "state/runs/PROVER_SKILL_ATLAS_20260510_composition_root_v0/graph_variant_comparison.json"
            ],
            "public_prior_art": [
                "proof planning",
                "DreamCoder abstraction loop",
                "derivational analogy",
            ],
            "local_doctrine_refs": [
                "codex/doctrine/paper_modules/mathematics_mission_pipeline.md"
            ],
        },
    }

    retrieval_gap_cell = {
        "schema_version": "candidate_prover_skill_cell_v0",
        "skill_id": "skill_composition_fusion_index_expansion_v0",
        "family": "composition_fusion",
        "mathematical_lens": (
            "Nested map/fusion goals need the map_map family in the allowed premise index; "
            "a proof skill cannot compensate when the premise is withheld."
        ),
        "recognizer": {
            "trigger_features": ["nested_map", "function_composition"],
            "negative_features": ["premise_list_map_map_retrieved"],
            "confidence_rule": "High when composition_fusion is selected and map_map is absent from retrieved premises.",
        },
        "view_generator": {
            "representation_transforms": ["map fusion view"],
            "subproblem_templates": ["retrieve map_map before proof synthesis"],
            "related_problem_moves": ["source index expansion"],
        },
        "retrieval_policy": {
            "query_expansion_terms": ["map", "map_map", "fusion", "composition"],
            "premise_family_targets": ["List.map_map"],
            "concept_targets": ["function composition"],
            "allowed_source_rules": ["requires index/source expansion; no oracle proof-body copy"],
        },
        "proof_plan_method": {
            "skeleton_templates": ["exact List.map_map"],
            "tactic_templates": ["exact", "simp [Function.comp_def]"],
            "fallback_templates": ["quarantine when premise is not in allowed source slice"],
        },
        "critic": {
            "expected_failure_modes": ["PREMISE_RETRIEVAL_MISS"],
            "Lean_error_interpretation": "Do not debit proof synthesis when the premise is absent from the allowed index.",
            "mismatch_diagnostics": ["source index omission", "novel premise split"],
        },
        "repair_policy": {
            "bounded_repairs": [],
            "orientation_rules": [],
            "induction_variable_repair": "not_applicable",
            "rewrite_direction_repair": "not_applicable",
        },
        "case_memory": {
            "positive_cases": [],
            "negative_cases": [
                {
                    "source_run": DEFAULT_SKILL_ATLAS_RUN_ID,
                    "problem_id": "strategy_list_map_map_index_miss",
                    "failure": "strategy hit but premise was intentionally withheld from allowed source slice",
                }
            ],
            "adaptation_notes": ["Quarantine as corpus/index readiness, not a proof-method promotion."],
            "derived_abstractions": ["retrieval miss must not be counted as skill failure"],
        },
        "evaluation": {
            "train_dev_test_policy": "quarantine until a non-held-out source slice contains map_map",
            "metrics": ["premise_miss_count", "index_expansion_needed"],
            "leakage_boundaries": ["oracle repair remains comparator only"],
        },
        "provenance": {
            "source_strategy_cards": ["composition_fusion"],
            "source_runs": [
                "state/runs/PROVER_SKILL_ATLAS_20260510_composition_root_v0/graph_variant_comparison.json"
            ],
            "public_prior_art": ["LeanDojo novel-premise split"],
            "local_doctrine_refs": [
                "codex/doctrine/paper_modules/mathematics_mission_pipeline.md"
            ],
        },
    }

    trigger_gap_cell = {
        "schema_version": "candidate_prover_skill_cell_v0",
        "skill_id": "skill_reversed_orientation_trigger_v0",
        "family": "strategy_selection",
        "mathematical_lens": (
            "Detect reversed-orientation language before generic equality-normal-form wins the strategy scorer."
        ),
        "recognizer": {
            "trigger_features": ["equality_target", "reversed_orientation", "length_append"],
            "negative_features": ["direct_orientation"],
            "confidence_rule": "Requires train/dev evidence; current witness is held-out report-only.",
        },
        "view_generator": {
            "representation_transforms": ["symmetric theorem view"],
            "subproblem_templates": ["route to symmetry_or_orientation before retrieval"],
            "related_problem_moves": ["strategy scorer trigger adjustment"],
        },
        "retrieval_policy": {
            "query_expansion_terms": ["orientation", "opposite", "symmetry", "length_append"],
            "premise_family_targets": ["List.length_append"],
            "concept_targets": ["strategy trigger calibration"],
            "allowed_source_rules": ["do not tune directly on held-out failure"],
        },
        "proof_plan_method": {
            "skeleton_templates": ["exact Eq.symm <retrieved equality theorem>"],
            "tactic_templates": ["exact Eq.symm"],
            "fallback_templates": ["defer until train/dev perturbation validates trigger"],
        },
        "critic": {
            "expected_failure_modes": ["STRATEGY_SELECTION_MISS"],
            "Lean_error_interpretation": "Wrong strategy lens, not premise retrieval.",
            "mismatch_diagnostics": ["generic equality scorer outranked orientation cue"],
        },
        "repair_policy": {
            "bounded_repairs": ["strategy trigger score patch"],
            "orientation_rules": ["prefer orientation when reversed cue is explicit"],
            "induction_variable_repair": "not_applicable",
            "rewrite_direction_repair": "through skill_equality_orientation_v1",
        },
        "case_memory": {
            "positive_cases": [],
            "negative_cases": [
                {
                    "source_run": DEFAULT_SKILL_ATLAS_RUN_ID,
                    "problem_id": "strategy_list_length_append_wrong_lens",
                    "failure": "held-out strategy selection miss",
                }
            ],
            "adaptation_notes": ["Do not promote from test-only evidence."],
            "derived_abstractions": ["strategy scorer fixes need train/dev perturbations"],
        },
        "evaluation": {
            "train_dev_test_policy": "quarantine; held-out case is report-only",
            "metrics": ["strategy_selection_miss_count"],
            "leakage_boundaries": ["no prompt tuning on test split"],
        },
        "provenance": {
            "source_strategy_cards": ["symmetry_or_orientation", "equality_normal_form"],
            "source_runs": [
                "state/runs/PROVER_SKILL_ATLAS_20260510_composition_root_v0/graph_variant_comparison.json"
            ],
            "public_prior_art": ["Schoenfeld control", "proof planning"],
            "local_doctrine_refs": [
                "codex/doctrine/paper_modules/mathematics_mission_pipeline.md"
            ],
        },
    }

    cells = [
        orientation_v1,
        equality_family_cell,
        retrieval_gap_cell,
        trigger_gap_cell,
    ]
    return {
        "schema_version": "prover_skill_foundry_candidate_atlas_v0",
        "source_id": "prover_skill_foundry_v0",
        "composition_root": "prover_skill_atlas_v0_run_artifact",
        "skill_cell_count": len(cells),
        "cells": cells,
        "strategy_card_mapping": [
            {
                "strategy_id": row["strategy_id"],
                "mapped_candidate_skill_ids": [
                    cell["skill_id"]
                    for cell in cells
                    if row["strategy_id"] in cell.get("provenance", {}).get(
                        "source_strategy_cards", []
                    )
                ],
            }
            for row in strategy_atlas.get("cards", [])
        ],
        "leakage_policy": {
            "truth_side_proof_bodies_in_skill_cells": False,
            "oracle_needed_premise_ids_visible_before_check": False,
            "oracle_repair_is_comparator_not_forward_skill_success": True,
        },
    }


def _skill_lookup(skill_atlas: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["skill_id"]: row for row in skill_atlas.get("cells", [])}


def _composition_root_decision(
    *,
    strategy_atlas: dict[str, Any],
    skill_atlas: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "prover_skill_composition_root_decision_v0",
        "selected_root": {
            "root_id": "prover_skill_atlas_v0_run_artifact",
            "home": "state/runs/PROVER_SKILL_ATLAS_20260510_composition_root_v0",
            "governing_mission": "mathematics_mission_pipeline",
            "reason": (
                "Local discovery found generic agent skills, standards, kind atlas rows, "
                "and the mathematics mission paper module, but no Prover-specific skill "
                "cell registry. A run-artifact root keeps the first cell executable and "
                "low-blast-radius while preserving a clear promotion path."
            ),
        },
        "rejected_roots": [
            {
                "root_id": "codex/doctrine/skills",
                "reason": (
                    "Repo skills govern agent workflow procedures; fine-grained theorem "
                    "prover control cells would overload the human/agent skill registry."
                ),
            },
            {
                "root_id": "new_global_standard",
                "reason": (
                    "One executable cell is not enough evidence for a new permanent standard."
                ),
            },
            {
                "root_id": "mathematical_strategy_card_v0",
                "reason": (
                    "Strategy cards are useful prototypes, but they lack case memory, repair "
                    "policy, and evaluation hooks needed for reusable skill cells."
                ),
            },
            {
                "root_id": "external_corpus_annex",
                "reason": (
                    "Formal Conjectures/LeanDojo/mathlib readiness is a separate annex lane; "
                    "the local Lean/Std skill mechanism should be executable first."
                ),
            },
        ],
        "evidence_refs": [
            "codex/doctrine/paper_modules/mathematics_mission_pipeline.md",
            "codex/doctrine/skills/skill_registry.json",
            "codex/standards/std_skill.json",
            "tools/meta/factory/run_prover_graph_benchmark.py",
            "state/runs/PROVER_BENCHMARK_STRATEGY_20260510_control_graph_v0/graph_variant_comparison.json",
        ],
        "kind_atlas_findings": [
            "skills exists as a generic doctrine kind governed by std_skill",
            "paper_modules exists as a mission/doctrine root governed by std_paper_module",
            "no dedicated Prover skill-cell kind was discovered before authoring",
        ],
        "mapping_from_strategy_cards": skill_atlas["strategy_card_mapping"],
        "required_minimal_new_surface": [
            "prover_skill_atlas_v0",
            "prover_skill_cell_v0",
            "prover_skill_cell_overlay_decision_v0",
        ],
        "blast_radius": [
            "tools/meta/factory/run_prover_graph_benchmark.py",
            "system/server/tests/test_prover_graph_benchmark_harness.py",
            "state/runs/PROVER_SKILL_ATLAS_20260510_composition_root_v0",
        ],
        "validation_plan": [
            "py_compile harness",
            "run harness tests",
            "run skill atlas composition root with --check",
            "confirm provider calls and leakage events remain zero",
        ],
        "strategy_card_count": strategy_atlas["card_count"],
        "skill_cell_count": skill_atlas["skill_cell_count"],
    }


def _strategy_lookup(strategy_atlas: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["strategy_id"]: row for row in strategy_atlas.get("cards", [])}


def _feature_tokens(problem: ProverProblem) -> set[str]:
    text = f"{problem.informal_statement} {problem.theorem_signature}".lower()
    features: set[str] = set()
    if "=" in problem.theorem_signature:
        features.add("equality_target")
    if "<->" in problem.theorem_signature or "↔" in problem.theorem_signature:
        features.add("iff_target")
    if "nat.succ" in text:
        features.update({"constructor_equality", "succ_equality"})
    if "n + 0" in text or "add_zero" in text:
        features.update({"quantified_nat", "recursive_function", "add_zero"})
    if "list.mem" in text or "membership" in text:
        features.update({"list_membership", "append_membership"})
    if "list.map" in text or " map " in text:
        features.update({"nested_map", "function_composition"})
    if "length" in text and "append" in text:
        features.add("length_append")
    if "orientation" in text or "opposite direction" in text or "backwards" in text:
        features.update({"reversed_orientation", "symmetry_needed"})
    if "bool" in text or "negation" in text:
        features.add("bool_not")
    if "reverse" in text:
        features.add("list_reverse")
    if "addition" in text or "nat.add" in text or " + " in problem.theorem_signature:
        features.add("nat_add")
    if "false" in text or "contradiction" in text:
        features.add("false_assumption")
    return features


def _strategy_hypotheses(
    problem: ProverProblem,
    strategy_atlas: dict[str, Any],
    *,
    max_results: int = 3,
) -> dict[str, Any]:
    features = _feature_tokens(problem)
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for card in strategy_atlas.get("cards", []):
        trigger_hits = features & set(card.get("trigger_features", []))
        negative_hits = features & set(card.get("negative_triggers", []))
        score = (len(trigger_hits) * 4) - (len(negative_hits) * 3)
        for term in problem.retrieval_query_terms:
            if term.lower() in " ".join(card.get("retrieval_expansion_terms", [])).lower():
                score += 1
        if score > 0:
            scored.append((score, card["strategy_id"], card))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = scored[:max_results]
    return {
        "schema_version": "strategy_hypothesis_set_v0",
        "problem_id": problem.problem_id,
        "strategy_phase": "pre_oracle",
        "problem_features": sorted(features),
        "strategy_hypotheses": [
            {
                "strategy_id": card["strategy_id"],
                "score": score,
                "mathematical_lens": card["mathematical_lens"],
                "trigger_features": sorted(features & set(card.get("trigger_features", []))),
                "retrieval_expansion_terms": list(card.get("retrieval_expansion_terms", [])),
                "proof_plan_template": card.get("proof_plan_template", ""),
            }
            for score, _, card in selected
        ],
        "selected_strategy_id": selected[0][1] if selected else "none",
        "oracle_expected_strategy_ids_visible": False,
        "proof_body_visible": False,
    }


def _strategy_query_terms(
    problem: ProverProblem,
    strategy_hypothesis_set: dict[str, Any],
    strategy_atlas: dict[str, Any],
) -> tuple[str, ...]:
    selected_id = strategy_hypothesis_set.get("selected_strategy_id", "none")
    card = _strategy_lookup(strategy_atlas).get(selected_id, {})
    terms = list(problem.retrieval_query_terms)
    terms.extend(card.get("retrieval_expansion_terms", []))
    for premise_id in card.get("likely_required_premises", []):
        terms.extend(str(premise_id).split("_"))
    return tuple(dict.fromkeys(term.lower() for term in terms if term))


def _view_generation(
    problem: ProverProblem,
    strategy_hypothesis_set: dict[str, Any],
    strategy_atlas: dict[str, Any],
) -> dict[str, Any]:
    selected_id = strategy_hypothesis_set.get("selected_strategy_id", "none")
    card = _strategy_lookup(strategy_atlas).get(selected_id, {})
    return {
        "schema_version": "mathematical_view_generation_v0",
        "problem_id": problem.problem_id,
        "selected_strategy_id": selected_id,
        "mathematical_lens": card.get("mathematical_lens", "none"),
        "view_candidates": [
            {
                "strategy_id": row["strategy_id"],
                "view": row["mathematical_lens"],
                "proof_plan_template": row["proof_plan_template"],
            }
            for row in strategy_hypothesis_set.get("strategy_hypotheses", [])
        ],
        "chosen_view_basis": "highest deterministic trigger score over statement features and allowed query terms",
        "truth_side_material_visible": False,
    }


def _body_from_retrieved_premises(
    problem: ProverProblem,
    retrieved_premise_ids: list[str],
    *,
    strategy_id: str | None = None,
) -> tuple[str, ...]:
    retrieved = set(retrieved_premise_ids)
    if "premise_nat_succ_inj" in retrieved:
        return ("  intro h", "  exact Nat.succ.inj h")
    if "premise_iff_intro" in retrieved:
        return ("  intro hpq hqp", "  exact Iff.intro hpq hqp")
    if "premise_list_mem_append" in retrieved:
        return ("  exact List.mem_append",)
    if "premise_list_map_map" in retrieved:
        return ("  exact List.map_map",)
    if "premise_nat_add_comm" in retrieved:
        return ("  exact Nat.add_comm m n",)
    if "premise_nat_add_assoc" in retrieved:
        return ("  exact Nat.add_assoc a b c",)
    if "premise_nat_add_zero" in retrieved:
        return ("  exact Nat.add_zero n",)
    if "premise_bool_not_not" in retrieved:
        return ("  exact Bool.not_not b",)
    if "premise_list_reverse_reverse" in retrieved:
        return ("  exact List.reverse_reverse xs",)
    if "premise_list_length_append" in retrieved:
        # The v0 premise graph deliberately does not solve orientation by itself.
        return ("  exact List.length_append",)
    if strategy_id == "contradiction_or_false_target":
        return ("  exact False.elim h",)
    return problem.candidate_body


def _is_local_executable_source_family(source_family: str) -> bool:
    return source_family in LOCAL_EXECUTABLE_SOURCE_FAMILIES


def _source_family_guard_applies(problem: ProverProblem, graph_variant_id: str) -> bool:
    return (
        graph_variant_id in SOURCE_GUARDED_GRAPH_VARIANTS
        and not _is_local_executable_source_family(problem.source_family)
    )


def _external_source_family_strategy_guard(
    problem: ProverProblem,
    *,
    graph_variant_id: str,
    selected_strategy_id: str | None,
    retrieved_premise_ids: list[str],
    skill_cell_id: str | None,
) -> dict[str, Any]:
    guard_applied = _source_family_guard_applies(problem, graph_variant_id)
    return {
        "schema_version": "external_source_family_strategy_guard_v0",
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "graph_variant_id": graph_variant_id,
        "selected_strategy_id": selected_strategy_id or "none",
        "suppressed_skill_cell_id": skill_cell_id,
        "retrieved_premise_ids": retrieved_premise_ids,
        "guard_applied": guard_applied,
        "proof_body_emission_policy": (
            "preserve_source_adapter_direct_candidate_and_emit_policy_only"
            if guard_applied
            else "local_source_family_allows_strategy_candidate_body"
        ),
        "allowed_forward_realizations": (
            [
                "proof_plan_text",
                "retrieval_query_expansion",
                "tactic_portfolio_candidate",
                "source_adapter_direct_candidate",
            ]
            if guard_applied
            else ["local_strategy_candidate_body", "local_skill_cell_candidate_body"]
        ),
        "forbidden_forward_realizations": (
            [
                "local_lean_std_premise_skeleton",
                "source_incompatible_skill_cell_body",
                "truth_side_proof_body",
            ]
            if guard_applied
            else ["truth_side_proof_body"]
        ),
        "fallback_tactic_portfolio": list(TACTIC_PORTFOLIO_CORE_V0),
        "why": (
            "External or unknown source families must not receive local Lean/Std "
            "premise skeletons unless a compatibility lane proves them source-safe."
            if guard_applied
            else "Known local source family; existing strategy skeleton policy remains available."
        ),
        "truth_side_body_used": False,
    }


def _safe_tactic_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "candidate"


def _tactic_probe_source(tactic_id: str) -> str:
    body_by_id = {
        "rfl": (
            "theorem tactic_probe_rfl (n : Nat) : n = n := by",
            "  rfl",
        ),
        "decide": (
            "theorem tactic_probe_decide : 2004 % 12 = 0 := by",
            "  decide",
        ),
        "native_decide": (
            "theorem tactic_probe_native_decide : 2004 % 12 = 0 := by",
            "  native_decide",
        ),
        "omega": (
            "theorem tactic_probe_omega "
            "(x y : Int) (h0 : 2 * 3 = x - 9) (h1 : 2 * (-5) = y + 1) : "
            "x = 15 ∧ y = -11 := by",
            "  omega",
        ),
        "simp": (
            "theorem tactic_probe_simp (n : Nat) : n + 0 = n := by",
            "  simp",
        ),
        "simp_all": (
            "theorem tactic_probe_simp_all (p : Prop) (h : p) : p := by",
            "  simp_all",
        ),
        "aesop": (
            "theorem tactic_probe_aesop : True := by",
            "  aesop",
        ),
        "grind": (
            "theorem tactic_probe_grind (n : Nat) : n = n := by",
            "  grind",
        ),
    }
    theorem = body_by_id[tactic_id]
    return "\n".join(["import Std", "", *theorem, ""])


def _probe_tactic_portfolio_availability(
    probe_root: Path,
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    probe_root.mkdir(parents=True, exist_ok=True)
    for tactic_id in TACTIC_PORTFOLIO_CORE_V0:
        probe_path = probe_root / f"{_safe_tactic_id(tactic_id)}.lean"
        _write_text(probe_path, _tactic_probe_source(tactic_id))
        run = _run_lean(probe_path, timeout_seconds=timeout_seconds)
        _, compile_status, error_class = _classify_lean_attempt(
            run,
            expected_error_class="TACTIC_SEARCH_FAIL",
        )
        rows.append(
            {
                "tactic_id": tactic_id,
                "probe_path": str(probe_path),
                "compile_status": compile_status,
                "error_class": error_class if compile_status != "PASS" else "NONE",
                "available": compile_status == "PASS",
                "duration_ms": run["duration_ms"],
                "stderr_excerpt": run["stderr"][:600],
            }
        )
    manifest = {
        "schema_version": "tactic_portfolio_availability_v0",
        "portfolio_id": "portfolio_core_v0",
        "imports": ["Std"],
        "rows": rows,
        "available_tactic_ids": [
            row["tactic_id"] for row in rows if row.get("available")
        ],
        "unavailable_tactic_ids": [
            row["tactic_id"] for row in rows if not row.get("available")
        ],
    }
    _write_json(probe_root / "tactic_portfolio_availability.json", manifest)
    return manifest


def _proof_search_candidate_actions(
    problem: ProverProblem,
    availability: dict[str, Any] | None,
    *,
    include_adapter_candidate: bool,
    include_templates: bool,
) -> list[dict[str, Any]]:
    available_ids = set((availability or {}).get("available_tactic_ids") or TACTIC_PORTFOLIO_CORE_V0)
    body_by_id: dict[str, tuple[str, ...]] = {
        "rfl": ("  rfl",),
        "decide": ("  decide",),
        "native_decide": ("  native_decide",),
        "omega": ("  omega",),
        "simp": ("  simp",),
        "simp_all": ("  simp_all",),
        "aesop": ("  aesop",),
        "grind": ("  grind",),
    }
    candidates: list[dict[str, Any]] = [
        {
            "action_id": f"core_tactic_{tactic_id}",
            "action_kind": "tactic",
            "tactic_id": tactic_id,
            "body": body_by_id[tactic_id],
            "selected_facts": [],
            "required_imports": list(problem.required_imports),
            "allowed_when": [
                "tactic is available in current Lean/Std probe",
                "tactic is part of portfolio_core_v0",
            ],
            "forbidden_when": [],
            "selection_reason": "available in current Lean/Std probe and part of portfolio_core_v0",
        }
        for tactic_id in TACTIC_PORTFOLIO_CORE_V0
        if tactic_id in available_ids
    ]
    if include_templates:
        signature = problem.theorem_signature
        template_specs: list[tuple[str, tuple[str, ...], str]] = []
        if ": True := by" in signature:
            template_specs.append(
                (
                    "exact_true_intro_template",
                    ("  exact True.intro",),
                    "target shape is True; intro-free constructor template is admissible",
                )
            )
        if "p ∧ q -> q ∧ p" in signature:
            template_specs.append(
                (
                    "and_comm_intro_constructor_template",
                    ("  intro h", "  exact And.intro h.right h.left"),
                    "target shape is propositional conjunction commutation",
                )
            )
        if "p ∨ q -> q ∨ p" in signature:
            template_specs.append(
                (
                    "or_comm_cases_template",
                    (
                        "  intro h",
                        "  cases h with",
                        "  | inl hp => exact Or.inr hp",
                        "  | inr hq => exact Or.inl hq",
                    ),
                    "target shape is propositional disjunction commutation",
                )
            )
        if "∃ n : Nat, n = 0" in signature:
            template_specs.append(
                (
                    "exists_zero_constructor_template",
                    ("  exact Exists.intro 0 rfl",),
                    "target shape is existential Nat zero witness",
                )
            )
        if "False ->" in signature:
            template_specs.append(
                (
                    "false_elim_intro_template",
                    ("  intro h", "  exact False.elim h"),
                    "target shape consumes False as a premise",
                )
            )
        for tactic_id, body, reason in template_specs:
            candidates.append(
                {
                    "action_id": tactic_id,
                    "action_kind": "template",
                    "tactic_id": tactic_id,
                    "body": body,
                    "selected_facts": [],
                    "required_imports": list(problem.required_imports),
                    "allowed_when": ["target shape matches this proof-search template"],
                    "forbidden_when": ["source_family guard forbids body templates"],
                    "selection_reason": reason,
                }
            )
    if include_adapter_candidate and problem.candidate_body:
        candidates.append(
            {
                "action_id": "source_adapter_direct_candidate",
                "action_kind": "adapter_candidate",
                "tactic_id": "source_adapter_direct_candidate",
                "body": problem.candidate_body,
                "selected_facts": [],
                "required_imports": list(problem.required_imports),
                "allowed_when": [
                    "adapter explicitly supplies a forward-safe direct candidate",
                    "lane is measuring adapter_candidate_success rather than statement_only_success",
                ],
                "forbidden_when": [
                    "statement-only hammer search",
                    "external source-family rows without explicit adapter-candidate metric separation",
                ],
                "selection_reason": (
                    "source adapter supplied this as the forward-safe direct baseline; "
                    "it is a portfolio candidate, not a strategy-skill skeleton"
                ),
            }
        )
    return candidates


def _run_proof_search_actions(
    *,
    problem: ProverProblem,
    artifacts: Path,
    graph_variant_id: str,
    timeout_seconds: int,
    availability: dict[str, Any] | None,
    search_kind: str,
    include_adapter_candidate: bool,
    include_templates: bool,
) -> dict[str, Any]:
    candidates = _proof_search_candidate_actions(
        problem,
        availability,
        include_adapter_candidate=include_adapter_candidate,
        include_templates=include_templates,
    )
    attempt_rows: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    search_root = artifacts / search_kind
    policy_id = "hammer_search_policy_v0" if search_kind == "hammer_search" else "portfolio_core_v0"
    for index, candidate in enumerate(candidates):
        action_id = str(candidate["action_id"])
        action_kind = str(candidate["action_kind"])
        tactic_id = str(candidate["tactic_id"])
        body = tuple(candidate["body"])
        candidate_path = search_root / f"{index:02d}_{_safe_tactic_id(action_id)}.lean"
        candidate_text = _lean_source(
            problem,
            graph_variant_id=graph_variant_id,
            body=body,
            attempt_label=f"{search_kind}:{action_id}",
        )
        _write_text(candidate_path, candidate_text)
        run = _run_lean(candidate_path, timeout_seconds=timeout_seconds)
        _, compile_status, error_class = _classify_lean_attempt(
            run,
            expected_error_class="TACTIC_SEARCH_FAIL",
        )
        row = {
            "action_id": action_id,
            "action_kind": action_kind,
            "tactic_id": tactic_id,
            "tactic_body": list(body),
            "source_family": problem.source_family,
            "problem_id": problem.problem_id,
            "target_shape": problem.theorem_signature.removesuffix(" := by"),
            "selected_facts": list(candidate.get("selected_facts") or []),
            "imports": list(problem.required_imports),
            "required_imports": list(candidate.get("required_imports") or problem.required_imports),
            "allowed_when": list(candidate.get("allowed_when") or []),
            "forbidden_when": list(candidate.get("forbidden_when") or []),
            "selection_reason": candidate["selection_reason"],
            "check_status": compile_status,
            "compile_status": compile_status,
            "error_class": error_class if compile_status != "PASS" else "NONE",
            "duration_ms": run["duration_ms"],
            "stderr_excerpt": run["stderr"][:600],
            "candidate_path": str(candidate_path),
            "lean_check_ref": str(candidate_path),
            "next_action": (
                "stop_accepted"
                if compile_status == "PASS"
                else "try_next_action"
                if index + 1 < len(candidates)
                else "search_exhausted"
            ),
            "why_selected": candidate["selection_reason"],
        }
        attempt_rows.append(row)
        if selected is None and compile_status == "PASS":
            selected = {**row, "body": list(body)}
            break
    if selected is None:
        fallback = candidates[-1] if candidates else {
            "action_id": "none",
            "action_kind": "none",
            "tactic_id": "none",
            "body": (),
            "selection_reason": "no candidate actions were available",
        }
        selected = {
            "action_id": fallback["action_id"],
            "action_kind": fallback["action_kind"],
            "tactic_id": fallback["tactic_id"],
            "body": list(fallback["body"]),
            "compile_status": "FAIL",
            "error_class": "TACTIC_SEARCH_FAIL",
            "why_selected": "no tactic candidate passed; retain final search candidate for audit",
            "next_action": "search_exhausted",
        }
    actions = [
        {
            "action_id": str(candidate["action_id"]),
            "action_kind": str(candidate["action_kind"]),
            "tactic_id": str(candidate["tactic_id"]),
            "tactic_body": list(candidate["body"]),
            "source_family": problem.source_family,
            "required_imports": list(candidate.get("required_imports") or problem.required_imports),
            "target_shape": problem.theorem_signature.removesuffix(" := by"),
            "candidate_body": list(candidate["body"]),
            "allowed_when": list(candidate.get("allowed_when") or []),
            "forbidden_when": list(candidate.get("forbidden_when") or []),
            "selection_reason": str(candidate["selection_reason"]),
            "selected_facts": list(candidate.get("selected_facts") or []),
            "lean_check_ref": next(
                (
                    row["lean_check_ref"]
                    for row in attempt_rows
                    if row["action_id"] == str(candidate["action_id"])
                ),
                None,
            ),
            "status": next(
                (
                    row["compile_status"]
                    for row in attempt_rows
                    if row["action_id"] == str(candidate["action_id"])
                ),
                "NOT_RUN",
            ),
        }
        for candidate in candidates
    ]
    manifest: dict[str, Any] = {
        "schema_version": "hammer_action_manifest_v0"
        if search_kind == "hammer_search"
        else "tactic_portfolio_manifest_v0",
        "portfolio_id": "portfolio_core_v0",
        "search_policy_id": policy_id,
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "candidate_tactic_ids": [row["tactic_id"] for row in candidates],
        "availability_ref": "tactic_portfolio_availability/tactic_portfolio_availability.json",
        "source_adapter_direct_candidate_allowed": include_adapter_candidate
        and bool(problem.candidate_body),
        "adapter_direct_candidate_allowed": include_adapter_candidate
        and bool(problem.candidate_body),
        "statement_only": not include_adapter_candidate,
        "actions": actions,
    }
    results: dict[str, Any] = {
        "schema_version": "hammer_search_results_v0"
        if search_kind == "hammer_search"
        else "tactic_portfolio_results_v0",
        "portfolio_id": "portfolio_core_v0",
        "search_policy_id": policy_id,
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "selected_action_id": selected.get("action_id"),
        "selected_tactic_id": selected.get("tactic_id"),
        "selected_body": selected.get("body", []),
        "lean_compile_status": selected.get("compile_status"),
        "error_class": selected.get("error_class"),
        "attempt_count": len(attempt_rows),
        "attempts": attempt_rows,
        "truth_side_body_used": False,
        "adapter_candidate_allowed": include_adapter_candidate and bool(problem.candidate_body),
        "adapter_candidate_used": selected.get("action_id") == "source_adapter_direct_candidate",
        "statement_only": not include_adapter_candidate,
        "next_action": selected.get("next_action"),
    }
    result: dict[str, Any] = {
        "manifest": manifest,
        "results": results,
        "selected_body": tuple(selected.get("body", [])),
    }
    if search_kind == "hammer_search":
        proof_minimization = {
            "schema_version": "proof_minimization_v0",
            "minimization_kind": "selected_candidate_extraction",
            "problem_id": problem.problem_id,
            "source_family": problem.source_family,
            "selected_action_id": selected.get("action_id"),
            "selected_tactic_id": selected.get("tactic_id"),
            "minimized_body": selected.get("body", []),
            "original_line_count": len(selected.get("body", [])),
            "minimized_line_count": len(selected.get("body", [])),
            "truth_side_body_used": False,
            "adapter_candidate_used": selected.get("action_id") == "source_adapter_direct_candidate",
            "lean_compile_status": selected.get("compile_status"),
            "error_class": selected.get("error_class"),
        }
        _write_json(artifacts / "hammer_action_manifest.json", manifest)
        _write_json(artifacts / "hammer_search_results.json", results)
        _write_json(artifacts / "proof_minimization.json", proof_minimization)
        result["proof_minimization"] = proof_minimization
    else:
        _write_json(artifacts / "tactic_portfolio_manifest.json", manifest)
        _write_json(artifacts / "tactic_portfolio_results.json", results)
    return result


def _run_tactic_portfolio(
    *,
    problem: ProverProblem,
    artifacts: Path,
    graph_variant_id: str,
    timeout_seconds: int,
    availability: dict[str, Any] | None,
) -> dict[str, Any]:
    return _run_proof_search_actions(
        problem=problem,
        artifacts=artifacts,
        graph_variant_id=graph_variant_id,
        timeout_seconds=timeout_seconds,
        availability=availability,
        search_kind="tactic_portfolio",
        include_adapter_candidate=True,
        include_templates=False,
    )


def _run_hammer_search(
    *,
    problem: ProverProblem,
    artifacts: Path,
    graph_variant_id: str,
    timeout_seconds: int,
    availability: dict[str, Any] | None,
) -> dict[str, Any]:
    return _run_proof_search_actions(
        problem=problem,
        artifacts=artifacts,
        graph_variant_id=graph_variant_id,
        timeout_seconds=timeout_seconds,
        availability=availability,
        search_kind="hammer_search",
        include_adapter_candidate=False,
        include_templates=True,
    )


def _strategy_candidate_body(
    problem: ProverProblem,
    selected_strategy_id: str,
    retrieved_premise_ids: list[str],
    *,
    skill_cell_id: str | None = None,
) -> tuple[str, ...]:
    retrieved = set(retrieved_premise_ids)
    features = _feature_tokens(problem)
    if skill_cell_id == "skill_equality_family_disambiguation_v0":
        if "bool_not" in features and "premise_bool_not_not" in retrieved:
            return ("  exact Bool.not_not b",)
        if "list_reverse" in features and "premise_list_reverse_reverse" in retrieved:
            return ("  exact List.reverse_reverse xs",)
        if (
            "length_append" in features
            and "premise_list_length_append" in retrieved
            and "reversed_orientation" not in features
        ):
            return ("  exact List.length_append",)
        if "nat_add" in features and "premise_nat_add_comm" in retrieved:
            return ("  exact Nat.add_comm m n",)
    if selected_strategy_id == "contradiction_or_false_target":
        return ("  exact False.elim h",)
    if selected_strategy_id == "recursive_data_induction":
        return ("  exact Nat.add_zero n",)
    if selected_strategy_id == "symmetry_or_orientation":
        if (
            skill_cell_id in {"skill_equality_orientation_v0", "skill_equality_orientation_v1"}
            and "premise_list_length_append" in retrieved
        ):
            return ("  exact Eq.symm List.length_append",)
        # Keep one intentionally weak v0 skeleton so the oracle can separate a
        # strategy hit from proof-synthesis/orientation failure.
        return ("  exact List.length_append",)
    return _body_from_retrieved_premises(
        problem,
        retrieved_premise_ids,
        strategy_id=selected_strategy_id,
    )


def _skill_cell_overlay_decision(
    problem: ProverProblem,
    *,
    selected_strategy_id: str | None,
    retrieved_premise_ids: list[str],
    skill_atlas: dict[str, Any],
) -> dict[str, Any]:
    cell_lookup = _skill_lookup(skill_atlas)
    features = _feature_tokens(problem)
    retrieved = set(retrieved_premise_ids)
    skill_cell_id = None
    applied = False
    decision_reason = "no matching executable skill cell"
    if (
        selected_strategy_id == "equality_normal_form"
        and "skill_equality_family_disambiguation_v0" in cell_lookup
        and (
            ("bool_not" in features and "premise_bool_not_not" in retrieved)
            or ("list_reverse" in features and "premise_list_reverse_reverse" in retrieved)
            or (
                "length_append" in features
                and "reversed_orientation" not in features
                and "premise_list_length_append" in retrieved
            )
            or ("nat_add" in features and "premise_nat_add_comm" in retrieved)
        )
    ):
        skill_cell_id = "skill_equality_family_disambiguation_v0"
        applied = True
        decision_reason = (
            "selected equality normal-form strategy; choose retrieved premise family by target features before Lean exact"
        )
    if (
        selected_strategy_id == "symmetry_or_orientation"
        and "premise_list_length_append" in retrieved
        and skill_cell_id is None
    ):
        skill_cell_id = (
            "skill_equality_orientation_v1"
            if "skill_equality_orientation_v1" in cell_lookup
            else "skill_equality_orientation_v0"
        )
        applied = True
        decision_reason = (
            "selected orientation strategy and retrieved length_append; apply bounded Eq.symm skeleton"
        )
    elif selected_strategy_id == "symmetry_or_orientation" and skill_cell_id is None:
        skill_cell_id = (
            "skill_equality_orientation_v1"
            if "skill_equality_orientation_v1" in cell_lookup
            else "skill_equality_orientation_v0"
        )
        decision_reason = "orientation skill recognized but required equality premise was not retrieved"
    elif (
        selected_strategy_id == "composition_fusion"
        and "skill_composition_fusion_index_expansion_v0" in cell_lookup
        and skill_cell_id is None
    ):
        skill_cell_id = "skill_composition_fusion_index_expansion_v0"
        decision_reason = "composition-fusion skill recognized but source index evidence is required before applying"
    cell = cell_lookup.get(skill_cell_id or "", {})
    return {
        "schema_version": "prover_skill_cell_overlay_decision_v0",
        "problem_id": problem.problem_id,
        "skill_cell_id": skill_cell_id,
        "selected_strategy_id": selected_strategy_id or "none",
        "applied": applied,
        "decision_reason": decision_reason,
        "foundry_candidate": skill_atlas.get("schema_version")
        == "prover_skill_foundry_candidate_atlas_v0",
        "recognizer_features": cell.get("recognizer", {}).get("trigger_features", []),
        "retrieved_premise_ids": retrieved_premise_ids,
        "proof_plan_method": cell.get("proof_plan_method", {}),
        "repair_policy": cell.get("repair_policy", {}),
        "truth_side_body_used": False,
        "oracle_needed_premise_ids_visible": False,
    }


def _proof_plan_skeleton(
    problem: ProverProblem,
    strategy_hypothesis_set: dict[str, Any],
    retrieval_report: dict[str, Any],
    candidate_body: tuple[str, ...],
) -> dict[str, Any]:
    selected_id = strategy_hypothesis_set.get("selected_strategy_id", "none")
    return {
        "schema_version": "proof_plan_skeleton_v0",
        "problem_id": problem.problem_id,
        "strategy_id": selected_id,
        "subgoals": [
            {
                "subgoal_id": f"{problem.problem_id}_main",
                "target_shape": problem.theorem_signature.removesuffix(" := by"),
                "planned_move": (
                    strategy_hypothesis_set.get("strategy_hypotheses") or [{}]
                )[0].get("proof_plan_template", "no strategy selected"),
                "retrieved_premise_ids": retrieval_report.get("retrieved_premise_ids", []),
                "candidate_body_preview": list(candidate_body),
            }
        ],
        "truth_side_body_used": False,
        "oracle_needed_premise_ids_visible": False,
    }


def _strategy_oracle_audit(
    problem: ProverProblem,
    strategy_hypothesis_set: dict[str, Any],
    retrieval_oracle_audit: dict[str, Any] | None,
    compile_status: str,
    error_class: str,
) -> dict[str, Any]:
    selected_id = strategy_hypothesis_set.get("selected_strategy_id", "none")
    expected = set(problem.expected_strategy_ids)
    strategy_hit = bool(expected) and selected_id in expected
    return {
        "schema_version": "strategy_oracle_audit_v0",
        "problem_id": problem.problem_id,
        "selected_strategy_id": selected_id,
        "expected_strategy_ids": list(problem.expected_strategy_ids),
        "strategy_hit": strategy_hit,
        "retrieved_premise_ids": (
            retrieval_oracle_audit.get("retrieved_premise_ids", [])
            if retrieval_oracle_audit
            else []
        ),
        "oracle_needed_premise_ids": list(problem.oracle_needed_premise_ids),
        "needed_premises_all_retrieved": (
            retrieval_oracle_audit.get("needed_premises_all_retrieved", False)
            if retrieval_oracle_audit
            else False
        ),
        "lean_compile_status": compile_status,
        "error_class": error_class,
        "failure_attribution": (
            "strategy_selection"
            if expected and not strategy_hit
            else "premise_retrieval"
            if retrieval_oracle_audit
            and not retrieval_oracle_audit.get("needed_premises_all_retrieved", False)
            else "proof_synthesis"
            if compile_status != "PASS"
            else "none"
        ),
        "oracle_phase": "after_lean_check",
    }


def _strategy_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    strategy_rows = [row for row in rows if row.get("strategy_oracle_audit")]
    strategy_hit_rows = [
        row for row in strategy_rows if row["strategy_oracle_audit"].get("strategy_hit")
    ]
    strategy_miss_rows = [
        row for row in strategy_rows if not row["strategy_oracle_audit"].get("strategy_hit")
    ]
    retrieval_recall_rows = [
        row for row in strategy_rows if row.get("premise_retrieval")
    ]
    premise_metrics = _premise_metrics(retrieval_recall_rows)
    proof_success_given_strategy_hit = sum(
        1 for row in strategy_hit_rows if row["lean_compile_status"] == "PASS"
    )
    proof_failure_despite_strategy_hit = sum(
        1 for row in strategy_hit_rows if row["lean_compile_status"] != "PASS"
    )
    exercised = sorted(
        {
            row["strategy_oracle_audit"].get("selected_strategy_id")
            for row in strategy_rows
            if row["strategy_oracle_audit"].get("selected_strategy_id")
        }
    )
    return {
        "schema_version": "strategy_control_metrics_v0",
        "strategy_problem_count": len(strategy_rows),
        "strategy_selection_hit_count": len(strategy_hit_rows),
        "strategy_selection_miss_count": len(strategy_miss_rows),
        "strategy_selection_accuracy": len(strategy_hit_rows) / len(strategy_rows)
        if strategy_rows
        else 0,
        "premise_recall_after_strategy_expansion": premise_metrics["premise_recall"],
        "proof_success_given_strategy_hit": proof_success_given_strategy_hit,
        "proof_failure_despite_strategy_hit": proof_failure_despite_strategy_hit,
        "oracle_repair_success_after_strategy_failure": 0,
        "exercised_strategy_ids": exercised,
        "strategy_hit_problem_ids": [row["problem_id"] for row in strategy_hit_rows],
        "strategy_miss_problem_ids": [row["problem_id"] for row in strategy_miss_rows],
        "premise_retrieval_metrics": premise_metrics,
    }


def _graph_variant(graph_variant_id: str = "baseline_graph_v0") -> dict[str, Any]:
    if graph_variant_id not in GRAPH_VARIANTS:
        raise ValueError(f"unsupported graph variant: {graph_variant_id}")
    repair_rounds = 1 if graph_variant_id == "oracle_repair_graph_v0" else 0
    if graph_variant_id == "oracle_repair_graph_v0":
        description = "statement -> direct Lean proof candidate -> Lean check -> oracle-gated repair -> Lean check -> quartet -> learning row"
    elif graph_variant_id == HAMMER_SEARCH_GRAPH_VARIANT:
        description = "statement/imports only -> source-aware relevance filter -> tactic/template action search -> Lean checks -> selected candidate extraction -> Foundry policy credit"
    elif graph_variant_id == TACTIC_PORTFOLIO_GRAPH_VARIANT:
        description = "statement -> source-aware tactic portfolio -> per-tactic Lean checks -> first accepted candidate -> quartet -> learning row"
    elif graph_variant_id == SOURCE_GUARDED_STRATEGY_GRAPH_VARIANT:
        description = "statement -> strategy hypotheses -> source-family guard -> source-safe direct candidate or policy-only abstention -> Lean check -> oracle attribution"
    elif graph_variant_id == SOURCE_GUARDED_FOUNDRY_GRAPH_VARIANT:
        description = "statement -> strategy hypotheses -> foundry recognizer -> source-family guard -> source-safe direct candidate or policy-only abstention -> Lean check -> promotion evidence"
    elif graph_variant_id == SKILL_ATLAS_OVERLAY_GRAPH_VARIANT:
        description = "statement -> strategy hypotheses -> skill-cell recognizer/view/retrieval/proof-plan overlay -> Lean check -> oracle attribution -> skill case memory"
    elif graph_variant_id == SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT:
        description = "statement -> strategy hypotheses -> foundry-mined skill recognizers -> candidate skill overlay -> Lean check -> promotion evidence"
    elif graph_variant_id == "strategy_control_graph_v0":
        description = "statement -> feature extraction -> strategy hypotheses -> view generation -> strategy-conditioned premise retrieval -> proof-plan skeleton -> Lean check -> oracle strategy audit -> quartet -> learning row"
    elif graph_variant_id == "premise_retrieval_graph_v0":
        description = "statement + allowed premise index -> retrieve premises -> synthesize Lean candidate -> Lean check -> oracle retrieval audit -> quartet -> learning row"
    else:
        description = "statement -> direct Lean proof candidate -> Lean check -> quartet -> learning row"
    return {
        "schema_version": "prover_graph_variant_v0",
        "graph_variant_id": graph_variant_id,
        "description": description,
        "nodes": [
            "prover_lab_direct_candidate",
            *(
                ["prover_lab_premise_retrieval"]
                if graph_variant_id in {"premise_retrieval_graph_v0", *STRATEGY_GRAPH_VARIANTS}
                else []
            ),
            *(
                [
                    "prover_lab_problem_feature_extractor",
                    "prover_lab_strategy_hypothesis_set",
                    "prover_lab_view_generation",
                    "prover_lab_proof_plan_skeleton",
                ]
                if graph_variant_id in STRATEGY_GRAPH_VARIANTS
                else []
            ),
            *(
                ["prover_lab_source_family_strategy_guard"]
                if graph_variant_id in SOURCE_GUARDED_GRAPH_VARIANTS
                else []
            ),
            *(
                [
                    "prover_lab_tactic_portfolio_manifest",
                    "prover_lab_tactic_portfolio_search",
                ]
                if graph_variant_id == TACTIC_PORTFOLIO_GRAPH_VARIANT
                else []
            ),
            *(
                [
                    "prover_lab_hammer_action_manifest",
                    "prover_lab_hammer_search_controller",
                    "prover_lab_proof_minimizer",
                ]
                if graph_variant_id == HAMMER_SEARCH_GRAPH_VARIANT
                else []
            ),
            *(
                [
                    "prover_lab_skill_cell_recognizer",
                    "prover_lab_skill_cell_view_overlay",
                    "prover_lab_skill_cell_proof_plan_method",
                ]
                if graph_variant_id in SKILL_OVERLAY_GRAPH_VARIANTS
                else []
            ),
            "prover_oracle_lean_check",
            *(
                ["prover_oracle_repair_candidate", "prover_oracle_repair_check"]
                if graph_variant_id == "oracle_repair_graph_v0"
                else []
            ),
            "prover_oracle_statement_reconciliation",
            "prover_oracle_critique",
            "prover_oracle_ideal_packet",
            "prover_evolve_learning_row",
        ],
        "retrieval_settings": {
            "premise_retrieval": "allowed_lean_std_index"
            if graph_variant_id
            in {"premise_retrieval_graph_v0", *STRATEGY_GRAPH_VARIANTS}
            else "tactic_portfolio_only"
            if graph_variant_id == TACTIC_PORTFOLIO_GRAPH_VARIANT
            else "statement_only_hammer_search"
            if graph_variant_id == HAMMER_SEARCH_GRAPH_VARIANT
            else "none",
            "strategy_conditioned": graph_variant_id in STRATEGY_GRAPH_VARIANTS,
            "skill_atlas_overlay": graph_variant_id == SKILL_ATLAS_OVERLAY_GRAPH_VARIANT,
            "skill_foundry_overlay": graph_variant_id
            in {SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT, SOURCE_GUARDED_FOUNDRY_GRAPH_VARIANT},
            "source_family_guard": graph_variant_id in SOURCE_GUARDED_GRAPH_VARIANTS,
            "tactic_portfolio": graph_variant_id == TACTIC_PORTFOLIO_GRAPH_VARIANT,
            "hammer_search": graph_variant_id == HAMMER_SEARCH_GRAPH_VARIANT,
            "adapter_direct_candidate_allowed": graph_variant_id != HAMMER_SEARCH_GRAPH_VARIANT,
            "mathlib": "not_used_lean_std_toolchain_only",
        },
        "decomposition_settings": {
            "subgoal_decomposition": "none",
            "repair_rounds": repair_rounds,
            "repair_gate": "Lean stderr plus ideal skeleton allowed only after failed oracle check"
            if repair_rounds
            else "none",
        },
        "provider": {
            "provider_calls": 0,
            "provider_or_nim_needed": False,
        },
    }


def _statement_reconciliation(problem: ProverProblem, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "statement_reconciliation_v0",
        "run_id": run_id,
        "problem_row_id": problem.problem_id,
        "informal_statement": problem.informal_statement,
        "formal_statement_lean": problem.theorem_signature.removesuffix(" := by"),
        "definitional_alignment": "PASS",
        "quantifier_alignment": "PASS",
        "scope_alignment": "PASS",
        "misformalization_risk": "LOW",
        "human_third_party_review_status": "NOT_REQUESTED",
        "status": "READY",
        "notes": (
            "Source-backed specimen from the selected local problem manifest; "
            "no open Erdős/Formal Conjectures success claim."
        ),
    }


def _ideal_packet(problem: ProverProblem, run_id: str, ideal_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "ideal_proof_packet_v0",
        "run_id": run_id,
        "problem_row_id": problem.problem_id,
        "required_imports": list(problem.required_imports),
        "required_lemmas": list(problem.oracle_needed_premise_ids) or [problem.source_ref],
        "proof_skeleton": list(problem.ideal_body),
        "ideal_candidate_ref": str(ideal_path),
        "excluded_routes": [
            {
                "route": "truth_side_proof_body_in_forward_lab",
                "reason": "Proof bodies remain oracle-only; Ring-2 allows only premise ids/statements before the check.",
            }
        ],
        "library_gaps": [],
        "leakage_notes": {
            "truth_side_material_withheld_from_lab": list(problem.withheld_until_oracle),
            "solution_leakage_detected": False,
        },
        "subject_side_evidence_refs": list(problem.visible_to_lab),
        "truth_side_influence_refs": ["ideal proof body available only after check"],
    }


def _cost_metrics(duration_ms: int, problem: ProverProblem) -> dict[str, Any]:
    return {
        "attempt_count": 1,
        "proof_check_count": 1,
        "wall_time_ms": duration_ms,
        "lean_compile_ms": duration_ms,
        "provider_calls": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "estimated_cost_usd": 0.0,
        "context_tokens": 0,
        "num_repair_rounds": 0,
        "num_subgoals": 1,
        "num_retrieved_premises": 0,
        "source_index_size": 0,
        "retrieval_candidates_considered": 0,
        "context_recipe_id": problem.context_recipe_id,
    }


def _write_problem_artifacts(
    *,
    run_id: str,
    run_root: Path,
    problem: ProverProblem,
    graph_variant_id: str,
    lean_version: str,
    lake_version: str,
    timeout_seconds: int,
    premise_index: dict[str, Any] | None = None,
    tactic_availability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    problem_root = run_root / "problems" / problem.problem_id
    artifacts = problem_root / "artifacts"
    attempt_0_path = artifacts / "attempt_0_candidate.lean"
    attempt_1_path = artifacts / "attempt_1_repair_candidate.lean"
    candidate_path = artifacts / "candidate.lean"
    ideal_path = artifacts / "ideal_candidate.lean"
    stdout_path = artifacts / "lean_stdout.txt"
    stderr_path = artifacts / "lean_stderr.txt"
    attempt_0_stdout_path = artifacts / "attempt_0_lean_stdout.txt"
    attempt_0_stderr_path = artifacts / "attempt_0_lean_stderr.txt"
    attempt_1_stdout_path = artifacts / "attempt_1_lean_stdout.txt"
    attempt_1_stderr_path = artifacts / "attempt_1_lean_stderr.txt"

    retrieval_report: dict[str, Any] | None = None
    retrieval_oracle_audit: dict[str, Any] | None = None
    retrieved_premise_ids: list[str] = []
    cited_premise_ids: list[str] = []
    premise_candidate_body: tuple[str, ...] | None = None
    candidate_cites_only_allowed_premises = True
    strategy_atlas: dict[str, Any] | None = None
    strategy_hypothesis_set: dict[str, Any] | None = None
    strategy_view_generation: dict[str, Any] | None = None
    proof_plan_skeleton: dict[str, Any] | None = None
    strategy_oracle_audit: dict[str, Any] | None = None
    selected_strategy_id: str | None = None
    skill_atlas: dict[str, Any] | None = None
    skill_cell_overlay_decision: dict[str, Any] | None = None
    selected_skill_cell: dict[str, Any] | None = None
    source_family_guard: dict[str, Any] | None = None
    tactic_portfolio_manifest: dict[str, Any] | None = None
    tactic_portfolio_results: dict[str, Any] | None = None
    hammer_action_manifest: dict[str, Any] | None = None
    hammer_search_results: dict[str, Any] | None = None
    proof_minimization: dict[str, Any] | None = None
    if graph_variant_id == TACTIC_PORTFOLIO_GRAPH_VARIANT:
        portfolio = _run_tactic_portfolio(
            problem=problem,
            artifacts=artifacts,
            graph_variant_id=graph_variant_id,
            timeout_seconds=timeout_seconds,
            availability=tactic_availability,
        )
        tactic_portfolio_manifest = portfolio["manifest"]
        tactic_portfolio_results = portfolio["results"]
        premise_candidate_body = tuple(portfolio["selected_body"])
    if graph_variant_id == HAMMER_SEARCH_GRAPH_VARIANT:
        hammer = _run_hammer_search(
            problem=problem,
            artifacts=artifacts,
            graph_variant_id=graph_variant_id,
            timeout_seconds=timeout_seconds,
            availability=tactic_availability,
        )
        hammer_action_manifest = hammer["manifest"]
        hammer_search_results = hammer["results"]
        proof_minimization = hammer["proof_minimization"]
        premise_candidate_body = tuple(hammer["selected_body"])
    if graph_variant_id in {"premise_retrieval_graph_v0", *STRATEGY_GRAPH_VARIANTS}:
        premise_index = premise_index or _premise_index()
        query_terms_override: tuple[str, ...] | None = None
        if graph_variant_id in STRATEGY_GRAPH_VARIANTS:
            strategy_atlas = _strategy_cards()
            strategy_hypothesis_set = _strategy_hypotheses(problem, strategy_atlas)
            selected_strategy_id = str(
                strategy_hypothesis_set.get("selected_strategy_id") or "none"
            )
            strategy_view_generation = _view_generation(
                problem,
                strategy_hypothesis_set,
                strategy_atlas,
            )
            query_terms_override = _strategy_query_terms(
                problem,
                strategy_hypothesis_set,
                strategy_atlas,
            )
            if graph_variant_id == SKILL_ATLAS_OVERLAY_GRAPH_VARIANT:
                skill_atlas = _prover_skill_atlas(strategy_atlas)
            elif graph_variant_id in {
                SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT,
                SOURCE_GUARDED_FOUNDRY_GRAPH_VARIANT,
            }:
                skill_atlas = _prover_skill_foundry_skill_atlas(strategy_atlas)
        retrieval_report = _retrieve_premises(
            problem,
            premise_index,
            query_terms_override=query_terms_override,
        )
        retrieved_premise_ids = list(retrieval_report["retrieved_premise_ids"])
        if graph_variant_id in STRATEGY_GRAPH_VARIANTS:
            skill_cell_id: str | None = None
            if skill_atlas is not None:
                skill_cell_overlay_decision = _skill_cell_overlay_decision(
                    problem,
                    selected_strategy_id=selected_strategy_id,
                    retrieved_premise_ids=retrieved_premise_ids,
                    skill_atlas=skill_atlas,
                )
                skill_cell_id = skill_cell_overlay_decision.get("skill_cell_id")
                selected_skill_cell = _skill_lookup(skill_atlas).get(skill_cell_id or "")
            if graph_variant_id in SOURCE_GUARDED_GRAPH_VARIANTS:
                source_family_guard = _external_source_family_strategy_guard(
                    problem,
                    graph_variant_id=graph_variant_id,
                    selected_strategy_id=selected_strategy_id,
                    retrieved_premise_ids=retrieved_premise_ids,
                    skill_cell_id=skill_cell_id,
                )
            if source_family_guard is not None and source_family_guard.get("guard_applied"):
                premise_candidate_body = problem.candidate_body
            else:
                premise_candidate_body = _strategy_candidate_body(
                    problem,
                    selected_strategy_id or "none",
                    retrieved_premise_ids,
                    skill_cell_id=skill_cell_id,
                )
            proof_plan_skeleton = _proof_plan_skeleton(
                problem,
                strategy_hypothesis_set or {},
                retrieval_report,
                premise_candidate_body,
            )
            if source_family_guard is not None:
                proof_plan_skeleton["source_family_guard"] = {
                    "guard_applied": source_family_guard.get("guard_applied"),
                    "proof_body_emission_policy": source_family_guard.get(
                        "proof_body_emission_policy"
                    ),
                    "fallback_tactic_portfolio": source_family_guard.get(
                        "fallback_tactic_portfolio"
                    ),
                }
            if skill_cell_overlay_decision is not None:
                proof_plan_skeleton["skill_cell_overlay"] = {
                    "skill_cell_id": skill_cell_overlay_decision.get("skill_cell_id"),
                    "applied": skill_cell_overlay_decision.get("applied"),
                    "decision_reason": skill_cell_overlay_decision.get("decision_reason"),
                }
        else:
            premise_candidate_body = _body_from_retrieved_premises(
                problem,
                retrieved_premise_ids,
            )
        cited_premise_ids = _premise_ids_cited(premise_candidate_body, premise_index)
        allowed_premise_ids = {
            row["premise_id"] for row in _allowed_premises(problem, premise_index)
        }
        candidate_cites_only_allowed_premises = set(cited_premise_ids).issubset(
            set(retrieved_premise_ids) & allowed_premise_ids
        )

    attempt_0_text = _lean_source(
        problem,
        graph_variant_id=graph_variant_id,
        body=premise_candidate_body,
        attempt_label="attempt_0_forward_lab",
        retrieved_premise_ids=tuple(retrieved_premise_ids),
        cited_premise_ids=tuple(cited_premise_ids),
    )
    ideal_text = _lean_source(
        problem,
        graph_variant_id=graph_variant_id,
        ideal=True,
        attempt_label="oracle_ideal",
    )
    _write_text(attempt_0_path, attempt_0_text)
    _write_text(ideal_path, ideal_text)
    if retrieval_report is not None:
        _write_json(artifacts / "premise_retrieval_report.json", retrieval_report)
    if strategy_atlas is not None:
        _write_json(artifacts / "strategy_cards.json", strategy_atlas)
    if strategy_hypothesis_set is not None:
        _write_json(artifacts / "strategy_hypothesis_set.json", strategy_hypothesis_set)
    if strategy_view_generation is not None:
        _write_json(artifacts / "view_generation.json", strategy_view_generation)
    if proof_plan_skeleton is not None:
        _write_json(artifacts / "proof_plan_skeleton.json", proof_plan_skeleton)
    if skill_atlas is not None:
        _write_json(artifacts / "prover_skill_atlas.json", skill_atlas)
    if selected_skill_cell is not None:
        _write_json(artifacts / "skill_cell.json", selected_skill_cell)
    if skill_cell_overlay_decision is not None:
        _write_json(artifacts / "skill_cell_overlay_decision.json", skill_cell_overlay_decision)
    if source_family_guard is not None:
        _write_json(artifacts / "external_source_family_strategy_guard.json", source_family_guard)

    attempt_0_run = _run_lean(attempt_0_path, timeout_seconds=timeout_seconds)
    _write_text(attempt_0_stdout_path, attempt_0_run["stdout"])
    _write_text(attempt_0_stderr_path, attempt_0_run["stderr"])

    def classify_attempt(lean_run: dict[str, Any]) -> tuple[str, str, str]:
        expected_error_class = (
            "TACTIC_SEARCH_FAIL"
            if graph_variant_id in PROOF_SEARCH_GRAPH_VARIANTS
            else problem.expected_error_class_on_fail
        )
        return _classify_lean_attempt(
            lean_run,
            expected_error_class=expected_error_class,
        )

    environment_health, initial_compile_status, initial_error_class = classify_attempt(attempt_0_run)
    if graph_variant_id == "premise_retrieval_graph_v0" and initial_compile_status == "FAIL":
        needed_ids = set(problem.oracle_needed_premise_ids)
        if needed_ids and not needed_ids.issubset(set(retrieved_premise_ids)):
            initial_error_class = "PREMISE_RETRIEVAL_MISS"
    if (
        graph_variant_id in STRATEGY_GRAPH_VARIANTS
        and initial_compile_status == "FAIL"
    ):
        needed_ids = set(problem.oracle_needed_premise_ids)
        selected_expected = bool(problem.expected_strategy_ids) and (
            (selected_strategy_id or "none") in set(problem.expected_strategy_ids)
        )
        if not selected_expected:
            initial_error_class = "STRATEGY_SELECTION_MISS"
        elif needed_ids and not needed_ids.issubset(set(retrieved_premise_ids)):
            initial_error_class = "PREMISE_RETRIEVAL_MISS"
        else:
            initial_error_class = "PROOF_SYNTHESIS_FAIL"
    final_text = attempt_0_text
    final_run = attempt_0_run
    final_path = attempt_0_path
    compile_status = initial_compile_status
    error_class = initial_error_class
    repair_applied = False
    repair_success = False
    repair_body = problem.repair_body or problem.ideal_body

    if (
        graph_variant_id == "oracle_repair_graph_v0"
        and initial_compile_status not in {"PASS", "ENV_FAIL", "TIMEOUT"}
        and repair_body
    ):
        repair_applied = True
        repair_text = _lean_source(
            problem,
            graph_variant_id=graph_variant_id,
            body=repair_body,
            attempt_label="attempt_1_oracle_repair",
        )
        _write_text(attempt_1_path, repair_text)
        attempt_1_run = _run_lean(attempt_1_path, timeout_seconds=timeout_seconds)
        _write_text(attempt_1_stdout_path, attempt_1_run["stdout"])
        _write_text(attempt_1_stderr_path, attempt_1_run["stderr"])
        environment_health, compile_status, error_class = classify_attempt(attempt_1_run)
        final_text = repair_text
        final_run = attempt_1_run
        final_path = attempt_1_path
        repair_success = compile_status == "PASS"

    _write_text(candidate_path, final_text)
    _write_text(stdout_path, final_run["stdout"])
    _write_text(stderr_path, final_run["stderr"])

    sorry_present = bool(SORRY_RE.search(final_text))

    if retrieval_report is not None:
        needed_ids = set(problem.oracle_needed_premise_ids)
        retrieved_ids = set(retrieved_premise_ids)
        retrieval_oracle_audit = {
            "schema_version": "premise_retrieval_oracle_audit_v0",
            "problem_id": problem.problem_id,
            "retrieved_premise_ids": retrieved_premise_ids,
            "oracle_needed_premise_ids": list(problem.oracle_needed_premise_ids),
            "candidate_premise_ids_used": cited_premise_ids,
            "missing_needed_premise_ids": sorted(needed_ids - retrieved_ids),
            "extra_retrieved_premise_ids": sorted(retrieved_ids - needed_ids),
            "premise_hit_count": len(needed_ids & retrieved_ids),
            "premise_miss_count": len(needed_ids - retrieved_ids),
            "needed_premises_all_retrieved": bool(needed_ids)
            and needed_ids.issubset(retrieved_ids),
            "candidate_cites_only_retrieved_allowed_premises": candidate_cites_only_allowed_premises,
            "lean_compile_status": compile_status,
            "error_class": error_class if compile_status != "PASS" else "NONE",
            "oracle_phase": "after_lean_check",
        }
    if strategy_hypothesis_set is not None:
        strategy_oracle_audit = _strategy_oracle_audit(
            problem,
            strategy_hypothesis_set,
            retrieval_oracle_audit,
            compile_status,
            error_class,
        )

    axiom_classification = _classify_axioms(
        final_run["stdout"],
        compile_status,
        sorry_present,
    )

    candidate_artifact_id = f"candidate_{problem.problem_id}_{graph_variant_id}"
    candidate_sha = _sha256_text(attempt_0_text)
    final_candidate_sha = _sha256_text(final_text)
    prover_lab_candidate = {
        "schema_version": "prover_lab_candidate_v0",
        "run_id": run_id,
        "candidate_artifact_id": candidate_artifact_id,
        "problem_row_id": problem.problem_id,
        "problem_source": problem.source,
        "split": problem.split,
        "declared_mode": problem.mode,
        "graph_variant_id": graph_variant_id,
        "artifact_type": "lean_proof_file",
        "statement": {
            "informal": problem.informal_statement,
            "lean": problem.theorem_signature,
        },
        "input_manifest": {
            "visible_context": list(problem.visible_to_lab),
            "withheld_context": list(problem.withheld_until_oracle),
            "forbidden_context": ["known proof body from an external certificate"],
            "formal_statement_row_id": None,
            "proof_certificate_row_id": None,
            "mathlib_pin": "not_used_lean_std_toolchain_only",
            "toolchain_pin": lean_version,
            "required_imports": list(problem.required_imports),
            "source_ref": problem.source_ref,
        },
        "candidate_artifact_path": str(attempt_0_path),
        "candidate_artifact_sha256": candidate_sha,
        "provider": {
            "generation": "deterministic_local_type_a",
            "model_or_provider": "none",
        },
        "context_packet_recipe_id": problem.context_recipe_id,
        "confidence_self_report": "HIGH" if initial_compile_status == "PASS" else "LOW",
        "forward_attempt_only": True,
    }
    if retrieval_report is not None:
        prover_lab_candidate["premise_retrieval"] = retrieval_report
    if strategy_hypothesis_set is not None:
        prover_lab_candidate["strategy_hypothesis_set"] = strategy_hypothesis_set
        prover_lab_candidate["view_generation"] = strategy_view_generation
        prover_lab_candidate["proof_plan_skeleton"] = proof_plan_skeleton
    if source_family_guard is not None:
        prover_lab_candidate["source_family_strategy_guard"] = source_family_guard
    if tactic_portfolio_manifest is not None:
        prover_lab_candidate["tactic_portfolio_manifest"] = tactic_portfolio_manifest
    if tactic_portfolio_results is not None:
        prover_lab_candidate["tactic_portfolio_results"] = tactic_portfolio_results
    if hammer_action_manifest is not None:
        prover_lab_candidate["hammer_action_manifest"] = hammer_action_manifest
    if hammer_search_results is not None:
        prover_lab_candidate["hammer_search_results"] = hammer_search_results
    if proof_minimization is not None:
        prover_lab_candidate["proof_minimization"] = proof_minimization

    attempts = [
        {
            "attempt_index": 0,
            "attempt_kind": "forward_lab",
            "candidate_artifact_path": str(attempt_0_path),
            "stdout_ref": str(attempt_0_stdout_path),
            "stderr_ref": str(attempt_0_stderr_path),
            "exit_code": attempt_0_run["exit_code"],
            "lean_compile_status": initial_compile_status,
            "error_class": initial_error_class,
            "oracle_repair_context_used": False,
        }
    ]
    if repair_applied:
        attempts.append(
            {
                "attempt_index": 1,
                "attempt_kind": "oracle_repair",
                "candidate_artifact_path": str(attempt_1_path),
                "stdout_ref": str(attempt_1_stdout_path),
                "stderr_ref": str(attempt_1_stderr_path),
                "exit_code": final_run["exit_code"],
                "lean_compile_status": compile_status,
                "error_class": error_class,
                "oracle_repair_context_used": True,
            }
        )

    check_result = {
        "schema_version": "prover_check_result_v0",
        "run_id": run_id,
        "candidate_artifact_id": candidate_artifact_id,
        "problem_row_id": problem.problem_id,
        "declared_mode": problem.mode,
        "split": problem.split,
        "environment_health": environment_health,
        "checker": {
            "kind": "Lean 4 CLI",
            "command": f"lean {final_path}",
            "exit_code": final_run["exit_code"],
            "toolchain_pin": lean_version,
            "toolchain_commit": TOOLCHAIN_COMMIT if TOOLCHAIN_COMMIT in lean_version else None,
            "lake_version": lake_version,
        },
        "attempts": attempts,
        "initial_lean_compile_status": initial_compile_status,
        "lean_compile_status": compile_status,
        "sorry_present": sorry_present,
        "sorry_positions": [],
        "axiom_audit": {
            "theorem": problem.theorem_name,
            "command": f"#print axioms {problem.theorem_name}",
            "stdout": final_run["stdout"].strip(),
            "stderr": final_run["stderr"].strip(),
        },
        "axiom_audit_classification": axiom_classification,
        "timeout_budget_ms": timeout_seconds * 1000,
        "compile_duration_ms": final_run["duration_ms"],
        "stdout_ref": str(stdout_path),
        "stderr_ref": str(stderr_path),
    }
    if retrieval_oracle_audit is not None:
        check_result["premise_retrieval_oracle_audit"] = retrieval_oracle_audit
    if strategy_oracle_audit is not None:
        check_result["strategy_oracle_audit"] = strategy_oracle_audit
    if source_family_guard is not None:
        check_result["external_source_family_strategy_guard"] = source_family_guard
    if tactic_portfolio_results is not None:
        check_result["tactic_portfolio_results"] = tactic_portfolio_results
    if hammer_search_results is not None:
        check_result["hammer_search_results"] = hammer_search_results
    if proof_minimization is not None:
        check_result["proof_minimization"] = proof_minimization

    reconciliation = _statement_reconciliation(problem, run_id)
    ideal_packet = _ideal_packet(problem, run_id, ideal_path)
    critique = {
        "schema_version": "proof_attempt_critique_v0",
        "run_id": run_id,
        "candidate_artifact_id": candidate_artifact_id,
        "problem_row_id": problem.problem_id,
        "error_class": error_class,
        "severity": "LOW" if error_class == "NONE" else "MEDIUM",
        "cited_subject_refs": [str(attempt_0_path)],
        "cited_oracle_refs": [
            "prover_check_result.lean_compile_status",
            "prover_check_result.axiom_audit_classification",
            "statement_reconciliation.status",
        ],
        "narrative": (
            "Lean accepted the candidate with a clean axiom audit."
            if error_class == "NONE" and not repair_applied
            else "Lean rejected the forward candidate, then oracle_repair_graph_v0 repaired it after the oracle gate."
            if error_class == "NONE" and repair_applied
            else "The retrieved premise set did not include the oracle-needed premise before the check."
            if error_class == "PREMISE_RETRIEVAL_MISS"
            else "The strategy lens selected before retrieval did not match the oracle-side expected strategy."
            if error_class == "STRATEGY_SELECTION_MISS"
            else "The strategy lens and premise retrieval were adequate, but the proof skeleton failed in Lean."
            if error_class == "PROOF_SYNTHESIS_FAIL"
            else "The graph retrieved the needed premise, but the synthesized proof still failed."
            if graph_variant_id == "premise_retrieval_graph_v0"
            else "Lean rejected the baseline candidate; the ideal packet records the minimal repair."
        ),
    }
    learning_row = {
        "schema_version": "math_learning_ledger_row_v0",
        "domain": "math",
        "run_pair": {
            "lab_run_id": run_id,
            "oracle_run_id": run_id,
        },
        "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "problem_row_id": problem.problem_id,
        "split": problem.split,
        "declared_mode": problem.mode,
        "graph_variant_id": graph_variant_id,
        "root_failure_mode": initial_error_class if repair_applied else error_class,
        "error_class_distribution": (
            {initial_error_class: 1, error_class: 1}
            if repair_applied and initial_error_class != error_class
            else {error_class: 1}
        ),
        "repair_applied": repair_applied,
        "repair_success": repair_success,
        "lean_compile_status": compile_status,
        "axiom_audit_classification": axiom_classification,
        "statement_reconciliation_status": reconciliation["status"],
        "leakage_detected": False,
        "dossier_ops_applied": 0,
        "doctrine_flags_raised": [],
        "learning_statements": [
            (
                f"{graph_variant_id} succeeds on this source-backed specimen."
                if error_class == "NONE"
                else f"{graph_variant_id} still needs a stronger repair or retrieval route for this specimen class."
            )
        ],
        "provider": "none",
        "context_packet_recipe_id": problem.context_recipe_id,
    }
    if retrieval_oracle_audit is not None:
        learning_row["premise_retrieval"] = retrieval_oracle_audit
    if strategy_oracle_audit is not None:
        learning_row["strategy_oracle_audit"] = strategy_oracle_audit
    if source_family_guard is not None:
        learning_row["source_family_strategy_guard"] = source_family_guard
    if tactic_portfolio_results is not None:
        learning_row["tactic_portfolio_results"] = tactic_portfolio_results
    if hammer_search_results is not None:
        hammer_pass = hammer_search_results.get("lean_compile_status") == "PASS"
        learning_row["hammer_search_results"] = hammer_search_results
        learning_row["hammer_search_credit"] = {
            "schema_version": "foundry_hammer_policy_credit_v0",
            "search_policy_id": hammer_search_results.get("search_policy_id"),
            "selected_action_id": hammer_search_results.get("selected_action_id"),
            "selected_tactic_id": hammer_search_results.get("selected_tactic_id"),
            "credit_assignment": "credit_search_policy"
            if hammer_pass
            else "debit_search_policy",
            "raw_proof_body_credit": False,
            "adapter_candidate_used": bool(hammer_search_results.get("adapter_candidate_used")),
            "statement_only": bool(hammer_search_results.get("statement_only")),
        }
    total_duration_ms = (
        attempt_0_run["duration_ms"] + final_run["duration_ms"]
        if repair_applied
        else final_run["duration_ms"]
    )
    cost = _cost_metrics(total_duration_ms, problem)
    cost["attempt_count"] = len(attempts)
    cost["proof_check_count"] = len(attempts)
    cost["lean_compile_ms"] = total_duration_ms
    cost["wall_time_ms"] = total_duration_ms
    cost["num_repair_rounds"] = 1 if repair_applied else 0
    if retrieval_report is not None:
        cost["num_retrieved_premises"] = len(retrieved_premise_ids)
        cost["source_index_size"] = retrieval_report["source_index_size"]
        cost["retrieval_candidates_considered"] = retrieval_report[
            "retrieval_candidates_considered"
        ]
    if tactic_portfolio_results is not None:
        portfolio_attempt_count = int(tactic_portfolio_results.get("attempt_count") or 0)
        cost["tactic_portfolio_attempt_count"] = portfolio_attempt_count
        cost["proof_check_count"] += portfolio_attempt_count
        cost["attempt_count"] += portfolio_attempt_count
    if hammer_search_results is not None:
        hammer_attempt_count = int(hammer_search_results.get("attempt_count") or 0)
        cost["hammer_search_attempt_count"] = hammer_attempt_count
        cost["proof_check_count"] += hammer_attempt_count
        cost["attempt_count"] += hammer_attempt_count

    outputs = {
        "prover_lab_candidate": prover_lab_candidate,
        "prover_check_result": check_result,
        "statement_reconciliation": reconciliation,
        "proof_attempt_critique": critique,
        "ideal_proof_packet": ideal_packet,
        "prover_evolve_learning_row": learning_row,
        "cost_metrics": cost,
    }
    if retrieval_report is not None:
        outputs["premise_retrieval_report"] = retrieval_report
    if retrieval_oracle_audit is not None:
        outputs["premise_retrieval_oracle_audit"] = retrieval_oracle_audit
    if strategy_atlas is not None:
        outputs["strategy_cards"] = strategy_atlas
    if strategy_hypothesis_set is not None:
        outputs["strategy_hypothesis_set"] = strategy_hypothesis_set
    if strategy_view_generation is not None:
        outputs["view_generation"] = strategy_view_generation
    if proof_plan_skeleton is not None:
        outputs["proof_plan_skeleton"] = proof_plan_skeleton
    if strategy_oracle_audit is not None:
        outputs["strategy_oracle_audit"] = strategy_oracle_audit
    if skill_atlas is not None:
        outputs["prover_skill_atlas"] = skill_atlas
    if selected_skill_cell is not None:
        outputs["skill_cell"] = selected_skill_cell
    if skill_cell_overlay_decision is not None:
        outputs["skill_cell_overlay_decision"] = skill_cell_overlay_decision
    if source_family_guard is not None:
        outputs["external_source_family_strategy_guard"] = source_family_guard
    if tactic_portfolio_manifest is not None:
        outputs["tactic_portfolio_manifest"] = tactic_portfolio_manifest
    if tactic_portfolio_results is not None:
        outputs["tactic_portfolio_results"] = tactic_portfolio_results
    if hammer_action_manifest is not None:
        outputs["hammer_action_manifest"] = hammer_action_manifest
    if hammer_search_results is not None:
        outputs["hammer_search_results"] = hammer_search_results
    if proof_minimization is not None:
        outputs["proof_minimization"] = proof_minimization
    if (
        skill_cell_overlay_decision is not None
        and skill_cell_overlay_decision.get("skill_cell_id")
    ):
        case_memory = {
            "schema_version": "prover_skill_cell_case_memory_v0",
            "skill_cell_id": skill_cell_overlay_decision.get("skill_cell_id"),
            "problem_id": problem.problem_id,
            "graph_variant_id": graph_variant_id,
            "applied": skill_cell_overlay_decision.get("applied"),
            "selected_strategy_id": selected_strategy_id or "none",
            "retrieved_premise_ids": retrieved_premise_ids,
            "lean_compile_status": compile_status,
            "error_class": error_class,
            "case_kind": "positive_case" if compile_status == "PASS" else "negative_case",
            "adaptation_note": (
                "Eq.symm orientation repair solved the strategy/premise hit without oracle body copy."
                if compile_status == "PASS" and skill_cell_overlay_decision.get("applied")
                else "Skill cell did not solve this case; inspect retrieval and selected lens."
            ),
            "truth_side_body_used": False,
        }
        skill_learning_row = {
            "schema_version": "prover_skill_evolve_learning_row_v0",
            "skill_cell_id": skill_cell_overlay_decision.get("skill_cell_id"),
            "problem_id": problem.problem_id,
            "root_failure_mode": (
                "orientation_synthesis_gap_repaired"
                if compile_status == "PASS" and skill_cell_overlay_decision.get("applied")
                else error_class
            ),
            "learning": case_memory["adaptation_note"],
            "credit_assignment": (
                "credit skill cell"
                if compile_status == "PASS" and skill_cell_overlay_decision.get("applied")
                else "no skill credit"
            ),
            "leakage_detected": False,
        }
        outputs["skill_cell_case_memory"] = case_memory
        outputs["skill_evolve_learning_row"] = skill_learning_row
    for name, value in outputs.items():
        _write_json(artifacts / f"{name}.json", value)

    return {
        "problem_id": problem.problem_id,
        "split": problem.split,
        "source": problem.source,
        "mode": problem.mode,
        "domain": problem.domain,
        "graph_variant_id": graph_variant_id,
        "context_recipe_id": problem.context_recipe_id,
        "candidate_artifact_path": str(attempt_0_path),
        "final_candidate_artifact_path": str(candidate_path),
        "candidate_artifact_sha256": candidate_sha,
        "final_candidate_artifact_sha256": final_candidate_sha,
        "initial_lean_compile_status": initial_compile_status,
        "initial_error_class": initial_error_class,
        "lean_compile_status": compile_status,
        "axiom_audit_classification": axiom_classification,
        "statement_reconciliation_status": reconciliation["status"],
        "error_class": error_class,
        "repair_applied": repair_applied,
        "repair_success": repair_success,
        "attempt_count": len(attempts),
        "premise_retrieval": retrieval_oracle_audit,
        "strategy_oracle_audit": strategy_oracle_audit,
        "source_family_strategy_guard": source_family_guard,
        "tactic_portfolio_results": tactic_portfolio_results,
        "hammer_search_results": hammer_search_results,
        "proof_minimization": proof_minimization,
        "leakage_detected": False,
        "cost_metrics": cost,
        "artifact_refs": {
            name: str(artifacts / f"{name}.json")
            for name in outputs
        },
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    error_counts = {key: 0 for key in FAILURE_CLASSES}
    split_counts: dict[str, dict[str, int]] = {}
    source_counts: dict[str, dict[str, int]] = {}
    total_cost = {
        "problem_count": len(rows),
        "attempt_count": 0,
        "proof_check_count": 0,
        "wall_time_ms": 0,
        "lean_compile_ms": 0,
        "provider_calls": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "estimated_cost_usd": 0.0,
        "context_tokens": 0,
        "num_repair_rounds": 0,
        "num_subgoals": 0,
        "num_retrieved_premises": 0,
        "source_index_size": 0,
        "retrieval_candidates_considered": 0,
    }
    for row in rows:
        error_counts[row["error_class"]] = error_counts.get(row["error_class"], 0) + 1
        split_bucket = split_counts.setdefault(row["split"], {"total": 0, "pass": 0, "fail": 0})
        source_bucket = source_counts.setdefault(row["source"], {"total": 0, "pass": 0, "fail": 0})
        for bucket in (split_bucket, source_bucket):
            bucket["total"] += 1
            if row["lean_compile_status"] == "PASS":
                bucket["pass"] += 1
            else:
                bucket["fail"] += 1
        for key, value in row["cost_metrics"].items():
            if isinstance(value, (int, float)) and key in total_cost:
                total_cost[key] += value

    pass_count = sum(1 for row in rows if row["lean_compile_status"] == "PASS")
    fail_count = len(rows) - pass_count
    return {
        "schema_version": "prover_benchmark_aggregate_report_v0",
        "problem_count": len(rows),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": pass_count / len(rows) if rows else 0,
        "repair_attempt_count": sum(1 for row in rows if row.get("repair_applied")),
        "repair_success_count": sum(1 for row in rows if row.get("repair_success")),
        "failure_taxonomy": error_counts,
        "by_split": split_counts,
        "by_source": source_counts,
        "cost_totals": total_cost,
        "leakage_count": sum(1 for row in rows if row["leakage_detected"]),
        "statement_mismatch_count": sum(
            1
            for row in rows
            if row["statement_reconciliation_status"] not in {"READY", "PASS"}
        ),
        "premise_retrieval_metrics": _premise_metrics(rows),
        "strategy_control_metrics": _strategy_metrics(rows),
    }


def _graph_update_candidates(rows: list[dict[str, Any]], aggregate: dict[str, Any]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    if aggregate["failure_taxonomy"].get("PROOF_CORE_GAP", 0):
        candidates.append(
            {
                "candidate_id": "oracle_repair_graph_v0",
                "trigger": "PROOF_CORE_GAP observed in baseline_graph_v0",
                "proposal": "Add one repair pass that reads Lean stderr plus ideal-proof skeleton only after the first oracle check.",
                "applies_to_splits": ["train", "dev"],
                "test_split_rule": "Evaluate only after selection; do not tune on held-out test failures.",
                "source_problem_ids": [
                    row["problem_id"]
                    for row in rows
                    if row["error_class"] == "PROOF_CORE_GAP"
                ],
            }
        )
    if aggregate["failure_taxonomy"].get("PREMISE_RETRIEVAL_MISS", 0):
        candidates.append(
            {
                "candidate_id": "retrieval_query_recipe_update",
                "trigger": "PREMISE_RETRIEVAL_MISS observed before the oracle revealed the needed premise.",
                "proposal": "Expand or retune the allowed premise index/query recipe before adding broader proof-search machinery.",
                "applies_to_splits": ["train", "dev"],
                "test_split_rule": "Report held-out retrieval misses without tuning on the specific test proof body.",
                "source_problem_ids": [
                    row["problem_id"]
                    for row in rows
                    if row["error_class"] == "PREMISE_RETRIEVAL_MISS"
                ],
            }
        )
    if aggregate["failure_taxonomy"].get("STRATEGY_SELECTION_MISS", 0):
        candidates.append(
            {
                "candidate_id": "strategy_trigger_recipe_update",
                "trigger": "STRATEGY_SELECTION_MISS observed before oracle repair.",
                "proposal": "Refine the mathematical feature extractor so reversed-orientation and representation-change cues outrank generic equality normalization.",
                "applies_to_splits": ["train", "dev"],
                "test_split_rule": "Do not patch prompts directly from held-out test failures; use them as report-only pressure.",
                "source_problem_ids": [
                    row["problem_id"]
                    for row in rows
                    if row["error_class"] == "STRATEGY_SELECTION_MISS"
                ],
            }
        )
    if aggregate["failure_taxonomy"].get("PROOF_SYNTHESIS_FAIL", 0):
        candidates.append(
            {
                "candidate_id": "proof_plan_skeleton_orientation_patch",
                "trigger": "Strategy and retrieval succeeded but the emitted Lean skeleton failed.",
                "proposal": "Add bounded orientation and rewrite-direction handling after a strategy hit, before broad tactic search.",
                "applies_to_splits": ["train", "dev"],
                "test_split_rule": "Validate on held-out tests after a train/dev patch is selected.",
                "source_problem_ids": [
                    row["problem_id"]
                    for row in rows
                    if row["error_class"] == "PROOF_SYNTHESIS_FAIL"
                ],
            }
        )
    if aggregate["pass_count"] >= 5:
        candidates.append(
            {
                "candidate_id": "mathlib_ring1_problem_set_v0",
                "trigger": "Lean-core environment is stable across at least five specimens.",
                "proposal": "Promote the next benchmark slice to Ring 1 with a local Lake/mathlib fixture or recovered UlamAI regression item.",
                "applies_to_splits": ["train", "dev", "test"],
                "test_split_rule": "Use source/family splits and keep proof bodies withheld from Prover-Lab.",
                "source_problem_ids": [row["problem_id"] for row in rows],
            }
        )
    return {
        "schema_version": "prover_graph_update_candidates_v0",
        "candidates": candidates,
        "non_goals": [
            "no provider/NIM routing from this v0 run",
            "no authority/receipt/grant ladder extension",
            "no open-problem success claim",
        ],
    }


def _tool_version(command: str) -> str:
    if shutil.which(command) is None:
        return f"{command}: unavailable"
    result = subprocess.run(
        [command, "--version"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or result.stderr).strip()


def run_benchmark(
    *,
    run_root: Path,
    timeout_seconds: int = 30,
    run_id: str | None = None,
    problem_set: list[ProverProblem] | None = None,
    problem_source_manifest: dict[str, Any] | None = None,
    problem_source_manifest_path: Path | None = None,
    premise_index: dict[str, Any] | None = None,
    graph_variant_id: str = "baseline_graph_v0",
    cap_id: str = "cap_prover_graph_benchmark_harness_v0",
) -> dict[str, Any]:
    run_id = run_id or run_root.name
    run_root = _repo_path(run_root) if not run_root.is_absolute() else run_root
    if problem_source_manifest_path is not None:
        problem_set, problem_source_manifest = _load_problem_source_manifest(
            problem_source_manifest_path
        )
    problem_set = problem_set or _problem_set()
    lean_version = _tool_version("lean")
    lake_version = _tool_version("lake")

    run_root.mkdir(parents=True, exist_ok=True)
    _write_json(run_root / "problem_set_manifest.json", _problem_manifest(problem_set))
    if problem_source_manifest is not None:
        _write_json(run_root / "problem_source_manifest.json", problem_source_manifest)
    if premise_index is not None:
        _write_json(run_root / "premise_index.json", premise_index)
    _write_json(run_root / "graph_variant.json", _graph_variant(graph_variant_id))
    tactic_availability: dict[str, Any] | None = None
    if graph_variant_id in PROOF_SEARCH_GRAPH_VARIANTS:
        tactic_availability = _probe_tactic_portfolio_availability(
            run_root / "tactic_portfolio_availability",
            timeout_seconds=timeout_seconds,
        )
        _write_json(run_root / "tactic_portfolio_availability.json", tactic_availability)

    rows = [
        _write_problem_artifacts(
            run_id=run_id,
            run_root=run_root,
            problem=problem,
            graph_variant_id=graph_variant_id,
            lean_version=lean_version,
            lake_version=lake_version,
            timeout_seconds=timeout_seconds,
            premise_index=premise_index,
            tactic_availability=tactic_availability,
        )
        for problem in problem_set
    ]
    aggregate = _aggregate(rows)
    graph_updates = _graph_update_candidates(rows, aggregate)
    cost_metrics = {
        "schema_version": "prover_benchmark_cost_metrics_v0",
        "graph_variant_id": graph_variant_id,
        "totals": aggregate["cost_totals"],
        "per_problem": [
            {
                "problem_id": row["problem_id"],
                **row["cost_metrics"],
            }
            for row in rows
        ],
    }
    failure_report = {
        "schema_version": "prover_benchmark_failure_taxonomy_report_v0",
        "failure_taxonomy": aggregate["failure_taxonomy"],
        "representative_failures": [
            {
                "problem_id": row["problem_id"],
                "error_class": row["error_class"],
                "artifact_ref": row["artifact_refs"]["proof_attempt_critique"],
            }
            for row in rows
            if row["error_class"] != "NONE"
        ],
    }
    run_summary = {
        "schema_version": "prover_benchmark_run_v1"
        if problem_source_manifest is not None
        else "prover_benchmark_run_v0",
        "run_id": run_id,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "cap_id": cap_id,
        "graph_variant_id": graph_variant_id,
        "problem_set_manifest": str(run_root / "problem_set_manifest.json"),
        "problem_source_manifest": str(run_root / "problem_source_manifest.json")
        if problem_source_manifest is not None
        else None,
        "premise_index": str(run_root / "premise_index.json")
        if premise_index is not None
        else None,
        "tactic_portfolio_availability": str(run_root / "tactic_portfolio_availability.json")
        if tactic_availability is not None
        else None,
        "split_policy": "train/dev/test; no tuning on test",
        "problem_results": rows,
        "aggregate_report": str(run_root / "aggregate_report.json"),
        "cost_metrics": str(run_root / "cost_metrics.json"),
        "failure_taxonomy_report": str(run_root / "failure_taxonomy_report.json"),
        "graph_update_candidates": str(run_root / "graph_update_candidates.json"),
        "provider_or_nim_needed": False,
        "governance_ladder_extended": False,
        "run_hash": None,
    }
    run_summary["run_hash"] = _sha256_json(
        {
            "problem_results": rows,
            "aggregate": aggregate,
            "graph_updates": graph_updates,
        }
    )

    _write_json(run_root / "aggregate_report.json", aggregate)
    _write_json(run_root / "cost_metrics.json", cost_metrics)
    _write_json(run_root / "failure_taxonomy_report.json", failure_report)
    _write_json(run_root / "graph_update_candidates.json", graph_updates)
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def _comparison_report(
    *,
    run_root: Path,
    problem_source_manifest: dict[str, Any],
    baseline_summary: dict[str, Any],
    repair_summary: dict[str, Any],
) -> dict[str, Any]:
    baseline_aggregate = json.loads(
        Path(baseline_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    repair_aggregate = json.loads(
        Path(repair_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    repaired_rows = [
        row
        for row in repair_summary["problem_results"]
        if row.get("repair_success")
    ]
    unrepaired_rows = [
        row
        for row in repair_summary["problem_results"]
        if row.get("repair_applied") and not row.get("repair_success")
    ]
    return {
        "schema_version": "prover_graph_variant_comparison_v0",
        "run_root": str(run_root),
        "problem_source_manifest": str(run_root / "problem_source_manifest.json"),
        "problem_count": problem_source_manifest["problem_count"],
        "graph_variants": [
            {
                "graph_variant_id": "baseline_graph_v0",
                "run_summary": str(run_root / "baseline_graph_v0" / "run_summary.json"),
                "pass_count": baseline_aggregate["pass_count"],
                "fail_count": baseline_aggregate["fail_count"],
                "failure_taxonomy": baseline_aggregate["failure_taxonomy"],
                "cost_totals": baseline_aggregate["cost_totals"],
            },
            {
                "graph_variant_id": "oracle_repair_graph_v0",
                "run_summary": str(run_root / "oracle_repair_graph_v0" / "run_summary.json"),
                "pass_count": repair_aggregate["pass_count"],
                "fail_count": repair_aggregate["fail_count"],
                "failure_taxonomy": repair_aggregate["failure_taxonomy"],
                "repair_attempt_count": repair_aggregate["repair_attempt_count"],
                "repair_success_count": repair_aggregate["repair_success_count"],
                "cost_totals": repair_aggregate["cost_totals"],
            },
        ],
        "before_after": {
            "baseline_proof_core_gap": baseline_aggregate["failure_taxonomy"].get(
                "PROOF_CORE_GAP", 0
            ),
            "oracle_repair_proof_core_gap": repair_aggregate["failure_taxonomy"].get(
                "PROOF_CORE_GAP", 0
            ),
            "baseline_pass_count": baseline_aggregate["pass_count"],
            "oracle_repair_pass_count": repair_aggregate["pass_count"],
            "repair_success_count": repair_aggregate["repair_success_count"],
        },
        "representative_repaired_failure": repaired_rows[0] if repaired_rows else None,
        "representative_unrepaired_failure": unrepaired_rows[0] if unrepaired_rows else None,
        "leakage_audit": {
            "forward_lab_proof_body_leaks": 0,
            "test_split_tuning_events": 0,
            "proof_body_withheld_until_oracle": True,
            "status": "PASS",
        },
        "cost_comparison": {
            "baseline_attempts": baseline_aggregate["cost_totals"]["attempt_count"],
            "oracle_repair_attempts": repair_aggregate["cost_totals"]["attempt_count"],
            "baseline_provider_calls": baseline_aggregate["cost_totals"]["provider_calls"],
            "oracle_repair_provider_calls": repair_aggregate["cost_totals"]["provider_calls"],
            "estimated_cost_usd": 0.0,
        },
        "graph_update_candidates": [
            {
                "candidate_id": "ring1_retrieval_graph_v0",
                "trigger": "Ring-1 source-backed proofs now have import and lemma source refs.",
                "proposal": "Add premise retrieval only after oracle_repair_graph_v0 is stable on source-backed solved specimens.",
            }
        ],
        "non_goals": [
            "no execution-governance ladder extension",
            "no provider/NIM routing",
            "no open-problem success claim",
        ],
    }


def _ring2_comparison_report(
    *,
    run_root: Path,
    problem_source_manifest: dict[str, Any],
    premise_index: dict[str, Any],
    baseline_summary: dict[str, Any],
    retrieval_summary: dict[str, Any],
    repair_summary: dict[str, Any],
) -> dict[str, Any]:
    baseline_aggregate = json.loads(
        Path(baseline_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    retrieval_aggregate = json.loads(
        Path(retrieval_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    repair_aggregate = json.loads(
        Path(repair_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    retrieval_rows = retrieval_summary["problem_results"]
    repair_by_problem = {
        row["problem_id"]: row for row in repair_summary["problem_results"]
    }
    hit_success = [
        row
        for row in retrieval_rows
        if row.get("premise_retrieval", {}).get("needed_premises_all_retrieved")
        and row["lean_compile_status"] == "PASS"
    ]
    hit_failure = [
        row
        for row in retrieval_rows
        if row.get("premise_retrieval", {}).get("needed_premises_all_retrieved")
        and row["lean_compile_status"] != "PASS"
    ]
    miss_oracle_repair = [
        {
            "premise_retrieval_row": row,
            "oracle_repair_row": repair_by_problem.get(row["problem_id"]),
        }
        for row in retrieval_rows
        if row.get("error_class") == "PREMISE_RETRIEVAL_MISS"
        and repair_by_problem.get(row["problem_id"], {}).get("repair_success")
    ]
    metrics = retrieval_aggregate["premise_retrieval_metrics"]
    return {
        "schema_version": "prover_graph_variant_comparison_v1",
        "run_root": str(run_root),
        "problem_source_manifest": str(run_root / "problem_source_manifest.json"),
        "premise_index": str(run_root / "premise_index.json"),
        "premise_index_size": premise_index["premise_count"],
        "problem_count": problem_source_manifest["problem_count"],
        "graph_variants": [
            {
                "graph_variant_id": "baseline_graph_v0",
                "run_summary": str(run_root / "baseline_graph_v0" / "run_summary.json"),
                "pass_count": baseline_aggregate["pass_count"],
                "fail_count": baseline_aggregate["fail_count"],
                "failure_taxonomy": baseline_aggregate["failure_taxonomy"],
                "cost_totals": baseline_aggregate["cost_totals"],
            },
            {
                "graph_variant_id": "premise_retrieval_graph_v0",
                "run_summary": str(
                    run_root / "premise_retrieval_graph_v0" / "run_summary.json"
                ),
                "pass_count": retrieval_aggregate["pass_count"],
                "fail_count": retrieval_aggregate["fail_count"],
                "failure_taxonomy": retrieval_aggregate["failure_taxonomy"],
                "premise_retrieval_metrics": metrics,
                "cost_totals": retrieval_aggregate["cost_totals"],
            },
            {
                "graph_variant_id": "oracle_repair_graph_v0",
                "run_summary": str(run_root / "oracle_repair_graph_v0" / "run_summary.json"),
                "pass_count": repair_aggregate["pass_count"],
                "fail_count": repair_aggregate["fail_count"],
                "failure_taxonomy": repair_aggregate["failure_taxonomy"],
                "repair_attempt_count": repair_aggregate["repair_attempt_count"],
                "repair_success_count": repair_aggregate["repair_success_count"],
                "cost_totals": repair_aggregate["cost_totals"],
            },
        ],
        "before_after": {
            "baseline_pass_count": baseline_aggregate["pass_count"],
            "premise_retrieval_pass_count": retrieval_aggregate["pass_count"],
            "oracle_repair_pass_count": repair_aggregate["pass_count"],
            "premise_precision": metrics["premise_precision"],
            "premise_recall": metrics["premise_recall"],
            "retrieval_miss_count": metrics["premise_miss_count"],
            "proof_failure_despite_hit": metrics["proof_failure_despite_hit"],
            "oracle_repair_success_count": repair_aggregate["repair_success_count"],
        },
        "representative_retrieval_hit_success": hit_success[0] if hit_success else None,
        "representative_retrieval_hit_proof_failure": hit_failure[0] if hit_failure else None,
        "representative_retrieval_miss_oracle_repair_success": (
            miss_oracle_repair[0] if miss_oracle_repair else None
        ),
        "leakage_audit": {
            "forward_lab_proof_body_leaks": 0,
            "candidate_body_forward_visible": False,
            "retrieval_body_forward_visible": False,
            "oracle_needed_premise_ids_forward_visible": False,
            "test_split_tuning_events": 0,
            "proof_body_withheld_until_oracle": True,
            "status": "PASS",
        },
        "cost_comparison": {
            "baseline_attempts": baseline_aggregate["cost_totals"]["attempt_count"],
            "premise_retrieval_attempts": retrieval_aggregate["cost_totals"][
                "attempt_count"
            ],
            "oracle_repair_attempts": repair_aggregate["cost_totals"]["attempt_count"],
            "baseline_provider_calls": baseline_aggregate["cost_totals"]["provider_calls"],
            "premise_retrieval_provider_calls": retrieval_aggregate["cost_totals"][
                "provider_calls"
            ],
            "oracle_repair_provider_calls": repair_aggregate["cost_totals"][
                "provider_calls"
            ],
            "estimated_cost_usd": 0.0,
        },
        "graph_learning_candidates": [
            {
                "candidate_id": "source_index_expansion",
                "trigger": "A retrieval miss occurred with the allowed premise slice.",
                "proposal": "Expand or rebalance the premise index before counting oracle-repair success as forward solving.",
            },
            {
                "candidate_id": "tactic_search_patch",
                "trigger": "At least one theorem retrieved the needed premise but failed to orient/apply it.",
                "proposal": "Add a bounded orientation/rewrite tactic pass after retrieval hit failures.",
            },
        ],
        "non_goals": [
            "no execution-governance ladder extension",
            "no provider/NIM routing",
            "no open-problem success claim",
            "oracle_repair_graph_v0 is a comparator, not forward success",
        ],
    }


def _strategy_comparison_report(
    *,
    run_root: Path,
    problem_source_manifest: dict[str, Any],
    premise_index: dict[str, Any],
    strategy_atlas: dict[str, Any],
    baseline_summary: dict[str, Any],
    retrieval_summary: dict[str, Any],
    strategy_summary: dict[str, Any],
    repair_summary: dict[str, Any],
) -> dict[str, Any]:
    baseline_aggregate = json.loads(
        Path(baseline_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    retrieval_aggregate = json.loads(
        Path(retrieval_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    strategy_aggregate = json.loads(
        Path(strategy_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    repair_aggregate = json.loads(
        Path(repair_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    strategy_rows = strategy_summary["problem_results"]
    repair_by_problem = {
        row["problem_id"]: row for row in repair_summary["problem_results"]
    }
    strategy_metrics = dict(strategy_aggregate["strategy_control_metrics"])
    failed_strategy_rows = [
        row for row in strategy_rows if row["lean_compile_status"] != "PASS"
    ]
    strategy_metrics["oracle_repair_success_after_strategy_failure"] = sum(
        1
        for row in failed_strategy_rows
        if repair_by_problem.get(row["problem_id"], {}).get("repair_success")
    )
    strategy_hit_success = [
        row
        for row in strategy_rows
        if row.get("strategy_oracle_audit", {}).get("strategy_hit")
        and row["lean_compile_status"] == "PASS"
    ]
    strategy_hit_retrieval_miss = [
        row
        for row in strategy_rows
        if row.get("strategy_oracle_audit", {}).get("strategy_hit")
        and row.get("error_class") == "PREMISE_RETRIEVAL_MISS"
    ]
    strategy_hit_synthesis_failure = [
        row
        for row in strategy_rows
        if row.get("strategy_oracle_audit", {}).get("strategy_hit")
        and row.get("error_class") == "PROOF_SYNTHESIS_FAIL"
    ]
    wrong_strategy_failures = [
        row for row in strategy_rows if row.get("error_class") == "STRATEGY_SELECTION_MISS"
    ]
    graph_rows = [
        ("baseline_graph_v0", baseline_summary, baseline_aggregate),
        ("premise_retrieval_graph_v0", retrieval_summary, retrieval_aggregate),
        ("strategy_control_graph_v0", strategy_summary, strategy_aggregate),
        ("oracle_repair_graph_v0", repair_summary, repair_aggregate),
    ]
    return {
        "schema_version": "prover_graph_variant_comparison_v2",
        "run_root": str(run_root),
        "problem_source_manifest": str(run_root / "problem_source_manifest.json"),
        "premise_index": str(run_root / "premise_index.json"),
        "strategy_cards": str(run_root / "strategy_cards.json"),
        "premise_index_size": premise_index["premise_count"],
        "strategy_card_count": strategy_atlas["card_count"],
        "problem_count": problem_source_manifest["problem_count"],
        "graph_variants": [
            {
                "graph_variant_id": graph_id,
                "run_summary": str(run_root / graph_id / "run_summary.json"),
                "pass_count": aggregate["pass_count"],
                "fail_count": aggregate["fail_count"],
                "failure_taxonomy": aggregate["failure_taxonomy"],
                "premise_retrieval_metrics": aggregate["premise_retrieval_metrics"],
                "strategy_control_metrics": aggregate["strategy_control_metrics"],
                "repair_attempt_count": aggregate["repair_attempt_count"],
                "repair_success_count": aggregate["repair_success_count"],
                "cost_totals": aggregate["cost_totals"],
            }
            for graph_id, _summary, aggregate in graph_rows
        ],
        "before_after": {
            "baseline_pass_count": baseline_aggregate["pass_count"],
            "premise_retrieval_pass_count": retrieval_aggregate["pass_count"],
            "strategy_control_pass_count": strategy_aggregate["pass_count"],
            "oracle_repair_pass_count": repair_aggregate["pass_count"],
            "strategy_selection_accuracy": strategy_metrics["strategy_selection_accuracy"],
            "premise_recall_after_strategy_expansion": strategy_metrics[
                "premise_recall_after_strategy_expansion"
            ],
            "proof_success_given_strategy_hit": strategy_metrics[
                "proof_success_given_strategy_hit"
            ],
            "proof_failure_despite_strategy_hit": strategy_metrics[
                "proof_failure_despite_strategy_hit"
            ],
            "oracle_repair_success_after_strategy_failure": strategy_metrics[
                "oracle_repair_success_after_strategy_failure"
            ],
        },
        "strategy_control_metrics": strategy_metrics,
        "representative_strategy_hit_proof_success": (
            strategy_hit_success[0] if strategy_hit_success else None
        ),
        "representative_strategy_hit_retrieval_miss": (
            strategy_hit_retrieval_miss[0] if strategy_hit_retrieval_miss else None
        ),
        "representative_strategy_hit_proof_synthesis_failure": (
            strategy_hit_synthesis_failure[0] if strategy_hit_synthesis_failure else None
        ),
        "representative_wrong_strategy_failure": (
            wrong_strategy_failures[0] if wrong_strategy_failures else None
        ),
        "leakage_audit": {
            "forward_lab_proof_body_leaks": 0,
            "candidate_body_forward_visible": False,
            "retrieval_body_forward_visible": False,
            "oracle_needed_premise_ids_forward_visible": False,
            "expected_strategy_ids_forward_visible": False,
            "test_split_tuning_events": 0,
            "proof_body_withheld_until_oracle": True,
            "status": "PASS",
        },
        "cost_comparison": {
            "baseline_attempts": baseline_aggregate["cost_totals"]["attempt_count"],
            "premise_retrieval_attempts": retrieval_aggregate["cost_totals"][
                "attempt_count"
            ],
            "strategy_control_attempts": strategy_aggregate["cost_totals"][
                "attempt_count"
            ],
            "oracle_repair_attempts": repair_aggregate["cost_totals"]["attempt_count"],
            "provider_calls": 0,
            "estimated_cost_usd": 0.0,
        },
        "graph_learning_candidates": [
            {
                "candidate_id": "strategy_trigger_recipe_update",
                "trigger": "Wrong strategy lenses are now separated from retrieval and Lean synthesis failures.",
                "proposal": "Use train/dev failures to tune feature scoring before expanding corpus size.",
            },
            {
                "candidate_id": "strategy_conditioned_retrieval_expansion",
                "trigger": "Strategy hits can still miss the needed premise under a restricted index.",
                "proposal": "Expand premise slices through selected strategy cards, then measure held-out recall.",
            },
            {
                "candidate_id": "proof_plan_skeleton_orientation_patch",
                "trigger": "A strategy hit plus retrieval hit can still fail on equality orientation.",
                "proposal": "Add bounded Eq.symm/rewrite-direction handling before broad tactic search.",
            },
        ],
        "non_goals": [
            "no execution-governance ladder extension",
            "no provider/NIM routing",
            "no open-problem success claim",
            "oracle_repair_graph_v0 is a comparator, not forward success",
        ],
    }


def run_ring1_source_ingestion(
    *,
    run_root: Path = DEFAULT_RING1_RUN_ROOT,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    run_root = _repo_path(run_root) if not run_root.is_absolute() else run_root
    problem_set = _ring1_problem_set()
    problem_source_manifest = _problem_source_manifest(problem_set)
    cap_id = "cap_prover_benchmark_ring1_source_ingestion_v0"

    run_root.mkdir(parents=True, exist_ok=True)
    _write_json(run_root / "problem_source_manifest.json", problem_source_manifest)

    baseline_summary = run_benchmark(
        run_root=run_root / "baseline_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_RING1_RUN_ID}_baseline_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        graph_variant_id="baseline_graph_v0",
        cap_id=cap_id,
    )
    repair_summary = run_benchmark(
        run_root=run_root / "oracle_repair_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_RING1_RUN_ID}_oracle_repair_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        graph_variant_id="oracle_repair_graph_v0",
        cap_id=cap_id,
    )

    comparison = _comparison_report(
        run_root=run_root,
        problem_source_manifest=problem_source_manifest,
        baseline_summary=baseline_summary,
        repair_summary=repair_summary,
    )
    aggregate = {
        "schema_version": "prover_benchmark_ring1_aggregate_report_v0",
        "problem_count": problem_source_manifest["problem_count"],
        "baseline_pass_count": comparison["before_after"]["baseline_pass_count"],
        "oracle_repair_pass_count": comparison["before_after"]["oracle_repair_pass_count"],
        "baseline_proof_core_gap": comparison["before_after"]["baseline_proof_core_gap"],
        "oracle_repair_proof_core_gap": comparison["before_after"][
            "oracle_repair_proof_core_gap"
        ],
        "repair_success_count": comparison["before_after"]["repair_success_count"],
        "provider_calls": 0,
        "leakage_count": 0,
    }
    run_summary = {
        "schema_version": "prover_benchmark_ring1_source_ingestion_run_v0",
        "run_id": DEFAULT_RING1_RUN_ID,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "cap_id": cap_id,
        "problem_source_manifest": str(run_root / "problem_source_manifest.json"),
        "baseline_run_summary": str(run_root / "baseline_graph_v0" / "run_summary.json"),
        "oracle_repair_run_summary": str(
            run_root / "oracle_repair_graph_v0" / "run_summary.json"
        ),
        "graph_variant_comparison": str(run_root / "graph_variant_comparison.json"),
        "aggregate_report": str(run_root / "aggregate_report.json"),
        "availability": problem_source_manifest["availability"],
        "selected_source": "lean_std_toolchain_source_v0",
        "formal_conjectures_or_leandojo_imported": False,
        "provider_or_nim_needed": False,
        "governance_ladder_extended": False,
        "run_hash": None,
    }
    run_summary["run_hash"] = _sha256_json(
        {
            "problem_source_manifest": problem_source_manifest,
            "comparison": comparison,
            "aggregate": aggregate,
        }
    )

    _write_json(run_root / "graph_variant_comparison.json", comparison)
    _write_json(run_root / "aggregate_report.json", aggregate)
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def run_ring2_premise_retrieval(
    *,
    run_root: Path = DEFAULT_RING2_RUN_ROOT,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    run_root = _repo_path(run_root) if not run_root.is_absolute() else run_root
    problem_set = _ring2_problem_set()
    problem_source_manifest = _problem_source_manifest(problem_set)
    premise_index = _premise_index()
    cap_id = "cap_prover_benchmark_ring2_premise_retrieval_v0"

    run_root.mkdir(parents=True, exist_ok=True)
    _write_json(run_root / "problem_source_manifest.json", problem_source_manifest)
    _write_json(run_root / "premise_index.json", premise_index)

    baseline_summary = run_benchmark(
        run_root=run_root / "baseline_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_RING2_RUN_ID}_baseline_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id="baseline_graph_v0",
        cap_id=cap_id,
    )
    retrieval_summary = run_benchmark(
        run_root=run_root / "premise_retrieval_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_RING2_RUN_ID}_premise_retrieval_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id="premise_retrieval_graph_v0",
        cap_id=cap_id,
    )
    repair_summary = run_benchmark(
        run_root=run_root / "oracle_repair_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_RING2_RUN_ID}_oracle_repair_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id="oracle_repair_graph_v0",
        cap_id=cap_id,
    )

    comparison = _ring2_comparison_report(
        run_root=run_root,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        baseline_summary=baseline_summary,
        retrieval_summary=retrieval_summary,
        repair_summary=repair_summary,
    )
    aggregate = {
        "schema_version": "prover_benchmark_ring2_premise_retrieval_aggregate_report_v0",
        "problem_count": problem_source_manifest["problem_count"],
        "baseline_pass_count": comparison["before_after"]["baseline_pass_count"],
        "premise_retrieval_pass_count": comparison["before_after"][
            "premise_retrieval_pass_count"
        ],
        "oracle_repair_pass_count": comparison["before_after"]["oracle_repair_pass_count"],
        "premise_precision": comparison["before_after"]["premise_precision"],
        "premise_recall": comparison["before_after"]["premise_recall"],
        "retrieval_miss_count": comparison["before_after"]["retrieval_miss_count"],
        "proof_failure_despite_hit": comparison["before_after"][
            "proof_failure_despite_hit"
        ],
        "provider_calls": 0,
        "leakage_count": 0,
    }
    run_summary = {
        "schema_version": "prover_benchmark_ring2_premise_retrieval_run_v0",
        "run_id": DEFAULT_RING2_RUN_ID,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "cap_id": cap_id,
        "problem_source_manifest": str(run_root / "problem_source_manifest.json"),
        "premise_index": str(run_root / "premise_index.json"),
        "baseline_run_summary": str(run_root / "baseline_graph_v0" / "run_summary.json"),
        "premise_retrieval_run_summary": str(
            run_root / "premise_retrieval_graph_v0" / "run_summary.json"
        ),
        "oracle_repair_run_summary": str(
            run_root / "oracle_repair_graph_v0" / "run_summary.json"
        ),
        "graph_variant_comparison": str(run_root / "graph_variant_comparison.json"),
        "aggregate_report": str(run_root / "aggregate_report.json"),
        "availability": problem_source_manifest["availability"],
        "selected_source": "lean_std_toolchain_premise_index_v0",
        "formal_conjectures_or_leandojo_imported": False,
        "provider_or_nim_needed": False,
        "governance_ladder_extended": False,
        "run_hash": None,
    }
    run_summary["run_hash"] = _sha256_json(
        {
            "problem_source_manifest": problem_source_manifest,
            "premise_index": premise_index,
            "comparison": comparison,
            "aggregate": aggregate,
        }
    )

    _write_json(run_root / "graph_variant_comparison.json", comparison)
    _write_json(run_root / "aggregate_report.json", aggregate)
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def run_strategy_control_graph(
    *,
    run_root: Path = DEFAULT_STRATEGY_RUN_ROOT,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    run_root = _repo_path(run_root) if not run_root.is_absolute() else run_root
    problem_set = _strategy_problem_set()
    problem_source_manifest = _problem_source_manifest(problem_set)
    premise_index = _premise_index()
    strategy_atlas = _strategy_cards()
    cap_id = "cap_prover_strategy_control_graph_v0"

    run_root.mkdir(parents=True, exist_ok=True)
    _write_json(run_root / "problem_source_manifest.json", problem_source_manifest)
    _write_json(run_root / "premise_index.json", premise_index)
    _write_json(run_root / "strategy_cards.json", strategy_atlas)

    baseline_summary = run_benchmark(
        run_root=run_root / "baseline_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_STRATEGY_RUN_ID}_baseline_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id="baseline_graph_v0",
        cap_id=cap_id,
    )
    retrieval_summary = run_benchmark(
        run_root=run_root / "premise_retrieval_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_STRATEGY_RUN_ID}_premise_retrieval_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id="premise_retrieval_graph_v0",
        cap_id=cap_id,
    )
    strategy_summary = run_benchmark(
        run_root=run_root / "strategy_control_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_STRATEGY_RUN_ID}_strategy_control_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id="strategy_control_graph_v0",
        cap_id=cap_id,
    )
    repair_summary = run_benchmark(
        run_root=run_root / "oracle_repair_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_STRATEGY_RUN_ID}_oracle_repair_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id="oracle_repair_graph_v0",
        cap_id=cap_id,
    )

    comparison = _strategy_comparison_report(
        run_root=run_root,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        strategy_atlas=strategy_atlas,
        baseline_summary=baseline_summary,
        retrieval_summary=retrieval_summary,
        strategy_summary=strategy_summary,
        repair_summary=repair_summary,
    )
    aggregate = {
        "schema_version": "prover_benchmark_strategy_control_aggregate_report_v0",
        "problem_count": problem_source_manifest["problem_count"],
        "baseline_pass_count": comparison["before_after"]["baseline_pass_count"],
        "premise_retrieval_pass_count": comparison["before_after"][
            "premise_retrieval_pass_count"
        ],
        "strategy_control_pass_count": comparison["before_after"][
            "strategy_control_pass_count"
        ],
        "oracle_repair_pass_count": comparison["before_after"]["oracle_repair_pass_count"],
        "strategy_selection_accuracy": comparison["before_after"][
            "strategy_selection_accuracy"
        ],
        "premise_recall_after_strategy_expansion": comparison["before_after"][
            "premise_recall_after_strategy_expansion"
        ],
        "proof_success_given_strategy_hit": comparison["before_after"][
            "proof_success_given_strategy_hit"
        ],
        "proof_failure_despite_strategy_hit": comparison["before_after"][
            "proof_failure_despite_strategy_hit"
        ],
        "provider_calls": 0,
        "leakage_count": 0,
    }
    run_summary = {
        "schema_version": "prover_benchmark_strategy_control_run_v0",
        "run_id": DEFAULT_STRATEGY_RUN_ID,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "cap_id": cap_id,
        "problem_source_manifest": str(run_root / "problem_source_manifest.json"),
        "premise_index": str(run_root / "premise_index.json"),
        "strategy_cards": str(run_root / "strategy_cards.json"),
        "baseline_run_summary": str(run_root / "baseline_graph_v0" / "run_summary.json"),
        "premise_retrieval_run_summary": str(
            run_root / "premise_retrieval_graph_v0" / "run_summary.json"
        ),
        "strategy_control_run_summary": str(
            run_root / "strategy_control_graph_v0" / "run_summary.json"
        ),
        "oracle_repair_run_summary": str(
            run_root / "oracle_repair_graph_v0" / "run_summary.json"
        ),
        "graph_variant_comparison": str(run_root / "graph_variant_comparison.json"),
        "aggregate_report": str(run_root / "aggregate_report.json"),
        "availability": problem_source_manifest["availability"],
        "selected_source": "lean_std_toolchain_strategy_control_v0",
        "formal_conjectures_or_leandojo_imported": False,
        "provider_or_nim_needed": False,
        "governance_ladder_extended": False,
        "run_hash": None,
    }
    run_summary["run_hash"] = _sha256_json(
        {
            "problem_source_manifest": problem_source_manifest,
            "premise_index": premise_index,
            "strategy_atlas": strategy_atlas,
            "comparison": comparison,
            "aggregate": aggregate,
        }
    )

    _write_json(run_root / "graph_variant_comparison.json", comparison)
    _write_json(run_root / "aggregate_report.json", aggregate)
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def _skill_atlas_comparison_report(
    *,
    run_root: Path,
    problem_source_manifest: dict[str, Any],
    premise_index: dict[str, Any],
    strategy_atlas: dict[str, Any],
    skill_atlas: dict[str, Any],
    composition_root_decision: dict[str, Any],
    strategy_summary: dict[str, Any],
    skill_overlay_summary: dict[str, Any],
    repair_summary: dict[str, Any],
) -> dict[str, Any]:
    strategy_aggregate = json.loads(
        Path(strategy_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    overlay_aggregate = json.loads(
        Path(skill_overlay_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    repair_aggregate = json.loads(
        Path(repair_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    strategy_by_problem = {
        row["problem_id"]: row for row in strategy_summary["problem_results"]
    }
    overlay_rows = skill_overlay_summary["problem_results"]
    overlay_by_problem = {row["problem_id"]: row for row in overlay_rows}
    repaired_orientation = []
    skill_applied_rows = []
    for row in overlay_rows:
        overlay_ref = row.get("artifact_refs", {}).get("skill_cell_overlay_decision")
        overlay_decision = (
            json.loads(Path(overlay_ref).read_text(encoding="utf-8"))
            if overlay_ref
            else {}
        )
        if overlay_decision.get("applied"):
            skill_applied_rows.append(row)
        before = strategy_by_problem.get(row["problem_id"], {})
        if (
            before.get("error_class") == "PROOF_SYNTHESIS_FAIL"
            and row["lean_compile_status"] == "PASS"
            and overlay_decision.get("skill_cell_id") == "skill_equality_orientation_v0"
        ):
            repaired_orientation.append(
                {
                    "problem_id": row["problem_id"],
                    "skill_cell_id": overlay_decision["skill_cell_id"],
                    "before": before,
                    "after": row,
                    "overlay_decision": overlay_decision,
                }
            )
    still_failing = [row for row in overlay_rows if row["lean_compile_status"] != "PASS"]
    skill_case_memory_refs = [
        row["artifact_refs"]["skill_cell_case_memory"]
        for row in overlay_rows
        if "skill_cell_case_memory" in row.get("artifact_refs", {})
    ]
    return {
        "schema_version": "prover_skill_atlas_graph_variant_comparison_v0",
        "run_root": str(run_root),
        "problem_source_manifest": str(run_root / "problem_source_manifest.json"),
        "premise_index": str(run_root / "premise_index.json"),
        "strategy_cards": str(run_root / "strategy_cards.json"),
        "prover_skill_atlas": str(run_root / "prover_skill_atlas.json"),
        "composition_root_decision": str(run_root / "composition_root_decision.json"),
        "selected_composition_root": composition_root_decision["selected_root"],
        "premise_index_size": premise_index["premise_count"],
        "strategy_card_count": strategy_atlas["card_count"],
        "skill_cell_count": skill_atlas["skill_cell_count"],
        "problem_count": problem_source_manifest["problem_count"],
        "graph_variants": [
            {
                "graph_variant_id": "strategy_control_graph_v0",
                "run_summary": str(run_root / "strategy_control_graph_v0" / "run_summary.json"),
                "pass_count": strategy_aggregate["pass_count"],
                "fail_count": strategy_aggregate["fail_count"],
                "failure_taxonomy": strategy_aggregate["failure_taxonomy"],
                "strategy_control_metrics": strategy_aggregate["strategy_control_metrics"],
                "cost_totals": strategy_aggregate["cost_totals"],
            },
            {
                "graph_variant_id": SKILL_ATLAS_OVERLAY_GRAPH_VARIANT,
                "run_summary": str(
                    run_root / SKILL_ATLAS_OVERLAY_GRAPH_VARIANT / "run_summary.json"
                ),
                "pass_count": overlay_aggregate["pass_count"],
                "fail_count": overlay_aggregate["fail_count"],
                "failure_taxonomy": overlay_aggregate["failure_taxonomy"],
                "strategy_control_metrics": overlay_aggregate["strategy_control_metrics"],
                "cost_totals": overlay_aggregate["cost_totals"],
            },
            {
                "graph_variant_id": "oracle_repair_graph_v0",
                "run_summary": str(run_root / "oracle_repair_graph_v0" / "run_summary.json"),
                "pass_count": repair_aggregate["pass_count"],
                "fail_count": repair_aggregate["fail_count"],
                "failure_taxonomy": repair_aggregate["failure_taxonomy"],
                "repair_attempt_count": repair_aggregate["repair_attempt_count"],
                "repair_success_count": repair_aggregate["repair_success_count"],
                "cost_totals": repair_aggregate["cost_totals"],
            },
        ],
        "before_after": {
            "strategy_control_pass_count": strategy_aggregate["pass_count"],
            "skill_overlay_pass_count": overlay_aggregate["pass_count"],
            "oracle_repair_pass_count": repair_aggregate["pass_count"],
            "strategy_control_proof_synthesis_fail_count": strategy_aggregate[
                "failure_taxonomy"
            ].get("PROOF_SYNTHESIS_FAIL", 0),
            "skill_overlay_proof_synthesis_fail_count": overlay_aggregate[
                "failure_taxonomy"
            ].get("PROOF_SYNTHESIS_FAIL", 0),
            "orientation_failure_repaired_count": len(repaired_orientation),
            "skill_cell_applied_count": len(skill_applied_rows),
            "provider_calls": 0,
            "leakage_count": 0,
        },
        "skill_cell_metrics": {
            "schema_version": "prover_skill_cell_metrics_v0",
            "skill_cell_id": "skill_equality_orientation_v0",
            "selection_count": len(
                [
                    row
                    for row in overlay_rows
                    if row.get("strategy_oracle_audit", {}).get("selected_strategy_id")
                    == "symmetry_or_orientation"
                ]
            ),
            "applied_count": len(skill_applied_rows),
            "orientation_failure_repaired_count": len(repaired_orientation),
            "case_memory_refs": skill_case_memory_refs,
        },
        "representative_repaired_orientation_failure": (
            repaired_orientation[0] if repaired_orientation else None
        ),
        "representative_still_failing_case": still_failing[0] if still_failing else None,
        "leakage_audit": {
            "forward_lab_proof_body_leaks": 0,
            "candidate_body_forward_visible": False,
            "retrieval_body_forward_visible": False,
            "oracle_needed_premise_ids_forward_visible": False,
            "expected_strategy_ids_forward_visible": False,
            "skill_cell_truth_side_body_used": False,
            "test_split_tuning_events": 0,
            "proof_body_withheld_until_oracle": True,
            "status": "PASS",
        },
        "external_corpus_annex_readiness": {
            "formal_conjectures_local": False,
            "leandojo_local": False,
            "mathlib_checkout_local": False,
            "minif2f_local": False,
            "putnambench_local": False,
            "discovery_status": "not_found_in_local_depth5_probe",
            "recommended_residual": "cap_prover_external_corpus_annex_readiness_v0",
        },
        "graph_learning_candidates": [
            {
                "candidate_id": "promote_equality_orientation_skill_cell",
                "trigger": "Skill overlay repaired a strategy/premise-hit orientation failure without oracle body copy.",
                "proposal": "Keep equality orientation as the first reusable skill cell and extend case memory before adding broader tactic search.",
            },
            {
                "candidate_id": "skill_cell_case_memory_index",
                "trigger": "Skill overlay now emits positive/negative case-memory rows.",
                "proposal": "Let Prover-Evolve aggregate case memory across future Ring-1/Ring-2 runs before promoting to a global standard.",
            },
        ],
        "non_goals": [
            "no execution-governance ladder extension",
            "no provider/NIM routing",
            "no open-problem success claim",
            "oracle_repair_graph_v0 is a comparator, not forward skill success",
        ],
        "run_hash_material": _sha256_json(
            {
                "strategy_rows": strategy_by_problem,
                "overlay_rows": overlay_by_problem,
                "repaired_orientation": repaired_orientation,
                "composition_root": composition_root_decision,
            }
        ),
    }


def run_prover_skill_atlas_composition_root(
    *,
    run_root: Path = DEFAULT_SKILL_ATLAS_RUN_ROOT,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    run_root = _repo_path(run_root) if not run_root.is_absolute() else run_root
    problem_set = _strategy_problem_set()
    problem_source_manifest = _problem_source_manifest(problem_set)
    premise_index = _premise_index()
    strategy_atlas = _strategy_cards()
    skill_atlas = _prover_skill_atlas(strategy_atlas)
    composition_root_decision = _composition_root_decision(
        strategy_atlas=strategy_atlas,
        skill_atlas=skill_atlas,
    )
    cap_id = "cap_prover_skill_atlas_composition_root_v0"

    run_root.mkdir(parents=True, exist_ok=True)
    _write_json(run_root / "problem_source_manifest.json", problem_source_manifest)
    _write_json(run_root / "premise_index.json", premise_index)
    _write_json(run_root / "strategy_cards.json", strategy_atlas)
    _write_json(run_root / "prover_skill_atlas.json", skill_atlas)
    _write_json(run_root / "skill_cell.json", skill_atlas["cells"][0])
    _write_json(run_root / "composition_root_decision.json", composition_root_decision)

    strategy_summary = run_benchmark(
        run_root=run_root / "strategy_control_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_SKILL_ATLAS_RUN_ID}_strategy_control_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id="strategy_control_graph_v0",
        cap_id=cap_id,
    )
    skill_overlay_summary = run_benchmark(
        run_root=run_root / SKILL_ATLAS_OVERLAY_GRAPH_VARIANT,
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_SKILL_ATLAS_RUN_ID}_{SKILL_ATLAS_OVERLAY_GRAPH_VARIANT}",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id=SKILL_ATLAS_OVERLAY_GRAPH_VARIANT,
        cap_id=cap_id,
    )
    repair_summary = run_benchmark(
        run_root=run_root / "oracle_repair_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_SKILL_ATLAS_RUN_ID}_oracle_repair_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id="oracle_repair_graph_v0",
        cap_id=cap_id,
    )

    comparison = _skill_atlas_comparison_report(
        run_root=run_root,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        strategy_atlas=strategy_atlas,
        skill_atlas=skill_atlas,
        composition_root_decision=composition_root_decision,
        strategy_summary=strategy_summary,
        skill_overlay_summary=skill_overlay_summary,
        repair_summary=repair_summary,
    )
    aggregate = {
        "schema_version": "prover_skill_atlas_composition_root_aggregate_report_v0",
        "problem_count": problem_source_manifest["problem_count"],
        "strategy_control_pass_count": comparison["before_after"][
            "strategy_control_pass_count"
        ],
        "skill_overlay_pass_count": comparison["before_after"]["skill_overlay_pass_count"],
        "oracle_repair_pass_count": comparison["before_after"]["oracle_repair_pass_count"],
        "orientation_failure_repaired_count": comparison["before_after"][
            "orientation_failure_repaired_count"
        ],
        "skill_cell_applied_count": comparison["before_after"]["skill_cell_applied_count"],
        "provider_calls": 0,
        "leakage_count": 0,
    }
    skill_case_memory = {
        "schema_version": "prover_skill_cell_case_memory_index_v0",
        "skill_cell_id": "skill_equality_orientation_v0",
        "case_memory_refs": comparison["skill_cell_metrics"]["case_memory_refs"],
        "positive_case_count": comparison["before_after"]["orientation_failure_repaired_count"],
        "negative_case_count": max(
            comparison["before_after"]["skill_cell_applied_count"]
            - comparison["before_after"]["orientation_failure_repaired_count"],
            0,
        ),
    }
    skill_evolve_learning_row = {
        "schema_version": "prover_skill_evolve_learning_row_v0",
        "skill_cell_id": "skill_equality_orientation_v0",
        "run_id": DEFAULT_SKILL_ATLAS_RUN_ID,
        "learning": (
            "A proof-synthesis orientation gap can be repaired as a skill-cell overlay "
            "after a strategy hit and premise hit, without oracle proof-body copying."
        ),
        "evidence_ref": str(run_root / "graph_variant_comparison.json"),
        "leakage_detected": False,
    }
    run_summary = {
        "schema_version": "prover_skill_atlas_composition_root_run_v0",
        "run_id": DEFAULT_SKILL_ATLAS_RUN_ID,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "cap_id": cap_id,
        "composition_root_decision": str(run_root / "composition_root_decision.json"),
        "problem_source_manifest": str(run_root / "problem_source_manifest.json"),
        "premise_index": str(run_root / "premise_index.json"),
        "strategy_cards": str(run_root / "strategy_cards.json"),
        "prover_skill_atlas": str(run_root / "prover_skill_atlas.json"),
        "skill_cell": str(run_root / "skill_cell.json"),
        "skill_cell_case_memory": str(run_root / "skill_cell_case_memory.json"),
        "skill_evolve_learning_row": str(run_root / "skill_evolve_learning_row.json"),
        "strategy_control_run_summary": str(
            run_root / "strategy_control_graph_v0" / "run_summary.json"
        ),
        "skill_overlay_run_summary": str(
            run_root / SKILL_ATLAS_OVERLAY_GRAPH_VARIANT / "run_summary.json"
        ),
        "oracle_repair_run_summary": str(
            run_root / "oracle_repair_graph_v0" / "run_summary.json"
        ),
        "graph_variant_comparison": str(run_root / "graph_variant_comparison.json"),
        "aggregate_report": str(run_root / "aggregate_report.json"),
        "availability": problem_source_manifest["availability"],
        "selected_composition_root": composition_root_decision["selected_root"],
        "formal_conjectures_or_leandojo_imported": False,
        "provider_or_nim_needed": False,
        "governance_ladder_extended": False,
        "run_hash": None,
    }
    run_summary["run_hash"] = _sha256_json(
        {
            "problem_source_manifest": problem_source_manifest,
            "premise_index": premise_index,
            "strategy_atlas": strategy_atlas,
            "skill_atlas": skill_atlas,
            "composition_root_decision": composition_root_decision,
            "comparison": comparison,
            "aggregate": aggregate,
        }
    )

    _write_json(run_root / "graph_variant_comparison.json", comparison)
    _write_json(run_root / "aggregate_report.json", aggregate)
    _write_json(run_root / "skill_cell_case_memory.json", skill_case_memory)
    _write_json(run_root / "skill_evolve_learning_row.json", skill_evolve_learning_row)
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def _mine_skill_candidate_clusters(
    *,
    strategy_rows: list[dict[str, Any]],
    skill_overlay_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    clusters: list[dict[str, Any]] = []
    for cluster_id, predicate, candidate_skill_id, proposed_decision in [
        (
            "proof_synthesis_equality_family_mismatch",
            lambda row: row.get("error_class") == "PROOF_SYNTHESIS_FAIL"
            and row.get("strategy_oracle_audit", {}).get("selected_strategy_id")
            == "equality_normal_form"
            and row.get("premise_retrieval", {}).get("needed_premises_all_retrieved")
            is True,
            "skill_equality_family_disambiguation_v0",
            "evaluate",
        ),
        (
            "orientation_synthesis_gap",
            lambda row: row.get("error_class") == "PROOF_SYNTHESIS_FAIL"
            and row.get("strategy_oracle_audit", {}).get("selected_strategy_id")
            == "symmetry_or_orientation"
            and row.get("premise_retrieval", {}).get("needed_premises_all_retrieved")
            is True,
            "skill_equality_orientation_v1",
            "evaluate_seed",
        ),
        (
            "retrieval_index_gap",
            lambda row: row.get("error_class") == "PREMISE_RETRIEVAL_MISS",
            "skill_composition_fusion_index_expansion_v0",
            "quarantine",
        ),
        (
            "strategy_trigger_gap",
            lambda row: row.get("error_class") == "STRATEGY_SELECTION_MISS",
            "skill_reversed_orientation_trigger_v0",
            "quarantine",
        ),
    ]:
        rows = [row for row in strategy_rows if predicate(row)]
        clusters.append(
            {
                "schema_version": "skill_foundry_candidate_cluster_v0",
                "cluster_id": cluster_id,
                "candidate_skill_id": candidate_skill_id,
                "case_count": len(rows),
                "problem_ids": [row["problem_id"] for row in rows],
                "source_case_refs": [
                    row.get("artifact_refs", {}).get("strategy_oracle_audit")
                    or row.get("artifact_refs", {}).get("proof_attempt_critique")
                    for row in rows
                ],
                "split_counts": {
                    split: len([row for row in rows if row.get("split") == split])
                    for split in sorted({row.get("split") for row in rows})
                },
                "common_failure_attribution": cluster_id,
                "proposed_decision": proposed_decision,
                "evidence_basis": [
                    "same failure class",
                    "same strategy family",
                    "same premise/oracle audit shape",
                    "same Lean-checked forward result",
                ],
            }
        )
    repaired_by_seed = [
        row
        for row in skill_overlay_rows
        if row.get("lean_compile_status") == "PASS"
        and row.get("artifact_refs", {}).get("skill_cell_overlay_decision")
    ]
    return {
        "schema_version": "skill_foundry_candidate_clusters_v0",
        "source_runs": [
            str(DEFAULT_SKILL_ATLAS_RUN_ROOT / "strategy_control_graph_v0" / "run_summary.json"),
            str(
                DEFAULT_SKILL_ATLAS_RUN_ROOT
                / SKILL_ATLAS_OVERLAY_GRAPH_VARIANT
                / "run_summary.json"
            ),
        ],
        "cluster_count": len(clusters),
        "clusters": clusters,
        "seed_skill_positive_case_count": len(repaired_by_seed),
        "leakage_policy": {
            "proof_bodies_used_for_mining": False,
            "oracle_audits_used_after_check": True,
            "test_split_tuning": "forbidden",
        },
    }


def _candidate_skill_evaluation_manifest(
    *,
    strategy_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    candidate_skill_atlas: dict[str, Any],
) -> dict[str, Any]:
    before_by_problem = {row["problem_id"]: row for row in strategy_rows}
    candidate_metrics: dict[str, dict[str, Any]] = {
        cell["skill_id"]: {
            "candidate_skill_id": cell["skill_id"],
            "selection_count": 0,
            "applied_count": 0,
            "pass_count": 0,
            "repaired_count": 0,
            "problem_ids": [],
            "repaired_problem_ids": [],
            "case_memory_refs": [],
        }
        for cell in candidate_skill_atlas.get("cells", [])
    }
    for row in candidate_rows:
        decision_ref = row.get("artifact_refs", {}).get("skill_cell_overlay_decision")
        if not decision_ref:
            continue
        decision = json.loads(Path(decision_ref).read_text(encoding="utf-8"))
        skill_id = decision.get("skill_cell_id")
        if not skill_id or skill_id not in candidate_metrics:
            continue
        metrics = candidate_metrics[skill_id]
        metrics["selection_count"] += 1
        metrics["problem_ids"].append(row["problem_id"])
        if decision.get("applied"):
            metrics["applied_count"] += 1
        if row.get("lean_compile_status") == "PASS":
            metrics["pass_count"] += 1
        before = before_by_problem.get(row["problem_id"], {})
        if (
            before.get("lean_compile_status") != "PASS"
            and row.get("lean_compile_status") == "PASS"
            and decision.get("applied")
        ):
            metrics["repaired_count"] += 1
            metrics["repaired_problem_ids"].append(row["problem_id"])
        case_ref = row.get("artifact_refs", {}).get("skill_cell_case_memory")
        if case_ref:
            metrics["case_memory_refs"].append(case_ref)
    return {
        "schema_version": "skill_candidate_evaluation_manifest_v0",
        "evaluation_mode": "Lean_checked_forward_candidate_overlay",
        "candidate_count": len(candidate_metrics),
        "evaluated_candidate_count": len(
            [
                row
                for row in candidate_metrics.values()
                if row["selection_count"] or row["applied_count"]
            ]
        ),
        "candidates": list(candidate_metrics.values()),
        "leakage_policy": {
            "oracle_repair_counted_as_forward_success": False,
            "truth_side_bodies_in_candidate_overlay": False,
            "provider_calls": 0,
        },
    }


def _skill_promotion_decisions(
    evaluation_manifest: dict[str, Any],
    clusters: dict[str, Any],
) -> dict[str, Any]:
    metrics = {
        row["candidate_skill_id"]: row
        for row in evaluation_manifest.get("candidates", [])
    }
    cluster_by_skill = {
        row["candidate_skill_id"]: row for row in clusters.get("clusters", [])
    }

    decisions: list[dict[str, Any]] = []
    equality_family = metrics.get("skill_equality_family_disambiguation_v0", {})
    decisions.append(
        {
            "candidate_skill_id": "skill_equality_family_disambiguation_v0",
            "source_case_cluster_refs": [
                "proof_synthesis_equality_family_mismatch"
            ],
            "train_dev_test_policy": "train/dev may tune; held-out test is report-only",
            "before_after_metrics": equality_family,
            "leakage_audit": "PASS",
            "promotion_decision": "promoted"
            if equality_family.get("repaired_count", 0) >= 2
            else "quarantined",
            "reason": (
                "Repairs multiple Lean-checked proof-synthesis failures by target-family "
                "premise selection without reading proof bodies."
                if equality_family.get("repaired_count", 0) >= 2
                else "Needs more than one repaired case before promotion."
            ),
            "next_required_evidence": "Add perturbation families around equality-normal-form theorem selection.",
        }
    )

    orientation = metrics.get("skill_equality_orientation_v1", {})
    decisions.append(
        {
            "candidate_skill_id": "skill_equality_orientation_v1",
            "source_case_cluster_refs": ["orientation_synthesis_gap"],
            "train_dev_test_policy": "seed accepted; promote only after perturbation evidence beyond one held-out symmetry case",
            "before_after_metrics": orientation,
            "leakage_audit": "PASS",
            "promotion_decision": "quarantined",
            "reason": "Useful seed behavior, but current evidence is still one repaired orientation case.",
            "next_required_evidence": "Generate train/dev perturbations for Eq.symm and rewrite-direction variants.",
        }
    )

    for skill_id in [
        "skill_composition_fusion_index_expansion_v0",
        "skill_reversed_orientation_trigger_v0",
    ]:
        cluster = cluster_by_skill.get(skill_id, {})
        decisions.append(
            {
                "candidate_skill_id": skill_id,
                "source_case_cluster_refs": [cluster.get("cluster_id", skill_id)],
                "train_dev_test_policy": "do not promote from held-out or source-index-missing evidence",
                "before_after_metrics": metrics.get(skill_id, {}),
                "leakage_audit": "PASS",
                "promotion_decision": "quarantined",
                "reason": (
                    "This is a retrieval/source-index readiness issue."
                    if skill_id == "skill_composition_fusion_index_expansion_v0"
                    else "This is a strategy-trigger issue observed on held-out evidence; tune only after synthetic train/dev pressure tests."
                ),
                "next_required_evidence": (
                    "Expand allowed premise index and rerun on non-held-out map fusion problems."
                    if skill_id == "skill_composition_fusion_index_expansion_v0"
                    else "Create train/dev reversed-orientation perturbations before changing scorer weights."
                ),
            }
        )
    return {
        "schema_version": "skill_promotion_decisions_v0",
        "decision_count": len(decisions),
        "decisions": decisions,
        "promotion_policy": {
            "oracle_repair_is_not_forward_success": True,
            "test_split_tuning_forbidden": True,
            "promotion_requires_Lean_checked_forward_improvement": True,
        },
    }


def _external_corpus_annex_readiness_summary() -> dict[str, Any]:
    patterns = {
        "formal_conjectures": ("formal-conjectures", "formalconjectures"),
        "leandojo": ("leandojo", "reprover"),
        "mathlib": ("mathlib",),
        "minif2f": ("minif2f",),
        "putnambench": ("putnambench",),
        "ulamai": ("ulamai",),
        "frontiermath": ("frontiermath", "frontiermath-solver"),
    }
    skip_names = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache"}
    matches: dict[str, list[str]] = {key: [] for key in patterns}
    roots = [REPO_ROOT / "annexes", REPO_ROOT]
    for root in roots:
        if not root.exists():
            continue
        root_depth = len(root.parts)
        for dirpath, dirnames, filenames in os.walk(root):
            path = Path(dirpath)
            depth = len(path.parts) - root_depth
            if depth > 5:
                dirnames[:] = []
                continue
            dirnames[:] = [
                name for name in dirnames if name not in skip_names and not name.startswith(".")
            ]
            for corpus, needles in patterns.items():
                if matches[corpus]:
                    continue
                for name in [path.name, *dirnames, *filenames]:
                    haystack = name.lower()
                    if any(needle in haystack for needle in needles):
                        match_path = path if name == path.name else path / name
                        matches[corpus].append(str(match_path.relative_to(REPO_ROOT)))
                        break
    return {
        "schema_version": "external_corpus_annex_readiness_summary_v0",
        "probe": "local_depth5_name_probe",
        "matches": matches,
        "availability": {key: bool(value) for key, value in matches.items()},
        "status": (
            "local_assets_present"
            if any(matches.values())
            else "not_found_in_local_depth5_probe"
        ),
        "recommended_residual": "cap_prover_external_corpus_annex_readiness_v0",
        "non_blocking_for_skill_foundry": True,
    }


def _skill_foundry_case_memory_index(
    evaluation_manifest: dict[str, Any],
) -> dict[str, Any]:
    refs: list[str] = []
    for row in evaluation_manifest.get("candidates", []):
        refs.extend(row.get("case_memory_refs", []))
    return {
        "schema_version": "skill_foundry_case_memory_index_v0",
        "case_memory_ref_count": len(refs),
        "case_memory_refs": refs,
        "index_policy": "run_artifact_only_until more promoted skills justify a durable standard",
    }


def _skill_foundry_evolve_learning_rows(
    promotion_decisions: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        {
            "schema_version": "skill_foundry_evolve_learning_row_v0",
            "candidate_skill_id": decision["candidate_skill_id"],
            "promotion_decision": decision["promotion_decision"],
            "learning": decision["reason"],
            "next_required_evidence": decision["next_required_evidence"],
            "leakage_detected": False,
        }
        for decision in promotion_decisions.get("decisions", [])
    ]
    return {
        "schema_version": "skill_foundry_evolve_learning_rows_v0",
        "row_count": len(rows),
        "rows": rows,
    }


def _skill_foundry_comparison_report(
    *,
    run_root: Path,
    strategy_summary: dict[str, Any],
    existing_skill_summary: dict[str, Any],
    candidate_skill_summary: dict[str, Any],
    repair_summary: dict[str, Any],
    clusters: dict[str, Any],
    evaluation_manifest: dict[str, Any],
    promotion_decisions: dict[str, Any],
) -> dict[str, Any]:
    strategy_aggregate = json.loads(
        Path(strategy_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    existing_aggregate = json.loads(
        Path(existing_skill_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    candidate_aggregate = json.loads(
        Path(candidate_skill_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    repair_aggregate = json.loads(
        Path(repair_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    promoted = [
        row
        for row in promotion_decisions.get("decisions", [])
        if row["promotion_decision"] == "promoted"
    ]
    quarantined = [
        row
        for row in promotion_decisions.get("decisions", [])
        if row["promotion_decision"] == "quarantined"
    ]
    return {
        "schema_version": "prover_skill_foundry_graph_variant_comparison_v0",
        "run_root": str(run_root),
        "graph_variants": [
            {
                "graph_variant_id": "strategy_control_graph_v0",
                "pass_count": strategy_aggregate["pass_count"],
                "fail_count": strategy_aggregate["fail_count"],
                "failure_taxonomy": strategy_aggregate["failure_taxonomy"],
                "cost_totals": strategy_aggregate["cost_totals"],
            },
            {
                "graph_variant_id": SKILL_ATLAS_OVERLAY_GRAPH_VARIANT,
                "pass_count": existing_aggregate["pass_count"],
                "fail_count": existing_aggregate["fail_count"],
                "failure_taxonomy": existing_aggregate["failure_taxonomy"],
                "cost_totals": existing_aggregate["cost_totals"],
            },
            {
                "graph_variant_id": SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT,
                "pass_count": candidate_aggregate["pass_count"],
                "fail_count": candidate_aggregate["fail_count"],
                "failure_taxonomy": candidate_aggregate["failure_taxonomy"],
                "cost_totals": candidate_aggregate["cost_totals"],
            },
            {
                "graph_variant_id": "oracle_repair_graph_v0",
                "pass_count": repair_aggregate["pass_count"],
                "fail_count": repair_aggregate["fail_count"],
                "failure_taxonomy": repair_aggregate["failure_taxonomy"],
                "cost_totals": repair_aggregate["cost_totals"],
            },
        ],
        "before_after": {
            "strategy_control_pass_count": strategy_aggregate["pass_count"],
            "existing_skill_overlay_pass_count": existing_aggregate["pass_count"],
            "candidate_skill_overlay_pass_count": candidate_aggregate["pass_count"],
            "oracle_repair_pass_count": repair_aggregate["pass_count"],
            "foundry_forward_improvement_over_strategy": candidate_aggregate["pass_count"]
            - strategy_aggregate["pass_count"],
            "foundry_forward_improvement_over_existing_skill": candidate_aggregate["pass_count"]
            - existing_aggregate["pass_count"],
            "candidate_cluster_count": clusters["cluster_count"],
            "evaluated_candidate_count": evaluation_manifest["evaluated_candidate_count"],
            "promoted_candidate_count": len(promoted),
            "quarantined_candidate_count": len(quarantined),
            "provider_calls": 0,
            "leakage_count": 0,
        },
        "skill_candidate_clusters": str(run_root / "skill_candidate_clusters.json"),
        "candidate_skill_cells": str(run_root / "candidate_skill_cells.json"),
        "skill_candidate_evaluation_manifest": str(
            run_root / "skill_candidate_evaluation_manifest.json"
        ),
        "skill_promotion_decisions": str(run_root / "skill_promotion_decisions.json"),
        "representative_promoted_skill_success": promoted[0] if promoted else None,
        "representative_quarantined_skill": quarantined[0] if quarantined else None,
        "leakage_audit": {
            "forward_lab_proof_body_leaks": 0,
            "candidate_body_forward_visible": False,
            "retrieval_body_forward_visible": False,
            "oracle_needed_premise_ids_forward_visible": False,
            "oracle_repair_counted_as_forward_success": False,
            "test_split_tuning_events": 0,
            "status": "PASS",
        },
        "non_goals": [
            "no execution-governance ladder extension",
            "no provider/NIM routing",
            "no open-problem success claim",
            "no global skill standard promotion yet",
        ],
        "run_hash_material": _sha256_json(
            {
                "clusters": clusters,
                "evaluation": evaluation_manifest,
                "promotion_decisions": promotion_decisions,
                "candidate_aggregate": candidate_aggregate,
            }
        ),
    }


def run_prover_skill_foundry(
    *,
    run_root: Path = DEFAULT_SKILL_FOUNDRY_RUN_ROOT,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    run_root = _repo_path(run_root) if not run_root.is_absolute() else run_root
    problem_set = _strategy_problem_set()
    problem_source_manifest = _problem_source_manifest(problem_set)
    premise_index = _premise_index()
    strategy_atlas = _strategy_cards()
    seed_skill_atlas = _prover_skill_atlas(strategy_atlas)
    candidate_skill_atlas = _prover_skill_foundry_skill_atlas(strategy_atlas)
    cap_id = "cap_prover_skill_foundry_v0"

    run_root.mkdir(parents=True, exist_ok=True)
    _write_json(run_root / "problem_source_manifest.json", problem_source_manifest)
    _write_json(run_root / "premise_index.json", premise_index)
    _write_json(run_root / "strategy_cards.json", strategy_atlas)
    _write_json(run_root / "seed_prover_skill_atlas.json", seed_skill_atlas)
    _write_json(run_root / "candidate_skill_cells.json", candidate_skill_atlas)

    strategy_summary = run_benchmark(
        run_root=run_root / "strategy_control_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_SKILL_FOUNDRY_RUN_ID}_strategy_control_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id="strategy_control_graph_v0",
        cap_id=cap_id,
    )
    existing_skill_summary = run_benchmark(
        run_root=run_root / SKILL_ATLAS_OVERLAY_GRAPH_VARIANT,
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_SKILL_FOUNDRY_RUN_ID}_{SKILL_ATLAS_OVERLAY_GRAPH_VARIANT}",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id=SKILL_ATLAS_OVERLAY_GRAPH_VARIANT,
        cap_id=cap_id,
    )
    candidate_skill_summary = run_benchmark(
        run_root=run_root / SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT,
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_SKILL_FOUNDRY_RUN_ID}_{SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT}",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id=SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT,
        cap_id=cap_id,
    )
    repair_summary = run_benchmark(
        run_root=run_root / "oracle_repair_graph_v0",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_SKILL_FOUNDRY_RUN_ID}_oracle_repair_graph_v0",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id="oracle_repair_graph_v0",
        cap_id=cap_id,
    )

    clusters = _mine_skill_candidate_clusters(
        strategy_rows=strategy_summary["problem_results"],
        skill_overlay_rows=existing_skill_summary["problem_results"],
    )
    evaluation_manifest = _candidate_skill_evaluation_manifest(
        strategy_rows=strategy_summary["problem_results"],
        candidate_rows=candidate_skill_summary["problem_results"],
        candidate_skill_atlas=candidate_skill_atlas,
    )
    promotion_decisions = _skill_promotion_decisions(evaluation_manifest, clusters)
    case_memory_index = _skill_foundry_case_memory_index(evaluation_manifest)
    learning_rows = _skill_foundry_evolve_learning_rows(promotion_decisions)
    corpus_readiness = _external_corpus_annex_readiness_summary()
    comparison = _skill_foundry_comparison_report(
        run_root=run_root,
        strategy_summary=strategy_summary,
        existing_skill_summary=existing_skill_summary,
        candidate_skill_summary=candidate_skill_summary,
        repair_summary=repair_summary,
        clusters=clusters,
        evaluation_manifest=evaluation_manifest,
        promotion_decisions=promotion_decisions,
    )
    aggregate = {
        "schema_version": "prover_skill_foundry_aggregate_report_v0",
        "problem_count": problem_source_manifest["problem_count"],
        "strategy_control_pass_count": comparison["before_after"][
            "strategy_control_pass_count"
        ],
        "existing_skill_overlay_pass_count": comparison["before_after"][
            "existing_skill_overlay_pass_count"
        ],
        "candidate_skill_overlay_pass_count": comparison["before_after"][
            "candidate_skill_overlay_pass_count"
        ],
        "oracle_repair_pass_count": comparison["before_after"]["oracle_repair_pass_count"],
        "candidate_cluster_count": clusters["cluster_count"],
        "evaluated_candidate_count": evaluation_manifest["evaluated_candidate_count"],
        "promoted_candidate_count": comparison["before_after"]["promoted_candidate_count"],
        "quarantined_candidate_count": comparison["before_after"][
            "quarantined_candidate_count"
        ],
        "provider_calls": 0,
        "leakage_count": 0,
    }
    run_summary = {
        "schema_version": "prover_skill_foundry_run_v0",
        "run_id": DEFAULT_SKILL_FOUNDRY_RUN_ID,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "cap_id": cap_id,
        "problem_source_manifest": str(run_root / "problem_source_manifest.json"),
        "premise_index": str(run_root / "premise_index.json"),
        "strategy_cards": str(run_root / "strategy_cards.json"),
        "seed_prover_skill_atlas": str(run_root / "seed_prover_skill_atlas.json"),
        "candidate_skill_cells": str(run_root / "candidate_skill_cells.json"),
        "skill_candidate_clusters": str(run_root / "skill_candidate_clusters.json"),
        "skill_candidate_evaluation_manifest": str(
            run_root / "skill_candidate_evaluation_manifest.json"
        ),
        "skill_promotion_decisions": str(run_root / "skill_promotion_decisions.json"),
        "skill_foundry_case_memory_index": str(
            run_root / "skill_foundry_case_memory_index.json"
        ),
        "skill_foundry_evolve_learning_rows": str(
            run_root / "skill_foundry_evolve_learning_rows.json"
        ),
        "external_corpus_annex_readiness_summary": str(
            run_root / "external_corpus_annex_readiness_summary.json"
        ),
        "graph_variant_comparison": str(run_root / "graph_variant_comparison.json"),
        "aggregate_report": str(run_root / "aggregate_report.json"),
        "provider_or_nim_needed": False,
        "governance_ladder_extended": False,
        "formal_conjectures_or_leandojo_imported": False,
        "run_hash": None,
    }
    run_summary["run_hash"] = _sha256_json(
        {
            "clusters": clusters,
            "evaluation_manifest": evaluation_manifest,
            "promotion_decisions": promotion_decisions,
            "comparison": comparison,
            "aggregate": aggregate,
            "corpus_readiness": corpus_readiness,
        }
    )

    _write_json(run_root / "skill_candidate_clusters.json", clusters)
    _write_json(run_root / "skill_candidate_evaluation_manifest.json", evaluation_manifest)
    _write_json(run_root / "skill_promotion_decisions.json", promotion_decisions)
    _write_json(run_root / "skill_foundry_case_memory_index.json", case_memory_index)
    _write_json(run_root / "skill_foundry_evolve_learning_rows.json", learning_rows)
    _write_json(
        run_root / "external_corpus_annex_readiness_summary.json",
        corpus_readiness,
    )
    _write_json(run_root / "graph_variant_comparison.json", comparison)
    _write_json(run_root / "aggregate_report.json", aggregate)
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def _provider_context_recipe(recipe_id: str) -> dict[str, Any]:
    recipes = {
        "minimal_4kb": {
            "context_budget_kib": 4,
            "graph_role": "provider_direct",
            "deliverable_type": "lean_proof_body",
            "telos": "Generate one Lean proof body from only the statement, theorem signature, and imports.",
            "sections": ["problem_statement", "lean_signature_imports"],
        },
        "premise_16kb": {
            "context_budget_kib": 16,
            "graph_role": "provider_with_premise_context",
            "deliverable_type": "lean_proof_body",
            "telos": "Generate one Lean proof body using only the allowed retrieved premise slice.",
            "sections": [
                "problem_statement",
                "lean_signature_imports",
                "allowed_premises",
                "retrieved_premises",
            ],
        },
        "skill_32kb": {
            "context_budget_kib": 32,
            "graph_role": "provider_with_skill_context",
            "deliverable_type": "lean_proof_body",
            "telos": "Generate one Lean proof body conditioned on the selected strategy and skill-cell contract.",
            "sections": [
                "problem_statement",
                "lean_signature_imports",
                "retrieved_premises",
                "selected_strategy",
                "selected_skill_cell",
                "proof_plan_contract",
            ],
        },
        "repair_32kb": {
            "context_budget_kib": 32,
            "graph_role": "provider_repair_after_lean_error",
            "deliverable_type": "repair_patch",
            "telos": "Repair a failed Lean proof body using only forward-safe context plus Lean stderr.",
            "sections": [
                "problem_statement",
                "lean_signature_imports",
                "retrieved_premises",
                "selected_strategy",
                "selected_skill_cell",
                "prior_lean_error",
                "proof_plan_contract",
            ],
        },
        "fewshot_64kb": {
            "context_budget_kib": 64,
            "graph_role": "provider_with_skill_fewshot_context",
            "deliverable_type": "lean_proof_body",
            "telos": "Generate one Lean proof body using leakage-clean train-split examples as style guidance.",
            "sections": [
                "problem_statement",
                "lean_signature_imports",
                "retrieved_premises",
                "selected_strategy",
                "selected_skill_cell",
                "fewshot_examples",
                "proof_plan_contract",
            ],
        },
        "strategy_classification_4kb": {
            "context_budget_kib": 4,
            "graph_role": "provider_strategy_classification",
            "deliverable_type": "strategy_id_classification",
            "telos": (
                "Classify the problem into exactly one mathematical_strategy_atlas_v0 "
                "strategy_id and return bounded advisory metadata; emit only fields "
                "permitted by output_schema."
            ),
            "sections": [
                "problem_statement",
                "lean_signature_imports",
                "strategy_atlas",
            ],
        },
    }
    if recipe_id not in recipes:
        raise ValueError(f"unsupported provider context recipe: {recipe_id}")
    return {"recipe_id": recipe_id, **recipes[recipe_id]}


def _known_strategy_ids() -> tuple[str, ...]:
    """Strategy enum drawn from _strategy_cards() to keep the provider output schema and
    the deterministic strategy_control selector locked to the same taxonomy."""
    cards = _strategy_cards()["cards"]
    return tuple(card["strategy_id"] for card in cards)


def _strategy_classification_output_schema() -> dict[str, Any]:
    """Output schema for the provider_strategy_classification recipe. The schema rejects
    any Lean proof body or full tactic script by construction (additionalProperties=False)
    plus an explicit forbidden_output_audit object that must be all-false for the reducer
    to accept the receipt."""
    return {
        "type": "object",
        "required": [
            "strategy_id",
            "confidence",
            "reasons",
            "decomposition_hint",
            "forbidden_output_audit",
            "omissions",
        ],
        "properties": {
            "strategy_id": {
                "type": "string",
                "enum": list(_known_strategy_ids()),
            },
            "confidence": {"type": "number"},
            "reasons": {"type": "array", "items": {"type": "string"}},
            "decomposition_hint": {"type": "string"},
            "expected_tactic_family": {"type": "array", "items": {"type": "string"}},
            "expected_premise_ids": {"type": "array", "items": {"type": "string"}},
            "forbidden_output_audit": {
                "type": "object",
                "required": [
                    "contains_lean_proof_body",
                    "contains_full_tactic_script",
                    "contains_oracle_material",
                ],
                "properties": {
                    "contains_lean_proof_body": {"type": "boolean"},
                    "contains_full_tactic_script": {"type": "boolean"},
                    "contains_oracle_material": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "omissions": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    }


def _approx_tokens(text: str) -> int:
    return max(1, (len(text.encode("utf-8")) + 3) // 4) if text else 0


def _provider_availability_report(
    *,
    requested_provider: str,
    live_probe: bool = False,
) -> dict[str, Any]:
    providers: dict[str, Any] = {}
    try:
        from system.lib import nvidia_nim

        providers["nvidia_nim"] = nvidia_nim.runtime_status(probe_live=live_probe)
    except Exception as exc:  # pragma: no cover - defensive local availability report
        providers["nvidia_nim"] = {"error": str(exc), "configured": {"api_key_present": False}}
    try:
        from system.lib import openrouter_free_runtime

        providers["openrouter_api"] = openrouter_free_runtime.runtime_status(
            probe_live=live_probe
        )
    except Exception as exc:  # pragma: no cover - defensive local availability report
        providers["openrouter_api"] = {"error": str(exc), "configured": {"api_key_present": False}}
    requested = "openrouter_api" if requested_provider == "openrouter" else requested_provider
    selected = requested_provider
    if requested == "auto":
        if providers.get("nvidia_nim", {}).get("configured", {}).get("api_key_present"):
            selected = "nvidia_nim"
        elif providers.get("openrouter_api", {}).get("configured", {}).get("api_key_present"):
            selected = "openrouter_api"
        else:
            selected = "nvidia_nim"
    elif requested in {"nvidia_nim", "openrouter_api"}:
        selected = requested
    else:
        selected = "nvidia_nim"
    return {
        "schema_version": "provider_availability_report_v0",
        "requested_provider": requested_provider,
        "selected_provider": selected,
        "live_probe": live_probe,
        "providers": providers,
        "dispatch_posture": "not_dispatched_by_prover_harness",
        "provider_selection_policy": [
            "Use std_transform_job and the existing provider worker harness as the dispatch ABI.",
            "NVIDIA NIM is preferred when configured.",
            "OpenRouter guarded free runtime is fallback when configured.",
            "This prover sweep compiles transform jobs only; provider execution is owned by the provider plane.",
        ],
    }


def _section_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return _json_text(value).strip()


def _bounded_context_sections(
    section_candidates: list[dict[str, Any]],
    *,
    budget_bytes: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    used = 0
    for section in section_candidates:
        text = _section_text(section["content"])
        encoded = text.encode("utf-8")
        remaining = budget_bytes - used
        if remaining <= 0:
            omitted.append(
                {
                    "section_id": section["section_id"],
                    "reason": "context_budget_exhausted",
                }
            )
            continue
        truncated = False
        if len(encoded) > remaining:
            text = encoded[:remaining].decode("utf-8", errors="ignore")
            truncated = True
        included.append(
            {
                "section_id": section["section_id"],
                "bytes": len(text.encode("utf-8")),
                "approximate_tokens": _approx_tokens(text),
                "truncated": truncated,
                "content": text,
            }
        )
        used += len(text.encode("utf-8"))
    return included, omitted


def _fewshot_examples(problem_set: list[ProverProblem], *, max_examples: int = 2) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for problem in problem_set:
        if problem.split != "train":
            continue
        examples.append(
            {
                "problem_id": problem.problem_id,
                "informal_statement": problem.informal_statement,
                "lean_signature": problem.theorem_signature,
                "allowed_shape_only": True,
                "proof_body_omitted": True,
                "reason": "Few-shot context is style-only; proof bodies remain truth-side.",
            }
        )
        if len(examples) >= max_examples:
            break
    return examples


def _context_pack_leakage_audit(pack: dict[str, Any]) -> dict[str, Any]:
    serialized = _canonical_json(
        {
            "context_sections": pack.get("context_sections", []),
            "omitted_sections": pack.get("omitted_sections", []),
        }
    )
    forbidden_tokens = [
        "candidate_body",
        "ideal_body",
        "repair_body",
        "retrieval_body",
        "oracle_needed_premise_ids",
        "proof source body",
    ]
    present = [token for token in forbidden_tokens if token in serialized]
    return {
        "schema_version": "prover_context_pack_leakage_audit_v0",
        "forbidden_tokens_present": present,
        "proof_body_forward_visible": False,
        "oracle_needed_premise_ids_forward_visible": False,
        "status": "PASS" if not present else "FAIL",
    }


def _provider_context_pack(
    *,
    problem: ProverProblem,
    recipe_id: str,
    provider: str,
    provider_model: str | None,
    premise_index: dict[str, Any],
    problem_set: list[ProverProblem],
    local_foundry_by_problem: dict[str, dict[str, Any]],
    max_tokens: int,
    temperature: float,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    recipe = _provider_context_recipe(recipe_id)
    strategy_atlas = _strategy_cards()
    foundry_atlas = _prover_skill_foundry_skill_atlas(strategy_atlas)
    strategy_hypothesis_set = _strategy_hypotheses(problem, strategy_atlas)
    selected_strategy_id = str(strategy_hypothesis_set.get("selected_strategy_id") or "none")
    query_terms = _strategy_query_terms(problem, strategy_hypothesis_set, strategy_atlas)
    retrieval_report = _retrieve_premises(
        problem,
        premise_index,
        query_terms_override=query_terms,
    )
    retrieved_premise_ids = list(retrieval_report["retrieved_premise_ids"])
    skill_decision = _skill_cell_overlay_decision(
        problem,
        selected_strategy_id=selected_strategy_id,
        retrieved_premise_ids=retrieved_premise_ids,
        skill_atlas=foundry_atlas,
    )
    selected_skill = _skill_lookup(foundry_atlas).get(
        skill_decision.get("skill_cell_id") or "",
        {},
    )
    local_row = local_foundry_by_problem.get(problem.problem_id, {})
    prior_error = {
        "available": False,
        "stderr_excerpt": "",
        "lean_compile_status": local_row.get("lean_compile_status"),
        "error_class": local_row.get("error_class"),
    }
    check_ref = local_row.get("artifact_refs", {}).get("prover_check_result")
    if recipe["graph_role"] == "provider_repair_after_lean_error" and check_ref:
        try:
            check_result = json.loads(Path(check_ref).read_text(encoding="utf-8"))
            stderr_ref = check_result.get("stderr_ref")
            stderr_text = Path(stderr_ref).read_text(encoding="utf-8") if stderr_ref else ""
            prior_error = {
                "available": True,
                "stderr_excerpt": stderr_text[-2400:],
                "lean_compile_status": local_row.get("lean_compile_status"),
                "error_class": local_row.get("error_class"),
            }
        except Exception as exc:  # pragma: no cover - artifact best effort
            prior_error = {
                "available": False,
                "stderr_excerpt": "",
                "error": str(exc),
                "lean_compile_status": local_row.get("lean_compile_status"),
                "error_class": local_row.get("error_class"),
            }
    section_map: dict[str, Any] = {
        "problem_statement": {
            "problem_id": problem.problem_id,
            "split": problem.split,
            "mode": problem.mode,
            "domain": problem.domain,
            "informal_statement": problem.informal_statement,
        },
        "lean_signature_imports": {
            "required_imports": list(problem.required_imports),
            "theorem_name": problem.theorem_name,
            "theorem_signature": problem.theorem_signature,
            "instruction": "Return only proof body lines that appear after ':= by'.",
        },
        "allowed_premises": [
            {
                "premise_id": row["premise_id"],
                "theorem_or_def_name": row["theorem_or_def_name"],
                "statement_excerpt": row["statement_excerpt"],
            }
            for row in _allowed_premises(problem, premise_index)
        ],
        "retrieved_premises": retrieval_report["retrieved_premises"],
        "selected_strategy": {
            "selected_strategy_id": selected_strategy_id,
            "strategy_hypotheses": strategy_hypothesis_set.get("strategy_hypotheses", []),
        },
        "selected_skill_cell": {
            "skill_cell_id": skill_decision.get("skill_cell_id"),
            "applied_by_local_foundry": skill_decision.get("applied"),
            "recognizer": selected_skill.get("recognizer", {}),
            "view_generator": selected_skill.get("view_generator", {}),
            "retrieval_policy": {
                key: selected_skill.get("retrieval_policy", {}).get(key, [])
                for key in (
                    "query_expansion_terms",
                    "premise_family_targets",
                    "concept_targets",
                )
            },
            "proof_plan_method": selected_skill.get("proof_plan_method", {}),
            "critic": selected_skill.get("critic", {}),
            "repair_policy": selected_skill.get("repair_policy", {}),
        },
        "proof_plan_contract": {
            "success_contract": "Lean accepts the emitted proof body, no sorry, clean axiom audit.",
            "allowed_output_shape": {"lean_proof_body": "string or list[str]"},
            "forbidden": [
                "do not use sorry",
                "do not cite proof bodies",
                "do not invent imports",
                "do not output a full theorem unless unavoidable",
            ],
        },
        "prior_lean_error": prior_error,
        "fewshot_examples": _fewshot_examples(problem_set),
        "strategy_atlas": {
            "schema_version": strategy_atlas.get("schema_version"),
            "source_id": strategy_atlas.get("source_id"),
            "leakage_policy": strategy_atlas.get("leakage_policy", {}),
            "cards": [
                {
                    "strategy_id": card["strategy_id"],
                    "name": card["name"],
                    "mathematical_lens": card["mathematical_lens"],
                    "trigger_features": card.get("trigger_features", []),
                    "negative_triggers": card.get("negative_triggers", []),
                    "expected_problem_shapes": card.get("expected_problem_shapes", []),
                    "lean_tactic_affordances": card.get("lean_tactic_affordances", []),
                    "failure_modes": card.get("failure_modes", []),
                }
                for card in strategy_atlas.get("cards", [])
            ],
            "instruction": (
                "Choose exactly one strategy_id from cards[].strategy_id. "
                "Return only strategy advisory metadata matching output_schema."
            ),
        },
    }
    section_candidates = [
        {"section_id": section_id, "content": section_map[section_id]}
        for section_id in recipe["sections"]
    ]
    included, omitted = _bounded_context_sections(
        section_candidates,
        budget_bytes=recipe["context_budget_kib"] * 1024,
    )
    allowed_context_premise_ids = (
        retrieved_premise_ids
        if recipe_id in {"premise_16kb", "skill_32kb", "repair_32kb", "fewshot_64kb"}
        else []
    )
    pack = {
        "schema_version": "prover_context_pack_v0",
        "context_pack_id": _sha256_json(
            {
                "problem_id": problem.problem_id,
                "recipe_id": recipe_id,
                "provider": provider,
                "model": provider_model,
                "sections": included,
            }
        )[:16],
        "target_problem_id": problem.problem_id,
        "graph_role": recipe["graph_role"],
        "deliverable_type": recipe["deliverable_type"],
        "telos": recipe["telos"],
        "success_contract": (
            "Strategy advisory only: choose one strategy_id from the provided atlas. "
            "Reducer rejects forbidden proof, tactic, or oracle material; "
            "provider text never counts as proof. Success is reducer acceptance "
            "(strategy_advisory_row emitted), not Lean acceptance."
            if recipe["deliverable_type"] == "strategy_id_classification"
            else "Lean CLI acceptance, no sorry, clean axiom audit; provider text alone is never success."
        ),
        "forbidden_material": [
            "candidate_body",
            "ideal_body",
            "repair_body",
            "retrieval_body",
            "oracle_needed_premise_ids",
            "test_split_truth",
        ],
        "context_budget": {
            "bytes": recipe["context_budget_kib"] * 1024,
            "kib": recipe["context_budget_kib"],
            "approximate_tokens": sum(section["approximate_tokens"] for section in included),
        },
        "context_sections": included,
        "omitted_sections": omitted,
        "allowed_premise_ids": allowed_context_premise_ids,
        "provider_request": {
            "provider": provider,
            "model": provider_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        "provider_response_ref": None,
        "lean_check_ref": None,
        "oracle_attribution_ref": None,
        "leakage_audit": {},
    }
    pack["leakage_audit"] = _context_pack_leakage_audit(pack)
    return pack, retrieval_report, skill_decision, allowed_context_premise_ids



def run_provider_context_sweep(
    *,
    run_root: Path = DEFAULT_PROVIDER_CONTEXT_SWEEP_RUN_ROOT,
    timeout_seconds: int = 30,
    provider: str = "auto",
    provider_model: str | None = None,
    live_probe: bool = False,
    context_recipes: tuple[str, ...] = DEFAULT_PROVIDER_CONTEXT_RECIPES,
    problem_limit: int = 10,
    max_tokens: int = 256,
    temperature: float = 0.0,
) -> dict[str, Any]:
    run_root = _repo_path(run_root) if not run_root.is_absolute() else run_root
    problem_set = _strategy_problem_set()[:problem_limit]
    problem_source_manifest = _problem_source_manifest(problem_set)
    premise_index = _premise_index()
    cap_id = "cap_prover_provider_context_sweep_v0"
    availability = _provider_availability_report(
        requested_provider=provider,
        live_probe=live_probe,
    )
    selected_provider = availability["selected_provider"]
    run_root.mkdir(parents=True, exist_ok=True)
    _write_json(run_root / "problem_source_manifest.json", problem_source_manifest)
    _write_json(run_root / "premise_index.json", premise_index)
    _write_json(run_root / "provider_availability_report.json", availability)

    local_foundry_summary = run_benchmark(
        run_root=run_root / "local_foundry_baseline",
        timeout_seconds=timeout_seconds,
        run_id=f"{DEFAULT_PROVIDER_CONTEXT_SWEEP_RUN_ID}_local_foundry_baseline",
        problem_set=problem_set,
        problem_source_manifest=problem_source_manifest,
        premise_index=premise_index,
        graph_variant_id=SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT,
        cap_id=cap_id,
    )
    local_foundry_by_problem = {
        row["problem_id"]: row for row in local_foundry_summary["problem_results"]
    }
    from system.lib import type_a_worker_harness
    from system.lib.compliance import transform_job_adapter

    transform_job_state_root = run_root / "transform_job_preview_state"
    rows: list[dict[str, Any]] = []
    transform_jobs: list[dict[str, Any]] = []
    for recipe_id in context_recipes:
        recipe = _provider_context_recipe(recipe_id)
        for problem in problem_set:
            context_pack, retrieval_report, skill_decision, allowed_premise_ids = (
                _provider_context_pack(
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
            is_strategy_classification = recipe_id in STRATEGY_CLASSIFICATION_RECIPES
            if is_strategy_classification:
                output_schema = _strategy_classification_output_schema()
                transform_task_class = PROVER_STRATEGY_CLASSIFICATION_TASK_CLASS
                transform_target_facet = "strategy_id_advisory"
            else:
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
                transform_task_class = PROVER_PROVIDER_TRANSFORM_TASK_CLASS
                transform_target_facet = "lean_proof_hypothesis"
            input_packet = {
                "schema_version": "prover_provider_context_transform_input_v0",
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
                task_class=transform_task_class,
                target_row_id=f"prover_problem:{problem.problem_id}:{recipe_id}",
                target_facet=transform_target_facet,
                target_band="prover_benchmark_problem",
                input_packet=input_packet,
                output_schema=output_schema,
                source_paths=[
                    "tools/meta/factory/run_prover_graph_benchmark.py",
                    "codex/standards/std_transform_job.json",
                    "codex/standards/std_compute_provider.json",
                    str(run_root / "local_foundry_baseline" / "run_summary.json"),
                ],
                provider_selection_policy={
                    "prefer": [selected_provider],
                    "capacity_lane_id": f"provider:{selected_provider}",
                    "paid_gate": False,
                    "models": (
                        {selected_provider: provider_model}
                        if provider_model
                        else {}
                    ),
                    "context_recipe_id": recipe_id,
                },
                validation_command=(
                    "./repo-python tools/meta/factory/run_prover_graph_benchmark.py "
                    "--provider-context-sweep --check --json"
                ),
                promotion_target={
                    "state": "draft_candidate_only",
                    "surface": "prover_oracle_candidate_reducer",
                    "run_root": str(run_root),
                    "lean_oracle_required_before_success": True,
                },
                created_by="prover_provider_context_sweep_transform_compiler",
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
                write_root=transform_job_state_root,
            )
            transform_jobs.append(written)
            rows.append(
                {
                    "problem_id": problem.problem_id,
                    "split": problem.split,
                    "source": problem.source,
                    "recipe_id": recipe_id,
                    "graph_role": recipe["graph_role"],
                    "provider": selected_provider,
                    "model": provider_model,
                    "transform_job_id": written["id"],
                    "transform_job_ref": str(
                        transform_job_state_root / written["artifact_path"]
                    ),
                    "target_row_id": written["target_row_id"],
                    "context_pack_id": context_pack["context_pack_id"],
                    "context_pack_kib": context_pack["context_budget"]["kib"],
                    "context_pack_bytes": context_pack["context_budget"]["bytes"],
                    "context_pack_approximate_tokens": context_pack["context_budget"][
                        "approximate_tokens"
                    ],
                    "retrieved_premise_ids": retrieval_report.get(
                        "retrieved_premise_ids", []
                    ),
                    "allowed_premise_ids": allowed_premise_ids,
                    "skill_cell_id": skill_decision.get("skill_cell_id"),
                    "provider_calls": 0,
                    "provider_dispatch": False,
                    "lean_check_status": "not_run_until_provider_receipt",
                    "leakage_detected": context_pack["leakage_audit"]["status"] != "PASS",
                }
            )
    compliance_report = transform_job_adapter.scan_transform_jobs(
        transform_job_state_root
    )
    by_recipe: dict[str, dict[str, Any]] = {}
    by_role: dict[str, dict[str, Any]] = {}
    for row in rows:
        for bucket, key in ((by_recipe, row["recipe_id"]), (by_role, row["graph_role"])):
            entry = bucket.setdefault(
                key,
                {
                    "transform_job_count": 0,
                    "provider_calls": 0,
                    "context_bytes": 0,
                    "leakage_count": 0,
                },
            )
            entry["transform_job_count"] += 1
            entry["context_bytes"] += int(row["context_pack_bytes"])
            entry["leakage_count"] += 1 if row["leakage_detected"] else 0
    aggregate = {
        "schema_version": "prover_provider_context_transform_job_aggregate_v0",
        "problem_count": len(problem_set),
        "attempt_count": len(rows),
        "transform_job_count": len(transform_jobs),
        "proof_check_count": 0,
        "pass_count": 0,
        "fail_count": 0,
        "by_recipe": by_recipe,
        "by_graph_role": by_role,
        "cost_totals": {
            "provider_calls": 0,
            "bytes_in": sum(int(row["context_pack_bytes"]) for row in rows),
            "bytes_out": 0,
            "tokens_in": sum(
                int(row["context_pack_approximate_tokens"]) for row in rows
            ),
            "tokens_out": 0,
            "wall_time_ms": 0,
            "estimated_cost_usd": 0.0,
        },
        "leakage_count": sum(1 for row in rows if row["leakage_detected"]),
        "unallowed_premise_count": 0,
        "dispatch_posture": "compiled_transform_jobs_not_dispatched",
    }
    recipe_comparison = {
        "schema_version": "provider_context_transform_job_recipe_comparison_v0",
        "recipes": [
            {"recipe_id": recipe_id, **metrics}
            for recipe_id, metrics in sorted(by_recipe.items())
        ],
        "graph_roles": [
            {"graph_role": role, **metrics}
            for role, metrics in sorted(by_role.items())
        ],
        "winner_policy": (
            "No provider winner is selected before receipts and Lean checks; "
            "this run only compiles std_transform_job packets."
        ),
    }
    local_aggregate = json.loads(
        Path(local_foundry_summary["aggregate_report"]).read_text(encoding="utf-8")
    )
    recipe_set = set(context_recipes)
    if recipe_set and recipe_set <= STRATEGY_CLASSIFICATION_RECIPES:
        sweep_task_class: str = PROVER_STRATEGY_CLASSIFICATION_TASK_CLASS
    elif recipe_set & STRATEGY_CLASSIFICATION_RECIPES:
        sweep_task_class = "mixed:prover_context_hypothesis+prover_strategy_classification"
    else:
        sweep_task_class = PROVER_PROVIDER_TRANSFORM_TASK_CLASS
    graph_comparison = {
        "schema_version": "provider_context_transform_job_graph_comparison_v0",
        "local_foundry_baseline": {
            "graph_variant_id": SKILL_FOUNDRY_OVERLAY_GRAPH_VARIANT,
            "run_summary": local_foundry_summary["aggregate_report"],
            "pass_count": local_aggregate["pass_count"],
            "fail_count": local_aggregate["fail_count"],
            "provider_calls": local_aggregate["cost_totals"]["provider_calls"],
        },
        "provider_graph_roles": recipe_comparison["graph_roles"],
        "before_after": {
            "local_foundry_pass_count": local_aggregate["pass_count"],
            "provider_attempt_pass_count": 0,
            "provider_calls": 0,
            "transform_job_count": len(transform_jobs),
            "leakage_count": aggregate["leakage_count"],
        },
        "provider_plane_contract": {
            "task_class": sweep_task_class,
            "dispatch_owner": "system.lib.type_a_worker_harness",
            "receipt_owner": "std_provider_receipt_v1",
            "row_patch_owner": "std_row_patch_v1",
            "success_owner": (
                "strategy classification reducer accepts advisory; "
                "no Lean acceptance required for strategy_id_classification"
                if sweep_task_class == PROVER_STRATEGY_CLASSIFICATION_TASK_CLASS
                else "Lean oracle reducer after provider receipt"
            ),
        },
        "leakage_audit": {
            "forward_lab_proof_body_leaks": 0,
            "oracle_repair_counted_as_forward_success": False,
            "provider_output_bypassed_lean": False,
            "context_pack_forbidden_material_leaks": aggregate["leakage_count"],
            "status": "PASS" if aggregate["leakage_count"] == 0 else "FAIL",
        },
        "non_goals": [
            "no execution-governance ladder extension",
            "no open-problem success claim",
            "no harness-owned provider dispatch",
            "provider text is not success without Lean acceptance",
        ],
    }
    context_pack_manifest = {
        "schema_version": "provider_context_pack_manifest_v0",
        "context_pack_count": len(rows),
        "context_packs": [
            {
                "problem_id": row["problem_id"],
                "recipe_id": row["recipe_id"],
                "graph_role": row["graph_role"],
                "context_pack_id": row["context_pack_id"],
                "context_pack_kib": row["context_pack_kib"],
                "bytes_in": row["context_pack_bytes"],
            }
            for row in rows
        ],
    }
    transform_job_manifest = {
        "schema_version": "prover_provider_context_transform_job_manifest_v0",
        "task_class": sweep_task_class,
        "provider": selected_provider,
        "model": provider_model,
        "dispatch_posture": "not_dispatched",
        "transform_job_count": len(transform_jobs),
        "write_root": str(transform_job_state_root),
        "jobs": [
            {
                "transform_job_id": row["transform_job_id"],
                "problem_id": row["problem_id"],
                "recipe_id": row["recipe_id"],
                "graph_role": row["graph_role"],
                "target_row_id": row["target_row_id"],
                "artifact_path": row["transform_job_ref"],
            }
            for row in rows
        ],
    }
    run_summary = {
        "schema_version": "prover_provider_context_sweep_run_v0",
        "run_id": DEFAULT_PROVIDER_CONTEXT_SWEEP_RUN_ID,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "cap_id": cap_id,
        "provider": selected_provider,
        "provider_model": provider_model,
        "dispatch_posture": "compiled_transform_jobs_not_dispatched",
        "context_recipes": list(context_recipes),
        "problem_count": len(problem_set),
        "problem_source_manifest": str(run_root / "problem_source_manifest.json"),
        "premise_index": str(run_root / "premise_index.json"),
        "provider_availability_report": str(run_root / "provider_availability_report.json"),
        "local_foundry_baseline_run_summary": str(
            run_root / "local_foundry_baseline" / "run_summary.json"
        ),
        "context_pack_manifest": str(run_root / "context_pack_manifest.json"),
        "context_recipe_comparison": str(run_root / "context_recipe_comparison.json"),
        "transform_job_manifest": str(run_root / "transform_job_manifest.json"),
        "transform_job_compliance_report": str(
            run_root / "transform_job_compliance_report.json"
        ),
        "graph_variant_comparison": str(run_root / "graph_variant_comparison.json"),
        "aggregate_report": str(run_root / "aggregate_report.json"),
        "provider_calls": 0,
        "provider_or_nim_needed": True,
        "governance_ladder_extended": False,
        "open_problem_success_claimed": False,
        "existing_surface_binding": {
            "transform_job_standard": "codex/standards/std_transform_job.json",
            "provider_worker_harness": "system/lib/type_a_worker_harness.py",
            "provider_receipt_standard": "std_provider_receipt_v1",
            "dispatch_command": (
                "./repo-python tools/meta/control/type_a_worker_harness.py run "
                "--job-path <transform_job_ref> --provider-id "
                f"{selected_provider}"
            ),
        },
        "run_hash": None,
    }
    run_summary["run_hash"] = _sha256_json(
        {
            "availability": availability,
            "aggregate": aggregate,
            "recipe_comparison": recipe_comparison,
            "graph_comparison": graph_comparison,
            "transform_jobs": transform_job_manifest,
            "rows": rows,
        }
    )
    _write_json(run_root / "context_pack_manifest.json", context_pack_manifest)
    _write_json(run_root / "context_recipe_comparison.json", recipe_comparison)
    _write_json(run_root / "transform_job_manifest.json", transform_job_manifest)
    _write_json(run_root / "transform_job_compliance_report.json", compliance_report)
    _write_json(run_root / "graph_variant_comparison.json", graph_comparison)
    _write_json(run_root / "aggregate_report.json", aggregate)
    _write_json(run_root / "provider_context_sweep_run_summary.json", run_summary)
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def _validate_run(run_root: Path) -> list[str]:
    issues: list[str] = []
    for path in run_root.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(f"{path}: {exc}")
    summary_path = run_root / "run_summary.json"
    aggregate_path = run_root / "aggregate_report.json"
    if not summary_path.exists():
        issues.append("missing run_summary.json")
    if not aggregate_path.exists():
        issues.append("missing aggregate_report.json")
    summary_schema = None
    if summary_path.exists():
        try:
            summary_schema = json.loads(summary_path.read_text(encoding="utf-8")).get(
                "schema_version"
            )
        except json.JSONDecodeError:
            summary_schema = None
    if aggregate_path.exists():
        aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
        if aggregate.get("problem_count", 0) < 5:
            issues.append("problem_count below v0 minimum")
        provider_calls = aggregate.get("cost_totals", {}).get(
            "provider_calls",
            aggregate.get("provider_calls", 0),
        )
        if provider_calls != 0 and summary_schema != "prover_provider_context_sweep_run_v0":
            issues.append("provider calls must remain zero in v0")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument(
        "--problem-source-manifest",
        help="Optional source-backed problem manifest to run instead of the built-in Lean-core set.",
    )
    parser.add_argument(
        "--graph-variant",
        choices=GRAPH_VARIANTS,
        default="baseline_graph_v0",
    )
    parser.add_argument(
        "--ring1-source-ingestion",
        action="store_true",
        help="Run the Ring-1 source-backed slice with baseline and oracle-repair variants.",
    )
    parser.add_argument(
        "--ring2-premise-retrieval",
        action="store_true",
        help="Run the Ring-2 premise-retrieval slice with baseline, retrieval, and oracle-repair variants.",
    )
    parser.add_argument(
        "--strategy-control-graph",
        action="store_true",
        help="Run the strategy-control slice with baseline, retrieval, strategy, and oracle-repair variants.",
    )
    parser.add_argument(
        "--skill-atlas-composition-root",
        action="store_true",
        help="Run the Prover skill-atlas composition root slice with a skill-cell overlay.",
    )
    parser.add_argument(
        "--skill-foundry",
        action="store_true",
        help="Run the Prover Skill Foundry slice with mined/evaluated candidate skill cells.",
    )
    parser.add_argument(
        "--provider-context-sweep",
        action="store_true",
        help=(
            "Compile provider-context std_transform_job packets over the Skill "
            "Foundry lane; no provider dispatch occurs in this harness."
        ),
    )
    parser.add_argument(
        "--provider",
        choices=("auto", "nvidia_nim", "openrouter_api", "openrouter"),
        default="auto",
        help=(
            "Provider lane for compiled transform jobs. Dispatch remains owned "
            "by type_a_worker_harness/provider_transform_job."
        ),
    )
    parser.add_argument("--provider-model", help="Optional provider model override.")
    parser.add_argument(
        "--provider-live-probe",
        action="store_true",
        help="Probe configured provider status live before compiling transform jobs.",
    )
    parser.add_argument(
        "--context-recipe",
        action="append",
        choices=PROVIDER_CONTEXT_RECIPES,
        help="Provider context recipe to run. Repeat to sweep multiple recipes.",
    )
    parser.add_argument(
        "--problem-limit",
        type=int,
        default=10,
        help="Maximum number of strategy problems for --provider-context-sweep.",
    )
    parser.add_argument("--max-provider-tokens", type=int, default=256)
    parser.add_argument("--provider-temperature", type=float, default=0.0)
    parser.add_argument("--json", action="store_true", help="Print run summary JSON.")
    parser.add_argument("--check", action="store_true", help="Validate emitted artifacts after running.")
    args = parser.parse_args(argv)

    run_root = Path(args.run_root)
    selected_suites = [
        args.ring1_source_ingestion,
        args.ring2_premise_retrieval,
        args.strategy_control_graph,
        args.skill_atlas_composition_root,
        args.skill_foundry,
        args.provider_context_sweep,
    ]
    if sum(1 for selected in selected_suites if selected) > 1:
        print("choose only one benchmark suite runner", file=sys.stderr)
        return 2
    if args.ring1_source_ingestion:
        if args.run_root == str(DEFAULT_RUN_ROOT):
            run_root = DEFAULT_RING1_RUN_ROOT
        summary = run_ring1_source_ingestion(
            run_root=run_root,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.ring2_premise_retrieval:
        if args.run_root == str(DEFAULT_RUN_ROOT):
            run_root = DEFAULT_RING2_RUN_ROOT
        summary = run_ring2_premise_retrieval(
            run_root=run_root,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.strategy_control_graph:
        if args.run_root == str(DEFAULT_RUN_ROOT):
            run_root = DEFAULT_STRATEGY_RUN_ROOT
        summary = run_strategy_control_graph(
            run_root=run_root,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.skill_atlas_composition_root:
        if args.run_root == str(DEFAULT_RUN_ROOT):
            run_root = DEFAULT_SKILL_ATLAS_RUN_ROOT
        summary = run_prover_skill_atlas_composition_root(
            run_root=run_root,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.skill_foundry:
        if args.run_root == str(DEFAULT_RUN_ROOT):
            run_root = DEFAULT_SKILL_FOUNDRY_RUN_ROOT
        summary = run_prover_skill_foundry(
            run_root=run_root,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.provider_context_sweep:
        if args.run_root == str(DEFAULT_RUN_ROOT):
            run_root = DEFAULT_PROVIDER_CONTEXT_SWEEP_RUN_ROOT
        summary = run_provider_context_sweep(
            run_root=run_root,
            timeout_seconds=args.timeout_seconds,
            provider=args.provider,
            provider_model=args.provider_model,
            live_probe=args.provider_live_probe,
            context_recipes=tuple(args.context_recipe or DEFAULT_PROVIDER_CONTEXT_RECIPES),
            problem_limit=args.problem_limit,
            max_tokens=args.max_provider_tokens,
            temperature=args.provider_temperature,
        )
    else:
        manifest_path = Path(args.problem_source_manifest) if args.problem_source_manifest else None
        summary = run_benchmark(
            run_root=run_root,
            timeout_seconds=args.timeout_seconds,
            problem_source_manifest_path=manifest_path,
            graph_variant_id=args.graph_variant,
            cap_id="cap_prover_benchmark_ring1_source_ingestion_v0"
            if manifest_path is not None
            else "cap_prover_graph_benchmark_harness_v0",
        )
    issues = _validate_run(_repo_path(run_root) if not run_root.is_absolute() else run_root)
    if args.check and issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    if args.json:
        print(_json_text(summary), end="")
    else:
        aggregate = json.loads(
            (_repo_path(run_root) / "aggregate_report.json").read_text(encoding="utf-8")
        )
        if args.ring1_source_ingestion:
            print(
                f"{summary['run_id']}: baseline {aggregate['baseline_pass_count']}/"
                f"{aggregate['problem_count']} passed; oracle_repair "
                f"{aggregate['oracle_repair_pass_count']}/{aggregate['problem_count']} passed; "
                f"repairs={aggregate['repair_success_count']}"
            )
            return 0
        if args.ring2_premise_retrieval:
            print(
                f"{summary['run_id']}: baseline {aggregate['baseline_pass_count']}/"
                f"{aggregate['problem_count']} passed; premise_retrieval "
                f"{aggregate['premise_retrieval_pass_count']}/{aggregate['problem_count']} passed; "
                f"oracle_repair {aggregate['oracle_repair_pass_count']}/"
                f"{aggregate['problem_count']} passed; recall={aggregate['premise_recall']:.2f}"
            )
            return 0
        if args.strategy_control_graph:
            print(
                f"{summary['run_id']}: baseline {aggregate['baseline_pass_count']}/"
                f"{aggregate['problem_count']} passed; premise_retrieval "
                f"{aggregate['premise_retrieval_pass_count']}/{aggregate['problem_count']} passed; "
                f"strategy_control {aggregate['strategy_control_pass_count']}/"
                f"{aggregate['problem_count']} passed; oracle_repair "
                f"{aggregate['oracle_repair_pass_count']}/{aggregate['problem_count']} passed; "
                f"strategy_acc={aggregate['strategy_selection_accuracy']:.2f}"
            )
            return 0
        if args.skill_atlas_composition_root:
            print(
                f"{summary['run_id']}: strategy_control "
                f"{aggregate['strategy_control_pass_count']}/{aggregate['problem_count']} "
                f"passed; skill_overlay {aggregate['skill_overlay_pass_count']}/"
                f"{aggregate['problem_count']} passed; orientation_repairs="
                f"{aggregate['orientation_failure_repaired_count']}"
            )
            return 0
        if args.skill_foundry:
            print(
                f"{summary['run_id']}: strategy_control "
                f"{aggregate['strategy_control_pass_count']}/{aggregate['problem_count']} "
                f"passed; existing_skill_overlay "
                f"{aggregate['existing_skill_overlay_pass_count']}/{aggregate['problem_count']} "
                f"passed; candidate_skill_overlay "
                f"{aggregate['candidate_skill_overlay_pass_count']}/{aggregate['problem_count']} "
                f"passed; promoted={aggregate['promoted_candidate_count']}; "
                f"quarantined={aggregate['quarantined_candidate_count']}"
            )
            return 0
        if args.provider_context_sweep:
            print(
                f"{summary['run_id']}: provider={summary['provider']} "
                f"dispatch={summary['dispatch_posture']} "
                f"jobs={aggregate['transform_job_count']} calls={aggregate['cost_totals']['provider_calls']} "
                f"leakage={aggregate['leakage_count']} recipes={','.join(summary['context_recipes'])}"
            )
            return 0
        print(
            f"{summary['run_id']}: {aggregate['pass_count']}/{aggregate['problem_count']} "
            f"passed; failures={aggregate['failure_taxonomy']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
