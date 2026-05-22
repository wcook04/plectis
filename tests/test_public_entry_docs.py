from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.validators.public_entry_docs import validate_public_entry_docs


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


def _copy_public_entry_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "paper_modules", public_root / "paper_modules")
    shutil.copytree(MICROCOSM_ROOT / "skills", public_root / "skills")
    shutil.copy2(MICROCOSM_ROOT / "README.md", public_root / "README.md")
    shutil.copy2(MICROCOSM_ROOT / "AGENTS.md", public_root / "AGENTS.md")
    return public_root


def test_public_entry_docs_validate_and_stay_redacted(tmp_path: Path) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    out = public_root / "receipts/first_wave/public_entry_docs_validation.json"

    receipt = validate_public_entry_docs(public_root, out, command="pytest")

    assert receipt["status"] == "pass"
    assert receipt["missing_docs"] == []
    assert receipt["missing_required_phrases_by_doc"] == {}
    assert receipt["forbidden_phrases_by_doc"] == {}
    assert receipt["stale_first_slice_only_phrases"] == []
    assert receipt["accepted_current_authority_organs"] == [
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
    ]
    assert receipt["evidence_class_registry"] == {
        "status": "pass",
        "source_ref": "core/organ_evidence_classes.json",
        "class_count": 5,
        "organ_count": 43,
        "missing_organs": [],
        "unexpected_organs": [],
        "duplicate_organs": [],
        "fail_closed_no_default": True,
    }
    assert receipt["deferred_organs"] == []
    assert receipt["private_state_scan"]["body_redacted"] is True
    assert receipt["private_state_scan"]["blocking_hit_count"] == 0
    text = out.read_text(encoding="utf-8")
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(receipt)
    assert "body" not in _walk_keys(receipt)


def test_public_entry_docs_block_missing_paper_module(tmp_path: Path) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    (public_root / "paper_modules/cold_clone_probe.md").unlink()

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "MISSING_PUBLIC_ENTRY_DOC" in receipt["blocking_codes"]
    assert receipt["missing_docs"] == ["paper_modules/cold_clone_probe.md"]


def test_public_entry_docs_block_missing_evidence_class_registry(tmp_path: Path) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    (public_root / "core/organ_evidence_classes.json").unlink()

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "EVIDENCE_CLASS_REGISTRY_MISMATCH" in receipt["blocking_codes"]
    assert receipt["evidence_class_registry"]["status"] == "missing"
    assert receipt["evidence_class_registry"]["fail_closed_no_default"] is False


def test_public_entry_readme_no_longer_claims_first_slice_only() -> None:
    text = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")
    agents = (MICROCOSM_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())
    normalized_agents = " ".join(agents.split())

    assert "Internal Runtime Spine" in text
    assert "Accepted Public Runtime Spine" in agents
    assert "only implemented organ here is `pattern_binding_contract`" not in text
    assert "only implemented organ here is `pattern_binding_contract`" not in agents
    assert "formal_math_lean_proof_witness" in text
    assert "corpus_readiness_mathlib_absence_gate" in text
    assert "mathematical_strategy_atlas_hypothesis_scorer" in text
    assert "tactic_portfolio_availability_probe" in text
    assert "target_shape_tactic_routing_gate" in text
    assert "lean_std_premise_index" in text
    assert "formal_math_premise_retrieval" in text
    assert "formal_math_verifier_trace_repair_loop" in text
    assert "formal_evidence_cell_anchor_resolver" in text
    assert "undeclared_library_prior_symbol_classifier" in text
    assert "ring2_premise_retrieval_precision_recall_harness" in text
    assert "provider_context_recipe_budget_policy" in text
    assert "verifier_lab_kernel" in text
    assert "public_reveal_walkthrough" in text
    assert "macro_projection_import_protocol" in text
    assert "prediction_oracle_reconciliation" in text
    assert "standards_meta_diagnostics" in text
    assert "durable_agent_work_landing_replay" in text
    assert "research_replication_rubric_artifact_replay" in text
    assert "world_model_projection_drift_control_room" in text
    assert "spatial_world_model_counterfactual_simulation_replay" in text
    assert "cold_reader_route_map" in text
    assert "proof_derived_governed_mutation_authorization" in text
    assert "belief_state_process_reward_replay" in text
    assert "formal-math-premise-retrieval" in text
    assert "ring2-premise-retrieval-precision-recall-harness" in text
    assert "provider-context-recipe-budget-policy" in text
    assert "corpus-readiness-mathlib-absence-gate" in text
    assert "mathematical-strategy-atlas-hypothesis-scorer" in text
    assert "tactic-portfolio-availability-probe" in text
    assert "target-shape-tactic-routing-gate" in text
    assert "lean-std-premise-index" in text
    assert "formal-math-lean-proof-witness" in text
    assert "verifier-lab-kernel" in text
    assert "formal-math-verifier-trace-repair-loop" in text
    assert "formal-evidence-cell-anchor-resolver" in text
    assert "undeclared-library-prior-symbol-classifier" in text
    assert "microcosm reveal" in text
    assert "macro-projection-import-protocol" in text
    assert "prediction-oracle-reconciliation" in text
    assert "standards-meta-diagnostics" in text
    assert "durable-agent-work-landing-replay" in text
    assert "research-replication-rubric-artifact-replay" in text
    assert "world-model-projection-drift-control-room" in text
    assert "spatial-world-model-counterfactual-simulation-replay" in text
    assert "microcosm spatial-simulation" in text
    assert "cold-reader-route-map" in text
    assert "proof-derived-governed-mutation-authorization" in text
    assert "belief-state-process-reward-replay" in text
    assert "public_reveal_walkthrough" in agents
    assert "corpus_readiness_mathlib_absence_gate" in agents
    assert "mathematical_strategy_atlas_hypothesis_scorer" in agents
    assert "tactic_portfolio_availability_probe" in agents
    assert "target_shape_tactic_routing_gate" in agents
    assert "lean_std_premise_index" in agents
    assert "formal_math_premise_retrieval" in agents
    assert "formal_math_verifier_trace_repair_loop" in agents
    assert "formal_evidence_cell_anchor_resolver" in agents
    assert "undeclared_library_prior_symbol_classifier" in agents
    assert "ring2_premise_retrieval_precision_recall_harness" in agents
    assert "provider_context_recipe_budget_policy" in agents
    assert "formal_math_lean_proof_witness" in agents
    assert "verifier_lab_kernel" in agents
    assert "macro_projection_import_protocol" in agents
    assert "prediction_oracle_reconciliation" in agents
    assert "standards_meta_diagnostics" in agents
    assert "durable_agent_work_landing_replay" in agents
    assert "research_replication_rubric_artifact_replay" in agents
    assert "world_model_projection_drift_control_room" in agents
    assert "spatial_world_model_counterfactual_simulation_replay" in agents
    assert "cold_reader_route_map" in agents
    assert "proof_derived_governed_mutation_authorization" in agents
    assert "belief_state_process_reward_replay" in agents
    assert "formal-math-premise-retrieval" in agents
    assert "ring2-premise-retrieval-precision-recall-harness" in agents
    assert "provider-context-recipe-budget-policy" in agents
    assert "corpus-readiness-mathlib-absence-gate" in agents
    assert "mathematical-strategy-atlas-hypothesis-scorer" in agents
    assert "tactic-portfolio-availability-probe" in agents
    assert "target-shape-tactic-routing-gate" in agents
    assert "lean-std-premise-index" in agents
    assert "formal-math-lean-proof-witness" in agents
    assert "verifier-lab-kernel" in agents
    assert "formal-math-verifier-trace-repair-loop" in agents
    assert "formal-evidence-cell-anchor-resolver" in agents
    assert "undeclared-library-prior-symbol-classifier" in agents
    assert "microcosm reveal" in agents
    assert "macro-projection-import-protocol" in agents
    assert "prediction-oracle-reconciliation" in agents
    assert "standards-meta-diagnostics" in agents
    assert "research-replication-rubric-artifact-replay" in agents
    assert "world-model-projection-drift-control-room" in agents
    assert "spatial-world-model-counterfactual-simulation-replay" in agents
    assert "spatial-simulation" in agents
    assert "cold-reader-route-map" in agents
    assert "proof-derived-governed-mutation-authorization" in agents
    assert "Do not widen Lean/Lake" in agents
    assert "Do not treat prediction fixtures as trading or financial advice" in agents
    assert "runnable, synthetic, and receipt-driven" not in text
    assert "public synthetic microcosm" not in text
    assert "private reconstruction control plane" not in text
    assert "source reconstruction workspace" not in agents
    assert "Use only synthetic fixtures" not in agents
    assert "Receipts Are Authority" not in agents
    assert "macro reconstruction contracts" not in agents
    assert "local project operating substrate" in normalized_text
    assert "repo -> .microcosm" in text
    assert "microcosm compile ." in text
    assert "std_python_microcosm_navigation_assay" in text
    assert "implementation_atlas.python_navigation_assay" in text
    assert "executable research prototype" in text
    assert "Architecture Kernel" in text
    assert "microcosm explain <project> <route_id>" in text
    assert "Evidence receipts are the black-box recorder" in text
    assert "evidence_class" in text
    assert "`accepted_current_authority` is not an evidence-strength claim" in normalized_text
    assert "executable research prototype" in normalized_agents
    assert "local project operating substrate" in normalized_agents
    assert "microcosm compile <project>" in agents
    assert "repo -> `.microcosm`" in agents
    assert "Fixtures Are Tests" in agents
    assert "Receipts Are Evidence" in agents
    assert "evidence_class" in agents
    assert "`accepted_current_authority` is not an evidence-strength claim" in normalized_agents


def test_public_entry_commands_do_not_depend_on_parent_state() -> None:
    docs = [
        MICROCOSM_ROOT / "README.md",
        MICROCOSM_ROOT / "skills/cold_start_navigation.md",
    ]

    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert "../state/" not in text
        assert "state/microcosm_portfolio/reconstruction" not in text
        assert "core/preflight_support/organ_fixture_validator_readiness_v1.json" in text
        assert "core/preflight_support/fixture_negative_case_matrix_v1.json" in text
    cold_start = (MICROCOSM_ROOT / "skills/cold_start_navigation.md").read_text(
        encoding="utf-8"
    )
    assert "std_python_microcosm_navigation_assay" in cold_start
    assert "implementation_atlas.python_navigation_assay" in cold_start


def test_public_entry_packet_routes_python_navigation_assay() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )

    route = entry_packet["python_navigation_route"]
    assert route["surface_id"] == "project_python_lens"
    assert route["command"] == "microcosm python-lens <project>"
    assert route["assay_id"] == "std_python_microcosm_navigation_assay"
    assert route["assay_ref"] == ".microcosm/python_lens.json::navigation_assay"
    assert route["implementation_atlas_ref"] == (
        ".microcosm/python_lens.json::implementation_atlas.python_navigation_assay"
    )
    assert route["canonical_depth_ladder"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]
    assert route["source_bodies_exported"] is False
