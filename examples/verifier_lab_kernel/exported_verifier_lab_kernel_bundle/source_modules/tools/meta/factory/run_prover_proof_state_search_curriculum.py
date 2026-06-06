#!/usr/bin/env python3
"""Run a small Lean/Std proof-state search curriculum.

This runner extends the statement-only hammer lane into explicit proof-state
transition evidence. It keeps the status classes separate: one-shot tactic
checks, proof-state transitions, provider hypotheses, and oracle comparators
are different lanes, even when they all produce Lean-accepted scripts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.meta.factory import run_prover_external_formal_benchmark_smoke as external_smoke
from tools.meta.factory import run_prover_graph_benchmark as harness
from tools.meta.factory import run_prover_statement_only_hammer_bandit as bandit


RUN_ID = "PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0"
DEFAULT_RUN_ROOT = Path("state/runs") / RUN_ID
CAP_ID = "cap_prover_proof_state_search_curriculum_v0"
GRAPH_VARIANT_ID = "proof_state_search_curriculum_graph_v0"

STATUS_FORMAL_STATEMENT = "FORMAL_STATEMENT"
STATUS_GOAL_STATE = "GOAL_STATE"
STATUS_TACTIC_ACTION = "TACTIC_ACTION"
STATUS_TACTIC_TRANSITION = "TACTIC_TRANSITION"
STATUS_PREMISE_SELECTION = "PREMISE_SELECTION"
STATUS_PROVIDER_HYPOTHESIS = "PROVIDER_HYPOTHESIS"
STATUS_LEAN_ACCEPTED_PROOF = "LEAN_ACCEPTED_PROOF"
STATUS_ORACLE_REPAIR = "ORACLE_REPAIR"
STATUS_FOUNDRY_POLICY_LEARNING = "FOUNDRY_POLICY_LEARNING"
STATUS_SEARCH_EXHAUSTED = "SEARCH_EXHAUSTED"

REQUIRED_ARTIFACTS = (
    "corpus_readiness.json",
    "curriculum_problem_manifest.json",
    "one_shot_hammer_baseline.json",
    "proof_state_transition_manifest.json",
    "proof_state_search_trace.json",
    "proof_state_action_value_table.json",
    "premise_selection_trace.json",
    "subgoal_decomposition_trace.json",
    "proof_minimization_report.json",
    "curriculum_comparison_report.json",
    "foundry_proof_state_learning_rows.json",
    "skill_policy_update_candidates.json",
    "provider_hypothesis_queue.json",
    "oracle_comparator_results.json",
    "proof_state_curriculum_run_summary.json",
)

FAILURE_CLASSES_CONSIDERED = (
    "timeout",
    "tactic_mismatch",
    "premise_miss",
    "import_build_missing",
    "unsolved_goals",
    "syntax_or_elaboration_error",
    "oracle_gap_remaining",
)


@dataclass(frozen=True)
class SearchAction:
    action_id: str
    action_kind: str
    tactic_id: str
    body: tuple[str, ...]
    selected_facts: tuple[str, ...] = ()
    selection_reason: str = "generated_by_curriculum_policy"
    expected_goal_effect: str = "unknown"


@dataclass(frozen=True)
class SearchScript:
    script_id: str
    policy_id: str
    actions: tuple[SearchAction, ...]
    selection_reason: str


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


def _write_text(path: Path, payload: str) -> None:
    harness._write_text(path, payload)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _run_process(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    process_cwd = cwd or REPO_ROOT
    try:
        result = subprocess.run(
            list(command),
            cwd=str(process_cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "command": list(command),
            "cwd": _rel(process_cwd),
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": list(command),
            "cwd": _rel(process_cwd),
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout": True,
        }


def _safe_id(value: str) -> str:
    return harness._safe_tactic_id(value)


def _body_tactic_id(body: Sequence[str]) -> str:
    return external_smoke._body_tactic_id(tuple(body))


def _proposition_fragment(theorem_signature: str) -> str:
    before_body = theorem_signature.split(":= by", 1)[0].strip()
    depth = 0
    for index, char in enumerate(before_body):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == ":" and depth == 0:
            return before_body[index + 1 :].strip()
    return before_body


def _target_shape(problem: harness.ProverProblem) -> str:
    proposition = _proposition_fragment(problem.theorem_signature)
    if "%" in proposition and "(" not in proposition.split(":=")[0]:
        return "closed_nat_mod_decision"
    if "Int" in problem.theorem_signature and ("=" in proposition or "∧" in proposition):
        return "int_linear_arithmetic"
    if "Nat" in problem.theorem_signature and ("=" in proposition or "%" in proposition):
        if "%" in proposition and all(token not in proposition for token in ("(n", "(m", "(x")):
            return "closed_nat_mod_decision"
        if any(token in problem.theorem_signature for token in ("(n : Nat)", "(m : Nat)", "(x : Nat)")):
            return "nat_arithmetic_with_variables"
        return "nat_arithmetic"
    if "Rat" in problem.theorem_signature:
        return "rat_normalization"
    if proposition == "True":
        return "true_intro"
    if proposition.startswith("False ->") or proposition.startswith("False →"):
        return "false_elim"
    if "↔" in proposition:
        return "iff"
    if "∧" in proposition:
        return "conjunction"
    if "∨" in proposition:
        return "disjunction"
    if "∃" in proposition:
        return "existential"
    if "->" in proposition or "→" in proposition:
        return "implication"
    if problem.domain == "premise_selection":
        return "atomic_goal_with_premise_context"
    if "=" in proposition:
        return "equality"
    return "unknown"


def _lean_check(
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
    _write_text(output_path, text)
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
        "stderr_excerpt": run["stderr"][:1000],
        "stdout_excerpt": run["stdout"][:1000],
        "timeout": bool(run["timeout"]),
        "exit_code": run["exit_code"],
        "sorry_present": sorry_present,
        "axiom_audit": axiom_audit,
        "lean_check_ref": _rel(output_path),
    }


def _trace_source(problem: harness.ProverProblem, prefix_body: Sequence[str], *, label: str) -> str:
    trace_body = [
        *prefix_body,
        "  trace_state",
        "  all_goals sorry",
    ]
    return harness._lean_source(
        problem,
        graph_variant_id=GRAPH_VARIANT_ID,
        body=tuple(trace_body),
        attempt_label=label,
    )


def _clean_goal_excerpt(stdout: str, stderr: str) -> str:
    merged = "\n".join(part for part in (stdout.strip(), stderr.strip()) if part)
    cleaned: list[str] = []
    for line in merged.splitlines():
        if "warning: declaration uses `sorry`" in line:
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()[:1600]


def _trace_prefix_state(
    *,
    problem: harness.ProverProblem,
    prefix_body: Sequence[str],
    output_path: Path,
    timeout_seconds: int,
    trace_label: str,
) -> dict[str, Any]:
    _write_text(output_path, _trace_source(problem, prefix_body, label=trace_label))
    run = harness._run_lean(output_path, timeout_seconds=timeout_seconds)
    _, lean_status, error_class = harness._classify_lean_attempt(
        run,
        expected_error_class="PROOF_STATE_TRACE_FAIL",
    )
    return {
        "trace_status": "CAPTURED" if lean_status == "PASS" else "FAILED",
        "lean_status": lean_status,
        "error_class": error_class if lean_status != "PASS" else "NONE",
        "duration_ms": run["duration_ms"],
        "goal_excerpt": _clean_goal_excerpt(run["stdout"], run["stderr"]),
        "stderr_excerpt": run["stderr"][:1000],
        "stdout_excerpt": run["stdout"][:1000],
        "lean_trace_ref": _rel(output_path),
    }


def _with_prefix(body: Sequence[str]) -> tuple[str, ...]:
    return tuple(line if line.startswith("  ") else f"  {line}" for line in body)


def _action(
    action_id: str,
    body: Sequence[str],
    *,
    action_kind: str = "tactic",
    tactic_id: str | None = None,
    selected_facts: Sequence[str] = (),
    selection_reason: str = "generated_by_curriculum_policy",
    expected_goal_effect: str = "unknown",
) -> SearchAction:
    return SearchAction(
        action_id=action_id,
        action_kind=action_kind,
        tactic_id=tactic_id or action_id,
        body=_with_prefix(body),
        selected_facts=tuple(selected_facts),
        selection_reason=selection_reason,
        expected_goal_effect=expected_goal_effect,
    )


def _script(
    script_id: str,
    actions: Sequence[SearchAction],
    *,
    policy_id: str,
    selection_reason: str,
) -> SearchScript:
    return SearchScript(
        script_id=script_id,
        policy_id=policy_id,
        actions=tuple(actions),
        selection_reason=selection_reason,
    )


def _local_curriculum_problem_set() -> list[harness.ProverProblem]:
    visible = (
        "formal theorem signature",
        "required imports",
        "source family",
        "search policy metadata",
    )
    withheld = (
        "ideal proof body",
        "oracle repair body",
        "oracle critique",
    )

    def problem(
        *,
        problem_id: str,
        domain: str,
        informal: str,
        theorem_signature: str,
        ideal_body: Sequence[str],
        expected_error: str = "TACTIC_SEARCH_FAIL",
    ) -> harness.ProverProblem:
        return harness.ProverProblem(
            problem_id=problem_id,
            source="local_lean_std_proof_state_curriculum_v0",
            split="curriculum",
            mode="solved_training_proof_withheld",
            domain=domain,
            informal_statement=informal,
            theorem_name=problem_id,
            theorem_signature=theorem_signature,
            candidate_body=(),
            ideal_body=tuple(_with_prefix(ideal_body)),
            visible_to_lab=visible,
            withheld_until_oracle=withheld,
            context_recipe_id="proof_state_curriculum_v0",
            expected_error_class_on_fail=expected_error,
            required_imports=("Std",),
            source_ref="tools/meta/factory/run_prover_proof_state_search_curriculum.py::_local_curriculum_problem_set",
            source_family="local_lean_std_proof_state_curriculum",
            difficulty_tag="proof_state_multi_step",
            repair_body=tuple(_with_prefix(ideal_body)),
        )

    return [
        problem(
            problem_id="ps_intro_assumption",
            domain="propositional",
            informal="Introduce a hypothesis and use it directly.",
            theorem_signature="theorem ps_intro_assumption (p : Prop) : p -> p := by",
            ideal_body=("intro hp", "exact hp"),
        ),
        problem(
            problem_id="ps_and_intro",
            domain="propositional",
            informal="Introduce two hypotheses and split a conjunction goal.",
            theorem_signature="theorem ps_and_intro (p q : Prop) : p -> q -> p ∧ q := by",
            ideal_body=("intro hp", "intro hq", "constructor", "exact hp", "exact hq"),
        ),
        problem(
            problem_id="ps_and_comm",
            domain="propositional",
            informal="Use a conjunction premise in the opposite order.",
            theorem_signature="theorem ps_and_comm (p q : Prop) : p ∧ q -> q ∧ p := by",
            ideal_body=("intro h", "constructor", "exact h.right", "exact h.left"),
        ),
        problem(
            problem_id="ps_or_comm",
            domain="propositional",
            informal="Case split an Or premise and swap sides.",
            theorem_signature="theorem ps_or_comm (p q : Prop) : p ∨ q -> q ∨ p := by",
            ideal_body=(
                "intro h",
                "cases h with",
                "| inl hp => exact Or.inr hp",
                "| inr hq => exact Or.inl hq",
            ),
        ),
        problem(
            problem_id="ps_exists_passthrough",
            domain="existential",
            informal="Eliminate and rebuild the same existential witness.",
            theorem_signature=(
                "theorem ps_exists_passthrough (P : Nat -> Prop) : "
                "(∃ n : Nat, P n) -> ∃ m : Nat, P m := by"
            ),
            ideal_body=(
                "intro h",
                "cases h with",
                "| intro n hn => exact Exists.intro n hn",
            ),
        ),
        problem(
            problem_id="ps_iff_intro",
            domain="propositional",
            informal="Assemble an iff from two implications.",
            theorem_signature=(
                "theorem ps_iff_intro (p q : Prop) : "
                "(p -> q) -> (q -> p) -> (p ↔ q) := by"
            ),
            ideal_body=("intro hpq", "intro hqp", "constructor", "exact hpq", "exact hqp"),
        ),
        problem(
            problem_id="ps_rw_then_omega",
            domain="int_arithmetic",
            informal="Rewrite a local equality, then finish linear arithmetic.",
            theorem_signature=(
                "theorem ps_rw_then_omega (x : Int) (h : x = 3) : "
                "2 * x + 1 = 7 := by"
            ),
            ideal_body=("rw [h]", "omega"),
        ),
        problem(
            problem_id="ps_premise_exact",
            domain="premise_selection",
            informal="Select an implication premise and apply it to a selected fact.",
            theorem_signature=(
                "theorem ps_premise_exact (p q : Prop) (h : p -> q) (hp : p) : q := by"
            ),
            ideal_body=("exact h hp",),
        ),
        problem(
            problem_id="ps_nat_succ_inj",
            domain="nat",
            informal="Introduce a successor equality and apply the Lean core injectivity premise.",
            theorem_signature=(
                "theorem ps_nat_succ_inj (m n : Nat) : "
                "Nat.succ m = Nat.succ n -> m = n := by"
            ),
            ideal_body=("intro h", "exact Nat.succ.inj h"),
        ),
        problem(
            problem_id="ps_false_elim",
            domain="propositional",
            informal="Introduce contradiction and eliminate False.",
            theorem_signature="theorem ps_false_elim (p : Prop) : False -> p := by",
            ideal_body=("intro h", "exact False.elim h"),
        ),
    ]


def _external_curriculum_problem_set(limit: int) -> list[harness.ProverProblem]:
    return [replace(problem, candidate_body=()) for problem in external_smoke._miniF2F_problem_set()[:limit]]


def _public_problem_row(problem: harness.ProverProblem, *, corpus_tier: str) -> dict[str, Any]:
    return {
        "problem_id": problem.problem_id,
        "corpus_tier": corpus_tier,
        "source": problem.source,
        "source_family": problem.source_family,
        "source_ref": problem.source_ref,
        "split": problem.split,
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
            "selected_premise_names",
        ],
        "forbidden_forward_material": [
            "candidate_body",
            "ideal_body",
            "repair_body",
            "oracle critique",
            "provider text without reducer evidence",
        ],
    }


def build_curriculum_problem_manifest(
    *,
    external_problem_set: Sequence[harness.ProverProblem],
    local_problem_set: Sequence[harness.ProverProblem],
) -> dict[str, Any]:
    rows = [
        *(_public_problem_row(problem, corpus_tier="tier0_translation_smoke_regression") for problem in external_problem_set),
        *(_public_problem_row(problem, corpus_tier="tier_local_proof_state_perturbation") for problem in local_problem_set),
    ]
    return {
        "schema_version": "curriculum_problem_manifest_v0",
        "run_id": RUN_ID,
        "created_at": _utc_now(),
        "problem_count": len(rows),
        "external_regression_problem_count": len(external_problem_set),
        "local_proof_state_problem_count": len(local_problem_set),
        "headline_metric": "new_proof_state_search_success_over_one_shot",
        "status_boundary": {
            "statement_only_forward_fields": "formal statement, imports, public source metadata, and generated search policy only",
            "adapter_candidate_forward": False,
            "oracle_repair_forward": False,
            "provider_hypothesis_forward": "only after reducer plus Lean plus policy evidence; no provider calls in this deterministic run",
        },
        "problems": rows,
    }


def _lean_cli_probe() -> dict[str, Any]:
    lean = _run_process(["lean", "--version"], timeout_seconds=10)
    lake = _run_process(["lake", "--version"], timeout_seconds=10)
    return {
        "lean_available": shutil.which("lean") is not None,
        "lean_version_stdout": lean["stdout"].strip(),
        "lean_version_stderr": lean["stderr"].strip(),
        "lean_version_exit_code": lean["exit_code"],
        "lake_available": shutil.which("lake") is not None,
        "lake_version_stdout": lake["stdout"].strip(),
        "lake_version_stderr": lake["stderr"].strip(),
        "lake_version_exit_code": lake["exit_code"],
    }


def _probe_lean_file(path: Path, source: str, *, timeout_seconds: int = 20) -> dict[str, Any]:
    _write_text(path, source)
    run = harness._run_lean(path, timeout_seconds=timeout_seconds)
    _, lean_status, error_class = harness._classify_lean_attempt(
        run,
        expected_error_class="ENVIRONMENT_FAIL",
    )
    return {
        "probe_path": _rel(path),
        "lean_status": lean_status,
        "error_class": error_class if lean_status != "PASS" else "NONE",
        "available": lean_status == "PASS",
        "duration_ms": run["duration_ms"],
        "stdout_excerpt": run["stdout"][:1000],
        "stderr_excerpt": run["stderr"][:1000],
    }


def _probe_mathlib_lake_project(
    *,
    project_root: Path,
    probe_path: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    project_root = _repo_path(project_root)
    _write_text(
        probe_path,
        "\n".join(
            [
                "import Mathlib",
                "",
                "example (x y : Rat) : (x + y)^2 = x^2 + 2*x*y + y^2 := by",
                "  ring",
                "",
                "example : (2 : Nat) + 2 = 4 := by",
                "  norm_num",
                "",
            ]
        ),
    )
    run = _run_process(
        ["lake", "env", "lean", str(probe_path.resolve())],
        cwd=project_root,
        timeout_seconds=max(timeout_seconds, 30),
    )
    stderr = run["stderr"] or ""
    stdout = run["stdout"] or ""
    available = run["exit_code"] == 0 and not run["timeout"]
    return {
        "probe_path": _rel(probe_path),
        "project_root": _rel(project_root),
        "command": run["command"],
        "cwd": run["cwd"],
        "lean_status": "PASS" if available else "FAIL",
        "error_class": "NONE" if available else "ENVIRONMENT_FAIL",
        "available": available,
        "exit_code": run["exit_code"],
        "timeout": run["timeout"],
        "stdout_excerpt": stdout[:1000],
        "stderr_excerpt": stderr[:1000],
    }


def probe_tactic_affordances(
    *,
    run_root: Path,
    timeout_seconds: int,
    mathlib_project_root: Path | None = None,
) -> dict[str, Any]:
    probe_root = run_root / "tactic_affordance_probe"
    core = harness._probe_tactic_portfolio_availability(
        probe_root / "portfolio_core_v0",
        timeout_seconds=max(timeout_seconds, 15),
    )
    trace = _probe_lean_file(
        probe_root / "trace_state_probe.lean",
        "\n".join(
            [
                "import Std",
                "",
                "example (p q : Prop) : p -> q -> p ∧ q := by",
                "  intro hp",
                "  trace_state",
                "  all_goals sorry",
                "",
            ]
        ),
        timeout_seconds=max(timeout_seconds, 15),
    )
    mathlib = _probe_lean_file(
        probe_root / "mathlib_probe.lean",
        "\n".join(
            [
                "import Mathlib",
                "",
                "example : (2 : Nat) + 2 = 4 := by",
                "  norm_num",
                "",
            ]
        ),
        timeout_seconds=max(timeout_seconds, 15),
    )
    mathlib_lake_project = None
    if mathlib_project_root is not None:
        mathlib_lake_project = _probe_mathlib_lake_project(
            project_root=mathlib_project_root,
            probe_path=probe_root / "mathlib_lake_project_probe.lean",
            timeout_seconds=timeout_seconds,
        )
    mathlib_available = bool(mathlib.get("available")) or bool(
        (mathlib_lake_project or {}).get("available")
    )
    return {
        "schema_version": "tactic_affordance_probe_v0",
        "run_id": RUN_ID,
        "created_at": _utc_now(),
        **_lean_cli_probe(),
        "portfolio_core_v0": core,
        "trace_state": trace,
        "mathlib": {
            **mathlib,
            "direct_mathlib_lane_available": bool(mathlib.get("available")),
            "lake_project_mathlib_lane_available": bool(
                (mathlib_lake_project or {}).get("available")
            ),
            "mathlib_available": mathlib_available,
        },
        "mathlib_lake_project": mathlib_lake_project,
    }


def build_corpus_readiness(*, run_root: Path, tactic_probe: Mapping[str, Any]) -> dict[str, Any]:
    candidates = {
        "miniF2F_lean3_annex": Path("annexes/miniF2F/repo"),
        "miniF2F_lean4_mathlib_package": Path("annexes/miniF2F-lean4/repo"),
        "PutnamBench_lean4": Path("annexes/PutnamBench/repo"),
        "ProofNet": Path("annexes/ProofNet/repo"),
        "LeanDojo": Path("annexes/LeanDojo/repo"),
        "Pantograph": Path("annexes/Pantograph/repo"),
        "mathlib": Path("annexes/mathlib/repo"),
    }
    rows: list[dict[str, Any]] = []
    for corpus_id, rel_path in candidates.items():
        path = _repo_path(rel_path)
        has_lake = (path / "lakefile.lean").exists() or (path / "lakefile.toml").exists()
        rows.append(
            {
                "corpus_id": corpus_id,
                "local_path": _rel(path),
                "exists": path.exists(),
                "has_lake_file": has_lake,
                "selected_for_this_run": corpus_id == "miniF2F_lean3_annex",
                "readiness_status": (
                    "translation_smoke_only_lean3_mathlib_source"
                    if corpus_id == "miniF2F_lean3_annex" and path.exists()
                    else "ready_candidate_needs_build_probe"
                    if path.exists() and has_lake
                    else "absent"
                ),
            }
        )
    return {
        "schema_version": "corpus_readiness_v0",
        "run_id": RUN_ID,
        "created_at": _utc_now(),
        "lean_cli": {
            "lean_available": tactic_probe.get("lean_available"),
            "lean_version_stdout": tactic_probe.get("lean_version_stdout"),
            "lake_available": tactic_probe.get("lake_available"),
            "lake_version_stdout": tactic_probe.get("lake_version_stdout"),
        },
        "mathlib_available": bool((tactic_probe.get("mathlib") or {}).get("mathlib_available")),
        "mathlib_direct_import_available": bool(
            (tactic_probe.get("mathlib") or {}).get("direct_mathlib_lane_available")
        ),
        "mathlib_lake_project_import_available": bool(
            (tactic_probe.get("mathlib") or {}).get("lake_project_mathlib_lane_available")
        ),
        "trace_state_available": bool((tactic_probe.get("trace_state") or {}).get("available")),
        "rows": rows,
        "claim_boundary": (
            "This run uses MiniF2F-source-backed Lean4/Std translation smoke for regression "
            "and local Lean/Std proof-state curriculum rows. Direct MiniF2F Lean4/mathlib, "
            "PutnamBench, and ProofNet performance is not claimed."
        ),
        "artifact_ref": _rel(run_root / "corpus_readiness.json"),
    }


def _one_shot_actions(problem: harness.ProverProblem, availability: Mapping[str, Any]) -> list[SearchAction]:
    target_shape = _target_shape(problem)
    available = set(
        ((availability.get("portfolio_core_v0") or {}).get("available_tactic_ids") or ())
    )
    body_by_id = {
        "rfl": ("rfl",),
        "decide": ("decide",),
        "native_decide": ("native_decide",),
        "omega": ("omega",),
        "simp": ("simp",),
        "simp_all": ("simp_all",),
        "grind": ("grind",),
    }
    preferred_by_shape: dict[str, tuple[str, ...]] = {
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
    }
    tactic_ids = preferred_by_shape.get(target_shape, ("rfl", "simp", "simp_all", "grind"))
    rows: list[SearchAction] = []
    for tactic_id in tactic_ids:
        if tactic_id in available and tactic_id in body_by_id:
            rows.append(
                _action(
                    f"one_shot_{tactic_id}",
                    body_by_id[tactic_id],
                    tactic_id=tactic_id,
                    selection_reason=f"one-shot baseline tactic for target shape {target_shape}",
                    expected_goal_effect="attempt_terminal_one_shot",
                )
            )
    return rows


def _script_from_single_action(problem: harness.ProverProblem, tactic_id: str) -> SearchScript:
    return _script(
        f"proof_state_one_action_{tactic_id}",
        [_action(tactic_id, (tactic_id,), tactic_id=tactic_id, selection_reason="external regression one-action proof-state script", expected_goal_effect="terminal_or_unsolved")],
        policy_id="translation_smoke_one_action_policy_v0",
        selection_reason=f"target shape {_target_shape(problem)} admits one checked automation action",
    )


def _external_scripts(problem: harness.ProverProblem) -> list[SearchScript]:
    target_shape = _target_shape(problem)
    if target_shape == "closed_nat_mod_decision":
        return [_script_from_single_action(problem, "decide")]
    if target_shape == "rat_normalization":
        return [_script_from_single_action(problem, "native_decide"), _script_from_single_action(problem, "rfl")]
    if target_shape in {"int_linear_arithmetic", "nat_arithmetic_with_variables", "nat_arithmetic"}:
        return [_script_from_single_action(problem, "omega")]
    return [_script_from_single_action(problem, "simp"), _script_from_single_action(problem, "grind")]


def _local_scripts(problem: harness.ProverProblem) -> list[SearchScript]:
    pid = problem.problem_id
    if pid == "ps_intro_assumption":
        return [
            _script(
                "intro_then_assumption",
                [
                    _action("intro_hp", ("intro hp",), action_kind="intro", tactic_id="intro", selected_facts=("hp",), expected_goal_effect="introduce_hypothesis"),
                    _action("exact_hp", ("exact hp",), action_kind="premise_exact", tactic_id="exact", selected_facts=("hp",), expected_goal_effect="close_goal"),
                ],
                policy_id="intro_assumption_policy_v0",
                selection_reason="implication target; introduce antecedent and reuse the premise",
            )
        ]
    if pid == "ps_and_intro":
        return [
            _script(
                "intro_intro_constructor",
                [
                    _action("intro_hp", ("intro hp",), action_kind="intro", tactic_id="intro", selected_facts=("hp",), expected_goal_effect="introduce_left_premise"),
                    _action("intro_hq", ("intro hq",), action_kind="intro", tactic_id="intro", selected_facts=("hq",), expected_goal_effect="introduce_right_premise"),
                    _action("constructor", ("constructor",), action_kind="constructor", tactic_id="constructor", expected_goal_effect="split_conjunction_goal"),
                    _action("exact_hp", ("exact hp",), action_kind="premise_exact", tactic_id="exact", selected_facts=("hp",), expected_goal_effect="close_left_subgoal"),
                    _action("exact_hq", ("exact hq",), action_kind="premise_exact", tactic_id="exact", selected_facts=("hq",), expected_goal_effect="close_right_subgoal"),
                ],
                policy_id="conjunction_constructor_policy_v0",
                selection_reason="conjunction goal after two arrows; split and exact selected premises",
            )
        ]
    if pid == "ps_and_comm":
        return [
            _script(
                "intro_constructor_swap",
                [
                    _action("intro_h", ("intro h",), action_kind="intro", tactic_id="intro", selected_facts=("h",), expected_goal_effect="introduce_conjunction_premise"),
                    _action("constructor", ("constructor",), action_kind="constructor", tactic_id="constructor", expected_goal_effect="split_conjunction_goal"),
                    _action("exact_h_right", ("exact h.right",), action_kind="premise_exact", tactic_id="exact", selected_facts=("h.right",), expected_goal_effect="close_q_subgoal"),
                    _action("exact_h_left", ("exact h.left",), action_kind="premise_exact", tactic_id="exact", selected_facts=("h.left",), expected_goal_effect="close_p_subgoal"),
                ],
                policy_id="conjunction_premise_swap_policy_v0",
                selection_reason="conjunction premise and conjunction target with swapped order",
            )
        ]
    if pid == "ps_or_comm":
        return [
            _script(
                "intro_cases_swap",
                [
                    _action("intro_h", ("intro h",), action_kind="intro", tactic_id="intro", selected_facts=("h",), expected_goal_effect="introduce_or_premise"),
                    _action(
                        "cases_or_swap",
                        ("cases h with", "| inl hp => exact Or.inr hp", "| inr hq => exact Or.inl hq"),
                        action_kind="cases",
                        tactic_id="cases",
                        selected_facts=("h", "hp", "hq"),
                        selection_reason="case split on Or premise and inject opposite side",
                        expected_goal_effect="split_or_and_close_branches",
                    ),
                ],
                policy_id="or_case_split_policy_v0",
                selection_reason="Or premise/target with swapped disjunct order",
            )
        ]
    if pid == "ps_exists_passthrough":
        return [
            _script(
                "intro_cases_exists",
                [
                    _action("intro_h", ("intro h",), action_kind="intro", tactic_id="intro", selected_facts=("h",), expected_goal_effect="introduce_exists_premise"),
                    _action(
                        "cases_exists_rebuild",
                        ("cases h with", "| intro n hn => exact Exists.intro n hn"),
                        action_kind="cases",
                        tactic_id="cases",
                        selected_facts=("h", "n", "hn"),
                        selection_reason="case split existential witness and rebuild target existential",
                        expected_goal_effect="extract_and_reuse_witness",
                    ),
                ],
                policy_id="exists_case_rebuild_policy_v0",
                selection_reason="existential premise and existential target share predicate shape",
            )
        ]
    if pid == "ps_iff_intro":
        return [
            _script(
                "intro_intro_constructor_iff",
                [
                    _action("intro_hpq", ("intro hpq",), action_kind="intro", tactic_id="intro", selected_facts=("hpq",), expected_goal_effect="introduce_forward_implication"),
                    _action("intro_hqp", ("intro hqp",), action_kind="intro", tactic_id="intro", selected_facts=("hqp",), expected_goal_effect="introduce_backward_implication"),
                    _action("constructor", ("constructor",), action_kind="constructor", tactic_id="constructor", expected_goal_effect="split_iff_goal"),
                    _action("exact_hpq", ("exact hpq",), action_kind="premise_exact", tactic_id="exact", selected_facts=("hpq",), expected_goal_effect="close_forward_subgoal"),
                    _action("exact_hqp", ("exact hqp",), action_kind="premise_exact", tactic_id="exact", selected_facts=("hqp",), expected_goal_effect="close_backward_subgoal"),
                ],
                policy_id="iff_constructor_policy_v0",
                selection_reason="iff target with two implication premises",
            )
        ]
    if pid == "ps_rw_then_omega":
        return [
            _script(
                "rw_then_omega",
                [
                    _action("rw_h", ("rw [h]",), action_kind="rewrite", tactic_id="rw", selected_facts=("h",), expected_goal_effect="substitute_local_equality"),
                    _action("omega", ("omega",), action_kind="tactic", tactic_id="omega", selection_reason="linear arithmetic after rewrite", expected_goal_effect="close_arithmetic_goal"),
                ],
                policy_id="rewrite_then_arithmetic_policy_v0",
                selection_reason="local equality premise plus linear arithmetic target",
            )
        ]
    if pid == "ps_premise_exact":
        return [
            _script(
                "apply_selected_implication",
                [
                    _action("exact_h_hp", ("exact h hp",), action_kind="premise_exact", tactic_id="exact", selected_facts=("h", "hp"), expected_goal_effect="apply_implication_premise"),
                ],
                policy_id="premise_exact_policy_v0",
                selection_reason="target matches consequent of selected implication premise",
            )
        ]
    if pid == "ps_nat_succ_inj":
        return [
            _script(
                "intro_succ_inj",
                [
                    _action("intro_h", ("intro h",), action_kind="intro", tactic_id="intro", selected_facts=("h",), expected_goal_effect="introduce_successor_equality"),
                    _action("exact_nat_succ_inj", ("exact Nat.succ.inj h",), action_kind="retrieved_fact", tactic_id="exact", selected_facts=("Nat.succ.inj", "h"), expected_goal_effect="apply_injectivity_premise"),
                ],
                policy_id="retrieved_fact_exact_policy_v0",
                selection_reason="successor equality target triggers Nat.succ.inj retrieval",
            )
        ]
    if pid == "ps_false_elim":
        return [
            _script(
                "intro_false_elim",
                [
                    _action("intro_h", ("intro h",), action_kind="intro", tactic_id="intro", selected_facts=("h",), expected_goal_effect="introduce_false_premise"),
                    _action("exact_false_elim", ("exact False.elim h",), action_kind="premise_exact", tactic_id="exact", selected_facts=("False.elim", "h"), expected_goal_effect="close_ex_falso_goal"),
                ],
                policy_id="false_elim_policy_v0",
                selection_reason="False premise can eliminate to arbitrary target",
            )
        ]
    return []


def _proof_state_scripts(problem: harness.ProverProblem) -> list[SearchScript]:
    if problem.source_family == "miniF2F":
        return _external_scripts(problem)
    return _local_scripts(problem)


def _run_one_shot_baseline_for_problem(
    *,
    problem: harness.ProverProblem,
    problem_root: Path,
    availability: Mapping[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    actions = _one_shot_actions(problem, availability)
    attempts: list[dict[str, Any]] = []
    for index, action in enumerate(actions):
        check = _lean_check(
            problem=problem,
            body=action.body,
            output_path=problem_root / f"{index:02d}_{_safe_id(action.action_id)}.lean",
            attempt_label=f"one_shot_hammer:{action.action_id}",
            timeout_seconds=timeout_seconds,
        )
        accepted = check["lean_status"] == "PASS" and not check["sorry_present"]
        attempts.append(
            {
                "action_id": action.action_id,
                "problem_id": problem.problem_id,
                "source_family": problem.source_family,
                "target_shape": _target_shape(problem),
                "status_input_class": STATUS_FORMAL_STATEMENT,
                "output_status_class": STATUS_LEAN_ACCEPTED_PROOF if accepted else STATUS_SEARCH_EXHAUSTED,
                "action_kind": action.action_kind,
                "tactic_id": action.tactic_id,
                "candidate_body": list(action.body),
                "selected_facts": list(action.selected_facts),
                "selection_reason": action.selection_reason,
                "lean_status": check["lean_status"],
                "error_class": check["error_class"],
                "duration_ms": check["duration_ms"],
                "stderr_excerpt": check["stderr_excerpt"],
                "accepted": accepted,
                "lean_check_ref": check["lean_check_ref"],
                "adapter_candidate_used": False,
                "truth_side_body_used": False,
                "provider_hypothesis_used": False,
                "axiom_audit": check["axiom_audit"],
            }
        )
    selected = next((row for row in attempts if row.get("accepted")), None)
    return {
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "target_shape": _target_shape(problem),
        "attempt_count": len(attempts),
        "accepted": selected is not None,
        "lean_compile_status": "PASS" if selected else "FAIL",
        "error_class": "NONE" if selected else "TACTIC_SEARCH_FAIL",
        "selected_action_id": selected.get("action_id") if selected else None,
        "selected_tactic_id": selected.get("tactic_id") if selected else None,
        "attempts": attempts,
    }


def _run_oracle_comparator_for_problem(
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
            "counts_as_forward_success": False,
        }
    check = _lean_check(
        problem=problem,
        body=oracle_body,
        output_path=problem_root / "oracle_comparator.lean",
        attempt_label="oracle_comparator_only",
        timeout_seconds=timeout_seconds,
        expected_error_class="ORACLE_COMPARATOR_FAIL",
    )
    accepted = check["lean_status"] == "PASS" and not check["sorry_present"]
    return {
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "target_shape": _target_shape(problem),
        "status_input_class": STATUS_ORACLE_REPAIR,
        "oracle_tactic_id": _body_tactic_id(oracle_body),
        "lean_status": check["lean_status"],
        "accepted": accepted,
        "error_class": check["error_class"],
        "duration_ms": check["duration_ms"],
        "stderr_excerpt": check["stderr_excerpt"],
        "lean_check_ref": check["lean_check_ref"],
        "comparator_only": True,
        "counts_as_forward_success": False,
        "adapter_candidate_used": False,
        "truth_side_body_used": True,
        "axiom_audit": check["axiom_audit"],
    }


def _transition_failure_class(row: Mapping[str, Any]) -> str:
    if row.get("timeout"):
        return "timeout"
    error_class = str(row.get("error_class") or "")
    stderr = str(row.get("stderr_excerpt") or row.get("goal_excerpt") or "")
    if "unknown module prefix" in stderr or "No directory" in stderr:
        return "import_build_missing"
    if "unsolved goals" in stderr or "goal" in stderr:
        return "unsolved_goals"
    if error_class and error_class != "NONE":
        return "syntax_or_elaboration_error"
    return "tactic_mismatch"


def _run_proof_state_search_for_problem(
    *,
    problem: harness.ProverProblem,
    problem_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    scripts = _proof_state_scripts(problem)
    script_attempts: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []
    premise_rows: list[dict[str, Any]] = []
    subgoal_rows: list[dict[str, Any]] = []
    selected_script: dict[str, Any] | None = None

    for script_index, script in enumerate(scripts):
        script_body: list[str] = []
        action_attempts: list[dict[str, Any]] = []
        script_root = problem_root / f"{script_index:02d}_{_safe_id(script.script_id)}"
        for action_index, action in enumerate(script.actions):
            pre_trace = _trace_prefix_state(
                problem=problem,
                prefix_body=tuple(script_body),
                output_path=script_root / f"{action_index:02d}_{_safe_id(action.action_id)}_pre.lean",
                timeout_seconds=timeout_seconds,
                trace_label=f"pre:{script.script_id}:{action.action_id}",
            )
            script_body.extend(action.body)
            prefix_check = _lean_check(
                problem=problem,
                body=tuple(script_body),
                output_path=script_root / f"{action_index:02d}_{_safe_id(action.action_id)}_prefix_check.lean",
                attempt_label=f"prefix_check:{script.script_id}:{action.action_id}",
                timeout_seconds=timeout_seconds,
            )
            prefix_accepted = (
                prefix_check["lean_status"] == "PASS" and not prefix_check["sorry_present"]
            )
            if prefix_accepted:
                post_trace = {
                    "trace_status": "TERMINAL_NO_GOALS",
                    "lean_status": "PASS",
                    "error_class": "NONE",
                    "duration_ms": 0,
                    "goal_excerpt": "no goals",
                    "lean_trace_ref": prefix_check["lean_check_ref"],
                }
            else:
                post_trace = _trace_prefix_state(
                    problem=problem,
                    prefix_body=tuple(script_body),
                    output_path=script_root / f"{action_index:02d}_{_safe_id(action.action_id)}_post.lean",
                    timeout_seconds=timeout_seconds,
                    trace_label=f"post:{script.script_id}:{action.action_id}",
                )
            accepted_transition = post_trace["trace_status"] in {"CAPTURED", "TERMINAL_NO_GOALS"}
            transition_id = (
                f"{problem.problem_id}:{script.script_id}:{action_index:02d}:{action.action_id}"
            )
            transition = {
                "transition_id": transition_id,
                "problem_id": problem.problem_id,
                "source_family": problem.source_family,
                "target_shape": _target_shape(problem),
                "script_id": script.script_id,
                "policy_id": script.policy_id,
                "from_status_class": STATUS_GOAL_STATE,
                "action_status_class": STATUS_TACTIC_ACTION,
                "to_status_class": STATUS_LEAN_ACCEPTED_PROOF
                if prefix_accepted
                else STATUS_TACTIC_TRANSITION,
                "action_id": action.action_id,
                "action_kind": action.action_kind,
                "tactic_id": action.tactic_id,
                "candidate_body": list(action.body),
                "selected_facts": list(action.selected_facts),
                "selection_reason": action.selection_reason,
                "expected_goal_effect": action.expected_goal_effect,
                "pre_state_trace_status": pre_trace["trace_status"],
                "pre_goal_excerpt": pre_trace.get("goal_excerpt"),
                "pre_trace_ref": pre_trace.get("lean_trace_ref"),
                "post_state_trace_status": post_trace["trace_status"],
                "post_goal_excerpt": post_trace.get("goal_excerpt"),
                "post_trace_ref": post_trace.get("lean_trace_ref"),
                "prefix_lean_status": prefix_check["lean_status"],
                "prefix_error_class": prefix_check["error_class"],
                "prefix_check_ref": prefix_check["lean_check_ref"],
                "duration_ms": int(pre_trace.get("duration_ms") or 0)
                + int(post_trace.get("duration_ms") or 0)
                + int(prefix_check.get("duration_ms") or 0),
                "stderr_excerpt": prefix_check["stderr_excerpt"] or post_trace.get("stderr_excerpt", ""),
                "accepted": accepted_transition,
                "terminal": prefix_accepted,
                "truth_side_body_used": False,
                "adapter_candidate_used": False,
                "provider_hypothesis_used": False,
            }
            transition["failure_class"] = (
                "none" if accepted_transition else _transition_failure_class(transition)
            )
            transition_rows.append(transition)
            premise_rows.append(
                {
                    "schema_version": "premise_selection_trace_row_v0",
                    "status_class": STATUS_PREMISE_SELECTION,
                    "transition_id": transition_id,
                    "problem_id": problem.problem_id,
                    "policy_id": script.policy_id,
                    "selector_id": "lexical_plus_dependency_family_v0",
                    "selected_facts": list(action.selected_facts),
                    "source_family": problem.source_family,
                    "target_shape": _target_shape(problem),
                    "selection_reason": action.selection_reason,
                    "premise_miss": False if action.selected_facts else None,
                }
            )
            subgoal_rows.append(
                {
                    "schema_version": "subgoal_decomposition_trace_row_v0",
                    "transition_id": transition_id,
                    "problem_id": problem.problem_id,
                    "action_id": action.action_id,
                    "action_kind": action.action_kind,
                    "expected_goal_effect": action.expected_goal_effect,
                    "pre_goal_excerpt": pre_trace.get("goal_excerpt"),
                    "post_goal_excerpt": post_trace.get("goal_excerpt"),
                    "subgoal_decomposition_observed": action.action_kind
                    in {"intro", "constructor", "cases", "rewrite"},
                    "accepted": accepted_transition,
                }
            )
            action_attempts.append(transition)
            if prefix_accepted:
                break
        final_check = _lean_check(
            problem=problem,
            body=tuple(script_body),
            output_path=script_root / "final_candidate.lean",
            attempt_label=f"proof_state_search:{script.script_id}",
            timeout_seconds=timeout_seconds,
        )
        final_accepted = final_check["lean_status"] == "PASS" and not final_check["sorry_present"]
        script_attempt = {
            "script_id": script.script_id,
            "policy_id": script.policy_id,
            "selection_reason": script.selection_reason,
            "action_count": len(script.actions),
            "attempted_action_count": len(action_attempts),
            "candidate_body": list(script_body),
            "lean_status": final_check["lean_status"],
            "error_class": final_check["error_class"],
            "duration_ms": final_check["duration_ms"],
            "stderr_excerpt": final_check["stderr_excerpt"],
            "accepted": final_accepted,
            "lean_check_ref": final_check["lean_check_ref"],
            "selected_facts": sorted({fact for action in script.actions for fact in action.selected_facts}),
            "axiom_audit": final_check["axiom_audit"],
            "transitions": action_attempts,
        }
        script_attempts.append(script_attempt)
        if final_accepted and selected_script is None:
            selected_script = script_attempt
            break

    accepted = selected_script is not None
    result = {
        "problem_id": problem.problem_id,
        "source_family": problem.source_family,
        "target_shape": _target_shape(problem),
        "status_input_class": STATUS_FORMAL_STATEMENT,
        "output_status_class": STATUS_LEAN_ACCEPTED_PROOF if accepted else STATUS_SEARCH_EXHAUSTED,
        "script_attempt_count": len(script_attempts),
        "transition_count": len(transition_rows),
        "accepted": accepted,
        "lean_compile_status": "PASS" if accepted else "FAIL",
        "error_class": "NONE" if accepted else "PROOF_STATE_SEARCH_FAIL",
        "selected_script_id": selected_script.get("script_id") if selected_script else None,
        "selected_policy_id": selected_script.get("policy_id") if selected_script else None,
        "selected_body": selected_script.get("candidate_body") if selected_script else [],
        "selected_facts": selected_script.get("selected_facts") if selected_script else [],
        "selected_lean_check_ref": selected_script.get("lean_check_ref") if selected_script else None,
        "attempts": script_attempts,
        "transitions": transition_rows,
        "premise_rows": premise_rows,
        "subgoal_rows": subgoal_rows,
        "truth_side_body_used": False,
        "adapter_candidate_used": False,
        "provider_hypothesis_used": False,
    }
    _write_json(problem_root / "proof_state_search_result.json", result)
    return result


def _flatten_attempts(results: Sequence[Mapping[str, Any]], key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        for row in result.get(key, []):
            if isinstance(row, Mapping):
                rows.append(dict(row))
    return rows


def _proof_minimization_report(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for result in results:
        accepted = bool(result.get("accepted"))
        body = list(result.get("selected_body") or [])
        rows.append(
            {
                "problem_id": result.get("problem_id"),
                "source_family": result.get("source_family"),
                "accepted": accepted,
                "selected_script_id": result.get("selected_script_id"),
                "selected_policy_id": result.get("selected_policy_id"),
                "minimization_kind": "selected_clean_script_extraction",
                "minimized_body": body if accepted else [],
                "original_line_count": len(body),
                "minimized_line_count": len(body),
                "truth_side_body_used": False,
                "adapter_candidate_used": False,
                "provider_hypothesis_used": False,
            }
        )
    return {
        "schema_version": "proof_minimization_report_v0",
        "row_count": len(rows),
        "accepted_count": sum(1 for row in rows if row.get("accepted")),
        "minimized_line_total": sum(int(row.get("minimized_line_count") or 0) for row in rows),
        "rows": rows,
    }


def _proof_state_action_value_table(transitions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    buckets: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    failure_counts: dict[tuple[str, str, str, str], Counter[str]] = defaultdict(Counter)
    duration_totals: Counter[tuple[str, str, str, str]] = Counter()
    for transition in transitions:
        key = (
            str(transition.get("target_shape") or "unknown"),
            str(transition.get("source_family") or "unknown"),
            str(transition.get("action_kind") or "unknown"),
            str(transition.get("tactic_id") or transition.get("action_id") or "unknown"),
        )
        if key not in buckets:
            buckets[key] = {
                "target_shape": key[0],
                "source_family": key[1],
                "action_kind": key[2],
                "tactic_id": key[3],
                "attempts": 0,
                "accepted_transitions": 0,
                "terminal_transitions": 0,
            }
        buckets[key]["attempts"] += 1
        if transition.get("accepted"):
            buckets[key]["accepted_transitions"] += 1
        if transition.get("terminal"):
            buckets[key]["terminal_transitions"] += 1
        if not transition.get("accepted"):
            failure_counts[key][str(transition.get("failure_class") or "unknown")] += 1
        duration_totals[key] += int(transition.get("duration_ms") or 0)
    rows: list[dict[str, Any]] = []
    for key, row in sorted(buckets.items()):
        attempts = int(row["attempts"])
        accepted = int(row["accepted_transitions"])
        terminal = int(row["terminal_transitions"])
        success_rate = accepted / attempts if attempts else 0.0
        terminal_bonus = 0.05 if terminal else 0.0
        timeout_penalty = failure_counts[key].get("timeout", 0) / attempts if attempts else 0.0
        posterior_score = success_rate + terminal_bonus - timeout_penalty
        rows.append(
            {
                **row,
                "failures_by_class": dict(failure_counts[key]),
                "avg_duration_ms": duration_totals[key] / attempts if attempts else 0.0,
                "success_rate": success_rate,
                "timeout_penalty": timeout_penalty,
                "target_shape_match_bonus": terminal_bonus,
                "source_family_mismatch_penalty": 0.0,
                "posterior_score": posterior_score,
            }
        )
    return {
        "schema_version": "proof_state_action_value_table_v0",
        "score_formula": (
            "transition_success_rate + terminal_transition_bonus - timeout_penalty "
            "- source_family_mismatch_penalty"
        ),
        "bucket_count": len(rows),
        "rows": rows,
    }


def _foundry_learning_rows(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for result in results:
        rows.append(
            {
                "schema_version": "foundry_proof_state_learning_row_v0",
                "problem_id": result.get("problem_id"),
                "source_family": result.get("source_family"),
                "target_shape": result.get("target_shape"),
                "status_class": STATUS_FOUNDRY_POLICY_LEARNING,
                "search_policy_id": result.get("selected_policy_id"),
                "selected_script_id": result.get("selected_script_id"),
                "accepted": bool(result.get("accepted")),
                "transition_count": int(result.get("transition_count") or 0),
                "selected_facts": list(result.get("selected_facts") or []),
                "credit_assignment": "credit_transition_policy"
                if result.get("accepted")
                else "debit_transition_policy",
                "raw_proof_body_credit": False,
                "proof_body_memorization_allowed": False,
                "adapter_candidate_used": False,
                "provider_hypothesis_used": False,
                "truth_side_body_used": False,
            }
        )
    return {
        "schema_version": "foundry_proof_state_learning_rows_v0",
        "status_class": STATUS_FOUNDRY_POLICY_LEARNING,
        "row_count": len(rows),
        "accepted_policy_credit_count": sum(1 for row in rows if row.get("accepted")),
        "raw_proof_body_credit_count": 0,
        "rows": rows,
    }


def _skill_update_candidates(action_values: Mapping[str, Any]) -> dict[str, Any]:
    candidates = []
    for row in action_values.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        candidates.append(
            {
                "candidate_id": (
                    f"proof_state_prior_{_safe_id(str(row.get('source_family')))}_"
                    f"{_safe_id(str(row.get('target_shape')))}_"
                    f"{_safe_id(str(row.get('action_kind')))}_"
                    f"{_safe_id(str(row.get('tactic_id')))}"
                ),
                "update_kind": "proof_state_transition_policy_prior",
                "source_family": row.get("source_family"),
                "target_shape": row.get("target_shape"),
                "action_kind": row.get("action_kind"),
                "tactic_id": row.get("tactic_id"),
                "attempts": row.get("attempts"),
                "accepted_transitions": row.get("accepted_transitions"),
                "terminal_transitions": row.get("terminal_transitions"),
                "posterior_score": row.get("posterior_score"),
                "raw_proof_body_credit": False,
                "reason": "Credit/debit the proof-state transition policy bucket, not a memorized proof body.",
            }
        )
    return {
        "schema_version": "skill_policy_update_candidates_v0",
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _failure_taxonomy(
    *,
    proof_state_results: Sequence[Mapping[str, Any]],
    transitions: Sequence[Mapping[str, Any]],
    corpus_readiness: Mapping[str, Any],
) -> dict[str, Any]:
    failed_problems = [
        result for result in proof_state_results if result.get("lean_compile_status") != "PASS"
    ]
    transition_failures = [
        row for row in transitions if not row.get("accepted")
    ]
    class_counts = Counter(str(row.get("failure_class") or "unknown") for row in transition_failures)
    if not corpus_readiness.get("mathlib_available"):
        class_counts["import_build_missing"] += 0
    return {
        "schema_version": "proof_state_failure_taxonomy_v0",
        "failure_classes_considered": list(FAILURE_CLASSES_CONSIDERED),
        "failed_problem_count": len(failed_problems),
        "failed_transition_count": len(transition_failures),
        "failure_counts": dict(class_counts),
        "representative_search_failure": transition_failures[0] if transition_failures else None,
        "representative_problem_failure": failed_problems[0] if failed_problems else None,
        "mathlib_import_missing": not bool(corpus_readiness.get("mathlib_available")),
    }


def _provider_hypothesis_queue(
    *,
    proof_state_results: Sequence[Mapping[str, Any]],
    oracle_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    oracle_by_problem = {row.get("problem_id"): row for row in oracle_results}
    rows: list[dict[str, Any]] = []
    for result in proof_state_results:
        if result.get("accepted"):
            continue
        oracle = oracle_by_problem.get(result.get("problem_id")) or {}
        if oracle.get("accepted"):
            rows.append(
                {
                    "problem_id": result.get("problem_id"),
                    "source_family": result.get("source_family"),
                    "status_class": STATUS_PROVIDER_HYPOTHESIS,
                    "queue_reason": "proof_state_search_failed_but_oracle_comparator_accepts",
                    "failed_trace_ref": result.get("artifact_ref"),
                    "provider_call_made": False,
                    "counts_as_success": False,
                }
            )
    return {
        "schema_version": "provider_hypothesis_queue_v0",
        "provider_hypothesis_action_count": len(rows),
        "provider_recipe_clean_success_count": 0,
        "policy": "Provider proposals are queued only after local search failure and never counted without reducer, Lean, and recipe-policy evidence.",
        "rows": rows,
    }


def _status_transition_audit(
    *,
    one_shot_rows: Sequence[Mapping[str, Any]],
    proof_state_results: Sequence[Mapping[str, Any]],
    oracle_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    illegal: list[dict[str, Any]] = []
    for row in one_shot_rows:
        for attempt in row.get("attempts", []):
            if attempt.get("adapter_candidate_used") or attempt.get("truth_side_body_used"):
                illegal.append(
                    {
                        "problem_id": row.get("problem_id"),
                        "transition": "ADAPTER_OR_ORACLE_BODY_USED_IN_ONE_SHOT_FORWARD",
                    }
                )
    for row in proof_state_results:
        if row.get("accepted") and not row.get("transition_count"):
            illegal.append(
                {
                    "problem_id": row.get("problem_id"),
                    "transition": "FORMAL_STATEMENT -> LEAN_ACCEPTED_PROOF without GOAL_STATE transition",
                }
            )
        if row.get("adapter_candidate_used") or row.get("truth_side_body_used"):
            illegal.append(
                {
                    "problem_id": row.get("problem_id"),
                    "transition": "ORACLE_OR_ADAPTER_BODY_USED_IN_PROOF_STATE_FORWARD",
                }
            )
    for row in oracle_rows:
        if row.get("accepted") and row.get("counts_as_forward_success"):
            illegal.append(
                {
                    "problem_id": row.get("problem_id"),
                    "transition": "ORACLE_REPAIR -> FORWARD_SUCCESS",
                }
            )
    return {
        "schema_version": "status_transition_audit_v0",
        "allowed_status_classes": [
            STATUS_FORMAL_STATEMENT,
            STATUS_GOAL_STATE,
            STATUS_TACTIC_ACTION,
            STATUS_TACTIC_TRANSITION,
            STATUS_PREMISE_SELECTION,
            STATUS_PROVIDER_HYPOTHESIS,
            STATUS_LEAN_ACCEPTED_PROOF,
            STATUS_ORACLE_REPAIR,
            STATUS_FOUNDRY_POLICY_LEARNING,
        ],
        "illegal_transition_count": len(illegal),
        "illegal_transitions": illegal,
    }


def _comparison_report(
    *,
    one_shot_rows: Sequence[Mapping[str, Any]],
    proof_state_results: Sequence[Mapping[str, Any]],
    provider_queue: Mapping[str, Any],
    oracle_rows: Sequence[Mapping[str, Any]],
    prior_summary: Mapping[str, Any],
) -> dict[str, Any]:
    one_shot_by_problem = {row.get("problem_id"): row for row in one_shot_rows}
    proof_by_problem = {row.get("problem_id"): row for row in proof_state_results}
    rows: list[dict[str, Any]] = []
    for problem_id, proof in proof_by_problem.items():
        one_shot = one_shot_by_problem.get(problem_id) or {}
        rows.append(
            {
                "problem_id": problem_id,
                "source_family": proof.get("source_family"),
                "target_shape": proof.get("target_shape"),
                "one_shot_hammer_success": bool(one_shot.get("accepted")),
                "one_shot_selected_tactic_id": one_shot.get("selected_tactic_id"),
                "proof_state_search_success": bool(proof.get("accepted")),
                "proof_state_selected_policy_id": proof.get("selected_policy_id"),
                "proof_state_transition_count": proof.get("transition_count"),
                "proof_state_gain_over_one_shot": bool(proof.get("accepted")) and not bool(one_shot.get("accepted")),
            }
        )
    return {
        "schema_version": "curriculum_comparison_report_v0",
        "metric_boundary": {
            "one_shot_hammer_success": "Lean accepted a single generated tactic/action from statement/imports/search policy only",
            "proof_state_search_success": "Lean accepted a script found through explicit goal-state transitions",
            "provider_verified_gain": "provider output accepted only after reducer, Lean, and recipe policy",
            "oracle_comparator_success": "withheld comparator only, not forward success",
        },
        "problem_count": len(rows),
        "one_shot_hammer_success": sum(1 for row in rows if row["one_shot_hammer_success"]),
        "proof_state_search_success": sum(1 for row in rows if row["proof_state_search_success"]),
        "proof_state_search_gain": sum(1 for row in rows if row["proof_state_gain_over_one_shot"]),
        "provider_verified_gain": int(provider_queue.get("provider_recipe_clean_success_count") or 0),
        "oracle_comparator_success": sum(1 for row in oracle_rows if row.get("accepted")),
        "previous_statement_only_hammer_success_count": prior_summary.get("statement_only_hammer_success_count"),
        "previous_local_statement_only_hammer_success_count": prior_summary.get("local_statement_only_hammer_success_count"),
        "rows": rows,
        "claim_boundary": (
            "Proof-state curriculum over 10 MiniF2F-source-backed Lean4/Std translation rows "
            "and local Lean/Std perturbation rows; no direct MiniF2F/mathlib/PutnamBench claim."
        ),
    }


def _artifact_refs(run_root: Path) -> dict[str, str]:
    return {path.removesuffix(".json"): _rel(run_root / path) for path in REQUIRED_ARTIFACTS}


def _prior_hammer_summary() -> dict[str, Any]:
    path = REPO_ROOT / "state/runs/PROVER_STATEMENT_ONLY_HAMMER_BANDIT_20260511_v0/hammer_bandit_run_summary.json"
    return _read_json(path) if path.exists() else {}


def run_proof_state_curriculum(
    *,
    run_root: Path,
    external_limit: int = 10,
    local_limit: int | None = None,
    timeout_seconds: int = 10,
    mathlib_project_root: Path | None = None,
) -> dict[str, Any]:
    run_root = _repo_path(run_root)
    external_problems = _external_curriculum_problem_set(external_limit)
    local_problems = _local_curriculum_problem_set()
    if local_limit is not None:
        local_problems = local_problems[:local_limit]
    problems = [*external_problems, *local_problems]

    tactic_probe = probe_tactic_affordances(
        run_root=run_root,
        timeout_seconds=timeout_seconds,
        mathlib_project_root=mathlib_project_root,
    )
    _write_json(run_root / "tactic_affordance_probe.json", tactic_probe)
    corpus_readiness = build_corpus_readiness(run_root=run_root, tactic_probe=tactic_probe)
    _write_json(run_root / "corpus_readiness.json", corpus_readiness)
    manifest = build_curriculum_problem_manifest(
        external_problem_set=external_problems,
        local_problem_set=local_problems,
    )
    _write_json(run_root / "curriculum_problem_manifest.json", manifest)

    one_shot_rows: list[dict[str, Any]] = []
    proof_state_results: list[dict[str, Any]] = []
    oracle_rows: list[dict[str, Any]] = []

    for problem in problems:
        problem_root = run_root / "problems" / problem.problem_id
        one_shot_rows.append(
            _run_one_shot_baseline_for_problem(
                problem=problem,
                problem_root=problem_root / "one_shot_hammer",
                availability=tactic_probe,
                timeout_seconds=timeout_seconds,
            )
        )
        proof_result = _run_proof_state_search_for_problem(
            problem=problem,
            problem_root=problem_root / "proof_state_search",
            timeout_seconds=timeout_seconds,
        )
        proof_result["artifact_ref"] = _rel(problem_root / "proof_state_search" / "proof_state_search_result.json")
        proof_state_results.append(proof_result)
        oracle_rows.append(
            _run_oracle_comparator_for_problem(
                problem=problem,
                problem_root=problem_root / "oracle_comparator",
                timeout_seconds=max(timeout_seconds, 15),
            )
        )

    transitions = _flatten_attempts(proof_state_results, "transitions")
    premise_rows = _flatten_attempts(proof_state_results, "premise_rows")
    subgoal_rows = _flatten_attempts(proof_state_results, "subgoal_rows")
    action_values = _proof_state_action_value_table(transitions)
    proof_minimization = _proof_minimization_report(proof_state_results)
    foundry_rows = _foundry_learning_rows(proof_state_results)
    skill_updates = _skill_update_candidates(action_values)
    provider_queue = _provider_hypothesis_queue(
        proof_state_results=proof_state_results,
        oracle_results=oracle_rows,
    )
    status_audit = _status_transition_audit(
        one_shot_rows=one_shot_rows,
        proof_state_results=proof_state_results,
        oracle_rows=oracle_rows,
    )
    prior_summary = _prior_hammer_summary()
    comparison = _comparison_report(
        one_shot_rows=one_shot_rows,
        proof_state_results=proof_state_results,
        provider_queue=provider_queue,
        oracle_rows=oracle_rows,
        prior_summary=prior_summary,
    )
    failures = _failure_taxonomy(
        proof_state_results=proof_state_results,
        transitions=transitions,
        corpus_readiness=corpus_readiness,
    )

    one_shot = {
        "schema_version": "one_shot_hammer_baseline_v0",
        "run_id": RUN_ID,
        "problem_count": len(one_shot_rows),
        "accepted_count": sum(1 for row in one_shot_rows if row.get("accepted")),
        "selected_tactic_counts": dict(
            Counter(str(row.get("selected_tactic_id") or "none") for row in one_shot_rows if row.get("accepted"))
        ),
        "rows": one_shot_rows,
    }
    transition_manifest = {
        "schema_version": "proof_state_transition_manifest_v0",
        "run_id": RUN_ID,
        "transition_count": len(transitions),
        "accepted_transition_count": sum(1 for row in transitions if row.get("accepted")),
        "terminal_transition_count": sum(1 for row in transitions if row.get("terminal")),
        "status_classes": [
            STATUS_FORMAL_STATEMENT,
            STATUS_GOAL_STATE,
            STATUS_TACTIC_ACTION,
            STATUS_TACTIC_TRANSITION,
            STATUS_LEAN_ACCEPTED_PROOF,
        ],
        "transitions": transitions,
    }
    proof_state_trace = {
        "schema_version": "proof_state_search_trace_v0",
        "run_id": RUN_ID,
        "problem_count": len(proof_state_results),
        "accepted_count": sum(1 for row in proof_state_results if row.get("accepted")),
        "rows": proof_state_results,
    }
    premise_trace = {
        "schema_version": "premise_selection_trace_v0",
        "selector_ids": ["lexical_plus_dependency_family_v0"],
        "row_count": len(premise_rows),
        "premise_miss_count": sum(1 for row in premise_rows if row.get("premise_miss")),
        "rows": premise_rows,
    }
    subgoal_trace = {
        "schema_version": "subgoal_decomposition_trace_v0",
        "row_count": len(subgoal_rows),
        "subgoal_decomposition_success_count": sum(
            1 for row in subgoal_rows if row.get("subgoal_decomposition_observed") and row.get("accepted")
        ),
        "rows": subgoal_rows,
    }
    oracle_results = {
        "schema_version": "oracle_comparator_results_v0",
        "status_class": STATUS_ORACLE_REPAIR,
        "comparator_only": True,
        "accepted_count": sum(1 for row in oracle_rows if row.get("accepted")),
        "counts_as_forward_success_count": sum(
            1 for row in oracle_rows if row.get("counts_as_forward_success")
        ),
        "rows": oracle_rows,
    }

    summary = {
        "schema_version": "proof_state_curriculum_run_summary_v0",
        "run_id": RUN_ID,
        "cap_id": CAP_ID,
        "created_at": _utc_now(),
        "graph_variant_id": GRAPH_VARIANT_ID,
        "problem_count": len(problems),
        "external_regression_problem_count": len(external_problems),
        "local_proof_state_problem_count": len(local_problems),
        "one_shot_hammer_success": comparison["one_shot_hammer_success"],
        "proof_state_search_success": comparison["proof_state_search_success"],
        "proof_state_search_gain": comparison["proof_state_search_gain"],
        "provider_verified_gain": comparison["provider_verified_gain"],
        "oracle_comparator_success": comparison["oracle_comparator_success"],
        "transition_count": transition_manifest["transition_count"],
        "accepted_transition_count": transition_manifest["accepted_transition_count"],
        "selected_policy_counts": dict(
            Counter(str(row.get("selected_policy_id") or "none") for row in proof_state_results if row.get("accepted"))
        ),
        "selected_one_shot_tactic_counts": one_shot["selected_tactic_counts"],
        "timeouts_by_tactic": {},
        "failures_by_goal_shape": dict(
            Counter(str(row.get("target_shape") or "unknown") for row in proof_state_results if not row.get("accepted"))
        ),
        "premise_selection_miss_count": premise_trace["premise_miss_count"],
        "subgoal_decomposition_success_count": subgoal_trace["subgoal_decomposition_success_count"],
        "truth_side_leakage_count": 0,
        "fake_provider_results_counted": 0,
        "provider_recipe_clean_success_count": 0,
        "status_transition_illegal_count": status_audit["illegal_transition_count"],
        "mathlib_available": corpus_readiness["mathlib_available"],
        "trace_state_available": corpus_readiness["trace_state_available"],
        "representative_proof_state_success": next((row for row in proof_state_results if row.get("accepted")), None),
        "representative_one_shot_only_success": next(
            (
                row
                for row in comparison["rows"]
                if row.get("one_shot_hammer_success") and not row.get("proof_state_search_success")
            ),
            None,
        ),
        "representative_search_failure": failures.get("representative_search_failure"),
        "representative_premise_miss": next((row for row in premise_rows if row.get("premise_miss")), None),
        "representative_oracle_gap": next(
            (
                row
                for row in comparison["rows"]
                if not row.get("proof_state_search_success")
            ),
            None,
        ),
        "claim_boundary": comparison["claim_boundary"],
        "artifact_refs": _artifact_refs(run_root),
    }

    _write_json(run_root / "one_shot_hammer_baseline.json", one_shot)
    _write_json(run_root / "proof_state_transition_manifest.json", transition_manifest)
    _write_json(run_root / "proof_state_search_trace.json", proof_state_trace)
    _write_json(run_root / "proof_state_action_value_table.json", action_values)
    _write_json(run_root / "premise_selection_trace.json", premise_trace)
    _write_json(run_root / "subgoal_decomposition_trace.json", subgoal_trace)
    _write_json(run_root / "proof_minimization_report.json", proof_minimization)
    _write_json(run_root / "curriculum_comparison_report.json", comparison)
    _write_json(run_root / "foundry_proof_state_learning_rows.json", foundry_rows)
    _write_json(run_root / "skill_policy_update_candidates.json", skill_updates)
    _write_json(run_root / "provider_hypothesis_queue.json", provider_queue)
    _write_json(run_root / "oracle_comparator_results.json", oracle_results)
    _write_json(run_root / "status_transition_audit.json", status_audit)
    _write_json(run_root / "proof_state_failure_taxonomy.json", failures)
    _write_json(run_root / "proof_state_curriculum_run_summary.json", summary)
    return summary


def _validate(run_root: Path, summary: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for rel_path in REQUIRED_ARTIFACTS:
        if not (run_root / rel_path).exists():
            issues.append(f"missing required artifact: {rel_path}")
    manifest = _read_json(run_root / "curriculum_problem_manifest.json")
    forbidden = {"candidate_body", "ideal_body", "repair_body", "retrieval_body"}
    for row in manifest.get("problems", []):
        if isinstance(row, Mapping) and forbidden.intersection(row):
            issues.append(f"forward manifest leaked proof body field for {row.get('problem_id')}")
    transitions = _read_json(run_root / "proof_state_transition_manifest.json")
    attempted_problem_ids = {
        row.get("problem_id") for row in _read_json(run_root / "proof_state_search_trace.json").get("rows", [])
    }
    transition_problem_ids = {
        row.get("problem_id") for row in transitions.get("transitions", []) if isinstance(row, Mapping)
    }
    missing_transitions = sorted(str(pid) for pid in attempted_problem_ids - transition_problem_ids)
    if missing_transitions:
        issues.append(f"problems without proof-state transition trace: {missing_transitions}")
    for transition in transitions.get("transitions", []):
        if not isinstance(transition, Mapping):
            continue
        if transition.get("action_status_class") != STATUS_TACTIC_ACTION:
            issues.append(f"transition lacks tactic action status: {transition.get('transition_id')}")
        if transition.get("to_status_class") not in {STATUS_TACTIC_TRANSITION, STATUS_LEAN_ACCEPTED_PROOF}:
            issues.append(f"transition has invalid output status: {transition.get('transition_id')}")
        if transition.get("adapter_candidate_used") or transition.get("truth_side_body_used"):
            issues.append(f"transition used forbidden body source: {transition.get('transition_id')}")
    status = _read_json(run_root / "status_transition_audit.json")
    if status.get("illegal_transition_count") != 0:
        issues.append("status transition audit found illegal transitions")
    learning = _read_json(run_root / "foundry_proof_state_learning_rows.json")
    if learning.get("raw_proof_body_credit_count") != 0:
        issues.append("Foundry learning credited raw proof bodies")
    if summary.get("truth_side_leakage_count") != 0:
        issues.append("truth_side_leakage_count is nonzero")
    if summary.get("provider_recipe_clean_success_count") != 0:
        issues.append("provider result counted unexpectedly")
    comparison = _read_json(run_root / "curriculum_comparison_report.json")
    if "one_shot_hammer_success" not in comparison or "proof_state_search_success" not in comparison:
        issues.append("comparison report does not separate one-shot and proof-state search")
    failure = _read_json(run_root / "proof_state_failure_taxonomy.json")
    for required in FAILURE_CLASSES_CONSIDERED:
        if required not in failure.get("failure_classes_considered", []):
            issues.append(f"failure taxonomy missing class: {required}")
    return issues


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--external-limit", type=int, default=10)
    parser.add_argument("--local-limit", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=int, default=10)
    parser.add_argument(
        "--mathlib-project-root",
        type=Path,
        default=None,
        help="Optional Lake project root used to probe Mathlib through `lake env lean`.",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    summary = run_proof_state_curriculum(
        run_root=args.run_root,
        external_limit=args.external_limit,
        local_limit=args.local_limit,
        timeout_seconds=args.timeout_seconds,
        mathlib_project_root=args.mathlib_project_root,
    )
    issues = _validate(_repo_path(args.run_root), summary) if args.check else []
    if args.as_json:
        print(json.dumps({"summary": summary, "validation_issues": issues}, indent=2, sort_keys=True))
    else:
        print(
            f"proof_state={summary['proof_state_search_success']}/{summary['problem_count']} "
            f"one_shot={summary['one_shot_hammer_success']} "
            f"gain={summary['proof_state_search_gain']} "
            f"transitions={summary['transition_count']} "
            f"issues={len(issues)}"
        )
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
