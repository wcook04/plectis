from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from microcosm_core.doctrine_lattice import (
    build_coverage_projection,
    build_doctrine_projection,
    build_entry_card,
    build_lattice_health,
    validate_coverage_projection,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_INSTANCE_NODE_KINDS = {
    "anti_principle",
    "axiom",
    "concept",
    "mechanism",
    "organ",
    "paper_module",
    "principle",
    "skill",
    "standard",
}


def test_projection_nodes_publish_authority_boundary_support_and_gap_metadata() -> None:
    projection = build_doctrine_projection(MICROCOSM_ROOT)

    assert projection["nodes"]
    for node in projection["nodes"]:
        kind = node["kind"]
        assert node["support_status"], node["id"]
        assert node["claim_ceiling"], node["id"]
        assert isinstance(node["gap_count"], int), node["id"]
        assert node["authority_boundary"], node["id"]
        if kind in SOURCE_INSTANCE_NODE_KINDS:
            assert node["authority_boundary"] == (
                f"generated_projection_node_from_{kind}_instance_not_source_authority"
            )

    code_locus = next(
        node for node in projection["nodes"] if node["kind"] == "code_locus"
    )
    assert code_locus["authority_boundary"] == (
        "derived_projection_node_from_source_edges_not_source_file_authority"
    )
    receipt = next(node for node in projection["nodes"] if node["kind"] == "receipt")
    assert receipt["authority_boundary"] == (
        "derived_projection_node_from_receipt_refs_not_receipt_content_proof"
    )
    doctrine_kind = next(
        node for node in projection["nodes"] if node["kind"] == "doctrine_kind"
    )
    assert doctrine_kind["authority_boundary"] == (
        "derived_projection_node_from_standard_skill_kind_edges_not_kind_source_authority"
    )


def test_doctrine_kind_nodes_are_walkable_from_standard_and_skill_edges() -> None:
    projection = build_doctrine_projection(MICROCOSM_ROOT)
    doctrine_kind_edges = [
        edge
        for edge in projection["edges"]
        if edge.get("target_kind") == "doctrine_kind"
    ]
    doctrine_kind_nodes = [
        node for node in projection["nodes"] if node["kind"] == "doctrine_kind"
    ]
    node_keys = {(node["kind"], node["id"]) for node in doctrine_kind_nodes}
    target_keys = {
        (edge["target_kind"], edge["target_id"])
        for edge in doctrine_kind_edges
        if edge.get("target_status") == "resolved_doctrine_kind_contract"
    }

    assert doctrine_kind_edges
    assert len(doctrine_kind_nodes) == len(target_keys)
    assert target_keys <= node_keys

    health = build_lattice_health(MICROCOSM_ROOT)
    doctrine_kinds = health["doctrine_kinds"]
    relation_counts = dict(
        sorted(Counter(edge["relation_id"] for edge in doctrine_kind_edges).items())
    )
    source_kind_counts = dict(
        sorted(Counter(edge["source_kind"] for edge in doctrine_kind_edges).items())
    )
    assert doctrine_kinds["known_count"] == len(doctrine_kind_nodes)
    assert doctrine_kinds["inbound_edge_count"] == len(doctrine_kind_edges)
    assert doctrine_kinds["counts_by_relation_id"] == relation_counts
    assert doctrine_kinds["counts_by_source_kind"] == source_kind_counts
    assert doctrine_kinds["counts_by_support_status"] == {
        "resolved_doctrine_kind_contract_from_source_edges": len(doctrine_kind_nodes),
    }
    assert doctrine_kinds["gap_count"] == 0
    assert doctrine_kinds["gap_details"] == []
    assert "walkability nodes" in doctrine_kinds["support_scope"]
    assert "not complete ontology" in doctrine_kinds["support_scope"]
    assert doctrine_kinds["sample_nodes"]
    for node in doctrine_kinds["sample_nodes"]:
        assert node["authority_boundary"] == (
            "derived_projection_node_from_standard_skill_kind_edges_not_kind_source_authority"
        )
        assert node["support_status"] == (
            "resolved_doctrine_kind_contract_from_source_edges"
        )
        assert node["gap_count"] == 0

    entry_card = build_entry_card(MICROCOSM_ROOT)
    current_counts = entry_card["current_counts"]
    assert current_counts["doctrine_kind_walkable_node_count"] == len(doctrine_kind_nodes)
    assert current_counts["doctrine_kind_inbound_edge_count"] == len(doctrine_kind_edges)
    assert current_counts["doctrine_kind_gap_count"] == 0


def test_code_locus_health_nodes_do_not_launder_path_existence() -> None:
    health = build_lattice_health(MICROCOSM_ROOT)
    code_loci = health["code_loci"]

    assert code_loci["known_count"] > 0
    assert code_loci["planned_or_unresolved_path_count"] == 0
    assert sum(code_loci["counts_by_support_status"].values()) == code_loci["known_count"]
    assert code_loci["counts_by_support_status"] == {
        "resolved_path_named_by_source_edges": code_loci["known_count"],
    }
    assert code_loci["planned_or_unresolved_path_details"] == []
    assert (
        "path existence is not code correctness"
        in code_loci["support_scope"]
    )
    assert code_loci["sample_nodes"]
    for node in code_loci["sample_nodes"]:
        assert node["authority_boundary"] == (
            "derived_projection_node_from_source_edges_not_source_file_authority"
        )
        assert node["claim_ceiling"] == (
            "path_existence_and_source_edge_routing_only_not_code_correctness_or_runtime_proof"
        )
        assert node["support_status"] == "resolved_path_named_by_source_edges"
        assert node["path_exists"] is True
        assert node["gap_count"] == 0


def test_receipt_health_nodes_do_not_launder_receipt_presence() -> None:
    health = build_lattice_health(MICROCOSM_ROOT)
    receipts = health["receipts"]

    assert receipts["known_count"] > 0
    assert receipts["missing_ref_count"] == 0
    assert receipts["nonlocal_ref_count"] > 0
    assert receipts["resolved_nonlocal_ref_count"] == receipts["nonlocal_ref_count"]
    assert receipts["unresolved_nonlocal_ref_count"] == 0
    assert sum(receipts["counts_by_support_status"].values()) == receipts["known_count"]
    assert receipts["counts_by_support_status"].get("missing_receipt_ref", 0) == 0
    assert receipts["counts_by_support_status"][
        "nonlocal_receipt_path_resolved_not_public_evidence"
    ] == receipts["resolved_nonlocal_ref_count"]
    assert receipts["counts_by_support_status"].get(
        "nonlocal_receipt_ref_declared_not_public_file_resolved",
        0,
    ) == receipts["unresolved_nonlocal_ref_count"]
    assert receipts["missing_ref_details"] == []
    assert len(receipts["nonlocal_ref_details"]) == receipts["nonlocal_ref_count"]
    assert receipts["unresolved_nonlocal_ref_details"] == []
    assert receipts["gap_details"] == []
    assert "receipt existence is not proof" in receipts["support_scope"]
    assert "nonlocal path walkability" in receipts["support_scope"]
    assert receipts["sample_nodes"]
    for node in receipts["sample_nodes"]:
        assert node["authority_boundary"] == (
            "derived_projection_node_from_receipt_refs_not_receipt_content_proof"
        )
        assert node["claim_ceiling"] == (
            "receipt_ref_presence_or_file_existence_not_proof_runtime_correctness_or_release_authority"
        )
        assert node["gap_count"] == 0
        assert node["support_status"] in {
            "receipt_path_resolved",
            "symbolic_receipt_id_declared_not_file_resolved",
            "declared_receipt_ref_not_file_resolved",
            "nonlocal_receipt_path_resolved_not_public_evidence",
        }
    for node in receipts["nonlocal_ref_details"]:
        assert node["support_status"] == (
            "nonlocal_receipt_path_resolved_not_public_evidence"
        )
        assert node["path_exists"] is True
        assert node["gap_count"] == 0
        assert node["claim_ceiling"] == (
            "nonlocal_receipt_handle_is_declared_authority_boundary_not_public_file_evidence"
        )

    projection = build_doctrine_projection(MICROCOSM_ROOT)
    nonlocal_receipt_nodes = [
        node
        for node in projection["nodes"]
        if node["kind"] == "receipt"
        and str(node["id"]).startswith("state/")
        and str(node["id"]).endswith(".json")
    ]
    assert nonlocal_receipt_nodes
    for node in nonlocal_receipt_nodes:
        assert node["support_status"] == (
            "nonlocal_receipt_path_resolved_not_public_evidence"
        )
        assert node["path_exists"] is True
        assert node["gap_count"] == 0
        assert node["claim_ceiling"] == (
            "nonlocal_receipt_handle_is_declared_authority_boundary_not_public_file_evidence"
        )


def test_skill_health_counts_selective_residual_relations_without_filling_edges() -> None:
    health = build_lattice_health(MICROCOSM_ROOT)
    skills = health["skills"]
    details = skills["unpopulated_selective_relation_details"]
    detail_count = len(details)

    assert detail_count > 0
    assert skills["unpopulated_selective_edge_count"] == detail_count
    assert skills["unpopulated_selective_relation_count"] == detail_count
    assert skills["unpopulated_selective_relation_detail_count"] == detail_count
    assert skills["unpopulated_selective_relation_counts_by_relation_id"] == {
        "skill.uses.mechanism": detail_count,
    }
    assert skills["unpopulated_selective_relation_counts_by_pressure_ref"] == {
        "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f": detail_count,
    }
    assert skills["unpopulated_selective_relation_counts_by_authority_boundary"] == {
        "computed_from_skill_markdown_mapping_residuals_not_source_edge_inference": detail_count,
    }
    assert "counted separately from affected skill nodes" in skills["support_scope"]
    assert "acts_on_kind candidate matches are navigation pressure" in skills[
        "support_scope"
    ]

    triad_counts = dict(sorted(Counter(row["triad_role"] for row in details).items()))
    assert skills["unpopulated_selective_relation_counts_by_triad_role"] == triad_counts
    assert set(triad_counts) == {
        "author",
        "refine_instance",
        "refine_standard_and_propagate",
    }
    assert len(set(triad_counts.values())) == 1
    skill_counts = dict(sorted(Counter(row["skill_id"] for row in details).items()))
    assert skills["unpopulated_selective_relation_counts_by_instance_id"] == skill_counts
    assert len(skill_counts) == skills["unpopulated_selective_edge_count"]
    assert sum(
        skills["unpopulated_selective_relation_counts_by_operates_standard"].values()
    ) == len(details)
    assert sum(
        skills["unpopulated_selective_relation_counts_by_acts_on_kind"].values()
    ) == len(details)
    concept_gap_ids = {
        row["skill_id"]
        for row in details
        if row["relation_id"] == "skill.applies.concept"
    }
    assert concept_gap_ids == set()
    external_candidate_detail_ids = {
        row["skill_id"]
        for row in details
        if row["acts_on_kind"] == "external_candidate"
    }
    assert external_candidate_detail_ids == {
        "skill.microcosm.external_candidate.author",
        "skill.microcosm.external_candidate.refine_instance",
        "skill.microcosm.external_candidate.refine_standard_and_propagate",
    }
    for skill_id in sorted(external_candidate_detail_ids):
        rel_path = Path(skill_id.replace("skill.", "skills/") + ".json")
        skill_json = json.loads((MICROCOSM_ROOT / rel_path).read_text(encoding="utf-8"))
        assert skill_json["concept_refs"] == [
            "concept.import_projection_and_drift_control_bundle"
        ]
        assert skill_json["mechanism_refs"] == []
        assert [
            row["relation_id"]
            for row in skill_json["relationships"]["unpopulated_selective_relations"]
        ] == ["skill.uses.mechanism"]
        assert any(
            edge["relation_id"] == "skill.applies.concept"
            and edge["target_id"] == "concept.import_projection_and_drift_control_bundle"
            and edge["target_status"] == "resolved_json_instance"
            for edge in skill_json["relationships"]["edges"]
        )
    for row in details:
        assert row["authority_boundary"] == (
            "computed_from_skill_markdown_mapping_residuals_not_source_edge_inference"
        )
        assert row["pressure_ref"] == (
            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
        )
        assert row["source_ref"].startswith("skills/")
    candidate_details = skills["residual_candidate_details"]
    assert skills["residual_candidate_detail_count"] == len(details)
    assert len(candidate_details) == len(details)
    assert skills["residual_candidate_counts_by_status"] == dict(
        sorted(Counter(row["candidate_status"] for row in candidate_details).items())
    )
    assert set(skills["residual_candidate_counts_by_status"]) <= {
        "acts_on_kind_matches_single_mechanism_candidate_not_source_edge",
        "no_acts_on_kind_mechanism_candidate_named",
    }
    assert sum(skills["residual_candidate_counts_by_status"].values()) == len(
        candidate_details
    )
    assert skills["residual_candidate_counts_by_target_kind"] == dict(
        sorted(
            Counter(row["candidate_target_kind"] for row in candidate_details).items()
        )
    )
    assert skills["residual_candidate_counts_by_target_kind"] == {
        "mechanism": len(candidate_details),
    }
    assert skills["residual_candidate_counts_by_candidate_count"] == dict(
        sorted(Counter(row["candidate_count_bucket"] for row in candidate_details).items())
    )
    for row in candidate_details:
        assert row["claim_ceiling"] == (
            "acts_on_kind_candidate_match_is_navigation_pressure_not_skill_edge_support_or_runtime_uptake"
        )
        assert row["candidate_count_bucket"] == str(row["candidate_count"])
        assert row["candidate_count"] == len(row["candidate_ids"])
        if row["relation_id"] == "skill.uses.mechanism":
            assert row["candidate_target_kind"] == "mechanism"
            for candidate_id in row["candidate_ids"]:
                assert candidate_id.startswith(f"mechanism.{row['acts_on_kind']}.")
        elif row["relation_id"] == "skill.applies.concept":
            assert row["candidate_target_kind"] == "concept"
            for candidate_id in row["candidate_ids"]:
                assert candidate_id == f"concept.{row['acts_on_kind']}"
        else:
            assert row["candidate_status"] == "unsupported_skill_residual_relation"


def test_health_types_non_skill_selective_residual_details_without_filling_edges() -> None:
    health = build_lattice_health(MICROCOSM_ROOT)

    organs = health["organs"]
    organ_details = organs["unpopulated_selective_relation_details"]
    organ_instance_counts = dict(
        sorted(Counter(row["organ_id"] for row in organ_details).items())
    )
    assert organs["unpopulated_selective_edge_count"] == 26
    assert organs["unpopulated_selective_relation_count"] == 26
    assert organs["residual_relation_count"] == 26
    assert organs["residual_relation_counts_by_requirement"] == {"selective": 26}
    assert organs["unpopulated_selective_relation_counts_by_relation_id"] == {
        "organ.wires_to.organ": 26,
    }
    assert organs["unpopulated_selective_relation_counts_by_instance_id"] == (
        organ_instance_counts
    )
    assert organs["unpopulated_selective_relation_counts_by_pressure_ref"] == {
        "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f": 26,
    }
    assert organs["unpopulated_selective_relation_counts_by_authority_boundary"] == {
        "computed_from_organ_atlas_registry_residuals_not_source_edge_inference": 26,
    }
    assert "typed from atlas/registry parity plus the relation registry" in organs[
        "support_scope"
    ]
    assert "mechanism upstream host-organ graph only" in organs["support_scope"]
    assert organs["wires_to_residual_fillability_detail_count"] == 26
    assert len(organs["wires_to_residual_fillability_details"]) == 26
    assert organs["wires_to_residual_counts_by_fillability_status"] == {
        "no_mechanism_upstream_wiring_target_named": 26,
    }
    assert organs["wires_to_mechanism_upstream_missing_source_declaration_count"] == 0
    assert (
        organs["wires_to_mechanism_upstream_missing_source_declaration_details"] == []
    )
    for row in organ_details:
        assert row["requirement"] == "selective"
        assert row["authority_boundary"] == (
            "computed_from_organ_atlas_registry_residuals_not_source_edge_inference"
        )
        assert row["pressure_ref"] == (
            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
        )
        assert row["source_refs"]["source_atlas_row_ref"].startswith(
            "core/organ_atlas.json::organs["
        )
    for row in organs["wires_to_residual_fillability_details"]:
        assert row["relation_id"] == "organ.wires_to.organ"
        assert row["fillability_status"] == "no_mechanism_upstream_wiring_target_named"
        assert row["mechanism_upstream_expected_wires_to"] == []
        assert row["mechanism_upstream_missing_wires_to"] == []
        assert row["claim_ceiling"] == (
            "mechanism_upstream_graph_classifies_fillability_only_not_runtime_invocation_or_release_authority"
        )

    mechanisms = health["mechanisms"]
    mechanism_details = mechanisms["unpopulated_selective_relation_details"]
    mechanism_relation_counts = dict(
        sorted(Counter(row["relation_id"] for row in mechanism_details).items())
    )
    mechanism_instance_counts = dict(
        sorted(Counter(row["mechanism_id"] for row in mechanism_details).items())
    )
    mechanism_upstream_count = mechanism_relation_counts[
        "mechanism.upstream_of.mechanism"
    ]
    assert mechanisms["unpopulated_selective_edge_count"] == len(mechanism_instance_counts)
    assert mechanisms["unpopulated_selective_relation_count"] == len(mechanism_details)
    assert mechanisms["residual_relation_count"] == len(mechanism_details)
    assert mechanisms["residual_relation_counts_by_requirement"] == {
        "selective": len(mechanism_details)
    }
    assert mechanisms[
        "unpopulated_selective_relation_counts_by_relation_id"
    ] == mechanism_relation_counts
    assert mechanisms["unpopulated_selective_relation_counts_by_instance_id"] == (
        mechanism_instance_counts
    )
    assert mechanisms["unpopulated_selective_relation_counts_by_pressure_ref"] == {
        "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f": len(
            mechanism_details
        ),
    }
    assert mechanisms[
        "unpopulated_selective_relation_counts_by_authority_boundary"
    ] == {
        "computed_from_mechanism_source_residuals_not_source_edge_inference": len(
            mechanism_details
        ),
    }
    assert mechanism_upstream_count > 0
    assert (
        "mechanism.engine_room_public_projection_leak_gate.validates_public_projection_leak_gate"
        not in mechanism_instance_counts
    )
    assert "typed from source rows plus the relation registry" in mechanisms[
        "support_scope"
    ]
    assert "classifies upstream residual fillability" in mechanisms["support_scope"]
    assert (
        mechanisms["upstream_residual_fillability_detail_count"]
        == mechanism_upstream_count
    )
    assert (
        len(mechanisms["upstream_residual_fillability_details"])
        == mechanism_upstream_count
    )
    assert mechanisms["upstream_residual_counts_by_fillability_status"] == {
        "no_capsule_dependency_upstream_target_named": mechanism_upstream_count,
    }
    assert mechanisms["upstream_capsule_dependency_missing_source_declaration_count"] == 0
    assert mechanisms["upstream_capsule_dependency_missing_source_declaration_details"] == []
    assert mechanisms["upstream_capsule_dependency_unresolved_subject_count"] == 0
    assert mechanisms["upstream_capsule_dependency_unresolved_subject_details"] == []
    for row in mechanism_details:
        assert row["requirement"] == "selective"
        assert row["authority_boundary"] == (
            "computed_from_mechanism_source_residuals_not_source_edge_inference"
        )
        assert row["pressure_ref"] == (
            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
        )
        assert row["source_ref"].startswith("core/mechanism_sources.json::mechanisms[")
    for row in mechanisms["upstream_residual_fillability_details"]:
        assert row["relation_id"] == "mechanism.upstream_of.mechanism"
        assert row["fillability_status"] == "no_capsule_dependency_upstream_target_named"
        assert row["capsule_dependency_expected_upstream_of"] == []
        assert row["capsule_dependency_missing_upstream_of"] == []
        assert row["capsule_dependency_unresolved_subjects"] == []
        assert row["claim_ceiling"] == (
            "capsule_dependency_graph_classifies_mechanism_upstream_fillability_only_not_runtime_invocation_or_release_authority"
        )

    paper_modules = health["paper_modules"]
    paper_module_details = paper_modules["unpopulated_selective_relation_details"]
    paper_module_relation_counts = dict(
        sorted(Counter(row["relation_id"] for row in paper_module_details).items())
    )
    paper_module_instance_counts = dict(
        sorted(Counter(row["paper_module_id"] for row in paper_module_details).items())
    )
    paper_module_requirement_counts = paper_modules[
        "residual_relation_counts_by_requirement"
    ]
    paper_module_required_count = paper_module_requirement_counts.get("required", 0)
    assert paper_modules["unpopulated_selective_edge_count"] == len(
        {row["paper_module_id"] for row in paper_module_details}
    )
    assert paper_modules["unpopulated_selective_relation_count"] == len(
        paper_module_details
    )
    assert paper_modules["residual_relation_count"] == (
        paper_module_required_count + len(paper_module_details)
    )
    expected_paper_module_requirement_counts = {}
    if paper_module_details:
        expected_paper_module_requirement_counts["selective"] = len(
            paper_module_details
        )
    if paper_module_required_count:
        expected_paper_module_requirement_counts["required"] = (
            paper_module_required_count
        )
    assert paper_module_requirement_counts == expected_paper_module_requirement_counts
    assert paper_modules[
        "unpopulated_selective_relation_counts_by_relation_id"
    ] == paper_module_relation_counts
    assert paper_modules["unpopulated_selective_relation_counts_by_instance_id"] == (
        paper_module_instance_counts
    )
    expected_paper_module_pressure_counts = {}
    expected_paper_module_authority_counts = {}
    expected_paper_module_relations = set()
    if paper_module_details:
        expected_paper_module_pressure_counts[
            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
        ] = len(paper_module_details)
        expected_paper_module_authority_counts[
            "computed_from_paper_module_capsule_or_legacy_residuals_not_source_edge_inference"
        ] = len(paper_module_details)
        expected_paper_module_relations.add("paper_module.depends_on.paper_module")
    assert (
        paper_modules["unpopulated_selective_relation_counts_by_pressure_ref"]
        == expected_paper_module_pressure_counts
    )
    assert (
        paper_modules["unpopulated_selective_relation_counts_by_authority_boundary"]
        == expected_paper_module_authority_counts
    )
    assert set(paper_module_relation_counts) == expected_paper_module_relations
    assert (
        "required subject residuals and selective relation residuals remain typed separately"
        in paper_modules["support_scope"]
    )
    for row in paper_module_details:
        assert row["requirement"] == "selective"
        assert row["relation_id"] != "paper_module.explains.organ_or_mechanism"
        assert row["authority_boundary"] == (
            "computed_from_paper_module_capsule_or_legacy_residuals_not_source_edge_inference"
        )
        assert row["pressure_ref"] == (
            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
        )
        assert row["source_ref"]


def test_standard_health_details_remaining_legacy_contracts_after_source_activation() -> None:
    health = build_lattice_health(MICROCOSM_ROOT)
    standards = health["standards"]

    assert standards["legacy_or_draft_contract_count"] == 11
    assert standards["legacy_or_draft_contract_detail_count"] == 11
    assert standards["legacy_or_draft_contract_counts_by_projection_status"] == {
        "legacy_or_draft_standard_contract": 11,
    }
    assert standards["legacy_or_draft_contract_counts_by_source_status"] == {
        "draft": 1,
        "staged_capsule_pending_shared_registry_integration": 10,
    }
    assert standards["legacy_or_draft_contract_counts_by_registry_status"] == {
        "draft": 1,
        "staged_capsule_pending_shared_registry_integration": 10,
    }
    assert "public_microcosm_standard_v1" not in (
        standards["legacy_or_draft_contract_counts_by_source_schema_version"]
    )
    assert standards["activation_witness_gap_detail_count"] == 11
    assert standards["activation_witness_gap_counts_by_gap_id"] == {
        "source_schema_not_public_microcosm_standard_v2": 11,
        "source_status_not_active": 11,
    }
    assert standards["activation_witness_gap_counts_by_source_status"] == {
        "draft": 1,
        "staged_capsule_pending_shared_registry_integration": 10,
    }
    assert standards["activation_witness_gap_counts_by_registry_status"] == {
        "draft": 1,
        "staged_capsule_pending_shared_registry_integration": 10,
    }
    assert standards["activation_witness_gap_counts_by_validator_contract_required"] == {
        "True": 11,
    }

    details = standards["legacy_or_draft_contract_details"]
    assert len(details) == standards["legacy_or_draft_contract_count"]
    assert {row["standard_id"] for row in details} == set(
        standards["legacy_or_draft_contract_ids"]
    )
    assert all(
        row["contract_projection_status"] == "legacy_or_draft_standard_contract"
        for row in details
    )
    assert all(
        row["authority_boundary"]
        == "computed_from_standard_source_status_not_contract_activation_or_runtime_use"
        for row in details
    )
    assert all(
        row["claim_ceiling"]
        == "legacy_or_draft_detail_is_reentry_metadata_not_active_v2_contract_support"
        for row in details
    )

    by_id = {row["standard_id"]: row for row in details}
    assert by_id["std_microcosm_batch7_zenith_macos_capsule"][
        "unresolved_used_by_organ_ids"
    ] == ["batch7_zenith_macos_capsule"]
    assert "std_microcosm_agent_trace" not in by_id
    assert "std_microcosm_atlas_route" not in by_id
    assert "std_microcosm_anti_claim" not in by_id
    assert "std_microcosm_private_fixture" not in by_id
    assert "std_microcosm_batch5_authority_systems_capsule" not in by_id
    assert "std_microcosm_batch7_demo_take_console_capsule" not in by_id
    assert "std_microcosm_batch7_oracle_sibling_capsule" not in by_id
    assert "std_microcosm_batch7_secondary_runtime_capsule" not in by_id

    activation_by_id = {
        row["standard_id"]: row
        for row in standards["activation_witness_gap_details"]
    }
    assert set(activation_by_id) == set(standards["legacy_or_draft_contract_ids"])
    assert activation_by_id["std_microcosm_engine_room_annex_knowledge_router"][
        "activation_gap_ids"
    ] == [
        "source_schema_not_public_microcosm_standard_v2",
        "source_status_not_active",
    ]
    assert activation_by_id["std_microcosm_engine_room_annex_knowledge_router"][
        "validator_refs"
    ] == ["validator.microcosm.organs.engine_room_annex_knowledge_router"]
    assert activation_by_id["std_microcosm_batch7_zenith_macos_capsule"][
        "activation_gap_ids"
    ] == [
        "source_schema_not_public_microcosm_standard_v2",
        "source_status_not_active",
    ]
    for row in activation_by_id.values():
        assert row["authority_boundary"] == (
            "computed_from_standard_source_contract_not_activation_or_runtime_use"
        )
        assert row["claim_ceiling"] == (
            "activation_witness_gap_detail_is_reentry_metadata_not_active_contract_support"
        )


def test_standard_health_groups_unresolved_used_by_organs_without_accepting_them() -> None:
    coverage = build_coverage_projection(MICROCOSM_ROOT)
    health = build_lattice_health(MICROCOSM_ROOT)
    standards = health["standards"]
    entry_card = build_entry_card(MICROCOSM_ROOT)
    organ_registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    accepted_organ_ids = {
        row["organ_id"]
        for row in organ_registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    }

    details = standards["used_by_organ_unresolved_details"]
    target_counts = dict(
        sorted(Counter(row["target_organ_id"] for row in details).items())
    )
    admission_details = standards["used_by_organ_admission_details"]
    projection_status_counts = dict(
        sorted(
            Counter(
                row["contract_projection_status"] for row in admission_details
            ).items()
        )
    )
    active_v2_admission_details = [
        row
        for row in admission_details
        if row["contract_projection_status"] == "active_v2_governed_json"
    ]
    unresolved_count = len(details)
    missing_accepted_count = len(
        [
            row
            for row in admission_details
            if row["admission_status"] == "target_organ_not_accepted_current_authority"
        ]
    )

    assert unresolved_count > 0
    assert standards["used_by_organ_unresolved_edge_count"] == unresolved_count
    assert standards["used_by_organ_unresolved_detail_count"] == unresolved_count
    assert (
        standards["used_by_organ_admission_detail_count"]
        == len(admission_details)
        == unresolved_count
    )
    assert standards["used_by_organ_missing_accepted_target_count"] == (
        missing_accepted_count
    )
    assert (
        entry_card["current_counts"][
            "standard_used_by_organ_missing_accepted_target_count"
        ]
        == missing_accepted_count
    )
    assert (
        coverage["deficit_summary"][
            "standard_used_by_organ_missing_accepted_target_count"
        ]
        == standards["used_by_organ_missing_accepted_target_count"]
    )
    assert standards["used_by_organ_unresolved_standard_count"] == len(
        {row["standard_id"] for row in details}
    )
    assert standards["used_by_organ_unresolved_target_organ_count"] == len(
        {row["target_organ_id"] for row in details}
    )
    assert standards["used_by_organ_unresolved_counts_by_target_organ_id"] == (
        target_counts
    )
    assert standards["used_by_organ_unresolved_counts_by_target_status"] == dict(
        sorted(Counter(row["target_status"] for row in details).items())
    )
    assert standards["used_by_organ_unresolved_counts_by_source_status"] == dict(
        sorted(Counter(row["source_standard_status"] for row in details).items())
    )
    assert standards["used_by_organ_unresolved_counts_by_registry_status"] == dict(
        sorted(Counter(row["registry_status"] for row in details).items())
    )
    assert standards["used_by_organ_unresolved_counts_by_projection_status"] == dict(
        sorted(Counter(row["contract_projection_status"] for row in details).items())
    )
    assert standards["used_by_organ_unresolved_counts_by_projection_status"] == (
        projection_status_counts
    )
    assert standards["used_by_organ_admission_counts_by_admission_status"] == dict(
        sorted(Counter(row["admission_status"] for row in admission_details).items())
    )
    assert standards["used_by_organ_admission_counts_by_target_status"] == dict(
        sorted(Counter(row["target_status"] for row in admission_details).items())
    )
    assert standards[
        "used_by_organ_admission_counts_by_contract_projection_status"
    ] == projection_status_counts
    assert standards[
        "used_by_organ_admission_counts_by_contract_projection_status"
    ] == projection_status_counts
    assert len(active_v2_admission_details) == projection_status_counts.get(
        "active_v2_governed_json",
        0,
    )
    assert standards["used_by_organ_unresolved_counts_by_source_schema_version"] == (
        dict(
            sorted(
                Counter(
                    row["source_standard_schema_version"] for row in details
                ).items()
            )
        )
    )
    assert target_counts["external_boundary_anti_corruption_runtime"] >= 1
    assert set(standards["used_by_organ_unresolved_standard_ids"]) == {
        row["standard_id"] for row in details
    }
    assert set(standards["used_by_organ_unresolved_target_organ_ids"]) == {
        row["target_organ_id"] for row in details
    }
    assert standards["used_by_organ_typed_residual_count"] == unresolved_count
    assert standards["used_by_organ_typed_residual_counts_by_gap_class"] == {
        "standard_used_by_organ_target_not_accepted_current_authority": (
            unresolved_count
        ),
    }
    assert standards["used_by_organ_typed_residual_counts_by_requirement"] == {
        "selective": unresolved_count,
    }
    assert standards["used_by_organ_typed_residual_counts_by_disposition"] == {
        "keep_as_reentry_pressure_not_usage_or_acceptance_proof": (
            unresolved_count
        ),
    }
    for row in details:
        assert row["target_status"] == "unresolved_json_instance"
        assert row["residual_pressure_ref"] == (
            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
        )
        assert row["residual_status"] == "typed_residual_pressure"
        assert row["residual_gap_class"] == (
            "standard_used_by_organ_target_not_accepted_current_authority"
        )
        assert row["residual_relation_id"] == "standard.used_by.organ"
        assert row["residual_requirement"] == "selective"
        assert row["residual_disposition"] == (
            "keep_as_reentry_pressure_not_usage_or_acceptance_proof"
        )
        assert row["claim_ceiling"] == (
            "standard_used_by_organ_residual_is_reentry_metadata_not_usage_or_acceptance_proof"
        )
        assert "--check-standard-corpus" in row["reentry_condition"]
        assert row["authority_boundary"] == (
            "computed_from_standard_relationships_used_by_organs_not_organ_acceptance_or_runtime_use"
        )
        assert row["edge_source_ref"]

    for row in admission_details:
        assert row["admission_status"] == "target_organ_not_accepted_current_authority"
        assert row["target_status"] == "unresolved_json_instance"
        assert row["target_organ_id"] not in accepted_organ_ids
        assert row["residual_status"] == "typed_residual_pressure"
        assert row["residual_gap_class"] == (
            "standard_used_by_organ_target_not_accepted_current_authority"
        )
        assert row["residual_relation_id"] == "standard.used_by.organ"
        assert row["residual_requirement"] == "selective"
        assert row["residual_disposition"] == (
            "keep_as_reentry_pressure_not_usage_or_acceptance_proof"
        )
        assert "--check-standard-corpus" in row["reentry_condition"]
        assert row["authority_boundary"] == (
            "computed_from_standard_used_by_organ_residuals_not_organ_admission_or_edge_support"
        )
        assert row["claim_ceiling"] == (
            "standard_used_by_organ_target_admission_status_is_reentry_metadata_not_usage_or_acceptance_proof"
        )
        assert row["edge_source_ref"]

    for row in active_v2_admission_details:
        assert row["source_standard_status"] == "active"
        assert row["source_standard_schema_version"] == "public_microcosm_standard_v2"
        assert row["registry_status"] == "draft"
        assert row["target_organ_id"] not in accepted_organ_ids


def test_mechanism_capsule_dependency_upstream_parity_uses_registry_direction() -> None:
    projection = build_coverage_projection(MICROCOSM_ROOT)
    health = build_lattice_health(MICROCOSM_ROOT, projection=projection)
    entry_card = build_entry_card(MICROCOSM_ROOT, projection=projection)

    parity = projection["mechanism_capsule_dependency_upstream_parity"]
    assert parity["status"] == "pass"
    assert parity["covered_edge_count"] > 0
    assert parity["missing_edge_count"] == 0
    assert {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["sample_covered_edges"]
    } >= {
        (
            "mechanism.agent_route_observability_runtime.validates_public_route_feedback",
            "mechanism.agent_memory_temporal_conflict_replay.validates_public_memory_conflict_replay",
        ),
        (
            "mechanism.agent_memory_temporal_conflict_replay.validates_public_memory_conflict_replay",
            "mechanism.sleeper_memory_poisoning_quarantine_replay.validates_public_sleeper_memory_poisoning_quarantine_replay",
        )
    }
    assert (
        "mechanism.agent_route_observability_runtime.validates_public_route_feedback",
        "mechanism.agent_memory_temporal_conflict_replay.validates_public_memory_conflict_replay",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.agent_memory_temporal_conflict_replay.validates_public_memory_conflict_replay",
        "mechanism.sleeper_memory_poisoning_quarantine_replay.validates_public_sleeper_memory_poisoning_quarantine_replay",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.bridge_phase_continuity_runtime.validates_synthetic_bridge_continuity",
        "mechanism.agent_memory_temporal_conflict_replay.validates_public_memory_conflict_replay",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.agent_sandbox_policy_escape_replay.validates_public_sandbox_policy_trace",
        "mechanism.sleeper_memory_poisoning_quarantine_replay.validates_public_sleeper_memory_poisoning_quarantine_replay",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.agent_route_observability_runtime.validates_public_route_feedback",
        "mechanism.agent_sandbox_policy_escape_replay.validates_public_sandbox_policy_trace",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.mcp_tool_authority_replay.validates_public_mcp_tool_authority_replay",
        "mechanism.agent_sandbox_policy_escape_replay.validates_public_sandbox_policy_trace",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.mcp_tool_authority_replay.validates_public_mcp_tool_authority_replay",
        "mechanism.sleeper_memory_poisoning_quarantine_replay.validates_public_sleeper_memory_poisoning_quarantine_replay",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.macro_projection_import_protocol.validates_public_macro_projection_imports",
        "mechanism.batch7_secondary_runtime_capsule.validates_public_secondary_runtime_capsule",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.macro_projection_import_protocol.validates_public_macro_projection_imports",
        "mechanism.batch5_authority_systems_capsule.validates_public_authority_systems_capsule",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.macro_projection_import_protocol.validates_public_macro_projection_imports",
        "mechanism.batch7_oracle_sibling_capsule.validates_public_oracle_sibling_capsule",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.macro_projection_import_protocol.validates_public_macro_projection_imports",
        "mechanism.executable_doctrine_grammar.validates_public_doctrine_grammar_bundle",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.macro_projection_import_protocol.validates_public_macro_projection_imports",
        "mechanism.batch7_zenith_macos_capsule.validates_public_zenith_macos_capsule",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.macro_projection_import_protocol.validates_public_macro_projection_imports",
        "mechanism.batch7_demo_take_console_capsule.validates_public_demo_take_console_capsule",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.macro_projection_import_protocol.validates_public_macro_projection_imports",
        "mechanism.engine_room_generated_projection_drift_gate.validates_public_generated_projection_drift_gate",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert (
        "mechanism.cold_reader_route_map.validates_public_first_run_route_map",
        "mechanism.first_screen_composition_root.validates_public_first_screen_composition_root",
    ) not in {
        (
            row["source_mechanism"],
            row["target_mechanism"],
        )
        for row in parity["missing_edges"]
    }
    assert parity["relation_direction"].startswith(
        "paper_module A depends_on paper_module B maps to mechanism(B).upstream_of mechanism(A)"
    )
    assert parity == health["mechanisms"]["capsule_dependency_upstream_parity"]
    assert (
        entry_card["current_counts"]["mechanism_capsule_dependency_upstream_missing_count"]
        == 0
    )
    assert any(
        guard["guard_id"] == "paper_dependency_not_reverse_mechanism_upstream_edge"
        for guard in entry_card["fake_green_guards"]
    )


def test_coverage_validator_blocks_stale_mechanism_parity_details() -> None:
    projection = build_coverage_projection(MICROCOSM_ROOT)
    stale_projection = json.loads(json.dumps(projection))
    stale_projection["mechanism_capsule_dependency_upstream_parity"][
        "relation_direction"
    ] = "stale parity detail that keeps summary counts unchanged"

    result = validate_coverage_projection(stale_projection, MICROCOSM_ROOT)

    assert result["status"] == "blocked"
    assert {
        "code": "coverage_projection_reproducibility_mismatch",
        "path": "mechanism_capsule_dependency_upstream_parity",
        "message": (
            "Coverage field mechanism_capsule_dependency_upstream_parity "
            "is not reproducible from source."
        ),
    } in result["errors"]


def test_organs_publish_wiring_named_by_mechanism_upstream_graph() -> None:
    organ_atlas = json.loads((MICROCOSM_ROOT / "core/organ_atlas.json").read_text())
    mechanisms = json.loads((MICROCOSM_ROOT / "core/mechanism_sources.json").read_text())[
        "mechanisms"
    ]
    atlas_organ_ids = {
        row.get("organ_id") or row.get("id")
        for row in organ_atlas["organs"]
        if row.get("organ_id") or row.get("id")
    }

    mechanism_to_organ = {
        row["id"]: row["runs_in"][0]
        for row in mechanisms
        if row.get("id") and row.get("runs_in")
    }
    expected_by_organ: dict[str, set[str]] = {}
    unadmitted_target_hosts: list[dict[str, str]] = []
    for mechanism in mechanisms:
        source_organ = mechanism_to_organ.get(mechanism["id"])
        if not source_organ:
            continue
        for target_mechanism in mechanism.get("upstream_of") or []:
            target_organ = mechanism_to_organ.get(target_mechanism)
            if target_organ and target_organ not in atlas_organ_ids:
                unadmitted_target_hosts.append(
                    {
                        "source_organ": source_organ,
                        "target_mechanism": target_mechanism,
                        "target_organ": target_organ,
                    }
                )
                continue
            if target_organ and target_organ != source_organ:
                expected_by_organ.setdefault(source_organ, set()).add(target_organ)

    missing = []
    for row in organ_atlas["organs"]:
        organ_id = row.get("organ_id") or row.get("id")
        expected_targets = expected_by_organ.get(organ_id, set())
        declared_targets = set(row.get("wires_to") or [])
        missing_targets = sorted(expected_targets - declared_targets)
        if missing_targets:
            missing.append(
                {
                    "organ_id": organ_id,
                    "missing_wires_to": missing_targets,
                }
            )

    assert sum(len(targets) for targets in expected_by_organ.values()) >= 150
    assert missing == [
        {
            "organ_id": "mission_transaction_work_spine",
            "missing_wires_to": ["proof_derived_governed_mutation_authorization"],
        },
        {
            "organ_id": "durable_agent_work_landing_replay",
            "missing_wires_to": ["mission_transaction_work_spine"],
        },
        {
            "organ_id": "bridge_phase_continuity_runtime",
            "missing_wires_to": ["durable_agent_work_landing_replay"],
        },
        {
            "organ_id": "macro_projection_import_protocol",
            "missing_wires_to": [
                "agent_monitor_redteam_falsification_replay",
                "bridge_phase_continuity_runtime",
                "cognitive_operator_registry",
                "finance_forecast_evaluation_spine",
                "indirect_prompt_injection_information_flow_policy_replay",
                "mcp_tool_authority_replay",
                "standards_meta_diagnostics",
                "world_model_projection_drift_control_room",
            ],
        },
    ]
    assert any(
        row["target_organ"] == "cold_clone_probe"
        for row in unadmitted_target_hosts
    )
