from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core.validators.fixture_freshness import run_fixture_freshness


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_SUPPORT = MICROCOSM_ROOT / "core/preflight_support"
READINESS = PREFLIGHT_SUPPORT / "organ_fixture_validator_readiness_v1.json"
NEGATIVE_MATRIX = PREFLIGHT_SUPPORT / "fixture_negative_case_matrix_v1.json"
MISSION_DAG = PREFLIGHT_SUPPORT / "microcosm_rebuild_mission_graph_v1.json"
RECEIPT_COVERAGE = PREFLIGHT_SUPPORT / "validator_receipt_coverage_map_v1.json"


def _copy_public_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "fixtures", public_root / "fixtures")
    shutil.copytree(MICROCOSM_ROOT / "receipts", public_root / "receipts")
    return public_root


def test_first_wave_acceptance_plan_records_bounded_lean_and_prediction_witnesses() -> None:
    acceptance = json.loads(
        (MICROCOSM_ROOT / "core/acceptance/first_wave_acceptance.json").read_text(
            encoding="utf-8"
        )
    )

    assert acceptance["status"] == "accepted_runtime_spine_verifier_lab_kernel_bound"
    assert len(acceptance["accepted_current_authority_organs"]) == 45
    assert acceptance["deferred_organs"] == []
    assert acceptance["lean_lake_authorized"] == "bounded_public_witness_only"
    assert acceptance["release_authorized"] is False
    assert acceptance["hosted_public_authorized"] is False
    assert acceptance["publication_authorized"] is False
    assert acceptance["recipient_work_authorized"] is False
    assert acceptance["provider_calls_authorized"] is False
    assert acceptance["trading_or_financial_advice_authorized"] is False
    assert acceptance["private_data_equivalence_authorized"] is False


def test_acceptance_summary_records_runtime_spine_with_bounded_lean_authority(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    run_fixture_freshness(
        READINESS,
        NEGATIVE_MATRIX,
        MISSION_DAG,
        RECEIPT_COVERAGE,
        public_root / "receipts/preflight/fixture_runner_freshness.json",
        command="pytest",
    )
    summary = json.loads(
        (public_root / "receipts/first_wave/acceptance_summary.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["status"] == "pass"
    assert summary["accepted_current_authority_organs"] == [
        "pattern_binding_contract",
        "executable_doctrine_grammar",
        "proof_diagnostic_evidence_spine",
        "formal_math_readiness_gate",
        "corpus_readiness_mathlib_absence_gate",
        "mathematical_strategy_atlas_hypothesis_scorer",
        "tactic_portfolio_availability_probe",
        "target_shape_tactic_routing_gate",
        "lean_std_premise_index",
        "formal_math_premise_retrieval",
        "formal_math_verifier_trace_repair_loop",
        "formal_evidence_cell_anchor_resolver",
        "undeclared_library_prior_symbol_classifier",
        "ring2_premise_retrieval_precision_recall_harness",
        "agent_benchmark_integrity_anti_gaming_replay",
        "provider_context_recipe_budget_policy",
        "formal_math_lean_proof_witness",
        "verifier_lab_kernel",
        "verifier_lab_execution_spine",
        "navigation_hologram_route_plane",
        "mission_transaction_work_spine",
        "durable_agent_work_landing_replay",
        "research_replication_rubric_artifact_replay",
        "world_model_projection_drift_control_room",
        "spatial_world_model_counterfactual_simulation_replay",
        "mechanistic_interpretability_circuit_attribution_replay",
        "agent_route_observability_runtime",
        "pattern_assimilation_step",
        "public_reveal_walkthrough",
        "macro_projection_import_protocol",
        "prediction_oracle_reconciliation",
        "standards_meta_diagnostics",
        "cold_reader_route_map",
        "agent_monitor_redteam_falsification_replay",
        "agent_sabotage_scheming_monitor_replay",
        "agent_memory_temporal_conflict_replay",
        "sleeper_memory_poisoning_quarantine_replay",
        "mcp_tool_authority_replay",
        "proof_derived_governed_mutation_authorization",
        "belief_state_process_reward_replay",
        "agent_sandbox_policy_escape_replay",
        "indirect_prompt_injection_information_flow_policy_replay",
        "agentic_vulnerability_discovery_patch_proof_replay",
        "materials_chemistry_closed_loop_lab_safety_replay",
        "certificate_kernel_execution_lab",
    ]
    assert summary["deferred_organs"] == []
    assert summary["lean_lake_authorized"] == "bounded_public_witness_only"
    assert summary["release_authorized"] is False
    assert summary["trading_or_financial_advice_authorized"] is False
    assert summary["private_data_equivalence_authorized"] is False
