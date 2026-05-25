from __future__ import annotations

import hashlib
import json
import shutil
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
from microcosm_core.organs.macro_projection_import_protocol import (
    EXPECTED_NEGATIVE_CASES,
    preview_import_plan,
    run,
    run_projection_bundle,
    validate_import_plan,
    validate_projection_protocol,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/macro_projection_import_protocol/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
)
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
    "command_node_cache_test_body_import",
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
BRIDGE_RUNTIME_CONTINUITY_SOURCE_BODY_MATERIAL_IDS = [
    "bridge_resume_source_body_import",
    "controller_heartbeat_source_body_import",
    "continuation_packet_source_body_import",
    "bridge_resume_test_body_import",
    "controller_heartbeat_test_body_import",
    "continuation_packet_test_body_import",
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
PROVIDER_CONTEXT_SOURCE_BODY_MATERIAL_IDS = [
    "provider_context_graph_benchmark_body_import",
    "provider_context_formal_ladder_eval_body_import",
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
    _copy_public_file(
        public_root,
        "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle/"
        "lake_project/MicrocosmProofWitness/CertificateKernel.lean",
    )
    _copy_dependency_preflight_receipt(public_root)
    _align_organ_registry_to_dependency_preflight(public_root)
    return public_root


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
    assert result["projection_cell_count"] == 52
    assert result["ready_projection_cell_count"] == 52
    assert result["blocked_projection_cell_count"] == 0
    assert result["source_ref_count"] >= 2
    assert result["public_runtime_ref_count"] >= 2
    assert result["validation_ref_count"] >= 2
    assert result["public_safe_body_material_count"] == 151
    assert result["public_safe_body_import_status"] == "pass"
    assert result["runtime_severance_status"] == "pass"
    assert result["runtime_dependency_status"] == "pass"
    assert result["dependency_preflight_gate_status"] == "pass"
    assert result["dependency_preflight_receipt_ref"] == (
        "receipts/preflight/dependency_preflight.json"
    )
    assert result["organ_lifecycle_coverage_status"] == "pass"
    assert result["organ_lifecycle_coverage_counts"]["accepted_organ_count"] == 46
    assert (
        result["organ_lifecycle_coverage_counts"][
            "public_authority_expected_organ_count"
        ]
        == 44
    )
    assert result["macro_runtime_dependency_count"] == 0
    assert result["authority_ceiling"]["credential_or_account_bound_bodies_exported"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["projection_board"]["next_best_lane"] == "real_substrate_import_path"
    assert result["projection_board"]["intake_board_ref"] == "projection_import_intake_board.json"
    assert result["projection_board"]["runtime_severance_board_embedded"] is True
    assert result["projection_intake_board"]["ready_cell_count"] == 52
    assert result["projection_intake_board"]["blocked_cell_count"] == 0
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_intake_board"]["landed_cell_count"] == 52
    assert result["projection_intake_board"]["projection_status_counts"] == {
        "public_runtime_import_landed": 50,
        "runtime_bridge_landed": 1,
        "self_hosted_status_protocol_landed": 1,
    }
    assert result["projection_intake_board"]["omitted_material_count"] == 2
    assert "public_macro_tool_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_proof_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 151
    assert result["projection_intake_board"]["public_safe_body_import_routes"] == {
        "direct_verified_public": 3,
        "verified_light_edit": 148,
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
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
    for material_id in RING2_PREMISE_RETRIEVAL_BODY_MATERIAL_IDS:
        assert by_material[material_id]["material_class"] == "public_macro_receipt_body"
        assert by_material[material_id]["classification_status"] == "pass"
        assert by_material[material_id]["body_text_in_receipt"] is False
        assert by_material[material_id]["body_import_verification"][
            "verification_mode"
        ] == "exact_source_digest_match"
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
        *BRIDGE_RUNTIME_CONTINUITY_SOURCE_BODY_MATERIAL_IDS,
        *FORMAL_MATH_PROOFLINE_SPINE_SOURCE_BODY_MATERIAL_IDS,
    ]:
        assert by_material[material_id]["material_class"] == "public_macro_tool_body"
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
    severance_board = result["runtime_severance_board"]
    assert severance_board["standalone_runtime_candidate"] is True
    assert severance_board["dependency_preflight_gate_status"] == "pass"
    assert severance_board["dependency_preflight_gate"]["status"] == "pass"
    assert severance_board["dependency_preflight_gate"]["defect_count"] == 0
    assert severance_board["organ_lifecycle_coverage_status"] == "pass"
    assert severance_board["organ_lifecycle_coverage_counts"]["runtime_step_count"] == 46
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
        assert "/Users/" not in text
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


def test_macro_projection_exported_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_projection_import_bundle"
    assert result["bundle_id"] == "macro_projection_import_protocol_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["projection_cell_count"] == 52
    assert result["projection_intake_board"]["ready_cell_count"] == 52
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_board"]["release_authorized"] is False
    assert result["projection_board"]["private_data_equivalence_claim"] is False
    assert result["public_safe_body_material_count"] == 151
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 151
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
        *BOOTSTRAP_ROUTE_SURFACE_BODY_MATERIAL_IDS,
        *AGENT_OPERATING_PACKET_BODY_MATERIAL_IDS,
        *ACTIVE_EXECUTION_CONSTELLATION_BODY_MATERIAL_IDS,
        *TASK_LEDGER_STARTUP_PRESSURE_BODY_MATERIAL_IDS,
        *NAVIGATION_COVERAGE_MATRIX_BODY_MATERIAL_IDS,
        *NAVIGATION_METABOLISM_LEDGER_BODY_MATERIAL_IDS,
        *NAVIGATION_SURFACE_AUDIT_BODY_MATERIAL_IDS,
        *COMMAND_NODE_CACHE_BODY_MATERIAL_IDS,
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
        *BRIDGE_RUNTIME_CONTINUITY_SOURCE_BODY_MATERIAL_IDS,
        *FORMAL_MATH_PROOFLINE_SPINE_SOURCE_BODY_MATERIAL_IDS,
        *PROVIDER_CONTEXT_SOURCE_BODY_MATERIAL_IDS,
        *TARGET_SHAPE_TACTIC_ROUTING_BODY_MATERIAL_IDS,
        *RING2_PREMISE_RETRIEVAL_BODY_MATERIAL_IDS,
        *EXECUTABLE_GRAMMAR_METABOLISM_BODY_MATERIAL_IDS,
    }
    assert result["public_safe_body_target_status"] == "pass"
    assert result["public_safe_body_digest_count"] == 151


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
    assert result["projection_intake_board"]["ready_cell_count"] == 52
    assert result["projection_intake_board"]["blocked_cell_count"] == 0
    assert result["projection_intake_board"]["projection_status_counts"][
        "self_hosted_status_protocol_landed"
    ] == 1
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_intake_board"]["release_authorized"] is False
    assert "pattern_metadata" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_tool_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert "public_macro_proof_body" in result["projection_intake_board"]["allowed_material_classes"]
    assert result["projection_intake_board"]["public_safe_body_import_count"] == 151
    assert result["projection_intake_board"]["public_safe_body_import_classes"] == {
        "public_macro_pattern_body": 1,
        "public_macro_proof_body": 1,
        "public_macro_receipt_body": 13,
        "public_macro_tool_body": 136,
    }
    assert result["runtime_severance_board"]["runtime_dependency_status"] == "pass"
    assert result["runtime_severance_board"]["macro_origin_refs_runtime_required"] is False
    assert all(
        row["selected_pattern_ids"]
        for row in result["projection_intake_board"]["projection_cells"]
    )
    assert "receipt_paths" not in result


def test_public_safe_macro_proof_body_is_importable_with_verification(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["public_safe_body_material_count"] == 151
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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    assert route_repair_row["body_import_verification"]["source_body_digest"] == source_digest
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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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


def test_bridge_resume_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in WORK_LANDING_CONTROL_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target = public_root / row["target_ref"]
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["material_class"] == "public_macro_tool_body"
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
    cell = by_cell["work_landing_control_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == WORK_LANDING_CONTROL_BODY_MATERIAL_IDS


def test_task_ledger_control_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in TASK_LEDGER_CONTROL_BODY_MATERIAL_IDS:
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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in WORK_LEDGER_CONTROL_BODY_MATERIAL_IDS:
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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in CHECKPOINT_LANE_BODY_MATERIAL_IDS:
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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in COMMAND_OUTPUT_PROJECTION_BODY_MATERIAL_IDS:
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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in TRACE_CAPSULE_BODY_MATERIAL_IDS:
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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in ROUTE_SELECTION_CONTROL_BODY_MATERIAL_IDS:
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
    cell = by_cell["route_selection_control_source_modules_import"]
    assert cell["projection_status"] == "public_runtime_import_landed"
    assert cell["classification"] == [
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_runtime_receipt",
    ]
    assert cell["action_required"] is False
    assert cell["public_safe_body_material_ids"] == ROUTE_SELECTION_CONTROL_BODY_MATERIAL_IDS


def test_bootstrap_route_surface_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=TASK_LEDGER_STARTUP_PRESSURE_BODY_MATERIAL_IDS,
        cell_id="task_ledger_startup_pressure_source_modules_import",
    )


def test_executable_grammar_metabolism_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in EXECUTABLE_GRAMMAR_METABOLISM_BODY_MATERIAL_IDS:
        row = by_material[material_id]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = public_root / target_ref
        source = MICROCOSM_ROOT.parent / row["source_refs"][0]
        digest = f"sha256:{hashlib.sha256(target.read_bytes()).hexdigest()}"
        source_digest = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

        assert target.is_file()
        assert row["classification"] == ["copied_non_secret_macro_body"]
        assert row["body_digest"] == digest
        assert row["body_import_verification"]["source_body_digest"] == source_digest
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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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


def _assert_exact_source_module_body_import(
    *,
    result: dict[str, Any],
    public_root: Path,
    material_ids: list[str],
    cell_id: str,
) -> None:
    by_material = {
        row["material_id"]: row
        for row in result["projection_intake_board"]["public_safe_body_imports"]
    }
    for material_id in material_ids:
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
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=PROVIDER_CONTEXT_SOURCE_BODY_MATERIAL_IDS,
        cell_id="provider_context_source_modules_import",
    )


def test_navigation_clusterability_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=NAVIGATION_CLUSTERABILITY_BODY_MATERIAL_IDS,
        cell_id="navigation_clusterability_source_modules_import",
    )


def test_annex_routing_coverage_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=ANNEX_ROUTING_COVERAGE_BODY_MATERIAL_IDS,
        cell_id="annex_routing_coverage_source_modules_import",
    )


def test_annex_currentness_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=ANNEX_CURRENTNESS_BODY_MATERIAL_IDS,
        cell_id="annex_currentness_source_modules_import",
    )


def test_entrypoint_health_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=ENTRYPOINT_HEALTH_BODY_MATERIAL_IDS,
        cell_id="entrypoint_health_source_modules_import",
    )


def test_agent_entrypoint_audit_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_ENTRYPOINT_AUDIT_BODY_MATERIAL_IDS,
        cell_id="agent_entrypoint_audit_source_modules_import",
    )


def test_navigation_fitness_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=NAVIGATION_FITNESS_BODY_MATERIAL_IDS,
        cell_id="navigation_fitness_source_modules_import",
    )


def test_dynamic_paper_lattice_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=DYNAMIC_PAPER_LATTICE_BODY_MATERIAL_IDS,
        cell_id="dynamic_paper_lattice_source_modules_import",
    )


def test_kind_atlas_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=KIND_ATLAS_BODY_MATERIAL_IDS,
        cell_id="kind_atlas_source_modules_import",
    )


def test_semantic_routing_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=SEMANTIC_ROUTING_BODY_MATERIAL_IDS,
        cell_id="semantic_routing_source_modules_import",
    )


def test_embedding_substrate_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=EMBEDDING_SUBSTRATE_BODY_MATERIAL_IDS,
        cell_id="embedding_substrate_source_modules_import",
    )


def test_nvidia_nim_provider_boundary_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=NVIDIA_NIM_PROVIDER_BOUNDARY_BODY_MATERIAL_IDS,
        cell_id="nvidia_nim_provider_boundary_source_modules_import",
    )


def test_agent_provider_router_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_PROVIDER_ROUTER_BODY_MATERIAL_IDS,
        cell_id="agent_provider_router_source_modules_import",
    )


def test_bridge_route_config_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=BRIDGE_ROUTE_CONFIG_BODY_MATERIAL_IDS,
        cell_id="bridge_route_config_source_modules_import",
    )


def test_kernel_bridge_config_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=KERNEL_BRIDGE_CONFIG_BODY_MATERIAL_IDS,
        cell_id="kernel_bridge_config_source_modules_import",
    )


def test_observe_runtime_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=OBSERVE_RUNTIME_BODY_MATERIAL_IDS,
        cell_id="observe_runtime_source_modules_import",
    )


def test_kernel_state_registry_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=KERNEL_STATE_REGISTRY_BODY_MATERIAL_IDS,
        cell_id="kernel_state_registry_source_modules_import",
    )


def test_agent_execution_trace_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_EXECUTION_TRACE_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_execution_trace_source_modules_import",
    )


def test_agent_observability_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_OBSERVABILITY_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_observability_source_modules_import",
    )


def test_agent_observability_animation_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_OBSERVABILITY_ANIMATION_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_observability_animation_source_modules_import",
    )


def test_agent_observability_classification_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_OBSERVABILITY_CLASSIFICATION_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_observability_classification_source_modules_import",
    )


def test_agent_mission_status_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=AGENT_MISSION_STATUS_SOURCE_BODY_MATERIAL_IDS,
        cell_id="agent_mission_status_source_modules_import",
    )


def test_operator_handoff_linkage_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=OPERATOR_HANDOFF_LINKAGE_SOURCE_BODY_MATERIAL_IDS,
        cell_id="operator_handoff_linkage_source_modules_import",
    )


def test_bridge_runtime_continuity_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    _assert_exact_source_module_body_import(
        result=result,
        public_root=public_root,
        material_ids=BRIDGE_RUNTIME_CONTINUITY_SOURCE_BODY_MATERIAL_IDS,
        cell_id="bridge_runtime_continuity_source_modules_import",
    )


def test_formal_math_proofline_spine_source_modules_body_import_is_unified_under_macro_projection_spine(
    tmp_path: Path,
) -> None:
    public_root = _copy_macro_projection_public_tree(tmp_path)
    result = run_projection_bundle(
        public_root / "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

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
