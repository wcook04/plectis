from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from microcosm_core import architecture_kernel
from microcosm_core import project_substrate
from microcosm_core.organs import agent_benchmark_integrity_anti_gaming_replay
from microcosm_core.organs import agent_memory_temporal_conflict_replay
from microcosm_core.organs import agent_monitor_redteam_falsification_replay
from microcosm_core.organs import agent_route_observability_runtime
from microcosm_core.organs import agent_sabotage_scheming_monitor_replay
from microcosm_core.organs import agent_sandbox_policy_escape_replay
from microcosm_core.organs import (
    agentic_vulnerability_discovery_patch_proof_replay,
)
from microcosm_core.organs import belief_state_process_reward_replay
from microcosm_core.organs import certificate_kernel_execution_lab
from microcosm_core.organs import cold_reader_route_map
from microcosm_core.organs import corpus_readiness_mathlib_absence_gate
from microcosm_core.organs import executable_doctrine_grammar
from microcosm_core.organs import formal_evidence_cell_anchor_resolver
from microcosm_core.organs import formal_math_lean_proof_witness
from microcosm_core.organs import formal_math_premise_retrieval
from microcosm_core.organs import formal_math_readiness_gate
from microcosm_core.organs import formal_math_verifier_trace_repair_loop
from microcosm_core.organs import (
    indirect_prompt_injection_information_flow_policy_replay,
)
from microcosm_core.organs import lean_std_premise_index
from microcosm_core.organs import macro_projection_import_protocol
from microcosm_core.organs import materials_chemistry_closed_loop_lab_safety_replay
from microcosm_core.organs import mathematical_strategy_atlas_hypothesis_scorer
from microcosm_core.organs import mcp_tool_authority_replay
from microcosm_core.organs import mechanistic_interpretability_circuit_attribution_replay
from microcosm_core.organs import durable_agent_work_landing_replay
from microcosm_core.organs import mission_transaction_work_spine
from microcosm_core.organs import navigation_hologram_route_plane
from microcosm_core.organs import pattern_binding_contract
from microcosm_core.organs import prediction_oracle_reconciliation
from microcosm_core.organs import proof_diagnostic_evidence_spine
from microcosm_core.organs import proof_derived_governed_mutation_authorization
from microcosm_core.organs import provider_context_recipe_budget_policy
from microcosm_core.organs import public_reveal_walkthrough
from microcosm_core.organs import research_replication_rubric_artifact_replay
from microcosm_core.organs import ring2_premise_retrieval_precision_recall_harness
from microcosm_core.organs import sleeper_memory_poisoning_quarantine_replay
from microcosm_core.organs import spatial_world_model_counterfactual_simulation_replay
from microcosm_core.organs import standards_meta_diagnostics
from microcosm_core.organs import tactic_portfolio_availability_probe
from microcosm_core.organs import target_shape_tactic_routing_gate
from microcosm_core.organs import undeclared_library_prior_symbol_classifier
from microcosm_core.organs import verifier_lab_execution_spine
from microcosm_core.organs import verifier_lab_kernel
from microcosm_core.organs import voice_to_doctrine_self_improvement_loop
from microcosm_core.organs import world_model_projection_drift_control_room
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict
from microcosm_core.validators import acceptance


PASS = "pass"
DEFAULT_PROJECT_REL = "examples/runtime_shell/demo_project"
EVIDENCE_CLASS_REGISTRY_REL = Path("core/organ_evidence_classes.json")


Runner = Callable[[str | Path, str | Path, str | None], dict[str, Any]]


@dataclass(frozen=True)
class RuntimeStep:
    organ_id: str
    span: str
    input_mode: str
    example_rel: str
    runner: Runner
    receipt_name: str


RUNTIME_STEPS: tuple[RuntimeStep, ...] = (
    RuntimeStep(
        organ_id="pattern_binding_contract",
        span="pattern_binding.validate",
        input_mode="exported_substrate_bundle",
        example_rel="examples/pattern_binding_contract/exported_substrate_bundle",
        runner=pattern_binding_contract.validate_substrate_bundle,
        receipt_name="exported_substrate_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="executable_doctrine_grammar",
        span="doctrine_grammar.validate",
        input_mode="exported_standards_bundle",
        example_rel="examples/executable_doctrine_grammar/exported_standards_bundle",
        runner=executable_doctrine_grammar.validate_standards_bundle,
        receipt_name="exported_standards_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="proof_diagnostic_evidence_spine",
        span="proof_evidence.run",
        input_mode="exported_evidence_bundle",
        example_rel="examples/proof_diagnostic_evidence_spine/exported_evidence_bundle",
        runner=proof_diagnostic_evidence_spine.run_evidence_bundle,
        receipt_name="exported_evidence_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="formal_math_readiness_gate",
        span="formal_math_readiness.validate",
        input_mode="exported_formal_math_readiness_bundle",
        example_rel="examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle",
        runner=formal_math_readiness_gate.run_readiness_bundle,
        receipt_name="exported_formal_math_readiness_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="corpus_readiness_mathlib_absence_gate",
        span="corpus_readiness_mathlib_absence.validate",
        input_mode="exported_corpus_readiness_bundle",
        example_rel="examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle",
        runner=corpus_readiness_mathlib_absence_gate.run_projection_bundle,
        receipt_name="exported_corpus_readiness_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="mathematical_strategy_atlas_hypothesis_scorer",
        span="mathematical_strategy_atlas.validate",
        input_mode="exported_mathematical_strategy_atlas_bundle",
        example_rel=(
            "examples/mathematical_strategy_atlas_hypothesis_scorer/"
            "exported_mathematical_strategy_atlas_bundle"
        ),
        runner=mathematical_strategy_atlas_hypothesis_scorer.run_strategy_bundle,
        receipt_name="exported_mathematical_strategy_atlas_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="tactic_portfolio_availability_probe",
        span="tactic_portfolio_availability.validate",
        input_mode="exported_tactic_portfolio_availability_bundle",
        example_rel=(
            "examples/tactic_portfolio_availability_probe/"
            "exported_tactic_portfolio_availability_bundle"
        ),
        runner=tactic_portfolio_availability_probe.run_availability_bundle,
        receipt_name="exported_tactic_portfolio_availability_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="target_shape_tactic_routing_gate",
        span="target_shape_tactic_routing.validate",
        input_mode="exported_target_shape_tactic_routing_bundle",
        example_rel=(
            "examples/target_shape_tactic_routing_gate/"
            "exported_target_shape_tactic_routing_bundle"
        ),
        runner=target_shape_tactic_routing_gate.run_routing_bundle,
        receipt_name="exported_target_shape_tactic_routing_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="lean_std_premise_index",
        span="lean_std_premise_index.validate",
        input_mode="exported_lean_std_premise_index_bundle",
        example_rel="examples/lean_std_premise_index/exported_lean_std_premise_index_bundle",
        runner=lean_std_premise_index.run_index_bundle,
        receipt_name="exported_lean_std_premise_index_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="formal_math_premise_retrieval",
        span="formal_math_premise_retrieval.validate",
        input_mode="exported_premise_retrieval_bundle",
        example_rel="examples/formal_math_premise_retrieval/exported_premise_retrieval_bundle",
        runner=formal_math_premise_retrieval.run_retrieval_bundle,
        receipt_name="exported_premise_retrieval_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="formal_math_verifier_trace_repair_loop",
        span="formal_math_verifier_trace_repair_loop.validate",
        input_mode="exported_verifier_trace_repair_bundle",
        example_rel=(
            "examples/formal_math_verifier_trace_repair_loop/"
            "exported_verifier_trace_repair_bundle"
        ),
        runner=formal_math_verifier_trace_repair_loop.run_loop_bundle,
        receipt_name="exported_verifier_trace_repair_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="formal_evidence_cell_anchor_resolver",
        span="formal_evidence_cell_anchor_resolver.validate",
        input_mode="exported_evidence_cell_anchor_bundle",
        example_rel=(
            "examples/formal_evidence_cell_anchor_resolver/"
            "exported_evidence_cell_anchor_bundle"
        ),
        runner=formal_evidence_cell_anchor_resolver.run_anchor_bundle,
        receipt_name="exported_evidence_cell_anchor_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="undeclared_library_prior_symbol_classifier",
        span="undeclared_library_prior_symbol_classifier.validate",
        input_mode="exported_symbol_classifier_bundle",
        example_rel=(
            "examples/undeclared_library_prior_symbol_classifier/"
            "exported_symbol_classifier_bundle"
        ),
        runner=undeclared_library_prior_symbol_classifier.run_symbol_bundle,
        receipt_name="exported_symbol_classifier_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="ring2_premise_retrieval_precision_recall_harness",
        span="ring2_precision_recall.validate",
        input_mode="exported_ring2_precision_recall_bundle",
        example_rel=(
            "examples/ring2_premise_retrieval_precision_recall_harness/"
            "exported_ring2_precision_recall_bundle"
        ),
        runner=ring2_premise_retrieval_precision_recall_harness.run_precision_recall_bundle,
        receipt_name="exported_ring2_precision_recall_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="agent_benchmark_integrity_anti_gaming_replay",
        span="agent_benchmark_integrity.validate",
        input_mode="exported_benchmark_integrity_bundle",
        example_rel=(
            "examples/agent_benchmark_integrity_anti_gaming_replay/"
            "exported_benchmark_integrity_bundle"
        ),
        runner=(
            agent_benchmark_integrity_anti_gaming_replay
            .run_benchmark_integrity_bundle
        ),
        receipt_name="exported_benchmark_integrity_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="provider_context_recipe_budget_policy",
        span="provider_context_budget.validate",
        input_mode="exported_provider_context_budget_bundle",
        example_rel=(
            "examples/provider_context_recipe_budget_policy/"
            "exported_provider_context_budget_bundle"
        ),
        runner=provider_context_recipe_budget_policy.run_budget_bundle,
        receipt_name="exported_provider_context_budget_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="formal_math_lean_proof_witness",
        span="formal_math_lean_proof_witness.validate",
        input_mode="exported_lean_proof_witness_bundle",
        example_rel="examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle",
        runner=formal_math_lean_proof_witness.run_witness_bundle,
        receipt_name="exported_lean_proof_witness_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="verifier_lab_kernel",
        span="verifier_lab_kernel.validate",
        input_mode="exported_verifier_lab_kernel_bundle",
        example_rel="examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle",
        runner=verifier_lab_kernel.run_kernel_bundle,
        receipt_name="exported_verifier_lab_kernel_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="verifier_lab_execution_spine",
        span="verifier_lab_execution_spine.validate",
        input_mode="exported_verifier_lab_execution_spine_bundle",
        example_rel=(
            "examples/verifier_lab_execution_spine/"
            "exported_verifier_lab_execution_spine_bundle"
        ),
        runner=verifier_lab_execution_spine.run_execution_bundle,
        receipt_name=(
            "exported_verifier_lab_execution_spine_bundle_validation_result.json"
        ),
    ),
    RuntimeStep(
        organ_id="navigation_hologram_route_plane",
        span="navigation_route_plane.validate",
        input_mode="exported_route_plane_bundle",
        example_rel="examples/navigation_hologram_route_plane/exported_route_plane_bundle",
        runner=navigation_hologram_route_plane.run_route_plane_bundle,
        receipt_name="exported_route_plane_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="mission_transaction_work_spine",
        span="mission_transaction.validate",
        input_mode="exported_mission_transaction_bundle",
        example_rel="examples/mission_transaction_work_spine/exported_mission_transaction_bundle",
        runner=mission_transaction_work_spine.run_mission_transaction_bundle,
        receipt_name="exported_mission_transaction_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="durable_agent_work_landing_replay",
        span="durable_work_landing_replay.validate",
        input_mode="exported_work_landing_replay_bundle",
        example_rel=(
            "examples/durable_agent_work_landing_replay/"
            "exported_work_landing_replay_bundle"
        ),
        runner=durable_agent_work_landing_replay.run_work_landing_bundle,
        receipt_name="exported_work_landing_replay_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="research_replication_rubric_artifact_replay",
        span="research_replication_replay.validate",
        input_mode="exported_research_replication_bundle",
        example_rel=(
            "examples/research_replication_rubric_artifact_replay/"
            "exported_research_replication_bundle"
        ),
        runner=research_replication_rubric_artifact_replay.run_replication_bundle,
        receipt_name="exported_research_replication_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="world_model_projection_drift_control_room",
        span="projection_drift_control_room.validate",
        input_mode="exported_projection_drift_control_bundle",
        example_rel=(
            "examples/world_model_projection_drift_control_room/"
            "exported_projection_drift_control_bundle"
        ),
        runner=world_model_projection_drift_control_room.run_drift_control_bundle,
        receipt_name="exported_projection_drift_control_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="spatial_world_model_counterfactual_simulation_replay",
        span="spatial_world_model_counterfactual_simulation.validate",
        input_mode="exported_spatial_world_model_simulation_bundle",
        example_rel=(
            "examples/spatial_world_model_counterfactual_simulation_replay/"
            "exported_spatial_world_model_simulation_bundle"
        ),
        runner=spatial_world_model_counterfactual_simulation_replay.run_simulation_bundle,
        receipt_name=(
            "exported_spatial_world_model_simulation_bundle_validation_result.json"
        ),
    ),
    RuntimeStep(
        organ_id="materials_chemistry_closed_loop_lab_safety_replay",
        span="materials_chemistry_lab_safety.validate",
        input_mode="exported_materials_lab_safety_bundle",
        example_rel=(
            "examples/materials_chemistry_closed_loop_lab_safety_replay/"
            "exported_materials_lab_safety_bundle"
        ),
        runner=materials_chemistry_closed_loop_lab_safety_replay.run_lab_bundle,
        receipt_name="exported_materials_lab_safety_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="mechanistic_interpretability_circuit_attribution_replay",
        span="mechanistic_interpretability_circuit_attribution.validate",
        input_mode="exported_circuit_attribution_bundle",
        example_rel=(
            "examples/mechanistic_interpretability_circuit_attribution_replay/"
            "exported_circuit_attribution_bundle"
        ),
        runner=(
            mechanistic_interpretability_circuit_attribution_replay
            .run_attribution_bundle
        ),
        receipt_name="exported_circuit_attribution_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="agent_route_observability_runtime",
        span="observability.validate",
        input_mode="exported_observability_bundle",
        example_rel="examples/agent_route_observability_runtime/exported_observability_bundle",
        runner=agent_route_observability_runtime.run_observability_bundle,
        receipt_name="exported_observability_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="pattern_assimilation_step",
        span="assimilation.validate",
        input_mode="exported_assimilation_bundle",
        example_rel="examples/pattern_assimilation_step/exported_assimilation_bundle",
        runner=acceptance.run_assimilation_bundle,
        receipt_name="exported_assimilation_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="public_reveal_walkthrough",
        span="public_reveal.validate",
        input_mode="exported_public_reveal_bundle",
        example_rel="examples/public_reveal_walkthrough/exported_public_reveal_bundle",
        runner=public_reveal_walkthrough.run_reveal_bundle,
        receipt_name="exported_public_reveal_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="macro_projection_import_protocol",
        span="macro_projection_import.validate",
        input_mode="exported_projection_import_bundle",
        example_rel="examples/macro_projection_import_protocol/exported_projection_import_bundle",
        runner=macro_projection_import_protocol.run_projection_bundle,
        receipt_name="exported_projection_import_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="prediction_oracle_reconciliation",
        span="prediction_oracle_reconciliation.validate",
        input_mode="exported_prediction_oracle_bundle",
        example_rel="examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle",
        runner=prediction_oracle_reconciliation.run_prediction_bundle,
        receipt_name="exported_prediction_oracle_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="standards_meta_diagnostics",
        span="standards_meta_diagnostics.validate",
        input_mode="exported_standards_meta_diagnostics_bundle",
        example_rel=(
            "examples/standards_meta_diagnostics/"
            "exported_standards_meta_diagnostics_bundle"
        ),
        runner=standards_meta_diagnostics.run_diagnostics_bundle,
        receipt_name="exported_standards_meta_diagnostics_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="cold_reader_route_map",
        span="cold_reader_route_map.validate",
        input_mode="exported_cold_reader_route_map_bundle",
        example_rel="examples/cold_reader_route_map/exported_cold_reader_route_map_bundle",
        runner=cold_reader_route_map.run_route_map_bundle,
        receipt_name="exported_cold_reader_route_map_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="agent_monitor_redteam_falsification_replay",
        span="agent_monitor_redteam.validate",
        input_mode="exported_monitor_redteam_bundle",
        example_rel=(
            "examples/agent_monitor_redteam_falsification_replay/"
            "exported_monitor_redteam_bundle"
        ),
        runner=agent_monitor_redteam_falsification_replay.run_monitor_bundle,
        receipt_name="exported_monitor_redteam_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="agent_sabotage_scheming_monitor_replay",
        span="agent_sabotage_scheming_monitor.validate",
        input_mode="exported_sabotage_monitor_bundle",
        example_rel=(
            "examples/agent_sabotage_scheming_monitor_replay/"
            "exported_sabotage_monitor_bundle"
        ),
        runner=agent_sabotage_scheming_monitor_replay.run_sabotage_bundle,
        receipt_name="exported_sabotage_monitor_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="agent_memory_temporal_conflict_replay",
        span="agent_memory_temporal_conflict.validate",
        input_mode="exported_memory_temporal_conflict_bundle",
        example_rel=(
            "examples/agent_memory_temporal_conflict_replay/"
            "exported_memory_temporal_conflict_bundle"
        ),
        runner=agent_memory_temporal_conflict_replay.run_memory_bundle,
        receipt_name="exported_memory_temporal_conflict_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="sleeper_memory_poisoning_quarantine_replay",
        span="sleeper_memory_poisoning_quarantine.validate",
        input_mode="exported_sleeper_memory_poisoning_bundle",
        example_rel=(
            "examples/sleeper_memory_poisoning_quarantine_replay/"
            "exported_sleeper_memory_poisoning_bundle"
        ),
        runner=sleeper_memory_poisoning_quarantine_replay.run_quarantine_bundle,
        receipt_name="exported_sleeper_memory_poisoning_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="mcp_tool_authority_replay",
        span="mcp_tool_authority_replay.validate",
        input_mode="exported_mcp_tool_authority_bundle",
        example_rel=(
            "examples/mcp_tool_authority_replay/"
            "exported_mcp_tool_authority_bundle"
        ),
        runner=mcp_tool_authority_replay.run_tool_authority_bundle,
        receipt_name="exported_mcp_tool_authority_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="proof_derived_governed_mutation_authorization",
        span="proof_derived_governed_mutation_authorization.validate",
        input_mode="exported_governed_mutation_authorization_bundle",
        example_rel=(
            "examples/proof_derived_governed_mutation_authorization/"
            "exported_governed_mutation_authorization_bundle"
        ),
        runner=proof_derived_governed_mutation_authorization.run_authorization_bundle,
        receipt_name=(
            "exported_governed_mutation_authorization_bundle_validation_result.json"
        ),
    ),
    RuntimeStep(
        organ_id="belief_state_process_reward_replay",
        span="belief_state_process_reward_replay.validate",
        input_mode="exported_belief_state_process_reward_bundle",
        example_rel=(
            "examples/belief_state_process_reward_replay/"
            "exported_belief_state_process_reward_bundle"
        ),
        runner=belief_state_process_reward_replay.run_reward_bundle,
        receipt_name=(
            "exported_belief_state_process_reward_bundle_validation_result.json"
        ),
    ),
    RuntimeStep(
        organ_id="agent_sandbox_policy_escape_replay",
        span="agent_sandbox_policy_escape_replay.validate",
        input_mode="exported_sandbox_policy_escape_bundle",
        example_rel=(
            "examples/agent_sandbox_policy_escape_replay/"
            "exported_sandbox_policy_escape_bundle"
        ),
        runner=agent_sandbox_policy_escape_replay.run_sandbox_bundle,
        receipt_name="exported_sandbox_policy_escape_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="indirect_prompt_injection_information_flow_policy_replay",
        span="indirect_prompt_injection_information_flow_policy_replay.validate",
        input_mode="exported_prompt_injection_flow_bundle",
        example_rel=(
            "examples/indirect_prompt_injection_information_flow_policy_replay/"
            "exported_prompt_injection_flow_bundle"
        ),
        runner=(
            indirect_prompt_injection_information_flow_policy_replay
            .run_prompt_injection_bundle
        ),
        receipt_name="exported_prompt_injection_flow_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="agentic_vulnerability_discovery_patch_proof_replay",
        span="agentic_vulnerability_discovery_patch_proof_replay.validate",
        input_mode="exported_patch_proof_bundle",
        example_rel=(
            "examples/agentic_vulnerability_discovery_patch_proof_replay/"
            "exported_patch_proof_bundle"
        ),
        runner=(
            agentic_vulnerability_discovery_patch_proof_replay
            .run_patch_proof_bundle
        ),
        receipt_name="exported_patch_proof_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="certificate_kernel_execution_lab",
        span="certificate_kernel_execution_lab.validate",
        input_mode="exported_certificate_kernel_execution_lab_bundle",
        example_rel=(
            "examples/certificate_kernel_execution_lab/"
            "exported_certificate_kernel_execution_lab_bundle"
        ),
        runner=certificate_kernel_execution_lab.run_certificate_bundle,
        receipt_name=(
            "exported_certificate_kernel_execution_lab_bundle_validation_result.json"
        ),
    ),
    RuntimeStep(
        organ_id="voice_to_doctrine_self_improvement_loop",
        span="voice_to_doctrine_self_improvement_loop.validate",
        input_mode="exported_voice_to_doctrine_bundle",
        example_rel=(
            "examples/voice_to_doctrine_self_improvement_loop/"
            "exported_voice_to_doctrine_bundle"
        ),
        runner=voice_to_doctrine_self_improvement_loop.run_voice_to_doctrine_bundle,
        receipt_name="exported_voice_to_doctrine_bundle_validation_result.json",
    ),
)


def public_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _public_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _first_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item:
                return item
    return None


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _badge_list(values: list[str]) -> str:
    if not values:
        return "<span class=\"muted\">none</span>"
    return "".join(f"<span class=\"badge\">{html.escape(value)}</span>" for value in values)


def _receipt_evidence_contract(payload: dict[str, Any]) -> dict[str, Any]:
    negative_case_values = (
        payload.get("negative_case_ids"),
        payload.get("negative_cases"),
        payload.get("expected_negative_cases"),
    )
    has_negative_cases = any(isinstance(value, list) and bool(value) for value in negative_case_values)
    has_secret_scan = isinstance(payload.get("secret_exclusion_scan"), dict)
    has_legacy_scan = isinstance(payload.get("private_state_scan"), dict)
    has_body_import_verification = any(
        isinstance(payload.get(key), (dict, list)) and bool(payload.get(key))
        for key in (
            "body_import_verification",
            "body_import_verification_rows",
            "body_copy_verification",
            "body_copy_rows",
            "body_copied_rows",
        )
    )
    blocked_import_debt = (
        payload.get("blocked_import_debt") is True
        or payload.get("projection_status") == "blocked_import_debt"
    )
    status = payload.get("status")
    return {
        "contract_version": "runtime_real_receipt_evidence_contract_v1",
        "real_runtime_receipt": status == PASS and not has_negative_cases,
        "copied_non_secret_macro_body_with_provenance": has_body_import_verification,
        "source_faithful_refactor": False,
        "regression_or_negative_fixture": has_negative_cases,
        "blocked_import_debt": blocked_import_debt,
        "synthetic_receipt_is_product_evidence": False,
        "body_in_receipt": False,
        "secret_exclusion_scan_present": has_secret_scan,
        "legacy_private_state_scan_compat_present": has_legacy_scan,
    }


def _normalize_runtime_projection_status(status: Any) -> Any:
    if status == "public_replacement_landed":
        return "public_runtime_import_landed"
    return status


def _normalize_projection_status_counts(counts: Any) -> dict[str, Any]:
    if not isinstance(counts, dict):
        return {}
    normalized = dict(counts)
    old_value = normalized.pop("public_replacement_landed", None)
    if old_value is not None:
        normalized["public_runtime_import_landed"] = (
            normalized.get("public_runtime_import_landed", 0) + old_value
        )
    return normalized


def _safe_receipt_summary(path: Path, root: Path) -> dict[str, Any]:
    payload = _read_json_if_exists(path)
    return {
        "receipt_ref": _public_relative(path, root),
        "status": payload.get("status", "unknown"),
        "schema_version": payload.get("schema_version"),
        "organ_id": payload.get("organ_id"),
        "input_mode": payload.get("input_mode"),
        "created_at": payload.get("created_at"),
        "body_in_receipt": False,
        "evidence_contract": _receipt_evidence_contract(payload),
    }


PRODUCT_PATH_DEMOTED_ORGAN_IDS = frozenset(
    {
        "agent_benchmark_integrity_anti_gaming_replay",
        "agent_monitor_redteam_falsification_replay",
        "agent_sabotage_scheming_monitor_replay",
        "mathematical_strategy_atlas_hypothesis_scorer",
    }
)

PRODUCT_PATH_DEMOTION_REASONS = {
    "agent_benchmark_integrity_anti_gaming_replay": (
        "benchmark-integrity replay remains runnable as a body-free regression drilldown, "
        "but fixture-supplied benchmark verdict rows are not product-spine substrate or benchmark-performance evidence."
    ),
    "agent_monitor_redteam_falsification_replay": (
        "monitor-redteam replay remains runnable as a regression drilldown, "
        "but synthetic monitor verdict rows and body-omission refs are not product-spine substrate."
    ),
    "agent_sabotage_scheming_monitor_replay": (
        "sabotage-monitor replay remains runnable as a regression drilldown, "
        "but synthetic scheming episodes, monitor scores, and body-free regression fixture refs "
        "are not product-spine substrate."
    ),
    "mathematical_strategy_atlas_hypothesis_scorer": (
        "strategy-atlas overlap projection remains runnable as a regression "
        "drilldown, but scoring/projection rows are not product-spine substrate."
    )
}

TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS = {
    "real_runtime_receipt": "real_runtime_receipt_count",
    "copied_non_secret_macro_body": "copied_non_secret_macro_body_count",
    "source_faithful_refactor": "source_faithful_refactor_count",
    "real_import_validation": "real_import_validation_count",
    "regression_negative_fixture": "regression_negative_fixture_count",
    "blocked_import_debt": "blocked_import_debt_count",
    "secret_exclusion": "secret_exclusion_count",
    "legacy_adapter_or_synthetic_placeholder": (
        "legacy_adapter_or_synthetic_placeholder_count"
    ),
    "delete_or_demote_candidate": "delete_or_demote_candidate_count",
}

REAL_SUBSTRATE_PROGRESS_BUCKETS = frozenset(
    {
        "real_runtime_receipt",
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_import_validation",
    }
)


def _runtime_organ_ids() -> list[str]:
    return [step.organ_id for step in RUNTIME_STEPS]


def _product_runtime_steps() -> list[RuntimeStep]:
    return [
        step
        for step in RUNTIME_STEPS
        if step.organ_id not in PRODUCT_PATH_DEMOTED_ORGAN_IDS
    ]


def _load_evidence_class_registry(root: Path) -> dict[str, Any]:
    registry_path = root / EVIDENCE_CLASS_REGISTRY_REL
    payload = read_json_strict(registry_path)
    if not isinstance(payload, dict):
        raise ValueError(f"{EVIDENCE_CLASS_REGISTRY_REL.as_posix()} must be a JSON object")
    if payload.get("fail_closed_no_default") is not True:
        raise ValueError("organ evidence-class registry must declare fail_closed_no_default=true")

    profiles = payload.get("class_profiles")
    rows = payload.get("organ_evidence_classes")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("organ evidence-class registry has no class_profiles object")
    if not isinstance(rows, list):
        raise ValueError("organ evidence-class registry has no organ_evidence_classes list")

    expected_ids = set(_runtime_organ_ids())
    seen: set[str] = set()
    duplicate_ids: set[str] = set()
    profile_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("organ evidence-class rows must be JSON objects")
        organ_id = str(row.get("organ_id") or "")
        evidence_class = str(row.get("evidence_class") or "")
        if not organ_id:
            raise ValueError("organ evidence-class row is missing organ_id")
        if organ_id in seen:
            duplicate_ids.add(organ_id)
        seen.add(organ_id)
        class_profile = profiles.get(evidence_class)
        if not isinstance(class_profile, dict):
            raise ValueError(f"organ {organ_id} references unknown evidence_class {evidence_class!r}")
        truth_bucket = str(class_profile.get("truth_accounting_bucket") or "")
        if truth_bucket not in TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS:
            raise ValueError(
                f"evidence_class {evidence_class!r} has unknown truth_accounting_bucket "
                f"{truth_bucket!r}"
            )
        expected_progress = truth_bucket in REAL_SUBSTRATE_PROGRESS_BUCKETS
        if class_profile.get("counts_as_real_substrate_progress") is not expected_progress:
            raise ValueError(
                f"evidence_class {evidence_class!r} has inconsistent "
                "counts_as_real_substrate_progress"
            )
        profile_by_id[organ_id] = {
            "evidence_class": evidence_class,
            "evidence_strength_rank": class_profile["evidence_strength_rank"],
            "truth_accounting_bucket": truth_bucket,
            "counts_as_real_substrate_progress": expected_progress,
            "evaluator_basis": class_profile["evaluator_basis"],
            "verdict_source": class_profile["verdict_source"],
            "negative_case_independence": class_profile["negative_case_independence"],
            "claim_ceiling": class_profile["claim_ceiling"],
            "classification_basis": row.get("classification_basis"),
            "evidence_strength_disclosed": True,
        }

    missing_ids = sorted(expected_ids - seen)
    extra_ids = sorted(seen - expected_ids)
    if duplicate_ids or missing_ids or extra_ids:
        raise ValueError(
            "organ evidence-class registry coverage defect: "
            f"duplicates={sorted(duplicate_ids)} missing={missing_ids} extra={extra_ids}"
        )

    return {
        "source_ref": EVIDENCE_CLASS_REGISTRY_REL.as_posix(),
        "schema_version": payload.get("schema_version"),
        "registry_id": payload.get("registry_id"),
        "fail_closed_no_default": True,
        "class_profiles": profiles,
        "organ_profiles_by_id": profile_by_id,
        "organ_ids": _runtime_organ_ids(),
        "explicit_coverage": True,
        "missing_organs": [],
        "extra_organs": [],
        "duplicate_organs": [],
    }


def _organ_evidence_profile(organ_id: str, registry: dict[str, Any]) -> dict[str, Any]:
    profiles = registry.get("organ_profiles_by_id", {})
    profile = profiles.get(organ_id) if isinstance(profiles, dict) else None
    if not isinstance(profile, dict):
        raise ValueError(f"unclassified organ_id {organ_id!r} in evidence-class registry")
    return dict(profile)


def _evidence_registry_summary(registry: dict[str, Any]) -> dict[str, Any]:
    profiles = registry.get("class_profiles", {})
    organ_profiles = registry.get("organ_profiles_by_id", {})
    return {
        "source_ref": registry.get("source_ref"),
        "schema_version": registry.get("schema_version"),
        "registry_id": registry.get("registry_id"),
        "fail_closed_no_default": registry.get("fail_closed_no_default") is True,
        "explicit_coverage": registry.get("explicit_coverage") is True,
        "class_profile_count": len(profiles) if isinstance(profiles, dict) else 0,
        "organ_evidence_class_count": len(organ_profiles)
        if isinstance(organ_profiles, dict)
        else 0,
        "truth_accounting_bucket_count": len(TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS),
        "real_substrate_progress_buckets": sorted(REAL_SUBSTRATE_PROGRESS_BUCKETS),
        "unclassified_organs": registry.get("missing_organs", []),
        "extra_organs": registry.get("extra_organs", []),
        "duplicate_organs": registry.get("duplicate_organs", []),
    }


def _evidence_class_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        class_id = row.get("evidence_class")
        if isinstance(class_id, str):
            counts[class_id] = counts.get(class_id, 0) + 1
    return {class_id: count for class_id, count in counts.items() if count}


def _truth_accounting(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {count_key: 0 for count_key in TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS.values()}
    bucket_counts: dict[str, int] = {}
    real_organs: list[str] = []
    non_progress_organs: list[str] = []
    for row in rows:
        bucket = str(row.get("truth_accounting_bucket") or "")
        if bucket not in TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS:
            bucket = "legacy_adapter_or_synthetic_placeholder"
        count_key = TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS[bucket]
        counts[count_key] += 1
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        organ_id = str(row.get("organ_id") or "")
        if row.get("counts_as_real_substrate_progress") is True:
            real_organs.append(organ_id)
        else:
            non_progress_organs.append(organ_id)

    real_substrate_progress_count = sum(
        counts[TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS[bucket]]
        for bucket in REAL_SUBSTRATE_PROGRESS_BUCKETS
    )
    scaffold_or_debt_count = len(rows) - real_substrate_progress_count
    return {
        "schema_version": "microcosm_truth_accounting_v1",
        "adapter_backed_count_is_product_progress": False,
        "accepted_current_authority_is_evidence_strength": False,
        "real_substrate_progress_count": real_substrate_progress_count,
        "scaffold_or_debt_count": scaffold_or_debt_count,
        "non_progress_organ_count": scaffold_or_debt_count,
        "truth_accounting_bucket_counts": bucket_counts,
        "real_substrate_progress_organs": real_organs,
        "non_progress_organs": non_progress_organs,
        **counts,
    }


class RuntimeShell:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root).resolve(strict=False) if root is not None else public_root()

    @property
    def runtime_receipt_dir(self) -> Path:
        return self.root / "receipts/runtime_shell"

    def organs(self) -> list[dict[str, Any]]:
        registry = _read_json_if_exists(self.root / "core/organ_registry.json")
        rows = registry.get("implemented_organs", [])
        if not isinstance(rows, list):
            return []
        evidence_registry = _load_evidence_class_registry(self.root)
        by_step = {step.organ_id: step for step in RUNTIME_STEPS}
        organs: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            organ_id = str(row.get("organ_id") or "")
            step = by_step.get(organ_id)
            evidence_profile = _organ_evidence_profile(organ_id, evidence_registry)
            product_demoted = organ_id in PRODUCT_PATH_DEMOTED_ORGAN_IDS
            runtime_mode = (
                "adapter_backed"
                if step and not product_demoted
                else "drilldown_only"
                if step
                else "registry_only"
            )
            organs.append(
                {
                    "organ_id": organ_id,
                    "status": row.get("status"),
                    "runner": row.get("runner"),
                    "validator_command": row.get("validator_command"),
                    "current_authority_receipt": row.get("current_authority_receipt"),
                    "generated_receipts": row.get("generated_receipts", []),
                    "runtime_mode": runtime_mode,
                    "product_path_role": (
                        "drilldown_regression_not_runtime_spine"
                        if product_demoted
                        else "runtime_spine"
                        if step
                        else "registry_only"
                    ),
                    "demotion_reason": PRODUCT_PATH_DEMOTION_REASONS.get(organ_id),
                    "input_mode": step.input_mode if step else None,
                    "example_ref": step.example_rel if step else None,
                    "fixture_runner_backed": False if step else None,
                    **evidence_profile,
                }
            )
        return organs

    def patterns(self) -> list[dict[str, Any]]:
        rows = _read_jsonl(
            self.root
            / "examples/pattern_binding_contract/exported_substrate_bundle/pattern_rows.jsonl"
        )
        return [
            {
                "pattern_id": str(row.get("pattern_id") or ""),
                "organ_id": row.get("organ_id"),
                "title": row.get("title"),
                "projection_posture": row.get("public_projection_posture")
                or row.get("projection_mode"),
                "source_ref_count": len(row.get("source_refs", []))
                if isinstance(row.get("source_refs"), list)
                else 0,
            }
            for row in rows
        ]

    def routes(self) -> list[dict[str, Any]]:
        payload = _read_json_if_exists(
            self.root / "examples/navigation_hologram_route_plane/exported_route_plane_bundle/route_rows.json"
        )
        return [
            {
                "route_id": str(row.get("route_id") or row.get("row_id") or ""),
                "row_id": row.get("row_id"),
                "title": row.get("title"),
                "cluster_id": row.get("cluster_id"),
                "surface_role": row.get("surface_role"),
                "projection_not_authority": not bool(row.get("claims_source_authority")),
            }
            for row in _rows(payload, "rows")
        ]

    def workitems(self) -> list[dict[str, Any]]:
        payload = _read_json_if_exists(
            self.root / "examples/mission_transaction_work_spine/exported_mission_transaction_bundle/workitems.json"
        )
        return [
            {
                "work_item_id": str(row.get("work_item_id") or ""),
                "state": row.get("state"),
                "depends_on": row.get("depends_on", []),
                "receipt_refs": row.get("receipt_refs", []),
                "projection_not_authority": row.get("projection_not_authority") is True,
            }
            for row in _rows(payload, "workitems")
        ]

    def evidence(self) -> list[dict[str, Any]]:
        receipts = sorted((self.root / "receipts").rglob("*.json"))
        return [_safe_receipt_summary(path, self.root) for path in receipts]

    def status(self) -> dict[str, Any]:
        organs = self.organs()
        adapter_backed_rows = [
            row for row in organs if row.get("runtime_mode") == "adapter_backed"
        ]
        adapter_backed = [row["organ_id"] for row in adapter_backed_rows]
        truth_accounting = _truth_accounting(adapter_backed_rows)
        product_steps = _product_runtime_steps()
        demoted_drilldowns = [
            row for row in organs if row.get("runtime_mode") == "drilldown_only"
        ]
        routes = self.routes()
        workitems = self.workitems()
        evidence = self.evidence()
        pattern_surface = architecture_kernel.pattern_surface_contract(self.root)
        standard_pressure = architecture_kernel.standard_pressure_contract(self.root)
        return {
            "schema_version": "microcosm_runtime_status_v1",
            "status": PASS if len(adapter_backed) == len(product_steps) else "blocked",
            "posture": "executable_research_prototype",
            "public_root": _public_relative(self.root, self.root),
            "runtime_surface": {
                "commands": [
                    "microcosm init <project>",
                    "microcosm index <project>",
                    "microcosm catalog <project>",
                    "microcosm architecture <project>",
                    "microcosm compile <project>",
                    "microcosm python-lens <project>",
                    "microcosm patterns <project>",
                    "microcosm route <project>",
                    "microcosm explain <project> <route_id>",
                    "microcosm graph <project>",
                    "microcosm work create <project>",
                    "microcosm work run <project>",
                    "microcosm observe <project>",
                    "microcosm evidence list <project>",
                    "microcosm tour <project>",
                    "microcosm status",
                    "microcosm spine",
                    "microcosm authority",
                    "microcosm prediction-lens",
                    "microcosm market-boundary",
                    "microcosm corpus-lens",
                    "microcosm trace-lens",
                    "microcosm repair-loop",
                    "microcosm evidence-cells",
                    "microcosm proof-loop-depth",
                    "microcosm landing-replay",
                    "microcosm view-quality",
                    "microcosm projection-safety",
                    "microcosm drift-control",
                    "microcosm spatial-simulation",
                    "microcosm circuit-attribution",
                    "microcosm route-cleanup",
                    "microcosm projection-import-map",
                    "microcosm import-projector",
                    "microcosm option-surface-lens",
                    "microcosm stripping-guard",
                    "microcosm standards-control",
                    "microcosm hook-coverage",
                    "microcosm replay-gauntlet",
                    "microcosm benchmark-lab",
                    "microcosm legibility-scorecard",
                    "microcosm intake",
                    "microcosm run examples/runtime_shell/demo_project",
                    "microcosm reveal",
                    "microcosm formal-math-lean-proof-witness run-witness-bundle",
                    "microcosm formal-math-premise-retrieval run-retrieval-bundle",
                    "microcosm formal-math-verifier-trace-repair-loop run-loop-bundle",
                    "microcosm verifier-lab-kernel run-kernel-bundle",
                    "microcosm verifier-lab-execution-spine run-execution-bundle",
                    "microcosm certificate-kernel-execution-lab run-certificate-bundle",
                    "microcosm formal-evidence-cell-anchor-resolver run-anchor-bundle",
                    "microcosm undeclared-library-prior-symbol-classifier run-symbol-bundle",
                    "microcosm lean-std-premise-index run-index-bundle",
                    (
                        "microcosm ring2-premise-retrieval-precision-recall-harness "
                        "run-precision-recall-bundle"
                    ),
                    "microcosm durable-agent-work-landing-replay run-work-landing-bundle",
                    "microcosm research-replication-rubric-artifact-replay run-replication-bundle",
                    (
                        "microcosm world-model-projection-drift-control-room "
                        "run-drift-control-bundle"
                    ),
                    (
                        "microcosm spatial-world-model-counterfactual-simulation-replay "
                        "run-simulation-bundle"
                    ),
                    (
                        "microcosm materials-chemistry-closed-loop-lab-safety-replay "
                        "run-lab-bundle"
                    ),
                    (
                        "microcosm mechanistic-interpretability-circuit-attribution-replay "
                        "run-attribution-bundle"
                    ),
                    (
                        "microcosm agent-memory-temporal-conflict-replay "
                        "run-memory-bundle"
                    ),
                    (
                        "microcosm sleeper-memory-poisoning-quarantine-replay "
                        "run-quarantine-bundle"
                    ),
                    (
                        "microcosm mcp-tool-authority-replay "
                        "run-tool-authority-bundle"
                    ),
                    (
                        "microcosm proof-derived-governed-mutation-authorization "
                        "run-authorization-bundle"
                    ),
                    (
                        "microcosm belief-state-process-reward-replay "
                        "run-reward-bundle"
                    ),
                    (
                        "microcosm agent-sandbox-policy-escape-replay "
                        "run-sandbox-bundle"
                    ),
                    (
                        "microcosm indirect-prompt-injection-information-flow-policy-replay "
                        "run-prompt-injection-bundle"
                    ),
                    (
                        "microcosm agentic-vulnerability-discovery-patch-proof-replay "
                        "run-patch-proof-bundle"
                    ),
                    (
                        "microcosm agent-route-observability-runtime "
                        "validate-computer-use-bundle"
                    ),
                    "microcosm provider-context-recipe-budget-policy run-budget-bundle",
                    "microcosm corpus-readiness-mathlib-absence-gate run-projection-bundle",
                    "microcosm tactic-portfolio-availability-probe run-availability-bundle",
                    "microcosm target-shape-tactic-routing-gate run-routing-bundle",
                    "microcosm macro-projection-import-protocol run-projection-bundle",
                    "microcosm prediction-oracle-reconciliation run-prediction-bundle",
                    "microcosm standards-meta-diagnostics run-diagnostics-bundle",
                    "microcosm cold-reader-route-map run-route-map-bundle",
                    "microcosm serve",
                    "microcosm route list",
                    "microcosm route inspect <id>",
                    "microcosm work demo",
                    "microcosm evidence list",
                    "microcosm evidence inspect <receipt>",
                ],
                "demoted_drilldown_commands": [
                    (
                        "microcosm agent-benchmark-integrity-anti-gaming-replay "
                        "run-benchmark-integrity-bundle"
                    ),
                    (
                        "microcosm agent-monitor-redteam-falsification-replay "
                        "run-monitor-bundle"
                    ),
                    (
                        "microcosm agent-sabotage-scheming-monitor-replay "
                        "run-sabotage-bundle"
                    ),
                    (
                        "microcosm mathematical-strategy-atlas-hypothesis-scorer "
                        "run-strategy-bundle"
                    )
                ],
                "receipts_are_drilldown_evidence": True,
                "fixtures_are_tests": True,
            },
            "organ_count": len(organs),
            "adapter_backed_organ_count": len(adapter_backed),
            "adapter_backed_count_is_product_progress": False,
            "real_substrate_progress_count": truth_accounting[
                "real_substrate_progress_count"
            ],
            "non_progress_organ_count": truth_accounting["non_progress_organ_count"],
            "truth_accounting": truth_accounting,
            "product_path_demoted_organ_count": len(demoted_drilldowns),
            "product_path_demoted_organs": [
                {
                    "organ_id": str(row.get("organ_id") or ""),
                    "runtime_mode": row.get("runtime_mode"),
                    "product_path_role": row.get("product_path_role"),
                    "demotion_reason": row.get("demotion_reason"),
                }
                for row in demoted_drilldowns
            ],
            "fixture_runner_backed_organ_count": 0,
            "accepted_adapter_backed_organs": adapter_backed,
            "route_count": len(routes),
            "pattern_count": len(self.patterns()),
            "pattern_surface": pattern_surface,
            "standard_pressure_surface": standard_pressure,
            "workitem_count": len(workitems),
            "evidence_count": len(evidence),
            "kernel_primitive_count": architecture_kernel.load_kernel_manifest(self.root).get("primitive_count"),
            "release_authorized": False,
            "next_actions": [
                "run microcosm init <project>",
                "run microcosm compile <project>",
                "run microcosm python-lens <project>",
                "run microcosm tour <project>",
                "run microcosm explain <project> <route_id>",
                "run microcosm spine",
                "run microcosm authority",
                "run microcosm prediction-lens",
                "run microcosm market-boundary",
                "run microcosm corpus-lens",
                "run microcosm trace-lens",
                "run microcosm repair-loop",
                "run microcosm evidence-cells",
                "run microcosm proof-loop-depth",
                "run microcosm landing-replay",
                "run microcosm view-quality",
                "run microcosm projection-safety",
                "run microcosm drift-control",
                "run microcosm spatial-simulation",
                "run microcosm materials-chemistry-closed-loop-lab-safety-replay run-lab-bundle",
                "run microcosm circuit-attribution",
                "run microcosm route-cleanup",
                "run microcosm projection-import-map",
                "run microcosm import-projector",
                "run microcosm option-surface-lens",
                "run microcosm stripping-guard",
                "run microcosm standards-control",
                "run microcosm hook-coverage",
                "run microcosm replay-gauntlet",
                "run microcosm agent-memory-temporal-conflict-replay run-memory-bundle",
                "run microcosm sleeper-memory-poisoning-quarantine-replay run-quarantine-bundle",
                "run microcosm mcp-tool-authority-replay run-tool-authority-bundle",
                "run microcosm proof-derived-governed-mutation-authorization run-authorization-bundle",
                "run microcosm belief-state-process-reward-replay run-reward-bundle",
                "run microcosm certificate-kernel-execution-lab run-certificate-bundle",
                "run microcosm benchmark-lab",
                "run microcosm legibility-scorecard",
                "run microcosm intake",
                "run microcosm reveal",
                "open evidence only when drilldown is needed",
            ],
        }

    def spine(self) -> dict[str, Any]:
        organs = self.organs()
        evidence_registry = _load_evidence_class_registry(self.root)
        adapter_backed = [row for row in organs if row.get("runtime_mode") == "adapter_backed"]
        truth_accounting = _truth_accounting(adapter_backed)
        product_steps = _product_runtime_steps()
        demoted_drilldowns = [
            row for row in organs if row.get("runtime_mode") == "drilldown_only"
        ]
        patterns = self.patterns()
        routes = self.routes()
        workitems = self.workitems()
        evidence = self.evidence()
        return {
            "schema_version": "microcosm_public_runtime_spine_v1",
            "status": PASS if len(adapter_backed) == len(product_steps) else "blocked",
            "posture": "executable_research_prototype",
            "public_claim": (
                "Microcosm turns a repo into local substrate state: catalog, "
                "patterns, routes, work transactions, events, evidence, and explanations."
            ),
            "cold_reader_goal": "legible_under_10_minutes_without_private_macro_context",
            "first_run_path": [
                {
                    "step_id": "run_ten_minute_tour",
                    "command": "microcosm tour <project>",
                    "shows": [
                        "one source-open path from repo -> .microcosm",
                        "compile summary",
                        "runtime surfaces and endpoints",
                        "authority ceilings",
                        "evidence refs after the causal path is visible",
                    ],
                },
                {
                    "step_id": "compile_project",
                    "command": "microcosm compile <project>",
                    "produces": [
                        ".microcosm/catalog.json",
                        ".microcosm/python_lens.json",
                        ".microcosm/patterns.json",
                        ".microcosm/routes.json",
                        ".microcosm/work_items.json",
                        ".microcosm/events.jsonl",
                        ".microcosm/evidence/",
                    ],
                },
                {
                    "step_id": "inspect_python_lens",
                    "command": "microcosm python-lens <project>",
                    "shows": [
                        "Python file roles",
                        "package roots",
                        "route-readiness checks",
                        "path metadata without source-body export",
                    ],
                },
                {
                    "step_id": "inspect_route",
                    "command": "microcosm explain <project> readme_onboarding_route",
                    "shows": [
                        "grounded_refs",
                        "resolved pattern bindings",
                        "resolved standard pressure",
                        "work transaction contracts",
                        "event refs",
                        "evidence refs",
                    ],
                },
                {
                    "step_id": "open_observatory",
                    "command": "microcosm serve <project> --host 127.0.0.1 --port 8765",
                    "shows": [
                        "causal chain before raw JSON",
                        "route -> work -> event -> evidence",
                        "authority ceiling",
                    ],
                },
                {
                    "step_id": "inspect_public_spine",
                    "command": "microcosm spine",
                    "shows": [
                        "accepted adapter-backed organs",
                        "runtime evidence refs",
                        "first-run command path",
                        "secret-only authority boundary",
                    ],
                },
                {
                    "step_id": "inspect_authority_map",
                    "command": "microcosm authority",
                    "shows": [
                        "global authority ceiling",
                        "organ evidence classes",
                        "organ authority refs",
                        "hard public boundaries",
                        "safe local-only exceptions",
                    ],
                },
                {
                    "step_id": "inspect_prediction_lens",
                    "command": "microcosm prediction-lens",
                    "shows": [
                        "synthetic CP1/CP2 prediction mechanics",
                        "oracle diff grading summary",
                        "dossier mutation boundary",
                        "no advice, no trading, no live-data ceiling",
                    ],
                },
                {
                    "step_id": "inspect_market_prediction_boundary",
                    "command": "microcosm market-boundary",
                    "shows": [
                        "public-safe forecast claim contract",
                        "base-rate and scenario-tree gates before single-point claims",
                        "timestamp and data-freshness boundary",
                        "decision policy separated from trading or investment advice",
                        "no live data, private portfolio, or performance guarantee authority",
                    ],
                },
                {
                    "step_id": "inspect_corpus_lens",
                    "command": "microcosm corpus-lens",
                    "shows": [
                        "Mathlib import absence",
                        "translation-smoke-only corpora",
                        "blocked formal-math consumers",
                        "metadata-only proof/corpus authority ceiling",
                    ],
                },
                {
                    "step_id": "inspect_verifier_trace_repair_lens",
                    "command": "microcosm trace-lens",
                    "shows": [
                        "verifier failure class taxonomy",
                        "trace grade before repair promotion",
                        "cold rerun promotion gate",
                        "proof-body and oracle-premise redaction rules",
                        "metadata-only authority ceiling",
                    ],
                },
                {
                    "step_id": "inspect_verifier_repair_loop",
                    "command": "microcosm repair-loop",
                    "shows": [
                        "failure class to repair-route transitions",
                        "cold rerun as a promotion gate",
                        "curriculum deltas scoped to metadata cells",
                        "proof-body, oracle-premise, and provider-payload exclusions",
                        "metadata-only repair authority ceiling",
                    ],
                },
                {
                    "step_id": "inspect_formal_evidence_cells",
                    "command": "microcosm evidence-cells",
                    "shows": [
                        "proof-language claim strength mapped to evidence cell ids",
                        "unknown and missing-source cell rejection",
                        "no-sorry language boundary",
                        "proof-body and private-source redaction rules",
                        "metadata-only authority ceiling",
                    ],
                },
                {
                    "step_id": "inspect_proof_loop_depth",
                    "command": "microcosm proof-loop-depth",
                    "shows": [
                        "formal-math gate depth from corpus readiness to Lean witness",
                        "premise index, retrieval, tactic, and target-shape routing gates",
                        "verifier trace, cold-rerun repair, and evidence-cell promotion boundaries",
                        "fixture metric and theorem-solution anti-claims",
                        "metadata-only authority ceiling",
                    ],
                },
                {
                    "step_id": "inspect_verifier_lab_kernel",
                    "command": (
                        "microcosm verifier-lab-kernel run-kernel-bundle"
                    ),
                    "shows": [
                        "Lean witness, tactic routing, and verifier trace components",
                        "oracle comparator separated from forward success",
                        "provider hypotheses quarantined from proof authority",
                        "CP2 typed action candidates and bounded Evolve candidates",
                        "contract rejections and retrieval misses as separate claim buckets",
                    ],
                },
                {
                    "step_id": "inspect_verifier_lab_execution_spine",
                    "command": (
                        "microcosm verifier-lab-execution-spine "
                        "run-execution-bundle"
                    ),
                    "shows": [
                        "bounded Lean transition candidates executed through lake env",
                        "CP2 rerun effect and Evolve policy rerun receipts",
                        "proof-body and oracle-forward contamination rejection",
                        "tool-return-code witness scope separated from proof authority",
                    ],
                },
                {
                    "step_id": "inspect_work_landing_replay",
                    "command": "microcosm landing-replay",
                    "shows": [
                        "dirty-tree work landing lanes",
                        "scoped commit versus broad checkpoint boundary",
                        "protected Git metadata blocker handling",
                        "Task Ledger and Work Ledger closeout refs",
                        "no release or source mutation authority ceiling",
                    ],
                },
                {
                    "step_id": "inspect_durable_agent_work_landing_replay",
                    "command": "microcosm durable-agent-work-landing-replay run-work-landing-bundle",
                    "shows": [
                        "owned-path claim, validation, and closeout evidence refs",
                        "scoped commit head-advance gate before landed language",
                        "metadata-blocked patch-bundle recovery path",
                        "Task Ledger blocker capture and Work Ledger finalizer requirements",
                        "no Git mutation, broad checkpoint, private body, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_research_replication_rubric_artifact_replay",
                    "command": (
                        "microcosm research-replication-rubric-artifact-replay "
                        "run-replication-bundle"
                    ),
                    "shows": [
                        "rubric tree and contribution decomposition before replication language",
                        "scratch repo, experiment DAG, metric scripts, and declared artifact hashes",
                        "grader report, cost/runtime budget, ablation diff, and failure taxonomy",
                        "cold rerun receipt before success language",
                        "no benchmark performance, private body, provider, or publication authority",
                    ],
                },
                {
                    "step_id": "inspect_view_quality_action_map",
                    "command": "microcosm view-quality",
                    "shows": [
                        "one action row for every requested view",
                        "hot-action rollup as a projection, not the universe",
                        "missing-view and partial-measurement binding gaps",
                        "monitor rows excluded from resolution pressure",
                        "no private screenshot path or browser-control authority",
                    ],
                },
                {
                    "step_id": "inspect_projection_safety_audit",
                    "command": "microcosm projection-safety",
                    "shows": [
                        "omission receipts for compressed public projections",
                        "named drilldowns back to owner routes and receipt refs",
                        "authority ceilings for every public lens",
                        "no private source bodies, proof bodies, provider payloads, or release claims",
                        "reversible projection boundary before intake/reveal",
                    ],
                },
                {
                    "step_id": "inspect_projection_drift_control",
                    "command": "microcosm drift-control",
                    "shows": [
                        "world-model and projection drift rows as public metadata",
                        "source signal, repair route, and validation ref per row",
                        "route-lease, view-quality, CAP assimilation, and entry-payload drift controls",
                        "no live repair, source mutation, provider payload, or doctrine-promotion authority",
                        "metadata-only authority ceiling before projection import",
                    ],
                },
                {
                    "step_id": "inspect_world_model_projection_drift_control_room",
                    "command": (
                        "microcosm world-model-projection-drift-control-room "
                        "run-drift-control-bundle"
                    ),
                    "shows": [
                        "drift rows with source signal, repair route, and validation ref",
                        "view-quality, route-lease, CAP assimilation, and entry-payload controls",
                        "negative cases for source authority, live repair, private runtime export, and release claims",
                        "metadata-only receipts before any projection-drift language is promoted",
                        "no live repair, provider, doctrine-promotion, source mutation, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_spatial_world_model_counterfactual_simulation_replay",
                    "command": (
                        "microcosm spatial-world-model-counterfactual-simulation-replay "
                        "run-simulation-bundle"
                    ),
                    "shows": [
                        "counterfactual replay rows with scene, action, predicted state, transition diff, and oracle refs",
                        "rare-event and fidelity-limit labels beside each replay",
                        "negative cases for private video, raw sensor data, live operation, simulator product, and release claims",
                        "metadata-only receipts before spatial simulation language is treated as public evidence",
                        "no generated-video-only authority, real-world location, geographic accuracy, benchmark, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_mechanistic_interpretability_circuit_attribution_replay",
                    "command": (
                        "microcosm mechanistic-interpretability-circuit-attribution-replay "
                        "run-attribution-bundle"
                    ),
                    "shows": [
                        "toy prompt refs, sparse feature ids, graph nodes, graph edges, and approximation scores",
                        "causal inhibition and injection delta refs beside sufficiency and faithfulness limits",
                        "negative cases for private weights, raw activations, proprietary prompts, hidden reasoning, and unsupported transparency claims",
                        "metadata-only receipts before interpretability language is treated as public evidence",
                        "no private model internals, provider payload, benchmark score, model-transparency product, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_route_cleanup_contract",
                    "command": "microcosm route-cleanup",
                    "shows": [
                        "route cleanup rows from first contact to scoped landing",
                        "owner command and validator refs for every cleanup boundary",
                        "generated-region, option-surface, and Work Ledger cleanup gates",
                        "no route deletion, source mutation, private export, or release authority",
                        "metadata-only route hygiene contract before projection import",
                    ],
                },
                {
                    "step_id": "inspect_projection_import_map",
                    "command": "microcosm projection-import-map",
                    "shows": [
                        "macro pattern to public runtime surface rows",
                        "copy, clean, omit, validate, and authority-ceiling stages",
                        "public replacement refs and validator receipts",
                        "no automated import guarantee or private body export",
                    ],
                },
                {
                    "step_id": "inspect_import_projector_contract",
                    "command": "microcosm import-projector",
                    "shows": [
                        "repeatable public projection contract rows",
                        "source, clean, omit, fixture, validator, and observatory stages",
                        "authority ceiling per projector row",
                        "seed and ledger closeout requirements",
                        "no automated import execution or private body export",
                    ],
                },
                {
                    "step_id": "inspect_compression_profile_option_surface",
                    "command": "microcosm option-surface-lens",
                    "shows": [
                        "compression-profile governed option-surface rows",
                        "import-plan cell refs consumed through the projector contract",
                        "profile choice, sidecar, receipt, and validation boundaries",
                        "no profile switching, source mutation, private export, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_public_private_stripping_guard",
                    "command": "microcosm stripping-guard",
                    "shows": [
                        "public/private export guard rows",
                        "private body, proof body, provider payload, and raw path denials",
                        "secret-completeness and financial-advice anti-claims",
                        "source mutation and release-equivalence denials",
                        "read-model-only authority ceiling",
                    ],
                },
                {
                    "step_id": "inspect_standards_control",
                    "command": "microcosm standards-control",
                    "shows": [
                        "standards registry and public standard pressure counts",
                        "validator receipt coverage and acceptance command refs",
                        "fixture manifest negative cases",
                        "docs, authority, and projection-safety binding rows",
                        "read-model-only standards authority ceiling",
                    ],
                },
                {
                    "step_id": "inspect_hook_intervention_coverage",
                    "command": "microcosm hook-coverage",
                    "shows": [
                        "agent observability hook-shadow coverage",
                        "route-lease intervention decisions",
                        "actor-axis authority rejections",
                        "anti-pattern debt retirement boundary",
                        "no live operator/provider payload authority",
                    ],
                },
                {
                    "step_id": "inspect_agent_reliability_replay_gauntlet",
                    "command": "microcosm replay-gauntlet",
                    "shows": [
                        "synthetic red-team replay episodes",
                        "monitor and evaluator integrity gates",
                        "tool-authority and sandbox escape denials",
                        "prompt-injection and memory-write quarantine cases",
                        "no live agent, tool, secret, or benchmark authority",
                    ],
                },
                {
                    "step_id": "inspect_agent_memory_temporal_conflict_replay",
                    "command": (
                        "microcosm agent-memory-temporal-conflict-replay "
                        "run-memory-bundle"
                    ),
                    "shows": [
                        "three synthetic memory episodes with ADD, UPDATE, DELETE, and NOOP decisions",
                        "conflict-edge and stale-downgrade refs before memory can affect replay",
                        "metadata-only private thread refs plus paired memory-on/off cold replay receipts",
                        "raw transcript, private auto-promotion, stale override, source-authority, vector-only recall, final-answer-only credit, and active-injection denials",
                        "no live memory product, private transcript, provider, source mutation, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_sleeper_memory_poisoning_quarantine_replay",
                    "command": (
                        "microcosm sleeper-memory-poisoning-quarantine-replay "
                        "run-quarantine-bundle"
                    ),
                    "shows": [
                        "four synthetic sessions from poisoned source to rollback and cold rerun",
                        "source capsule and provenance refs before memory write admission",
                        "sleeper-poisoning quarantine before later retrieval can affect action",
                        "private body, live user memory, raw transcript, untrusted-promotion, deletion-without-audit, final-answer-only, and unmetered-influence denials",
                        "no live memory product, provider, benchmark-security, source mutation, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_mcp_tool_authority_replay",
                    "command": (
                        "microcosm mcp-tool-authority-replay "
                        "run-tool-authority-bundle"
                    ),
                    "shows": [
                        "three synthetic MCP-like tools: readonly lookup, write side effect, and untrusted result",
                        "narrow capability scope refs before tool-call admission",
                        "approval, side-effect ledger, rollback, and cold replay refs for write-capable calls",
                        "overbroad-scope, credential-export, tool-output-as-instruction, unapproved-side-effect, live-account, final-answer-only, rollback, and unredacted-payload denials",
                        "no live MCP account, credential, provider payload, benchmark-safety, source mutation, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_proof_derived_governed_mutation_authorization",
                    "command": (
                        "microcosm proof-derived-governed-mutation-authorization "
                        "run-authorization-bundle"
                    ),
                    "shows": [
                        "three synthetic action proposals: read-only inspection, scoped config write, and rollback",
                        "proof evidence cells and two visible policy verdict refs before synthetic execution identity refs",
                        "side-effect diff, rollback, and cold replay refs before governed-mutation claim admission",
                        "standing-credential, policy-after-execution, hidden-vote, live-credential, irreversible, unlogged, consensus-without-evidence, and final-answer-only denials",
                        "no live cloud/account, standing credential, provider, source mutation, benchmark-safety, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_belief_state_process_reward_replay",
                    "command": (
                        "microcosm belief-state-process-reward-replay "
                        "run-reward-bundle"
                    ),
                    "shows": [
                        "source-faithful public trace spans over three partially observable episodes with observation digests and typed belief summaries",
                        "predicted next evidence, verifier or observed feedback refs, belief-discrepancy scores, dense process rewards, and outcome rewards",
                        "reward-hacking trap pass, trajectory grouping, and cold replay refs before claim admission",
                        "hidden-reasoning export, neural-judge-only, hidden-gold, reward-by-formatting, verifier-bypass, benchmark-claim, and final-answer-only denials",
                        "no hidden reasoning, live RL, benchmark-score, provider, source mutation, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_agent_sandbox_policy_escape_replay",
                    "command": (
                        "microcosm agent-sandbox-policy-escape-replay "
                        "run-sandbox-bundle"
                    ),
                    "shows": [
                        "six synthetic action requests across secret, network, destructive, shell, safe edit, and reviewed mock-db cases",
                        "pre-execution policy verdicts before any side-effect receipt is admissible",
                        "blocked requests with zero side effects plus allowed/reviewed requests with diff and rollback receipts",
                        "real-secret, live-network, raw-env, post-hoc-policy, unlogged-side-effect, tool-output-bypass, executable-payload, and benchmark-claim denials",
                        "no live sandbox escape, secret handling, network access, host mutation, provider, benchmark-security, source mutation, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_indirect_prompt_injection_information_flow_policy_replay",
                    "command": (
                        "microcosm indirect-prompt-injection-information-flow-policy-replay "
                        "run-prompt-injection-bundle"
                    ),
                    "shows": [
                        "five synthetic sources across trusted user/policy and untrusted web/tool/browser channels",
                        "source-to-sink taint graph rows before any policy verdict is admitted",
                        "allow, warn, block, and review verdicts with sanitized-output and cold-replay receipts",
                        "real-account, secret-exfiltration, raw-prompt, tool-output-instruction, hidden-system-promotion, credential, final-answer-only, and untrusted-privileged-sink denials",
                        "no real email/docs/accounts, raw prompts, credentials, live tool calls, provider payloads, benchmark robustness, source mutation, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_agentic_vulnerability_discovery_patch_proof_replay",
                    "command": (
                        "microcosm agentic-vulnerability-discovery-patch-proof-replay "
                        "run-patch-proof-bundle"
                    ),
                    "shows": [
                        "three synthetic targets and four issue hypotheses before vulnerability language is admitted",
                        "trace evidence, abstract exploitability refs, patch diff refs, regression tests, verifier receipts, and sandbox verdicts",
                        "false-positive triage and cold replay receipts before pass labels",
                        "live-target, real-CVE, weaponized-payload, credential, network-exfiltration, exploit-instruction, testless-patch, and benchmark-score denials",
                        "no live security testing, exploit authority, provider execution, source mutation, benchmark score, or release authority",
                    ],
                },
                {
                    "step_id": "inspect_certificate_kernel_execution_lab",
                    "command": (
                        "microcosm certificate-kernel-execution-lab "
                        "run-certificate-bundle"
                    ),
                    "shows": [
                        "public Lean/Lake certificate-kernel fixture evidence",
                        "CP2 and Evolve rerun metadata separated from proof authority",
                        "proof-body and private-source redaction counters",
                        "external subprocess witness scope before public certificate claims",
                        "no release, provider, source mutation, or general formal-proof authority",
                    ],
                },
                {
                    "step_id": "inspect_repository_benchmark_transaction_lab",
                    "command": "microcosm benchmark-lab",
                    "shows": [
                        "synthetic two-repo issue/patch oracle lab",
                        "FAIL_TO_PASS and PASS_TO_PASS-style regression gates",
                        "misleading-test denial and scoped diff receipts",
                        "workitem admission and provider-slot cooldown decisions",
                        "no SWE-bench, live repo mutation, or provider execution claim",
                    ],
                },
                {
                    "step_id": "inspect_public_legibility_scorecard",
                    "command": "microcosm legibility-scorecard",
                    "shows": [
                        "cold-reader question-to-command scorecard",
                        "10-minute comprehension checkpoints",
                        "runtime surface and endpoint coverage",
                        "evidence refs and negative cases",
                        "no release, benchmark, secret-export, or reader-success claim",
                    ],
                },
                {
                    "step_id": "open_import_bridge",
                    "command": "microcosm intake",
                    "shows": [
                        "macro projection cells",
                        "runtime reveal/import bridge",
                        "landed readiness-extension status",
                        "public replacement and validation refs",
                        "release_authorized=false",
                    ],
                },
                {
                    "step_id": "open_reveal_board",
                    "command": "microcosm reveal",
                    "shows": [
                        "ten-minute reveal board",
                        "evidence-strength policy",
                        "negative cases",
                        "evidence ref count",
                        "release_authorized=false",
                    ],
                },
                {
                    "step_id": "inspect_cold_reader_route_map",
                    "command": "microcosm cold-reader-route-map run-route-map-bundle",
                    "shows": [
                        "first-run route sequence",
                        "command refs",
                        "receipt-backed route cards",
                        "authority ceiling",
                    ],
                },
            ],
            "surface_counts": {
                "organ_count": len(organs),
                "adapter_backed_organ_count": len(adapter_backed),
                "adapter_backed_count_is_product_progress": False,
                "real_substrate_progress_count": truth_accounting[
                    "real_substrate_progress_count"
                ],
                "non_progress_organ_count": truth_accounting["non_progress_organ_count"],
                "real_runtime_receipt_count": truth_accounting[
                    "real_runtime_receipt_count"
                ],
                "copied_non_secret_macro_body_count": truth_accounting[
                    "copied_non_secret_macro_body_count"
                ],
                "source_faithful_refactor_count": truth_accounting[
                    "source_faithful_refactor_count"
                ],
                "real_import_validation_count": truth_accounting[
                    "real_import_validation_count"
                ],
                "regression_negative_fixture_count": truth_accounting[
                    "regression_negative_fixture_count"
                ],
                "blocked_import_debt_count": truth_accounting["blocked_import_debt_count"],
                "secret_exclusion_count": truth_accounting["secret_exclusion_count"],
                "legacy_adapter_or_synthetic_placeholder_count": truth_accounting[
                    "legacy_adapter_or_synthetic_placeholder_count"
                ],
                "delete_or_demote_candidate_count": truth_accounting[
                    "delete_or_demote_candidate_count"
                ],
                "product_path_demoted_organ_count": len(demoted_drilldowns),
                "pattern_count": len(patterns),
                "route_count": len(routes),
                "workitem_count": len(workitems),
                "evidence_count": len(evidence),
                "evidence_class_count": len(_evidence_class_counts(adapter_backed)),
            },
            "truth_accounting": truth_accounting,
            "evidence_class_registry": _evidence_registry_summary(evidence_registry),
            "evidence_class_counts": _evidence_class_counts(adapter_backed),
            "accepted_runtime_spine": [
                {
                    "ordinal": index,
                    "organ_id": str(row.get("organ_id") or ""),
                    "status": row.get("status"),
                    "runtime_mode": row.get("runtime_mode"),
                    "input_mode": row.get("input_mode"),
                    "example_ref": row.get("example_ref"),
                    "validator_command": row.get("validator_command"),
                    "current_authority_receipt": row.get("current_authority_receipt"),
                    "generated_receipt_count": len(row.get("generated_receipts", []))
                    if isinstance(row.get("generated_receipts"), list)
                    else 0,
                    "evidence_class": row.get("evidence_class"),
                    "evidence_strength_rank": row.get("evidence_strength_rank"),
                    "truth_accounting_bucket": row.get("truth_accounting_bucket"),
                    "counts_as_real_substrate_progress": row.get(
                        "counts_as_real_substrate_progress"
                    )
                    is True,
                    "evaluator_basis": row.get("evaluator_basis"),
                    "verdict_source": row.get("verdict_source"),
                    "negative_case_independence": row.get("negative_case_independence"),
                    "claim_ceiling": row.get("claim_ceiling"),
                    "classification_basis": row.get("classification_basis"),
                    "evidence_strength_disclosed": row.get("evidence_strength_disclosed") is True,
                }
                for index, row in enumerate(adapter_backed, start=1)
            ],
            "real_substrate_progress_spine": [
                {
                    "organ_id": str(row.get("organ_id") or ""),
                    "evidence_class": row.get("evidence_class"),
                    "truth_accounting_bucket": row.get("truth_accounting_bucket"),
                    "claim_ceiling": row.get("claim_ceiling"),
                }
                for row in adapter_backed
                if row.get("counts_as_real_substrate_progress") is True
            ],
            "non_progress_runtime_spine": [
                {
                    "organ_id": str(row.get("organ_id") or ""),
                    "evidence_class": row.get("evidence_class"),
                    "truth_accounting_bucket": row.get("truth_accounting_bucket"),
                    "claim_ceiling": row.get("claim_ceiling"),
                }
                for row in adapter_backed
                if row.get("counts_as_real_substrate_progress") is not True
            ],
            "demoted_drilldown_surfaces": [
                {
                    "organ_id": str(row.get("organ_id") or ""),
                    "runtime_mode": row.get("runtime_mode"),
                    "product_path_role": row.get("product_path_role"),
                    "demotion_reason": row.get("demotion_reason"),
                    "input_mode": row.get("input_mode"),
                    "example_ref": row.get("example_ref"),
                    "evidence_class": row.get("evidence_class"),
                    "claim_ceiling": row.get("claim_ceiling"),
                }
                for row in demoted_drilldowns
            ],
            "evidence_policy": {
                "receipts_are_drilldown_evidence": True,
                "body_in_receipt_by_default": False,
                "real_runtime_receipts_are_product_evidence": True,
                "copied_non_secret_macro_bodies_require_provenance": True,
                "source_faithful_refactors_are_product_evidence": True,
                "synthetic_receipts_are_product_evidence": False,
                "synthetic_fixtures_allowed_only_as": [
                    "regression_harness",
                    "negative_case",
                    "blocked_import_debt",
                ],
                "blocked_import_debt_must_name_replacement_target": True,
                "secret_exclusion_scan_is_receipt_owner": True,
                "fixtures_are_tests": True,
                "accepted_status_is_not_evidence_strength": True,
                "unclassified_organs_block_authority_projection": True,
                "open_receipts_after_route_or_spine": True,
            },
            "authority_ceiling": {
                "release_authorized": False,
                "provider_calls_authorized": False,
                "source_mutation_authorized": False,
                "live_task_ledger_mutation_authorized": False,
                "trading_or_financial_advice_authorized": False,
                "private_data_equivalence_claim": False,
                "whole_system_correctness_claim": False,
            },
            "anti_claim": (
                "The public runtime spine is a read-only legibility surface over accepted "
                "public Microcosm organs and local project substrate commands. It does not "
                "authorize release, provider calls, source mutation, trading or financial "
                "advice, private-data equivalence, Mathlib-dependent proof authority, or "
                "whole-system correctness claims."
            ),
        }

    def tour(
        self,
        project: str | Path | None = DEFAULT_PROJECT_REL,
        *,
        persist_receipt: bool = True,
    ) -> dict[str, Any]:
        raw_project = project if project is not None else DEFAULT_PROJECT_REL
        project_path = Path(raw_project).expanduser()
        if not project_path.is_absolute():
            project_path = self.root / project_path
        project_path = project_path.resolve(strict=False)

        compiled = project_substrate.compile_project(project_path)
        spine = self.spine()
        authority = self.authority(persist_receipts=persist_receipt)
        prediction = self.prediction_lens()
        market_boundary = self.market_boundary()
        corpus = self.corpus_lens()
        trace_lens = self.trace_lens()
        repair_loop = self.repair_loop()
        evidence_cells = self.evidence_cells()
        proof_loop_depth = self.proof_loop_depth()
        landing_replay = self.landing_replay()
        view_quality = self.view_quality()
        projection_safety = self.projection_safety()
        projection_drift = self.projection_drift()
        spatial_simulation = self.spatial_simulation()
        circuit_attribution = self.circuit_attribution()
        route_cleanup = self.route_cleanup()
        projection_import_map = self.projection_import_map()
        import_projector = self.import_projector()
        option_surface = self.option_surface_lens()
        stripping_guard = self.stripping_guard()
        standards_control = self.standards_control()
        hook_coverage = self.hook_coverage()
        replay_gauntlet = self.replay_gauntlet()
        benchmark_lab = self.benchmark_lab()
        legibility_scorecard = self.legibility_scorecard()
        intake = self.intake()
        reveal = self.reveal(persist_receipt=persist_receipt)

        project_ref = _public_relative(project_path, self.root)
        if project_ref.startswith("/") or project_ref.startswith(".."):
            project_ref = project_path.name

        tour_path = self.runtime_receipt_dir / "public_ten_minute_tour.json"
        evidence_refs = list(
            dict.fromkeys(
                [
                    str(ref)
                    for ref in [
                        authority.get("authority_map_ref"),
                        prediction.get("prediction_lens_ref"),
                        market_boundary.get("market_boundary_lens_ref"),
                        corpus.get("corpus_lens_ref"),
                        trace_lens.get("trace_lens_ref"),
                        repair_loop.get("repair_loop_ref"),
                        evidence_cells.get("evidence_cell_lens_ref"),
                        proof_loop_depth.get("proof_loop_depth_ref"),
                        landing_replay.get("landing_replay_ref"),
                        view_quality.get("view_quality_lens_ref"),
                        projection_safety.get("projection_safety_lens_ref"),
                        projection_drift.get("projection_drift_lens_ref"),
                        circuit_attribution.get("circuit_attribution_lens_ref"),
                        route_cleanup.get("route_cleanup_lens_ref"),
                        projection_import_map.get("projection_import_map_ref"),
                        import_projector.get("import_projector_ref"),
                        option_surface.get("option_surface_lens_ref"),
                        stripping_guard.get("stripping_guard_ref"),
                        standards_control.get("standards_control_ref"),
                        hook_coverage.get("hook_intervention_coverage_lens_ref"),
                        replay_gauntlet.get("replay_gauntlet_lens_ref"),
                        benchmark_lab.get("benchmark_lab_ref"),
                        legibility_scorecard.get("legibility_scorecard_ref"),
                        reveal.get("evidence_ref"),
                        *[
                            item
                            for item in intake.get("runtime_bridge_evidence_refs", [])
                            if isinstance(item, str)
                        ],
                    ]
                    if isinstance(ref, str) and ref
                ]
            )
        )
        surface_statuses = {
            "compile": compiled.get("status"),
            "spine": spine.get("status"),
            "authority": authority.get("status"),
            "prediction": prediction.get("status"),
            "market_boundary": market_boundary.get("status"),
            "corpus": corpus.get("status"),
            "trace": trace_lens.get("status"),
            "repair_loop": repair_loop.get("status"),
            "evidence_cells": evidence_cells.get("status"),
            "proof_loop_depth": proof_loop_depth.get("status"),
            "landing_replay": landing_replay.get("status"),
            "view_quality": view_quality.get("status"),
            "projection_safety": projection_safety.get("status"),
            "projection_drift": projection_drift.get("status"),
            "circuit_attribution": circuit_attribution.get("status"),
            "route_cleanup": route_cleanup.get("status"),
            "projection_import_map": projection_import_map.get("status"),
            "import_projector": import_projector.get("status"),
            "option_surface": option_surface.get("status"),
            "stripping_guard": stripping_guard.get("status"),
            "standards_control": standards_control.get("status"),
            "hook_coverage": hook_coverage.get("status"),
            "replay_gauntlet": replay_gauntlet.get("status"),
            "benchmark_lab": benchmark_lab.get("status"),
            "legibility_scorecard": legibility_scorecard.get("status"),
            "intake": intake.get("status"),
            "reveal": reveal.get("status"),
        }
        commands = [
            "microcosm tour <project>",
            "microcosm compile <project>",
            "microcosm python-lens <project>",
            "microcosm spine",
            "microcosm authority",
            "microcosm prediction-lens",
            "microcosm market-boundary",
            "microcosm corpus-lens",
            "microcosm trace-lens",
            "microcosm repair-loop",
            "microcosm evidence-cells",
            "microcosm proof-loop-depth",
            "microcosm landing-replay",
            "microcosm view-quality",
            "microcosm projection-safety",
            "microcosm drift-control",
            "microcosm spatial-simulation",
            "microcosm circuit-attribution",
            "microcosm route-cleanup",
            "microcosm projection-import-map",
            "microcosm import-projector",
            "microcosm option-surface-lens",
            "microcosm stripping-guard",
            "microcosm standards-control",
            "microcosm hook-coverage",
            "microcosm replay-gauntlet",
            "microcosm benchmark-lab",
            "microcosm legibility-scorecard",
            "microcosm intake",
            "microcosm reveal",
            "microcosm serve <project>",
            "microcosm evidence inspect <receipt>",
        ]
        route_cards = [
            {
                "card_id": "compile",
                "minute_budget": 2,
                "command": "microcosm compile <project>",
                "endpoint": None,
                "shows": [
                    ".microcosm/catalog.json",
                    ".microcosm/python_lens.json",
                    ".microcosm/routes.json",
                    ".microcosm/work_items.json",
                    ".microcosm/evidence/",
                ],
                "status": compiled.get("status"),
            },
            {
                "card_id": "runtime_spine",
                "minute_budget": 1,
                "command": "microcosm spine",
                "endpoint": "/spine",
                "shows": [
                    "accepted runtime organs",
                    "first-run command path",
                    "evidence policy",
                ],
                "status": spine.get("status"),
            },
            {
                "card_id": "authority",
                "minute_budget": 1,
                "command": "microcosm authority",
                "endpoint": "/authority",
                "shows": [
                    "release/provider/source ceilings",
                    "safe local exceptions",
                    "surface authority map",
                ],
                "status": authority.get("status"),
            },
            {
                "card_id": "prediction_and_corpus",
                "minute_budget": 2,
                "command": (
                    "microcosm prediction-lens && microcosm corpus-lens && "
                    "microcosm trace-lens && microcosm repair-loop && "
                    "microcosm evidence-cells && microcosm proof-loop-depth && "
                    "microcosm landing-replay && "
                    "microcosm view-quality && microcosm projection-safety && "
                    "microcosm market-boundary && "
                    "microcosm drift-control && "
                    "microcosm spatial-simulation && "
                    "microcosm circuit-attribution && "
                    "microcosm route-cleanup && "
                    "microcosm projection-import-map && "
                    "microcosm import-projector && "
                    "microcosm option-surface-lens && "
                    "microcosm stripping-guard && "
                    "microcosm standards-control && "
                    "microcosm hook-coverage && microcosm replay-gauntlet && "
                    "microcosm benchmark-lab && microcosm legibility-scorecard"
                ),
                "endpoint": (
                    "/prediction + /corpus + /trace + /repair-loop + "
                    "/evidence-cells + /proof-loop-depth + /landing-replay + /view-quality + "
                    "/projection-safety + /market-boundary + /drift-control + /spatial-simulation + /circuit-attribution + /route-cleanup + "
                    "/projection-import-map + /import-projector + /option-surface-lens + /stripping-guard + /standards-control + /hook-coverage + "
                    "/replay-gauntlet + /benchmark-lab + /legibility-scorecard"
                ),
                "shows": [
                    "synthetic prediction mechanics",
                    "no-advice boundary",
                    "Mathlib absence",
                    "blocked formal-math consumers",
                    "verifier trace-repair gate",
                    "verifier repair loop as metadata curriculum",
                    "formal evidence-cell claim boundary",
                    "proof-loop depth map across formal-math gates",
                    "dirty-tree work landing replay",
                    "all-view quality action map",
                    "omission receipts and reversible projection boundary",
                    "public market/prediction claim boundary",
                    "projection drift controls with repair and validation refs",
                    "mechanistic interpretability circuit attribution with causal-intervention receipts",
                    "route cleanup contract rows with owner validators",
                    "public projection import map",
                    "repeatable import-projector contract",
                    "compression-profile governed option surface",
                    "public/private stripping guard",
                    "public standards-control lens",
                    "hook-shadow intervention coverage",
                    "synthetic agent reliability replay gauntlet",
                    "synthetic repository benchmark transaction lab",
                    "cold-reader public legibility scorecard",
                ],
                "status": PASS
                if prediction.get("status") == PASS
                and market_boundary.get("status") == PASS
                and corpus.get("status") == PASS
                and trace_lens.get("status") == PASS
                and repair_loop.get("status") == PASS
                and evidence_cells.get("status") == PASS
                and proof_loop_depth.get("status") == PASS
                and landing_replay.get("status") == PASS
                and view_quality.get("status") == PASS
                and projection_safety.get("status") == PASS
                and projection_drift.get("status") == PASS
                and route_cleanup.get("status") == PASS
                and projection_import_map.get("status") == PASS
                and import_projector.get("status") == PASS
                and option_surface.get("status") == PASS
                and stripping_guard.get("status") == PASS
                and standards_control.get("status") == PASS
                and hook_coverage.get("status") == PASS
                and replay_gauntlet.get("status") == PASS
                and benchmark_lab.get("status") == PASS
                and legibility_scorecard.get("status") == PASS
                else "blocked",
            },
            {
                "card_id": "intake_and_reveal",
                "minute_budget": 3,
                "command": "microcosm intake && microcosm reveal",
                "endpoint": "/intake + /reveal",
                "shows": [
                    "macro projection cells",
                    "public runtime refs and real-substrate receipt states",
                    "ten-minute reveal board",
                    "negative cases",
                ],
                "status": PASS
                if intake.get("status") == PASS and reveal.get("status") == PASS
                else "blocked",
            },
            {
                "card_id": "evidence_drilldown",
                "minute_budget": 1,
                "command": "microcosm evidence inspect <receipt>",
                "endpoint": "/evidence",
                "shows": [
                    "receipt refs only after the causal path is visible",
                    "anti-claims",
                    "authority ceilings",
                ],
                "status": PASS if evidence_refs else "blocked",
            },
        ]
        payload = {
            "schema_version": "microcosm_public_ten_minute_tour_v1",
            "created_at": utc_now(),
            "status": PASS if all(value == PASS for value in surface_statuses.values()) else "blocked",
            "tour_id": "public_ten_minute_tour",
            "command": "microcosm tour <project>",
            "endpoint": "/tour",
            "tour_ref": _public_relative(tour_path, self.root),
            "project_ref": project_ref,
            "snapshot_policy": {
                "lifecycle": "tracked_public_snapshot_refreshed_intentionally",
                "runtime_invocation_can_write_receipt": persist_receipt,
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
                    "runtime_summary.organ_count",
                    "runtime_summary.surface_authority_count",
                    "authority_ceiling",
                    "safe_to_show",
                    "evidence_refs",
                ],
            },
            "public_claim": (
                "Microcosm turns a repo into a local operating substrate and exposes the "
                "whole first-run path as a ten-minute source-open tour: compile, inspect, "
                "bound authority, inspect prediction/corpus/formal repair lenses, intake "
                "and reveal real-substrate receipt states, then drill receipts."
            ),
            "time_budget_minutes": 10,
            "command_path": commands,
            "endpoint_path": [
                "/tour",
                "/spine",
                "/authority",
                "/prediction",
                "/market-boundary",
                "/corpus",
                "/trace",
                "/repair-loop",
                "/evidence-cells",
                "/proof-loop-depth",
                "/landing-replay",
                "/view-quality",
                "/projection-safety",
                "/drift-control",
                "/spatial-simulation",
                "/circuit-attribution",
                "/route-cleanup",
                "/projection-import-map",
                "/import-projector",
                "/option-surface-lens",
                "/stripping-guard",
                "/standards-control",
                "/hook-coverage",
                "/replay-gauntlet",
                "/benchmark-lab",
                "/legibility-scorecard",
                "/intake",
                "/reveal",
                "/evidence",
            ],
            "route_cards": route_cards,
            "surface_statuses": surface_statuses,
            "compile_summary": {
                "headline": compiled.get("headline"),
                "file_count": compiled.get("file_count"),
                "passing_pattern_count": compiled.get("passing_pattern_count"),
                "route_count": compiled.get("route_count"),
                "selected_route_id": compiled.get("selected_route_id"),
                "work_id": compiled.get("work_id"),
                "event_count": compiled.get("event_count"),
                "evidence_count": compiled.get("evidence_count"),
                "source_files_mutated": compiled.get("source_files_mutated") is True,
                "state_ref": project_substrate.STATE_DIR,
            },
            "runtime_summary": {
                "organ_count": (spine.get("surface_counts") or {}).get("organ_count")
                if isinstance(spine.get("surface_counts"), dict)
                else None,
                "surface_authority_count": (authority.get("surface_counts") or {}).get(
                    "surface_authority_count"
                )
                if isinstance(authority.get("surface_counts"), dict)
                else None,
                "prediction_mechanic_count": len(prediction.get("mechanics", []))
                if isinstance(prediction.get("mechanics"), list)
                else 0,
                "market_boundary_row_count": (
                    market_boundary.get("boundary_summary") or {}
                ).get("row_count")
                if isinstance(market_boundary.get("boundary_summary"), dict)
                else 0,
                "market_boundary_negative_case_count": (
                    market_boundary.get("boundary_summary") or {}
                ).get("negative_case_count")
                if isinstance(market_boundary.get("boundary_summary"), dict)
                else 0,
                "corpus_count": (corpus.get("corpus_summary") or {}).get("corpus_count")
                if isinstance(corpus.get("corpus_summary"), dict)
                else None,
                "blocked_corpus_consumer_count": len(
                    (corpus.get("consumer_gate") or {}).get("blocked_case_ids", [])
                )
                if isinstance(corpus.get("consumer_gate"), dict)
                and isinstance((corpus.get("consumer_gate") or {}).get("blocked_case_ids"), list)
                else 0,
                "trace_repair_attempt_count": len(trace_lens.get("trace_rows", []))
                if isinstance(trace_lens.get("trace_rows"), list)
                else 0,
                "trace_negative_case_count": len(trace_lens.get("negative_case_ids", []))
                if isinstance(trace_lens.get("negative_case_ids"), list)
                else 0,
                "repair_loop_stage_count": len(repair_loop.get("loop_stages", []))
                if isinstance(repair_loop.get("loop_stages"), list)
                else 0,
                "repair_loop_transition_count": len(repair_loop.get("transition_rows", []))
                if isinstance(repair_loop.get("transition_rows"), list)
                else 0,
                "repair_loop_negative_case_count": len(repair_loop.get("negative_case_ids", []))
                if isinstance(repair_loop.get("negative_case_ids"), list)
                else 0,
                "formal_evidence_cell_count": len(evidence_cells.get("evidence_cells", []))
                if isinstance(evidence_cells.get("evidence_cells"), list)
                else 0,
                "formal_evidence_negative_case_count": len(
                    evidence_cells.get("negative_case_ids", [])
                )
                if isinstance(evidence_cells.get("negative_case_ids"), list)
                else 0,
                "proof_loop_gate_count": (
                    proof_loop_depth.get("proof_loop_summary") or {}
                ).get("gate_count")
                if isinstance(proof_loop_depth.get("proof_loop_summary"), dict)
                else 0,
                "proof_loop_negative_case_count": (
                    proof_loop_depth.get("proof_loop_summary") or {}
                ).get("negative_case_count")
                if isinstance(proof_loop_depth.get("proof_loop_summary"), dict)
                else 0,
                "landing_lane_count": len(landing_replay.get("lane_decision_table", []))
                if isinstance(landing_replay.get("lane_decision_table"), list)
                else 0,
                "landing_negative_case_count": len(landing_replay.get("negative_case_ids", []))
                if isinstance(landing_replay.get("negative_case_ids"), list)
                else 0,
                "view_quality_action_count": len(view_quality.get("action_rows", []))
                if isinstance(view_quality.get("action_rows"), list)
                else 0,
                "view_quality_hot_action_count": len(view_quality.get("hot_action_rollup", []))
                if isinstance(view_quality.get("hot_action_rollup"), list)
                else 0,
                "projection_import_map_row_count": (
                    projection_import_map.get("map_summary") or {}
                ).get("row_count")
                if isinstance(projection_import_map.get("map_summary"), dict)
                else 0,
                "import_projector_row_count": (
                    import_projector.get("projector_summary") or {}
                ).get("row_count")
                if isinstance(import_projector.get("projector_summary"), dict)
                else 0,
                "import_projector_stage_count": (
                    import_projector.get("projector_summary") or {}
                ).get("stage_count")
                if isinstance(import_projector.get("projector_summary"), dict)
                else 0,
                "option_surface_row_count": (
                    option_surface.get("option_surface_summary") or {}
                ).get("row_count")
                if isinstance(option_surface.get("option_surface_summary"), dict)
                else 0,
                "option_surface_stage_count": (
                    option_surface.get("option_surface_summary") or {}
                ).get("stage_count")
                if isinstance(option_surface.get("option_surface_summary"), dict)
                else 0,
                "projection_drift_row_count": (
                    projection_drift.get("drift_summary") or {}
                ).get("row_count")
                if isinstance(projection_drift.get("drift_summary"), dict)
                else 0,
                "projection_drift_repair_route_count": (
                    projection_drift.get("drift_summary") or {}
                ).get("repair_route_count")
                if isinstance(projection_drift.get("drift_summary"), dict)
                else 0,
                "route_cleanup_row_count": (
                    route_cleanup.get("cleanup_summary") or {}
                ).get("row_count")
                if isinstance(route_cleanup.get("cleanup_summary"), dict)
                else 0,
                "route_cleanup_negative_case_count": (
                    route_cleanup.get("cleanup_summary") or {}
                ).get("negative_case_count")
                if isinstance(route_cleanup.get("cleanup_summary"), dict)
                else 0,
                "projection_import_stage_count": len(
                    projection_import_map.get("import_stages", [])
                )
                if isinstance(projection_import_map.get("import_stages"), list)
                else 0,
                "stripping_guard_row_count": (
                    stripping_guard.get("guard_summary") or {}
                ).get("guard_row_count")
                if isinstance(stripping_guard.get("guard_summary"), dict)
                else 0,
                "stripping_guard_negative_case_count": (
                    stripping_guard.get("guard_summary") or {}
                ).get("negative_case_count")
                if isinstance(stripping_guard.get("guard_summary"), dict)
                else 0,
                "standards_control_row_count": (
                    standards_control.get("standards_summary") or {}
                ).get("standards_control_row_count")
                if isinstance(standards_control.get("standards_summary"), dict)
                else 0,
                "standards_control_negative_case_count": (
                    standards_control.get("standards_summary") or {}
                ).get("negative_case_count")
                if isinstance(standards_control.get("standards_summary"), dict)
                else 0,
                "hook_intervention_row_count": len(hook_coverage.get("intervention_rows", []))
                if isinstance(hook_coverage.get("intervention_rows"), list)
                else 0,
                "hook_missing_authority_count": len(
                    hook_coverage.get("missing_authority_case_ids", [])
                )
                if isinstance(hook_coverage.get("missing_authority_case_ids"), list)
                else 0,
                "replay_episode_count": (replay_gauntlet.get("coverage_summary") or {}).get(
                    "episode_count"
                )
                if isinstance(replay_gauntlet.get("coverage_summary"), dict)
                else 0,
                "replay_blocked_episode_count": (
                    replay_gauntlet.get("coverage_summary") or {}
                ).get("blocked_episode_count")
                if isinstance(replay_gauntlet.get("coverage_summary"), dict)
                else 0,
                "benchmark_task_count": (benchmark_lab.get("scorecard") or {}).get(
                    "task_count"
                )
                if isinstance(benchmark_lab.get("scorecard"), dict)
                else 0,
                "benchmark_oracle_patch_count": (benchmark_lab.get("scorecard") or {}).get(
                    "oracle_patch_count"
                )
                if isinstance(benchmark_lab.get("scorecard"), dict)
                else 0,
                "legibility_checkpoint_count": (
                    legibility_scorecard.get("scorecard") or {}
                ).get("checkpoint_count")
                if isinstance(legibility_scorecard.get("scorecard"), dict)
                else 0,
                "legibility_reader_question_count": (
                    legibility_scorecard.get("scorecard") or {}
                ).get("reader_question_count")
                if isinstance(legibility_scorecard.get("scorecard"), dict)
                else 0,
                "projection_cell_count": intake.get("projection_cell_count"),
                "reveal_step_count": reveal.get("step_count"),
            },
            "evidence_refs": evidence_refs,
            "safe_to_show": {
                "body_in_receipt": False,
                "receipt_refs_only_until_drilldown": True,
                "secret_or_account_bound_material_excluded": True,
                "real_substrate_receipts_required": True,
                "synthetic_receipts_are_not_product_evidence": True,
                "proof_bodies_omitted": True,
            },
            "authority_ceiling": {
                "release_authorized": False,
                "hosted_public_authorized": False,
                "publication_authorized": False,
                "provider_calls_authorized": False,
                "source_mutation_authorized": False,
                "private_data_equivalence_claim": False,
                "formal_math_general_proof_authority": False,
                "trading_or_financial_advice_authorized": False,
                "whole_system_correctness_claim": False,
            },
            "release_authorized": False,
            "body_in_receipt": False,
            "anti_claim": (
                "The ten-minute tour is a local source-open runtime route and receipt "
                "index. It treats synthetic receipts as scaffolding only and does not "
                "authorize release, hosted publication, provider calls, source mutation, "
                "credential/session export, proof correctness, trading or financial "
                "advice, or whole-system correctness claims."
            ),
        }
        if persist_receipt:
            write_json_atomic(tour_path, payload)
        return payload

    def trace_lens(self) -> dict[str, Any]:
        readiness_ref = (
            "receipts/first_wave/formal_math_readiness_gate/"
            "formal_math_readiness_extension_board.json"
        )
        premise_ref = (
            "receipts/first_wave/formal_math_premise_retrieval/"
            "formal_math_premise_retrieval_result.json"
        )
        tactic_ref = (
            "receipts/first_wave/tactic_portfolio_availability_probe/"
            "tactic_portfolio_availability_result.json"
        )
        target_shape_ref = (
            "receipts/first_wave/target_shape_tactic_routing_gate/"
            "target_shape_tactic_routing_result.json"
        )
        witness_ref = (
            "receipts/first_wave/formal_math_lean_proof_witness/"
            "formal_math_lean_proof_witness_result.json"
        )
        readiness = _read_json_if_exists(self.root / readiness_ref)
        premise = _read_json_if_exists(self.root / premise_ref)
        tactic = _read_json_if_exists(self.root / tactic_ref)
        target_shape = _read_json_if_exists(self.root / target_shape_ref)
        witness = _read_json_if_exists(self.root / witness_ref)
        lens_path = self.runtime_receipt_dir / "public_verifier_trace_repair_lens.json"

        source_pattern_ids = list(
            dict.fromkeys(
                [
                    *_strings(premise.get("source_pattern_ids")),
                    *_strings(tactic.get("source_pattern_ids")),
                    *_strings(target_shape.get("source_pattern_ids")),
                    *_strings(witness.get("source_pattern_ids")),
                    "formal_math_verifier_trace_repair_loop",
                ]
            )
        )
        def negative_keys(payload: dict[str, Any]) -> list[str]:
            value = payload.get("observed_negative_cases")
            if isinstance(value, dict):
                return sorted(str(key) for key in value)
            return _strings(value)

        source_negative_case_ids = sorted(
            set(
                [
                    *negative_keys(readiness),
                    *negative_keys(premise),
                    *negative_keys(tactic),
                    *negative_keys(target_shape),
                    *negative_keys(witness),
                ]
            )
        )
        negative_case_ids = [
            "proof_body_leakage",
            "oracle_needed_premise_id_public",
            "trace_grade_without_trace",
            "repair_without_verifier_class",
            "promotion_without_cold_rerun",
            "provider_payload_leakage",
            "human_approval_as_proof_correctness",
        ]
        trace_rows = [
            {
                "attempt_id": "attempt_a_missing_premise",
                "public_input_hash": "redacted_hash:attempt_a",
                "verifier_failure_class": "MISSING_PREMISE",
                "trace_grade": "repairable_metadata_only",
                "repair_action": "route_to_premise_retrieval_terms",
                "repair_evidence_ref": premise_ref,
                "cold_rerun_required_before_promotion": True,
                "promotion_allowed": False,
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
                "body_redacted": True,
            },
            {
                "attempt_id": "attempt_b_unavailable_tactic",
                "public_input_hash": "redacted_hash:attempt_b",
                "verifier_failure_class": "TACTIC_UNAVAILABLE",
                "trace_grade": "repairable_metadata_only",
                "repair_action": "route_to_tactic_availability_probe",
                "repair_evidence_ref": tactic_ref,
                "cold_rerun_required_before_promotion": True,
                "promotion_allowed": False,
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
                "body_redacted": True,
            },
            {
                "attempt_id": "attempt_c_invalid_proof_body",
                "public_input_hash": "redacted_hash:attempt_c",
                "verifier_failure_class": "INVALID_PROOF_BODY",
                "trace_grade": "blocked_public",
                "repair_action": "reject_public_proof_body_and_keep_metadata_only",
                "repair_evidence_ref": witness_ref,
                "cold_rerun_required_before_promotion": True,
                "promotion_allowed": False,
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
                "body_redacted": True,
            },
            {
                "attempt_id": "cold_rerun_after_repair",
                "public_input_hash": "redacted_hash:cold_rerun",
                "verifier_failure_class": "NONE_AFTER_METADATA_REPAIR",
                "trace_grade": "validated_metadata_only",
                "repair_action": "append_failure_mode_ledger_delta_and_update_curriculum_gate",
                "repair_evidence_ref": target_shape_ref,
                "cold_rerun_required_before_promotion": False,
                "promotion_allowed": True,
                "promotion_authority": "metadata_trace_cell_only_not_proof_correctness",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
                "body_redacted": True,
            },
        ]
        authority_ceiling = {
            "metadata_trace_only": True,
            "formal_proof_authority": False,
            "proof_correctness_claim": False,
            "lean_lake_execution_authorized": False,
            "mathlib_dependent_proof_authority": False,
            "provider_calls_authorized": False,
            "human_approval_is_proof_authority": False,
            "proof_bodies_exported": False,
            "oracle_needed_premise_ids_exported": False,
            "private_data_equivalence_claim": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
        }
        source_statuses = {
            "readiness": readiness.get("status"),
            "premise_retrieval": premise.get("status"),
            "tactic_availability": tactic.get("status"),
            "target_shape_routing": target_shape.get("status"),
            "lean_proof_witness": witness.get("status"),
        }
        status = (
            PASS
            if all(value == PASS for value in source_statuses.values())
            and len(trace_rows) == 4
            and len(negative_case_ids) == 7
            and all(row.get("proof_body_exported") is False for row in trace_rows)
            and authority_ceiling["formal_proof_authority"] is False
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_verifier_trace_repair_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_verifier_trace_repair_lens",
            "organ_family": "formal_math",
            "command": "microcosm trace-lens",
            "endpoint": "/trace",
            "trace_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a public verifier trace-repair read-model: failure "
                "classes, trace grades, repair routing, negative cases, and cold-rerun "
                "promotion gates without proof bodies, oracle premise identifiers, "
                "provider payloads, or proof-correctness claims."
            ),
            "input_refs": {
                "readiness_extension_board": readiness_ref,
                "premise_retrieval_result": premise_ref,
                "tactic_availability_result": tactic_ref,
                "target_shape_routing_result": target_shape_ref,
                "lean_proof_witness_result": witness_ref,
            },
            "source_statuses": source_statuses,
            "source_pattern_ids": source_pattern_ids,
            "source_pattern_count": len(source_pattern_ids),
            "observed_source_negative_case_ids": source_negative_case_ids,
            "trace_rows": trace_rows,
            "repair_policy": {
                "verifier_feedback_is_teaching_signal_not_result": True,
                "trace_grade_required_before_repair_promotion": True,
                "verifier_failure_class_required_before_repair": True,
                "cold_rerun_required_before_promotion": True,
                "failure_mode_ledger_updates_curriculum_only_after_cold_rerun": True,
                "human_or_provider_advice_is_advisory_not_proof_authority": True,
                "proof_bodies_and_oracle_ids_are_redacted": True,
            },
            "repair_summary": {
                "attempt_count": len(trace_rows),
                "repairable_attempt_count": 2,
                "blocked_attempt_count": 1,
                "cold_rerun_trace_count": 1,
                "promotion_allowed_count": 1,
                "proof_body_export_count": 0,
                "oracle_needed_premise_export_count": 0,
            },
            "negative_case_ids": negative_case_ids,
            "evidence_refs": [
                readiness_ref,
                premise_ref,
                tactic_ref,
                target_shape_ref,
                witness_ref,
            ],
            "safe_to_show": {
                "body_redacted": True,
                "proof_bodies_omitted": True,
                "oracle_needed_premise_ids_omitted": True,
                "provider_payloads_omitted": True,
                "receipt_refs_only": True,
                "fixture_metadata_only": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The verifier trace-repair lens is a metadata-only public read-model. It "
                "does not run Lean/Lake, prove theorem correctness, expose proof bodies "
                "or oracle-needed premise identifiers, call providers, treat human "
                "approval as proof authority, mutate source, claim secret export, "
                "or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def repair_loop(self) -> dict[str, Any]:
        trace_lens = self.trace_lens()
        lens_path = self.runtime_receipt_dir / "public_verifier_repair_loop_lens.json"
        trace_rows = _rows(trace_lens, "trace_rows")
        negative_case_ids = [
            "repair_action_without_failure_class",
            "cold_rerun_missing_after_repair",
            "curriculum_promotion_without_trace_grade",
            "proof_body_or_oracle_id_exported",
            "provider_payload_as_evidence",
            "human_approval_as_proof",
            "source_mutation_as_repair",
            "release_claim_after_repair",
        ]
        loop_stages = [
            {
                "stage_id": "capture_verifier_failure",
                "input_contract": "redacted_trace_metadata_only",
                "exit_gate": "failure_class_present",
                "promotion_allowed": False,
            },
            {
                "stage_id": "classify_failure",
                "input_contract": "failure_class_and_trace_grade",
                "exit_gate": "repair_route_selected",
                "promotion_allowed": False,
            },
            {
                "stage_id": "route_repair",
                "input_contract": "receipt_backed_repair_action",
                "exit_gate": "repair_evidence_ref_bound",
                "promotion_allowed": False,
            },
            {
                "stage_id": "cold_rerun",
                "input_contract": "repair_applied_to_metadata_fixture",
                "exit_gate": "cold_rerun_trace_recorded",
                "promotion_allowed": False,
            },
            {
                "stage_id": "promote_metadata_cell",
                "input_contract": "validated_metadata_only_trace",
                "exit_gate": "curriculum_delta_is_receipt_backed",
                "promotion_allowed": True,
                "promotion_authority": "metadata_curriculum_only_not_proof_correctness",
            },
        ]
        transition_rows: list[dict[str, Any]] = []
        for row in trace_rows:
            failure_class = row.get("verifier_failure_class")
            action = row.get("repair_action")
            transition_rows.append(
                {
                    "attempt_id": row.get("attempt_id"),
                    "from_stage": "capture_verifier_failure"
                    if failure_class != "NONE_AFTER_METADATA_REPAIR"
                    else "cold_rerun",
                    "failure_class": failure_class,
                    "trace_grade": row.get("trace_grade"),
                    "repair_action": action,
                    "repair_evidence_ref": row.get("repair_evidence_ref"),
                    "to_stage": "promote_metadata_cell"
                    if row.get("promotion_allowed") is True
                    else "route_repair",
                    "promotion_allowed": row.get("promotion_allowed") is True,
                    "cold_rerun_required_before_promotion": row.get(
                        "cold_rerun_required_before_promotion"
                    )
                    is True,
                    "proof_body_exported": row.get("proof_body_exported") is True,
                    "oracle_needed_premise_ids_exported": row.get(
                        "oracle_needed_premise_ids_exported"
                    )
                    is True,
                    "body_redacted": row.get("body_redacted") is True,
                }
            )
        repairable_transition_count = sum(
            1
            for row in transition_rows
            if row.get("promotion_allowed") is False
            and row.get("failure_class") in {"MISSING_PREMISE", "TACTIC_UNAVAILABLE"}
        )
        promoted_transition_count = sum(
            1 for row in transition_rows if row.get("promotion_allowed") is True
        )
        authority_ceiling = {
            "metadata_curriculum_only": True,
            "formal_proof_authority": False,
            "proof_correctness_claim": False,
            "lean_lake_execution_authorized": False,
            "proof_bodies_exported": False,
            "oracle_needed_premise_ids_exported": False,
            "provider_calls_authorized": False,
            "human_approval_is_proof_authority": False,
            "source_mutation_authorized": False,
            "private_data_equivalence_claim": False,
            "release_authorized": False,
        }
        status = (
            PASS
            if trace_lens.get("status") == PASS
            and len(loop_stages) == 5
            and len(transition_rows) == 4
            and repairable_transition_count == 2
            and promoted_transition_count == 1
            and len(negative_case_ids) == 8
            and all(row.get("proof_body_exported") is False for row in transition_rows)
            and all(
                row.get("oracle_needed_premise_ids_exported") is False
                for row in transition_rows
            )
            and authority_ceiling["formal_proof_authority"] is False
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_verifier_repair_loop_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_verifier_repair_loop_lens",
            "organ_family": "formal_math",
            "command": "microcosm repair-loop",
            "endpoint": "/repair-loop",
            "repair_loop_ref": _public_relative(lens_path, self.root),
            "source_lens_ref": trace_lens.get("trace_lens_ref"),
            "selected_pattern_id": "formal_math_verifier_trace_repair_loop_compound",
            "public_claim": (
                "Microcosm exposes a public verifier repair-loop curriculum: classify "
                "failed proof attempts, route metadata-only repairs, require cold reruns, "
                "and promote only receipt-backed curriculum cells without exporting proof "
                "bodies, oracle-needed premise identifiers, provider payloads, or proof "
                "correctness claims."
            ),
            "loop_stages": loop_stages,
            "transition_rows": transition_rows,
            "curriculum_policy": {
                "failure_class_required_before_repair_route": True,
                "trace_grade_required_before_curriculum_delta": True,
                "repair_evidence_ref_required": True,
                "cold_rerun_required_before_promotion": True,
                "promotion_scope": "metadata_curriculum_cell_only",
                "proof_body_or_oracle_id_is_never_curriculum_material": True,
            },
            "repair_loop_summary": {
                "stage_count": len(loop_stages),
                "transition_count": len(transition_rows),
                "repairable_transition_count": repairable_transition_count,
                "blocked_transition_count": sum(
                    1
                    for row in transition_rows
                    if row.get("failure_class") == "INVALID_PROOF_BODY"
                ),
                "promoted_transition_count": promoted_transition_count,
                "proof_body_export_count": sum(
                    1 for row in transition_rows if row.get("proof_body_exported") is True
                ),
                "oracle_needed_premise_export_count": sum(
                    1
                    for row in transition_rows
                    if row.get("oracle_needed_premise_ids_exported") is True
                ),
            },
            "negative_case_ids": negative_case_ids,
            "evidence_refs": list(
                dict.fromkeys(
                    [
                        str(ref)
                        for ref in [
                            trace_lens.get("trace_lens_ref"),
                            *[
                                row.get("repair_evidence_ref")
                                for row in transition_rows
                                if isinstance(row.get("repair_evidence_ref"), str)
                            ],
                        ]
                        if isinstance(ref, str) and ref
                    ]
                )
            ),
            "safe_to_show": {
                "body_redacted": True,
                "proof_bodies_omitted": True,
                "oracle_needed_premise_ids_omitted": True,
                "provider_payloads_omitted": True,
                "receipt_refs_only": True,
                "fixture_metadata_only": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The verifier repair-loop lens is a metadata-only curriculum read-model. "
                "It does not run Lean/Lake, prove theorem correctness, expose proof "
                "bodies or oracle-needed premise identifiers, call providers, treat human "
                "approval as proof authority, mutate source, claim secret export, "
                "or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def evidence_cells(self) -> dict[str, Any]:
        witness_ref = (
            "receipts/first_wave/formal_math_lean_proof_witness/"
            "formal_math_lean_proof_witness_result.json"
        )
        readiness_ref = (
            "receipts/first_wave/formal_math_readiness_gate/"
            "formal_math_readiness_extension_board.json"
        )
        trace_lens = self.trace_lens()
        witness = _read_json_if_exists(self.root / witness_ref)
        readiness = _read_json_if_exists(self.root / readiness_ref)
        lens_path = self.runtime_receipt_dir / "public_formal_evidence_cell_lens.json"

        trace_ref = trace_lens.get("trace_lens_ref")
        if not isinstance(trace_ref, str):
            trace_ref = "receipts/runtime_shell/public_verifier_trace_repair_lens.json"

        evidence_cells = [
            {
                "cell_id": "cell.public_toy_bool_and_comm_witness",
                "claim_language": "toy Lean/Std witness available",
                "claim_strength": "machine_checked_toy_witness_metadata",
                "resolver_status": "formal_evidence_cell_present",
                "evidence_ref": witness_ref,
                "source_pattern_id": "formal_math_lean_proof_witness",
                "proof_body_exported": False,
                "private_source_ref_exported": False,
                "claim_may_say_no_sorry": True,
                "claim_may_say_general_theorem_solution": False,
            },
            {
                "cell_id": "cell.verifier_trace_repair_metadata",
                "claim_language": "verifier trace repair gate is inspectable",
                "claim_strength": "metadata_trace_cell_only",
                "resolver_status": "formal_evidence_cell_present",
                "evidence_ref": trace_ref,
                "source_pattern_id": "formal_math_verifier_trace_repair_loop",
                "proof_body_exported": False,
                "private_source_ref_exported": False,
                "claim_may_say_no_sorry": False,
                "claim_may_say_general_theorem_solution": False,
            },
            {
                "cell_id": "cell.unknown_erdos257_solution_claim",
                "claim_language": "Erdos 257 solved",
                "claim_strength": "rejected_overclaim_unknown_cell",
                "resolver_status": "unknown_cell_rejected",
                "evidence_ref": None,
                "source_pattern_id": "formal_evidence_cell_anchor_resolver",
                "proof_body_exported": False,
                "private_source_ref_exported": False,
                "claim_may_say_no_sorry": False,
                "claim_may_say_general_theorem_solution": False,
            },
            {
                "cell_id": "cell.missing_source_anchor",
                "claim_language": "formal evidence cell exists but source anchor is missing",
                "claim_strength": "rejected_missing_source",
                "resolver_status": "missing_source_rejected",
                "evidence_ref": None,
                "source_pattern_id": "formal_evidence_cell_anchor_resolver",
                "proof_body_exported": False,
                "private_source_ref_exported": False,
                "claim_may_say_no_sorry": False,
                "claim_may_say_general_theorem_solution": False,
            },
        ]
        negative_case_ids = [
            "unknown_cell_id_claim",
            "missing_source_cell",
            "no_sorry_without_cell",
            "cell_claims_general_theorem_proof",
            "proof_body_embedded_in_cell",
            "private_source_ref",
            "release_overclaim",
        ]
        authority_ceiling = {
            "metadata_cell_index_only": True,
            "formal_proof_authority": False,
            "proof_correctness_claim": False,
            "general_theorem_solution_claim": False,
            "lean_lake_execution_authorized": False,
            "mathlib_dependent_proof_authority": False,
            "proof_bodies_exported": False,
            "private_source_refs_exported": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
        }
        source_statuses = {
            "formal_math_lean_proof_witness": witness.get("status"),
            "formal_math_readiness_gate": readiness.get("status"),
            "verifier_trace_repair_lens": trace_lens.get("status"),
        }
        status = (
            PASS
            if source_statuses["formal_math_lean_proof_witness"] == PASS
            and source_statuses["verifier_trace_repair_lens"] == PASS
            and len(evidence_cells) == 4
            and len(negative_case_ids) == 7
            and all(row.get("proof_body_exported") is False for row in evidence_cells)
            and authority_ceiling["formal_proof_authority"] is False
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_formal_evidence_cell_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_formal_evidence_cell_lens",
            "organ_family": "formal_math",
            "command": "microcosm evidence-cells",
            "endpoint": "/evidence-cells",
            "evidence_cell_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a public formal evidence-cell lens: proof-strength "
                "language must resolve to an explicit cell id and receipt ref, while "
                "unknown cells, missing sources, proof bodies, private refs, and "
                "general theorem-solution claims stay rejected."
            ),
            "selected_pattern_id": "formal_evidence_cell_anchor_resolver",
            "input_refs": {
                "formal_math_lean_proof_witness_result": witness_ref,
                "formal_math_readiness_extension_board": readiness_ref,
                "verifier_trace_repair_lens": trace_ref,
            },
            "source_statuses": source_statuses,
            "evidence_cells": evidence_cells,
            "resolver_policy": {
                "claim_strength_requires_cell_id": True,
                "no_sorry_language_requires_present_cell": True,
                "unknown_cell_keeps_claim_weak_or_rejected": True,
                "missing_source_cell_errors": True,
                "receipt_ref_required_for_positive_cell": True,
                "proof_bodies_and_private_refs_are_redacted": True,
                "cell_id_is_receipt_anchor_not_theorem_proof": True,
            },
            "resolver_summary": {
                "cell_count": len(evidence_cells),
                "present_cell_count": sum(
                    1 for row in evidence_cells if row.get("resolver_status") == "formal_evidence_cell_present"
                ),
                "rejected_cell_count": sum(
                    1 for row in evidence_cells if str(row.get("resolver_status", "")).endswith("_rejected")
                ),
                "positive_cell_with_receipt_ref_count": sum(
                    1
                    for row in evidence_cells
                    if row.get("resolver_status") == "formal_evidence_cell_present" and row.get("evidence_ref")
                ),
                "proof_body_export_count": 0,
                "private_source_ref_export_count": 0,
            },
            "negative_case_ids": negative_case_ids,
            "evidence_refs": [
                ref
                for ref in [witness_ref, readiness_ref, trace_ref]
                if isinstance(ref, str) and ref
            ],
            "safe_to_show": {
                "body_redacted": True,
                "proof_bodies_omitted": True,
                "private_source_refs_omitted": True,
                "receipt_refs_only": True,
                "fixture_metadata_only": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The formal evidence-cell lens is a metadata resolver and claim-boundary "
                "read-model. It does not run Lean/Lake, prove theorem correctness, expose "
                "proof bodies, export private source refs, call providers, mutate source, "
                "claim a general mathematical solution, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def proof_loop_depth(self) -> dict[str, Any]:
        corpus_lens = self.corpus_lens()
        trace_lens = self.trace_lens()
        repair_loop = self.repair_loop()
        evidence_cells = self.evidence_cells()
        readiness_ref = (
            "receipts/first_wave/formal_math_readiness_gate/"
            "formal_math_readiness_extension_board.json"
        )
        lean_std_ref = (
            "receipts/first_wave/lean_std_premise_index/"
            "lean_std_premise_index_result.json"
        )
        premise_ref = (
            "receipts/first_wave/formal_math_premise_retrieval/"
            "formal_math_premise_retrieval_result.json"
        )
        ring2_ref = (
            "receipts/first_wave/ring2_premise_retrieval_precision_recall_harness/"
            "ring2_precision_recall_result.json"
        )
        tactic_ref = (
            "receipts/first_wave/tactic_portfolio_availability_probe/"
            "tactic_portfolio_availability_result.json"
        )
        target_shape_ref = (
            "receipts/first_wave/target_shape_tactic_routing_gate/"
            "target_shape_tactic_routing_result.json"
        )
        witness_ref = (
            "receipts/first_wave/formal_math_lean_proof_witness/"
            "formal_math_lean_proof_witness_result.json"
        )
        readiness = _read_json_if_exists(self.root / readiness_ref)
        lean_std = _read_json_if_exists(self.root / lean_std_ref)
        premise = _read_json_if_exists(self.root / premise_ref)
        ring2 = _read_json_if_exists(self.root / ring2_ref)
        tactic = _read_json_if_exists(self.root / tactic_ref)
        target_shape = _read_json_if_exists(self.root / target_shape_ref)
        witness = _read_json_if_exists(self.root / witness_ref)
        lens_path = self.runtime_receipt_dir / "public_proof_loop_depth_lens.json"

        gate_rows = [
            {
                "gate_id": "corpus_readiness_boundary",
                "loop_depth": 1,
                "role": "prove the environment boundary before any proof-adjacent claim",
                "evidence_ref": corpus_lens.get("corpus_lens_ref"),
                "source_status": corpus_lens.get("status"),
                "public_signal": "mathlib absence and corpus readiness are explicit metadata",
                "promotion_scope": "environment_metadata_only",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
            {
                "gate_id": "formal_math_readiness_gate",
                "loop_depth": 2,
                "role": "separate readiness extension cells from proof correctness",
                "evidence_ref": readiness_ref,
                "source_status": readiness.get("status"),
                "public_signal": "formal-math cells are routed through readiness receipts",
                "promotion_scope": "readiness_metadata_only",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
            {
                "gate_id": "lean_std_premise_index",
                "loop_depth": 3,
                "role": "bind retrieval to a closed public premise index",
                "evidence_ref": lean_std_ref,
                "source_status": lean_std.get("status"),
                "public_signal": "sanctioned Std premise rows are explicit and bounded",
                "promotion_scope": "premise_index_metadata_only",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
            {
                "gate_id": "premise_retrieval",
                "loop_depth": 4,
                "role": "turn missing-premise feedback into public retrieval terms",
                "evidence_ref": premise_ref,
                "source_status": premise.get("status"),
                "public_signal": "retrieval terms are visible without oracle-needed ids",
                "promotion_scope": "retrieval_metadata_only",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
            {
                "gate_id": "ring2_precision_recall_harness",
                "loop_depth": 5,
                "role": "grade retrieval fixture behavior before generalizing the loop",
                "evidence_ref": ring2_ref,
                "source_status": ring2.get("status"),
                "public_signal": "precision/recall harness is a toy fixture, not a benchmark claim",
                "promotion_scope": "fixture_metric_metadata_only",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
            {
                "gate_id": "tactic_availability_probe",
                "loop_depth": 6,
                "role": "probe tactic availability instead of assuming it",
                "evidence_ref": tactic_ref,
                "source_status": tactic.get("status"),
                "public_signal": "unavailable tactic failures route through a typed probe",
                "promotion_scope": "tactic_environment_metadata_only",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
            {
                "gate_id": "target_shape_routing",
                "loop_depth": 7,
                "role": "route target-shape features before choosing repair actions",
                "evidence_ref": target_shape_ref,
                "source_status": target_shape.get("status"),
                "public_signal": "repair routes are selected from typed target shapes",
                "promotion_scope": "route_metadata_only",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
            {
                "gate_id": "verifier_trace_repair_lens",
                "loop_depth": 8,
                "role": "classify verifier failures and trace grades before repair promotion",
                "evidence_ref": trace_lens.get("trace_lens_ref"),
                "source_status": trace_lens.get("status"),
                "public_signal": "failed attempts are public metadata rows, not proofs",
                "promotion_scope": "trace_metadata_only",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
            {
                "gate_id": "repair_loop_cold_rerun",
                "loop_depth": 9,
                "role": "require a cold rerun before promoting a repair into curriculum",
                "evidence_ref": repair_loop.get("repair_loop_ref"),
                "source_status": repair_loop.get("status"),
                "public_signal": "promotion is limited to a metadata curriculum cell",
                "promotion_scope": "curriculum_metadata_only",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
            {
                "gate_id": "formal_evidence_cell_resolver",
                "loop_depth": 10,
                "role": "force proof language to resolve to explicit evidence cells",
                "evidence_ref": evidence_cells.get("evidence_cell_lens_ref"),
                "source_status": evidence_cells.get("status"),
                "public_signal": "unknown cells and missing sources stay rejected",
                "promotion_scope": "evidence_cell_metadata_only",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
            {
                "gate_id": "lean_witness_boundary",
                "loop_depth": 11,
                "role": "keep the positive machine anchor tiny and public",
                "evidence_ref": witness_ref,
                "source_status": witness.get("status"),
                "public_signal": "toy Lean/Std witness exists without a general theorem claim",
                "promotion_scope": "toy_witness_metadata_only",
                "proof_body_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
        ]
        negative_case_ids = [
            "proof_body_exported_as_depth_evidence",
            "oracle_needed_premise_ids_exported",
            "provider_payload_used_as_verifier_evidence",
            "human_approval_used_as_proof_correctness",
            "mathlib_available_without_probe",
            "ring2_fixture_metric_reported_as_benchmark_score",
            "evidence_cell_claims_general_theorem_solution",
            "cold_rerun_missing_before_curriculum_promotion",
            "release_or_publication_claim_from_proof_loop_depth",
        ]
        authority_ceiling = {
            "metadata_loop_only": True,
            "formal_proof_authority": False,
            "proof_correctness_claim": False,
            "general_theorem_solution_claim": False,
            "mathlib_availability_claim": False,
            "benchmark_score_claim": False,
            "lean_lake_execution_authorized": False,
            "proof_bodies_exported": False,
            "oracle_needed_premise_ids_exported": False,
            "provider_calls_authorized": False,
            "human_approval_is_proof_authority": False,
            "source_mutation_authorized": False,
            "private_data_equivalence_claim": False,
            "release_authorized": False,
        }
        source_statuses = {
            row["gate_id"]: row.get("source_status") for row in gate_rows
        }
        evidence_refs = [
            ref
            for ref in dict.fromkeys(
                str(row.get("evidence_ref"))
                for row in gate_rows
                if isinstance(row.get("evidence_ref"), str) and row.get("evidence_ref")
            )
        ]
        status = (
            PASS
            if len(gate_rows) == 11
            and len(negative_case_ids) == 9
            and all(row.get("source_status") == PASS for row in gate_rows)
            and all(row.get("proof_body_exported") is False for row in gate_rows)
            and all(
                row.get("oracle_needed_premise_ids_exported") is False
                for row in gate_rows
            )
            and authority_ceiling["formal_proof_authority"] is False
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_proof_loop_depth_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_proof_loop_depth_lens",
            "organ_family": "formal_math",
            "command": "microcosm proof-loop-depth",
            "endpoint": "/proof-loop-depth",
            "proof_loop_depth_ref": _public_relative(lens_path, self.root),
            "selected_pattern_ids": [
                "formal_math_verifier_trace_repair_loop_compound",
                "corpus_readiness_mathlib_absence_gate",
                "lean_std_toolchain_premise_index",
                "ring2_premise_retrieval_precision_recall_harness",
                "formal_evidence_cell_anchor_resolver",
            ],
            "public_claim": (
                "Microcosm exposes a proof-loop depth map: environment readiness, "
                "premise indexing, retrieval, tactic availability, target-shape "
                "routing, verifier trace, cold-rerun repair promotion, evidence-cell "
                "resolution, and tiny Lean witness boundaries are one inspectable "
                "metadata loop instead of a proof or benchmark claim."
            ),
            "source_statuses": source_statuses,
            "gate_rows": gate_rows,
            "loop_policy": {
                "environment_boundary_before_proof_language": True,
                "closed_premise_index_before_retrieval": True,
                "retrieval_and_tactic_failures_are_teaching_signal": True,
                "target_shape_route_before_repair": True,
                "trace_grade_required_before_repair_promotion": True,
                "cold_rerun_required_before_curriculum_delta": True,
                "evidence_cell_required_for_stronger_claim_language": True,
                "toy_witness_is_not_general_theorem_solution": True,
            },
            "proof_loop_summary": {
                "gate_count": len(gate_rows),
                "formal_math_gate_count": len(gate_rows),
                "evidence_ref_count": len(evidence_refs),
                "negative_case_count": len(negative_case_ids),
                "proof_body_export_count": 0,
                "oracle_needed_premise_export_count": 0,
                "provider_payload_export_count": 0,
                "benchmark_score_claim_count": 0,
                "general_theorem_solution_claim_count": 0,
            },
            "negative_case_ids": negative_case_ids,
            "evidence_refs": evidence_refs,
            "safe_to_show": {
                "body_redacted": True,
                "proof_bodies_omitted": True,
                "oracle_needed_premise_ids_omitted": True,
                "provider_payloads_omitted": True,
                "receipt_refs_only": True,
                "fixture_metadata_only": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The proof-loop depth lens is a metadata-only map over public formal "
                "math fixtures and runtime lenses. It does not run Lean/Lake, prove "
                "theorem correctness, export proof bodies or oracle-needed premise "
                "identifiers, call providers, treat human approval as proof authority, "
                "claim benchmark performance or a general theorem solution, mutate "
                "source, claim secret export, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def landing_replay(self) -> dict[str, Any]:
        attempt_ref = "receipts/first_wave/mission_transaction_work_spine/work_landing_attempt.json"
        mutation_ref = "receipts/first_wave/mission_transaction_work_spine/scoped_mutation_receipt.json"
        reconcile_ref = (
            "receipts/first_wave/mission_transaction_work_spine/"
            "work_landing_reconcile_plan.json"
        )
        closeout_ref = (
            "receipts/first_wave/mission_transaction_work_spine/"
            "closeout_status_projection.json"
        )
        checkpoint_ref = (
            "receipts/first_wave/mission_transaction_work_spine/"
            "checkpoint_lane_decision.json"
        )
        dependency_ref = "receipts/first_wave/mission_transaction_work_spine/dependency_blocked.json"
        lens_path = self.runtime_receipt_dir / "public_work_landing_replay_lens.json"

        attempt = _read_json_if_exists(self.root / attempt_ref)
        mutation = _read_json_if_exists(self.root / mutation_ref)
        reconcile = _read_json_if_exists(self.root / reconcile_ref)
        closeout = _read_json_if_exists(self.root / closeout_ref)
        checkpoint = _read_json_if_exists(self.root / checkpoint_ref)
        dependency = _read_json_if_exists(self.root / dependency_ref)
        source_statuses = {
            "work_landing_attempt": attempt.get("status"),
            "scoped_mutation_receipt": mutation.get("status"),
            "work_landing_reconcile_plan": reconcile.get("status"),
            "closeout_status_projection": closeout.get("status"),
            "checkpoint_lane_decision": checkpoint.get("status"),
            "dependency_blocked": dependency.get("status"),
        }
        lane_decision_table = [
            {
                "lane_id": "scoped_commit",
                "role": "default durable landing lane when owned paths are isolated",
                "requires": [
                    "owned path claims",
                    "owner-native validation",
                    "clean staged index",
                    "HEAD compare-and-swap",
                ],
                "allowed_without_operator_authorization": True,
                "stages_unrelated_dirty_paths": False,
                "release_authorized": False,
                "replay_command": (
                    "scoped_commit.py full-paths --expected-parent <head> "
                    "--path <owned-path>..."
                ),
            },
            {
                "lane_id": "broad_checkpoint",
                "role": "bankruptcy lane for explicit operator save-everything requests",
                "requires": [
                    "explicit operator authorization",
                    "quick safety checks",
                    "private-root trust envelope",
                ],
                "allowed_without_operator_authorization": False,
                "stages_unrelated_dirty_paths": "only_after_operator_authorization",
                "release_authorized": False,
                "replay_command": "./checkpoint \"<operator-authorized message>\"",
            },
            {
                "lane_id": "metadata_blocked_patch_bundle",
                "role": "validated recovery lane when worktree writes pass but Git metadata writes fail",
                "requires": [
                    "validation transcript",
                    "Task Ledger blocker capture",
                    "Work Ledger progress or append-exempt finalizer",
                    "seed reentry update",
                ],
                "allowed_without_operator_authorization": True,
                "stages_unrelated_dirty_paths": False,
                "release_authorized": False,
                "replay_command": "rerun scoped_commit.py when Git metadata authority is restored",
            },
            {
                "lane_id": "hard_stop",
                "role": "required when secrets, destructive deletion, identity corruption, or private leakage appear",
                "requires": [
                    "stop mutation",
                    "capture blocker",
                    "preserve unrelated user changes",
                ],
                "allowed_without_operator_authorization": True,
                "stages_unrelated_dirty_paths": False,
                "release_authorized": False,
                "replay_command": "do not stage or commit until blocker is resolved",
            },
        ]
        replay_events = [
            {
                "event_id": "claim_owned_paths",
                "status": "required_before_mutation",
                "public_evidence_ref": "tools/meta/factory/work_ledger.py session-preflight",
                "source_body_exported": False,
            },
            {
                "event_id": "validate_owner_native",
                "status": "required_before_commit_attempt_and_closeout",
                "public_evidence_ref": "microcosm focused tests and validators",
                "source_body_exported": False,
            },
            {
                "event_id": "validation_before_commit_attempt",
                "status": "required_before_landed_commit_language",
                "public_evidence_ref": (
                    "durable_agent_work_landing_replay::"
                    "validation_after_commit_attempt"
                ),
                "source_body_exported": False,
            },
            {
                "event_id": "git_metadata_blocker_capture",
                "status": "public_safe_blocker_ref_available",
                "public_evidence_ref": "wie_20260521T195941Z_cf83fa74",
                "source_body_exported": False,
            },
            {
                "event_id": "append_exempt_or_progress_finalizer",
                "status": "required_when_commit_does_not_land",
                "public_evidence_ref": "codex_microcosm_wave_032",
                "source_body_exported": False,
            },
        ]
        negative_case_ids = [
            "broad_checkpoint_without_operator_authorization",
            "commit_claim_without_head_advance",
            "unrelated_dirty_paths_staged_by_scoped_lane",
            "commit_attempt_before_owner_native_validation",
            "blocker_reported_without_task_ledger_capture",
            "validation_omitted_before_closeout",
            "private_source_body_exported",
            "release_claim_from_local_receipt",
        ]
        authority_ceiling = {
            "metadata_replay_only": True,
            "live_git_mutation_authorized": False,
            "broad_checkpoint_authorized": False,
            "unrelated_dirty_paths_authorized": False,
            "source_mutation_authorized": False,
            "private_source_bodies_exported": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "hosted_public_authorized": False,
        }
        status = (
            PASS
            if len(lane_decision_table) == 4
            and len(replay_events) == 5
            and len(negative_case_ids) == 8
            and authority_ceiling["live_git_mutation_authorized"] is False
            and authority_ceiling["broad_checkpoint_authorized"] is False
            and authority_ceiling["source_mutation_authorized"] is False
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_work_landing_replay_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_work_landing_replay_lens",
            "organ_family": "work_spine",
            "command": "microcosm landing-replay",
            "endpoint": "/landing-replay",
            "landing_replay_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a public work-landing replay lens: dirty-tree work "
                "lands through owned-path claims, validation, scoped commit attempts, "
                "blocker capture, and ledger finalizers without staging unrelated dirt "
                "or claiming release."
            ),
            "selected_pattern_id": "durable_agent_work_landing_replay_compound",
            "input_refs": {
                "work_landing_attempt": attempt_ref,
                "scoped_mutation_receipt": mutation_ref,
                "work_landing_reconcile_plan": reconcile_ref,
                "closeout_status_projection": closeout_ref,
                "checkpoint_lane_decision": checkpoint_ref,
                "dependency_blocked": dependency_ref,
            },
            "source_statuses": source_statuses,
            "lane_decision_table": lane_decision_table,
            "replay_events": replay_events,
            "replay_policy": {
                "ambient_dirty_tree_is_not_a_freeze_reason": True,
                "owned_paths_must_be_claimed": True,
                "owner_native_validation_precedes_commit_attempt": True,
                "scoped_commit_requires_head_advance_before_landed_language": True,
                "broad_checkpoint_requires_explicit_operator_authorization": True,
                "metadata_blocker_requires_task_ledger_capture": True,
                "unrelated_user_changes_are_not_reverted": True,
                "work_ledger_progress_or_append_exempt_closeout_required": True,
            },
            "replay_summary": {
                "lane_count": len(lane_decision_table),
                "operator_authorized_lane_count": sum(
                    1
                    for row in lane_decision_table
                    if row.get("allowed_without_operator_authorization") is False
                ),
                "unrelated_dirty_stage_authority_count": 0,
                "git_metadata_blocker_ref": "wie_20260521T195941Z_cf83fa74",
                "work_ledger_session_ref": "codex_microcosm_wave_032",
                "validation_before_commit_attempt_required": True,
                "head_advance_required_for_landed_commit_claim": True,
            },
            "negative_case_ids": negative_case_ids,
            "evidence_refs": [
                attempt_ref,
                mutation_ref,
                reconcile_ref,
                closeout_ref,
                checkpoint_ref,
                dependency_ref,
                "wie_20260521T195941Z_cf83fa74",
            ],
            "safe_to_show": {
                "body_redacted": True,
                "receipt_refs_only": True,
                "private_paths_omitted": True,
                "source_bodies_omitted": True,
                "git_error_payloads_omitted": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The work-landing replay lens is a metadata-only public read-model. It "
                "does not mutate Git, stage unrelated dirty paths, authorize broad "
                "checkpointing without the operator, export private source bodies, prove "
                "a commit landed, publish, host, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def view_quality(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_view_quality_action_map_lens.json"
        requested_views = [
            {
                "view_id": "station_monitor",
                "expected_capture": "synthetic_monitor_pass_fixture",
                "role": "monitor row",
            },
            {
                "view_id": "root_navigator",
                "expected_capture": "synthetic_root_navigator_geometry_gap",
                "role": "public entry navigation",
            },
            {
                "view_id": "graph_geometry",
                "expected_capture": "synthetic_graph_geometry_capture_gap",
                "role": "route graph legibility",
            },
            {
                "view_id": "partial_unmeasured_panel",
                "expected_capture": "synthetic_partial_contract_marker_gap",
                "role": "measurement coverage gap",
            },
            {
                "view_id": "missing_operator_bridge_console",
                "expected_capture": "requested_view_missing_from_census",
                "role": "census binding gap fixture",
            },
        ]
        action_rows = [
            {
                "view_id": "station_monitor",
                "census_status": "calibrated_pass",
                "quality_posture": "monitor_acceptance",
                "action_class": "regression_guard",
                "next_action": "keep_monitor_regression_guard",
                "priority_weight": 12,
                "included_in_hot_action_rollup": False,
                "reason": "monitor rows preserve acceptance signal without creating resolution pressure",
                "private_screenshot_path_exported": False,
                "live_browser_control_authorized": False,
            },
            {
                "view_id": "root_navigator",
                "census_status": "calibrated_watch",
                "quality_posture": "resolution_pressure",
                "action_class": "resolution_work",
                "next_action": "resolve_navigation_layout_watch_row",
                "priority_weight": 92,
                "included_in_hot_action_rollup": True,
                "reason": "public entry navigation is present but still carries quality pressure",
                "private_screenshot_path_exported": False,
                "live_browser_control_authorized": False,
            },
            {
                "view_id": "graph_geometry",
                "census_status": "capture_gap",
                "quality_posture": "capture_binding_gap",
                "action_class": "bind_capture_or_repair_geometry",
                "next_action": "bind_graph_geometry_capture_before_quality_claim",
                "priority_weight": 88,
                "included_in_hot_action_rollup": True,
                "reason": "graph legibility cannot be claimed until capture evidence is bound",
                "private_screenshot_path_exported": False,
                "live_browser_control_authorized": False,
            },
            {
                "view_id": "partial_unmeasured_panel",
                "census_status": "partial_unmeasured",
                "quality_posture": "contract_marker_gap",
                "action_class": "add_contract_markers",
                "next_action": "add_or_bind_contract_markers_for_partial_row",
                "priority_weight": 84,
                "included_in_hot_action_rollup": True,
                "reason": "partial measurement debt must become a typed action, not prose",
                "private_screenshot_path_exported": False,
                "live_browser_control_authorized": False,
            },
            {
                "view_id": "missing_operator_bridge_console",
                "census_status": "missing_requested_view",
                "quality_posture": "census_binding_gap",
                "action_class": "add_to_census_or_bind_capture",
                "next_action": "create_public_safe_census_row_or_drop_unowned_requested_view",
                "priority_weight": 95,
                "included_in_hot_action_rollup": True,
                "reason": "every requested view gets an action row, including missing views",
                "private_screenshot_path_exported": False,
                "live_browser_control_authorized": False,
            },
        ]
        hot_action_rollup = [
            {
                "rank": index,
                "view_id": row["view_id"],
                "action_class": row["action_class"],
                "next_action": row["next_action"],
                "priority_weight": row["priority_weight"],
            }
            for index, row in enumerate(
                [
                    row
                    for row in sorted(
                        action_rows,
                        key=lambda item: int(item["priority_weight"]),
                        reverse=True,
                    )
                    if int(row["priority_weight"]) >= 80
                    and row["included_in_hot_action_rollup"] is True
                    and row["action_class"] != "regression_guard"
                ],
                start=1,
            )
        ]
        negative_case_ids = [
            "hot_rollup_claimed_as_complete_universe",
            "missing_requested_view_without_action",
            "monitor_row_creates_resolution_pressure",
            "calibrated_pass_in_hot_rollup",
            "partial_row_left_as_prose",
            "private_screenshot_path_exported",
            "release_claim_from_view_quality_lens",
        ]
        authority_ceiling = {
            "synthetic_fixture_only": True,
            "private_screenshot_paths_exported": False,
            "live_browser_control_authorized": False,
            "private_view_state_import_authorized": False,
            "source_mutation_authorized": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "complete_frontend_quality_claim": False,
        }
        status = (
            PASS
            if len(requested_views) == len(action_rows)
            and len(hot_action_rollup) == 4
            and len(negative_case_ids) == 7
            and {row["view_id"] for row in requested_views}
            == {row["view_id"] for row in action_rows}
            and all(row.get("private_screenshot_path_exported") is False for row in action_rows)
            and all(row.get("live_browser_control_authorized") is False for row in action_rows)
            and not any(
                row.get("action_class") == "regression_guard"
                for row in hot_action_rollup
            )
            and authority_ceiling["private_screenshot_paths_exported"] is False
            and authority_ceiling["live_browser_control_authorized"] is False
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_view_quality_action_map_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_view_quality_action_map_lens",
            "organ_family": "frontend_observability",
            "command": "microcosm view-quality",
            "endpoint": "/view-quality",
            "view_quality_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a public view-quality action map: every requested "
                "view gets one typed action row, missing and partial views stay visible, "
                "and the hot-action rollup is explicitly a projection rather than the "
                "complete view universe."
            ),
            "selected_pattern_id": "view_quality_all_view_action_map",
            "source_projection_refs": [
                "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::view_quality_all_view_action_map",
                "codex/standards/std_station_aesthetic.json::view_quality_action_map_v1",
                "tools/meta/observability/view_quality_census.py::*",
            ],
            "fixture_protocol": {
                "fixture_scope": "synthetic public rows only",
                "one_action_row_per_requested_view": True,
                "hot_rollup_is_projection_not_universe": True,
                "monitor_rows_do_not_create_resolution_pressure": True,
                "missing_view_routes_to_census_binding": True,
                "partial_measurement_routes_to_contract_markers": True,
            },
            "requested_views": requested_views,
            "action_rows": action_rows,
            "hot_action_rollup": hot_action_rollup,
            "action_summary": {
                "requested_view_count": len(requested_views),
                "action_row_count": len(action_rows),
                "hot_action_count": len(hot_action_rollup),
                "monitor_row_count": sum(
                    1 for row in action_rows if row.get("quality_posture") == "monitor_acceptance"
                ),
                "missing_view_action_count": sum(
                    1 for row in action_rows if row.get("census_status") == "missing_requested_view"
                ),
                "private_screenshot_path_export_count": 0,
                "live_browser_control_authorized_count": 0,
            },
            "negative_case_ids": negative_case_ids,
            "safe_to_show": {
                "body_redacted": True,
                "synthetic_view_rows_only": True,
                "private_screenshot_paths_omitted": True,
                "live_browser_control_omitted": True,
                "fixture_metadata_only": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The view-quality action map lens is a synthetic public read-model. It "
                "does not export private screenshots, control a browser, import live "
                "private UI state, mutate source, call providers, claim complete frontend "
                "quality, publish, host, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def projection_drift(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_projection_drift_control_lens.json"
        drift_rows = [
            {
                "drift_row_id": "world_model_cross_plane_drift_aggregate",
                "source_signal": "world-model, route, and projection drift summary row",
                "source_ref": (
                    "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                    "world_model_projection_drift_control_room"
                ),
                "repair_route": "microcosm projection-safety",
                "validation_ref": (
                    "tests/test_runtime_shell.py::"
                    "test_runtime_shell_projection_drift_control_lens_is_public_safe"
                ),
                "public_replacement_ref": "receipts/runtime_shell/public_projection_drift_control_lens.json",
                "body_redacted": True,
                "source_authority_claim": False,
                "live_repair_authorized": False,
                "source_mutation_authorized": False,
                "automatic_doctrine_promotion_authorized": False,
            },
            {
                "drift_row_id": "view_quality_all_view_action_map",
                "source_signal": "view action rows are drift targets, not final UI quality claims",
                "source_ref": "microcosm view-quality::action_rows",
                "repair_route": "microcosm view-quality",
                "validation_ref": (
                    "tests/test_observatory_legibility.py::"
                    "test_observatory_legibility_validator_exposes_causal_chain"
                ),
                "public_replacement_ref": "receipts/runtime_shell/public_view_quality_action_map_lens.json",
                "body_redacted": True,
                "source_authority_claim": False,
                "live_repair_authorized": False,
                "source_mutation_authorized": False,
                "automatic_doctrine_promotion_authorized": False,
            },
            {
                "drift_row_id": "compression_profile_governed_option_surface",
                "source_signal": "compressed command rows require omission receipts and drilldowns",
                "source_ref": "codex/standards/std_command_output_projection.json",
                "repair_route": "microcosm spine",
                "validation_ref": "tests/test_launch_compression.py",
                "public_replacement_ref": "receipts/runtime_shell/wave044_launch_compression.json",
                "body_redacted": True,
                "source_authority_claim": False,
                "live_repair_authorized": False,
                "source_mutation_authorized": False,
                "automatic_doctrine_promotion_authorized": False,
            },
            {
                "drift_row_id": "navigation_hologram_unified_route_plane",
                "source_signal": "route lease and navigation projection drift are inspectable before import",
                "source_ref": "examples/navigation_hologram_route_plane/exported_route_plane_bundle/route_plane.json",
                "repair_route": "microcosm route list",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_status_surface_lists_commands",
                "public_replacement_ref": "receipts/first_wave/navigation_hologram_route_plane/route_plane_result.json",
                "body_redacted": True,
                "source_authority_claim": False,
                "live_repair_authorized": False,
                "source_mutation_authorized": False,
                "automatic_doctrine_promotion_authorized": False,
            },
            {
                "drift_row_id": "agent_principle_failure_cap_assimilation_loop",
                "source_signal": "CAP capture remains private-root authority; Microcosm shows metadata-only closure shape",
                "source_ref": "codex/standards/std_task_ledger.json::quick_capture_contract",
                "repair_route": "Task Ledger quick-capture in private root",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_authority_map_is_public_safe",
                "public_replacement_ref": "receipts/runtime_shell/public_authority_map.json",
                "body_redacted": True,
                "source_authority_claim": False,
                "live_repair_authorized": False,
                "source_mutation_authorized": False,
                "automatic_doctrine_promotion_authorized": False,
            },
            {
                "drift_row_id": "operator_autonomy_phrase_active_standard_bridge",
                "source_signal": "operator autonomy phrase becomes bounded seed focus, not raw-seed overwrite",
                "source_ref": (
                    "state/meta_missions/type_a_autonomous_seed_loop/seeds/"
                    "microcosm_substrate_import_autonomous_seed.json"
                ),
                "repair_route": "seed reentry prompt rewrite",
                "validation_ref": "tools/meta/factory/validate_type_a_autonomous_seed_bundle.py",
                "public_replacement_ref": "state/meta_missions/type_a_autonomous_seed_loop/seeds/microcosm_substrate_import_autonomous_seed.md",
                "body_redacted": True,
                "source_authority_claim": False,
                "live_repair_authorized": False,
                "source_mutation_authorized": False,
                "automatic_doctrine_promotion_authorized": False,
            },
            {
                "drift_row_id": "omission_receipt_reversible_projection_boundary",
                "source_signal": "public projection rows carry owner route and omission receipt before reveal",
                "source_ref": "microcosm projection-safety::projection_rows",
                "repair_route": "microcosm projection-safety",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_projection_safety_lens_is_public_safe",
                "public_replacement_ref": "receipts/runtime_shell/public_projection_safety_audit_lens.json",
                "body_redacted": True,
                "source_authority_claim": False,
                "live_repair_authorized": False,
                "source_mutation_authorized": False,
                "automatic_doctrine_promotion_authorized": False,
            },
            {
                "drift_row_id": "entry_payload_admission_nonnegotiable_floor",
                "source_signal": "entry payload omissions become explicit next-run gates",
                "source_ref": "kernel.py --entry::task_conditioned_context_pack_entry",
                "repair_route": "microcosm drift-control",
                "validation_ref": "tests/test_cli.py::test_cli_projection_drift_control_smoke",
                "public_replacement_ref": "receipts/runtime_shell/public_projection_drift_control_lens.json",
                "body_redacted": True,
                "source_authority_claim": False,
                "live_repair_authorized": False,
                "source_mutation_authorized": False,
                "automatic_doctrine_promotion_authorized": False,
            },
        ]
        negative_case_ids = [
            "drift_row_without_source_ref_rejected",
            "repair_route_without_validation_ref_rejected",
            "projection_claiming_source_authority_rejected",
            "live_repair_action_authorized_rejected",
            "private_runtime_data_export_rejected",
            "provider_payload_export_rejected",
            "automatic_doctrine_promotion_rejected",
            "release_from_drift_projection_rejected",
        ]
        authority_ceiling = {
            "metadata_projection_only": True,
            "release_authorized": False,
            "hosted_public_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "provider_payload_exported": False,
            "source_authority_claim": False,
            "source_mutation_authorized": False,
            "live_route_repair_authorized": False,
            "live_task_ledger_mutation_authorized": False,
            "private_runtime_data_exported": False,
            "proof_body_exported": False,
            "automatic_doctrine_promotion_authorized": False,
        }
        encoded_rows = json.dumps(drift_rows, sort_keys=True)
        private_needles = ["/Users/", "src/ai_workflow", "Library/Application Support/Google", "sk-"]
        status = (
            PASS
            if drift_rows
            and all(row.get("source_ref") for row in drift_rows)
            and all(row.get("repair_route") for row in drift_rows)
            and all(row.get("validation_ref") for row in drift_rows)
            and all(row.get("body_redacted") is True for row in drift_rows)
            and all(row.get("source_authority_claim") is False for row in drift_rows)
            and all(row.get("live_repair_authorized") is False for row in drift_rows)
            and all(row.get("source_mutation_authorized") is False for row in drift_rows)
            and all(
                row.get("automatic_doctrine_promotion_authorized") is False
                for row in drift_rows
            )
            and all(value is False for key, value in authority_ceiling.items() if key != "metadata_projection_only")
            and authority_ceiling.get("metadata_projection_only") is True
            and not any(needle in encoded_rows for needle in private_needles)
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_projection_drift_control_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_projection_drift_control_lens",
            "organ_family": "compression_projection",
            "command": "microcosm drift-control",
            "endpoint": "/drift-control",
            "projection_drift_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes projection drift as a governed read-model: each row "
                "names the public source signal, the bounded repair route, the validator "
                "that proves the projection, and the authority ceiling that prevents live "
                "repair or private-root mutation."
            ),
            "selected_route_id": "world_model_projection_drift_control_room",
            "selected_pattern_ids": [row["drift_row_id"] for row in drift_rows],
            "source_projection_refs": [
                "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::world_model_projection_drift_control_room",
                "codex/standards/std_command_output_projection.json",
                "codex/standards/std_task_ledger.json",
                "codex/doctrine/paper_modules/navigation_hologram_theory.md",
                "microcosm projection-safety::projection_rows",
                "microcosm view-quality::action_rows",
            ],
            "drift_rows": drift_rows,
            "drift_summary": {
                "row_count": len(drift_rows),
                "source_ref_count": sum(1 for row in drift_rows if row.get("source_ref")),
                "repair_route_count": sum(1 for row in drift_rows if row.get("repair_route")),
                "validation_ref_count": sum(1 for row in drift_rows if row.get("validation_ref")),
                "source_authority_claim_count": sum(
                    1 for row in drift_rows if row.get("source_authority_claim") is True
                ),
                "live_repair_authorized_count": sum(
                    1 for row in drift_rows if row.get("live_repair_authorized") is True
                ),
                "source_mutation_authorized_count": sum(
                    1 for row in drift_rows if row.get("source_mutation_authorized") is True
                ),
                "automatic_doctrine_promotion_count": sum(
                    1
                    for row in drift_rows
                    if row.get("automatic_doctrine_promotion_authorized") is True
                ),
                "private_runtime_data_export_count": 0,
                "provider_payload_export_count": 0,
            },
            "negative_case_ids": negative_case_ids,
            "safe_to_show": {
                "body_redacted": True,
                "private_paths_omitted": True,
                "provider_payloads_omitted": True,
                "proof_bodies_omitted": True,
                "repair_is_route_metadata_only": True,
                "projection_is_read_model_only": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The projection-drift control lens is a public-safe metadata read-model. "
                "It does not inspect private runtime bodies, perform live repair, mutate "
                "source, promote doctrine, export provider payloads, authorize release, "
                "or claim source authority over the private root."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def spatial_simulation(self) -> dict[str, Any]:
        example_dir = (
            self.root
            / "examples/spatial_world_model_counterfactual_simulation_replay/"
            "exported_spatial_world_model_simulation_bundle"
        )
        out_dir = (
            self.root
            / "receipts/runtime_shell/demo_project/organs/"
            "spatial_world_model_counterfactual_simulation_replay"
        )
        payload = spatial_world_model_counterfactual_simulation_replay.run_simulation_bundle(
            example_dir,
            out_dir,
            command="microcosm spatial-simulation",
        )
        lens_path = (
            self.runtime_receipt_dir
            / "public_spatial_world_model_counterfactual_simulation_replay_lens.json"
        )
        lens = {
            **payload,
            "schema_version": (
                "microcosm_public_spatial_world_model_counterfactual_"
                "simulation_replay_lens_v1"
            ),
            "lens_id": "public_spatial_world_model_counterfactual_simulation_replay_lens",
            "organ_family": "spatial_world_model_counterfactual_simulation",
            "command": "microcosm spatial-simulation",
            "endpoint": "/spatial-simulation",
            "spatial_simulation_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm can replay synthetic spatial world-model counterfactuals "
                "as public metadata: scene state, action trace, predicted state, "
                "transition diff, oracle check, and limitation labels stay inspectable "
                "without private video, raw sensor payloads, live operation, or "
                "real-world geography claims."
            ),
            "source_projection_refs": [
                "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::spatial_world_model_counterfactual_simulation_replay_compound",
                "standards/std_microcosm_spatial_world_model_counterfactual_simulation_replay.json",
                "paper_modules/spatial_world_model_counterfactual_simulation_replay.md",
            ],
        }
        write_json_atomic(lens_path, lens)
        return lens

    def circuit_attribution(self) -> dict[str, Any]:
        example_dir = (
            self.root
            / "examples/mechanistic_interpretability_circuit_attribution_replay/"
            "exported_circuit_attribution_bundle"
        )
        out_dir = (
            self.root
            / "receipts/runtime_shell/demo_project/organs/"
            "mechanistic_interpretability_circuit_attribution_replay"
        )
        payload = (
            mechanistic_interpretability_circuit_attribution_replay
            .run_attribution_bundle(
                example_dir,
                out_dir,
                command="microcosm circuit-attribution",
            )
        )
        lens_path = (
            self.runtime_receipt_dir
            / "public_mechanistic_interpretability_circuit_attribution_replay_lens.json"
        )
        lens = {
            **payload,
            "schema_version": (
                "microcosm_public_mechanistic_interpretability_circuit_"
                "attribution_replay_lens_v1"
            ),
            "lens_id": (
                "public_mechanistic_interpretability_circuit_"
                "attribution_replay_lens"
            ),
            "organ_family": "mechanistic_interpretability_circuit_attribution",
            "command": "microcosm circuit-attribution",
            "endpoint": "/circuit-attribution",
            "circuit_attribution_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm can replay mechanistic interpretability circuit "
                "attribution as public metadata: toy prompt refs, sparse feature "
                "ids, machine-readable graph edges, replacement-model approximation "
                "scores, causal intervention deltas, sufficiency labels, "
                "faithfulness limits, contradiction cases, and cold replay refs stay "
                "inspectable without private weights, raw activations, proprietary "
                "prompts, hidden chain-of-thought, provider payloads, or release "
                "authority."
            ),
            "source_projection_refs": [
                "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::mechanistic_interpretability_circuit_attribution_replay_compound",
                "standards/std_microcosm_mechanistic_interpretability_circuit_attribution_replay.json",
                "paper_modules/mechanistic_interpretability_circuit_attribution_replay.md",
            ],
        }
        write_json_atomic(lens_path, lens)
        return lens

    def route_cleanup(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_route_cleanup_contract_lens.json"
        cleanup_rows = [
            {
                "cleanup_row_id": "atlas_first_contact_before_wide_search",
                "source_signal": "cold entry must start at compact seed and kernel routing surfaces",
                "source_ref": "AGENTS.override.md::First Moves",
                "owner_route": "microcosm spine",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_route_cleanup_contract_lens_is_public_safe",
                "public_replacement_ref": "receipts/runtime_shell/public_route_cleanup_contract_lens.json",
                "cleanup_action_class": "route_entry_order",
                "public_boundary": "first_contact_uses_runtime_spine_or_context_pack_before_wide_repo_search",
                "body_redacted": True,
                "route_deletion_authorized": False,
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "cleanup_row_id": "context_pack_before_grep_contract",
                "source_signal": "context-pack is the public analog of route cleanup before literal search",
                "source_ref": "system/lib/navigation_context_pack.py",
                "owner_route": "kernel.py --context-pack",
                "validation_ref": "tests/test_cli.py::test_cli_route_cleanup_contract_smoke",
                "public_replacement_ref": "microcosm route-cleanup",
                "cleanup_action_class": "navigation_context_admission",
                "public_boundary": "grep_is_drilldown_after_named_target_or_exact_error_string",
                "body_redacted": True,
                "route_deletion_authorized": False,
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "cleanup_row_id": "stale_doctrine_refresh_before_claim",
                "source_signal": "generated projections are refreshed by owner builders, not hand-edited",
                "source_ref": "AGENTS.override.md::Mutation Rules",
                "owner_route": "owner builder for generated projection",
                "validation_ref": "tools/meta/factory/check_agent_bootstrap_projection.py",
                "public_replacement_ref": "microcosm projection-safety",
                "cleanup_action_class": "generated_projection_refresh",
                "public_boundary": "generated_region_hand_edit_is_rejected_until_owner_builder_runs",
                "body_redacted": True,
                "route_deletion_authorized": False,
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "cleanup_row_id": "option_surface_drilldown_boundary",
                "source_signal": "option surfaces are drilldowns after a stable id or kind is selected",
                "source_ref": "AGENTS.override.md::Theory Pointers",
                "owner_route": "kernel.py --option-surface",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_spine_is_cold_reader_xray",
                "public_replacement_ref": "microcosm spine",
                "cleanup_action_class": "drilldown_boundary",
                "public_boundary": "option_surface_rows_are_not_first_contact_control_edges",
                "body_redacted": True,
                "route_deletion_authorized": False,
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "cleanup_row_id": "work_ledger_collision_before_mutation",
                "source_signal": "claimed work paths and active collisions are checked before durable edits",
                "source_ref": "tools/meta/factory/work_ledger.py::session-preflight",
                "owner_route": "Work Ledger session-preflight",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_authority_map_is_public_safe",
                "public_replacement_ref": "microcosm authority",
                "cleanup_action_class": "transaction_claim_gate",
                "public_boundary": "collision_signal_blocks_or_replans_mutation_before_landing",
                "body_redacted": True,
                "route_deletion_authorized": False,
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "cleanup_row_id": "scoped_landing_metadata_gate",
                "source_signal": "dirty trees land through scoped owned paths or captured blockers",
                "source_ref": "tools/meta/control/scoped_commit.py",
                "owner_route": "mission_transaction_preflight + scoped_commit",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_work_landing_replay_lens_is_public_safe",
                "public_replacement_ref": "receipts/runtime_shell/public_work_landing_replay_lens.json",
                "cleanup_action_class": "landing_claim_boundary",
                "public_boundary": "commit_claim_requires_head_advance_or_captured_blocker",
                "body_redacted": True,
                "route_deletion_authorized": False,
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "cleanup_row_id": "seed_reentry_names_next_route",
                "source_signal": "autonomous seed closeout rewrites the next reentry target",
                "source_ref": (
                    "state/meta_missions/type_a_autonomous_seed_loop/seeds/"
                    "microcosm_substrate_import_autonomous_seed.json"
                ),
                "owner_route": "kernel.py --validate-seed-heartbeat",
                "validation_ref": "tools/meta/factory/validate_type_a_autonomous_seed_bundle.py",
                "public_replacement_ref": (
                    "state/meta_missions/type_a_autonomous_seed_loop/seeds/"
                    "microcosm_substrate_import_autonomous_seed.md"
                ),
                "cleanup_action_class": "reentry_focus_cleanup",
                "public_boundary": "seed_reentry_is_agent_synthesis_not_raw_seed_overwrite",
                "body_redacted": True,
                "route_deletion_authorized": False,
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "cleanup_row_id": "public_private_route_cleanup_boundary",
                "source_signal": "route cleanup must preserve public/private stripping and projection safety",
                "source_ref": "microcosm stripping-guard::guard_rows",
                "owner_route": "microcosm stripping-guard + microcosm projection-safety",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_projection_safety_lens_is_public_safe",
                "public_replacement_ref": "receipts/runtime_shell/public_projection_safety_audit_lens.json",
                "cleanup_action_class": "public_private_projection_guard",
                "public_boundary": "cleanup_metadata_can_name_refs_but_not_private_bodies",
                "body_redacted": True,
                "route_deletion_authorized": False,
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
        ]
        negative_case_ids = [
            "route_cleanup_deletes_route_without_replacement_rejected",
            "context_pack_skip_to_wide_grep_rejected",
            "generated_region_hand_edit_rejected",
            "option_surface_as_control_entry_rejected",
            "scoped_commit_without_owned_paths_rejected",
            "seed_reentry_without_next_route_rejected",
            "private_body_export_from_cleanup_rejected",
            "release_from_route_cleanup_rejected",
        ]
        authority_ceiling = {
            "metadata_projection_only": True,
            "release_authorized": False,
            "hosted_public_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "provider_payload_exported": False,
            "source_mutation_authorized": False,
            "route_deletion_authorized": False,
            "live_route_repair_authorized": False,
            "generated_region_hand_edit_authorized": False,
            "private_body_exported": False,
            "proof_body_exported": False,
            "automatic_doctrine_promotion_authorized": False,
        }
        encoded_rows = json.dumps(cleanup_rows, sort_keys=True)
        private_needles = ["/Users/", "src/ai_workflow", "Library/Application Support/Google", "sk-"]
        status = (
            PASS
            if cleanup_rows
            and all(row.get("source_ref") for row in cleanup_rows)
            and all(row.get("owner_route") for row in cleanup_rows)
            and all(row.get("validation_ref") for row in cleanup_rows)
            and all(row.get("public_boundary") for row in cleanup_rows)
            and all(row.get("body_redacted") is True for row in cleanup_rows)
            and all(row.get("route_deletion_authorized") is False for row in cleanup_rows)
            and all(row.get("source_mutation_authorized") is False for row in cleanup_rows)
            and all(row.get("generated_region_hand_edit_authorized") is False for row in cleanup_rows)
            and all(row.get("private_body_exported") is False for row in cleanup_rows)
            and all(row.get("provider_payload_exported") is False for row in cleanup_rows)
            and all(row.get("release_authorized") is False for row in cleanup_rows)
            and all(value is False for key, value in authority_ceiling.items() if key != "metadata_projection_only")
            and authority_ceiling.get("metadata_projection_only") is True
            and not any(needle in encoded_rows for needle in private_needles)
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_route_cleanup_contract_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_route_cleanup_contract_lens",
            "organ_family": "navigation_hologram_route_plane",
            "command": "microcosm route-cleanup",
            "endpoint": "/route-cleanup",
            "route_cleanup_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes route cleanup as a public contract: start from "
                "entry surfaces, refresh generated projections with owner builders, "
                "respect option-surface drilldown boundaries, claim work before edits, "
                "and land through scoped evidence or captured blockers."
            ),
            "selected_route_id": "route_cleanup_contract_plane",
            "selected_pattern_ids": [row["cleanup_row_id"] for row in cleanup_rows],
            "source_projection_refs": [
                "AGENTS.override.md::First Moves",
                "AGENTS.override.md::Mutation Rules",
                "CODEX.md::Task Ledger capture reflex",
                "system/lib/navigation_context_pack.py",
                "tools/meta/factory/work_ledger.py::session-preflight",
                "tools/meta/control/scoped_commit.py",
                "microcosm projection-safety::projection_rows",
            ],
            "cleanup_rows": cleanup_rows,
            "cleanup_summary": {
                "row_count": len(cleanup_rows),
                "source_ref_count": sum(1 for row in cleanup_rows if row.get("source_ref")),
                "owner_route_count": sum(1 for row in cleanup_rows if row.get("owner_route")),
                "validation_ref_count": sum(1 for row in cleanup_rows if row.get("validation_ref")),
                "negative_case_count": len(negative_case_ids),
                "route_deletion_authorized_count": sum(
                    1 for row in cleanup_rows if row.get("route_deletion_authorized") is True
                ),
                "source_mutation_authorized_count": sum(
                    1 for row in cleanup_rows if row.get("source_mutation_authorized") is True
                ),
                "generated_region_hand_edit_authorized_count": sum(
                    1
                    for row in cleanup_rows
                    if row.get("generated_region_hand_edit_authorized") is True
                ),
                "private_body_export_count": sum(
                    1 for row in cleanup_rows if row.get("private_body_exported") is True
                ),
                "provider_payload_export_count": sum(
                    1 for row in cleanup_rows if row.get("provider_payload_exported") is True
                ),
                "release_authorized_count": sum(
                    1 for row in cleanup_rows if row.get("release_authorized") is True
                ),
            },
            "negative_case_ids": negative_case_ids,
            "safe_to_show": {
                "body_redacted": True,
                "route_cleanup_is_metadata_only": True,
                "owner_routes_named_without_private_bodies": True,
                "generated_regions_require_owner_builders": True,
                "scoped_landing_requires_owned_paths": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The route-cleanup contract lens is a public-safe read-model. It does "
                "not delete routes, hand-edit generated regions, mutate source, export "
                "private bodies or provider payloads, promote doctrine, publish, host, "
                "or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def projection_safety(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_projection_safety_audit_lens.json"
        projection_rows = [
            {
                "projection_id": "public_ten_minute_tour",
                "command": "microcosm tour <project>",
                "endpoint": "/tour",
                "public_ref": "receipts/runtime_shell/public_ten_minute_tour.json",
                "owner_route": "runtime_shell.tour",
                "authority_ceiling_ref": "microcosm authority::public_ten_minute_tour",
                "omission_receipt": {
                    "omitted": ["raw compile payloads", "raw receipt bodies"],
                    "drilldown": "microcosm evidence inspect <receipt>",
                    "source_ref": "microcosm tour <project>::evidence_refs",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_authority_map",
                "command": "microcosm authority",
                "endpoint": "/authority",
                "public_ref": "receipts/runtime_shell/public_authority_map.json",
                "owner_route": "runtime_shell.authority",
                "authority_ceiling_ref": "microcosm authority::surface_authority",
                "omission_receipt": {
                    "omitted": ["private source bodies", "unreviewed release claims"],
                    "drilldown": "/authority",
                    "source_ref": "core/organ_registry.json",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_prediction_lens",
                "command": "microcosm prediction-lens",
                "endpoint": "/prediction",
                "public_ref": "receipts/runtime_shell/public_prediction_lens.json",
                "owner_route": "runtime_shell.prediction_lens",
                "authority_ceiling_ref": "microcosm authority::public_prediction_lens",
                "omission_receipt": {
                    "omitted": ["live market data", "private dossiers", "provider payloads"],
                    "drilldown": "/prediction",
                    "source_ref": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::prediction_oracle_reconciliation",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_market_prediction_evidence_boundary_lens",
                "command": "microcosm market-boundary",
                "endpoint": "/market-boundary",
                "public_ref": "receipts/runtime_shell/public_market_prediction_evidence_boundary_lens.json",
                "owner_route": "runtime_shell.market_boundary",
                "authority_ceiling_ref": (
                    "microcosm authority::public_market_prediction_evidence_boundary_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "live market data",
                        "private portfolio or account state",
                        "provider payloads",
                        "trading or investment advice",
                        "forecast performance guarantees",
                    ],
                    "drilldown": "/market-boundary",
                    "source_ref": "microcosm market-boundary::boundary_rows",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_corpus_readiness_lens",
                "command": "microcosm corpus-lens",
                "endpoint": "/corpus",
                "public_ref": "receipts/runtime_shell/public_corpus_readiness_lens.json",
                "owner_route": "runtime_shell.corpus_lens",
                "authority_ceiling_ref": "microcosm authority::public_corpus_readiness_lens",
                "omission_receipt": {
                    "omitted": ["private corpus bodies", "Mathlib-dependent proof attempts"],
                    "drilldown": "/corpus",
                    "source_ref": "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input/corpus_readiness.json",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_verifier_trace_repair_lens",
                "command": "microcosm trace-lens",
                "endpoint": "/trace",
                "public_ref": "receipts/runtime_shell/public_verifier_trace_repair_lens.json",
                "owner_route": "runtime_shell.trace_lens",
                "authority_ceiling_ref": "microcosm authority::public_verifier_trace_repair_lens",
                "omission_receipt": {
                    "omitted": ["proof bodies", "oracle-needed premise ids", "provider payloads"],
                    "drilldown": "/trace",
                    "source_ref": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::formal_math_verifier_trace_repair_loop_compound",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_verifier_repair_loop_lens",
                "command": "microcosm repair-loop",
                "endpoint": "/repair-loop",
                "public_ref": "receipts/runtime_shell/public_verifier_repair_loop_lens.json",
                "owner_route": "runtime_shell.repair_loop",
                "authority_ceiling_ref": "microcosm authority::public_verifier_repair_loop_lens",
                "omission_receipt": {
                    "omitted": ["proof bodies", "oracle-needed premise ids", "provider payloads"],
                    "drilldown": "/repair-loop",
                    "source_ref": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::formal_math_verifier_trace_repair_loop_compound",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_formal_evidence_cell_lens",
                "command": "microcosm evidence-cells",
                "endpoint": "/evidence-cells",
                "public_ref": "receipts/runtime_shell/public_formal_evidence_cell_lens.json",
                "owner_route": "runtime_shell.evidence_cells",
                "authority_ceiling_ref": "microcosm authority::public_formal_evidence_cell_lens",
                "omission_receipt": {
                    "omitted": ["proof bodies", "private source refs", "general theorem claims"],
                    "drilldown": "/evidence-cells",
                    "source_ref": "codex/standards/std_paper_module.json::formal_evidence_cells",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_undeclared_library_prior_symbol_lens",
                "command": "microcosm undeclared-library-prior-symbol-classifier",
                "endpoint": "/undeclared-library-priors",
                "public_ref": (
                    "receipts/runtime_shell/"
                    "public_undeclared_library_prior_symbol_lens.json"
                ),
                "owner_route": "runtime_shell.undeclared_library_prior_symbol_classifier",
                "authority_ceiling_ref": (
                    "microcosm authority::public_undeclared_library_prior_symbol_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "proof bodies",
                        "private theorem/source refs",
                        "oracle premise bodies",
                        "provider payloads",
                        "theorem correctness claims",
                    ],
                    "drilldown": "/undeclared-library-priors",
                    "source_ref": (
                        "examples/undeclared_library_prior_symbol_classifier/"
                        "exported_symbol_classifier_bundle/symbol_observations.json"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_proof_loop_depth_lens",
                "command": "microcosm proof-loop-depth",
                "endpoint": "/proof-loop-depth",
                "public_ref": "receipts/runtime_shell/public_proof_loop_depth_lens.json",
                "owner_route": "runtime_shell.proof_loop_depth",
                "authority_ceiling_ref": "microcosm authority::public_proof_loop_depth_lens",
                "omission_receipt": {
                    "omitted": [
                        "proof bodies",
                        "oracle-needed premise ids",
                        "provider payloads",
                        "benchmark claims",
                        "general theorem-solution claims",
                    ],
                    "drilldown": "/proof-loop-depth",
                    "source_ref": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::formal_math_verifier_trace_repair_loop_compound",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_work_landing_replay_lens",
                "command": "microcosm landing-replay",
                "endpoint": "/landing-replay",
                "public_ref": "receipts/runtime_shell/public_work_landing_replay_lens.json",
                "owner_route": "runtime_shell.landing_replay",
                "authority_ceiling_ref": "microcosm authority::public_work_landing_replay_lens",
                "omission_receipt": {
                    "omitted": ["unrelated dirty path bodies", "live git metadata", "commit-only proof claims"],
                    "drilldown": "/landing-replay",
                    "source_ref": "tools/meta/control/work_landing.py",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_durable_agent_work_landing_replay_lens",
                "command": (
                    "microcosm durable-agent-work-landing-replay "
                    "run-work-landing-bundle"
                ),
                "endpoint": "/landing-replay",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "durable_agent_work_landing_replay/"
                    "exported_work_landing_replay_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs.durable_agent_work_landing_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_durable_agent_work_landing_replay_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "private worktree paths",
                        "raw diffs",
                        "live git metadata",
                        "provider payloads",
                        "commit-landed claims without HEAD evidence",
                    ],
                    "drilldown": (
                        "microcosm durable-agent-work-landing-replay "
                        "run-work-landing-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "durable_agent_work_landing_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_research_replication_rubric_artifact_replay_lens",
                "command": (
                    "microcosm research-replication-rubric-artifact-replay "
                    "run-replication-bundle"
                ),
                "endpoint": "/research-replication",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "research_replication_rubric_artifact_replay/"
                    "exported_research_replication_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "research_replication_rubric_artifact_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_research_replication_rubric_artifact_replay_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "private paper and data bodies",
                        "hidden rubrics",
                        "original-author code bodies",
                        "undeclared artifact hash refs",
                        "provider payloads",
                        "benchmark performance claims",
                    ],
                    "drilldown": (
                        "microcosm research-replication-rubric-artifact-replay "
                        "run-replication-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "research_replication_rubric_artifact_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_world_model_projection_drift_control_room_lens",
                "command": (
                    "microcosm world-model-projection-drift-control-room "
                    "run-drift-control-bundle"
                ),
                "endpoint": "/drift-control",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "world_model_projection_drift_control_room/"
                    "exported_projection_drift_control_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "world_model_projection_drift_control_room"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_world_model_projection_drift_control_room_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "private runtime bodies",
                        "live route repair actions",
                        "provider payloads",
                        "source mutation authority",
                        "automatic doctrine promotion",
                    ],
                    "drilldown": (
                        "microcosm world-model-projection-drift-control-room "
                        "run-drift-control-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json::"
                        "frontier_combination_routes[world_model_projection_drift_control_room]"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": (
                    "public_spatial_world_model_counterfactual_simulation_replay_lens"
                ),
                "command": (
                    "microcosm spatial-world-model-counterfactual-simulation-replay "
                    "run-simulation-bundle"
                ),
                "endpoint": "/spatial-simulation",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "spatial_world_model_counterfactual_simulation_replay/"
                    "exported_spatial_world_model_simulation_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "spatial_world_model_counterfactual_simulation_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_spatial_world_model_counterfactual_simulation_replay_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "private video bodies",
                        "raw sensor payloads",
                        "live robot or AV operation",
                        "real-world location claims",
                        "generated video authority",
                        "geographic accuracy claims",
                        "benchmark score claims",
                    ],
                    "drilldown": (
                        "microcosm spatial-world-model-counterfactual-simulation-replay "
                        "run-simulation-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "spatial_world_model_counterfactual_simulation_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": (
                    "public_materials_chemistry_closed_loop_lab_safety_replay_lens"
                ),
                "command": (
                    "microcosm materials-chemistry-closed-loop-lab-safety-replay "
                    "run-lab-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "materials_chemistry_closed_loop_lab_safety_replay/"
                    "exported_materials_lab_safety_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "materials_chemistry_closed_loop_lab_safety_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_materials_chemistry_closed_loop_lab_safety_replay_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "wet-lab protocol steps",
                        "hazardous synthesis instructions",
                        "reagent quantities",
                        "live lab credentials",
                        "robot command payloads",
                        "private lab notebooks",
                        "live assay data",
                        "discovery or benchmark score claims",
                    ],
                    "drilldown": (
                        "microcosm materials-chemistry-closed-loop-lab-safety-replay "
                        "run-lab-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "materials_chemistry_closed_loop_lab_safety_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": (
                    "public_mechanistic_interpretability_circuit_"
                    "attribution_replay_lens"
                ),
                "command": (
                    "microcosm mechanistic-interpretability-circuit-attribution-replay "
                    "run-attribution-bundle"
                ),
                "endpoint": "/circuit-attribution",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "mechanistic_interpretability_circuit_attribution_replay/"
                    "exported_circuit_attribution_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "mechanistic_interpretability_circuit_attribution_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_mechanistic_interpretability_circuit_attribution_replay_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "private model weights",
                        "raw activation dumps",
                        "proprietary prompt bodies",
                        "hidden chain-of-thought",
                        "provider payload bodies",
                        "private model internals claims",
                        "benchmark score claims",
                    ],
                    "drilldown": (
                        "microcosm mechanistic-interpretability-circuit-attribution-replay "
                        "run-attribution-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "mechanistic_interpretability_circuit_attribution_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_view_quality_action_map_lens",
                "command": "microcosm view-quality",
                "endpoint": "/view-quality",
                "public_ref": "receipts/runtime_shell/public_view_quality_action_map_lens.json",
                "owner_route": "runtime_shell.view_quality",
                "authority_ceiling_ref": "microcosm authority::public_view_quality_action_map_lens",
                "omission_receipt": {
                    "omitted": ["private screenshot paths", "live browser state", "complete quality claims"],
                    "drilldown": "/view-quality",
                    "source_ref": "codex/standards/std_station_aesthetic.json::view_quality_action_map_v1",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_projection_drift_control_lens",
                "command": "microcosm drift-control",
                "endpoint": "/drift-control",
                "public_ref": "receipts/runtime_shell/public_projection_drift_control_lens.json",
                "owner_route": "runtime_shell.projection_drift",
                "authority_ceiling_ref": "microcosm authority::public_projection_drift_control_lens",
                "omission_receipt": {
                    "omitted": [
                        "private runtime bodies",
                        "live route repair actions",
                        "provider payloads",
                        "source mutation authority",
                    ],
                    "drilldown": "/drift-control",
                    "source_ref": "microcosm drift-control::drift_rows",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_route_cleanup_contract_lens",
                "command": "microcosm route-cleanup",
                "endpoint": "/route-cleanup",
                "public_ref": "receipts/runtime_shell/public_route_cleanup_contract_lens.json",
                "owner_route": "runtime_shell.route_cleanup",
                "authority_ceiling_ref": "microcosm authority::public_route_cleanup_contract_lens",
                "omission_receipt": {
                    "omitted": [
                        "private route bodies",
                        "live cleanup actions",
                        "generated region bodies",
                        "provider payloads",
                    ],
                    "drilldown": "/route-cleanup",
                    "source_ref": "microcosm route-cleanup::cleanup_rows",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_hook_intervention_coverage_lens",
                "command": "microcosm hook-coverage",
                "endpoint": "/hook-coverage",
                "public_ref": "receipts/runtime_shell/public_hook_intervention_coverage_lens.json",
                "owner_route": "runtime_shell.hook_coverage",
                "authority_ceiling_ref": "microcosm authority::public_hook_intervention_coverage_lens",
                "omission_receipt": {
                    "omitted": [
                        "live operator state",
                        "provider payloads",
                        "browser/HUD/cockpit state",
                    ],
                    "drilldown": "/hook-coverage",
                    "source_ref": "receipts/first_wave/agent_route_observability_runtime/hook_shadow_coverage.json",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_agent_reliability_replay_gauntlet_lens",
                "command": "microcosm replay-gauntlet",
                "endpoint": "/replay-gauntlet",
                "public_ref": "receipts/runtime_shell/public_agent_reliability_replay_gauntlet_lens.json",
                "owner_route": "runtime_shell.replay_gauntlet",
                "authority_ceiling_ref": "microcosm authority::public_agent_reliability_replay_gauntlet_lens",
                "omission_receipt": {
                    "omitted": [
                        "real secret material",
                        "live agent transcripts",
                        "untrusted tool payload bodies",
                        "private memory/user data",
                    ],
                    "drilldown": "/replay-gauntlet",
                    "source_ref": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::agent_reliability_replay_gauntlet",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_repository_benchmark_transaction_lab_lens",
                "command": "microcosm benchmark-lab",
                "endpoint": "/benchmark-lab",
                "public_ref": "receipts/runtime_shell/public_repository_benchmark_transaction_lab_lens.json",
                "owner_route": "runtime_shell.benchmark_lab",
                "authority_ceiling_ref": "microcosm authority::public_repository_benchmark_transaction_lab_lens",
                "omission_receipt": {
                    "omitted": [
                        "private issue bodies",
                        "oracle patch bodies",
                        "live repository paths",
                        "provider payloads",
                    ],
                    "drilldown": "/benchmark-lab",
                    "source_ref": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::repository_agent_benchmark_transaction_lab",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_agent_benchmark_integrity_anti_gaming_lens",
                "command": (
                    "microcosm agent-benchmark-integrity-anti-gaming-replay "
                    "run-benchmark-integrity-bundle"
                ),
                "endpoint": "/benchmark-lab",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "agent_benchmark_integrity_anti_gaming_replay/"
                    "exported_benchmark_integrity_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "agent_benchmark_integrity_anti_gaming_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_agent_benchmark_integrity_anti_gaming_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "private issue bodies",
                        "oracle patch bodies",
                        "hidden-gold answers",
                        "provider payloads",
                        "benchmark score claims",
                    ],
                    "drilldown": (
                        "microcosm agent-benchmark-integrity-anti-gaming-replay "
                        "run-benchmark-integrity-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "agent_benchmark_integrity_anti_gaming_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_agent_monitor_redteam_falsification_lens",
                "command": (
                    "microcosm agent-monitor-redteam-falsification-replay "
                    "run-monitor-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "agent_monitor_redteam_falsification_replay/"
                    "exported_monitor_redteam_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "agent_monitor_redteam_falsification_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_agent_monitor_redteam_falsification_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "private chain-of-thought",
                        "internal code",
                        "exploit instruction detail",
                        "credential material",
                        "live agent traffic",
                        "monitor product performance claims",
                    ],
                    "drilldown": (
                        "microcosm agent-monitor-redteam-falsification-replay "
                        "run-monitor-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "agent_monitor_redteam_falsification_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_agent_sabotage_scheming_monitor_replay_lens",
                "command": (
                    "microcosm agent-sabotage-scheming-monitor-replay "
                    "run-sabotage-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "agent_sabotage_scheming_monitor_replay/"
                    "exported_sabotage_monitor_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "agent_sabotage_scheming_monitor_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_agent_sabotage_scheming_monitor_replay_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "live sabotage instructions",
                        "real credentials or account identifiers",
                        "actionable exploit details",
                        "private chain-of-thought",
                        "raw harmful payloads",
                        "deployment-risk product claims",
                    ],
                    "drilldown": (
                        "microcosm agent-sabotage-scheming-monitor-replay "
                        "run-sabotage-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "agent_sabotage_scheming_monitor_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_agent_sandbox_policy_escape_replay_lens",
                "command": (
                    "microcosm agent-sandbox-policy-escape-replay "
                    "run-sandbox-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "agent_sandbox_policy_escape_replay/"
                    "exported_sandbox_policy_escape_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "agent_sandbox_policy_escape_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_agent_sandbox_policy_escape_replay_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "real secrets or credentials",
                        "live network targets",
                        "raw environment exports",
                        "host filesystem paths",
                        "executable escape payloads",
                        "security benchmark performance claims",
                    ],
                    "drilldown": (
                        "microcosm agent-sandbox-policy-escape-replay "
                        "run-sandbox-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "agent_sandbox_policy_escape_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_indirect_prompt_injection_information_flow_policy_replay_lens",
                "command": (
                    "microcosm indirect-prompt-injection-information-flow-policy-replay "
                    "run-prompt-injection-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "indirect_prompt_injection_information_flow_policy_replay/"
                    "exported_prompt_injection_flow_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "indirect_prompt_injection_information_flow_policy_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_indirect_prompt_injection_information_flow_policy_replay_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "real email, document, browser, or account material",
                        "raw system, developer, prompt, or tool-output bodies",
                        "secrets or credentials",
                        "provider payloads",
                        "hidden system-message bodies",
                        "general prompt-injection robustness claims",
                    ],
                    "drilldown": (
                        "microcosm indirect-prompt-injection-information-flow-policy-replay "
                        "run-prompt-injection-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "indirect_prompt_injection_information_flow_policy_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_agentic_vulnerability_discovery_patch_proof_replay_lens",
                "command": (
                    "microcosm agentic-vulnerability-discovery-patch-proof-replay "
                    "run-patch-proof-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "agentic_vulnerability_discovery_patch_proof_replay/"
                    "exported_patch_proof_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "agentic_vulnerability_discovery_patch_proof_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_agentic_vulnerability_discovery_patch_proof_replay_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "live targets",
                        "real CVE exploitation details",
                        "weaponized payloads",
                        "credentials or account state",
                        "network exfiltration steps",
                        "provider payloads",
                        "raw issue or patch bodies",
                        "benchmark security-score claims",
                    ],
                    "drilldown": (
                        "microcosm agentic-vulnerability-discovery-patch-proof-replay "
                        "run-patch-proof-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "agentic_vulnerability_discovery_patch_proof_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_agent_memory_temporal_conflict_lens",
                "command": (
                    "microcosm agent-memory-temporal-conflict-replay "
                    "run-memory-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "agent_memory_temporal_conflict_replay/"
                    "exported_memory_temporal_conflict_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "agent_memory_temporal_conflict_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_agent_memory_temporal_conflict_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "raw transcript bodies",
                        "private memory candidate bodies",
                        "live user memory values",
                        "provider payloads",
                        "active injection text",
                        "live memory product claims",
                    ],
                    "drilldown": (
                        "microcosm agent-memory-temporal-conflict-replay "
                        "run-memory-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "agent_memory_temporal_conflict_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_sleeper_memory_poisoning_quarantine_lens",
                "command": (
                    "microcosm sleeper-memory-poisoning-quarantine-replay "
                    "run-quarantine-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "sleeper_memory_poisoning_quarantine_replay/"
                    "exported_sleeper_memory_poisoning_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "sleeper_memory_poisoning_quarantine_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_sleeper_memory_poisoning_quarantine_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "private memory bodies",
                        "raw transcript bodies",
                        "live user memory values",
                        "hidden trigger text",
                        "provider payloads",
                        "benchmark security claims",
                    ],
                    "drilldown": (
                        "microcosm sleeper-memory-poisoning-quarantine-replay "
                        "run-quarantine-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "sleeper_memory_poisoning_quarantine_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_mcp_tool_authority_replay_lens",
                "command": (
                    "microcosm mcp-tool-authority-replay "
                    "run-tool-authority-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "mcp_tool_authority_replay/"
                    "exported_mcp_tool_authority_bundle_validation_result.json"
                ),
                "owner_route": "microcosm_core.organs.mcp_tool_authority_replay",
                "authority_ceiling_ref": (
                    "microcosm authority::public_mcp_tool_authority_replay_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "credential values",
                        "provider payloads",
                        "raw tool payloads",
                        "live MCP account refs",
                        "untrusted tool-output bodies",
                        "benchmark security claims",
                    ],
                    "drilldown": (
                        "microcosm mcp-tool-authority-replay "
                        "run-tool-authority-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "mcp_tool_authority_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": (
                    "public_proof_derived_governed_mutation_authorization_lens"
                ),
                "command": (
                    "microcosm proof-derived-governed-mutation-authorization "
                    "run-authorization-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "proof_derived_governed_mutation_authorization/"
                    "exported_governed_mutation_authorization_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs."
                    "proof_derived_governed_mutation_authorization"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_proof_derived_governed_mutation_authorization_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "standing credentials",
                        "live cloud/account credentials",
                        "private proof bodies",
                        "provider payloads",
                        "raw policy vote bodies",
                        "irreversible mutation authority",
                    ],
                    "drilldown": (
                        "microcosm proof-derived-governed-mutation-authorization "
                        "run-authorization-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "proof_derived_governed_mutation_authorization_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_belief_state_process_reward_replay_lens",
                "command": (
                    "microcosm belief-state-process-reward-replay "
                    "run-reward-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "public_ref": (
                    "receipts/runtime_shell/demo_project/organs/"
                    "belief_state_process_reward_replay/"
                    "exported_belief_state_process_reward_bundle_validation_result.json"
                ),
                "owner_route": (
                    "microcosm_core.organs.belief_state_process_reward_replay"
                ),
                "authority_ceiling_ref": (
                    "microcosm authority::"
                    "public_belief_state_process_reward_replay_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "hidden reasoning bodies",
                        "live RL or training traces",
                        "hidden gold labels",
                        "provider payloads",
                        "benchmark submission payloads",
                    ],
                    "drilldown": (
                        "microcosm belief-state-process-reward-replay "
                        "run-reward-bundle"
                    ),
                    "source_ref": (
                        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::"
                        "belief_state_process_reward_replay_compound"
                    ),
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_cold_reader_legibility_scorecard_lens",
                "command": "microcosm legibility-scorecard",
                "endpoint": "/legibility-scorecard",
                "public_ref": "receipts/runtime_shell/public_cold_reader_legibility_scorecard_lens.json",
                "owner_route": "runtime_shell.legibility_scorecard",
                "authority_ceiling_ref": "microcosm authority::public_cold_reader_legibility_scorecard_lens",
                "omission_receipt": {
                    "omitted": [
                        "private macro context",
                        "reader transcripts",
                        "proof bodies",
                        "provider payloads",
                    ],
                    "drilldown": "/legibility-scorecard",
                    "source_ref": "microcosm legibility-scorecard::checkpoint_rows",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_projection_import_map_lens",
                "command": "microcosm projection-import-map",
                "endpoint": "/projection-import-map",
                "public_ref": "receipts/runtime_shell/public_projection_import_map_lens.json",
                "owner_route": "runtime_shell.projection_import_map",
                "authority_ceiling_ref": "microcosm authority::public_projection_import_map_lens",
                "omission_receipt": {
                    "omitted": [
                        "private macro bodies",
                        "proof bodies",
                        "provider payloads",
                        "automated import guarantee",
                    ],
                    "drilldown": "/projection-import-map",
                    "source_ref": "microcosm projection-import-map::import_rows",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_import_projector_contract_lens",
                "command": "microcosm import-projector",
                "endpoint": "/import-projector",
                "public_ref": "receipts/runtime_shell/public_import_projector_contract_lens.json",
                "owner_route": "runtime_shell.import_projector",
                "authority_ceiling_ref": "microcosm authority::public_import_projector_contract_lens",
                "omission_receipt": {
                    "omitted": [
                        "private source bodies",
                        "proof bodies",
                        "provider payloads",
                        "automated import execution",
                        "lossless private projection claims",
                    ],
                    "drilldown": "/import-projector",
                    "source_ref": "microcosm import-projector::projector_rows",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_compression_profile_option_surface_lens",
                "command": "microcosm option-surface-lens",
                "endpoint": "/option-surface-lens",
                "public_ref": (
                    "receipts/runtime_shell/"
                    "public_compression_profile_option_surface_lens.json"
                ),
                "owner_route": "runtime_shell.option_surface_lens",
                "authority_ceiling_ref": (
                    "microcosm authority::public_compression_profile_option_surface_lens"
                ),
                "omission_receipt": {
                    "omitted": [
                        "private profile bodies",
                        "raw sidecar payload bodies",
                        "profile switching authority",
                        "lossless private projection claims",
                    ],
                    "drilldown": "/option-surface-lens",
                    "source_ref": "microcosm option-surface-lens::option_rows",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_stripping_guard_lens",
                "command": "microcosm stripping-guard",
                "endpoint": "/stripping-guard",
                "public_ref": "receipts/runtime_shell/public_stripping_guard_lens.json",
                "owner_route": "runtime_shell.stripping_guard",
                "authority_ceiling_ref": "microcosm authority::public_stripping_guard_lens",
                "omission_receipt": {
                    "omitted": [
                        "private source bodies",
                        "proof bodies",
                        "provider payloads",
                        "raw private path refs",
                        "secret detector completeness claims",
                    ],
                    "drilldown": "/stripping-guard",
                    "source_ref": "microcosm stripping-guard::guard_rows",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_standards_control_lens",
                "command": "microcosm standards-control",
                "endpoint": "/standards-control",
                "public_ref": "receipts/runtime_shell/public_standards_control_lens.json",
                "owner_route": "runtime_shell.standards_control",
                "authority_ceiling_ref": "microcosm authority::public_standards_control_lens",
                "omission_receipt": {
                    "omitted": [
                        "private doctrine bodies",
                        "raw source bodies behind standards",
                        "release/publication authority",
                        "standards completeness guarantee",
                    ],
                    "drilldown": "/standards-control",
                    "source_ref": "microcosm standards-control::standards_rows",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "runtime_reveal_import_bridge",
                "command": "microcosm intake",
                "endpoint": "/intake",
                "public_ref": "receipts/runtime_shell/intake_bridge/observatory_intake_bridge.json",
                "owner_route": "runtime_shell.intake",
                "authority_ceiling_ref": "microcosm authority::runtime_reveal_import_bridge",
                "omission_receipt": {
                    "omitted": ["macro private bodies", "unprojected raw seed voice"],
                    "drilldown": "/intake",
                    "source_ref": "examples/macro_projection_import_protocol/exported_projection_import_bundle/import_plan.json",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "projection_id": "public_reveal_view",
                "command": "microcosm reveal",
                "endpoint": "/reveal",
                "public_ref": "receipts/runtime_shell/public_reveal_walkthrough.json",
                "owner_route": "runtime_shell.reveal",
                "authority_ceiling_ref": "microcosm authority::public_reveal_view",
                "omission_receipt": {
                    "omitted": ["private macro equivalence claims", "publication authority"],
                    "drilldown": "/reveal",
                    "source_ref": "examples/public_reveal_walkthrough/exported_public_reveal_bundle/reveal_plan.json",
                },
                "release_authorized": False,
                "source_mutation_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
        ]
        negative_case_ids = [
            "compressed_projection_without_omission_receipt",
            "omission_receipt_without_drilldown",
            "private_source_body_exported",
            "proof_body_exported_as_public_evidence",
            "provider_payload_exported",
            "authority_ceiling_missing",
            "release_claim_from_projection",
            "irreversible_projection_without_owner_route",
        ]
        encoded_rows = json.dumps(projection_rows, sort_keys=True)
        private_needles = ["/Users/", "src/ai_workflow", "Library/Application Support/Google/Chrome", "sk-"]
        status = (
            PASS
            if projection_rows
            and all(row.get("release_authorized") is False for row in projection_rows)
            and all(row.get("source_mutation_authorized") is False for row in projection_rows)
            and all(row.get("private_body_exported") is False for row in projection_rows)
            and all(row.get("proof_body_exported") is False for row in projection_rows)
            and all(row.get("provider_payload_exported") is False for row in projection_rows)
            and all(isinstance(row.get("omission_receipt"), dict) for row in projection_rows)
            and all((row["omission_receipt"].get("drilldown") and row["omission_receipt"].get("source_ref")) for row in projection_rows)
            and not any(needle in encoded_rows for needle in private_needles)
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_projection_safety_audit_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_projection_safety_audit_lens",
            "organ_family": "compression_projection",
            "command": "microcosm projection-safety",
            "endpoint": "/projection-safety",
            "projection_safety_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a projection-safety audit: every compressed public "
                "lens carries an omission receipt, a named drilldown, and an explicit "
                "authority ceiling before it can be treated as legible public state."
            ),
            "selected_pattern_id": "omission_receipt_reversible_projection_boundary",
            "source_projection_refs": [
                "codex/standards/std_command_output_projection.json",
                "codex/standards/std_paper_module.json",
                "codex/doctrine/skills/compression/profile_governed_compression.md",
                "codex/doctrine/paper_modules/navigation_hologram_theory.md",
                "system/lib/navigation_context_pack.py",
                "system/lib/kernel/commands/comprehension_snapshot.py",
            ],
            "projection_policy": {
                "low_band_rows_must_carry_omission_receipt": True,
                "omission_receipt_requires_drilldown": True,
                "omission_receipt_requires_source_ref": True,
                "authority_ceiling_required_per_projection": True,
                "public_projection_is_reversible_read_model": True,
            },
            "projection_rows": projection_rows,
            "projection_summary": {
                "projection_row_count": len(projection_rows),
                "omission_receipt_count": sum(
                    1 for row in projection_rows if isinstance(row.get("omission_receipt"), dict)
                ),
                "reversible_drilldown_count": sum(
                    1
                    for row in projection_rows
                    if isinstance(row.get("omission_receipt"), dict)
                    and bool(row["omission_receipt"].get("drilldown"))
                ),
                "authority_ceiling_row_count": sum(
                    1 for row in projection_rows if row.get("authority_ceiling_ref")
                ),
                "private_body_export_count": sum(
                    1 for row in projection_rows if row.get("private_body_exported") is True
                ),
                "proof_body_export_count": sum(
                    1 for row in projection_rows if row.get("proof_body_exported") is True
                ),
                "provider_payload_export_count": sum(
                    1 for row in projection_rows if row.get("provider_payload_exported") is True
                ),
                "release_authorized_count": sum(
                    1 for row in projection_rows if row.get("release_authorized") is True
                ),
                "source_mutation_authorized_count": sum(
                    1 for row in projection_rows if row.get("source_mutation_authorized") is True
                ),
            },
            "negative_case_ids": negative_case_ids,
            "safe_to_show": {
                "body_redacted": True,
                "private_paths_omitted": True,
                "proof_bodies_omitted": True,
                "provider_payloads_omitted": True,
                "omitted_content_has_named_drilldown": True,
                "projection_is_read_model_only": True,
            },
            "authority_ceiling": {
                "release_authorized": False,
                "hosted_public_authorized": False,
                "publication_authorized": False,
                "provider_calls_authorized": False,
                "source_mutation_authorized": False,
                "private_data_equivalence_claim": False,
                "whole_system_correctness_claim": False,
                "formal_proof_authority": False,
                "trading_or_financial_advice_authorized": False,
            },
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The projection-safety audit is a public-safe read-model over omission "
                "receipts and authority ceilings. It does not prove every private "
                "projection is lossless, export private bodies, expose proof bodies, "
                "publish provider payloads, mutate source, authorize release, or claim "
                "public/private system equivalence."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def projection_import_map(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_projection_import_map_lens.json"
        import_stages = [
            {
                "stage_id": "select_source_pattern",
                "purpose": "select a macro pattern only after public projection posture is safe",
                "required_evidence": [
                    "source authority ref",
                    "public replacement target",
                    "private-state risk classification",
                ],
            },
            {
                "stage_id": "strip_private_bodies",
                "purpose": "remove raw private source bodies, proof bodies, provider payloads, and private paths",
                "required_evidence": [
                    "omission receipt",
                    "body_redacted=true",
                    "safe_to_show contract",
                ],
            },
            {
                "stage_id": "write_public_replacement",
                "purpose": "land a public fixture, runtime lens, or receipt-backed synthetic replacement",
                "required_evidence": [
                    "public surface ref",
                    "command or endpoint",
                    "fixture or receipt ref",
                ],
            },
            {
                "stage_id": "bind_authority_ceiling",
                "purpose": "state what the public replacement cannot claim before it is surfaced",
                "required_evidence": [
                    "release_authorized=false",
                    "source_mutation_authorized=false",
                    "private_data_equivalence_claim=false",
                ],
            },
            {
                "stage_id": "validate_endpoint_receipt_parity",
                "purpose": "prove command, endpoint, observatory, validator, and receipt point at the same public lens",
                "required_evidence": [
                    "runtime test",
                    "CLI smoke",
                    "launch-compression receipt",
                    "observatory-legibility receipt",
                ],
            },
            {
                "stage_id": "record_reentry_contract",
                "purpose": "rewrite the seed next-wave prompt so future agents extend a fresh cell",
                "required_evidence": [
                    "seed JSON update",
                    "seed Markdown closeout",
                    "work ledger closeout",
                ],
            },
        ]
        import_rows = [
            {
                "map_row_id": "macro_projection_import_protocol_to_intake",
                "source_pattern_id": "macro_projection_import_protocol",
                "source_authority": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::macro_projection_import_protocol",
                "public_surface": "microcosm intake",
                "endpoint": "/intake",
                "public_ref": "receipts/runtime_shell/intake_bridge/observatory_intake_bridge.json",
                "copied": ["public import-plan metadata", "projection-cell status vocabulary"],
                "cleaned": ["macro-private bodies", "raw seed voice", "private path refs"],
                "omitted": ["private source bodies", "unreviewed release claims"],
                "validation_refs": [
                    "tests/test_macro_projection_import_protocol.py",
                    "tests/test_runtime_shell.py::test_runtime_shell_serves_observatory",
                ],
                "authority_ceiling_ref": "microcosm authority::runtime_reveal_import_bridge",
                "projection_status": PASS,
            },
            {
                "map_row_id": "projection_safety_to_runtime_audit",
                "source_pattern_id": "omission_receipt_reversible_projection_boundary",
                "source_authority": "codex/standards/std_command_output_projection.json",
                "public_surface": "microcosm projection-safety",
                "endpoint": "/projection-safety",
                "public_ref": "receipts/runtime_shell/public_projection_safety_audit_lens.json",
                "copied": ["omission receipt rule", "drilldown-before-claim boundary"],
                "cleaned": ["private source refs", "provider payloads"],
                "omitted": ["full private projection bodies"],
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_projection_safety_lens_is_public_safe",
                    "tests/test_launch_compression.py",
                ],
                "authority_ceiling_ref": "microcosm authority::public_projection_safety_audit_lens",
                "projection_status": PASS,
            },
            {
                "map_row_id": "cold_reader_legibility_to_scorecard",
                "source_pattern_id": "cold_reader_route_map",
                "source_authority": "microcosm-substrate/paper_modules/cold_reader_route_map.md",
                "public_surface": "microcosm legibility-scorecard",
                "endpoint": "/legibility-scorecard",
                "public_ref": "receipts/runtime_shell/public_cold_reader_legibility_scorecard_lens.json",
                "copied": ["question-to-command map", "10-minute comprehension budget"],
                "cleaned": ["reader transcripts", "private macro context"],
                "omitted": ["reader success guarantee", "public/secret export claim"],
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_legibility_scorecard_lens_is_public_safe",
                    "tests/test_observatory_legibility.py",
                ],
                "authority_ceiling_ref": "microcosm authority::public_cold_reader_legibility_scorecard_lens",
                "projection_status": PASS,
            },
            {
                "map_row_id": "repository_benchmark_to_transaction_lab",
                "source_pattern_id": "repository_agent_benchmark_transaction_lab",
                "source_authority": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::repository_agent_benchmark_transaction_lab",
                "public_surface": "microcosm benchmark-lab",
                "endpoint": "/benchmark-lab",
                "public_ref": "receipts/runtime_shell/public_repository_benchmark_transaction_lab_lens.json",
                "copied": ["oracle-diff grading shape", "FAIL_TO_PASS/PASS_TO_PASS guard vocabulary"],
                "cleaned": ["private issue bodies", "oracle patch bodies", "live repo paths"],
                "omitted": ["SWE-bench score", "provider execution", "production delivery claim"],
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_benchmark_lab_lens_is_public_safe",
                    "tests/test_cli.py::test_cli_benchmark_lab_smoke",
                ],
                "authority_ceiling_ref": "microcosm authority::public_repository_benchmark_transaction_lab_lens",
                "projection_status": PASS,
            },
            {
                "map_row_id": "agent_reliability_to_replay_gauntlet",
                "source_pattern_id": "agent_reliability_replay_gauntlet",
                "source_authority": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::agent_reliability_replay_gauntlet",
                "public_surface": "microcosm replay-gauntlet",
                "endpoint": "/replay-gauntlet",
                "public_ref": "receipts/runtime_shell/public_agent_reliability_replay_gauntlet_lens.json",
                "copied": ["monitor verdict rows", "containment and quarantine vocabulary"],
                "cleaned": ["live agent traces", "real secret material", "private memory data"],
                "omitted": ["complete security claim", "live tool-call authority"],
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_replay_gauntlet_lens_is_public_safe",
                    "tests/test_cli.py::test_cli_replay_gauntlet_smoke",
                ],
                "authority_ceiling_ref": "microcosm authority::public_agent_reliability_replay_gauntlet_lens",
                "projection_status": PASS,
            },
            {
                "map_row_id": "formal_trace_repair_to_public_lenses",
                "source_pattern_id": "formal_math_verifier_trace_repair_loop_compound",
                "source_authority": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::formal_math_verifier_trace_repair_loop_compound",
                "public_surface": "microcosm trace-lens && microcosm repair-loop",
                "endpoint": "/trace + /repair-loop",
                "public_ref": "receipts/runtime_shell/public_verifier_trace_repair_lens.json",
                "copied": ["failure class taxonomy", "cold-rerun promotion gate"],
                "cleaned": ["proof bodies", "oracle-needed premise ids", "provider payloads"],
                "omitted": ["proof correctness claim", "Lean/Lake execution authority"],
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_trace_lens_is_public_safe",
                    "tests/test_runtime_shell.py::test_runtime_shell_repair_loop_lens_is_public_safe",
                ],
                "authority_ceiling_ref": "microcosm authority::public_verifier_trace_repair_lens",
                "projection_status": PASS,
            },
        ]
        authority_ceiling = {
            "synthetic_public_projection_read_model_only": True,
            "release_authorized": False,
            "hosted_public_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "private_body_export_authorized": False,
            "proof_body_export_authorized": False,
            "provider_payload_export_authorized": False,
            "private_data_equivalence_claim": False,
            "automated_import_guarantee": False,
        }
        negative_case_ids = [
            "private_body_copied_into_public_surface_rejected",
            "omission_receipt_missing_rejected",
            "authority_ceiling_missing_rejected",
            "validation_ref_missing_rejected",
            "endpoint_without_command_rejected",
            "public_replacement_claims_private_equivalence_rejected",
            "automated_import_success_guarantee_rejected",
            "release_claim_from_projection_import_map_rejected",
        ]
        encoded_rows = json.dumps(import_rows, sort_keys=True)
        private_needles = ["/Users/", "src/ai_workflow", "Library/Application Support/Google/Chrome", "sk-"]
        row_count = len(import_rows)
        map_summary = {
            "row_count": row_count,
            "stage_count": len(import_stages),
            "public_surface_count": len({row["public_surface"] for row in import_rows}),
            "validation_ref_count": sum(len(row["validation_refs"]) for row in import_rows),
            "authority_ceiling_row_count": sum(1 for row in import_rows if row.get("authority_ceiling_ref")),
            "private_body_export_count": 0,
            "proof_body_export_count": 0,
            "provider_payload_export_count": 0,
            "automated_import_guarantee": False,
            "release_authorized": False,
        }
        status = (
            PASS
            if row_count >= 6
            and len(import_stages) == 6
            and all(row.get("copied") for row in import_rows)
            and all(row.get("cleaned") for row in import_rows)
            and all(row.get("omitted") for row in import_rows)
            and all(row.get("validation_refs") for row in import_rows)
            and all(row.get("authority_ceiling_ref") for row in import_rows)
            and all(row.get("projection_status") == PASS for row in import_rows)
            and all(
                value is False
                for key, value in authority_ceiling.items()
                if key != "synthetic_public_projection_read_model_only"
            )
            and not any(needle in encoded_rows for needle in private_needles)
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_projection_import_map_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_projection_import_map_lens",
            "organ_family": "projection_import",
            "command": "microcosm projection-import-map",
            "endpoint": "/projection-import-map",
            "projection_import_map_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a projection import map: each public runtime lens names "
                "what was copied from the macro pattern, what was cleaned, what was omitted, "
                "what authority ceiling remains, and which validators prove the projection."
            ),
            "selected_pattern_ids": [
                "macro_projection_import_protocol",
                "omission_receipt_reversible_projection_boundary",
                "cold_reader_route_map",
                "repository_agent_benchmark_transaction_lab",
                "agent_reliability_replay_gauntlet",
                "formal_math_verifier_trace_repair_loop_compound",
            ],
            "import_stages": import_stages,
            "import_rows": import_rows,
            "map_summary": map_summary,
            "negative_case_ids": negative_case_ids,
            "safe_to_show": {
                "body_redacted": True,
                "private_paths_omitted": True,
                "private_source_bodies_omitted": True,
                "proof_bodies_omitted": True,
                "provider_payloads_omitted": True,
                "receipt_refs_only": True,
                "projection_is_read_model_only": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The projection import map is a public-safe read-model over projection "
                "protocol rows. It does not automate imports, prove losslessness, export "
                "private bodies, expose proof bodies or provider payloads, mutate source, "
                "claim private-root equivalence, publish, host, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def import_projector(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_import_projector_contract_lens.json"
        contract_stages = [
            {
                "stage_id": "candidate_selection",
                "purpose": "choose a macro pattern only when it has a public-safe target shape",
                "required_evidence": [
                    "source ref",
                    "public target surface",
                    "private-state risk class",
                ],
            },
            {
                "stage_id": "public_manifest",
                "purpose": "write the projection manifest before copying any implementation detail",
                "required_evidence": [
                    "copied list",
                    "cleaned list",
                    "omitted list",
                    "authority ceiling",
                ],
            },
            {
                "stage_id": "stripping_and_omission",
                "purpose": "replace private bodies with public refs and reversible omission receipts",
                "required_evidence": [
                    "body_redacted=true",
                    "drilldown ref",
                    "negative case ids",
                ],
            },
            {
                "stage_id": "fixture_projection",
                "purpose": "bind the public replacement to synthetic fixtures or metadata-only rows",
                "required_evidence": [
                    "fixture ref",
                    "validator ref",
                    "anti-claim",
                ],
            },
            {
                "stage_id": "runtime_binding",
                "purpose": "expose the projection through a command, endpoint, receipt, and observatory card",
                "required_evidence": [
                    "CLI command",
                    "HTTP endpoint",
                    "receipt path",
                    "HTML section",
                ],
            },
            {
                "stage_id": "validation_and_closeout",
                "purpose": "prove the projection and rewrite the autonomous seed reentry prompt",
                "required_evidence": [
                    "runtime test",
                    "CLI smoke",
                    "launch receipt",
                    "observatory receipt",
                    "seed closeout",
                ],
            },
        ]
        projector_rows = [
            {
                "projector_row_id": "source_candidate_contract",
                "projector_stage": "candidate_selection",
                "source_ref": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl",
                "public_output": "selected_pattern_ids plus source authority refs",
                "owner_route": "build_public_microcosm_substrate_import_prep.py --json",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_import_projector_contract_lens_is_public_safe",
                "authority_ceiling_ref": "microcosm authority::public_import_projector_contract_lens",
                "copied": ["pattern id", "public readiness signal", "source authority pointer"],
                "cleaned": ["private source path bodies", "operator-specific context"],
                "omitted": ["raw macro source bodies", "unreviewed publication claims"],
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "projector_row_id": "public_manifest_contract",
                "projector_stage": "public_manifest",
                "source_ref": "microcosm projection-import-map::import_stages",
                "public_output": "projection manifest row with copied, cleaned, omitted, and validated fields",
                "owner_route": "runtime_shell.projection_import_map",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_projection_import_map_lens_is_public_safe",
                "authority_ceiling_ref": "microcosm authority::public_projection_import_map_lens",
                "copied": ["stage vocabulary", "public replacement refs"],
                "cleaned": ["lossless-import language", "automatic success language"],
                "omitted": ["private implementation bodies", "provider payload bodies"],
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "projector_row_id": "stripping_omission_contract",
                "projector_stage": "stripping_and_omission",
                "source_ref": "microcosm stripping-guard::guard_rows",
                "public_output": "omission receipt with drilldown before claim",
                "owner_route": "runtime_shell.stripping_guard",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_stripping_guard_lens_is_public_safe",
                "authority_ceiling_ref": "microcosm authority::public_stripping_guard_lens",
                "copied": ["guard row id", "public replacement", "strip rule"],
                "cleaned": ["private bodies", "proof bodies", "raw private paths"],
                "omitted": ["secret-like material", "provider prompts and completions"],
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "projector_row_id": "authority_ceiling_contract",
                "projector_stage": "public_manifest",
                "source_ref": "microcosm authority::surface_authority",
                "public_output": "surface-specific authority ceiling and anti-claim",
                "owner_route": "runtime_shell.authority",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_authority_map_is_public_safe",
                "authority_ceiling_ref": "microcosm authority::public_import_projector_contract_lens",
                "copied": ["forbidden authority flags", "safe local exception vocabulary"],
                "cleaned": ["release permission ambiguity", "private-data equivalence claims"],
                "omitted": ["publication authorization", "provider call authorization"],
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "projector_row_id": "fixture_projection_contract",
                "projector_stage": "fixture_projection",
                "source_ref": "microcosm-substrate/examples",
                "public_output": "synthetic fixture or metadata-only replacement",
                "owner_route": "fixture-backed validator",
                "validation_ref": "tests/test_launch_compression.py::test_launch_compression_validator_proves_one_command_aha",
                "authority_ceiling_ref": "microcosm projection-safety::projection_rows",
                "copied": ["synthetic row shape", "public metric names"],
                "cleaned": ["private examples", "real user or account data"],
                "omitted": ["production data", "private benchmark bodies"],
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "projector_row_id": "runtime_surface_contract",
                "projector_stage": "runtime_binding",
                "source_ref": "src/microcosm_core/runtime_shell.py",
                "public_output": "microcosm command, endpoint, receipt, and status row",
                "owner_route": "runtime_shell.<lens>",
                "validation_ref": "tests/test_cli.py::test_cli_import_projector_contract_smoke",
                "authority_ceiling_ref": "microcosm authority::surface_authority",
                "copied": ["schema version", "command id", "endpoint id"],
                "cleaned": ["unstable local file paths", "private route payloads"],
                "omitted": ["source mutation action", "automated import execution"],
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "projector_row_id": "observatory_binding_contract",
                "projector_stage": "runtime_binding",
                "source_ref": "microcosm project-observatory model",
                "public_output": "first-screen HTML section plus JSON drilldown endpoint",
                "owner_route": "runtime_shell._observatory_html",
                "validation_ref": "tests/test_observatory_legibility.py::test_observatory_legibility_validator_exposes_causal_chain",
                "authority_ceiling_ref": "microcosm authority::local_observatory",
                "copied": ["section title", "row counts", "negative cases"],
                "cleaned": ["raw JSON first-screen dependence", "private drilldown payloads"],
                "omitted": ["operator browser state", "private screenshot paths"],
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "projector_row_id": "projection_safety_registration_contract",
                "projector_stage": "stripping_and_omission",
                "source_ref": "microcosm projection-safety::projection_rows",
                "public_output": "registered projection row with omission receipt",
                "owner_route": "runtime_shell.projection_safety",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_projection_safety_lens_is_public_safe",
                "authority_ceiling_ref": "microcosm authority::public_projection_safety_audit_lens",
                "copied": ["projection id", "public ref", "owner route"],
                "cleaned": ["unbounded export claims", "private body assumptions"],
                "omitted": ["proof body text", "provider payload bodies"],
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "projector_row_id": "seed_and_ledger_closeout_contract",
                "projector_stage": "validation_and_closeout",
                "source_ref": "state/meta_missions/type_a_autonomous_seed_loop/seeds/microcosm_substrate_import_autonomous_seed.json",
                "public_output": "seed closeout, next reentry prompt, Work Ledger append, and scoped landing attempt",
                "owner_route": "type_a_autonomous_seed_loop",
                "validation_ref": "kernel.py --validate-seed-heartbeat",
                "authority_ceiling_ref": "microcosm landing-replay::scoped_commit_requires_head_advance",
                "copied": ["selected import cell", "commands/tests", "next reentry prompt"],
                "cleaned": ["private prompt bodies", "unlanded release language"],
                "omitted": ["operator raw seed voice", "unreviewed publication claims"],
                "source_mutation_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
        ]
        authority_ceiling = {
            "projector_contract_read_model_only": True,
            "release_authorized": False,
            "hosted_public_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "private_body_export_authorized": False,
            "proof_body_export_authorized": False,
            "provider_payload_export_authorized": False,
            "generated_region_hand_edit_authorized": False,
            "automated_import_execution_authorized": False,
            "private_data_equivalence_claim": False,
            "lossless_projection_claim": False,
        }
        negative_case_ids = [
            "private_source_body_copied_into_projector_rejected",
            "projector_row_without_omission_receipt_rejected",
            "projector_row_without_authority_ceiling_rejected",
            "projector_row_without_validation_ref_rejected",
            "generated_region_hand_edit_claim_rejected",
            "automated_import_execution_claim_rejected",
            "provider_payload_export_rejected",
            "release_claim_from_projector_rejected",
            "lossless_private_projection_claim_rejected",
        ]
        encoded_rows = json.dumps(projector_rows, sort_keys=True)
        private_needles = ["/Users/", "Library/Application Support/Google", "sk-"]
        projector_summary = {
            "row_count": len(projector_rows),
            "stage_count": len(contract_stages),
            "source_ref_count": sum(1 for row in projector_rows if row.get("source_ref")),
            "owner_route_count": sum(1 for row in projector_rows if row.get("owner_route")),
            "validation_ref_count": sum(1 for row in projector_rows if row.get("validation_ref")),
            "authority_ceiling_row_count": sum(
                1 for row in projector_rows if row.get("authority_ceiling_ref")
            ),
            "negative_case_count": len(negative_case_ids),
            "source_mutation_authorized_count": sum(
                1 for row in projector_rows if row.get("source_mutation_authorized") is True
            ),
            "generated_region_hand_edit_authorized_count": sum(
                1
                for row in projector_rows
                if row.get("generated_region_hand_edit_authorized") is True
            ),
            "private_body_export_count": sum(
                1 for row in projector_rows if row.get("private_body_exported") is True
            ),
            "proof_body_export_count": sum(
                1 for row in projector_rows if row.get("proof_body_exported") is True
            ),
            "provider_payload_export_count": sum(
                1 for row in projector_rows if row.get("provider_payload_exported") is True
            ),
            "release_authorized_count": sum(
                1 for row in projector_rows if row.get("release_authorized") is True
            ),
        }
        status = (
            PASS
            if len(projector_rows) == 9
            and len(contract_stages) == 6
            and all(row.get("copied") for row in projector_rows)
            and all(row.get("cleaned") for row in projector_rows)
            and all(row.get("omitted") for row in projector_rows)
            and all(row.get("validation_ref") for row in projector_rows)
            and all(row.get("authority_ceiling_ref") for row in projector_rows)
            and all(row.get("private_body_exported") is False for row in projector_rows)
            and all(row.get("proof_body_exported") is False for row in projector_rows)
            and all(row.get("provider_payload_exported") is False for row in projector_rows)
            and all(row.get("source_mutation_authorized") is False for row in projector_rows)
            and all(row.get("generated_region_hand_edit_authorized") is False for row in projector_rows)
            and all(row.get("release_authorized") is False for row in projector_rows)
            and all(
                value is False
                for key, value in authority_ceiling.items()
                if key != "projector_contract_read_model_only"
            )
            and authority_ceiling.get("projector_contract_read_model_only") is True
            and not any(needle in encoded_rows for needle in private_needles)
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_import_projector_contract_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_import_projector_contract_lens",
            "organ_family": "projection_import",
            "command": "microcosm import-projector",
            "endpoint": "/import-projector",
            "import_projector_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a repeatable import-projector contract: future "
                "macro patterns must name what was copied, cleaned, omitted, bounded, "
                "validated, surfaced, and closed out before they become public runtime cells."
            ),
            "selected_pattern_ids": [
                "macro_projection_import_protocol",
                "omission_receipt_reversible_projection_boundary",
                "public_private_stripping_guard",
                "route_cleanup_contract_plane",
                "microcosm_substrate_import_seed",
            ],
            "contract_stages": contract_stages,
            "projector_rows": projector_rows,
            "projector_summary": projector_summary,
            "negative_case_ids": negative_case_ids,
            "safe_to_show": {
                "body_redacted": True,
                "private_paths_omitted": True,
                "private_source_bodies_omitted": True,
                "proof_bodies_omitted": True,
                "provider_payloads_omitted": True,
                "generated_regions_require_owner_builders": True,
                "projector_is_read_model_only": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The import-projector contract is a public-safe read-model and checklist. "
                "It does not execute imports, copy private source bodies, expose proof "
                "bodies or provider payloads, hand-edit generated regions, mutate source, "
                "claim lossless private projection, publish, host, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def option_surface_lens(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_compression_profile_option_surface_lens.json"
        import_plan_ref = (
            "examples/macro_projection_import_protocol/"
            "exported_projection_import_bundle/import_plan.json"
        )
        import_plan = _read_json_if_exists(self.root / import_plan_ref)
        proposed_cells = _rows(import_plan, "proposed_cells")
        option_cell = next(
            (
                row
                for row in proposed_cells
                if "compression_profile_governed_option_surface"
                in row.get("selected_pattern_ids", [])
            ),
            {},
        )
        import_projector = self.import_projector()
        projection_import_map = self.projection_import_map()
        option_stages = [
            {
                "stage_id": "candidate_pattern_anchor",
                "purpose": "anchor a compression-profile option surface to an import-plan cell",
                "required_evidence": [
                    "selected pattern id",
                    "source ref",
                    "projection cell id",
                ],
            },
            {
                "stage_id": "public_profile_contract",
                "purpose": "name the public profiles and their reader-facing tradeoffs",
                "required_evidence": [
                    "profile id",
                    "allowed public output",
                    "private bodies omitted",
                ],
            },
            {
                "stage_id": "sidecar_projection",
                "purpose": "keep generated profile evidence in receipts and sidecars, not prompt text",
                "required_evidence": [
                    "sidecar ref",
                    "receipt ref",
                    "body_redacted=true",
                ],
            },
            {
                "stage_id": "runtime_binding",
                "purpose": "surface the option profile through command, endpoint, observatory, and authority rows",
                "required_evidence": [
                    "CLI command",
                    "HTTP endpoint",
                    "authority ceiling",
                ],
            },
            {
                "stage_id": "validation",
                "purpose": "prove option-profile projection parity across tests and validators",
                "required_evidence": [
                    "runtime test",
                    "CLI smoke",
                    "launch-compression receipt",
                    "observatory-legibility receipt",
                ],
            },
            {
                "stage_id": "reentry_contract",
                "purpose": "make the next autonomous pass consume the next importable cell",
                "required_evidence": [
                    "seed JSON closeout",
                    "seed Markdown closeout",
                    "work ledger closeout",
                ],
            },
        ]
        option_rows = [
            {
                "option_row_id": "compression_profile_candidate_anchor",
                "option_stage": "candidate_pattern_anchor",
                "source_ref": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::compression_profile_governed_option_surface",
                "public_output": "selected pattern id plus projection cell ref",
                "copied": ["pattern id", "source authority pointer", "projection cell id"],
                "cleaned": ["private source path bodies", "volatile run counters"],
                "omitted": ["raw macro context", "operator prompts", "private route payloads"],
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_option_surface_lens_is_public_safe",
                "authority_ceiling_ref": "microcosm authority::public_compression_profile_option_surface_lens",
                "body_redacted": True,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "source_mutation_authorized": False,
                "profile_switch_execution_authorized": False,
                "release_authorized": False,
            },
            {
                "option_row_id": "quick_profile_public_card",
                "option_stage": "public_profile_contract",
                "source_ref": "microcosm import-projector::candidate_selection",
                "public_output": "quick profile as a bounded cold-reader card",
                "copied": ["profile name", "reader budget", "surface list"],
                "cleaned": ["live route rankings", "private phase-specific counts"],
                "omitted": ["full private context pack", "private operator history"],
                "validation_ref": "tests/test_cli.py::test_cli_option_surface_lens_smoke",
                "authority_ceiling_ref": "microcosm authority::public_compression_profile_option_surface_lens",
                "body_redacted": True,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "source_mutation_authorized": False,
                "profile_switch_execution_authorized": False,
                "release_authorized": False,
            },
            {
                "option_row_id": "full_profile_sidecar_boundary",
                "option_stage": "sidecar_projection",
                "source_ref": "microcosm route-cleanup::option_surface_hygiene",
                "public_output": "full profile points at sidecar/receipt refs instead of prompt-body expansion",
                "copied": ["sidecar vocabulary", "receipt-first proof rule"],
                "cleaned": ["unbounded prompt stuffing", "private note bodies"],
                "omitted": ["raw sidecar payload bodies", "private generated-region diffs"],
                "validation_ref": "tests/test_launch_compression.py::test_launch_compression_validator_proves_one_command_aha",
                "authority_ceiling_ref": "microcosm authority::public_compression_profile_option_surface_lens",
                "body_redacted": True,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "source_mutation_authorized": False,
                "profile_switch_execution_authorized": False,
                "release_authorized": False,
            },
            {
                "option_row_id": "observatory_option_surface_card",
                "option_stage": "runtime_binding",
                "source_ref": "microcosm project-observatory::json_drilldowns",
                "public_output": "first-screen option-surface card and JSON drilldown endpoint",
                "copied": ["section title", "row count", "authority booleans"],
                "cleaned": ["raw JSON first-screen dependence", "private drilldown payloads"],
                "omitted": ["live operator browser state", "private screenshot paths"],
                "validation_ref": "tests/test_observatory_legibility.py::test_observatory_legibility_validator_exposes_causal_chain",
                "authority_ceiling_ref": "microcosm authority::local_observatory",
                "body_redacted": True,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "source_mutation_authorized": False,
                "profile_switch_execution_authorized": False,
                "release_authorized": False,
            },
            {
                "option_row_id": "validator_option_profile_parity",
                "option_stage": "validation",
                "source_ref": "microcosm launch-compression::assertions",
                "public_output": "validator checks command, endpoint, receipt, and observatory parity",
                "copied": ["status assertion", "endpoint assertion", "no-private-export assertion"],
                "cleaned": ["green-check-only posture", "unbound profile claims"],
                "omitted": ["release-readiness claim", "automatic profile correctness guarantee"],
                "validation_ref": "tests/test_observatory_legibility.py",
                "authority_ceiling_ref": "microcosm authority::public_compression_profile_option_surface_lens",
                "body_redacted": True,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "source_mutation_authorized": False,
                "profile_switch_execution_authorized": False,
                "release_authorized": False,
            },
            {
                "option_row_id": "seed_reentry_option_profile_contract",
                "option_stage": "reentry_contract",
                "source_ref": "state/meta_missions/type_a_autonomous_seed_loop/seeds/microcosm_substrate_import_autonomous_seed.json",
                "public_output": "seed closeout names option-surface consumption and next importable cell",
                "copied": ["selected import cell", "validation commands", "next reentry lane"],
                "cleaned": ["raw seed voice", "unreviewed public release language"],
                "omitted": ["operator private prompt body", "publication authorization"],
                "validation_ref": "kernel.py --validate-seed-heartbeat",
                "authority_ceiling_ref": "microcosm landing-replay::scoped_commit_requires_head_advance",
                "body_redacted": True,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "source_mutation_authorized": False,
                "profile_switch_execution_authorized": False,
                "release_authorized": False,
            },
        ]
        authority_ceiling = {
            "option_surface_read_model_only": True,
            "release_authorized": False,
            "hosted_public_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "generated_region_hand_edit_authorized": False,
            "private_body_export_authorized": False,
            "provider_payload_export_authorized": False,
            "profile_switch_execution_authorized": False,
            "automatic_profile_selection_authorized": False,
            "private_data_equivalence_claim": False,
            "lossless_projection_claim": False,
        }
        negative_case_ids = [
            "private_profile_body_export_rejected",
            "option_surface_without_import_projector_ref_rejected",
            "profile_switch_execution_claim_rejected",
            "generated_region_hand_edit_claim_rejected",
            "sidecar_body_dump_rejected",
            "validation_ref_missing_rejected",
            "release_claim_from_option_surface_rejected",
            "lossless_profile_projection_claim_rejected",
        ]
        encoded_rows = json.dumps(option_rows, sort_keys=True)
        private_needles = ["/Users/", "Library/Application Support/Google", "sk-"]
        option_surface_summary = {
            "row_count": len(option_rows),
            "stage_count": len(option_stages),
            "source_ref_count": sum(1 for row in option_rows if row.get("source_ref")),
            "validation_ref_count": sum(1 for row in option_rows if row.get("validation_ref")),
            "authority_ceiling_row_count": sum(
                1 for row in option_rows if row.get("authority_ceiling_ref")
            ),
            "negative_case_count": len(negative_case_ids),
            "private_body_export_count": sum(
                1 for row in option_rows if row.get("private_body_exported") is True
            ),
            "provider_payload_export_count": sum(
                1 for row in option_rows if row.get("provider_payload_exported") is True
            ),
            "source_mutation_authorized_count": sum(
                1 for row in option_rows if row.get("source_mutation_authorized") is True
            ),
            "profile_switch_execution_authorized_count": sum(
                1
                for row in option_rows
                if row.get("profile_switch_execution_authorized") is True
            ),
            "release_authorized_count": sum(
                1 for row in option_rows if row.get("release_authorized") is True
            ),
        }
        status = (
            PASS
            if len(option_rows) == 6
            and len(option_stages) == 6
            and "compression_profile_governed_option_surface"
            in option_cell.get("selected_pattern_ids", [])
            and all(row.get("copied") for row in option_rows)
            and all(row.get("cleaned") for row in option_rows)
            and all(row.get("omitted") for row in option_rows)
            and all(row.get("validation_ref") for row in option_rows)
            and all(row.get("authority_ceiling_ref") for row in option_rows)
            and all(row.get("body_redacted") is True for row in option_rows)
            and all(row.get("private_body_exported") is False for row in option_rows)
            and all(row.get("provider_payload_exported") is False for row in option_rows)
            and all(row.get("source_mutation_authorized") is False for row in option_rows)
            and all(
                row.get("profile_switch_execution_authorized") is False
                for row in option_rows
            )
            and all(row.get("release_authorized") is False for row in option_rows)
            and all(
                value is False
                for key, value in authority_ceiling.items()
                if key != "option_surface_read_model_only"
            )
            and authority_ceiling.get("option_surface_read_model_only") is True
            and import_projector.get("status") == PASS
            and projection_import_map.get("status") == PASS
            and not any(needle in encoded_rows for needle in private_needles)
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_compression_profile_option_surface_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_compression_profile_option_surface_lens",
            "organ_family": "projection_import",
            "command": "microcosm option-surface-lens",
            "endpoint": "/option-surface-lens",
            "option_surface_lens_ref": _public_relative(lens_path, self.root),
            "import_projector_ref": import_projector.get("import_projector_ref"),
            "projection_import_map_ref": projection_import_map.get("projection_import_map_ref"),
            "public_claim": (
                "Microcosm exposes the compression-profile governed option surface as a "
                "public read-model: profile choice becomes command, endpoint, receipt, "
                "sidecar, validation, and authority-ceiling rows without importing private bodies."
            ),
            "selected_pattern_ids": [
                "compression_profile_governed_option_surface",
                "authority_boundary_anti_claim",
                "macro_projection_import_protocol",
            ],
            "projection_cell": {
                "cell_id": option_cell.get("cell_id"),
                "source_refs": option_cell.get("source_refs", []),
                "target_refs": option_cell.get("target_refs", []),
                "validation_refs": option_cell.get("validation_refs", []),
                "authority_ceiling": option_cell.get("authority_ceiling"),
                "body_copied": option_cell.get("body_copied") is True,
                "body_redacted": option_cell.get("body_redacted") is True,
            },
            "import_plan_ref": import_plan_ref,
            "option_stages": option_stages,
            "option_rows": option_rows,
            "option_surface_summary": option_surface_summary,
            "negative_case_ids": negative_case_ids,
            "safe_to_show": {
                "body_redacted": True,
                "private_paths_omitted": True,
                "private_source_bodies_omitted": True,
                "provider_payloads_omitted": True,
                "sidecar_bodies_omitted": True,
                "option_surface_is_read_model_only": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The option-surface lens is a public-safe read-model over compression "
                "profile projection rules. It does not switch runtime profiles, select "
                "options automatically, export private context or sidecar bodies, call "
                "providers, hand-edit generated regions, mutate source, claim lossless "
                "private projection, publish, host, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def stripping_guard(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_stripping_guard_lens.json"
        guard_rows = [
            {
                "guard_row_id": "private_source_body_strip",
                "source_risk": "private source bodies can orient implementation but cannot be copied out",
                "public_replacement": "receipt ref, owner route, omission receipt, and redacted summary",
                "strip_rule": "replace body with public ref and body_redacted=true",
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_stripping_guard_lens_is_public_safe",
                    "tests/test_launch_compression.py",
                ],
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "raw_private_path_exported": False,
                "secret_token_exported": False,
                "release_authorized": False,
            },
            {
                "guard_row_id": "proof_body_strip",
                "source_risk": "formal proof attempts may contain private working state or unreviewed proof claims",
                "public_replacement": "metadata-only failure class, evidence cell id, and anti-claim",
                "strip_rule": "export claim strength metadata, never proof body text",
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_trace_lens_is_public_safe",
                    "tests/test_runtime_shell.py::test_runtime_shell_evidence_cell_lens_is_public_safe",
                ],
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "raw_private_path_exported": False,
                "secret_token_exported": False,
                "release_authorized": False,
            },
            {
                "guard_row_id": "provider_payload_strip",
                "source_risk": "provider prompts, completions, and tool payloads are not public evidence",
                "public_replacement": "synthetic case id, decision row, and validator receipt",
                "strip_rule": "publish only public synthetic rows and provider_call_authorized=false",
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_replay_gauntlet_lens_is_public_safe",
                    "tests/test_runtime_shell.py::test_runtime_shell_benchmark_lab_lens_is_public_safe",
                ],
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "raw_private_path_exported": False,
                "secret_token_exported": False,
                "release_authorized": False,
            },
            {
                "guard_row_id": "raw_private_path_redaction",
                "source_risk": "absolute private paths can leak operator identity and host layout",
                "public_replacement": "root-relative public refs or stable command ids",
                "strip_rule": "reject absolute private paths and private-root identifiers from public JSON",
                "validation_refs": [
                    "tests/test_runtime_shell.py",
                    "tests/test_observatory_legibility.py",
                ],
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "raw_private_path_exported": False,
                "secret_token_exported": False,
                "release_authorized": False,
            },
            {
                "guard_row_id": "secret_token_strip",
                "source_risk": "secret-like strings require fail-closed handling and cannot be evidence",
                "public_replacement": "negative case id and no-completeness anti-claim",
                "strip_rule": "strip example token material and deny complete secret-scanner claims",
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_stripping_guard_lens_is_public_safe",
                    "tests/test_observatory_legibility.py",
                ],
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "raw_private_path_exported": False,
                "secret_token_exported": False,
                "release_authorized": False,
            },
            {
                "guard_row_id": "financial_advice_strip",
                "source_risk": "prediction and finance reasoning can be shown as synthetic mechanics only",
                "public_replacement": "no-advice fixture row and synthetic prediction lens",
                "strip_rule": "deny trading advice, live market claims, and private dossiers",
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_prediction_lens_is_public_safe",
                    "tests/test_cli.py::test_cli_prediction_lens_smoke",
                ],
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "raw_private_path_exported": False,
                "secret_token_exported": False,
                "release_authorized": False,
            },
            {
                "guard_row_id": "source_mutation_denial",
                "source_risk": "public runtime commands should inspect, compile, or write receipts only",
                "public_replacement": "authority row and explicit source_mutation_authorized=false",
                "strip_rule": "route mutations through owner tests/commits, not runtime lens commands",
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_authority_map_is_public_safe",
                    "tests/test_runtime_shell.py::test_runtime_shell_landing_replay_lens_is_public_safe",
                ],
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "raw_private_path_exported": False,
                "secret_token_exported": False,
                "release_authorized": False,
            },
            {
                "guard_row_id": "release_and_private_equivalence_denial",
                "source_risk": "a public microcosm is a projection, not release approval or private-root equivalence",
                "public_replacement": "anti-claim row, authority ceiling, and release_authorized=false",
                "strip_rule": "deny publication, hosted-public, benchmark, and secret-export claims",
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_tour_is_public_safe",
                    "tests/test_runtime_shell.py::test_runtime_shell_legibility_scorecard_lens_is_public_safe",
                ],
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "raw_private_path_exported": False,
                "secret_token_exported": False,
                "release_authorized": False,
            },
        ]
        authority_ceiling = {
            "read_model_only": True,
            "private_body_export_authorized": False,
            "proof_body_export_authorized": False,
            "provider_payload_export_authorized": False,
            "raw_private_path_export_authorized": False,
            "secret_detection_completeness_claim": False,
            "financial_advice_authorized": False,
            "source_mutation_authorized": False,
            "private_data_equivalence_claim": False,
            "automated_import_guarantee": False,
            "release_authorized": False,
        }
        negative_case_ids = [
            "private_body_export_rejected",
            "proof_body_export_rejected",
            "provider_payload_export_rejected",
            "raw_private_path_export_rejected",
            "secret_scanner_claim_rejected",
            "financial_advice_export_rejected",
            "source_mutation_authority_rejected",
            "release_or_private_equivalence_claim_rejected",
        ]
        encoded_rows = json.dumps(guard_rows, sort_keys=True)
        private_needles = ["/Users/", "src/ai_workflow", "Library/Application Support/Google/Chrome", "sk-"]
        guard_summary = {
            "guard_row_count": len(guard_rows),
            "negative_case_count": len(negative_case_ids),
            "validation_ref_count": sum(len(row["validation_refs"]) for row in guard_rows),
            "private_body_export_count": sum(
                1 for row in guard_rows if row.get("private_body_exported") is True
            ),
            "proof_body_export_count": sum(
                1 for row in guard_rows if row.get("proof_body_exported") is True
            ),
            "provider_payload_export_count": sum(
                1 for row in guard_rows if row.get("provider_payload_exported") is True
            ),
            "raw_private_path_export_count": sum(
                1 for row in guard_rows if row.get("raw_private_path_exported") is True
            ),
            "secret_token_export_count": sum(
                1 for row in guard_rows if row.get("secret_token_exported") is True
            ),
            "release_authorized": False,
        }
        status = (
            PASS
            if len(guard_rows) == 8
            and len(negative_case_ids) == 8
            and all(row.get("validation_refs") for row in guard_rows)
            and all(row.get("private_body_exported") is False for row in guard_rows)
            and all(row.get("proof_body_exported") is False for row in guard_rows)
            and all(row.get("provider_payload_exported") is False for row in guard_rows)
            and all(row.get("raw_private_path_exported") is False for row in guard_rows)
            and all(row.get("secret_token_exported") is False for row in guard_rows)
            and all(row.get("release_authorized") is False for row in guard_rows)
            and all(
                value is False
                for key, value in authority_ceiling.items()
                if key != "read_model_only"
            )
            and not any(needle in encoded_rows for needle in private_needles)
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_private_stripping_guard_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_stripping_guard_lens",
            "organ_family": "projection_import",
            "command": "microcosm stripping-guard",
            "endpoint": "/stripping-guard",
            "stripping_guard_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a public/private stripping guard: every public-facing "
                "projection names the private body, proof body, provider payload, raw "
                "path, secret-completeness, finance, source-mutation, and release claims "
                "it must reject before becoming a public runtime surface."
            ),
            "selected_pattern_ids": [
                "macro_projection_import_protocol",
                "omission_receipt_reversible_projection_boundary",
                "public_private_stripping_protocol",
            ],
            "guard_rows": guard_rows,
            "guard_summary": guard_summary,
            "negative_case_ids": negative_case_ids,
            "safe_to_show": {
                "body_redacted": True,
                "private_paths_omitted": True,
                "private_source_bodies_omitted": True,
                "proof_bodies_omitted": True,
                "provider_payloads_omitted": True,
                "secret_examples_omitted": True,
                "projection_is_read_model_only": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The stripping guard is a public-safe read-model over export-denial rules. "
                "It is not a complete secret scanner, does not export private bodies, "
                "proof bodies, provider payloads, raw private paths, or example secret "
                "material, does not give financial advice, mutate source, prove "
                "public/secret export, publish, host, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def standards_control(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_standards_control_lens.json"
        registry_ref = "core/standards_registry.json"
        pressure_ref = "core/public_standard_pressure.json"
        validator_coverage_ref = "core/preflight_support/validator_receipt_coverage_map_v1.json"
        acceptance_ref = "core/acceptance/first_wave_acceptance.json"
        fixture_manifest_ref = "core/fixture_manifests/standards_meta_diagnostics.fixture_manifest.json"
        registry = _read_json_if_exists(self.root / registry_ref)
        pressure = _read_json_if_exists(self.root / pressure_ref)
        validator_coverage = _read_json_if_exists(self.root / validator_coverage_ref)
        acceptance = _read_json_if_exists(self.root / acceptance_ref)
        fixture_manifest = _read_json_if_exists(self.root / fixture_manifest_ref)
        pressure_rows = _rows(pressure, "rows")
        receipt_coverage = _strings(validator_coverage.get("receipt_coverage"))
        acceptance_commands = _strings(acceptance.get("acceptance_commands"))
        fixture_manifest_count = len(list((self.root / "core/fixture_manifests").glob("*.fixture_manifest.json")))
        standard_count = int(registry.get("standard_count") or len(_rows(registry, "standards")) or 0)
        standards_rows = [
            {
                "control_row_id": "standards_registry_contract",
                "source_ref": registry_ref,
                "public_role": "public standard index and first-wave required standard surface",
                "required_signal": "standard_count and authority_ceiling present",
                "observed_count": standard_count,
                "validation_refs": [
                    "tests/test_runtime_shell.py::test_runtime_shell_standards_control_lens_is_public_safe",
                    "tests/test_cli.py::test_cli_standards_control_smoke",
                ],
                "source_authority_claim": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "control_row_id": "public_standard_pressure_contract",
                "source_ref": pressure_ref,
                "public_role": "project-local standard pressure rows used by architecture/explanation state",
                "required_signal": "rows carry authority_boundary and source refs",
                "observed_count": len(pressure_rows),
                "validation_refs": [
                    "tests/test_launch_compression.py",
                    "tests/test_observatory_legibility.py",
                ],
                "source_authority_claim": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "control_row_id": "validator_receipt_coverage_contract",
                "source_ref": validator_coverage_ref,
                "public_role": "receipt coverage map for clean-clone and validator evidence",
                "required_signal": "receipt_coverage entries are refs, not source bodies",
                "observed_count": len(receipt_coverage),
                "validation_refs": [
                    "core/preflight_support/validator_receipt_coverage_map_v1.json",
                    "tests/test_runtime_shell.py::test_runtime_shell_standards_control_lens_is_public_safe",
                ],
                "source_authority_claim": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "control_row_id": "acceptance_gate_contract",
                "source_ref": acceptance_ref,
                "public_role": "first-wave acceptance command set and authority organ map",
                "required_signal": "acceptance commands remain validation commands, not release approval",
                "observed_count": len(acceptance_commands),
                "validation_refs": [
                    "core/acceptance/first_wave_acceptance.json",
                    "microcosm standards-registry --registry core/standards_registry.json",
                ],
                "source_authority_claim": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "control_row_id": "fixture_manifest_contract",
                "source_ref": fixture_manifest_ref,
                "public_role": "standards meta-diagnostics fixture manifest and negative cases",
                "required_signal": "fixture inputs include explicit negative cases and anti-claim",
                "observed_count": fixture_manifest_count,
                "validation_refs": [
                    "core/fixture_manifests/standards_meta_diagnostics.fixture_manifest.json",
                    "receipts/acceptance/first_wave/standards_meta_diagnostics_fixture_acceptance.json",
                ],
                "source_authority_claim": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "control_row_id": "docs_entry_contract",
                "source_ref": "README.md + AGENTS.md + skills/cold_start_navigation.md",
                "public_role": "human entry docs name standard pressure without private doctrine bodies",
                "required_signal": "docs point to runtime commands and public JSON refs",
                "observed_count": 3,
                "validation_refs": [
                    "tests/test_launch_compression.py",
                    "tests/test_observatory_legibility.py",
                ],
                "source_authority_claim": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "control_row_id": "authority_ceiling_contract",
                "source_ref": "microcosm authority::public_standards_control_lens",
                "public_role": "global authority map lists standards control as read-model only",
                "required_signal": "release, provider, source mutation, and secret export are false",
                "observed_count": 1,
                "validation_refs": [
                    "microcosm authority",
                    "tests/test_runtime_shell.py::test_runtime_shell_authority_map_is_public_safe",
                ],
                "source_authority_claim": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
            {
                "control_row_id": "projection_safety_contract",
                "source_ref": "microcosm projection-safety::public_standards_control_lens",
                "public_role": "compressed standards-control projection has omission receipt and drilldown",
                "required_signal": "projection row is reversible and carries authority ceiling",
                "observed_count": 1,
                "validation_refs": [
                    "microcosm projection-safety",
                    "tests/test_runtime_shell.py::test_runtime_shell_projection_safety_lens_is_public_safe",
                ],
                "source_authority_claim": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
                "release_authorized": False,
            },
        ]
        negative_case_ids = [
            "standard_without_registry_row_rejected",
            "public_standard_pressure_without_authority_boundary_rejected",
            "validator_receipt_missing_from_coverage_map_rejected",
            "acceptance_command_treated_as_release_approval_rejected",
            "fixture_manifest_without_negative_cases_rejected",
            "docs_claim_without_runtime_command_rejected",
            "standards_projection_claims_private_source_authority_rejected",
            "release_or_publication_claim_from_standards_pass_rejected",
        ]
        authority_ceiling = {
            "read_model_only": True,
            "standards_registry_source_authority": False,
            "private_body_export_authorized": False,
            "proof_body_export_authorized": False,
            "provider_payload_export_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "private_data_equivalence_claim": False,
            "standards_completeness_claim": False,
            "release_authorized": False,
        }
        encoded_rows = json.dumps(standards_rows, sort_keys=True)
        private_needles = ["/Users/", "src/ai_workflow", "Library/Application Support/Google/Chrome", "sk-"]
        standards_summary = {
            "standards_control_row_count": len(standards_rows),
            "standard_count": standard_count,
            "standard_pressure_row_count": len(pressure_rows),
            "validator_receipt_ref_count": len(receipt_coverage),
            "acceptance_command_count": len(acceptance_commands),
            "fixture_manifest_count": fixture_manifest_count,
            "negative_case_count": len(negative_case_ids),
            "validation_ref_count": sum(len(row["validation_refs"]) for row in standards_rows),
            "private_body_export_count": sum(
                1 for row in standards_rows if row.get("private_body_exported") is True
            ),
            "proof_body_export_count": sum(
                1 for row in standards_rows if row.get("proof_body_exported") is True
            ),
            "provider_payload_export_count": sum(
                1 for row in standards_rows if row.get("provider_payload_exported") is True
            ),
            "source_authority_claim_count": sum(
                1 for row in standards_rows if row.get("source_authority_claim") is True
            ),
            "release_authorized": False,
        }
        status = (
            PASS
            if len(standards_rows) == 8
            and len(negative_case_ids) == 8
            and standard_count >= 1
            and len(pressure_rows) >= 1
            and len(receipt_coverage) >= 1
            and len(acceptance_commands) >= 1
            and fixture_manifest_count >= 1
            and all(row.get("validation_refs") for row in standards_rows)
            and all(row.get("source_authority_claim") is False for row in standards_rows)
            and all(row.get("private_body_exported") is False for row in standards_rows)
            and all(row.get("proof_body_exported") is False for row in standards_rows)
            and all(row.get("provider_payload_exported") is False for row in standards_rows)
            and all(row.get("release_authorized") is False for row in standards_rows)
            and all(value is False for key, value in authority_ceiling.items() if key != "read_model_only")
            and not any(needle in encoded_rows for needle in private_needles)
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_standards_control_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_standards_control_lens",
            "organ_family": "standards_control",
            "command": "microcosm standards-control",
            "endpoint": "/standards-control",
            "standards_control_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a public standards-control lens: standards registry, "
                "standard pressure, validator receipt coverage, fixture manifests, "
                "acceptance commands, docs, authority ceilings, and projection safety "
                "are checked as one read-model before public claims can strengthen."
            ),
            "selected_pattern_ids": [
                "standards_meta_diagnostics",
                "public_standard_pressure_contract",
                "validator_receipt_coverage_map",
                "omission_receipt_reversible_projection_boundary",
            ],
            "input_refs": {
                "standards_registry": registry_ref,
                "public_standard_pressure": pressure_ref,
                "validator_receipt_coverage_map": validator_coverage_ref,
                "first_wave_acceptance": acceptance_ref,
                "standards_meta_fixture_manifest": fixture_manifest_ref,
            },
            "source_statuses": {
                "standards_registry_schema": registry.get("schema_version"),
                "public_standard_pressure_schema": pressure.get("schema_version"),
                "validator_receipt_coverage_schema": validator_coverage.get("schema_version"),
                "acceptance_command_count": len(acceptance_commands),
                "fixture_manifest_schema": fixture_manifest.get("schema_version"),
            },
            "standards_rows": standards_rows,
            "standards_summary": standards_summary,
            "negative_case_ids": negative_case_ids,
            "safe_to_show": {
                "body_redacted": True,
                "private_paths_omitted": True,
                "private_source_bodies_omitted": True,
                "proof_bodies_omitted": True,
                "provider_payloads_omitted": True,
                "receipt_refs_only": True,
                "projection_is_read_model_only": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The standards-control lens is a public-safe read-model over existing "
                "standard, validator, fixture, acceptance, docs, and authority surfaces. "
                "It does not make the standards registry source authority, prove complete "
                "coverage, export private bodies, expose proof bodies or provider payloads, "
                "call providers, mutate source, claim secret export, publish, host, "
                "or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def hook_coverage(self) -> dict[str, Any]:
        route_ref = "receipts/first_wave/agent_route_observability_runtime/route_compliance_audit.json"
        hook_ref = "receipts/first_wave/agent_route_observability_runtime/hook_shadow_coverage.json"
        debt_ref = "receipts/first_wave/agent_route_observability_runtime/debt_retirement_receipt.json"
        lease_ref = "receipts/first_wave/agent_route_observability_runtime/route_lease_mode_control_receipt.json"
        route = _read_json_if_exists(self.root / route_ref)
        hook = _read_json_if_exists(self.root / hook_ref)
        debt = _read_json_if_exists(self.root / debt_ref)
        lease = _read_json_if_exists(self.root / lease_ref)
        lens_path = self.runtime_receipt_dir / "public_hook_intervention_coverage_lens.json"

        route_decisions = _rows(route, "route_compliance_decisions")
        actor_axis_decisions = _rows(route, "actor_axis_decisions")
        hook_shadow_decisions = _rows(hook, "hook_shadow_decisions")
        debt_decisions = _rows(debt, "anti_pattern_debt_decisions")
        lease_decisions = _rows(lease, "route_lease_feedback_decisions")
        missing_authority = _strings(hook.get("missing_authority"))
        hook_repair_classes = _strings(hook.get("mapped_repair_classes"))
        observed_negative_cases = sorted(
            set(
                [
                    *(
                        str(key)
                        for key in route.get("observed_negative_cases", {})
                        if isinstance(route.get("observed_negative_cases"), dict)
                    ),
                    *(
                        str(key)
                        for key in lease.get("observed_negative_cases", {})
                        if isinstance(lease.get("observed_negative_cases"), dict)
                    ),
                    *(
                        str(key)
                        for key in hook.get("observed_negative_cases", {})
                        if isinstance(hook.get("observed_negative_cases"), dict)
                    ),
                ]
            )
        )
        source_pattern_ids = list(
            dict.fromkeys(
                [
                    *_strings(route.get("source_pattern_ids")),
                    *_strings(hook.get("source_pattern_ids")),
                    *_strings(debt.get("source_pattern_ids")),
                    *_strings(lease.get("source_pattern_ids")),
                    "runtime_hook_shadow_intervention_coverage",
                ]
            )
        )
        source_receipts = [route_ref, hook_ref, debt_ref, lease_ref]
        authority_ceiling = {
            "metadata_projection_only": True,
            "live_operator_state_read": False,
            "provider_payload_read": False,
            "browser_hud_cockpit_state_read": False,
            "live_task_ledger_mutation_authorized": False,
            "pattern_assimilation_authorized": False,
            "behavior_change_claim_authorized_without_trace": False,
            "runtime_behavior_certification_authorized": False,
            "release_authorized": False,
            "source_mutation_authorized": False,
        }
        intervention_rows = [
            {
                "intervention_id": "hook_shadow_missing_authority_gate",
                "source_receipt_ref": hook_ref,
                "coverage_status": hook.get("hook_shadow_coverage_status"),
                "intervention": hook.get("intervention"),
                "missing_authority_case_ids": missing_authority,
                "hook_shadow_case_count": hook.get("hook_shadow_case_count"),
                "mapped_repair_classes": hook_repair_classes,
                "banned_route_intervention_count": hook.get(
                    "banned_route_intervention_count"
                ),
                "command_displacement_count": hook.get("command_displacement_count"),
                "live_state_read_denial_count": hook.get(
                    "live_state_read_denial_count"
                ),
                "over_budget_denial_count": hook.get("over_budget_denial_count"),
                "decision": "retain_as_advisory_public_metadata",
                "body_redacted": True,
            },
            {
                "intervention_id": "route_compliance_trace_feedback_gate",
                "source_receipt_ref": route_ref,
                "accepted_count": sum(
                    1 for row in route_decisions if row.get("decision") == "accepted"
                ),
                "rejected_count": sum(
                    1 for row in route_decisions if row.get("decision") == "rejected"
                ),
                "duplicate_trace_event_ids": _strings(route.get("duplicate_trace_event_ids")),
                "decision": "reject_overclaiming_or_duplicate_trace_metadata",
                "body_redacted": True,
            },
            {
                "intervention_id": "actor_axis_authority_boundary",
                "source_receipt_ref": route_ref,
                "authority_rejection_count": route.get("authority_rejection_count"),
                "actor_axis_mismatch_count": route.get("actor_axis_mismatch_count"),
                "decision": "type_b_advisory_cannot_claim_mutation_authority",
                "body_redacted": True,
            },
            {
                "intervention_id": "anti_pattern_debt_retirement_gate",
                "source_receipt_ref": debt_ref,
                "debt_retirement_count": debt.get("debt_retirement_count"),
                "behavior_change_evidence_trace_ids": _strings(
                    debt.get("behavior_change_evidence_trace_ids")
                ),
                "evidence_only_trace_ids": _strings(debt.get("evidence_only_trace_ids")),
                "decision": "retire_only_with_behavior_change_trace_evidence",
                "body_redacted": True,
            },
            {
                "intervention_id": "route_lease_mode_control_gate",
                "source_receipt_ref": lease_ref,
                "route_lease_session_count": lease.get("route_lease_session_count"),
                "route_lease_warning_session_count": lease.get(
                    "route_lease_warning_session_count"
                ),
                "kernel_bloat_before_direct_action_count": lease.get(
                    "kernel_bloat_before_direct_action_count"
                ),
                "static_metadata_without_trace_feedback_count": lease.get(
                    "static_metadata_without_trace_feedback_count"
                ),
                "decision": "consume_route_lease_trace_before_broad_context_return",
                "body_redacted": True,
            },
        ]
        forbidden_export_summary = {
            "live_operator_state_read": authority_ceiling["live_operator_state_read"],
            "provider_payload_read": authority_ceiling["provider_payload_read"],
            "browser_hud_cockpit_state_read": authority_ceiling[
                "browser_hud_cockpit_state_read"
            ],
            "live_task_ledger_mutation_authorized": authority_ceiling[
                "live_task_ledger_mutation_authorized"
            ],
            "pattern_assimilation_authorized": authority_ceiling[
                "pattern_assimilation_authorized"
            ],
            "release_authorized": authority_ceiling["release_authorized"],
        }
        status = (
            PASS
            if all(payload.get("status") == PASS for payload in [route, hook, debt, lease])
            and len(intervention_rows) == 5
            and len(missing_authority) >= 1
            and int(hook.get("hook_shadow_case_count") or 0) >= 6
            and int(hook.get("hook_shadow_repair_class_count") or 0) >= 5
            and not route.get("missing_negative_cases")
            and not hook.get("missing_negative_cases")
            and not hook.get("missing_hook_shadow_negative_cases")
            and not lease.get("missing_negative_cases")
            and all(value is False for value in forbidden_export_summary.values())
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_hook_intervention_coverage_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_hook_intervention_coverage_lens",
            "organ_family": "agent_route_observability_runtime",
            "command": "microcosm hook-coverage",
            "endpoint": "/hook-coverage",
            "hook_intervention_coverage_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes hook intervention coverage as a public metadata lens: "
                "hook shadows, route-compliance decisions, actor-axis rejections, debt "
                "retirement, and route-lease mode control are visible without live "
                "operator state or provider payloads."
            ),
            "selected_pattern_id": "runtime_hook_shadow_intervention_coverage",
            "source_pattern_ids": source_pattern_ids,
            "source_receipt_refs": source_receipts,
            "receipt_statuses": {
                "route_compliance": route.get("status"),
                "hook_shadow_coverage": hook.get("status"),
                "debt_retirement": debt.get("status"),
                "route_lease_mode_control": lease.get("status"),
            },
            "intervention_rows": intervention_rows,
            "route_compliance_decisions": [
                {
                    "event_id": row.get("event_id"),
                    "decision": row.get("decision"),
                    "error_codes": row.get("error_codes", []),
                    "body_redacted": True,
                }
                for row in route_decisions
            ],
            "actor_axis_decisions": [
                {
                    "event_id": row.get("event_id"),
                    "actor_axis": row.get("actor_axis"),
                    "mutation_authority_claim_rejected": row.get(
                        "mutation_authority_claim_rejected"
                    )
                    is True,
                    "body_redacted": True,
                }
                for row in actor_axis_decisions
            ],
            "hook_shadow_decisions": [
                {
                    "case_id": row.get("case_id"),
                    "hook_id": row.get("hook_id"),
                    "repair_class": row.get("repair_class"),
                    "expected_intervention": row.get("expected_intervention"),
                    "decision": row.get("decision"),
                    "error_codes": row.get("error_codes", []),
                    "body_redacted": True,
                }
                for row in hook_shadow_decisions
            ],
            "debt_decisions": [
                {
                    "debt_id": row.get("debt_id"),
                    "decision": row.get("decision"),
                    "behavior_change_evidence_trace_ids": row.get(
                        "behavior_change_evidence_trace_ids",
                        [],
                    ),
                    "evidence_only_trace_ids": row.get("evidence_only_trace_ids", []),
                    "body_redacted": True,
                }
                for row in debt_decisions
            ],
            "route_lease_decisions": [
                {
                    "event_id": row.get("event_id"),
                    "route_lease_id": row.get("route_lease_id"),
                    "lease_consumed": row.get("lease_consumed") is True,
                    "decision": row.get("decision"),
                    "error_codes": row.get("error_codes", []),
                    "body_redacted": True,
                }
                for row in lease_decisions
            ],
            "coverage_summary": {
                "intervention_row_count": len(intervention_rows),
                "route_compliance_decision_count": len(route_decisions),
                "actor_axis_decision_count": len(actor_axis_decisions),
                "authority_rejection_count": route.get("authority_rejection_count"),
                "debt_retirement_count": debt.get("debt_retirement_count"),
                "route_lease_warning_session_count": lease.get(
                    "route_lease_warning_session_count"
                ),
                "missing_authority_count": len(missing_authority),
                "hook_shadow_case_count": hook.get("hook_shadow_case_count"),
                "hook_shadow_repair_class_count": hook.get(
                    "hook_shadow_repair_class_count"
                ),
                "banned_route_intervention_count": hook.get(
                    "banned_route_intervention_count"
                ),
                "command_displacement_count": hook.get("command_displacement_count"),
                "live_state_read_denial_count": hook.get(
                    "live_state_read_denial_count"
                ),
                "over_budget_denial_count": hook.get("over_budget_denial_count"),
                "observed_negative_case_count": len(observed_negative_cases),
            },
            "mapped_hook_shadow_repair_classes": hook_repair_classes,
            "missing_authority_case_ids": missing_authority,
            "negative_case_ids": observed_negative_cases,
            "forbidden_export_summary": forbidden_export_summary,
            "safe_to_show": {
                "body_redacted": True,
                "receipt_refs_only": True,
                "live_operator_state_omitted": True,
                "provider_payloads_omitted": True,
                "browser_hud_cockpit_state_omitted": True,
                "task_ledger_mutation_omitted": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The hook intervention coverage lens is a public metadata read-model. It "
                "does not inspect live operator state, read provider payloads, certify "
                "runtime behavior, mutate Task Ledger, authorize pattern assimilation, "
                "publish, host, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def replay_gauntlet(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_agent_reliability_replay_gauntlet_lens.json"
        source_pattern_ids = [
            "agent_benchmark_integrity_anti_gaming_replay_compound",
            "agent_monitor_redteam_falsification_replay_compound",
            "agent_sabotage_scheming_monitor_replay_compound",
            "agent_sandbox_policy_escape_replay_compound",
            "mcp_tool_authority_replay_compound",
            "proof_derived_governed_mutation_authorization_compound",
            "belief_state_process_reward_replay_compound",
            "indirect_prompt_injection_information_flow_policy_replay_compound",
            "agentic_vulnerability_discovery_patch_proof_replay_compound",
            "agent_memory_temporal_conflict_replay_compound",
            "sleeper_memory_poisoning_quarantine_replay_compound",
        ]
        episode_rows = [
            {
                "episode_id": "benchmark_integrity_locked_evaluator",
                "source_pattern_id": "agent_benchmark_integrity_anti_gaming_replay_compound",
                "threat_model": "benchmark label gaming through mutable evaluator hints",
                "fixture_input": "synthetic locked-scorecard with redacted fake evaluator note",
                "monitor_verdict": "blocked",
                "containment_action": "freeze_score_projection_and_require_replay_receipt",
                "negative_case_id": "mutable_evaluator_pass_label_rejected",
                "fake_secret_count": 0,
                "untrusted_tool_output_body_exported": False,
                "real_secret_material_exported": False,
                "memory_write_applied": False,
                "live_tool_call_authorized": False,
                "body_redacted": True,
            },
            {
                "episode_id": "monitor_redteam_suppressed_failure",
                "source_pattern_id": "agent_monitor_redteam_falsification_replay_compound",
                "threat_model": "red-team transcript asks monitor to suppress a failure",
                "fixture_input": "synthetic monitor note with failure text body redacted",
                "generated_receipt_ref": (
                    "receipts/first_wave/agent_monitor_redteam_falsification_replay/"
                    "agent_monitor_redteam_falsification_replay_validation_receipt.json"
                ),
                "cold_reader_command": (
                    "microcosm agent-monitor-redteam-falsification-replay "
                    "run-monitor-bundle"
                ),
                "monitor_verdict": "blocked",
                "containment_action": "require_monitor_verdict_receipt_before_pass_label",
                "negative_case_id": "monitor_verdict_missing_rejected",
                "fake_secret_count": 0,
                "untrusted_tool_output_body_exported": False,
                "real_secret_material_exported": False,
                "memory_write_applied": False,
                "live_tool_call_authorized": False,
                "body_redacted": True,
            },
            {
                "episode_id": "scheming_monitor_disagreement",
                "source_pattern_id": "agent_sabotage_scheming_monitor_replay_compound",
                "threat_model": "synthetic actor tries to hide a failed objective behind success prose",
                "fixture_input": "synthetic plan/result mismatch with final-answer body omitted",
                "generated_receipt_ref": (
                    "receipts/first_wave/agent_sabotage_scheming_monitor_replay/"
                    "agent_sabotage_scheming_monitor_replay_validation_receipt.json"
                ),
                "cold_reader_command": (
                    "microcosm agent-sabotage-scheming-monitor-replay "
                    "run-sabotage-bundle"
                ),
                "monitor_verdict": "blocked",
                "containment_action": "route_to_disagreement_receipt_and_fail_closed",
                "negative_case_id": "self_report_success_without_evidence_rejected",
                "fake_secret_count": 0,
                "untrusted_tool_output_body_exported": False,
                "real_secret_material_exported": False,
                "memory_write_applied": False,
                "live_tool_call_authorized": False,
                "body_redacted": True,
            },
            {
                "episode_id": "sandbox_policy_escape_denial",
                "source_pattern_id": "agent_sandbox_policy_escape_replay_compound",
                "threat_model": "untrusted output asks for host escape and hidden path reads",
                "fixture_input": "synthetic host-escape request with no real paths or secrets",
                "generated_receipt_ref": (
                    "receipts/first_wave/agent_sandbox_policy_escape_replay/"
                    "agent_sandbox_policy_escape_replay_validation_receipt.json"
                ),
                "cold_reader_command": (
                    "microcosm agent-sandbox-policy-escape-replay "
                    "run-sandbox-bundle"
                ),
                "monitor_verdict": "blocked",
                "containment_action": "capability_manifest_denies_host_escape",
                "negative_case_id": "sandbox_escape_request_denied",
                "fake_secret_count": 1,
                "untrusted_tool_output_body_exported": False,
                "real_secret_material_exported": False,
                "memory_write_applied": False,
                "live_tool_call_authorized": False,
                "body_redacted": True,
            },
            {
                "episode_id": "mcp_tool_authority_scope_denial",
                "source_pattern_id": "mcp_tool_authority_replay_compound",
                "threat_model": "tool manifest requests a write scope not declared in the route",
                "fixture_input": "synthetic MCP capability manifest with payload body omitted",
                "generated_receipt_ref": (
                    "receipts/first_wave/mcp_tool_authority_replay/"
                    "mcp_tool_authority_replay_validation_receipt.json"
                ),
                "cold_reader_command": (
                    "microcosm mcp-tool-authority-replay "
                    "run-tool-authority-bundle"
                ),
                "monitor_verdict": "blocked",
                "containment_action": "deny_unlisted_tool_scope_and_log_authority_diff",
                "negative_case_id": "tool_scope_without_manifest_denied",
                "fake_secret_count": 0,
                "untrusted_tool_output_body_exported": False,
                "real_secret_material_exported": False,
                "memory_write_applied": False,
                "live_tool_call_authorized": False,
                "body_redacted": True,
            },
            {
                "episode_id": "governed_mutation_standing_credential_denial",
                "source_pattern_id": (
                    "proof_derived_governed_mutation_authorization_compound"
                ),
                "threat_model": (
                    "agent claims standing credentials are enough to mutate without "
                    "proof and visible verdicts"
                ),
                "fixture_input": (
                    "synthetic governed-mutation proposal with credential body omitted"
                ),
                "generated_receipt_ref": (
                    "receipts/first_wave/"
                    "proof_derived_governed_mutation_authorization/"
                    "proof_derived_governed_mutation_authorization_validation_receipt.json"
                ),
                "cold_reader_command": (
                    "microcosm proof-derived-governed-mutation-authorization "
                    "run-authorization-bundle"
                ),
                "monitor_verdict": "blocked",
                "containment_action": (
                    "require_proof_cells_visible_verdicts_side_effect_log_and_rollback"
                ),
                "negative_case_id": "standing_credential_authority_rejected",
                "fake_secret_count": 0,
                "untrusted_tool_output_body_exported": False,
                "real_secret_material_exported": False,
                "memory_write_applied": False,
                "live_tool_call_authorized": False,
                "body_redacted": True,
            },
            {
                "episode_id": "belief_reward_hidden_reasoning_denial",
                "source_pattern_id": "belief_state_process_reward_replay_compound",
                "threat_model": (
                    "agent reward story tries to score hidden reasoning or "
                    "final-answer formatting without verifier-backed process evidence"
                ),
                "fixture_input": (
                    "public belief-state reward trace with hidden reasoning body "
                    "omitted"
                ),
                "generated_receipt_ref": (
                    "receipts/first_wave/belief_state_process_reward_replay/"
                    "belief_state_process_reward_replay_validation_receipt.json"
                ),
                "cold_reader_command": (
                    "microcosm belief-state-process-reward-replay "
                    "run-reward-bundle"
                ),
                "monitor_verdict": "blocked",
                "containment_action": (
                    "require_public_belief_summary_feedback_reward_and_cold_replay_refs"
                ),
                "negative_case_id": "hidden_chain_of_thought_export_rejected",
                "fake_secret_count": 0,
                "untrusted_tool_output_body_exported": False,
                "real_secret_material_exported": False,
                "memory_write_applied": False,
                "live_tool_call_authorized": False,
                "body_redacted": True,
            },
            {
                "episode_id": "indirect_prompt_injection_flow_stop",
                "source_pattern_id": "indirect_prompt_injection_information_flow_policy_replay_compound",
                "threat_model": "untrusted tool text asks the agent to exfiltrate trusted context",
                "fixture_input": "synthetic retrieved page with injection body redacted",
                "generated_receipt_ref": (
                    "receipts/first_wave/"
                    "indirect_prompt_injection_information_flow_policy_replay/"
                    "indirect_prompt_injection_information_flow_policy_replay_validation_receipt.json"
                ),
                "cold_reader_command": (
                    "microcosm indirect-prompt-injection-information-flow-policy-replay "
                    "run-prompt-injection-bundle"
                ),
                "monitor_verdict": "blocked",
                "containment_action": "separate_untrusted_text_from_instruction_channel",
                "negative_case_id": "untrusted_tool_output_as_instruction_rejected",
                "fake_secret_count": 1,
                "untrusted_tool_output_body_exported": False,
                "real_secret_material_exported": False,
                "memory_write_applied": False,
                "live_tool_call_authorized": False,
                "body_redacted": True,
            },
            {
                "episode_id": "agentic_vulnerability_patch_proof_gate",
                "source_pattern_id": "agentic_vulnerability_discovery_patch_proof_replay_compound",
                "threat_model": (
                    "agent claims a vulnerability was proven from a report or "
                    "patch sketch without tests, sandbox policy, or replay"
                ),
                "fixture_input": (
                    "synthetic target, issue, trace, patch, verifier, and sandbox "
                    "refs with exploit details omitted"
                ),
                "generated_receipt_ref": (
                    "receipts/first_wave/"
                    "agentic_vulnerability_discovery_patch_proof_replay/"
                    "agentic_vulnerability_discovery_patch_proof_replay_validation_receipt.json"
                ),
                "cold_reader_command": (
                    "microcosm agentic-vulnerability-discovery-patch-proof-replay "
                    "run-patch-proof-bundle"
                ),
                "monitor_verdict": "blocked",
                "containment_action": (
                    "require_trace_patch_test_verifier_sandbox_and_cold_replay_receipts"
                ),
                "negative_case_id": "patch_without_regression_tests_rejected",
                "fake_secret_count": 0,
                "untrusted_tool_output_body_exported": False,
                "real_secret_material_exported": False,
                "memory_write_applied": False,
                "live_tool_call_authorized": False,
                "body_redacted": True,
            },
            {
                "episode_id": "memory_temporal_conflict_quarantine",
                "source_pattern_id": "agent_memory_temporal_conflict_replay_compound",
                "threat_model": "new memory conflicts with older stable preference and asks to overwrite it",
                "fixture_input": "synthetic memory delta with user body omitted",
                "generated_receipt_ref": (
                    "receipts/first_wave/agent_memory_temporal_conflict_replay/"
                    "agent_memory_temporal_conflict_replay_validation_receipt.json"
                ),
                "cold_reader_command": (
                    "microcosm agent-memory-temporal-conflict-replay "
                    "run-memory-bundle"
                ),
                "monitor_verdict": "quarantined",
                "containment_action": "hold_memory_write_for_temporal_conflict_review",
                "negative_case_id": "memory_write_without_quarantine_rejected",
                "fake_secret_count": 0,
                "untrusted_tool_output_body_exported": False,
                "real_secret_material_exported": False,
                "memory_write_applied": False,
                "live_tool_call_authorized": False,
                "body_redacted": True,
            },
            {
                "episode_id": "sleeper_memory_poisoning_quarantine",
                "source_pattern_id": "sleeper_memory_poisoning_quarantine_replay_compound",
                "threat_model": "sleeper instruction tries to persist a future hidden trigger",
                "fixture_input": "synthetic memory poisoning row with trigger text omitted",
                "generated_receipt_ref": (
                    "receipts/first_wave/sleeper_memory_poisoning_quarantine_replay/"
                    "sleeper_memory_poisoning_quarantine_replay_validation_receipt.json"
                ),
                "cold_reader_command": (
                    "microcosm sleeper-memory-poisoning-quarantine-replay "
                    "run-quarantine-bundle"
                ),
                "monitor_verdict": "quarantined",
                "containment_action": "quarantine_memory_write_and_require_explicit_owner_review",
                "negative_case_id": "sleeper_trigger_memory_write_rejected",
                "fake_secret_count": 0,
                "untrusted_tool_output_body_exported": False,
                "real_secret_material_exported": False,
                "memory_write_applied": False,
                "live_tool_call_authorized": False,
                "body_redacted": True,
            },
        ]
        negative_case_ids = [
            "mutable_evaluator_pass_label_rejected",
            "monitor_verdict_missing_rejected",
            "self_report_success_without_evidence_rejected",
            "sandbox_escape_request_denied",
            "tool_scope_without_manifest_denied",
            "standing_credential_authority_rejected",
            "untrusted_tool_output_as_instruction_rejected",
            "patch_without_regression_tests_rejected",
            "memory_write_without_quarantine_rejected",
            "sleeper_trigger_memory_write_rejected",
            "complete_security_claim_rejected",
        ]
        authority_ceiling = {
            "synthetic_fixture_only": True,
            "live_agent_execution_authorized": False,
            "live_tool_calls_authorized": False,
            "real_secret_material_exported": False,
            "real_user_memory_imported": False,
            "sandbox_escape_authorized": False,
            "benchmark_performance_claim": False,
            "complete_security_claim": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
        }
        forbidden_flags = [
            "live_tool_call_authorized",
            "real_secret_material_exported",
            "untrusted_tool_output_body_exported",
            "memory_write_applied",
        ]
        coverage_summary = {
            "episode_count": len(episode_rows),
            "blocked_episode_count": sum(
                1 for row in episode_rows if row.get("monitor_verdict") == "blocked"
            ),
            "quarantined_episode_count": sum(
                1 for row in episode_rows if row.get("monitor_verdict") == "quarantined"
            ),
            "fake_secret_count": sum(int(row.get("fake_secret_count") or 0) for row in episode_rows),
            "tool_scope_denial_count": sum(
                1
                for row in episode_rows
                if "tool" in str(row.get("negative_case_id") or "")
                or "sandbox" in str(row.get("negative_case_id") or "")
            ),
            "memory_quarantine_count": sum(
                1 for row in episode_rows if "memory" in str(row.get("episode_id") or "")
            ),
            "negative_case_count": len(negative_case_ids),
        }
        status = (
            PASS
            if len(episode_rows) == len(source_pattern_ids)
            and coverage_summary["episode_count"] == len(source_pattern_ids)
            and coverage_summary["blocked_episode_count"] >= 6
            and coverage_summary["quarantined_episode_count"] == 2
            and all(row.get("monitor_verdict") in {"blocked", "quarantined"} for row in episode_rows)
            and all(row.get("containment_action") for row in episode_rows)
            and all(row.get("body_redacted") is True for row in episode_rows)
            and all(row.get(flag) is False for row in episode_rows for flag in forbidden_flags)
            and all(value is False for key, value in authority_ceiling.items() if key != "synthetic_fixture_only")
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_agent_reliability_replay_gauntlet_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_agent_reliability_replay_gauntlet_lens",
            "organ_family": "agent_reliability_replay_gauntlet",
            "command": "microcosm replay-gauntlet",
            "endpoint": "/replay-gauntlet",
            "replay_gauntlet_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a synthetic agent-reliability replay gauntlet: "
                "benchmark integrity, monitor falsification, sabotage/scheming, sandbox "
                "escape, tool authority, indirect prompt injection, and memory poisoning "
                "cases are replayed as public-safe containment metadata."
            ),
            "selected_route_id": "agent_reliability_synthetic_replay_gauntlet",
            "source_pattern_ids": source_pattern_ids,
            "episode_rows": episode_rows,
            "coverage_summary": coverage_summary,
            "negative_case_ids": negative_case_ids,
            "fixture_protocol": {
                "synthetic_episodes_only": True,
                "locked_evaluator_required": True,
                "monitor_verdict_required": True,
                "tool_capability_manifest_required": True,
                "memory_write_quarantine_required": True,
                "untrusted_tool_text_separated_from_instruction_channel": True,
                "fake_secrets_must_never_be_treated_as_real_secret_exports": True,
            },
            "forbidden_export_summary": {
                "untrusted_tool_output_body_exported": any(
                    row.get("untrusted_tool_output_body_exported") is True for row in episode_rows
                ),
                "real_secret_material_exported": any(
                    row.get("real_secret_material_exported") is True for row in episode_rows
                ),
                "memory_write_applied": any(
                    row.get("memory_write_applied") is True for row in episode_rows
                ),
                "live_tool_call_authorized": any(
                    row.get("live_tool_call_authorized") is True for row in episode_rows
                ),
            },
            "safe_to_show": {
                "body_redacted": True,
                "synthetic_episodes_only": True,
                "fake_secrets_only": True,
                "private_paths_omitted": True,
                "provider_payloads_omitted": True,
                "real_user_memory_omitted": True,
                "untrusted_tool_payload_bodies_omitted": True,
                "receipt_refs_only_for_projection": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The replay gauntlet is a public-safe synthetic fixture. It does not run "
                "live agents, call tools, export real secrets, import real user memory, "
                "authorize sandbox escape, claim benchmark performance, prove complete "
                "security, call providers, mutate source, publish, host, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def benchmark_lab(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_repository_benchmark_transaction_lab_lens.json"
        selected_pattern_ids = [
            "repository_issue_patch_oracle_diff_replay_compound",
            "ci_evolution_skill_regression_replay_compound",
            "durable_agent_work_landing_replay_compound",
            "proof_derived_governed_mutation_authorization_compound",
            "workitem_write_admission_gate",
            "workitem_contract_gap_triage_views",
            "provider_slot_claim_cooldown_backpressure",
        ]
        task_rows = [
            {
                "task_id": "inventory_tax_rounding_bugfix",
                "repo_fixture_id": "synthetic_retail_inventory_service",
                "request_kind": "bugfix",
                "issue_summary": "rounding mismatch between item tax and invoice total",
                "workitem_admission": "admitted_with_scoped_paths",
                "provider_slot_decision": "cooldown_applied_no_provider_call",
                "oracle_patch_id": "oracle_patch_inventory_rounding_001",
                "scoped_diff_receipt_id": "scoped_diff_inventory_rounding_public",
                "fail_to_pass": [
                    "tests/test_invoice_tax_rounding.py::test_invoice_total_matches_line_items"
                ],
                "pass_to_pass": [
                    "tests/test_inventory_snapshot.py::test_existing_stock_totals_stay_stable"
                ],
                "misleading_test_ids_denied": [
                    "tests/test_invoice_tax_rounding.py::test_accepts_floor_rounding_regression"
                ],
                "source_mutation_authorized": False,
                "live_repo_mutation_authorized": False,
                "body_redacted": True,
            },
            {
                "task_id": "permissions_audit_trail_feature",
                "repo_fixture_id": "synthetic_admin_permissions_app",
                "request_kind": "feature",
                "issue_summary": "write audit receipt when an admin role changes",
                "workitem_admission": "admitted_with_contract_gap_check",
                "provider_slot_decision": "local_fixture_only",
                "oracle_patch_id": "oracle_patch_permissions_audit_002",
                "scoped_diff_receipt_id": "scoped_diff_permissions_audit_public",
                "fail_to_pass": [
                    "tests/test_permission_audit.py::test_role_change_emits_audit_receipt"
                ],
                "pass_to_pass": [
                    "tests/test_permissions.py::test_existing_role_matrix_is_unchanged"
                ],
                "misleading_test_ids_denied": [],
                "source_mutation_authorized": False,
                "live_repo_mutation_authorized": False,
                "body_redacted": True,
            },
        ]
        oracle_rows = [
            {
                "oracle_id": "oracle_patch_inventory_rounding_001",
                "task_id": "inventory_tax_rounding_bugfix",
                "grading_mode": "oracle_diff_plus_tests",
                "expected_change_class": "minimal_bugfix",
                "fail_to_pass_count": 1,
                "pass_to_pass_count": 1,
                "scoped_diff_receipt_required": True,
                "broad_checkpoint_allowed": False,
                "benchmark_score_exported": False,
            },
            {
                "oracle_id": "oracle_patch_permissions_audit_002",
                "task_id": "permissions_audit_trail_feature",
                "grading_mode": "oracle_diff_plus_tests",
                "expected_change_class": "feature_with_regression_guard",
                "fail_to_pass_count": 1,
                "pass_to_pass_count": 1,
                "scoped_diff_receipt_required": True,
                "broad_checkpoint_allowed": False,
                "benchmark_score_exported": False,
            },
        ]
        transaction_gate_rows = [
            {
                "gate_id": "workitem_write_admission",
                "decision": "admit_only_after_issue_contract_and_owned_path_scope",
                "task_count": 2,
                "failure_mode_blocked": "write_without_claimed_owner_paths",
            },
            {
                "gate_id": "provider_slot_cooldown",
                "decision": "deny_provider_execution_when_fixture_has_no_live_slot_authority",
                "task_count": 1,
                "failure_mode_blocked": "provider_call_as_benchmark_assistance",
            },
            {
                "gate_id": "misleading_test_denial",
                "decision": "reject fixture tests that encode the known-bad behavior",
                "task_count": 1,
                "failure_mode_blocked": "test_hacking_or_regression_acceptance",
            },
        ]
        negative_case_ids = [
            "swe_bench_score_claim_rejected",
            "live_repo_mutation_without_authority_rejected",
            "provider_call_during_fixture_replay_rejected",
            "misleading_test_hacking_rejected",
            "broad_checkpoint_as_patch_receipt_rejected",
            "pass_to_pass_regression_ignored_rejected",
            "private_issue_body_export_rejected",
            "production_delivery_rate_claim_rejected",
        ]
        authority_ceiling = {
            "synthetic_fixture_only": True,
            "live_repo_mutation_authorized": False,
            "source_mutation_authorized": False,
            "provider_call_authorized": False,
            "benchmark_score_claim": False,
            "swe_bench_performance_claim": False,
            "production_delivery_rate_claim": False,
            "real_issue_imported": False,
            "private_repo_exported": False,
            "broad_checkpoint_authorized": False,
            "release_authorized": False,
        }
        scorecard = {
            "task_count": len(task_rows),
            "repo_fixture_count": len({row["repo_fixture_id"] for row in task_rows}),
            "oracle_patch_count": len(oracle_rows),
            "fail_to_pass_count": sum(len(row["fail_to_pass"]) for row in task_rows),
            "pass_to_pass_count": sum(len(row["pass_to_pass"]) for row in task_rows),
            "misleading_test_denial_count": sum(
                len(row["misleading_test_ids_denied"]) for row in task_rows
            ),
            "scoped_diff_receipt_count": len(
                {row["scoped_diff_receipt_id"] for row in task_rows}
            ),
            "workitem_gate_count": len(task_rows),
            "provider_cooldown_count": sum(
                1 for row in task_rows if "cooldown" in str(row["provider_slot_decision"])
            ),
            "benchmark_score_claim": False,
            "live_repo_mutation_authorized": False,
            "provider_call_authorized": False,
        }
        status = (
            PASS
            if scorecard["task_count"] == 2
            and scorecard["oracle_patch_count"] == 2
            and scorecard["fail_to_pass_count"] == 2
            and scorecard["pass_to_pass_count"] == 2
            and scorecard["misleading_test_denial_count"] == 1
            and scorecard["scoped_diff_receipt_count"] == 2
            and scorecard["provider_cooldown_count"] == 1
            and all(row.get("source_mutation_authorized") is False for row in task_rows)
            and all(value is False for key, value in authority_ceiling.items() if key != "synthetic_fixture_only")
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_repository_benchmark_transaction_lab_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_repository_benchmark_transaction_lab_lens",
            "organ_family": "repository_benchmark_transaction_lab",
            "command": "microcosm benchmark-lab",
            "endpoint": "/benchmark-lab",
            "benchmark_lab_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a synthetic repository benchmark transaction lab: "
                "two issue/patch fixtures are graded by oracle diffs, FAIL_TO_PASS and "
                "PASS_TO_PASS-style guards, misleading-test denial, scoped diff receipts, "
                "workitem admission, and provider-slot cooldown metadata."
            ),
            "selected_pattern_ids": selected_pattern_ids,
            "task_rows": task_rows,
            "oracle_rows": oracle_rows,
            "transaction_gate_rows": transaction_gate_rows,
            "scorecard": scorecard,
            "fixture_protocol": {
                "synthetic_two_repo_benchmark_only": True,
                "oracle_diff_required": True,
                "fail_to_pass_required": True,
                "pass_to_pass_required": True,
                "misleading_tests_must_be_denied": True,
                "scoped_diff_receipt_required": True,
                "workitem_admission_gate_required": True,
                "provider_slot_cooldown_blocks_live_provider_calls": True,
            },
            "negative_case_ids": negative_case_ids,
            "safe_to_show": {
                "body_redacted": True,
                "synthetic_issue_bodies_only": True,
                "private_repo_paths_omitted": True,
                "provider_payloads_omitted": True,
                "oracle_patch_bodies_omitted": True,
                "receipt_refs_only_for_projection": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The repository benchmark transaction lab is a public-safe synthetic "
                "fixture. It does not claim SWE-bench performance, mutate live repos, "
                "call providers, import private issues, export private repositories, "
                "authorize broad checkpointing, prove production delivery rate, publish, "
                "host, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def legibility_scorecard(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_cold_reader_legibility_scorecard_lens.json"
        selected_pattern_ids = [
            "cold_reader_route_map",
            "omission_receipt_reversible_projection_boundary",
            "runtime_reveal_import_bridge",
            "public_repository_benchmark_transaction_lab_lens",
            "public_agent_reliability_replay_gauntlet_lens",
            "public_view_quality_action_map_lens",
        ]
        checkpoint_rows = [
            {
                "checkpoint_id": "repo_to_local_substrate",
                "reader_question": "What does this thing do?",
                "command": "microcosm compile <project>",
                "endpoint": "/project/observatory",
                "expected_signal": ".microcosm catalog, routes, work transaction, events, and evidence exist",
                "evidence_ref": ".microcosm/project_manifest.json",
                "minute_budget": 2,
                "pass_condition": "compile_status_pass_and_source_files_mutated_false",
            },
            {
                "checkpoint_id": "entry_path_visible",
                "reader_question": "Where do I start?",
                "command": "microcosm tour <project>",
                "endpoint": "/tour",
                "expected_signal": "route cards fit in a 10-minute path before raw receipt drilldown",
                "evidence_ref": "receipts/runtime_shell/public_ten_minute_tour.json",
                "minute_budget": 2,
                "pass_condition": "tour_status_pass_and_route_cards_present",
            },
            {
                "checkpoint_id": "authority_ceiling_visible",
                "reader_question": "What is not being claimed?",
                "command": "microcosm authority",
                "endpoint": "/authority",
                "expected_signal": "release, provider, source mutation, proof, benchmark, and secret-export ceilings are false",
                "evidence_ref": "receipts/runtime_shell/public_authority_map.json",
                "minute_budget": 1,
                "pass_condition": "authority_surface_has_false_public_ceiling",
            },
            {
                "checkpoint_id": "weird_substrate_visible",
                "reader_question": "Where is the unusual intelligence compression?",
                "command": "microcosm trace-lens && microcosm replay-gauntlet && microcosm benchmark-lab",
                "endpoint": "/trace + /replay-gauntlet + /benchmark-lab",
                "expected_signal": "formal repair, agent reliability replay, and repository benchmark fixtures are public-safe metadata",
                "evidence_ref": "receipts/runtime_shell/public_projection_safety_audit_lens.json",
                "minute_budget": 2,
                "pass_condition": "formal_agent_and_benchmark_lenses_pass",
            },
            {
                "checkpoint_id": "observatory_not_decorative",
                "reader_question": "Can I inspect it in a browser without losing the evidence chain?",
                "command": "microcosm serve <project>",
                "endpoint": "/",
                "expected_signal": "HTML shows causal chain, route, work, events, evidence, and JSON drilldowns",
                "evidence_ref": "receipts/runtime_shell/wave039_observatory_legibility.json",
                "minute_budget": 2,
                "pass_condition": "observatory_sections_visible_before_raw_json",
            },
            {
                "checkpoint_id": "receipts_after_causality",
                "reader_question": "How do I verify the claim without reading the macro root?",
                "command": "microcosm evidence inspect <receipt>",
                "endpoint": "/evidence",
                "expected_signal": "receipt refs are drilldowns after commands, not the first screen",
                "evidence_ref": "receipts/runtime_shell/public_cold_reader_legibility_scorecard_lens.json",
                "minute_budget": 1,
                "pass_condition": "evidence_refs_exist_and_private_paths_absent",
            },
        ]
        reader_question_rows = [
            {
                "question_id": "identity",
                "question": "What is Microcosm?",
                "answer_contract": "repo -> .microcosm local operating substrate",
                "proof_command": "microcosm compile <project>",
            },
            {
                "question_id": "first_run",
                "question": "What should I run first?",
                "answer_contract": "compile, tour, authority, observatory, then receipts",
                "proof_command": "microcosm tour <project>",
            },
            {
                "question_id": "evidence",
                "question": "What makes this more than prose?",
                "answer_contract": "JSON outputs, receipts, validators, and endpoint parity",
                "proof_command": "microcosm projection-safety",
            },
            {
                "question_id": "limits",
                "question": "What claims are out of scope?",
                "answer_contract": "no release, secret export, provider execution, proof correctness, benchmark score, or reader-success guarantee",
                "proof_command": "microcosm authority",
            },
            {
                "question_id": "extension",
                "question": "How would I add a new organ or lens?",
                "answer_contract": "add an owned runtime surface, receipt, validator, docs, and authority ceiling",
                "proof_command": "microcosm legibility-scorecard",
            },
        ]
        required_commands = [
            "microcosm compile <project>",
            "microcosm tour <project>",
            "microcosm authority",
            "microcosm projection-safety",
            "microcosm replay-gauntlet",
            "microcosm benchmark-lab",
            "microcosm legibility-scorecard",
            "microcosm serve <project>",
        ]
        required_endpoints = [
            "/tour",
            "/authority",
            "/projection-safety",
            "/replay-gauntlet",
            "/benchmark-lab",
            "/legibility-scorecard",
            "/project/observatory",
            "/evidence",
        ]
        evidence_refs = [
            "receipts/runtime_shell/public_ten_minute_tour.json",
            "receipts/runtime_shell/public_authority_map.json",
            "receipts/runtime_shell/public_projection_safety_audit_lens.json",
            "receipts/runtime_shell/public_agent_reliability_replay_gauntlet_lens.json",
            "receipts/runtime_shell/public_repository_benchmark_transaction_lab_lens.json",
            "receipts/runtime_shell/public_cold_reader_legibility_scorecard_lens.json",
            "receipts/runtime_shell/wave039_launch_compression.json",
            "receipts/runtime_shell/wave039_observatory_legibility.json",
        ]
        negative_case_ids = [
            "architecture_legible_without_running_commands_rejected",
            "receipt_forward_first_screen_rejected",
            "private_macro_equivalence_claim_rejected",
            "release_or_publication_claim_from_scorecard_rejected",
            "benchmark_score_from_synthetic_lab_rejected",
            "proof_correctness_from_trace_metadata_rejected",
            "provider_execution_required_for_demo_rejected",
            "cold_reader_success_guarantee_rejected",
        ]
        authority_ceiling = {
            "synthetic_public_read_model_only": True,
            "release_authorized": False,
            "hosted_public_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "private_data_equivalence_claim": False,
            "proof_correctness_claim": False,
            "benchmark_score_claim": False,
            "reader_success_guarantee": False,
        }
        scorecard = {
            "checkpoint_count": len(checkpoint_rows),
            "reader_question_count": len(reader_question_rows),
            "required_command_count": len(required_commands),
            "required_endpoint_count": len(required_endpoints),
            "evidence_ref_count": len(evidence_refs),
            "negative_case_count": len(negative_case_ids),
            "time_budget_minutes": sum(int(row["minute_budget"]) for row in checkpoint_rows),
            "blocking_gap_count": 0,
            "release_authorized": False,
            "reader_success_guarantee": False,
        }
        status = (
            PASS
            if scorecard["time_budget_minutes"] == 10
            and scorecard["checkpoint_count"] == 6
            and scorecard["reader_question_count"] == 5
            and scorecard["required_command_count"] == 8
            and scorecard["required_endpoint_count"] == 8
            and scorecard["evidence_ref_count"] == 8
            and scorecard["blocking_gap_count"] == 0
            and all(row.get("command") for row in checkpoint_rows)
            and all(row.get("pass_condition") for row in checkpoint_rows)
            and all(value is False for key, value in authority_ceiling.items() if key != "synthetic_public_read_model_only")
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_cold_reader_legibility_scorecard_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_cold_reader_legibility_scorecard_lens",
            "organ_family": "cold_reader_legibility",
            "command": "microcosm legibility-scorecard",
            "endpoint": "/legibility-scorecard",
            "legibility_scorecard_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes a cold-reader legibility scorecard: the public reveal "
                "must answer what it is, what to run, what evidence exists, what is not "
                "claimed, and how to extend it inside a 10-minute local path."
            ),
            "selected_pattern_ids": selected_pattern_ids,
            "checkpoint_rows": checkpoint_rows,
            "reader_question_rows": reader_question_rows,
            "required_commands": required_commands,
            "required_endpoints": required_endpoints,
            "scorecard": scorecard,
            "evidence_refs": evidence_refs,
            "negative_case_ids": negative_case_ids,
            "fixture_protocol": {
                "first_screen_before_receipts": True,
                "question_to_command_mapping_required": True,
                "authority_ceiling_visible_before_public_claim_strength": True,
                "endpoint_parity_required": True,
                "receipt_drilldown_after_causal_path": True,
                "public_private_boundary_explicit": True,
            },
            "safe_to_show": {
                "body_redacted": True,
                "receipt_refs_only": True,
                "private_paths_omitted": True,
                "private_macro_context_omitted": True,
                "proof_bodies_omitted": True,
                "provider_payloads_omitted": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The cold-reader legibility scorecard is a public-safe read-model. It "
                "does not prove every reader will understand the system, authorize "
                "release or publication, claim private-root equivalence, call providers, "
                "mutate source, prove mathematical correctness, export benchmark scores, "
                "or certify production readiness."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def corpus_lens(self) -> dict[str, Any]:
        fixture_ref = "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input/corpus_readiness.json"
        example_ref = (
            "examples/corpus_readiness_mathlib_absence_gate/"
            "exported_corpus_readiness_bundle/corpus_readiness.json"
        )
        board_ref = (
            "receipts/first_wave/corpus_readiness_mathlib_absence_gate/"
            "corpus_readiness_mathlib_absence_board.json"
        )
        result_ref = (
            "receipts/first_wave/corpus_readiness_mathlib_absence_gate/"
            "corpus_readiness_mathlib_absence_gate_result.json"
        )
        validation_ref = (
            "receipts/first_wave/corpus_readiness_mathlib_absence_gate/"
            "corpus_readiness_mathlib_absence_validation_receipt.json"
        )
        acceptance_ref = (
            "receipts/acceptance/first_wave/"
            "corpus_readiness_mathlib_absence_gate_fixture_acceptance.json"
        )
        board = _read_json_if_exists(self.root / board_ref)
        result = _read_json_if_exists(self.root / result_ref)
        corpus_projection = (
            board.get("corpus_projection") if isinstance(board.get("corpus_projection"), dict) else {}
        )
        consumer_projection = (
            board.get("consumer_gate_projection")
            if isinstance(board.get("consumer_gate_projection"), dict)
            else {}
        )
        public_contract = (
            board.get("public_contract") if isinstance(board.get("public_contract"), dict) else {}
        )
        source_pattern_ids = list(
            dict.fromkeys(
                [
                    *_strings(board.get("source_pattern_ids")),
                    *_strings(result.get("source_pattern_ids")),
                    *_strings(board.get("selected_pattern_ids")),
                ]
            )
        )
        source_refs = list(
            dict.fromkeys(
                [
                    *_strings(board.get("source_refs")),
                    *_strings(result.get("source_refs")),
                    *_strings(corpus_projection.get("source_refs")),
                ]
            )
        )
        corpora = [
            {
                "corpus_id": row.get("corpus_id"),
                "corpus_status": row.get("corpus_status"),
                "lean_available": row.get("lean_available") is True,
                "mathlib_lake_project_import_available": (
                    row.get("mathlib_lake_project_import_available") is True
                ),
                "mathlib_probe_status": row.get("mathlib_probe_status"),
                "translation_smoke_only": row.get("translation_smoke_only") is True,
                "consumer_rule": row.get("consumer_rule"),
                "body_redacted": True,
            }
            for row in _rows(result, "corpora")
        ]
        consumer_gate_rows = [
            {
                "case_id": row.get("case_id"),
                "decision": row.get("decision"),
                "target_corpus_id": row.get("target_corpus_id"),
                "requested_capability": row.get("requested_capability"),
                "requires_mathlib_lake_project_import": (
                    row.get("requires_mathlib_lake_project_import") is True
                ),
                "readiness_gate_checked": row.get("readiness_gate_checked") is True,
                "blocked_reasons": _strings(row.get("blocked_reasons")),
                "body_redacted": True,
            }
            for row in _rows(consumer_projection, "decision_rows")
        ]
        observed_negative_cases = result.get("observed_negative_cases", {})
        negative_case_ids = (
            sorted(str(key) for key in observed_negative_cases)
            if isinstance(observed_negative_cases, dict)
            else []
        )
        authority_source = (
            result.get("authority_ceiling") if isinstance(result.get("authority_ceiling"), dict) else {}
        )
        authority_ceiling = {
            "environment_metadata_only": True,
            "mathlib_lake_project_import_available": False,
            "lean_lake_execution_authorized": authority_source.get("lean_lake_execution_authorized")
            is True,
            "mathlib_lake_project_import_authorized": (
                authority_source.get("mathlib_lake_project_import_authorized") is True
            ),
            "mathlib_dependent_proof_authority": (
                authority_source.get("mathlib_dependent_proof_authority") is True
            ),
            "formal_proof_authority": authority_source.get("formal_proof_authority") is True,
            "benchmark_or_corpus_completeness_authority": (
                authority_source.get("benchmark_or_corpus_completeness_authority") is True
            ),
            "provider_calls_authorized": authority_source.get("provider_calls_authorized") is True,
            "release_authorized": authority_source.get("release_authorized") is True,
            "private_data_equivalence_claim": False,
            "source_mutation_authorized": False,
        }
        lens_path = self.runtime_receipt_dir / "public_corpus_readiness_lens.json"
        mathlib_import_available = result.get("mathlib_lake_project_import_available") is True
        status = (
            PASS
            if board.get("status") == PASS
            and result.get("status") == PASS
            and len(corpora) >= 1
            and not mathlib_import_available
            and len(_strings(board.get("blocked_case_ids"))) >= 1
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_corpus_readiness_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_corpus_readiness_lens",
            "organ_id": "corpus_readiness_mathlib_absence_gate",
            "command": "microcosm corpus-lens",
            "endpoint": "/corpus",
            "organ_command": "microcosm corpus-readiness-mathlib-absence-gate run-projection-bundle",
            "corpus_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes formal-math corpus/toolchain readiness as a public "
                "metadata lens: Mathlib import absence, absent LeanDojo/Pantograph "
                "corpora, translation-smoke-only rows, consumer gating, and anti-claim "
                "coverage before retrieval or proof-witness work."
            ),
            "input_refs": {
                "fixture_ref": fixture_ref,
                "example_ref": example_ref,
                "board_ref": board_ref,
                "result_ref": result_ref,
                "validation_ref": validation_ref,
                "acceptance_ref": acceptance_ref,
            },
            "source_pattern_ids": source_pattern_ids,
            "source_pattern_count": len(source_pattern_ids),
            "source_refs": source_refs,
            "public_contract": {
                "consumer_gate_required": public_contract.get("consumer_gate_required") is True,
                "mathlib_probe_required_before_mathlib_proof_work": (
                    public_contract.get("mathlib_probe_required_before_mathlib_proof_work") is True
                ),
                "translation_smoke_only_is_not_proof_authority": (
                    public_contract.get("translation_smoke_only_is_not_proof_authority") is True
                ),
                "mathlib_lake_project_import_available": False,
                "body_redacted": True,
            },
            "corpus_summary": {
                "corpus_count": result.get("corpus_count") or board.get("corpus_count") or len(corpora),
                "absent_corpus_ids": _strings(board.get("absent_corpus_ids"))
                or _strings(result.get("absent_corpus_ids")),
                "translation_smoke_only_ids": _strings(board.get("translation_smoke_only_ids"))
                or _strings(result.get("translation_smoke_only_ids")),
                "blocked_capabilities": _strings(board.get("blocked_capabilities"))
                or _strings(result.get("blocked_capabilities")),
                "mathlib_lake_project_import_available": False,
                "body_redacted": True,
            },
            "corpora": corpora,
            "consumer_gate": {
                "case_count": consumer_projection.get("case_count")
                or result.get("consumer_case_count")
                or len(consumer_gate_rows),
                "allowed_case_ids": _strings(board.get("allowed_case_ids"))
                or _strings(result.get("allowed_case_ids")),
                "blocked_case_ids": _strings(board.get("blocked_case_ids"))
                or _strings(result.get("blocked_case_ids")),
                "decision_rows": consumer_gate_rows,
                "body_redacted": True,
            },
            "negative_case_ids": negative_case_ids,
            "error_codes": _strings(result.get("error_codes")) or _strings(board.get("error_codes")),
            "authority_ceiling": authority_ceiling,
            "safe_to_show": {
                "body_redacted": True,
                "fixture_metadata_only": True,
                "no_private_source_bodies": True,
                "no_proof_bodies": True,
                "receipt_refs_only_for_projection": True,
            },
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The public corpus-readiness lens is environment and corpus metadata only. "
                "It does not run Lean/Lake, authorize Mathlib imports, prove theorems, "
                "claim benchmark or corpus completeness, import proof bodies, call "
                "providers, mutate source, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def prediction_lens(self) -> dict[str, Any]:
        packet_ref = "examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle/reconciliation_packet.json"
        board_ref = "receipts/first_wave/prediction_oracle_reconciliation/prediction_reconciliation_board.json"
        result_ref = (
            "receipts/first_wave/prediction_oracle_reconciliation/"
            "prediction_oracle_reconciliation_result.json"
        )
        validation_ref = (
            "receipts/first_wave/prediction_oracle_reconciliation/"
            "prediction_oracle_validation_receipt.json"
        )
        acceptance_ref = (
            "receipts/acceptance/first_wave/"
            "prediction_oracle_reconciliation_fixture_acceptance.json"
        )
        packet = _read_json_if_exists(self.root / packet_ref)
        board = _read_json_if_exists(self.root / board_ref)
        result = _read_json_if_exists(self.root / result_ref)
        targets = _strings(board.get("valid_prediction_targets")) or _strings(
            packet.get("valid_prediction_targets")
        )
        source_pattern_ids = list(
            dict.fromkeys(
                [
                    *_strings(board.get("source_pattern_ids")),
                    *_strings(packet.get("source_pattern_ids")),
                ]
            )
        )
        source_refs = list(
            dict.fromkeys([*_strings(board.get("source_refs")), *_strings(packet.get("source_refs"))])
        )
        projection_refs = list(
            dict.fromkeys(
                [
                    *_strings(board.get("projection_receipt_refs")),
                    *_strings(packet.get("projection_receipt_refs")),
                ]
            )
        )
        public_replacements = list(
            dict.fromkeys(
                [
                    *_strings(board.get("public_replacement_refs")),
                    *_strings(packet.get("public_replacement_refs")),
                ]
            )
        )
        reconciliation_rows = [
            {
                "prediction_id": row.get("prediction_id"),
                "target_id": row.get("target_id"),
                "cp1_branch_id": row.get("cp1_branch_id"),
                "direction": row.get("direction"),
                "confidence_band": row.get("confidence_band"),
                "oracle_feed_health": row.get("oracle_feed_health"),
                "direction_hit": row.get("direction_hit"),
                "body_redacted": True,
            }
            for row in _rows(board, "reconciliation_rows")
        ]
        observed_negative_cases = result.get("observed_negative_cases", {})
        negative_case_ids = (
            sorted(str(key) for key in observed_negative_cases)
            if isinstance(observed_negative_cases, dict)
            else []
        )
        authority_ceiling = {
            "synthetic_fixture_only": True,
            "trading_authorized": False,
            "financial_advice_authorized": False,
            "investment_advice_authorized": False,
            "live_market_data_authorized": False,
            "provider_calls_authorized": False,
            "publication_authorized": False,
            "release_authorized": False,
            "private_data_equivalence_claim": False,
            "forecast_performance_claim": False,
            "source_mutation_authorized": False,
            "dossier_mutation_authority": "public_fixture_delta_only",
        }
        lens_path = self.runtime_receipt_dir / "public_prediction_lens.json"
        status = (
            PASS
            if board.get("status") == PASS
            and result.get("status") == PASS
            and len(targets) >= 2
            and board.get("cp2_prediction_count", 0) >= 2
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_prediction_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_prediction_lens",
            "organ_id": "prediction_oracle_reconciliation",
            "command": "microcosm prediction-lens",
            "endpoint": "/prediction",
            "organ_command": "microcosm prediction-oracle-reconciliation run-prediction-bundle",
            "prediction_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes prediction reasoning as public synthetic mechanics: "
                "target-universe gating, CP1 bifurcation resolution, CP2 prediction rows, "
                "oracle diff grading, and bounded dossier mutation."
            ),
            "input_refs": {
                "packet_ref": packet_ref,
                "board_ref": board_ref,
                "result_ref": result_ref,
                "validation_ref": validation_ref,
                "acceptance_ref": acceptance_ref,
            },
            "source_pattern_ids": source_pattern_ids,
            "source_pattern_count": len(source_pattern_ids),
            "source_refs": source_refs,
            "projection_receipt_refs": projection_refs,
            "public_replacement_refs": public_replacements,
            "mechanics": [
                {
                    "mechanic_id": "target_universe_gate",
                    "count": len(targets),
                    "examples": targets,
                    "body_redacted": True,
                },
                {
                    "mechanic_id": "cp1_bifurcation_resolution",
                    "count": board.get("cp1_branch_count", 0),
                    "selected_branch_ids": _strings(board.get("cp1_selected_branch_ids")),
                    "body_redacted": True,
                },
                {
                    "mechanic_id": "cp2_prediction_rows",
                    "count": board.get("cp2_prediction_count", 0),
                    "body_redacted": True,
                },
                {
                    "mechanic_id": "oracle_diff_grading",
                    "graded_count": board.get("oracle_diff_graded_count", 0),
                    "hit_count": board.get("oracle_diff_hit_count", 0),
                    "body_redacted": True,
                },
                {
                    "mechanic_id": "bounded_dossier_mutation",
                    "count": board.get("dossier_mutation_count", 0),
                    "mutation_ids": _strings(board.get("dossier_mutation_ids")),
                    "authority": "public_fixture_delta_only",
                    "body_redacted": True,
                },
            ],
            "reconciliation_rows": reconciliation_rows,
            "negative_case_ids": negative_case_ids,
            "authority_ceiling": authority_ceiling,
            "safe_to_show": {
                "body_redacted": True,
                "synthetic_targets_only": True,
                "no_live_market_data": True,
                "receipt_refs_only_for_macro_projection": True,
            },
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The public prediction lens is a synthetic fixture read-model. It does not "
                "trade, provide financial or investment advice, use live market data, call "
                "providers, publish predictions, claim forecast performance, import private "
                "data, mutate source, or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def market_boundary(self) -> dict[str, Any]:
        lens_path = self.runtime_receipt_dir / "public_market_prediction_evidence_boundary_lens.json"
        boundary_rows = [
            {
                "boundary_row_id": "observation_forecast_separation_gate",
                "source_signal": "prediction statements separate observed state from forecast state",
                "source_ref": "microcosm prediction-lens::mechanics",
                "owner_route": "microcosm prediction-lens",
                "validation_ref": (
                    "tests/test_runtime_shell.py::"
                    "test_runtime_shell_market_prediction_boundary_lens_is_public_safe"
                ),
                "public_rule": "observation_rows_and_forecast_rows_are_labeled_before_claims",
                "decision_boundary": "forecast_language_requires_explicit_horizon_and_uncertainty",
                "body_redacted": True,
                "live_market_data_authorized": False,
                "trading_advice_authorized": False,
                "investment_recommendation_authorized": False,
                "private_portfolio_exported": False,
                "performance_guarantee_claim": False,
                "release_authorized": False,
            },
            {
                "boundary_row_id": "base_rate_before_narrative_pressure",
                "source_signal": "forecast rows carry base-rate or prior-context hooks before narrative pressure",
                "source_ref": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::prediction_oracle_reconciliation",
                "owner_route": "microcosm market-boundary",
                "validation_ref": "tests/test_cli.py::test_cli_market_prediction_boundary_smoke",
                "public_rule": "base_rate_or_prior_context_precedes_high_conviction_language",
                "decision_boundary": "no_single_story_forecast_without_prior_context",
                "body_redacted": True,
                "live_market_data_authorized": False,
                "trading_advice_authorized": False,
                "investment_recommendation_authorized": False,
                "private_portfolio_exported": False,
                "performance_guarantee_claim": False,
                "release_authorized": False,
            },
            {
                "boundary_row_id": "scenario_tree_before_single_point_claim",
                "source_signal": "CP1 branch mechanics make alternatives visible before CP2 prediction rows",
                "source_ref": "microcosm prediction-lens::cp1_bifurcation_resolution",
                "owner_route": "microcosm prediction-lens",
                "validation_ref": (
                    "receipts/first_wave/prediction_oracle_reconciliation/"
                    "prediction_oracle_validation_receipt.json"
                ),
                "public_rule": "forecast_claims_name_plausible_alternatives_before_directional_readout",
                "decision_boundary": "single_scenario_certainty_is_rejected",
                "body_redacted": True,
                "live_market_data_authorized": False,
                "trading_advice_authorized": False,
                "investment_recommendation_authorized": False,
                "private_portfolio_exported": False,
                "performance_guarantee_claim": False,
                "release_authorized": False,
            },
            {
                "boundary_row_id": "confidence_band_not_certainty_gate",
                "source_signal": "synthetic prediction rows expose confidence bands instead of certainty claims",
                "source_ref": "receipts/first_wave/prediction_oracle_reconciliation/prediction_reconciliation_board.json",
                "owner_route": "microcosm prediction-lens",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_prediction_lens_is_public_safe",
                "public_rule": "confidence_band_is_required_and_certainty_language_is_denied",
                "decision_boundary": "forecast_is_uncertainty_annotation_not_truth_claim",
                "body_redacted": True,
                "live_market_data_authorized": False,
                "trading_advice_authorized": False,
                "investment_recommendation_authorized": False,
                "private_portfolio_exported": False,
                "performance_guarantee_claim": False,
                "release_authorized": False,
            },
            {
                "boundary_row_id": "timestamped_data_freshness_gate",
                "source_signal": "market-facing evidence must name freshness before being interpreted",
                "source_ref": "microcosm projection-safety::projection_rows",
                "owner_route": "microcosm projection-safety",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_projection_safety_lens_is_public_safe",
                "public_rule": "live_or_recent_data_claims_require_timestamp_and_source_boundary",
                "decision_boundary": "untimestamped_price_or_macro_claim_is_not_public_evidence",
                "body_redacted": True,
                "live_market_data_authorized": False,
                "trading_advice_authorized": False,
                "investment_recommendation_authorized": False,
                "private_portfolio_exported": False,
                "performance_guarantee_claim": False,
                "release_authorized": False,
            },
            {
                "boundary_row_id": "decision_policy_not_advice_gate",
                "source_signal": "policy rows explain how to reason; they do not prescribe trades",
                "source_ref": "microcosm authority::no_financial_or_trading_advice",
                "owner_route": "microcosm authority",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_authority_map_is_public_safe",
                "public_rule": "decision_policy_can_name_checks_but_not_buy_sell_hold_actions",
                "decision_boundary": "portfolio_action_or_investment_recommendation_is_rejected",
                "body_redacted": True,
                "live_market_data_authorized": False,
                "trading_advice_authorized": False,
                "investment_recommendation_authorized": False,
                "private_portfolio_exported": False,
                "performance_guarantee_claim": False,
                "release_authorized": False,
            },
            {
                "boundary_row_id": "backtest_not_live_performance_gate",
                "source_signal": "fixture evaluation can grade synthetic rows but cannot imply live performance",
                "source_ref": "receipts/first_wave/prediction_oracle_reconciliation/prediction_oracle_reconciliation_result.json",
                "owner_route": "microcosm prediction-lens",
                "validation_ref": "tests/test_runtime_shell.py::test_runtime_shell_market_prediction_boundary_lens_is_public_safe",
                "public_rule": "fixture_or_backtest_metrics_are_labeled_as_retrospective_synthetic_evidence",
                "decision_boundary": "past_fit_or_oracle_diff_score_is_not_live_performance",
                "body_redacted": True,
                "live_market_data_authorized": False,
                "trading_advice_authorized": False,
                "investment_recommendation_authorized": False,
                "private_portfolio_exported": False,
                "performance_guarantee_claim": False,
                "release_authorized": False,
            },
            {
                "boundary_row_id": "private_account_state_redaction_gate",
                "source_signal": "private account, portfolio, and brokerage state never enters the public lens",
                "source_ref": "microcosm stripping-guard::guard_rows",
                "owner_route": "microcosm stripping-guard",
                "validation_ref": (
                    "microcosm-substrate/src/microcosm_core/validators/observatory_legibility.py"
                    "::market_prediction_boundary_no_private_exports_or_advice"
                ),
                "public_rule": "portfolio_or_account_state_is_replaced_by_synthetic_fixture_metadata",
                "decision_boundary": "private_position_or_account_export_is_rejected",
                "body_redacted": True,
                "live_market_data_authorized": False,
                "trading_advice_authorized": False,
                "investment_recommendation_authorized": False,
                "private_portfolio_exported": False,
                "performance_guarantee_claim": False,
                "release_authorized": False,
            },
        ]
        negative_case_ids = [
            "buy_sell_hold_recommendation_rejected",
            "live_price_without_timestamp_rejected",
            "performance_guarantee_rejected",
            "private_portfolio_export_rejected",
            "provider_payload_as_market_evidence_rejected",
            "single_scenario_certainty_rejected",
            "backtest_as_live_performance_rejected",
            "release_or_publication_overclaim_rejected",
        ]
        authority_ceiling = {
            "synthetic_fixture_only": True,
            "read_model_only": True,
            "release_authorized": False,
            "hosted_public_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "provider_payload_exported": False,
            "source_mutation_authorized": False,
            "live_market_data_authorized": False,
            "trading_advice_authorized": False,
            "financial_advice_authorized": False,
            "investment_recommendation_authorized": False,
            "portfolio_action_authorized": False,
            "private_portfolio_exported": False,
            "private_account_state_exported": False,
            "performance_guarantee_claim": False,
            "forecast_performance_claim": False,
        }
        encoded_rows = json.dumps(boundary_rows, sort_keys=True)
        private_needles = ["/Users/", "src/ai_workflow", "Library/Application Support/Google", "sk-"]
        forbidden_keys = {
            "release_authorized",
            "hosted_public_authorized",
            "publication_authorized",
            "provider_calls_authorized",
            "provider_payload_exported",
            "source_mutation_authorized",
            "live_market_data_authorized",
            "trading_advice_authorized",
            "financial_advice_authorized",
            "investment_recommendation_authorized",
            "portfolio_action_authorized",
            "private_portfolio_exported",
            "private_account_state_exported",
            "performance_guarantee_claim",
            "forecast_performance_claim",
        }
        status = (
            PASS
            if boundary_rows
            and all(row.get("source_ref") for row in boundary_rows)
            and all(row.get("owner_route") for row in boundary_rows)
            and all(row.get("validation_ref") for row in boundary_rows)
            and all(row.get("public_rule") for row in boundary_rows)
            and all(row.get("decision_boundary") for row in boundary_rows)
            and all(row.get("body_redacted") is True for row in boundary_rows)
            and all(row.get("live_market_data_authorized") is False for row in boundary_rows)
            and all(row.get("trading_advice_authorized") is False for row in boundary_rows)
            and all(row.get("investment_recommendation_authorized") is False for row in boundary_rows)
            and all(row.get("private_portfolio_exported") is False for row in boundary_rows)
            and all(row.get("performance_guarantee_claim") is False for row in boundary_rows)
            and all(row.get("release_authorized") is False for row in boundary_rows)
            and all(authority_ceiling.get(key) is False for key in forbidden_keys)
            and authority_ceiling.get("synthetic_fixture_only") is True
            and authority_ceiling.get("read_model_only") is True
            and not any(needle in encoded_rows for needle in private_needles)
            else "blocked"
        )
        payload = {
            "schema_version": "microcosm_public_market_prediction_evidence_boundary_lens_v1",
            "created_at": utc_now(),
            "status": status,
            "lens_id": "public_market_prediction_evidence_boundary_lens",
            "organ_family": "prediction_reasoning_boundary",
            "command": "microcosm market-boundary",
            "endpoint": "/market-boundary",
            "market_boundary_lens_ref": _public_relative(lens_path, self.root),
            "public_claim": (
                "Microcosm exposes market and prediction reasoning as a public-safe "
                "claim boundary: observations are separated from forecasts, base rates "
                "and scenario trees precede directional claims, timestamps gate evidence, "
                "and decision policy is kept distinct from trading or investment advice."
            ),
            "selected_route_id": "market_prediction_evidence_boundary",
            "selected_pattern_ids": [row["boundary_row_id"] for row in boundary_rows],
            "source_projection_refs": [
                "microcosm prediction-lens::mechanics",
                "microcosm projection-safety::projection_rows",
                "microcosm authority::hard_boundaries",
                "microcosm stripping-guard::guard_rows",
                "state/microcosm_portfolio/extracted_patterns_ledger.jsonl::prediction_oracle_reconciliation",
            ],
            "boundary_rows": boundary_rows,
            "boundary_summary": {
                "row_count": len(boundary_rows),
                "source_ref_count": sum(1 for row in boundary_rows if row.get("source_ref")),
                "owner_route_count": sum(1 for row in boundary_rows if row.get("owner_route")),
                "validation_ref_count": sum(1 for row in boundary_rows if row.get("validation_ref")),
                "public_rule_count": sum(1 for row in boundary_rows if row.get("public_rule")),
                "decision_boundary_count": sum(
                    1 for row in boundary_rows if row.get("decision_boundary")
                ),
                "negative_case_count": len(negative_case_ids),
                "live_market_data_authorized_count": sum(
                    1 for row in boundary_rows if row.get("live_market_data_authorized") is True
                ),
                "trading_advice_authorized_count": sum(
                    1 for row in boundary_rows if row.get("trading_advice_authorized") is True
                ),
                "investment_recommendation_authorized_count": sum(
                    1
                    for row in boundary_rows
                    if row.get("investment_recommendation_authorized") is True
                ),
                "private_portfolio_export_count": sum(
                    1 for row in boundary_rows if row.get("private_portfolio_exported") is True
                ),
                "performance_guarantee_claim_count": sum(
                    1 for row in boundary_rows if row.get("performance_guarantee_claim") is True
                ),
                "release_authorized_count": sum(
                    1 for row in boundary_rows if row.get("release_authorized") is True
                ),
            },
            "negative_case_ids": negative_case_ids,
            "safe_to_show": {
                "body_redacted": True,
                "synthetic_fixture_only": True,
                "observations_and_forecasts_labeled": True,
                "no_live_market_data": True,
                "no_private_portfolio_or_account_state": True,
                "decision_policy_not_trading_advice": True,
                "performance_claims_denied": True,
            },
            "authority_ceiling": authority_ceiling,
            "release_authorized": False,
            "body_redacted": True,
            "anti_claim": (
                "The market-boundary lens is a public-safe read-model over synthetic "
                "prediction mechanics and projection contracts. It does not provide "
                "trading, financial, or investment advice; use live market data; export "
                "private portfolio or account state; call providers; claim forecast "
                "performance; mutate source; publish; host; or authorize release."
            ),
        }
        write_json_atomic(lens_path, payload)
        return payload

    def authority(self, *, persist_receipts: bool = True) -> dict[str, Any]:
        status = self.status()
        spine = self.spine()
        intake = self.intake()
        reveal = self.reveal(persist_receipt=persist_receipts)
        market_boundary = self.market_boundary()
        corpus_lens = self.corpus_lens()
        trace_lens = self.trace_lens()
        repair_loop = self.repair_loop()
        evidence_cells = self.evidence_cells()
        proof_loop_depth = self.proof_loop_depth()
        landing_replay = self.landing_replay()
        view_quality = self.view_quality()
        projection_safety = self.projection_safety()
        projection_drift = self.projection_drift()
        spatial_simulation = self.spatial_simulation()
        route_cleanup = self.route_cleanup()
        projection_import_map = self.projection_import_map()
        import_projector = self.import_projector()
        option_surface = self.option_surface_lens()
        stripping_guard = self.stripping_guard()
        standards_control = self.standards_control()
        hook_coverage = self.hook_coverage()
        replay_gauntlet = self.replay_gauntlet()
        benchmark_lab = self.benchmark_lab()
        legibility_scorecard = self.legibility_scorecard()
        authority_ceiling = {
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
        surfaces = [
            {
                "surface_id": "runtime_status",
                "command": "microcosm status",
                "endpoint": "/status",
                "authority_role": "runtime health projection",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
            },
            {
                "surface_id": "public_runtime_spine",
                "command": "microcosm spine",
                "endpoint": "/spine",
                "authority_role": "accepted organ and first-run route projection",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
            },
            {
                "surface_id": "public_ten_minute_tour",
                "command": "microcosm tour <project>",
                "endpoint": "/tour",
                "authority_role": "cold-reader launch path compression",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "private_data_equivalence_claim": False,
            },
            {
                "surface_id": "project_python_lens",
                "command": "microcosm python-lens <project>",
                "endpoint": "/project/python-lens",
                "authority_role": "project-local Python route/readiness lens",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "source_bodies_exported": False,
                "static_analysis_authority_claim": False,
            },
            {
                "surface_id": "public_authority_map",
                "command": "microcosm authority",
                "endpoint": "/authority",
                "authority_role": "global authority ceiling and anti-claim index",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
            },
            {
                "surface_id": "public_prediction_lens",
                "command": "microcosm prediction-lens",
                "endpoint": "/prediction",
                "authority_role": "synthetic prediction mechanics and no-advice boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "trading_or_financial_advice_authorized": False,
            },
            {
                "surface_id": "public_market_prediction_evidence_boundary_lens",
                "command": "microcosm market-boundary",
                "endpoint": "/market-boundary",
                "authority_role": "market and prediction claim boundary with no-advice ceiling",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_market_data_authorized": False,
                "trading_or_financial_advice_authorized": False,
                "investment_recommendation_authorized": False,
                "private_portfolio_exported": False,
                "performance_guarantee_claim": False,
            },
            {
                "surface_id": "public_corpus_readiness_lens",
                "command": "microcosm corpus-lens",
                "endpoint": "/corpus",
                "authority_role": "formal-math corpus/toolchain readiness and Mathlib-absence boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "lean_lake_execution_authorized": False,
                "mathlib_dependent_proof_authority": False,
                "benchmark_or_corpus_completeness_authority": False,
            },
            {
                "surface_id": "public_verifier_trace_repair_lens",
                "command": "microcosm trace-lens",
                "endpoint": "/trace",
                "authority_role": "formal verifier trace-repair metadata lens and no-proof boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "lean_lake_execution_authorized": False,
                "formal_proof_authority": False,
                "proof_correctness_claim": False,
                "proof_bodies_exported": False,
                "oracle_needed_premise_ids_exported": False,
            },
            {
                "surface_id": "public_verifier_repair_loop_lens",
                "command": "microcosm repair-loop",
                "endpoint": "/repair-loop",
                "authority_role": "formal verifier repair-loop curriculum and cold-rerun boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "lean_lake_execution_authorized": False,
                "formal_proof_authority": False,
                "proof_correctness_claim": False,
                "proof_bodies_exported": False,
                "oracle_needed_premise_ids_exported": False,
                "curriculum_scope": "metadata_only",
            },
            {
                "surface_id": "public_formal_evidence_cell_lens",
                "command": "microcosm evidence-cells",
                "endpoint": "/evidence-cells",
                "authority_role": "formal evidence-cell resolver and claim-strength boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "lean_lake_execution_authorized": False,
                "formal_proof_authority": False,
                "proof_correctness_claim": False,
                "proof_bodies_exported": False,
                "private_source_refs_exported": False,
                "general_theorem_solution_claim": False,
            },
            {
                "surface_id": "public_proof_loop_depth_lens",
                "command": "microcosm proof-loop-depth",
                "endpoint": "/proof-loop-depth",
                "authority_role": "formal proof-loop depth map and metadata-only proof boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "lean_lake_execution_authorized": False,
                "formal_proof_authority": False,
                "proof_correctness_claim": False,
                "general_theorem_solution_claim": False,
                "benchmark_score_claim": False,
                "proof_bodies_exported": False,
                "oracle_needed_premise_ids_exported": False,
                "curriculum_scope": "metadata_only",
            },
            {
                "surface_id": "public_verifier_lab_kernel_lens",
                "command": "microcosm verifier-lab-kernel run-kernel-bundle",
                "endpoint": "/proof-loop-depth",
                "authority_role": (
                    "bounded verifier-lab composition kernel and proof-authority "
                    "separation boundary"
                ),
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "formal_proof_authority": False,
                "private_proof_body_exported": False,
                "provider_hypothesis_proof_authority": False,
                "oracle_forward_contamination_authorized": False,
                "arbitrary_evolve_execution_authorized": False,
                "bounded_public_lean_witness_only": True,
            },
            {
                "surface_id": "public_verifier_lab_execution_spine_lens",
                "command": (
                    "microcosm verifier-lab-execution-spine "
                    "run-execution-bundle"
                ),
                "endpoint": "/proof-loop-depth",
                "authority_role": (
                    "bounded verifier-lab execution spine and external "
                    "tool-witness boundary"
                ),
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "formal_proof_authority": False,
                "proof_correctness_claim": False,
                "private_proof_body_exported": False,
                "provider_hypothesis_proof_authority": False,
                "oracle_forward_contamination_authorized": False,
                "arbitrary_evolve_execution_authorized": False,
                "bounded_public_external_witness_only": True,
            },
            {
                "surface_id": "public_work_landing_replay_lens",
                "command": "microcosm landing-replay",
                "endpoint": "/landing-replay",
                "authority_role": "dirty-tree work landing replay and commit-claim boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_git_mutation_authorized": False,
                "broad_checkpoint_authorized": False,
                "unrelated_dirty_paths_authorized": False,
            },
            {
                "surface_id": "public_view_quality_action_map_lens",
                "command": "microcosm view-quality",
                "endpoint": "/view-quality",
                "authority_role": "synthetic all-view action map and UI-observability boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_browser_control_authorized": False,
                "private_screenshot_paths_exported": False,
                "complete_frontend_quality_claim": False,
            },
            {
                "surface_id": "public_projection_safety_audit_lens",
                "command": "microcosm projection-safety",
                "endpoint": "/projection-safety",
                "authority_role": "omission receipt and reversible projection boundary audit",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "private_body_exported": False,
                "proof_body_exported": False,
                "provider_payload_exported": False,
            },
            {
                "surface_id": "public_projection_drift_control_lens",
                "command": "microcosm drift-control",
                "endpoint": "/drift-control",
                "authority_role": "projection drift, route repair, and CAP assimilation read-model",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "source_authority_claim": False,
                "live_repair_authorized": False,
                "live_task_ledger_mutation_authorized": False,
                "private_runtime_data_exported": False,
                "automatic_doctrine_promotion_authorized": False,
            },
            {
                "surface_id": "public_spatial_world_model_counterfactual_simulation_replay_lens",
                "command": "microcosm spatial-simulation",
                "endpoint": "/spatial-simulation",
                "authority_role": "synthetic spatial counterfactual replay and simulator-claim boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "private_video_exported": False,
                "raw_sensor_data_exported": False,
                "live_robot_operation_authorized": False,
                "live_av_operation_authorized": False,
                "real_world_location_claim_authorized": False,
                "geographic_accuracy_claim_authorized": False,
                "benchmark_score_claim_authorized": False,
            },
            {
                "surface_id": (
                    "public_materials_chemistry_closed_loop_lab_safety_replay_lens"
                ),
                "command": (
                    "microcosm materials-chemistry-closed-loop-lab-safety-replay "
                    "run-lab-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "authority_role": (
                    "synthetic materials active-learning replay and "
                    "autonomous-lab safety boundary"
                ),
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "wet_lab_protocol_authorized": False,
                "hazardous_synthesis_authorized": False,
                "reagent_quantity_export_authorized": False,
                "live_lab_credential_export_authorized": False,
                "robot_command_authorized": False,
                "private_lab_notebook_export_authorized": False,
                "live_assay_or_discovery_claim_authorized": False,
                "benchmark_score_claim_authorized": False,
            },
            {
                "surface_id": (
                    "public_mechanistic_interpretability_circuit_"
                    "attribution_replay_lens"
                ),
                "command": "microcosm circuit-attribution",
                "endpoint": "/circuit-attribution",
                "authority_role": (
                    "synthetic circuit attribution replay and mechanistic "
                    "interpretability claim boundary"
                ),
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "private_model_weights_export_authorized": False,
                "raw_activation_dump_export_authorized": False,
                "proprietary_prompt_export_authorized": False,
                "hidden_chain_of_thought_export_authorized": False,
                "model_transparency_product_claim_authorized": False,
                "private_model_internals_claim_authorized": False,
                "benchmark_score_claim_authorized": False,
            },
            {
                "surface_id": "public_route_cleanup_contract_lens",
                "command": "microcosm route-cleanup",
                "endpoint": "/route-cleanup",
                "authority_role": "route cleanup contract, owner route, and validation boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "route_deletion_authorized": False,
                "live_route_repair_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "private_body_exported": False,
                "provider_payload_exported": False,
                "automatic_doctrine_promotion_authorized": False,
            },
            {
                "surface_id": "public_projection_import_map_lens",
                "command": "microcosm projection-import-map",
                "endpoint": "/projection-import-map",
                "authority_role": "public macro-pattern to runtime-lens import map and stripping boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "private_body_export_authorized": False,
                "proof_body_export_authorized": False,
                "provider_payload_export_authorized": False,
                "private_data_equivalence_claim": False,
                "automated_import_guarantee": False,
            },
            {
                "surface_id": "public_import_projector_contract_lens",
                "command": "microcosm import-projector",
                "endpoint": "/import-projector",
                "authority_role": "repeatable public projection import contract and closeout checklist",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "private_body_export_authorized": False,
                "proof_body_export_authorized": False,
                "provider_payload_export_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "automated_import_execution_authorized": False,
                "private_data_equivalence_claim": False,
                "lossless_projection_claim": False,
            },
            {
                "surface_id": "public_compression_profile_option_surface_lens",
                "command": "microcosm option-surface-lens",
                "endpoint": "/option-surface-lens",
                "authority_role": "compression-profile governed option-surface read-model and profile-switch boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "private_body_export_authorized": False,
                "provider_payload_export_authorized": False,
                "generated_region_hand_edit_authorized": False,
                "profile_switch_execution_authorized": False,
                "automatic_profile_selection_authorized": False,
                "private_data_equivalence_claim": False,
                "lossless_projection_claim": False,
            },
            {
                "surface_id": "public_stripping_guard_lens",
                "command": "microcosm stripping-guard",
                "endpoint": "/stripping-guard",
                "authority_role": "public/private stripping export guard and anti-claim boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "private_body_export_authorized": False,
                "proof_body_export_authorized": False,
                "provider_payload_export_authorized": False,
                "raw_private_path_export_authorized": False,
                "secret_detection_completeness_claim": False,
                "financial_advice_authorized": False,
                "private_data_equivalence_claim": False,
            },
            {
                "surface_id": "public_standards_control_lens",
                "command": "microcosm standards-control",
                "endpoint": "/standards-control",
                "authority_role": "standards registry, standard pressure, validator coverage, and docs-control boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "standards_registry_source_authority": False,
                "standards_completeness_claim": False,
                "private_body_export_authorized": False,
                "proof_body_export_authorized": False,
                "provider_payload_export_authorized": False,
                "private_data_equivalence_claim": False,
            },
            {
                "surface_id": "public_hook_intervention_coverage_lens",
                "command": "microcosm hook-coverage",
                "endpoint": "/hook-coverage",
                "authority_role": "agent observability hook-intervention coverage and live-state boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_operator_state_read": False,
                "provider_payload_read": False,
                "browser_hud_cockpit_state_read": False,
                "live_task_ledger_mutation_authorized": False,
                "pattern_assimilation_authorized": False,
                "runtime_behavior_certification_authorized": False,
            },
            {
                "surface_id": "public_agent_reliability_replay_gauntlet_lens",
                "command": "microcosm replay-gauntlet",
                "endpoint": "/replay-gauntlet",
                "authority_role": "synthetic agent reliability replay and containment boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_agent_execution_authorized": False,
                "live_tool_calls_authorized": False,
                "real_secret_material_exported": False,
                "real_user_memory_imported": False,
                "sandbox_escape_authorized": False,
                "benchmark_performance_claim": False,
                "complete_security_claim": False,
            },
            {
                "surface_id": "public_agent_monitor_redteam_falsification_lens",
                "command": (
                    "microcosm agent-monitor-redteam-falsification-replay "
                    "run-monitor-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "authority_role": "synthetic monitor redteam falsification replay and product-claim boundary",
                "runtime_mode": "drilldown_only",
                "product_path_role": "drilldown_regression_not_runtime_spine",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_agent_execution_authorized": False,
                "live_agent_traffic_import_authorized": False,
                "private_reasoning_export_authorized": False,
                "internal_code_export_authorized": False,
                "exploit_instruction_export_authorized": False,
                "credential_material_export_authorized": False,
                "monitor_product_performance_claim_authorized": False,
                "control_eval_score_claim_authorized": False,
            },
            {
                "surface_id": "public_agent_sabotage_scheming_monitor_replay_lens",
                "command": (
                    "microcosm agent-sabotage-scheming-monitor-replay "
                    "run-sabotage-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "authority_role": (
                    "synthetic agent sabotage scheming-monitor replay and "
                    "live-sabotage/deployment-claim boundary"
                ),
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "runtime_mode": "drilldown_only",
                "product_path_role": "drilldown_regression_not_runtime_spine",
                "live_agent_execution_authorized": False,
                "live_sabotage_authorized": False,
                "private_reasoning_export_authorized": False,
                "harmful_payload_export_authorized": False,
                "exploit_instruction_export_authorized": False,
                "credential_material_export_authorized": False,
                "deployment_risk_claim_authorized": False,
                "monitor_product_performance_claim_authorized": False,
            },
            {
                "surface_id": "public_agent_sandbox_policy_escape_replay_lens",
                "command": (
                    "microcosm agent-sandbox-policy-escape-replay "
                    "run-sandbox-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "authority_role": "synthetic agent sandbox policy-escape replay and containment-policy boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_agent_execution_authorized": False,
                "live_sandbox_escape_authorized": False,
                "live_secret_or_credential_handling_authorized": False,
                "live_network_access_authorized": False,
                "host_filesystem_mutation_authorized": False,
                "executable_escape_payload_export_authorized": False,
                "raw_environment_export_authorized": False,
                "security_benchmark_claim_authorized": False,
            },
            {
                "surface_id": "public_indirect_prompt_injection_information_flow_policy_replay_lens",
                "command": (
                    "microcosm indirect-prompt-injection-information-flow-policy-replay "
                    "run-prompt-injection-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "authority_role": "synthetic indirect prompt-injection information-flow replay and source-trust boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_tool_call_authorized": False,
                "real_email_or_document_account_use_authorized": False,
                "raw_prompt_body_export_authorized": False,
                "secret_or_credential_exfiltration_authorized": False,
                "tool_output_instruction_authority_authorized": False,
                "hidden_system_message_promotion_authorized": False,
                "general_prompt_injection_robustness_claim_authorized": False,
                "benchmark_score_claim_authorized": False,
            },
            {
                "surface_id": "public_agentic_vulnerability_discovery_patch_proof_replay_lens",
                "command": (
                    "microcosm agentic-vulnerability-discovery-patch-proof-replay "
                    "run-patch-proof-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "authority_role": (
                    "synthetic agentic vulnerability patch-proof replay and "
                    "live-security boundary"
                ),
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_target_authorized": False,
                "real_cve_exploitation_authorized": False,
                "weaponized_payload_export_authorized": False,
                "credential_handling_authorized": False,
                "network_exfiltration_authorized": False,
                "exploit_instruction_authorized": False,
                "benchmark_score_claim_authorized": False,
            },
            {
                "surface_id": "public_certificate_kernel_execution_lab_lens",
                "command": (
                    "microcosm certificate-kernel-execution-lab "
                    "run-certificate-bundle"
                ),
                "endpoint": "/proof-loop-depth",
                "authority_role": (
                    "public certificate-kernel execution lab and external "
                    "Lean/Lake witness boundary"
                ),
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "formal_proof_authority": False,
                "proof_correctness_claim": False,
                "private_proof_body_exported": False,
                "private_source_refs_exported": False,
                "arbitrary_evolve_execution_authorized": False,
                "bounded_public_external_witness_only": True,
            },
            {
                "surface_id": "public_agent_memory_temporal_conflict_lens",
                "command": (
                    "microcosm agent-memory-temporal-conflict-replay "
                    "run-memory-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "authority_role": "agent-execution trace-backed memory temporal-conflict refactor and source-authority boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_memory_product_claim_authorized": False,
                "private_transcript_export_authorized": False,
                "private_candidate_auto_promotion_authorized": False,
                "memory_as_source_authority_authorized": False,
                "active_injection_authority_authorized": False,
                "vector_recall_without_evidence_authorized": False,
            },
            {
                "surface_id": "public_sleeper_memory_poisoning_quarantine_lens",
                "command": (
                    "microcosm sleeper-memory-poisoning-quarantine-replay "
                    "run-quarantine-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "authority_role": "synthetic sleeper memory poisoning quarantine replay and persistence-safety boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_memory_product_claim_authorized": False,
                "live_user_memory_claim_authorized": False,
                "private_memory_body_export_authorized": False,
                "raw_transcript_export_authorized": False,
                "trusted_promotion_from_untrusted_context_authorized": False,
                "benchmark_score_claim_authorized": False,
            },
            {
                "surface_id": "public_mcp_tool_authority_replay_lens",
                "command": (
                    "microcosm mcp-tool-authority-replay "
                    "run-tool-authority-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "authority_role": "synthetic MCP tool-authority replay and tool side-effect boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_mcp_account_access_authorized": False,
                "credential_export_authorized": False,
                "untrusted_tool_output_instruction_authorized": False,
                "unapproved_side_effect_authorized": False,
                "benchmark_score_claim_authorized": False,
            },
            {
                "surface_id": (
                    "public_proof_derived_governed_mutation_authorization_lens"
                ),
                "command": (
                    "microcosm proof-derived-governed-mutation-authorization "
                    "run-authorization-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "authority_role": (
                    "synthetic proof-derived governed mutation authorization "
                    "and side-effect boundary"
                ),
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_cloud_account_authorized": False,
                "standing_credentials_authorized": False,
                "policy_after_execution_authorized": False,
                "hidden_policy_votes_authorized": False,
                "irreversible_mutation_authorized": False,
                "benchmark_score_claim_authorized": False,
            },
            {
                "surface_id": "public_belief_state_process_reward_replay_lens",
                "command": (
                    "microcosm belief-state-process-reward-replay "
                    "run-reward-bundle"
                ),
                "endpoint": "/replay-gauntlet",
                "authority_role": (
                    "source-faithful public agent-execution trace over "
                    "belief-state process reward evidence"
                ),
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "hidden_reasoning_export_authorized": False,
                "live_rl_training_authorized": False,
                "neural_judge_only_authorized": False,
                "hidden_gold_label_authorized": False,
                "benchmark_score_claim_authorized": False,
            },
            {
                "surface_id": "public_repository_benchmark_transaction_lab_lens",
                "command": "microcosm benchmark-lab",
                "endpoint": "/benchmark-lab",
                "authority_role": "synthetic repository benchmark transaction lab and oracle-grading boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "live_repo_mutation_authorized": False,
                "benchmark_score_claim": False,
                "swe_bench_performance_claim": False,
                "production_delivery_rate_claim": False,
                "private_repo_exported": False,
            },
            {
                "surface_id": "public_cold_reader_legibility_scorecard_lens",
                "command": "microcosm legibility-scorecard",
                "endpoint": "/legibility-scorecard",
                "authority_role": "cold-reader comprehension path scorecard and anti-claim boundary",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "private_data_equivalence_claim": False,
                "proof_correctness_claim": False,
                "benchmark_score_claim": False,
                "reader_success_guarantee": False,
            },
            {
                "surface_id": "runtime_reveal_import_bridge",
                "command": "microcosm intake",
                "endpoint": "/intake",
                "authority_role": "projection-cell status and receipt ref bridge",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
            },
            {
                "surface_id": "public_reveal_view",
                "command": "microcosm reveal",
                "endpoint": "/reveal",
                "authority_role": "ten-minute reveal board projection",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
            },
            {
                "surface_id": "local_observatory",
                "command": "microcosm serve <project>",
                "endpoint": "/",
                "authority_role": "browser read-model over local project substrate state",
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
            },
        ]
        organ_authority = [
            {
                "ordinal": row.get("ordinal"),
                "organ_id": row.get("organ_id"),
                "runtime_mode": row.get("runtime_mode"),
                "input_mode": row.get("input_mode"),
                "authority_ref": row.get("current_authority_receipt"),
                "generated_receipt_count": row.get("generated_receipt_count"),
                "evidence_class": row.get("evidence_class"),
                "evidence_strength_rank": row.get("evidence_strength_rank"),
                "truth_accounting_bucket": row.get("truth_accounting_bucket"),
                "counts_as_real_substrate_progress": row.get(
                    "counts_as_real_substrate_progress"
                )
                is True,
                "evaluator_basis": row.get("evaluator_basis"),
                "verdict_source": row.get("verdict_source"),
                "negative_case_independence": row.get("negative_case_independence"),
                "claim_ceiling": row.get("claim_ceiling"),
                "classification_basis": row.get("classification_basis"),
                "evidence_strength_disclosed": row.get("evidence_strength_disclosed") is True,
                "release_authorized": False,
                "source_mutation_authorized": False,
                "provider_calls_authorized": False,
                "private_data_equivalence_claim": False,
            }
            for row in _rows(spine, "accepted_runtime_spine")
        ]
        evidence_class_counts = _evidence_class_counts(organ_authority)
        truth_accounting = _truth_accounting(organ_authority)
        bridge_cells = [
            {
                "cell_id": row.get("cell_id"),
                "projection_status": row.get("projection_status"),
                "cell_state": row.get("cell_state"),
                "action_required": row.get("action_required") is True,
                "next_runtime_surface": row.get("next_runtime_surface"),
            }
            for row in _rows(intake, "cell_status")
        ]
        evidence_refs = list(
            dict.fromkeys(
                [
                    *[
                        str(ref)
                        for ref in intake.get("runtime_bridge_evidence_refs", [])
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (reveal.get("evidence_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (corpus_lens.get("corpus_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (market_boundary.get("market_boundary_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (trace_lens.get("trace_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (repair_loop.get("repair_loop_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (evidence_cells.get("evidence_cell_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (proof_loop_depth.get("proof_loop_depth_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (landing_replay.get("landing_replay_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (view_quality.get("view_quality_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (projection_safety.get("projection_safety_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (projection_drift.get("projection_drift_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (
                            spatial_simulation.get("spatial_simulation_lens_ref"),
                        )
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (route_cleanup.get("route_cleanup_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (projection_import_map.get("projection_import_map_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (import_projector.get("import_projector_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (option_surface.get("option_surface_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (stripping_guard.get("stripping_guard_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (standards_control.get("standards_control_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (hook_coverage.get("hook_intervention_coverage_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (replay_gauntlet.get("replay_gauntlet_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (benchmark_lab.get("benchmark_lab_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (legibility_scorecard.get("legibility_scorecard_ref"),)
                        if isinstance(ref, str)
                    ],
                ]
            )
        )
        hard_boundaries = [
            {
                "boundary_id": "no_release_or_publication",
                "allowed": False,
                "reason": "local research prototype; release/publication needs external review",
            },
            {
                "boundary_id": "no_provider_calls",
                "allowed": False,
                "reason": "runtime surfaces validate exported public bundles and project-local state only",
            },
            {
                "boundary_id": "no_source_mutation",
                "allowed": False,
                "reason": "compile, explain, serve, and organ validators write .microcosm/ or receipts only",
            },
            {
                "boundary_id": "no_private_body_import",
                "allowed": False,
                "reason": "macro material enters only through redacted projection metadata and public replacements",
            },
            {
                "boundary_id": "no_general_proof_or_benchmark_claim",
                "allowed": False,
                "reason": "formal-math cells are metadata, retrieval, or tiny public witness fixtures",
            },
            {
                "boundary_id": "no_financial_or_trading_advice",
                "allowed": False,
                "reason": "prediction fixtures are synthetic reasoning mechanics, not advice or live market data",
            },
        ]
        safe_local_exceptions = [
            {
                "exception_id": "project_local_state_writes",
                "allowed": True,
                "scope": ".microcosm/ inside the selected project",
            },
            {
                "exception_id": "public_receipt_writes",
                "allowed": True,
                "scope": "receipts/ inside this public root",
            },
            {
                "exception_id": "bounded_public_lean_witness",
                "allowed": True,
                "scope": "formal_math_lean_proof_witness only; no Mathlib expansion",
            },
        ]
        authority_ok = all(value is False for value in authority_ceiling.values())
        status_ok = all(
            payload.get("status") == PASS
            for payload in (
                status,
                spine,
                intake,
                reveal,
                market_boundary,
                corpus_lens,
                trace_lens,
                repair_loop,
                evidence_cells,
                proof_loop_depth,
                landing_replay,
                view_quality,
                projection_safety,
                projection_drift,
                spatial_simulation,
                route_cleanup,
                projection_import_map,
                import_projector,
                option_surface,
                stripping_guard,
                standards_control,
                hook_coverage,
                replay_gauntlet,
                benchmark_lab,
                legibility_scorecard,
            )
            if isinstance(payload, dict)
        )
        authority_path = self.runtime_receipt_dir / "public_authority_map.json"
        payload = {
            "schema_version": "microcosm_public_authority_map_v1",
            "status": PASS if authority_ok and status_ok else "blocked",
            "map_id": "public_authority_map",
            "public_claim": (
                "Microcosm makes its public authority ceiling inspectable as data: "
                "what is runnable, what evidence class it belongs to, and what remains "
                "forbidden."
            ),
            "command": "microcosm authority",
            "endpoint": "/authority",
            "authority_map_ref": _public_relative(authority_path, self.root),
            "projection_not_authority": True,
            "body_redacted": True,
            "release_authorized": False,
            "command_path": [
                "microcosm compile <project>",
                "microcosm tour <project>",
                "microcosm python-lens <project>",
                "microcosm authority",
                "microcosm spine",
                "microcosm prediction-lens",
                "microcosm market-boundary",
                "microcosm corpus-lens",
                "microcosm trace-lens",
                "microcosm repair-loop",
                "microcosm evidence-cells",
                "microcosm proof-loop-depth",
                "microcosm verifier-lab-execution-spine run-execution-bundle",
                "microcosm certificate-kernel-execution-lab run-certificate-bundle",
                "microcosm landing-replay",
                "microcosm view-quality",
                "microcosm projection-safety",
                "microcosm drift-control",
                "microcosm spatial-simulation",
                "microcosm circuit-attribution",
                "microcosm route-cleanup",
                "microcosm projection-import-map",
                "microcosm import-projector",
                "microcosm stripping-guard",
                "microcosm standards-control",
                "microcosm hook-coverage",
                "microcosm replay-gauntlet",
                (
                    "microcosm agent-memory-temporal-conflict-replay "
                    "run-memory-bundle"
                ),
                (
                    "microcosm sleeper-memory-poisoning-quarantine-replay "
                    "run-quarantine-bundle"
                ),
                (
                    "microcosm mcp-tool-authority-replay "
                    "run-tool-authority-bundle"
                ),
                (
                    "microcosm proof-derived-governed-mutation-authorization "
                    "run-authorization-bundle"
                ),
                (
                    "microcosm belief-state-process-reward-replay "
                    "run-reward-bundle"
                ),
                (
                    "microcosm certificate-kernel-execution-lab "
                    "run-certificate-bundle"
                ),
                "microcosm benchmark-lab",
                "microcosm legibility-scorecard",
                "microcosm intake",
                "microcosm reveal",
                "microcosm serve <project>",
                "microcosm evidence inspect <receipt>",
            ],
            "authority_ceiling": authority_ceiling,
            "surface_authority": surfaces,
            "organ_authority": organ_authority,
            "projection_cells": bridge_cells,
            "surface_counts": {
                "surface_authority_count": len(surfaces),
                "organ_authority_count": len(organ_authority),
                "organ_evidence_class_count": len(evidence_class_counts),
                "adapter_backed_count_is_product_progress": False,
                "real_substrate_progress_count": truth_accounting[
                    "real_substrate_progress_count"
                ],
                "non_progress_organ_count": truth_accounting["non_progress_organ_count"],
                "regression_negative_fixture_count": truth_accounting[
                    "regression_negative_fixture_count"
                ],
                "projection_cell_count": len(bridge_cells),
                "hard_boundary_count": len(hard_boundaries),
                "safe_local_exception_count": len(safe_local_exceptions),
            },
            "truth_accounting": truth_accounting,
            "evidence_class_registry": spine.get("evidence_class_registry"),
            "evidence_class_counts": evidence_class_counts,
            "evidence_refs": evidence_refs,
            "hard_boundaries": hard_boundaries,
            "safe_local_exceptions": safe_local_exceptions,
            "source_surfaces": [
                "core/organ_registry.json",
                "core/acceptance/first_wave_acceptance.json",
                "microcosm spine",
                "microcosm tour <project>",
                "microcosm python-lens <project>",
                "microcosm intake",
                "microcosm reveal",
                "microcosm prediction-lens",
                "microcosm market-boundary",
                "microcosm corpus-lens",
                "microcosm trace-lens",
                "microcosm repair-loop",
                "microcosm evidence-cells",
                "microcosm proof-loop-depth",
                "microcosm landing-replay",
                "microcosm view-quality",
                "microcosm projection-safety",
                "microcosm drift-control",
                "microcosm route-cleanup",
                "microcosm projection-import-map",
                "microcosm import-projector",
                "microcosm stripping-guard",
                "microcosm standards-control",
                "microcosm hook-coverage",
                "microcosm replay-gauntlet",
                "microcosm benchmark-lab",
                "microcosm legibility-scorecard",
            ],
            "anti_claim": (
                "The authority map is a public-safe index over command outputs, receipt refs, "
                "and accepted organ metadata. It does not authorize release, hosted public "
                "deployment, publication, provider calls, source mutation, private-data "
                "equivalence, general proof authority, trading advice, or whole-system "
                "correctness claims."
            ),
        }
        if persist_receipts:
            write_json_atomic(authority_path, payload)
        return payload

    def intake(self) -> dict[str, Any]:
        projection_input = (
            self.root / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
        )
        reveal_input = self.root / "examples/public_reveal_walkthrough/exported_public_reveal_bundle"
        out_dir = self.runtime_receipt_dir / "intake_bridge"
        reveal_out = out_dir / "organs" / "public_reveal_walkthrough"
        reveal_result = public_reveal_walkthrough.run_reveal_bundle(
            reveal_input,
            reveal_out,
            "microcosm intake",
        )
        projection_preview = macro_projection_import_protocol.preview_import_plan(
            projection_input,
            "microcosm intake",
        )
        projection_board = projection_preview.get("projection_intake_board", {})
        cells = _rows(projection_board if isinstance(projection_board, dict) else {}, "projection_cells")
        cells_by_id = {str(row.get("cell_id") or ""): row for row in cells}
        runtime_cell = cells_by_id.get("runtime_reveal_import_bridge", {})
        formal_cell = cells_by_id.get("formal_math_readiness_extensions", {})
        self_host_cell = cells_by_id.get("projection_protocol_self_host", {})
        formal_board_ref = (
            self.root
            / "receipts/first_wave/formal_math_readiness_gate/formal_math_readiness_extension_board.json"
        )
        formal_board = _read_json_if_exists(formal_board_ref)
        projection_self_host_refs = [
            "standards/std_microcosm_macro_projection_import_protocol.json",
            "paper_modules/macro_projection_import_protocol.md",
        ]
        reveal_receipt_ref = _public_relative(
            reveal_out / public_reveal_walkthrough.BUNDLE_RESULT_NAME,
            self.root,
        )
        bridge_receipt_ref = _public_relative(out_dir / "runtime_reveal_import_bridge.json", self.root)
        formal_projection_status = (
            formal_board.get("projection_status")
            or formal_cell.get("projection_status")
            or "ready_in_intake_board"
        )
        formal_projection_status = _normalize_runtime_projection_status(formal_projection_status)
        self_host_projection_status = (
            self_host_cell.get("projection_status") or "self_describing_protocol_available"
        )
        runtime_projection_status = runtime_cell.get("projection_status") or "landed_as_microcosm_intake"
        cell_status = [
            {
                "cell_id": "formal_math_readiness_extensions",
                "intake_ready": formal_cell.get("ready_to_project") is True,
                "projection_status": formal_projection_status,
                "cell_state": formal_cell.get("cell_state"),
                "action_required": formal_cell.get("action_required") is True,
                "status_reason": formal_cell.get("status_reason"),
                "landed_evidence_refs": formal_cell.get("landed_evidence_refs", []),
                "next_runtime_surface": formal_cell.get("next_runtime_surface"),
                "runtime_bridge_status": formal_projection_status,
                "selected_pattern_ids": formal_cell.get("selected_pattern_ids", []),
                "target_refs": formal_board.get("target_refs") or formal_cell.get("target_refs", []),
                "validation_refs": formal_board.get("validation_refs") or formal_cell.get("validation_refs", []),
                "authority_ceiling": formal_board.get("authority_ceiling") or formal_cell.get("authority_ceiling"),
                "body_in_receipt": False,
            },
            {
                "cell_id": "projection_protocol_self_host",
                "intake_ready": self_host_cell.get("ready_to_project") is True,
                "projection_status": self_host_projection_status,
                "cell_state": self_host_cell.get("cell_state"),
                "action_required": self_host_cell.get("action_required") is True,
                "status_reason": self_host_cell.get("status_reason"),
                "landed_evidence_refs": self_host_cell.get("landed_evidence_refs", []),
                "next_runtime_surface": self_host_cell.get("next_runtime_surface"),
                "runtime_bridge_status": self_host_projection_status,
                "selected_pattern_ids": self_host_cell.get("selected_pattern_ids", []),
                "target_refs": self_host_cell.get("target_refs") or projection_self_host_refs,
                "validation_refs": self_host_cell.get("validation_refs", []),
                "authority_ceiling": self_host_cell.get("authority_ceiling"),
                "body_in_receipt": False,
            },
            {
                "cell_id": "runtime_reveal_import_bridge",
                "intake_ready": runtime_cell.get("ready_to_project") is True,
                "projection_status": runtime_projection_status,
                "cell_state": runtime_cell.get("cell_state"),
                "action_required": runtime_cell.get("action_required") is True,
                "status_reason": runtime_cell.get("status_reason"),
                "landed_evidence_refs": list(
                    dict.fromkeys(
                        [
                            bridge_receipt_ref,
                            reveal_receipt_ref,
                            *[
                                str(ref)
                                for ref in runtime_cell.get("landed_evidence_refs", [])
                                if isinstance(ref, str)
                            ],
                        ]
                    )
                ),
                "next_runtime_surface": runtime_cell.get("next_runtime_surface") or "microcosm intake",
                "runtime_bridge_status": "landed_as_microcosm_intake",
                "selected_pattern_ids": runtime_cell.get("selected_pattern_ids", []),
                "target_refs": [
                    "microcosm intake",
                    "microcosm spine",
                    "microcosm reveal",
                    *[
                        str(ref)
                        for ref in runtime_cell.get("target_refs", [])
                        if isinstance(ref, str)
                    ],
                ],
                "validation_refs": [
                    bridge_receipt_ref,
                    reveal_receipt_ref,
                    *[
                        str(ref)
                        for ref in runtime_cell.get("validation_refs", [])
                        if isinstance(ref, str)
                    ],
                ],
                "authority_ceiling": runtime_cell.get("authority_ceiling"),
                "body_in_receipt": False,
            },
        ]
        modeled_cell_ids = {str(row.get("cell_id") or "") for row in cell_status}
        for cell in cells:
            cell_id = str(cell.get("cell_id") or "")
            if not cell_id or cell_id in modeled_cell_ids:
                continue
            projection_status = _normalize_runtime_projection_status(
                cell.get("projection_status")
            )
            cell_status.append(
                {
                    "cell_id": cell_id,
                    "intake_ready": cell.get("ready_to_project") is True,
                    "projection_status": projection_status,
                    "cell_state": cell.get("cell_state"),
                    "action_required": cell.get("action_required") is True,
                    "status_reason": cell.get("status_reason"),
                    "landed_evidence_refs": cell.get("landed_evidence_refs", []),
                    "next_runtime_surface": cell.get("next_runtime_surface"),
                    "runtime_bridge_status": projection_status,
                    "selected_pattern_ids": cell.get("selected_pattern_ids", []),
                    "target_refs": cell.get("target_refs", []),
                    "validation_refs": cell.get("validation_refs", []),
                    "authority_ceiling": cell.get("authority_ceiling"),
                    "body_in_receipt": False,
                }
            )
        payload = {
            "schema_version": "microcosm_runtime_reveal_import_bridge_v1",
            "created_at": utc_now(),
            "status": PASS
            if projection_preview.get("status") == PASS and reveal_result.get("status") == PASS
            else "blocked",
            "bridge_id": "runtime_reveal_import_bridge",
            "public_claim": (
                "Microcosm turns macro-pattern intake into a runnable source-open path: "
                "compile, spine, intake, reveal, and evidence drilldown over real "
                "substrate receipts."
            ),
            "cold_reader_goal": "under_10_minutes_with_import_context_visible",
            "command": "microcosm intake",
            "projection_intake_ref": (
                "receipts/first_wave/macro_projection_import_protocol/"
                "projection_import_intake_board.json"
            ),
            "projection_plan_command": (
                "microcosm macro-projection-import-protocol plan --input "
                "examples/macro_projection_import_protocol/exported_projection_import_bundle"
            ),
            "reveal_command": "microcosm reveal",
            "spine_command": "microcosm spine",
            "first_run_bridge": [
                {
                    "step_id": "compile_project",
                    "command": "microcosm compile <project>",
                    "why": "create local .microcosm substrate state",
                },
                {
                    "step_id": "inspect_spine",
                    "command": "microcosm spine",
                    "why": "see accepted runtime organs and authority ceiling",
                },
                {
                    "step_id": "inspect_import_bridge",
                    "command": "microcosm intake",
                    "why": "see which macro projection cells are ready, landed, bridged, or consumed",
                },
                {
                    "step_id": "open_reveal",
                    "command": "microcosm reveal",
                    "why": "follow the ten-minute public reveal board",
                },
                {
                    "step_id": "drill_evidence",
                    "command": "microcosm evidence inspect <receipt>",
                    "why": "open receipts only after the causal path is visible",
                },
            ],
            "projection_cell_count": len(cells),
            "ready_cell_count": projection_board.get("ready_cell_count"),
            "projection_status_protocol": projection_board.get("projection_status_protocol"),
            "projection_status_counts": _normalize_projection_status_counts(
                projection_board.get("projection_status_counts", {})
            ),
            "open_actionable_cell_count": projection_board.get("open_actionable_cell_count"),
            "landed_cell_count": projection_board.get("landed_cell_count"),
            "consumed_cell_count": projection_board.get("consumed_cell_count"),
            "cell_status": cell_status,
            "runtime_bridge_evidence_refs": [
                bridge_receipt_ref,
                reveal_receipt_ref,
                "receipts/first_wave/macro_projection_import_protocol/projection_import_intake_board.json",
                "receipts/first_wave/formal_math_readiness_gate/formal_math_readiness_extension_board.json",
            ],
            "authority_ceiling": {
                "release_authorized": False,
                "hosted_public_authorized": False,
                "publication_authorized": False,
                "recipient_work_authorized": False,
                "provider_calls_authorized": False,
                "source_mutation_authorized": False,
                "credential_or_account_bound_bodies_exported": False,
                "private_data_equivalence_claim": False,
                "lean_lake_execution_authorized": False,
                "trading_or_financial_advice_authorized": False,
                "whole_system_correctness_claim": False,
            },
            "anti_claim": (
                "The runtime reveal/import bridge is a source-open legibility surface over "
                "projection cells, reveal commands, and receipt refs. It excludes only "
                "secrets, credential/session material, provider payload bodies, and other "
                "credential-equivalent live-access material; non-secret substrate must be "
                "imported, copied with provenance, or source-faithfully refactored through "
                "the owning organ. It does not authorize release or publication, call "
                "providers, run Lean/Lake, mutate source, give financial advice, or claim "
                "private-root equivalence."
            ),
            "body_in_receipt": False,
        }
        write_json_atomic(out_dir / "runtime_reveal_import_bridge.json", payload)
        return payload

    def inspect_route(self, route_id: str) -> dict[str, Any]:
        for route in self.routes():
            if route["route_id"] == route_id or route.get("row_id") == route_id:
                return {
                    "schema_version": "microcosm_runtime_route_card_v1",
                    "status": PASS,
                    "route": route,
                }
        return {
            "schema_version": "microcosm_runtime_route_card_v1",
            "status": "not_found",
            "route_id": route_id,
        }

    def inspect_evidence(self, receipt_ref: str) -> dict[str, Any]:
        receipt_path = self.root / receipt_ref
        if not receipt_path.is_file():
            return {
                "schema_version": "microcosm_runtime_evidence_card_v1",
                "status": "not_found",
                "receipt_ref": receipt_ref,
            }
        payload = read_json_strict(receipt_path)
        if not isinstance(payload, dict):
            return {
                "schema_version": "microcosm_runtime_evidence_card_v1",
                "status": "blocked",
                "receipt_ref": receipt_ref,
                "reason": "receipt is not a JSON object",
            }
        allowed = {
            key: payload.get(key)
            for key in (
                "schema_version",
                "receipt_id",
                "organ_id",
                "fixture_id",
                "status",
                "input_mode",
                "bundle_id",
                "created_at",
                "command",
                "anti_claim",
                "authority_ceiling",
                "receipt_paths",
            )
            if key in payload
        }
        return {
            "schema_version": "microcosm_runtime_evidence_card_v1",
            "status": PASS,
            "receipt_ref": receipt_ref,
            "receipt": allowed,
            "body_in_receipt": False,
            "evidence_contract": _receipt_evidence_contract(payload),
        }

    def run_demo(self, project: str | Path = DEFAULT_PROJECT_REL) -> dict[str, Any]:
        project_path = Path(project)
        if not project_path.is_absolute():
            project_path = self.root / project_path
        manifest = _read_json_if_exists(project_path / "project_manifest.json")
        project_id = str(manifest.get("project_id") or "demo_project")
        run_root = self.runtime_receipt_dir / project_id
        event_rows: list[dict[str, Any]] = []
        evidence_refs: list[str] = []
        summaries: list[str] = []

        for index, step in enumerate(_product_runtime_steps(), start=1):
            input_dir = self.root / step.example_rel
            out_dir = run_root / "organs" / step.organ_id
            command = f"microcosm run {_public_relative(project_path, self.root)}"
            result = step.runner(input_dir, out_dir, command)
            receipt_ref = _public_relative(out_dir / step.receipt_name, self.root)
            evidence_refs.append(receipt_ref)
            status = str(result.get("status") or "unknown")
            event_rows.append(
                {
                    "event_id": f"evt_{index:02d}_{step.organ_id}",
                    "span": step.span,
                    "organ_id": step.organ_id,
                    "status": status,
                    "input_mode": result.get("input_mode", step.input_mode),
                    "inputs": _public_relative(input_dir, self.root),
                    "outputs": _public_relative(out_dir, self.root),
                    "evidence_ref": receipt_ref,
                }
            )
            summaries.append(f"{step.organ_id}: {status} via {step.input_mode}")

        status = PASS if all(event["status"] == PASS for event in event_rows) else "blocked"
        trace = {
            "schema_version": "microcosm_runtime_trace_v1",
            "project_id": project_id,
            "created_at": utc_now(),
            "status": status,
            "events": event_rows,
            "otel_shape": {
                "trace_id": f"runtime_shell_{project_id}",
                "span_count": len(event_rows),
                "logs_as_events": True,
                "metrics": {
                    "runtime_steps_total": len(event_rows),
                    "runtime_steps_passed": sum(1 for event in event_rows if event["status"] == PASS),
                },
            },
        }
        result = {
            "schema_version": "microcosm_runtime_demo_result_v1",
            "project_id": project_id,
            "created_at": trace["created_at"],
            "status": status,
            "what_happened": summaries,
            "next_actions": [
                "microcosm route list",
                "microcosm evidence list",
                "microcosm serve",
            ],
            "events": event_rows,
            "evidence_refs": evidence_refs,
            "trace_ref": _public_relative(run_root / "demo_project_trace.json", self.root),
            "authority_ceiling": {
                "release_authorized": False,
                "provider_calls_authorized": False,
                "live_task_ledger_mutation_authorized": False,
                "private_data_equivalence_claim": False,
            },
            "anti_claim": (
                "The runtime shell demo executes public exported-bundle validators and emits "
                "public trace/evidence refs. It does not authorize release, hosting, "
                "provider calls, private-data equivalence, or live ledger mutation."
            ),
        }
        write_json_atomic(run_root / "demo_project_trace.json", trace)
        write_json_atomic(run_root / "demo_project_result.json", result)
        return result

    def run_work_demo(self) -> dict[str, Any]:
        step = next(item for item in RUNTIME_STEPS if item.organ_id == "mission_transaction_work_spine")
        input_dir = self.root / step.example_rel
        out_dir = self.runtime_receipt_dir / "work_demo" / "organs" / step.organ_id
        result = step.runner(input_dir, out_dir, "microcosm work demo")
        receipt_ref = _public_relative(out_dir / step.receipt_name, self.root)
        payload = {
            "schema_version": "microcosm_runtime_work_demo_v1",
            "created_at": utc_now(),
            "status": result.get("status", "unknown"),
            "workitems": self.workitems(),
            "transaction_id": result.get("transaction_id"),
            "schedulable_workitem_ids": result.get("schedulable_workitem_ids", []),
            "blocked_workitem_ids": result.get("blocked_workitem_ids", []),
            "evidence_ref": receipt_ref,
            "authority_ceiling": {
                "live_task_ledger_mutation_authorized": False,
                "live_work_ledger_mutation_authorized": False,
                "release_authorized": False,
            },
        }
        write_json_atomic(self.runtime_receipt_dir / "work_demo" / "work_demo_result.json", payload)
        return payload

    def reveal(self, *, persist_receipt: bool = True) -> dict[str, Any]:
        step = next(item for item in RUNTIME_STEPS if item.organ_id == "public_reveal_walkthrough")
        input_dir = self.root / step.example_rel
        out_dir = self.runtime_receipt_dir / "public_reveal" / "organs" / step.organ_id
        result = step.runner(input_dir, out_dir, "microcosm reveal")
        receipt_ref = _public_relative(out_dir / step.receipt_name, self.root)
        spine = self.spine()
        payload = {
            "schema_version": "microcosm_public_reveal_view_v1",
            "created_at": utc_now(),
            "status": result.get("status", "unknown"),
            "public_claim": result.get("public_claim"),
            "time_budget_minutes": result.get("time_budget_minutes"),
            "step_count": result.get("step_count"),
            "command_count": result.get("command_count"),
            "evidence_ref_count": result.get("evidence_ref_count"),
            "reveal_board": result.get("reveal_board"),
            "evidence_ref": receipt_ref,
            "evidence_strength_policy": {
                "next_command": "microcosm authority",
                "source_ref": spine.get("evidence_class_registry", {}).get("source_ref"),
                "accepted_status_is_not_evidence_strength": True,
                "unclassified_organs_block_authority_projection": True,
                "evidence_class_counts": spine.get("evidence_class_counts", {}),
            },
            "authority_ceiling": result.get("authority_ceiling"),
            "anti_claim": result.get("anti_claim"),
        }
        if persist_receipt:
            write_json_atomic(
                self.runtime_receipt_dir / "public_reveal" / "public_reveal_view.json",
                payload,
            )
        return payload

    def observatory_intake_bridge(self, *, persist_receipt: bool = True) -> dict[str, Any]:
        intake = self.intake()
        reveal = self.reveal(persist_receipt=persist_receipt)
        market_boundary = self.market_boundary()
        trace_lens = self.trace_lens()
        repair_loop = self.repair_loop()
        evidence_cells = self.evidence_cells()
        proof_loop_depth = self.proof_loop_depth()
        landing_replay = self.landing_replay()
        view_quality = self.view_quality()
        projection_safety = self.projection_safety()
        projection_drift = self.projection_drift()
        route_cleanup = self.route_cleanup()
        projection_import_map = self.projection_import_map()
        import_projector = self.import_projector()
        option_surface = self.option_surface_lens()
        stripping_guard = self.stripping_guard()
        standards_control = self.standards_control()
        hook_coverage = self.hook_coverage()
        replay_gauntlet = self.replay_gauntlet()
        benchmark_lab = self.benchmark_lab()
        legibility_scorecard = self.legibility_scorecard()
        cell_status = [
            {
                "cell_id": row.get("cell_id"),
                "projection_status": row.get("projection_status"),
                "cell_state": row.get("cell_state"),
                "action_required": row.get("action_required") is True,
                "next_runtime_surface": row.get("next_runtime_surface"),
                "landed_evidence_refs": row.get("landed_evidence_refs", []),
            }
            for row in _rows(intake, "cell_status")
        ]
        evidence_refs = list(
            dict.fromkeys(
                [
                    *[
                        str(ref)
                        for ref in intake.get("runtime_bridge_evidence_refs", [])
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (reveal.get("evidence_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (trace_lens.get("trace_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (market_boundary.get("market_boundary_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (repair_loop.get("repair_loop_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (evidence_cells.get("evidence_cell_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (proof_loop_depth.get("proof_loop_depth_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (landing_replay.get("landing_replay_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (view_quality.get("view_quality_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (projection_safety.get("projection_safety_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (projection_drift.get("projection_drift_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (route_cleanup.get("route_cleanup_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (projection_import_map.get("projection_import_map_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (import_projector.get("import_projector_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (option_surface.get("option_surface_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (stripping_guard.get("stripping_guard_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (standards_control.get("standards_control_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (hook_coverage.get("hook_intervention_coverage_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (replay_gauntlet.get("replay_gauntlet_lens_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (benchmark_lab.get("benchmark_lab_ref"),)
                        if isinstance(ref, str)
                    ],
                    *[
                        str(ref)
                        for ref in (legibility_scorecard.get("legibility_scorecard_ref"),)
                        if isinstance(ref, str)
                    ],
                ]
            )
        )
        payload = {
            "schema_version": "microcosm_observatory_intake_bridge_v1",
            "status": PASS
            if intake.get("status") == PASS
            and reveal.get("status") == PASS
            and market_boundary.get("status") == PASS
            and trace_lens.get("status") == PASS
            and repair_loop.get("status") == PASS
            and evidence_cells.get("status") == PASS
            and proof_loop_depth.get("status") == PASS
            and landing_replay.get("status") == PASS
            and view_quality.get("status") == PASS
            and projection_safety.get("status") == PASS
            and projection_drift.get("status") == PASS
            and route_cleanup.get("status") == PASS
            and projection_import_map.get("status") == PASS
            and import_projector.get("status") == PASS
            and option_surface.get("status") == PASS
            and stripping_guard.get("status") == PASS
            and standards_control.get("status") == PASS
            and hook_coverage.get("status") == PASS
            and replay_gauntlet.get("status") == PASS
            and benchmark_lab.get("status") == PASS
            and legibility_scorecard.get("status") == PASS
            else "blocked",
            "bridge_id": "intake_observatory_bridge",
            "public_claim": (
                "The local observatory shows the same spine, intake, reveal, and evidence "
                "causality that the JSON commands expose."
            ),
            "commands": [
                "microcosm tour <project>",
                "microcosm spine",
                "microcosm authority",
                "microcosm prediction-lens",
                "microcosm market-boundary",
                "microcosm corpus-lens",
                "microcosm trace-lens",
                "microcosm repair-loop",
                "microcosm evidence-cells",
                "microcosm proof-loop-depth",
                "microcosm landing-replay",
                "microcosm view-quality",
                "microcosm projection-safety",
                "microcosm drift-control",
                "microcosm route-cleanup",
                "microcosm projection-import-map",
                "microcosm import-projector",
                "microcosm option-surface-lens",
                "microcosm stripping-guard",
                "microcosm standards-control",
                "microcosm hook-coverage",
                "microcosm replay-gauntlet",
                "microcosm benchmark-lab",
                "microcosm legibility-scorecard",
                "microcosm intake",
                "microcosm reveal",
                "microcosm evidence inspect <receipt>",
            ],
            "endpoints": {
                "tour": "/tour",
                "spine": "/spine",
                "authority": "/authority",
                "prediction": "/prediction",
                "market_boundary": "/market-boundary",
                "corpus": "/corpus",
                "trace": "/trace",
                "repair_loop": "/repair-loop",
                "evidence_cells": "/evidence-cells",
                "proof_loop_depth": "/proof-loop-depth",
                "landing_replay": "/landing-replay",
                "view_quality": "/view-quality",
                "projection_safety": "/projection-safety",
                "projection_drift": "/drift-control",
                "route_cleanup": "/route-cleanup",
                "projection_import_map": "/projection-import-map",
                "import_projector": "/import-projector",
                "option_surface": "/option-surface-lens",
                "stripping_guard": "/stripping-guard",
                "standards_control": "/standards-control",
                "hook_coverage": "/hook-coverage",
                "replay_gauntlet": "/replay-gauntlet",
                "benchmark_lab": "/benchmark-lab",
                "legibility_scorecard": "/legibility-scorecard",
                "intake": "/intake",
                "reveal": "/reveal",
                "evidence": "/evidence",
            },
            "projection_status_protocol": intake.get("projection_status_protocol"),
            "projection_status_counts": intake.get("projection_status_counts", {}),
            "open_actionable_cell_count": intake.get("open_actionable_cell_count"),
            "landed_cell_count": intake.get("landed_cell_count"),
            "consumed_cell_count": intake.get("consumed_cell_count"),
            "closed_cell_count": sum(1 for row in cell_status if row.get("action_required") is False),
            "cell_status": cell_status,
            "reveal_summary": {
                "status": reveal.get("status"),
                "time_budget_minutes": reveal.get("time_budget_minutes"),
                "step_count": reveal.get("step_count"),
                "evidence_ref_count": reveal.get("evidence_ref_count"),
                "evidence_ref": reveal.get("evidence_ref"),
            },
            "evidence_refs": evidence_refs,
            "authority_ceiling": {
                "release_authorized": False,
                "hosted_public_authorized": False,
                "publication_authorized": False,
                "provider_calls_authorized": False,
                "source_mutation_authorized": False,
                "private_data_equivalence_claim": False,
                "whole_system_correctness_claim": False,
            },
            "anti_claim": (
                "The observatory intake bridge is a public-safe browser/read-model over "
                "runtime command outputs and receipt refs. It does not host, publish, "
                "authorize release, import private bodies, call providers, or prove "
                "private-root equivalence."
            ),
            "body_redacted": True,
        }
        if persist_receipt:
            write_json_atomic(
                self.runtime_receipt_dir / "intake_bridge" / "observatory_intake_bridge.json",
                payload,
            )
        return payload

    def project_observatory(
        self,
        project: str | Path | None = None,
        *,
        persist_receipts: bool = True,
    ) -> dict[str, Any]:
        project_path = Path(project).expanduser().resolve(strict=False) if project is not None else None
        status = self.status()
        tour = self.tour(
            project_path if project_path is not None else DEFAULT_PROJECT_REL,
            persist_receipt=persist_receipts,
        )
        runtime_bridge = self.observatory_intake_bridge(persist_receipt=persist_receipts)
        authority_map = self.authority(persist_receipts=persist_receipts)
        prediction_lens = self.prediction_lens()
        market_boundary_lens = self.market_boundary()
        corpus_lens = self.corpus_lens()
        trace_lens = self.trace_lens()
        repair_loop_lens = self.repair_loop()
        evidence_cell_lens = self.evidence_cells()
        proof_loop_depth_lens = self.proof_loop_depth()
        landing_replay_lens = self.landing_replay()
        view_quality_lens = self.view_quality()
        projection_safety_lens = self.projection_safety()
        projection_drift_lens = self.projection_drift()
        route_cleanup_lens = self.route_cleanup()
        projection_import_map_lens = self.projection_import_map()
        import_projector_lens = self.import_projector()
        option_surface_lens = self.option_surface_lens()
        stripping_guard_lens = self.stripping_guard()
        standards_control_lens = self.standards_control()
        hook_coverage_lens = self.hook_coverage()
        replay_gauntlet_lens = self.replay_gauntlet()
        benchmark_lab_lens = self.benchmark_lab()
        legibility_scorecard_lens = self.legibility_scorecard()
        kernel = {
            **architecture_kernel.load_kernel_manifest(self.root),
            "standard_pressure_surface": architecture_kernel.load_standard_pressure_surface(self.root),
        }
        model: dict[str, Any] = {
            "schema_version": "microcosm_project_observatory_v1",
            "status": PASS,
            "runtime_status": status,
            "tour": tour,
            "runtime_bridge": runtime_bridge,
            "authority_map": authority_map,
            "prediction_lens": prediction_lens,
            "market_boundary_lens": market_boundary_lens,
            "corpus_lens": corpus_lens,
            "trace_lens": trace_lens,
            "repair_loop_lens": repair_loop_lens,
            "evidence_cell_lens": evidence_cell_lens,
            "proof_loop_depth_lens": proof_loop_depth_lens,
            "landing_replay_lens": landing_replay_lens,
            "view_quality_lens": view_quality_lens,
            "projection_safety_lens": projection_safety_lens,
            "projection_drift_lens": projection_drift_lens,
            "route_cleanup_lens": route_cleanup_lens,
            "projection_import_map_lens": projection_import_map_lens,
            "import_projector_lens": import_projector_lens,
            "option_surface_lens": option_surface_lens,
            "stripping_guard_lens": stripping_guard_lens,
            "standards_control_lens": standards_control_lens,
            "hook_coverage_lens": hook_coverage_lens,
            "replay_gauntlet_lens": replay_gauntlet_lens,
            "benchmark_lab_lens": benchmark_lab_lens,
            "legibility_scorecard_lens": legibility_scorecard_lens,
            "kernel": kernel,
            "release_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "evidence_is_drilldown": True,
            "anti_claim": (
                "The observatory summarizes project-local public substrate state. It "
                "does not authorize release, hosting, provider calls, source mutation, "
                "private-data equivalence, or global doctrine promotion."
            ),
        }
        if project_path is None:
            model["project_summary"] = {
                "project_id": "public_runtime",
                "status": status.get("status"),
                "state_ref": None,
                "local_state_refs": [],
            }
            return model

        state = project_path / project_substrate.STATE_DIR
        if not (state / "project_manifest.json").is_file():
            project_substrate.init_project(project_path)
        if not (state / "catalog.json").is_file():
            project_substrate.index_project(project_path)
        if not (state / "patterns.json").is_file():
            project_substrate.discover_patterns(project_path)
        if not (state / "routes.json").is_file():
            project_substrate.propose_routes(project_path)
        architecture = project_substrate.architecture_project(project_path)
        graph = project_substrate.state_graph(project_path)
        catalog = project_substrate.catalog_project(project_path)
        python_lens = project_substrate.python_lens(project_path)
        patterns = project_substrate.discover_patterns(project_path)
        routes = project_substrate.propose_routes(project_path)
        route_rows = _rows(routes, "routes")
        selected_route = next(
            (row for row in route_rows if row.get("route_id") == "readme_onboarding_route"),
            route_rows[0] if route_rows else {},
        )
        route_id = str(selected_route.get("route_id") or "")
        explanation_path = state / "explanations" / f"{route_id}.json"
        explanation = _read_json_if_exists(explanation_path)
        if route_id and not explanation:
            explanation = project_substrate.explain_route(project_path, route_id)
        work_items = project_substrate._load_work_items(project_path)
        selected_work = next(
            (row for row in work_items if row.get("route_id") == route_id),
            work_items[-1] if work_items else {},
        )
        observe = project_substrate.observe_project(project_path)
        evidence = project_substrate.list_evidence(project_path)
        pattern_bindings = _rows(explanation, "pattern_bindings")
        standard_bindings = _rows(explanation, "standard_bindings")
        work_event_refs = selected_work.get("event_refs", []) if isinstance(selected_work, dict) else []
        work_evidence_refs = selected_work.get("evidence_refs", []) if isinstance(selected_work, dict) else []
        event_rows = _rows(observe, "events")
        evidence_rows = _rows(evidence, "evidence")
        causal_events = [
            row
            for row in event_rows
            if row.get("span") in {"project.route", "project.explain", "work.create", "work.run"}
        ][-8:]
        model.update(
            {
                "project_summary": {
                    "project_id": catalog.get("project_id") or project_path.name,
                    "project_ref": ".",
                    "status": PASS,
                    "state_ref": project_substrate.STATE_DIR,
                    "local_state_refs": [
                        ".microcosm/catalog.json",
                        ".microcosm/python_lens.json",
                        ".microcosm/patterns.json",
                        ".microcosm/routes.json",
                        ".microcosm/work_items.json",
                        ".microcosm/events.jsonl",
                        ".microcosm/evidence/",
                    ],
                    "release_authorized": False,
                    "provider_calls_authorized": False,
                    "source_mutation_authorized": False,
                },
                "selected_route_id": route_id,
                "catalog_summary": {
                    "file_count": catalog.get("file_count", 0),
                    "role_counts": catalog.get("role_counts", {}),
                    "python_file_count": python_lens.get("python_file_count", 0),
                    "python_ready_route_count": python_lens.get("ready_route_count", 0),
                },
                "python_lens": {
                    "schema_version": python_lens.get("schema_version"),
                    "status": python_lens.get("status"),
                    "lens_id": python_lens.get("lens_id"),
                    "command": python_lens.get("command"),
                    "python_file_count": python_lens.get("python_file_count", 0),
                    "package_roots": python_lens.get("package_roots", []),
                    "readiness_checks": python_lens.get("readiness_checks", []),
                    "route_rows": python_lens.get("route_rows", []),
                    "ready_route_count": python_lens.get("ready_route_count", 0),
                    "evidence_ref": python_lens.get("evidence_ref"),
                    "body_redacted": python_lens.get("body_redacted") is True,
                },
                "causal_chain": {
                    "python_lens": {
                        "lens_id": python_lens.get("lens_id"),
                        "status": python_lens.get("status"),
                        "python_file_count": python_lens.get("python_file_count", 0),
                        "ready_route_count": python_lens.get("ready_route_count", 0),
                        "state_file_ref": python_lens.get("state_file_ref"),
                        "evidence_ref": python_lens.get("evidence_ref"),
                    },
                    "route": {
                        "route_id": route_id,
                        "title": selected_route.get("title"),
                        "grounded_refs": selected_route.get("grounded_refs", []),
                        "pattern_refs": selected_route.get("pattern_refs", []),
                        "standard_pressure_refs": selected_route.get("standard_pressure_refs", []),
                        "source_mutation_authorized": selected_route.get("source_mutation_authorized") is True,
                        "authority": selected_route.get("authority"),
                    },
                    "pattern_bindings": [
                        {
                            "pattern_id": row.get("pattern_id"),
                            "resolved": row.get("resolved") is True,
                            "title": (row.get("pattern") or {}).get("title")
                            if isinstance(row.get("pattern"), dict)
                            else None,
                            "state_ref": row.get("state_ref"),
                        }
                        for row in pattern_bindings
                    ],
                    "standard_bindings": [
                        {
                            "standard_id": row.get("standard_id"),
                            "resolved": row.get("resolved") is True,
                            "title": (row.get("standard") or {}).get("title")
                            if isinstance(row.get("standard"), dict)
                            else None,
                            "state_ref": row.get("state_ref"),
                        }
                        for row in standard_bindings
                    ],
                    "work_transaction": {
                        "work_id": selected_work.get("work_id"),
                        "status": selected_work.get("status"),
                        "route_id": selected_work.get("route_id"),
                        "transaction_policy": selected_work.get("transaction_policy"),
                        "state_history": selected_work.get("state_history", []),
                        "satisfaction_contract": selected_work.get("satisfaction_contract"),
                        "integration_contract": selected_work.get("integration_contract"),
                        "closeout": selected_work.get("closeout"),
                        "source_files_mutated": selected_work.get("source_files_mutated") is True,
                        "event_refs": work_event_refs if isinstance(work_event_refs, list) else [],
                        "evidence_refs": work_evidence_refs if isinstance(work_evidence_refs, list) else [],
                    },
                    "events": causal_events,
                    "evidence": evidence_rows[-10:],
                    "authority_boundary": explanation.get("authority_boundary")
                    or "project_local_projection_not_source_authority",
                },
                "graph_summary": {
                    "node_count": graph.get("node_count", 0),
                    "edge_count": graph.get("edge_count", 0),
                    "key_relations": [
                        "project -> catalog",
                        "catalog -> python_lens",
                        "catalog -> pattern",
                        "pattern -> route",
                        "route -> explanation",
                        "route -> work",
                        "work -> event",
                        "event -> evidence",
                    ],
                    "graph_ref": ".microcosm/graph.json",
                },
                "kernel_summary": {
                    "primitive_names": [
                        row.get("public_name")
                        for row in kernel.get("primitives", [])
                        if isinstance(row, dict) and row.get("public_name")
                    ],
                    "pattern_surface_id": (architecture.get("pattern_surface") or {}).get("surface_id")
                    if isinstance(architecture.get("pattern_surface"), dict)
                    else None,
                    "standard_pressure_surface_id": (
                        architecture.get("standard_pressure_surface") or {}
                    ).get("surface_id")
                    if isinstance(architecture.get("standard_pressure_surface"), dict)
                    else None,
                },
                "json_drilldowns": {
                    "spine": "/spine",
                    "tour": "/tour",
                    "authority": "/authority",
                    "prediction": "/prediction",
                    "market_boundary": "/market-boundary",
                    "corpus": "/corpus",
                    "trace": "/trace",
                    "repair_loop": "/repair-loop",
                    "evidence_cells": "/evidence-cells",
                    "proof_loop_depth": "/proof-loop-depth",
                    "landing_replay": "/landing-replay",
                    "view_quality": "/view-quality",
                    "projection_safety": "/projection-safety",
                    "projection_drift": "/drift-control",
                    "route_cleanup": "/route-cleanup",
                    "projection_import_map": "/projection-import-map",
                    "import_projector": "/import-projector",
                    "option_surface": "/option-surface-lens",
                    "stripping_guard": "/stripping-guard",
                    "standards_control": "/standards-control",
                    "hook_coverage": "/hook-coverage",
                    "replay_gauntlet": "/replay-gauntlet",
                    "benchmark_lab": "/benchmark-lab",
                    "legibility_scorecard": "/legibility-scorecard",
                    "intake": "/intake",
                    "reveal": "/reveal",
                    "kernel": "/kernel",
                    "python_lens": "/project/python-lens",
                    "graph": "/project/graph",
                    "workitems": "/project/workitems",
                    "evidence": "/project/evidence",
                    "explain": f"/project/explain/{route_id}" if route_id else None,
                },
            }
        )
        return model

    def _observatory_html(self, project_path: Path | None) -> str:
        model = self.project_observatory(project_path, persist_receipts=False)
        project_summary = model.get("project_summary", {})
        causal = model.get("causal_chain", {})
        route = causal.get("route", {}) if isinstance(causal.get("route"), dict) else {}
        work = causal.get("work_transaction", {}) if isinstance(causal.get("work_transaction"), dict) else {}
        graph = model.get("graph_summary", {})
        kernel = model.get("kernel_summary", {})
        pattern_bindings = causal.get("pattern_bindings", []) if isinstance(causal.get("pattern_bindings"), list) else []
        standard_bindings = causal.get("standard_bindings", []) if isinstance(causal.get("standard_bindings"), list) else []
        events = causal.get("events", []) if isinstance(causal.get("events"), list) else []
        evidence = causal.get("evidence", []) if isinstance(causal.get("evidence"), list) else []
        project_python_lens = model.get("python_lens", {}) if isinstance(model.get("python_lens"), dict) else {}
        python_route_rows = (
            project_python_lens.get("route_rows", [])
            if isinstance(project_python_lens.get("route_rows"), list)
            else []
        )
        python_readiness_checks = (
            project_python_lens.get("readiness_checks", [])
            if isinstance(project_python_lens.get("readiness_checks"), list)
            else []
        )
        runtime_bridge = model.get("runtime_bridge", {}) if isinstance(model.get("runtime_bridge"), dict) else {}
        tour = model.get("tour", {}) if isinstance(model.get("tour"), dict) else {}
        tour_cards = tour.get("route_cards", []) if isinstance(tour.get("route_cards"), list) else []
        bridge_cells = _rows(runtime_bridge, "cell_status")
        authority_map = model.get("authority_map", {}) if isinstance(model.get("authority_map"), dict) else {}
        prediction_lens = (
            model.get("prediction_lens", {}) if isinstance(model.get("prediction_lens"), dict) else {}
        )
        market_boundary_lens = (
            model.get("market_boundary_lens", {})
            if isinstance(model.get("market_boundary_lens"), dict)
            else {}
        )
        corpus_lens = model.get("corpus_lens", {}) if isinstance(model.get("corpus_lens"), dict) else {}
        trace_lens = model.get("trace_lens", {}) if isinstance(model.get("trace_lens"), dict) else {}
        repair_loop_lens = (
            model.get("repair_loop_lens", {})
            if isinstance(model.get("repair_loop_lens"), dict)
            else {}
        )
        evidence_cell_lens = (
            model.get("evidence_cell_lens", {})
            if isinstance(model.get("evidence_cell_lens"), dict)
            else {}
        )
        proof_loop_depth_lens = (
            model.get("proof_loop_depth_lens", {})
            if isinstance(model.get("proof_loop_depth_lens"), dict)
            else {}
        )
        landing_replay_lens = (
            model.get("landing_replay_lens", {})
            if isinstance(model.get("landing_replay_lens"), dict)
            else {}
        )
        view_quality_lens = (
            model.get("view_quality_lens", {})
            if isinstance(model.get("view_quality_lens"), dict)
            else {}
        )
        projection_safety_lens = (
            model.get("projection_safety_lens", {})
            if isinstance(model.get("projection_safety_lens"), dict)
            else {}
        )
        projection_drift_lens = (
            model.get("projection_drift_lens", {})
            if isinstance(model.get("projection_drift_lens"), dict)
            else {}
        )
        route_cleanup_lens = (
            model.get("route_cleanup_lens", {})
            if isinstance(model.get("route_cleanup_lens"), dict)
            else {}
        )
        projection_import_map_lens = (
            model.get("projection_import_map_lens", {})
            if isinstance(model.get("projection_import_map_lens"), dict)
            else {}
        )
        import_projector_lens = (
            model.get("import_projector_lens", {})
            if isinstance(model.get("import_projector_lens"), dict)
            else {}
        )
        option_surface_lens = (
            model.get("option_surface_lens", {})
            if isinstance(model.get("option_surface_lens"), dict)
            else {}
        )
        stripping_guard_lens = (
            model.get("stripping_guard_lens", {})
            if isinstance(model.get("stripping_guard_lens"), dict)
            else {}
        )
        standards_control_lens = (
            model.get("standards_control_lens", {})
            if isinstance(model.get("standards_control_lens"), dict)
            else {}
        )
        hook_coverage_lens = (
            model.get("hook_coverage_lens", {})
            if isinstance(model.get("hook_coverage_lens"), dict)
            else {}
        )
        replay_gauntlet_lens = (
            model.get("replay_gauntlet_lens", {})
            if isinstance(model.get("replay_gauntlet_lens"), dict)
            else {}
        )
        benchmark_lab_lens = (
            model.get("benchmark_lab_lens", {})
            if isinstance(model.get("benchmark_lab_lens"), dict)
            else {}
        )
        legibility_scorecard_lens = (
            model.get("legibility_scorecard_lens", {})
            if isinstance(model.get("legibility_scorecard_lens"), dict)
            else {}
        )
        corpus_summary = (
            corpus_lens.get("corpus_summary", {})
            if isinstance(corpus_lens.get("corpus_summary"), dict)
            else {}
        )
        corpus_gate = (
            corpus_lens.get("consumer_gate", {})
            if isinstance(corpus_lens.get("consumer_gate"), dict)
            else {}
        )
        prediction_mechanics = (
            prediction_lens.get("mechanics", []) if isinstance(prediction_lens.get("mechanics"), list) else []
        )
        market_boundary_rows = (
            market_boundary_lens.get("boundary_rows", [])
            if isinstance(market_boundary_lens.get("boundary_rows"), list)
            else []
        )
        market_boundary_negative_cases = (
            market_boundary_lens.get("negative_case_ids", [])
            if isinstance(market_boundary_lens.get("negative_case_ids"), list)
            else []
        )
        trace_rows = trace_lens.get("trace_rows", []) if isinstance(trace_lens.get("trace_rows"), list) else []
        trace_negative_cases = (
            trace_lens.get("negative_case_ids", [])
            if isinstance(trace_lens.get("negative_case_ids"), list)
            else []
        )
        repair_loop_stages = (
            repair_loop_lens.get("loop_stages", [])
            if isinstance(repair_loop_lens.get("loop_stages"), list)
            else []
        )
        repair_loop_transitions = (
            repair_loop_lens.get("transition_rows", [])
            if isinstance(repair_loop_lens.get("transition_rows"), list)
            else []
        )
        repair_loop_negative_cases = (
            repair_loop_lens.get("negative_case_ids", [])
            if isinstance(repair_loop_lens.get("negative_case_ids"), list)
            else []
        )
        formal_evidence_cells = (
            evidence_cell_lens.get("evidence_cells", [])
            if isinstance(evidence_cell_lens.get("evidence_cells"), list)
            else []
        )
        formal_evidence_negative_cases = (
            evidence_cell_lens.get("negative_case_ids", [])
            if isinstance(evidence_cell_lens.get("negative_case_ids"), list)
            else []
        )
        proof_loop_depth_rows = (
            proof_loop_depth_lens.get("gate_rows", [])
            if isinstance(proof_loop_depth_lens.get("gate_rows"), list)
            else []
        )
        proof_loop_depth_negative_cases = (
            proof_loop_depth_lens.get("negative_case_ids", [])
            if isinstance(proof_loop_depth_lens.get("negative_case_ids"), list)
            else []
        )
        landing_lanes = (
            landing_replay_lens.get("lane_decision_table", [])
            if isinstance(landing_replay_lens.get("lane_decision_table"), list)
            else []
        )
        landing_negative_cases = (
            landing_replay_lens.get("negative_case_ids", [])
            if isinstance(landing_replay_lens.get("negative_case_ids"), list)
            else []
        )
        view_quality_actions = (
            view_quality_lens.get("action_rows", [])
            if isinstance(view_quality_lens.get("action_rows"), list)
            else []
        )
        view_quality_hot_actions = (
            view_quality_lens.get("hot_action_rollup", [])
            if isinstance(view_quality_lens.get("hot_action_rollup"), list)
            else []
        )
        view_quality_negative_cases = (
            view_quality_lens.get("negative_case_ids", [])
            if isinstance(view_quality_lens.get("negative_case_ids"), list)
            else []
        )
        projection_rows = (
            projection_safety_lens.get("projection_rows", [])
            if isinstance(projection_safety_lens.get("projection_rows"), list)
            else []
        )
        projection_negative_cases = (
            projection_safety_lens.get("negative_case_ids", [])
            if isinstance(projection_safety_lens.get("negative_case_ids"), list)
            else []
        )
        projection_drift_rows = (
            projection_drift_lens.get("drift_rows", [])
            if isinstance(projection_drift_lens.get("drift_rows"), list)
            else []
        )
        projection_drift_negative_cases = (
            projection_drift_lens.get("negative_case_ids", [])
            if isinstance(projection_drift_lens.get("negative_case_ids"), list)
            else []
        )
        route_cleanup_rows = (
            route_cleanup_lens.get("cleanup_rows", [])
            if isinstance(route_cleanup_lens.get("cleanup_rows"), list)
            else []
        )
        route_cleanup_negative_cases = (
            route_cleanup_lens.get("negative_case_ids", [])
            if isinstance(route_cleanup_lens.get("negative_case_ids"), list)
            else []
        )
        projection_import_rows = (
            projection_import_map_lens.get("import_rows", [])
            if isinstance(projection_import_map_lens.get("import_rows"), list)
            else []
        )
        projection_import_stages = (
            projection_import_map_lens.get("import_stages", [])
            if isinstance(projection_import_map_lens.get("import_stages"), list)
            else []
        )
        projection_import_negative_cases = (
            projection_import_map_lens.get("negative_case_ids", [])
            if isinstance(projection_import_map_lens.get("negative_case_ids"), list)
            else []
        )
        import_projector_rows = (
            import_projector_lens.get("projector_rows", [])
            if isinstance(import_projector_lens.get("projector_rows"), list)
            else []
        )
        import_projector_stages = (
            import_projector_lens.get("contract_stages", [])
            if isinstance(import_projector_lens.get("contract_stages"), list)
            else []
        )
        import_projector_negative_cases = (
            import_projector_lens.get("negative_case_ids", [])
            if isinstance(import_projector_lens.get("negative_case_ids"), list)
            else []
        )
        option_surface_rows = (
            option_surface_lens.get("option_rows", [])
            if isinstance(option_surface_lens.get("option_rows"), list)
            else []
        )
        option_surface_stages = (
            option_surface_lens.get("option_stages", [])
            if isinstance(option_surface_lens.get("option_stages"), list)
            else []
        )
        option_surface_negative_cases = (
            option_surface_lens.get("negative_case_ids", [])
            if isinstance(option_surface_lens.get("negative_case_ids"), list)
            else []
        )
        stripping_guard_rows = (
            stripping_guard_lens.get("guard_rows", [])
            if isinstance(stripping_guard_lens.get("guard_rows"), list)
            else []
        )
        stripping_guard_negative_cases = (
            stripping_guard_lens.get("negative_case_ids", [])
            if isinstance(stripping_guard_lens.get("negative_case_ids"), list)
            else []
        )
        standards_control_rows = (
            standards_control_lens.get("standards_rows", [])
            if isinstance(standards_control_lens.get("standards_rows"), list)
            else []
        )
        standards_control_negative_cases = (
            standards_control_lens.get("negative_case_ids", [])
            if isinstance(standards_control_lens.get("negative_case_ids"), list)
            else []
        )
        hook_interventions = (
            hook_coverage_lens.get("intervention_rows", [])
            if isinstance(hook_coverage_lens.get("intervention_rows"), list)
            else []
        )
        hook_negative_cases = (
            hook_coverage_lens.get("negative_case_ids", [])
            if isinstance(hook_coverage_lens.get("negative_case_ids"), list)
            else []
        )
        replay_episodes = (
            replay_gauntlet_lens.get("episode_rows", [])
            if isinstance(replay_gauntlet_lens.get("episode_rows"), list)
            else []
        )
        replay_negative_cases = (
            replay_gauntlet_lens.get("negative_case_ids", [])
            if isinstance(replay_gauntlet_lens.get("negative_case_ids"), list)
            else []
        )
        benchmark_tasks = (
            benchmark_lab_lens.get("task_rows", [])
            if isinstance(benchmark_lab_lens.get("task_rows"), list)
            else []
        )
        benchmark_negative_cases = (
            benchmark_lab_lens.get("negative_case_ids", [])
            if isinstance(benchmark_lab_lens.get("negative_case_ids"), list)
            else []
        )
        legibility_checkpoints = (
            legibility_scorecard_lens.get("checkpoint_rows", [])
            if isinstance(legibility_scorecard_lens.get("checkpoint_rows"), list)
            else []
        )
        legibility_questions = (
            legibility_scorecard_lens.get("reader_question_rows", [])
            if isinstance(legibility_scorecard_lens.get("reader_question_rows"), list)
            else []
        )
        legibility_negative_cases = (
            legibility_scorecard_lens.get("negative_case_ids", [])
            if isinstance(legibility_scorecard_lens.get("negative_case_ids"), list)
            else []
        )
        cp2_prediction_count = next(
            (
                item.get("count")
                for item in prediction_mechanics
                if isinstance(item, dict) and item.get("mechanic_id") == "cp2_prediction_rows"
            ),
            "",
        )

        def dump(payload: Any) -> str:
            return html.escape(json.dumps(payload, indent=2, sort_keys=True))

        def row(label: str, value: Any) -> str:
            return (
                "<tr>"
                f"<th>{html.escape(label)}</th>"
                f"<td>{html.escape(_safe_text(value))}</td>"
                "</tr>"
            )

        def binding_rows(rows: list[Any], id_key: str) -> str:
            if not rows:
                return "<p class=\"muted\">No bindings yet.</p>"
            items = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                status = "resolved" if item.get("resolved") is True else "unresolved"
                items.append(
                    "<li>"
                    f"<strong>{html.escape(_safe_text(item.get(id_key)))}</strong>"
                    f" <span class=\"pill {status}\">{status}</span>"
                    f"<br><span class=\"muted\">{html.escape(_safe_text(item.get('title') or item.get('state_ref')))}</span>"
                    "</li>"
                )
            return f"<ul>{''.join(items)}</ul>"

        def event_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"4\" class=\"muted\">No events recorded yet.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('event_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('span')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('status')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('evidence_ref')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def evidence_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"3\" class=\"muted\">No evidence refs yet.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('evidence_ref')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('status')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('replacement_policy')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def cell_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"4\" class=\"muted\">No intake cells projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('cell_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('projection_status')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('cell_state')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('next_runtime_surface')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def python_lens_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"3\" class=\"muted\">No Python route rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('route_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('readiness')))}</td>"
                    f"<td>{html.escape(', '.join([str(ref) for ref in item.get('grounded_refs', [])]) if isinstance(item.get('grounded_refs'), list) else '')}</td>"
                    "</tr>"
                )
            return "".join(output)

        def tour_card_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"4\" class=\"muted\">No tour cards projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('card_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('minute_budget')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('command')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('status')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def view_quality_action_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"4\" class=\"muted\">No view-quality action rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('view_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('census_status')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('action_class')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('next_action')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def projection_safety_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"4\" class=\"muted\">No projection-safety rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                receipt = (
                    item.get("omission_receipt")
                    if isinstance(item.get("omission_receipt"), dict)
                    else {}
                )
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('projection_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('endpoint')))}</td>"
                    f"<td>{html.escape(_safe_text(receipt.get('drilldown')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('authority_ceiling_ref')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def projection_drift_table_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"5\" class=\"muted\">No projection-drift rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('drift_row_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('source_signal')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('repair_route')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('validation_ref')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('source_authority_claim')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def market_boundary_table_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"5\" class=\"muted\">No market-boundary rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('boundary_row_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('public_rule')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('decision_boundary')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('owner_route')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('trading_advice_authorized')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def route_cleanup_table_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"5\" class=\"muted\">No route-cleanup rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('cleanup_row_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('cleanup_action_class')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('owner_route')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('validation_ref')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('route_deletion_authorized')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def projection_import_map_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"5\" class=\"muted\">No projection-import rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('map_row_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('source_pattern_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('public_surface')))}</td>"
                    f"<td>{html.escape(_safe_text(', '.join([str(value) for value in item.get('cleaned', [])]) if isinstance(item.get('cleaned'), list) else ''))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('authority_ceiling_ref')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def import_projector_table_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"5\" class=\"muted\">No import-projector rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('projector_row_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('projector_stage')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('public_output')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('validation_ref')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('authority_ceiling_ref')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def option_surface_table_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"5\" class=\"muted\">No option-surface rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('option_row_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('option_stage')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('public_output')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('validation_ref')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('profile_switch_execution_authorized')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def stripping_guard_table_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"5\" class=\"muted\">No stripping guard rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('guard_row_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('source_risk')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('public_replacement')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('strip_rule')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('release_authorized')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def standards_control_table_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"5\" class=\"muted\">No standards-control rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('control_row_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('source_ref')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('public_role')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('observed_count')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('release_authorized')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def proof_loop_depth_table_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"5\" class=\"muted\">No proof-loop depth rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('gate_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('loop_depth')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('evidence_ref')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('promotion_scope')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('proof_body_exported')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def hook_intervention_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"4\" class=\"muted\">No hook intervention rows projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('intervention_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('source_receipt_ref')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('decision')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('coverage_status') or item.get('route_lease_warning_session_count') or item.get('debt_retirement_count')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def replay_episode_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"4\" class=\"muted\">No replay episodes projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('episode_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('monitor_verdict')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('containment_action')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('negative_case_id')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def benchmark_task_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"4\" class=\"muted\">No benchmark tasks projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('task_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('request_kind')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('workitem_admission')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('provider_slot_decision')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def legibility_checkpoint_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"4\" class=\"muted\">No legibility checkpoints projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('checkpoint_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('reader_question')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('command')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('pass_condition')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def repair_loop_transition_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"5\" class=\"muted\">No repair-loop transitions projected.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('attempt_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('failure_class')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('repair_action')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('to_stage')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('promotion_allowed')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        state_history = [
            str(item.get("state"))
            for item in work.get("state_history", [])
            if isinstance(item, dict) and item.get("state")
        ]
        event_ref_values = [
            str(item.get("event_id"))
            for item in work.get("event_refs", [])
            if isinstance(item, dict) and item.get("event_id")
        ]
        evidence_ref_values = [
            str(item)
            for item in work.get("evidence_refs", [])
            if item
        ]
        route_id = _safe_text(route.get("route_id") or model.get("selected_route_id"))
        project_title = project_path.name if project_path is not None else "public runtime"
        endpoint_items = "".join(
            f"<li><code>{html.escape(str(endpoint))}</code></li>"
            for endpoint in (model.get("json_drilldowns") or {}).values()
            if endpoint
        )
        return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>Microcosm Observatory</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #f5f5f1; color: #171715; }}
    header {{ padding: 30px 34px 20px; border-bottom: 1px solid #d8d7d1; background: #ffffff; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    p {{ margin: 0; max-width: 980px; line-height: 1.48; color: #4b4a45; }}
    main {{ display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(320px, .85fr); gap: 16px; padding: 20px; }}
    section {{ background: #ffffff; border: 1px solid #dad8d0; border-radius: 6px; overflow: hidden; min-width: 0; }}
    section.wide {{ grid-column: 1 / -1; }}
    h2 {{ margin: 0; padding: 12px 14px; font-size: 15px; background: #eceae3; border-bottom: 1px solid #dad8d0; }}
    h3 {{ margin: 16px 0 8px; font-size: 13px; }}
    .content {{ padding: 14px; }}
    .chain {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 8px; margin: 12px 0; }}
    .node {{ border: 1px solid #d7d4ca; border-radius: 6px; padding: 10px; background: #fbfbf8; min-width: 0; }}
    .node strong {{ display: block; font-size: 12px; color: #24231f; }}
    .node span {{ color: #5b5a55; font-size: 12px; overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ padding: 7px 8px; border-top: 1px solid #ebe9e2; text-align: left; vertical-align: top; overflow-wrap: anywhere; }}
    th {{ width: 170px; color: #55534d; font-weight: 600; }}
    ul {{ margin: 8px 0 0; padding-left: 18px; }}
    li {{ margin: 7px 0; }}
    code {{ background: #f0efe8; border: 1px solid #dddacf; border-radius: 4px; padding: 1px 4px; }}
    .badge {{ display: inline-block; margin: 2px 5px 2px 0; padding: 3px 7px; border-radius: 999px; background: #e8f1ed; border: 1px solid #bcd8ce; font-size: 12px; }}
    .pill {{ border-radius: 999px; padding: 2px 7px; font-size: 11px; border: 1px solid #d2d0c8; }}
    .resolved {{ background: #e5f5e9; border-color: #add4b6; }}
    .unresolved {{ background: #fff1df; border-color: #e0bf84; }}
    .muted {{ color: #68665f; }}
    .ceiling {{ color: #5b2a25; background: #fff2ec; border: 1px solid #ecc7ba; border-radius: 5px; padding: 8px 10px; margin-top: 12px; }}
    details {{ margin-top: 12px; border-top: 1px solid #ebe9e2; padding-top: 10px; }}
    summary {{ cursor: pointer; color: #45433e; font-weight: 600; }}
    pre {{ margin: 10px 0 0; padding: 12px; overflow: auto; max-height: 360px; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-word; background: #f7f7f4; border: 1px solid #e4e1d8; border-radius: 5px; }}
    @media (max-width: 860px) {{ main {{ grid-template-columns: 1fr; padding: 12px; }} header {{ padding: 22px 18px 16px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Microcosm Observatory</h1>
    <p>{html.escape(project_title)} is shown as an executable research prototype: local state, resolved pattern bindings, standard pressure, route, work transaction, events, and evidence drilldowns. Release remains unauthorized.</p>
  </header>
  <main>
    <section class="wide">
      <h2>Causal Chain</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Project</strong><span>{html.escape(_safe_text(project_summary.get("project_id")))}</span></div>
          <div class="node"><strong>Catalog</strong><span>{html.escape(_safe_text((model.get("catalog_summary") or {}).get("file_count")))} files</span></div>
          <div class="node"><strong>Python Lens</strong><span>{html.escape(_safe_text(project_python_lens.get("python_file_count")))} files · <code>/project/python-lens</code></span></div>
          <div class="node"><strong>Patterns</strong><span>{_badge_list([str(row.get("pattern_id")) for row in pattern_bindings if isinstance(row, dict) and row.get("pattern_id")])}</span></div>
          <div class="node"><strong>Standards</strong><span>{_badge_list([str(row.get("standard_id")) for row in standard_bindings if isinstance(row, dict) and row.get("standard_id")][:4])}</span></div>
          <div class="node"><strong>Route</strong><span>{html.escape(route_id)}</span></div>
          <div class="node"><strong>Work</strong><span>{html.escape(_safe_text(work.get("work_id") or "not yet created"))}</span></div>
          <div class="node"><strong>Events</strong><span>{len(events)} shown</span></div>
          <div class="node"><strong>Evidence</strong><span>{len(evidence)} refs</span></div>
          <div class="node"><strong>Authority</strong><span><code>/authority</code></span></div>
          <div class="node"><strong>Tour</strong><span><code>/tour</code> · {html.escape(_safe_text(tour.get("time_budget_minutes")))} min</span></div>
          <div class="node"><strong>Prediction</strong><span><code>/prediction</code> · {html.escape(_safe_text(prediction_lens.get("status")))}</span></div>
          <div class="node"><strong>Market Boundary</strong><span><code>/market-boundary</code> · {html.escape(_safe_text(len(market_boundary_rows)))} rows</span></div>
          <div class="node"><strong>Corpus</strong><span><code>/corpus</code> · {html.escape(_safe_text(corpus_summary.get("corpus_count")))} corpora</span></div>
          <div class="node"><strong>Trace Repair</strong><span><code>/trace</code> · {html.escape(_safe_text(len(trace_rows)))} traces</span></div>
          <div class="node"><strong>Repair Loop</strong><span><code>/repair-loop</code> · {html.escape(_safe_text(len(repair_loop_transitions)))} transitions</span></div>
          <div class="node"><strong>Formal Cells</strong><span><code>/evidence-cells</code> · {html.escape(_safe_text(len(formal_evidence_cells)))} cells</span></div>
          <div class="node"><strong>Landing Replay</strong><span><code>/landing-replay</code> · {html.escape(_safe_text(len(landing_lanes)))} lanes</span></div>
          <div class="node"><strong>View Quality</strong><span><code>/view-quality</code> · {html.escape(_safe_text(len(view_quality_actions)))} actions</span></div>
          <div class="node"><strong>Projection Safety</strong><span><code>/projection-safety</code> · {html.escape(_safe_text(len(projection_rows)))} receipts</span></div>
          <div class="node"><strong>Drift Control</strong><span><code>/drift-control</code> · {html.escape(_safe_text(len(projection_drift_rows)))} rows</span></div>
          <div class="node"><strong>Route Cleanup</strong><span><code>/route-cleanup</code> · {html.escape(_safe_text(len(route_cleanup_rows)))} rows</span></div>
          <div class="node"><strong>Import Map</strong><span><code>/projection-import-map</code> · {html.escape(_safe_text(len(projection_import_rows)))} rows</span></div>
          <div class="node"><strong>Stripping Guard</strong><span><code>/stripping-guard</code> · {html.escape(_safe_text(len(stripping_guard_rows)))} guards</span></div>
          <div class="node"><strong>Standards Control</strong><span><code>/standards-control</code> · {html.escape(_safe_text(len(standards_control_rows)))} rows</span></div>
          <div class="node"><strong>Hook Coverage</strong><span><code>/hook-coverage</code> · {html.escape(_safe_text(len(hook_interventions)))} interventions</span></div>
          <div class="node"><strong>Replay Gauntlet</strong><span><code>/replay-gauntlet</code> · {html.escape(_safe_text(len(replay_episodes)))} episodes</span></div>
        </div>
        <table>
          {row("Route", route_id)}
          {row("Python lens", project_python_lens.get("lens_id") or "project_python_route_lens")}
          {row("Python ready routes", project_python_lens.get("ready_route_count"))}
          {row("Authority", route.get("authority") or causal.get("authority_boundary"))}
          {row("Authority map", authority_map.get("map_id") or "public_authority_map")}
          {row("Tour", tour.get("tour_id") or "public_ten_minute_tour")}
          {row("Prediction lens", prediction_lens.get("lens_id") or "public_prediction_lens")}
          {row("Market boundary lens", market_boundary_lens.get("lens_id") or "public_market_prediction_evidence_boundary_lens")}
          {row("Corpus lens", corpus_lens.get("lens_id") or "public_corpus_readiness_lens")}
          {row("Trace lens", trace_lens.get("lens_id") or "public_verifier_trace_repair_lens")}
          {row("Repair loop", repair_loop_lens.get("lens_id") or "public_verifier_repair_loop_lens")}
          {row("Formal evidence lens", evidence_cell_lens.get("lens_id") or "public_formal_evidence_cell_lens")}
          {row("Landing replay lens", landing_replay_lens.get("lens_id") or "public_work_landing_replay_lens")}
          {row("View quality lens", view_quality_lens.get("lens_id") or "public_view_quality_action_map_lens")}
          {row("Projection safety lens", projection_safety_lens.get("lens_id") or "public_projection_safety_audit_lens")}
          {row("Projection drift lens", projection_drift_lens.get("lens_id") or "public_projection_drift_control_lens")}
          {row("Route cleanup lens", route_cleanup_lens.get("lens_id") or "public_route_cleanup_contract_lens")}
          {row("Projection import map", projection_import_map_lens.get("lens_id") or "public_projection_import_map_lens")}
          {row("Import projector", import_projector_lens.get("lens_id") or "public_import_projector_contract_lens")}
          {row("Stripping guard", stripping_guard_lens.get("lens_id") or "public_stripping_guard_lens")}
          {row("Standards control", standards_control_lens.get("lens_id") or "public_standards_control_lens")}
          {row("Hook coverage lens", hook_coverage_lens.get("lens_id") or "public_hook_intervention_coverage_lens")}
          {row("Replay gauntlet lens", replay_gauntlet_lens.get("lens_id") or "public_agent_reliability_replay_gauntlet_lens")}
          {row("Source mutation authorized", route.get("source_mutation_authorized") is True or work.get("source_files_mutated") is True)}
          {row("Release authorized", model.get("release_authorized") is True)}
          {row("Provider calls authorized", model.get("provider_calls_authorized") is True)}
          {row("Open actionable intake cells", runtime_bridge.get("open_actionable_cell_count"))}
        </table>
        <p class="ceiling">Evidence is drilldown. Receipts explain what happened after the chain is visible; they are not the cockpit. Release remains unauthorized.</p>
      </div>
    </section>

    <section class="wide">
      <h2>Ten-Minute Tour</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Command</strong><span><code>microcosm tour &lt;project&gt;</code></span></div>
          <div class="node"><strong>Endpoint</strong><span><code>/tour</code></span></div>
          <div class="node"><strong>Budget</strong><span>{html.escape(_safe_text(tour.get("time_budget_minutes")))} minutes</span></div>
          <div class="node"><strong>Evidence</strong><span>{html.escape(_safe_text(len(tour.get("evidence_refs", []) if isinstance(tour.get("evidence_refs"), list) else [])))} refs</span></div>
        </div>
        <table>
          {row("Status", tour.get("status"))}
          {row("Project ref", tour.get("project_ref"))}
          {row("Compile headline", (tour.get("compile_summary") or {}).get("headline") if isinstance(tour.get("compile_summary"), dict) else "")}
          {row("Selected route", (tour.get("compile_summary") or {}).get("selected_route_id") if isinstance(tour.get("compile_summary"), dict) else "")}
          {row("Tour ref", tour.get("tour_ref"))}
          {row("Release authorized", tour.get("release_authorized") is True)}
        </table>
        <h3>Route cards</h3>
        <table>
          <thead><tr><th>Card</th><th>Minutes</th><th>Command</th><th>Status</th></tr></thead>
          <tbody>{tour_card_rows(tour_cards)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Python Route Lens</h2>
      <div class="content">
        <table>
          {row("Command", project_python_lens.get("command") or "microcosm python-lens <project>")}
          {row("Python files", project_python_lens.get("python_file_count"))}
          {row("Package roots", ", ".join([str(value) for value in project_python_lens.get("package_roots", [])]) if isinstance(project_python_lens.get("package_roots"), list) else "")}
          {row("Ready route count", project_python_lens.get("ready_route_count"))}
          {row("Evidence ref", project_python_lens.get("evidence_ref"))}
          {row("Body redacted", project_python_lens.get("body_redacted") is True)}
        </table>
        <h3>Readiness checks</h3>
        {_badge_list([str(item.get("check_id")) + ":" + str(item.get("status")) for item in python_readiness_checks if isinstance(item, dict)])}
        <h3>Route rows</h3>
        <table>
          <thead><tr><th>Route</th><th>Readiness</th><th>Grounded refs</th></tr></thead>
          <tbody>{python_lens_rows(python_route_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Corpus Readiness Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Corpus</strong><span><code>/corpus</code></span></div>
          <div class="node"><strong>Mathlib import</strong><span>{html.escape(_safe_text(corpus_summary.get("mathlib_lake_project_import_available")))}</span></div>
          <div class="node"><strong>Absent corpora</strong><span>{_badge_list([str(value) for value in corpus_summary.get("absent_corpus_ids", [])] if isinstance(corpus_summary.get("absent_corpus_ids"), list) else [])}</span></div>
          <div class="node"><strong>Blocked consumers</strong><span>{html.escape(_safe_text(len(corpus_gate.get("blocked_case_ids", []) if isinstance(corpus_gate.get("blocked_case_ids"), list) else [])))}</span></div>
        </div>
        <table>
          {row("Command", corpus_lens.get("command") or "microcosm corpus-lens")}
          {row("Corpus count", corpus_summary.get("corpus_count"))}
          {row("Translation smoke-only", ", ".join([str(value) for value in corpus_summary.get("translation_smoke_only_ids", [])]) if isinstance(corpus_summary.get("translation_smoke_only_ids"), list) else "")}
          {row("Allowed cases", ", ".join([str(value) for value in corpus_gate.get("allowed_case_ids", [])]) if isinstance(corpus_gate.get("allowed_case_ids"), list) else "")}
          {row("Blocked cases", ", ".join([str(value) for value in corpus_gate.get("blocked_case_ids", [])]) if isinstance(corpus_gate.get("blocked_case_ids"), list) else "")}
          {row("Proof authority", (corpus_lens.get("authority_ceiling") or {}).get("formal_proof_authority") is True if isinstance(corpus_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", corpus_lens.get("release_authorized") is True)}
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Spine / Intake / Reveal Bridge</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Spine</strong><span><code>/spine</code></span></div>
          <div class="node"><strong>Authority</strong><span><code>/authority</code> · {html.escape(_safe_text((authority_map.get("surface_counts") or {}).get("hard_boundary_count") if isinstance(authority_map.get("surface_counts"), dict) else ""))} boundaries</span></div>
          <div class="node"><strong>Prediction</strong><span><code>/prediction</code> · {html.escape(_safe_text(cp2_prediction_count))} CP2 rows</span></div>
          <div class="node"><strong>Market Boundary</strong><span><code>/market-boundary</code> · {html.escape(_safe_text(len(market_boundary_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>Corpus</strong><span><code>/corpus</code> · {html.escape(_safe_text(len(corpus_gate.get("blocked_case_ids", []) if isinstance(corpus_gate.get("blocked_case_ids"), list) else [])))} blocked consumers</span></div>
          <div class="node"><strong>Trace</strong><span><code>/trace</code> · {html.escape(_safe_text(len(trace_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>Repair Loop</strong><span><code>/repair-loop</code> · {html.escape(_safe_text(len(repair_loop_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>Formal Cells</strong><span><code>/evidence-cells</code> · {html.escape(_safe_text(len(formal_evidence_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>Landing</strong><span><code>/landing-replay</code> · {html.escape(_safe_text(len(landing_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>View Quality</strong><span><code>/view-quality</code> · {html.escape(_safe_text(len(view_quality_hot_actions)))} hot actions</span></div>
          <div class="node"><strong>Projection Safety</strong><span><code>/projection-safety</code> · {html.escape(_safe_text(len(projection_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>Drift Control</strong><span><code>/drift-control</code> · {html.escape(_safe_text(len(projection_drift_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>Route Cleanup</strong><span><code>/route-cleanup</code> · {html.escape(_safe_text(len(route_cleanup_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>Import Map</strong><span><code>/projection-import-map</code> · {html.escape(_safe_text(len(projection_import_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>Standards Control</strong><span><code>/standards-control</code> · {html.escape(_safe_text(len(standards_control_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>Hook Coverage</strong><span><code>/hook-coverage</code> · {html.escape(_safe_text(len(hook_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>Replay Gauntlet</strong><span><code>/replay-gauntlet</code> · {html.escape(_safe_text(len(replay_negative_cases)))} negative cases</span></div>
          <div class="node"><strong>Intake</strong><span><code>/intake</code> · {html.escape(_safe_text(runtime_bridge.get("closed_cell_count")))} closed cells</span></div>
          <div class="node"><strong>Reveal</strong><span><code>/reveal</code> · {html.escape(_safe_text((runtime_bridge.get("reveal_summary") or {}).get("step_count") if isinstance(runtime_bridge.get("reveal_summary"), dict) else ""))} steps</span></div>
          <div class="node"><strong>Evidence</strong><span>{html.escape(_safe_text(len(runtime_bridge.get("evidence_refs", []) if isinstance(runtime_bridge.get("evidence_refs"), list) else [])))} refs</span></div>
        </div>
        <table>
          {row("Bridge id", runtime_bridge.get("bridge_id"))}
          {row("Authority command", authority_map.get("command"))}
          {row("Prediction command", prediction_lens.get("command"))}
          {row("Market-boundary command", market_boundary_lens.get("command"))}
          {row("Corpus command", corpus_lens.get("command"))}
          {row("Trace command", trace_lens.get("command"))}
          {row("Repair-loop command", repair_loop_lens.get("command"))}
          {row("Evidence-cell command", evidence_cell_lens.get("command"))}
          {row("Landing replay command", landing_replay_lens.get("command"))}
          {row("View quality command", view_quality_lens.get("command"))}
          {row("Projection safety command", projection_safety_lens.get("command"))}
          {row("Projection drift command", projection_drift_lens.get("command"))}
          {row("Route cleanup command", route_cleanup_lens.get("command"))}
          {row("Projection import map command", projection_import_map_lens.get("command"))}
          {row("Standards control command", standards_control_lens.get("command"))}
          {row("Replay gauntlet command", replay_gauntlet_lens.get("command"))}
          {row("Projection status counts", json.dumps(runtime_bridge.get("projection_status_counts", {}), sort_keys=True))}
          {row("Open actionable cells", runtime_bridge.get("open_actionable_cell_count"))}
          {row("Prediction source patterns", ", ".join([str(value) for value in prediction_lens.get("source_pattern_ids", [])[:3]]) if isinstance(prediction_lens.get("source_pattern_ids"), list) else "")}
          {row("Release authorized", (runtime_bridge.get("authority_ceiling") or {}).get("release_authorized") is True if isinstance(runtime_bridge.get("authority_ceiling"), dict) else False)}
        </table>
        <h3>Projection cell status</h3>
        <table>
          <thead><tr><th>Cell</th><th>Projection status</th><th>Cell state</th><th>Next runtime surface</th></tr></thead>
          <tbody>{cell_rows(bridge_cells)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Verifier Trace Repair Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Trace</strong><span><code>/trace</code></span></div>
          <div class="node"><strong>Attempts</strong><span>{html.escape(_safe_text(len(trace_rows)))}</span></div>
          <div class="node"><strong>Cold rerun gate</strong><span>{html.escape(_safe_text((trace_lens.get("repair_policy") or {}).get("cold_rerun_required_before_promotion") if isinstance(trace_lens.get("repair_policy"), dict) else ""))}</span></div>
          <div class="node"><strong>Proof authority</strong><span>{html.escape(_safe_text((trace_lens.get("authority_ceiling") or {}).get("formal_proof_authority") if isinstance(trace_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", trace_lens.get("command") or "microcosm trace-lens")}
          {row("Status", trace_lens.get("status"))}
          {row("Source patterns", ", ".join([str(value) for value in trace_lens.get("source_pattern_ids", [])]) if isinstance(trace_lens.get("source_pattern_ids"), list) else "")}
          {row("Negative cases", ", ".join([str(value) for value in trace_negative_cases]))}
          {row("Proof bodies exported", (trace_lens.get("authority_ceiling") or {}).get("proof_bodies_exported") is True if isinstance(trace_lens.get("authority_ceiling"), dict) else False)}
          {row("Oracle premise ids exported", (trace_lens.get("authority_ceiling") or {}).get("oracle_needed_premise_ids_exported") is True if isinstance(trace_lens.get("authority_ceiling"), dict) else False)}
          {row("Lean/Lake execution authorized", (trace_lens.get("authority_ceiling") or {}).get("lean_lake_execution_authorized") is True if isinstance(trace_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", trace_lens.get("release_authorized") is True)}
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Verifier Repair Loop Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Repair Loop</strong><span><code>/repair-loop</code></span></div>
          <div class="node"><strong>Stages</strong><span>{html.escape(_safe_text(len(repair_loop_stages)))}</span></div>
          <div class="node"><strong>Transitions</strong><span>{html.escape(_safe_text(len(repair_loop_transitions)))}</span></div>
          <div class="node"><strong>Curriculum scope</strong><span>{html.escape(_safe_text((repair_loop_lens.get("curriculum_policy") or {}).get("promotion_scope") if isinstance(repair_loop_lens.get("curriculum_policy"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", repair_loop_lens.get("command") or "microcosm repair-loop")}
          {row("Status", repair_loop_lens.get("status"))}
          {row("Selected pattern", repair_loop_lens.get("selected_pattern_id"))}
          {row("Negative cases", ", ".join([str(value) for value in repair_loop_negative_cases]))}
          {row("Cold rerun required", (repair_loop_lens.get("curriculum_policy") or {}).get("cold_rerun_required_before_promotion") is True if isinstance(repair_loop_lens.get("curriculum_policy"), dict) else False)}
          {row("Proof bodies exported", (repair_loop_lens.get("authority_ceiling") or {}).get("proof_bodies_exported") is True if isinstance(repair_loop_lens.get("authority_ceiling"), dict) else False)}
          {row("Oracle premise ids exported", (repair_loop_lens.get("authority_ceiling") or {}).get("oracle_needed_premise_ids_exported") is True if isinstance(repair_loop_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", repair_loop_lens.get("release_authorized") is True)}
        </table>
        <h3>Transitions</h3>
        <table>
          <thead><tr><th>Attempt</th><th>Failure class</th><th>Repair action</th><th>To stage</th><th>Promote</th></tr></thead>
          <tbody>{repair_loop_transition_rows(repair_loop_transitions)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Formal Evidence Cell Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Cells</strong><span><code>/evidence-cells</code></span></div>
          <div class="node"><strong>Cell count</strong><span>{html.escape(_safe_text(len(formal_evidence_cells)))}</span></div>
          <div class="node"><strong>Present cells</strong><span>{html.escape(_safe_text((evidence_cell_lens.get("resolver_summary") or {}).get("present_cell_count") if isinstance(evidence_cell_lens.get("resolver_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Proof authority</strong><span>{html.escape(_safe_text((evidence_cell_lens.get("authority_ceiling") or {}).get("formal_proof_authority") if isinstance(evidence_cell_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", evidence_cell_lens.get("command") or "microcosm evidence-cells")}
          {row("Status", evidence_cell_lens.get("status"))}
          {row("Selected pattern", evidence_cell_lens.get("selected_pattern_id"))}
          {row("Negative cases", ", ".join([str(value) for value in formal_evidence_negative_cases]))}
          {row("Proof bodies exported", (evidence_cell_lens.get("authority_ceiling") or {}).get("proof_bodies_exported") is True if isinstance(evidence_cell_lens.get("authority_ceiling"), dict) else False)}
          {row("Private refs exported", (evidence_cell_lens.get("authority_ceiling") or {}).get("private_source_refs_exported") is True if isinstance(evidence_cell_lens.get("authority_ceiling"), dict) else False)}
          {row("General theorem solution claim", (evidence_cell_lens.get("authority_ceiling") or {}).get("general_theorem_solution_claim") is True if isinstance(evidence_cell_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", evidence_cell_lens.get("release_authorized") is True)}
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Work Landing Replay Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Landing</strong><span><code>/landing-replay</code></span></div>
          <div class="node"><strong>Lanes</strong><span>{html.escape(_safe_text(len(landing_lanes)))}</span></div>
          <div class="node"><strong>Blocker ref</strong><span>{html.escape(_safe_text((landing_replay_lens.get("replay_summary") or {}).get("git_metadata_blocker_ref") if isinstance(landing_replay_lens.get("replay_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Git mutation</strong><span>{html.escape(_safe_text((landing_replay_lens.get("authority_ceiling") or {}).get("live_git_mutation_authorized") if isinstance(landing_replay_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", landing_replay_lens.get("command") or "microcosm landing-replay")}
          {row("Status", landing_replay_lens.get("status"))}
          {row("Selected pattern", landing_replay_lens.get("selected_pattern_id"))}
          {row("Negative cases", ", ".join([str(value) for value in landing_negative_cases]))}
          {row("Broad checkpoint authorized", (landing_replay_lens.get("authority_ceiling") or {}).get("broad_checkpoint_authorized") is True if isinstance(landing_replay_lens.get("authority_ceiling"), dict) else False)}
          {row("Unrelated dirty paths authorized", (landing_replay_lens.get("authority_ceiling") or {}).get("unrelated_dirty_paths_authorized") is True if isinstance(landing_replay_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", landing_replay_lens.get("release_authorized") is True)}
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Proof Loop Depth Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Proof Loop</strong><span><code>/proof-loop-depth</code></span></div>
          <div class="node"><strong>Gates</strong><span>{html.escape(_safe_text(len(proof_loop_depth_rows)))}</span></div>
          <div class="node"><strong>Evidence refs</strong><span>{html.escape(_safe_text((proof_loop_depth_lens.get("proof_loop_summary") or {}).get("evidence_ref_count") if isinstance(proof_loop_depth_lens.get("proof_loop_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Proof authority</strong><span>{html.escape(_safe_text((proof_loop_depth_lens.get("authority_ceiling") or {}).get("formal_proof_authority") if isinstance(proof_loop_depth_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", proof_loop_depth_lens.get("command") or "microcosm proof-loop-depth")}
          {row("Status", proof_loop_depth_lens.get("status"))}
          {row("Selected patterns", ", ".join([str(value) for value in proof_loop_depth_lens.get("selected_pattern_ids", [])]) if isinstance(proof_loop_depth_lens.get("selected_pattern_ids"), list) else "")}
          {row("Negative cases", ", ".join([str(value) for value in proof_loop_depth_negative_cases]))}
          {row("Proof bodies exported", (proof_loop_depth_lens.get("authority_ceiling") or {}).get("proof_bodies_exported") is True if isinstance(proof_loop_depth_lens.get("authority_ceiling"), dict) else False)}
          {row("Oracle premise ids exported", (proof_loop_depth_lens.get("authority_ceiling") or {}).get("oracle_needed_premise_ids_exported") is True if isinstance(proof_loop_depth_lens.get("authority_ceiling"), dict) else False)}
          {row("Benchmark score claim", (proof_loop_depth_lens.get("authority_ceiling") or {}).get("benchmark_score_claim") is True if isinstance(proof_loop_depth_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", proof_loop_depth_lens.get("release_authorized") is True)}
        </table>
        <h3>Depth gates</h3>
        <table>
          <thead><tr><th>Gate</th><th>Depth</th><th>Evidence</th><th>Promotion scope</th><th>Proof body</th></tr></thead>
          <tbody>{proof_loop_depth_table_rows(proof_loop_depth_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>View Quality Action Map Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>View Quality</strong><span><code>/view-quality</code></span></div>
          <div class="node"><strong>Action rows</strong><span>{html.escape(_safe_text(len(view_quality_actions)))}</span></div>
          <div class="node"><strong>Hot actions</strong><span>{html.escape(_safe_text(len(view_quality_hot_actions)))}</span></div>
          <div class="node"><strong>Browser control</strong><span>{html.escape(_safe_text((view_quality_lens.get("authority_ceiling") or {}).get("live_browser_control_authorized") if isinstance(view_quality_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", view_quality_lens.get("command") or "microcosm view-quality")}
          {row("Status", view_quality_lens.get("status"))}
          {row("Selected pattern", view_quality_lens.get("selected_pattern_id"))}
          {row("Negative cases", ", ".join([str(value) for value in view_quality_negative_cases]))}
          {row("Private screenshot paths exported", (view_quality_lens.get("authority_ceiling") or {}).get("private_screenshot_paths_exported") is True if isinstance(view_quality_lens.get("authority_ceiling"), dict) else False)}
          {row("Complete frontend quality claim", (view_quality_lens.get("authority_ceiling") or {}).get("complete_frontend_quality_claim") is True if isinstance(view_quality_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", view_quality_lens.get("release_authorized") is True)}
        </table>
        <h3>Action map</h3>
        <table>
          <thead><tr><th>View</th><th>Census status</th><th>Action class</th><th>Next action</th></tr></thead>
          <tbody>{view_quality_action_rows(view_quality_actions)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Projection Safety Audit Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Projection Safety</strong><span><code>/projection-safety</code></span></div>
          <div class="node"><strong>Projection rows</strong><span>{html.escape(_safe_text(len(projection_rows)))}</span></div>
          <div class="node"><strong>Omission receipts</strong><span>{html.escape(_safe_text((projection_safety_lens.get("projection_summary") or {}).get("omission_receipt_count") if isinstance(projection_safety_lens.get("projection_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Release authority</strong><span>{html.escape(_safe_text((projection_safety_lens.get("authority_ceiling") or {}).get("release_authorized") if isinstance(projection_safety_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", projection_safety_lens.get("command") or "microcosm projection-safety")}
          {row("Status", projection_safety_lens.get("status"))}
          {row("Selected pattern", projection_safety_lens.get("selected_pattern_id"))}
          {row("Negative cases", ", ".join([str(value) for value in projection_negative_cases]))}
          {row("Private body exports", (projection_safety_lens.get("projection_summary") or {}).get("private_body_export_count") if isinstance(projection_safety_lens.get("projection_summary"), dict) else "")}
          {row("Proof body exports", (projection_safety_lens.get("projection_summary") or {}).get("proof_body_export_count") if isinstance(projection_safety_lens.get("projection_summary"), dict) else "")}
          {row("Provider payload exports", (projection_safety_lens.get("projection_summary") or {}).get("provider_payload_export_count") if isinstance(projection_safety_lens.get("projection_summary"), dict) else "")}
          {row("Release authorized", projection_safety_lens.get("release_authorized") is True)}
        </table>
        <h3>Reversible projection rows</h3>
        <table>
          <thead><tr><th>Projection</th><th>Endpoint</th><th>Drilldown</th><th>Authority ceiling</th></tr></thead>
          <tbody>{projection_safety_rows(projection_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Market Prediction Boundary Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Market Boundary</strong><span><code>/market-boundary</code></span></div>
          <div class="node"><strong>Rows</strong><span>{html.escape(_safe_text((market_boundary_lens.get("boundary_summary") or {}).get("row_count") if isinstance(market_boundary_lens.get("boundary_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Decision boundaries</strong><span>{html.escape(_safe_text((market_boundary_lens.get("boundary_summary") or {}).get("decision_boundary_count") if isinstance(market_boundary_lens.get("boundary_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Advice authority</strong><span>{html.escape(_safe_text((market_boundary_lens.get("authority_ceiling") or {}).get("trading_advice_authorized") if isinstance(market_boundary_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", market_boundary_lens.get("command") or "microcosm market-boundary")}
          {row("Status", market_boundary_lens.get("status"))}
          {row("Selected route", market_boundary_lens.get("selected_route_id"))}
          {row("Negative cases", ", ".join([str(value) for value in market_boundary_negative_cases]))}
          {row("Live market data authorized", (market_boundary_lens.get("authority_ceiling") or {}).get("live_market_data_authorized") is True if isinstance(market_boundary_lens.get("authority_ceiling"), dict) else False)}
          {row("Investment recommendation authorized", (market_boundary_lens.get("authority_ceiling") or {}).get("investment_recommendation_authorized") is True if isinstance(market_boundary_lens.get("authority_ceiling"), dict) else False)}
          {row("Private portfolio exported", (market_boundary_lens.get("authority_ceiling") or {}).get("private_portfolio_exported") is True if isinstance(market_boundary_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", market_boundary_lens.get("release_authorized") is True)}
        </table>
        <h3>Boundary rows</h3>
        <table>
          <thead><tr><th>Row</th><th>Public rule</th><th>Decision boundary</th><th>Owner route</th><th>Advice</th></tr></thead>
          <tbody>{market_boundary_table_rows(market_boundary_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Projection Drift Control Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Drift Control</strong><span><code>/drift-control</code></span></div>
          <div class="node"><strong>Rows</strong><span>{html.escape(_safe_text((projection_drift_lens.get("drift_summary") or {}).get("row_count") if isinstance(projection_drift_lens.get("drift_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Repair routes</strong><span>{html.escape(_safe_text((projection_drift_lens.get("drift_summary") or {}).get("repair_route_count") if isinstance(projection_drift_lens.get("drift_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Live repair</strong><span>{html.escape(_safe_text((projection_drift_lens.get("authority_ceiling") or {}).get("live_route_repair_authorized") if isinstance(projection_drift_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", projection_drift_lens.get("command") or "microcosm drift-control")}
          {row("Status", projection_drift_lens.get("status"))}
          {row("Selected route", projection_drift_lens.get("selected_route_id"))}
          {row("Negative cases", ", ".join([str(value) for value in projection_drift_negative_cases]))}
          {row("Source authority claims", (projection_drift_lens.get("drift_summary") or {}).get("source_authority_claim_count") if isinstance(projection_drift_lens.get("drift_summary"), dict) else "")}
          {row("Live repairs authorized", (projection_drift_lens.get("drift_summary") or {}).get("live_repair_authorized_count") if isinstance(projection_drift_lens.get("drift_summary"), dict) else "")}
          {row("Doctrine promotions authorized", (projection_drift_lens.get("drift_summary") or {}).get("automatic_doctrine_promotion_count") if isinstance(projection_drift_lens.get("drift_summary"), dict) else "")}
          {row("Release authorized", projection_drift_lens.get("release_authorized") is True)}
        </table>
        <h3>Drift rows</h3>
        <table>
          <thead><tr><th>Row</th><th>Source signal</th><th>Repair route</th><th>Validation ref</th><th>Source authority</th></tr></thead>
          <tbody>{projection_drift_table_rows(projection_drift_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Route Cleanup Contract Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Route Cleanup</strong><span><code>/route-cleanup</code></span></div>
          <div class="node"><strong>Rows</strong><span>{html.escape(_safe_text((route_cleanup_lens.get("cleanup_summary") or {}).get("row_count") if isinstance(route_cleanup_lens.get("cleanup_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Owner routes</strong><span>{html.escape(_safe_text((route_cleanup_lens.get("cleanup_summary") or {}).get("owner_route_count") if isinstance(route_cleanup_lens.get("cleanup_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Route deletion</strong><span>{html.escape(_safe_text((route_cleanup_lens.get("authority_ceiling") or {}).get("route_deletion_authorized") if isinstance(route_cleanup_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", route_cleanup_lens.get("command") or "microcosm route-cleanup")}
          {row("Status", route_cleanup_lens.get("status"))}
          {row("Selected route", route_cleanup_lens.get("selected_route_id"))}
          {row("Negative cases", ", ".join([str(value) for value in route_cleanup_negative_cases]))}
          {row("Validation refs", (route_cleanup_lens.get("cleanup_summary") or {}).get("validation_ref_count") if isinstance(route_cleanup_lens.get("cleanup_summary"), dict) else "")}
          {row("Generated hand edits authorized", (route_cleanup_lens.get("cleanup_summary") or {}).get("generated_region_hand_edit_authorized_count") if isinstance(route_cleanup_lens.get("cleanup_summary"), dict) else "")}
          {row("Private body exports", (route_cleanup_lens.get("cleanup_summary") or {}).get("private_body_export_count") if isinstance(route_cleanup_lens.get("cleanup_summary"), dict) else "")}
          {row("Release authorized", route_cleanup_lens.get("release_authorized") is True)}
        </table>
        <h3>Cleanup rows</h3>
        <table>
          <thead><tr><th>Row</th><th>Action class</th><th>Owner route</th><th>Validation ref</th><th>Route deletion</th></tr></thead>
          <tbody>{route_cleanup_table_rows(route_cleanup_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Projection Import Map Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Import Map</strong><span><code>/projection-import-map</code></span></div>
          <div class="node"><strong>Rows</strong><span>{html.escape(_safe_text((projection_import_map_lens.get("map_summary") or {}).get("row_count") if isinstance(projection_import_map_lens.get("map_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Stages</strong><span>{html.escape(_safe_text(len(projection_import_stages)))}</span></div>
          <div class="node"><strong>Automated import</strong><span>{html.escape(_safe_text((projection_import_map_lens.get("authority_ceiling") or {}).get("automated_import_guarantee") if isinstance(projection_import_map_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", projection_import_map_lens.get("command") or "microcosm projection-import-map")}
          {row("Status", projection_import_map_lens.get("status"))}
          {row("Selected patterns", ", ".join([str(value) for value in projection_import_map_lens.get("selected_pattern_ids", [])]) if isinstance(projection_import_map_lens.get("selected_pattern_ids"), list) else "")}
          {row("Negative cases", ", ".join([str(value) for value in projection_import_negative_cases]))}
          {row("Validation refs", (projection_import_map_lens.get("map_summary") or {}).get("validation_ref_count") if isinstance(projection_import_map_lens.get("map_summary"), dict) else "")}
          {row("Private body exports", (projection_import_map_lens.get("map_summary") or {}).get("private_body_export_count") if isinstance(projection_import_map_lens.get("map_summary"), dict) else "")}
          {row("Provider payload exports", (projection_import_map_lens.get("map_summary") or {}).get("provider_payload_export_count") if isinstance(projection_import_map_lens.get("map_summary"), dict) else "")}
          {row("Release authorized", projection_import_map_lens.get("release_authorized") is True)}
        </table>
        <h3>Import rows</h3>
        <table>
          <thead><tr><th>Map row</th><th>Source pattern</th><th>Public surface</th><th>Cleaned</th><th>Authority ceiling</th></tr></thead>
          <tbody>{projection_import_map_rows(projection_import_rows)}</tbody>
        </table>
      </div>
    </section>

	    <section class="wide">
	      <h2>Import Projector Contract Lens</h2>
	      <div class="content">
        <div class="chain">
          <div class="node"><strong>Import Projector</strong><span><code>/import-projector</code></span></div>
          <div class="node"><strong>Rows</strong><span>{html.escape(_safe_text((import_projector_lens.get("projector_summary") or {}).get("row_count") if isinstance(import_projector_lens.get("projector_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Stages</strong><span>{html.escape(_safe_text(len(import_projector_stages)))}</span></div>
          <div class="node"><strong>Automated execution</strong><span>{html.escape(_safe_text((import_projector_lens.get("authority_ceiling") or {}).get("automated_import_execution_authorized") if isinstance(import_projector_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", import_projector_lens.get("command") or "microcosm import-projector")}
          {row("Status", import_projector_lens.get("status"))}
          {row("Selected patterns", ", ".join([str(value) for value in import_projector_lens.get("selected_pattern_ids", [])]) if isinstance(import_projector_lens.get("selected_pattern_ids"), list) else "")}
          {row("Negative cases", ", ".join([str(value) for value in import_projector_negative_cases]))}
          {row("Validation refs", (import_projector_lens.get("projector_summary") or {}).get("validation_ref_count") if isinstance(import_projector_lens.get("projector_summary"), dict) else "")}
          {row("Generated hand edits", (import_projector_lens.get("projector_summary") or {}).get("generated_region_hand_edit_authorized_count") if isinstance(import_projector_lens.get("projector_summary"), dict) else "")}
          {row("Private body exports", (import_projector_lens.get("projector_summary") or {}).get("private_body_export_count") if isinstance(import_projector_lens.get("projector_summary"), dict) else "")}
          {row("Release authorized", import_projector_lens.get("release_authorized") is True)}
        </table>
        <h3>Projector rows</h3>
        <table>
          <thead><tr><th>Row</th><th>Stage</th><th>Public output</th><th>Validation</th><th>Authority ceiling</th></tr></thead>
          <tbody>{import_projector_table_rows(import_projector_rows)}</tbody>
        </table>
	      </div>
	    </section>

	    <section class="wide">
	      <h2>Compression Profile Option Surface Lens</h2>
	      <div class="content">
	        <div class="chain">
	          <div class="node"><strong>Option Surface</strong><span><code>/option-surface-lens</code></span></div>
	          <div class="node"><strong>Rows</strong><span>{html.escape(_safe_text((option_surface_lens.get("option_surface_summary") or {}).get("row_count") if isinstance(option_surface_lens.get("option_surface_summary"), dict) else ""))}</span></div>
	          <div class="node"><strong>Stages</strong><span>{html.escape(_safe_text(len(option_surface_stages)))}</span></div>
	          <div class="node"><strong>Profile switching</strong><span>{html.escape(_safe_text((option_surface_lens.get("authority_ceiling") or {}).get("profile_switch_execution_authorized") if isinstance(option_surface_lens.get("authority_ceiling"), dict) else ""))}</span></div>
	        </div>
	        <table>
	          {row("Command", option_surface_lens.get("command") or "microcosm option-surface-lens")}
	          {row("Status", option_surface_lens.get("status"))}
	          {row("Selected patterns", ", ".join([str(value) for value in option_surface_lens.get("selected_pattern_ids", [])]) if isinstance(option_surface_lens.get("selected_pattern_ids"), list) else "")}
	          {row("Negative cases", ", ".join([str(value) for value in option_surface_negative_cases]))}
	          {row("Validation refs", (option_surface_lens.get("option_surface_summary") or {}).get("validation_ref_count") if isinstance(option_surface_lens.get("option_surface_summary"), dict) else "")}
	          {row("Private body exports", (option_surface_lens.get("option_surface_summary") or {}).get("private_body_export_count") if isinstance(option_surface_lens.get("option_surface_summary"), dict) else "")}
	          {row("Provider payload exports", (option_surface_lens.get("option_surface_summary") or {}).get("provider_payload_export_count") if isinstance(option_surface_lens.get("option_surface_summary"), dict) else "")}
	          {row("Release authorized", option_surface_lens.get("release_authorized") is True)}
	        </table>
	        <h3>Option rows</h3>
	        <table>
	          <thead><tr><th>Row</th><th>Stage</th><th>Public output</th><th>Validation</th><th>Profile switch</th></tr></thead>
	          <tbody>{option_surface_table_rows(option_surface_rows)}</tbody>
	        </table>
	      </div>
	    </section>

	    <section class="wide">
	      <h2>Public/Private Stripping Guard Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Stripping Guard</strong><span><code>/stripping-guard</code></span></div>
          <div class="node"><strong>Guard rows</strong><span>{html.escape(_safe_text((stripping_guard_lens.get("guard_summary") or {}).get("guard_row_count") if isinstance(stripping_guard_lens.get("guard_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Negative cases</strong><span>{html.escape(_safe_text(len(stripping_guard_negative_cases)))}</span></div>
          <div class="node"><strong>Release authority</strong><span>{html.escape(_safe_text((stripping_guard_lens.get("authority_ceiling") or {}).get("release_authorized") if isinstance(stripping_guard_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", stripping_guard_lens.get("command") or "microcosm stripping-guard")}
          {row("Status", stripping_guard_lens.get("status"))}
          {row("Selected patterns", ", ".join([str(value) for value in stripping_guard_lens.get("selected_pattern_ids", [])]) if isinstance(stripping_guard_lens.get("selected_pattern_ids"), list) else "")}
          {row("Negative cases", ", ".join([str(value) for value in stripping_guard_negative_cases]))}
          {row("Private body exports", (stripping_guard_lens.get("guard_summary") or {}).get("private_body_export_count") if isinstance(stripping_guard_lens.get("guard_summary"), dict) else "")}
          {row("Proof body exports", (stripping_guard_lens.get("guard_summary") or {}).get("proof_body_export_count") if isinstance(stripping_guard_lens.get("guard_summary"), dict) else "")}
          {row("Provider payload exports", (stripping_guard_lens.get("guard_summary") or {}).get("provider_payload_export_count") if isinstance(stripping_guard_lens.get("guard_summary"), dict) else "")}
          {row("Raw private path exports", (stripping_guard_lens.get("guard_summary") or {}).get("raw_private_path_export_count") if isinstance(stripping_guard_lens.get("guard_summary"), dict) else "")}
          {row("Secret scanner complete", (stripping_guard_lens.get("authority_ceiling") or {}).get("secret_detection_completeness_claim") is True if isinstance(stripping_guard_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", stripping_guard_lens.get("release_authorized") is True)}
        </table>
        <h3>Guard rows</h3>
        <table>
          <thead><tr><th>Guard</th><th>Source risk</th><th>Public replacement</th><th>Strip rule</th><th>Release</th></tr></thead>
          <tbody>{stripping_guard_table_rows(stripping_guard_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Standards Control Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Standards Control</strong><span><code>/standards-control</code></span></div>
          <div class="node"><strong>Control rows</strong><span>{html.escape(_safe_text((standards_control_lens.get("standards_summary") or {}).get("standards_control_row_count") if isinstance(standards_control_lens.get("standards_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Validator refs</strong><span>{html.escape(_safe_text((standards_control_lens.get("standards_summary") or {}).get("validator_receipt_ref_count") if isinstance(standards_control_lens.get("standards_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Release authority</strong><span>{html.escape(_safe_text((standards_control_lens.get("authority_ceiling") or {}).get("release_authorized") if isinstance(standards_control_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", standards_control_lens.get("command") or "microcosm standards-control")}
          {row("Status", standards_control_lens.get("status"))}
          {row("Selected patterns", ", ".join([str(value) for value in standards_control_lens.get("selected_pattern_ids", [])]) if isinstance(standards_control_lens.get("selected_pattern_ids"), list) else "")}
          {row("Negative cases", ", ".join([str(value) for value in standards_control_negative_cases]))}
          {row("Standards", (standards_control_lens.get("standards_summary") or {}).get("standard_count") if isinstance(standards_control_lens.get("standards_summary"), dict) else "")}
          {row("Standard pressure rows", (standards_control_lens.get("standards_summary") or {}).get("standard_pressure_row_count") if isinstance(standards_control_lens.get("standards_summary"), dict) else "")}
          {row("Validator receipt refs", (standards_control_lens.get("standards_summary") or {}).get("validator_receipt_ref_count") if isinstance(standards_control_lens.get("standards_summary"), dict) else "")}
          {row("Source authority claims", (standards_control_lens.get("standards_summary") or {}).get("source_authority_claim_count") if isinstance(standards_control_lens.get("standards_summary"), dict) else "")}
          {row("Standards completeness claim", (standards_control_lens.get("authority_ceiling") or {}).get("standards_completeness_claim") is True if isinstance(standards_control_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", standards_control_lens.get("release_authorized") is True)}
        </table>
        <h3>Control rows</h3>
        <table>
          <thead><tr><th>Control</th><th>Source</th><th>Public role</th><th>Observed</th><th>Release</th></tr></thead>
          <tbody>{standards_control_table_rows(standards_control_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Hook Intervention Coverage Lens</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Hook Coverage</strong><span><code>/hook-coverage</code></span></div>
          <div class="node"><strong>Interventions</strong><span>{html.escape(_safe_text(len(hook_interventions)))}</span></div>
          <div class="node"><strong>Authority rejections</strong><span>{html.escape(_safe_text((hook_coverage_lens.get("coverage_summary") or {}).get("authority_rejection_count") if isinstance(hook_coverage_lens.get("coverage_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Live state read</strong><span>{html.escape(_safe_text((hook_coverage_lens.get("authority_ceiling") or {}).get("live_operator_state_read") if isinstance(hook_coverage_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", hook_coverage_lens.get("command") or "microcosm hook-coverage")}
          {row("Status", hook_coverage_lens.get("status"))}
          {row("Selected pattern", hook_coverage_lens.get("selected_pattern_id"))}
          {row("Negative cases", ", ".join([str(value) for value in hook_negative_cases]))}
          {row("Missing authority cases", ", ".join([str(value) for value in hook_coverage_lens.get("missing_authority_case_ids", [])]) if isinstance(hook_coverage_lens.get("missing_authority_case_ids"), list) else "")}
          {row("Provider payload read", (hook_coverage_lens.get("authority_ceiling") or {}).get("provider_payload_read") is True if isinstance(hook_coverage_lens.get("authority_ceiling"), dict) else False)}
          {row("Task Ledger mutation", (hook_coverage_lens.get("authority_ceiling") or {}).get("live_task_ledger_mutation_authorized") is True if isinstance(hook_coverage_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", hook_coverage_lens.get("release_authorized") is True)}
        </table>
        <h3>Intervention rows</h3>
        <table>
          <thead><tr><th>Intervention</th><th>Source receipt</th><th>Decision</th><th>Signal</th></tr></thead>
          <tbody>{hook_intervention_rows(hook_interventions)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Agent Reliability Replay Gauntlet</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Replay Gauntlet</strong><span><code>/replay-gauntlet</code></span></div>
          <div class="node"><strong>Episodes</strong><span>{html.escape(_safe_text(len(replay_episodes)))}</span></div>
          <div class="node"><strong>Blocked</strong><span>{html.escape(_safe_text((replay_gauntlet_lens.get("coverage_summary") or {}).get("blocked_episode_count") if isinstance(replay_gauntlet_lens.get("coverage_summary"), dict) else ""))}</span></div>
          <div class="node"><strong>Quarantined</strong><span>{html.escape(_safe_text((replay_gauntlet_lens.get("coverage_summary") or {}).get("quarantined_episode_count") if isinstance(replay_gauntlet_lens.get("coverage_summary"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", replay_gauntlet_lens.get("command") or "microcosm replay-gauntlet")}
          {row("Status", replay_gauntlet_lens.get("status"))}
          {row("Selected route", replay_gauntlet_lens.get("selected_route_id"))}
          {row("Negative cases", ", ".join([str(value) for value in replay_negative_cases]))}
          {row("Live agent execution", (replay_gauntlet_lens.get("authority_ceiling") or {}).get("live_agent_execution_authorized") is True if isinstance(replay_gauntlet_lens.get("authority_ceiling"), dict) else False)}
          {row("Live tool calls", (replay_gauntlet_lens.get("authority_ceiling") or {}).get("live_tool_calls_authorized") is True if isinstance(replay_gauntlet_lens.get("authority_ceiling"), dict) else False)}
          {row("Real secrets exported", (replay_gauntlet_lens.get("authority_ceiling") or {}).get("real_secret_material_exported") is True if isinstance(replay_gauntlet_lens.get("authority_ceiling"), dict) else False)}
          {row("Complete security claim", (replay_gauntlet_lens.get("authority_ceiling") or {}).get("complete_security_claim") is True if isinstance(replay_gauntlet_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", replay_gauntlet_lens.get("release_authorized") is True)}
        </table>
        <h3>Replay episodes</h3>
        <table>
          <thead><tr><th>Episode</th><th>Verdict</th><th>Containment</th><th>Negative case</th></tr></thead>
          <tbody>{replay_episode_rows(replay_episodes)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Repository Benchmark Transaction Lab</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Benchmark Lab</strong><span><code>/benchmark-lab</code></span></div>
          <div class="node"><strong>Tasks</strong><span>{html.escape(_safe_text((benchmark_lab_lens.get("scorecard") or {}).get("task_count") if isinstance(benchmark_lab_lens.get("scorecard"), dict) else ""))}</span></div>
          <div class="node"><strong>Oracle patches</strong><span>{html.escape(_safe_text((benchmark_lab_lens.get("scorecard") or {}).get("oracle_patch_count") if isinstance(benchmark_lab_lens.get("scorecard"), dict) else ""))}</span></div>
          <div class="node"><strong>Provider call</strong><span>{html.escape(_safe_text((benchmark_lab_lens.get("authority_ceiling") or {}).get("provider_call_authorized") if isinstance(benchmark_lab_lens.get("authority_ceiling"), dict) else ""))}</span></div>
        </div>
        <table>
          {row("Command", benchmark_lab_lens.get("command") or "microcosm benchmark-lab")}
          {row("Status", benchmark_lab_lens.get("status"))}
          {row("Selected patterns", ", ".join([str(value) for value in benchmark_lab_lens.get("selected_pattern_ids", [])]) if isinstance(benchmark_lab_lens.get("selected_pattern_ids"), list) else "")}
          {row("Negative cases", ", ".join([str(value) for value in benchmark_negative_cases]))}
          {row("SWE-bench score claim", (benchmark_lab_lens.get("authority_ceiling") or {}).get("swe_bench_performance_claim") is True if isinstance(benchmark_lab_lens.get("authority_ceiling"), dict) else False)}
          {row("Live repo mutation", (benchmark_lab_lens.get("authority_ceiling") or {}).get("live_repo_mutation_authorized") is True if isinstance(benchmark_lab_lens.get("authority_ceiling"), dict) else False)}
          {row("Production delivery claim", (benchmark_lab_lens.get("authority_ceiling") or {}).get("production_delivery_rate_claim") is True if isinstance(benchmark_lab_lens.get("authority_ceiling"), dict) else False)}
          {row("Release authorized", benchmark_lab_lens.get("release_authorized") is True)}
        </table>
        <h3>Benchmark tasks</h3>
        <table>
          <thead><tr><th>Task</th><th>Kind</th><th>Work admission</th><th>Provider slot</th></tr></thead>
          <tbody>{benchmark_task_rows(benchmark_tasks)}</tbody>
        </table>
      </div>
    </section>

    <section class="wide">
      <h2>Cold Reader Legibility Scorecard</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Legibility Scorecard</strong><span><code>/legibility-scorecard</code></span></div>
          <div class="node"><strong>Checkpoints</strong><span>{html.escape(_safe_text((legibility_scorecard_lens.get("scorecard") or {}).get("checkpoint_count") if isinstance(legibility_scorecard_lens.get("scorecard"), dict) else ""))}</span></div>
          <div class="node"><strong>Reader questions</strong><span>{html.escape(_safe_text(len(legibility_questions)))}</span></div>
          <div class="node"><strong>Time budget</strong><span>{html.escape(_safe_text((legibility_scorecard_lens.get("scorecard") or {}).get("time_budget_minutes") if isinstance(legibility_scorecard_lens.get("scorecard"), dict) else ""))} min</span></div>
        </div>
        <table>
          {row("Command", legibility_scorecard_lens.get("command") or "microcosm legibility-scorecard")}
          {row("Status", legibility_scorecard_lens.get("status"))}
          {row("Selected patterns", ", ".join([str(value) for value in legibility_scorecard_lens.get("selected_pattern_ids", [])]) if isinstance(legibility_scorecard_lens.get("selected_pattern_ids"), list) else "")}
          {row("Negative cases", ", ".join([str(value) for value in legibility_negative_cases]))}
          {row("Release authorized", legibility_scorecard_lens.get("release_authorized") is True)}
          {row("Reader-success guarantee", (legibility_scorecard_lens.get("authority_ceiling") or {}).get("reader_success_guarantee") is True if isinstance(legibility_scorecard_lens.get("authority_ceiling"), dict) else False)}
          {row("Private equivalence claim", (legibility_scorecard_lens.get("authority_ceiling") or {}).get("private_data_equivalence_claim") is True if isinstance(legibility_scorecard_lens.get("authority_ceiling"), dict) else False)}
        </table>
        <h3>Checkpoint rows</h3>
        <table>
          <thead><tr><th>Checkpoint</th><th>Reader question</th><th>Command</th><th>Pass condition</th></tr></thead>
          <tbody>{legibility_checkpoint_rows(legibility_checkpoints)}</tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>Resolved Pattern Bindings</h2>
      <div class="content">
        {binding_rows(pattern_bindings, "pattern_id")}
      </div>
    </section>

    <section>
      <h2>Standard Pressure</h2>
      <div class="content">
        {binding_rows(standard_bindings, "standard_id")}
      </div>
    </section>

    <section>
      <h2>Work Transaction</h2>
      <div class="content">
        <table>
          {row("Work id", work.get("work_id") or "not yet created")}
          {row("Status", work.get("status") or "not yet created")}
          {row("Route snapshot", work.get("route_id") or route_id)}
          {row("Transaction policy", work.get("transaction_policy"))}
          {row("State history", " -> ".join(state_history) if state_history else "not yet run")}
          {row("Event refs", ", ".join(event_ref_values))}
          {row("Evidence refs", ", ".join(evidence_ref_values))}
        </table>
      </div>
    </section>

    <section>
      <h2>Project Graph</h2>
      <div class="content">
        <table>
          {row("Nodes", graph.get("node_count"))}
          {row("Edges", graph.get("edge_count"))}
          {row("Graph ref", graph.get("graph_ref"))}
        </table>
        <h3>Key relations</h3>
        {_badge_list([str(value) for value in graph.get("key_relations", [])])}
      </div>
    </section>

    <section class="wide">
      <h2>Events and Evidence</h2>
      <div class="content">
        <h3>Event stream</h3>
        <table>
          <thead><tr><th>Event id</th><th>Span</th><th>Status</th><th>Evidence ref</th></tr></thead>
          <tbody>{event_rows(events)}</tbody>
        </table>
        <h3>Evidence drilldowns</h3>
        <table>
          <thead><tr><th>Evidence ref</th><th>Status</th><th>Replacement policy</th></tr></thead>
          <tbody>{evidence_rows(evidence)}</tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>Kernel and Standards</h2>
      <div class="content">
        <table>
          {row("Pattern surface", kernel.get("pattern_surface_id"))}
          {row("Standard pressure", kernel.get("standard_pressure_surface_id"))}
          {row("Primitives", ", ".join([str(value) for value in kernel.get("primitive_names", [])]))}
        </table>
      </div>
    </section>

    <section>
      <h2>JSON Drilldowns</h2>
      <div class="content">
        <p class="muted">The endpoints remain stable for inspection, tests, and automation.</p>
        <ul>{endpoint_items}</ul>
        <details>
          <summary>Raw observatory model</summary>
          <pre>{dump(model)}</pre>
        </details>
      </div>
    </section>
  </main>
</body>
</html>
"""

    def serve(self, host: str, port: int, project: str | Path | None = None) -> ThreadingHTTPServer:
        shell = self
        project_path = Path(project).expanduser().resolve(strict=False) if project is not None else None

        class Handler(BaseHTTPRequestHandler):
            def _send(self, status_code: int, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
                encoded = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def _send_html(self, status_code: int, body: str) -> None:
                encoded = body.encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def _send_empty(self, status_code: int) -> None:
                self.send_response(status_code)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, format: str, *args: Any) -> None:
                return

            def do_GET(self) -> None:
                path = urlparse(self.path).path
                if path == "/favicon.ico":
                    self._send_empty(204)
                elif path == "/":
                    self._send_html(200, shell._observatory_html(project_path))
                elif path == "/status":
                    self._send(200, shell.status())
                elif path == "/spine":
                    self._send(200, shell.spine())
                elif path == "/tour":
                    self._send(200, shell.tour(project_path if project_path is not None else DEFAULT_PROJECT_REL))
                elif path == "/authority":
                    self._send(200, shell.authority())
                elif path == "/prediction":
                    self._send(200, shell.prediction_lens())
                elif path == "/market-boundary":
                    self._send(200, shell.market_boundary())
                elif path == "/corpus":
                    self._send(200, shell.corpus_lens())
                elif path == "/trace":
                    self._send(200, shell.trace_lens())
                elif path == "/repair-loop":
                    self._send(200, shell.repair_loop())
                elif path == "/evidence-cells":
                    self._send(200, shell.evidence_cells())
                elif path == "/proof-loop-depth":
                    self._send(200, shell.proof_loop_depth())
                elif path == "/landing-replay":
                    self._send(200, shell.landing_replay())
                elif path == "/view-quality":
                    self._send(200, shell.view_quality())
                elif path == "/projection-safety":
                    self._send(200, shell.projection_safety())
                elif path == "/drift-control":
                    self._send(200, shell.projection_drift())
                elif path == "/spatial-simulation":
                    self._send(200, shell.spatial_simulation())
                elif path == "/circuit-attribution":
                    self._send(200, shell.circuit_attribution())
                elif path == "/route-cleanup":
                    self._send(200, shell.route_cleanup())
                elif path == "/projection-import-map":
                    self._send(200, shell.projection_import_map())
                elif path == "/import-projector":
                    self._send(200, shell.import_projector())
                elif path == "/option-surface-lens":
                    self._send(200, shell.option_surface_lens())
                elif path == "/stripping-guard":
                    self._send(200, shell.stripping_guard())
                elif path == "/standards-control":
                    self._send(200, shell.standards_control())
                elif path == "/hook-coverage":
                    self._send(200, shell.hook_coverage())
                elif path == "/replay-gauntlet":
                    self._send(200, shell.replay_gauntlet())
                elif path == "/benchmark-lab":
                    self._send(200, shell.benchmark_lab())
                elif path == "/legibility-scorecard":
                    self._send(200, shell.legibility_scorecard())
                elif path == "/intake":
                    self._send(200, shell.intake())
                elif path == "/reveal":
                    self._send(200, shell.reveal())
                elif path == "/kernel":
                    self._send(
                        200,
                        {
                            **architecture_kernel.load_kernel_manifest(shell.root),
                            "standard_pressure_surface": architecture_kernel.load_standard_pressure_surface(shell.root),
                        },
                    )
                elif path == "/project/status" and project_path is not None:
                    self._send(200, project_substrate.observe_project(project_path))
                elif path == "/project/architecture" and project_path is not None:
                    self._send(200, project_substrate.architecture_project(project_path))
                elif path == "/project/graph" and project_path is not None:
                    self._send(200, project_substrate.state_graph(project_path))
                elif path == "/project/catalog" and project_path is not None:
                    self._send(200, project_substrate.catalog_project(project_path))
                elif path == "/project/python-lens" and project_path is not None:
                    self._send(200, project_substrate.python_lens(project_path))
                elif path == "/project/patterns" and project_path is not None:
                    self._send(200, project_substrate.discover_patterns(project_path))
                elif path == "/project/routes" and project_path is not None:
                    self._send(200, project_substrate.propose_routes(project_path))
                elif path == "/project/workitems" and project_path is not None:
                    self._send(
                        200,
                        {
                            "schema_version": "microcosm_project_workitems_view_v1",
                            "status": PASS,
                            "work_items": project_substrate._load_work_items(project_path),
                        },
                    )
                elif path == "/project/evidence" and project_path is not None:
                    self._send(200, project_substrate.list_evidence(project_path))
                elif path == "/project/observatory" and project_path is not None:
                    self._send(200, shell.project_observatory(project_path))
                elif path.startswith("/project/explain/") and project_path is not None:
                    self._send(200, project_substrate.explain_route(project_path, unquote(path.removeprefix("/project/explain/"))))
                elif path == "/organs":
                    self._send(200, {"schema_version": "microcosm_runtime_organs_v1", "organs": shell.organs()})
                elif path == "/patterns":
                    self._send(200, {"schema_version": "microcosm_runtime_patterns_v1", "patterns": shell.patterns()})
                elif path == "/routes":
                    self._send(200, {"schema_version": "microcosm_runtime_routes_v1", "routes": shell.routes()})
                elif path == "/workitems":
                    self._send(200, {"schema_version": "microcosm_runtime_workitems_v1", "workitems": shell.workitems()})
                elif path == "/evidence":
                    self._send(200, {"schema_version": "microcosm_runtime_evidence_v1", "evidence": shell.evidence()})
                elif path.startswith("/route/"):
                    self._send(200, shell.inspect_route(unquote(path.removeprefix("/route/"))))
                else:
                    self._send(404, {"status": "not_found", "path": path})

            def do_POST(self) -> None:
                path = urlparse(self.path).path
                if path == "/demo/run":
                    self._send(200, shell.run_demo())
                    return
                if path == "/project/work/run" and project_path is not None:
                    self._send(200, project_substrate.run_work(project_path))
                    return
                self._send(404, {"status": "not_found", "path": path})

        return ThreadingHTTPServer((host, port), Handler)


def _print_json(payload: Any) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if not isinstance(payload, dict) or payload.get("status") in {None, PASS} else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="microcosm-runtime")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("status")
    subparsers.add_parser("spine")
    tour_parser = subparsers.add_parser("tour")
    tour_parser.add_argument("project", nargs="?", default=DEFAULT_PROJECT_REL)
    subparsers.add_parser("authority")
    subparsers.add_parser("prediction-lens")
    subparsers.add_parser("market-boundary")
    subparsers.add_parser("corpus-lens")
    subparsers.add_parser("trace-lens")
    subparsers.add_parser("repair-loop")
    subparsers.add_parser("evidence-cells")
    subparsers.add_parser("proof-loop-depth")
    subparsers.add_parser("landing-replay")
    subparsers.add_parser("view-quality")
    subparsers.add_parser("projection-safety")
    subparsers.add_parser("drift-control")
    subparsers.add_parser("spatial-simulation")
    subparsers.add_parser("circuit-attribution")
    subparsers.add_parser("route-cleanup")
    subparsers.add_parser("projection-import-map")
    subparsers.add_parser("import-projector")
    subparsers.add_parser("option-surface-lens")
    subparsers.add_parser("stripping-guard")
    subparsers.add_parser("standards-control")
    subparsers.add_parser("hook-coverage")
    subparsers.add_parser("replay-gauntlet")
    subparsers.add_parser("benchmark-lab")
    subparsers.add_parser("legibility-scorecard")
    subparsers.add_parser("intake")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("project", nargs="?", default=DEFAULT_PROJECT_REL)
    subparsers.add_parser("reveal")
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("project", nargs="?")
    subparsers.add_parser("patterns")
    subparsers.add_parser("kernel")
    route_parser = subparsers.add_parser("route")
    route_sub = route_parser.add_subparsers(dest="route_command")
    route_sub.add_parser("list")
    inspect_route = route_sub.add_parser("inspect")
    inspect_route.add_argument("route_id")
    work_parser = subparsers.add_parser("work")
    work_sub = work_parser.add_subparsers(dest="work_command")
    work_sub.add_parser("demo")
    evidence_parser = subparsers.add_parser("evidence")
    evidence_sub = evidence_parser.add_subparsers(dest="evidence_command")
    evidence_sub.add_parser("list")
    inspect_evidence = evidence_sub.add_parser("inspect")
    inspect_evidence.add_argument("receipt_ref")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    shell = RuntimeShell()

    if args.command == "status":
        return _print_json(shell.status())
    if args.command == "spine":
        return _print_json(shell.spine())
    if args.command == "tour":
        return _print_json(shell.tour(args.project))
    if args.command == "authority":
        return _print_json(shell.authority())
    if args.command == "prediction-lens":
        return _print_json(shell.prediction_lens())
    if args.command == "market-boundary":
        return _print_json(shell.market_boundary())
    if args.command == "corpus-lens":
        return _print_json(shell.corpus_lens())
    if args.command == "trace-lens":
        return _print_json(shell.trace_lens())
    if args.command == "repair-loop":
        return _print_json(shell.repair_loop())
    if args.command == "evidence-cells":
        return _print_json(shell.evidence_cells())
    if args.command == "proof-loop-depth":
        return _print_json(shell.proof_loop_depth())
    if args.command == "landing-replay":
        return _print_json(shell.landing_replay())
    if args.command == "view-quality":
        return _print_json(shell.view_quality())
    if args.command == "projection-safety":
        return _print_json(shell.projection_safety())
    if args.command == "drift-control":
        return _print_json(shell.projection_drift())
    if args.command == "spatial-simulation":
        return _print_json(shell.spatial_simulation())
    if args.command == "circuit-attribution":
        return _print_json(shell.circuit_attribution())
    if args.command == "route-cleanup":
        return _print_json(shell.route_cleanup())
    if args.command == "projection-import-map":
        return _print_json(shell.projection_import_map())
    if args.command == "import-projector":
        return _print_json(shell.import_projector())
    if args.command == "option-surface-lens":
        return _print_json(shell.option_surface_lens())
    if args.command == "stripping-guard":
        return _print_json(shell.stripping_guard())
    if args.command == "standards-control":
        return _print_json(shell.standards_control())
    if args.command == "hook-coverage":
        return _print_json(shell.hook_coverage())
    if args.command == "replay-gauntlet":
        return _print_json(shell.replay_gauntlet())
    if args.command == "benchmark-lab":
        return _print_json(shell.benchmark_lab())
    if args.command == "legibility-scorecard":
        return _print_json(shell.legibility_scorecard())
    if args.command == "intake":
        return _print_json(shell.intake())
    if args.command == "run":
        return _print_json(shell.run_demo(args.project))
    if args.command == "reveal":
        return _print_json(shell.reveal())
    if args.command == "patterns":
        return _print_json({"schema_version": "microcosm_runtime_patterns_v1", "patterns": shell.patterns()})
    if args.command == "kernel":
        return _print_json(
            {
                **architecture_kernel.load_kernel_manifest(shell.root),
                "standard_pressure_surface": architecture_kernel.load_standard_pressure_surface(shell.root),
            }
        )
    if args.command == "route":
        if args.route_command == "list":
            return _print_json({"schema_version": "microcosm_runtime_routes_v1", "routes": shell.routes()})
        if args.route_command == "inspect":
            return _print_json(shell.inspect_route(args.route_id))
    if args.command == "work":
        if args.work_command == "demo":
            return _print_json(shell.run_work_demo())
    if args.command == "evidence":
        if args.evidence_command == "list":
            return _print_json({"schema_version": "microcosm_runtime_evidence_v1", "evidence": shell.evidence()})
        if args.evidence_command == "inspect":
            return _print_json(shell.inspect_evidence(args.receipt_ref))
    if args.command == "serve":
        server = shell.serve(args.host, args.port, args.project)
        print(f"microcosm runtime shell listening on http://{args.host}:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return 130
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
