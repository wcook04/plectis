from __future__ import annotations

import json
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent


def _std_microcosm() -> dict:
    return json.loads(
        (REPO_ROOT / "codex/standards/std_microcosm.json").read_text(
            encoding="utf-8"
        )
    )


def _std_standard_type_plane() -> dict:
    return json.loads(
        (REPO_ROOT / "codex/standards/std_standard_type_plane.json").read_text(
            encoding="utf-8"
        )
    )


def _entry_packet() -> dict:
    return json.loads(
        (REPO_ROOT / "microcosm-substrate/atlas/entry_packet.json").read_text(
            encoding="utf-8"
        )
    )


def test_microcosm_paper_module_coverage_contract_is_standard_backed() -> None:
    standard = _std_microcosm()
    contract = standard["paper_module_coverage_contract"]

    assert contract["primary_modules"] == [
        "codex/doctrine/paper_modules/microcosm_substrate.md",
        "codex/doctrine/paper_modules/microcosm_entry_lattice.md",
        "codex/doctrine/paper_modules/microcosm_public_export_type_plane.md",
        "codex/doctrine/paper_modules/paper_module_coverage_metabolism.md",
        "codex/doctrine/paper_modules/idea_microcosm_metabolism.md",
        "codex/doctrine/paper_modules/public_constellation_strategy.md",
        "codex/doctrine/paper_modules/dissemination_strategy.md",
    ]
    assert contract["supporting_lattice_modules"] == [
        "codex/doctrine/paper_modules/prime_directives.md",
        "codex/doctrine/paper_modules/local_to_general_propagation.md",
        "codex/doctrine/paper_modules/navigation_hologram_theory.md",
    ]
    assert contract["module_depth_roles"] == {
        "product_roof": "codex/doctrine/paper_modules/microcosm_substrate.md",
        "entry_lattice": "codex/doctrine/paper_modules/microcosm_entry_lattice.md",
        "public_export_bridge": (
            "codex/doctrine/paper_modules/microcosm_public_export_type_plane.md"
        ),
        "coverage_metabolism": (
            "codex/doctrine/paper_modules/paper_module_coverage_metabolism.md"
        ),
        "laboratory_boundary": (
            "codex/doctrine/paper_modules/idea_microcosm_metabolism.md"
        ),
        "public_boundary_context": [
            "codex/doctrine/paper_modules/public_constellation_strategy.md",
            "codex/doctrine/paper_modules/dissemination_strategy.md",
        ],
        "route_governance_support": [
            "codex/doctrine/paper_modules/prime_directives.md",
            "codex/doctrine/paper_modules/local_to_general_propagation.md",
            "codex/doctrine/paper_modules/navigation_hologram_theory.md",
        ],
    }
    assert contract["required_projection_surfaces"] == [
        "codex/doctrine/paper_modules/_index.json",
        "codex/doctrine/paper_modules/_validation_report.json",
        "codex/doctrine/paper_modules/_route_coverage.json",
        "codex/doctrine/paper_modules/README.md",
    ]
    assert contract["atlas_option_surfaces"] == [
        "paper_modules",
        "standards",
        "microcosm_extracted_patterns",
        "system_microcosm",
        "axiom_candidates",
    ]
    assert contract["healthy_state_receipt"] == {
        "module_status": "all_authored_modules_up_to_date",
        "queue_status": "refresh_split_first_author_deprecate_queues_zero",
        "fact_audit_status": "paper_module_fact_audit_findings_zero",
    }
    assert contract["depth_order"] == [
        "entry_packet_selects_microcosm_public_substrate",
        "behavior_first_screen_visible",
        "microcosm_substrate_product_roof",
        "microcosm_entry_lattice_route_depth",
        "microcosm_public_export_type_plane_bridge",
        "paper_module_coverage_metabolism_corpus_health",
        "selected_module_card_then_source_evidence",
    ]
    assert contract["standard_type_plane_bridge"] == {
        "type_plane_row": (
            "codex/standards/std_standard_type_plane.json::"
            "type_plane_rows.public_microcosm_exports"
        ),
        "paper_module": (
            "codex/doctrine/paper_modules/microcosm_public_export_type_plane.md"
        ),
        "entry_route": (
            './repo-python kernel.py --entry "public Microcosm export '
            'dissemination boundary" --context-budget 12000'
        ),
        "atlas_drilldowns": [
            "paper_modules:microcosm_public_export_type_plane",
            "standards:std_microcosm",
            "standards:std_standard_type_plane",
        ],
        "authority_ceiling": (
            "type_plane_navigation_bridge_only_not_release_source_truth_provider_"
            "proof_or_candidate_axiom_authority"
        ),
    }
    assert contract["entry_packet_parity"] == {
        "source_ref": (
            "microcosm-substrate/atlas/entry_packet.json::"
            "doctrine_lattice_route.paper_module_refs"
        ),
        "coverage_rule": (
            "Every doctrine_lattice_route.paper_module_refs entry must be "
            "classified by primary_modules or supporting_lattice_modules."
        ),
        "role_coverage_rule": (
            "Every primary_modules and supporting_lattice_modules entry must be "
            "represented in module_depth_roles, so Atlas card readers see why "
            "each paper edge exists."
        ),
        "supporting_module_role": (
            "route_governance_and_propagation_context_not_microcosm_product_roof"
        ),
        "authority_ceiling": (
            "entry_packet_parity_only_not_product_primary_module_release_"
            "source_truth_proof_or_candidate_axiom_authority"
        ),
    }
    assert contract["authority_ceiling"] == (
        "coverage_navigation_only_not_public_release_source_truth_proof_or_"
        "candidate_axiom_authority"
    )

    rule = next(
        rule
        for rule in standard["validation_rules"]
        if rule["id"] == "microcosm_paper_module_coverage_contract"
    )
    assert rule["source_ref"] == (
        "codex/standards/std_microcosm.json::paper_module_coverage_contract"
    )
    assert rule["projection_ref"] == (
        "codex/doctrine/paper_modules/microcosm_entry_lattice.md::"
        "paper_module_coverage_contract"
    )
    assert rule["fields"] == [
        "primary_modules",
        "supporting_lattice_modules",
        "module_depth_roles",
        "required_projection_surfaces",
        "atlas_option_surfaces",
        "healthy_state_receipt",
        "depth_order",
        "standard_type_plane_bridge",
        "entry_packet_parity",
        "authority_ceiling",
    ]


def test_microcosm_paper_module_coverage_classifies_entry_packet_refs() -> None:
    contract = _std_microcosm()["paper_module_coverage_contract"]
    entry_packet_refs = _entry_packet()["doctrine_lattice_route"]["paper_module_refs"]

    classified_refs = (
        contract["primary_modules"] + contract["supporting_lattice_modules"]
    )
    assert set(entry_packet_refs).issubset(set(classified_refs))
    assert "codex/doctrine/paper_modules/paper_module_coverage_metabolism.md" in set(
        classified_refs
    )
    assert set(contract["supporting_lattice_modules"]) == {
        "codex/doctrine/paper_modules/prime_directives.md",
        "codex/doctrine/paper_modules/local_to_general_propagation.md",
        "codex/doctrine/paper_modules/navigation_hologram_theory.md",
    }


def test_microcosm_paper_module_depth_roles_cover_all_classified_refs() -> None:
    contract = _std_microcosm()["paper_module_coverage_contract"]
    roles = contract["module_depth_roles"]
    role_paths: set[str] = set()

    for value in roles.values():
        if isinstance(value, list):
            role_paths.update(value)
        else:
            role_paths.add(value)

    classified = set(contract["primary_modules"]) | set(
        contract["supporting_lattice_modules"]
    )
    assert classified == role_paths
    assert roles["product_roof"] == (
        "codex/doctrine/paper_modules/microcosm_substrate.md"
    )
    assert roles["entry_lattice"] == (
        "codex/doctrine/paper_modules/microcosm_entry_lattice.md"
    )
    assert roles["public_export_bridge"] == (
        "codex/doctrine/paper_modules/microcosm_public_export_type_plane.md"
    )
    assert roles["coverage_metabolism"] == (
        "codex/doctrine/paper_modules/paper_module_coverage_metabolism.md"
    )
    assert roles["laboratory_boundary"] == (
        "codex/doctrine/paper_modules/idea_microcosm_metabolism.md"
    )
    assert roles["route_governance_support"] == contract[
        "supporting_lattice_modules"
    ]


def test_microcosm_paper_module_coverage_contract_is_projected_into_modules() -> None:
    entry_lattice = (
        REPO_ROOT / "codex/doctrine/paper_modules/microcosm_entry_lattice.md"
    ).read_text(encoding="utf-8")
    product_roof = (
        REPO_ROOT / "codex/doctrine/paper_modules/microcosm_substrate.md"
    ).read_text(encoding="utf-8")
    public_export_bridge = (
        REPO_ROOT
        / "codex/doctrine/paper_modules/microcosm_public_export_type_plane.md"
    ).read_text(encoding="utf-8")

    for required in [
        "std_microcosm.json::paper_module_coverage_contract",
        "microcosm_public_export_type_plane",
        "paper_module_coverage_metabolism",
        "generated sidecars",
        "supporting route-lattice modules",
        "module_depth_roles",
        "entry-packet parity rule",
        "all authored modules up to date",
        "refresh/split/first-author/deprecate queues at zero",
    ]:
        assert required in entry_lattice

    assert "Verify paper-module coverage/depth" in entry_lattice
    assert "Route public Microcosm exports" in entry_lattice
    assert "Verify paper-module coverage without bloating this roof" in product_roof
    assert "paper_module_coverage_contract.module_depth_roles" in product_roof
    assert "sidecars as source truth" in product_roof
    assert "first-screen <project>` emits the JSON one-screen reader map" in product_roof
    assert "entry-packet paper-module ref classification" in public_export_bridge
    assert "primary/support module taxonomy" in public_export_bridge
    assert "module depth roles" in public_export_bridge


def test_public_microcosm_exports_type_plane_row_has_paper_module_bridge() -> None:
    standard = _std_microcosm()
    bridge = standard["paper_module_coverage_contract"]["standard_type_plane_bridge"]
    type_plane = _std_standard_type_plane()
    row = next(
        row
        for row in type_plane["type_plane_rows"]
        if row["type_id"] == "public_microcosm_exports"
    )

    assert bridge["paper_module"] in row["governing_standard_refs"]
    assert bridge["paper_module"] in row["projection_refs"]
    assert row["entry_depth_contract"]["standard_bridge"] == (
        "codex/standards/std_microcosm.json::"
        "paper_module_coverage_contract.standard_type_plane_bridge"
    )
    assert row["entry_depth_contract"]["paper_module_depth_order"] == [
        "microcosm_substrate",
        "microcosm_entry_lattice",
        "microcosm_public_export_type_plane",
        "paper_module_coverage_metabolism",
        "public_constellation_strategy",
        "dissemination_strategy",
    ]
    assert row["entry_depth_contract"]["coverage_role_contract"] == (
        "codex/standards/std_microcosm.json::"
        "paper_module_coverage_contract.module_depth_roles"
    )
    assert row["entry_depth_contract"]["supporting_lattice_depth"] == [
        "prime_directives",
        "local_to_general_propagation",
        "navigation_hologram_theory",
    ]
    assert row["entry_depth_contract"]["context_boundary_depth"] == [
        "idea_microcosm_metabolism",
        "public_constellation_strategy",
        "dissemination_strategy",
    ]
    assert row["entry_depth_contract"]["human_first_screen_projection"] == (
        "microcosm hello <project>"
    )
    assert row["entry_depth_contract"]["shared_behavior_proof"] == (
        "microcosm tour --card <project>"
    )
    assert row["entry_depth_contract"]["json_first_screen_projection"] == (
        "microcosm first-screen <project>"
    )
    assert row["entry_depth_contract"]["claim_boundary_drilldowns"] == [
        "microcosm authority --card",
        "microcosm workingness --card",
        "evidence_class_counters",
    ]
    assert "generated public export files only after behavior proof" in (
        row["entry_depth_contract"]["export_depth_rule"]
    )
    assert "--entry" in row["entry_depth_contract"]["control_entry"]
    assert any(
        "microcosm_public_export_type_plane" in probe
        for probe in row["validation_probe"]
    )
