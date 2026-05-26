from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.validators.standards_registry import validate_standards_registry


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def _copy_public_standards_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "standards", public_root / "standards")
    return public_root


def test_standards_registry_validation_passes_with_secret_exclusion(tmp_path: Path) -> None:
    public_root = _copy_public_standards_tree(tmp_path)
    out = public_root / "receipts/first_wave/standards_registry_validation.json"
    registry = json.loads((public_root / "core/standards_registry.json").read_text(encoding="utf-8"))
    expected_count = len(registry["standards"])

    receipt = validate_standards_registry(
        public_root / "core/standards_registry.json",
        public_root / "standards",
        public_root / "core/acceptance/first_wave_acceptance.json",
        out,
        command="pytest",
    )

    assert receipt["status"] == "pass"
    assert receipt["standard_count"] == expected_count
    assert receipt["checked_standard_count"] == expected_count
    assert "std_microcosm_corpus_readiness_mathlib_absence_gate" in receipt["checked_standard_ids"]
    assert "std_microcosm_mathematical_strategy_atlas_hypothesis_scorer" in receipt["checked_standard_ids"]
    assert "std_microcosm_target_shape_tactic_routing_gate" in receipt["checked_standard_ids"]
    assert "std_microcosm_lean_std_premise_index" in receipt["checked_standard_ids"]
    assert "std_microcosm_formal_math_verifier_trace_repair_loop" in receipt["checked_standard_ids"]
    assert "std_microcosm_verifier_lab_kernel" in receipt["checked_standard_ids"]
    assert "std_microcosm_verifier_lab_execution_spine" in receipt["checked_standard_ids"]
    assert "std_microcosm_certificate_kernel_execution_lab" in receipt["checked_standard_ids"]
    assert "std_microcosm_formal_evidence_cell_anchor_resolver" in receipt["checked_standard_ids"]
    assert (
        "std_microcosm_undeclared_library_prior_symbol_classifier"
        in receipt["checked_standard_ids"]
    )
    assert (
        "std_microcosm_ring2_premise_retrieval_precision_recall_harness"
        in receipt["checked_standard_ids"]
    )
    assert "std_microcosm_agent_benchmark_integrity_anti_gaming_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_agent_monitor_redteam_falsification_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_agent_sabotage_scheming_monitor_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_agent_sandbox_policy_escape_replay" in receipt["checked_standard_ids"]
    assert (
        "std_microcosm_indirect_prompt_injection_information_flow_policy_replay"
        in receipt["checked_standard_ids"]
    )
    assert (
        "std_microcosm_agentic_vulnerability_discovery_patch_proof_replay"
        in receipt["checked_standard_ids"]
    )
    assert (
        "std_microcosm_materials_chemistry_closed_loop_lab_safety_replay"
        in receipt["checked_standard_ids"]
    )
    assert "std_microcosm_agent_memory_temporal_conflict_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_sleeper_memory_poisoning_quarantine_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_mcp_tool_authority_replay" in receipt["checked_standard_ids"]
    assert (
        "std_microcosm_proof_derived_governed_mutation_authorization"
        in receipt["checked_standard_ids"]
    )
    assert "std_microcosm_belief_state_process_reward_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_durable_agent_work_landing_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_research_replication_rubric_artifact_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_world_model_projection_drift_control_room" in receipt["checked_standard_ids"]
    assert (
        "std_microcosm_spatial_world_model_counterfactual_simulation_replay"
        in receipt["checked_standard_ids"]
    )
    assert (
        "std_microcosm_mechanistic_interpretability_circuit_attribution_replay"
        in receipt["checked_standard_ids"]
    )
    assert "std_microcosm_tactic_portfolio_availability_probe" in receipt["checked_standard_ids"]
    assert "std_microcosm_standards_meta_diagnostics" in receipt["checked_standard_ids"]
    assert "std_microcosm_cold_reader_route_map" in receipt["checked_standard_ids"]
    assert "std_microcosm_provider_context_recipe_budget_policy" in receipt["checked_standard_ids"]
    assert "std_microcosm_observatory_legibility" in receipt["checked_standard_ids"]
    assert receipt["duplicate_standard_ids"] == []
    assert receipt["missing_standard_files"] == []
    assert receipt["missing_required_fields_by_standard"] == {}
    assert receipt["acceptance_status"]["lean_lake_authorized"] == "bounded_public_witness_only"
    assert receipt["acceptance_status"]["release_authorized"] is False
    assert (
        registry["authority_ceiling"]["count_authority"]
        == "inventory_only_not_completeness_readiness_maturity_or_product_progress"
    )
    assert registry["authority_ceiling"]["standard_count_is_completeness_or_readiness"] is False
    assert registry["authority_ceiling"]["first_wave_required_count_is_product_progress"] is False
    assert registry["authority_ceiling"]["score_based_progress_authority"] is False
    assert "Standard counts and first-wave-required rows are inventory fields only" in registry["anti_claim"]
    assert (
        receipt["authority_ceiling"]["count_authority"]
        == "inventory_only_not_completeness_readiness_maturity_or_product_progress"
    )
    assert receipt["authority_ceiling"]["standard_count_is_completeness_or_readiness"] is False
    assert receipt["authority_ceiling"]["first_wave_required_count_is_product_progress"] is False
    assert receipt["authority_ceiling"]["score_based_progress_authority"] is False
    assert "not completeness, readiness, maturity, or score-based progress" in receipt["anti_claim"]
    assert receipt["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert receipt["secret_exclusion_scan"]["body_in_receipt"] is False
    assert "private_state_scan" not in receipt
    text = out.read_text(encoding="utf-8")
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(receipt)
    assert "body" not in _walk_keys(receipt)


def test_standards_registry_rejects_duplicate_standard_ids(tmp_path: Path) -> None:
    public_root = _copy_public_standards_tree(tmp_path)
    registry_path = public_root / "core/standards_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["standards"].append(dict(registry["standards"][0]))
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    receipt = validate_standards_registry(
        registry_path,
        public_root / "standards",
        public_root / "core/acceptance/first_wave_acceptance.json",
        public_root / "receipts/first_wave/standards_registry_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert registry["standards"][0]["standard_id"] in receipt["duplicate_standard_ids"]
