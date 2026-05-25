from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from microcosm_core.public_payload_boundary import public_payload_boundary
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.public_entry_docs"
FIXTURE_ID = "first_wave.public_entry_docs"
REQUIRED_DOCS = [
    "README.md",
    "AGENTS.md",
    "atlas/entry_packet.json",
    "paper_modules/pattern_binding_contract.md",
    "paper_modules/executable_doctrine_grammar.md",
    "paper_modules/proof_diagnostic_evidence_spine.md",
    "paper_modules/formal_math_readiness_gate.md",
    "paper_modules/corpus_readiness_mathlib_absence.md",
    "paper_modules/mathematical_strategy_atlas.md",
    "paper_modules/tactic_portfolio_availability.md",
    "paper_modules/target_shape_tactic_routing.md",
    "paper_modules/formal_math_premise_retrieval.md",
    "paper_modules/formal_math_verifier_trace_repair_loop.md",
    "paper_modules/formal_evidence_cell_anchor_resolver.md",
    "paper_modules/undeclared_library_prior_classifier.md",
    "paper_modules/lean_std_premise_index.md",
    "paper_modules/ring2_premise_precision_recall.md",
    "paper_modules/agent_benchmark_integrity_anti_gaming_replay.md",
    "paper_modules/durable_agent_work_landing_replay.md",
    "paper_modules/research_replication_rubric_artifact_replay.md",
    "paper_modules/world_model_projection_drift_control_room.md",
    "paper_modules/spatial_world_model_counterfactual_simulation_replay.md",
    "paper_modules/materials_chemistry_closed_loop_lab_safety_replay.md",
    "paper_modules/mechanistic_interpretability_circuit_attribution_replay.md",
    "paper_modules/provider_context_recipe_budget.md",
    "paper_modules/public_reveal_walkthrough.md",
    "paper_modules/macro_projection_import_protocol.md",
    "paper_modules/formal_math_lean_proof_witness.md",
    "paper_modules/verifier_lab_kernel.md",
    "paper_modules/prediction_oracle_reconciliation.md",
    "paper_modules/standards_meta_diagnostics.md",
    "paper_modules/cold_reader_route_map.md",
    "paper_modules/agent_monitor_redteam_falsification_replay.md",
    "paper_modules/agent_sabotage_scheming_monitor_replay.md",
    "paper_modules/agent_memory_temporal_conflict_replay.md",
    "paper_modules/sleeper_memory_poisoning_quarantine_replay.md",
    "paper_modules/mcp_tool_authority_replay.md",
    "paper_modules/proof_derived_governed_mutation_authorization.md",
    "paper_modules/belief_state_process_reward_replay.md",
    "paper_modules/agent_sandbox_policy_escape_replay.md",
    "paper_modules/indirect_prompt_injection_information_flow_policy_replay.md",
    "paper_modules/agentic_vulnerability_discovery_patch_proof_replay.md",
    "paper_modules/voice_to_doctrine_self_improvement_loop.md",
    "paper_modules/cold_clone_probe.md",
    "skills/cold_start_navigation.md",
]
ACCEPTED_ORGAN_IDS = [
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
    "materials_chemistry_closed_loop_lab_safety_replay",
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
    "certificate_kernel_execution_lab",
    "voice_to_doctrine_self_improvement_loop",
]
REQUIRED_PHRASES_BY_DOC = {
    "README.md": [
        "repo -> .microcosm",
        "Real Substrate Posture",
        "Microcosm is the public repo form of the macro system",
        "not a synthetic safety proxy",
        "Public should carry private by default",
        "as much of the macro substrate as possible",
        "Synthetic fixtures are allowed only as regression wrappers",
        "The exclusion set is narrow",
        "raw operator voice, slurs or abusive wording",
        "is not a reason to ship a fake stand-in",
        "Any `body_copied=true` claim must name the source file",
        "microcosm compile .",
        "std_python_microcosm_navigation_assay",
        "implementation_atlas.python_navigation_assay",
        "executable research prototype",
        "local project operating substrate",
        ".microcosm/",
        "Architecture Kernel",
        "microcosm explain <project> <route_id>",
        "Evidence receipts are the black-box recorder",
        "`accepted_current_authority` is not an evidence-strength claim",
        "evidence_class",
        "Internal Runtime Spine",
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
        "durable_agent_work_landing_replay",
        "research_replication_rubric_artifact_replay",
        "world_model_projection_drift_control_room",
        "spatial_world_model_counterfactual_simulation_replay",
        "materials_chemistry_closed_loop_lab_safety_replay",
        "mechanistic_interpretability_circuit_attribution_replay",
        "provider_context_recipe_budget_policy",
        "formal_math_lean_proof_witness",
        "verifier_lab_kernel",
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
        "sleeper_memory_poisoning_quarantine_replay",
        "mcp_tool_authority_replay",
        "proof_derived_governed_mutation_authorization",
        "belief_state_process_reward_replay",
        "agent_sandbox_policy_escape_replay",
        "indirect_prompt_injection_information_flow_policy_replay",
        "agentic_vulnerability_discovery_patch_proof_replay",
        "formal-math-lean-proof-witness",
        "corpus-readiness-mathlib-absence-gate",
        "mathematical-strategy-atlas-hypothesis-scorer",
        "tactic-portfolio-availability-probe",
        "target-shape-tactic-routing-gate",
        "lean-std-premise-index",
        "formal-math-premise-retrieval",
        "formal-math-verifier-trace-repair-loop",
        "formal-evidence-cell-anchor-resolver",
        "undeclared-library-prior-symbol-classifier",
        "ring2-premise-retrieval-precision-recall-harness",
        "agent-benchmark-integrity-anti-gaming-replay",
        "durable-agent-work-landing-replay",
        "research-replication-rubric-artifact-replay",
        "world-model-projection-drift-control-room",
        "spatial-world-model-counterfactual-simulation-replay",
        "materials-chemistry-closed-loop-lab-safety-replay",
        "mechanistic-interpretability-circuit-attribution-replay",
        "provider-context-recipe-budget-policy",
        "verifier-lab-kernel",
        "microcosm reveal",
        "macro-projection-import-protocol",
        "prediction-oracle-reconciliation",
        "standards-meta-diagnostics",
        "cold-reader-route-map",
        "agent-monitor-redteam-falsification-replay",
        "agent-sabotage-scheming-monitor-replay",
        "agent-memory-temporal-conflict-replay",
        "sleeper-memory-poisoning-quarantine-replay",
        "mcp-tool-authority-replay",
        "proof-derived-governed-mutation-authorization",
        "belief-state-process-reward-replay",
        "agent-sandbox-policy-escape-replay",
        "indirect-prompt-injection-information-flow-policy-replay",
        "agentic-vulnerability-discovery-patch-proof-replay",
        "sleeper-memory-poisoning-quarantine-replay",
        "mcp-tool-authority-replay",
        "proof-derived-governed-mutation-authorization",
        "belief-state-process-reward-replay",
        "agent-sandbox-policy-escape-replay",
        "indirect-prompt-injection-information-flow-policy-replay",
        "agentic-vulnerability-discovery-patch-proof-replay",
        "not trading or financial advice",
        "not authorize release",
    ],
    "AGENTS.md": [
        "microcosm compile <project>",
        "repo -> `.microcosm`",
        "Real Substrate Posture",
        "Microcosm is the public repo form of the macro system",
        "not a synthetic safety proxy",
        "Public should carry private by default",
        "as much of the macro substrate as possible",
        "Use synthetic fixtures only as regression wrappers",
        "The hard exclusion set is narrow",
        "raw operator voice, slurs or abusive wording",
        "Do not turn \"private state\" or \"release authority\" into a generic excuse",
        "Any `body_copied=true` claim must point at a real target file",
        "executable research prototype",
        "local project operating substrate",
        "microcosm init <project>",
        "microcosm explain <project> <route_id>",
        "Accepted Public Runtime Spine",
        "`accepted_current_authority` is not an evidence-strength claim",
        "evidence_class",
        "Do not widen Lean/Lake",
        "formal_math_lean_proof_witness",
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
        "durable_agent_work_landing_replay",
        "research_replication_rubric_artifact_replay",
        "world_model_projection_drift_control_room",
        "spatial_world_model_counterfactual_simulation_replay",
        "materials_chemistry_closed_loop_lab_safety_replay",
        "mechanistic_interpretability_circuit_attribution_replay",
        "provider_context_recipe_budget_policy",
        "verifier_lab_kernel",
        "Fixtures Are Tests",
        "Receipts Are Evidence",
        "public_reveal_walkthrough",
        "macro_projection_import_protocol",
        "prediction_oracle_reconciliation",
        "standards_meta_diagnostics",
        "cold_reader_route_map",
        "agent_monitor_redteam_falsification_replay",
        "agent_sabotage_scheming_monitor_replay",
        "agent_memory_temporal_conflict_replay",
        "mcp_tool_authority_replay",
        "proof_derived_governed_mutation_authorization",
        "belief_state_process_reward_replay",
        "agent_sandbox_policy_escape_replay",
        "indirect_prompt_injection_information_flow_policy_replay",
        "agentic_vulnerability_discovery_patch_proof_replay",
        "formal-math-lean-proof-witness",
        "corpus-readiness-mathlib-absence-gate",
        "mathematical-strategy-atlas-hypothesis-scorer",
        "tactic-portfolio-availability-probe",
        "target-shape-tactic-routing-gate",
        "lean-std-premise-index",
        "formal-math-premise-retrieval",
        "formal-math-verifier-trace-repair-loop",
        "formal-evidence-cell-anchor-resolver",
        "undeclared-library-prior-symbol-classifier",
        "ring2-premise-retrieval-precision-recall-harness",
        "agent-benchmark-integrity-anti-gaming-replay",
        "durable-agent-work-landing-replay",
        "research-replication-rubric-artifact-replay",
        "world-model-projection-drift-control-room",
        "spatial-world-model-counterfactual-simulation-replay",
        "materials-chemistry-closed-loop-lab-safety-replay",
        "mechanistic-interpretability-circuit-attribution-replay",
        "provider-context-recipe-budget-policy",
        "verifier-lab-kernel",
        "microcosm reveal",
        "macro-projection-import-protocol",
        "prediction-oracle-reconciliation",
        "standards-meta-diagnostics",
        "cold-reader-route-map",
        "agent-monitor-redteam-falsification-replay",
        "agent-sabotage-scheming-monitor-replay",
        "agent-memory-temporal-conflict-replay",
        "mcp-tool-authority-replay",
        "proof-derived-governed-mutation-authorization",
        "belief-state-process-reward-replay",
        "agent-sandbox-policy-escape-replay",
        "indirect-prompt-injection-information-flow-policy-replay",
        "agentic-vulnerability-discovery-patch-proof-replay",
        "Do not treat prediction fixtures as trading or financial advice",
    ],
    "skills/cold_start_navigation.md": [
        "First-Screen Route Contract",
        "Bring a folder first",
        "atlas/entry_packet.json::local_first_screen_route",
        "microcosm tour <project>",
        "microcosm status --card <project>",
        "front_door.route_explanation",
        "microcosm workingness",
        "microcosm serve <project> --host 127.0.0.1 --port 8765",
        "Receipts are evidence drilldowns after the behavior route is visible",
        "evidence_class",
        "`accepted_current_authority` is not an evidence-strength claim",
        "std_python_microcosm_navigation_assay",
        "implementation_atlas.python_navigation_assay",
    ],
}
FORBIDDEN_PHRASES_BY_DOC = {
    "README.md": [
        "runnable, synthetic, and receipt-driven",
        "private reconstruction control plane",
        "public synthetic microcosm",
        "public-safe ten-minute path",
        "public-safe authority ceiling",
    ],
    "AGENTS.md": [
        "source reconstruction workspace",
        "Use only synthetic fixtures",
        "Receipts Are Authority",
        "macro reconstruction contracts",
        "only to project\n   metadata",
        "only to project metadata",
        "public-safe route",
    ],
}


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key, [])
    return [row for row in rows if isinstance(row, dict)]


def _receipt_safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan)
    safe.pop("forbidden_output_fields", None)
    return safe


def _normalized_text(text: str) -> str:
    return " ".join(text.split())


def _accepted_organs(public_root: Path) -> list[str]:
    registry = read_json_strict(public_root / "core/organ_registry.json")
    return [
        str(row.get("organ_id"))
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicated: set[str] = set()
    for value in values:
        if value in seen:
            duplicated.add(value)
        seen.add(value)
    return sorted(duplicated)


def _ordered_code_list_after_heading(text: str, heading: str) -> list[str]:
    if heading not in text:
        return []
    rows: list[str] = []
    started = False
    for line in text.split(heading, 1)[1].splitlines():
        stripped = line.strip()
        if started and stripped.startswith("## "):
            break
        if stripped and stripped[0].isdigit() and ". `" in stripped and "`" in stripped:
            parts = stripped.split("`")
            if len(parts) >= 3:
                rows.append(parts[1])
                started = True
                continue
        if started and stripped and not stripped[0].isdigit():
            break
    return rows


def _bullet_code_list_between(text: str, start_heading: str, end_heading: str) -> list[str]:
    if start_heading not in text:
        return []
    section = text.split(start_heading, 1)[1]
    if end_heading in section:
        section = section.split(end_heading, 1)[0]
    rows: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- `") and stripped.endswith("`"):
            rows.append(stripped[3:-1])
    return rows


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _entry_packet_route_contract(
    public_root: Path,
    doc_text_by_rel: dict[str, str],
) -> dict[str, Any]:
    path = public_root / "atlas/entry_packet.json"
    required_commands = [
        "microcosm tour <project>",
        "microcosm compile <project>",
        "microcosm python-lens <project>",
        "microcosm explain <project> <selected_route_id>",
        "microcosm evidence list <project>",
        "microcosm status --card <project>",
        "microcosm workingness",
        "microcosm proof-lab --out /tmp/microcosm-proof-lab",
        "microcosm serve <project> --host 127.0.0.1 --port 8765",
    ]
    required_state_refs = [
        ".microcosm/catalog.json",
        ".microcosm/routes.json",
        ".microcosm/work_items.json",
        ".microcosm/events.jsonl",
        ".microcosm/evidence/",
        ".microcosm/graph.json",
        ".microcosm/python_lens.json",
    ]
    required_observatory_endpoints = [
        "/",
        "/status",
        "/tour",
        "/workingness",
        "/proof-lab",
        "/project/python-lens",
        "/project/explain/<selected_route_id>",
    ]
    required_drilldown_routes = [
        "tour_front_door_status_route",
        "status_and_workingness_route",
        "python_navigation_route",
        "route_explanation_chain_route",
        "proof_lab_route",
    ]
    required_allowed_refs = [
        "atlas/entry_packet.json::local_first_screen_route",
        "atlas/entry_packet.json::cold_clone_probe_route",
        "microcosm status --card <project>::front_door.route_explanation",
        "microcosm status --card <project>::front_door.source_open_body_import_floor",
        "microcosm status --card <project>::macro_body_import_floor",
        "/workingness",
    ]
    if not path.is_file():
        return {
            "status": "missing",
            "source_ref": "atlas/entry_packet.json",
            "blocking_reasons": ["missing_entry_packet"],
            "authority": (
                "entry-packet route parity only; not source, release, provider, "
                "proof, or mutation authority"
            ),
        }
    try:
        payload = read_json_strict(path)
    except Exception as exc:
        return {
            "status": "blocked",
            "source_ref": "atlas/entry_packet.json",
            "blocking_reasons": ["invalid_entry_packet_json"],
            "parse_error": type(exc).__name__,
            "authority": (
                "entry-packet route parity only; not source, release, provider, "
                "proof, or mutation authority"
            ),
        }
    if not isinstance(payload, dict):
        payload = {}
    route = payload.get("local_first_screen_route")
    route = route if isinstance(route, dict) else {}
    safe_to_show = route.get("safe_to_show")
    safe_to_show = safe_to_show if isinstance(safe_to_show, dict) else {}
    command_path = _string_list(route.get("command_path"))
    state_refs = _string_list(route.get("state_refs"))
    observatory_endpoints = _string_list(route.get("observatory_endpoints"))
    drilldown_routes = _string_list(route.get("drilldown_routes"))
    allowed_drilldowns = _string_list(payload.get("allowed_drilldowns"))
    missing_commands = [
        command for command in required_commands if command not in command_path
    ]
    missing_state_refs = [ref for ref in required_state_refs if ref not in state_refs]
    missing_endpoints = [
        endpoint
        for endpoint in required_observatory_endpoints
        if endpoint not in observatory_endpoints
    ]
    missing_drilldown_routes = [
        route_id for route_id in required_drilldown_routes if route_id not in drilldown_routes
    ]
    missing_allowed_drilldowns = [
        ref
        for ref in (
            required_allowed_refs
            + required_commands
            + required_state_refs
            + required_observatory_endpoints
        )
        if ref not in allowed_drilldowns
    ]
    first_command = str(payload.get("first_command") or "")
    primary_command = str(route.get("primary_first_screen_command") or "")
    command_mismatch = []
    if first_command != "microcosm tour <project>":
        command_mismatch.append("first_command")
    if primary_command != first_command:
        command_mismatch.append("primary_first_screen_command")
    route_selection_rule = str(route.get("route_selection_rule") or "")
    missing_route_selection_rule = (
        "readme_onboarding_route is a generated route only" not in route_selection_rule
    )
    unsafe_flags = [
        key
        for key in [
            "source_files_mutated",
            "provider_calls_authorized",
            "release_authorized",
            "proof_correctness_claim",
        ]
        if safe_to_show.get(key) is not False
    ]
    cold_start_text = _normalized_text(
        doc_text_by_rel.get("skills/cold_start_navigation.md", "")
    )
    cold_start_missing = [
        phrase
        for phrase in (
            required_commands
            + [
                "atlas/entry_packet.json::local_first_screen_route",
                "atlas/entry_packet.json::cold_clone_probe_route",
                "atlas/entry_packet.json::status_and_workingness_route",
                "atlas/entry_packet.json::proof_lab_route",
                "front_door.source_open_body_import_floor",
                "Receipts are evidence drilldowns after the behavior route is visible",
            ]
        )
        if phrase not in cold_start_text
    ]
    blocking_reasons: list[str] = []
    if missing_commands:
        blocking_reasons.append("missing_local_first_screen_commands")
    if missing_state_refs:
        blocking_reasons.append("missing_state_refs")
    if missing_endpoints:
        blocking_reasons.append("missing_observatory_endpoints")
    if missing_drilldown_routes:
        blocking_reasons.append("missing_drilldown_routes")
    if missing_allowed_drilldowns:
        blocking_reasons.append("missing_allowed_drilldowns")
    if command_mismatch:
        blocking_reasons.append("first_command_mismatch")
    if missing_route_selection_rule:
        blocking_reasons.append("missing_route_selection_rule")
    if unsafe_flags:
        blocking_reasons.append("unsafe_safe_to_show_flags")
    if cold_start_missing:
        blocking_reasons.append("cold_start_route_contract_missing")
    return {
        "status": PASS if not blocking_reasons else "blocked",
        "source_ref": "atlas/entry_packet.json",
        "first_command": first_command,
        "primary_first_screen_command": primary_command,
        "missing_local_first_screen_commands": missing_commands,
        "missing_state_refs": missing_state_refs,
        "missing_observatory_endpoints": missing_endpoints,
        "missing_drilldown_routes": missing_drilldown_routes,
        "missing_allowed_drilldowns": missing_allowed_drilldowns,
        "command_mismatch": command_mismatch,
        "missing_route_selection_rule": missing_route_selection_rule,
        "unsafe_safe_to_show_flags": unsafe_flags,
        "cold_start_missing_phrases": cold_start_missing,
        "blocking_reasons": blocking_reasons,
        "authority": (
            "entry-packet route parity only; not source, release, provider, "
            "proof, or mutation authority"
        ),
    }


def _entry_spine_claims(public_root: Path, expected_organs: list[str]) -> dict[str, Any]:
    expected_set = set(expected_organs)
    docs: dict[str, dict[str, Any]] = {}
    doc_specs = {
        "README.md": (
            _ordered_code_list_after_heading,
            ("## Internal Runtime Spine",),
        ),
        "AGENTS.md": (
            _bullet_code_list_between,
            ("## Accepted Public Runtime Spine", "## Rules"),
        ),
    }
    for rel, (extractor, args) in doc_specs.items():
        path = public_root / rel
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        claimed = extractor(text, *args)
        claimed_set = set(claimed)
        missing = [organ_id for organ_id in expected_organs if organ_id not in claimed_set]
        unexpected = sorted(organ_id for organ_id in claimed if organ_id not in expected_set)
        duplicates = _duplicates(claimed)
        docs[rel] = {
            "claimed_count": len(claimed),
            "expected_count": len(expected_organs),
            "missing_organs": missing,
            "unexpected_organs": unexpected,
            "duplicate_organs": duplicates,
            "status": PASS
            if not missing and not unexpected and not duplicates
            else "blocked",
        }
    blocked_docs = [rel for rel, row in docs.items() if row["status"] != PASS]
    return {
        "status": PASS if not blocked_docs else "blocked",
        "expected_source": "core/organ_registry.json::implemented_organs[status=accepted_current_authority]",
        "expected_organ_count": len(expected_organs),
        "docs": docs,
        "blocked_docs": blocked_docs,
        "authority": (
            "public entry spine claim alignment only; status card remains the "
            "runtime count lens"
        ),
    }


def _evidence_class_registry_summary(public_root: Path) -> dict[str, Any]:
    path = public_root / "core/organ_evidence_classes.json"
    if not path.is_file():
        return {
            "status": "missing",
            "source_ref": "core/organ_evidence_classes.json",
            "class_count": 0,
            "organ_count": 0,
            "missing_organs": ACCEPTED_ORGAN_IDS,
            "unexpected_organs": [],
            "duplicate_organs": [],
            "fail_closed_no_default": False,
        }
    payload = read_json_strict(path)
    rows = _rows(payload if isinstance(payload, dict) else {}, "organ_evidence_classes")
    seen: set[str] = set()
    duplicates: set[str] = set()
    class_ids: set[str] = set()
    for row in rows:
        organ_id = str(row.get("organ_id") or "")
        evidence_class = str(row.get("evidence_class") or "")
        if organ_id in seen:
            duplicates.add(organ_id)
        if organ_id:
            seen.add(organ_id)
        if evidence_class:
            class_ids.add(evidence_class)
    missing = [organ_id for organ_id in ACCEPTED_ORGAN_IDS if organ_id not in seen]
    unexpected = sorted(organ_id for organ_id in seen if organ_id not in ACCEPTED_ORGAN_IDS)
    fail_closed = isinstance(payload, dict) and payload.get("fail_closed_no_default") is True
    return {
        "status": "pass" if not missing and not unexpected and not duplicates and fail_closed else "blocked",
        "source_ref": "core/organ_evidence_classes.json",
        "class_count": len(class_ids),
        "organ_count": len(seen),
        "missing_organs": missing,
        "unexpected_organs": unexpected,
        "duplicate_organs": sorted(duplicates),
        "fail_closed_no_default": fail_closed,
    }


def validate_public_entry_docs(
    root: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    public_root = Path(root).resolve(strict=False)
    output_file = Path(out_path)
    missing_docs: list[str] = []
    missing_required_phrases_by_doc: dict[str, list[str]] = {}
    forbidden_phrases_by_doc: dict[str, list[str]] = {}
    stale_first_slice_only_phrases: list[str] = []
    doc_text_by_rel: dict[str, str] = {}
    doc_paths: list[Path] = []
    for rel in REQUIRED_DOCS:
        path = public_root / rel
        doc_paths.append(path)
        if not path.is_file():
            missing_docs.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        doc_text_by_rel[rel] = text
        normalized = _normalized_text(text)
        missing_phrases = [
            phrase
            for phrase in REQUIRED_PHRASES_BY_DOC.get(rel, [])
            if phrase not in normalized
        ]
        if missing_phrases:
            missing_required_phrases_by_doc[rel] = missing_phrases
        forbidden_phrases = [
            phrase for phrase in FORBIDDEN_PHRASES_BY_DOC.get(rel, []) if phrase in text
        ]
        if forbidden_phrases:
            forbidden_phrases_by_doc[rel] = forbidden_phrases
        if "only implemented\n   organ here is `pattern_binding_contract`" in text:
            stale_first_slice_only_phrases.append(rel)
        if "only implemented organ here is `pattern_binding_contract`" in text:
            stale_first_slice_only_phrases.append(rel)

    accepted = _accepted_organs(public_root)
    entry_spine_claims = _entry_spine_claims(public_root, accepted)
    entry_packet_route_contract = _entry_packet_route_contract(
        public_root,
        doc_text_by_rel,
    )
    missing_accepted_organs = [
        organ_id for organ_id in ACCEPTED_ORGAN_IDS if organ_id not in accepted
    ]
    unexpected_accepted_organs = [
        organ_id for organ_id in accepted if organ_id not in ACCEPTED_ORGAN_IDS
    ]
    evidence_class_registry = _evidence_class_registry_summary(public_root)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = _receipt_safe_scan(
        scan_paths(
            [public_root / rel for rel in REQUIRED_DOCS if (public_root / rel).is_file()],
            forbidden_classes=policy,
            display_root=public_root,
        )
    )
    blocking_codes: list[str] = []
    if missing_docs:
        blocking_codes.append("MISSING_PUBLIC_ENTRY_DOC")
    if missing_required_phrases_by_doc:
        blocking_codes.append("MISSING_REQUIRED_ENTRY_PHRASE")
    if stale_first_slice_only_phrases:
        blocking_codes.append("STALE_FIRST_SLICE_ONLY_ENTRY_TEXT")
    if forbidden_phrases_by_doc:
        blocking_codes.append("PUBLIC_ENTRY_DOC_ROUTE_DRIFT")
    if missing_accepted_organs or unexpected_accepted_organs:
        blocking_codes.append("ACCEPTED_ORGAN_REGISTRY_MISMATCH")
    if evidence_class_registry["status"] != PASS:
        blocking_codes.append("EVIDENCE_CLASS_REGISTRY_MISMATCH")
    if entry_spine_claims["status"] != PASS:
        blocking_codes.append("PUBLIC_ENTRY_SPINE_CLAIM_MISMATCH")
    if entry_packet_route_contract["status"] != PASS:
        blocking_codes.append("ENTRY_PACKET_ROUTE_CONTRACT_MISMATCH")
    if scan["blocking_hit_count"]:
        blocking_codes.append("SECRET_EXCLUSION_SCAN_BLOCKED")

    blocking_codes = sorted(set(blocking_codes))
    status = PASS if not blocking_codes else "blocked"
    receipt = {
        "schema_version": "public_entry_docs_validation_receipt_v2",
        "checker_id": CHECKER_ID,
        "fixture_id": FIXTURE_ID,
        "status": status,
        "command": command,
        "required_docs": REQUIRED_DOCS,
        "missing_docs": missing_docs,
        "missing_required_phrases_by_doc": missing_required_phrases_by_doc,
        "forbidden_phrases_by_doc": forbidden_phrases_by_doc,
        "stale_first_slice_only_phrases": sorted(set(stale_first_slice_only_phrases)),
        "accepted_current_authority_organs": accepted,
        "entry_spine_claims": entry_spine_claims,
        "entry_packet_route_contract": entry_packet_route_contract,
        "evidence_class_registry": evidence_class_registry,
        "missing_accepted_organs": missing_accepted_organs,
        "unexpected_accepted_organs": unexpected_accepted_organs,
        "deferred_organs": [],
        "blocking_codes": blocking_codes,
        "secret_exclusion_scan": scan,
        "payload_boundary": public_payload_boundary(
            boundary_id="public_entry_docs",
            command=command,
            surface_ref=_display(output_file, public_root=public_root),
        ),
        "authority_ceiling": {
            "status": PASS,
            "entry_docs_authority": "public_entry_navigation_and_real_substrate_posture",
            "lean_lake_authorized": "bounded_public_witness_only",
            "trading_or_financial_advice_authorized": False,
            "hosted_release_operations_authorized": False,
            "secret_export_authorized": False,
            "metadata_only_standin_policy": "forbidden_when_real_non_secret_macro_body_is_importable",
            "macro_substrate_import_policy": "encourage_maximum_non_secret_macro_substrate_import",
            "body_copied_requires_source_target_validation": True,
        },
        "anti_claim": "Public entry-doc validation proves standalone public entry documentation, cold-start navigation presence, and the real-substrate import posture: Microcosm should carry as much non-secret macro substrate as possible. It does not authorize Lean/Lake beyond the bounded public witness organ, hosted release operations, publication, recipient sends, credentialed provider calls, secret export, raw operator voice, slurs or abusive wording, private personal material, or whole-system correctness; it also does not allow metadata-only stand-ins when a real non-secret macro body can be imported.",
        "receipt_paths": [_display(output_file, public_root=public_root)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public entry docs")
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.public_entry_docs "
        f"--root {args.root} --out {args.out}"
    )
    receipt = validate_public_entry_docs(args.root, args.out, command=command)
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
