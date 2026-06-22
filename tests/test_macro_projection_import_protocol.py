from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_computer_use_trace,
)
from microcosm_core.macro_tools.agent_trace_route_repair import (
    build_public_agent_trace_route_repair_view,
    load_public_agent_trace_route_repair_bundle,
)
from microcosm_core.macro_tools.agent_observability_store import (
    build_public_agent_observability_store_view,
    load_public_agent_observability_store_bundle,
)
from microcosm_core.macro_tools.finance_eval_spine import (
    REQUIRED_MODULES as FINANCE_EVAL_REQUIRED_MODULES,
)
from microcosm_core.organs.agent_route_observability_runtime import (
    run_agent_observability_store_bundle,
    run_agent_trace_route_repair_bundle,
    run_bridge_dispatch_yield_resume_bundle,
    run_controller_heartbeat_bundle,
    run_multi_agent_fanin_bundle,
    run_session_attribution_bundle,
)
from microcosm_core.macro_tools.work_landing import (
    build_public_work_landing_reconcile_plan,
    build_public_work_landing_status,
    build_public_workitem_write_admission,
)
from microcosm_core.organs import macro_projection_import_protocol
from microcosm_core.organs.macro_projection_import_protocol import (
    EXPECTED_NEGATIVE_CASES,
    preview_import_plan,
    run,
    run_projection_bundle,
    refresh_exact_copy_source_modules,
    validate_import_plan,
    validate_projection_protocol,
)
from microcosm_core.receipts import normalize_public_receipt_paths
from microcosm_core.runtime_shell import PRODUCT_PATH_DEMOTED_ORGAN_IDS
from microcosm_core.secret_exclusion_scan import public_relative_path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/macro_projection_import_protocol/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
)
PRIVATE_HOME_PREFIX = "/" + "Users" + "/"
OPERATOR_HOME_SAMPLE = PRIVATE_HOME_PREFIX + "example"
COMPUTER_USE_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_computer_use_action_trace_bundle"
)
SESSION_ATTRIBUTION_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_session_attribution_bundle"
)
MULTI_AGENT_FANIN_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_multi_agent_fanin_replay_bundle"
)
BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_bridge_dispatch_yield_resume_bundle"
)
CONTROLLER_HEARTBEAT_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_controller_heartbeat_bundle"
)
AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_agent_trace_route_repair_bundle"
)
AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_agent_observability_store_bundle"
)


def _accepted_organ_count() -> int:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    return len(
        [
            row
            for row in registry["implemented_organs"]
            if row.get("status") == "accepted_current_authority"
        ]
    )


def _adapter_backed_organ_count() -> int:
    return _accepted_organ_count() - len(PRODUCT_PATH_DEMOTED_ORGAN_IDS)
ROUTE_PLANE_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/navigation_hologram_route_plane/exported_route_plane_bundle"
)
ROUTE_PLANE_BODY_MATERIAL_IDS = [
    "navigation_route_plane_body_import",
    "navigation_route_plane_intervention_source_body_import",
    "navigation_route_plane_context_pack_source_body_import",
    "navigation_route_plane_entry_packet_source_body_import",
    "navigation_route_plane_option_surface_source_body_import",
    "navigation_route_plane_navigation_contract_source_body_import",
]
FINANCE_EVAL_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/finance_forecast_evaluation_spine/exported_finance_eval_bundle"
)
DEPENDENCY_PREFLIGHT_RECEIPT = (
    MICROCOSM_ROOT / "receipts/preflight/dependency_preflight.json"
)
FINANCE_EVAL_BODY_MATERIAL_IDS = [
    f"finance_{Path(module).stem}_body_import"
    for module in FINANCE_EVAL_REQUIRED_MODULES
]
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
CHECKPOINT_LANE_BODY_MATERIAL_IDS = [
    "checkpoint_script_body_import",
    "checkpoint_private_backup_body_import",
]
COMMAND_OUTPUT_PROJECTION_BODY_MATERIAL_IDS = [
    "command_output_projection_helper_body_import",
    "command_output_sidecar_helper_body_import",
    "command_output_audit_body_import",
    "command_output_projection_standard_body_import",
]
TRACE_CAPSULE_BODY_MATERIAL_IDS = [
    "trace_capsule_cli_prompt_trace_body_import",
    "trace_capsule_cli_prompt_trace_test_body_import",
    "agent_trace_structurer_parser_body_import",
    "agent_trace_structurer_parser_test_body_import",
]
ROUTE_SELECTION_CONTROL_BODY_MATERIAL_IDS = [
    "route_selection_intervention_body_import",
    "route_selection_context_pack_body_import",
    "route_selection_entry_packet_body_import",
    "route_selection_option_surface_body_import",
    "route_selection_navigation_contract_standard_body_import",
]
ROUTE_WORKER_PACKET_BODY_MATERIAL_IDS = [
    "route_worker_node_card_builder_body_import",
    "route_worker_candidate_builder_body_import",
    "route_worker_graph_ranker_body_import",
    "route_worker_discovery_edc_body_import",
    "route_worker_verb_correction_body_import",
    "route_worker_nvidia_hints_body_import",
    "route_worker_packet_test_body_import",
]
ROUTE_OPERATOR_COURT_BODY_MATERIAL_IDS = [
    "route_operator_court_body_import",
    "routing_pilot_harness_body_import",
    "route_operator_court_test_body_import",
]
ROUTE_DISCOVERY_CONFIRMATION_BODY_MATERIAL_IDS = [
    "route_discovery_confirmation_body_import",
]
PROJECTION_LOSS_AUDIT_BODY_MATERIAL_IDS = [
    "projection_loss_audit_body_import",
]
SEMANTIC_ROUTE_QUALITY_AUDIT_BODY_MATERIAL_IDS = [
    "semantic_route_quality_audit_body_import",
]
REACTION_WIRING_BODY_MATERIAL_IDS = [
    "reaction_wiring_config_body_import",
    "reaction_wiring_engine_body_import",
    "reaction_wiring_proof_cli_body_import",
]
NAVIGATION_CONTEXT_ROSETTA_BODY_MATERIAL_IDS = [
    "navigation_context_rosetta_body_import",
    "kind_band_contract_audit_body_import",
    "navigation_context_rosetta_test_body_import",
    "navigation_rosetta_grammar_standard_body_import",
    "navigation_rosetta_math_paper_body_import",
]
BOOTSTRAP_ROUTE_SURFACE_BODY_MATERIAL_IDS = [
    "bootstrap_agent_bootstrap_live_body_import",
    "bootstrap_routing_hologram_body_import",
    "bootstrap_agent_bootstrap_projection_body_import",
    "bootstrap_routing_projection_body_import",
]
AGENT_OPERATING_PACKET_BODY_MATERIAL_IDS = [
    "agent_operating_packet_sidecar_body_import",
    "agent_operating_packet_projection_body_import",
]
ACTIVE_EXECUTION_CONSTELLATION_BODY_MATERIAL_IDS = [
    "active_execution_constellation_projection_body_import",
    "active_execution_constellation_test_body_import",
]
TASK_LEDGER_STARTUP_PRESSURE_BODY_MATERIAL_IDS = [
    "task_ledger_priority_scheduler_body_import",
    "task_ledger_navigation_command_body_import",
    "task_ledger_priority_scheduler_test_body_import",
    "task_ledger_cap_reflex_playbook_body_import",
]
EXECUTABLE_GRAMMAR_METABOLISM_BODY_MATERIAL_IDS = [
    "executable_grammar_metabolism_readme_body_import",
    "executable_grammar_metabolism_board_body_import",
    "executable_grammar_metabolism_receipt_body_import",
]
NAVIGATION_COVERAGE_MATRIX_BODY_MATERIAL_IDS = [
    "navigation_coverage_matrix_projection_body_import",
    "navigation_coverage_matrix_test_body_import",
]
NAVIGATION_METABOLISM_LEDGER_BODY_MATERIAL_IDS = [
    "navigation_metabolism_ledger_projection_body_import",
    "navigation_metabolism_ledger_test_body_import",
]
NAVIGATION_SURFACE_AUDIT_BODY_MATERIAL_IDS = [
    "navigation_surface_audit_projection_body_import",
    "navigation_surface_contracts_body_import",
    "navigation_surface_audit_test_body_import",
]
COMMAND_NODE_CACHE_BODY_MATERIAL_IDS = [
    "command_node_cache_body_import",
    "pulse_cache_body_import",
    "command_node_cache_test_body_import",
]
WORK_ADMISSION_BODY_MATERIAL_IDS = [
    "work_admission_body_import",
    "work_admission_test_body_import",
]
NAVIGATION_CLUSTERABILITY_BODY_MATERIAL_IDS = [
    "navigation_clusterability_body_import",
    "navigation_clusterability_test_body_import",
]
ANNEX_ROUTING_COVERAGE_BODY_MATERIAL_IDS = [
    "annex_routing_coverage_body_import",
    "annex_routing_coverage_test_body_import",
]
ANNEX_CURRENTNESS_BODY_MATERIAL_IDS = [
    "annex_currentness_body_import",
    "annex_currentness_test_body_import",
]
ENTRYPOINT_HEALTH_BODY_MATERIAL_IDS = [
    "entrypoint_health_body_import",
    "entrypoint_health_test_body_import",
]
AGENT_ENTRYPOINT_AUDIT_BODY_MATERIAL_IDS = [
    "agent_entrypoint_audit_body_import",
    "agent_entrypoint_audit_test_body_import",
]
NAVIGATION_FITNESS_BODY_MATERIAL_IDS = [
    "navigation_fitness_body_import",
    "navigation_fitness_test_body_import",
]
DYNAMIC_PAPER_LATTICE_BODY_MATERIAL_IDS = [
    "dynamic_paper_lattice_body_import",
    "dynamic_paper_lattice_test_body_import",
]
KIND_ATLAS_BODY_MATERIAL_IDS = [
    "kind_atlas_body_import",
    "kind_atlas_test_body_import",
]
SEMANTIC_ROUTING_BODY_MATERIAL_IDS = [
    "semantic_routing_body_import",
    "semantic_routing_test_body_import",
]
EMBEDDING_SUBSTRATE_BODY_MATERIAL_IDS = [
    "embedding_substrate_body_import",
    "embedding_sources_body_import",
    "embedding_substrate_test_body_import",
]
NVIDIA_NIM_PROVIDER_BOUNDARY_BODY_MATERIAL_IDS = [
    "nvidia_nim_provider_adapter_body_import",
    "nvidia_model_profile_registry_body_import",
]
AGENT_PROVIDER_ROUTER_BODY_MATERIAL_IDS = [
    "agent_provider_router_body_import",
    "openrouter_free_runtime_body_import",
]
BRIDGE_ROUTE_CONFIG_BODY_MATERIAL_IDS = [
    "bridge_routes_body_import",
    "bridge_routes_test_body_import",
]
KERNEL_BRIDGE_CONFIG_BODY_MATERIAL_IDS = [
    "kernel_bridge_config_body_import",
    "kernel_bridge_state_body_import",
    "kernel_bridge_config_parity_test_body_import",
]
OBSERVE_RUNTIME_BODY_MATERIAL_IDS = [
    "codex_paths_body_import",
    "markdown_routing_body_import",
    "observe_memory_body_import",
    "observe_surfaces_body_import",
    "observe_runtime_body_import",
]
KERNEL_STATE_REGISTRY_BODY_MATERIAL_IDS = [
    "observe_assets_body_import",
    "standards_registry_body_import",
]
AGENT_EXECUTION_TRACE_SOURCE_BODY_MATERIAL_IDS = [
    "agent_execution_trace_source_body_import",
    "strict_json_source_body_import",
    "agent_execution_trace_test_body_import",
    "agent_execution_trace_standard_body_import",
]
AGENT_OBSERVABILITY_SOURCE_BODY_MATERIAL_IDS = [
    "agent_observability_source_body_import",
    "agent_observability_test_body_import",
]
AGENT_OBSERVABILITY_ANIMATION_SOURCE_BODY_MATERIAL_IDS = [
    "agent_observability_animation_source_body_import",
    "agent_observability_animation_coverage_body_import",
    "agent_session_attribution_source_body_import",
    "agent_observability_animation_test_body_import",
    "agent_observability_animation_coverage_test_body_import",
    "agent_session_attribution_test_body_import",
]
AGENT_OBSERVABILITY_CLASSIFICATION_SOURCE_BODY_MATERIAL_IDS = [
    "agent_observability_classification_source_body_import",
]
AGENT_MISSION_STATUS_SOURCE_BODY_MATERIAL_IDS = [
    "agent_mission_status_source_body_import",
    "agent_mission_status_test_body_import",
]
OPERATOR_HANDOFF_LINKAGE_SOURCE_BODY_MATERIAL_IDS = [
    "operator_handoff_linkage_source_body_import",
    "operator_handoff_prompt_fingerprints_dependency_body_import",
    "operator_handoff_linkage_test_body_import",
]
PROMPT_SHELF_MOVEMENT_SOURCE_BODY_MATERIAL_IDS = [
    "prompt_shelf_movement_index_body_import",
    "prompt_shelf_movement_index_test_body_import",
]
PROMPT_SHELF_UPPROPAGATION_SOURCE_BODY_MATERIAL_IDS = [
    "prompt_shelf_uppropagation_index_body_import",
    "prompt_shelf_uppropagation_index_test_body_import",
]
PROMPT_SHELF_UPPROPAGATION_DIGEST_SOURCE_BODY_MATERIAL_IDS = [
    "prompt_shelf_uppropagation_digest_body_import",
    "prompt_shelf_uppropagation_digest_test_body_import",
]
PROMPT_SHELF_RUNS_INDEX_SOURCE_BODY_MATERIAL_IDS = [
    "prompt_shelf_runs_index_body_import",
    "b3_packet_lint_dependency_body_import",
    "prompt_shelf_runs_index_test_body_import",
]
STANDARD_OPTION_SURFACE_SOURCE_BODY_MATERIAL_IDS = [
    "standard_option_surface_body_import",
    "standard_option_surface_test_body_import",
]
BRIDGE_RUNTIME_CONTINUITY_SOURCE_BODY_MATERIAL_IDS = [
    "bridge_resume_source_body_import",
    "controller_heartbeat_source_body_import",
    "continuation_packet_source_body_import",
    "bridge_resume_test_body_import",
    "controller_heartbeat_test_body_import",
    "continuation_packet_test_body_import",
]
AGENT_ROUTE_FANIN_CONTINUATION_SOURCE_BODY_MATERIAL_IDS = [
    "agent_route_fanin_continuation_source_body_import",
]
AGENT_ROUTE_SESSION_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS = [
    "agent_route_session_attribution_source_body_import",
]
SESSION_HEARTBEAT_SOURCE_BODY_MATERIAL_IDS = [
    "session_heartbeat_source_body_import",
    "session_heartbeat_test_body_import",
]
ORCHESTRATION_OVERNIGHT_CONTROL_SOURCE_BODY_MATERIAL_IDS = [
    "orchestration_control_body_import",
    "pipeline_advance_control_body_import",
    "pipeline_overnight_control_body_import",
    "overnight_control_launcher_body_import",
    "pipeline_advance_test_body_import",
    "pipeline_overnight_test_body_import",
    "orchestration_control_test_body_import",
]
SEED_DISTILLATION_SUBAGENT_LANE_SOURCE_BODY_MATERIAL_IDS = [
    "seed_distillation_subagent_lane_body_import",
    "seed_distillation_subagent_lane_test_body_import",
]
SEED_DISTILLATION_DEPENDENCY_SOURCE_BODY_MATERIAL_IDS = [
    "seed_atomization_body_import",
    "seed_distillation_body_import",
    "seed_registry_body_import",
    "seed_distillation_validator_body_import",
    "seed_paragraph_ledger_body_import",
    "seed_attempt_recovery_body_import",
    "seed_attempt_recovery_test_body_import",
]
ARTIFACT_PROJECTION_DEBT_SOURCE_BODY_MATERIAL_IDS = [
    "artifact_projection_debt_body_import",
    "artifact_projection_debt_test_body_import",
]
NAVIGATION_TRACE_SOURCE_BODY_MATERIAL_IDS = [
    "navigation_trace_source_body_import",
    "navigation_trace_test_body_import",
]
GENERATED_PROJECTION_CONTROL_SOURCE_BODY_MATERIAL_IDS = [
    "generated_projection_registry_body_import",
    "generated_state_drainer_body_import",
    "generated_state_drainer_test_body_import",
    "generated_state_drainer_cli_compact_test_body_import",
]
SHARED_WORKTREE_GUARD_SOURCE_BODY_MATERIAL_IDS = [
    "shared_worktree_guard_body_import",
    "shared_worktree_guard_test_body_import",
]
RAW_GIT_COMMIT_GUARD_SOURCE_BODY_MATERIAL_IDS = [
    "raw_git_runtime_hook_body_import",
    "raw_git_run_git_guard_body_import",
    "raw_git_pre_commit_hook_body_import",
    "raw_git_prepare_commit_msg_hook_body_import",
    "raw_git_commit_guard_test_body_import",
]
FORMAL_MATH_PROOFLINE_SPINE_SOURCE_BODY_MATERIAL_IDS = [
    "formal_math_proofline_spine_body_import",
    "formal_math_proof_repair_lane_body_import",
    "formal_math_proofline_spine_test_body_import",
    "formal_math_proof_repair_lane_test_body_import",
]
TARGET_SHAPE_TACTIC_ROUTING_BODY_MATERIAL_IDS = [
    "target_shape_ring2_premise_run_summary_body_import",
    "target_shape_ring2_failure_taxonomy_body_import",
    "target_shape_ring2_graph_update_candidates_body_import",
    "target_shape_ring2_oracle_repair_summary_body_import",
]
RING2_PREMISE_RETRIEVAL_BODY_MATERIAL_IDS = [
    "ring2_premise_retrieval_aggregate_report_body_import",
    "ring2_premise_retrieval_run_summary_body_import",
    "ring2_premise_retrieval_graph_variant_comparison_body_import",
    "ring2_premise_retrieval_problem_source_manifest_body_import",
]
PROOF_DIAGNOSTIC_RING2_RUNTIME_BODY_MATERIAL_IDS = [
    "proof_diagnostic_ring2_root_aggregate_report_body_import",
    "proof_diagnostic_ring2_premise_aggregate_report_body_import",
    "proof_diagnostic_ring2_premise_cost_metrics_body_import",
    "proof_diagnostic_ring2_premise_graph_variant_body_import",
    "proof_diagnostic_ring2_premise_run_summary_body_import",
    "proof_diagnostic_ring2_premise_failure_taxonomy_body_import",
    "proof_diagnostic_ring2_premise_graph_update_body_import",
    "proof_diagnostic_ring2_oracle_aggregate_report_body_import",
    "proof_diagnostic_ring2_oracle_cost_metrics_body_import",
    "proof_diagnostic_ring2_oracle_failure_taxonomy_body_import",
    "proof_diagnostic_ring2_oracle_graph_update_body_import",
    "proof_diagnostic_ring2_oracle_graph_variant_body_import",
    "proof_diagnostic_ring2_oracle_run_summary_body_import",
]
PROVIDER_CONTEXT_SOURCE_BODY_MATERIAL_IDS = [
    "provider_context_batch_calibration_report_body_import",
    "provider_context_compute_provider_standard_body_import",
    "provider_context_formal_ladder_eval_body_import",
    "provider_context_graph_benchmark_body_import",
    "provider_context_provider_adapter_standard_body_import",
    "provider_context_provider_navigation_transform_receipt_standard_body_import",
    "provider_context_receipt_reducer_body_import",
    "provider_context_transform_job_standard_body_import",
]
PROVIDER_CONTEXT_SOURCE_BODY_MATERIAL_CLASSES = {
    "provider_context_compute_provider_standard_body_import": "public_macro_standard_body",
    "provider_context_provider_adapter_standard_body_import": "public_macro_standard_body",
    "provider_context_provider_navigation_transform_receipt_standard_body_import": (
        "public_macro_standard_body"
    ),
    "provider_context_transform_job_standard_body_import": "public_macro_standard_body",
}
WORLD_MODEL_PROJECTION_DRIFT_SOURCE_BODY_MATERIAL_IDS = [
    "world_model_drift_aggregate_source_body_import",
    "world_model_drift_endpoint_source_body_import",
    "view_quality_action_map_source_body_import",
    "view_quality_action_map_test_body_import",
]
SPATIAL_WORLD_MODEL_SOURCE_BODY_MATERIAL_IDS = [
    "station_geometry_checker_source_body_import",
    "station_geometry_checker_test_body_import",
    "station_geometry_build_wiring_source_body_import",
]
MECHANISTIC_ORACLE_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS = [
    "mechanistic_oracle_attribution_legacy_node_body_import",
    "mechanistic_oracle_attribution_substrate_node_body_import",
]


def _copy_dependency_preflight_receipt(public_root: Path) -> Path:
    receipt = public_root / "receipts/preflight/dependency_preflight.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEPENDENCY_PREFLIGHT_RECEIPT, receipt)
    return receipt


def _align_organ_registry_to_dependency_preflight(public_root: Path) -> None:
    receipt = json.loads(
        (public_root / "receipts/preflight/dependency_preflight.json").read_text(
            encoding="utf-8"
        )
    )
    expected_count = receipt["organ_lifecycle_coverage"]["coverage_counts"][
        "accepted_organ_count"
    ]
    registry_path = public_root / "core/organ_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    accepted_rows = [
        row
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]
    keep_ids = {row["organ_id"] for row in accepted_rows[:expected_count]}
    registry["implemented_organs"] = [
        row
        for row in registry["implemented_organs"]
        if row.get("status") != "accepted_current_authority" or row["organ_id"] in keep_ids
    ]
    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _copy_public_file(public_root: Path, rel_path: str) -> None:
    destination = public_root / rel_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MICROCOSM_ROOT / rel_path, destination)


def _copy_macro_projection_public_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/macro_projection_import_protocol",
        public_root / "fixtures/first_wave/macro_projection_import_protocol",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/macro_projection_import_protocol",
        public_root / "examples/macro_projection_import_protocol",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/target_shape_tactic_routing_gate",
        public_root / "examples/target_shape_tactic_routing_gate",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/ring2_premise_retrieval_precision_recall_harness",
        public_root / "examples/ring2_premise_retrieval_precision_recall_harness",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/proof_diagnostic_evidence_spine",
        public_root / "examples/proof_diagnostic_evidence_spine",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
        public_root / "examples/provider_context_recipe_budget_policy",
    )
    _copy_public_file(
        public_root,
        "src/microcosm_core/organs/mission_transaction_work_spine.py",
    )
    _copy_public_file(public_root, "src/microcosm_core/macro_tools/__init__.py")
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/agent_execution_trace.py",
    )
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/agent_trace_route_repair.py",
    )
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/agent_observability_store.py",
    )
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/agent_session_attribution.py",
    )
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/continuation_packet.py",
    )
    _copy_public_file(public_root, "src/microcosm_core/macro_tools/bridge_resume.py")
    _copy_public_file(public_root, "src/microcosm_core/macro_tools/controller_heartbeat.py")
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/command_output_projection.py",
    )
    _copy_public_file(
        public_root,
        "src/microcosm_core/macro_tools/command_output_sidecar.py",
    )
    _copy_public_file(public_root, "src/microcosm_core/macro_tools/work_landing.py")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/navigation_hologram_route_plane",
        public_root / "examples/navigation_hologram_route_plane",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/finance_forecast_evaluation_spine",
        public_root / "examples/finance_forecast_evaluation_spine",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/work_landing_control_spine",
        public_root / "examples/work_landing_control_spine",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mission_transaction_work_spine",
        public_root / "examples/mission_transaction_work_spine",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/world_model_projection_drift_control_room",
        public_root / "examples/world_model_projection_drift_control_room",
    )
    _copy_public_file(
        public_root,
        "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle/"
        "lake_project/MicrocosmProofWitness/CertificateKernel.lean",
    )
    _copy_dependency_preflight_receipt(public_root)
    _align_organ_registry_to_dependency_preflight(public_root)
    return public_root


_MACRO_PROJECTION_BUNDLE_TEMP: tempfile.TemporaryDirectory[str] | None = None
_MACRO_PROJECTION_BUNDLE_RUN: dict[str, Any] | None = None


def _macro_projection_bundle_run() -> dict[str, Any]:
    global _MACRO_PROJECTION_BUNDLE_TEMP
    global _MACRO_PROJECTION_BUNDLE_RUN
    if _MACRO_PROJECTION_BUNDLE_RUN is not None:
        return _MACRO_PROJECTION_BUNDLE_RUN
    _MACRO_PROJECTION_BUNDLE_TEMP = tempfile.TemporaryDirectory(
        prefix="macro_projection_bundle_run_"
    )
    temp_root = Path(_MACRO_PROJECTION_BUNDLE_TEMP.name)
    public_root = _copy_macro_projection_public_tree(temp_root)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        temp_root / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )
    _MACRO_PROJECTION_BUNDLE_RUN = {
        "public_root": public_root,
        "result": result,
    }
    return _MACRO_PROJECTION_BUNDLE_RUN


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


def test_macro_projection_sha256_digest_streams_without_read_bytes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "large_source_module.py"
    body = b"macro projection body import\n" * 8192
    source.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self == source:
            raise AssertionError("macro projection digest must stream")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert macro_projection_import_protocol._sha256_digest(source) == (
        "sha256:" + hashlib.sha256(body).hexdigest()
    )


def test_source_ref_candidates_prefer_macro_root_for_macro_only_refs(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    public_tool = public_root / "tools/meta/factory/task_ledger_apply.py"
    macro_tool = tmp_path / "tools/meta/factory/task_ledger_apply.py"
    public_source = public_root / "src/microcosm_core/organs/example.py"
    macro_source = tmp_path / "src/microcosm_core/organs/example.py"
    for path in (public_tool, macro_tool, public_source, macro_source):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(path.as_posix(), encoding="utf-8")

    macro_candidates = macro_projection_import_protocol._source_ref_file_candidates(
        "tools/meta/factory/task_ledger_apply.py",
        public_root=public_root,
    )
    public_candidates = macro_projection_import_protocol._source_ref_file_candidates(
        "src/microcosm_core/organs/example.py",
        public_root=public_root,
    )

    assert macro_candidates[:2] == [macro_tool, public_tool]
    assert public_candidates[:2] == [public_source, macro_source]


def _assert_source_digest_matches_import_contract(
    *,
    row: dict[str, Any],
    result: dict[str, Any],
    source: Path,
    target: Path,
) -> None:
    target_digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    recorded_source_digest = row["body_import_verification"]["source_body_digest"]

    assert row["body_digest"] == target_digest
    assert row["body_import_verification"]["target_body_digest"] == target_digest
    if recorded_source_digest == source_digest:
        return

    drift_rows = {
        drift_row["material_id"]: drift_row
        for drift_row in result.get("live_source_drift_rows", [])
    }
    drift = drift_rows.get(row["material_id"])
    if drift is None:
        assert recorded_source_digest == target_digest
        return
    assert drift["status"] == "live_source_drift_not_import_proof_failure"
    assert drift["recorded_source_body_digest"] == recorded_source_digest
    assert drift["current_source_body_digest"] == source_digest
    assert recorded_source_digest == target_digest


def _assert_public_safe_verification_mode(row: dict[str, Any]) -> None:
    verification = row["body_import_verification"]
    mode = verification["verification_mode"]
    relation = verification.get("source_to_target_relation")
    assert mode in {"exact_source_digest_match", "verified_light_edit_recipe"}
    if mode == "exact_source_digest_match":
        assert relation in (
            macro_projection_import_protocol.EXACT_COPY_SOURCE_TO_TARGET_RELATIONS
        )
    else:
        assert relation in (
            macro_projection_import_protocol.VERIFIED_LIGHT_EDIT_SOURCE_TO_TARGET_RELATIONS
        )


def test_macro_projection_import_bundle_manifest_lists_every_source_module_manifest() -> None:
    bundle_manifest = json.loads(
        (BUNDLE_INPUT / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    input_names = set(bundle_manifest["inputs"])
    source_manifest_names = {
        path.name for path in BUNDLE_INPUT.glob("*source_module_manifest.json")
    }

    assert len(bundle_manifest["inputs"]) == len(input_names)
    assert source_manifest_names <= input_names


def test_source_module_manifest_paths_all_examples_streams_without_recursive_glob(
    monkeypatch,
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    input_path = public_root / "examples/z_bundle"
    manifest_paths = [
        input_path / "source_module_manifest.json",
        input_path / "z_source_module_manifest.json",
        public_root / "examples/a_bundle/source_module_manifest.json",
        public_root / "examples/mid/nested/custom_source_module_manifest.json",
    ]
    for path in manifest_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"modules": []}\n', encoding="utf-8")
    (public_root / "examples/mid/nested/notes.txt").write_text(
        "not a manifest\n",
        encoding="utf-8",
    )

    original_glob = Path.glob

    def fail_recursive_manifest_glob(self: Path, pattern: str):
        if self == public_root / "examples" and pattern.startswith("**/"):
            raise AssertionError(
                "all-examples manifest discovery should stream instead of recursive glob"
            )
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", fail_recursive_manifest_glob)

    result = macro_projection_import_protocol._source_module_manifest_paths(
        input_path,
        public_root=public_root,
        all_examples=True,
    )

    assert [path.relative_to(public_root).as_posix() for path in result] == [
        "examples/z_bundle/source_module_manifest.json",
        "examples/z_bundle/z_source_module_manifest.json",
        "examples/a_bundle/source_module_manifest.json",
        "examples/mid/nested/custom_source_module_manifest.json",
    ]


def _test_target_ref_carries_source_ref(*, target_ref: str, source_ref: str) -> bool:
    normalized_target = target_ref.removeprefix("microcosm-substrate/")
    normalized_source = source_ref.split("::", 1)[0]
    return normalized_target == normalized_source or normalized_target.endswith(
        f"source_modules/{normalized_source}"
    )


def test_macro_projection_fixture_manifest_counts_exact_source_open_body_floor() -> None:
    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/macro_projection_import_protocol.fixture_manifest.json"
        ).read_text()
    )
    body_imports = manifest["source_open_body_imports"]
    source_manifest_refs = body_imports["source_manifest_refs"]
    module_rows: list[dict[str, Any]] = []

    for manifest_ref in source_manifest_refs:
        source_manifest = json.loads((MICROCOSM_ROOT / manifest_ref).read_text())
        module_rows.extend(source_manifest["modules"])

    assert body_imports["status"] == "pass"
    assert body_imports["body_material_count"] == len(module_rows) == 177
    assert body_imports["body_material_ids"] == [
        row["module_id"] for row in module_rows
    ]
    assert body_imports["body_text_exported_in_receipts"] is False
    assert body_imports["body_text_exported_in_workingness"] is False
    assert body_imports["authority_ceiling"]["provider_payload_exported"] is False
    assert body_imports["authority_ceiling"]["credential_exported"] is False

    for row in module_rows:
        source = MICROCOSM_ROOT.parent / row["source_ref"]
        target = MICROCOSM_ROOT.parent / row["target_ref"]
        digest = hashlib.sha256(target.read_bytes()).hexdigest()

        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        row_source_digest = str(row["source_sha256"]).removeprefix("sha256:")
        row_target_digest = str(row["target_sha256"]).removeprefix("sha256:")
        assert row_target_digest == digest
        if row_source_digest != source_digest:
            assert row_source_digest == digest
            assert row.get("source_to_target_relation", "exact_copy") in (
                macro_projection_import_protocol.EXACT_COPY_SOURCE_TO_TARGET_RELATIONS
            )
            continue
        if source_digest != digest:
            assert row.get("sha256_match") in {False, True}
            assert row.get("source_to_target_relation") in (
                macro_projection_import_protocol.VERIFIED_LIGHT_EDIT_SOURCE_TO_TARGET_RELATIONS
            )
            if not _test_target_ref_carries_source_ref(
                target_ref=row["target_ref"],
                source_ref=row["source_ref"],
            ):
                assert "source_modules/" in row["target_ref"]
        else:
            assert row["sha256_match"] is True
            assert row.get("source_to_target_relation", "exact_copy") in (
                macro_projection_import_protocol.EXACT_COPY_SOURCE_TO_TARGET_RELATIONS
            )
            assert source_digest == digest


def test_macro_projection_import_protocol_observes_negative_cases(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        tmp_path / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/macro_projection_import_protocol_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["projection_cell_count"] == 65
    assert result["ready_projection_cell_count"] == 65
    assert result["blocked_projection_cell_count"] == 0
    assert result["source_ref_count"] >= 2
    assert result["public_runtime_ref_count"] >= 2
    assert result["validation_ref_count"] >= 2
    assert result["public_safe_body_material_count"] == 203
    assert result["public_safe_body_import_status"] == "pass"
    assert result["runtime_severance_status"] == "pass"
    assert result["runtime_dependency_status"] == "pass"
    assert result["dependency_preflight_gate_status"] == "pass"
    assert result["dependency_preflight_receipt_ref"] == (
        "receipts/preflight/dependency_preflight.json"
    )
    assert result["organ_lifecycle_coverage_status"] == "pass"
    assert result["organ_lifecycle_coverage_counts"]["accepted_organ_count"] == (
        _accepted_organ_count()
    )
    assert (
        result["organ_lifecycle_coverage_counts"][
            "public_authority_expected_organ_count"
        ]
        == _adapter_backed_organ_count()
    )
    assert result["macro_runtime_dependency_count"] == 0
    assert result["authority_ceiling"]["credential_or_account_bound_bodies_exported"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["projection_board"]["next_best_lane"] == "real_substrate_import_path"
    assert result["projection_board"]["intake_board_ref"] == "projection_import_intake_board.json"
    assert result["projection_board"]["runtime_severance_board_embedded"] is True
    assert result["projection_intake_board"]["ready_cell_count"] == 65
    assert result["projection_intake_board"]["blocked_cell_count"] == 0
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_intake_board"]["landed_cell_count"] == 65
    assert result["projection_intake_board"]["projection_status_counts"] == {
        "public_runtime_import_landed": 63,
        "runtime_bridge_landed": 1,
        "self_hosted_status_protocol_landed": 1,
    }
    assert result["projection_intake_board"]["omitted_material_count"] == 2
    assert "public_macro_tool_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_proof_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 203
    assert result["projection_intake_board"]["public_safe_body_import_routes"] == {
        "direct_verified_public": 3,
        "verified_light_edit": 200,
    }
    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    assert by_material["ledger_row_metadata_projection"]["material_class"] == (
        "public_macro_pattern_body"
    )
    assert by_material["ledger_row_metadata_projection"]["classification_status"] == "pass"
    assert by_material["ledger_row_metadata_projection"]["body_text_in_receipt"] is False
    assert by_material["ledger_row_metadata_projection"]["body_import_verification"][
        "verification_mode"
    ] == "exact_source_digest_match"
    assert by_material["lean_certificate_kernel_body_import"]["material_class"] == (
        "public_macro_proof_body"
    )
    assert by_material["lean_certificate_kernel_body_import"]["classification_status"] == "pass"
    assert by_material["lean_certificate_kernel_body_import"]["body_text_in_receipt"] is False
    assert by_material["lean_certificate_kernel_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "exact_source_digest_match"
    assert by_material["work_landing_tool_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["work_landing_tool_body_import"]["classification_status"] == "pass"
    assert by_material["work_landing_tool_body_import"]["body_text_in_receipt"] is False
    assert by_material["work_landing_tool_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/work_landing.py"
    )
    assert by_material["work_landing_tool_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["agent_execution_trace_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["agent_execution_trace_body_import"]["classification_status"] == "pass"
    assert by_material["agent_execution_trace_body_import"]["body_text_in_receipt"] is False
    assert by_material["agent_execution_trace_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/agent_execution_trace.py"
    )
    assert by_material["agent_trace_route_repair_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["agent_trace_route_repair_body_import"]["classification_status"] == "pass"
    assert by_material["agent_trace_route_repair_body_import"]["body_text_in_receipt"] is False
    assert by_material["agent_trace_route_repair_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/agent_trace_route_repair.py"
    )
    assert by_material["agent_trace_route_repair_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["agent_observability_store_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["agent_observability_store_body_import"]["classification_status"] == "pass"
    assert by_material["agent_observability_store_body_import"]["body_text_in_receipt"] is False
    assert by_material["agent_observability_store_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/agent_observability_store.py"
    )
    assert by_material["agent_observability_store_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["agent_session_attribution_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["agent_session_attribution_body_import"]["classification_status"] == "pass"
    assert by_material["agent_session_attribution_body_import"]["body_text_in_receipt"] is False
    assert by_material["agent_session_attribution_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/agent_session_attribution.py"
    )
    assert by_material["agent_session_attribution_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "exact_source_digest_match"
    assert by_material["continuation_packet_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["continuation_packet_body_import"]["classification_status"] == "pass"
    assert by_material["continuation_packet_body_import"]["body_text_in_receipt"] is False
    assert by_material["continuation_packet_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/continuation_packet.py"
    )
    assert by_material["continuation_packet_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["bridge_resume_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["bridge_resume_body_import"]["classification_status"] == "pass"
    assert by_material["bridge_resume_body_import"]["body_text_in_receipt"] is False
    assert by_material["bridge_resume_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/bridge_resume.py"
    )
    assert by_material["bridge_resume_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["controller_heartbeat_body_import"]["material_class"] == (
        "public_macro_tool_body"
    )
    assert by_material["controller_heartbeat_body_import"]["classification_status"] == "pass"
    assert by_material["controller_heartbeat_body_import"]["body_text_in_receipt"] is False
    assert by_material["controller_heartbeat_body_import"]["target_ref"] == (
        "src/microcosm_core/macro_tools/controller_heartbeat.py"
    )
    assert by_material["controller_heartbeat_body_import"]["body_import_verification"][
        "verification_mode"
    ] == "verified_light_edit_recipe"
    assert by_material["navigation_route_plane_body_import"]["material_class"] == (
        "public_macro_receipt_body"
    )
    assert by_material["navigation_route_plane_body_import"]["classification_status"] == "pass"
    assert by_material["navigation_route_plane_body_import"]["body_text_in_receipt"] is False
    assert by_material["navigation_route_plane_body_import"]["target_ref"] == (
        "examples/navigation_hologram_route_plane/exported_route_plane_bundle/route_rows.json"
    )
    for material_id in FINANCE_EVAL_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_tool_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
    for material_id in WORK_LANDING_CONTROL_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_tool_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
        assert (
            by_material[material_id]["body_import_verification"]["source_line_count"]
            == by_material[material_id]["body_import_verification"]["target_line_count"]
        )
    assert by_material["agent_operating_packet_sidecar_body_import"][
        "material_class"
    ] == "public_macro_receipt_body"
    assert by_material["agent_operating_packet_projection_body_import"][
        "material_class"
    ] == "public_macro_tool_body"
    for material_id in ACTIVE_EXECUTION_CONSTELLATION_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_tool_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
    for material_id in TASK_LEDGER_STARTUP_PRESSURE_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_tool_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
    for material_id in TARGET_SHAPE_TACTIC_ROUTING_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_receipt_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        _assert_public_safe_verification_mode(by_material[material_id])
    for material_id in RING2_PREMISE_RETRIEVAL_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_receipt_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        _assert_public_safe_verification_mode(by_material[material_id])
    for material_id in NAVIGATION_COVERAGE_MATRIX_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_tool_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
    for material_id in NAVIGATION_METABOLISM_LEDGER_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_tool_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
    for material_id in COMMAND_NODE_CACHE_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_tool_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
    for material_id in [
        *NAVIGATION_CLUSTERABILITY_BODY_MATERIAL_IDS,
        *ANNEX_ROUTING_COVERAGE_BODY_MATERIAL_IDS,
        *ANNEX_CURRENTNESS_BODY_MATERIAL_IDS,
        *ENTRYPOINT_HEALTH_BODY_MATERIAL_IDS,
        *AGENT_ENTRYPOINT_AUDIT_BODY_MATERIAL_IDS,
        *NAVIGATION_FITNESS_BODY_MATERIAL_IDS,
        *DYNAMIC_PAPER_LATTICE_BODY_MATERIAL_IDS,
        *KIND_ATLAS_BODY_MATERIAL_IDS,
        *SEMANTIC_ROUTING_BODY_MATERIAL_IDS,
        *EMBEDDING_SUBSTRATE_BODY_MATERIAL_IDS,
        *NVIDIA_NIM_PROVIDER_BOUNDARY_BODY_MATERIAL_IDS,
        *AGENT_PROVIDER_ROUTER_BODY_MATERIAL_IDS,
        *BRIDGE_ROUTE_CONFIG_BODY_MATERIAL_IDS,
        *KERNEL_BRIDGE_CONFIG_BODY_MATERIAL_IDS,
        *OBSERVE_RUNTIME_BODY_MATERIAL_IDS,
        *KERNEL_STATE_REGISTRY_BODY_MATERIAL_IDS,
        *AGENT_EXECUTION_TRACE_SOURCE_BODY_MATERIAL_IDS,
        *PROMPT_SHELF_MOVEMENT_SOURCE_BODY_MATERIAL_IDS,
        *PROMPT_SHELF_UPPROPAGATION_SOURCE_BODY_MATERIAL_IDS,
        *BRIDGE_RUNTIME_CONTINUITY_SOURCE_BODY_MATERIAL_IDS,
        *ORCHESTRATION_OVERNIGHT_CONTROL_SOURCE_BODY_MATERIAL_IDS,
        *NAVIGATION_TRACE_SOURCE_BODY_MATERIAL_IDS,
        *GENERATED_PROJECTION_CONTROL_SOURCE_BODY_MATERIAL_IDS,
        *SHARED_WORKTREE_GUARD_SOURCE_BODY_MATERIAL_IDS,
        *FORMAL_MATH_PROOFLINE_SPINE_SOURCE_BODY_MATERIAL_IDS,
        *WORLD_MODEL_PROJECTION_DRIFT_SOURCE_BODY_MATERIAL_IDS,
        *SPATIAL_WORLD_MODEL_SOURCE_BODY_MATERIAL_IDS,
    ]:
        assert by_material[material_id]["material_class"] == "public_macro_tool_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
    for material_id in MECHANISTIC_ORACLE_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_pattern_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
    assert result["projection_intake_board"]["negative_case_coverage_status"] == "pass"
    assert (
        result["projection_intake_board"]["projection_status_protocol"]["status_field"]
        == "projection_status"
    )
    by_cell = {
        row["cell_id"]: row for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["formal_math_readiness_extensions"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["formal_math_readiness_extensions"]["public_safe_body_material_ids"] == [
        "lean_certificate_kernel_body_import",
        *TARGET_SHAPE_TACTIC_ROUTING_BODY_MATERIAL_IDS,
        *RING2_PREMISE_RETRIEVAL_BODY_MATERIAL_IDS,
    ]
    assert by_cell["projection_protocol_self_host"]["projection_status"] == (
        "self_hosted_status_protocol_landed"
    )
    assert by_cell["projection_protocol_self_host"]["action_required"] is False
    assert by_cell["projection_protocol_self_host"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["projection_protocol_self_host"]["public_safe_body_material_ids"] == [
        "ledger_row_metadata_projection"
    ]
    assert by_cell["runtime_reveal_import_bridge"]["projection_status"] == "runtime_bridge_landed"
    assert by_cell["runtime_reveal_import_bridge"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["runtime_reveal_import_bridge"]["public_safe_body_material_ids"] == [
        "work_landing_tool_body_import"
    ]
    assert by_cell["agent_execution_trace_refactor"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["agent_execution_trace_refactor"]["public_safe_body_material_ids"] == [
        "agent_execution_trace_body_import"
    ]
    assert by_cell["agent_trace_route_repair_observability_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["agent_trace_route_repair_observability_import"][
        "public_safe_body_material_ids"
    ] == [
        "agent_trace_route_repair_body_import"
    ]
    assert by_cell["agent_observability_store_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["agent_observability_store_import"][
        "public_safe_body_material_ids"
    ] == [
        "agent_observability_store_body_import"
    ]
    assert by_cell["agent_session_attribution_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["agent_session_attribution_import"]["public_safe_body_material_ids"] == [
        "agent_session_attribution_body_import"
    ]
    assert by_cell["multi_agent_fanin_replay_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["multi_agent_fanin_replay_import"]["public_safe_body_material_ids"] == [
        "continuation_packet_body_import",
        "bridge_resume_body_import",
    ]
    assert by_cell["controller_continuity_heartbeat_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["controller_continuity_heartbeat_import"][
        "public_safe_body_material_ids"
    ] == [
        "controller_heartbeat_body_import",
    ]
    assert by_cell["navigation_route_plane_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["navigation_route_plane_import"]["public_safe_body_material_ids"] == [
        *ROUTE_PLANE_BODY_MATERIAL_IDS
    ]
    assert by_cell["finance_eval_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["finance_eval_source_modules_import"][
        "public_safe_body_material_ids"
    ] == FINANCE_EVAL_BODY_MATERIAL_IDS
    assert by_cell["finance_eval_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["finance_eval_source_modules_import"]["action_required"] is False
    assert by_cell["work_landing_control_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["work_landing_control_source_modules_import"][
        "public_safe_body_material_ids"
    ] == WORK_LANDING_CONTROL_BODY_MATERIAL_IDS
    assert by_cell["work_landing_control_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["work_landing_control_source_modules_import"]["action_required"] is False
    assert by_cell["trace_capsule_prompt_edit_capture_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["trace_capsule_prompt_edit_capture_source_modules_import"][
        "public_safe_body_material_ids"
    ] == TRACE_CAPSULE_BODY_MATERIAL_IDS
    assert by_cell["trace_capsule_prompt_edit_capture_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["trace_capsule_prompt_edit_capture_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["route_selection_control_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["route_selection_control_source_modules_import"][
        "public_safe_body_material_ids"
    ] == ROUTE_SELECTION_CONTROL_BODY_MATERIAL_IDS
    assert by_cell["route_selection_control_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["route_selection_control_source_modules_import"]["action_required"] is False
    assert by_cell["bootstrap_route_surface_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["bootstrap_route_surface_source_modules_import"][
        "public_safe_body_material_ids"
    ] == BOOTSTRAP_ROUTE_SURFACE_BODY_MATERIAL_IDS
    assert by_cell["bootstrap_route_surface_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["bootstrap_route_surface_source_modules_import"]["action_required"] is False
    assert by_cell["agent_operating_packet_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["agent_operating_packet_source_modules_import"][
        "public_safe_body_material_ids"
    ] == AGENT_OPERATING_PACKET_BODY_MATERIAL_IDS
    assert by_cell["agent_operating_packet_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["agent_operating_packet_source_modules_import"]["action_required"] is False
    assert by_cell["active_execution_constellation_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["active_execution_constellation_source_modules_import"][
        "public_safe_body_material_ids"
    ] == ACTIVE_EXECUTION_CONSTELLATION_BODY_MATERIAL_IDS
    assert by_cell["active_execution_constellation_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["active_execution_constellation_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["task_ledger_startup_pressure_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["task_ledger_startup_pressure_source_modules_import"][
        "public_safe_body_material_ids"
    ] == TASK_LEDGER_STARTUP_PRESSURE_BODY_MATERIAL_IDS
    assert by_cell["task_ledger_startup_pressure_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["task_ledger_startup_pressure_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["world_model_projection_drift_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["world_model_projection_drift_source_modules_import"][
        "public_safe_body_material_ids"
    ] == WORLD_MODEL_PROJECTION_DRIFT_SOURCE_BODY_MATERIAL_IDS
    assert by_cell["world_model_projection_drift_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["world_model_projection_drift_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["spatial_world_model_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["spatial_world_model_source_modules_import"][
        "public_safe_body_material_ids"
    ] == SPATIAL_WORLD_MODEL_SOURCE_BODY_MATERIAL_IDS
    assert by_cell["spatial_world_model_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["spatial_world_model_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["mechanistic_oracle_attribution_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["mechanistic_oracle_attribution_source_modules_import"][
        "public_safe_body_material_ids"
    ] == MECHANISTIC_ORACLE_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS
    assert by_cell["mechanistic_oracle_attribution_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["mechanistic_oracle_attribution_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["navigation_coverage_matrix_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["navigation_coverage_matrix_source_modules_import"][
        "public_safe_body_material_ids"
    ] == NAVIGATION_COVERAGE_MATRIX_BODY_MATERIAL_IDS
    assert by_cell["navigation_coverage_matrix_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["navigation_coverage_matrix_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["navigation_metabolism_ledger_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["navigation_metabolism_ledger_source_modules_import"][
        "public_safe_body_material_ids"
    ] == NAVIGATION_METABOLISM_LEDGER_BODY_MATERIAL_IDS
    assert by_cell["navigation_metabolism_ledger_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["navigation_metabolism_ledger_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["navigation_surface_audit_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["navigation_surface_audit_source_modules_import"][
        "public_safe_body_material_ids"
    ] == NAVIGATION_SURFACE_AUDIT_BODY_MATERIAL_IDS
    assert by_cell["navigation_surface_audit_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["navigation_surface_audit_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["command_node_cache_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["command_node_cache_source_modules_import"][
        "public_safe_body_material_ids"
    ] == COMMAND_NODE_CACHE_BODY_MATERIAL_IDS
    assert by_cell["command_node_cache_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["command_node_cache_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["navigation_clusterability_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["navigation_clusterability_source_modules_import"][
        "public_safe_body_material_ids"
    ] == NAVIGATION_CLUSTERABILITY_BODY_MATERIAL_IDS
    assert by_cell["navigation_clusterability_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["navigation_clusterability_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["annex_routing_coverage_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["annex_routing_coverage_source_modules_import"][
        "public_safe_body_material_ids"
    ] == ANNEX_ROUTING_COVERAGE_BODY_MATERIAL_IDS
    assert by_cell["annex_routing_coverage_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["annex_routing_coverage_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["annex_currentness_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["annex_currentness_source_modules_import"][
        "public_safe_body_material_ids"
    ] == ANNEX_CURRENTNESS_BODY_MATERIAL_IDS
    assert by_cell["annex_currentness_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["annex_currentness_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["entrypoint_health_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["entrypoint_health_source_modules_import"][
        "public_safe_body_material_ids"
    ] == ENTRYPOINT_HEALTH_BODY_MATERIAL_IDS
    assert by_cell["entrypoint_health_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["entrypoint_health_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["agent_entrypoint_audit_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["agent_entrypoint_audit_source_modules_import"][
        "public_safe_body_material_ids"
    ] == AGENT_ENTRYPOINT_AUDIT_BODY_MATERIAL_IDS
    assert by_cell["agent_entrypoint_audit_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["agent_entrypoint_audit_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["navigation_fitness_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["navigation_fitness_source_modules_import"][
        "public_safe_body_material_ids"
    ] == NAVIGATION_FITNESS_BODY_MATERIAL_IDS
    assert by_cell["navigation_fitness_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["navigation_fitness_source_modules_import"]["action_required"] is False
    assert by_cell["dynamic_paper_lattice_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["dynamic_paper_lattice_source_modules_import"][
        "public_safe_body_material_ids"
    ] == DYNAMIC_PAPER_LATTICE_BODY_MATERIAL_IDS
    assert by_cell["dynamic_paper_lattice_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["dynamic_paper_lattice_source_modules_import"][
        "action_required"
    ] is False
    assert by_cell["kind_atlas_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["kind_atlas_source_modules_import"][
        "public_safe_body_material_ids"
    ] == KIND_ATLAS_BODY_MATERIAL_IDS
    assert by_cell["kind_atlas_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["kind_atlas_source_modules_import"]["action_required"] is False
    assert by_cell["semantic_routing_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["semantic_routing_source_modules_import"][
        "public_safe_body_material_ids"
    ] == SEMANTIC_ROUTING_BODY_MATERIAL_IDS
    assert by_cell["semantic_routing_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["semantic_routing_source_modules_import"]["action_required"] is False
    assert by_cell["embedding_substrate_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["embedding_substrate_source_modules_import"][
        "public_safe_body_material_ids"
    ] == EMBEDDING_SUBSTRATE_BODY_MATERIAL_IDS
    assert by_cell["embedding_substrate_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["embedding_substrate_source_modules_import"]["action_required"] is False
    assert by_cell["nvidia_nim_provider_boundary_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["nvidia_nim_provider_boundary_source_modules_import"][
        "public_safe_body_material_ids"
    ] == NVIDIA_NIM_PROVIDER_BOUNDARY_BODY_MATERIAL_IDS
    assert by_cell["nvidia_nim_provider_boundary_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert (
        by_cell["nvidia_nim_provider_boundary_source_modules_import"]["action_required"]
        is False
    )
    assert by_cell["agent_provider_router_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["agent_provider_router_source_modules_import"][
        "public_safe_body_material_ids"
    ] == AGENT_PROVIDER_ROUTER_BODY_MATERIAL_IDS
    assert by_cell["agent_provider_router_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["agent_provider_router_source_modules_import"]["action_required"] is False
    assert by_cell["bridge_route_config_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["bridge_route_config_source_modules_import"][
        "public_safe_body_material_ids"
    ] == BRIDGE_ROUTE_CONFIG_BODY_MATERIAL_IDS
    assert by_cell["bridge_route_config_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["bridge_route_config_source_modules_import"]["action_required"] is False
    assert by_cell["kernel_bridge_config_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["kernel_bridge_config_source_modules_import"][
        "public_safe_body_material_ids"
    ] == KERNEL_BRIDGE_CONFIG_BODY_MATERIAL_IDS
    assert by_cell["kernel_bridge_config_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["kernel_bridge_config_source_modules_import"]["action_required"] is False
    assert by_cell["observe_runtime_source_modules_import"]["copy_policy"] == (
        "verified_macro_body_with_claim_floor"
    )
    assert by_cell["observe_runtime_source_modules_import"][
        "public_safe_body_material_ids"
    ] == OBSERVE_RUNTIME_BODY_MATERIAL_IDS
    assert by_cell["observe_runtime_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["observe_runtime_source_modules_import"]["action_required"] is False
    assert by_cell["bridge_runtime_continuity_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["bridge_runtime_continuity_source_modules_import"][
        "public_safe_body_material_ids"
    ] == BRIDGE_RUNTIME_CONTINUITY_SOURCE_BODY_MATERIAL_IDS
    assert by_cell["bridge_runtime_continuity_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert (
        by_cell["bridge_runtime_continuity_source_modules_import"]["action_required"]
        is False
    )
    assert by_cell["formal_math_proofline_spine_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["formal_math_proofline_spine_source_modules_import"][
        "public_safe_body_material_ids"
    ] == FORMAL_MATH_PROOFLINE_SPINE_SOURCE_BODY_MATERIAL_IDS
    assert by_cell["formal_math_proofline_spine_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert (
        by_cell["formal_math_proofline_spine_source_modules_import"]["action_required"]
        is False
    )
    assert by_cell["generated_projection_control_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["generated_projection_control_source_modules_import"][
        "public_safe_body_material_ids"
    ] == GENERATED_PROJECTION_CONTROL_SOURCE_BODY_MATERIAL_IDS
    assert by_cell["generated_projection_control_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert (
        by_cell["generated_projection_control_source_modules_import"]["action_required"]
        is False
    )
    assert by_cell["shared_worktree_guard_source_modules_import"][
        "copy_policy"
    ] == "verified_macro_body_with_claim_floor"
    assert by_cell["shared_worktree_guard_source_modules_import"][
        "public_safe_body_material_ids"
    ] == SHARED_WORKTREE_GUARD_SOURCE_BODY_MATERIAL_IDS
    assert by_cell["shared_worktree_guard_source_modules_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert (
        by_cell["shared_worktree_guard_source_modules_import"]["action_required"]
        is False
    )
    severance_board = result["runtime_severance_board"]
    assert severance_board["standalone_runtime_candidate"] is True
    assert severance_board["dependency_preflight_gate_status"] == "pass"
    assert severance_board["dependency_preflight_gate"]["status"] == "pass"
    assert severance_board["dependency_preflight_gate"]["defect_count"] == 0
    assert severance_board["organ_lifecycle_coverage_status"] == "pass"
    assert severance_board["organ_lifecycle_coverage_counts"]["runtime_step_count"] == (
        _accepted_organ_count()
    )
    assert {
        row["check_id"]: row["status"]
        for row in severance_board["severance_checks"]
    }["organ_lifecycle_coverage_preflight_passes"] == "pass"
    assert severance_board["macro_origin_ref_policy"] == (
        "macro_origin_refs_are_provenance_only_not_runtime_dependencies"
    )
    assert severance_board["macro_origin_refs_runtime_required"] is False
    assert severance_board["macro_runtime_dependency_count"] == 0
    assert severance_board["blocked_runtime_dependencies"] == []
    assert "tools/meta/control/work_landing.py" in severance_board["macro_origin_refs"]
    assert (
        "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/"
        "CertificateKernel.lean"
        in severance_board["macro_origin_refs"]
    )
    assert all(not ref.startswith("state/") for ref in severance_board["runtime_dependency_refs"])
    assert all(not ref.startswith("formal_math/") for ref in severance_board["runtime_dependency_refs"])
    assert all(not ref.startswith("tools/meta/") for ref in severance_board["runtime_dependency_refs"])
    assert (
        "src/microcosm_core/macro_tools/work_landing.py"
        in severance_board["runtime_dependency_refs"]
    )
    assert (
        "src/microcosm_core/macro_tools/bridge_resume.py"
        in severance_board["runtime_dependency_refs"]
    )
    assert (
        "src/microcosm_core/macro_tools/agent_execution_trace.py"
        in severance_board["runtime_dependency_refs"]
    )
    assert (
        "src/microcosm_core/macro_tools/agent_trace_route_repair.py"
        in severance_board["runtime_dependency_refs"]
    )
    assert (
        "examples/navigation_hologram_route_plane/exported_route_plane_bundle/route_rows.json"
        in severance_board["runtime_dependency_refs"]
    )
    assert (
        "examples/macro_projection_import_protocol/exported_projection_import_bundle/"
        "source_modules/tools/meta/observability/cli_prompt_trace.py"
        in severance_board["runtime_dependency_refs"]
    )
    assert any(
        receipt_ref.endswith("projection_import_intake_board.json")
        for receipt_ref in result["receipt_paths"]
    )


def test_macro_projection_import_protocol_receipts_are_public_relative_and_secret_only(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)

    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        public_root / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["runtime_severance_board"]["standalone_runtime_candidate"] is True
    assert result["runtime_severance_board"]["macro_runtime_dependency_count"] == 0
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert OPERATOR_HOME_SAMPLE not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_macro_projection_release_severance_requires_lifecycle_preflight(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    receipt = public_root / "receipts/preflight/dependency_preflight.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    lifecycle = payload["organ_lifecycle_coverage"]
    lifecycle["status"] = "blocked"
    lifecycle["defect_count"] = 1
    lifecycle["defects"] = [
        {
            "defect_code": "missing_public_lens",
            "organ_id": "verifier_lab_execution_spine",
        }
    ]
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        public_root / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["runtime_dependency_status"] == "pass"
    assert result["runtime_severance_status"] == "blocked"
    assert result["dependency_preflight_gate_status"] == "blocked"
    assert result["organ_lifecycle_coverage_status"] == "blocked"
    assert "MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_BLOCKED" in result["error_codes"]
    severance_board = result["runtime_severance_board"]
    assert severance_board["dependency_preflight_gate"]["defects"][0]["defect_code"] == (
        "organ_lifecycle_coverage_blocked"
    )
    assert {
        row["check_id"]: row["status"]
        for row in severance_board["severance_checks"]
    }["organ_lifecycle_coverage_preflight_passes"] == "blocked"


def test_macro_projection_release_severance_blocks_stale_lifecycle_counts(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    receipt = public_root / "receipts/preflight/dependency_preflight.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["organ_lifecycle_coverage"]["coverage_counts"]["organ_authority_row_count"] -= 1
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        public_root / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["dependency_preflight_gate_status"] == "blocked"
    assert result["organ_lifecycle_coverage_status"] == "pass"
    assert "MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_STALE" in result["error_codes"]
    defects = result["runtime_severance_board"]["dependency_preflight_gate"]["defects"]
    assert {
        row["subject_id"]
        for row in defects
        if row["defect_code"] == "organ_lifecycle_coverage_stale_count"
    } == {"organ_authority_row_count"}


def test_macro_projection_release_severance_accepts_demotion_adjusted_lifecycle_counts(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    shutil.copy2(
        MICROCOSM_ROOT / "core/organ_registry.json",
        public_root / "core/organ_registry.json",
    )

    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        public_root / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
    )

    gate = result["runtime_severance_board"]["dependency_preflight_gate"]
    assert result["dependency_preflight_gate_status"] == "pass"
    assert gate["status"] == "pass"
    assert gate["accepted_registry_count"] > gate["expected_accepted_organ_count"]
    assert gate["coverage_counts"]["demoted_drilldown_organ_count"] > 0
    assert "MACRO_PROJECTION_ORGAN_LIFECYCLE_COVERAGE_STALE" not in result["error_codes"]


def test_macro_projection_exported_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_projection_import_bundle"
    assert result["bundle_id"] == "macro_projection_import_protocol_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["projection_cell_count"] == 80
    assert result["projection_intake_board"]["ready_cell_count"] == 80
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_board"]["release_authorized"] is False
    assert result["projection_board"]["private_data_equivalence_claim"] is False
    assert result["public_safe_body_material_count"] == 254
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 254
    assert result["runtime_severance_status"] == "pass"
    assert result["runtime_severance_board"]["macro_origin_refs_runtime_required"] is False
    assert result["runtime_severance_board"]["macro_runtime_dependency_count"] == 0
    assert {
        row["material_id"]
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    } == {
        "ledger_row_metadata_projection",
        "lean_certificate_kernel_body_import",
        "work_landing_tool_body_import",
        "agent_execution_trace_body_import",
        "agent_trace_route_repair_body_import",
        "agent_observability_store_body_import",
        "agent_session_attribution_body_import",
        "continuation_packet_body_import",
        "bridge_resume_body_import",
        "controller_heartbeat_body_import",
        *ROUTE_PLANE_BODY_MATERIAL_IDS,
        *FINANCE_EVAL_BODY_MATERIAL_IDS,
        *WORK_LANDING_CONTROL_BODY_MATERIAL_IDS,
        *TASK_LEDGER_CONTROL_BODY_MATERIAL_IDS,
        *WORK_LEDGER_CONTROL_BODY_MATERIAL_IDS,
        *CHECKPOINT_LANE_BODY_MATERIAL_IDS,
        *COMMAND_OUTPUT_PROJECTION_BODY_MATERIAL_IDS,
        *TRACE_CAPSULE_BODY_MATERIAL_IDS,
        *ROUTE_SELECTION_CONTROL_BODY_MATERIAL_IDS,
        *ROUTE_WORKER_PACKET_BODY_MATERIAL_IDS,
        *ROUTE_OPERATOR_COURT_BODY_MATERIAL_IDS,
        *ROUTE_DISCOVERY_CONFIRMATION_BODY_MATERIAL_IDS,
        *PROJECTION_LOSS_AUDIT_BODY_MATERIAL_IDS,
        *SEMANTIC_ROUTE_QUALITY_AUDIT_BODY_MATERIAL_IDS,
        *REACTION_WIRING_BODY_MATERIAL_IDS,
        *NAVIGATION_CONTEXT_ROSETTA_BODY_MATERIAL_IDS,
        *BOOTSTRAP_ROUTE_SURFACE_BODY_MATERIAL_IDS,
        *AGENT_OPERATING_PACKET_BODY_MATERIAL_IDS,
        *ACTIVE_EXECUTION_CONSTELLATION_BODY_MATERIAL_IDS,
        *TASK_LEDGER_STARTUP_PRESSURE_BODY_MATERIAL_IDS,
        *NAVIGATION_COVERAGE_MATRIX_BODY_MATERIAL_IDS,
        *NAVIGATION_METABOLISM_LEDGER_BODY_MATERIAL_IDS,
        *NAVIGATION_SURFACE_AUDIT_BODY_MATERIAL_IDS,
        *COMMAND_NODE_CACHE_BODY_MATERIAL_IDS,
        *WORK_ADMISSION_BODY_MATERIAL_IDS,
        *NAVIGATION_CLUSTERABILITY_BODY_MATERIAL_IDS,
        *ANNEX_ROUTING_COVERAGE_BODY_MATERIAL_IDS,
        *ANNEX_CURRENTNESS_BODY_MATERIAL_IDS,
        *ENTRYPOINT_HEALTH_BODY_MATERIAL_IDS,
        *AGENT_ENTRYPOINT_AUDIT_BODY_MATERIAL_IDS,
        *NAVIGATION_FITNESS_BODY_MATERIAL_IDS,
        *DYNAMIC_PAPER_LATTICE_BODY_MATERIAL_IDS,
        *KIND_ATLAS_BODY_MATERIAL_IDS,
        *SEMANTIC_ROUTING_BODY_MATERIAL_IDS,
        *EMBEDDING_SUBSTRATE_BODY_MATERIAL_IDS,
        *NVIDIA_NIM_PROVIDER_BOUNDARY_BODY_MATERIAL_IDS,
        *AGENT_PROVIDER_ROUTER_BODY_MATERIAL_IDS,
        *BRIDGE_ROUTE_CONFIG_BODY_MATERIAL_IDS,
        *KERNEL_BRIDGE_CONFIG_BODY_MATERIAL_IDS,
        *OBSERVE_RUNTIME_BODY_MATERIAL_IDS,
        *KERNEL_STATE_REGISTRY_BODY_MATERIAL_IDS,
        *AGENT_EXECUTION_TRACE_SOURCE_BODY_MATERIAL_IDS,
        *AGENT_OBSERVABILITY_SOURCE_BODY_MATERIAL_IDS,
        *AGENT_OBSERVABILITY_ANIMATION_SOURCE_BODY_MATERIAL_IDS,
        *AGENT_OBSERVABILITY_CLASSIFICATION_SOURCE_BODY_MATERIAL_IDS,
        *AGENT_MISSION_STATUS_SOURCE_BODY_MATERIAL_IDS,
        *OPERATOR_HANDOFF_LINKAGE_SOURCE_BODY_MATERIAL_IDS,
        *PROMPT_SHELF_MOVEMENT_SOURCE_BODY_MATERIAL_IDS,
        *PROMPT_SHELF_UPPROPAGATION_SOURCE_BODY_MATERIAL_IDS,
        *PROMPT_SHELF_UPPROPAGATION_DIGEST_SOURCE_BODY_MATERIAL_IDS,
        *PROMPT_SHELF_RUNS_INDEX_SOURCE_BODY_MATERIAL_IDS,
        *STANDARD_OPTION_SURFACE_SOURCE_BODY_MATERIAL_IDS,
        *BRIDGE_RUNTIME_CONTINUITY_SOURCE_BODY_MATERIAL_IDS,
        *AGENT_ROUTE_FANIN_CONTINUATION_SOURCE_BODY_MATERIAL_IDS,
        *AGENT_ROUTE_SESSION_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS,
        *SESSION_HEARTBEAT_SOURCE_BODY_MATERIAL_IDS,
        *ORCHESTRATION_OVERNIGHT_CONTROL_SOURCE_BODY_MATERIAL_IDS,
        *SEED_DISTILLATION_SUBAGENT_LANE_SOURCE_BODY_MATERIAL_IDS,
        *SEED_DISTILLATION_DEPENDENCY_SOURCE_BODY_MATERIAL_IDS,
        *ARTIFACT_PROJECTION_DEBT_SOURCE_BODY_MATERIAL_IDS,
        *NAVIGATION_TRACE_SOURCE_BODY_MATERIAL_IDS,
        *GENERATED_PROJECTION_CONTROL_SOURCE_BODY_MATERIAL_IDS,
        *SHARED_WORKTREE_GUARD_SOURCE_BODY_MATERIAL_IDS,
        *RAW_GIT_COMMIT_GUARD_SOURCE_BODY_MATERIAL_IDS,
        *FORMAL_MATH_PROOFLINE_SPINE_SOURCE_BODY_MATERIAL_IDS,
        *PROVIDER_CONTEXT_SOURCE_BODY_MATERIAL_IDS,
        *WORLD_MODEL_PROJECTION_DRIFT_SOURCE_BODY_MATERIAL_IDS,
        *SPATIAL_WORLD_MODEL_SOURCE_BODY_MATERIAL_IDS,
        *MECHANISTIC_ORACLE_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS,
        *TARGET_SHAPE_TACTIC_ROUTING_BODY_MATERIAL_IDS,
        *RING2_PREMISE_RETRIEVAL_BODY_MATERIAL_IDS,
        *PROOF_DIAGNOSTIC_RING2_RUNTIME_BODY_MATERIAL_IDS,
        *EXECUTABLE_GRAMMAR_METABOLISM_BODY_MATERIAL_IDS,
    }
    assert result["public_safe_body_target_status"] == "pass"
    assert result["public_safe_body_digest_count"] == 254


def test_macro_projection_plan_exposes_source_digest_drift(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    source_path = public_root / "src/microcosm_core/macro_tools/agent_execution_trace.py"
    source_path.write_text(
        source_path.read_text(encoding="utf-8") + "\n# local digest drift\n",
        encoding="utf-8",
    )

    result = preview_import_plan(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["finding_count"] >= 1
    assert result["blocking_surface_ids"] == ["public_safe_body_import_floor"]
    details = result["blocking_surface_details"]["public_safe_body_import_floor"]
    assert "MACRO_PROJECTION_PUBLIC_SAFE_BODY_DIGEST_MISMATCH" in details["error_codes"]
    assert result["status_surfaces"]["public_safe_body_target_status"] == "blocked"
    assert result["finding_preview"][0]["body_in_receipt"] is False


def test_macro_projection_run_routes_exported_bundle_without_traceback(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "macro_projection_run_compat",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_projection_import_bundle"
    assert result["expected_negative_cases"] == []
    assert result["compatibility_route"] == {
        "requested_action": "run",
        "resolved_action": "run-projection-bundle",
        "reason": "exported projection bundles do not carry fixture negative-case inputs",
        "fixture_action": "run",
        "exported_bundle_action": "run-projection-bundle",
    }
    raw_receipt_path = public_relative_path(
        tmp_path
        / "macro_projection_run_compat"
        / "exported_projection_import_bundle_validation_result.json",
        display_root=MICROCOSM_ROOT,
    )
    expected_receipt_path = normalize_public_receipt_paths(
        {"receipt_paths": [raw_receipt_path]}
    )["receipt_paths"][0]
    assert result["receipt_paths"] == [expected_receipt_path]
    receipt_path = Path(raw_receipt_path)
    if not receipt_path.is_absolute():
        public_root_candidate = MICROCOSM_ROOT / receipt_path
        repo_root_candidate = MICROCOSM_ROOT.parent / receipt_path
        receipt_path = (
            public_root_candidate
            if public_root_candidate.is_file()
            else repo_root_candidate
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["compatibility_route"] == result["compatibility_route"]
    assert receipt["receipt_paths"] == result["receipt_paths"]


def test_projection_protocol_rejects_claimed_body_without_target_or_real_digest(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    protocol_path = (
        public_root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
        / "projection_protocol.json"
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    for row in protocol["copied_material"]:
        if row["material_id"] == "lean_certificate_kernel_body_import":
            (public_root / row["target_ref"]).unlink()
            row["body_digest"] = (
                "sha256:placeholder-lean-certificate-kernel"
            )
            break

    result = validate_projection_protocol(
        protocol,
        import_policy=json.loads(
            (public_root / "core/private_state_forbidden_classes.json").read_text(
                encoding="utf-8"
            )
        ),
        public_root=public_root,
    )

    assert result["status"] == "blocked"
    assert result["public_safe_body_target_status"] == "blocked"
    error_codes = {row["error_code"] for row in result["findings"]}
    assert "MACRO_PROJECTION_PUBLIC_SAFE_BODY_TARGET_MISSING" in error_codes
    assert "MACRO_PROJECTION_PUBLIC_SAFE_BODY_DIGEST_PLACEHOLDER" in error_codes


def test_projection_protocol_rejects_body_import_without_verification(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    protocol_path = (
        public_root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
        / "projection_protocol.json"
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    for row in protocol["copied_material"]:
        if row["material_id"] == "lean_certificate_kernel_body_import":
            row.pop("body_import_verification", None)
            break

    result = validate_projection_protocol(
        protocol,
        import_policy=json.loads(
            (public_root / "core/private_state_forbidden_classes.json").read_text(
                encoding="utf-8"
            )
        ),
        public_root=public_root,
    )

    assert result["status"] == "blocked"
    assert result["public_safe_body_target_status"] == "blocked"
    error_codes = {row["error_code"] for row in result["findings"]}
    assert "MACRO_PROJECTION_PUBLIC_SAFE_BODY_VERIFICATION_MISSING" in error_codes


def test_projection_protocol_rejects_exact_import_when_source_ref_digest_lies(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    protocol_path = (
        public_root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
        / "projection_protocol.json"
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    for row in protocol["copied_material"]:
        if row["material_id"] == "lean_certificate_kernel_body_import":
            row["source_ref"] = "tools/meta/control/work_landing.py"
            row["source_refs"] = ["tools/meta/control/work_landing.py"]
            row["body_import_verification"]["source_body_digest"] = (
                row["body_import_verification"]["target_body_digest"]
            )
            break

    result = validate_projection_protocol(
        protocol,
        import_policy=json.loads(
            (public_root / "core/private_state_forbidden_classes.json").read_text(
                encoding="utf-8"
            )
        ),
        public_root=public_root,
    )

    assert result["status"] == "blocked"
    assert result["public_safe_body_target_status"] == "blocked"
    error_codes = {row["error_code"] for row in result["findings"]}
    assert "MACRO_PROJECTION_PUBLIC_SAFE_BODY_SOURCE_DIGEST_MISMATCH" in error_codes


def test_macro_projection_import_plan_preview_is_non_writing(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = preview_import_plan(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["schema_version"] == "macro_projection_import_intake_preview_v1"
    assert result["input_mode"] == "exported_projection_import_bundle"
    assert result["projection_intake_board"]["ready_cell_count"] == 80
    assert result["projection_intake_board"]["blocked_cell_count"] == 0
    assert result["projection_intake_board"]["projection_status_counts"][
        "self_hosted_status_protocol_landed"
    ] == 1
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_intake_board"]["release_authorized"] is False
    assert "pattern_metadata" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_tool_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_proof_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 254
    assert result["projection_intake_board"]["public_safe_body_import_classes"] == {
        "public_macro_pattern_body": 3,
        "public_macro_proof_body": 1,
        "public_macro_receipt_body": 26,
        "public_macro_standard_body": 4,
        "public_macro_tool_body": 220,
    }
    assert result["runtime_severance_board"]["runtime_dependency_status"] == "pass"
    assert result["runtime_severance_board"]["macro_origin_refs_runtime_required"] is False
    assert all(
        row["selected_pattern_ids"]
        for row in result["projection_intake_board"]["projection_cells"]
    )
    assert "receipt_paths" not in result


def test_macro_projection_plan_reports_source_module_parent_drift_without_block(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    source_ref = "tools/meta/observability/cli_prompt_trace.py"
    parent_source = public_root.parent / source_ref
    parent_source.parent.mkdir(parents=True, exist_ok=True)
    target = (
        public_root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle/"
        "source_modules/tools/meta/observability/cli_prompt_trace.py"
    )
    parent_source.write_text(
        target.read_text(encoding="utf-8") + "\n# parent source drift\n",
        encoding="utf-8",
    )

    result = preview_import_plan(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["blocking_surface_ids"] == []
    drift_rows = {
        row["material_id"]: row
        for row in result["live_source_drift_rows"]
    }
    assert (
        drift_rows["trace_capsule_cli_prompt_trace_body_import"]["status"]
        == "live_source_drift_not_import_proof_failure"
    )
    assert result["live_source_drift_count"] >= 1


def test_refresh_exact_copy_source_modules_refreshes_protocol_alias_rows(
    tmp_path: Path,
) -> None:
    """Protocol material ids may differ from legacy source-module manifest rows."""
    public_root = tmp_path / "microcosm-substrate"
    bundle = public_root / "examples/example_bundle"
    source_root = tmp_path
    source = source_root / "macro/source.py"
    target = bundle / "source_modules/macro/source.py"
    policy = public_root / "core/private_state_forbidden_classes.json"
    protocol_path = bundle / "projection_protocol.json"
    manifest_path = bundle / "source_module_manifest.json"
    old_body = "def source():\n    return 'old'\n"
    new_body = "def source():\n    return 'new'\n"
    old_digest = hashlib.sha256(old_body.encode("utf-8")).hexdigest()

    source.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    policy.parent.mkdir(parents=True)
    source.write_text(new_body, encoding="utf-8")
    target.write_text(old_body, encoding="utf-8")
    policy.write_text("{}", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "path": "source_modules/macro/source.py",
                        "source_ref": "macro/source.py",
                        "body_copied": True,
                        "sha256_match": True,
                        "source_sha256": old_digest,
                        "target_sha256": old_digest,
                        "line_count": old_body.count("\n"),
                        "byte_count": len(old_body.encode("utf-8")),
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    protocol_path.write_text(
        json.dumps(
            {
                "copied_material": [
                    {
                        "material_id": "alias_source_body_import",
                        "material_class": "public_macro_tool_body",
                        "target_ref": "examples/example_bundle/source_modules/macro/source.py",
                        "source_refs": [
                            "macro/source.py",
                            "microcosm-substrate/examples/example_bundle/source_module_manifest.json",
                        ],
                        "body_digest": f"sha256:{old_digest}",
                        "body_line_count": old_body.count("\n"),
                        "body_import_verification": {
                            "verification_status": "verified",
                            "verification_mode": "exact_source_digest_match",
                            "source_body_digest": f"sha256:{old_digest}",
                            "target_body_digest": f"sha256:{old_digest}",
                            "source_line_count": old_body.count("\n"),
                            "target_line_count": old_body.count("\n"),
                            "source_ref": "macro/source.py",
                            "target_ref": "examples/example_bundle/source_modules/macro/source.py",
                            "source_to_target_relation": "exact_copy",
                        },
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = refresh_exact_copy_source_modules(
        bundle,
        source_root=source_root,
        write=True,
        command="pytest",
    )

    new_digest = hashlib.sha256(new_body.encode("utf-8")).hexdigest()
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol_row = protocol["copied_material"][0]
    verification = protocol_row["body_import_verification"]
    assert result["status"] == "pass"
    assert result["protocol_row_update_count"] == 1
    assert target.read_text(encoding="utf-8") == new_body
    assert protocol_row["body_digest"] == f"sha256:{new_digest}"
    assert verification["source_body_digest"] == f"sha256:{new_digest}"
    assert verification["target_body_digest"] == f"sha256:{new_digest}"


def test_refresh_exact_copy_source_modules_updates_target_adjacent_manifest(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    source_root = tmp_path
    macro_bundle = (
        public_root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
    )
    fixture_input = public_root / "fixtures/first_wave/macro_projection_import_protocol/input"
    policy_path = public_root / "core/private_state_forbidden_classes.json"
    target_bundle = public_root / "examples/navigation_hologram_route_plane/exported_bundle"
    manifest_path = target_bundle / "source_module_manifest.json"
    target_ref = (
        "examples/navigation_hologram_route_plane/exported_bundle/"
        "source_modules/macro/source.py"
    )
    source_ref = "macro/source.py"
    source = source_root / source_ref
    target = public_root / target_ref
    old_body = "VALUE = 'old'\n"
    new_body = "VALUE = 'new'\n"
    old_digest = hashlib.sha256(old_body.encode("utf-8")).hexdigest()

    for path, text in ((source, new_body), (target, old_body)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    macro_bundle.mkdir(parents=True, exist_ok=True)
    fixture_input.mkdir(parents=True, exist_ok=True)
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text("{}", encoding="utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "module_id": "cross_bundle_body_import",
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "body_copied": True,
                        "classification": "copied_non_secret_macro_body",
                        "sha256_match": True,
                        "source_sha256": old_digest,
                        "target_sha256": old_digest,
                        "line_count": old_body.count("\n"),
                        "byte_count": len(old_body.encode("utf-8")),
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    def protocol_payload() -> dict[str, Any]:
        return {
            "copied_material": [
                {
                    "material_id": "cross_bundle_body_import",
                    "material_class": "public_macro_tool_body",
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "body_digest": f"sha256:{old_digest}",
                    "body_line_count": old_body.count("\n"),
                    "body_import_verification": {
                        "verification_status": "verified",
                        "verification_mode": "exact_source_digest_match",
                        "source_body_digest": f"sha256:{old_digest}",
                        "target_body_digest": f"sha256:{old_digest}",
                        "source_line_count": old_body.count("\n"),
                        "target_line_count": old_body.count("\n"),
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "source_to_target_relation": "exact_copy",
                    },
                }
            ]
        }

    for protocol_path in (
        macro_bundle / "projection_protocol.json",
        fixture_input / "projection_protocol.json",
    ):
        protocol_path.write_text(
            json.dumps(protocol_payload(), indent=2) + "\n",
            encoding="utf-8",
        )

    result = refresh_exact_copy_source_modules(
        macro_bundle,
        source_root=source_root,
        material_ids=["cross_bundle_body_import"],
        write=True,
        command="pytest",
    )

    new_digest = hashlib.sha256(new_body.encode("utf-8")).hexdigest()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_row = manifest["modules"][0]
    assert result["status"] == "pass"
    assert result["target_copy_count"] == 1
    assert result["protocol_row_update_count"] == 2
    assert result["manifest_row_update_count"] == 1
    assert target.read_text(encoding="utf-8") == new_body
    assert manifest_row["source_sha256"] == new_digest
    assert manifest_row["target_sha256"] == new_digest


def _bundle_manifest_co_update_fixture(
    tmp_path: Path,
    *,
    target_body: str,
    manifest_digest: str,
    bundle_expected_digest: str,
    source_body: str,
) -> tuple[Path, Path, Path, Path]:
    public_root = tmp_path / "microcosm-substrate"
    source_root = tmp_path
    bundle = public_root / "examples/work_landing_demo/exported_bundle"
    manifest_path = bundle / "source_module_manifest.json"
    bundle_manifest_path = bundle / "bundle_manifest.json"
    source_ref = "tools/demo/work_landing.py"
    target_ref = (
        "examples/work_landing_demo/exported_bundle/"
        "source_modules/tools/demo/work_landing.py"
    )
    source = source_root / source_ref
    target = public_root / target_ref
    policy_path = public_root / "core/private_state_forbidden_classes.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text("{}", encoding="utf-8")
    for path, text in ((source, source_body), (target, target_body)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "module_id": "work_landing_demo_body",
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "body_copied": True,
                        "classification": "copied_non_secret_macro_body",
                        "sha256_match": True,
                        "source_sha256": manifest_digest,
                        "target_sha256": manifest_digest,
                        "line_count": target_body.count("\n"),
                        "byte_count": len(target_body.encode("utf-8")),
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    bundle_manifest_path.write_text(
        json.dumps(
            {
                "bundle_id": "work_landing_demo",
                "body_in_receipt": False,
                "files": [
                    {
                        "path": "source_modules/tools/demo/work_landing.py",
                        "expected_sha256": bundle_expected_digest,
                        "expected_line_count": 1,
                        "body_in_receipt": False,
                    },
                    {"path": "source_module_manifest.json"},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path, bundle_manifest_path, target, source_root


def test_refresh_exact_copy_source_modules_co_updates_bundle_manifest_expected_rows(
    tmp_path: Path,
) -> None:
    old_body = "VALUE = 'old'\n"
    new_body = "VALUE = 'new'\nEXTRA = 1\n"
    old_digest = hashlib.sha256(old_body.encode("utf-8")).hexdigest()
    manifest_path, bundle_manifest_path, target, source_root = (
        _bundle_manifest_co_update_fixture(
            tmp_path,
            target_body=old_body,
            manifest_digest=old_digest,
            bundle_expected_digest=old_digest,
            source_body=new_body,
        )
    )

    result = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=source_root,
        write=True,
        scan_protocols=False,
        command="pytest",
    )

    new_digest = hashlib.sha256(new_body.encode("utf-8")).hexdigest()
    assert result["status"] == "pass"
    assert result["target_copy_count"] == 1
    assert result["bundle_manifest_row_update_count"] == 1
    assert target.read_text(encoding="utf-8") == new_body
    bundle_manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    row = bundle_manifest["files"][0]
    assert row["expected_sha256"] == new_digest
    assert row["expected_line_count"] == new_body.count("\n")


def test_refresh_exact_copy_source_modules_repairs_stale_bundle_manifest_when_bodies_fresh(
    tmp_path: Path,
) -> None:
    body = "VALUE = 'fresh'\nEXTRA = 2\n"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    stale_digest = hashlib.sha256(b"stale").hexdigest()
    manifest_path, bundle_manifest_path, target, source_root = (
        _bundle_manifest_co_update_fixture(
            tmp_path,
            target_body=body,
            manifest_digest=digest,
            bundle_expected_digest=stale_digest,
            source_body=body,
        )
    )

    result = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=source_root,
        write=True,
        scan_protocols=False,
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["target_copy_count"] == 0
    assert result["manifest_row_update_count"] == 0
    assert result["bundle_manifest_row_update_count"] == 1
    assert target.read_text(encoding="utf-8") == body
    bundle_manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    row = bundle_manifest["files"][0]
    assert row["expected_sha256"] == digest
    assert row["expected_line_count"] == body.count("\n")


def test_refresh_exact_copy_source_modules_blocks_cross_tree_target_writes(
    tmp_path: Path,
) -> None:
    # Regression for the fallback-pollution class: a fixture tree without the
    # public-root policy marker makes _public_root_for_path fall back to the
    # live module tree; a prefix-style target_ref then resolves into that live
    # tree and a write would create files there. The refresh must fail closed.
    public_root = tmp_path / "microcosm-substrate"
    bundle = public_root / "examples/cross_tree_demo/exported_bundle"
    manifest_path = bundle / "source_module_manifest.json"
    source_ref = "tools/demo/cross_tree.py"
    target_ref = (
        "examples/cross_tree_demo/exported_bundle/"
        "source_modules/tools/demo/cross_tree.py"
    )
    source = tmp_path / source_ref
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("VALUE = 'new'\n", encoding="utf-8")
    old_digest = hashlib.sha256(b"VALUE = 'old'\n").hexdigest()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "module_id": "cross_tree_demo_body",
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "body_copied": True,
                        "classification": "copied_non_secret_macro_body",
                        "sha256_match": True,
                        "source_sha256": old_digest,
                        "target_sha256": old_digest,
                        "line_count": 1,
                        "byte_count": 14,
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=tmp_path,
        write=True,
        scan_protocols=False,
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["write_applied"] is False
    defect_codes = {row.get("defect_code") for row in result["defects"]}
    assert "source_module_refresh_cross_tree_target" in defect_codes
    assert result["target_copy_count"] == 0


def test_refresh_exact_copy_source_modules_detects_manifest_count_metadata_drift(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    source_root = tmp_path
    bundle = public_root / "examples/example_bundle"
    manifest_path = bundle / "source_module_manifest.json"
    source_ref = "macro/source.py"
    target_ref = "examples/example_bundle/source_modules/macro/source.py"
    source = source_root / source_ref
    target = public_root / target_ref
    policy_path = public_root / "core/private_state_forbidden_classes.json"
    old_body = "VALUE = 'old'\n"
    body = "VALUE = 'new'\nEXTRA = True\n"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()

    for path in (source, target):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text("{}", encoding="utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "module_id": "metadata_only_body_import",
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "body_copied": True,
                        "source_to_target_relation": "exact_copy",
                        "sha256": digest,
                        "source_sha256": digest,
                        "target_sha256": digest,
                        "sha256_match": True,
                        "line_count": old_body.count("\n"),
                        "byte_count": len(old_body.encode("utf-8")),
                        "source_line_count": old_body.count("\n"),
                        "target_line_count": old_body.count("\n"),
                        "source_byte_count": len(old_body.encode("utf-8")),
                        "target_byte_count": len(old_body.encode("utf-8")),
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    dry_run = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=source_root,
        material_ids=["metadata_only_body_import"],
        write=False,
        command="pytest",
    )

    assert dry_run["status"] == "drift_detected"
    assert dry_run["manifest_row_update_count"] == 1
    assert dry_run["target_copy_count"] == 0
    manifest_row = dry_run["manifest_rows"][0]
    assert manifest_row["metadata_refresh_required"] is True
    assert manifest_row["target_refresh_required"] is False

    write_result = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=source_root,
        material_ids=["metadata_only_body_import"],
        write=True,
        command="pytest",
    )

    updated = json.loads(manifest_path.read_text(encoding="utf-8"))["modules"][0]
    assert write_result["status"] == "pass"
    assert updated["source_line_count"] == body.count("\n")
    assert updated["target_line_count"] == body.count("\n")
    assert updated["source_byte_count"] == len(body.encode("utf-8"))
    assert updated["target_byte_count"] == len(body.encode("utf-8"))


def test_refresh_exact_copy_source_modules_blocks_dirty_pending_source_write(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "repo"
    public_root = source_root / "microcosm-substrate"
    bundle = public_root / "examples/example_bundle"
    manifest_path = bundle / "source_module_manifest.json"
    source_ref = "macro/source.py"
    target_ref = "examples/example_bundle/source_modules/macro/source.py"
    source = source_root / source_ref
    target = public_root / target_ref
    policy_path = public_root / "core/private_state_forbidden_classes.json"
    old_body = "VALUE = 'old'\n"
    new_body = "VALUE = 'new'\n"
    old_digest = hashlib.sha256(old_body.encode("utf-8")).hexdigest()

    for path in (source, target):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old_body, encoding="utf-8")
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text("{}", encoding="utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "module_id": "dirty_source_body_import",
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "body_copied": True,
                        "source_to_target_relation": "exact_copy",
                        "source_sha256": old_digest,
                        "target_sha256": old_digest,
                        "sha256_match": True,
                        "line_count": old_body.count("\n"),
                        "byte_count": len(old_body.encode("utf-8")),
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=source_root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=source_root, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "user.name=Test Runner",
            "commit",
            "-m",
            "baseline",
        ],
        cwd=source_root,
        check=True,
        capture_output=True,
    )
    source.write_text(new_body, encoding="utf-8")

    result = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=source_root,
        material_ids=["dirty_source_body_import"],
        write=True,
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["write_applied"] is False
    assert result["write_guard"] == "dirty_pending_sources_blocked_write"
    assert result["source_coupling"]["status"] == "dirty_pending_sources_detected"
    assert result["source_coupling"]["dirty_source_ref_count"] == 1
    assert result["source_coupling"]["dirty_source_refs"] == [
        {
            "source_ref": source_ref,
            "git_path": source_ref,
            "git_status": " M",
        }
    ]
    assert result["defects"] == [
        {
            "defect_code": "source_module_refresh_dirty_source_requires_review",
            "dirty_source_ref_count": 1,
            "dirty_source_refs": result["source_coupling"]["dirty_source_refs"],
            "body_in_receipt": False,
        }
    ]
    assert target.read_text(encoding="utf-8") == old_body

    override = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=source_root,
        material_ids=["dirty_source_body_import"],
        write=True,
        allow_dirty_sources=True,
        command="pytest",
    )

    new_digest = hashlib.sha256(new_body.encode("utf-8")).hexdigest()
    updated = json.loads(manifest_path.read_text(encoding="utf-8"))["modules"][0]
    assert override["status"] == "pass"
    assert override["write_applied"] is True
    assert override["write_guard"] == "dirty_pending_sources_override"
    assert target.read_text(encoding="utf-8") == new_body
    assert updated["source_sha256"] == new_digest
    assert updated["target_sha256"] == new_digest


def test_refresh_exact_copy_source_modules_blocks_dirty_pending_output_write(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "repo"
    public_root = source_root / "microcosm-substrate"
    bundle = public_root / "examples/example_bundle"
    manifest_path = bundle / "source_module_manifest.json"
    source_ref = "macro/source.py"
    target_ref = "examples/example_bundle/source_modules/macro/source.py"
    source = source_root / source_ref
    target = public_root / target_ref
    policy_path = public_root / "core/private_state_forbidden_classes.json"
    old_body = "VALUE = 'old'\n"
    new_body = "VALUE = 'new'\n"
    operator_target_body = "VALUE = 'operator draft'\n"
    old_digest = hashlib.sha256(old_body.encode("utf-8")).hexdigest()

    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(new_body, encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(old_body, encoding="utf-8")
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text("{}", encoding="utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "module_id": "dirty_output_body_import",
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "body_copied": True,
                        "source_to_target_relation": "exact_copy",
                        "source_sha256": old_digest,
                        "target_sha256": old_digest,
                        "sha256_match": True,
                        "line_count": old_body.count("\n"),
                        "byte_count": len(old_body.encode("utf-8")),
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=source_root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=source_root, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "user.name=Test Runner",
            "commit",
            "-m",
            "baseline",
        ],
        cwd=source_root,
        check=True,
        capture_output=True,
    )

    target.write_text(operator_target_body, encoding="utf-8")
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["modules"][0]["operator_note"] = "unrelated manifest draft"
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")

    dry_run = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=source_root,
        material_ids=["dirty_output_body_import"],
        write=False,
        command="pytest",
    )

    assert dry_run["status"] == "drift_detected"
    assert dry_run["defect_count"] == 0
    assert dry_run["output_coupling"]["status"] == "dirty_pending_output_paths_detected"
    assert dry_run["output_coupling"]["dirty_output_path_count"] == 2

    result = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=source_root,
        material_ids=["dirty_output_body_import"],
        write=True,
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["write_applied"] is False
    assert result["write_guard"] == "dirty_pending_outputs_blocked_write"
    assert result["source_coupling"]["status"] == "pending_sources_clean"
    assert result["output_coupling"]["status"] == "dirty_pending_output_paths_detected"
    dirty_output_paths = sorted(
        result["output_coupling"]["dirty_output_paths"],
        key=lambda row: row["git_path"],
    )
    assert [row["git_status"] for row in dirty_output_paths] == [" M", " M"]
    assert [row["output_path_roles"] for row in dirty_output_paths] == [
        ["manifest_json_update"],
        ["target_copy"],
    ]
    assert result["defects"] == [
        {
            "defect_code": "source_module_refresh_dirty_output_requires_review",
            "dirty_output_path_count": 2,
            "dirty_output_paths": result["output_coupling"]["dirty_output_paths"],
            "body_in_receipt": False,
        }
    ]
    assert target.read_text(encoding="utf-8") == operator_target_body
    manifest_after = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_after["modules"][0]["operator_note"] == "unrelated manifest draft"
    assert manifest_after["modules"][0]["source_sha256"] == old_digest

    override = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=source_root,
        material_ids=["dirty_output_body_import"],
        write=True,
        allow_dirty_outputs=True,
        command="pytest",
    )

    new_digest = hashlib.sha256(new_body.encode("utf-8")).hexdigest()
    updated = json.loads(manifest_path.read_text(encoding="utf-8"))["modules"][0]
    assert override["status"] == "pass"
    assert override["write_applied"] is True
    assert override["write_guard"] == "dirty_pending_outputs_override"
    assert override["allow_dirty_outputs"] is True
    assert target.read_text(encoding="utf-8") == new_body
    assert updated["operator_note"] == "unrelated manifest draft"
    assert updated["source_sha256"] == new_digest
    assert updated["target_sha256"] == new_digest
    assert updated["sha256_match"] is True


def test_refresh_exact_copy_source_modules_scopes_protocol_rows_for_manifest_file(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle = (
        public_root
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
    )
    source_root = tmp_path
    manifest_path = bundle / "work_admission_source_module_manifest.json"
    policy_path = public_root / "core/private_state_forbidden_classes.json"
    protocol_path = bundle / "projection_protocol.json"
    old_body = "VALUE = 'old'\n"
    first_body = "VALUE = 'first'\n"
    second_body = "VALUE = 'second'\n"
    old_digest = hashlib.sha256(old_body.encode("utf-8")).hexdigest()

    first_source = source_root / "macro/first.py"
    second_source = source_root / "macro/second.py"
    first_target = bundle / "source_modules/macro/first.py"
    second_target = bundle / "source_modules/macro/second.py"
    for path, text in (
        (first_source, first_body),
        (second_source, second_body),
        (first_target, old_body),
        (second_target, old_body),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text("{}", encoding="utf-8")

    manifest_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "module_id": "first_body_import",
                        "source_ref": "macro/first.py",
                        "target_ref": (
                            "microcosm-substrate/examples/"
                            "macro_projection_import_protocol/"
                            "exported_projection_import_bundle/source_modules/"
                            "macro/first.py"
                        ),
                        "body_copied": True,
                        "classification": "copied_non_secret_macro_body",
                        "sha256_match": True,
                        "source_sha256": old_digest,
                        "target_sha256": old_digest,
                        "line_count": old_body.count("\n"),
                        "byte_count": len(old_body.encode("utf-8")),
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    def protocol_row(material_id: str, source_ref: str, target_name: str) -> dict:
        target_ref = (
            "examples/macro_projection_import_protocol/"
            f"exported_projection_import_bundle/source_modules/macro/{target_name}"
        )
        return {
            "material_id": material_id,
            "material_class": "public_macro_tool_body",
            "source_ref": source_ref,
            "target_ref": target_ref,
            "body_digest": f"sha256:{old_digest}",
            "body_line_count": old_body.count("\n"),
            "body_import_verification": {
                "verification_status": "verified",
                "verification_mode": "exact_source_digest_match",
                "source_body_digest": f"sha256:{old_digest}",
                "target_body_digest": f"sha256:{old_digest}",
                "source_line_count": old_body.count("\n"),
                "target_line_count": old_body.count("\n"),
                "source_ref": source_ref,
                "target_ref": target_ref,
                "source_to_target_relation": "exact_copy",
            },
        }

    protocol_path.write_text(
        json.dumps(
            {
                "copied_material": [
                    protocol_row("first_body_import", "macro/first.py", "first.py"),
                    protocol_row("second_body_import", "macro/second.py", "second.py"),
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=source_root,
        write=False,
        command="pytest",
    )

    assert result["status"] == "drift_detected"
    assert result["manifest_row_update_count"] == 1
    assert result["protocol_row_update_count"] == 1
    assert result["target_copy_count"] == 1
    assert [row["material_id"] for row in result["protocol_rows"]] == [
        "first_body_import"
    ]


def test_refresh_exact_copy_source_modules_can_skip_protocol_scan_for_manifest_write(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle = public_root / "examples/example_bundle"
    source_root = tmp_path
    manifest_path = bundle / "source_module_manifest.json"
    protocol_path = bundle / "projection_protocol.json"
    source_ref = "macro/source.py"
    manifest_target_ref = "source_modules/macro/source.py"
    protocol_target_ref = "examples/example_bundle/source_modules/macro/source.py"
    source = source_root / source_ref
    target = bundle / manifest_target_ref
    old_body = "VALUE = 'old'\n"
    new_body = "VALUE = 'new'\n"
    old_digest = hashlib.sha256(old_body.encode("utf-8")).hexdigest()

    for path, text in ((source, new_body), (target, old_body)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "module_id": "source_body_import",
                        "source_ref": source_ref,
                        "target_ref": manifest_target_ref,
                        "body_copied": True,
                        "classification": "copied_non_secret_macro_body",
                        "sha256_match": True,
                        "source_sha256": old_digest,
                        "target_sha256": old_digest,
                        "line_count": old_body.count("\n"),
                        "byte_count": len(old_body.encode("utf-8")),
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    protocol_path.write_text(
        json.dumps(
            {
                "copied_material": [
                    {
                        "material_id": "source_body_import",
                        "source_ref": source_ref,
                        "target_ref": protocol_target_ref,
                        "body_digest": f"sha256:{old_digest}",
                        "body_line_count": old_body.count("\n"),
                        "body_import_verification": {
                            "verification_status": "verified",
                            "verification_mode": "exact_source_digest_match",
                            "source_body_digest": f"sha256:{old_digest}",
                            "target_body_digest": f"sha256:{old_digest}",
                            "source_line_count": old_body.count("\n"),
                            "target_line_count": old_body.count("\n"),
                            "source_ref": source_ref,
                            "target_ref": protocol_target_ref,
                            "source_to_target_relation": "exact_copy",
                        },
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = refresh_exact_copy_source_modules(
        manifest_path,
        source_root=source_root,
        material_ids=["source_body_import"],
        scan_protocols=False,
        write=True,
        command="pytest",
    )

    new_digest = hashlib.sha256(new_body.encode("utf-8")).hexdigest()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_row = manifest["modules"][0]
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol_row = protocol["copied_material"][0]
    assert result["status"] == "pass"
    assert result["protocol_scan_enabled"] is False
    assert result["protocol_count"] == 0
    assert result["protocol_row_update_count"] == 0
    assert result["manifest_row_update_count"] == 1
    assert result["target_copy_count"] == 1
    assert target.read_text(encoding="utf-8") == new_body
    assert manifest_row["source_sha256"] == new_digest
    assert manifest_row["target_sha256"] == new_digest
    assert protocol_row["body_digest"] == f"sha256:{old_digest}"


def test_refresh_exact_copy_source_modules_blocks_restricted_private_boundary_write(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    source_root = public_root.parent
    material_targets = {
        "trace_capsule_cli_prompt_trace_body_import": {
            "source_ref": "tools/meta/observability/cli_prompt_trace.py",
            "target_refs": [
                (
                    "examples/macro_projection_import_protocol/"
                    "exported_projection_import_bundle/source_modules/tools/meta/"
                    "observability/cli_prompt_trace.py"
                )
            ],
            "manifest_ref": (
                "examples/macro_projection_import_protocol/"
                "exported_projection_import_bundle/"
                "trace_capsule_source_module_manifest.json"
            ),
        },
        "world_model_drift_aggregate_source_body_import": {
            "source_ref": "system/server/world_model.py",
            "target_refs": [
                (
                    "examples/macro_projection_import_protocol/"
                    "exported_projection_import_bundle/source_modules/system/server/"
                    "world_model.py"
                ),
                (
                    "examples/world_model_projection_drift_control_room/"
                    "exported_projection_drift_control_bundle/source_modules/system/"
                    "server/world_model.py"
                ),
            ],
            "manifest_ref": (
                "examples/world_model_projection_drift_control_room/"
                "exported_projection_drift_control_bundle/source_module_manifest.json"
            ),
        },
    }
    for material_id, spec in material_targets.items():
        source = source_root / spec["source_ref"]
        first_target = public_root / spec["target_refs"][0]
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            first_target.read_text(encoding="utf-8")
            + f"\n# refreshed source drift for {material_id}\n",
            encoding="utf-8",
        )

    dry_run = refresh_exact_copy_source_modules(
        public_root,
        source_root=source_root,
        material_ids=list(material_targets),
        all_examples=True,
        write=False,
        command="pytest",
    )

    assert dry_run["status"] == "drift_detected"
    assert dry_run["write_applied"] is False
    assert dry_run["target_copy_count"] == 3
    assert dry_run["manifest_row_update_count"] == 3
    assert dry_run["protocol_row_update_count"] == 4
    assert dry_run["body_text_in_receipt"] is False
    assert dry_run["source_module_boundary"]["status"] == "blocked"

    write_result = refresh_exact_copy_source_modules(
        public_root,
        source_root=source_root,
        material_ids=list(material_targets),
        all_examples=True,
        write=True,
        command="pytest",
    )

    assert write_result["status"] == "blocked"
    assert write_result["write_applied"] is False
    assert write_result["write_guard"] == "source_module_refresh_authority_blocked_write"
    assert write_result["target_copy_count"] == 3
    authority_defect = next(
        row
        for row in write_result["defects"]
        if row["defect_code"] == "source_module_refresh_authority_blocked"
    )
    assert authority_defect["blocked_decision_count"] >= 2
    assert {
        "tools/meta/observability/cli_prompt_trace.py",
        "system/server/world_model.py",
    } <= {row["source_ref"] for row in authority_defect["blocked_decisions"]}
    assert write_result["source_module_boundary"]["body_in_receipt"] is False
    assert write_result["source_module_refresh_authority"]["body_in_receipt"] is False
    for material_id, spec in material_targets.items():
        source = source_root / spec["source_ref"]
        source_bytes = source.read_bytes()

        for target_ref in spec["target_refs"]:
            assert (public_root / target_ref).read_bytes() != source_bytes

        manifest = json.loads((public_root / spec["manifest_ref"]).read_text())
        manifest_row = next(
            row for row in manifest["modules"] if row["module_id"] == material_id
        )
        assert manifest_row["target_sha256"] != hashlib.sha256(source_bytes).hexdigest()

    clean_protocol_only_result = refresh_exact_copy_source_modules(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        source_root=source_root,
        material_ids=["agent_session_attribution_body_import"],
        write=False,
        command="pytest",
    )

    assert clean_protocol_only_result["status"] == "pass"
    assert clean_protocol_only_result["defect_count"] == 0
    assert clean_protocol_only_result["pending_update_count"] == 0
    assert clean_protocol_only_result["matched_material_ids"] == [
        "agent_session_attribution_body_import"
    ]


def _granted_restricted_exact_copy_fixture(tmp_path: Path) -> dict[str, Any]:
    public_root = tmp_path / "microcosm-substrate"
    source_root = tmp_path
    bundle = (
        public_root
        / "examples/proof_derived_governed_mutation_authorization/"
        "exported_governed_mutation_authorization_bundle"
    )
    source = source_root / "tools/meta/control/scoped_commit.py"
    target = bundle / "source_modules/ai_workflow/tools/meta/control/scoped_commit.py"
    manifest_path = bundle / "source_module_manifest.json"
    old_body = "def scoped_commit():\n    return 'old'\n"
    new_body = "def scoped_commit():\n    return 'new'\n"
    old_digest = hashlib.sha256(old_body.encode("utf-8")).hexdigest()

    source.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    (public_root / "core").mkdir(parents=True)
    (public_root / "core/private_state_forbidden_classes.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (public_root / "core/source_module_refresh_policy_v0.json").write_text(
        json.dumps(
            {
                "schema_version": "source_module_refresh_policy_v0",
                "policy_id": "test_refresh_policy",
                "policy_revision": "test_policy_rev",
                "operation": "exact_copy_source_module_refresh",
                "grants": [
                    {
                        "grant_id": "scoped_commit_refresh_grant",
                        "status": "active",
                        "operation": "exact_copy_source_module_refresh",
                        "source_ref": "tools/meta/control/scoped_commit.py",
                        "source_to_target_relation": "exact_copy",
                        "material_ids": [
                            "scoped_commit_private_index_control_body_import"
                        ],
                        "target_refs": [
                            (
                                "examples/proof_derived_governed_mutation_authorization/"
                                "exported_governed_mutation_authorization_bundle/"
                                "source_modules/ai_workflow/tools/meta/control/scoped_commit.py"
                            )
                        ],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    source.write_text(new_body, encoding="utf-8")
    target.write_text(old_body, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "module_id": "scoped_commit_private_index_control_body_import",
                        "path": "source_modules/ai_workflow/tools/meta/control/scoped_commit.py",
                        "source_ref": "tools/meta/control/scoped_commit.py",
                        "target_ref": (
                            "microcosm-substrate/examples/"
                            "proof_derived_governed_mutation_authorization/"
                            "exported_governed_mutation_authorization_bundle/"
                            "source_modules/ai_workflow/tools/meta/control/scoped_commit.py"
                        ),
                        "body_copied": True,
                        "body_in_receipt": False,
                        "source_to_target_relation": "exact_copy",
                        "sha256_match": True,
                        "source_sha256": f"sha256:{old_digest}",
                        "target_sha256": f"sha256:{old_digest}",
                        "line_count": old_body.count("\n"),
                        "byte_count": len(old_body.encode("utf-8")),
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "public_root": public_root,
        "source_root": source_root,
        "bundle": bundle,
        "source": source,
        "target": target,
        "manifest_path": manifest_path,
        "old_body": old_body,
        "new_body": new_body,
    }


def test_refresh_exact_copy_source_modules_allows_granted_restricted_exact_copy(
    tmp_path: Path,
) -> None:
    fixture = _granted_restricted_exact_copy_fixture(tmp_path)
    bundle = fixture["bundle"]
    source_root = fixture["source_root"]
    target = fixture["target"]
    manifest_path = fixture["manifest_path"]
    new_body = fixture["new_body"]

    dry_run = refresh_exact_copy_source_modules(
        bundle,
        source_root=source_root,
        write=False,
        command="pytest",
    )

    assert dry_run["status"] == "drift_detected"
    assert dry_run["source_module_boundary"]["status"] == "blocked"
    assert dry_run["source_module_refresh_authority"]["status"] == "pass"
    dry_run_decision = dry_run["source_module_refresh_authority"]["decisions"][0]
    assert dry_run_decision["classification_status"] == (
        "restricted_private_control_plane"
    )
    assert dry_run_decision["classification_retained"] is True
    assert dry_run_decision["authorization_status"] == "allow_with_authority"
    assert dry_run_decision["policy_fingerprint"].startswith("sha256:")
    assert dry_run_decision["source_sha256"].startswith("sha256:")
    dry_plan = dry_run["source_module_refresh_plan"]
    assert dry_plan["plan_fingerprint"].startswith("sha256:")
    assert dry_plan["target_copy_preconditions"][0]["target_preimage_sha256"].startswith(
        "sha256:"
    )
    assert dry_plan["target_copy_preconditions"][0][
        "intended_target_sha256"
    ].startswith("sha256:")

    write_result = refresh_exact_copy_source_modules(
        bundle,
        source_root=source_root,
        write=True,
        command="pytest",
    )

    new_digest = hashlib.sha256(new_body.encode("utf-8")).hexdigest()
    assert write_result["status"] == "pass"
    assert write_result["write_guard"] == "source_coupling_checked"
    assert write_result["write_applied"] is True
    assert target.read_text(encoding="utf-8") == new_body
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_row = manifest["modules"][0]
    assert manifest_row["source_sha256"] == f"sha256:{new_digest}"
    assert manifest_row["target_sha256"] == f"sha256:{new_digest}"
    receipt_row = write_result["manifest_rows"][0]
    assert receipt_row["target_preimage_sha256"].startswith("sha256:")
    assert receipt_row["intended_target_sha256"] == f"sha256:{new_digest}"
    assert receipt_row["observed_postwrite_sha256"] == f"sha256:{new_digest}"


def test_refresh_exact_copy_source_modules_refuses_stale_source_target_or_policy(
    tmp_path: Path,
) -> None:
    for stale_case in ("source", "target", "policy"):
        fixture = _granted_restricted_exact_copy_fixture(tmp_path / stale_case)
        bundle = fixture["bundle"]
        source_root = fixture["source_root"]
        source = fixture["source"]
        target = fixture["target"]
        public_root = fixture["public_root"]

        def mutate_after_plan() -> None:
            if stale_case == "source":
                source.write_text(
                    "def scoped_commit():\n    return 'changed after plan'\n",
                    encoding="utf-8",
                )
            elif stale_case == "target":
                target.write_text(
                    "def scoped_commit():\n    return 'target changed after plan'\n",
                    encoding="utf-8",
                )
            else:
                policy_path = public_root / "core/source_module_refresh_policy_v0.json"
                policy = json.loads(policy_path.read_text(encoding="utf-8"))
                policy["grants"][0]["status"] = "revoked"
                policy_path.write_text(json.dumps(policy, indent=2) + "\n")

        result = refresh_exact_copy_source_modules(
            bundle,
            source_root=source_root,
            write=True,
            command=f"pytest stale {stale_case}",
            _pre_write_hook=mutate_after_plan,
        )

        assert result["status"] == "blocked"
        assert result["write_applied"] is False
        assert result["write_guard"] == "source_module_refresh_stale_plan_blocked_write"
        stale_defect = next(
            row
            for row in result["defects"]
            if row["defect_code"] == "source_module_refresh_stale_plan"
        )
        observed_preconditions = {
            row["precondition"] for row in stale_defect["stale_preconditions"]
        }
        if stale_case == "source":
            assert "source_sha256" in observed_preconditions
        elif stale_case == "target":
            assert "target_preimage_sha256" in observed_preconditions
        else:
            assert "policy_fingerprint" in observed_preconditions
            assert "policy_authority_decisions" in observed_preconditions


def test_refresh_exact_copy_source_modules_accepts_source_import_class_rows(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    source_root = public_root.parent
    material_id = "source_import_class_only_body_import"
    source_ref = "local_source/source_import_class_only.py"
    source = source_root / source_ref
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("VALUE = 'refreshed exact copy'\n", encoding="utf-8")

    manifest_refs = [
        (
            "examples/source_import_class_shape/exported_bundle/"
            "source_module_manifest.json"
        ),
        (
            "fixtures/first_wave/source_import_class_shape/input/"
            "source_module_manifest.json"
        ),
    ]
    target_refs = [f"source_artifacts/{source_ref}"] * len(manifest_refs)
    for manifest_ref, target_ref in zip(manifest_refs, target_refs, strict=True):
        manifest_path = public_root / manifest_ref
        target = manifest_path.parent / target_ref
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("VALUE = 'stale copy'\n", encoding="utf-8")
        manifest = {
            "schema_version": "test_source_module_manifest_v1",
            "modules": [
                {
                    "module_id": material_id,
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "source_to_target_relation": "exact_copy",
                    "source_import_class": "copied_non_secret_macro_body",
                    "required_anchors": ["refreshed exact copy"],
                    "body_copied": True,
                    "body_in_receipt": False,
                    "sha256": "sha256:stale",
                    "line_count": 1,
                    "byte_count": len("VALUE = 'stale copy'\n"),
                }
            ],
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = refresh_exact_copy_source_modules(
        public_root / manifest_refs[1],
        source_root=source_root,
        material_ids=[material_id],
        all_examples=True,
        write=True,
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["target_copy_count"] == 2
    assert result["manifest_row_update_count"] == 2
    for manifest_ref, target_ref in zip(manifest_refs, target_refs, strict=True):
        target = (public_root / manifest_ref).parent / target_ref
        assert target.read_bytes() == source.read_bytes()
        manifest = json.loads((public_root / manifest_ref).read_text(encoding="utf-8"))
        row = manifest["modules"][0]
        assert row["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
        assert row["sha256"].startswith("sha256:")
        assert row["sha256_match"] is True


def test_refresh_exact_copy_source_modules_accepts_legacy_source_import_rows(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    marker_path = public_root / "core/private_state_forbidden_classes.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MICROCOSM_ROOT / "core/private_state_forbidden_classes.json", marker_path)
    source_root = tmp_path
    source_ref = "macro/legacy_work_landing.py"
    source = source_root / source_ref
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("LEGACY = 'refreshed exact copy'\n", encoding="utf-8")

    manifest_path = (
        public_root / "examples/legacy_work_landing/exported_bundle/source_module_manifest.json"
    )
    target_ref = "source_modules/macro/legacy_work_landing.py"
    target = manifest_path.parent / target_ref
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("LEGACY = 'stale copy'\n", encoding="utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "legacy_source_module_manifest_v1",
                "modules": [
                    {
                        "source_ref": source_ref,
                        "path": target_ref,
                        "source_import_class": "copied_non_secret_macro_body",
                        "body_in_receipt": False,
                        "sha256": "stale",
                        "source_sha256": "sha256:stale",
                        "target_sha256": "sha256:stale",
                        "line_count": 1,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = refresh_exact_copy_source_modules(
        manifest_path.parent,
        source_root=source_root,
        write=True,
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["target_copy_count"] == 1
    assert result["manifest_row_update_count"] == 1
    assert target.read_bytes() == source.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][0]
    assert row["body_copied"] is True
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert row["source_sha256"] == f"sha256:{source_digest}"
    assert row["target_sha256"] == f"sha256:{source_digest}"
    assert row["sha256"] == source_digest
    assert row["sha256_match"] is True


def test_refresh_exact_copy_source_modules_filters_legacy_source_ref_rows(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    marker_path = public_root / "core/private_state_forbidden_classes.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MICROCOSM_ROOT / "core/private_state_forbidden_classes.json", marker_path)
    source_root = tmp_path
    selected_source_ref = "macro/selected_observability.py"
    other_source_ref = "macro/other_observability.py"
    selected_source = source_root / selected_source_ref
    other_source = source_root / other_source_ref
    selected_source.parent.mkdir(parents=True, exist_ok=True)
    selected_source.write_text("SELECTED = 'refreshed exact copy'\n", encoding="utf-8")
    other_source.write_text("OTHER = 'refreshed exact copy'\n", encoding="utf-8")

    manifest_path = (
        public_root
        / "examples/legacy_observability/exported_bundle/source_module_manifest.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    selected_target_ref = "source_modules/macro/selected_observability.py"
    other_target_ref = "source_modules/macro/other_observability.py"
    for target_ref in (selected_target_ref, other_target_ref):
        target = manifest_path.parent / target_ref
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("STALE = True\n", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "legacy_source_module_manifest_v1",
                "modules": [
                    {
                        "source_ref": selected_source_ref,
                        "path": selected_target_ref,
                        "source_import_class": "copied_non_secret_macro_body",
                        "body_in_receipt": False,
                        "sha256": "stale",
                        "source_sha256": "sha256:stale",
                        "target_sha256": "sha256:stale",
                        "line_count": 1,
                    },
                    {
                        "source_ref": other_source_ref,
                        "path": other_target_ref,
                        "source_import_class": "copied_non_secret_macro_body",
                        "body_in_receipt": False,
                        "sha256": "stale",
                        "source_sha256": "sha256:stale",
                        "target_sha256": "sha256:stale",
                        "line_count": 1,
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = refresh_exact_copy_source_modules(
        manifest_path.parent,
        source_root=source_root,
        material_ids=[selected_source_ref],
        write=True,
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["matched_material_ids"] == [selected_source_ref]
    assert result["target_copy_count"] == 1
    assert result["manifest_row_update_count"] == 1
    assert (
        manifest_path.parent / selected_target_ref
    ).read_bytes() == selected_source.read_bytes()
    assert (manifest_path.parent / other_target_ref).read_text(encoding="utf-8") == (
        "STALE = True\n"
    )


def test_refresh_exact_copy_source_modules_resolves_microcosm_local_sources(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    marker_path = public_root / "core/private_state_forbidden_classes.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MICROCOSM_ROOT / "core/private_state_forbidden_classes.json", marker_path)
    source_root = tmp_path / "macro-root"
    source_root.mkdir()
    source_ref = "src/microcosm_core/organs/local_microcosm_source.py"
    source = public_root / source_ref
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("LOCAL_MICROCOSM = 'refreshed exact copy'\n", encoding="utf-8")

    manifest_path = (
        public_root
        / "examples/local_microcosm_source/exported_bundle/source_module_manifest.json"
    )
    target_ref = "source_modules/microcosm_core/organs/local_microcosm_source.py"
    target = manifest_path.parent / target_ref
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("LOCAL_MICROCOSM = 'stale copy'\n", encoding="utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "local_microcosm_source_manifest_v1",
                "modules": [
                    {
                        "module_id": "local_microcosm_source_body_import",
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "source_to_target_relation": "exact_copy",
                        "body_copied": True,
                        "body_in_receipt": False,
                        "line_count": 1,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = refresh_exact_copy_source_modules(
        manifest_path.parent,
        source_root=source_root,
        write=True,
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["target_copy_count"] == 1
    assert result["manifest_row_update_count"] == 1
    assert target.read_bytes() == source.read_bytes()


def test_refresh_exact_copy_source_modules_resolves_private_macro_source_fixtures(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    marker_path = public_root / "core/private_state_forbidden_classes.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MICROCOSM_ROOT / "core/private_state_forbidden_classes.json", marker_path)
    source_root = tmp_path / "macro-root"
    source_root.mkdir()
    source_ref = (
        "private-macro-source/microcosms/"
        "executable_grammar_metabolism/README.md"
    )
    target_ref = (
        "examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle/source_modules/"
        f"{source_ref}"
    )
    source = public_root / target_ref
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("# Executable grammar metabolism\n", encoding="utf-8")

    manifest_path = (
        public_root
        / "examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle/"
        "executable_grammar_metabolism_source_module_manifest.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "private_macro_source_manifest_v1",
                "modules": [
                    {
                        "module_id": "executable_grammar_metabolism_readme_body_import",
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "source_to_target_relation": "exact_copy",
                        "body_copied": True,
                        "body_in_receipt": False,
                        "sha256": "stale",
                        "source_sha256": "stale",
                        "target_sha256": "stale",
                        "line_count": 1,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = refresh_exact_copy_source_modules(
        manifest_path.parent,
        source_root=source_root,
        write=True,
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["defect_count"] == 0
    assert result["target_copy_count"] == 0
    assert result["manifest_row_update_count"] == 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][0]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert row["source_sha256"] == digest
    assert row["target_sha256"] == digest
    assert row["sha256_match"] is True


def test_refresh_exact_copy_source_modules_refreshes_public_light_edit_metadata(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    marker_path = public_root / "core/private_state_forbidden_classes.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MICROCOSM_ROOT / "core/private_state_forbidden_classes.json", marker_path)
    source_root = tmp_path
    source_ref = "public_examples/public_normalized_source.json"
    source = source_root / source_ref
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text('{"path": "/private/host/path"}\n', encoding="utf-8")

    manifest_path = (
        public_root
        / "examples/public_normalized/exported_bundle/source_module_manifest.json"
    )
    target_ref = "source_modules/public_examples/public_normalized_source.json"
    target = manifest_path.parent / target_ref
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{"path": "<repo-root>/state/runs"}\n', encoding="utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "public_normalized_manifest_v1",
                "modules": [
                    {
                        "module_id": "public_normalized_body_import",
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "source_to_target_relation": (
                            "source_faithful_public_safe_path_normalized_copy"
                        ),
                        "source_import_class": "copied_non_secret_macro_body",
                        "required_anchors": ["<repo-root>/state/runs"],
                        "body_copied": True,
                        "body_in_receipt": False,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = refresh_exact_copy_source_modules(
        manifest_path.parent,
        source_root=source_root,
        write=True,
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["defect_count"] == 0
    assert result["target_copy_count"] == 0
    assert result["manifest_row_update_count"] == 1
    assert target.read_text(encoding="utf-8") == '{"path": "<repo-root>/state/runs"}\n'
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][0]
    assert row["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert row["target_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert row["sha256_match"] is False


def test_refresh_exact_copy_source_modules_accepts_exact_relation_aliases(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    marker_path = public_root / "core/private_state_forbidden_classes.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MICROCOSM_ROOT / "core/private_state_forbidden_classes.json", marker_path)
    source_root = tmp_path
    source_ref = "macro/public_safe.py"
    source = source_root / source_ref
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("VALUE = 42\n", encoding="utf-8")

    manifest_path = public_root / "examples/exact_alias/exported_bundle/source_module_manifest.json"
    target_ref = "source_modules/macro/public_safe.py"
    target = manifest_path.parent / target_ref
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("VALUE = 1\n", encoding="utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "exact_alias_manifest_v1",
                "modules": [
                    {
                        "module_id": "public_safe_alias_body_import",
                        "source_ref": source_ref,
                        "target_ref": target_ref,
                        "source_to_target_relation": "exact_public_safe_macro_copy",
                        "source_import_class": "copied_non_secret_macro_body",
                        "required_anchors": ["VALUE = 42"],
                        "body_copied": True,
                        "body_in_receipt": False,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = refresh_exact_copy_source_modules(
        manifest_path.parent,
        source_root=source_root,
        write=True,
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["defect_count"] == 0
    assert result["target_copy_count"] == 1
    assert result["manifest_row_update_count"] == 1
    assert target.read_text(encoding="utf-8") == "VALUE = 42\n"


def test_public_safe_macro_proof_body_is_importable_with_verification(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    assert result["status"] == "pass"
    assert result["public_safe_body_material_count"] == 254
    assert result["public_safe_body_import_status"] == "pass"
    assert "MACRO_PROJECTION_FORBIDDEN_BODY_IMPORT" not in result["error_codes"]
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["authority_ceiling"]["private_data_equivalence_claim"] is False
    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    assert by_material["lean_certificate_kernel_body_import"]["route"] == (
        "verified_light_edit"
    )
    assert by_material["lean_certificate_kernel_body_import"]["source_refs"] == [
        "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/CertificateKernel.lean"
    ]
    assert by_material["lean_certificate_kernel_body_import"]["body_import_verification"][
        "source_body_digest"
    ] == by_material["lean_certificate_kernel_body_import"]["body_digest"]
    assert result["runtime_severance_board"]["runtime_severance_status"] == "pass"
    assert (
        "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/"
        "CertificateKernel.lean"
        not in result["runtime_severance_board"]["runtime_dependency_refs"]
    )


def test_pattern_ledger_body_is_imported_as_exact_copy(tmp_path: Path) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    body_import_ids = {
        row["material_id"]
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    assert "ledger_row_metadata_projection" in body_import_ids
    protocol_rows = {
        row["material_id"]: row
        for row in json.loads(
            (
                public_root
                / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
                / "projection_protocol.json"
            ).read_text(encoding="utf-8")
        )["copied_material"]
    }
    ledger_row = protocol_rows["ledger_row_metadata_projection"]
    target = public_root / ledger_row["target_ref"]
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    assert target.is_file()
    assert target.read_text(encoding="utf-8").count("\n") == 373
    assert ledger_row["body_copied"] is True
    assert ledger_row["material_class"] == "public_macro_pattern_body"
    assert ledger_row["public_safe_mode"] == "direct_verified_macro_body"
    assert ledger_row["body_digest"] == digest
    assert ledger_row["body_import_verification"]["verification_mode"] == (
        "exact_source_digest_match"
    )
    assert ledger_row["body_import_verification"]["source_body_digest"] == digest
    assert ledger_row["body_import_verification"]["target_body_digest"] == digest
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["projection_protocol_self_host"]["public_safe_body_material_ids"] == [
        "ledger_row_metadata_projection"
    ]


def test_work_landing_tool_body_is_imported_as_light_edit(tmp_path: Path) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    body_import_ids = {
        row["material_id"]
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    assert "work_landing_tool_body_import" in body_import_ids
    protocol_rows = {
        row["material_id"]: row
        for row in json.loads(
            (
                public_root
                / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
                / "projection_protocol.json"
            ).read_text(encoding="utf-8")
        )["copied_material"]
    }
    work_landing_row = protocol_rows["work_landing_tool_body_import"]
    assert work_landing_row["body_copied"] is True
    assert work_landing_row["material_class"] == "public_macro_tool_body"
    assert work_landing_row["target_ref"] == "src/microcosm_core/macro_tools/work_landing.py"
    assert work_landing_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    status = build_public_work_landing_status(
        subject_ids=["cap_demo"],
        owned_paths=["microcosm-substrate/tests/test_macro_projection_import_protocol.py"],
    )
    reconcile = build_public_work_landing_reconcile_plan(
        subject_ids=["cap_demo"],
        owned_paths=["microcosm-substrate/tests/test_macro_projection_import_protocol.py"],
    )
    admission = build_public_workitem_write_admission(
        subject_ids=["cap_demo"],
        owned_paths=["microcosm-substrate/tests/test_macro_projection_import_protocol.py"],
    )
    assert status["status"] == "pass"
    assert status["landing_lane"] == "scoped_commit"
    assert reconcile["work_landing_reconcile_status"] == "ordered_dry_run_plan_emitted"
    assert admission["write_admitted"] is True
    assert status["body_in_receipt"] is False
    assert status["authority_ceiling"]["live_task_ledger_mutation_authorized"] is False


def test_agent_execution_trace_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    agent_row = by_material["agent_execution_trace_body_import"]
    target = public_root / agent_row["target_ref"]
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    trace = build_public_computer_use_trace(COMPUTER_USE_BUNDLE_INPUT)

    assert target.is_file()
    assert agent_row["material_class"] == "public_macro_tool_body"
    assert agent_row["body_digest"] == digest
    assert agent_row["body_import_verification"]["target_body_digest"] == digest
    assert agent_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert trace["status"] == "pass"
    assert trace["span_count"] > 0
    assert trace["authority_ceiling"]["provider_payload_read"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["agent_execution_trace_refactor"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_execution_trace_refactor"]["action_required"] is False


def test_agent_trace_route_repair_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    route_repair_row = by_material["agent_trace_route_repair_body_import"]
    target = public_root / route_repair_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "system/lib/navigation_route_intervention.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    view = build_public_agent_trace_route_repair_view(
        load_public_agent_trace_route_repair_bundle(AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT)
    )
    replay = run_agent_trace_route_repair_bundle(
        AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert route_repair_row["material_class"] == "public_macro_tool_body"
    assert route_repair_row["body_digest"] == digest
    recorded_source_digest = route_repair_row["body_import_verification"][
        "source_body_digest"
    ]
    if recorded_source_digest != source_digest:
        assert route_repair_row["body_import_verification"]["rewrite_recipe_ref"]
        assert route_repair_row["body_import_verification"]["source_symbol_refs"]
    else:
        assert recorded_source_digest == source_digest
    assert route_repair_row["body_import_verification"]["target_body_digest"] == digest
    assert route_repair_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert view["status"] == "pass"
    assert view["route_repair_summary"]["suggested_route_count"] == 4
    assert replay["status"] == "pass"
    assert replay["suggested_route_count"] == 4
    assert replay["authority_ceiling"]["live_hook_install_authorized"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["agent_trace_route_repair_observability_import"][
        "projection_status"
    ] == "public_runtime_import_landed"
    assert by_cell["agent_trace_route_repair_observability_import"][
        "action_required"
    ] is False


def test_agent_observability_store_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    store_row = by_material["agent_observability_store_body_import"]
    target = public_root / store_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "system/lib/agent_observability.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    view = build_public_agent_observability_store_view(
        load_public_agent_observability_store_bundle(AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT)
    )
    replay = run_agent_observability_store_bundle(
        AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert store_row["material_class"] == "public_macro_tool_body"
    assert store_row["body_digest"] == digest
    assert store_row["body_import_verification"]["source_body_digest"] == source_digest
    assert store_row["body_import_verification"]["target_body_digest"] == digest
    assert store_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert view["status"] == "pass"
    assert view["store_summary"]["event_count"] == 6
    assert replay["status"] == "pass"
    assert replay["accepted_event_count"] == 6
    assert replay["authority_ceiling"]["live_home_session_logs_read"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["agent_observability_store_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_observability_store_import"]["action_required"] is False


def test_agent_session_attribution_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    attribution_row = by_material["agent_session_attribution_body_import"]
    target = public_root / attribution_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "system/lib/agent_session_attribution.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    replay = run_session_attribution_bundle(
        SESSION_ATTRIBUTION_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert attribution_row["material_class"] == "public_macro_tool_body"
    assert attribution_row["body_digest"] == digest
    assert attribution_row["body_import_verification"]["source_body_digest"] == source_digest
    assert attribution_row["body_import_verification"]["target_body_digest"] == digest
    assert attribution_row["body_import_verification"]["verification_mode"] == (
        "exact_source_digest_match"
    )
    assert replay["status"] == "pass"
    assert replay["matched_session_count"] == 2
    assert replay["authority_ceiling"]["raw_transcript_body_exported"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["agent_session_attribution_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["agent_session_attribution_import"]["action_required"] is False


def test_continuation_packet_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    continuation_row = by_material["continuation_packet_body_import"]
    target = public_root / continuation_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "system/lib/continuation_packet.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    replay = run_multi_agent_fanin_bundle(
        MULTI_AGENT_FANIN_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert continuation_row["material_class"] == "public_macro_tool_body"
    assert continuation_row["body_digest"] == digest
    assert continuation_row["body_import_verification"]["source_body_digest"] == source_digest
    assert continuation_row["body_import_verification"]["target_body_digest"] == digest
    assert continuation_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert replay["status"] == "pass"
    assert replay["continuation_packet_count"] == 2
    assert replay["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["multi_agent_fanin_replay_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["multi_agent_fanin_replay_import"]["action_required"] is False


def test_agent_route_fanin_continuation_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_ROUTE_FANIN_CONTINUATION_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_route_fanin_continuation_source_modules_import",
    )


def test_agent_route_session_attribution_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_ROUTE_SESSION_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_route_session_attribution_source_modules_import",
    )


def test_bridge_resume_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    bridge_row = by_material["bridge_resume_body_import"]
    target = public_root / bridge_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "tools/meta/bridge/bridge_resume.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    replay = run_bridge_dispatch_yield_resume_bundle(
        BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert bridge_row["material_class"] == "public_macro_tool_body"
    assert bridge_row["body_digest"] == digest
    assert bridge_row["body_import_verification"]["source_body_digest"] == source_digest
    assert bridge_row["body_import_verification"]["target_body_digest"] == digest
    assert bridge_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert replay["status"] == "pass"
    assert replay["trigger_written_count"] == 2
    assert replay["no_send_trigger_count"] == 2
    assert replay["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["multi_agent_fanin_replay_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["multi_agent_fanin_replay_import"]["public_safe_body_material_ids"] == [
        "continuation_packet_body_import",
        "bridge_resume_body_import",
    ]


def test_controller_heartbeat_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    controller_row = by_material["controller_heartbeat_body_import"]
    target = public_root / controller_row["target_ref"]
    source = MICROCOSM_ROOT.parent / "system/lib/controller_heartbeat.py"
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    replay = run_controller_heartbeat_bundle(
        CONTROLLER_HEARTBEAT_BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime",
        command="pytest",
    )

    assert target.is_file()
    assert controller_row["material_class"] == "public_macro_tool_body"
    assert controller_row["body_digest"] == digest
    assert controller_row["body_import_verification"]["source_body_digest"] == source_digest
    assert controller_row["body_import_verification"]["target_body_digest"] == digest
    assert controller_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert replay["status"] == "pass"
    assert replay["heartbeat_count"] == 2
    assert replay["exact_5x5_count"] == 2
    assert replay["dedupe_duplicate_count"] == 1
    assert replay["authority_ceiling"]["seed_or_blackboard_read_authorized"] is False
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["controller_continuity_heartbeat_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["controller_continuity_heartbeat_import"]["action_required"] is False
    assert by_cell["controller_continuity_heartbeat_import"][
        "public_safe_body_material_ids"
    ] == [
        "controller_heartbeat_body_import",
    ]


def test_navigation_route_plane_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    route_row = by_material["navigation_route_plane_body_import"]
    target = public_root / route_row["target_ref"]
    digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
    route_payload = json.loads((ROUTE_PLANE_BUNDLE_INPUT / "route_rows.json").read_text())
    source_manifest = json.loads(
        (ROUTE_PLANE_BUNDLE_INPUT / "source_module_manifest.json").read_text()
    )

    assert target.is_file()
    assert route_row["material_class"] == "public_macro_receipt_body"
    assert route_row["body_digest"] == digest
    assert route_row["body_import_verification"]["target_body_digest"] == digest
    assert route_row["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert route_payload["body_material_status"] == (
        "copied_non_secret_macro_route_substrate_with_provenance"
    )
    assert route_payload["row_count"] == 41
    for module in source_manifest["modules"]:
        material = by_material[module["module_id"]]
        source_target = public_root / material["target_ref"]
        module_digest = f"sha256:{hashlib.sha256(source_target.read_bytes()).hexdigest()}"

        assert source_target.is_file()
        assert material["material_class"] == "public_macro_tool_body"
        assert material["body_digest"] == module_digest
        assert material["body_import_verification"]["source_body_digest"] == module_digest
        assert material["body_import_verification"]["target_body_digest"] == module_digest
        assert material["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["navigation_route_plane_import"]["public_safe_body_material_ids"] == (
        ROUTE_PLANE_BODY_MATERIAL_IDS
    )
    assert by_cell["navigation_route_plane_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["navigation_route_plane_import"]["action_required"] is False


def test_work_landing_control_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in WORK_LANDING_CONTROL_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target = public_root / row["target_ref"]
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["body_digest"] == digest
        _assert_source_digest_matches_import_contract(
            row=row,
            result=result,
            source=source,
            target=target,
        )
        _assert_public_safe_verification_mode(row)
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["work_landing_control_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == WORK_LANDING_CONTROL_BODY_MATERIAL_IDS


def test_task_ledger_control_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in TASK_LEDGER_CONTROL_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        _assert_source_digest_matches_import_contract(
            row=row,
            result=result,
            source=source,
            target=target,
        )
        _assert_public_safe_verification_mode(row)
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["task_ledger_control_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == TASK_LEDGER_CONTROL_BODY_MATERIAL_IDS


def test_work_ledger_control_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in WORK_LEDGER_CONTROL_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        _assert_source_digest_matches_import_contract(
            row=row,
            result=result,
            source=source,
            target=target,
        )
        _assert_public_safe_verification_mode(row)
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["work_ledger_control_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == WORK_LEDGER_CONTROL_BODY_MATERIAL_IDS


def test_checkpoint_lane_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in CHECKPOINT_LANE_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        _assert_source_digest_matches_import_contract(
            row=row,
            result=result,
            source=source,
            target=target,
        )
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["checkpoint_lane_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == CHECKPOINT_LANE_BODY_MATERIAL_IDS


def test_command_output_projection_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in COMMAND_OUTPUT_PROJECTION_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        _assert_source_digest_matches_import_contract(
            row=row,
            result=result,
            source=source,
            target=target,
        )
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["command_output_projection_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert (
        cell["public_safe_body_material_ids"]
        == COMMAND_OUTPUT_PROJECTION_BODY_MATERIAL_IDS
    )


def test_trace_capsule_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in TRACE_CAPSULE_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        _assert_source_digest_matches_import_contract(
            row=row,
            result=result,
            source=source,
            target=target,
        )
        verification = row["body_import_verification"]
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
        target_digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        if verification["source_body_digest"] == target_digest:
            assert verification["verification_mode"] == "exact_source_digest_match"
            assert verification["source_to_target_relation"] in (
                macro_projection_import_protocol.EXACT_COPY_SOURCE_TO_TARGET_RELATIONS
            )
        else:
            assert verification["source_body_digest"] == source_digest
            assert verification["verification_mode"] == "verified_light_edit_recipe"
            assert verification["source_to_target_relation"] in (
                macro_projection_import_protocol.VERIFIED_LIGHT_EDIT_SOURCE_TO_TARGET_RELATIONS
            )
        assert verification["source_line_count"] == verification["target_line_count"]
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["trace_capsule_prompt_edit_capture_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == TRACE_CAPSULE_BODY_MATERIAL_IDS


def test_route_selection_control_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in ROUTE_SELECTION_CONTROL_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        _assert_source_digest_matches_import_contract(
            row=row,
            result=result,
            source=source,
            target=target,
        )
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["route_selection_control_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == ROUTE_SELECTION_CONTROL_BODY_MATERIAL_IDS


def test_route_worker_packet_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=ROUTE_WORKER_PACKET_BODY_MATERIAL_IDS,
        cell_id="route_worker_packet_source_modules_import",
    )


def test_route_operator_court_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=ROUTE_OPERATOR_COURT_BODY_MATERIAL_IDS,
        cell_id="route_operator_court_source_modules_import",
    )


def test_route_discovery_confirmation_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=ROUTE_DISCOVERY_CONFIRMATION_BODY_MATERIAL_IDS,
        cell_id="route_discovery_confirmation_source_modules_import",
    )


def test_projection_loss_audit_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=PROJECTION_LOSS_AUDIT_BODY_MATERIAL_IDS,
        cell_id="projection_loss_audit_source_modules_import",
    )


def test_semantic_route_quality_audit_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=SEMANTIC_ROUTE_QUALITY_AUDIT_BODY_MATERIAL_IDS,
        cell_id="semantic_route_quality_audit_source_modules_import",
    )


def test_reaction_wiring_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=REACTION_WIRING_BODY_MATERIAL_IDS,
        cell_id="reaction_wiring_source_modules_import",
    )


def test_navigation_context_rosetta_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = preview_import_plan(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in NAVIGATION_CONTEXT_ROSETTA_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        assert row["body_import_verification"]["source_body_digest"] == source_digest
        assert row["body_import_verification"]["target_body_digest"] == digest
        verification = row["body_import_verification"]
        if source_digest == digest:
            assert verification["verification_mode"] == "exact_source_digest_match"
            assert verification["source_to_target_relation"] in (
                macro_projection_import_protocol.EXACT_COPY_SOURCE_TO_TARGET_RELATIONS
            )
        else:
            assert verification["verification_mode"] == "verified_light_edit_recipe"
            assert verification["source_to_target_relation"] in (
                macro_projection_import_protocol.VERIFIED_LIGHT_EDIT_SOURCE_TO_TARGET_RELATIONS
            )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["navigation_context_rosetta_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert (
        cell["public_safe_body_material_ids"]
        == NAVIGATION_CONTEXT_ROSETTA_BODY_MATERIAL_IDS
    )


def test_bootstrap_route_surface_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in BOOTSTRAP_ROUTE_SURFACE_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        _assert_source_digest_matches_import_contract(
            row=row,
            result=result,
            source=source,
            target=target,
        )
        assert row["body_import_verification"]["target_body_digest"] == digest
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    assert by_material["bootstrap_agent_bootstrap_live_body_import"][
        "material_class"
    ] == "public_macro_receipt_body"
    assert by_material["bootstrap_agent_bootstrap_projection_body_import"][
        "material_class"
    ] == "public_macro_tool_body"
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["bootstrap_route_surface_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == BOOTSTRAP_ROUTE_SURFACE_BODY_MATERIAL_IDS


def test_agent_operating_packet_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in AGENT_OPERATING_PACKET_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        _assert_source_digest_matches_import_contract(
            row=row,
            result=result,
            source=source,
            target=target,
        )
        _assert_public_safe_verification_mode(row)
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    assert by_material["agent_operating_packet_sidecar_body_import"][
        "material_class"
    ] == "public_macro_receipt_body"
    assert by_material["agent_operating_packet_projection_body_import"][
        "material_class"
    ] == "public_macro_tool_body"
    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["agent_operating_packet_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == AGENT_OPERATING_PACKET_BODY_MATERIAL_IDS


def test_active_execution_constellation_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in ACTIVE_EXECUTION_CONSTELLATION_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        _assert_source_digest_matches_import_contract(
            row=row,
            result=result,
            source=source,
            target=target,
        )
        assert row["body_import_verification"]["target_body_digest"] == digest
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["active_execution_constellation_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == (
        ACTIVE_EXECUTION_CONSTELLATION_BODY_MATERIAL_IDS
    )


def test_task_ledger_startup_pressure_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=TASK_LEDGER_STARTUP_PRESSURE_BODY_MATERIAL_IDS,
        cell_id="task_ledger_startup_pressure_source_modules_import",
    )


def test_executable_grammar_metabolism_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in EXECUTABLE_GRAMMAR_METABOLISM_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_ref = row["source_refs"][0]

        assert target.is_file()
        assert "self-indexing-cognitive-substrate" not in source_ref
        assert "self-indexing-cognitive-substrate" not in row["target_ref"]
        assert source_ref.startswith(
            "private-macro-source/microcosms/executable_grammar_metabolism/"
        )
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        assert row["body_import_verification"]["source_body_digest"] == digest
        assert row["body_import_verification"]["target_body_digest"] == digest
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_text_in_receipt"] is False

    assert by_material["executable_grammar_metabolism_readme_body_import"][
        "material_class"
    ] == "public_macro_tool_body"
    assert by_material["executable_grammar_metabolism_board_body_import"][
        "material_class"
    ] == "public_macro_tool_body"
    assert by_material["executable_grammar_metabolism_receipt_body_import"][
        "material_class"
    ] == "public_macro_receipt_body"

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["executable_grammar_metabolism_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "real_runtime_receipt",
        "owner_standard_bound",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == (
        EXECUTABLE_GRAMMAR_METABOLISM_BODY_MATERIAL_IDS
    )


def test_navigation_coverage_matrix_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in NAVIGATION_COVERAGE_MATRIX_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        assert row["body_import_verification"]["source_body_digest"] == source_digest
        assert row["body_import_verification"]["target_body_digest"] == digest
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["navigation_coverage_matrix_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == (
        NAVIGATION_COVERAGE_MATRIX_BODY_MATERIAL_IDS
    )


def test_navigation_metabolism_ledger_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in NAVIGATION_METABOLISM_LEDGER_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        assert row["body_import_verification"]["source_body_digest"] == source_digest
        assert row["body_import_verification"]["target_body_digest"] == digest
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["navigation_metabolism_ledger_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == (
        NAVIGATION_METABOLISM_LEDGER_BODY_MATERIAL_IDS
    )


def test_navigation_surface_audit_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in NAVIGATION_SURFACE_AUDIT_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        assert row["body_import_verification"]["source_body_digest"] == source_digest
        assert row["body_import_verification"]["target_body_digest"] == digest
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["navigation_surface_audit_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == (
        NAVIGATION_SURFACE_AUDIT_BODY_MATERIAL_IDS
    )


def test_command_node_cache_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in COMMAND_NODE_CACHE_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        assert row["body_import_verification"]["source_body_digest"] == source_digest
        assert row["body_import_verification"]["target_body_digest"] == digest
        assert row["body_import_verification"]["verification_mode"] == (
            "exact_source_digest_match"
        )
        assert row["body_import_verification"]["source_line_count"] == (
            row["body_import_verification"]["target_line_count"]
        )
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell["command_node_cache_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == (
        COMMAND_NODE_CACHE_BODY_MATERIAL_IDS
    )


def test_work_admission_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=WORK_ADMISSION_BODY_MATERIAL_IDS,
        cell_id="work_admission_source_modules_import",
    )


def _assert_exact_source_module_body_import(
    *,
    result: dict[str, Any],
    public_root: Path,
    material_ids: list[str],
    cell_id: str,
    expected_material_class: str = "public_macro_tool_body",
    expected_material_classes_by_id: dict[str, str] | None = None,
) -> None:
    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in material_ids:
        row = by_material[material_id]
        expected_class = (
            expected_material_classes_by_id or {}
        ).get(material_id, expected_material_class)
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == expected_class
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        verification = row["body_import_verification"]
        _assert_source_digest_matches_import_contract(
            row=row,
            result=result,
            source=source,
            target=target,
        )
        if verification["source_body_digest"] == digest:
            assert verification["verification_mode"] == "exact_source_digest_match"
            assert verification["source_to_target_relation"] in (
                macro_projection_import_protocol.EXACT_COPY_SOURCE_TO_TARGET_RELATIONS
            )
        else:
            assert verification["source_body_digest"] == source_digest
            assert verification["verification_mode"] == "verified_light_edit_recipe"
            assert verification["source_to_target_relation"] in (
                macro_projection_import_protocol.VERIFIED_LIGHT_EDIT_SOURCE_TO_TARGET_RELATIONS
            )
        assert verification["source_line_count"] == verification["target_line_count"]
        assert row["body_text_in_receipt"] is False

    by_cell = {
        row["cell_id"]: row
        for row in result["projection_intake_board"]["projection_cells"]
    }
    cell = by_cell[cell_id]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == material_ids


def test_provider_context_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=PROVIDER_CONTEXT_SOURCE_BODY_MATERIAL_IDS,
        cell_id="provider_context_source_modules_import",
        expected_material_classes_by_id=PROVIDER_CONTEXT_SOURCE_BODY_MATERIAL_CLASSES,
    )


def test_proof_diagnostic_runtime_artifact_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=PROOF_DIAGNOSTIC_RING2_RUNTIME_BODY_MATERIAL_IDS,
        cell_id="proof_diagnostic_evidence_spine_runtime_artifacts",
        expected_material_class="public_macro_receipt_body",
    )


def test_world_model_projection_drift_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=WORLD_MODEL_PROJECTION_DRIFT_SOURCE_BODY_MATERIAL_IDS,
        cell_id="world_model_projection_drift_source_modules_import",
    )


def test_spatial_world_model_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=SPATIAL_WORLD_MODEL_SOURCE_BODY_MATERIAL_IDS,
        cell_id="spatial_world_model_source_modules_import",
    )


def test_mechanistic_oracle_attribution_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=MECHANISTIC_ORACLE_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS,
        cell_id="mechanistic_oracle_attribution_source_modules_import",
        expected_material_class="public_macro_pattern_body",
    )


def test_navigation_clusterability_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=NAVIGATION_CLUSTERABILITY_BODY_MATERIAL_IDS,
        cell_id="navigation_clusterability_source_modules_import",
    )


def test_annex_routing_coverage_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=ANNEX_ROUTING_COVERAGE_BODY_MATERIAL_IDS,
        cell_id="annex_routing_coverage_source_modules_import",
    )


def test_annex_currentness_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=ANNEX_CURRENTNESS_BODY_MATERIAL_IDS,
        cell_id="annex_currentness_source_modules_import",
    )


def test_entrypoint_health_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=ENTRYPOINT_HEALTH_BODY_MATERIAL_IDS,
        cell_id="entrypoint_health_source_modules_import",
    )


def test_agent_entrypoint_audit_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_ENTRYPOINT_AUDIT_BODY_MATERIAL_IDS,
        cell_id="agent_entrypoint_audit_source_modules_import",
    )


def test_navigation_fitness_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=NAVIGATION_FITNESS_BODY_MATERIAL_IDS,
        cell_id="navigation_fitness_source_modules_import",
    )


def test_dynamic_paper_lattice_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=DYNAMIC_PAPER_LATTICE_BODY_MATERIAL_IDS,
        cell_id="dynamic_paper_lattice_source_modules_import",
    )


def test_kind_atlas_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=KIND_ATLAS_BODY_MATERIAL_IDS,
        cell_id="kind_atlas_source_modules_import",
    )


def test_semantic_routing_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=SEMANTIC_ROUTING_BODY_MATERIAL_IDS,
        cell_id="semantic_routing_source_modules_import",
    )


def test_embedding_substrate_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=EMBEDDING_SUBSTRATE_BODY_MATERIAL_IDS,
        cell_id="embedding_substrate_source_modules_import",
    )


def test_nvidia_nim_provider_boundary_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=NVIDIA_NIM_PROVIDER_BOUNDARY_BODY_MATERIAL_IDS,
        cell_id="nvidia_nim_provider_boundary_source_modules_import",
    )


def test_agent_provider_router_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_PROVIDER_ROUTER_BODY_MATERIAL_IDS,
        cell_id="agent_provider_router_source_modules_import",
    )


def test_bridge_route_config_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=BRIDGE_ROUTE_CONFIG_BODY_MATERIAL_IDS,
        cell_id="bridge_route_config_source_modules_import",
    )


def test_kernel_bridge_config_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=KERNEL_BRIDGE_CONFIG_BODY_MATERIAL_IDS,
        cell_id="kernel_bridge_config_source_modules_import",
    )


def test_observe_runtime_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=OBSERVE_RUNTIME_BODY_MATERIAL_IDS,
        cell_id="observe_runtime_source_modules_import",
    )


def test_kernel_state_registry_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=KERNEL_STATE_REGISTRY_BODY_MATERIAL_IDS,
        cell_id="kernel_state_registry_source_modules_import",
    )


def test_agent_execution_trace_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_EXECUTION_TRACE_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_execution_trace_source_modules_import",
    )


def test_agent_observability_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_OBSERVABILITY_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_observability_source_modules_import",
    )


def test_agent_observability_animation_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_OBSERVABILITY_ANIMATION_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_observability_animation_source_modules_import",
    )


def test_agent_observability_classification_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_OBSERVABILITY_CLASSIFICATION_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_observability_classification_source_modules_import",
    )


def test_agent_mission_status_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_MISSION_STATUS_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_mission_status_source_modules_import",
    )


def test_operator_handoff_linkage_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=OPERATOR_HANDOFF_LINKAGE_SOURCE_BODY_MATERIAL_IDS,
        cell_id="operator_handoff_linkage_source_modules_import",
    )


def test_prompt_shelf_movement_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=PROMPT_SHELF_MOVEMENT_SOURCE_BODY_MATERIAL_IDS,
        cell_id="prompt_shelf_movement_source_modules_import",
    )


def test_prompt_shelf_uppropagation_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=PROMPT_SHELF_UPPROPAGATION_SOURCE_BODY_MATERIAL_IDS,
        cell_id="prompt_shelf_uppropagation_source_modules_import",
    )


def test_prompt_shelf_uppropagation_digest_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=PROMPT_SHELF_UPPROPAGATION_DIGEST_SOURCE_BODY_MATERIAL_IDS,
        cell_id="prompt_shelf_uppropagation_digest_source_modules_import",
    )


def test_prompt_shelf_runs_index_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=PROMPT_SHELF_RUNS_INDEX_SOURCE_BODY_MATERIAL_IDS,
        cell_id="prompt_shelf_runs_index_source_modules_import",
    )


def test_standard_option_surface_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=STANDARD_OPTION_SURFACE_SOURCE_BODY_MATERIAL_IDS,
        cell_id="standard_option_surface_source_modules_import",
    )


def test_bridge_runtime_continuity_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=BRIDGE_RUNTIME_CONTINUITY_SOURCE_BODY_MATERIAL_IDS,
        cell_id="bridge_runtime_continuity_source_modules_import",
    )


def test_session_heartbeat_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=SESSION_HEARTBEAT_SOURCE_BODY_MATERIAL_IDS,
        cell_id="session_heartbeat_source_modules_import",
    )


def test_orchestration_overnight_control_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=ORCHESTRATION_OVERNIGHT_CONTROL_SOURCE_BODY_MATERIAL_IDS,
        cell_id="orchestration_overnight_control_source_modules_import",
    )


def test_seed_distillation_subagent_lane_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=SEED_DISTILLATION_SUBAGENT_LANE_SOURCE_BODY_MATERIAL_IDS,
        cell_id="seed_distillation_subagent_lane_source_modules_import",
    )


def test_seed_distillation_dependency_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=SEED_DISTILLATION_DEPENDENCY_SOURCE_BODY_MATERIAL_IDS,
        cell_id="seed_distillation_dependency_source_modules_import",
    )


def test_artifact_projection_debt_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=ARTIFACT_PROJECTION_DEBT_SOURCE_BODY_MATERIAL_IDS,
        cell_id="artifact_projection_debt_source_modules_import",
    )


def test_navigation_trace_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=NAVIGATION_TRACE_SOURCE_BODY_MATERIAL_IDS,
        cell_id="navigation_trace_source_modules_import",
    )


def test_generated_projection_control_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=GENERATED_PROJECTION_CONTROL_SOURCE_BODY_MATERIAL_IDS,
        cell_id="generated_projection_control_source_modules_import",
    )


def test_shared_worktree_guard_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=SHARED_WORKTREE_GUARD_SOURCE_BODY_MATERIAL_IDS,
        cell_id="shared_worktree_guard_source_modules_import",
    )


def test_raw_git_commit_guard_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=RAW_GIT_COMMIT_GUARD_SOURCE_BODY_MATERIAL_IDS,
        cell_id="raw_git_commit_guard_source_modules_import",
    )


def test_formal_math_proofline_spine_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    bundle_run = _macro_projection_bundle_run()
    public_root = bundle_run["public_root"]
    result = bundle_run["result"]

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=FORMAL_MATH_PROOFLINE_SPINE_SOURCE_BODY_MATERIAL_IDS,
        cell_id="formal_math_proofline_spine_source_modules_import",
    )


def test_import_plan_rejects_missing_public_safe_body_material_id() -> None:
    result = validate_import_plan(
        {
            "plan_id": "missing_public_safe_body_material",
            "next_best_lane": "real_substrate_import_path",
            "proposed_cells": [
                {
                    "cell_id": "cell_with_missing_material",
                    "source_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
                    "target_refs": ["fixtures/example.json"],
                    "validation_refs": ["receipts/example.json"],
                    "public_safe_body_material_ids": ["missing_body_material"],
                },
                {
                    "cell_id": "cell_two",
                    "source_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
                    "target_refs": ["fixtures/example-two.json"],
                    "validation_refs": ["receipts/example-two.json"],
                },
                {
                    "cell_id": "cell_three",
                    "source_refs": ["state/microcosm_portfolio/extracted_patterns_ledger.jsonl"],
                    "target_refs": ["fixtures/example-three.json"],
                    "validation_refs": ["receipts/example-three.json"],
                },
            ],
        },
        public_safe_material_ids={"known_body_material"},
    )

    assert result["status"] == "blocked"
    assert result["blocking_finding_count"] == 1
    assert result["findings"][0]["error_code"] == (
        "MACRO_PROJECTION_PUBLIC_SAFE_BODY_MATERIAL_MISSING"
    )


def test_import_plan_rejects_public_bound_private_root_refs() -> None:
    result = validate_import_plan(
        {
            "plan_id": "private_root_ref_import_plan",
            "next_best_lane": "real_substrate_import_path",
            "proposed_cells": [
                {
                    "cell_id": "cell_with_private_root_refs",
                    "source_refs": [
                        (
                            "self-indexing-cognitive-substrate/microcosms/"
                            "executable_grammar_metabolism/README.md"
                        )
                    ],
                    "target_refs": [
                        (
                            "examples/macro_projection_import_protocol/"
                            "exported_projection_import_bundle/source_modules/"
                            "self-indexing-cognitive-substrate/microcosms/"
                            "executable_grammar_metabolism/README.md"
                        )
                    ],
                    "validation_refs": ["receipts/example.json"],
                },
                {
                    "cell_id": "cell_two",
                    "source_refs": ["public-source.json"],
                    "target_refs": ["fixtures/example-two.json"],
                    "validation_refs": ["receipts/example-two.json"],
                },
                {
                    "cell_id": "cell_three",
                    "source_refs": ["public-source-three.json"],
                    "target_refs": ["fixtures/example-three.json"],
                    "validation_refs": ["receipts/example-three.json"],
                },
            ],
        }
    )

    assert result["status"] == "blocked"
    assert result["public_bound_private_root_ref_count"] == 2
    assert {
        finding["subject_id"]
        for finding in result["findings"]
        if finding["error_code"] == "MACRO_PROJECTION_PUBLIC_BOUND_PRIVATE_ROOT_REF"
    } == {
        "cell_with_private_root_refs:source_ref:self-indexing-cognitive-substrate",
        "cell_with_private_root_refs:target_ref:self-indexing-cognitive-substrate",
    }
