from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from urllib.request import urlopen

import pytest

from microcosm_core import project_substrate
from microcosm_core.runtime_shell import (
    PROOF_LAB_FIRST_SCREEN_COMMAND,
    PROOF_LAB_RECEIPT_REF,
    PROOF_LAB_ROUTE_REF,
    RuntimeShell,
    SOURCE_OPEN_BODY_POLICY,
    VERIFIER_EXECUTION_LENS_COMMAND,
    VERIFIER_EXECUTION_RECEIPT_REF,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_ORGAN_EVIDENCE_CLASSES = {
    "pattern_binding_contract": "semantic_validator",
    "executable_doctrine_grammar": "semantic_validator",
    "proof_diagnostic_evidence_spine": "algorithmic_projection",
    "formal_math_readiness_gate": "algorithmic_projection",
    "corpus_readiness_mathlib_absence_gate": "algorithmic_projection",
    "tactic_portfolio_availability_probe": "algorithmic_projection",
    "target_shape_tactic_routing_gate": "algorithmic_projection",
    "lean_std_premise_index": "algorithmic_projection",
    "formal_math_premise_retrieval": "algorithmic_projection",
    "formal_math_verifier_trace_repair_loop": "algorithmic_projection",
    "formal_evidence_cell_anchor_resolver": "algorithmic_projection",
    "undeclared_library_prior_symbol_classifier": "algorithmic_projection",
    "ring2_premise_retrieval_precision_recall_harness": "algorithmic_projection",
    "provider_context_recipe_budget_policy": "algorithmic_projection",
    "formal_math_lean_proof_witness": "external_subprocess_witness",
    "verifier_lab_kernel": "semantic_validator",
    "verifier_lab_execution_spine": "external_subprocess_witness",
    "navigation_hologram_route_plane": "semantic_validator",
    "mission_transaction_work_spine": "algorithmic_projection",
    "durable_agent_work_landing_replay": "semantic_validator",
    "research_replication_rubric_artifact_replay": "algorithmic_projection",
    "world_model_projection_drift_control_room": "semantic_validator",
    "spatial_world_model_counterfactual_simulation_replay": "semantic_validator",
    "materials_chemistry_closed_loop_lab_safety_replay": "algorithmic_projection",
    "mechanistic_interpretability_circuit_attribution_replay": "semantic_validator",
    "agent_route_observability_runtime": "semantic_validator",
    "pattern_assimilation_step": "semantic_validator",
    "public_reveal_walkthrough": "semantic_validator",
    "macro_projection_import_protocol": "verified_macro_body_import",
    "prediction_oracle_reconciliation": "algorithmic_projection",
    "standards_meta_diagnostics": "semantic_validator",
    "cold_reader_route_map": "semantic_validator",
    "agent_memory_temporal_conflict_replay": "algorithmic_projection",
    "sleeper_memory_poisoning_quarantine_replay": "algorithmic_projection",
    "mcp_tool_authority_replay": "algorithmic_projection",
    "proof_derived_governed_mutation_authorization": "semantic_validator",
    "belief_state_process_reward_replay": "algorithmic_projection",
    "agent_sandbox_policy_escape_replay": "algorithmic_projection",
    "indirect_prompt_injection_information_flow_policy_replay": "algorithmic_projection",
    "agentic_vulnerability_discovery_patch_proof_replay": "algorithmic_projection",
    "certificate_kernel_execution_lab": "external_subprocess_witness",
    "voice_to_doctrine_self_improvement_loop": "semantic_validator",
}
WORK_LANDING_CONTROL_BODY_MATERIAL_IDS = [
    "work_landing_status_body_import",
    "mission_transaction_landing_preflight_body_import",
    "work_landing_control_tool_body_import",
    "mission_transaction_preflight_tool_body_import",
    "scoped_commit_tool_body_import",
]
TASK_LEDGER_CONTROL_BODY_MATERIAL_IDS = [
    "task_ledger_events_body_import",
    "task_ledger_apply_tool_body_import",
    "task_ledger_priority_body_import",
    "task_ledger_project_tool_body_import",
]
WORK_LEDGER_CONTROL_BODY_MATERIAL_IDS = [
    "work_ledger_tool_body_import",
    "work_ledger_event_body_import",
    "work_ledger_runtime_body_import",
    "work_ledger_standard_body_import",
]
COMMAND_OUTPUT_PROJECTION_BODY_MATERIAL_IDS = [
    "command_output_projection_helper_body_import",
    "command_output_sidecar_helper_body_import",
    "command_output_audit_body_import",
    "command_output_projection_standard_body_import",
]


def _copy_runtime_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "examples", public_root / "examples")
    shutil.copytree(MICROCOSM_ROOT / "src", public_root / "src")
    shutil.copytree(MICROCOSM_ROOT / "receipts/first_wave", public_root / "receipts/first_wave")
    shutil.copytree(MICROCOSM_ROOT / "receipts/preflight", public_root / "receipts/preflight")
    return public_root


def test_runtime_shell_status_is_product_centered() -> None:
    shell = RuntimeShell(MICROCOSM_ROOT)

    status = shell.status()

    assert status["status"] == "pass"
    assert status["adapter_backed_organ_count"] == 42
    assert status["adapter_backed_count_is_product_progress"] is False
    assert status["real_substrate_progress_count"] == 42
    assert status["non_progress_organ_count"] == 0
    assert status["truth_accounting"]["real_runtime_receipt_count"] == 3
    assert status["truth_accounting"]["copied_non_secret_macro_body_count"] == 1
    assert status["truth_accounting"]["source_faithful_refactor_count"] == 23
    assert status["truth_accounting"]["real_import_validation_count"] == 15
    assert status["truth_accounting"]["regression_negative_fixture_count"] == 0
    assert status["truth_accounting"]["adapter_backed_count_is_product_progress"] is False
    assert status["copied_non_secret_macro_body_material_count"] == 37
    assert status["mixed_public_safe_macro_import_assay_status"] == "pass"
    assert status["macro_body_import_floor"]["status"] == "pass"
    assert status["macro_body_import_floor"][
        "public_safe_body_material_counts_by_class"
    ] == {
        "public_macro_pattern_body": 1,
        "public_macro_proof_body": 1,
        "public_macro_receipt_body": 1,
        "public_macro_tool_body": 34,
    }
    assert status["product_path_demoted_organ_count"] == 4
    assert status["fixture_runner_backed_organ_count"] == 0
    assert status["release_authorized"] is False
    assert status["front_door"]["schema_version"] == (
        "microcosm_cold_reader_first_screen_v1"
    )
    assert status["front_door"]["primary_command"] == "microcosm tour <project>"
    assert status["front_door"]["generated_state"]["state_dir"] == ".microcosm"
    assert ".microcosm/graph.json" in status["front_door"]["generated_state"]["refs"]
    assert status["front_door"]["behavior_surfaces"] == {
        "route_state_ref": ".microcosm/routes.json",
        "work_state_ref": ".microcosm/work_items.json",
        "event_log_ref": ".microcosm/events.jsonl",
        "evidence_dir_ref": ".microcosm/evidence/",
        "graph_ref": ".microcosm/graph.json",
        "observatory_command": "microcosm serve <project> --host 127.0.0.1 --port 8765",
    }
    assert status["front_door"]["proof_surface"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert status["front_door"]["authority_ceiling"]["release_authorized"] is False
    assert status["first_screen_proof_lab"]["status"] == "pass"
    assert status["first_screen_proof_lab"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert status["first_screen_proof_lab"]["route_ref"] == PROOF_LAB_ROUTE_REF
    assert status["first_screen_proof_lab"]["receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert status["first_screen_proof_lab"]["route_component_count"] == 9
    assert status["first_screen_proof_lab"]["lean_lake_return_code"] == 0
    assert (
        status["first_screen_proof_lab"]["component_metrics"][
            "retrieval_mean_public_recall"
        ]
        == 1.0
    )
    assert "microcosm init <project>" in status["runtime_surface"]["commands"]
    assert "microcosm compile <project>" in status["runtime_surface"]["commands"]
    assert "microcosm python-lens <project>" in status["runtime_surface"]["commands"]
    assert "microcosm route <project>" in status["runtime_surface"]["commands"]
    assert "microcosm explain <project> <route_id>" in status["runtime_surface"]["commands"]
    assert "microcosm evidence list <project>" in status["runtime_surface"]["commands"]
    assert "microcosm tour <project>" in status["runtime_surface"]["commands"]
    assert "microcosm spine" in status["runtime_surface"]["commands"]
    assert "microcosm authority" in status["runtime_surface"]["commands"]
    assert "microcosm prediction-lens" in status["runtime_surface"]["commands"]
    assert "microcosm market-boundary" in status["runtime_surface"]["commands"]
    assert "microcosm corpus-lens" in status["runtime_surface"]["commands"]
    assert "microcosm trace-lens" in status["runtime_surface"]["commands"]
    assert "microcosm repair-loop" in status["runtime_surface"]["commands"]
    assert "microcosm evidence-cells" in status["runtime_surface"]["commands"]
    assert "microcosm proof-loop-depth" in status["runtime_surface"]["commands"]
    assert "microcosm landing-replay" in status["runtime_surface"]["commands"]
    assert "microcosm view-quality" in status["runtime_surface"]["commands"]
    assert "microcosm projection-safety" in status["runtime_surface"]["commands"]
    assert "microcosm drift-control" in status["runtime_surface"]["commands"]
    assert "microcosm route-cleanup" in status["runtime_surface"]["commands"]
    assert "microcosm projection-import-map" in status["runtime_surface"]["commands"]
    assert "microcosm import-projector" in status["runtime_surface"]["commands"]
    assert "microcosm stripping-guard" in status["runtime_surface"]["commands"]
    assert "microcosm standards-control" in status["runtime_surface"]["commands"]
    assert "microcosm hook-coverage" in status["runtime_surface"]["commands"]
    assert "microcosm replay-gauntlet" in status["runtime_surface"]["commands"]
    assert "microcosm benchmark-lab" in status["runtime_surface"]["commands"]
    assert "microcosm legibility-scorecard" in status["runtime_surface"]["commands"]
    assert "microcosm intake" in status["runtime_surface"]["commands"]
    assert "microcosm reveal" in status["runtime_surface"]["commands"]
    assert (
        "microcosm mathematical-strategy-atlas-hypothesis-scorer run-strategy-bundle"
        not in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm agent-benchmark-integrity-anti-gaming-replay "
        "run-benchmark-integrity-bundle"
        not in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm agent-monitor-redteam-falsification-replay "
        "run-monitor-bundle"
        not in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm agent-sabotage-scheming-monitor-replay run-sabotage-bundle"
        not in status["runtime_surface"]["commands"]
    )
    assert status["runtime_surface"]["demoted_drilldown_commands"] == [
        (
            "microcosm agent-benchmark-integrity-anti-gaming-replay "
            "run-benchmark-integrity-bundle"
        ),
        (
            "microcosm agent-monitor-redteam-falsification-replay "
            "run-monitor-bundle"
        ),
        "microcosm agent-sabotage-scheming-monitor-replay run-sabotage-bundle",
        "microcosm mathematical-strategy-atlas-hypothesis-scorer run-strategy-bundle"
    ]
    assert (
        "microcosm tactic-portfolio-availability-probe run-availability-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm target-shape-tactic-routing-gate run-routing-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm provider-context-recipe-budget-policy run-budget-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm ring2-premise-retrieval-precision-recall-harness "
        "run-precision-recall-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm formal-math-verifier-trace-repair-loop run-loop-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm verifier-lab-kernel run-kernel-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm verifier-lab-execution-spine run-execution-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm formal-evidence-cell-anchor-resolver run-anchor-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm undeclared-library-prior-symbol-classifier run-symbol-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm standards-meta-diagnostics run-diagnostics-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm cold-reader-route-map run-route-map-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm agent-memory-temporal-conflict-replay run-memory-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm sleeper-memory-poisoning-quarantine-replay "
        "run-quarantine-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm mcp-tool-authority-replay "
        "run-tool-authority-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm agent-sandbox-policy-escape-replay "
        "run-sandbox-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm indirect-prompt-injection-information-flow-policy-replay "
        "run-prompt-injection-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm agent-route-observability-runtime "
        "validate-computer-use-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm agent-route-observability-runtime "
        "validate-session-attribution-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm agent-route-observability-runtime "
        "validate-multi-agent-fanin-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm agent-route-observability-runtime "
        "validate-agent-trace-route-repair-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm research-replication-rubric-artifact-replay run-replication-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm world-model-projection-drift-control-room run-drift-control-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert (
        "microcosm spatial-world-model-counterfactual-simulation-replay "
        "run-simulation-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert "microcosm spatial-simulation" in status["runtime_surface"]["commands"]
    assert (
        "microcosm lean-std-premise-index run-index-bundle"
        in status["runtime_surface"]["commands"]
    )
    assert status["runtime_surface"]["receipts_are_drilldown_evidence"] is True
    assert status["posture"] == "executable_research_prototype"
    assert status["kernel_primitive_count"] >= 10


def test_runtime_shell_spine_is_cold_reader_xray() -> None:
    shell = RuntimeShell(MICROCOSM_ROOT)

    spine = shell.spine()

    assert spine["status"] == "pass"
    assert spine["schema_version"] == "microcosm_public_runtime_spine_v1"
    assert spine["cold_reader_goal"] == "legible_under_10_minutes_without_private_macro_context"
    assert spine["surface_counts"]["adapter_backed_organ_count"] == 42
    assert spine["surface_counts"]["adapter_backed_count_is_product_progress"] is False
    assert spine["surface_counts"]["real_substrate_progress_count"] == 42
    assert spine["surface_counts"]["non_progress_organ_count"] == 0
    assert spine["surface_counts"]["real_runtime_receipt_count"] == 3
    assert spine["surface_counts"]["copied_non_secret_macro_body_count"] == 1
    assert spine["surface_counts"]["copied_non_secret_macro_body_material_count"] == 37
    assert spine["surface_counts"]["public_safe_body_material_count"] == 37
    assert spine["surface_counts"]["mixed_public_safe_macro_import_assay_status"] == "pass"
    assert spine["surface_counts"]["source_faithful_refactor_count"] == 23
    assert spine["surface_counts"]["real_import_validation_count"] == 15
    assert spine["surface_counts"]["regression_negative_fixture_count"] == 0
    assert spine["surface_counts"]["blocked_import_debt_count"] == 0
    assert spine["surface_counts"]["secret_exclusion_count"] == 0
    assert spine["surface_counts"]["legacy_adapter_or_synthetic_placeholder_count"] == 0
    assert spine["surface_counts"]["delete_or_demote_candidate_count"] == 0
    assert spine["surface_counts"]["product_path_demoted_organ_count"] == 4
    assert len(spine["accepted_runtime_spine"]) == 42
    assert len(spine["real_substrate_progress_spine"]) == 42
    assert len(spine["non_progress_runtime_spine"]) == 0
    assert spine["surface_counts"]["evidence_class_count"] == 4
    assert spine["evidence_class_registry"]["fail_closed_no_default"] is True
    assert spine["evidence_class_registry"]["organ_evidence_class_count"] == 46
    assert spine["truth_accounting"]["adapter_backed_count_is_product_progress"] is False
    assert spine["truth_accounting"]["real_substrate_progress_count"] == 42
    assert spine["truth_accounting"]["non_progress_organ_count"] == 0
    assert spine["macro_body_import_floor"]["status"] == "pass"
    assert spine["macro_body_import_floor"][
        "copied_non_secret_macro_body_material_count"
    ] == 37
    assert spine["macro_body_import_floor"]["mixed_public_safe_macro_import_assay"][
        "non_lean_tool_body_material_ids"
    ] == [
        "work_landing_tool_body_import",
        "agent_execution_trace_body_import",
        "agent_trace_route_repair_body_import",
        "agent_observability_store_body_import",
        "agent_session_attribution_body_import",
        "continuation_packet_body_import",
        "bridge_resume_body_import",
        "controller_heartbeat_body_import",
        "finance_event_keys_body_import",
        "finance_admit_forecasts_body_import",
        "finance_resolve_forecasts_body_import",
        "finance_eval_replay_body_import",
        "finance_historical_replay_body_import",
        "finance_calibrate_forecast_probabilities_body_import",
        "finance_variant_registry_body_import",
        "finance_compare_variants_body_import",
        "finance_build_eval_operating_picture_body_import",
        *WORK_LANDING_CONTROL_BODY_MATERIAL_IDS,
        *TASK_LEDGER_CONTROL_BODY_MATERIAL_IDS,
        *WORK_LEDGER_CONTROL_BODY_MATERIAL_IDS,
        *COMMAND_OUTPUT_PROJECTION_BODY_MATERIAL_IDS,
    ]
    assert spine["macro_body_import_floor"]["mixed_public_safe_macro_import_assay"][
        "proof_body_material_ids"
    ] == ["lean_certificate_kernel_body_import"]
    assert spine["first_screen_proof_lab"]["status"] == "pass"
    assert spine["first_screen_proof_lab"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert spine["first_screen_proof_lab"]["receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert spine["evidence_class_registry"]["unclassified_organs"] == []
    assert sum(spine["evidence_class_counts"].values()) == 42
    rows_by_id = {row["organ_id"]: row for row in spine["accepted_runtime_spine"]}
    assert {organ_id: row["evidence_class"] for organ_id, row in rows_by_id.items()} == (
        EXPECTED_ORGAN_EVIDENCE_CLASSES
    )
    assert spine["evidence_class_counts"] == {
        "semantic_validator": 15,
        "algorithmic_projection": 23,
        "external_subprocess_witness": 3,
        "verified_macro_body_import": 1,
    }
    assert rows_by_id["proof_diagnostic_evidence_spine"]["evidence_class"] == (
        "algorithmic_projection"
    )
    assert rows_by_id["durable_agent_work_landing_replay"]["evidence_class"] == (
        "semantic_validator"
    )
    assert rows_by_id["proof_derived_governed_mutation_authorization"]["evidence_class"] == (
        "semantic_validator"
    )
    assert rows_by_id["world_model_projection_drift_control_room"]["evidence_class"] == (
        "semantic_validator"
    )
    assert (
        rows_by_id["world_model_projection_drift_control_room"][
            "counts_as_real_substrate_progress"
        ]
        is True
    )
    assert rows_by_id["world_model_projection_drift_control_room"][
        "truth_accounting_bucket"
    ] == "real_import_validation"
    assert rows_by_id["spatial_world_model_counterfactual_simulation_replay"][
        "evidence_class"
    ] == "semantic_validator"
    assert (
        rows_by_id["spatial_world_model_counterfactual_simulation_replay"][
            "counts_as_real_substrate_progress"
        ]
        is True
    )
    assert rows_by_id["spatial_world_model_counterfactual_simulation_replay"][
        "truth_accounting_bucket"
    ] == "real_import_validation"
    assert rows_by_id["mechanistic_interpretability_circuit_attribution_replay"][
        "evidence_class"
    ] == "semantic_validator"
    assert (
        rows_by_id["mechanistic_interpretability_circuit_attribution_replay"][
            "counts_as_real_substrate_progress"
        ]
        is True
    )
    assert rows_by_id["mechanistic_interpretability_circuit_attribution_replay"][
        "truth_accounting_bucket"
    ] == "real_import_validation"
    assert rows_by_id["research_replication_rubric_artifact_replay"]["evidence_class"] == (
        "algorithmic_projection"
    )
    assert (
        rows_by_id["research_replication_rubric_artifact_replay"][
            "counts_as_real_substrate_progress"
        ]
        is True
    )
    assert rows_by_id["research_replication_rubric_artifact_replay"][
        "truth_accounting_bucket"
    ] == "source_faithful_refactor"
    assert rows_by_id["pattern_binding_contract"]["truth_accounting_bucket"] == (
        "real_import_validation"
    )
    assert rows_by_id["formal_math_lean_proof_witness"]["truth_accounting_bucket"] == (
        "real_runtime_receipt"
    )
    assert rows_by_id["proof_diagnostic_evidence_spine"]["truth_accounting_bucket"] == (
        "source_faithful_refactor"
    )
    assert rows_by_id["agentic_vulnerability_discovery_patch_proof_replay"][
        "evidence_class"
    ] == "algorithmic_projection"
    assert (
        rows_by_id["agentic_vulnerability_discovery_patch_proof_replay"][
            "counts_as_real_substrate_progress"
        ]
        is True
    )
    assert rows_by_id["agentic_vulnerability_discovery_patch_proof_replay"][
        "truth_accounting_bucket"
    ] == "source_faithful_refactor"
    assert spine["demoted_drilldown_surfaces"] == [
        {
            "organ_id": "mathematical_strategy_atlas_hypothesis_scorer",
            "runtime_mode": "drilldown_only",
            "product_path_role": "drilldown_regression_not_runtime_spine",
            "demotion_reason": (
                "strategy-atlas overlap projection remains runnable as a regression "
                "drilldown, but scoring/projection rows are not product-spine substrate."
            ),
            "input_mode": "exported_mathematical_strategy_atlas_bundle",
            "example_ref": (
                "examples/mathematical_strategy_atlas_hypothesis_scorer/"
                "exported_mathematical_strategy_atlas_bundle"
            ),
            "evidence_class": "algorithmic_projection",
            "claim_ceiling": "projection mechanics only, not domain correctness",
        },
        {
            "organ_id": "agent_benchmark_integrity_anti_gaming_replay",
            "runtime_mode": "drilldown_only",
            "product_path_role": "drilldown_regression_not_runtime_spine",
            "demotion_reason": (
                "benchmark-integrity replay remains runnable as a body-free regression drilldown, "
                "but fixture-supplied benchmark verdict rows are not product-spine substrate or benchmark-performance evidence."
            ),
            "input_mode": "exported_benchmark_integrity_bundle",
            "example_ref": (
                "examples/agent_benchmark_integrity_anti_gaming_replay/"
                "exported_benchmark_integrity_bundle"
            ),
            "evidence_class": "fixture_echo_smoke",
            "claim_ceiling": (
                "smoke/projection demo only, not behavioral or safety validation"
            ),
        },
        {
            "organ_id": "agent_monitor_redteam_falsification_replay",
            "runtime_mode": "drilldown_only",
            "product_path_role": "drilldown_regression_not_runtime_spine",
            "demotion_reason": (
                "monitor-redteam replay remains runnable as a regression drilldown, "
                "but synthetic monitor verdict rows and body-omission refs are not product-spine substrate."
            ),
            "input_mode": "exported_monitor_redteam_bundle",
            "example_ref": (
                "examples/agent_monitor_redteam_falsification_replay/"
                "exported_monitor_redteam_bundle"
            ),
            "evidence_class": "fixture_echo_smoke",
            "claim_ceiling": (
                "smoke/projection demo only, not behavioral or safety validation"
            ),
        },
        {
            "organ_id": "agent_sabotage_scheming_monitor_replay",
            "runtime_mode": "drilldown_only",
            "product_path_role": "drilldown_regression_not_runtime_spine",
            "demotion_reason": (
                "sabotage-monitor replay remains runnable as a regression drilldown, "
                "but synthetic scheming episodes, monitor scores, and body-free "
                "regression fixture refs are not product-spine substrate."
            ),
            "input_mode": "exported_sabotage_monitor_bundle",
            "example_ref": (
                "examples/agent_sabotage_scheming_monitor_replay/"
                "exported_sabotage_monitor_bundle"
            ),
            "evidence_class": "fixture_echo_smoke",
            "claim_ceiling": (
                "smoke/projection demo only, not behavioral or safety validation"
            ),
        }
    ]
    assert all(row["evidence_strength_disclosed"] is True for row in spine["accepted_runtime_spine"])
    assert spine["evidence_policy"]["accepted_status_is_not_evidence_strength"] is True
    assert spine["evidence_policy"]["unclassified_organs_block_authority_projection"] is True
    assert [step["step_id"] for step in spine["first_run_path"]] == [
        "run_ten_minute_tour",
        "compile_project",
        "inspect_python_lens",
        "inspect_route",
        "open_observatory",
        "inspect_public_spine",
        "inspect_authority_map",
        "inspect_prediction_lens",
        "inspect_market_prediction_boundary",
        "inspect_corpus_lens",
        "inspect_verifier_trace_repair_lens",
        "inspect_verifier_repair_loop",
        "inspect_formal_evidence_cells",
        "inspect_proof_loop_depth",
        "inspect_verifier_lab_kernel",
        "inspect_verifier_lab_execution_spine",
        "inspect_work_landing_replay",
        "inspect_durable_agent_work_landing_replay",
        "inspect_research_replication_rubric_artifact_replay",
        "inspect_view_quality_action_map",
        "inspect_projection_safety_audit",
        "inspect_projection_drift_control",
        "inspect_world_model_projection_drift_control_room",
        "inspect_spatial_world_model_counterfactual_simulation_replay",
        "inspect_mechanistic_interpretability_circuit_attribution_replay",
        "inspect_route_cleanup_contract",
        "inspect_projection_import_map",
        "inspect_import_projector_contract",
        "inspect_compression_profile_option_surface",
        "inspect_public_private_stripping_guard",
        "inspect_standards_control",
        "inspect_hook_intervention_coverage",
        "inspect_agent_reliability_replay_gauntlet",
        "inspect_agent_memory_temporal_conflict_replay",
        "inspect_sleeper_memory_poisoning_quarantine_replay",
        "inspect_mcp_tool_authority_replay",
        "inspect_proof_derived_governed_mutation_authorization",
        "inspect_belief_state_process_reward_replay",
        "inspect_agent_sandbox_policy_escape_replay",
        "inspect_indirect_prompt_injection_information_flow_policy_replay",
        "inspect_agentic_vulnerability_discovery_patch_proof_replay",
        "inspect_certificate_kernel_execution_lab",
        "inspect_repository_benchmark_transaction_lab",
        "inspect_public_legibility_scorecard",
        "open_import_bridge",
        "open_reveal_board",
        "inspect_cold_reader_route_map",
    ]
    assert spine["first_run_path"][0]["command"] == "microcosm tour <project>"
    assert spine["first_run_path"][2]["command"] == "microcosm python-lens <project>"
    assert spine["first_run_path"][5]["command"] == "microcosm spine"
    assert spine["first_run_path"][6]["command"] == "microcosm authority"
    assert spine["first_run_path"][7]["command"] == "microcosm prediction-lens"
    assert spine["first_run_path"][8]["command"] == "microcosm market-boundary"
    assert spine["first_run_path"][9]["command"] == "microcosm corpus-lens"
    assert spine["first_run_path"][10]["command"] == "microcosm trace-lens"
    assert spine["first_run_path"][11]["command"] == "microcosm repair-loop"
    assert spine["first_run_path"][12]["command"] == "microcosm evidence-cells"
    assert spine["first_run_path"][13]["command"] == "microcosm proof-loop-depth"
    assert spine["first_run_path"][14]["command"] == PROOF_LAB_FIRST_SCREEN_COMMAND
    assert spine["first_run_path"][14]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert spine["first_run_path"][14]["route_ref"] == PROOF_LAB_ROUTE_REF
    assert spine["first_run_path"][14]["receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert spine["first_run_path"][14]["route_component_count"] == 9
    assert (
        spine["first_run_path"][14]["component_metrics"][
            "ring2_mean_recall_at_k"
        ]
        == 0.9
    )
    assert spine["first_run_path"][15]["command"] == VERIFIER_EXECUTION_LENS_COMMAND
    assert spine["first_run_path"][16]["command"] == "microcosm landing-replay"
    assert spine["first_run_path"][17]["command"].startswith(
        "microcosm durable-agent-work-landing-replay"
    )
    assert spine["first_run_path"][18]["command"].startswith(
        "microcosm research-replication-rubric-artifact-replay"
    )
    assert spine["first_run_path"][19]["command"] == "microcosm view-quality"
    assert spine["first_run_path"][20]["command"] == "microcosm projection-safety"
    assert spine["first_run_path"][21]["command"] == "microcosm drift-control"
    assert spine["first_run_path"][22]["command"].startswith(
        "microcosm world-model-projection-drift-control-room"
    )
    assert spine["first_run_path"][23]["command"].startswith(
        "microcosm spatial-world-model-counterfactual-simulation-replay"
    )
    assert spine["first_run_path"][24]["command"].startswith(
        "microcosm mechanistic-interpretability-circuit-attribution-replay"
    )
    assert spine["first_run_path"][25]["command"] == "microcosm route-cleanup"
    assert spine["first_run_path"][26]["command"] == "microcosm projection-import-map"
    assert spine["first_run_path"][27]["command"] == "microcosm import-projector"
    assert spine["first_run_path"][28]["command"] == "microcosm option-surface-lens"
    assert spine["first_run_path"][29]["command"] == "microcosm stripping-guard"
    assert spine["first_run_path"][30]["command"] == "microcosm standards-control"
    assert spine["first_run_path"][31]["command"] == "microcosm hook-coverage"
    assert spine["first_run_path"][32]["command"] == "microcosm replay-gauntlet"
    assert spine["first_run_path"][33]["command"].startswith(
        "microcosm agent-memory-temporal-conflict-replay"
    )
    assert spine["first_run_path"][34]["command"].startswith(
        "microcosm sleeper-memory-poisoning-quarantine-replay"
    )
    assert spine["first_run_path"][35]["command"].startswith(
        "microcosm mcp-tool-authority-replay"
    )
    assert spine["first_run_path"][36]["command"].startswith(
        "microcosm proof-derived-governed-mutation-authorization"
    )
    assert spine["first_run_path"][37]["command"].startswith(
        "microcosm belief-state-process-reward-replay"
    )
    assert spine["first_run_path"][38]["command"].startswith(
        "microcosm agent-sandbox-policy-escape-replay"
    )
    assert spine["first_run_path"][39]["command"].startswith(
        "microcosm indirect-prompt-injection-information-flow-policy-replay"
    )
    assert spine["first_run_path"][40]["command"].startswith(
        "microcosm agentic-vulnerability-discovery-patch-proof-replay"
    )
    assert spine["first_run_path"][41]["command"].startswith(
        "microcosm certificate-kernel-execution-lab"
    )
    assert spine["first_run_path"][42]["command"] == "microcosm benchmark-lab"
    assert spine["first_run_path"][43]["command"] == "microcosm legibility-scorecard"
    assert spine["first_run_path"][44]["command"] == "microcosm intake"
    assert spine["first_run_path"][46]["command"] == "microcosm cold-reader-route-map run-route-map-bundle"
    assert spine["evidence_policy"]["body_in_receipt_by_default"] is False
    assert spine["evidence_policy"]["real_runtime_receipts_are_product_evidence"] is True
    assert spine["evidence_policy"]["copied_non_secret_macro_bodies_require_provenance"] is True
    assert spine["evidence_policy"]["source_faithful_refactors_are_product_evidence"] is True
    assert spine["evidence_policy"]["synthetic_receipts_are_product_evidence"] is False
    assert spine["evidence_policy"]["synthetic_fixtures_allowed_only_as"] == [
        "regression_harness",
        "negative_case",
        "blocked_import_debt",
    ]
    assert spine["evidence_policy"]["blocked_import_debt_must_name_replacement_target"] is True
    assert spine["evidence_policy"]["secret_exclusion_scan_is_receipt_owner"] is True
    assert spine["authority_ceiling"]["release_authorized"] is False
    assert spine["authority_ceiling"]["trading_or_financial_advice_authorized"] is False
    assert all(row["generated_receipt_count"] >= 1 for row in spine["accepted_runtime_spine"])
    encoded = json.dumps(spine, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_blocks_unclassified_organs(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    registry_path = public_root / "core/organ_evidence_classes.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["organ_evidence_classes"] = [
        row
        for row in registry["organ_evidence_classes"]
        if row["organ_id"] != "pattern_binding_contract"
    ]
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    shell = RuntimeShell(public_root)

    with pytest.raises(ValueError, match="coverage defect"):
        shell.spine()


def test_runtime_shell_workingness_map_tracks_failure_modes_without_scoring() -> None:
    shell = RuntimeShell(MICROCOSM_ROOT)

    workingness = shell.workingness_map()

    assert workingness["schema_version"] == "microcosm_workingness_failure_map_v1"
    assert workingness["status"] == "pass"
    assert workingness["completeness_status"] == "partial_failure_modes"
    assert workingness["command"] == "microcosm workingness"
    assert workingness["endpoint"] == "/workingness"
    assert workingness["map_policy"]["not_a_scorecard"] is True
    assert workingness["map_policy"]["failure_modes_come_from_owning_standards"] is True
    assert workingness["authority_ceiling"]["score_based_progress_authority"] is False
    assert workingness["surface_counts"]["mapped_organ_count"] == 46
    assert workingness["surface_counts"]["adapter_backed_organ_count"] == 42
    assert workingness["surface_counts"]["demoted_drilldown_count"] == 4
    assert workingness["surface_counts"]["missing_standard_count"] >= 1
    assert workingness["surface_counts"]["missing_failure_modes_count"] >= 1
    assert workingness["surface_counts"]["rows_with_failure_modes"] >= 30

    rows_by_id = {
        row["thing_id"]: row for row in workingness["thing_failure_map"]
    }
    verifier = rows_by_id["verifier_lab_kernel"]
    assert verifier["workingness_state"] == "evidence_backed_runtime_spine"
    assert verifier["needs_to_work"]["standard_ref"] == (
        "standards/std_microcosm_verifier_lab_kernel.json"
    )
    assert "provider hypothesis claims proof authority" in verifier["known_failure_modes"]
    assert verifier["evaluation_comparison"]["accepted_status_is_not_evidence_strength"] is True
    assert verifier["observed_workingness"]["evidence_class"] == "semantic_validator"

    monitor = rows_by_id["agent_monitor_redteam_falsification_replay"]
    assert monitor["workingness_state"] == "demoted_regression_drilldown"
    assert monitor["observed_workingness"]["evidence_class"] == "fixture_echo_smoke"
    assert monitor["evaluation_comparison"]["gap_class"] == (
        "kept_out_of_product_path_until_evidence_strengthens"
    )
    assert any(
        target["target_id"] == "upgrade_or_keep_demoted"
        for target in monitor["future_work_targets"]
    )

    encoded = json.dumps(workingness, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_authority_map_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    authority = shell.authority()

    assert authority["status"] == "pass"
    assert authority["schema_version"] == "microcosm_public_authority_map_v2"
    assert authority["command"] == "microcosm authority"
    assert authority["endpoint"] == "/authority"
    assert authority["release_authorized"] is False
    assert authority["projection_not_authority"] is True
    assert authority["source_open_body_policy"] == (
        "source_open_except_secret_credential_provider_account_session_and_live_access_payloads"
    )
    assert authority["unsafe_payload_bodies_exported"] is False
    assert authority["payload_boundary"]["source_open_default"] is True
    assert authority["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert authority["payload_boundary"]["public_refs_are_drilldowns_not_replacements"] is True
    assert authority["authority_ceiling"] == {
        "release_authorized": False,
        "hosted_public_authorized": False,
        "publication_authorized": False,
        "provider_calls_authorized": False,
        "source_mutation_authorized": False,
        "live_task_ledger_mutation_authorized": False,
        "trading_or_financial_advice_authorized": False,
        "private_data_equivalence_claim": False,
        "whole_system_correctness_claim": False,
        "formal_math_general_proof_authority": False,
        "lean_lake_execution_authorized": False,
        "live_git_mutation_authorized": False,
        "broad_checkpoint_authorized": False,
        "live_browser_control_authorized": False,
        "private_screenshot_paths_exported": False,
        "reader_success_guarantee": False,
    }
    assert authority["surface_counts"]["organ_authority_count"] == 42
    assert authority["surface_counts"]["surface_authority_count"] == 45
    assert authority["surface_counts"]["organ_evidence_class_count"] == 4
    assert authority["surface_counts"]["adapter_backed_count_is_product_progress"] is False
    assert authority["surface_counts"]["real_substrate_progress_count"] == 42
    assert authority["surface_counts"]["non_progress_organ_count"] == 0
    assert authority["surface_counts"]["regression_negative_fixture_count"] == 0
    assert authority["surface_counts"]["hard_boundary_count"] == 6
    assert authority["surface_counts"]["safe_local_exception_count"] == 3
    assert authority["truth_accounting"]["real_substrate_progress_count"] == 42
    assert authority["truth_accounting"]["copied_non_secret_macro_body_count"] == 1
    assert authority["truth_accounting"]["regression_negative_fixture_count"] == 0
    assert authority["truth_accounting"]["adapter_backed_count_is_product_progress"] is False
    assert (
        authority["surface_counts"]["copied_non_secret_macro_body_material_count"] == 37
    )
    assert (
        authority["surface_counts"]["mixed_public_safe_macro_import_assay_status"]
        == "pass"
    )
    assert authority["evidence_class_registry"]["fail_closed_no_default"] is True
    assert authority["evidence_class_registry"]["organ_evidence_class_count"] == 46
    assert authority["evidence_class_registry"]["unclassified_organs"] == []
    assert authority["evidence_class_counts"] == {
        "semantic_validator": 15,
        "algorithmic_projection": 23,
        "external_subprocess_witness": 3,
        "verified_macro_body_import": 1,
    }
    organ_authority_by_id = {row["organ_id"]: row for row in authority["organ_authority"]}
    assert {organ_id: row["evidence_class"] for organ_id, row in organ_authority_by_id.items()} == (
        EXPECTED_ORGAN_EVIDENCE_CLASSES
    )
    assert "agent_sabotage_scheming_monitor_replay" not in organ_authority_by_id
    assert (
        organ_authority_by_id["formal_math_lean_proof_witness"]["verdict_source"]
        == "subprocess_or_tool_witness"
    )
    assert (
        organ_authority_by_id["proof_diagnostic_evidence_spine"]["evidence_class"]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["durable_agent_work_landing_replay"]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["proof_derived_governed_mutation_authorization"][
            "evidence_class"
        ]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["world_model_projection_drift_control_room"]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["world_model_projection_drift_control_room"][
            "counts_as_real_substrate_progress"
        ]
        is True
    )
    assert organ_authority_by_id["world_model_projection_drift_control_room"][
        "truth_accounting_bucket"
    ] == "real_import_validation"
    assert (
        organ_authority_by_id[
            "mechanistic_interpretability_circuit_attribution_replay"
        ]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id[
            "mechanistic_interpretability_circuit_attribution_replay"
        ]["truth_accounting_bucket"]
        == "real_import_validation"
    )
    assert (
        organ_authority_by_id["research_replication_rubric_artifact_replay"]["evidence_class"]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["research_replication_rubric_artifact_replay"][
            "counts_as_real_substrate_progress"
        ]
        is True
    )
    assert organ_authority_by_id["research_replication_rubric_artifact_replay"][
        "truth_accounting_bucket"
    ] == "source_faithful_refactor"
    assert organ_authority_by_id["pattern_binding_contract"]["truth_accounting_bucket"] == (
        "real_import_validation"
    )
    assert all(row["evidence_strength_disclosed"] is True for row in authority["organ_authority"])
    assert any(row["surface_id"] == "project_python_lens" for row in authority["surface_authority"])
    assert any(row["surface_id"] == "public_authority_map" for row in authority["surface_authority"])
    assert any(row["surface_id"] == "public_ten_minute_tour" for row in authority["surface_authority"])
    assert any(
        row["surface_id"] == "public_market_prediction_evidence_boundary_lens"
        and row["endpoint"] == "/market-boundary"
        and row["trading_or_financial_advice_authorized"] is False
        and row["private_portfolio_exported"] is False
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_corpus_readiness_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_verifier_trace_repair_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_verifier_repair_loop_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_formal_evidence_cell_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_proof_loop_depth_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_work_landing_replay_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_view_quality_action_map_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_projection_safety_audit_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_projection_drift_control_lens"
        and row["endpoint"] == "/drift-control"
        and row["source_authority_claim"] is False
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_route_cleanup_contract_lens"
        and row["endpoint"] == "/route-cleanup"
        and row["route_deletion_authorized"] is False
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_projection_import_map_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_import_projector_contract_lens"
        and row["endpoint"] == "/import-projector"
        and row["automated_import_execution_authorized"] is False
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_compression_profile_option_surface_lens"
        and row["endpoint"] == "/option-surface-lens"
        and row["profile_switch_execution_authorized"] is False
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_stripping_guard_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_standards_control_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_cold_reader_legibility_scorecard_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_hook_intervention_coverage_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_agent_reliability_replay_gauntlet_lens"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_agent_sabotage_scheming_monitor_replay_lens"
        and row["runtime_mode"] == "drilldown_only"
        and row["product_path_role"] == "drilldown_regression_not_runtime_spine"
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"]
        == "public_proof_derived_governed_mutation_authorization_lens"
        and row["live_cloud_account_authorized"] is False
        and row["standing_credentials_authorized"] is False
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_verifier_lab_kernel_lens"
        and row["provider_hypothesis_proof_authority"] is False
        and row["oracle_forward_contamination_authorized"] is False
        and row["route_id"] == "formal_prover_context_strategy_gate"
        and row["receipt_ref"] == PROOF_LAB_RECEIPT_REF
        and row["route_component_count"] == 9
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_verifier_lab_execution_spine_lens"
        and row["bounded_public_external_witness_only"] is True
        and row["proof_correctness_claim"] is False
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_belief_state_process_reward_replay_lens"
        and row["hidden_reasoning_export_authorized"] is False
        and row["live_rl_training_authorized"] is False
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_indirect_prompt_injection_information_flow_policy_replay_lens"
        and row["live_tool_call_authorized"] is False
        and row["raw_prompt_body_export_authorized"] is False
        for row in authority["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_repository_benchmark_transaction_lab_lens"
        for row in authority["surface_authority"]
    )
    assert authority["organ_authority"][0]["release_authorized"] is False
    assert authority["organ_authority"][0]["evidence_class"] == "semantic_validator"
    assert all(row["allowed"] is False for row in authority["hard_boundaries"])
    assert {row["exception_id"] for row in authority["safe_local_exceptions"]} == {
        "project_local_state_writes",
        "public_receipt_writes",
        "bounded_public_lean_witness",
    }
    assert (public_root / authority["authority_map_ref"]).is_file()
    encoded = json.dumps(authority, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_authority_map_uses_payload_boundary(tmp_path: Path) -> None:
    test_runtime_shell_authority_map_is_public_safe(tmp_path)


def test_runtime_shell_tour_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    tour = shell.tour("examples/runtime_shell/demo_project")

    assert tour["status"] == "pass"
    assert tour["schema_version"] == "microcosm_public_ten_minute_tour_v1"
    assert tour["command"] == "microcosm tour <project>"
    assert tour["endpoint"] == "/tour"
    assert tour["time_budget_minutes"] == 10
    assert tour["front_door_status"]["status_scope"] == (
        "required_behavioral_first_screen_surfaces"
    )
    assert tour["front_door_status"]["blocking_surface_ids"] == []
    assert tour["front_door_status"]["drilldown_blocked_surface_ids"] == [
        "authority",
        "intake",
    ]
    assert tour["compile_summary"]["headline"] == "repo -> .microcosm"
    assert tour["compile_summary"]["source_files_mutated"] is False
    assert tour["snapshot_policy"] == {
        "lifecycle": "tracked_public_snapshot_refreshed_intentionally",
        "runtime_invocation_can_write_receipt": True,
        "incidental_validator_reads_write_receipt": False,
        "test_runs_should_use_temp_public_root": True,
        "volatile_fields": [
            "created_at",
            "project_ref",
            "compile_summary.event_count",
            "compile_summary.evidence_count",
            "compile_summary.file_count",
        ],
        "stable_truth_fields": [
            "first_screen",
            "runtime_summary.organ_count",
            "runtime_summary.surface_authority_count",
            "authority_ceiling",
            "safe_to_show",
            "evidence_refs",
        ],
    }
    assert tour["surface_statuses"] == {
        "authority": "blocked",
        "benchmark_lab": "pass",
        "compile": "pass",
        "corpus": "pass",
        "circuit_attribution": "pass",
        "evidence_cells": "pass",
        "hook_coverage": "pass",
        "import_projector": "pass",
        "intake": "blocked",
        "landing_replay": "pass",
        "legibility_scorecard": "pass",
        "market_boundary": "pass",
        "option_surface": "pass",
        "projection_import_map": "pass",
        "projection_drift": "pass",
        "projection_safety": "pass",
        "proof_loop_depth": "pass",
        "proof_lab": "pass",
        "prediction": "pass",
        "route_cleanup": "pass",
        "replay_gauntlet": "pass",
        "repair_loop": "pass",
        "reveal": "pass",
        "spine": "pass",
        "standards_control": "pass",
        "stripping_guard": "pass",
        "trace": "pass",
        "verifier_lab_execution_spine": "pass",
        "view_quality": "pass",
    }
    assert tour["first_screen"]["schema_version"] == (
        "microcosm_cold_reader_first_screen_v1"
    )
    assert tour["first_screen"]["status"] == "pass"
    assert tour["first_screen"]["primary_command"] == "microcosm tour <project>"
    assert [row["step_id"] for row in tour["first_screen"]["minimal_command_path"]] == [
        "compile_project",
        "inspect_first_screen",
        "inspect_python_routes",
        "inspect_route_causal_chain",
        "open_observatory",
        "run_first_screen_proof_lab",
        "drill_receipts_only_after_behavior",
    ]
    assert tour["first_screen"]["generated_state"]["state_dir"] == ".microcosm"
    assert ".microcosm/catalog.json" in tour["first_screen"]["generated_state"]["refs"]
    assert ".microcosm/evidence/" in tour["first_screen"]["generated_state"]["refs"]
    assert tour["first_screen"]["behavior_surfaces"]["route_state_ref"] == (
        ".microcosm/routes.json"
    )
    assert tour["first_screen"]["behavior_surfaces"]["observatory_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert tour["first_screen"]["proof_surface"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert tour["first_screen"]["safe_to_show"]["receipt_refs_visible_after_behavior"] is True
    assert tour["first_screen"]["authority_ceiling"]["release_authorized"] is False
    assert [row["card_id"] for row in tour["route_cards"]] == [
        "compile",
        "runtime_spine",
        "authority",
        "prediction_and_corpus",
        "verifier_lab_kernel",
        "verifier_lab_execution_spine",
        "intake_and_reveal",
        "evidence_drilldown",
    ]
    assert "/tour" in tour["endpoint_path"]
    assert "/trace" in tour["endpoint_path"]
    assert "/repair-loop" in tour["endpoint_path"]
    assert "/evidence-cells" in tour["endpoint_path"]
    assert "/proof-loop-depth" in tour["endpoint_path"]
    assert "/verifier-lab-execution-spine" in tour["endpoint_path"]
    assert "/verifier-lab-kernel" in tour["endpoint_path"]
    assert "/landing-replay" in tour["endpoint_path"]
    assert "/view-quality" in tour["endpoint_path"]
    assert "/projection-safety" in tour["endpoint_path"]
    assert "/market-boundary" in tour["endpoint_path"]
    assert "/drift-control" in tour["endpoint_path"]
    assert "/circuit-attribution" in tour["endpoint_path"]
    assert "/route-cleanup" in tour["endpoint_path"]
    assert "/projection-import-map" in tour["endpoint_path"]
    assert "/import-projector" in tour["endpoint_path"]
    assert "/option-surface-lens" in tour["endpoint_path"]
    assert "/stripping-guard" in tour["endpoint_path"]
    assert "/standards-control" in tour["endpoint_path"]
    assert "/hook-coverage" in tour["endpoint_path"]
    assert "/replay-gauntlet" in tour["endpoint_path"]
    assert "/benchmark-lab" in tour["endpoint_path"]
    assert "/legibility-scorecard" in tour["endpoint_path"]
    assert "microcosm trace-lens" in tour["command_path"]
    assert "microcosm repair-loop" in tour["command_path"]
    assert "microcosm evidence-cells" in tour["command_path"]
    assert "microcosm proof-loop-depth" in tour["command_path"]
    assert VERIFIER_EXECUTION_LENS_COMMAND in tour["command_path"]
    assert "microcosm landing-replay" in tour["command_path"]
    assert "microcosm view-quality" in tour["command_path"]
    assert "microcosm projection-safety" in tour["command_path"]
    assert "microcosm market-boundary" in tour["command_path"]
    assert "microcosm drift-control" in tour["command_path"]
    assert "microcosm circuit-attribution" in tour["command_path"]
    assert "microcosm route-cleanup" in tour["command_path"]
    assert "microcosm projection-import-map" in tour["command_path"]
    assert "microcosm import-projector" in tour["command_path"]
    assert "microcosm option-surface-lens" in tour["command_path"]
    assert "microcosm stripping-guard" in tour["command_path"]
    assert "microcosm standards-control" in tour["command_path"]
    assert "microcosm hook-coverage" in tour["command_path"]
    assert "microcosm replay-gauntlet" in tour["command_path"]
    assert "microcosm benchmark-lab" in tour["command_path"]
    assert "microcosm legibility-scorecard" in tour["command_path"]
    assert (
        tour["route_cards"][3]["endpoint"]
        == "/prediction + /corpus + /trace + /repair-loop + /evidence-cells + /proof-loop-depth + /landing-replay + /view-quality + /projection-safety + /market-boundary + /drift-control + /spatial-simulation + /circuit-attribution + /route-cleanup + /projection-import-map + /import-projector + /option-surface-lens + /stripping-guard + /standards-control + /hook-coverage + /replay-gauntlet + /benchmark-lab + /legibility-scorecard"
    )
    assert tour["runtime_summary"]["projection_drift_row_count"] == 8
    assert tour["runtime_summary"]["projection_drift_repair_route_count"] == 8
    assert tour["runtime_summary"]["route_cleanup_row_count"] == 8
    assert tour["runtime_summary"]["route_cleanup_negative_case_count"] == 8
    assert tour["runtime_summary"]["import_projector_row_count"] == 9
    assert tour["runtime_summary"]["import_projector_stage_count"] == 6
    assert tour["runtime_summary"]["option_surface_row_count"] == 6
    assert tour["runtime_summary"]["option_surface_stage_count"] == 6
    assert tour["runtime_summary"]["proof_loop_gate_count"] == 12
    assert tour["runtime_summary"]["proof_loop_negative_case_count"] == 10
    assert tour["runtime_summary"]["verifier_lab_execution_transition_count"] == 6
    assert (
        tour["runtime_summary"]["verifier_lab_execution_cp2_downstream_effect_count"]
        == 1
    )
    assert tour["runtime_summary"]["stripping_guard_row_count"] == 8
    assert tour["runtime_summary"]["stripping_guard_negative_case_count"] == 8
    assert tour["runtime_summary"]["standards_control_row_count"] == 8
    assert tour["runtime_summary"]["standards_control_negative_case_count"] == 8
    assert "microcosm evidence inspect <receipt>" in tour["command_path"]
    assert tour["authority_ceiling"]["release_authorized"] is False
    assert tour["safe_to_show"]["body_in_receipt"] is False
    assert tour["safe_to_show"]["receipt_refs_only_until_drilldown"] is True
    assert tour["safe_to_show"]["secret_or_account_bound_material_excluded"] is True
    assert tour["safe_to_show"]["real_substrate_receipts_required"] is True
    assert tour["safe_to_show"]["synthetic_receipts_are_not_product_evidence"] is True
    assert tour["body_in_receipt"] is False
    assert (public_root / tour["tour_ref"]).is_file()
    encoded = json.dumps(tour, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_trace_lens_uses_payload_boundary(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.trace_lens()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_verifier_trace_repair_lens_v1"
    assert lens["command"] == "microcosm trace-lens"
    assert lens["endpoint"] == "/trace"
    assert lens["lens_id"] == "public_verifier_trace_repair_lens"
    assert [row["verifier_failure_class"] for row in lens["trace_rows"]] == [
        "MISSING_PREMISE",
        "TACTIC_UNAVAILABLE",
        "INVALID_PROOF_BODY",
        "NONE_AFTER_METADATA_REPAIR",
    ]
    assert set(lens["negative_case_ids"]) == {
        "proof_body_leakage",
        "oracle_needed_premise_id_public",
        "trace_grade_without_trace",
        "repair_without_verifier_class",
        "promotion_without_cold_rerun",
        "provider_payload_leakage",
        "human_approval_as_proof_correctness",
    }
    assert lens["repair_policy"]["cold_rerun_required_before_promotion"] is True
    assert (
        lens["repair_policy"][
            "proof_bodies_and_oracle_ids_excluded_by_payload_boundary"
        ]
        is True
    )
    assert lens["repair_summary"]["attempt_count"] == 4
    assert lens["repair_summary"]["proof_body_export_count"] == 0
    assert lens["repair_summary"]["public_drilldown_ref_count"] == 4
    assert lens["repair_summary"]["unsafe_payload_body_export_count"] == 0
    assert lens["authority_ceiling"]["formal_proof_authority"] is False
    assert lens["authority_ceiling"]["proof_bodies_exported"] is False
    assert lens["authority_ceiling"]["oracle_needed_premise_ids_exported"] is False
    assert lens["authority_ceiling"]["human_approval_is_proof_authority"] is False
    assert lens["safe_to_show"]["provider_payloads_omitted"] is True
    assert all(row["public_drilldown_ref"] for row in lens["trace_rows"])
    assert all(
        row["unsafe_payload_bodies_exported"] is False for row in lens["trace_rows"]
    )
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["payload_boundary"]["boundary_id"] == "public_verifier_trace_repair_lens"
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert "source-open public payload-boundary read-model" in lens["anti_claim"]
    assert "metadata-only public read-model" not in lens["anti_claim"]
    assert (public_root / lens["trace_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "body_redacted" not in lens
    assert "redacted_hash" not in encoded
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_repair_loop_lens_uses_payload_boundary(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.repair_loop()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_verifier_repair_loop_lens_v1"
    assert lens["command"] == "microcosm repair-loop"
    assert lens["endpoint"] == "/repair-loop"
    assert lens["lens_id"] == "public_verifier_repair_loop_lens"
    assert lens["selected_pattern_id"] == "formal_math_verifier_trace_repair_loop_compound"
    assert [row["stage_id"] for row in lens["loop_stages"]] == [
        "capture_verifier_failure",
        "classify_failure",
        "route_repair",
        "cold_rerun",
        "promote_metadata_cell",
    ]
    assert [row["failure_class"] for row in lens["transition_rows"]] == [
        "MISSING_PREMISE",
        "TACTIC_UNAVAILABLE",
        "INVALID_PROOF_BODY",
        "NONE_AFTER_METADATA_REPAIR",
    ]
    assert set(lens["negative_case_ids"]) == {
        "repair_action_without_failure_class",
        "cold_rerun_missing_after_repair",
        "curriculum_promotion_without_trace_grade",
        "proof_body_or_oracle_id_exported",
        "provider_payload_as_evidence",
        "human_approval_as_proof",
        "source_mutation_as_repair",
        "release_claim_after_repair",
    }
    assert lens["curriculum_policy"]["cold_rerun_required_before_promotion"] is True
    assert lens["curriculum_policy"]["promotion_scope"] == "metadata_curriculum_cell_only"
    assert lens["repair_loop_summary"]["stage_count"] == 5
    assert lens["repair_loop_summary"]["transition_count"] == 4
    assert lens["repair_loop_summary"]["repairable_transition_count"] == 2
    assert lens["repair_loop_summary"]["promoted_transition_count"] == 1
    assert lens["repair_loop_summary"]["proof_body_export_count"] == 0
    assert lens["repair_loop_summary"]["public_drilldown_ref_count"] == 4
    assert lens["repair_loop_summary"]["unsafe_payload_body_export_count"] == 0
    assert lens["authority_ceiling"]["formal_proof_authority"] is False
    assert lens["authority_ceiling"]["proof_bodies_exported"] is False
    assert lens["authority_ceiling"]["oracle_needed_premise_ids_exported"] is False
    assert lens["authority_ceiling"]["provider_calls_authorized"] is False
    assert lens["safe_to_show"]["provider_payloads_omitted"] is True
    assert all(row["public_drilldown_ref"] for row in lens["transition_rows"])
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["transition_rows"]
    )
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["payload_boundary"]["boundary_id"] == "public_verifier_repair_loop_lens"
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert (public_root / lens["repair_loop_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "body_redacted" not in lens
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_evidence_cell_lens_uses_payload_boundary(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.evidence_cells()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_formal_evidence_cell_lens_v1"
    assert lens["command"] == "microcosm evidence-cells"
    assert lens["endpoint"] == "/evidence-cells"
    assert lens["lens_id"] == "public_formal_evidence_cell_lens"
    assert [row["resolver_status"] for row in lens["evidence_cells"]] == [
        "formal_evidence_cell_present",
        "formal_evidence_cell_present",
        "unknown_cell_rejected",
        "missing_source_rejected",
    ]
    assert set(lens["negative_case_ids"]) == {
        "unknown_cell_id_claim",
        "missing_source_cell",
        "no_sorry_without_cell",
        "cell_claims_general_theorem_proof",
        "proof_body_embedded_in_cell",
        "private_source_ref",
        "release_overclaim",
    }
    assert lens["resolver_policy"]["claim_strength_requires_cell_id"] is True
    assert lens["resolver_policy"]["cell_id_is_receipt_anchor_not_theorem_proof"] is True
    assert lens["resolver_summary"]["cell_count"] == 4
    assert lens["resolver_summary"]["present_cell_count"] == 2
    assert lens["resolver_summary"]["proof_body_export_count"] == 0
    assert lens["resolver_summary"]["public_drilldown_ref_count"] == 2
    assert lens["resolver_summary"]["unsafe_payload_body_export_count"] == 0
    assert lens["authority_ceiling"]["formal_proof_authority"] is False
    assert lens["authority_ceiling"]["proof_bodies_exported"] is False
    assert lens["authority_ceiling"]["private_source_refs_exported"] is False
    assert lens["authority_ceiling"]["general_theorem_solution_claim"] is False
    assert lens["safe_to_show"]["proof_bodies_omitted"] is True
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["evidence_cells"]
    )
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["payload_boundary"]["boundary_id"] == "public_formal_evidence_cell_lens"
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert (public_root / lens["evidence_cell_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "body_redacted" not in lens
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_proof_loop_depth_lens_uses_payload_boundary(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.proof_loop_depth()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_proof_loop_depth_lens_v1"
    assert lens["command"] == "microcosm proof-loop-depth"
    assert lens["endpoint"] == "/proof-loop-depth"
    assert lens["lens_id"] == "public_proof_loop_depth_lens"
    assert [row["gate_id"] for row in lens["gate_rows"]] == [
        "corpus_readiness_boundary",
        "formal_math_readiness_gate",
        "lean_std_premise_index",
        "premise_retrieval",
        "ring2_precision_recall_harness",
        "tactic_availability_probe",
        "target_shape_routing",
        "verifier_trace_repair_lens",
        "repair_loop_cold_rerun",
        "formal_evidence_cell_resolver",
        "lean_witness_boundary",
        "verifier_lab_execution_spine",
    ]
    assert all(row["proof_body_exported"] is False for row in lens["gate_rows"])
    assert all(
        row["oracle_needed_premise_ids_exported"] is False
        for row in lens["gate_rows"]
    )
    assert set(lens["negative_case_ids"]) >= {
        "proof_body_exported_as_depth_evidence",
        "oracle_needed_premise_ids_exported",
        "provider_payload_used_as_verifier_evidence",
        "ring2_fixture_metric_reported_as_benchmark_score",
        "evidence_cell_claims_general_theorem_solution",
        "external_tool_return_code_claimed_as_general_proof",
        "release_or_publication_claim_from_proof_loop_depth",
    }
    assert lens["proof_loop_summary"]["gate_count"] == 12
    assert lens["proof_loop_summary"]["evidence_ref_count"] == 13
    assert lens["proof_loop_summary"]["proof_body_export_count"] == 0
    assert lens["proof_loop_summary"]["benchmark_score_claim_count"] == 0
    assert lens["proof_loop_summary"]["public_drilldown_ref_count"] == 12
    assert lens["proof_loop_summary"]["unsafe_payload_body_export_count"] == 0
    assert lens["proof_loop_summary"]["proof_lab_route_component_count"] == 9
    assert lens["proof_loop_summary"]["proof_lab_lean_lake_return_code"] == 0
    assert lens["proof_loop_summary"]["proof_lab_execution_transition_count"] == 6
    assert lens["proof_loop_summary"]["proof_lab_execution_accepted_transition_count"] == 4
    assert (
        lens["proof_loop_summary"]["proof_lab_execution_cp2_downstream_effect_count"]
        == 1
    )
    assert lens["proof_loop_summary"]["proof_lab_execution_evolve_accepted_count"] == 1
    assert lens["first_screen_proof_lab"]["route_ref"] == PROOF_LAB_ROUTE_REF
    assert (
        lens["first_screen_verifier_lab_execution_spine"]["receipt_ref"]
        == VERIFIER_EXECUTION_RECEIPT_REF
    )
    assert (
        lens["first_screen_verifier_lab_execution_spine"]["command"]
        == VERIFIER_EXECUTION_LENS_COMMAND
    )
    assert lens["authority_ceiling"]["formal_proof_authority"] is False
    assert lens["authority_ceiling"]["proof_bodies_exported"] is False
    assert lens["authority_ceiling"]["oracle_needed_premise_ids_exported"] is False
    assert lens["authority_ceiling"]["benchmark_score_claim"] is False
    assert lens["authority_ceiling"]["general_theorem_solution_claim"] is False
    assert lens["safe_to_show"]["provider_payloads_omitted"] is True
    assert all(row["public_drilldown_ref"] for row in lens["gate_rows"])
    assert all(
        row["unsafe_payload_bodies_exported"] is False for row in lens["gate_rows"]
    )
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["payload_boundary"]["boundary_id"] == "public_proof_loop_depth_lens"
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert (public_root / lens["proof_loop_depth_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "body_redacted" not in lens
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_verifier_lab_execution_spine_lens_uses_real_receipt(
    tmp_path: Path,
) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.verifier_lab_execution_spine_lens()

    assert lens["status"] == "pass"
    assert (
        lens["schema_version"]
        == "microcosm_public_verifier_lab_execution_spine_lens_v1"
    )
    assert lens["command"] == VERIFIER_EXECUTION_LENS_COMMAND
    assert lens["endpoint"] == "/verifier-lab-execution-spine"
    assert lens["source_receipt_ref"] == VERIFIER_EXECUTION_RECEIPT_REF
    assert lens["execution_spine_id"] == "std_public_lean_transition_lab_v1"
    assert lens["execution_summary"]["transition_count"] == 6
    assert lens["execution_summary"]["accepted_transition_count"] == 4
    assert lens["execution_summary"]["residual_transition_count"] == 2
    assert lens["execution_summary"]["cp2_downstream_effect_count"] == 1
    assert lens["execution_summary"]["evolve_accepted_count"] == 1
    assert lens["execution_summary"]["provider_results_counted"] == 0
    assert lens["execution_summary"]["proof_body_export_count"] == 0
    assert lens["execution_summary"]["source_mutation_count"] == 0
    assert lens["tool_witness"]["lean_available"] is True
    assert lens["tool_witness"]["lake_available"] is True
    assert lens["tool_witness"]["lake_project_build_return_code"] == 0
    assert lens["secret_exclusion"]["blocking_hit_count"] == 0
    assert lens["claim_separation_counts"]["lean_verified"] == 4
    assert lens["claim_separation_counts"]["provider_suggested"] == 1
    assert lens["authority_ceiling"]["external_tool_witness_only"] is True
    assert lens["authority_ceiling"]["formal_proof_authority"] is False
    assert lens["authority_ceiling"]["provider_results_counted"] is False
    assert lens["safe_to_show"]["proof_bodies_omitted"] is True
    assert all(row["public_drilldown_ref"] for row in lens["transition_rows"])
    assert all(row["proof_body_exported"] is False for row in lens["transition_rows"])
    assert all(row["provider_visible"] is False for row in lens["transition_rows"])
    assert all(row["source_mutation_authorized"] is False for row in lens["evolve_rows"])
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert (
        lens["payload_boundary"]["boundary_id"]
        == "public_verifier_lab_execution_spine_lens"
    )
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert (public_root / lens["verifier_lab_execution_spine_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "body_redacted" not in lens
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_public_proof_lenses_preserve_stable_created_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)
    shell.proof_loop_depth()
    lens_paths = [
        public_root / "receipts/runtime_shell/public_corpus_readiness_lens.json",
        public_root / "receipts/runtime_shell/public_verifier_trace_repair_lens.json",
        public_root / "receipts/runtime_shell/public_verifier_repair_loop_lens.json",
        public_root / "receipts/runtime_shell/public_formal_evidence_cell_lens.json",
        public_root / "receipts/runtime_shell/public_proof_loop_depth_lens.json",
        public_root
        / "receipts/runtime_shell/public_verifier_lab_execution_spine_lens.json",
    ]
    before = {
        path: json.loads(path.read_text(encoding="utf-8")) for path in lens_paths
    }

    monkeypatch.setattr(
        "microcosm_core.runtime_shell.utc_now",
        lambda: "2099-01-01T00:00:00+00:00",
    )

    shell.proof_loop_depth()

    after = {
        path: json.loads(path.read_text(encoding="utf-8")) for path in lens_paths
    }
    assert after == before


def test_runtime_shell_landing_replay_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.landing_replay()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_work_landing_replay_lens_v1"
    assert lens["command"] == "microcosm landing-replay"
    assert lens["endpoint"] == "/landing-replay"
    assert lens["lens_id"] == "public_work_landing_replay_lens"
    assert [row["lane_id"] for row in lens["lane_decision_table"]] == [
        "scoped_commit",
        "broad_checkpoint",
        "metadata_blocked_patch_bundle",
        "hard_stop",
    ]
    assert set(lens["negative_case_ids"]) == {
        "broad_checkpoint_without_operator_authorization",
        "commit_claim_without_head_advance",
        "unrelated_dirty_paths_staged_by_scoped_lane",
        "commit_attempt_before_owner_native_validation",
        "blocker_reported_without_task_ledger_capture",
        "validation_omitted_before_closeout",
        "private_source_body_exported",
        "release_claim_from_local_receipt",
    }
    assert lens["replay_policy"]["scoped_commit_requires_head_advance_before_landed_language"] is True
    assert lens["replay_policy"]["owner_native_validation_precedes_commit_attempt"] is True
    assert lens["replay_policy"]["broad_checkpoint_requires_explicit_operator_authorization"] is True
    assert lens["replay_summary"]["lane_count"] == 4
    assert lens["replay_summary"]["unrelated_dirty_stage_authority_count"] == 0
    assert any(
        row["event_id"] == "git_metadata_blocker_capture"
        and row["status"] == "source_open_blocker_ref_available"
        for row in lens["replay_events"]
    )
    assert lens["authority_ceiling"]["live_git_mutation_authorized"] is False
    assert lens["authority_ceiling"]["broad_checkpoint_authorized"] is False
    assert lens["authority_ceiling"]["source_mutation_authorized"] is False
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_work_landing_replay_lens"
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert lens["safe_to_show"]["private_paths_omitted"] is True
    assert lens["safe_to_show"]["private_source_bodies_omitted"] is True
    assert "body_redacted" not in lens
    assert (public_root / lens["landing_replay_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_work_landing_replay_lens_uses_payload_boundary(tmp_path: Path) -> None:
    test_runtime_shell_landing_replay_lens_is_public_safe(tmp_path)


def test_runtime_shell_view_quality_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.view_quality()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_view_quality_action_map_lens_v1"
    assert lens["command"] == "microcosm view-quality"
    assert lens["endpoint"] == "/view-quality"
    assert lens["lens_id"] == "public_view_quality_action_map_lens"
    assert lens["selected_pattern_id"] == "view_quality_all_view_action_map"
    assert [row["view_id"] for row in lens["action_rows"]] == [
        "station_monitor",
        "root_navigator",
        "graph_geometry",
        "partial_unmeasured_panel",
        "missing_operator_bridge_console",
    ]
    assert [row["view_id"] for row in lens["hot_action_rollup"]] == [
        "missing_operator_bridge_console",
        "root_navigator",
        "graph_geometry",
        "partial_unmeasured_panel",
    ]
    assert any(
        row["view_id"] == "missing_operator_bridge_console"
        and row["next_action"]
        == "create_source_open_census_row_or_drop_unowned_requested_view"
        for row in lens["action_rows"]
    )
    assert all("score" not in row for row in lens["action_rows"])
    assert all("priority_weight" in row for row in lens["action_rows"])
    assert all("score" not in row for row in lens["hot_action_rollup"])
    assert all("priority_weight" in row for row in lens["hot_action_rollup"])
    assert set(lens["negative_case_ids"]) == {
        "hot_rollup_claimed_as_complete_universe",
        "missing_requested_view_without_action",
        "monitor_row_creates_resolution_pressure",
        "calibrated_pass_in_hot_rollup",
        "partial_row_left_as_prose",
        "private_screenshot_path_exported",
        "release_claim_from_view_quality_lens",
    }
    assert lens["fixture_protocol"]["one_action_row_per_requested_view"] is True
    assert lens["fixture_protocol"]["hot_rollup_is_projection_not_universe"] is True
    assert lens["action_summary"]["requested_view_count"] == 5
    assert lens["action_summary"]["action_row_count"] == 5
    assert lens["action_summary"]["hot_action_count"] == 4
    assert lens["action_summary"]["private_screenshot_path_export_count"] == 0
    assert lens["authority_ceiling"]["private_screenshot_paths_exported"] is False
    assert lens["authority_ceiling"]["live_browser_control_authorized"] is False
    assert lens["authority_ceiling"]["complete_frontend_quality_claim"] is False
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_view_quality_action_map_lens"
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert lens["safe_to_show"]["synthetic_view_rows_only"] is True
    assert lens["safe_to_show"]["view_quality_actions_are_public_payload_boundary_rows"] is True
    assert "body_redacted" not in lens
    assert (public_root / lens["view_quality_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_projection_safety_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.projection_safety()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_projection_safety_audit_lens_v1"
    assert lens["command"] == "microcosm projection-safety"
    assert lens["endpoint"] == "/projection-safety"
    assert lens["lens_id"] == "public_projection_safety_audit_lens"
    assert lens["selected_pattern_id"] == "omission_receipt_reversible_projection_boundary"
    assert lens["projection_summary"]["projection_row_count"] == 42
    assert lens["projection_summary"]["omission_receipt_count"] == 42
    assert lens["projection_summary"]["reversible_drilldown_count"] == 42
    assert lens["projection_summary"]["private_body_export_count"] == 0
    assert lens["projection_summary"]["proof_body_export_count"] == 0
    assert lens["projection_summary"]["provider_payload_export_count"] == 0
    assert lens["projection_summary"]["release_authorized_count"] == 0
    assert set(lens["negative_case_ids"]) == {
        "compressed_projection_without_omission_receipt",
        "omission_receipt_without_drilldown",
        "private_source_body_exported",
        "proof_body_exported_as_public_evidence",
        "provider_payload_exported",
        "authority_ceiling_missing",
        "release_claim_from_projection",
        "irreversible_projection_without_owner_route",
    }
    assert any(
        row["projection_id"] == "public_proof_loop_depth_lens"
        for row in lens["projection_rows"]
    )
    assert any(
        row["projection_id"] == "public_projection_drift_control_lens"
        and row["endpoint"] == "/drift-control"
        for row in lens["projection_rows"]
    )
    assert any(
        row["projection_id"]
        == "public_spatial_world_model_counterfactual_simulation_replay_lens"
        and row["endpoint"] == "/spatial-simulation"
        for row in lens["projection_rows"]
    )
    assert any(
        row["projection_id"] == "public_route_cleanup_contract_lens"
        and row["endpoint"] == "/route-cleanup"
        for row in lens["projection_rows"]
    )
    assert any(
        row["projection_id"] == "public_import_projector_contract_lens"
        and row["endpoint"] == "/import-projector"
        for row in lens["projection_rows"]
    )
    assert any(
        row["projection_id"] == "public_compression_profile_option_surface_lens"
        and row["endpoint"] == "/option-surface-lens"
        for row in lens["projection_rows"]
    )
    assert any(
        row["projection_id"] == "public_agent_sandbox_policy_escape_replay_lens"
        and row["endpoint"] == "/replay-gauntlet"
        for row in lens["projection_rows"]
    )
    assert any(
        row["projection_id"] == "public_indirect_prompt_injection_information_flow_policy_replay_lens"
        and row["endpoint"] == "/replay-gauntlet"
        for row in lens["projection_rows"]
    )
    assert all(row["omission_receipt"]["drilldown"] for row in lens["projection_rows"])
    assert lens["authority_ceiling"]["release_authorized"] is False
    assert lens["authority_ceiling"]["source_mutation_authorized"] is False
    assert lens["safe_to_show"]["omitted_content_has_named_drilldown"] is True
    assert lens["source_open_body_policy"]
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_projection_safety_audit_lens"
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert (public_root / lens["projection_safety_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_projection_safety_lens_uses_payload_boundary(tmp_path: Path) -> None:
    test_runtime_shell_projection_safety_lens_is_public_safe(tmp_path)


def test_runtime_shell_projection_drift_control_lens_uses_payload_boundary(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.projection_drift()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_projection_drift_control_lens_v1"
    assert lens["command"] == "microcosm drift-control"
    assert lens["endpoint"] == "/drift-control"
    assert lens["lens_id"] == "public_projection_drift_control_lens"
    assert lens["selected_route_id"] == "world_model_projection_drift_control_room"
    assert lens["drift_summary"]["row_count"] == 8
    assert lens["drift_summary"]["source_ref_count"] == 8
    assert lens["drift_summary"]["repair_route_count"] == 8
    assert lens["drift_summary"]["validation_ref_count"] == 8
    assert lens["drift_summary"]["source_authority_claim_count"] == 0
    assert lens["drift_summary"]["live_repair_authorized_count"] == 0
    assert lens["drift_summary"]["source_mutation_authorized_count"] == 0
    assert lens["drift_summary"]["automatic_doctrine_promotion_count"] == 0
    assert lens["drift_summary"]["private_runtime_data_export_count"] == 0
    assert lens["drift_summary"]["provider_payload_export_count"] == 0
    assert set(lens["negative_case_ids"]) >= {
        "drift_row_without_source_ref_rejected",
        "live_repair_action_authorized_rejected",
        "projection_claiming_source_authority_rejected",
        "automatic_doctrine_promotion_rejected",
        "release_from_drift_projection_rejected",
    }
    assert lens["authority_ceiling"]["source_open_drilldown_contract"] is True
    assert lens["authority_ceiling"]["source_authority_claim"] is False
    assert lens["authority_ceiling"]["live_route_repair_authorized"] is False
    assert lens["authority_ceiling"]["live_task_ledger_mutation_authorized"] is False
    assert lens["authority_ceiling"]["private_runtime_data_exported"] is False
    assert lens["authority_ceiling"]["automatic_doctrine_promotion_authorized"] is False
    assert all(row["source_ref"] for row in lens["drift_rows"])
    assert all(row["repair_route"] for row in lens["drift_rows"])
    assert all(row["validation_ref"] for row in lens["drift_rows"])
    assert all(row["public_drilldown_ref"] for row in lens["drift_rows"])
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["drift_rows"]
    )
    assert lens["drift_summary"]["public_drilldown_ref_count"] == 8
    assert lens["drift_summary"]["unsafe_payload_body_export_count"] == 0
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["payload_boundary"]["boundary_id"] == "public_projection_drift_control_lens"
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["safe_to_show"]["repair_is_route_drilldown_only"] is True
    assert lens["release_authorized"] is False
    assert "body_redacted" not in lens
    assert (public_root / lens["projection_drift_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_spatial_simulation_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.spatial_simulation()

    assert lens["status"] == "pass"
    assert (
        lens["schema_version"]
        == "microcosm_public_spatial_world_model_counterfactual_simulation_replay_lens_v1"
    )
    assert lens["command"] == "microcosm spatial-simulation"
    assert lens["endpoint"] == "/spatial-simulation"
    assert (
        lens["lens_id"]
        == "public_spatial_world_model_counterfactual_simulation_replay_lens"
    )
    assert lens["selected_route_id"] == "spatial_world_model_counterfactual_simulation_replay"
    assert lens["simulation_summary"]["scene_state_count"] == 6
    assert lens["simulation_summary"]["replay_count"] == 6
    assert lens["simulation_summary"]["transition_diff_count"] == 6
    assert lens["simulation_summary"]["oracle_state_check_count"] == 6
    assert lens["negative_case_summary"]["expected_negative_case_count"] == 0
    assert lens["authority_ceiling"]["private_video_exported"] is False
    assert lens["authority_ceiling"]["raw_sensor_data_exported"] is False
    assert lens["authority_ceiling"]["live_robot_operation_authorized"] is False
    assert lens["authority_ceiling"]["live_av_operation_authorized"] is False
    assert lens["authority_ceiling"]["release_authorized"] is False
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert (
        lens["payload_boundary"]["boundary_id"]
        == "public_spatial_world_model_counterfactual_simulation_replay_lens"
    )
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["safe_to_show"]["unsafe_payload_bodies_in_receipt"] is False
    assert lens["safe_to_show"]["private_video_bodies_omitted"] is True
    assert (
        lens["safe_to_show"][
            "counterfactual_replay_rows_are_public_payload_boundary_rows"
        ]
        is True
    )
    assert all(
        row["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
        for row in lens["counterfactual_replays"]
    )
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["counterfactual_replays"]
    )
    assert "body_redacted" not in lens
    assert (public_root / lens["spatial_simulation_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "private_state_scan" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_route_cleanup_contract_lens_uses_payload_boundary(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.route_cleanup()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_route_cleanup_contract_lens_v1"
    assert lens["command"] == "microcosm route-cleanup"
    assert lens["endpoint"] == "/route-cleanup"
    assert lens["lens_id"] == "public_route_cleanup_contract_lens"
    assert lens["selected_route_id"] == "route_cleanup_contract_plane"
    assert lens["cleanup_summary"]["row_count"] == 8
    assert lens["cleanup_summary"]["source_ref_count"] == 8
    assert lens["cleanup_summary"]["owner_route_count"] == 8
    assert lens["cleanup_summary"]["validation_ref_count"] == 8
    assert lens["cleanup_summary"]["negative_case_count"] == 8
    assert lens["cleanup_summary"]["route_deletion_authorized_count"] == 0
    assert lens["cleanup_summary"]["source_mutation_authorized_count"] == 0
    assert lens["cleanup_summary"]["generated_region_hand_edit_authorized_count"] == 0
    assert lens["cleanup_summary"]["private_body_export_count"] == 0
    assert lens["cleanup_summary"]["provider_payload_export_count"] == 0
    assert lens["cleanup_summary"]["release_authorized_count"] == 0
    assert set(lens["negative_case_ids"]) >= {
        "route_cleanup_deletes_route_without_replacement_rejected",
        "context_pack_skip_to_wide_grep_rejected",
        "generated_region_hand_edit_rejected",
        "option_surface_as_control_entry_rejected",
        "release_from_route_cleanup_rejected",
    }
    assert lens["authority_ceiling"]["source_open_drilldown_contract"] is True
    assert lens["authority_ceiling"]["route_deletion_authorized"] is False
    assert lens["authority_ceiling"]["source_mutation_authorized"] is False
    assert lens["authority_ceiling"]["generated_region_hand_edit_authorized"] is False
    assert lens["authority_ceiling"]["private_body_exported"] is False
    assert lens["authority_ceiling"]["provider_payload_exported"] is False
    assert lens["safe_to_show"]["route_cleanup_is_source_open_drilldown_contract"] is True
    assert all(row["source_ref"] for row in lens["cleanup_rows"])
    assert all(row["owner_route"] for row in lens["cleanup_rows"])
    assert all(row["validation_ref"] for row in lens["cleanup_rows"])
    assert all(row["public_drilldown_ref"] for row in lens["cleanup_rows"])
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["cleanup_rows"]
    )
    assert lens["cleanup_summary"]["public_drilldown_ref_count"] == 8
    assert lens["cleanup_summary"]["unsafe_payload_body_export_count"] == 0
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["payload_boundary"]["boundary_id"] == "public_route_cleanup_contract_lens"
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["release_authorized"] is False
    assert (public_root / lens["route_cleanup_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "body_redacted" not in lens
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_projection_import_map_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.projection_import_map()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_projection_import_map_lens_v1"
    assert lens["command"] == "microcosm projection-import-map"
    assert lens["endpoint"] == "/projection-import-map"
    assert lens["lens_id"] == "public_projection_import_map_lens"
    assert lens["map_summary"]["row_count"] == 6
    assert lens["map_summary"]["stage_count"] == 6
    assert lens["map_summary"]["validation_ref_count"] == 12
    assert lens["map_summary"]["private_body_export_count"] == 0
    assert lens["map_summary"]["provider_payload_export_count"] == 0
    assert lens["map_summary"]["automated_import_guarantee"] is False
    assert {row["source_pattern_id"] for row in lens["import_rows"]} >= {
        "macro_projection_import_protocol",
        "omission_receipt_reversible_projection_boundary",
        "repository_agent_benchmark_transaction_lab",
        "agent_reliability_replay_gauntlet",
        "formal_math_verifier_trace_repair_loop_compound",
    }
    assert all(row["cleaned"] for row in lens["import_rows"])
    assert all(row["omitted"] for row in lens["import_rows"])
    assert all(row["validation_refs"] for row in lens["import_rows"])
    assert set(lens["negative_case_ids"]) >= {
        "private_body_copied_into_public_surface_rejected",
        "automated_import_success_guarantee_rejected",
        "release_claim_from_projection_import_map_rejected",
    }
    assert lens["authority_ceiling"]["private_body_export_authorized"] is False
    assert lens["authority_ceiling"]["proof_body_export_authorized"] is False
    assert lens["authority_ceiling"]["provider_payload_export_authorized"] is False
    assert lens["authority_ceiling"]["automated_import_guarantee"] is False
    assert lens["safe_to_show"]["private_source_bodies_omitted"] is True
    assert lens["source_open_body_policy"]
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_projection_import_map_lens"
    assert lens["payload_boundary"]["public_refs_are_drilldowns_not_replacements"] is True
    assert (public_root / lens["projection_import_map_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_import_projector_contract_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.import_projector()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_import_projector_contract_lens_v1"
    assert lens["command"] == "microcosm import-projector"
    assert lens["endpoint"] == "/import-projector"
    assert lens["lens_id"] == "public_import_projector_contract_lens"
    assert lens["projector_summary"]["row_count"] == 9
    assert lens["projector_summary"]["stage_count"] == 6
    assert lens["projector_summary"]["source_ref_count"] == 9
    assert lens["projector_summary"]["owner_route_count"] == 9
    assert lens["projector_summary"]["validation_ref_count"] == 9
    assert lens["projector_summary"]["authority_ceiling_row_count"] == 9
    assert lens["projector_summary"]["private_body_export_count"] == 0
    assert lens["projector_summary"]["proof_body_export_count"] == 0
    assert lens["projector_summary"]["provider_payload_export_count"] == 0
    assert lens["projector_summary"]["generated_region_hand_edit_authorized_count"] == 0
    assert lens["projector_summary"]["release_authorized_count"] == 0
    assert {row["projector_stage"] for row in lens["projector_rows"]} == {
        "candidate_selection",
        "public_manifest",
        "stripping_and_omission",
        "fixture_projection",
        "runtime_binding",
        "validation_and_closeout",
    }
    assert set(lens["negative_case_ids"]) >= {
        "private_source_body_copied_into_projector_rejected",
        "projector_row_without_omission_receipt_rejected",
        "generated_region_hand_edit_claim_rejected",
        "automated_import_execution_claim_rejected",
        "lossless_private_projection_claim_rejected",
    }
    assert lens["authority_ceiling"]["projector_contract_read_model_only"] is True
    assert lens["authority_ceiling"]["private_body_export_authorized"] is False
    assert lens["authority_ceiling"]["proof_body_export_authorized"] is False
    assert lens["authority_ceiling"]["provider_payload_export_authorized"] is False
    assert lens["authority_ceiling"]["generated_region_hand_edit_authorized"] is False
    assert lens["authority_ceiling"]["automated_import_execution_authorized"] is False
    assert lens["authority_ceiling"]["lossless_projection_claim"] is False
    assert lens["safe_to_show"]["projector_is_read_model_only"] is True
    assert all(row["validation_ref"] for row in lens["projector_rows"])
    assert all(row["authority_ceiling_ref"] for row in lens["projector_rows"])
    assert lens["release_authorized"] is False
    assert lens["source_open_body_policy"]
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_import_projector_contract_lens"
    assert lens["payload_boundary"]["metadata_only_standin_authorized"] is False
    assert (public_root / lens["import_projector_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_option_surface_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.option_surface_lens()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_compression_profile_option_surface_lens_v1"
    assert lens["command"] == "microcosm option-surface-lens"
    assert lens["endpoint"] == "/option-surface-lens"
    assert lens["lens_id"] == "public_compression_profile_option_surface_lens"
    assert lens["option_surface_summary"]["row_count"] == 6
    assert lens["option_surface_summary"]["stage_count"] == 6
    assert lens["option_surface_summary"]["source_ref_count"] == 6
    assert lens["option_surface_summary"]["validation_ref_count"] == 6
    assert lens["option_surface_summary"]["authority_ceiling_row_count"] == 6
    assert lens["option_surface_summary"]["private_body_export_count"] == 0
    assert lens["option_surface_summary"]["provider_payload_export_count"] == 0
    assert lens["option_surface_summary"]["profile_switch_execution_authorized_count"] == 0
    assert lens["projection_cell"]["cell_id"] == "projection_protocol_self_host"
    assert "compression_profile_governed_option_surface" in lens["selected_pattern_ids"]
    assert {row["option_stage"] for row in lens["option_rows"]} == {
        "candidate_pattern_anchor",
        "public_profile_contract",
        "sidecar_projection",
        "runtime_binding",
        "validation",
        "reentry_contract",
    }
    assert set(lens["negative_case_ids"]) >= {
        "private_profile_body_export_rejected",
        "profile_switch_execution_claim_rejected",
        "sidecar_body_dump_rejected",
        "lossless_profile_projection_claim_rejected",
    }
    assert lens["authority_ceiling"]["option_surface_read_model_only"] is True
    assert lens["authority_ceiling"]["private_body_export_authorized"] is False
    assert lens["authority_ceiling"]["provider_payload_export_authorized"] is False
    assert lens["authority_ceiling"]["profile_switch_execution_authorized"] is False
    assert lens["authority_ceiling"]["automatic_profile_selection_authorized"] is False
    assert lens["authority_ceiling"]["lossless_projection_claim"] is False
    assert lens["safe_to_show"]["option_surface_is_read_model_only"] is True
    assert all(row["validation_ref"] for row in lens["option_rows"])
    assert all(row["authority_ceiling_ref"] for row in lens["option_rows"])
    assert all(row["unsafe_payload_bodies_exported"] is False for row in lens["option_rows"])
    assert (
        lens["projection_cell"]["legacy_import_plan_compat"]["classification"]
        == "legacy_import_plan_payload_flags_normalized_to_source_open_boundary"
    )
    legacy_compat = lens["projection_cell"]["legacy_import_plan_compat"]
    assert legacy_compat["legacy_payload_flag_schema_present"] is True
    assert legacy_compat["legacy_payload_flags_exported"] is False
    assert (
        legacy_compat["source_open_payload_boundary_ref"]
        == "microcosm option-surface-lens::payload_boundary"
    )
    assert legacy_compat["public_contract_fields"] == [
        "source_open_body_policy",
        "unsafe_payload_bodies_in_receipt",
        "payload_boundary",
    ]
    assert lens["release_authorized"] is False
    assert lens["source_open_body_policy"]
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert (
        lens["payload_boundary"]["boundary_id"]
        == "public_compression_profile_option_surface_lens"
    )
    assert lens["payload_boundary"]["legacy_schema_compat_present"] is True
    assert (public_root / lens["option_surface_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded
    assert "source_cell_redacted_flag" not in encoded
    assert "body_redacted" not in encoded
    assert "body_copied" not in encoded


def test_runtime_shell_stripping_guard_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.stripping_guard()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_private_stripping_guard_lens_v1"
    assert lens["command"] == "microcosm stripping-guard"
    assert lens["endpoint"] == "/stripping-guard"
    assert lens["lens_id"] == "public_stripping_guard_lens"
    assert lens["guard_summary"]["guard_row_count"] == 8
    assert lens["guard_summary"]["negative_case_count"] == 8
    assert lens["guard_summary"]["validation_ref_count"] == 16
    assert lens["guard_summary"]["private_body_export_count"] == 0
    assert lens["guard_summary"]["proof_body_export_count"] == 0
    assert lens["guard_summary"]["provider_payload_export_count"] == 0
    assert lens["guard_summary"]["raw_private_path_export_count"] == 0
    assert lens["guard_summary"]["secret_token_export_count"] == 0
    assert set(lens["negative_case_ids"]) == {
        "private_body_export_rejected",
        "proof_body_export_rejected",
        "provider_payload_export_rejected",
        "raw_private_path_export_rejected",
        "secret_scanner_claim_rejected",
        "financial_advice_export_rejected",
        "source_mutation_authority_rejected",
        "release_or_private_equivalence_claim_rejected",
    }
    assert {row["guard_row_id"] for row in lens["guard_rows"]} == {
        "private_source_body_strip",
        "proof_body_strip",
        "provider_payload_strip",
        "raw_private_path_redaction",
        "secret_token_strip",
        "financial_advice_strip",
        "source_mutation_denial",
        "release_and_private_equivalence_denial",
    }
    assert all(row["validation_refs"] for row in lens["guard_rows"])
    assert lens["authority_ceiling"]["read_model_only"] is True
    assert lens["authority_ceiling"]["private_body_export_authorized"] is False
    assert lens["authority_ceiling"]["proof_body_export_authorized"] is False
    assert lens["authority_ceiling"]["provider_payload_export_authorized"] is False
    assert lens["authority_ceiling"]["raw_private_path_export_authorized"] is False
    assert lens["authority_ceiling"]["secret_detection_completeness_claim"] is False
    assert lens["authority_ceiling"]["financial_advice_authorized"] is False
    assert lens["authority_ceiling"]["source_mutation_authorized"] is False
    assert lens["authority_ceiling"]["private_data_equivalence_claim"] is False
    assert lens["authority_ceiling"]["release_authorized"] is False
    assert lens["safe_to_show"]["secret_examples_omitted"] is True
    assert all(row["unsafe_payload_bodies_exported"] is False for row in lens["guard_rows"])
    assert all(row["public_drilldown"] for row in lens["guard_rows"])
    assert lens["source_open_body_policy"]
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_stripping_guard_lens"
    assert (public_root / lens["stripping_guard_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_standards_control_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.standards_control()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_standards_control_lens_v1"
    assert lens["command"] == "microcosm standards-control"
    assert lens["endpoint"] == "/standards-control"
    assert lens["lens_id"] == "public_standards_control_lens"
    assert lens["standards_summary"]["standards_control_row_count"] == 8
    assert lens["standards_summary"]["negative_case_count"] == 8
    assert lens["standards_summary"]["validation_ref_count"] == 16
    assert lens["standards_summary"]["standard_count"] >= 1
    assert lens["standards_summary"]["standard_pressure_row_count"] >= 1
    assert lens["standards_summary"]["validator_receipt_ref_count"] >= 1
    assert lens["standards_summary"]["private_body_export_count"] == 0
    assert lens["standards_summary"]["proof_body_export_count"] == 0
    assert lens["standards_summary"]["provider_payload_export_count"] == 0
    assert lens["standards_summary"]["source_authority_claim_count"] == 0
    assert set(lens["negative_case_ids"]) == {
        "standard_without_registry_row_rejected",
        "public_standard_pressure_without_authority_boundary_rejected",
        "validator_receipt_missing_from_coverage_map_rejected",
        "acceptance_command_treated_as_release_approval_rejected",
        "fixture_manifest_without_negative_cases_rejected",
        "docs_claim_without_runtime_command_rejected",
        "standards_projection_claims_private_source_authority_rejected",
        "release_or_publication_claim_from_standards_pass_rejected",
    }
    assert {row["control_row_id"] for row in lens["standards_rows"]} == {
        "standards_registry_contract",
        "public_standard_pressure_contract",
        "validator_receipt_coverage_contract",
        "acceptance_gate_contract",
        "fixture_manifest_contract",
        "docs_entry_contract",
        "authority_ceiling_contract",
        "projection_safety_contract",
    }
    assert all(row["validation_refs"] for row in lens["standards_rows"])
    assert all(row["source_authority_claim"] is False for row in lens["standards_rows"])
    assert all(row["private_body_exported"] is False for row in lens["standards_rows"])
    assert all(row["proof_body_exported"] is False for row in lens["standards_rows"])
    assert all(row["provider_payload_exported"] is False for row in lens["standards_rows"])
    assert all(row["release_authorized"] is False for row in lens["standards_rows"])
    assert lens["authority_ceiling"]["read_model_only"] is True
    assert lens["authority_ceiling"]["standards_registry_source_authority"] is False
    assert lens["authority_ceiling"]["private_body_export_authorized"] is False
    assert lens["authority_ceiling"]["proof_body_export_authorized"] is False
    assert lens["authority_ceiling"]["provider_payload_export_authorized"] is False
    assert lens["authority_ceiling"]["provider_calls_authorized"] is False
    assert lens["authority_ceiling"]["source_mutation_authorized"] is False
    assert lens["authority_ceiling"]["private_data_equivalence_claim"] is False
    assert lens["authority_ceiling"]["standards_completeness_claim"] is False
    assert lens["authority_ceiling"]["release_authorized"] is False
    assert lens["safe_to_show"]["receipt_refs_only"] is True
    assert lens["safe_to_show"]["projection_is_read_model_only"] is True
    assert lens["source_open_body_policy"]
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_standards_control_lens"
    assert "body_redacted" not in lens
    assert all(
        row["unsafe_payload_bodies_exported"] is False for row in lens["standards_rows"]
    )
    assert (public_root / lens["standards_control_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_hook_coverage_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.hook_coverage()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_hook_intervention_coverage_lens_v1"
    assert lens["command"] == "microcosm hook-coverage"
    assert lens["endpoint"] == "/hook-coverage"
    assert lens["lens_id"] == "public_hook_intervention_coverage_lens"
    assert lens["selected_pattern_id"] == "runtime_hook_shadow_intervention_coverage"
    assert lens["coverage_summary"]["intervention_row_count"] == 5
    assert lens["coverage_summary"]["route_compliance_decision_count"] == 9
    assert lens["coverage_summary"]["authority_rejection_count"] == 1
    assert lens["coverage_summary"]["debt_retirement_count"] == 1
    assert lens["coverage_summary"]["route_lease_warning_session_count"] == 2
    assert lens["coverage_summary"]["hook_shadow_case_count"] == 6
    assert lens["coverage_summary"]["hook_shadow_repair_class_count"] == 6
    assert lens["coverage_summary"]["banned_route_intervention_count"] == 1
    assert lens["coverage_summary"]["command_displacement_count"] == 1
    assert lens["coverage_summary"]["live_state_read_denial_count"] == 1
    assert lens["coverage_summary"]["over_budget_denial_count"] == 1
    assert lens["missing_authority_case_ids"] == ["hook_shadow_missing_authority"]
    assert "secret_exclusion_posture" in lens["mapped_hook_shadow_repair_classes"]
    assert set(lens["negative_case_ids"]) == {
        "agent_trace_missing_route_lease",
        "duplicate_trace_event_conflict",
        "hook_shadow_banned_route_attempt",
        "hook_shadow_budget_overrun",
        "hook_shadow_command_displacement",
        "hook_shadow_live_state_read_attempt",
        "hook_shadow_missing_authority",
        "route_compliance_overclaims_behavior_change",
        "route_lease_broad_kernel_bloat_before_direct_action",
        "route_lease_static_metadata_without_trace_feedback",
        "telemetry_private_transcript_body",
        "wrong_actor_axis_and_evidence_only_telemetry",
    }
    assert lens["authority_ceiling"]["live_operator_state_read"] is False
    assert lens["authority_ceiling"]["provider_payload_read"] is False
    assert lens["authority_ceiling"]["source_open_read_model_only"] is True
    assert lens["authority_ceiling"]["live_task_ledger_mutation_authorized"] is False
    assert lens["authority_ceiling"]["pattern_assimilation_authorized"] is False
    assert lens["safe_to_show"]["receipt_refs_only"] is True
    assert lens["source_open_body_policy"]
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_hook_intervention_coverage_lens"
    assert "body_redacted" not in lens
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["intervention_rows"]
    )
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["route_compliance_decisions"]
    )
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["hook_shadow_decisions"]
    )
    assert (public_root / lens["hook_intervention_coverage_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "metadata_projection_only" not in encoded
    assert "private_state_scan_posture" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_replay_gauntlet_lens_uses_payload_boundary(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.replay_gauntlet()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_agent_reliability_replay_gauntlet_lens_v1"
    assert lens["command"] == "microcosm replay-gauntlet"
    assert lens["endpoint"] == "/replay-gauntlet"
    assert lens["lens_id"] == "public_agent_reliability_replay_gauntlet_lens"
    assert lens["selected_route_id"] == "agent_reliability_synthetic_replay_gauntlet"
    assert lens["coverage_summary"]["episode_count"] == 11
    assert lens["coverage_summary"]["blocked_episode_count"] == 9
    assert lens["coverage_summary"]["quarantined_episode_count"] == 2
    assert lens["coverage_summary"]["fake_secret_count"] == 2
    assert set(lens["negative_case_ids"]) >= {
        "mutable_evaluator_pass_label_rejected",
        "sandbox_escape_request_denied",
        "tool_scope_without_manifest_denied",
        "untrusted_tool_output_as_instruction_rejected",
        "memory_write_without_quarantine_rejected",
        "sleeper_trigger_memory_write_rejected",
        "complete_security_claim_rejected",
    }
    assert lens["fixture_protocol"]["locked_evaluator_required"] is True
    assert lens["fixture_protocol"]["monitor_verdict_required"] is True
    assert lens["fixture_protocol"]["memory_write_quarantine_required"] is True
    assert lens["authority_ceiling"]["live_agent_execution_authorized"] is False
    assert lens["authority_ceiling"]["live_tool_calls_authorized"] is False
    assert lens["authority_ceiling"]["real_secret_material_exported"] is False
    assert lens["authority_ceiling"]["complete_security_claim"] is False
    assert lens["safe_to_show"]["fake_secrets_only"] is True
    assert lens["source_open_body_policy"]
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_agent_reliability_replay_gauntlet_lens"
    assert "body_redacted" not in lens
    assert all(row["real_secret_material_exported"] is False for row in lens["episode_rows"])
    assert all(row["live_tool_call_authorized"] is False for row in lens["episode_rows"])
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["episode_rows"]
    )
    assert (public_root / lens["replay_gauntlet_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_benchmark_lab_lens_uses_payload_boundary(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.benchmark_lab()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_repository_benchmark_transaction_lab_lens_v1"
    assert lens["command"] == "microcosm benchmark-lab"
    assert lens["endpoint"] == "/benchmark-lab"
    assert lens["lens_id"] == "public_repository_benchmark_transaction_lab_lens"
    assert lens["scorecard"]["task_count"] == 2
    assert lens["scorecard"]["oracle_patch_count"] == 2
    assert lens["scorecard"]["fail_to_pass_count"] == 2
    assert lens["scorecard"]["pass_to_pass_count"] == 2
    assert lens["scorecard"]["misleading_test_denial_count"] == 1
    assert lens["scorecard"]["scoped_diff_receipt_count"] == 2
    assert lens["scorecard"]["provider_cooldown_count"] == 1
    assert [row["task_id"] for row in lens["task_rows"]] == [
        "inventory_tax_rounding_bugfix",
        "permissions_audit_trail_feature",
    ]
    assert set(lens["negative_case_ids"]) >= {
        "swe_bench_score_claim_rejected",
        "live_repo_mutation_without_authority_rejected",
        "provider_call_during_fixture_replay_rejected",
        "misleading_test_hacking_rejected",
    }
    assert lens["fixture_protocol"]["oracle_diff_required"] is True
    assert lens["fixture_protocol"]["pass_to_pass_required"] is True
    assert lens["authority_ceiling"]["live_repo_mutation_authorized"] is False
    assert lens["authority_ceiling"]["provider_call_authorized"] is False
    assert lens["authority_ceiling"]["swe_bench_performance_claim"] is False
    assert lens["authority_ceiling"]["production_delivery_rate_claim"] is False
    assert lens["safe_to_show"]["oracle_patch_bodies_omitted"] is True
    assert lens["source_open_body_policy"]
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_repository_benchmark_transaction_lab_lens"
    assert "body_redacted" not in lens
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["task_rows"]
    )
    assert (public_root / lens["benchmark_lab_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_legibility_scorecard_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.legibility_scorecard()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_cold_reader_legibility_scorecard_lens_v1"
    assert lens["command"] == "microcosm legibility-scorecard"
    assert lens["endpoint"] == "/legibility-scorecard"
    assert lens["lens_id"] == "public_cold_reader_legibility_scorecard_lens"
    assert lens["scorecard"]["checkpoint_count"] == 6
    assert lens["scorecard"]["reader_question_count"] == 5
    assert lens["scorecard"]["time_budget_minutes"] == 10
    assert lens["scorecard"]["blocking_gap_count"] == 0
    assert set(lens["negative_case_ids"]) >= {
        "architecture_legible_without_running_commands_rejected",
        "receipt_forward_first_screen_rejected",
        "private_macro_equivalence_claim_rejected",
        "release_or_publication_claim_from_scorecard_rejected",
        "cold_reader_success_guarantee_rejected",
    }
    assert lens["fixture_protocol"]["question_to_command_mapping_required"] is True
    assert lens["fixture_protocol"]["receipt_drilldown_after_causal_path"] is True
    assert lens["authority_ceiling"]["release_authorized"] is False
    assert lens["authority_ceiling"]["reader_success_guarantee"] is False
    assert lens["authority_ceiling"]["private_data_equivalence_claim"] is False
    assert lens["authority_ceiling"]["benchmark_score_claim"] is False
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert (
        lens["payload_boundary"]["boundary_id"]
        == "public_cold_reader_legibility_scorecard_lens"
    )
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert lens["safe_to_show"]["private_macro_context_omitted"] is True
    assert lens["safe_to_show"]["scorecard_rows_are_public_payload_boundary_rows"] is True
    assert "body_redacted" not in lens
    assert (public_root / lens["legibility_scorecard_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_corpus_lens_is_public_safe(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.corpus_lens()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_corpus_readiness_lens_v1"
    assert lens["command"] == "microcosm corpus-lens"
    assert lens["endpoint"] == "/corpus"
    assert lens["organ_id"] == "corpus_readiness_mathlib_absence_gate"
    assert lens["source_pattern_count"] == 1
    assert lens["corpus_summary"]["corpus_count"] == 7
    assert lens["corpus_summary"]["mathlib_lake_project_import_available"] is False
    assert set(lens["corpus_summary"]["absent_corpus_ids"]) == {
        "LeanDojo",
        "Pantograph",
        "ProofNet",
        "PutnamBench_lean4",
        "mathlib",
        "miniF2F_lean4_mathlib_package",
    }
    assert lens["corpus_summary"]["translation_smoke_only_ids"] == [
        "miniF2F_lean3_annex"
    ]
    assert len(lens["corpora"]) == 7
    assert {row["corpus_id"] for row in lens["corpora"]} == {
        "LeanDojo",
        "Pantograph",
        "ProofNet",
        "PutnamBench_lean4",
        "mathlib",
        "miniF2F_lean3_annex",
        "miniF2F_lean4_mathlib_package",
    }
    assert lens["consumer_gate"]["allowed_case_ids"] == [
        "miniF2F_lean3_translation_smoke_allowed"
    ]
    assert lens["consumer_gate"]["blocked_case_ids"] == [
        "leandojo_training_blocked_absent",
        "mathlib_import_blocked_until_probe",
        "miniF2F_lean4_mathlib_search_blocked_absent",
        "pantograph_state_search_blocked_absent",
        "proofnet_blocked_absent",
        "putnambench_lean4_blocked_absent",
    ]
    assert set(lens["negative_case_ids"]) == {
        "consumer_skips_readiness_gate",
        "mathlib_available_without_probe",
        "private_corpus_source_ref",
        "proof_body_leakage",
        "release_overclaim",
    }
    assert lens["authority_ceiling"]["environment_metadata_only"] is True
    assert lens["authority_ceiling"]["lean_lake_execution_authorized"] is False
    assert lens["authority_ceiling"]["mathlib_dependent_proof_authority"] is False
    assert lens["authority_ceiling"]["benchmark_or_corpus_completeness_authority"] is False
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_corpus_readiness_lens"
    assert lens["payload_boundary"]["source_open_default"] is True
    assert lens["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert all(row["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY for row in lens["corpora"])
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["consumer_gate"]["decision_rows"]
    )
    assert lens["safe_to_show"]["no_proof_bodies"] is True
    assert lens["safe_to_show"]["corpus_rows_are_public_payload_boundary_rows"] is True
    assert "body_redacted" not in lens
    assert (public_root / lens["corpus_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_prediction_lens_uses_payload_boundary(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.prediction_lens()

    assert lens["status"] == "pass"
    assert lens["schema_version"] == "microcosm_public_prediction_lens_v1"
    assert lens["command"] == "microcosm prediction-lens"
    assert lens["endpoint"] == "/prediction"
    assert lens["organ_id"] == "prediction_oracle_reconciliation"
    assert lens["source_pattern_count"] == 6
    assert [row["mechanic_id"] for row in lens["mechanics"]] == [
        "target_universe_gate",
        "cp1_bifurcation_resolution",
        "cp2_prediction_rows",
        "oracle_diff_grading",
        "bounded_dossier_mutation",
    ]
    assert lens["mechanics"][0]["count"] == 2
    assert lens["mechanics"][2]["count"] == 2
    assert lens["mechanics"][3]["graded_count"] == 2
    assert lens["mechanics"][3]["hit_count"] == 1
    assert set(lens["negative_case_ids"]) == {
        "invalid_cp2_target",
        "missing_bifurcation_resolution",
        "post_t_evidence_ref",
        "trading_advice_overclaim",
        "unconfirmed_equity_lane_claim",
        "unsafe_dossier_mutation",
    }
    assert lens["authority_ceiling"]["trading_authorized"] is False
    assert lens["authority_ceiling"]["financial_advice_authorized"] is False
    assert lens["authority_ceiling"]["live_market_data_authorized"] is False
    assert lens["authority_ceiling"]["forecast_performance_claim"] is False
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert lens["payload_boundary"]["boundary_id"] == "public_prediction_lens"
    assert lens["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert lens["safe_to_show"]["synthetic_targets_only"] is True
    assert lens["safe_to_show"]["no_financial_or_investment_advice"] is True
    assert lens["safe_to_show"]["private_account_state_omitted"] is True
    assert "body_redacted" not in lens
    assert "public_replacement_refs" not in lens
    assert all(
        row["unsafe_payload_bodies_exported"] is False for row in lens["mechanics"]
    )
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["reconciliation_rows"]
    )
    assert (public_root / lens["prediction_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_market_prediction_boundary_lens_uses_payload_boundary(
    tmp_path: Path,
) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    lens = shell.market_boundary()

    assert lens["status"] == "pass"
    assert (
        lens["schema_version"]
        == "microcosm_public_market_prediction_evidence_boundary_lens_v1"
    )
    assert lens["command"] == "microcosm market-boundary"
    assert lens["endpoint"] == "/market-boundary"
    assert lens["lens_id"] == "public_market_prediction_evidence_boundary_lens"
    assert lens["selected_route_id"] == "market_prediction_evidence_boundary"
    assert lens["boundary_summary"]["row_count"] == 8
    assert lens["boundary_summary"]["source_ref_count"] == 8
    assert lens["boundary_summary"]["owner_route_count"] == 8
    assert lens["boundary_summary"]["validation_ref_count"] == 8
    assert lens["boundary_summary"]["public_rule_count"] == 8
    assert lens["boundary_summary"]["decision_boundary_count"] == 8
    assert lens["boundary_summary"]["negative_case_count"] == 8
    assert lens["boundary_summary"]["live_market_data_authorized_count"] == 0
    assert lens["boundary_summary"]["trading_advice_authorized_count"] == 0
    assert lens["boundary_summary"]["investment_recommendation_authorized_count"] == 0
    assert lens["boundary_summary"]["private_portfolio_export_count"] == 0
    assert lens["boundary_summary"]["performance_guarantee_claim_count"] == 0
    assert lens["boundary_summary"]["release_authorized_count"] == 0
    assert set(lens["negative_case_ids"]) >= {
        "buy_sell_hold_recommendation_rejected",
        "live_price_without_timestamp_rejected",
        "performance_guarantee_rejected",
        "private_portfolio_export_rejected",
        "single_scenario_certainty_rejected",
        "backtest_as_live_performance_rejected",
    }
    assert lens["authority_ceiling"]["synthetic_fixture_only"] is True
    assert lens["authority_ceiling"]["read_model_only"] is True
    assert lens["authority_ceiling"]["live_market_data_authorized"] is False
    assert lens["authority_ceiling"]["trading_advice_authorized"] is False
    assert lens["authority_ceiling"]["financial_advice_authorized"] is False
    assert lens["authority_ceiling"]["investment_recommendation_authorized"] is False
    assert lens["authority_ceiling"]["portfolio_action_authorized"] is False
    assert lens["authority_ceiling"]["private_portfolio_exported"] is False
    assert lens["authority_ceiling"]["private_account_state_exported"] is False
    assert lens["authority_ceiling"]["performance_guarantee_claim"] is False
    assert all(row["source_ref"] for row in lens["boundary_rows"])
    assert all(row["public_rule"] for row in lens["boundary_rows"])
    assert all(row["decision_boundary"] for row in lens["boundary_rows"])
    assert lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert lens["unsafe_payload_bodies_in_receipt"] is False
    assert (
        lens["payload_boundary"]["boundary_id"]
        == "public_market_prediction_evidence_boundary_lens"
    )
    assert lens["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in lens["boundary_rows"]
    )
    assert lens["safe_to_show"]["decision_policy_not_trading_advice"] is True
    assert lens["release_authorized"] is False
    assert "body_redacted" not in lens
    assert (public_root / lens["market_boundary_lens_ref"]).is_file()
    encoded = json.dumps(lens, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_runs_demo_workflow_against_exported_bundles(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    result = shell.run_demo("examples/runtime_shell/demo_project")

    assert result["status"] == "pass"
    assert len(result["events"]) == 42
    assert [event["status"] for event in result["events"]] == ["pass"] * 42
    assert {event["input_mode"] for event in result["events"]} == {
        "exported_substrate_bundle",
        "exported_standards_bundle",
        "exported_evidence_bundle",
        "exported_formal_math_readiness_bundle",
        "exported_corpus_readiness_bundle",
        "exported_tactic_portfolio_availability_bundle",
        "exported_target_shape_tactic_routing_bundle",
        "exported_lean_std_premise_index_bundle",
        "exported_premise_retrieval_bundle",
            "exported_verifier_trace_repair_bundle",
            "exported_evidence_cell_anchor_bundle",
            "exported_symbol_classifier_bundle",
            "exported_ring2_precision_recall_bundle",
            "exported_work_landing_replay_bundle",
            "exported_research_replication_bundle",
            "exported_projection_drift_control_bundle",
            "exported_spatial_world_model_simulation_bundle",
            "exported_materials_lab_safety_bundle",
            "exported_circuit_attribution_bundle",
            "exported_provider_context_budget_bundle",
            "exported_lean_proof_witness_bundle",
            "exported_verifier_lab_kernel_bundle",
            "exported_verifier_lab_execution_spine_bundle",
            "exported_certificate_kernel_execution_lab_bundle",
            "exported_voice_to_doctrine_bundle",
        "exported_route_plane_bundle",
        "exported_mission_transaction_bundle",
        "exported_observability_bundle",
        "exported_assimilation_bundle",
        "exported_public_reveal_bundle",
        "exported_projection_import_bundle",
        "exported_prediction_oracle_bundle",
                "exported_standards_meta_diagnostics_bundle",
                "exported_cold_reader_route_map_bundle",
                "exported_memory_temporal_conflict_bundle",
            "exported_sleeper_memory_poisoning_bundle",
            "exported_mcp_tool_authority_bundle",
            "exported_governed_mutation_authorization_bundle",
            "exported_belief_state_process_reward_bundle",
            "exported_sandbox_policy_escape_bundle",
            "exported_prompt_injection_flow_bundle",
            "exported_patch_proof_bundle",
        }
    for ref in result["evidence_refs"]:
        assert ref.startswith("receipts/runtime_shell/demo_project/organs/")
        assert (public_root / ref).is_file()

    trace = json.loads((public_root / result["trace_ref"]).read_text(encoding="utf-8"))
    assert trace["status"] == "pass"
    assert trace["otel_shape"]["span_count"] == 42
    assert trace["otel_shape"]["metrics"]["runtime_steps_passed"] == 42
    output_text = (public_root / "receipts/runtime_shell/demo_project/demo_project_result.json").read_text(
        encoding="utf-8"
    )
    assert "/Users/" not in output_text
    assert "src/ai_workflow" not in output_text


def test_runtime_shell_route_and_evidence_drilldowns(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)
    result = shell.run_demo()
    work_demo = shell.run_work_demo()

    route = shell.inspect_route("entry_control_packet")
    evidence = shell.inspect_evidence(result["evidence_refs"][0])

    assert route["status"] == "pass"
    assert route["route"]["route_id"] == "sit_entry_control_packet"
    assert route["route"]["row_id"] == "entry_control_packet"
    assert evidence["status"] == "pass"
    assert evidence["receipt"]["status"] == "pass"
    assert evidence["body_in_receipt"] is False
    assert evidence["evidence_contract"]["real_runtime_receipt"] is True
    assert evidence["evidence_contract"]["synthetic_receipt_is_product_evidence"] is False
    assert work_demo["status"] == "pass"
    assert work_demo["evidence_ref"].startswith("receipts/runtime_shell/work_demo/")
    assert work_demo["authority_ceiling"]["live_task_ledger_mutation_authorized"] is False


def test_runtime_shell_serves_observatory_and_status_endpoint(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)
    project = tmp_path / "scratch_project"
    (project / "src/app").mkdir(parents=True)
    (project / "README.md").write_text("# Scratch\n", encoding="utf-8")
    (project / "pyproject.toml").write_text("[project]\nname='scratch'\nversion='0.1.0'\n", encoding="utf-8")
    (project / "src/app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    project_substrate.init_project(project)
    project_substrate.index_project(project)
    project_substrate.propose_routes(project)
    project_substrate.explain_route(project, "readme_onboarding_route")
    created = project_substrate.create_work(project, "readme_onboarding_route")
    project_substrate.run_work(project, str(created["work_id"]))
    server = shell.serve("127.0.0.1", 0, project)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://{host}:{port}/", timeout=20) as response:
            html = response.read().decode("utf-8")
        with urlopen(f"http://{host}:{port}/status", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/spine", timeout=5) as response:
            spine = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/tour", timeout=5) as response:
            tour = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/authority", timeout=5) as response:
            authority = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/prediction", timeout=5) as response:
            prediction = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/market-boundary", timeout=5) as response:
            market_boundary = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/corpus", timeout=5) as response:
            corpus = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/trace", timeout=5) as response:
            trace_lens = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/repair-loop", timeout=5) as response:
            repair_loop = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/evidence-cells", timeout=5) as response:
            evidence_cells = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/proof-loop-depth", timeout=5) as response:
            proof_loop_depth = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/landing-replay", timeout=5) as response:
            landing_replay = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/view-quality", timeout=5) as response:
            view_quality = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/projection-safety", timeout=5) as response:
            projection_safety = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/drift-control", timeout=5) as response:
            projection_drift = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/route-cleanup", timeout=5) as response:
            route_cleanup = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/projection-import-map", timeout=5) as response:
            projection_import_map = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/import-projector", timeout=5) as response:
            import_projector = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/option-surface-lens", timeout=5) as response:
            option_surface = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/stripping-guard", timeout=5) as response:
            stripping_guard = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/standards-control", timeout=5) as response:
            standards_control = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/hook-coverage", timeout=5) as response:
            hook_coverage = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/replay-gauntlet", timeout=5) as response:
            replay_gauntlet = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/benchmark-lab", timeout=5) as response:
            benchmark_lab = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/legibility-scorecard", timeout=5) as response:
            legibility_scorecard = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/intake", timeout=5) as response:
            intake = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/reveal", timeout=5) as response:
            reveal = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/project/python-lens", timeout=5) as response:
            python_lens = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/favicon.ico", timeout=5) as response:
            favicon_status = response.status
        with urlopen(f"http://{host}:{port}/project/observatory", timeout=45) as response:
            observatory = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/project/explain/readme_onboarding_route", timeout=5) as response:
            explanation = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert "Microcosm Observatory" in html
    assert "Causal Chain" in html
    assert "readme_onboarding_route" in html
    assert "repo_has_readme" in html
    assert "reversible_work_transaction" in html
    assert "created -&gt; selected -&gt; planned -&gt; executed_simulation -&gt; closed" in html
    assert "Evidence is drilldown" in html
    assert "Release remains unauthorized" in html
    assert "Python Route Lens" in html
    assert "/project/python-lens" in html
    assert "Payload boundary" in html
    assert "Body redacted" not in html
    assert "Ten-Minute Tour" in html
    assert "/tour" in html
    assert "Spine / Intake / Reveal Bridge" in html
    assert "/spine" in html
    assert "/authority" in html
    assert "/prediction" in html
    assert "/market-boundary" in html
    assert "/corpus" in html
    assert "/trace" in html
    assert "/repair-loop" in html
    assert "/evidence-cells" in html
    assert "/proof-loop-depth" in html
    assert "/landing-replay" in html
    assert "/view-quality" in html
    assert "/projection-safety" in html
    assert "/drift-control" in html
    assert "/route-cleanup" in html
    assert "/projection-import-map" in html
    assert "/import-projector" in html
    assert "/option-surface-lens" in html
    assert "/stripping-guard" in html
    assert "/standards-control" in html
    assert "/hook-coverage" in html
    assert "/replay-gauntlet" in html
    assert "/benchmark-lab" in html
    assert "/legibility-scorecard" in html
    assert "/intake" in html
    assert "/reveal" in html
    assert "Authority Map" in html or "Authority" in html
    assert "Prediction lens" in html or "Prediction" in html
    assert "Market Prediction Boundary Lens" in html
    assert "Corpus Readiness Lens" in html
    assert "Verifier Trace Repair Lens" in html
    assert "Verifier Repair Loop Lens" in html
    assert "Formal Evidence Cell Lens" in html
    assert "Proof Loop Depth Lens" in html
    assert "Work Landing Replay Lens" in html
    assert "View Quality Action Map Lens" in html
    assert "Projection Safety Audit Lens" in html
    assert "Projection Drift Control Lens" in html
    assert "Route Cleanup Contract Lens" in html
    assert "Projection Import Map Lens" in html
    assert "Import Projector Contract Lens" in html
    assert "Compression Profile Option Surface Lens" in html
    assert "Public/Private Stripping Guard Lens" in html
    assert "Standards Control Lens" in html
    assert "Hook Intervention Coverage Lens" in html
    assert "Agent Reliability Replay Gauntlet" in html
    assert "Repository Benchmark Transaction Lab" in html
    assert "Cold Reader Legibility Scorecard" in html
    assert "self_hosted_status_protocol_landed" in html
    assert "Open actionable cells" in html
    assert "<details>" in html
    assert html.find("Causal Chain") < html.find("<pre>")
    assert "/Users/" not in html
    assert "src/ai_workflow" not in html
    assert payload["status"] == "pass"
    assert payload["adapter_backed_organ_count"] == 42
    assert payload["product_path_demoted_organ_count"] == 4
    assert spine["schema_version"] == "microcosm_public_runtime_spine_v1"
    assert tour["schema_version"] == "microcosm_public_ten_minute_tour_v1"
    assert tour["status"] == "pass"
    assert tour["front_door_status"]["blocking_surface_ids"] == []
    assert tour["front_door_status"]["drilldown_blocked_surface_ids"] == [
        "authority",
        "intake",
    ]
    assert authority["schema_version"] == "microcosm_public_authority_map_v2"
    assert authority["authority_ceiling"]["release_authorized"] is False
    assert authority["surface_counts"]["organ_authority_count"] == 42
    assert authority["surface_counts"]["surface_authority_count"] == 45
    assert prediction["schema_version"] == "microcosm_public_prediction_lens_v1"
    assert prediction["authority_ceiling"]["trading_authorized"] is False
    assert (
        market_boundary["schema_version"]
        == "microcosm_public_market_prediction_evidence_boundary_lens_v1"
    )
    assert market_boundary["boundary_summary"]["row_count"] == 8
    assert market_boundary["authority_ceiling"]["trading_advice_authorized"] is False
    assert market_boundary["authority_ceiling"]["private_portfolio_exported"] is False
    assert corpus["schema_version"] == "microcosm_public_corpus_readiness_lens_v1"
    assert corpus["corpus_summary"]["mathlib_lake_project_import_available"] is False
    assert trace_lens["schema_version"] == "microcosm_public_verifier_trace_repair_lens_v1"
    assert trace_lens["authority_ceiling"]["formal_proof_authority"] is False
    assert repair_loop["schema_version"] == "microcosm_public_verifier_repair_loop_lens_v1"
    assert repair_loop["authority_ceiling"]["formal_proof_authority"] is False
    assert repair_loop["repair_loop_summary"]["transition_count"] == 4
    assert evidence_cells["schema_version"] == "microcosm_public_formal_evidence_cell_lens_v1"
    assert evidence_cells["authority_ceiling"]["formal_proof_authority"] is False
    assert evidence_cells["authority_ceiling"]["general_theorem_solution_claim"] is False
    assert proof_loop_depth["schema_version"] == "microcosm_public_proof_loop_depth_lens_v1"
    assert proof_loop_depth["authority_ceiling"]["formal_proof_authority"] is False
    assert proof_loop_depth["authority_ceiling"]["benchmark_score_claim"] is False
    assert proof_loop_depth["proof_loop_summary"]["gate_count"] == 12
    assert landing_replay["schema_version"] == "microcosm_public_work_landing_replay_lens_v1"
    assert landing_replay["authority_ceiling"]["live_git_mutation_authorized"] is False
    assert landing_replay["authority_ceiling"]["broad_checkpoint_authorized"] is False
    assert view_quality["schema_version"] == "microcosm_public_view_quality_action_map_lens_v1"
    assert view_quality["authority_ceiling"]["private_screenshot_paths_exported"] is False
    assert view_quality["action_summary"]["action_row_count"] == 5
    assert projection_safety["schema_version"] == "microcosm_public_projection_safety_audit_lens_v1"
    assert projection_safety["projection_summary"]["private_body_export_count"] == 0
    assert projection_drift["schema_version"] == "microcosm_public_projection_drift_control_lens_v1"
    assert projection_drift["drift_summary"]["row_count"] == 8
    assert projection_drift["authority_ceiling"]["live_route_repair_authorized"] is False
    assert projection_drift["authority_ceiling"]["source_authority_claim"] is False
    assert route_cleanup["schema_version"] == "microcosm_public_route_cleanup_contract_lens_v1"
    assert route_cleanup["cleanup_summary"]["row_count"] == 8
    assert route_cleanup["authority_ceiling"]["route_deletion_authorized"] is False
    assert route_cleanup["authority_ceiling"]["generated_region_hand_edit_authorized"] is False
    assert projection_import_map["schema_version"] == "microcosm_public_projection_import_map_lens_v1"
    assert projection_import_map["map_summary"]["row_count"] == 6
    assert projection_import_map["authority_ceiling"]["automated_import_guarantee"] is False
    assert import_projector["schema_version"] == "microcosm_public_import_projector_contract_lens_v1"
    assert import_projector["projector_summary"]["row_count"] == 9
    assert import_projector["projector_summary"]["private_body_export_count"] == 0
    assert import_projector["authority_ceiling"]["automated_import_execution_authorized"] is False
    assert option_surface["schema_version"] == (
        "microcosm_public_compression_profile_option_surface_lens_v1"
    )
    assert option_surface["option_surface_summary"]["row_count"] == 6
    assert option_surface["option_surface_summary"]["private_body_export_count"] == 0
    assert option_surface["authority_ceiling"]["profile_switch_execution_authorized"] is False
    assert stripping_guard["schema_version"] == "microcosm_public_private_stripping_guard_lens_v1"
    assert stripping_guard["guard_summary"]["guard_row_count"] == 8
    assert stripping_guard["guard_summary"]["private_body_export_count"] == 0
    assert stripping_guard["authority_ceiling"]["secret_detection_completeness_claim"] is False
    assert standards_control["schema_version"] == "microcosm_public_standards_control_lens_v1"
    assert standards_control["standards_summary"]["standards_control_row_count"] == 8
    assert standards_control["standards_summary"]["source_authority_claim_count"] == 0
    assert standards_control["authority_ceiling"]["standards_completeness_claim"] is False
    assert hook_coverage["schema_version"] == "microcosm_public_hook_intervention_coverage_lens_v1"
    assert hook_coverage["coverage_summary"]["intervention_row_count"] == 5
    assert hook_coverage["coverage_summary"]["hook_shadow_case_count"] == 6
    assert hook_coverage["authority_ceiling"]["live_operator_state_read"] is False
    assert replay_gauntlet["schema_version"] == (
        "microcosm_public_agent_reliability_replay_gauntlet_lens_v1"
    )
    assert replay_gauntlet["coverage_summary"]["episode_count"] == 11
    assert replay_gauntlet["authority_ceiling"]["live_agent_execution_authorized"] is False
    assert replay_gauntlet["authority_ceiling"]["complete_security_claim"] is False
    assert benchmark_lab["schema_version"] == (
        "microcosm_public_repository_benchmark_transaction_lab_lens_v1"
    )
    assert benchmark_lab["scorecard"]["task_count"] == 2
    assert benchmark_lab["authority_ceiling"]["live_repo_mutation_authorized"] is False
    assert benchmark_lab["authority_ceiling"]["swe_bench_performance_claim"] is False
    assert legibility_scorecard["schema_version"] == (
        "microcosm_public_cold_reader_legibility_scorecard_lens_v1"
    )
    assert legibility_scorecard["scorecard"]["checkpoint_count"] == 6
    assert legibility_scorecard["authority_ceiling"]["reader_success_guarantee"] is False
    assert intake["schema_version"] == "microcosm_runtime_reveal_import_bridge_v1"
    assert intake["open_actionable_cell_count"] == 0
    assert reveal["schema_version"] == "microcosm_public_reveal_view_v1"
    assert python_lens["schema_version"] == "microcosm_project_python_lens_v1"
    assert python_lens["python_file_count"] == 1
    assert python_lens["ready_route_count"] == 2
    assert python_lens["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert python_lens["unsafe_payload_bodies_in_receipt"] is False
    assert python_lens["payload_boundary"]["boundary_id"] == "project_python_lens_read_model"
    assert python_lens["payload_boundary"]["legacy_schema_compat_present"] is False
    assert python_lens["safe_to_show"]["python_lens_rows_are_public_payload_boundary_rows"] is True
    assert python_lens["legacy_payload_schema_compat"]["legacy_payload_schema_present"] is False
    assert python_lens["legacy_payload_schema_compat"]["legacy_payload_flags_exported"] is False
    assert "legacy_body_redacted_compat_present" not in python_lens
    assert "body_redacted" not in python_lens
    assert "body_redacted" not in json.dumps(python_lens, sort_keys=True)
    assert favicon_status == 204
    assert observatory["status"] == "pass"
    assert observatory["selected_route_id"] == "readme_onboarding_route"
    assert observatory["tour"]["schema_version"] == "microcosm_public_ten_minute_tour_v1"
    assert observatory["authority_map"]["schema_version"] == "microcosm_public_authority_map_v2"
    assert observatory["prediction_lens"]["schema_version"] == "microcosm_public_prediction_lens_v1"
    assert observatory["corpus_lens"]["schema_version"] == "microcosm_public_corpus_readiness_lens_v1"
    assert observatory["trace_lens"]["schema_version"] == "microcosm_public_verifier_trace_repair_lens_v1"
    assert observatory["repair_loop_lens"]["schema_version"] == (
        "microcosm_public_verifier_repair_loop_lens_v1"
    )
    assert observatory["evidence_cell_lens"]["schema_version"] == "microcosm_public_formal_evidence_cell_lens_v1"
    assert observatory["landing_replay_lens"]["schema_version"] == (
        "microcosm_public_work_landing_replay_lens_v1"
    )
    assert observatory["view_quality_lens"]["schema_version"] == (
        "microcosm_public_view_quality_action_map_lens_v1"
    )
    assert observatory["projection_safety_lens"]["schema_version"] == (
        "microcosm_public_projection_safety_audit_lens_v1"
    )
    assert observatory["projection_drift_lens"]["schema_version"] == (
        "microcosm_public_projection_drift_control_lens_v1"
    )
    assert observatory["route_cleanup_lens"]["schema_version"] == (
        "microcosm_public_route_cleanup_contract_lens_v1"
    )
    assert observatory["projection_import_map_lens"]["schema_version"] == (
        "microcosm_public_projection_import_map_lens_v1"
    )
    assert observatory["import_projector_lens"]["schema_version"] == (
        "microcosm_public_import_projector_contract_lens_v1"
    )
    assert observatory["option_surface_lens"]["schema_version"] == (
        "microcosm_public_compression_profile_option_surface_lens_v1"
    )
    assert observatory["stripping_guard_lens"]["schema_version"] == (
        "microcosm_public_private_stripping_guard_lens_v1"
    )
    assert observatory["standards_control_lens"]["schema_version"] == (
        "microcosm_public_standards_control_lens_v1"
    )
    assert observatory["hook_coverage_lens"]["schema_version"] == (
        "microcosm_public_hook_intervention_coverage_lens_v1"
    )
    assert observatory["replay_gauntlet_lens"]["schema_version"] == (
        "microcosm_public_agent_reliability_replay_gauntlet_lens_v1"
    )
    assert observatory["benchmark_lab_lens"]["schema_version"] == (
        "microcosm_public_repository_benchmark_transaction_lab_lens_v1"
    )
    assert observatory["legibility_scorecard_lens"]["schema_version"] == (
        "microcosm_public_cold_reader_legibility_scorecard_lens_v1"
    )
    assert observatory["python_lens"]["schema_version"] == "microcosm_project_python_lens_v1"
    assert observatory["python_lens"]["python_file_count"] == 1
    assert observatory["python_lens"]["ready_route_count"] == 2
    assert observatory["python_lens"]["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert observatory["python_lens"]["payload_boundary"]["boundary_id"] == (
        "project_python_lens_read_model"
    )
    assert observatory["python_lens"]["legacy_payload_schema_compat"][
        "legacy_payload_flags_exported"
    ] is False
    assert "legacy_body_redacted_compat_present" not in observatory["python_lens"]
    assert "body_redacted" not in observatory["python_lens"]
    assert "body_redacted" not in json.dumps(observatory["python_lens"], sort_keys=True)
    assert observatory["runtime_bridge"]["bridge_id"] == "intake_observatory_bridge"
    assert observatory["runtime_bridge"]["open_actionable_cell_count"] == 0
    assert observatory["runtime_bridge"]["projection_status_counts"] == {
        "public_runtime_import_landed": 14,
        "runtime_bridge_landed": 1,
        "self_hosted_status_protocol_landed": 1,
    }
    assert observatory["causal_chain"]["work_transaction"]["work_id"] == "work_0001"
    assert explanation["status"] == "pass"
    assert explanation["route_id"] == "readme_onboarding_route"


def test_runtime_shell_reveal_projects_ten_minute_board(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    reveal = shell.reveal()

    assert reveal["status"] == "pass"
    assert reveal["step_count"] == 5
    assert reveal["command_count"] >= 4
    assert reveal["evidence_ref_count"] >= 4
    assert reveal["reveal_board"]["release_authorized"] is False
    assert reveal["evidence_strength_policy"]["source_ref"] == "core/organ_evidence_classes.json"
    assert (
        reveal["evidence_strength_policy"]["accepted_status_is_not_evidence_strength"]
        is True
    )
    assert (
        reveal["evidence_strength_policy"]["unclassified_organs_block_authority_projection"]
        is True
    )
    assert reveal["evidence_strength_policy"]["evidence_class_counts"] == {
        "semantic_validator": 15,
        "algorithmic_projection": 23,
        "external_subprocess_witness": 3,
        "verified_macro_body_import": 1,
    }
    assert reveal["public_claim"].startswith("Microcosm turns a repo")
    assert (public_root / reveal["evidence_ref"]).is_file()


def test_runtime_shell_intake_projects_reveal_import_bridge(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    intake = shell.intake()

    assert intake["status"] == "pass"
    assert intake["schema_version"] == "microcosm_runtime_reveal_import_bridge_v1"
    assert intake["bridge_id"] == "runtime_reveal_import_bridge"
    assert intake["projection_cell_count"] == 15
    assert [step["command"] for step in intake["first_run_bridge"]] == [
        "microcosm compile <project>",
        "microcosm spine",
        "microcosm intake",
        "microcosm reveal",
        "microcosm evidence inspect <receipt>",
    ]
    by_cell = {row["cell_id"]: row for row in intake["cell_status"]}
    assert set(by_cell) == {
        "agent_execution_trace_refactor",
        "agent_observability_store_import",
        "agent_trace_route_repair_observability_import",
        "agent_session_attribution_import",
        "controller_continuity_heartbeat_import",
        "finance_eval_source_modules_import",
        "formal_math_readiness_extensions",
        "multi_agent_fanin_replay_import",
        "navigation_route_plane_import",
        "projection_protocol_self_host",
        "runtime_reveal_import_bridge",
        "task_ledger_control_source_modules_import",
        "work_landing_control_source_modules_import",
        "work_ledger_control_source_modules_import",
        "command_output_projection_source_modules_import",
    }
    assert by_cell["formal_math_readiness_extensions"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["projection_protocol_self_host"]["projection_status"] == (
        "self_hosted_status_protocol_landed"
    )
    assert by_cell["projection_protocol_self_host"]["action_required"] is False
    assert by_cell["runtime_reveal_import_bridge"]["projection_status"] == "runtime_bridge_landed"
    assert by_cell["runtime_reveal_import_bridge"]["runtime_bridge_status"] == "landed_as_microcosm_intake"
    assert by_cell["agent_execution_trace_refactor"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_execution_trace_refactor"]["runtime_bridge_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_execution_trace_refactor"]["action_required"] is False
    assert by_cell["agent_trace_route_repair_observability_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["agent_trace_route_repair_observability_import"][
        "runtime_bridge_status"
    ] == "public_runtime_import_landed"
    assert by_cell["agent_trace_route_repair_observability_import"][
        "action_required"
    ] is False
    assert by_cell["agent_observability_store_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_observability_store_import"]["runtime_bridge_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_observability_store_import"]["action_required"] is False
    assert by_cell["agent_session_attribution_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_session_attribution_import"]["runtime_bridge_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_session_attribution_import"]["action_required"] is False
    assert by_cell["navigation_route_plane_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["navigation_route_plane_import"]["runtime_bridge_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["navigation_route_plane_import"]["action_required"] is False
    assert by_cell["finance_eval_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["finance_eval_source_modules_import"]["runtime_bridge_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["finance_eval_source_modules_import"]["action_required"] is False
    assert by_cell["work_landing_control_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["work_landing_control_source_modules_import"]["runtime_bridge_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["work_landing_control_source_modules_import"]["action_required"] is False
    assert by_cell["command_output_projection_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["command_output_projection_source_modules_import"][
        "runtime_bridge_status"
    ] == "public_runtime_import_landed"
    assert (
        by_cell["command_output_projection_source_modules_import"]["action_required"]
        is False
    )
    assert intake["projection_status_counts"] == {
        "public_runtime_import_landed": 13,
        "runtime_bridge_landed": 1,
        "self_hosted_status_protocol_landed": 1,
    }
    assert intake["open_actionable_cell_count"] == 0
    assert intake["authority_ceiling"]["release_authorized"] is False
    assert intake["authority_ceiling"]["credential_or_account_bound_bodies_exported"] is False
    assert intake["body_in_receipt"] is False
    assert all(row["body_in_receipt"] is False for row in intake["cell_status"])
    assert all("body_redacted" not in row for row in intake["cell_status"])
    for ref in intake["runtime_bridge_evidence_refs"][:2]:
        assert (public_root / ref).is_file()
    encoded = json.dumps(intake, sort_keys=True)
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded


def test_runtime_shell_observatory_intake_bridge_uses_payload_boundary(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    bridge = shell.observatory_intake_bridge()

    assert bridge["status"] == "pass"
    assert bridge["schema_version"] == "microcosm_observatory_intake_bridge_v1"
    assert bridge["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert bridge["unsafe_payload_bodies_in_receipt"] is False
    assert bridge["payload_boundary"]["boundary_id"] == "public_observatory_intake_bridge"
    assert bridge["payload_boundary"]["source_open_default"] is True
    assert (
        bridge["safe_to_show"]["observatory_bridge_rows_are_public_payload_boundary_rows"]
        is True
    )
    assert bridge["safe_to_show"]["private_browser_or_live_access_payloads_omitted"] is True
    assert "body_redacted" not in bridge
    encoded = json.dumps(bridge, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "public_replacement_ref" not in encoded
    assert "/Users/" not in encoded
    assert "src/ai_workflow" not in encoded
