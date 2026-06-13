from __future__ import annotations

from pathlib import Path

from microcosm_core.doctrine_lattice import expected_paper_module_instances


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _dependency_edges(module_id: str) -> list[dict[str, object]]:
    instance = expected_paper_module_instances(MICROCOSM_ROOT)[module_id]
    return [
        edge
        for edge in instance["relationships"]["edges"]
        if edge["relation_id"] == "paper_module.depends_on.paper_module"
    ]


def test_route_plane_paper_module_dependencies_resolve_to_sibling_shards() -> None:
    edges = _dependency_edges("paper_module.navigation_hologram_route_plane")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.cold_reader_route_map": "resolved_json_instance",
        "paper_module.agent_route_observability_runtime": "resolved_json_instance",
        "paper_module.routing_anti_patterns_registry": "resolved_json_instance",
        "paper_module.pattern_binding_contract": "resolved_json_instance",
    }


def test_route_observability_paper_module_dependencies_include_import_protocol() -> None:
    edges = _dependency_edges("paper_module.agent_route_observability_runtime")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.navigation_hologram_route_plane": "resolved_json_instance",
        "paper_module.cold_reader_route_map": "resolved_json_instance",
        "paper_module.routing_anti_patterns_registry": "resolved_json_instance",
        "paper_module.pattern_binding_contract": "resolved_json_instance",
        "paper_module.macro_projection_import_protocol": "resolved_json_instance",
    }


def test_bridge_continuity_dependency_routes_to_import_protocol() -> None:
    edges = _dependency_edges("paper_module.bridge_phase_continuity_runtime")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.macro_projection_import_protocol": "resolved_json_instance",
    }


def test_standards_meta_dependency_routes_to_import_protocol() -> None:
    edges = _dependency_edges("paper_module.standards_meta_diagnostics")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.macro_projection_import_protocol": "resolved_json_instance",
    }


def test_finance_forecast_dependency_routes_to_import_protocol() -> None:
    edges = _dependency_edges("paper_module.finance_forecast_evaluation_spine")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.macro_projection_import_protocol": "resolved_json_instance",
    }


def test_corpus_readiness_dependency_routes_to_tactic_portfolio() -> None:
    edges = _dependency_edges("paper_module.corpus_readiness_mathlib_absence_gate")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.tactic_portfolio_availability": "resolved_json_instance",
    }


def test_research_replication_dependency_routes_to_benchmark_integrity() -> None:
    edges = _dependency_edges("paper_module.research_replication_rubric_artifact_replay")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.agent_benchmark_integrity_anti_gaming_replay": "resolved_json_instance",
    }


def test_materials_lab_dependency_routes_to_replay_drift_and_import_modules() -> None:
    edges = _dependency_edges("paper_module.materials_chemistry_closed_loop_lab_safety_replay")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.research_replication_rubric_artifact_replay": "resolved_json_instance",
        "paper_module.world_model_projection_drift_control_room": "resolved_json_instance",
        "paper_module.macro_projection_import_protocol": "resolved_json_instance",
    }


def test_formal_math_repair_dependency_routes_to_proof_support_modules() -> None:
    edges = _dependency_edges("paper_module.formal_math_verifier_trace_repair_loop")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.lean_std_premise_index": "resolved_json_instance",
        "paper_module.tactic_portfolio_availability": "resolved_json_instance",
        "paper_module.target_shape_tactic_routing": "resolved_json_instance",
        "paper_module.formal_math_premise_retrieval": "resolved_json_instance",
    }


def test_lean_std_premise_index_dependency_routes_to_retrieval_module() -> None:
    edges = _dependency_edges("paper_module.lean_std_premise_index")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.formal_math_premise_retrieval": "resolved_json_instance",
    }


def test_certificate_kernel_dependency_routes_to_execution_spine() -> None:
    edges = _dependency_edges("paper_module.certificate_kernel_execution_lab")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.verifier_lab_execution_spine": "resolved_json_instance",
    }


def test_engine_room_leak_gate_dependency_routes_to_demo_module() -> None:
    edges = _dependency_edges("paper_module.engine_room_public_projection_leak_gate")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.engine_room_demo": "resolved_json_instance",
    }


def test_agent_memory_temporal_conflict_dependency_routes_to_source_named_siblings() -> None:
    edges = _dependency_edges("paper_module.agent_memory_temporal_conflict_replay")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.agent_route_observability_runtime": "resolved_json_instance",
        "paper_module.bridge_phase_continuity_runtime": "resolved_json_instance",
    }


def test_agent_monitor_redteam_dependency_routes_to_import_protocol() -> None:
    edges = _dependency_edges("paper_module.agent_monitor_redteam_falsification_replay")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.macro_projection_import_protocol": "resolved_json_instance",
    }


def test_sleeper_memory_dependency_routes_to_source_named_sibling_replays() -> None:
    edges = _dependency_edges("paper_module.sleeper_memory_poisoning_quarantine_replay")

    assert {
        str(edge["target_id"]): edge["target_status"]
        for edge in edges
    } == {
        "paper_module.agent_memory_temporal_conflict_replay": "resolved_json_instance",
        "paper_module.mcp_tool_authority_replay": "resolved_json_instance",
        "paper_module.agent_sandbox_policy_escape_replay": "resolved_json_instance",
    }
