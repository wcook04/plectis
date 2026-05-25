from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.validators.public_entry_docs import validate_public_entry_docs


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent


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


def test_public_entry_docs_validate_source_open_payload_boundary(tmp_path: Path) -> None:
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
        "voice_to_doctrine_self_improvement_loop",
    ]
    assert receipt["evidence_class_registry"] == {
        "status": "pass",
        "source_ref": "core/organ_evidence_classes.json",
        "class_count": 5,
        "organ_count": 46,
        "missing_organs": [],
        "unexpected_organs": [],
        "duplicate_organs": [],
        "fail_closed_no_default": True,
    }
    assert receipt["entry_spine_claims"]["status"] == "pass"
    assert receipt["entry_spine_claims"]["expected_organ_count"] == 46
    assert receipt["entry_spine_claims"]["blocked_docs"] == []
    for rel in ("README.md", "AGENTS.md"):
        doc_claim = receipt["entry_spine_claims"]["docs"][rel]
        assert doc_claim["status"] == "pass"
        assert doc_claim["claimed_count"] == 46
        assert doc_claim["expected_count"] == 46
        assert doc_claim["missing_organs"] == []
        assert doc_claim["unexpected_organs"] == []
        assert doc_claim["duplicate_organs"] == []
    assert receipt["deferred_organs"] == []
    assert receipt["secret_exclusion_scan"]["body_in_receipt"] is False
    assert receipt["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert receipt["payload_boundary"]["source_open_default"] is True
    assert receipt["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert receipt["payload_boundary"]["metadata_only_standin_authorized"] is False
    assert receipt["authority_ceiling"]["entry_docs_authority"] == (
        "public_entry_navigation_and_real_substrate_posture"
    )
    assert receipt["authority_ceiling"]["secret_export_authorized"] is False
    assert (
        receipt["authority_ceiling"]["metadata_only_standin_policy"]
        == "forbidden_when_real_non_secret_macro_body_is_importable"
    )
    assert (
        receipt["authority_ceiling"]["macro_substrate_import_policy"]
        == "encourage_maximum_non_secret_macro_substrate_import"
    )
    assert receipt["authority_ceiling"]["body_copied_requires_source_target_validation"] is True
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


def test_public_entry_docs_block_runtime_spine_claim_mismatch(tmp_path: Path) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    agents = public_root / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8").replace(
            "- `certificate_kernel_execution_lab`\n",
            "",
        ),
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "PUBLIC_ENTRY_SPINE_CLAIM_MISMATCH" in receipt["blocking_codes"]
    assert receipt["entry_spine_claims"]["status"] == "blocked"
    assert receipt["entry_spine_claims"]["blocked_docs"] == ["AGENTS.md"]
    assert receipt["entry_spine_claims"]["docs"]["AGENTS.md"]["missing_organs"] == [
        "certificate_kernel_execution_lab"
    ]


def test_public_entry_readme_no_longer_claims_first_slice_only() -> None:
    text = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")
    agents = (MICROCOSM_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())
    normalized_agents = " ".join(agents.split())

    assert "Internal Runtime Spine" in text
    assert "Accepted Public Runtime Spine" in agents
    assert "Real Substrate Posture" in text
    assert "Real Substrate Posture" in agents
    assert "46 accepted public runtime organs" in text
    assert "46 accepted public runtime organ records" in agents
    assert "Microcosm is the public repo form of the macro system" in text
    assert "Microcosm is the public repo form of the macro system" in agents
    assert "not a synthetic safety proxy" in text
    assert "not a synthetic safety proxy" in agents
    assert "Public should carry private by default" in text
    assert "Public should carry private by default" in agents
    assert "as much of the macro substrate as possible" in normalized_text
    assert "as much of the macro substrate as possible" in normalized_agents
    assert "The exclusion set is narrow" in text
    assert "The hard exclusion set is narrow" in agents
    assert "raw operator voice, slurs or abusive wording" in normalized_text
    assert "raw operator voice, slurs or abusive wording" in normalized_agents
    assert "Any `body_copied=true` claim must name the source file" in text
    assert "Any `body_copied=true` claim must point at a real target file" in agents
    assert "public-safe ten-minute path" not in normalized_text
    assert "public-safe authority ceiling" not in normalized_text
    assert "public-safe route" not in normalized_agents
    assert "only to project metadata" not in normalized_agents
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
    assert "verifier_lab_execution_spine" in text
    assert "certificate_kernel_execution_lab" in text
    assert "voice_to_doctrine_self_improvement_loop" in text
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
    assert "verifier_lab_execution_spine" in agents
    assert "materials_chemistry_closed_loop_lab_safety_replay" in agents
    assert "certificate_kernel_execution_lab" in agents
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
    assert "route_utility_curriculum" in text
    assert "route_utility_curriculum.ratchet" in text
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
    assert "route_utility_curriculum" in cold_start
    assert "route_utility_curriculum.ratchet" in cold_start
    assert "proof-lab --out /tmp/microcosm-proof-lab" in cold_start
    assert "verifier-lab-kernel run-kernel-bundle" in cold_start
    assert "formal_prover_context_strategy_gate" in cold_start
    assert "atlas/entry_packet.json::proof_lab_route" in cold_start


def test_public_entry_packet_routes_python_navigation_assay() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    encoded_entry_packet = json.dumps(entry_packet, sort_keys=True)
    assert "body_redacted" not in encoded_entry_packet
    assert "public_first_slice" not in encoded_entry_packet
    assert "public first slice" not in encoded_entry_packet

    route = entry_packet["python_navigation_route"]
    assert route["surface_id"] == "project_python_lens"
    assert route["command"] == "microcosm python-lens <project>"
    assert route["assay_id"] == "std_python_microcosm_navigation_assay"
    assert route["assay_ref"] == ".microcosm/python_lens.json::navigation_assay"
    assert route["implementation_atlas_ref"] == (
        ".microcosm/python_lens.json::implementation_atlas.python_navigation_assay"
    )
    assert (
        route["route_utility_curriculum_ref"]
        == ".microcosm/python_lens.json::route_utility_curriculum"
    )
    assert (
        route["route_utility_ratchet_ref"]
        == ".microcosm/python_lens.json::route_utility_curriculum.ratchet"
    )
    assert ".microcosm/python_lens.json::route_utility_curriculum" in entry_packet[
        "allowed_drilldowns"
    ]
    assert ".microcosm/python_lens.json::route_utility_curriculum.ratchet" in entry_packet[
        "allowed_drilldowns"
    ]
    assert route["canonical_depth_ladder"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]
    assert route["payload_boundary_ref"] == "project_python_lens_read_model"
    assert route["source_bodies_exported"] is False
    assert "body_redacted" not in route


def test_public_entry_packet_routes_proof_lab_first_screen() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )

    proof_lab = entry_packet["proof_lab_route"]
    assert proof_lab["surface_id"] == "first_screen_verifier_lab_kernel"
    assert proof_lab["organ_id"] == "verifier_lab_kernel"
    assert proof_lab["command"] == "microcosm proof-lab --out /tmp/microcosm-proof-lab"
    assert proof_lab["expanded_command"] == (
        "microcosm verifier-lab-kernel run-kernel-bundle --input "
        "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle --out "
        "/tmp/microcosm-proof-lab"
    )
    assert proof_lab["endpoint"] == "/proof-lab"
    assert proof_lab["alias_endpoints"] == ["/verifier-lab-kernel"]
    assert proof_lab["source_lens_endpoint"] == "/proof-loop-depth"
    assert proof_lab["route_id"] == "formal_prover_context_strategy_gate"
    assert proof_lab["route_component_count"] == 9
    assert proof_lab["route_ref"] == (
        "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/proof_lab_route.json"
    )
    assert proof_lab["standard_ref"] == "standards/std_microcosm_verifier_lab_kernel.json"
    assert proof_lab["paper_module_ref"] == "paper_modules/verifier_lab_kernel.md"
    assert proof_lab["safe_to_show"]["proof_bodies_exported"] is False
    assert proof_lab["safe_to_show"]["provider_payload_bodies_exported"] is False
    assert proof_lab["safe_to_show"]["credential_equivalent_payloads_exported"] is False
    assert proof_lab["safe_to_show"]["release_authorized"] is False
    assert proof_lab["route_ref"] in entry_packet["allowed_drilldowns"]
    assert proof_lab["receipt_ref"] in entry_packet["allowed_drilldowns"]
    assert proof_lab["command"] in entry_packet["allowed_drilldowns"]
    assert proof_lab["expanded_command"] in entry_packet["allowed_drilldowns"]
    assert proof_lab["receipt_ref"] in entry_packet["receipt_dependencies"]

    front_door = entry_packet["tour_front_door_status_route"]
    assert front_door["surface_id"] == "microcosm_tour_front_door_status"
    assert front_door["command"] == "microcosm tour <project>"
    assert front_door["endpoint"] == "/tour"
    assert front_door["status_ref"] in entry_packet["allowed_drilldowns"]
    assert front_door["receipt_ref"] in entry_packet["allowed_drilldowns"]
    assert "receipts/runtime_shell/public_ten_minute_tour.json" in entry_packet[
        "receipt_dependencies"
    ]
    assert front_door["warning_drilldown_surface_ids"] == ["authority", "intake"]
    assert front_door["safe_to_show"]["release_authorized"] is False
    assert front_door["safe_to_show"]["source_mutation_authorized"] is False
    assert "blocking_surface_ids" in front_door["top_level_status_rule"]

    doctrine_route = entry_packet["doctrine_navigation_route"]
    assert doctrine_route["surface_id"] == "microcosm_doctrine_navigation"
    assert doctrine_route["band_ladder"] == [
        "cluster_flag",
        "flag",
        "card",
        "source_receipt",
    ]
    assert "codex/doctrine/paper_modules/microcosm_substrate.md" in doctrine_route[
        "macro_doctrine_refs"
    ]
    assert "codex/standards/std_microcosm.json" in doctrine_route[
        "macro_doctrine_refs"
    ]
    assert "private_state_scan" not in entry_packet["receipt_dependencies"]


def test_public_entry_packet_routes_doctrine_lattice() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    standard = json.loads(
        (REPO_ROOT / "codex/standards/std_microcosm.json").read_text(encoding="utf-8")
    )

    lattice = entry_packet["doctrine_lattice_route"]
    standard_lattice = standard["doctrine_lattice"]
    assert lattice["surface_id"] == "microcosm_doctrine_lattice"
    assert standard_lattice["entry_surface"] == (
        "microcosm-substrate/atlas/entry_packet.json::doctrine_lattice_route"
    )
    assert standard_lattice["agent_entry_route"] == "sit_microcosm_public_substrate"
    assert lattice["band_ladder"] == [
        "cluster_flag",
        "flag",
        "card",
        "source_receipt",
    ]

    for field in [
        "principle_refs",
        "candidate_axiom_pressure_refs",
        "candidate_axiom_policy",
        "concept_refs",
        "mechanism_refs",
        "standard_refs",
        "paper_module_refs",
    ]:
        assert lattice[field] == standard_lattice[field]

    assert [row["kind"] for row in lattice["atlas_option_surfaces"]] == (
        standard_lattice["atlas_option_surfaces"]
    )
    validation_rule = standard["validation_rules"][0]
    assert validation_rule["id"] == "microcosm_doctrine_lattice_entry_packet_parity"
    assert validation_rule["fields"] == [
        "principle_refs",
        "candidate_axiom_pressure_refs",
        "candidate_axiom_policy",
        "concept_refs",
        "mechanism_refs",
        "standard_refs",
        "paper_module_refs",
        "atlas_option_surfaces",
    ]
    assert standard["validation_probe"] == [
        "PYTHONPATH=microcosm-substrate/src ./repo-pytest microcosm-substrate/tests/test_public_entry_docs.py::test_public_entry_packet_routes_doctrine_lattice -q"
    ]
    assert "candidate-axiom promotion authority" in lattice["authority"]
    assert "candidate_axiom_promotion_authority" in standard_lattice["authority_ceiling"]
