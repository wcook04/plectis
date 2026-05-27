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
    assert "std_microcosm_first_screen_composition_root" in receipt["checked_standard_ids"]
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


def test_authority_boundary_manifest_demotes_overread_claims() -> None:
    manifest = json.loads(
        (MICROCOSM_ROOT / "core/authority_boundary.json").read_text(encoding="utf-8")
    )
    standard = json.loads(
        (MICROCOSM_ROOT / "standards/std_microcosm_authority_boundary.json").read_text(
            encoding="utf-8"
        )
    )

    payload = manifest["authority_boundary_payload"]
    denied = payload["denied_authority"]

    assert payload["surface_role"] == "root_public_private_boundary_manifest_read_model"
    assert payload["reader_action"].startswith("Use this manifest to reject overbroad")
    assert denied["complete_secret_detection_claim"] is False
    assert denied["private_data_equivalence_claim"] is False
    assert denied["release_authorized"] is False
    assert denied["source_mutation_authorized"] is False
    assert denied["score_based_progress_authority"] is False
    assert denied["whole_system_correctness_claim"] is False
    assert any("passing scan or receipt" in guard for guard in payload["overread_guard"])
    assert "complete secret detection" in manifest["anti_claim"]
    assert "authority_boundary_payload" in standard["required_fields"]
    assert any(
        "authority_boundary_payload.denied_authority" in rule
        for rule in standard["validation_rules"]
    )
    assert any("complete secret audit" in claim for claim in standard["anti_claims"])


def test_first_screen_composition_root_demotes_evidence_counts_to_accounting() -> None:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/standards_registry.json").read_text(encoding="utf-8")
    )
    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_first_screen_composition_root.json"
        ).read_text(encoding="utf-8")
    )

    rows = {
        str(row.get("standard_id")): row
        for row in registry.get("standards", [])
        if isinstance(row, dict)
    }
    row = rows["std_microcosm_first_screen_composition_root"]

    assert row["kind_id"] == "first_screen_composition_root"
    assert row["path"] == "standards/std_microcosm_first_screen_composition_root.json"
    assert "cold_reader_route_map" in row["used_by_organs"]
    assert "public_reveal_walkthrough" in row["used_by_organs"]
    assert standard["authority_ceiling"]["count_authority"] == (
        "evidence_accounting_only_not_maturity_score"
    )
    assert standard["authority_ceiling"]["score_based_progress_authority"] is False
    assert standard["authority_ceiling"]["release_authority"] is False
    assert standard["authority_ceiling"]["reader_success_authority"] is False
    assert "microcosm tour --card <project>" in standard["validation_rules"][0]
    assert any("accounting" in claim for claim in standard["anti_claims"])
    assert "first_screen_composition_root" in standard["paper_module_contract"]["module_slug"]


def test_concept_and_mechanism_standards_bind_agent_entry() -> None:
    concept = json.loads(
        (MICROCOSM_ROOT / "standards/std_microcosm_concept.json").read_text(
            encoding="utf-8"
        )
    )
    mechanism = json.loads(
        (MICROCOSM_ROOT / "standards/std_microcosm_mechanism.json").read_text(
            encoding="utf-8"
        )
    )
    pressure = json.loads(
        (MICROCOSM_ROOT / "core/public_standard_pressure.json").read_text(
            encoding="utf-8"
        )
    )
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    pressure_by_id = {
        row["standard_id"]: row
        for row in pressure["rows"]
        if isinstance(row, dict)
    }
    population_specimens = entry_packet["concept_mechanism_entry_route"][
        "population_specimens"
    ]

    assert concept["entry_surface_contract"]["agent_entry_ref"] == (
        "AGENTS.md::Concept And Mechanism Entry"
    )
    assert concept["entry_surface_contract"]["first_screen_ref"] == (
        "microcosm first-screen <project>::doctrine_effect_frame"
    )
    assert "entry_surface_contract" in concept["required_fields"]
    assert "population_specimen_contract" in concept["required_fields"]
    assert "activation_receipt_contract" in concept["required_fields"]
    assert concept["population_specimen_contract"]["loop_ref"] == (
        "atlas/entry_packet.json::concept_mechanism_entry_route.population_specimens"
    )
    assert concept["activation_receipt_contract"]["loop_ref"] == (
        "atlas/entry_packet.json::concept_mechanism_entry_route.activation_receipts"
    )
    assert concept["population_specimen_contract"]["minimum_specimen_count"] <= len(
        population_specimens
    )
    assert "mechanism_pair_ref" in concept["population_specimen_contract"][
        "row_must_bind"
    ]
    assert any(
        source_ref.get("path") == "AGENTS.md"
        for source_ref in concept["source_refs"]
        if isinstance(source_ref, dict)
    )
    assert (
        "concept_handle_requires_entry_surface"
        in pressure_by_id
    )
    assert pressure_by_id["concept_handle_requires_entry_surface"][
        "runtime_hook"
    ] == "first_screen_composition.doctrine_effect_frame"

    assert mechanism["entry_surface_contract"]["agent_entry_ref"] == (
        "AGENTS.md::Concept And Mechanism Entry"
    )
    assert mechanism["entry_surface_contract"]["first_screen_ref"] == (
        "microcosm first-screen <project>::doctrine_effect_frame"
    )
    assert "entry_surface_contract" in mechanism["required_fields"]
    assert "population_specimen_contract" in mechanism["required_fields"]
    assert "activation_receipt_contract" in mechanism["required_fields"]
    assert mechanism["population_specimen_contract"]["loop_ref"] == (
        "atlas/entry_packet.json::concept_mechanism_entry_route.population_specimens"
    )
    assert mechanism["activation_receipt_contract"]["loop_ref"] == (
        "atlas/entry_packet.json::concept_mechanism_entry_route.activation_receipts"
    )
    assert mechanism["population_specimen_contract"][
        "minimum_specimen_count"
    ] <= len(population_specimens)
    assert "transformation_shape" in mechanism["population_specimen_contract"][
        "row_must_bind"
    ]
    assert any(
        source_ref.get("path") == "AGENTS.md"
        for source_ref in mechanism["source_refs"]
        if isinstance(source_ref, dict)
    )
    assert (
        "mechanism_handle_requires_runnable_contract"
        in pressure_by_id
    )
    assert (
        "microcosm executable-doctrine-grammar validate-standards-bundle"
        in pressure_by_id["mechanism_handle_requires_runnable_contract"][
            "route_refs"
        ]
    )
    assert "concept_mechanism_requires_population_specimen_loop" in pressure_by_id
    assert (
        "atlas/entry_packet.json::concept_mechanism_entry_route.population_specimens"
        in pressure_by_id["concept_mechanism_requires_population_specimen_loop"][
            "route_refs"
        ]
    )
    assert "concept_mechanism_requires_activation_receipt_loop" in pressure_by_id
    assert (
        "atlas/entry_packet.json::concept_mechanism_entry_route.activation_receipts"
        in pressure_by_id["concept_mechanism_requires_activation_receipt_loop"][
            "route_refs"
        ]
    )


def test_concept_mechanism_population_specimens_bind_to_runnable_lanes() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    route = entry_packet["concept_mechanism_entry_route"]
    specimens = route["population_specimens"]
    activation_receipts = route["activation_receipts"]
    specimen_by_id = {row["specimen_id"]: row for row in specimens}

    assert set(specimen_by_id) >= {
        "first_screen_doctrine_effect_frame",
        "executable_doctrine_grammar_standard_bundle",
        "standards_meta_diagnostics_bundle",
        "voice_to_doctrine_self_improvement_loop_bundle",
    }
    assert route["population_loop"]["build_new_threshold"].startswith(
        "do not create a parallel concept index"
    )
    assert route["population_loop"]["pressure_refs"][-1] == (
        "core/public_standard_pressure.json::concept_mechanism_requires_activation_receipt_loop"
    )
    assert any(
        command.startswith("microcosm first-screen --full")
        for command in route["validation_commands"]
    )
    assert any(
        "microcosm_core.validators.concept_mechanism_population" in command
        for command in route["validation_commands"]
    )

    for specimen in specimens:
        concept_binding = specimen["concept_binding"]
        mechanism_binding = specimen["mechanism_binding"]

        assert concept_binding["concept_role"] != mechanism_binding["mechanism_role"]
        assert concept_binding["payload_shape_ref"]
        assert concept_binding["relationship_shape"]
        assert "glossary" in concept_binding["anti_glossary_rule"]
        assert mechanism_binding["transformation_shape"]
        assert mechanism_binding["state_or_proof_effect"]
        assert "feature prose" in mechanism_binding["anti_feature_prose_rule"]
        assert mechanism_binding["concept_pair_ref"] == (
            f"{specimen['specimen_id']}.concept_binding"
        )
        assert specimen["source_refs"]
        assert specimen["validator_refs"]
        assert specimen["anti_claims"]
        assert specimen["omission_receipt"]["drilldown"]

    assert any(
        "test_executable_doctrine_grammar_accepts_exported_standards_bundle" in ref
        for ref in specimen_by_id[
            "executable_doctrine_grammar_standard_bundle"
        ]["validator_refs"]
    )
    assert any(
        "test_standards_meta_diagnostics_bundle_validates_runtime_shape" in ref
        for ref in specimen_by_id["standards_meta_diagnostics_bundle"][
            "validator_refs"
        ]
    )
    assert any(
        "test_voice_to_doctrine_exported_bundle_validates_runtime_shape" in ref
        for ref in specimen_by_id[
            "voice_to_doctrine_self_improvement_loop_bundle"
        ]["validator_refs"]
    )

    activation_by_id = {row["receipt_id"]: row for row in activation_receipts}
    activation = activation_by_id[
        "concept_index_frontend_view_compiler_projection_guard_2026_05_27"
    ]
    assert activation["pressure_id"] == (
        "cap_quick_concept_index_frontend_view_compiler_sub_d34cd121c080"
    )
    assert activation["selected_specimen_id"] == "voice_to_doctrine_self_improvement_loop_bundle"
    assert activation["residual_disposition"] == "redirected_to_projection_consumer"
    assert "parallel concept index" in activation["authority_boundary"].replace("_", " ")
    assert "population_specimens" in activation["reentry_condition"]
    assert activation["concept_binding"]["mechanism_pair_ref"] == (
        "concept_index_frontend_view_compiler_projection_guard_2026_05_27.mechanism_binding"
    )
    assert activation["mechanism_binding"]["concept_pair_ref"] == (
        "concept_index_frontend_view_compiler_projection_guard_2026_05_27.concept_binding"
    )


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
