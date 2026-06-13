from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

from microcosm_core.doctrine_lattice import (
    _kind_coverage_rows,
    _registry_atlas_join_health,
    build_anti_principle_instance_corpus,
    build_axiom_instance_corpus,
    build_concept_instance_corpus,
    build_entry_card,
    build_doctrine_projection,
    build_lattice_health,
    build_coverage_projection,
    build_mechanism_instance_corpus,
    build_organ_instance_corpus,
    build_paper_module_instance_corpus,
    build_principle_instance_corpus,
    build_skill_instance_corpus,
    build_standard_instance_corpus,
    check_public_codex_leaks,
    expected_paper_module_instances,
    load_kind_standards,
    load_skill_instances,
    load_standard_instances,
    load_relation_registry,
    validate_anti_principle_instance_corpus,
    validate_axiom_instance_corpus,
    validate_concept_instance_corpus,
    validate_doctrine_projection,
    validate_entry_card,
    validate_coverage_projection,
    validate_kind_standard_contracts,
    validate_mechanism_instance_corpus,
    validate_organ_instance_corpus,
    validate_paper_module_instance_corpus,
    validate_principle_instance_corpus,
    validate_skill_instance_corpus,
    validate_standard_instance_corpus,
    validate_relation_registry,
    write_entry_card,
    write_coverage_projection,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
STANDARD_TRIAD_SKILL_BATCH_STANDARD_IDS = {
    "std_microcosm_agent_benchmark_integrity_anti_gaming_replay",
    "std_microcosm_agent_memory_temporal_conflict_replay",
    "std_microcosm_agent_monitor_redteam_falsification_replay",
    "std_microcosm_agent_route_observability_runtime",
    "std_microcosm_agent_sabotage_scheming_monitor_replay",
    "std_microcosm_agent_sandbox_policy_escape_replay",
    "std_microcosm_agent_trace",
    "std_microcosm_agentic_vulnerability_discovery_patch_proof_replay",
    "std_microcosm_anti_claim",
    "std_microcosm_atlas_route",
    "std_microcosm_authority_boundary",
    "std_microcosm_belief_state_process_reward_replay",
    "std_microcosm_batch10_cold_eval_honesty_capsule",
    "std_microcosm_batch10_governance_compilers_capsule",
    "std_microcosm_batch10_live_source_drift_capsule",
    "std_microcosm_batch11_saturation_engines_capsule",
    "std_microcosm_batch12_market_dashboard_read_model_capsule",
    "std_microcosm_batch12_prediction_market_board_capsule",
    "std_microcosm_batch12_release_claim_language_gate",
    "std_microcosm_batch4_proof_authority_runtime",
    "std_microcosm_batch6_unsurfaced_primitives_capsule",
    "std_microcosm_batch7_macro_engines_capsule",
    "std_microcosm_batch7_station_runtime_capsule",
    "std_microcosm_batch8_audio_level_rms_port",
    "std_microcosm_batch8_compliance_pipeline_capsule",
    "std_microcosm_batch8_policy_engines_capsule",
    "std_microcosm_batch8_station_surface_atlas_layout_port",
    "std_microcosm_batch8_structural_theses_capsule",
    "std_microcosm_batch8_tools_tail_primitives_capsule",
    "std_microcosm_batch8_validator_checker_capsule",
    "std_microcosm_batch9_macro_engines_capsule",
    "std_microcosm_concurrency_mission_control",
    "std_microcosm_indirect_prompt_injection_information_flow_policy_replay",
    "std_microcosm_mcp_tool_authority_replay",
    "std_microcosm_mechanistic_interpretability_circuit_attribution_replay",
    "std_microcosm_pattern_assimilation_step",
    "std_microcosm_sleeper_memory_poisoning_quarantine_replay",
    "std_microcosm_tool_server_pressure_inventory",
    "std_microcosm_undeclared_library_prior_symbol_classifier",
}
STAGED_STANDARD_TRIAD_SKILL_SOURCE_STANDARD_IDS = {
    "std_microcosm_batch5_authority_systems_capsule",
    "std_microcosm_batch7_demo_take_console_capsule",
    "std_microcosm_batch7_oracle_sibling_capsule",
    "std_microcosm_batch7_secondary_runtime_capsule",
    "std_microcosm_batch7_zenith_macos_capsule",
    "std_microcosm_engine_room_annex_knowledge_router",
    "std_microcosm_engine_room_bridge_campaign_dag",
    "std_microcosm_engine_room_command_run_singleflight",
    "std_microcosm_engine_room_derived_fact_provider_engine",
    "std_microcosm_engine_room_egress_self_compliance_gate",
    "std_microcosm_engine_room_generated_projection_drift_gate",
    "std_microcosm_engine_room_lean_proof_search_lab",
    "std_microcosm_engine_room_metabolism_runtime",
    "std_microcosm_engine_room_navigation_fitness_benchmark",
    "std_microcosm_engine_room_public_projection_leak_gate",
    "std_microcosm_work_landing_control_spine",
}
ENGINE_ROOM_STAGED_STANDARD_IDS = {
    "std_microcosm_engine_room_annex_knowledge_router",
    "std_microcosm_engine_room_bridge_campaign_dag",
    "std_microcosm_engine_room_command_run_singleflight",
    "std_microcosm_engine_room_derived_fact_provider_engine",
    "std_microcosm_engine_room_egress_self_compliance_gate",
    "std_microcosm_engine_room_generated_projection_drift_gate",
    "std_microcosm_engine_room_lean_proof_search_lab",
    "std_microcosm_engine_room_metabolism_runtime",
    "std_microcosm_engine_room_navigation_fitness_benchmark",
    "std_microcosm_engine_room_public_projection_leak_gate",
}
EXPECTED_SKILL_INSTANCE_COUNT = 401
EXPECTED_SKILL_SELECTIVE_RELATION_COUNT = 6
EXPECTED_SKILL_SELECTIVE_NODE_COUNT = 6
EXPECTED_ORGAN_SELECTIVE_RELATION_COUNT = 29
EXPECTED_STANDARD_INSTANCE_COUNT = 146
EXPECTED_STANDARD_REQUIRED_EDGE_GAP_COUNT = 0
EXPECTED_STANDARD_REQUIRED_RELATION_GAP_COUNT = 0
EXPECTED_STANDARD_TRIAD_RESOLVED_EDGE_COUNT = 438
EXPECTED_STANDARD_TRIAD_PLANNED_UNRESOLVED_EDGE_COUNT = 0
EXPECTED_STANDARD_REQUIRED_RELATION_GAP_DETAIL_COUNT = 0
EXPECTED_STANDARD_USED_BY_ORGAN_EDGE_COUNT = 247
EXPECTED_STANDARD_USED_BY_ORGAN_RESOLVED_EDGE_COUNT = 219
EXPECTED_STANDARD_USED_BY_ORGAN_UNRESOLVED_EDGE_COUNT = 28
EXPECTED_SOURCE_LEVEL_STANDARD_LEGACY_COUNT_AFTER_ACCEPTED_ORGAN_ACTIVATION = 11
ACCEPTED_ORGAN_STANDARD_V2_ACTIVATION_IDS = {
    "std_microcosm_agent_memory_temporal_conflict_replay",
    "std_microcosm_agent_monitor_redteam_falsification_replay",
    "std_microcosm_agent_route_observability_runtime",
    "std_microcosm_agent_sabotage_scheming_monitor_replay",
    "std_microcosm_agent_sandbox_policy_escape_replay",
    "std_microcosm_agentic_vulnerability_discovery_patch_proof_replay",
    "std_microcosm_batch4_proof_authority_runtime",
    "std_microcosm_batch6_unsurfaced_primitives_capsule",
    "std_microcosm_belief_state_process_reward_replay",
    "std_microcosm_bridge_phase_continuity_runtime",
    "std_microcosm_certificate_kernel_execution_lab",
    "std_microcosm_corpus_readiness_mathlib_absence_gate",
    "std_microcosm_executable_doctrine_grammar",
    "std_microcosm_indirect_prompt_injection_information_flow_policy_replay",
    "std_microcosm_macro_projection_import_protocol",
    "std_microcosm_materials_chemistry_closed_loop_lab_safety_replay",
    "std_microcosm_mathematical_strategy_atlas_hypothesis_scorer",
    "std_microcosm_mcp_tool_authority_replay",
    "std_microcosm_mechanistic_interpretability_circuit_attribution_replay",
    "std_microcosm_mission_transaction_work_spine",
    "std_microcosm_navigation_hologram_route_plane",
    "std_microcosm_pattern_binding_contract",
    "std_microcosm_prediction_oracle_reconciliation",
    "std_microcosm_proof_derived_governed_mutation_authorization",
    "std_microcosm_public_reveal_walkthrough",
    "std_microcosm_research_replication_rubric_artifact_replay",
    "std_microcosm_sleeper_memory_poisoning_quarantine_replay",
    "std_microcosm_verifier_lab_execution_spine",
    "std_microcosm_verifier_lab_kernel",
    "std_microcosm_voice_to_doctrine_self_improvement_loop",
    "std_microcosm_world_model_projection_drift_control_room",
}
FAMILY_CONCEPT_IDS = {
    "concept.agent_reliability_and_safety_validator_bundle",
    "concept.architecture_and_navigation_route_contract_bundle",
    "concept.entry_and_reveal_route_readiness_bundle",
    "concept.formal_math_and_proof_witness_bundle",
    "concept.import_projection_and_drift_control_bundle",
    "concept.research_and_science_replay_evidence_bundle",
    "concept.work_landing_and_continuity_control_bundle",
}


def _mechanism_source(mechanism_id: str) -> dict:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(
            encoding="utf-8"
        )
    )
    return next(row for row in registry["mechanisms"] if row["id"] == mechanism_id)


def _mechanism_source_count() -> int:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(
            encoding="utf-8"
        )
    )
    return len(registry["mechanisms"])


def _concept_source_count() -> int:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    return len(entry_packet["concept_mechanism_entry_route"]["population_specimens"])


def _organ_source_count() -> int:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    return sum(
        1
        for row in registry["implemented_organs"]
        if row["status"] == "accepted_current_authority"
    )


def _paper_module_capsule_source_count() -> int:
    capsules = json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(
            encoding="utf-8"
        )
    )
    return len(capsules["paper_modules"])


def _family_concept_map() -> dict[str, str]:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    family_map: dict[str, str] = {}
    for row in entry_packet["concept_mechanism_entry_route"]["population_specimens"]:
        if row.get("specimen_role") != "organ_family_concept_specimen":
            continue
        family = str(row["entry_ref"]).split("family=", 1)[1]
        family_map[family] = f"concept.{row['specimen_id']}"
    return family_map


def _organ_atlas_row(organ_id: str) -> dict:
    return _organ_atlas_indexed_row(organ_id)[1]


def _organ_atlas_indexed_row(organ_id: str) -> tuple[int, dict]:
    atlas = json.loads(
        (MICROCOSM_ROOT / "core/organ_atlas.json").read_text(encoding="utf-8")
    )
    return next(
        (index, row)
        for index, row in enumerate(atlas["organs"])
        if row.get("organ_id", row.get("id")) == organ_id
    )


def _assert_atlas_required_edges_resolved(
    projection: dict,
    organ_id: str,
    *,
    paper_module_ref: str,
    atlas_mechanism_id: str,
    code_path: str,
    authority_class: str = "source_assertion",
    evidence_rank: int = 5,
) -> None:
    coverage = projection["organ_required_edge_coverage"]
    assert organ_id not in coverage["without_paper_module_ref"]
    assert organ_id not in coverage["without_mechanism_ref"]
    assert organ_id not in coverage["without_code_loci"]

    organ = _organ_atlas_row(organ_id)
    assert organ["paper_module_ref"] == paper_module_ref
    assert any(
        edge["ref"] == atlas_mechanism_id
        and edge["resolution_status"] == "resolved"
        for edge in organ["mechanism_refs"]
    )
    assert any(
        locus["path"] == code_path and locus["resolution"] == "resolved"
        for locus in organ["code_loci"]
    )

    mechanism = _mechanism_source(atlas_mechanism_id)
    assert mechanism["runs_in"] == [organ_id]
    assert mechanism["resolution_evidence"]["authority_class"] == authority_class
    assert mechanism["resolution_evidence"]["evidence_rank"] == evidence_rank
    assert any(
        locus["path"] == code_path and locus["resolution"] == "resolved"
        for locus in mechanism["code_loci"]
    )


def _assert_organ_law_refs_resolved(
    organ_id: str,
    *,
    axiom_refs: set[str],
    principle_refs: set[str],
) -> None:
    organ = json.loads(
        (MICROCOSM_ROOT / f"organs/{organ_id}.json").read_text(encoding="utf-8")
    )
    atlas_row = _organ_atlas_row(organ_id)
    edges = organ["relationships"]["edges"]
    residuals = {
        residual["relation_id"]
        for residual in organ["relationships"]["unpopulated_selective_relations"]
    }

    assert set(atlas_row["axiom_refs"]) == axiom_refs
    assert set(atlas_row["principle_refs"]) == principle_refs
    assert set(organ["axiom_refs"]) == axiom_refs
    assert set(organ["principle_refs"]) == principle_refs
    assert {
        edge["target_id"]
        for edge in edges
        if edge["relation_id"] == "organ.constrained_by.axiom"
    } == axiom_refs
    assert {
        edge["target_id"]
        for edge in edges
        if edge["relation_id"] == "organ.governed_by.principle"
    } == principle_refs
    assert "organ.constrained_by.axiom" not in residuals
    assert "organ.governed_by.principle" not in residuals
    assert organ["authority_boundary"] == (
        "public_organ_json_seeded_from_organ_atlas_and_registry_not_authority_flip_until_parity_receipt"
    )


def test_relation_registry_covers_all_v2_lattice_edges() -> None:
    standards = load_kind_standards(MICROCOSM_ROOT)
    registry = load_relation_registry(MICROCOSM_ROOT)

    result = validate_relation_registry(registry, standards)
    relations = {row["relation_id"]: row for row in registry["relations"]}

    assert result["status"] == "pass"
    assert result["relation_count"] >= 30
    assert result["errors"] == []
    principle_grounding = relations["principle.grounded_by.axiom"]["truth_boundary"]
    assert principle_grounding["claim_role"] == "grounding_route_not_support_witness"
    assert principle_grounding["computed_by"] == "validator.microcosm.axiom_support_cover"
    assert any(
        "do not certify principle support strength" in rule
        for rule in principle_grounding["non_laundering_rules"]
    )
    for relation_id in (
        "principle.governs.concept",
        "principle.governs.mechanism",
    ):
        boundary = relations[relation_id]["truth_boundary"]
        assert boundary["claim_role"] == "governance_route_not_support_witness"
        assert any(
            "substrate-routing evidence only" in rule
            for rule in boundary["non_laundering_rules"]
        )
    anti_negates = relations["anti_principle.negates_failure_of.principle"][
        "truth_boundary"
    ]
    assert anti_negates["claim_role"] == (
        "failure_guard_route_not_principle_truth_verdict"
    )
    assert any(
        "not proof that the principle is false or unsupported" in rule
        for rule in anti_negates["non_laundering_rules"]
    )
    anti_guards = relations["anti_principle.guards.axiom"]["truth_boundary"]
    assert anti_guards["claim_role"] == (
        "failure_guard_route_not_obligation_rejection_proof"
    )
    assert any(
        "do not verify exact obligation rejection" in rule
        for rule in anti_guards["non_laundering_rules"]
    )
    organ_governance = relations["organ.governed_by.principle"]["truth_boundary"]
    assert organ_governance["claim_role"] == (
        "organ_governance_route_not_principle_support_witness"
    )
    assert organ_governance["computed_by"] == (
        "validator.microcosm.axiom_support_cover"
    )
    assert any(
        "not proof that the principle is supported" in rule
        for rule in organ_governance["non_laundering_rules"]
    )
    assert any(
        "blanket organ-to-principle wiring is forbidden" in rule
        for rule in organ_governance["non_laundering_rules"]
    )
    organ_constraint = relations["organ.constrained_by.axiom"]["truth_boundary"]
    assert organ_constraint["claim_role"] == (
        "organ_constraint_route_not_axiom_support_witness"
    )
    assert organ_constraint["computed_by"] == (
        "validator.microcosm.axiom_support_cover"
    )
    assert any(
        "not proof of axiom support strength" in rule
        for rule in organ_constraint["non_laundering_rules"]
    )
    assert any(
        "blanket organ-to-axiom wiring is forbidden" in rule
        for rule in organ_constraint["non_laundering_rules"]
    )


def test_axiom_witness_relation_is_standard_and_registry_governed() -> None:
    standards = load_kind_standards(MICROCOSM_ROOT)
    registry = load_relation_registry(MICROCOSM_ROOT)

    axiom_edges = standards["axiom"]["lattice_edges"]["selective"]
    witness_edge = next(
        edge
        for edge in axiom_edges
        if edge["to_kind"] == "organ"
        and edge["relation_verb"] == "witnessed_by"
        and edge["reverse_verb"] == "witnesses"
    )
    witness_relation = next(
        row
        for row in registry["relations"]
        if row["relation_id"] == "axiom.witnessed_by.organ"
    )

    assert witness_edge == {
        "to_kind": "organ",
        "relation_verb": "witnessed_by",
        "reverse_verb": "witnesses",
        "cardinality": "zero_to_many",
        "requirement": "selective",
    }
    assert witness_relation["source_kind"] == "axiom"
    assert witness_relation["target_kind"] == "organ"
    assert witness_relation["forward_verb"] == witness_edge["relation_verb"]
    assert witness_relation["reverse_verb"] == witness_edge["reverse_verb"]
    assert witness_relation["cardinality"] == witness_edge["cardinality"]
    assert witness_relation["requirement"] == witness_edge["requirement"]
    assert witness_relation["authority_class"] == "source_assertion"
    assert witness_relation["target_resolution"] == "resolve_when_present"
    assert witness_relation["edge_justification_required"] is True
    assert witness_relation["projection_surfaces"] == [
        "coverage_health",
        "atlas_card",
        "markdown_reference",
        "mermaid_graph",
    ]

    result = validate_relation_registry(registry, standards)
    assert result["status"] == "pass"
    assert result["errors"] == []


def test_doctrine_lattice_coverage_is_reproducible_from_sources(tmp_path: Path) -> None:
    projection = write_coverage_projection(
        MICROCOSM_ROOT,
        tmp_path / "doctrine_lattice_coverage.json",
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )

    assert projection["status"] == "pass"
    assert projection["contract_status"] == "pass"
    assert projection["population_status"] == "complete"
    validation = validate_coverage_projection(projection, MICROCOSM_ROOT)
    assert validation["status"] == "pass"
    assert validation["errors"] == []

    written = json.loads((tmp_path / "doctrine_lattice_coverage.json").read_text(encoding="utf-8"))
    assert written == projection


def test_doctrine_projection_status_only_card_is_read_only_and_compact() -> None:
    surface_paths = [
        MICROCOSM_ROOT / "atlas/doctrine_lattice_projection.json",
        MICROCOSM_ROOT / "atlas/doctrine_lattice_graph.mmd",
        MICROCOSM_ROOT / "atlas/doctrine_lattice_health.json",
        MICROCOSM_ROOT / "atlas/doctrine_lattice_entry_card.json",
        MICROCOSM_ROOT / "core/doctrine_lattice_coverage.json",
    ]
    before_mtimes = {path: path.stat().st_mtime_ns for path in surface_paths}

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_doctrine_projection.py",
            "--status-only",
        ],
        cwd=MICROCOSM_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "available"
    assert payload["read_only"] is True
    assert payload["owner_surface"].endswith("build_doctrine_projection.py --status-only")
    assert payload["surface_count"] == 5
    assert payload["missing_or_invalid"] == []
    assert len(result.stdout) < 8000
    assert {
        "atlas/doctrine_lattice_projection.json",
        "core/doctrine_lattice_coverage.json",
    }.issubset({row["path"] for row in payload["surfaces"]})
    assert {path: path.stat().st_mtime_ns for path in surface_paths} == before_mtimes


def test_doctrine_projection_builder_exposes_targeted_refresh_controls() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_doctrine_projection.py",
            "--help",
        ],
        cwd=MICROCOSM_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "--write-organ-instance" in result.stdout
    assert "--write-principle-instance" in result.stdout
    assert "--write-aggregate-surfaces" in result.stdout
    assert "--write-organ-corpus" in result.stdout


def test_axiom_instance_corpus_is_seeded_from_routing_with_parity() -> None:
    corpus = build_axiom_instance_corpus(MICROCOSM_ROOT)
    validation = validate_axiom_instance_corpus(MICROCOSM_ROOT)

    assert corpus["expected_axiom_count"] == 12
    assert corpus["json_instance_count"] == 12
    assert corpus["parity_status"] == "pass"
    assert corpus["authority_flip_status"] == "not_flipped_routing_still_source_of_record"
    assert validation["status"] == "pass"
    assert validation["errors"] == []

    ax1 = json.loads((MICROCOSM_ROOT / "axioms/AX-1.json").read_text(encoding="utf-8"))
    assert ax1["schema_version"] == "microcosm_axiom_instance_v1"
    assert ax1["axiom_payload"]["support_contract"]["computed_by"] == (
        "validator.microcosm.axiom_support_cover"
    )
    assert ax1["axiom_payload"]["support_contract"]["legacy_routing_witness_strength"][
        "status"
    ] == "legacy_label_not_computed_support_claim"
    reciprocity = ax1["axiom_payload"]["substrate_reciprocity_contract"]
    assert reciprocity["contract_version"] == "microcosm_axiom_substrate_reciprocity_v1"
    assert reciprocity["source_authority_ref"].startswith("core/axiom_organ_routing.json")
    assert reciprocity["law_to_substrate"]["grounded_principle_ids"] == ["P-1", "P-2"]
    assert reciprocity["law_to_substrate"]["substrate_constraint_relation"] == (
        "organ.constrained_by.axiom"
    )
    assert "agent_sabotage_scheming_monitor_replay" in reciprocity["substrate_to_law"][
        "witness_organs"
    ]
    assert reciprocity["claim_ceiling"]["computed_by"] == (
        "validator.microcosm.axiom_support_cover"
    )
    assert "not support claims" in reciprocity["claim_ceiling"]["boundary"]
    assert any(edge["target_id"] == "P-1" for edge in ax1["relationships"]["edges"])

    ax8 = json.loads((MICROCOSM_ROOT / "axioms/AX-8.json").read_text(encoding="utf-8"))
    ax8_reciprocity = ax8["axiom_payload"]["substrate_reciprocity_contract"]
    assert ax8_reciprocity["substrate_to_law"]["layer_debt_ids"] == [
        "AX8-general-taint-propagation"
    ]
    assert "cannot silently de-admit" in json.dumps(
        json.loads(
            (MICROCOSM_ROOT / "standards/std_microcosm_axiom.json").read_text(
                encoding="utf-8"
            )
        )["axiom_payload_contract"]["substrate_reciprocity_contract"][
            "non_laundering_rules"
        ]
    )


def test_principle_and_anti_principle_corpora_are_seeded_with_parity() -> None:
    principle_corpus = build_principle_instance_corpus(MICROCOSM_ROOT)
    anti_principle_corpus = build_anti_principle_instance_corpus(MICROCOSM_ROOT)
    principle_validation = validate_principle_instance_corpus(MICROCOSM_ROOT)
    anti_principle_validation = validate_anti_principle_instance_corpus(MICROCOSM_ROOT)

    assert principle_corpus["expected_principle_count"] == 20
    assert principle_corpus["json_instance_count"] == 20
    assert principle_corpus["parity_status"] == "pass"
    assert principle_validation["status"] == "pass"
    assert principle_validation["errors"] == []
    assert anti_principle_corpus["expected_anti_principle_count"] == 17
    assert anti_principle_corpus["json_instance_count"] == 17
    assert anti_principle_corpus["parity_status"] == "pass"
    assert anti_principle_validation["status"] == "pass"
    assert anti_principle_validation["errors"] == []

    p1 = json.loads((MICROCOSM_ROOT / "principles/P-1.json").read_text(encoding="utf-8"))
    assert p1["schema_version"] == "microcosm_principle_instance_v1"
    assert p1["axiom_refs"] == ["AX-1"]
    assert p1["obligation_refs"] == [
        "AX-1.O1.certificate_exists",
        "AX-1.O2.checker_accepts",
        "AX-1.O3.claim_ceiling",
        "AX-1.O4.bare_assertion_bottom",
    ]
    assert p1["principle_payload"]["support_contract"]["computed_by"] == (
        "validator.microcosm.axiom_support_cover"
    )
    assert p1["principle_payload"]["support_contract"][
        "grounding_obligation_refs"
    ] == p1["obligation_refs"]
    governance = p1["principle_payload"]["substrate_governance_contract"]
    assert governance["contract_version"] == "microcosm_principle_substrate_governance_v1"
    assert governance["source_authority_ref"] == "PRINCIPLES.md::P-1"
    assert governance["principle_to_substrate"]["grounding_axiom_ids"] == ["AX-1"]
    assert governance["principle_to_substrate"][
        "grounding_obligation_refs"
    ] == p1["obligation_refs"]
    assert governance["principle_to_substrate"]["governed_mechanism_ids"]
    assert governance["principle_to_substrate"]["governed_concept_ids"]
    assert "not a witness" in governance["principle_to_substrate"]["rule"]
    assert governance["substrate_to_principle"]["derived_from"] == [
        "PRINCIPLES.md grounding text",
        "PRINCIPLES.md obligation grounding text",
        "core/organ_atlas.json principle_refs plus mechanism_refs/concept_refs",
    ]

    assert governance["claim_ceiling"]["computed_by"] == (
        "validator.microcosm.axiom_support_cover"
    )
    principle_standard = json.loads(
        (MICROCOSM_ROOT / "standards/std_microcosm_principle.json").read_text(
            encoding="utf-8"
        )
    )
    support_contract = principle_standard["principle_payload_contract"][
        "support_contract"
    ]
    assert support_contract["instance_payload_field"] == (
        "principle_payload.support_contract"
    )
    assert support_contract["computed_by_validator"] == (
        "validator.microcosm.axiom_support_cover"
    )
    assert "grounding_obligation_refs" in support_contract["support_fields"]
    assert support_contract["claim_ceiling"]["principle_support_status"] == (
        "inherited_from_grounding_obligation_refs_not_asserted_by_principle_source"
    )
    assert any(
        "governed mechanism, governed concept, organ-atlas" in rule
        for rule in support_contract["non_laundering_rules"]
    )
    assert (
        principle_standard["principle_payload_contract"][
            "substrate_governance_contract"
        ]["instance_payload_field"]
        == "principle_payload.substrate_governance_contract"
    )
    assert (
        "grounding_obligation_refs"
        in principle_standard["principle_payload_contract"][
            "substrate_governance_contract"
        ]["principle_to_substrate_fields"]
    )
    assert any(
        "residual and fillability classifications are routing pressure" in rule
        for rule in principle_standard["principle_payload_contract"][
            "substrate_governance_contract"
        ]["non_laundering_rules"]
    )
    assert any(
        "candidate routes, singleton matches, generated neighbour hints" in rule
        for rule in principle_standard["principle_payload_contract"][
            "substrate_governance_contract"
        ]["non_laundering_rules"]
    )
    anti_principle_standard = json.loads(
        (
            MICROCOSM_ROOT / "standards/std_microcosm_anti_principle.json"
        ).read_text(encoding="utf-8")
    )
    anti_contract = anti_principle_standard["anti_principle_payload_contract"][
        "rejection_mapping_boundary_contract"
    ]
    assert anti_contract["instance_payload_field"] == "anti_principle_payload"
    assert "relationships.unpopulated_selective_relations" in anti_contract[
        "anti_principle_to_substrate_fields"
    ]
    assert any(
        "core/axiom_organ_routing.json anti_principle_ids" in ref
        for ref in anti_contract["accepted_source_refs"]
    )
    assert any(
        "not positive support" in rule
        for rule in anti_contract["non_laundering_rules"]
    )
    assert any(
        "cannot verify exact per-obligation rejection" in rule
        for rule in anti_contract["non_laundering_rules"]
    )
    assert any(
        edge["relation_id"] == "principle.grounded_by.axiom"
        and edge["target_id"] == "AX-1"
        and edge["target_status"] == "resolved_json_instance"
        for edge in p1["relationships"]["edges"]
    )
    assert any(
        edge["relation_id"] == "principle.governs.mechanism"
        and edge["target_id"]
        == "mechanism.agent_sabotage_scheming_monitor_replay.validates_public_sabotage_scheming_monitor_replay"
        and edge["target_status"] == "resolved_json_instance"
        for edge in p1["relationships"]["edges"]
    )
    assert p1["relationships"]["governs_mechanism_ids"]
    assert p1["relationships"]["governs_concept_ids"]
    assert any(
        edge["relation_id"] == "principle.governs.concept"
        and edge["target_status"] == "resolved_json_instance"
        for edge in p1["relationships"]["edges"]
    )
    assert p1["relationships"]["unpopulated_selective_relations"] == []

    p18 = json.loads((MICROCOSM_ROOT / "principles/P-18.json").read_text(encoding="utf-8"))
    assert p18["schema_version"] == "microcosm_principle_instance_v1"
    assert p18["axiom_refs"] == ["AX-3", "AX-9", "AX-11", "AX-12"]
    assert "AX-12.O4.evidence_truth_floor_blocks_release" in p18["obligation_refs"]
    assert p18["relationships"]["obligation_refs"] == p18["obligation_refs"]
    assert p18["principle_payload"]["support_contract"][
        "grounding_obligation_refs"
    ] == p18["obligation_refs"]
    assert p18["principle_payload"]["substrate_governance_contract"][
        "principle_to_substrate"
    ]["grounding_obligation_refs"] == p18["obligation_refs"]
    assert {
        edge["target_id"]
        for edge in p18["relationships"]["edges"]
        if edge["relation_id"] == "principle.grounded_by.axiom"
    } == {"AX-3", "AX-9", "AX-11", "AX-12"}
    assert set(p18["relationships"]["governs_mechanism_ids"]) == {
        "mechanism.batch12_release_claim_language_gate.validates_public_release_claim_language_gate",
        "mechanism.concurrency_mission_control.validates_public_concurrency_mission_control",
        "mechanism.durable_agent_work_landing_replay.validates_public_work_landing_replay_contract",
        "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
        "mechanism.macro_projection_import_protocol.validates_public_macro_projection_imports",
        "mechanism.mcp_tool_authority_replay.validates_public_mcp_tool_authority_replay",
        "mechanism.mission_transaction_work_spine.validates_public_mission_transaction_bundle",
        "mechanism.proof_derived_governed_mutation_authorization.validates_synthetic_governed_mutation_authorization",
        "mechanism.standards_meta_diagnostics.validates_public_standards_meta_diagnostics",
    }
    assert {
        edge["target_id"]
        for edge in p18["relationships"]["edges"]
        if edge["relation_id"] == "principle.governs.mechanism"
    } == set(p18["relationships"]["governs_mechanism_ids"])
    assert set(p18["relationships"]["governs_concept_ids"]) == {
        "concept.agent_reliability_and_safety_validator_bundle",
        "concept.architecture_and_navigation_route_contract_bundle",
        "concept.formal_math_and_proof_witness_bundle",
        "concept.import_projection_and_drift_control_bundle",
        "concept.work_landing_and_continuity_control_bundle",
    }
    assert {
        edge["target_id"]
        for edge in p18["relationships"]["edges"]
        if edge["relation_id"] == "principle.governs.concept"
    } == set(p18["relationships"]["governs_concept_ids"])
    assert p18["relationships"]["unpopulated_selective_relations"] == []

    p19 = json.loads((MICROCOSM_ROOT / "principles/P-19.json").read_text(encoding="utf-8"))
    assert p19["schema_version"] == "microcosm_principle_instance_v1"
    assert p19["axiom_refs"] == ["AX-5", "AX-6", "AX-11"]
    assert p19["obligation_refs"] == [
        "AX-5.O2.no_evidence_defaults_blocked",
        "AX-5.O3.authority_cannot_raise_without_derivation",
        "AX-6.O1.closed_world_domain_declared",
        "AX-6.O2.absence_not_negation",
        "AX-6.O3.fact_claims_cite_loci_and_dag",
        "AX-11.O1.grammar_membership_required",
        "AX-11.O2.receipts_and_anti_claims_present",
        "AX-11.O3.prose_alone_is_projection",
    ]
    assert p19["relationships"]["obligation_refs"] == p19["obligation_refs"]
    assert {
        edge["target_id"]
        for edge in p19["relationships"]["edges"]
        if edge["relation_id"] == "principle.grounded_by.axiom"
    } == {"AX-5", "AX-6", "AX-11"}
    assert set(p19["relationships"]["governs_mechanism_ids"]) == {
        "mechanism.doctrine_fact_claim_audit.validates_public_doctrine_fact_claim_audit",
        "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
        "mechanism.pattern_binding_contract.validates_public_pattern_bindings",
        "mechanism.proof_diagnostic_evidence_spine.validates_ring2_diagnostic_evidence_membrane",
        "mechanism.self_ignorance_coverage_ledger.validates_public_self_ignorance_coverage_ledger",
        "mechanism.standards_meta_diagnostics.validates_public_standards_meta_diagnostics",
    }
    assert set(p19["relationships"]["governs_concept_ids"]) == {
        "concept.architecture_and_navigation_route_contract_bundle",
        "concept.formal_math_and_proof_witness_bundle",
    }
    assert {
        edge["target_id"]
        for edge in p19["relationships"]["edges"]
        if edge["relation_id"] == "principle.governs.mechanism"
    } == set(p19["relationships"]["governs_mechanism_ids"])
    assert {
        edge["target_id"]
        for edge in p19["relationships"]["edges"]
        if edge["relation_id"] == "principle.governs.concept"
    } == set(p19["relationships"]["governs_concept_ids"])
    assert p19["relationships"]["unpopulated_selective_relations"] == []
    assert "typed pressure route, not an edge" in p19["statement"]
    assert "candidate route" in p19["statement"]
    assert "current source authority row" in p19["statement"]
    assert "names the relation" in p19["statement"]
    p19_statement = " ".join(p19["statement"].split())
    assert "Bidirectional substrate representation follows the same floor" in p19_statement
    assert "principle-to-substrate edges must be source-derived" in p19_statement
    assert (
        "substrate-to-principle evidence may refine governed ids only when "
        "current source rows name the relation"
    ) in p19_statement
    assert "Neither direction is support proof, projection authority" in p19_statement
    assert "permission to launder residual pressure into an edge" in p19_statement
    p19_markdown = (
        MICROCOSM_ROOT / "principles/P-19.md"
    ).read_text(encoding="utf-8")
    assert "Bidirectional\nsubstrate representation follows the same floor" in p19_markdown

    p20 = json.loads((MICROCOSM_ROOT / "principles/P-20.json").read_text(encoding="utf-8"))
    assert p20["schema_version"] == "microcosm_principle_instance_v1"
    assert p20["axiom_refs"] == ["AX-11", "AX-12"]
    assert p20["relationships"]["obligation_refs"] == p20["obligation_refs"]
    assert {
        edge["target_id"]
        for edge in p20["relationships"]["edges"]
        if edge["relation_id"] == "principle.grounded_by.axiom"
    } == {"AX-11", "AX-12"}
    assert set(p20["relationships"]["failure_guarded_by_anti_principle_ids"]) == {
        "AP-1",
        "AP-3",
        "AP-10",
        "AP-11",
        "AP-13",
        "AP-14",
        "AP-15",
        "AP-16",
        "AP-17",
    }
    assert {
        edge["target_id"]
        for edge in p20["relationships"]["edges"]
        if edge["relation_id"] == "anti_principle.negates_failure_of.principle"
    } == set(p20["relationships"]["failure_guarded_by_anti_principle_ids"])
    assert p20["relationships"]["unpopulated_selective_relations"] == []
    assert p20["principle_payload"]["support_contract"]["computed_by"] == (
        "validator.microcosm.axiom_support_cover"
    )
    assert p20["principle_payload"]["substrate_governance_contract"][
        "principle_to_substrate"
    ]["guarding_anti_principle_ids"] == p20["relationships"][
        "failure_guarded_by_anti_principle_ids"
    ]

    ap17 = json.loads(
        (MICROCOSM_ROOT / "anti_principles/AP-17.json").read_text(encoding="utf-8")
    )
    assert ap17["schema_version"] == "microcosm_anti_principle_instance_v1"
    assert ap17["guards"] == ["AX-4", "AX-11"]
    assert {
        edge["target_id"]
        for edge in ap17["relationships"]["edges"]
        if edge["relation_id"] == "anti_principle.guards.axiom"
    } == {"AX-4", "AX-11"}
    assert {
        edge["target_id"]
        for edge in ap17["relationships"]["edges"]
        if edge["relation_id"] == "anti_principle.negates_failure_of.principle"
    } == {"P-5", "P-12", "P-14", "P-15", "P-17", "P-18", "P-19", "P-20"}
    assert ap17["relationships"]["unpopulated_selective_relations"] == []


def test_root_doctrine_markdown_has_public_glance_tables() -> None:
    axioms_text = (MICROCOSM_ROOT / "AXIOMS.md").read_text(encoding="utf-8")
    principles_text = (MICROCOSM_ROOT / "PRINCIPLES.md").read_text(encoding="utf-8")

    assert "## Axioms At A Glance" in axioms_text
    assert axioms_text.index("## Axioms At A Glance") < axioms_text.index("## AX-1 ")
    assert "| ID | Axiom | Anti-axiom |" in axioms_text
    assert axioms_text.count("| AX-") == 12
    assert (
        "| AX-12 | Reflexive accountability / no privileged meta-layer | "
        "Meta artifact exemption. |"
    ) in axioms_text

    assert "## Principles At A Glance" in principles_text
    assert principles_text.index("## Principles At A Glance") < principles_text.index(
        "## P-1 "
    )
    assert "| ID | Principle | Grounding |" in principles_text
    assert principles_text.count("| P-") == 20
    assert (
        "| P-20 | Bind receipts before record authority | AX-11, AX-12. |"
    ) in principles_text


def test_concept_and_mechanism_corpora_are_seeded_with_parity() -> None:
    concept_corpus = build_concept_instance_corpus(MICROCOSM_ROOT)
    mechanism_corpus = build_mechanism_instance_corpus(MICROCOSM_ROOT)
    concept_validation = validate_concept_instance_corpus(MICROCOSM_ROOT)
    mechanism_validation = validate_mechanism_instance_corpus(MICROCOSM_ROOT)
    mechanism_source_count = _mechanism_source_count()
    concept_source_count = _concept_source_count()

    assert concept_corpus["expected_concept_count"] == concept_source_count
    assert concept_corpus["json_instance_count"] == concept_source_count
    assert concept_corpus["parity_status"] == "pass"
    assert concept_corpus["unpopulated_selective_relation_count"] == 0
    assert concept_validation["status"] == "pass"
    assert concept_validation["errors"] == []
    assert mechanism_corpus["expected_mechanism_count"] == mechanism_source_count
    assert mechanism_corpus["json_instance_count"] == mechanism_source_count
    assert mechanism_corpus["parity_status"] == "pass"
    assert mechanism_corpus["without_code_loci_count"] == 0
    assert mechanism_validation["status"] == "pass"
    assert mechanism_validation["errors"] == []

    concept = json.loads(
        (
            MICROCOSM_ROOT
            / "concepts/concept.first_screen_doctrine_effect_frame.json"
        ).read_text(encoding="utf-8")
    )
    assert concept["schema_version"] == "microcosm_concept_instance_v1"
    assert concept["concept_payload"]["source_specimen_id"] == (
        "first_screen_doctrine_effect_frame"
    )
    assert {
        edge["relation_id"] for edge in concept["relationships"]["edges"]
    } == {
        "concept.implements_or_refines.principle",
        "concept.instantiated_by.mechanism",
        "concept.abides_by.axiom",
    }
    assert concept["relationships"]["principle_refs"] == ["P-12", "P-15"]
    assert concept["relationships"]["axiom_refs"] == ["AX-11", "AX-12"]
    assert concept["relationships"]["mechanism_refs"] == [
        "mechanism.cold_reader_route_map.validates_public_first_run_route_map"
    ]
    assert concept["relationships"]["unpopulated_selective_relations"] == []

    resolved_concepts = {
        "concept.executable_doctrine_grammar_standard_bundle": (
            "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
            {"P-8", "P-12", "P-15"},
            {"AX-7", "AX-11", "AX-12"},
        ),
        "concept.standards_meta_diagnostics_bundle": (
            "mechanism.standards_meta_diagnostics.validates_public_standards_meta_diagnostics",
            {"P-7", "P-13", "P-15"},
            {"AX-6", "AX-11", "AX-12"},
        ),
        "concept.voice_to_doctrine_self_improvement_loop_bundle": (
            "mechanism.voice_to_doctrine_self_improvement_loop.validates_public_voice_to_doctrine_self_improvement_loop",
            {"P-8", "P-13", "P-16"},
            {"AX-3", "AX-7", "AX-12"},
        ),
    }
    for concept_id, (mechanism_id, principle_ids, axiom_ids) in resolved_concepts.items():
        concept_path = MICROCOSM_ROOT / "concepts" / f"{concept_id}.json"
        resolved_concept = json.loads(concept_path.read_text(encoding="utf-8"))
        assert resolved_concept["relationships"]["unpopulated_selective_relations"] == []
        assert set(resolved_concept["relationships"]["principle_refs"]) == principle_ids
        assert resolved_concept["relationships"]["mechanism_refs"] == [mechanism_id]
        assert set(resolved_concept["relationships"]["axiom_refs"]) == axiom_ids
        assert {
            edge["relation_id"] for edge in resolved_concept["relationships"]["edges"]
        } == {
            "concept.implements_or_refines.principle",
            "concept.instantiated_by.mechanism",
            "concept.abides_by.axiom",
        }

    family_concepts = {
        concept_id: json.loads(
            (MICROCOSM_ROOT / "concepts" / f"{concept_id}.json").read_text(
                encoding="utf-8"
            )
        )
        for concept_id in FAMILY_CONCEPT_IDS
    }
    assert set(family_concepts) == FAMILY_CONCEPT_IDS
    for concept_id, family_concept in family_concepts.items():
        relationships = family_concept["relationships"]
        assert relationships["unpopulated_selective_relations"] == []
        assert relationships["mechanism_refs"]
        assert {
            edge["target_status"]
            for edge in relationships["edges"]
            if edge["relation_id"] == "concept.instantiated_by.mechanism"
        } == {"resolved_json_instance"}
        assert "organ_family_concept_specimen" == relationships["specimen_role"]

    mechanism = json.loads(
        (
            MICROCOSM_ROOT
            / "mechanisms/mechanism.verifier_lab_kernel.composes_public_formal_math_receipts.json"
        ).read_text(encoding="utf-8")
    )
    assert mechanism["schema_version"] == "microcosm_mechanism_instance_v1"
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/verifier_lab_kernel.py"
    )
    assert any(
        edge["relation_id"] == "mechanism.grounded_in.code_locus"
        and edge["target_status"] == "resolved_code_locus"
        for edge in mechanism["relationships"]["edges"]
    )
    assert any(
        edge["relation_id"] == "mechanism.runs_in.organ"
        and edge["target_id"] == "verifier_lab_kernel"
        and edge["target_status"] == "resolved_registry_or_atlas_target"
        for edge in mechanism["relationships"]["edges"]
    )
    frontend_mechanism = json.loads(
        (
            MICROCOSM_ROOT
            / "mechanisms/mechanism.batch10_frontend_work_market_cockpit_capsule.validates_frontend_work_market_source_open_capsule.json"
        ).read_text(encoding="utf-8")
    )
    assert frontend_mechanism["organ_refs"] == [
        "batch10_frontend_work_market_cockpit_capsule"
    ]
    assert frontend_mechanism["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in frontend_mechanism["relationships"]["edges"]
    } >= {
        (
            "mechanism.runs_in.organ",
            "batch10_frontend_work_market_cockpit_capsule",
            "resolved_registry_or_atlas_target",
        ),
        (
            "mechanism.grounded_in.code_locus",
            "src/microcosm_core/organs/batch10_frontend_work_market_cockpit_capsule.py",
            "resolved_code_locus",
        ),
    }


def test_cold_clone_probe_mechanism_preserves_unresolved_host_residual() -> None:
    mechanism = json.loads(
        (
            MICROCOSM_ROOT
            / "mechanisms/mechanism.cold_clone_probe.validates_public_source_root_bootstrap.json"
        ).read_text(encoding="utf-8")
    )
    relationships = mechanism["relationships"]
    edges = relationships["edges"]

    assert mechanism["organ_refs"] == ["cold_clone_probe"]
    assert relationships["runs_in"] == ["cold_clone_probe"]
    assert any(
        edge["relation_id"] == "mechanism.grounded_in.code_locus"
        and edge["target_id"] == "src/microcosm_core/cold_clone_probe.py"
        and edge["target_status"] == "resolved_code_locus"
        for edge in edges
    )
    assert any(
        edge["relation_id"] == "mechanism.grounds.concept"
        and edge["target_id"] == "concept.entry_and_reveal_route_readiness_bundle"
        and edge["target_status"] == "resolved_json_instance"
        for edge in edges
    )
    assert any(
        edge["relation_id"] == "mechanism.runs_in.organ"
        and edge["target_id"] == "cold_clone_probe"
        and edge["target_status"] == "planned_registry_or_atlas_target"
        and edge["residual_pressure_ref"]
        == "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
        for edge in edges
    )
    assert not any(
        edge["relation_id"] == "mechanism.runs_in.organ"
        and edge["target_id"] == "cold_clone_probe"
        and edge["target_status"] == "resolved_registry_or_atlas_target"
        for edge in edges
    )
    residuals = relationships["unpopulated_selective_relations"]
    assert len(residuals) == 1
    assert residuals[0]["relation_id"] == "mechanism.upstream_of.mechanism"
    assert residuals[0]["pressure_ref"] == (
        "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
    )
    assert residuals[0]["status"] == "residual_pressure"


def test_family_concept_refs_bind_organs_mechanisms_and_paper_modules() -> None:
    family_concepts = _family_concept_map()
    assert set(family_concepts.values()) == FAMILY_CONCEPT_IDS

    organ_atlas = json.loads(
        (MICROCOSM_ROOT / "core/organ_atlas.json").read_text(encoding="utf-8")
    )
    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    paper_registry = json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(
            encoding="utf-8"
        )
    )
    family_by_organ = {row["organ_id"]: row["family"] for row in organ_atlas["organs"]}

    assert {
        family_by_organ["batch12_market_dashboard_read_model_capsule"],
        family_by_organ["batch12_prediction_market_board_capsule"],
    } == {"research_and_science_replays"}
    assert (
        family_by_organ["batch12_release_claim_language_gate"]
        == "import_projection_and_drift"
    )

    for row in organ_atlas["organs"]:
        family_concept = family_concepts[row["family"]]
        assert family_concept in row["concept_refs"]
        organ = json.loads(
            (MICROCOSM_ROOT / "organs" / f"{row['organ_id']}.json").read_text(
                encoding="utf-8"
            )
        )
        assert family_concept in organ["relationships"]["concept_refs"]
        assert any(
            edge["relation_id"] == "organ.instantiates.concept"
            and edge["target_id"] == family_concept
            and edge["target_status"] == "resolved_json_instance"
            for edge in organ["relationships"]["edges"]
        )

    for row in mechanism_registry["mechanisms"]:
        missing_host_organs = sorted(
            {
                organ_id
                for organ_id in row.get("runs_in") or []
                if organ_id not in family_by_organ
            }
        )
        if missing_host_organs:
            expected_planned_hosts = {
                "mechanism.batch7_zenith_macos_capsule.validates_public_zenith_macos_capsule": [
                    "batch7_zenith_macos_capsule"
                ],
                "mechanism.cold_clone_probe.validates_public_source_root_bootstrap": [
                    "cold_clone_probe"
                ],
                "mechanism.first_screen_composition_root.validates_public_first_screen_composition_root": [
                    "runtime_shell"
                ],
                "mechanism.microcosm_axiom_substrate.validates_public_axiom_support_boundary": [
                    "microcosm_axiom_substrate"
                ],
            }
            assert row["id"] in expected_planned_hosts
            assert missing_host_organs == expected_planned_hosts[row["id"]]
        expected_concepts = {
            family_concepts[family_by_organ[organ_id]]
            for organ_id in row.get("runs_in") or []
            if organ_id in family_by_organ
        }
        assert expected_concepts <= set(row["concept_refs"])
        mechanism = json.loads(
            (MICROCOSM_ROOT / "mechanisms" / f"{row['id']}.json").read_text(
                encoding="utf-8"
            )
        )
        assert expected_concepts <= set(mechanism["relationships"]["concept_refs"])
        for concept_id in expected_concepts:
            assert any(
                edge["relation_id"] == "mechanism.grounds.concept"
                and edge["target_id"] == concept_id
                and edge["target_status"] == "resolved_json_instance"
                for edge in mechanism["relationships"]["edges"]
            )

    for row in paper_registry["paper_modules"]:
        expected_concepts = {
            family_concepts[family_by_organ[subject["ref"]]]
            for subject in row.get("subjects") or []
            if subject.get("kind") == "organ"
        }
        assert expected_concepts <= set(row["concept_refs"])
        module_slug = row["id"].split(".", 1)[1]
        paper_module = json.loads(
            (MICROCOSM_ROOT / "paper_modules" / f"{module_slug}.json").read_text(
                encoding="utf-8"
            )
        )
        if paper_module["status"] == "legacy_projection_only":
            assert any(
                residual["relation_id"]
                == "paper_module.explains.organ_or_mechanism"
                and residual["requirement"] == "required"
                for residual in paper_module["relationships"][
                    "unpopulated_selective_relations"
                ]
            )
            continue
        assert expected_concepts <= set(paper_module["relationships"]["concept_refs"])
        for concept_id in expected_concepts:
            assert any(
                edge["relation_id"] == "paper_module.governed_by.concept"
                and edge["target_id"] == concept_id
                and edge["target_status"] == "resolved_json_instance"
                for edge in paper_module["relationships"]["edges"]
            )


def test_organ_corpus_is_seeded_from_atlas_and_registry_with_parity() -> None:
    organ_corpus = build_organ_instance_corpus(MICROCOSM_ROOT)
    organ_validation = validate_organ_instance_corpus(MICROCOSM_ROOT)

    assert organ_corpus["expected_organ_count"] == _organ_source_count()
    assert organ_corpus["json_instance_count"] == _organ_source_count()
    assert organ_corpus["parity_status"] == "pass"
    assert organ_corpus["required_relation_gap_count"] == 0
    assert organ_corpus["unpopulated_selective_relation_count"] > 0
    assert organ_validation["status"] == "pass"
    assert organ_validation["errors"] == []

    organ = json.loads(
        (MICROCOSM_ROOT / "organs/pattern_binding_contract.json").read_text(
            encoding="utf-8"
        )
    )
    assert organ["schema_version"] == "microcosm_organ_instance_v1"
    assert organ["paper_module_ref"] == "paper_modules/pattern_binding_contract.md"
    assert any(
        edge["relation_id"] == "organ.explained_by.paper_module"
        and edge["target_status"] == "resolved_paper_module_ref"
        for edge in organ["relationships"]["edges"]
    )
    assert any(
        edge["relation_id"] == "organ.operates_through.mechanism"
        and edge["target_id"]
        == "mechanism.pattern_binding_contract.validates_public_pattern_bindings"
        and edge["target_status"] == "resolved_json_instance"
        for edge in organ["relationships"]["edges"]
    )
    assert any(
        edge["relation_id"] == "organ.implemented_by.code_locus"
        and edge["target_status"] == "resolved_code_locus"
        for edge in organ["relationships"]["edges"]
    )
    assert any(
        edge["relation_id"] == "organ.constrained_by.axiom"
        and edge["target_id"] == "AX-1"
        for edge in organ["relationships"]["edges"]
    )
    assert not any(
        residual["relation_id"] == "organ.constrained_by.axiom"
        for residual in organ["relationships"]["unpopulated_selective_relations"]
    )

    frontend_organ = json.loads(
        (
            MICROCOSM_ROOT
            / "organs/batch10_frontend_work_market_cockpit_capsule.json"
        ).read_text(encoding="utf-8")
    )
    assert frontend_organ["paper_module_ref"] == (
        "paper_modules/batch10_frontend_work_market_cockpit_capsule.md"
    )
    assert frontend_organ["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in frontend_organ["relationships"]["edges"]
    } >= {
        (
            "organ.explained_by.paper_module",
            "paper_module.batch10_frontend_work_market_cockpit_capsule",
            "resolved_paper_module_ref",
        ),
        (
            "organ.operates_through.mechanism",
            "mechanism.batch10_frontend_work_market_cockpit_capsule.validates_frontend_work_market_source_open_capsule",
            "resolved_json_instance",
        ),
        (
            "organ.implemented_by.code_locus",
            "src/microcosm_core/organs/batch10_frontend_work_market_cockpit_capsule.py",
            "resolved_code_locus",
        ),
    }


def test_paper_module_corpus_is_seeded_from_capsules_and_legacy_markdown_with_parity() -> None:
    corpus = build_paper_module_instance_corpus(MICROCOSM_ROOT)
    validation = validate_paper_module_instance_corpus(MICROCOSM_ROOT)
    capsule_source_count = _paper_module_capsule_source_count()

    assert corpus["expected_paper_module_count"] == corpus["json_instance_count"]
    assert validation["expected_count"] == corpus["expected_paper_module_count"]
    assert validation["actual_count"] == corpus["json_instance_count"]
    assert corpus["json_capsule_backed_count"] == (
        corpus["json_instance_count"] - corpus["legacy_only_count"]
    )
    assert corpus["json_capsule_backed_count"] <= capsule_source_count
    assert corpus["legacy_only_count"] == (
        corpus["json_instance_count"] - corpus["json_capsule_backed_count"]
    )
    assert corpus["legacy_only_count"] == corpus["required_subject_gap_count"]
    assert corpus["parity_status"] == "pass"
    assert corpus["authority_flip_status"] == "not_flipped"
    assert validation["status"] == "pass"
    assert validation["errors"] == []

    capsule_backed = json.loads(
        (MICROCOSM_ROOT / "paper_modules/verifier_lab_kernel.json").read_text(
            encoding="utf-8"
        )
    )
    assert capsule_backed["schema_version"] == "microcosm_paper_module_instance_v1"
    assert capsule_backed["status"] == "active"
    assert capsule_backed["paper_module_payload"]["source_authority"] == "json_capsule"
    assert any(
        edge["relation_id"] == "paper_module.explains.organ_or_mechanism"
        and edge["target_kind"] == "organ"
        and edge["target_id"] == "verifier_lab_kernel"
        and edge["target_status"] == "resolved_json_instance"
        for edge in capsule_backed["relationships"]["edges"]
    )
    assert any(
        edge["relation_id"] == "paper_module.cites.code_locus"
        and edge["target_status"] == "resolved_code_locus"
        for edge in capsule_backed["relationships"]["edges"]
    )

    assert corpus["legacy_only_count"] == 0
    assert corpus["legacy_only_ids"] == []
    assert corpus["required_subject_gap_count"] == 0
    assert corpus["required_subject_gap_ids"] == []
    assert "paper_module.tactic_portfolio_availability_probe" not in set(
        corpus["expected_json_ids"]
    )
    assert not (
        MICROCOSM_ROOT / "paper_modules/tactic_portfolio_availability_probe.json"
    ).exists()

    capsules = json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(
            encoding="utf-8"
        )
    )["paper_modules"]
    tactic_capsule = next(
        row
        for row in capsules
        if row["id"] == "paper_module.tactic_portfolio_availability"
    )
    assert tactic_capsule["legacy_markdown_projection_aliases"] == [
        {
            "path": "paper_modules/tactic_portfolio_availability_probe.md",
            "import_policy": "suppress_legacy_row",
            "reason": (
                "Reader-boundary alias for the same accepted probe organ already "
                "explained by paper_module.tactic_portfolio_availability; importing "
                "it as an independent legacy row double-counts a readiness blocker."
            ),
        }
    ]


def test_skill_corpus_is_seeded_from_markdown_with_required_edges_and_parity() -> None:
    corpus = build_skill_instance_corpus(MICROCOSM_ROOT)
    validation = validate_skill_instance_corpus(MICROCOSM_ROOT)

    assert corpus["expected_skill_count"] == EXPECTED_SKILL_INSTANCE_COUNT
    assert corpus["json_instance_count"] == EXPECTED_SKILL_INSTANCE_COUNT
    assert corpus["required_relation_gap_count"] == 0
    assert (
        corpus["unpopulated_selective_relation_count"]
        == EXPECTED_SKILL_SELECTIVE_RELATION_COUNT
    )
    assert corpus["parity_status"] == "pass"
    assert corpus["authority_flip_status"] == (
        "not_flipped_legacy_markdown_still_source_of_record"
    )
    assert validation["status"] == "pass"
    assert validation["errors"] == []

    cold_start = json.loads(
        (MICROCOSM_ROOT / "skills/cold_start_navigation.json").read_text(
            encoding="utf-8"
        )
    )
    assert cold_start["schema_version"] == "microcosm_skill_instance_v1"
    assert cold_start["triad_role"] == "author"
    assert cold_start["operates_standard"] == "std_microcosm_atlas_route"
    assert cold_start["acts_on_kind"] == "atlas_route"
    assert any(
        edge["relation_id"] == "skill.operates.standard"
        and edge["target_status"] == "resolved_standard_contract"
        for edge in cold_start["relationships"]["edges"]
    )
    assert any(
        edge["relation_id"] == "skill.acts_on.doctrine_kind"
        and edge["target_status"] == "resolved_doctrine_kind_contract"
        for edge in cold_start["relationships"]["edges"]
    )
    assert any(
        edge["relation_id"] == "skill.applies.concept"
        and edge["target_id"] == "concept.first_screen_doctrine_effect_frame"
        and edge["target_status"] == "resolved_json_instance"
        for edge in cold_start["relationships"]["edges"]
    )
    assert any(
        edge["relation_id"] == "skill.uses.mechanism"
        and edge["target_id"]
        == "mechanism.navigation_hologram_route_plane.validates_public_route_plane_bundle"
        and edge["target_status"] == "resolved_json_instance"
        for edge in cold_start["relationships"]["edges"]
    )
    assert cold_start["relationships"]["unpopulated_selective_relations"] == []
    organ_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.organ.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert organ_author["triad_role"] == "author"
    assert organ_author["operates_standard"] == "std_microcosm_organ"
    assert organ_author["acts_on_kind"] == "organ"
    assert organ_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in organ_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_organ",
            "resolved_standard_contract",
        ),
        ("skill.acts_on.doctrine_kind", "organ", "resolved_doctrine_kind_contract"),
        (
            "skill.applies.concept",
            "concept.standards_meta_diagnostics_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.standards_meta_diagnostics.validates_public_standards_meta_diagnostics",
            "resolved_json_instance",
        ),
    }
    mechanism_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.mechanism.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert mechanism_author["triad_role"] == "author"
    assert mechanism_author["operates_standard"] == "std_microcosm_mechanism"
    assert mechanism_author["acts_on_kind"] == "mechanism"
    assert mechanism_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in mechanism_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_mechanism",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "mechanism",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.executable_doctrine_grammar_standard_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
            "resolved_json_instance",
        ),
    }
    for role in ("author", "refine_instance", "refine_standard_and_propagate"):
        executable_grammar_skill = json.loads(
            (
                MICROCOSM_ROOT
                / f"skills/microcosm.executable_doctrine_grammar.{role}.json"
            ).read_text(encoding="utf-8")
        )
        assert executable_grammar_skill["operates_standard"] == (
            "std_microcosm_executable_doctrine_grammar"
        )
        assert executable_grammar_skill["acts_on_kind"] == (
            "executable_doctrine_grammar"
        )
        assert (
            executable_grammar_skill["relationships"][
                "unpopulated_selective_relations"
            ]
            == []
        )
        assert {
            (edge["relation_id"], edge["target_id"], edge["target_status"])
            for edge in executable_grammar_skill["relationships"]["edges"]
        } >= {
            (
                "skill.applies.concept",
                "concept.executable_doctrine_grammar_standard_bundle",
                "resolved_json_instance",
            ),
            (
                "skill.uses.mechanism",
                "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
                "resolved_json_instance",
            ),
        }
    axiom_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.axiom.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert axiom_author["triad_role"] == "author"
    assert axiom_author["operates_standard"] == "std_microcosm_axiom"
    assert axiom_author["acts_on_kind"] == "axiom"
    assert axiom_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in axiom_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_axiom",
            "resolved_standard_contract",
        ),
        ("skill.acts_on.doctrine_kind", "axiom", "resolved_doctrine_kind_contract"),
        (
            "skill.applies.concept",
            "concept.executable_doctrine_grammar_standard_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
            "resolved_json_instance",
        ),
    }
    principle_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.principle.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert principle_author["triad_role"] == "author"
    assert principle_author["operates_standard"] == "std_microcosm_principle"
    assert principle_author["acts_on_kind"] == "principle"
    assert principle_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in principle_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_principle",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "principle",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.executable_doctrine_grammar_standard_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
            "resolved_json_instance",
        ),
    }
    anti_principle_author = json.loads(
        (
            MICROCOSM_ROOT / "skills/microcosm.anti_principle.author.json"
        ).read_text(encoding="utf-8")
    )
    assert anti_principle_author["triad_role"] == "author"
    assert anti_principle_author["operates_standard"] == (
        "std_microcosm_anti_principle"
    )
    assert anti_principle_author["acts_on_kind"] == "anti_principle"
    assert anti_principle_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in anti_principle_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_anti_principle",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "anti_principle",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.executable_doctrine_grammar_standard_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
            "resolved_json_instance",
        ),
    }
    concept_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.concept.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert concept_author["triad_role"] == "author"
    assert concept_author["operates_standard"] == "std_microcosm_concept"
    assert concept_author["acts_on_kind"] == "concept"
    assert concept_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in concept_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_concept",
            "resolved_standard_contract",
        ),
        ("skill.acts_on.doctrine_kind", "concept", "resolved_doctrine_kind_contract"),
        (
            "skill.applies.concept",
            "concept.executable_doctrine_grammar_standard_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
            "resolved_json_instance",
        ),
    }
    paper_module_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.paper_module.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert paper_module_author["triad_role"] == "author"
    assert paper_module_author["operates_standard"] == "std_microcosm_paper_module"
    assert paper_module_author["acts_on_kind"] == "paper_module"
    assert paper_module_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in paper_module_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_paper_module",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "paper_module",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.executable_doctrine_grammar_standard_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
            "resolved_json_instance",
        ),
    }
    skill_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.skill.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert skill_author["triad_role"] == "author"
    assert skill_author["operates_standard"] == "std_microcosm_skill"
    assert skill_author["acts_on_kind"] == "skill"
    assert skill_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in skill_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_skill",
            "resolved_standard_contract",
        ),
        ("skill.acts_on.doctrine_kind", "skill", "resolved_doctrine_kind_contract"),
        (
            "skill.applies.concept",
            "concept.executable_doctrine_grammar_standard_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
            "resolved_json_instance",
        ),
    }
    standard_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.standard.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert standard_author["triad_role"] == "author"
    assert standard_author["operates_standard"] == "std_microcosm_standard"
    assert standard_author["acts_on_kind"] == "standard"
    assert standard_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in standard_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_standard",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "standard",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.executable_doctrine_grammar_standard_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
            "resolved_json_instance",
        ),
    }
    validator_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.validator.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert validator_author["triad_role"] == "author"
    assert validator_author["operates_standard"] == "std_microcosm_validator"
    assert validator_author["acts_on_kind"] == "validator"
    assert validator_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in validator_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_validator",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "validator",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.executable_doctrine_grammar_standard_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
            "resolved_json_instance",
        ),
    }
    receipt_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.receipt.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt_author["triad_role"] == "author"
    assert receipt_author["operates_standard"] == "std_microcosm_receipt"
    assert receipt_author["acts_on_kind"] == "receipt"
    assert receipt_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in receipt_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_receipt",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "receipt",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.standards_meta_diagnostics_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            (
                "mechanism.proof_diagnostic_evidence_spine."
                "validates_ring2_diagnostic_evidence_membrane"
            ),
            "resolved_json_instance",
        ),
    }
    task_ledger_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.task_ledger.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert task_ledger_author["triad_role"] == "author"
    assert task_ledger_author["operates_standard"] == "std_microcosm_task_ledger"
    assert task_ledger_author["acts_on_kind"] == "task_ledger"
    assert task_ledger_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in task_ledger_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_task_ledger",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "task_ledger",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.voice_to_doctrine_self_improvement_loop_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.mission_transaction_work_spine.validates_public_mission_transaction_bundle",
            "resolved_json_instance",
        ),
    }
    work_item_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.work_item.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert work_item_author["triad_role"] == "author"
    assert work_item_author["operates_standard"] == "std_microcosm_work_item"
    assert work_item_author["acts_on_kind"] == "work_item"
    assert work_item_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in work_item_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_work_item",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "work_item",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.voice_to_doctrine_self_improvement_loop_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.mission_transaction_work_spine.validates_public_mission_transaction_bundle",
            "resolved_json_instance",
        ),
    }
    work_ledger_author = json.loads(
        (MICROCOSM_ROOT / "skills/microcosm.work_ledger.author.json").read_text(
            encoding="utf-8"
        )
    )
    assert work_ledger_author["triad_role"] == "author"
    assert work_ledger_author["operates_standard"] == "std_microcosm_work_ledger"
    assert work_ledger_author["acts_on_kind"] == "work_ledger"
    assert work_ledger_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in work_ledger_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_work_ledger",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "work_ledger",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.standards_meta_diagnostics_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.concurrency_mission_control.validates_public_concurrency_mission_control",
            "resolved_json_instance",
        ),
    }
    public_runtime_author = json.loads(
        (
            MICROCOSM_ROOT
            / "skills/microcosm.microcosm_public_runtime_organ_standard.author.json"
        ).read_text(encoding="utf-8")
    )
    assert public_runtime_author["triad_role"] == "author"
    assert (
        public_runtime_author["operates_standard"]
        == "std_microcosm_standards_meta_diagnostics"
    )
    assert public_runtime_author["acts_on_kind"] == "microcosm_public_runtime_organ_standard"
    assert public_runtime_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in public_runtime_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_standards_meta_diagnostics",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "microcosm_public_runtime_organ_standard",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.standards_meta_diagnostics_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.standards_meta_diagnostics.validates_public_standards_meta_diagnostics",
            "resolved_json_instance",
        ),
    }
    runtime_organ_author = json.loads(
        (
            MICROCOSM_ROOT
            / "skills/microcosm.microcosm_runtime_organ.author.json"
        ).read_text(encoding="utf-8")
    )
    assert runtime_organ_author["triad_role"] == "author"
    assert (
        runtime_organ_author["operates_standard"]
        == "std_microcosm_target_shape_tactic_routing_gate"
    )
    assert runtime_organ_author["acts_on_kind"] == "microcosm_runtime_organ"
    assert runtime_organ_author["relationships"]["unpopulated_selective_relations"] == []
    assert {
        (edge["relation_id"], edge["target_id"], edge["target_status"])
        for edge in runtime_organ_author["relationships"]["edges"]
    } >= {
        (
            "skill.operates.standard",
            "std_microcosm_target_shape_tactic_routing_gate",
            "resolved_standard_contract",
        ),
        (
            "skill.acts_on.doctrine_kind",
            "microcosm_runtime_organ",
            "resolved_doctrine_kind_contract",
        ),
        (
            "skill.applies.concept",
            "concept.standards_meta_diagnostics_bundle",
            "resolved_json_instance",
        ),
        (
            "skill.uses.mechanism",
            "mechanism.target_shape_tactic_routing_gate.validates_public_tactic_routing_boundary",
            "resolved_json_instance",
        ),
    }


def test_source_backed_organ_skill_mappings_resolve_neighbours() -> None:
    atlas = json.loads(
        (MICROCOSM_ROOT / "core/organ_atlas.json").read_text(encoding="utf-8")
    )
    organs = {row["organ_id"]: row for row in atlas["organs"]}
    organ_bound_skill_ids: list[str] = []

    for path in sorted((MICROCOSM_ROOT / "skills").glob("*.json")):
        skill = json.loads(path.read_text(encoding="utf-8"))
        edges = skill["relationships"]["edges"]
        route_edges = [
            edge
            for edge in edges
            if edge["relation_id"] == "skill.operates.standard"
            and "core/organ_atlas.json::"
            in edge["justification"]["summary"]
        ]
        if not route_edges:
            continue

        organ_id = skill["acts_on_kind"]
        organ = organs[organ_id]
        expected_mechanism_refs = [
            ref["ref"] if isinstance(ref, dict) else ref
            for ref in organ["mechanism_refs"]
        ]

        assert skill["concept_refs"] == organ["concept_refs"]
        assert skill["mechanism_refs"] == expected_mechanism_refs
        assert skill["relationships"]["unpopulated_selective_relations"] == []
        assert "without inferring from prose, generated projections" in (
            route_edges[0]["justification"]["summary"]
        )
        assert {
            (edge["relation_id"], edge["target_id"], edge["target_status"])
            for edge in edges
        } >= {
            (
                "skill.applies.concept",
                organ["concept_refs"][0],
                "resolved_json_instance",
            ),
            (
                "skill.uses.mechanism",
                expected_mechanism_refs[0],
                "resolved_json_instance",
            ),
        }
        organ_bound_skill_ids.append(skill["id"])

    assert len(organ_bound_skill_ids) == 81


def test_standard_corpus_projects_registry_backed_json_without_greenwashing() -> None:
    corpus = build_standard_instance_corpus(MICROCOSM_ROOT)
    validation = validate_standard_instance_corpus(MICROCOSM_ROOT)

    assert validation["status"] == "pass"
    assert corpus["expected_standard_count"] == EXPECTED_STANDARD_INSTANCE_COUNT
    assert corpus["json_instance_count"] == EXPECTED_STANDARD_INSTANCE_COUNT
    assert corpus["parity_status"] == "pass"
    assert corpus["authority_flip_status"] == "already_json_source_contract_no_markdown_authority_flip"
    assert corpus["legacy_or_draft_contract_count"] > 0
    assert corpus["required_relation_gap_count"] == (
        EXPECTED_STANDARD_REQUIRED_RELATION_GAP_COUNT
    )
    assert corpus["required_relation_gap_instance_count"] == (
        EXPECTED_STANDARD_REQUIRED_EDGE_GAP_COUNT
    )
    assert corpus["governs_kind_resolved_edge_count"] == EXPECTED_STANDARD_INSTANCE_COUNT
    assert corpus["governs_kind_unresolved_edge_count"] == 0
    assert corpus["governs_kind_missing_required_count"] == 0
    assert (
        corpus["triad_skill_resolved_edge_count"]
        == corpus["json_instance_count"] * 3
    )
    assert (
        corpus["triad_skill_planned_unresolved_edge_count"]
        == EXPECTED_STANDARD_TRIAD_PLANNED_UNRESOLVED_EDGE_COUNT
    )
    assert corpus["triad_skill_unresolved_edge_count"] == 0
    assert corpus["triad_skill_missing_required_count"] == 0
    assert (
        corpus["used_by_organ_edge_count"]
        == corpus["used_by_organ_resolved_edge_count"]
        + corpus["used_by_organ_unresolved_edge_count"]
    )
    assert (
        corpus["used_by_organ_unresolved_edge_count"]
        == corpus["used_by_organ_unresolved_detail_count"]
    )
    assert corpus["required_relation_gap_count"] == (
        corpus["triad_skill_planned_unresolved_edge_count"]
        + corpus["triad_skill_unresolved_edge_count"]
        + corpus["triad_skill_missing_required_count"]
    )
    assert corpus["extra_json_ids"] == []
    assert corpus["files_missing_standard_id"] == []


def test_accepted_organ_standards_activate_with_receipt_backing_only() -> None:
    corpus = build_standard_instance_corpus(MICROCOSM_ROOT)
    instances = load_standard_instances(MICROCOSM_ROOT)
    standards_registry = json.loads(
        (MICROCOSM_ROOT / "core/standards_registry.json").read_text(
            encoding="utf-8"
        )
    )
    organ_registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    registry_by_standard_id = {
        row["standard_id"]: row for row in standards_registry["standards"]
    }
    accepted_organs = {
        row["organ_id"]: row
        for row in organ_registry["implemented_organs"]
        if row["status"] == "accepted_current_authority"
    }

    assert corpus["legacy_or_draft_contract_count"] == (
        EXPECTED_SOURCE_LEVEL_STANDARD_LEGACY_COUNT_AFTER_ACCEPTED_ORGAN_ACTIVATION
    )

    for standard_id in ACCEPTED_ORGAN_STANDARD_V2_ACTIVATION_IDS:
        source = json.loads(
            (MICROCOSM_ROOT / "standards" / f"{standard_id}.json").read_text(
                encoding="utf-8"
            )
        )
        instance = instances[standard_id]
        organ_id = source["kind_id"]
        organ = accepted_organs[organ_id]
        registry_row = registry_by_standard_id[standard_id]
        source_basis = source["standard_payload"]["contract_projection_basis"]
        projected_payload = instance["standard_payload"]

        assert source["schema_version"] == "public_microcosm_standard_v2"
        assert source["status"] == "active"
        assert source["source_format"] == "json"
        assert source["source_authority"] == (
            "json_standard_contract_backed_by_accepted_organ_registry_receipt"
        )
        assert registry_row["status"] == "accepted_public_runtime_standard"
        assert projected_payload["contract_projection_status"] == (
            "active_v2_governed_json"
        )
        assert source_basis["organ_authority_receipt"] == (
            organ["current_authority_receipt"]
        )
        assert source_basis["validator_id"] == registry_row["validator_id"]
        assert source_basis["receipt_id"] == registry_row["receipt_id"]
        assert source_basis["organ_evidence_class"] == organ["evidence_class"]
        assert source_basis["organ_evidence_strength_rank"] == (
            organ["evidence_strength_rank"]
        )
        assert source_basis["truth_accounting_bucket"] == (
            organ["truth_accounting_bucket"]
        )
        assert "do not grant release" in source_basis["authority_boundary"]
        if registry_row.get("validator_id"):
            assert registry_row["validator_id"] in source["validator_refs"]
        assert organ["validator_command"] in source["validator_refs"]
        if registry_row.get("receipt_id"):
            assert registry_row["receipt_id"] in source["receipt_refs"]
        assert organ["current_authority_receipt"] in source["receipt_refs"]
        assert source["authority_ceiling"]["accepted_organ_ref"] == (
            f"core/organ_registry.json#{organ_id}"
        )
        assert source["authority_ceiling"]["claim_ceiling_ref"] == (
            f"core/organ_registry.json#{organ_id}.claim_ceiling"
        )
        assert source["authority_ceiling"]["release_authorized"] is False
        assert source["authority_ceiling"]["publication_authorized"] is False
        assert source["authority_ceiling"]["provider_dispatch"] is False
        assert source["authority_ceiling"]["source_mutation_authorized"] is False
        assert source["authority_ceiling"]["private_root_equivalence_claim"] is False
        assert source["authority_ceiling"]["whole_system_correctness_claim"] is False
        assert source["authority_ceiling"]["runtime_correctness_claim"] is False


def test_batch7_pending_capsule_standards_do_not_activate_without_subjects() -> None:
    pending_batch7_standard_ids = {
        "std_microcosm_batch7_zenith_macos_capsule",
    }
    instances = load_standard_instances(MICROCOSM_ROOT)
    standards_registry = json.loads(
        (MICROCOSM_ROOT / "core/standards_registry.json").read_text(
            encoding="utf-8"
        )
    )
    organ_registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    registry_by_standard_id = {
        row["standard_id"]: row for row in standards_registry["standards"]
    }
    accepted_organ_ids = {
        row["organ_id"]
        for row in organ_registry["implemented_organs"]
        if row["status"] == "accepted_current_authority"
    }

    for standard_id in pending_batch7_standard_ids:
        source = json.loads(
            (MICROCOSM_ROOT / "standards" / f"{standard_id}.json").read_text(
                encoding="utf-8"
            )
        )
        instance = instances[standard_id]
        registry_row = registry_by_standard_id[standard_id]
        organ_id = source["kind_id"]
        used_by_edges = [
            edge
            for edge in instance["relationships"]["edges"]
            if edge["relation_id"] == "standard.used_by.organ"
        ]

        assert organ_id not in accepted_organ_ids
        assert source["status"] == "draft"
        assert registry_row["status"] == "draft"
        assert registry_row["receipt_id"] is None
        assert source["relationships"]["registry_integration_status"] == (
            "inventory_only_registered_not_active_v2_promoted"
        )
        assert instance["standard_payload"]["contract_projection_status"] == (
            "legacy_or_draft_standard_contract"
        )
        assert len(used_by_edges) == 1
        used_by_edge = used_by_edges[0]
        assert used_by_edge["target_id"] == organ_id
        assert used_by_edge["target_status"] == "unresolved_json_instance"
        assert used_by_edge["residual_status"] == "typed_residual_pressure"
        assert used_by_edge["residual_requirement"] == "selective"
        assert used_by_edge["residual_gap_class"] == (
            "standard_used_by_organ_target_not_accepted_current_authority"
        )
        assert used_by_edge["residual_pressure_ref"] == (
            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
        )
        assert used_by_edge["justification"]["source_ref"] == (
            f"standards/{standard_id}.json::relationships.used_by_organs[0]"
        )


def test_engine_room_staged_standards_expose_activation_boundary_without_promotion() -> None:
    instances = load_standard_instances(MICROCOSM_ROOT)
    standards_registry = json.loads(
        (MICROCOSM_ROOT / "core/standards_registry.json").read_text(
            encoding="utf-8"
        )
    )
    registry_by_standard_id = {
        row["standard_id"]: row for row in standards_registry["standards"]
    }

    for standard_id in ENGINE_ROOM_STAGED_STANDARD_IDS:
        source = json.loads(
            (MICROCOSM_ROOT / "standards" / f"{standard_id}.json").read_text(
                encoding="utf-8"
            )
        )
        instance = instances[standard_id]
        registry_row = registry_by_standard_id[standard_id]
        boundary = source["activation_boundary"]

        assert source["status"] == "staged_capsule_pending_shared_registry_integration"
        assert source["schema_version"] != "public_microcosm_standard_v2"
        assert registry_row["status"] == (
            "staged_capsule_pending_shared_registry_integration"
        )
        assert registry_row["receipt_id"] is None
        assert source["receipt_contract"]["required"] is False
        assert source["receipt_contract"]["receipt_id"] is None
        assert source["relationships"]["used_by_organs"] == []
        assert instance["relationships"]["used_by_organs"] == []
        assert instance["standard_payload"]["contract_projection_status"] == (
            "legacy_or_draft_standard_contract"
        )
        assert instance["standard_payload"]["receipt_contract_required"] is False
        assert boundary["status"] == "blocked_until_active_v2_admission"
        assert "fixture pass is not active v2 standard support" in (
            boundary["non_laundering_rules"]
        )
        assert "not active public runtime standard" in boundary["claim_ceiling"]


def _assert_planned_standard_triad_pressure(planned_standard_ids: set[str]) -> None:
    instances = load_standard_instances(MICROCOSM_ROOT)
    known_skill_ids = set(load_skill_instances(MICROCOSM_ROOT))

    for standard_id in planned_standard_ids:
        instance = instances[standard_id]
        relationships = instance["relationships"]
        triad_edges = [
            edge
            for edge in relationships["edges"]
            if edge["relation_id"] == "standard.owns_triad.skill"
        ]
        assert len(triad_edges) == 3
        assert relationships["triad_skill_ids"] == [
            f"skill.microcosm.{instance['governs_kind']}.author",
            f"skill.microcosm.{instance['governs_kind']}.refine_instance",
            (
                f"skill.microcosm.{instance['governs_kind']}."
                "refine_standard_and_propagate"
            ),
        ]
        assert {edge["target_status"] for edge in triad_edges} == {
            "planned_unresolved"
        }
        assert {
            residual["relation_id"]
            for residual in relationships["unpopulated_selective_relations"]
        } == set()
        assert set(relationships["triad_skill_ids"]).isdisjoint(known_skill_ids)


def test_core_standard_triad_skill_pressure_resolves_only_when_skill_json_exists() -> None:
    instances = load_standard_instances(MICROCOSM_ROOT)
    for standard_id, governed_kind in {
        "std_microcosm_anti_principle": "anti_principle",
        "std_microcosm_axiom": "axiom",
        "std_microcosm_concept": "concept",
        "std_microcosm_principle": "principle",
        "std_microcosm_organ": "organ",
        "std_microcosm_mechanism": "mechanism",
        "std_microcosm_paper_module": "paper_module",
        "std_microcosm_skill": "skill",
        "std_microcosm_standard": "standard",
        "std_microcosm_validator": "validator",
        "std_microcosm_receipt": "receipt",
        "std_microcosm_task_ledger": "task_ledger",
        "std_microcosm_work_item": "work_item",
        "std_microcosm_work_ledger": "work_ledger",
        "std_microcosm_agent_closeout_faithfulness_audit": "microcosm_public_runtime_organ_standard",
        "std_microcosm_bounded_autonomy_campaign_packet": "microcosm_public_runtime_organ_standard",
        "std_microcosm_cognitive_operator_registry": "microcosm_public_runtime_organ_standard",
        "std_microcosm_cold_reader_route_map": "microcosm_public_runtime_organ_standard",
        "std_microcosm_doctrine_fact_claim_audit": "microcosm_public_runtime_organ_standard",
        "std_microcosm_finance_forecast_evaluation_spine": "microcosm_public_runtime_organ_standard",
        "std_microcosm_routing_anti_patterns_registry": "microcosm_public_runtime_organ_standard",
        "std_microcosm_self_ignorance_coverage_ledger": "microcosm_public_runtime_organ_standard",
        "std_microcosm_standards_meta_diagnostics": "microcosm_public_runtime_organ_standard",
        "std_microcosm_tactic_portfolio_availability_probe": "microcosm_public_runtime_organ_standard",
        "std_microcosm_workstream_driver_recency_coalescer": "microcosm_public_runtime_organ_standard",
        "std_microcosm_provider_context_recipe_budget_policy": "microcosm_runtime_organ",
        "std_microcosm_ring2_premise_retrieval_precision_recall_harness": "microcosm_runtime_organ",
        "std_microcosm_target_shape_tactic_routing_gate": "microcosm_runtime_organ",
    }.items():
        instance = instances[standard_id]
        triad_edges = [
            edge
            for edge in instance["relationships"]["edges"]
            if edge["relation_id"] == "standard.owns_triad.skill"
        ]

        assert instance["relationships"]["triad_skill_ids"] == [
            f"skill.microcosm.{governed_kind}.author",
            f"skill.microcosm.{governed_kind}.refine_instance",
            f"skill.microcosm.{governed_kind}.refine_standard_and_propagate",
        ]
        assert {edge["target_status"] for edge in triad_edges} == {
            "resolved_json_instance"
        }
        assert {
            edge["target_id"] for edge in triad_edges
        } == set(instance["relationships"]["triad_skill_ids"])
        assert instance["relationships"]["unpopulated_selective_relations"] == []


def test_selected_accepted_standard_triad_skills_resolve_from_markdown_sources() -> None:
    instances = load_standard_instances(MICROCOSM_ROOT)
    skill_instances = load_skill_instances(MICROCOSM_ROOT)

    for standard_id in STANDARD_TRIAD_SKILL_BATCH_STANDARD_IDS:
        instance = instances[standard_id]
        triad_edges = [
            edge
            for edge in instance["relationships"]["edges"]
            if edge["relation_id"] == "standard.owns_triad.skill"
        ]
        assert len(triad_edges) == 3
        assert {edge["target_status"] for edge in triad_edges} == {
            "resolved_json_instance"
        }
        assert set(instance["relationships"]["triad_skill_ids"]) == {
            edge["target_id"] for edge in triad_edges
        }
        for skill_id in instance["relationships"]["triad_skill_ids"]:
            skill = skill_instances[skill_id]
            assert skill["operates_standard"] == standard_id
            assert skill["acts_on_kind"] == instance["governs_kind"]
            assert skill["relationships"]["unpopulated_selective_relations"] == []


def test_staged_standard_triad_skill_sources_resolve_without_mechanism_laundering() -> None:
    instances = load_standard_instances(MICROCOSM_ROOT)
    skill_instances = load_skill_instances(MICROCOSM_ROOT)

    for standard_id in STAGED_STANDARD_TRIAD_SKILL_SOURCE_STANDARD_IDS:
        instance = instances[standard_id]
        triad_edges = [
            edge
            for edge in instance["relationships"]["edges"]
            if edge["relation_id"] == "standard.owns_triad.skill"
        ]

        assert len(triad_edges) == 3
        assert {edge["target_status"] for edge in triad_edges} == {
            "resolved_json_instance"
        }
        assert set(instance["relationships"]["triad_skill_ids"]) == {
            edge["target_id"] for edge in triad_edges
        }
        for skill_id in instance["relationships"]["triad_skill_ids"]:
            skill = skill_instances[skill_id]
            residuals = skill["relationships"]["unpopulated_selective_relations"]
            assert skill["operates_standard"] == standard_id
            assert skill["acts_on_kind"] == instance["governs_kind"]
            assert skill["concept_refs"] == [
                {
                    "author": "concept.executable_doctrine_grammar_standard_bundle",
                    "refine_instance": "concept.voice_to_doctrine_self_improvement_loop_bundle",
                    "refine_standard_and_propagate": (
                        "concept.standards_meta_diagnostics_bundle"
                    ),
                }[skill["triad_role"]]
            ]
            if skill["mechanism_refs"]:
                assert all(
                    mechanism_ref.startswith("mechanism.")
                    for mechanism_ref in skill["mechanism_refs"]
                )
                assert not any(
                    residual["relation_id"] == "skill.uses.mechanism"
                    for residual in residuals
                )
            else:
                assert residuals == [
                    {
                        "relation_id": "skill.uses.mechanism",
                        "status": "residual_pressure",
                        "requirement": "selective",
                        "reason": "Skill markdown source does not name used mechanism ids.",
                        "pressure_ref": (
                            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                        ),
                    }
                ]


def test_control_plane_standards_route_triad_skills_resolve_from_markdown_sources() -> None:
    instances = load_standard_instances(MICROCOSM_ROOT)
    known_skill_ids = set(load_skill_instances(MICROCOSM_ROOT))

    for standard_id in {
        "std_microcosm_claim",
        "std_microcosm_omission_receipt",
        "std_microcosm_route_decision",
        "std_microcosm_route_lease",
        "std_microcosm_standards_registry",
    }:
        instance = instances[standard_id]
        triad_edges = [
            edge
            for edge in instance["relationships"]["edges"]
            if edge["relation_id"] == "standard.owns_triad.skill"
        ]
        assert len(triad_edges) == 3
        assert {edge["target_status"] for edge in triad_edges} == {
            "resolved_json_instance"
        }
        assert set(instance["relationships"]["triad_skill_ids"]) <= known_skill_ids


def test_replay_standards_route_triad_skills_resolve_from_markdown_sources() -> None:
    instances = load_standard_instances(MICROCOSM_ROOT)
    replay_standard_ids = {
        "std_microcosm_belief_state_process_reward_replay",
        "std_microcosm_indirect_prompt_injection_information_flow_policy_replay",
        "std_microcosm_mcp_tool_authority_replay",
        "std_microcosm_mechanistic_interpretability_circuit_attribution_replay",
        "std_microcosm_sleeper_memory_poisoning_quarantine_replay",
    }

    assert replay_standard_ids <= STANDARD_TRIAD_SKILL_BATCH_STANDARD_IDS
    for standard_id in replay_standard_ids:
        triad_edges = [
            edge
            for edge in instances[standard_id]["relationships"]["edges"]
            if edge["relation_id"] == "standard.owns_triad.skill"
        ]
        assert len(triad_edges) == 3
        assert {edge["target_status"] for edge in triad_edges} == {
            "resolved_json_instance"
        }


def test_agent_replay_standards_route_triad_skill_pressure_without_resolution() -> None:
    resolved_standard_ids = {
        "std_microcosm_agent_trace",
        "std_microcosm_agentic_vulnerability_discovery_patch_proof_replay",
    }

    assert resolved_standard_ids <= STANDARD_TRIAD_SKILL_BATCH_STANDARD_IDS
    for standard_id in resolved_standard_ids:
        instance = load_standard_instances(MICROCOSM_ROOT)[standard_id]
        triad_edges = [
            edge
            for edge in instance["relationships"]["edges"]
            if edge["relation_id"] == "standard.owns_triad.skill"
        ]
        assert len(triad_edges) == 3
        assert {edge["target_status"] for edge in triad_edges} == {
            "resolved_json_instance"
        }


def test_batch10_frontend_standard_triad_resolves_to_seeded_skill_sources() -> None:
    instance = load_standard_instances(MICROCOSM_ROOT)[
        "std_microcosm_batch10_frontend_work_market_cockpit_capsule"
    ]
    triad_edges = [
        edge
        for edge in instance["relationships"]["edges"]
        if edge["relation_id"] == "standard.owns_triad.skill"
    ]
    assert len(triad_edges) == 3
    assert {edge["target_status"] for edge in triad_edges} == {
        "resolved_json_instance"
    }
    assert {edge["target_id"] for edge in triad_edges} == {
        "skill.microcosm.batch10_frontend_work_market_cockpit_capsule.author",
        "skill.microcosm.batch10_frontend_work_market_cockpit_capsule.refine_instance",
        (
            "skill.microcosm.batch10_frontend_work_market_cockpit_capsule."
            "refine_standard_and_propagate"
        ),
    }


def test_doctrine_projection_uses_computed_support_not_legacy_strength() -> None:
    projection = build_doctrine_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )

    assert projection["status"] == "pass"
    assert projection["axiom_instance_corpus"]["json_instance_count"] == 12
    assert projection["support_truth_calculus"]["status"] == "computed"
    piloted_axioms = projection["support_truth_calculus"]["piloted_axioms"]
    assert set(piloted_axioms) == {f"AX-{i}" for i in range(1, 13)}
    assert piloted_axioms == sorted(piloted_axioms)

    ax1 = next(node for node in projection["nodes"] if node["id"] == "AX-1")
    assert ax1["legacy_witness_strength"]["value"] == "strong"
    assert ax1["claim_ceiling"] == "not_strong_rejection_mapping_unverified"
    assert ax1["claim_ceiling"] != ax1["legacy_witness_strength"]["value"]


def test_doctrine_projection_includes_principle_and_anti_principle_nodes_without_authority_flip() -> None:
    projection = build_doctrine_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )

    assert projection["status"] == "pass"
    assert projection["principle_instance_corpus"]["json_instance_count"] == (
        build_principle_instance_corpus(MICROCOSM_ROOT)["json_instance_count"]
    )
    assert projection["principle_instance_corpus"]["authority_flip_status"] == (
        "not_flipped_legacy_markdown_still_source_of_record"
    )
    assert projection["anti_principle_instance_corpus"]["json_instance_count"] == 17
    assert projection["concept_instance_corpus"]["json_instance_count"] == (
        _concept_source_count()
    )
    assert projection["mechanism_instance_corpus"]["json_instance_count"] == (
        _mechanism_source_count()
    )
    assert projection["organ_instance_corpus"]["json_instance_count"] == (
        _organ_source_count()
    )
    assert projection["paper_module_instance_corpus"]["json_instance_count"] == (
        build_paper_module_instance_corpus(MICROCOSM_ROOT)["json_instance_count"]
    )
    assert projection["paper_module_instance_corpus"]["legacy_only_count"] == (
        projection["paper_module_instance_corpus"]["required_subject_gap_count"]
    )
    assert (
        projection["skill_instance_corpus"]["json_instance_count"]
        == EXPECTED_SKILL_INSTANCE_COUNT
    )
    assert projection["skill_instance_corpus"]["required_relation_gap_count"] == 0
    assert (
        projection["skill_instance_corpus"]["unpopulated_selective_relation_count"]
        == EXPECTED_SKILL_SELECTIVE_RELATION_COUNT
    )
    assert (
        projection["standard_instance_corpus"]["json_instance_count"]
        == EXPECTED_STANDARD_INSTANCE_COUNT
    )
    assert projection["standard_instance_corpus"]["legacy_or_draft_contract_count"] > 0
    assert (
        projection["standard_instance_corpus"]["required_relation_gap_count"]
        == EXPECTED_STANDARD_REQUIRED_RELATION_GAP_COUNT
    )
    nodes = {(node["kind"], node["id"]): node for node in projection["nodes"]}
    assert ("principle", "P-1") in nodes
    assert ("principle", "P-18") in nodes
    assert ("principle", "P-19") in nodes
    assert ("anti_principle", "AP-17") in nodes
    assert ("concept", "concept.first_screen_doctrine_effect_frame") in nodes
    assert (
        "mechanism",
        "mechanism.verifier_lab_kernel.composes_public_formal_math_receipts",
    ) in nodes
    assert ("organ", "pattern_binding_contract") in nodes
    assert ("paper_module", "paper_module.verifier_lab_kernel") in nodes
    assert (
        "paper_module",
        "paper_module.agent_memory_temporal_conflict_replay",
    ) in nodes
    assert ("skill", "skill.cold_start_navigation") in nodes
    assert ("standard", "std_microcosm_axiom") in nodes
    assert ("code_locus", "src/microcosm_core/organs/verifier_lab_kernel.py") in nodes
    assert (
        "receipt",
        "receipts/first_wave/verifier_lab_kernel/verifier_lab_kernel_validation_receipt.json",
    ) in nodes
    code_locus_node = nodes[
        ("code_locus", "src/microcosm_core/organs/verifier_lab_kernel.py")
    ]
    assert code_locus_node["support_status"] == "resolved_path_named_by_source_edges"
    assert code_locus_node["claim_ceiling"] == (
        "path_existence_and_source_edge_routing_only_not_code_correctness_or_runtime_proof"
    )
    assert code_locus_node["relation_ids"] == [
        "mechanism.grounded_in.code_locus",
        "organ.implemented_by.code_locus",
        "paper_module.cites.code_locus",
    ]
    receipt_node = nodes[
        (
            "receipt",
            "receipts/first_wave/verifier_lab_kernel/verifier_lab_kernel_validation_receipt.json",
        )
    ]
    assert receipt_node["support_status"] == "receipt_path_resolved"
    assert receipt_node["claim_ceiling"] == (
        "receipt_ref_presence_or_file_existence_not_proof_runtime_correctness_or_release_authority"
    )
    assert receipt_node["relation_ids"] == [
        "mechanism.evidenced_by.receipt",
        "organ.evidenced_by.receipt",
        "standard.evidenced_by.receipt",
    ]
    assert receipt_node["gap_count"] == 0
    assert any(
        edge["relation_id"] == "mechanism.evidenced_by.receipt"
        and edge["source_id"]
        == "mechanism.verifier_lab_kernel.composes_public_formal_math_receipts"
        and edge["target_id"]
        == "receipts/first_wave/verifier_lab_kernel/verifier_lab_kernel_validation_receipt.json"
        and edge["target_status"] == "resolved_receipt_ref"
        and "does not certify proof" in edge["justification"]["summary"]
        for edge in projection["edges"]
    )
    assert nodes[("principle", "P-3")]["support_status"] == (
        "computed_from_piloted_grounding_axioms"
    )
    assert nodes[("principle", "P-3")]["claim_ceiling"] == (
        "bounded_by_inherited_axiom_support_verdicts"
    )
    assert nodes[("principle", "P-3")]["inherited_support_verdicts"]["AX-2"] == (
        "bound_resolved_strength_uncomputable"
    )
    assert nodes[("principle", "P-3")]["residual_pressure_ref"] is None
    assert nodes[("principle", "P-4")]["support_status"] == (
        "computed_from_piloted_grounding_axioms"
    )
    assert nodes[("principle", "P-4")]["inherited_support_verdicts"]["AX-3"] == (
        "bound_resolved_strength_uncomputable"
    )
    assert nodes[("principle", "P-16")]["support_status"] == (
        "computed_from_piloted_grounding_axioms"
    )
    assert nodes[("principle", "P-16")]["inherited_support_verdicts"]["AX-3"] == (
        "bound_resolved_strength_uncomputable"
    )
    assert nodes[("principle", "P-7")]["support_status"] == (
        "computed_from_piloted_grounding_axioms"
    )
    assert nodes[("principle", "P-7")]["inherited_support_verdicts"]["AX-6"] == (
        "bound_resolved_strength_uncomputable"
    )
    assert nodes[("principle", "P-8")]["support_status"] == (
        "computed_from_piloted_grounding_axioms"
    )
    assert nodes[("principle", "P-8")]["inherited_support_verdicts"]["AX-7"] == (
        "bound_resolved_strength_uncomputable"
    )
    assert nodes[("principle", "P-12")]["support_status"] == (
        "computed_from_piloted_grounding_axioms"
    )
    assert nodes[("principle", "P-12")]["inherited_support_verdicts"]["AX-11"] == (
        "bound_resolved_strength_uncomputable"
    )
    assert nodes[("principle", "P-15")]["support_status"] == (
        "computed_from_piloted_grounding_axioms"
    )
    assert nodes[("principle", "P-15")]["inherited_support_verdicts"]["AX-11"] == (
        "bound_resolved_strength_uncomputable"
    )
    assert nodes[("principle", "P-13")]["support_status"] == (
        "computed_from_piloted_grounding_axioms"
    )
    assert nodes[("principle", "P-13")]["inherited_support_verdicts"]["AX-12"] == (
        "partial_capped_by_layer_debt"
    )
    assert nodes[("anti_principle", "AP-17")]["claim_ceiling"] == (
        "axiom_guard_relation_only_no_failed_principle_mapping"
    )
    assert nodes[("concept", "concept.first_screen_doctrine_effect_frame")][
        "claim_ceiling"
    ] == "entry_packet_specimen_backed_concept_boundary_only"
    assert nodes[
        (
            "mechanism",
            "mechanism.verifier_lab_kernel.composes_public_formal_math_receipts",
        )
    ]["support_status"] == "code_locus_grounded_from_registry"
    assert nodes[("organ", "pattern_binding_contract")]["support_status"] == (
        "required_atlas_links_resolved_not_runtime_correctness_claim"
    )
    batch4_organ = nodes[("organ", "batch4_proof_authority_runtime")]
    assert batch4_organ["support_status"] == (
        "required_atlas_links_resolved_not_runtime_correctness_claim"
    )
    assert batch4_organ["required_edge_gap_relation_ids"] == []
    assert batch4_organ["law_binding_gap_relation_ids"] == []
    assert batch4_organ["resolved_required_edge_count"] == 3
    assert nodes[("paper_module", "paper_module.verifier_lab_kernel")]["support_status"] == (
        "json_capsule_subject_edges_resolved_not_runtime_correctness_claim"
    )
    assert nodes[
        ("paper_module", "paper_module.agent_memory_temporal_conflict_replay")
    ]["support_status"] == (
        "json_capsule_subject_edges_resolved_not_runtime_correctness_claim"
    )
    assert nodes[("skill", "skill.cold_start_navigation")]["support_status"] == (
        "required_skill_edges_resolved_not_workflow_correctness_claim"
    )
    assert nodes[("skill", "skill.cold_start_navigation")]["claim_ceiling"] == (
        "skill_markdown_digest_and_route_mapping_only_not_agent_uptake_or_runtime_correctness"
    )
    assert nodes[("standard", "std_microcosm_axiom")]["support_status"] == (
        "standard_required_edges_resolved_not_contract_completeness_claim"
    )
    assert nodes[("standard", "std_microcosm_axiom")]["claim_ceiling"] == (
        "standard_json_contract_inventory_only_not_completeness_release_or_runtime_proof"
    )
    assert nodes[("standard", "std_microcosm_axiom")][
        "required_edge_gap_relation_ids"
    ] == []
    assert nodes[("standard", "std_microcosm_axiom")][
        "required_edge_gap_count"
    ] == 0
    assert nodes[("standard", "std_microcosm_axiom")][
        "planned_unresolved_triad_skill_ids"
    ] == []
    assert nodes[("standard", "std_microcosm_axiom")][
        "planned_unresolved_triad_skill_roles"
    ] == []
    assert nodes[("standard", "std_microcosm_axiom")][
        "resolved_triad_skill_count"
    ] == 3
    assert any(
        edge["source_kind"] == "principle"
        and edge["source_id"] == "P-1"
        and edge["target_kind"] == "axiom"
        and edge["target_id"] == "AX-1"
        and edge["target_status"] == "resolved_json_instance"
        for edge in projection["edges"]
    )
    assert any(
        edge["source_kind"] == "anti_principle"
        and edge["source_id"] == "AP-17"
        and edge["target_kind"] == "axiom"
        and edge["target_id"] == "AX-11"
        for edge in projection["edges"]
    )
    assert any(
        edge["source_kind"] == "principle"
        and edge["source_id"] == "P-1"
        and edge["relation_id"] == "principle.governs.mechanism"
        and edge["target_kind"] == "mechanism"
        and edge["target_status"] == "resolved_json_instance"
        for edge in projection["edges"]
    )
    assert any(
        edge["source_kind"] == "anti_principle"
        and edge["source_id"] == "AP-17"
        and edge["relation_id"] == "anti_principle.negates_failure_of.principle"
        and edge["target_kind"] == "principle"
        and edge["target_id"] == "P-15"
        and edge["target_status"] == "resolved_json_instance"
        for edge in projection["edges"]
    )
    assert any(
        edge["source_kind"] == "organ"
        and edge["source_id"] == "pattern_binding_contract"
        and edge["relation_id"] == "organ.operates_through.mechanism"
        and edge["target_status"] == "resolved_json_instance"
        for edge in projection["edges"]
    )
    assert any(
        edge["source_kind"] == "paper_module"
        and edge["source_id"] == "paper_module.verifier_lab_kernel"
        and edge["target_kind"] == "organ"
        and edge["target_id"] == "verifier_lab_kernel"
        and edge["target_status"] == "resolved_json_instance"
        for edge in projection["edges"]
    )
    assert any(
        edge["source_kind"] == "skill"
        and edge["source_id"] == "skill.cold_start_navigation"
        and edge["relation_id"] == "skill.applies.concept"
        and edge["target_id"] == "concept.first_screen_doctrine_effect_frame"
        and edge["target_status"] == "resolved_json_instance"
        for edge in projection["edges"]
    )
    assert any(
        edge["source_kind"] == "standard"
        and edge["source_id"] == "std_microcosm_axiom"
        and edge["relation_id"] == "standard.governs.doctrine_kind"
        and edge["target_id"] == "axiom"
        and edge["target_status"] == "resolved_doctrine_kind_contract"
        for edge in projection["edges"]
    )
    assert any(
        edge["source_kind"] == "standard"
        and edge["source_id"] == "std_microcosm_axiom"
        and edge["relation_id"] == "standard.owns_triad.skill"
        and edge["target_id"] == "skill.microcosm.axiom.author"
        and edge["target_status"] == "resolved_json_instance"
        for edge in projection["edges"]
    )


def test_doctrine_lattice_health_routes_gaps_without_weakening_doctrine() -> None:
    health = build_lattice_health(MICROCOSM_ROOT)

    assert health["status"] == "deficit"
    assert health["axioms"]["json_instance_count"] == 12
    assert health["axioms"]["parity_status"] == "pass"
    assert health["principles"]["json_instance_count"] == (
        build_principle_instance_corpus(MICROCOSM_ROOT)["json_instance_count"]
    )
    assert health["principles"]["parity_status"] == "pass"
    assert health["anti_principles"]["json_instance_count"] == 17
    assert health["anti_principles"]["parity_status"] == "pass"
    assert health["concepts"]["json_instance_count"] == _concept_source_count()
    assert health["concepts"]["parity_status"] == "pass"
    assert health["mechanisms"]["json_instance_count"] == _mechanism_source_count()
    assert health["mechanisms"]["parity_status"] == "pass"
    assert health["organs"]["json_instance_count"] == _organ_source_count()
    assert health["organs"]["parity_status"] == "pass"
    assert health["paper_modules"]["json_instance_count"] == (
        build_paper_module_instance_corpus(MICROCOSM_ROOT)["json_instance_count"]
    )
    assert health["paper_modules"]["json_instance_parity_status"] == "pass"
    assert health["paper_modules"]["json_capsule_backed_count"] == (
        health["paper_modules"]["json_capsule_count"]
    )
    assert health["paper_modules"]["legacy_only_count"] == (
        health["paper_modules"]["legacy_only_json_instance_count"]
    )
    assert health["paper_modules"]["legacy_only_json_instance_count"] == (
        health["paper_modules"]["required_subject_gap_count"]
    )
    assert health["skills"]["json_instance_count"] == EXPECTED_SKILL_INSTANCE_COUNT
    assert health["skills"]["json_instance_parity_status"] == "pass"
    assert health["skills"]["required_edge_gap_count"] == 0
    assert (
        health["skills"]["unpopulated_selective_edge_count"]
        == EXPECTED_SKILL_SELECTIVE_NODE_COUNT
    )
    assert (
        health["standards"]["json_instance_count"]
        == EXPECTED_STANDARD_INSTANCE_COUNT
    )
    assert health["standards"]["json_instance_parity_status"] == "pass"
    assert health["standards"]["legacy_or_draft_contract_count"] > 0
    assert (
        health["standards"]["required_edge_gap_count"]
        == EXPECTED_STANDARD_REQUIRED_EDGE_GAP_COUNT
    )
    assert (
        health["standards"]["required_relation_gap_count"]
        == EXPECTED_STANDARD_TRIAD_PLANNED_UNRESOLVED_EDGE_COUNT
    )
    assert (
        health["standards"]["governs_kind_resolved_edge_count"]
        == EXPECTED_STANDARD_INSTANCE_COUNT
    )
    assert (
        health["standards"]["triad_skill_resolved_edge_count"]
        == EXPECTED_STANDARD_TRIAD_RESOLVED_EDGE_COUNT
    )
    assert (
        health["standards"]["triad_skill_planned_unresolved_edge_count"]
        == EXPECTED_STANDARD_TRIAD_PLANNED_UNRESOLVED_EDGE_COUNT
    )
    assert health["standards"]["triad_skill_missing_required_count"] == 0
    assert (
        health["standards"]["used_by_organ_edge_count"]
        == EXPECTED_STANDARD_USED_BY_ORGAN_EDGE_COUNT
    )
    assert (
        health["standards"]["used_by_organ_resolved_edge_count"]
        == EXPECTED_STANDARD_USED_BY_ORGAN_RESOLVED_EDGE_COUNT
    )
    assert (
        health["standards"]["used_by_organ_unresolved_edge_count"]
        == EXPECTED_STANDARD_USED_BY_ORGAN_UNRESOLVED_EDGE_COUNT
    )
    assert (
        health["standards"]["used_by_organ_unresolved_detail_count"]
        == EXPECTED_STANDARD_USED_BY_ORGAN_UNRESOLVED_EDGE_COUNT
    )
    assert health["standards"]["unregistered_standard_file_count"] == 0
    assert health["standards"]["missing_standard_id_file_count"] == 0
    unresolved_standard_organ_refs = {
        (row["standard_id"], row["target_organ_id"], row["target_status"])
        for row in health["standards"]["used_by_organ_unresolved_details"]
    }
    assert unresolved_standard_organ_refs >= {
        (
            "std_microcosm_external_candidate",
            "external_boundary_anti_corruption_runtime",
            "unresolved_json_instance",
        ),
        (
            "std_microcosm_external_candidate",
            "formal_prover_lab_evaluation_suborgan",
            "unresolved_json_instance",
        ),
    }
    standard_gap_details = {
        row["standard_id"]: row
        for row in health["standards"]["required_relation_gap_details"]
    }
    assert (
        health["standards"]["required_relation_gap_detail_count"]
        == EXPECTED_STANDARD_REQUIRED_RELATION_GAP_DETAIL_COUNT
    )
    assert set(standard_gap_details) == set(health["standards"]["required_edge_gaps"])
    assert "std_microcosm_anti_principle" not in standard_gap_details
    assert "std_microcosm_axiom" not in standard_gap_details
    assert "std_microcosm_concept" not in standard_gap_details
    assert "std_microcosm_paper_module" not in standard_gap_details
    assert "std_microcosm_principle" not in standard_gap_details
    assert "std_microcosm_skill" not in standard_gap_details
    assert "std_microcosm_standard" not in standard_gap_details
    assert "std_microcosm_validator" not in standard_gap_details
    assert "std_microcosm_receipt" not in standard_gap_details
    assert "std_microcosm_task_ledger" not in standard_gap_details
    assert "std_microcosm_work_item" not in standard_gap_details
    assert "std_microcosm_work_ledger" not in standard_gap_details
    assert "std_microcosm_batch10_frontend_work_market_cockpit_capsule" not in (
        standard_gap_details
    )
    assert not {
        "std_microcosm_agent_closeout_faithfulness_audit",
        "std_microcosm_bounded_autonomy_campaign_packet",
        "std_microcosm_cognitive_operator_registry",
        "std_microcosm_cold_reader_route_map",
        "std_microcosm_doctrine_fact_claim_audit",
        "std_microcosm_finance_forecast_evaluation_spine",
        "std_microcosm_routing_anti_patterns_registry",
        "std_microcosm_self_ignorance_coverage_ledger",
        "std_microcosm_standards_meta_diagnostics",
        "std_microcosm_tactic_portfolio_availability_probe",
        "std_microcosm_workstream_driver_recency_coalescer",
        "std_microcosm_provider_context_recipe_budget_policy",
        "std_microcosm_ring2_premise_retrieval_precision_recall_harness",
        "std_microcosm_target_shape_tactic_routing_gate",
    }.intersection(standard_gap_details)
    assert health["principles"]["unpopulated_governs_edge_count"] == 0
    assert health["principles"]["unpopulated_governs_edges"] == []
    assert health["anti_principles"]["unpopulated_negates_edge_count"] == 0
    assert health["anti_principles"]["unpopulated_negates_edges"] == []
    residual_gap_classes = {
        row["gap_class"] for row in health["residual_pressure"]
    }
    assert "principle_and_anti_principle_edge_population" not in (
        residual_gap_classes
    )
    assert {
        "doctrine_lattice_population",
        "concept_and_mechanism_edge_population",
        "organ_required_and_selective_edge_population",
        "paper_module_json_capsule_and_edge_population",
        "standard_contract_and_triad_population",
    } <= residual_gap_classes
    if health["skills"]["unpopulated_selective_edge_count"]:
        assert "skill_selective_edge_population" in residual_gap_classes
    assert "evidence_walkability_population" not in residual_gap_classes
    for row in health["residual_pressure"]:
        assert row["pressure_ref"] == (
            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
        )
        assert row["reentry_condition"]
    assert health["concepts"]["unpopulated_selective_edge_count"] == 0
    assert health["concepts"]["unpopulated_selective_edges"] == []
    assert health["concepts"]["support_scope"] == (
        "concept specimen parity and typed selective neighbours are computed from source-named ids; "
        "unresolved or omitted selective edges remain residual pressure"
    )
    assert health["mechanisms"]["without_code_loci_count"] == 0
    code_loci_health = health["code_loci"]
    assert code_loci_health["known_count"] == code_loci_health["resolved_path_count"]
    assert code_loci_health["known_count"] >= 81
    assert code_loci_health["planned_or_unresolved_path_count"] == 0
    assert code_loci_health["counts_by_support_status"] == {
        "resolved_path_named_by_source_edges": code_loci_health["known_count"]
    }
    assert code_loci_health["inbound_edge_count"] >= code_loci_health["known_count"]
    assert code_loci_health["relation_ids"] == [
        "mechanism.grounded_in.code_locus",
        "organ.implemented_by.code_locus",
        "paper_module.cites.code_locus",
    ]
    assert (
        "path existence is not code correctness"
        in code_loci_health["support_scope"]
    )
    receipt_health = health["receipts"]
    receipt_support_counts = receipt_health["counts_by_support_status"]
    assert receipt_health["known_count"] == sum(receipt_support_counts.values())
    assert receipt_health["edge_count"] >= receipt_health["known_count"]
    assert receipt_health["resolved_path_count"] == receipt_support_counts[
        "receipt_path_resolved"
    ]
    assert receipt_health["symbolic_id_count"] == receipt_support_counts[
        "symbolic_receipt_id_declared_not_file_resolved"
    ]
    assert receipt_health["declared_ref_count"] == receipt_support_counts[
        "declared_receipt_ref_not_file_resolved"
    ]
    assert receipt_health["nonlocal_ref_count"] == receipt_support_counts[
        "nonlocal_receipt_path_resolved_not_public_evidence"
    ]
    assert receipt_health["resolved_nonlocal_ref_count"] == receipt_health["nonlocal_ref_count"]
    assert receipt_health["unresolved_nonlocal_ref_count"] == 0
    assert receipt_health["missing_ref_count"] == 0
    assert receipt_health["relation_ids"] == [
        "anti_principle.evidenced_by.receipt",
        "axiom.evidenced_by.receipt",
        "mechanism.evidenced_by.receipt",
        "organ.evidenced_by.receipt",
        "principle.evidenced_by.receipt",
        "standard.evidenced_by.receipt",
    ]
    assert (
        "receipt existence is not proof"
        in receipt_health["support_scope"]
    )
    projection = build_doctrine_projection(MICROCOSM_ROOT)
    receipt_nodes = {
        node["id"]: node
        for node in projection["nodes"]
        if node.get("kind") == "receipt"
    }
    assert (
        receipt_nodes[
            "receipts/preflight/navigation_hologram_route_plane.json"
        ]["support_status"]
        == "receipt_path_resolved"
    )
    assert (
        receipt_nodes[
            (
                "receipts/runtime_shell/demo_project/organs/"
                "batch12_release_claim_language_gate/"
                "exported_batch12_release_claim_language_gate_bundle_validation_result.json"
            )
        ]["support_status"]
        == "receipt_path_resolved"
    )
    nonlocal_receipt = receipt_nodes[
        "state/microcosm_portfolio/reconstruction/"
        "navigation_hologram_route_plane_current_authority_build_receipt_v1.json"
    ]
    assert (
        nonlocal_receipt["support_status"]
        == "nonlocal_receipt_path_resolved_not_public_evidence"
    )
    assert nonlocal_receipt["gap_count"] == 0
    assert (
        "not_public_file_evidence"
        in nonlocal_receipt["claim_ceiling"]
    )
    assert health["axioms"]["not_obligation_piloted"] == []
    assert health["axioms"]["support_frontier_count"] == 12
    assert health["principles"]["obligation_level_supported_count"] == (
        build_principle_instance_corpus(MICROCOSM_ROOT)["json_instance_count"]
    )
    assert health["principles"]["unsupported_at_obligation_level"] == []
    assert "AX-4" not in health["axioms"]["not_obligation_piloted"]
    assert "AX-5" not in health["axioms"]["not_obligation_piloted"]
    assert "AX-9" not in health["axioms"]["not_obligation_piloted"]
    assert "AX-10" not in health["axioms"]["not_obligation_piloted"]
    assert "AX-11" not in health["axioms"]["not_obligation_piloted"]
    assert "AX-12" not in health["axioms"]["not_obligation_piloted"]
    assert "AX-2" not in health["axioms"]["not_obligation_piloted"]
    assert "AX-3" not in health["axioms"]["not_obligation_piloted"]
    assert "AX-6" not in health["axioms"]["not_obligation_piloted"]
    assert "AX-7" not in health["axioms"]["not_obligation_piloted"]
    assert "P-5" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-6" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-10" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-11" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-12" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-13" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-15" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-3" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-4" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-7" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-8" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-16" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-17" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-18" not in health["principles"]["unsupported_at_obligation_level"]
    assert "P-19" not in health["principles"]["unsupported_at_obligation_level"]
    assert health["organs"]["unconstrained_by_axiom_count"] == 0
    assert health["organs"]["unconstrained_by_axiom"] == []
    assert "batch6_unsurfaced_primitives_capsule" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "agent_benchmark_integrity_anti_gaming_replay" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "agent_closeout_faithfulness_audit" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "agent_memory_temporal_conflict_replay" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "agent_monitor_redteam_falsification_replay" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "agent_route_observability_runtime" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "agent_sandbox_policy_escape_replay" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "agentic_vulnerability_discovery_patch_proof_replay" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "formal_math_lean_proof_witness" not in health["organs"]["unconstrained_by_axiom"]
    assert "certificate_kernel_execution_lab" not in health["organs"]["unconstrained_by_axiom"]
    assert "agent_sabotage_scheming_monitor_replay" not in health["organs"]["unconstrained_by_axiom"]
    assert "concurrency_mission_control" not in health["organs"]["unconstrained_by_axiom"]
    assert "prediction_oracle_reconciliation" not in health["organs"]["unconstrained_by_axiom"]
    assert "self_ignorance_coverage_ledger" not in health["organs"]["unconstrained_by_axiom"]
    assert "tool_server_pressure_inventory" not in health["organs"]["unconstrained_by_axiom"]
    assert "voice_to_doctrine_self_improvement_loop" not in health["organs"]["unconstrained_by_axiom"]
    assert "workstream_driver_recency_coalescer" not in health["organs"]["unconstrained_by_axiom"]
    resolved_import_organs = {
        "batch4_proof_authority_runtime",
        "batch8_station_surface_atlas_layout_port",
    }
    assert health["organs"]["required_edge_gap_count"] == 0
    gap_details = {
        row["organ_id"]: row
        for row in health["organs"]["required_edge_gap_details"]
    }
    assert health["organs"]["required_edge_gap_detail_count"] == 0
    assert gap_details == {}
    assert "batch6_unsurfaced_primitives_capsule" not in gap_details
    assert set(gap_details).isdisjoint(resolved_import_organs)
    assert (
        health["organs"]["unpopulated_selective_edge_count"]
        == EXPECTED_ORGAN_SELECTIVE_RELATION_COUNT
    )
    assert health["paper_modules"]["unpopulated_selective_edge_count"] == len(
        health["paper_modules"]["unpopulated_selective_edges"]
    )
    assert health["paper_modules"]["unpopulated_selective_edge_count"] > 0
    assert health["residual_pressure"][0]["pressure_ref"] == (
        "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
    )


def test_axiom_witness_organs_are_bound_to_source_routing_laws() -> None:
    routing = json.loads(
        (MICROCOSM_ROOT / "core/axiom_organ_routing.json").read_text(
            encoding="utf-8"
        )
    )
    expected: dict[str, dict[str, set[str]]] = {}
    for axiom in routing["rows"]:
        for organ_id in axiom.get("witness_organs") or []:
            expected.setdefault(
                organ_id,
                {"axiom_refs": set(), "principle_refs": set()},
            )
            expected[organ_id]["axiom_refs"].add(axiom["axiom_id"])
            expected[organ_id]["principle_refs"].update(
                axiom.get("principle_ids") or []
            )

    assert len(expected) >= 18
    for organ_id, refs in expected.items():
        atlas_index, organ = _organ_atlas_indexed_row(organ_id)
        assert refs["axiom_refs"].issubset(set(organ.get("axiom_refs") or []))
        assert refs["principle_refs"].issubset(set(organ.get("principle_refs") or []))


def test_formal_math_organs_are_bound_to_checker_and_refusal_laws() -> None:
    expected_axioms = {"AX-1", "AX-2", "AX-5", "AX-7"}
    expected_principles = {"P-1", "P-2", "P-3", "P-6", "P-8"}
    target_organs = {
        "formal_evidence_cell_anchor_resolver",
        "formal_math_premise_retrieval",
        "formal_math_readiness_gate",
        "formal_math_verifier_trace_repair_loop",
        "lean_std_premise_index",
        "mathematical_strategy_atlas_hypothesis_scorer",
        "provider_context_recipe_budget_policy",
        "ring2_premise_retrieval_precision_recall_harness",
        "tactic_portfolio_availability_probe",
        "target_shape_tactic_routing_gate",
        "undeclared_library_prior_symbol_classifier",
    }

    health = build_lattice_health(MICROCOSM_ROOT)
    coverage = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )

    assert target_organs.isdisjoint(set(health["organs"]["unconstrained_by_axiom"]))
    for organ_id in target_organs:
        _assert_organ_law_refs_resolved(
            organ_id,
            axiom_refs=expected_axioms,
            principle_refs=expected_principles,
        )


def test_batch_import_organs_are_bound_to_digest_and_provenance_laws() -> None:
    expected_axioms = {"AX-1", "AX-4", "AX-5", "AX-8"}
    expected_principles = {"P-1", "P-2", "P-5", "P-6", "P-9", "P-15"}
    target_organs = {
        "batch10_cold_eval_honesty_capsule",
        "batch10_governance_compilers_capsule",
        "batch10_live_source_drift_capsule",
        "batch11_saturation_engines_capsule",
        "batch12_market_dashboard_read_model_capsule",
        "batch12_prediction_market_board_capsule",
        "batch8_audio_level_rms_port",
        "batch8_compliance_pipeline_capsule",
        "batch8_policy_engines_capsule",
        "batch8_structural_theses_capsule",
        "batch8_tools_tail_primitives_capsule",
        "batch8_validator_checker_capsule",
        "batch9_macro_engines_capsule",
    }

    health = build_lattice_health(MICROCOSM_ROOT)

    assert target_organs.isdisjoint(set(health["organs"]["unconstrained_by_axiom"]))
    for organ_id in target_organs:
        _assert_organ_law_refs_resolved(
            organ_id,
            axiom_refs=expected_axioms,
            principle_refs=expected_principles,
        )


def test_batch7_organs_are_bound_to_digest_and_provenance_laws() -> None:
    expected_axioms = {"AX-1", "AX-4", "AX-5", "AX-8"}
    expected_principles = {"P-1", "P-2", "P-5", "P-6", "P-9", "P-15"}
    target_organs = {
        "batch7_macro_engines_capsule",
        "batch7_station_runtime_capsule",
    }

    health = build_lattice_health(MICROCOSM_ROOT)

    assert target_organs.isdisjoint(set(health["organs"]["unconstrained_by_axiom"]))
    for organ_id in target_organs:
        _assert_organ_law_refs_resolved(
            organ_id,
            axiom_refs=expected_axioms,
            principle_refs=expected_principles,
        )


def test_engine_room_demo_is_bound_to_public_boundary_laws() -> None:
    expected_axioms = {"AX-1", "AX-4", "AX-5", "AX-7", "AX-8", "AX-11"}
    expected_principles = {
        "P-1",
        "P-2",
        "P-3",
        "P-5",
        "P-6",
        "P-8",
        "P-9",
        "P-12",
        "P-15",
    }

    health = build_lattice_health(MICROCOSM_ROOT)

    assert "engine_room_demo" not in health["organs"]["unconstrained_by_axiom"]
    _assert_organ_law_refs_resolved(
        "engine_room_demo",
        axiom_refs=expected_axioms,
        principle_refs=expected_principles,
    )


def test_public_reveal_walkthrough_is_bound_to_public_boundary_laws() -> None:
    expected_axioms = {"AX-1", "AX-4", "AX-5", "AX-7", "AX-8", "AX-11"}
    expected_principles = {
        "P-1",
        "P-2",
        "P-3",
        "P-5",
        "P-6",
        "P-8",
        "P-9",
        "P-12",
        "P-15",
    }

    health = build_lattice_health(MICROCOSM_ROOT)
    coverage = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )

    assert "public_reveal_walkthrough" not in health["organs"]["unconstrained_by_axiom"]
    assert (
        coverage["deficit_summary"]["organ_unpopulated_selective_relation_count"]
        == EXPECTED_ORGAN_SELECTIVE_RELATION_COUNT
    )
    _assert_organ_law_refs_resolved(
        "public_reveal_walkthrough",
        axiom_refs=expected_axioms,
        principle_refs=expected_principles,
    )


def test_mechanism_upstream_edges_back_source_organ_wiring_wave() -> None:
    expected_new_wires = {
        "agent_route_observability_runtime": {"bounded_autonomy_campaign_packet"},
        "bridge_phase_continuity_runtime": {
            "concurrency_mission_control",
            "workstream_driver_recency_coalescer",
        },
        "cold_reader_route_map": {
            "doctrine_fact_claim_audit",
            "pattern_assimilation_step",
            "routing_anti_patterns_registry",
            "self_ignorance_coverage_ledger",
            "voice_to_doctrine_self_improvement_loop",
        },
        "corpus_readiness_mathlib_absence_gate": {"verifier_lab_kernel"},
        "doctrine_fact_claim_audit": {"self_ignorance_coverage_ledger"},
        "durable_agent_work_landing_replay": {"workstream_driver_recency_coalescer"},
        "executable_doctrine_grammar": {"doctrine_fact_claim_audit"},
        "formal_evidence_cell_anchor_resolver": {"proof_diagnostic_evidence_spine"},
        "formal_math_lean_proof_witness": {
            "formal_math_premise_retrieval",
            "formal_math_readiness_gate",
            "proof_diagnostic_evidence_spine",
            "verifier_lab_kernel",
        },
        "formal_math_premise_retrieval": {"verifier_lab_kernel"},
        "formal_math_readiness_gate": {
            "macro_projection_import_protocol",
            "tactic_portfolio_availability_probe",
        },
        "formal_math_verifier_trace_repair_loop": {
            "formal_evidence_cell_anchor_resolver",
            "proof_diagnostic_evidence_spine",
            "verifier_lab_kernel",
        },
        "lean_std_premise_index": {
            "mathematical_strategy_atlas_hypothesis_scorer",
            "verifier_lab_kernel",
        },
        "materials_chemistry_closed_loop_lab_safety_replay": {
            "spatial_world_model_counterfactual_simulation_replay",
        },
        "mission_transaction_work_spine": {
            "bounded_autonomy_campaign_packet",
            "concurrency_mission_control",
            "macro_projection_import_protocol",
            "tool_server_pressure_inventory",
        },
        "navigation_hologram_route_plane": {
            "doctrine_fact_claim_audit",
            "macro_projection_import_protocol",
            "self_ignorance_coverage_ledger",
            "voice_to_doctrine_self_improvement_loop",
        },
        "pattern_binding_contract": {
            "macro_projection_import_protocol",
            "pattern_assimilation_step",
            "voice_to_doctrine_self_improvement_loop",
        },
        "proof_derived_governed_mutation_authorization": {
            "batch12_release_claim_language_gate",
        },
        "proof_diagnostic_evidence_spine": {"verifier_lab_kernel"},
        "public_reveal_walkthrough": {
            "batch12_release_claim_language_gate",
            "mechanistic_interpretability_circuit_attribution_replay",
        },
        "research_replication_rubric_artifact_replay": {
            "mechanistic_interpretability_circuit_attribution_replay",
            "prediction_oracle_reconciliation",
            "spatial_world_model_counterfactual_simulation_replay",
        },
        "voice_to_doctrine_self_improvement_loop": {"pattern_assimilation_step"},
        "world_model_projection_drift_control_room": {
            "mechanistic_interpretability_circuit_attribution_replay",
            "prediction_oracle_reconciliation",
            "spatial_world_model_counterfactual_simulation_replay",
            "tool_server_pressure_inventory",
        },
    }
    atlas = json.loads(
        (MICROCOSM_ROOT / "core/organ_atlas.json").read_text(encoding="utf-8")
    )
    mechanisms = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )["mechanisms"]
    organ_by_id = {row["organ_id"]: row for row in atlas["organs"]}
    mechanism_by_id = {row["id"]: row for row in mechanisms}
    hosted_mechanism_ids: dict[str, set[str]] = {
        organ_id: set() for organ_id in organ_by_id
    }
    mechanism_hosts: dict[str, set[str]] = {}

    for mechanism in mechanisms:
        mechanism_id = mechanism["id"]
        for host in mechanism.get("runs_in") or []:
            hosted_mechanism_ids.setdefault(host, set()).add(mechanism_id)
            mechanism_hosts.setdefault(mechanism_id, set()).add(host)
        for host in mechanism.get("organ_refs") or []:
            hosted_mechanism_ids.setdefault(host, set()).add(mechanism_id)
            mechanism_hosts.setdefault(mechanism_id, set()).add(host)
    for organ_id, organ in organ_by_id.items():
        for ref in organ.get("mechanism_refs") or []:
            mechanism_id = ref["ref"] if isinstance(ref, dict) else ref
            hosted_mechanism_ids.setdefault(organ_id, set()).add(mechanism_id)
            mechanism_hosts.setdefault(mechanism_id, set()).add(organ_id)

    asserted_edge_count = 0
    for source_organ, target_organs in expected_new_wires.items():
        atlas_row = organ_by_id[source_organ]
        assert target_organs.issubset(set(atlas_row["wires_to"]))
        assert "core/mechanism_sources.json upstream_of rows" in (
            atlas_row["wiring_note"]
        )
        assert "not live invocation" in atlas_row["wiring_note"]

        organ_instance = json.loads(
            (MICROCOSM_ROOT / "organs" / f"{source_organ}.json").read_text(
                encoding="utf-8"
            )
        )
        residual_ids = {
            residual["relation_id"]
            for residual in organ_instance["relationships"][
                "unpopulated_selective_relations"
            ]
        }
        assert "organ.wires_to.organ" not in residual_ids

        source_mechanisms = hosted_mechanism_ids[source_organ]
        for target_organ in target_organs:
            target_mechanisms = hosted_mechanism_ids[target_organ]
            source_backing_edges = []
            for source_mechanism in source_mechanisms:
                mechanism = mechanism_by_id[source_mechanism]
                upstream = set(mechanism.get("upstream") or []) | set(
                    mechanism.get("upstream_of") or []
                )
                for target_mechanism in target_mechanisms:
                    if target_mechanism in upstream:
                        source_backing_edges.append(
                            (source_mechanism, target_mechanism)
                        )

            assert source_backing_edges
            assert any(
                edge["relation_id"] == "organ.wires_to.organ"
                and edge["target_id"] == target_organ
                and edge["target_status"] == "resolved_registry_or_atlas_target"
                and edge["justification"]["source_ref"].endswith(".wires_to")
                for edge in organ_instance["relationships"]["edges"]
            )
            asserted_edge_count += 1

    assert asserted_edge_count == 49


def test_batch4_and_8_import_organs_resolve_source_edges_and_laws() -> None:
    target_specs = {
        "batch4_proof_authority_runtime": {
            "mechanism": "mechanism.batch4_proof_authority_runtime.validates_public_proof_authority_runtime_capsule",
            "code_path": "src/microcosm_core/organs/batch4_proof_authority_runtime.py",
            "authority_class": "verified_macro_body_import",
            "axioms": {"AX-4", "AX-8", "AX-10", "AX-11"},
            "principles": {"P-2", "P-5", "P-9", "P-15"},
        },
        "batch8_station_surface_atlas_layout_port": {
            "mechanism": "mechanism.batch8_station_surface_atlas_layout_port.validates_public_station_surface_atlas_layout_port",
            "code_path": "src/microcosm_core/organs/batch8_station_surface_atlas_layout_port.py",
            "authority_class": "algorithmic_projection",
            "axioms": {"AX-5", "AX-7", "AX-8", "AX-10"},
            "principles": {"P-2", "P-9", "P-15", "P-16"},
        },
    }

    health = build_lattice_health(MICROCOSM_ROOT)
    coverage = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )

    assert set(target_specs).isdisjoint(set(health["organs"]["unconstrained_by_axiom"]))
    gap_details = {
        row["organ_id"]: row
        for row in health["organs"]["required_edge_gap_details"]
    }
    assert set(gap_details).isdisjoint(set(target_specs))
    for organ_id, spec in target_specs.items():
        _assert_atlas_required_edges_resolved(
            coverage,
            organ_id,
            paper_module_ref=f"paper_modules/{organ_id}.md",
            atlas_mechanism_id=spec["mechanism"],
            code_path=spec["code_path"],
            authority_class=spec["authority_class"],
        )
        _assert_organ_law_refs_resolved(
            organ_id,
            axiom_refs=spec["axioms"],
            principle_refs=spec["principles"],
        )


def test_proof_replay_organs_are_bound_to_checker_and_refusal_laws() -> None:
    expected_axioms = {"AX-1", "AX-2", "AX-5", "AX-7"}
    expected_principles = {"P-1", "P-2", "P-3", "P-6", "P-8", "P-15"}
    target_organs = {
        "bounded_autonomy_campaign_packet",
        "materials_chemistry_closed_loop_lab_safety_replay",
        "proof_diagnostic_evidence_spine",
        "research_replication_rubric_artifact_replay",
        "spatial_world_model_counterfactual_simulation_replay",
        "verifier_lab_execution_spine",
        "verifier_lab_kernel",
    }

    health = build_lattice_health(MICROCOSM_ROOT)

    assert target_organs.isdisjoint(set(health["organs"]["unconstrained_by_axiom"]))
    for organ_id in target_organs:
        _assert_organ_law_refs_resolved(
            organ_id,
            axiom_refs=expected_axioms,
            principle_refs=(
                expected_principles | {"P-19"}
                if organ_id == "proof_diagnostic_evidence_spine"
                else expected_principles
            ),
        )


def test_control_route_organs_are_bound_to_public_boundary_laws() -> None:
    expected_axioms = {"AX-1", "AX-4", "AX-5", "AX-7", "AX-8", "AX-11"}
    expected_principles = {
        "P-1",
        "P-2",
        "P-3",
        "P-5",
        "P-6",
        "P-8",
        "P-9",
        "P-12",
        "P-15",
    }
    target_organs = {
        "bridge_phase_continuity_runtime",
        "cognitive_operator_registry",
        "cold_reader_route_map",
        "navigation_hologram_route_plane",
        "pattern_assimilation_step",
        "pattern_binding_contract",
        "routing_anti_patterns_registry",
        "world_model_projection_drift_control_room",
    }

    health = build_lattice_health(MICROCOSM_ROOT)

    assert target_organs.isdisjoint(set(health["organs"]["unconstrained_by_axiom"]))
    for organ_id in target_organs:
        _assert_organ_law_refs_resolved(
            organ_id,
            axiom_refs=expected_axioms,
            principle_refs=(
                expected_principles | {"P-19"}
                if organ_id == "pattern_binding_contract"
                else expected_principles
            ),
        )


def test_doctrine_projection_validation_checks_generated_surfaces() -> None:
    result = validate_doctrine_projection(MICROCOSM_ROOT)

    assert result["status"] == "pass"
    assert result["errors"] == []


def test_coverage_reports_current_organ_binding_deficits_without_greenwashing() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )

    assert projection["organ_count"] == _organ_source_count()
    assert projection["accepted_current_authority_organ_count"] == _organ_source_count()
    coverage = projection["organ_required_edge_coverage"]
    assert len(coverage["without_paper_module_ref"]) <= 41
    assert len(coverage["without_mechanism_ref"]) <= 77
    assert len(coverage["without_code_loci"]) <= 77
    assert "verifier_lab_kernel" not in coverage["without_paper_module_ref"]
    assert "verifier_lab_kernel" not in coverage["without_mechanism_ref"]
    assert "verifier_lab_kernel" not in coverage["without_code_loci"]
    assert coverage["resolved_mechanism_count"] >= 1
    assert coverage["planned_mechanism_count"] == 0
    assert coverage["missing_mechanism_count"] == len(coverage["without_mechanism_ref"])
    assert projection["deficit_summary"]["organs_missing_paper_module_ref"] == len(coverage["without_paper_module_ref"])
    assert projection["deficit_summary"]["organs_missing_mechanism_ref"] == len(coverage["without_mechanism_ref"])
    assert projection["deficit_summary"]["organs_missing_code_loci"] == len(coverage["without_code_loci"])
    assert projection["deficit_summary"]["kinds_still_v1_draft"] == []
    assert projection["deficit_summary"]["meta_standard_v1"] is False
    assert projection["deficit_summary"]["axiom_json_instance_count"] == 12
    assert projection["deficit_summary"]["axiom_json_missing_count"] == 0
    assert projection["deficit_summary"]["concept_json_instance_count"] == (
        _concept_source_count()
    )
    assert projection["deficit_summary"]["concept_json_missing_count"] == 0
    assert (
        projection["deficit_summary"]["concept_unpopulated_selective_relation_count"]
        == 0
    )
    assert projection["deficit_summary"]["mechanism_json_instance_count"] == (
        projection["mechanism_instance_corpus"]["json_instance_count"]
    )
    assert projection["deficit_summary"]["mechanism_json_missing_count"] == 0
    assert projection["deficit_summary"]["mechanism_without_code_loci_count"] == 0
    assert projection["deficit_summary"]["organ_json_instance_count"] == (
        projection["organ_instance_corpus"]["json_instance_count"]
    )
    assert projection["deficit_summary"]["organ_json_missing_count"] == 0
    assert projection["deficit_summary"]["organ_required_relation_gap_count"] == 0
    assert (
        projection["deficit_summary"]["organ_unpopulated_selective_relation_count"]
        > 0
    )
    assert projection["deficit_summary"]["paper_module_json_instance_count"] == (
        projection["paper_module_instance_corpus"]["json_instance_count"]
    )
    assert projection["deficit_summary"]["paper_module_json_missing_count"] == 0
    assert projection["deficit_summary"]["paper_module_legacy_only_count"] == (
        projection["paper_module_instance_corpus"]["legacy_only_count"]
    )
    assert projection["deficit_summary"]["paper_module_required_subject_gap_count"] == (
        projection["paper_module_instance_corpus"]["required_subject_gap_count"]
    )
    assert (
        projection["deficit_summary"]["paper_module_unpopulated_selective_relation_count"]
        > 0
    )
    assert (
        projection["deficit_summary"]["skill_json_instance_count"]
        == EXPECTED_SKILL_INSTANCE_COUNT
    )
    assert projection["deficit_summary"]["skill_json_missing_count"] == 0
    assert projection["deficit_summary"]["skill_required_relation_gap_count"] == 0
    assert (
        projection["deficit_summary"]["skill_unpopulated_selective_relation_count"]
        == EXPECTED_SKILL_SELECTIVE_RELATION_COUNT
    )
    assert (
        projection["deficit_summary"]["standard_json_instance_count"]
        == EXPECTED_STANDARD_INSTANCE_COUNT
    )
    assert projection["deficit_summary"]["standard_json_missing_count"] == 0
    assert projection["deficit_summary"]["standard_legacy_or_draft_contract_count"] > 0
    assert (
        projection["deficit_summary"]["standard_required_relation_gap_count"]
        == EXPECTED_STANDARD_REQUIRED_RELATION_GAP_COUNT
    )
    assert (
        projection["deficit_summary"]["standard_governs_kind_resolved_edge_count"]
        == EXPECTED_STANDARD_INSTANCE_COUNT
    )
    assert (
        projection["deficit_summary"]["standard_triad_skill_resolved_edge_count"]
        == EXPECTED_STANDARD_TRIAD_RESOLVED_EDGE_COUNT
    )
    assert (
        projection["deficit_summary"]["standard_triad_skill_planned_unresolved_edge_count"]
        == EXPECTED_STANDARD_TRIAD_PLANNED_UNRESOLVED_EDGE_COUNT
    )
    assert projection["deficit_summary"]["standard_triad_skill_missing_required_count"] == 0
    assert projection["deficit_summary"]["standard_unregistered_file_count"] == 0


def test_verifier_lab_kernel_standard_binds_capsule_and_mechanism_source() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.verifier_lab_kernel"
    mechanism_id = (
        "mechanism.verifier_lab_kernel."
        "composes_public_formal_math_receipts"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert "verifier_lab_kernel" not in coverage["without_paper_module_ref"]
    assert "verifier_lab_kernel" not in coverage["without_mechanism_ref"]
    assert "verifier_lab_kernel" not in coverage["without_code_loci"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["verifier_lab_kernel"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/verifier_lab_kernel.py"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 5
    assert (
        "receipts/first_wave/verifier_lab_kernel/verifier_lab_kernel_validation_receipt.json"
        in mechanism["receipt_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT / "standards/std_microcosm_verifier_lab_kernel.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.verifier_lab_kernel"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert "private proof-body import" in (
        standard["doctrine_population_status"]["authority_boundary"]
    )
    source_ref_paths = {
        ref["path"] if isinstance(ref, dict) else ref
        for ref in standard["source_refs"]
    }
    assert (
        "core/paper_module_capsules.json#paper_module.verifier_lab_kernel"
        in source_ref_paths
    )
    assert (
        "core/mechanism_sources.json#mechanism.verifier_lab_kernel.composes_public_formal_math_receipts"
        in source_ref_paths
    )


def test_status_lanes_distinguish_contract_pass_from_remaining_release_gate() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )

    assert projection["status"] == "pass"
    assert projection["contract_status"] == "pass"
    assert projection["relation_registry_status"] == "pass"
    assert projection["projection_reproducibility_status"] == "fresh_at_generation"
    assert projection["population_status"] == "complete"
    assert projection["release_readiness_status"] == "ready_for_separate_release_gate"
    assert projection["public_brand_guard_status"] == "pass"


def test_standard_contract_rejects_over_minted_per_organ_doctrine() -> None:
    standards = load_kind_standards(MICROCOSM_ROOT)
    registry = load_relation_registry(MICROCOSM_ROOT)
    bad = copy.deepcopy(standards)
    organ = bad["organ"]
    concept_edge = next(
        edge for edge in organ["lattice_edges"]["selective"] if edge["to_kind"] == "concept"
    )
    organ["lattice_edges"]["required"].append(concept_edge)

    result = validate_kind_standard_contracts(bad, registry)

    assert result["status"] == "blocked"
    assert "organ_over_mints_selective_doctrine" in {error["code"] for error in result["errors"]}


def test_standard_contract_rejects_generated_markdown_as_source_authority() -> None:
    standards = load_kind_standards(MICROCOSM_ROOT)
    registry = load_relation_registry(MICROCOSM_ROOT)
    bad = copy.deepcopy(standards)
    bad["paper_module"]["projections"]["markdown"]["source_authority"] = True

    result = validate_kind_standard_contracts(bad, registry)

    assert result["status"] == "blocked"
    assert "projection_generated_not_source_guard" in {error["code"] for error in result["errors"]}


def test_per_kind_unregistered_edge_count_tracks_missing_relation_key() -> None:
    standards = load_kind_standards(MICROCOSM_ROOT)
    registry = load_relation_registry(MICROCOSM_ROOT)
    bad = copy.deepcopy(registry)
    bad["relations"] = [
        row
        for row in bad["relations"]
        if row["relation_id"] != "organ.implemented_by.code_locus"
    ]

    relation_result = validate_relation_registry(bad, standards)
    rows = _kind_coverage_rows(standards, relation_result)

    assert relation_result["status"] == "blocked"
    assert "lattice_edge_missing_relation_registry_row" in {
        error["code"] for error in relation_result["errors"]
    }
    assert rows["organ"]["unregistered_lattice_edge_count"] == 1


def test_relation_registry_rejects_bad_projection_surface_and_kind_union() -> None:
    standards = load_kind_standards(MICROCOSM_ROOT)
    registry = load_relation_registry(MICROCOSM_ROOT)
    bad = copy.deepcopy(registry)
    bad["relations"][0]["projection_surfaces"] = ["not_registered"]
    bad["kind_unions"][0]["members"].append("not_a_kind")

    result = validate_relation_registry(bad, standards)

    assert result["status"] == "blocked"
    codes = {error["code"] for error in result["errors"]}
    assert "relation_bad_projection_surface" in codes
    assert "kind_union_unknown_member" in codes


def test_coverage_validation_includes_paper_module_corpus_drift() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    bad = copy.deepcopy(projection)
    bad["paper_module_corpus"]["markdown_file_count"] += 1

    validation = validate_coverage_projection(bad, MICROCOSM_ROOT)

    assert validation["status"] == "blocked"
    assert "paper_module_corpus" in {error["path"] for error in validation["errors"]}


def test_verifier_lab_kernel_population_resolves_required_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]

    assert "verifier_lab_kernel" not in coverage["without_paper_module_ref"]
    assert "verifier_lab_kernel" not in coverage["without_mechanism_ref"]
    assert "verifier_lab_kernel" not in coverage["without_code_loci"]
    assert coverage["resolved_mechanism_count"] >= 1
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    assert "paper_module.verifier_lab_kernel" in projection["paper_module_corpus"]["json_capsule_ids"]


def test_navigation_hologram_source_rows_resolve_under_atlas_binding() -> None:
    mechanism_id = "mechanism.navigation_hologram_route_plane.validates_public_route_plane_bundle"
    paper_module_id = "paper_module.navigation_hologram_route_plane"
    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    paper_capsule_registry = json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(encoding="utf-8")
    )
    mechanism_sources = {
        row["id"]: row for row in mechanism_registry["mechanisms"]
    }
    paper_capsules = {
        row["id"]: row for row in paper_capsule_registry["paper_modules"]
    }
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )

    assert paper_module_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert mechanism_id in mechanism_sources

    join = _registry_atlas_join_health(
        MICROCOSM_ROOT,
        accepted=[
            {
                "organ_id": "navigation_hologram_route_plane",
                "status": "accepted_current_authority",
            }
        ],
        atlas_rows=[
            {
                "organ_id": "navigation_hologram_route_plane",
                "paper_module_ref": f"core/paper_module_capsules.json#{paper_module_id}",
                "mechanism_refs": [
                    {
                        "ref": mechanism_id,
                        "resolution_status": "resolved",
                    }
                ],
                "code_loci": [
                    {
                        "path": "src/microcosm_core/organs/navigation_hologram_route_plane.py",
                        "resolution": "resolved",
                    }
                ],
            }
        ],
        mechanism_sources=mechanism_sources,
        paper_capsules=paper_capsules,
    )

    assert join["status"] == "pass"
    assert join["resolved_mechanism_count"] == 1
    assert join["resolved_code_locus_count"] == 1
    assert join["errors"] == []


def test_navigation_hologram_route_plane_population_resolves_required_edges() -> None:
    capsule_id = "paper_module.navigation_hologram_route_plane"
    mechanism_id = "mechanism.navigation_hologram_route_plane.validates_public_route_plane_bundle"
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]

    assert "navigation_hologram_route_plane" not in coverage["without_paper_module_ref"]
    assert "navigation_hologram_route_plane" not in coverage["without_mechanism_ref"]
    assert "navigation_hologram_route_plane" not in coverage["without_code_loci"]
    assert coverage["resolved_mechanism_count"] >= 2
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["navigation_hologram_route_plane"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/navigation_hologram_route_plane.py"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 5
    assert (
        "receipts/first_wave/navigation_hologram_route_plane/exported_route_plane_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_navigation_hologram_route_plane.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.navigation_hologram_route_plane"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert (
        standard["doctrine_population_status"]["source_module_manifest_status"]
        == "populated"
    )
    assert "live route freshness" in (
        standard["doctrine_population_status"]["authority_boundary"]
    )
    assert "core/paper_module_capsules.json#paper_module.navigation_hologram_route_plane" in {
        ref["path"] for ref in standard["source_refs"]
    }


def test_agent_route_observability_runtime_population_resolves_required_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.agent_route_observability_runtime"
    mechanism_id = (
        "mechanism.agent_route_observability_runtime."
        "validates_public_route_feedback"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert "agent_route_observability_runtime" not in coverage["without_paper_module_ref"]
    assert "agent_route_observability_runtime" not in coverage["without_mechanism_ref"]
    assert "agent_route_observability_runtime" not in coverage["without_code_loci"]
    assert coverage["resolved_mechanism_count"] >= 3
    assert coverage["resolved_code_locus_count"] >= 3
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["agent_route_observability_runtime"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/agent_route_observability_runtime.py"
    )
    assert "receipts/first_wave/agent_route_observability_runtime/egress_mirror_receipt.json" in (
        mechanism["receipt_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_agent_route_observability_runtime.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.agent_route_observability_runtime"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert standard["body_import_verification"]["source_open_body_import_floor"][
        "body_material_count"
    ] == 8
    assert "core/paper_module_capsules.json#paper_module.agent_route_observability_runtime" in {
        ref["path"] for ref in standard["source_refs"]
    }


def test_agent_closeout_faithfulness_audit_population_resolves_required_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]

    assert "agent_closeout_faithfulness_audit" not in coverage["without_paper_module_ref"]
    assert "agent_closeout_faithfulness_audit" not in coverage["without_mechanism_ref"]
    assert "agent_closeout_faithfulness_audit" not in coverage["without_code_loci"]
    assert coverage["resolved_mechanism_count"] >= 4
    assert coverage["resolved_code_locus_count"] >= 4
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    assert (
        "paper_module.agent_closeout_faithfulness_audit"
        in projection["paper_module_corpus"]["json_capsule_ids"]
    )
    mechanism_id = (
        "mechanism.agent_closeout_faithfulness_audit."
        "validates_closeout_evidence_claims"
    )

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["agent_closeout_faithfulness_audit"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/agent_closeout_faithfulness_audit.py"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 5

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_agent_closeout_faithfulness_audit.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.agent_closeout_faithfulness_audit"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert "unchecked pytest-pass claim" in (
        standard["doctrine_population_status"]["authority_boundary"]
    )
    assert (
        "core/paper_module_capsules.json#paper_module.agent_closeout_faithfulness_audit"
        in standard["source_refs"]
    )
    assert (
        "core/mechanism_sources.json#mechanism.agent_closeout_faithfulness_audit.validates_closeout_evidence_claims"
        in standard["source_refs"]
    )


def test_bridge_phase_continuity_runtime_population_has_capsule_and_mechanism_source() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.bridge_phase_continuity_runtime"
    mechanism_id = (
        "mechanism.bridge_phase_continuity_runtime."
        "validates_synthetic_bridge_continuity"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["bridge_phase_continuity_runtime"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/bridge_phase_continuity_runtime.py"
    )
    assert "receipts/second_wave/bridge_phase_continuity_runtime/closeout_transition.json" in (
        mechanism["receipt_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_bridge_phase_continuity_runtime.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.bridge_phase_continuity_runtime"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert "bridge_phase_continuity_runtime" not in coverage["without_paper_module_ref"]
    assert "bridge_phase_continuity_runtime" not in coverage["without_mechanism_ref"]
    assert "bridge_phase_continuity_runtime" not in coverage["without_code_loci"]


def test_cold_reader_route_map_population_has_capsule_and_mechanism_source() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.cold_reader_route_map"
    mechanism_id = (
        "mechanism.cold_reader_route_map."
        "validates_public_first_run_route_map"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["cold_reader_route_map"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/cold_reader_route_map.py"
    )
    assert "receipts/runtime_shell/demo_project/organs/cold_reader_route_map/exported_cold_reader_route_map_bundle_validation_result.json" in (
        mechanism["receipt_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_cold_reader_route_map.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.cold_reader_route_map"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert "cold_reader_route_map" not in coverage["without_paper_module_ref"]
    assert "cold_reader_route_map" not in coverage["without_mechanism_ref"]
    assert "cold_reader_route_map" not in coverage["without_code_loci"]


def test_mission_transaction_work_spine_population_has_atlas_capsule_and_mechanism_source() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.mission_transaction_work_spine"
    mechanism_id = (
        "mechanism.mission_transaction_work_spine."
        "validates_public_mission_transaction_bundle"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    assert "mission_transaction_work_spine" not in coverage["without_paper_module_ref"]
    assert "mission_transaction_work_spine" not in coverage["without_mechanism_ref"]
    assert "mission_transaction_work_spine" not in coverage["without_code_loci"]

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["mission_transaction_work_spine"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/mission_transaction_work_spine.py"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert (
        "receipts/first_wave/mission_transaction_work_spine/exported_mission_transaction_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    paper_module = json.loads(
        (
            MICROCOSM_ROOT / "paper_modules/mission_transaction_work_spine.json"
        ).read_text(encoding="utf-8")
    )
    depends_edges = [
        edge
        for edge in paper_module["relationships"]["edges"]
        if edge["relation_id"] == "paper_module.depends_on.paper_module"
    ]
    assert depends_edges == [
        {
            "relation_id": "paper_module.depends_on.paper_module",
            "relation_verb": "depends_on",
            "reverse_verb": "depended_on_by",
            "target_kind": "paper_module",
            "target_id": "paper_module.durable_agent_work_landing_replay",
            "target_status": "resolved_json_instance",
            "justification": {
                "source_ref": (
                    "core/paper_module_capsules.json::paper_modules"
                    "[20:paper_module.mission_transaction_work_spine].depends_on"
                ),
                "summary": (
                    "Paper-module source row names this sibling/dependency "
                    "paper module."
                ),
            },
            "residual_pressure_ref": None,
        }
    ]

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_mission_transaction_work_spine.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.mission_transaction_work_spine"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert (
        standard["doctrine_population_status"]["coverage_projection_status"]
        == "required_edges_populated"
    )
    assert "core/paper_module_capsules.json#paper_module.mission_transaction_work_spine" in {
        ref["path"] for ref in standard["source_refs"]
    }
    assert (
        "core/mechanism_sources.json#mechanism.mission_transaction_work_spine.validates_public_mission_transaction_bundle"
        in {ref["path"] for ref in standard["source_refs"]}
    )


def test_formal_math_verifier_trace_repair_loop_population_has_atlas_capsule_and_mechanism_source() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.formal_math_verifier_trace_repair_loop"
    mechanism_id = (
        "mechanism.formal_math_verifier_trace_repair_loop."
        "validates_public_verifier_trace_repair_bundle"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    assert "formal_math_verifier_trace_repair_loop" not in coverage[
        "without_paper_module_ref"
    ]
    assert "formal_math_verifier_trace_repair_loop" not in coverage[
        "without_mechanism_ref"
    ]
    assert "formal_math_verifier_trace_repair_loop" not in coverage[
        "without_code_loci"
    ]

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["formal_math_verifier_trace_repair_loop"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/formal_math_verifier_trace_repair_loop.py"
    )
    assert "validate_source_module_manifest" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert (
        "receipts/runtime_shell/demo_project/organs/formal_math_verifier_trace_repair_loop/exported_verifier_trace_repair_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/formal_math_verifier_trace_repair_loop/exported_verifier_trace_repair_bundle/source_module_manifest.json"
        in mechanism["input_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_formal_math_verifier_trace_repair_loop.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.formal_math_verifier_trace_repair_loop"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert (
        standard["doctrine_population_status"]["coverage_projection_status"]
        == "required_edges_populated"
    )
    assert standard["source_module_manifest_contract"]["manifest_ref"] == (
        "examples/formal_math_verifier_trace_repair_loop/exported_verifier_trace_repair_bundle/source_module_manifest.json"
    )
    assert "core/paper_module_capsules.json#paper_module.formal_math_verifier_trace_repair_loop" in {
        ref["path"] for ref in standard["source_refs"]
    }
    assert (
        "core/mechanism_sources.json#mechanism.formal_math_verifier_trace_repair_loop.validates_public_verifier_trace_repair_bundle"
        in {ref["path"] for ref in standard["source_refs"]}
    )


def test_formal_math_readiness_gate_population_has_capsule_and_mechanism_prestaged_until_atlas_binding() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.formal_math_readiness_gate"
    mechanism_id = (
        "mechanism.formal_math_readiness_gate."
        "validates_public_formal_math_readiness_bundle"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    _assert_atlas_required_edges_resolved(
        projection,
        "formal_math_readiness_gate",
        paper_module_ref="paper_modules/formal_math_readiness_gate.md",
        atlas_mechanism_id=(
            "mechanism.formal_math_readiness_gate."
            "validates_public_readiness_boundary"
        ),
        code_path="src/microcosm_core/organs/formal_math_readiness_gate.py",
    )

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["formal_math_readiness_gate"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/formal_math_readiness_gate.py"
    )
    assert "validate_source_module_imports" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert (
        "receipts/runtime_shell/demo_project/organs/formal_math_readiness_gate/exported_formal_math_readiness_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle/source_body_floor/source_module_manifest.json"
        in mechanism["input_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT / "standards/std_microcosm_formal_math_readiness_gate.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.formal_math_readiness_gate"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == (
        "deferred_for_sibling_organ_atlas_lane"
    )
    assert (
        standard["doctrine_population_status"]["coverage_projection_status"]
        == "json_corpus_populated_atlas_edges_pending"
    )
    assert standard["source_module_manifest_contract"]["manifest_ref"] == (
        "examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle/source_module_manifest.json"
    )
    assert "core/paper_module_capsules.json#paper_module.formal_math_readiness_gate" in {
        ref["path"] for ref in standard["source_refs"]
    }
    assert (
        "core/mechanism_sources.json#mechanism.formal_math_readiness_gate.validates_public_formal_math_readiness_bundle"
        in {ref["path"] for ref in standard["source_refs"]}
    )


def test_formal_math_lean_proof_witness_population_has_capsule_and_mechanism_prestaged_until_atlas_binding() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.formal_math_lean_proof_witness"
    mechanism_id = (
        "mechanism.formal_math_lean_proof_witness."
        "validates_public_lean_lake_witness"
    )
    atlas_mechanism_id = (
        "mechanism.formal_math_lean_proof_witness."
        "validates_public_lean_witness"
    )
    upstream_mechanism_ids = {
        "mechanism.formal_math_premise_retrieval.validates_public_premise_retrieval_slice",
        "mechanism.formal_math_readiness_gate.validates_public_formal_math_readiness_bundle",
        "mechanism.proof_diagnostic_evidence_spine.validates_ring2_diagnostic_evidence_membrane",
        "mechanism.verifier_lab_execution_spine.validates_public_verifier_transition_witness",
        "mechanism.verifier_lab_kernel.composes_public_formal_math_receipts",
    }

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    _assert_atlas_required_edges_resolved(
        projection,
        "formal_math_lean_proof_witness",
        paper_module_ref="paper_modules/formal_math_lean_proof_witness.md",
        atlas_mechanism_id=atlas_mechanism_id,
        code_path="src/microcosm_core/organs/formal_math_lean_proof_witness.py",
    )

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["formal_math_lean_proof_witness"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/formal_math_lean_proof_witness.py"
    )
    assert "validate_source_module_imports" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["authority_class"] == (
        "external_subprocess_witness"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 4
    assert (
        "receipts/runtime_shell/demo_project/organs/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle/source_module_manifest.json"
        in mechanism["input_refs"]
    )
    atlas_mechanism = next(
        row
        for row in mechanism_registry["mechanisms"]
        if row["id"] == atlas_mechanism_id
    )
    assert set(atlas_mechanism["upstream_of"]) == upstream_mechanism_ids

    lean_witness_instance = json.loads(
        (
            MICROCOSM_ROOT
            / "mechanisms"
            / f"{atlas_mechanism_id}.json"
        ).read_text(encoding="utf-8")
    )
    upstream_edges = {
        edge["target_id"]: edge
        for edge in lean_witness_instance["relationships"]["edges"]
        if edge["relation_id"] == "mechanism.upstream_of.mechanism"
    }
    assert set(upstream_edges) == upstream_mechanism_ids
    assert all(
        edge["target_status"] == "resolved_json_instance"
        for edge in upstream_edges.values()
    )
    assert "mechanism.upstream_of.mechanism" not in {
        residual["relation_id"]
        for residual in lean_witness_instance["relationships"][
            "unpopulated_selective_relations"
        ]
    }

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_formal_math_lean_proof_witness.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.formal_math_lean_proof_witness"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == (
        "deferred_for_sibling_organ_atlas_lane"
    )
    assert (
        standard["doctrine_population_status"]["coverage_projection_status"]
        == "json_corpus_populated_atlas_edges_pending"
    )
    assert standard["source_module_manifest_contract"]["manifest_ref"] == (
        "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle/source_module_manifest.json"
    )
    assert standard["source_open_body_imports"]["body_material_count"] == 5
    assert standard["source_open_body_imports"]["body_in_receipt"] is False
    assert standard["negative_cases"]["coverage_status"] == "all_observed"
    assert "invalid_proof_rejected" in standard["negative_cases"]["expected"]
    assert "core/paper_module_capsules.json#paper_module.formal_math_lean_proof_witness" in {
        ref["path"] for ref in standard["source_refs"]
    }
    assert (
        "core/mechanism_sources.json#mechanism.formal_math_lean_proof_witness.validates_public_lean_lake_witness"
        in {ref["path"] for ref in standard["source_refs"]}
    )

    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 5
    assert len(manifest["blocked_import_debt"]) == 1
    assert all(module["body_in_receipt"] is False for module in manifest["modules"])
    assert all(module["sha256"].startswith("sha256:") for module in manifest["modules"])


def test_formal_evidence_cell_anchor_resolver_population_has_capsule_and_mechanism_prestaged_until_atlas_binding() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.formal_evidence_cell_anchor_resolver"
    mechanism_id = (
        "mechanism.formal_evidence_cell_anchor_resolver."
        "validates_public_evidence_cell_anchor_resolution"
    )
    atlas_mechanism_id = (
        "mechanism.formal_evidence_cell_anchor_resolver."
        "validates_public_evidence_cell_anchors"
    )
    proof_diagnostic_mechanism_id = (
        "mechanism.proof_diagnostic_evidence_spine."
        "validates_ring2_diagnostic_evidence_membrane"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    _assert_atlas_required_edges_resolved(
        projection,
        "formal_evidence_cell_anchor_resolver",
        paper_module_ref="paper_modules/formal_evidence_cell_anchor_resolver.md",
        atlas_mechanism_id=atlas_mechanism_id,
        code_path="src/microcosm_core/organs/formal_evidence_cell_anchor_resolver.py",
    )

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["formal_evidence_cell_anchor_resolver"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/formal_evidence_cell_anchor_resolver.py"
    )
    assert "run_anchor_bundle" in mechanism["code_loci"][0]["symbols"]
    assert "validate_source_module_manifest" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert (
        "receipts/runtime_shell/demo_project/organs/formal_evidence_cell_anchor_resolver/exported_evidence_cell_anchor_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/formal_evidence_cell_anchor_resolver/exported_evidence_cell_anchor_bundle/source_module_manifest.json"
        in mechanism["input_refs"]
    )

    anchor_instance = json.loads(
        (
            MICROCOSM_ROOT
            / "mechanisms"
            / f"{atlas_mechanism_id}.json"
        ).read_text(encoding="utf-8")
    )
    assert any(
        edge["relation_id"] == "mechanism.upstream_of.mechanism"
        and edge["target_id"] == proof_diagnostic_mechanism_id
        and edge["target_status"] == "resolved_json_instance"
        for edge in anchor_instance["relationships"]["edges"]
    )
    assert "mechanism.upstream_of.mechanism" not in {
        residual["relation_id"]
        for residual in anchor_instance["relationships"][
            "unpopulated_selective_relations"
        ]
    }

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_formal_evidence_cell_anchor_resolver.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.formal_evidence_cell_anchor_resolver"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == (
        "deferred_for_sibling_organ_atlas_lane"
    )
    assert (
        standard["doctrine_population_status"]["coverage_projection_status"]
        == "json_corpus_populated_atlas_edges_pending"
    )
    assert standard["source_module_manifest_contract"]["manifest_ref"] == (
        "examples/formal_evidence_cell_anchor_resolver/exported_evidence_cell_anchor_bundle/source_module_manifest.json"
    )
    assert standard["source_module_manifest_contract"]["body_material_count"] == 6
    assert standard["source_open_body_imports"]["body_material_count"] == 6
    assert standard["source_open_body_imports"]["body_text_exported_in_receipts"] is False
    assert standard["negative_cases"]["coverage_status"] == "all_observed"
    assert "theorem_correctness_overclaim" in standard["negative_cases"]["expected"]
    assert "core/paper_module_capsules.json#paper_module.formal_evidence_cell_anchor_resolver" in {
        ref["path"] for ref in standard["source_refs"]
    }
    assert (
        "core/mechanism_sources.json#mechanism.formal_evidence_cell_anchor_resolver.validates_public_evidence_cell_anchor_resolution"
        in {ref["path"] for ref in standard["source_refs"]}
    )

    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/formal_evidence_cell_anchor_resolver/exported_evidence_cell_anchor_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 6
    assert all(module["body_in_receipt"] is False for module in manifest["modules"])
    assert all(module["sha256_match"] is True for module in manifest["modules"])
    assert {
        module["material_class"] for module in manifest["modules"]
    } == {
        "public_macro_pattern_body",
        "public_macro_receipt_body",
        "public_macro_tool_body",
    }


def test_agent_benchmark_integrity_anti_gaming_replay_population_resolves_required_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.agent_benchmark_integrity_anti_gaming_replay"
    mechanism_id = (
        "mechanism.agent_benchmark_integrity_anti_gaming_replay."
        "validates_public_benchmark_integrity_replay"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    assert "agent_benchmark_integrity_anti_gaming_replay" not in coverage[
        "without_paper_module_ref"
    ]
    assert "agent_benchmark_integrity_anti_gaming_replay" not in coverage[
        "without_mechanism_ref"
    ]
    assert "agent_benchmark_integrity_anti_gaming_replay" not in coverage[
        "without_code_loci"
    ]

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["agent_benchmark_integrity_anti_gaming_replay"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/agent_benchmark_integrity_anti_gaming_replay.py"
    )
    assert "run_benchmark_integrity_bundle" in mechanism["code_loci"][0]["symbols"]
    assert "validate_source_module_imports" in mechanism["code_loci"][0]["symbols"]
    assert "validate_public_trace" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert (
        "receipts/runtime_shell/demo_project/organs/agent_benchmark_integrity_anti_gaming_replay/exported_benchmark_integrity_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/agent_benchmark_integrity_anti_gaming_replay/exported_benchmark_integrity_bundle/source_module_manifest.json"
        in mechanism["input_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_agent_benchmark_integrity_anti_gaming_replay.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.agent_benchmark_integrity_anti_gaming_replay"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == (
        "deferred_for_sibling_organ_atlas_lane"
    )
    assert (
        standard["doctrine_population_status"]["coverage_projection_status"]
        == "json_corpus_populated_atlas_edges_pending"
    )
    assert standard["source_module_manifest_contract"]["manifest_ref"] == (
        "examples/agent_benchmark_integrity_anti_gaming_replay/exported_benchmark_integrity_bundle/source_module_manifest.json"
    )
    assert standard["source_module_manifest_contract"]["body_material_count"] == 3
    assert standard["source_open_body_imports"]["body_material_count"] == 3
    assert standard["source_open_body_imports"]["body_in_receipt"] is False
    assert standard["negative_cases"]["coverage_status"] == "all_observed"
    assert "score_overclaim" in standard["negative_cases"]["expected"]
    assert "core/paper_module_capsules.json#paper_module.agent_benchmark_integrity_anti_gaming_replay" in {
        ref["path"] for ref in standard["source_refs"]
    }
    assert (
        "core/mechanism_sources.json#mechanism.agent_benchmark_integrity_anti_gaming_replay.validates_public_benchmark_integrity_replay"
        in {ref["path"] for ref in standard["source_refs"]}
    )

    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/agent_benchmark_integrity_anti_gaming_replay/exported_benchmark_integrity_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == len(manifest["modules"])
    assert all(module["body_in_receipt"] is False for module in manifest["modules"])
    assert all(
        module["source_import_class"] == "copied_non_secret_macro_body"
        for module in manifest["modules"]
    )
    assert {module["material_class"] for module in manifest["modules"]} == {
        "public_macro_pattern_body",
        "public_sanitized_real_benchmark_trace",
    }


def test_research_replication_rubric_artifact_replay_population_resolves_required_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    capsule_id = "paper_module.research_replication_rubric_artifact_replay"
    mechanism_id = (
        "mechanism.research_replication_rubric_artifact_replay."
        "validates_public_research_replication_replay"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    _assert_atlas_required_edges_resolved(
        projection,
        "research_replication_rubric_artifact_replay",
        paper_module_ref="paper_modules/research_replication_rubric_artifact_replay.md",
        atlas_mechanism_id=mechanism_id,
        code_path="src/microcosm_core/organs/research_replication_rubric_artifact_replay.py",
        evidence_rank=3,
    )

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["research_replication_rubric_artifact_replay"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/research_replication_rubric_artifact_replay.py"
    )
    assert "run_replication_bundle" in mechanism["code_loci"][0]["symbols"]
    assert "validate_source_module_imports" in mechanism["code_loci"][0]["symbols"]
    assert "validate_research_replays" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert (
        "receipts/runtime_shell/demo_project/organs/research_replication_rubric_artifact_replay/exported_research_replication_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/research_replication_rubric_artifact_replay/exported_research_replication_bundle/source_module_manifest.json"
        in mechanism["input_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_research_replication_rubric_artifact_replay.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.research_replication_rubric_artifact_replay"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == (
        "deferred_for_sibling_organ_atlas_lane"
    )
    assert (
        standard["doctrine_population_status"]["coverage_projection_status"]
        == "json_corpus_populated_atlas_edges_pending"
    )
    assert standard["source_module_manifest_contract"]["manifest_ref"] == (
        "examples/research_replication_rubric_artifact_replay/exported_research_replication_bundle/source_module_manifest.json"
    )
    assert standard["source_module_manifest_contract"]["body_material_count"] == 4
    assert standard["source_open_body_imports"]["body_material_count"] == 4
    assert standard["source_open_body_imports"]["body_in_receipt"] is False
    assert standard["negative_cases"]["coverage_status"] == "all_observed"
    assert "benchmark_performance_claim" in standard["negative_cases"]["expected"]
    assert "core/paper_module_capsules.json#paper_module.research_replication_rubric_artifact_replay" in {
        ref["path"] for ref in standard["source_refs"]
    }
    assert (
        "core/mechanism_sources.json#mechanism.research_replication_rubric_artifact_replay.validates_public_research_replication_replay"
        in {ref["path"] for ref in standard["source_refs"]}
    )

    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/research_replication_rubric_artifact_replay/exported_research_replication_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 4
    assert all(module["body_in_receipt"] is False for module in manifest["modules"])
    assert all(
        module["source_import_class"] == "copied_non_secret_macro_body"
        for module in manifest["modules"]
    )
    assert {
        module["material_class"] for module in manifest["modules"]
    } == {"public_macro_pattern_body", "public_python_source_body"}

    runtime_receipt = json.loads(
        (
            MICROCOSM_ROOT
            / "receipts/runtime_shell/demo_project/organs/research_replication_rubric_artifact_replay/exported_research_replication_bundle_validation_result.json"
        ).read_text(encoding="utf-8")
    )
    assert runtime_receipt["status"] == "pass"
    assert runtime_receipt["source_module_import_count"] == 4
    assert runtime_receipt["source_open_body_imports"]["body_material_count"] == 4
    assert {
        row["module_id"] for row in runtime_receipt["source_module_imports"]
    } == {
        "research_replication_deterministic_pattern_order_body_import",
        "research_replication_extracted_pattern_ledger_row_body_import",
        "research_replication_high_novelty_growth_receipt_body_import",
        "research_replication_replay_control_plane_source_body_import",
    }


def test_agentic_vulnerability_discovery_patch_proof_replay_population_resolves_required_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    capsule_id = "paper_module.agentic_vulnerability_discovery_patch_proof_replay"
    mechanism_id = (
        "mechanism.agentic_vulnerability_discovery_patch_proof_replay."
        "validates_public_agentic_vulnerability_patch_proof_replay"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    _assert_atlas_required_edges_resolved(
        projection,
        "agentic_vulnerability_discovery_patch_proof_replay",
        paper_module_ref=(
            "paper_modules/"
            "agentic_vulnerability_discovery_patch_proof_replay.md"
        ),
        atlas_mechanism_id=mechanism_id,
        code_path=(
            "src/microcosm_core/organs/"
            "agentic_vulnerability_discovery_patch_proof_replay.py"
        ),
        evidence_rank=3,
    )

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["agentic_vulnerability_discovery_patch_proof_replay"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/agentic_vulnerability_discovery_patch_proof_replay.py"
    )
    assert "run_patch_proof_bundle" in mechanism["code_loci"][0]["symbols"]
    assert "_source_module_manifest_result" in mechanism["code_loci"][0]["symbols"]
    assert "_source_open_body_import_summary" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert (
        "receipts/runtime_shell/demo_project/organs/agentic_vulnerability_discovery_patch_proof_replay/exported_patch_proof_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/agentic_vulnerability_discovery_patch_proof_replay/exported_patch_proof_bundle/source_module_manifest.json"
        in mechanism["input_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_agentic_vulnerability_discovery_patch_proof_replay.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.agentic_vulnerability_discovery_patch_proof_replay"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == (
        "deferred_for_sibling_organ_atlas_lane"
    )
    assert (
        standard["doctrine_population_status"]["coverage_projection_status"]
        == "json_corpus_populated_atlas_edges_pending"
    )
    assert standard["source_module_manifest_contract"]["manifest_ref"] == (
        "examples/agentic_vulnerability_discovery_patch_proof_replay/exported_patch_proof_bundle/source_module_manifest.json"
    )
    assert standard["source_module_manifest_contract"]["body_material_count"] == 9
    assert standard["source_open_body_imports"]["body_material_count"] == 9
    assert standard["source_open_body_imports"]["body_in_receipt"] is False
    assert (
        standard["source_open_body_imports"]["body_material_classes"][
            "public_macro_tool_body"
        ]
        == 3
    )
    assert "strict_json_source_body_import" in standard["source_open_body_imports"][
        "body_material_ids"
    ]
    assert standard["negative_cases"]["coverage_status"] == "all_observed"
    assert "real_cve_exploitation" in standard["negative_cases"]["expected"]
    assert (
        "core/paper_module_capsules.json#paper_module.agentic_vulnerability_discovery_patch_proof_replay"
        in {ref["path"] for ref in standard["source_refs"]}
    )
    assert (
        "core/mechanism_sources.json#mechanism.agentic_vulnerability_discovery_patch_proof_replay.validates_public_agentic_vulnerability_patch_proof_replay"
        in {ref["path"] for ref in standard["source_refs"]}
    )

    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/agentic_vulnerability_discovery_patch_proof_replay/exported_patch_proof_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 9
    assert all(module["body_in_receipt"] is False for module in manifest["modules"])
    assert all(module["sha256_match"] is True for module in manifest["modules"])
    assert "strict_json_source_body_import" in {
        module["module_id"] for module in manifest["modules"]
    }

    runtime_receipt = json.loads(
        (
            MICROCOSM_ROOT
            / "receipts/runtime_shell/demo_project/organs/agentic_vulnerability_discovery_patch_proof_replay/exported_patch_proof_bundle_validation_result.json"
        ).read_text(encoding="utf-8")
    )
    assert runtime_receipt["status"] == "pass"
    assert runtime_receipt["body_copied_material_count"] == 9
    assert runtime_receipt["source_module_imports"]["module_count"] == 9
    assert runtime_receipt["source_open_body_imports"]["body_material_count"] == 9
    assert "strict_json_source_body_import" in runtime_receipt[
        "source_module_imports"
    ]["module_ids"]


def test_materials_chemistry_closed_loop_lab_safety_replay_population_resolves_required_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    capsule_id = "paper_module.materials_chemistry_closed_loop_lab_safety_replay"
    mechanism_id = (
        "mechanism.materials_chemistry_closed_loop_lab_safety_replay."
        "validates_public_materials_lab_safety_replay"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    _assert_atlas_required_edges_resolved(
        projection,
        "materials_chemistry_closed_loop_lab_safety_replay",
        paper_module_ref=(
            "paper_modules/"
            "materials_chemistry_closed_loop_lab_safety_replay.md"
        ),
        atlas_mechanism_id=mechanism_id,
        code_path=(
            "src/microcosm_core/organs/"
            "materials_chemistry_closed_loop_lab_safety_replay.py"
        ),
        evidence_rank=3,
    )

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["materials_chemistry_closed_loop_lab_safety_replay"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/materials_chemistry_closed_loop_lab_safety_replay.py"
    )
    assert "run_lab_bundle" in mechanism["code_loci"][0]["symbols"]
    assert "_source_module_manifest_result" in mechanism["code_loci"][0]["symbols"]
    assert "_source_open_body_import_summary" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert (
        "receipts/runtime_shell/demo_project/organs/materials_chemistry_closed_loop_lab_safety_replay/exported_materials_lab_safety_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/materials_chemistry_closed_loop_lab_safety_replay/exported_materials_lab_safety_bundle/source_module_manifest.json"
        in mechanism["input_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_materials_chemistry_closed_loop_lab_safety_replay.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.materials_chemistry_closed_loop_lab_safety_replay"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["source_module_manifest_contract"]["manifest_ref"] == (
        "examples/materials_chemistry_closed_loop_lab_safety_replay/exported_materials_lab_safety_bundle/source_module_manifest.json"
    )
    assert standard["source_module_manifest_contract"]["body_material_count"] == 4
    assert standard["source_open_body_imports"]["body_material_count"] == 4
    assert standard["source_open_body_imports"]["body_in_receipt"] is False
    assert (
        standard["source_open_body_imports"]["body_material_classes"][
            "public_standard_body"
        ]
        == 1
    )
    assert "laboratory_standard_body_import" in standard["source_open_body_imports"][
        "body_material_ids"
    ]
    assert standard["negative_cases"]["coverage_status"] == "all_observed"
    assert "wetlab_protocol_steps" in standard["negative_cases"]["expected"]
    assert (
        "core/paper_module_capsules.json#paper_module.materials_chemistry_closed_loop_lab_safety_replay"
        in {ref["path"] for ref in standard["source_refs"]}
    )
    assert (
        "core/mechanism_sources.json#mechanism.materials_chemistry_closed_loop_lab_safety_replay.validates_public_materials_lab_safety_replay"
        in {ref["path"] for ref in standard["source_refs"]}
    )

    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/materials_chemistry_closed_loop_lab_safety_replay/exported_materials_lab_safety_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 4
    assert all(module["body_in_receipt"] is False for module in manifest["modules"])
    assert all(module["sha256_match"] is True for module in manifest["modules"])
    assert {
        module["material_class"] for module in manifest["modules"]
    } == {
        "public_macro_control_plane_body",
        "public_macro_receipt_body",
        "public_macro_tool_body",
        "public_standard_body",
    }

    runtime_receipt = json.loads(
        (
            MICROCOSM_ROOT
            / "receipts/runtime_shell/demo_project/organs/materials_chemistry_closed_loop_lab_safety_replay/exported_materials_lab_safety_bundle_validation_result.json"
        ).read_text(encoding="utf-8")
    )
    assert runtime_receipt["status"] == "pass"
    assert runtime_receipt["body_copied_material_count"] == 4
    assert runtime_receipt["source_module_imports"]["module_count"] == 4
    assert runtime_receipt["source_open_body_imports"]["body_material_count"] == 4
    assert "laboratory_standard_body_import" in runtime_receipt[
        "source_module_imports"
    ]["module_ids"]


def test_certificate_kernel_execution_lab_population_resolves_required_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    capsule_id = "paper_module.certificate_kernel_execution_lab"
    mechanism_id = (
        "mechanism.certificate_kernel_execution_lab."
        "validates_public_certificate_kernel_execution"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    _assert_atlas_required_edges_resolved(
        projection,
        "certificate_kernel_execution_lab",
        paper_module_ref="paper_modules/certificate_kernel_execution_lab.md",
        atlas_mechanism_id=mechanism_id,
        code_path="src/microcosm_core/organs/certificate_kernel_execution_lab.py",
        authority_class="external_subprocess_witness",
        evidence_rank=4,
    )

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["certificate_kernel_execution_lab"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/certificate_kernel_execution_lab.py"
    )
    assert "run_certificate_bundle" in mechanism["code_loci"][0]["symbols"]
    assert "_source_module_manifest_result" in mechanism["code_loci"][0]["symbols"]
    assert "_source_open_body_import_summary" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["authority_class"] == (
        "external_subprocess_witness"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 4
    assert (
        "receipts/runtime_shell/demo_project/organs/certificate_kernel_execution_lab/exported_certificate_kernel_execution_lab_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/certificate_kernel_execution_lab/exported_certificate_kernel_execution_lab_bundle/source_module_manifest.json"
        in mechanism["input_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_certificate_kernel_execution_lab.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.certificate_kernel_execution_lab"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert (
        standard["doctrine_population_status"]["coverage_projection_status"]
        == "required_edges_populated"
    )
    assert standard["source_module_manifest_contract"]["manifest_ref"] == (
        "examples/certificate_kernel_execution_lab/exported_certificate_kernel_execution_lab_bundle/source_module_manifest.json"
    )
    assert standard["source_module_manifest_contract"]["body_material_count"] == 9
    assert standard["source_open_body_imports"]["body_material_count"] == 9
    assert standard["source_open_body_imports"]["body_in_receipt"] is False
    assert (
        standard["source_open_body_imports"]["body_material_classes"][
            "public_macro_proof_body"
        ]
        == 4
    )
    assert "certificate_kernel_lean_body_import" in standard[
        "source_open_body_imports"
    ]["body_material_ids"]
    assert standard["negative_cases"]["coverage_status"] == "all_observed"
    assert "cp2_certificate_contains_proof_body" in standard["negative_cases"][
        "expected"
    ]
    assert (
        "core/paper_module_capsules.json#paper_module.certificate_kernel_execution_lab"
        in {ref["path"] for ref in standard["source_refs"]}
    )
    assert (
        "core/mechanism_sources.json#mechanism.certificate_kernel_execution_lab.validates_public_certificate_kernel_execution"
        in {ref["path"] for ref in standard["source_refs"]}
    )

    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/certificate_kernel_execution_lab/exported_certificate_kernel_execution_lab_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 9
    assert all(module["body_in_receipt"] is False for module in manifest["modules"])
    assert all(module["sha256_match"] is True for module in manifest["modules"])
    assert {
        module["material_class"] for module in manifest["modules"]
    } == {
        "public_macro_proof_body",
        "public_macro_receipt_body",
        "public_macro_tool_body",
    }

    runtime_receipt = json.loads(
        (
            MICROCOSM_ROOT
            / "receipts/runtime_shell/demo_project/organs/certificate_kernel_execution_lab/exported_certificate_kernel_execution_lab_bundle_validation_result.json"
        ).read_text(encoding="utf-8")
    )
    assert runtime_receipt["status"] == "pass"
    assert runtime_receipt["body_copied_material_count"] == 9
    assert runtime_receipt["source_module_imports"]["module_count"] == 9
    assert runtime_receipt["source_open_body_imports"]["body_material_count"] == 9
    assert "certificate_kernel_lean_body_import" in runtime_receipt[
        "source_module_imports"
    ]["module_ids"]


def test_batch8_non_station_capsules_resolve_mechanism_and_code_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    bindings = {
        "batch8_audio_level_rms_port": {
            "mechanism_id": (
                "mechanism.batch8_audio_level_rms_port."
                "validates_public_audio_level_rms_port"
            ),
            "code_path": "src/microcosm_core/organs/batch8_audio_level_rms_port.py",
            "authority_class": "algorithmic_projection",
            "evidence_rank": 3,
            "bundle_ref": (
                "examples/batch8_audio_level_rms_port/"
                "exported_batch8_audio_level_rms_port_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch8_audio_level_rms_port/"
                "exported_batch8_audio_level_rms_port_bundle_validation_result.json"
            ),
        },
        "batch8_compliance_pipeline_capsule": {
            "mechanism_id": (
                "mechanism.batch8_compliance_pipeline_capsule."
                "validates_public_compliance_pipeline_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/"
                "batch8_compliance_pipeline_capsule.py"
            ),
            "authority_class": "semantic_validator",
            "evidence_rank": 5,
            "bundle_ref": (
                "examples/batch8_compliance_pipeline_capsule/"
                "exported_batch8_compliance_pipeline_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch8_compliance_pipeline_capsule/"
                "exported_batch8_compliance_pipeline_capsule_validation_result.json"
            ),
        },
        "batch8_policy_engines_capsule": {
            "mechanism_id": (
                "mechanism.batch8_policy_engines_capsule."
                "validates_public_policy_engines_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/batch8_policy_engines_capsule.py"
            ),
            "authority_class": "verified_macro_body_import",
            "evidence_rank": 5,
            "bundle_ref": (
                "examples/batch8_policy_engines_capsule/"
                "exported_batch8_policy_engines_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch8_policy_engines_capsule/"
                "exported_batch8_policy_engines_capsule_bundle_validation_result.json"
            ),
        },
        "batch8_structural_theses_capsule": {
            "mechanism_id": (
                "mechanism.batch8_structural_theses_capsule."
                "validates_public_structural_theses_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/batch8_structural_theses_capsule.py"
            ),
            "authority_class": "verified_macro_body_import",
            "evidence_rank": 5,
            "bundle_ref": (
                "examples/batch8_structural_theses_capsule/"
                "exported_batch8_structural_theses_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch8_structural_theses_capsule/"
                "exported_batch8_structural_theses_capsule_bundle_validation_result.json"
            ),
        },
        "batch8_tools_tail_primitives_capsule": {
            "mechanism_id": (
                "mechanism.batch8_tools_tail_primitives_capsule."
                "validates_public_tools_tail_primitives_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/"
                "batch8_tools_tail_primitives_capsule.py"
            ),
            "authority_class": "verified_macro_body_import",
            "evidence_rank": 5,
            "bundle_ref": (
                "examples/batch8_tools_tail_primitives_capsule/"
                "exported_batch8_tools_tail_primitives_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch8_tools_tail_primitives_capsule/"
                "exported_batch8_tools_tail_primitives_capsule_bundle_validation_result.json"
            ),
        },
        "batch8_validator_checker_capsule": {
            "mechanism_id": (
                "mechanism.batch8_validator_checker_capsule."
                "validates_public_validator_checker_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/batch8_validator_checker_capsule.py"
            ),
            "authority_class": "verified_macro_body_import",
            "evidence_rank": 5,
            "bundle_ref": (
                "examples/batch8_validator_checker_capsule/"
                "exported_batch8_validator_checker_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch8_validator_checker_capsule/"
                "exported_batch8_validator_checker_capsule_validation_result.json"
            ),
        },
    }

    assert projection["registry_atlas_join_health"]["status"] == "pass"
    for organ_id, binding in bindings.items():
        capsule_id = f"paper_module.{organ_id}"
        paper_module_ref = f"paper_modules/{organ_id}.md"
        manifest_ref = f"{binding['bundle_ref']}/source_module_manifest.json"

        assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
        _assert_atlas_required_edges_resolved(
            projection,
            organ_id,
            paper_module_ref=paper_module_ref,
            atlas_mechanism_id=binding["mechanism_id"],
            code_path=binding["code_path"],
            authority_class=binding["authority_class"],
            evidence_rank=binding["evidence_rank"],
        )

        mechanism = _mechanism_source(binding["mechanism_id"])
        assert binding["runtime_receipt_ref"] in mechanism["receipt_refs"]
        assert binding["bundle_ref"] in mechanism["input_refs"]
        assert manifest_ref in mechanism["input_refs"]

        runtime_receipt = json.loads(
            (MICROCOSM_ROOT / binding["runtime_receipt_ref"]).read_text(
                encoding="utf-8"
            )
        )
        assert runtime_receipt["status"] == "pass"


def test_batch7_9_10_11_capsules_resolve_mechanism_and_code_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    bindings = {
        "batch7_macro_engines_capsule": {
            "mechanism_id": (
                "mechanism.batch7_macro_engines_capsule."
                "validates_public_macro_engines_capsule"
            ),
            "code_path": "src/microcosm_core/organs/batch7_macro_engines_capsule.py",
            "bundle_ref": (
                "examples/batch7_macro_engines_capsule/"
                "exported_batch7_macro_engines_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch7_macro_engines_capsule/"
                "exported_batch7_macro_engines_capsule_bundle_validation_result.json"
            ),
        },
        "batch7_station_runtime_capsule": {
            "mechanism_id": (
                "mechanism.batch7_station_runtime_capsule."
                "validates_public_station_runtime_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/batch7_station_runtime_capsule.py"
            ),
            "bundle_ref": (
                "examples/batch7_station_runtime_capsule/"
                "exported_batch7_station_runtime_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch7_station_runtime_capsule/"
                "exported_batch7_station_runtime_capsule_validation_result.json"
            ),
        },
        "batch9_macro_engines_capsule": {
            "mechanism_id": (
                "mechanism.batch9_macro_engines_capsule."
                "validates_public_macro_engines_capsule"
            ),
            "code_path": "src/microcosm_core/organs/batch9_macro_engines_capsule.py",
            "bundle_ref": (
                "examples/batch9_macro_engines_capsule/"
                "exported_batch9_macro_engines_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch9_macro_engines_capsule/"
                "exported_batch9_macro_engines_capsule_bundle_validation_result.json"
            ),
        },
        "batch10_cold_eval_honesty_capsule": {
            "mechanism_id": (
                "mechanism.batch10_cold_eval_honesty_capsule."
                "validates_public_cold_eval_honesty_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/batch10_cold_eval_honesty_capsule.py"
            ),
            "bundle_ref": (
                "examples/batch10_cold_eval_honesty_capsule/"
                "exported_batch10_cold_eval_honesty_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch10_cold_eval_honesty_capsule/"
                "exported_batch10_cold_eval_honesty_capsule_validation_result.json"
            ),
        },
        "batch10_live_source_drift_capsule": {
            "mechanism_id": (
                "mechanism.batch10_live_source_drift_capsule."
                "validates_public_live_source_drift_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/batch10_live_source_drift_capsule.py"
            ),
            "bundle_ref": (
                "examples/batch10_live_source_drift_capsule/"
                "exported_batch10_live_source_drift_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch10_live_source_drift_capsule/"
                "exported_batch10_live_source_drift_capsule_bundle_validation_result.json"
            ),
        },
        "batch10_governance_compilers_capsule": {
            "mechanism_id": (
                "mechanism.batch10_governance_compilers_capsule."
                "validates_public_governance_compilers_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/"
                "batch10_governance_compilers_capsule.py"
            ),
            "bundle_ref": (
                "examples/batch10_governance_compilers_capsule/"
                "exported_batch10_governance_compilers_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch10_governance_compilers_capsule/"
                "exported_batch10_governance_compilers_capsule_bundle_validation_result.json"
            ),
        },
        "batch11_saturation_engines_capsule": {
            "mechanism_id": (
                "mechanism.batch11_saturation_engines_capsule."
                "validates_public_saturation_engines_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/batch11_saturation_engines_capsule.py"
            ),
            "bundle_ref": (
                "examples/batch11_saturation_engines_capsule/"
                "exported_batch11_saturation_engines_capsule_bundle"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "batch11_saturation_engines_capsule/"
                "exported_batch11_saturation_engines_capsule_bundle_validation_result.json"
            ),
        },
    }

    assert projection["registry_atlas_join_health"]["status"] == "pass"
    for organ_id, binding in bindings.items():
        capsule_id = f"paper_module.{organ_id}"
        paper_module_ref = f"paper_modules/{organ_id}.md"
        manifest_ref = f"{binding['bundle_ref']}/source_module_manifest.json"

        assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
        _assert_atlas_required_edges_resolved(
            projection,
            organ_id,
            paper_module_ref=paper_module_ref,
            atlas_mechanism_id=binding["mechanism_id"],
            code_path=binding["code_path"],
            authority_class="verified_macro_body_import",
            evidence_rank=5,
        )

        mechanism = _mechanism_source(binding["mechanism_id"])
        assert binding["runtime_receipt_ref"] in mechanism["receipt_refs"]
        assert binding["bundle_ref"] in mechanism["input_refs"]
        assert manifest_ref in mechanism["input_refs"]

        runtime_receipt = json.loads(
            (MICROCOSM_ROOT / binding["runtime_receipt_ref"]).read_text(
                encoding="utf-8"
            )
        )
        assert runtime_receipt["status"] == "pass"


def test_clean_five_capsules_resolve_mechanism_and_code_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    bindings = {
        "agent_sabotage_scheming_monitor_replay": {
            "mechanism_id": (
                "mechanism.agent_sabotage_scheming_monitor_replay."
                "validates_public_sabotage_scheming_monitor_replay"
            ),
            "code_path": (
                "src/microcosm_core/organs/"
                "agent_sabotage_scheming_monitor_replay.py"
            ),
            "bundle_ref": (
                "examples/agent_sabotage_scheming_monitor_replay/"
                "exported_sabotage_monitor_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/agent_sabotage_scheming_monitor_replay/"
                "agent_sabotage_scheming_monitor_replay_result.json"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "agent_sabotage_scheming_monitor_replay/"
                "exported_sabotage_monitor_bundle_validation_result.json"
            ),
        },
        "batch12_market_dashboard_read_model_capsule": {
            "mechanism_id": (
                "mechanism.batch12_market_dashboard_read_model_capsule."
                "validates_public_market_dashboard_read_model_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/"
                "batch12_market_dashboard_read_model_capsule.py"
            ),
            "bundle_ref": (
                "examples/batch12_market_dashboard_read_model_capsule/"
                "exported_batch12_market_dashboard_read_model_capsule_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/"
                "batch12_market_dashboard_read_model_capsule/"
                "batch12_market_dashboard_read_model_capsule_result.json"
            ),
        },
        "batch12_prediction_market_board_capsule": {
            "mechanism_id": (
                "mechanism.batch12_prediction_market_board_capsule."
                "validates_public_prediction_market_board_capsule"
            ),
            "code_path": (
                "src/microcosm_core/organs/"
                "batch12_prediction_market_board_capsule.py"
            ),
            "bundle_ref": (
                "examples/batch12_prediction_market_board_capsule/"
                "exported_batch12_prediction_market_board_capsule_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/batch12_prediction_market_board_capsule/"
                "batch12_prediction_market_board_capsule_result.json"
            ),
        },
        "finance_forecast_evaluation_spine": {
            "mechanism_id": (
                "mechanism.finance_forecast_evaluation_spine."
                "validates_public_finance_forecast_evaluation_spine"
            ),
            "code_path": (
                "src/microcosm_core/organs/"
                "finance_forecast_evaluation_spine.py"
            ),
            "bundle_ref": (
                "examples/finance_forecast_evaluation_spine/"
                "exported_finance_eval_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/finance_forecast_evaluation_spine/"
                "finance_forecast_evaluation_spine_result.json"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "finance_forecast_evaluation_spine/"
                "exported_finance_forecast_evaluation_spine_bundle_validation_result.json"
            ),
        },
        "standards_meta_diagnostics": {
            "mechanism_id": (
                "mechanism.standards_meta_diagnostics."
                "validates_public_standards_meta_diagnostics"
            ),
            "code_path": (
                "src/microcosm_core/organs/standards_meta_diagnostics.py"
            ),
            "bundle_ref": (
                "examples/standards_meta_diagnostics/"
                "exported_standards_meta_diagnostics_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/standards_meta_diagnostics/"
                "standards_meta_diagnostics_result.json"
            ),
            "runtime_receipt_ref": (
                "receipts/runtime_shell/demo_project/organs/"
                "standards_meta_diagnostics/"
                "exported_standards_meta_diagnostics_bundle_validation_result.json"
            ),
        },
    }

    assert projection["registry_atlas_join_health"]["status"] == "pass"
    for organ_id, binding in bindings.items():
        capsule_id = f"paper_module.{organ_id}"
        paper_module_ref = f"paper_modules/{organ_id}.md"
        manifest_ref = f"{binding['bundle_ref']}/source_module_manifest.json"

        assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
        _assert_atlas_required_edges_resolved(
            projection,
            organ_id,
            paper_module_ref=paper_module_ref,
            atlas_mechanism_id=binding["mechanism_id"],
            code_path=binding["code_path"],
            authority_class="verified_macro_body_import",
            evidence_rank=5,
        )

        mechanism = _mechanism_source(binding["mechanism_id"])
        assert binding["result_ref"] in mechanism["receipt_refs"]
        assert binding["bundle_ref"] in mechanism["input_refs"]
        assert manifest_ref in mechanism["input_refs"]

        result_receipt = json.loads(
            (MICROCOSM_ROOT / binding["result_ref"]).read_text(encoding="utf-8")
        )
        assert result_receipt["status"] == "pass"

        runtime_receipt_ref = binding.get("runtime_receipt_ref")
        if runtime_receipt_ref is not None:
            assert runtime_receipt_ref in mechanism["receipt_refs"]
            runtime_receipt = json.loads(
                (MICROCOSM_ROOT / runtime_receipt_ref).read_text(
                    encoding="utf-8"
                )
            )
            assert runtime_receipt["status"] == "pass"


def test_six_capsule_wave_resolves_mechanism_code_subject_and_law_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    bindings = {
        "concurrency_mission_control": {
            "mechanism_id": (
                "mechanism.concurrency_mission_control."
                "validates_public_concurrency_mission_control"
            ),
            "code_path": "src/microcosm_core/organs/concurrency_mission_control.py",
            "bundle_ref": (
                "examples/concurrency_mission_control/"
                "exported_concurrency_mission_control_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/concurrency_mission_control/"
                "concurrency_mission_control_result.json"
            ),
            "authority_class": "verified_macro_body_import",
            "evidence_rank": 5,
            "principle_refs": {"P-2", "P-6", "P-8", "P-10", "P-16"},
            "axiom_refs": {"AX-5", "AX-7", "AX-8", "AX-9"},
        },
        "prediction_oracle_reconciliation": {
            "mechanism_id": (
                "mechanism.prediction_oracle_reconciliation."
                "validates_public_prediction_oracle_reconciliation"
            ),
            "code_path": (
                "src/microcosm_core/organs/prediction_oracle_reconciliation.py"
            ),
            "bundle_ref": (
                "examples/prediction_oracle_reconciliation/"
                "exported_prediction_oracle_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/prediction_oracle_reconciliation/"
                "prediction_oracle_reconciliation_result.json"
            ),
            "authority_class": "algorithmic_projection",
            "evidence_rank": 3,
            "principle_refs": {"P-2", "P-6", "P-8", "P-9"},
            "axiom_refs": {"AX-5", "AX-7", "AX-8", "AX-10"},
        },
        "self_ignorance_coverage_ledger": {
            "mechanism_id": (
                "mechanism.self_ignorance_coverage_ledger."
                "validates_public_self_ignorance_coverage_ledger"
            ),
            "code_path": (
                "src/microcosm_core/organs/self_ignorance_coverage_ledger.py"
            ),
            "bundle_ref": (
                "examples/self_ignorance_coverage_ledger/"
                "exported_self_ignorance_coverage_ledger_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/self_ignorance_coverage_ledger/"
                "self_ignorance_coverage_ledger_result.json"
            ),
            "authority_class": "algorithmic_projection",
            "evidence_rank": 3,
            "principle_refs": {"P-2", "P-7", "P-11", "P-15"},
            "axiom_refs": {"AX-6", "AX-7", "AX-8", "AX-10"},
        },
        "tool_server_pressure_inventory": {
            "mechanism_id": (
                "mechanism.tool_server_pressure_inventory."
                "validates_public_tool_server_pressure_inventory"
            ),
            "code_path": (
                "src/microcosm_core/organs/tool_server_pressure_inventory.py"
            ),
            "bundle_ref": (
                "examples/tool_server_pressure_inventory/"
                "exported_tool_server_pressure_inventory_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/tool_server_pressure_inventory/"
                "tool_server_pressure_inventory_result.json"
            ),
            "authority_class": "semantic_validator",
            "evidence_rank": 5,
            "principle_refs": {"P-2", "P-4", "P-6", "P-9"},
            "axiom_refs": {"AX-3", "AX-5", "AX-7", "AX-8"},
        },
        "voice_to_doctrine_self_improvement_loop": {
            "mechanism_id": (
                "mechanism.voice_to_doctrine_self_improvement_loop."
                "validates_public_voice_to_doctrine_self_improvement_loop"
            ),
            "code_path": (
                "src/microcosm_core/organs/"
                "voice_to_doctrine_self_improvement_loop.py"
            ),
            "bundle_ref": (
                "examples/voice_to_doctrine_self_improvement_loop/"
                "exported_voice_to_doctrine_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/voice_to_doctrine_self_improvement_loop/"
                "voice_to_doctrine_self_improvement_loop_result.json"
            ),
            "authority_class": "semantic_validator",
            "evidence_rank": 5,
            "principle_refs": {"P-2", "P-7", "P-9", "P-13"},
            "axiom_refs": {"AX-6", "AX-7", "AX-8", "AX-12"},
        },
        "workstream_driver_recency_coalescer": {
            "mechanism_id": (
                "mechanism.workstream_driver_recency_coalescer."
                "validates_public_workstream_driver_recency_coalescer"
            ),
            "code_path": (
                "src/microcosm_core/organs/"
                "workstream_driver_recency_coalescer.py"
            ),
            "bundle_ref": (
                "examples/workstream_driver_recency_coalescer/"
                "exported_workstream_driver_recency_coalescer_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/workstream_driver_recency_coalescer/"
                "workstream_driver_recency_coalescer_result.json"
            ),
            "authority_class": "semantic_validator",
            "evidence_rank": 5,
            "principle_refs": {"P-2", "P-6", "P-9", "P-15"},
            "axiom_refs": {"AX-5", "AX-7", "AX-8", "AX-10"},
        },
    }

    capsule_registry = json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(
            encoding="utf-8"
        )
    )
    capsules = {
        row["id"]: row for row in capsule_registry["paper_modules"]
    }

    assert projection["registry_atlas_join_health"]["status"] == "pass"
    for organ_id, binding in bindings.items():
        capsule_id = f"paper_module.{organ_id}"
        paper_module_ref = f"paper_modules/{organ_id}.md"
        manifest_ref = f"{binding['bundle_ref']}/source_module_manifest.json"

        assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
        assert {
            "kind": "mechanism",
            "ref": binding["mechanism_id"],
        } in capsules[capsule_id]["subjects"]
        _assert_atlas_required_edges_resolved(
            projection,
            organ_id,
            paper_module_ref=paper_module_ref,
            atlas_mechanism_id=binding["mechanism_id"],
            code_path=binding["code_path"],
            authority_class=binding["authority_class"],
            evidence_rank=binding["evidence_rank"],
        )

        organ = _organ_atlas_row(organ_id)
        assert set(organ["principle_refs"]) >= binding["principle_refs"]
        assert set(organ["axiom_refs"]) >= binding["axiom_refs"]

        mechanism = _mechanism_source(binding["mechanism_id"])
        assert binding["result_ref"] in mechanism["receipt_refs"]
        assert binding["bundle_ref"] in mechanism["input_refs"]
        assert manifest_ref in mechanism["input_refs"]

        result_receipt = json.loads(
            (MICROCOSM_ROOT / binding["result_ref"]).read_text(encoding="utf-8")
        )
        assert result_receipt["status"] == "pass"


def test_replay_registry_capsule_wave_resolves_required_edges_without_law_laundering() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    health = build_lattice_health(MICROCOSM_ROOT)
    bindings = {
        "spatial_world_model_counterfactual_simulation_replay": {
            "mechanism_id": (
                "mechanism.spatial_world_model_counterfactual_simulation_replay."
                "validates_public_spatial_world_model_counterfactual_simulation_replay"
            ),
            "code_path": (
                "src/microcosm_core/organs/"
                "spatial_world_model_counterfactual_simulation_replay.py"
            ),
            "bundle_ref": (
                "examples/spatial_world_model_counterfactual_simulation_replay/"
                "exported_spatial_world_model_simulation_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/"
                "spatial_world_model_counterfactual_simulation_replay/"
                "spatial_world_model_counterfactual_simulation_replay_result.json"
            ),
        },
        "routing_anti_patterns_registry": {
            "mechanism_id": (
                "mechanism.routing_anti_patterns_registry."
                "validates_public_routing_anti_patterns_registry"
            ),
            "code_path": "src/microcosm_core/organs/routing_anti_patterns_registry.py",
            "bundle_ref": (
                "examples/routing_anti_patterns_registry/"
                "exported_routing_anti_patterns_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/routing_anti_patterns_registry/"
                "routing_anti_patterns_registry_result.json"
            ),
        },
    }
    capsule_registry = json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(
            encoding="utf-8"
        )
    )
    capsules = {
        row["id"]: row for row in capsule_registry["paper_modules"]
    }

    assert projection["registry_atlas_join_health"]["status"] == "pass"
    for organ_id, binding in bindings.items():
        capsule_id = f"paper_module.{organ_id}"
        paper_module_ref = f"paper_modules/{organ_id}.md"
        manifest_ref = f"{binding['bundle_ref']}/source_module_manifest.json"

        assert {
            "kind": "mechanism",
            "ref": binding["mechanism_id"],
        } in capsules[capsule_id]["subjects"]
        _assert_atlas_required_edges_resolved(
            projection,
            organ_id,
            paper_module_ref=paper_module_ref,
            atlas_mechanism_id=binding["mechanism_id"],
            code_path=binding["code_path"],
            authority_class="verified_macro_body_import",
            evidence_rank=5,
        )

        mechanism = _mechanism_source(binding["mechanism_id"])
        assert binding["result_ref"] in mechanism["receipt_refs"]
        assert binding["bundle_ref"] in mechanism["input_refs"]
        assert manifest_ref in mechanism["input_refs"]

        result_receipt = json.loads(
            (MICROCOSM_ROOT / binding["result_ref"]).read_text(encoding="utf-8")
        )
        assert result_receipt["status"] == "pass"

    assert "spatial_world_model_counterfactual_simulation_replay" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "routing_anti_patterns_registry" not in (
        health["organs"]["unconstrained_by_axiom"]
    )


def test_four_clean_required_edge_wave_resolves_mechanisms_without_law_laundering() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    health = build_lattice_health(MICROCOSM_ROOT)
    bindings = {
        "batch12_release_claim_language_gate": {
            "capsule_id": "paper_module.batch12_release_claim_language_gate",
            "mechanism_id": (
                "mechanism.batch12_release_claim_language_gate."
                "validates_public_release_claim_language_gate"
            ),
            "code_path": (
                "src/microcosm_core/organs/batch12_release_claim_language_gate.py"
            ),
            "bundle_ref": (
                "examples/batch12_release_claim_language_gate/"
                "exported_batch12_release_claim_language_gate_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/batch12_release_claim_language_gate/"
                "batch12_release_claim_language_gate_result.json"
            ),
            "authority_class": "semantic_validator",
        },
        "bounded_autonomy_campaign_packet": {
            "capsule_id": "paper_module.bounded_autonomy_campaign_packet",
            "mechanism_id": (
                "mechanism.bounded_autonomy_campaign_packet."
                "validates_public_bounded_autonomy_campaign_packet"
            ),
            "code_path": (
                "src/microcosm_core/organs/bounded_autonomy_campaign_packet.py"
            ),
            "bundle_ref": (
                "examples/bounded_autonomy_campaign_packet/"
                "exported_bounded_autonomy_campaign_packet_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/bounded_autonomy_campaign_packet/"
                "bounded_autonomy_campaign_packet_result.json"
            ),
            "authority_class": "semantic_validator",
        },
        "doctrine_fact_claim_audit": {
            "capsule_id": "paper_module.doctrine_fact_claim_audit",
            "mechanism_id": (
                "mechanism.doctrine_fact_claim_audit."
                "validates_public_doctrine_fact_claim_audit"
            ),
            "code_path": "src/microcosm_core/organs/doctrine_fact_claim_audit.py",
            "bundle_ref": (
                "examples/doctrine_fact_claim_audit/"
                "exported_doctrine_fact_claim_audit_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/doctrine_fact_claim_audit/"
                "doctrine_fact_claim_audit_result.json"
            ),
            "authority_class": "semantic_validator",
        },
        "pattern_assimilation_step": {
            "capsule_id": "paper_module.pattern_assimilation",
            "mechanism_id": (
                "mechanism.pattern_assimilation_step."
                "validates_public_pattern_assimilation_step"
            ),
            "code_path": "src/microcosm_core/validators/acceptance.py",
            "bundle_ref": (
                "examples/pattern_assimilation_step/exported_assimilation_bundle"
            ),
            "result_ref": (
                "receipts/first_wave/pattern_assimilation_step/"
                "pattern_assimilation_step_result.json"
            ),
            "authority_class": "semantic_validator",
        },
    }
    capsule_registry = json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(
            encoding="utf-8"
        )
    )
    capsules = {
        row["id"]: row for row in capsule_registry["paper_modules"]
    }

    assert projection["registry_atlas_join_health"]["status"] == "pass"
    for organ_id, binding in bindings.items():
        paper_module_ref = _organ_atlas_row(organ_id)["paper_module_ref"]
        manifest_ref = f"{binding['bundle_ref']}/source_module_manifest.json"

        assert {
            "kind": "mechanism",
            "ref": binding["mechanism_id"],
        } in capsules[binding["capsule_id"]]["subjects"]
        _assert_atlas_required_edges_resolved(
            projection,
            organ_id,
            paper_module_ref=paper_module_ref,
            atlas_mechanism_id=binding["mechanism_id"],
            code_path=binding["code_path"],
            authority_class=binding["authority_class"],
            evidence_rank=5,
        )

        mechanism = _mechanism_source(binding["mechanism_id"])
        assert binding["result_ref"] in mechanism["receipt_refs"]
        assert binding["bundle_ref"] in mechanism["input_refs"]
        assert manifest_ref in mechanism["input_refs"]

        result_receipt = json.loads(
            (MICROCOSM_ROOT / binding["result_ref"]).read_text(encoding="utf-8")
        )
        assert result_receipt["status"] == "pass"

    assert "bounded_autonomy_campaign_packet" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "pattern_assimilation_step" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "batch12_release_claim_language_gate" not in (
        health["organs"]["unconstrained_by_axiom"]
    )
    assert "doctrine_fact_claim_audit" not in (
        health["organs"]["unconstrained_by_axiom"]
    )


def test_engine_room_demo_mechanism_resolves_required_edges_without_law_laundering() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    health = build_lattice_health(MICROCOSM_ROOT)
    mechanism_id = "mechanism.engine_room_demo.validates_public_engine_room_demo"
    capsule_registry = json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(
            encoding="utf-8"
        )
    )
    capsules = {
        row["id"]: row for row in capsule_registry["paper_modules"]
    }

    assert {
        "kind": "mechanism",
        "ref": mechanism_id,
    } in capsules["paper_module.engine_room_demo"]["subjects"]
    _assert_atlas_required_edges_resolved(
        projection,
        "engine_room_demo",
        paper_module_ref="paper_modules/engine_room_demo.md",
        atlas_mechanism_id=mechanism_id,
        code_path="src/microcosm_core/organs/engine_room_demo.py",
        authority_class="semantic_validator",
        evidence_rank=5,
    )

    mechanism = _mechanism_source(mechanism_id)
    assert "fixtures/first_wave/engine_room_demo/input" in mechanism["input_refs"]
    assert "src/microcosm_core/engine_room/demo.py" in mechanism["input_refs"]
    assert any(
        locus["path"] == "src/microcosm_core/engine_room/demo.py"
        and locus["resolution"] == "resolved"
        for locus in mechanism["code_loci"]
    )
    for receipt_ref in [
        "receipts/acceptance/first_wave/engine_room_demo_fixture_acceptance.json",
        "receipts/first_wave/engine_room_demo/engine_room_demo_result.json",
        "receipts/first_wave/engine_room_demo/engine_room_demo_validation_receipt.json",
    ]:
        assert receipt_ref in mechanism["receipt_refs"]
        receipt = json.loads((MICROCOSM_ROOT / receipt_ref).read_text(encoding="utf-8"))
        assert receipt["status"] == "pass"

    assert "engine_room_demo" not in health["organs"]["unconstrained_by_axiom"]


def test_replay_mechanism_wave_resolves_required_edges_without_law_laundering() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest-replay-wave",
    )
    health = build_lattice_health(MICROCOSM_ROOT)
    capsule_registry = json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(
            encoding="utf-8"
        )
    )
    capsules = {
        row["id"]: row for row in capsule_registry["paper_modules"]
    }
    replay_rows = {
        "belief_state_process_reward_replay": {
            "mechanism_id": (
                "mechanism.belief_state_process_reward_replay."
                "validates_public_belief_state_process_reward_replay"
            ),
            "principle_refs": ["P-1", "P-2"],
            "axiom_refs": ["AX-1"],
            "receipt_refs": [
                "receipts/acceptance/first_wave/belief_state_process_reward_replay_fixture_acceptance.json",
                "receipts/first_wave/belief_state_process_reward_replay/belief_state_process_reward_replay_result.json",
                "receipts/runtime_shell/demo_project/organs/belief_state_process_reward_replay/exported_belief_state_process_reward_bundle_validation_result.json",
            ],
        },
        "indirect_prompt_injection_information_flow_policy_replay": {
            "mechanism_id": (
                "mechanism.indirect_prompt_injection_information_flow_policy_replay."
                "validates_public_indirect_prompt_injection_information_flow_policy_replay"
            ),
            "principle_refs": ["P-14", "P-9"],
            "axiom_refs": ["AX-8"],
            "receipt_refs": [
                "receipts/acceptance/first_wave/indirect_prompt_injection_information_flow_policy_replay_fixture_acceptance.json",
                "receipts/first_wave/indirect_prompt_injection_information_flow_policy_replay/indirect_prompt_injection_information_flow_policy_replay_result.json",
                "receipts/runtime_shell/demo_project/organs/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle_validation_result.json",
            ],
        },
        "mcp_tool_authority_replay": {
            "mechanism_id": (
                "mechanism.mcp_tool_authority_replay."
                "validates_public_mcp_tool_authority_replay"
            ),
            "principle_refs": ["P-16", "P-18", "P-4"],
            "axiom_refs": ["AX-3"],
            "receipt_refs": [
                "receipts/acceptance/first_wave/mcp_tool_authority_replay_fixture_acceptance.json",
                "receipts/first_wave/mcp_tool_authority_replay/mcp_tool_authority_replay_result.json",
                "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle_validation_result.json",
            ],
        },
        "mechanistic_interpretability_circuit_attribution_replay": {
            "mechanism_id": (
                "mechanism.mechanistic_interpretability_circuit_attribution_replay."
                "validates_public_mechanistic_interpretability_circuit_attribution_replay"
            ),
            "principle_refs": ["P-2", "P-3"],
            "axiom_refs": ["AX-1"],
            "receipt_refs": [
                "receipts/acceptance/first_wave/mechanistic_interpretability_circuit_attribution_replay_fixture_acceptance.json",
                "receipts/first_wave/mechanistic_interpretability_circuit_attribution_replay/mechanistic_interpretability_circuit_attribution_replay_result.json",
                "receipts/runtime_shell/demo_project/organs/mechanistic_interpretability_circuit_attribution_replay/exported_circuit_attribution_bundle_validation_result.json",
            ],
        },
        "sleeper_memory_poisoning_quarantine_replay": {
            "mechanism_id": (
                "mechanism.sleeper_memory_poisoning_quarantine_replay."
                "validates_public_sleeper_memory_poisoning_quarantine_replay"
            ),
            "principle_refs": ["P-14", "P-9"],
            "axiom_refs": ["AX-8"],
            "receipt_refs": [
                "receipts/acceptance/first_wave/sleeper_memory_poisoning_quarantine_replay_fixture_acceptance.json",
                "receipts/first_wave/sleeper_memory_poisoning_quarantine_replay/sleeper_memory_poisoning_quarantine_replay_result.json",
                "receipts/runtime_shell/demo_project/organs/sleeper_memory_poisoning_quarantine_replay/exported_sleeper_memory_poisoning_bundle_validation_result.json",
            ],
        },
    }

    for organ_id, row in replay_rows.items():
        mechanism_id = row["mechanism_id"]
        atlas_index, organ = _organ_atlas_indexed_row(organ_id)
        family_concept = _family_concept_map()[organ["family"]]
        assert organ["principle_refs"] == row["principle_refs"]
        assert organ["axiom_refs"] == row["axiom_refs"]
        assert family_concept in organ["concept_refs"]
        assert {
            "kind": "mechanism",
            "ref": mechanism_id,
        } in capsules[f"paper_module.{organ_id}"]["subjects"]
        _assert_atlas_required_edges_resolved(
            projection,
            organ_id,
            paper_module_ref=f"paper_modules/{organ_id}.md",
            atlas_mechanism_id=mechanism_id,
            code_path=f"src/microcosm_core/organs/{organ_id}.py",
            authority_class="verified_macro_body_import",
            evidence_rank=5,
        )

        mechanism = _mechanism_source(mechanism_id)
        assert "generated_projection_output_not_source_authority" in (
            mechanism["guardrails"]
        )
        assert "without" in mechanism["statement"]
        for receipt_ref in row["receipt_refs"]:
            assert receipt_ref in mechanism["receipt_refs"]
            receipt = json.loads(
                (MICROCOSM_ROOT / receipt_ref).read_text(encoding="utf-8")
            )
            assert receipt["status"] == "pass"

        organ_instance = json.loads(
            (MICROCOSM_ROOT / "organs" / f"{organ_id}.json").read_text(
                encoding="utf-8"
            )
        )
        edges = organ_instance["relationships"]["edges"]
        residuals = {
            residual["relation_id"]
            for residual in organ_instance["relationships"][
                "unpopulated_selective_relations"
            ]
        }
        for principle_id in row["principle_refs"]:
            assert {
                "relation_id": "organ.governed_by.principle",
                "target_id": principle_id,
                "target_kind": "principle",
                "target_status": "resolved_json_instance",
                "relation_verb": "governed_by",
                "reverse_verb": "governs",
                "residual_pressure_ref": None,
                "justification": {
                    "source_ref": (
                        f"core/organ_atlas.json::organs["
                        f"{atlas_index}:{organ_id}"
                        f"].principle_refs"
                    ),
                    "summary": (
                        "Organ atlas row names this principle as governing the organ."
                    ),
                },
            } in edges
        for axiom_id in row["axiom_refs"]:
            assert {
                "relation_id": "organ.constrained_by.axiom",
                "target_id": axiom_id,
                "target_kind": "axiom",
                "target_status": "resolved_json_instance",
                "relation_verb": "constrained_by",
                "reverse_verb": "constrains",
                "residual_pressure_ref": None,
                "justification": {
                    "source_ref": (
                        f"core/organ_atlas.json::organs["
                        f"{atlas_index}:{organ_id}"
                        f"].axiom_refs"
                    ),
                    "summary": (
                        "Organ atlas row names this axiom as a selective constraint "
                        "for the organ."
                    ),
                },
            } in edges
        assert "organ.governed_by.principle" not in residuals
        assert "organ.constrained_by.axiom" not in residuals
        assert "organ.instantiates.concept" not in residuals
        assert {
            "relation_id": "organ.instantiates.concept",
            "target_id": family_concept,
            "target_kind": "concept",
            "target_status": "resolved_json_instance",
            "relation_verb": "instantiates",
            "reverse_verb": "instantiated_by",
            "residual_pressure_ref": None,
            "justification": {
                "source_ref": (
                    f"core/organ_atlas.json::organs[{atlas_index}:{organ_id}].concept_refs"
                ),
                "summary": (
                    "Organ atlas row names this recurring concept boundary for the organ."
                ),
            },
        } in edges
        assert "organ.wires_to.organ" in residuals

    assert set(replay_rows).isdisjoint(health["organs"]["required_edge_gaps"])
    assert set(replay_rows).issubset(
        set(health["organs"]["unpopulated_selective_edges"])
    )


def test_agent_replay_law_binding_wave_remains_claim_ceiling_bounded() -> None:
    health = build_lattice_health(MICROCOSM_ROOT)
    family_concepts = _family_concept_map()
    law_bound_organs = {
        "agent_benchmark_integrity_anti_gaming_replay",
        "agent_closeout_faithfulness_audit",
        "agent_memory_temporal_conflict_replay",
        "agent_monitor_redteam_falsification_replay",
        "agent_route_observability_runtime",
        "agent_sandbox_policy_escape_replay",
        "agentic_vulnerability_discovery_patch_proof_replay",
    }
    law_bound_organs_with_wiring_residual = set()

    for organ_id in law_bound_organs:
        atlas_index, organ = _organ_atlas_indexed_row(organ_id)
        assert organ["family"] == "agent_reliability_and_safety"
        family_concept = family_concepts[organ["family"]]
        if not organ.get("wires_to"):
            law_bound_organs_with_wiring_residual.add(organ_id)
        claim_ceiling = organ["claim_ceiling_restated"].lower()
        assert any(
            phrase in claim_ceiling
            for phrase in ("does not", "authorizes no", "not real", "; no ")
        )
        assert organ["principle_refs"] == ["P-1", "P-2"]
        assert organ["axiom_refs"] == ["AX-1"]

        organ_instance = json.loads(
            (MICROCOSM_ROOT / "organs" / f"{organ_id}.json").read_text(
                encoding="utf-8"
            )
        )
        edges = organ_instance["relationships"]["edges"]
        residuals = {
            residual["relation_id"]
            for residual in organ_instance["relationships"][
                "unpopulated_selective_relations"
            ]
        }
        principle_edges = [
            edge
            for edge in edges
            if edge["relation_id"] == "organ.governed_by.principle"
        ]
        axiom_edges = [
            edge
            for edge in edges
            if edge["relation_id"] == "organ.constrained_by.axiom"
        ]

        assert {edge["target_id"] for edge in principle_edges} == {"P-1", "P-2"}
        assert {edge["target_id"] for edge in axiom_edges} == {"AX-1"}
        assert {
            edge["justification"]["source_ref"] for edge in principle_edges
        } == {
            f"core/organ_atlas.json::organs[{atlas_index}:{organ_id}].principle_refs"
        }
        assert {edge["justification"]["source_ref"] for edge in axiom_edges} == {
            f"core/organ_atlas.json::organs[{atlas_index}:{organ_id}].axiom_refs"
        }
        assert "organ.governed_by.principle" not in residuals
        assert "organ.constrained_by.axiom" not in residuals
        assert "organ.instantiates.concept" not in residuals
        assert any(
            edge["relation_id"] == "organ.instantiates.concept"
            and edge["target_id"] == family_concept
            and edge["target_status"] == "resolved_json_instance"
            for edge in edges
        )
        if "organ.wires_to.organ" not in residuals:
            assert any(
                edge["relation_id"] == "organ.wires_to.organ" for edge in edges
            )

    assert law_bound_organs.isdisjoint(health["organs"]["unconstrained_by_axiom"])
    assert law_bound_organs_with_wiring_residual.issubset(
        set(health["organs"]["unpopulated_selective_edges"])
    )


def test_corpus_readiness_mathlib_absence_gate_population_has_capsule_and_mechanism_prestaged_until_atlas_binding() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.corpus_readiness_mathlib_absence_gate"
    mechanism_id = (
        "mechanism.corpus_readiness_mathlib_absence_gate."
        "validates_public_corpus_readiness_boundary"
    )
    mathlib_absence_mechanism_id = (
        "mechanism.corpus_readiness_mathlib_absence_gate."
        "validates_public_mathlib_absence_boundary"
    )
    lean_witness_mechanism_id = (
        "mechanism.formal_math_lean_proof_witness.validates_public_lean_lake_witness"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    _assert_atlas_required_edges_resolved(
        projection,
        "corpus_readiness_mathlib_absence_gate",
        paper_module_ref="paper_modules/corpus_readiness_mathlib_absence.md",
        atlas_mechanism_id=mathlib_absence_mechanism_id,
        code_path="src/microcosm_core/organs/corpus_readiness_mathlib_absence_gate.py",
    )

    capsule_registry = json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(
            encoding="utf-8"
        )
    )
    capsule = next(
        row for row in capsule_registry["paper_modules"] if row["id"] == capsule_id
    )
    assert capsule["legacy_markdown_projection"] == (
        "paper_modules/corpus_readiness_mathlib_absence.md"
    )
    assert {"kind": "organ", "ref": "corpus_readiness_mathlib_absence_gate"} in (
        capsule["subjects"]
    )
    assert {"kind": "mechanism", "ref": mechanism_id} in capsule["subjects"]
    assert "validate_source_module_imports" in capsule["code_loci"][0]["symbols"]

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["corpus_readiness_mathlib_absence_gate"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/corpus_readiness_mathlib_absence_gate.py"
    )
    assert "run_projection_bundle" in mechanism["code_loci"][0]["symbols"]
    assert "validate_consumer_gate_cases" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["authority_class"] == (
        "algorithmic_projection"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert (
        "receipts/runtime_shell/demo_project/organs/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_module_manifest.json"
        in mechanism["input_refs"]
    )

    mathlib_absence_instance = json.loads(
        (
            MICROCOSM_ROOT
            / "mechanisms"
            / f"{mathlib_absence_mechanism_id}.json"
        ).read_text(encoding="utf-8")
    )
    assert any(
        edge["relation_id"] == "mechanism.upstream_of.mechanism"
        and edge["target_id"] == lean_witness_mechanism_id
        and edge["target_status"] == "resolved_json_instance"
        for edge in mathlib_absence_instance["relationships"]["edges"]
    )
    assert "mechanism.upstream_of.mechanism" not in {
        residual["relation_id"]
        for residual in mathlib_absence_instance["relationships"][
            "unpopulated_selective_relations"
        ]
    }

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_corpus_readiness_mathlib_absence_gate.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.corpus_readiness_mathlib_absence_gate"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["paper_module_contract"]["module_slug"] == (
        "corpus_readiness_mathlib_absence"
    )
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == (
        "deferred_for_sibling_organ_atlas_lane"
    )
    assert standard["source_module_manifest_contract"]["manifest_ref"] == (
        "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_module_manifest.json"
    )
    assert standard["source_module_manifest_contract"]["body_material_count"] == 4
    assert standard["source_open_body_imports"]["body_material_count"] == 4
    assert standard["source_open_body_imports"]["body_in_receipt"] is False
    assert (
        standard["source_open_body_imports"]["body_material_classes"][
            "public_macro_receipt_body"
        ]
        == 3
    )
    assert (
        "prover_proof_state_curriculum_tactic_affordance_probe_mathlib_probe_lean_body_import"
        in standard["source_open_body_imports"]["body_material_ids"]
    )
    assert standard["negative_cases"]["coverage_status"] == "all_observed"
    assert "mathlib_available_without_probe" in standard["negative_cases"][
        "expected"
    ]
    assert (
        "core/paper_module_capsules.json#paper_module.corpus_readiness_mathlib_absence_gate"
        in {ref["path"] for ref in standard["source_refs"]}
    )
    assert (
        "core/mechanism_sources.json#mechanism.corpus_readiness_mathlib_absence_gate.validates_public_corpus_readiness_boundary"
        in {ref["path"] for ref in standard["source_refs"]}
    )

    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert len(manifest["modules"]) == 4
    assert all(module["body_copied"] is True for module in manifest["modules"])
    assert all(module["body_in_receipt"] is False for module in manifest["modules"])
    assert all(module["sha256_match"] is True for module in manifest["modules"])
    assert {
        module["material_class"] for module in manifest["modules"]
    } == {
        "public_macro_receipt_body",
        "public_macro_tool_body",
    }

    runtime_receipt = json.loads(
        (
            MICROCOSM_ROOT
            / "receipts/runtime_shell/demo_project/organs/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle_validation_result.json"
        ).read_text(encoding="utf-8")
    )
    assert runtime_receipt["status"] == "pass"
    assert runtime_receipt["source_module_import_count"] == 4
    assert runtime_receipt["copied_source_artifact_count"] == 4
    assert runtime_receipt["source_modules_pass"] is True
    assert runtime_receipt["body_in_receipt"] is False
    assert runtime_receipt["mathlib_lake_project_import_available"] is False
    assert "mathlib_import_blocked_until_probe" in runtime_receipt["blocked_case_ids"]
    assert {
        row["module_id"] for row in runtime_receipt["source_module_imports"]
    } == {
        "prover_proof_state_curriculum_corpus_readiness_json_body_import",
        "prover_proof_state_curriculum_tactic_affordance_probe_json_body_import",
        "prover_proof_state_curriculum_tactic_affordance_probe_mathlib_probe_lean_body_import",
        "prover_proof_state_curriculum_tactic_affordance_probe_portfolio_availability_json_body_import",
    }


def test_corpus_readiness_paper_module_capsule_is_not_shadowed_by_legacy_slug() -> None:
    instance = expected_paper_module_instances(MICROCOSM_ROOT)[
        "paper_module.corpus_readiness_mathlib_absence_gate"
    ]
    relationships = instance["relationships"]

    assert instance["paper_module_payload"]["source_authority"] == "json_capsule"
    assert instance["status"] == "active"
    assert relationships["source_ref"].startswith(
        "core/paper_module_capsules.json::paper_modules"
    )
    assert relationships["subjects"] == [
        {"kind": "organ", "ref": "corpus_readiness_mathlib_absence_gate"},
        {
            "kind": "mechanism",
            "ref": (
                "mechanism.corpus_readiness_mathlib_absence_gate."
                "validates_public_corpus_readiness_boundary"
            ),
        },
        {
            "kind": "mechanism",
            "ref": (
                "mechanism.corpus_readiness_mathlib_absence_gate."
                "validates_public_mathlib_absence_boundary"
            ),
        },
    ]
    assert any(
        edge["relation_id"] == "paper_module.explains.organ_or_mechanism"
        for edge in relationships["edges"]
    )


def test_world_model_projection_drift_control_room_population_resolves_required_edges() -> None:
    capsule_id = "paper_module.world_model_projection_drift_control_room"
    macro_capsule_id = "paper_module.macro_projection_import_protocol"
    mechanism_id = (
        "mechanism.world_model_projection_drift_control_room."
        "validates_public_projection_drift_control_boundary"
    )
    macro_mechanism_id = (
        "mechanism.macro_projection_import_protocol."
        "validates_public_macro_projection_imports"
    )
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    paper_module = json.loads(
        (
            MICROCOSM_ROOT
            / "paper_modules/world_model_projection_drift_control_room.json"
        ).read_text(encoding="utf-8")
    )
    assert paper_module["id"] == capsule_id
    assert paper_module["relationships"]["depends_on"] == [macro_capsule_id]
    assert paper_module["relationships"]["unpopulated_selective_relations"] == []
    assert any(
        edge["relation_id"] == "paper_module.depends_on.paper_module"
        and edge["target_id"] == macro_capsule_id
        for edge in paper_module["relationships"]["edges"]
    )
    assert "world_model_projection_drift_control_room" not in coverage["without_paper_module_ref"]
    assert "world_model_projection_drift_control_room" not in coverage["without_mechanism_ref"]
    assert "world_model_projection_drift_control_room" not in coverage["without_code_loci"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["world_model_projection_drift_control_room"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/world_model_projection_drift_control_room.py"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 5
    assert (
        "receipts/runtime_shell/demo_project/organs/world_model_projection_drift_control_room/exported_projection_drift_control_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    macro_mechanism = next(
        row
        for row in mechanism_registry["mechanisms"]
        if row["id"] == macro_mechanism_id
    )
    assert mechanism_id in macro_mechanism["upstream_of"]

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_world_model_projection_drift_control_room.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.world_model_projection_drift_control_room"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert (
        standard["source_module_manifest_contract"]["manifest_ref"]
        == "examples/world_model_projection_drift_control_room/exported_projection_drift_control_bundle/source_module_manifest.json"
    )
    assert standard["source_module_manifest_contract"]["body_material_count"] == 4
    assert standard["source_open_body_imports"]["body_in_receipt"] is False
    assert "source authority" in (
        standard["doctrine_population_status"]["authority_boundary"]
    )


def test_formal_math_premise_retrieval_population_has_capsule_and_mechanism_prestaged_until_atlas_binding() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.formal_math_premise_retrieval"
    mechanism_id = (
        "mechanism.formal_math_premise_retrieval."
        "validates_public_premise_retrieval_slice"
    )
    atlas_mechanism_id = (
        "mechanism.formal_math_premise_retrieval."
        "validates_public_premise_retrieval_projection"
    )
    verifier_lab_mechanism_id = (
        "mechanism.verifier_lab_kernel.composes_public_formal_math_receipts"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    _assert_atlas_required_edges_resolved(
        projection,
        "formal_math_premise_retrieval",
        paper_module_ref="paper_modules/formal_math_premise_retrieval.md",
        atlas_mechanism_id=atlas_mechanism_id,
        code_path="src/microcosm_core/organs/formal_math_premise_retrieval.py",
    )

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["formal_math_premise_retrieval"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/formal_math_premise_retrieval.py"
    )
    assert "run_retrieval_bundle" in mechanism["code_loci"][0]["symbols"]
    assert "_retrieval_bundle_freshness_basis" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert (
        "receipts/runtime_shell/demo_project/organs/formal_math_premise_retrieval/exported_premise_retrieval_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/formal_math_premise_retrieval/exported_premise_retrieval_bundle/source_module_manifest.json"
        in mechanism["input_refs"]
    )
    assert (
        "examples/formal_math_premise_retrieval/exported_premise_retrieval_bundle/source_body_floor/source_module_manifest.json"
        in mechanism["input_refs"]
    )

    premise_instance = json.loads(
        (
            MICROCOSM_ROOT
            / "mechanisms"
            / f"{atlas_mechanism_id}.json"
        ).read_text(encoding="utf-8")
    )
    assert any(
        edge["relation_id"] == "mechanism.upstream_of.mechanism"
        and edge["target_id"] == verifier_lab_mechanism_id
        and edge["target_status"] == "resolved_json_instance"
        for edge in premise_instance["relationships"]["edges"]
    )
    assert "mechanism.upstream_of.mechanism" not in {
        residual["relation_id"]
        for residual in premise_instance["relationships"][
            "unpopulated_selective_relations"
        ]
    }

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_formal_math_premise_retrieval.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.formal_math_premise_retrieval"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == (
        "deferred_for_sibling_organ_atlas_lane"
    )
    assert (
        standard["doctrine_population_status"]["coverage_projection_status"]
        == "json_corpus_populated_atlas_edges_pending"
    )
    assert standard["source_module_manifest_contract"]["runtime_manifest_ref"] == (
        "examples/formal_math_premise_retrieval/exported_premise_retrieval_bundle/source_module_manifest.json"
    )
    assert standard["source_module_manifest_contract"]["body_floor_manifest_ref"] == (
        "examples/formal_math_premise_retrieval/exported_premise_retrieval_bundle/source_body_floor/source_module_manifest.json"
    )
    assert standard["source_module_manifest_contract"]["body_material_count"] == 6
    assert standard["source_open_body_floor"]["body_material_count"] == 6
    assert standard["source_open_body_floor"]["body_text_exported_in_receipts"] is False
    assert standard["negative_cases"]["coverage_status"] == "all_observed"
    assert "query_oracle_ids_forbidden" in standard["negative_cases"]["expected"]
    assert "core/paper_module_capsules.json#paper_module.formal_math_premise_retrieval" in {
        ref["path"] for ref in standard["source_refs"]
    }
    assert (
        "core/mechanism_sources.json#mechanism.formal_math_premise_retrieval.validates_public_premise_retrieval_slice"
        in {ref["path"] for ref in standard["source_refs"]}
    )

    runtime_manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/formal_math_premise_retrieval/exported_premise_retrieval_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert runtime_manifest["body_in_receipt"] is False
    assert runtime_manifest["module_count"] == 4
    assert len(runtime_manifest["source_faithful_modules"]) == 2
    assert all(module["body_in_receipt"] is False for module in runtime_manifest["modules"])
    assert all(module["sha256_match"] is True for module in runtime_manifest["modules"])
    assert {
        module["source_to_target_relation"]
        for module in runtime_manifest["source_faithful_modules"]
    } == {
        "source_faithful_normalized_copy",
        "source_faithful_public_query_slice",
    }

    body_floor_manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/formal_math_premise_retrieval/exported_premise_retrieval_bundle/source_body_floor/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert body_floor_manifest["body_in_receipt"] is False
    assert body_floor_manifest["module_count"] == 1
    assert body_floor_manifest["modules"][0]["source_to_target_relation"] == "exact_copy"


def test_lean_std_premise_index_population_has_capsule_and_mechanism_prestaged_until_atlas_binding() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.lean_std_premise_index"
    mechanism_id = (
        "mechanism.lean_std_premise_index."
        "validates_public_lean_std_premise_catalog"
    )
    atlas_mechanism_id = (
        "mechanism.lean_std_premise_index."
        "validates_public_lean_std_premise_index"
    )
    strategy_mechanism_id = (
        "mechanism.mathematical_strategy_atlas_hypothesis_scorer."
        "validates_public_strategy_hypothesis_projection"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"
    _assert_atlas_required_edges_resolved(
        projection,
        "lean_std_premise_index",
        paper_module_ref="paper_modules/lean_std_premise_index.md",
        atlas_mechanism_id=atlas_mechanism_id,
        code_path="src/microcosm_core/organs/lean_std_premise_index.py",
    )

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["lean_std_premise_index"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/lean_std_premise_index.py"
    )
    assert "run_index_bundle" in mechanism["code_loci"][0]["symbols"]
    assert "_source_module_manifest_result" in mechanism["code_loci"][0]["symbols"]
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert (
        "receipts/runtime_shell/demo_project/organs/lean_std_premise_index/exported_lean_std_premise_index_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "examples/lean_std_premise_index/exported_lean_std_premise_index_bundle/source_module_manifest.json"
        in mechanism["input_refs"]
    )

    lean_std_instance = json.loads(
        (
            MICROCOSM_ROOT
            / "mechanisms"
            / f"{atlas_mechanism_id}.json"
        ).read_text(encoding="utf-8")
    )
    assert any(
        edge["relation_id"] == "mechanism.upstream_of.mechanism"
        and edge["target_id"] == strategy_mechanism_id
        and edge["target_status"] == "resolved_json_instance"
        for edge in lean_std_instance["relationships"]["edges"]
    )
    assert "mechanism.upstream_of.mechanism" not in {
        residual["relation_id"]
        for residual in lean_std_instance["relationships"][
            "unpopulated_selective_relations"
        ]
    }

    standard = json.loads(
        (
            MICROCOSM_ROOT / "standards/std_microcosm_lean_std_premise_index.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.lean_std_premise_index"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == (
        "deferred_for_sibling_organ_atlas_lane"
    )
    assert (
        standard["doctrine_population_status"]["coverage_projection_status"]
        == "json_corpus_populated_atlas_edges_pending"
    )
    assert standard["source_module_manifest_contract"]["manifest_ref"] == (
        "examples/lean_std_premise_index/exported_lean_std_premise_index_bundle/source_module_manifest.json"
    )
    assert standard["source_open_body_floor"]["body_material_count"] == 6
    assert standard["source_open_body_floor"]["body_text_exported_in_receipts"] is False
    assert standard["negative_cases"]["coverage_status"] == "all_observed"
    assert "mathlib_premise_forbidden" in standard["negative_cases"]["expected"]
    assert "core/paper_module_capsules.json#paper_module.lean_std_premise_index" in {
        ref["path"] for ref in standard["source_refs"]
    }
    assert (
        "core/mechanism_sources.json#mechanism.lean_std_premise_index.validates_public_lean_std_premise_catalog"
        in {ref["path"] for ref in standard["source_refs"]}
    )

    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/lean_std_premise_index/exported_lean_std_premise_index_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 6
    assert any(
        module["source_to_target_relation"] == "source_faithful_normalized_copy"
        for module in manifest["modules"]
    )
    assert all(module["body_in_receipt"] is False for module in manifest["modules"])
    assert all(
        module["sha256_match"] is True
        for module in manifest["modules"]
        if module["source_to_target_relation"] == "exact_public_safe_macro_copy"
    )


def test_proof_diagnostic_evidence_spine_population_has_capsule_and_mechanism_source() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.proof_diagnostic_evidence_spine"
    mechanism_id = (
        "mechanism.proof_diagnostic_evidence_spine."
        "validates_ring2_diagnostic_evidence_membrane"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["proof_diagnostic_evidence_spine"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/proof_diagnostic_evidence_spine.py"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 3
    assert "receipts/runtime_shell/demo_project/organs/proof_diagnostic_evidence_spine/exported_evidence_bundle_validation_result.json" in (
        mechanism["receipt_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_proof_diagnostic_evidence_spine.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.proof_diagnostic_evidence_spine"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert "algorithmic-projection evidence ceiling" in (
        standard["doctrine_population_status"]["authority_boundary"]
    )
    assert "proof_diagnostic_evidence_spine" not in coverage["without_paper_module_ref"]
    assert "proof_diagnostic_evidence_spine" not in coverage["without_mechanism_ref"]
    assert "proof_diagnostic_evidence_spine" not in coverage["without_code_loci"]


def test_durable_agent_work_landing_replay_population_has_capsule_and_mechanism_source() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.durable_agent_work_landing_replay"
    mechanism_id = (
        "mechanism.durable_agent_work_landing_replay."
        "validates_public_work_landing_replay_contract"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    bridge_mechanism = next(
        row
        for row in mechanism_registry["mechanisms"]
        if row["id"]
        == "mechanism.bridge_phase_continuity_runtime.validates_synthetic_bridge_continuity"
    )
    assert mechanism["runs_in"] == ["durable_agent_work_landing_replay"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/durable_agent_work_landing_replay.py"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 5
    assert (
        "receipts/runtime_shell/demo_project/organs/durable_agent_work_landing_replay/exported_work_landing_replay_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    paper_module = json.loads(
        (
            MICROCOSM_ROOT / "paper_modules/durable_agent_work_landing_replay.json"
        ).read_text(encoding="utf-8")
    )
    depends_edges = [
        edge
        for edge in paper_module["relationships"]["edges"]
        if edge["relation_id"] == "paper_module.depends_on.paper_module"
    ]
    assert depends_edges == [
        {
            "relation_id": "paper_module.depends_on.paper_module",
            "relation_verb": "depends_on",
            "reverse_verb": "depended_on_by",
            "target_kind": "paper_module",
            "target_id": "paper_module.bridge_phase_continuity_runtime",
            "target_status": "resolved_json_instance",
            "justification": {
                "source_ref": (
                    "core/paper_module_capsules.json::paper_modules"
                    "[16:paper_module.durable_agent_work_landing_replay].depends_on"
                ),
                "summary": (
                    "Paper-module source row names this sibling/dependency "
                    "paper module."
                ),
            },
            "residual_pressure_ref": None,
        }
    ]
    assert mechanism_id in bridge_mechanism["upstream_of"]
    assert (
        "mechanism.mission_transaction_work_spine."
        "validates_public_mission_transaction_bundle"
        in mechanism["upstream_of"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_durable_agent_work_landing_replay.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.durable_agent_work_landing_replay"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert "replay-only evidence ceiling" in (
        standard["doctrine_population_status"]["authority_boundary"]
    )
    assert "durable_agent_work_landing_replay" not in coverage["without_paper_module_ref"]
    assert "durable_agent_work_landing_replay" not in coverage["without_mechanism_ref"]
    assert "durable_agent_work_landing_replay" not in coverage["without_code_loci"]


def test_executable_doctrine_grammar_population_resolves_required_edges() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.executable_doctrine_grammar"
    mechanism_id = (
        "mechanism.executable_doctrine_grammar."
        "validates_public_doctrine_grammar_bundle"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["executable_doctrine_grammar"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/executable_doctrine_grammar.py"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 5
    assert (
        "receipts/first_wave/executable_doctrine_grammar/exported_executable_grammar_metabolism_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_executable_doctrine_grammar.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.executable_doctrine_grammar"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert standard["source_open_body_imports"]["body_material_count"] == 12
    assert standard["source_open_body_imports"]["body_in_receipt"] is False
    assert "executable_doctrine_grammar" not in coverage["without_paper_module_ref"]
    assert "executable_doctrine_grammar" not in coverage["without_mechanism_ref"]
    assert "executable_doctrine_grammar" not in coverage["without_code_loci"]


def test_proof_derived_governed_mutation_authorization_population_has_capsule_and_mechanism_source() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.proof_derived_governed_mutation_authorization"
    mechanism_id = (
        "mechanism.proof_derived_governed_mutation_authorization."
        "validates_synthetic_governed_mutation_authorization"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    capsule_registry = json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(encoding="utf-8")
    )
    capsule = next(
        row for row in capsule_registry["paper_modules"] if row["id"] == capsule_id
    )
    assert capsule["depends_on"] == ["paper_module.mission_transaction_work_spine"]

    paper_module = json.loads(
        (
            MICROCOSM_ROOT
            / "paper_modules/proof_derived_governed_mutation_authorization.json"
        ).read_text(encoding="utf-8")
    )
    assert paper_module["relationships"]["unpopulated_selective_relations"] == []
    assert any(
        edge["relation_id"] == "paper_module.depends_on.paper_module"
        and edge["target_id"] == "paper_module.mission_transaction_work_spine"
        for edge in paper_module["relationships"]["edges"]
    )

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    mission_mechanism = next(
        row
        for row in mechanism_registry["mechanisms"]
        if row["id"]
        == "mechanism.mission_transaction_work_spine.validates_public_mission_transaction_bundle"
    )
    assert mechanism["runs_in"] == ["proof_derived_governed_mutation_authorization"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/proof_derived_governed_mutation_authorization.py"
    )
    assert mechanism_id in mission_mechanism["upstream_of"]
    assert mechanism["resolution_evidence"]["evidence_rank"] == 5
    assert (
        "receipts/first_wave/proof_derived_governed_mutation_authorization/exported_governed_mutation_authorization_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_proof_derived_governed_mutation_authorization.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.proof_derived_governed_mutation_authorization"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert standard["source_open_body_imports"]["body_material_count"] == 6
    assert standard["source_open_body_imports"]["body_in_receipt"] is False
    assert "standing credential authority" in (
        standard["doctrine_population_status"]["authority_boundary"]
    )
    assert (
        "proof_derived_governed_mutation_authorization"
        not in coverage["without_paper_module_ref"]
    )
    assert (
        "proof_derived_governed_mutation_authorization"
        not in coverage["without_mechanism_ref"]
    )
    assert (
        "proof_derived_governed_mutation_authorization"
        not in coverage["without_code_loci"]
    )


def test_public_reveal_walkthrough_population_has_capsule_mechanism_and_manifest_hygiene() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.public_reveal_walkthrough"
    mechanism_id = (
        "mechanism.public_reveal_walkthrough."
        "validates_public_reveal_walkthrough"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["public_reveal_walkthrough"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/public_reveal_walkthrough.py"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 5
    assert (
        "receipts/runtime_shell/demo_project/organs/public_reveal_walkthrough/exported_public_reveal_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    _assert_atlas_required_edges_resolved(
        projection,
        "public_reveal_walkthrough",
        paper_module_ref="paper_modules/public_reveal_walkthrough.md",
        atlas_mechanism_id=mechanism_id,
        code_path="src/microcosm_core/organs/public_reveal_walkthrough.py",
    )
    paper_module = json.loads(
        (
            MICROCOSM_ROOT / "paper_modules/public_reveal_walkthrough.json"
        ).read_text(encoding="utf-8")
    )
    depends_edges = [
        edge
        for edge in paper_module["relationships"]["edges"]
        if edge["relation_id"] == "paper_module.depends_on.paper_module"
    ]
    assert depends_edges == [
        {
            "relation_id": "paper_module.depends_on.paper_module",
            "relation_verb": "depends_on",
            "reverse_verb": "depended_on_by",
            "target_kind": "paper_module",
            "target_id": "paper_module.first_screen_composition_root",
            "target_status": "resolved_json_instance",
            "justification": {
                "source_ref": (
                    "core/paper_module_capsules.json::paper_modules"
                    "[28:paper_module.public_reveal_walkthrough].depends_on"
                ),
                "summary": (
                    "Paper-module source row names this sibling/dependency "
                    "paper module."
                ),
            },
            "residual_pressure_ref": None,
        }
    ]

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_public_reveal_walkthrough.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.public_reveal_walkthrough"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["source_open_body_imports"]["body_material_count"] == 5
    assert standard["source_open_body_imports"]["body_in_receipt"] is False

    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/public_reveal_walkthrough/exported_public_reveal_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 5
    assert all(
        module["source_to_target_relation"] == "exact_copy"
        for module in manifest["modules"]
    )
    assert all(module["sha256_match"] is True for module in manifest["modules"])
    assert all(module["sha256"].startswith("sha256:") for module in manifest["modules"])
    assert all(
        module["source_sha256"].startswith("sha256:")
        for module in manifest["modules"]
    )
    assert all(
        module["target_sha256"].startswith("sha256:")
        for module in manifest["modules"]
    )


def test_cognitive_operator_registry_population_has_capsule_and_mechanism_source() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.cognitive_operator_registry"
    mechanism_id = (
        "mechanism.cognitive_operator_registry."
        "validates_public_operator_contract"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["cognitive_operator_registry"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/cognitive_operator_registry.py"
    )
    assert "receipts/first_wave/cognitive_operator_registry/exported_cognitive_operator_registry_bundle_validation_result.json" in (
        mechanism["receipt_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_cognitive_operator_registry.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.cognitive_operator_registry"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert "cognitive_operator_registry" not in coverage["without_paper_module_ref"]
    assert "cognitive_operator_registry" not in coverage["without_mechanism_ref"]
    assert "cognitive_operator_registry" not in coverage["without_code_loci"]


def test_pattern_binding_contract_population_has_capsule_and_mechanism_source() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.pattern_binding_contract"
    mechanism_id = (
        "mechanism.pattern_binding_contract."
        "validates_public_pattern_bindings"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["pattern_binding_contract"]
    assert {
        locus["path"] for locus in mechanism["code_loci"]
    } == {
        "src/microcosm_core/organs/pattern_binding_contract.py",
        "src/microcosm_core/macro_tools/pattern_route_readiness.py",
    }
    assert mechanism["resolution_evidence"]["evidence_rank"] == 5
    assert (
        "receipts/first_wave/pattern_binding_contract/exported_substrate_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "receipts/first_wave/pattern_binding_contract/route_readiness/exported_route_readiness_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_pattern_binding_contract.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.pattern_binding_contract"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert "standalone public leaves" in (
        standard["doctrine_population_status"]["authority_boundary"]
    )
    assert "pattern_binding_contract" not in coverage["without_paper_module_ref"]
    assert "pattern_binding_contract" not in coverage["without_mechanism_ref"]
    assert "pattern_binding_contract" not in coverage["without_code_loci"]


def test_macro_projection_import_protocol_population_has_capsule_and_mechanism_source() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest",
    )
    coverage = projection["organ_required_edge_coverage"]
    capsule_id = "paper_module.macro_projection_import_protocol"
    mechanism_id = (
        "mechanism.macro_projection_import_protocol."
        "validates_public_macro_projection_imports"
    )

    assert capsule_id in projection["paper_module_corpus"]["json_capsule_ids"]
    assert projection["registry_atlas_join_health"]["status"] == "pass"

    mechanism_registry = json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(encoding="utf-8")
    )
    mechanism = next(
        row for row in mechanism_registry["mechanisms"] if row["id"] == mechanism_id
    )
    assert mechanism["runs_in"] == ["macro_projection_import_protocol"]
    assert mechanism["code_loci"][0]["path"] == (
        "src/microcosm_core/organs/macro_projection_import_protocol.py"
    )
    assert mechanism["resolution_evidence"]["evidence_rank"] == 5
    assert (
        "receipts/first_wave/macro_projection_import_protocol/exported_projection_import_bundle_validation_result.json"
        in mechanism["receipt_refs"]
    )
    assert (
        "receipts/acceptance/first_wave/macro_projection_import_protocol_fixture_acceptance.json"
        in mechanism["receipt_refs"]
    )

    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_macro_projection_import_protocol.json"
        ).read_text(encoding="utf-8")
    )
    assert standard["paper_module_contract"]["capsule_ref"] == (
        "core/paper_module_capsules.json#paper_module.macro_projection_import_protocol"
    )
    assert standard["paper_module_contract"]["mechanism_ref"] == mechanism_id
    assert standard["doctrine_population_status"]["json_capsule"] == "populated"
    assert standard["doctrine_population_status"]["mechanism_source"] == "populated"
    assert standard["doctrine_population_status"]["atlas_binding_status"] == "populated"
    assert "static receipt-count claims" in (
        standard["doctrine_population_status"]["authority_boundary"]
    )
    assert standard["source_module_manifest_contract"]["manifest_glob"] == (
        "examples/macro_projection_import_protocol/exported_projection_import_bundle/*_source_module_manifest.json"
    )
    assert "core/paper_module_capsules.json#paper_module.macro_projection_import_protocol" in {
        ref["path"] for ref in standard["source_refs"]
    }
    assert "macro_projection_import_protocol" not in coverage["without_paper_module_ref"]
    assert "macro_projection_import_protocol" not in coverage["without_mechanism_ref"]
    assert "macro_projection_import_protocol" not in coverage["without_code_loci"]


def test_doctrine_lattice_entry_card_is_microcosm_local_and_projection_backed() -> None:
    projection = build_coverage_projection(
        MICROCOSM_ROOT,
        generated_at="2026-06-01T00:00:00Z",
        command="pytest-entry-card",
    )

    card = build_entry_card(
        MICROCOSM_ROOT,
        projection=projection,
        command="pytest-entry-card",
    )

    assert card["schema_version"] == "microcosm_doctrine_lattice_entry_card_v1"
    assert card["entry_scope"] == "microcosm_substrate_local_agent_entry_only"
    assert card["source_refs"]["entry_route"] == "atlas/entry_packet.json::doctrine_lattice_route"
    assert card["source_refs"]["coverage_projection"] == "core/doctrine_lattice_coverage.json"
    assert card["source_refs"]["paper_module_instances"] == "paper_modules/*.json"
    assert card["source_refs"]["skill_instances"] == "skills/*.json"
    assert card["source_refs"]["standard_instances"] == "standards/std_microcosm_*.json"
    assert card["status_card"]["deficit_summary"]["organs_missing_mechanism_ref"] == (
        projection["deficit_summary"]["organs_missing_mechanism_ref"]
    )
    assert card["current_counts"]["resolved_mechanism_count"] == (
        projection["organ_required_edge_coverage"]["resolved_mechanism_count"]
    )
    assert card["current_counts"]["planned_mechanism_count"] == (
        projection["organ_required_edge_coverage"]["planned_mechanism_count"]
    )
    assert card["current_counts"]["paper_module_json_instance_count"] == (
        projection["paper_module_instance_corpus"]["json_instance_count"]
    )
    assert card["current_counts"]["paper_module_legacy_only_count"] == (
        projection["deficit_summary"]["paper_module_legacy_only_count"]
    )
    assert card["current_counts"]["paper_module_required_subject_gap_count"] == (
        projection["deficit_summary"]["paper_module_required_subject_gap_count"]
    )
    assert (
        card["current_counts"]["skill_json_instance_count"]
        == EXPECTED_SKILL_INSTANCE_COUNT
    )
    assert card["current_counts"]["skill_required_relation_gap_count"] == 0
    assert (
        card["current_counts"]["skill_unpopulated_selective_relation_count"]
        == EXPECTED_SKILL_SELECTIVE_RELATION_COUNT
    )
    assert (
        card["current_counts"]["standard_json_instance_count"]
        == EXPECTED_STANDARD_INSTANCE_COUNT
    )
    assert card["current_counts"]["standard_legacy_or_draft_contract_count"] > 0
    assert (
        card["current_counts"]["standard_required_relation_gap_count"]
        == EXPECTED_STANDARD_REQUIRED_RELATION_GAP_COUNT
    )
    assert (
        card["current_counts"]["standard_used_by_organ_unresolved_edge_count"]
        == EXPECTED_STANDARD_USED_BY_ORGAN_UNRESOLVED_EDGE_COUNT
    )
    assert card["current_counts"]["standard_unregistered_file_count"] == 0
    assert card["next_population_targets"] == projection["next_population_targets"][:3]
    assert "agent_route_observability_runtime" not in {
        target["organ_id"] for target in card["next_population_targets"]
    }
    assert "AGENTS.override.md" not in json.dumps(card, sort_keys=True)


def test_doctrine_lattice_entry_card_validation_tracks_projection_counts(tmp_path: Path) -> None:
    card = write_entry_card(
        MICROCOSM_ROOT,
        tmp_path / "doctrine_lattice_entry_card.json",
        generated_at="2026-06-01T00:00:00Z",
        command="pytest-entry-card",
    )

    validation = validate_entry_card(card, MICROCOSM_ROOT)
    assert validation["status"] == "pass"
    assert validation["errors"] == []
    assert json.loads((tmp_path / "doctrine_lattice_entry_card.json").read_text(encoding="utf-8")) == card

    bad = copy.deepcopy(card)
    bad["current_counts"]["organs_missing_mechanism_ref"] += 1
    bad_validation = validate_entry_card(bad, MICROCOSM_ROOT)
    assert bad_validation["status"] == "blocked"
    assert "current_counts" in {error["path"] for error in bad_validation["errors"]}


def test_planned_mechanism_refs_do_not_count_as_resolved() -> None:
    result = _registry_atlas_join_health(
        MICROCOSM_ROOT,
        accepted=[{"organ_id": "planned_demo", "status": "accepted_current_authority"}],
        atlas_rows=[
            {
                "organ_id": "planned_demo",
                "mechanism_refs": [
                    {
                        "ref": "planned_mechanism_demo",
                        "resolution_status": "planned_unresolved",
                    }
                ],
                "code_loci": [
                    {
                        "path": "src/microcosm_core/doctrine_lattice.py",
                        "resolution": "planned",
                    }
                ],
            }
        ],
        mechanism_sources={},
        paper_capsules={},
    )

    assert result["status"] == "pass"
    assert result["planned_mechanism_count"] == 1
    assert result["resolved_mechanism_count"] == 0
    assert result["planned_code_locus_count"] == 1
    assert result["resolved_code_locus_count"] == 0
    assert result["errors"] == []


def test_public_codex_leak_guard_allows_current_public_prose_and_rejects_brand_leak() -> None:
    current = check_public_codex_leaks(MICROCOSM_ROOT)
    assert current["status"] == "pass"
    assert current["brand_leak_count"] == 0

    bad = check_public_codex_leaks(
        surfaces={"README.md": "Microcosm is powered by Codex as a public product brand."}
    )
    assert bad["status"] == "blocked"
    assert bad["brand_leak_count"] == 1
