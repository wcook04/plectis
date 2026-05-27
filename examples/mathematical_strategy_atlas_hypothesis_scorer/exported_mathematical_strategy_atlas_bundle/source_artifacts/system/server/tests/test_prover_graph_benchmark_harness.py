"""Tests for the small Prover graph benchmark harness."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "meta" / "factory"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import run_prover_graph_benchmark as harness  # noqa: E402


def test_problem_set_is_split_aware_and_leakage_scoped() -> None:
    manifest = harness._problem_manifest(harness._problem_set())

    assert manifest["problem_count"] >= 5
    assert {"train", "dev", "test"}.issubset(manifest["split_policy"])
    assert manifest["leakage_policy"]["test_split_tuning"] == "forbidden"
    assert all(row["withheld_until_oracle"] for row in manifest["problems"])


def test_ring1_source_manifest_is_source_backed_and_split_aware() -> None:
    problem_set = harness._ring1_problem_set()
    manifest = harness._problem_source_manifest(problem_set)

    assert manifest["schema_version"] == "prover_problem_source_manifest_v0"
    assert manifest["problem_count"] >= 10
    assert {"train", "dev", "test"}.issubset(manifest["split_policy"])
    assert manifest["leakage_policy"]["proof_body_withheld_until_oracle"] is True
    assert all(row["required_imports"] for row in manifest["problems"])
    assert all(row["source_ref"] for row in manifest["problems"])
    assert all(
        row["oracle_only"]["ideal_body_available_after_oracle"]
        for row in manifest["problems"]
    )
    assert all("candidate_body" not in row for row in manifest["problems"])
    assert all("retrieval_body" not in row for row in manifest["problems"])


def test_aggregate_reports_failure_taxonomy_and_costs() -> None:
    rows = [
        {
            "problem_id": "a",
            "split": "train",
            "source": "local_lean_core",
            "lean_compile_status": "PASS",
            "error_class": "NONE",
            "leakage_detected": False,
            "statement_reconciliation_status": "READY",
            "cost_metrics": {
                "attempt_count": 1,
                "proof_check_count": 1,
                "wall_time_ms": 2,
                "lean_compile_ms": 2,
                "provider_calls": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "estimated_cost_usd": 0.0,
                "context_tokens": 0,
                "num_repair_rounds": 0,
                "num_subgoals": 1,
                "num_retrieved_premises": 0,
            },
        },
        {
            "problem_id": "b",
            "split": "test",
            "source": "local_lean_core",
            "lean_compile_status": "FAIL",
            "error_class": "PROOF_CORE_GAP",
            "leakage_detected": False,
            "statement_reconciliation_status": "READY",
            "cost_metrics": {
                "attempt_count": 1,
                "proof_check_count": 1,
                "wall_time_ms": 3,
                "lean_compile_ms": 3,
                "provider_calls": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "estimated_cost_usd": 0.0,
                "context_tokens": 0,
                "num_repair_rounds": 0,
                "num_subgoals": 1,
                "num_retrieved_premises": 0,
            },
        },
    ]

    aggregate = harness._aggregate(rows)

    assert aggregate["pass_count"] == 1
    assert aggregate["fail_count"] == 1
    assert aggregate["failure_taxonomy"]["PROOF_CORE_GAP"] == 1
    assert aggregate["cost_totals"]["provider_calls"] == 0


@pytest.mark.skipif(shutil.which("lean") is None, reason="Lean CLI not available")
def test_hammer_search_graph_is_statement_only_and_credits_policy(tmp_path: Path) -> None:
    problem = harness.ProverProblem(
        problem_id="hammer_statement_only_true",
        source="external_translation_smoke",
        split="test",
        mode="prove",
        domain="logic",
        informal_statement="True is provable.",
        theorem_name="hammer_statement_only_true",
        theorem_signature="theorem hammer_statement_only_true : True := by",
        candidate_body=("  exact False.elim h",),
        ideal_body=("  exact True.intro",),
        visible_to_lab=("statement", "imports"),
        withheld_until_oracle=("adapter candidate body", "ideal proof body"),
        context_recipe_id="hammer_test",
        expected_error_class_on_fail="TACTIC_SEARCH_FAIL",
        required_imports=("Std",),
        source_ref="test/external_statement_only.lean",
        source_family="miniF2F",
    )

    run_root = tmp_path / "hammer_search"
    summary = harness.run_benchmark(
        run_root=run_root,
        timeout_seconds=30,
        run_id="hammer_search_test",
        problem_set=[problem],
        graph_variant_id=harness.HAMMER_SEARCH_GRAPH_VARIANT,
        cap_id="test",
    )
    row = summary["problem_results"][0]
    manifest = harness.json.loads(
        Path(row["artifact_refs"]["hammer_action_manifest"]).read_text(encoding="utf-8")
    )
    results = harness.json.loads(
        Path(row["artifact_refs"]["hammer_search_results"]).read_text(encoding="utf-8")
    )
    proof_minimization = harness.json.loads(
        Path(row["artifact_refs"]["proof_minimization"]).read_text(encoding="utf-8")
    )
    learning = harness.json.loads(
        Path(row["artifact_refs"]["prover_evolve_learning_row"]).read_text(encoding="utf-8")
    )
    candidate = Path(row["candidate_artifact_path"]).read_text(encoding="utf-8")

    assert row["lean_compile_status"] == "PASS"
    assert manifest["adapter_direct_candidate_allowed"] is False
    assert manifest["statement_only"] is True
    assert "source_adapter_direct_candidate" not in {
        action["action_id"] for action in manifest["actions"]
    }
    assert results["adapter_candidate_used"] is False
    assert results["statement_only"] is True
    assert proof_minimization["truth_side_body_used"] is False
    assert learning["hammer_search_credit"]["raw_proof_body_credit"] is False
    assert "False.elim h" not in candidate
    assert results["selected_action_id"] != "source_adapter_direct_candidate"


@pytest.mark.skipif(shutil.which("lean") is None, reason="Lean CLI not available")
def test_run_benchmark_emits_valid_tmp_run(tmp_path: Path) -> None:
    run_root = tmp_path / "prover_benchmark"

    summary = harness.run_benchmark(run_root=run_root, timeout_seconds=30)
    issues = harness._validate_run(run_root)

    assert issues == []
    assert summary["provider_or_nim_needed"] is False
    assert summary["governance_ladder_extended"] is False
    aggregate = (run_root / "aggregate_report.json").read_text(encoding="utf-8")
    assert '"problem_count": 6' in aggregate


@pytest.mark.skipif(shutil.which("lean") is None, reason="Lean CLI not available")
def test_ring1_source_ingestion_compares_baseline_and_oracle_repair(tmp_path: Path) -> None:
    run_root = tmp_path / "ring1_benchmark"

    summary = harness.run_ring1_source_ingestion(run_root=run_root, timeout_seconds=30)
    issues = harness._validate_run(run_root)

    assert issues == []
    assert summary["provider_or_nim_needed"] is False
    assert summary["governance_ladder_extended"] is False
    comparison = harness.json.loads(
        (run_root / "graph_variant_comparison.json").read_text(encoding="utf-8")
    )
    assert comparison["before_after"]["baseline_proof_core_gap"] >= 1
    assert comparison["before_after"]["oracle_repair_proof_core_gap"] == 0
    assert comparison["before_after"]["repair_success_count"] >= 1
    assert comparison["leakage_audit"]["forward_lab_proof_body_leaks"] == 0


def test_problem_source_manifest_round_trips(tmp_path: Path) -> None:
    problem_set = harness._ring1_problem_set()
    manifest = harness._problem_source_manifest(problem_set)
    manifest_path = tmp_path / "problem_source_manifest.json"
    manifest_path.write_text(harness._json_text(manifest), encoding="utf-8")

    loaded, loaded_manifest = harness._load_problem_source_manifest(manifest_path)

    assert loaded_manifest["schema_version"] == "prover_problem_source_manifest_v0"
    assert [problem.problem_id for problem in loaded] == [
        problem.problem_id for problem in problem_set
    ]
    assert loaded[0].required_imports == ("Std",)


def test_ring2_premise_index_is_forward_safe() -> None:
    premise_index = harness._premise_index()
    problem_set = harness._ring2_problem_set()
    manifest = harness._problem_source_manifest(problem_set)

    assert premise_index["schema_version"] == "premise_index_v0"
    assert premise_index["premise_count"] >= 10
    assert premise_index["leakage_policy"]["proof_bodies_in_index"] is False
    assert manifest["source_id"] == "lean_std_toolchain_ring2_premise_retrieval_v0"
    assert all(
        row["oracle_only"]["needed_premise_ids_available_after_oracle"]
        for row in manifest["problems"]
    )
    assert all("candidate_body" not in row for row in manifest["problems"])
    assert all("retrieval_body" not in row for row in manifest["problems"])
    assert all("proof body" in " ".join(row["withheld_until_oracle"]) for row in manifest["problems"])


def test_premise_retrieval_reports_hit_and_miss() -> None:
    premise_index = harness._premise_index()
    problems = {problem.problem_id: problem for problem in harness._ring2_problem_set()}

    hit = harness._retrieve_premises(problems["ring2_nat_add_comm"], premise_index)
    miss = harness._retrieve_premises(
        problems["ring2_list_map_map_index_miss"], premise_index
    )

    assert "premise_nat_add_comm" in hit["retrieved_premise_ids"]
    assert "premise_list_map_map" not in miss["retrieved_premise_ids"]
    assert miss["oracle_needed_premise_ids_visible"] is False
    assert miss["proof_body_visible"] is False


@pytest.mark.skipif(shutil.which("lean") is None, reason="Lean CLI not available")
def test_ring2_premise_retrieval_compares_three_variants(tmp_path: Path) -> None:
    run_root = tmp_path / "ring2_benchmark"

    summary = harness.run_ring2_premise_retrieval(run_root=run_root, timeout_seconds=30)
    issues = harness._validate_run(run_root)

    assert issues == []
    assert summary["provider_or_nim_needed"] is False
    assert summary["governance_ladder_extended"] is False
    comparison = harness.json.loads(
        (run_root / "graph_variant_comparison.json").read_text(encoding="utf-8")
    )
    variants = {
        row["graph_variant_id"]: row
        for row in comparison["graph_variants"]
    }
    assert set(variants) == {
        "baseline_graph_v0",
        "premise_retrieval_graph_v0",
        "oracle_repair_graph_v0",
    }
    metrics = variants["premise_retrieval_graph_v0"]["premise_retrieval_metrics"]
    assert metrics["premise_recall"] < 1.0
    assert metrics["proof_success_given_hit"] >= 1
    assert metrics["proof_failure_despite_hit"] >= 1
    assert comparison["representative_retrieval_hit_success"] is not None
    assert comparison["representative_retrieval_hit_proof_failure"] is not None
    assert comparison["representative_retrieval_miss_oracle_repair_success"] is not None
    assert comparison["leakage_audit"]["forward_lab_proof_body_leaks"] == 0
    assert comparison["cost_comparison"]["premise_retrieval_provider_calls"] == 0


def test_strategy_cards_are_executable_control_objects() -> None:
    atlas = harness._strategy_cards()
    strategy_ids = {row["strategy_id"] for row in atlas["cards"]}

    assert atlas["schema_version"] == "mathematical_strategy_atlas_v0"
    assert len(strategy_ids) >= 6
    assert {
        "equality_normal_form",
        "iff_split",
        "constructor_injectivity",
        "recursive_data_induction",
        "membership_decomposition",
        "composition_fusion",
    }.issubset(strategy_ids)
    assert all(row["mathematical_lens"] for row in atlas["cards"])
    assert atlas["leakage_policy"]["truth_side_proof_bodies_in_cards"] is False


def test_prover_skill_atlas_maps_strategy_card_to_executable_cell() -> None:
    strategy_atlas = harness._strategy_cards()
    skill_atlas = harness._prover_skill_atlas(strategy_atlas)
    decision = harness._composition_root_decision(
        strategy_atlas=strategy_atlas,
        skill_atlas=skill_atlas,
    )
    cells = {row["skill_id"]: row for row in skill_atlas["cells"]}

    assert skill_atlas["schema_version"] == "prover_skill_atlas_v0"
    assert decision["schema_version"] == "prover_skill_composition_root_decision_v0"
    assert decision["selected_root"]["root_id"] == "prover_skill_atlas_v0_run_artifact"
    assert "skill_equality_orientation_v0" in cells
    cell = cells["skill_equality_orientation_v0"]
    assert cell["recognizer"]["trigger_features"]
    assert cell["view_generator"]["representation_transforms"]
    assert cell["retrieval_policy"]["allowed_source_rules"]
    assert cell["proof_plan_method"]["skeleton_templates"]
    assert cell["critic"]["expected_failure_modes"]
    assert cell["repair_policy"]["rewrite_direction_repair"] == "allowed_without_oracle_body_copy"
    assert skill_atlas["leakage_policy"]["truth_side_proof_bodies_in_skill_cells"] is False


def test_strategy_problem_manifest_hides_truth_side_bodies() -> None:
    manifest = harness._problem_source_manifest(harness._strategy_problem_set())

    assert manifest["source_id"] == "lean_std_toolchain_strategy_control_v0"
    assert manifest["problem_count"] >= 12
    for row in manifest["problems"]:
        assert "candidate_body" not in row
        assert "retrieval_body" not in row
        assert "ideal_body" not in row["oracle_only"]
        assert "repair_body" not in row["oracle_only"]
        assert "needed_premise_ids" not in row["oracle_only"]
        assert row["expected_strategy_ids_visible_to_lab"] is False


@pytest.mark.skipif(shutil.which("lean") is None, reason="Lean CLI not available")
def test_strategy_control_graph_compares_four_variants(tmp_path: Path) -> None:
    run_root = tmp_path / "strategy_benchmark"

    summary = harness.run_strategy_control_graph(run_root=run_root, timeout_seconds=30)
    issues = harness._validate_run(run_root)

    assert issues == []
    assert summary["provider_or_nim_needed"] is False
    assert summary["governance_ladder_extended"] is False
    comparison = harness.json.loads(
        (run_root / "graph_variant_comparison.json").read_text(encoding="utf-8")
    )
    variants = {
        row["graph_variant_id"]: row
        for row in comparison["graph_variants"]
    }
    assert set(variants) == {
        "baseline_graph_v0",
        "premise_retrieval_graph_v0",
        "strategy_control_graph_v0",
        "oracle_repair_graph_v0",
    }
    metrics = comparison["strategy_control_metrics"]
    assert len(metrics["exercised_strategy_ids"]) >= 6
    assert metrics["strategy_selection_accuracy"] < 1.0
    assert metrics["proof_success_given_strategy_hit"] >= 1
    assert metrics["proof_failure_despite_strategy_hit"] >= 1
    assert comparison["representative_strategy_hit_proof_success"] is not None
    assert comparison["representative_strategy_hit_retrieval_miss"] is not None
    assert comparison["representative_strategy_hit_proof_synthesis_failure"] is not None
    assert comparison["representative_wrong_strategy_failure"] is not None
    assert comparison["leakage_audit"]["candidate_body_forward_visible"] is False
    assert comparison["leakage_audit"]["retrieval_body_forward_visible"] is False
    assert comparison["cost_comparison"]["provider_calls"] == 0


@pytest.mark.skipif(shutil.which("lean") is None, reason="Lean CLI not available")
def test_skill_atlas_overlay_repairs_orientation_without_oracle_body(tmp_path: Path) -> None:
    run_root = tmp_path / "skill_atlas"

    summary = harness.run_prover_skill_atlas_composition_root(
        run_root=run_root,
        timeout_seconds=30,
    )
    issues = harness._validate_run(run_root)

    assert issues == []
    assert summary["provider_or_nim_needed"] is False
    assert summary["governance_ladder_extended"] is False
    comparison = harness.json.loads(
        (run_root / "graph_variant_comparison.json").read_text(encoding="utf-8")
    )
    variants = {
        row["graph_variant_id"]: row
        for row in comparison["graph_variants"]
    }
    assert {
        "strategy_control_graph_v0",
        harness.SKILL_ATLAS_OVERLAY_GRAPH_VARIANT,
        "oracle_repair_graph_v0",
    }.issubset(variants)
    assert comparison["before_after"]["orientation_failure_repaired_count"] >= 1
    assert (
        comparison["representative_repaired_orientation_failure"]["problem_id"]
        == "strategy_list_length_append_symmetry_hit_fail"
    )
    assert comparison["leakage_audit"]["skill_cell_truth_side_body_used"] is False
    assert comparison["leakage_audit"]["retrieval_body_forward_visible"] is False
    assert comparison["before_after"]["provider_calls"] == 0
    repaired = comparison["representative_repaired_orientation_failure"]["after"]
    overlay_decision = harness.json.loads(
        Path(repaired["artifact_refs"]["skill_cell_overlay_decision"]).read_text(
            encoding="utf-8"
        )
    )
    assert overlay_decision["skill_cell_id"] == "skill_equality_orientation_v0"
    assert overlay_decision["applied"] is True


def test_skill_foundry_candidate_atlas_is_evidence_driven() -> None:
    strategy_atlas = harness._strategy_cards()
    candidate_atlas = harness._prover_skill_foundry_skill_atlas(strategy_atlas)
    cells = {row["skill_id"]: row for row in candidate_atlas["cells"]}

    assert candidate_atlas["schema_version"] == "prover_skill_foundry_candidate_atlas_v0"
    assert candidate_atlas["skill_cell_count"] >= 3
    assert "skill_equality_orientation_v1" in cells
    assert "skill_equality_family_disambiguation_v0" in cells
    assert "skill_composition_fusion_index_expansion_v0" in cells
    assert (
        candidate_atlas["leakage_policy"]["truth_side_proof_bodies_in_skill_cells"]
        is False
    )
    family_cell = cells["skill_equality_family_disambiguation_v0"]
    assert family_cell["case_memory"]["negative_cases"]
    assert family_cell["proof_plan_method"]["skeleton_templates"]
    assert "oracle_needed_premise_ids" in " ".join(
        family_cell["retrieval_policy"]["allowed_source_rules"]
    )


@pytest.mark.skipif(shutil.which("lean") is None, reason="Lean CLI not available")
def test_skill_foundry_mines_evaluates_and_promotes_candidates(tmp_path: Path) -> None:
    run_root = tmp_path / "skill_foundry"

    summary = harness.run_prover_skill_foundry(run_root=run_root, timeout_seconds=30)
    issues = harness._validate_run(run_root)

    assert issues == []
    assert summary["provider_or_nim_needed"] is False
    assert summary["governance_ladder_extended"] is False
    comparison = harness.json.loads(
        (run_root / "graph_variant_comparison.json").read_text(encoding="utf-8")
    )
    aggregate = harness.json.loads(
        (run_root / "aggregate_report.json").read_text(encoding="utf-8")
    )
    clusters = harness.json.loads(
        (run_root / "skill_candidate_clusters.json").read_text(encoding="utf-8")
    )
    decisions = harness.json.loads(
        (run_root / "skill_promotion_decisions.json").read_text(encoding="utf-8")
    )

    assert clusters["cluster_count"] >= 3
    assert aggregate["evaluated_candidate_count"] >= 2
    assert aggregate["candidate_skill_overlay_pass_count"] > aggregate[
        "existing_skill_overlay_pass_count"
    ]
    assert aggregate["promoted_candidate_count"] >= 1
    assert any(
        row["candidate_skill_id"] == "skill_equality_family_disambiguation_v0"
        and row["promotion_decision"] == "promoted"
        for row in decisions["decisions"]
    )
    assert comparison["leakage_audit"]["forward_lab_proof_body_leaks"] == 0
    assert comparison["before_after"]["provider_calls"] == 0


def test_provider_context_pack_is_byte_budgeted_and_leakage_clean() -> None:
    problem_set = harness._strategy_problem_set()
    problem = problem_set[0]

    context_pack, retrieval, skill_decision, allowed_premise_ids = (
        harness._provider_context_pack(
            problem=problem,
            recipe_id="skill_32kb",
            provider="nvidia_nim",
            provider_model=None,
            premise_index=harness._premise_index(),
            problem_set=problem_set,
            local_foundry_by_problem={},
            max_tokens=256,
            temperature=0.0,
        )
    )

    assert context_pack["schema_version"] == "prover_context_pack_v0"
    assert context_pack["graph_role"] == "provider_with_skill_context"
    assert context_pack["context_budget"]["kib"] == 32
    assert sum(section["bytes"] for section in context_pack["context_sections"]) <= 32 * 1024
    assert context_pack["leakage_audit"]["status"] == "PASS"
    context_sections = harness._canonical_json(context_pack["context_sections"])
    assert "candidate_body" not in context_sections
    assert "ideal_body" not in context_sections
    assert retrieval["proof_body_visible"] is False
    assert skill_decision["oracle_needed_premise_ids_visible"] is False
    assert allowed_premise_ids == retrieval["retrieved_premise_ids"]


@pytest.mark.skipif(shutil.which("lean") is None, reason="Lean CLI not available")
def test_provider_context_sweep_compiles_existing_transform_jobs(tmp_path: Path) -> None:
    run_root = tmp_path / "provider_context_sweep"

    summary = harness.run_provider_context_sweep(
        run_root=run_root,
        timeout_seconds=30,
        provider="nvidia_nim",
        context_recipes=("minimal_4kb", "skill_32kb", "repair_32kb"),
        problem_limit=10,
    )
    issues = harness._validate_run(run_root)

    assert issues == []
    assert summary["provider_or_nim_needed"] is True
    assert summary["governance_ladder_extended"] is False
    assert summary["dispatch_posture"] == "compiled_transform_jobs_not_dispatched"
    aggregate = harness.json.loads(
        (run_root / "aggregate_report.json").read_text(encoding="utf-8")
    )
    comparison = harness.json.loads(
        (run_root / "graph_variant_comparison.json").read_text(encoding="utf-8")
    )
    context_manifest = harness.json.loads(
        (run_root / "context_pack_manifest.json").read_text(encoding="utf-8")
    )
    transform_manifest = harness.json.loads(
        (run_root / "transform_job_manifest.json").read_text(encoding="utf-8")
    )
    compliance = harness.json.loads(
        (run_root / "transform_job_compliance_report.json").read_text(encoding="utf-8")
    )

    assert aggregate["problem_count"] == 10
    assert aggregate["attempt_count"] == 30
    assert aggregate["transform_job_count"] == 30
    assert aggregate["cost_totals"]["provider_calls"] == 0
    assert aggregate["leakage_count"] == 0
    assert context_manifest["context_pack_count"] == 30
    assert transform_manifest["task_class"] == harness.PROVER_PROVIDER_TRANSFORM_TASK_CLASS
    assert transform_manifest["dispatch_posture"] == "not_dispatched"
    assert compliance["noncompliant_artifact_count"] == 0
    roles = {row["graph_role"] for row in comparison["provider_graph_roles"]}
    assert {
        "provider_direct",
        "provider_with_skill_context",
        "provider_repair_after_lean_error",
    }.issubset(roles)
    assert comparison["leakage_audit"]["provider_output_bypassed_lean"] is False
    assert comparison["provider_plane_contract"]["dispatch_owner"] == (
        "system.lib.type_a_worker_harness"
    )
