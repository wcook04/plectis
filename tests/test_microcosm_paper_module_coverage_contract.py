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
        "codex/doctrine/paper_modules/paper_module_entry_projection_integrity.md",
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
        "entry_projection_integrity": (
            "codex/doctrine/paper_modules/"
            "paper_module_entry_projection_integrity.md"
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
        "paper_module_entry_projection_integrity_entry_count_honesty",
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
    assert contract["entry_intent_opening"] == {
        "intent_id": "microcosm_paper_module_depth",
        "owner": "system/lib/navigation_index_spine.py::ENTRY_INTENT_SPECS",
        "purpose": (
            "Task-conditioned entry/context packets for Microcosm paper-module, "
            "Atlas, coverage, and depth prompts must open Microcosm paper-module "
            "and type-plane handles before generic cognitive-operator or broad "
            "Atlas surfaces."
        ),
        "first_opening_kind": "paper_modules",
        "selected_opening_kind_order": [
            "paper_modules",
            "navigation_type_plane",
            "standards",
            "microcosm_extracted_patterns",
            "system_microcosm",
        ],
        "handoff_sequence_depth_order": [
            {
                "step_id": "open_microcosm_depth_module_cards",
                "command": (
                    "./repo-python kernel.py --option-surface paper_modules "
                    "--band card --ids microcosm_entry_lattice,"
                    "paper_module_coverage_metabolism,"
                    "paper_module_entry_projection_integrity,"
                    "microcosm_public_export_type_plane,microcosm_substrate"
                ),
                "surface_role": "ATLAS_PROJECTION",
                "role": "combined_microcosm_module_cards",
            },
            {
                "step_id": "open_microcosm_standard_contract",
                "command": (
                    "./repo-python kernel.py --option-surface standards "
                    "--band card --ids std_microcosm"
                ),
                "surface_role": "ATLAS_PROJECTION",
                "role": "standard_contract_card",
            },
            {
                "step_id": "open_public_microcosm_export_type_plane",
                "command": (
                    "./repo-python kernel.py --option-surface navigation_type_plane "
                    "--band card --ids public_microcosm_exports"
                ),
                "surface_role": "ATLAS_PROJECTION",
                "role": "public_export_type_plane_card",
            },
            {
                "step_id": "verify_microcosm_paper_module_coverage",
                "command": "./repo-python kernel.py --paper-module-coverage",
                "surface_role": "DRILLDOWN",
                "role": "coverage_health_receipt",
            },
        ],
        "context_pack_selected_row_order": [
            {
                "kind_id": "paper_modules",
                "row_id": "microcosm_entry_lattice",
                "role": "entry_lattice",
            },
            {
                "kind_id": "standards",
                "row_id": "std_microcosm",
                "role": "standard_contract",
            },
            {
                "kind_id": "paper_modules",
                "row_id": "paper_module_coverage_metabolism",
                "role": "coverage_metabolism",
            },
            {
                "kind_id": "paper_modules",
                "row_id": "paper_module_entry_projection_integrity",
                "role": "entry_projection_integrity",
            },
            {
                "kind_id": "paper_modules",
                "row_id": "microcosm_public_export_type_plane",
                "role": "public_export_type_plane_bridge",
            },
            {
                "kind_id": "navigation_type_plane",
                "row_id": "public_microcosm_exports",
                "role": "standard_type_plane_row",
            },
            {
                "kind_id": "paper_modules",
                "row_id": "microcosm_substrate",
                "role": "product_roof",
            },
        ],
        "context_pack_next_command_order": [
            {
                "command": (
                    "./repo-python kernel.py --option-surface paper_modules "
                    "--band card --ids microcosm_entry_lattice,"
                    "paper_module_coverage_metabolism,"
                    "paper_module_entry_projection_integrity,"
                    "microcosm_public_export_type_plane,microcosm_substrate"
                ),
                "surface_role": "ATLAS_PROJECTION",
                "role": "combined_microcosm_module_cards",
            },
            {
                "command": (
                    "./repo-python kernel.py --option-surface standards "
                    "--band card --ids std_microcosm"
                ),
                "surface_role": "ATLAS_PROJECTION",
                "role": "standard_contract_card",
            },
            {
                "command": (
                    "./repo-python kernel.py --option-surface navigation_type_plane "
                    "--band card --ids public_microcosm_exports"
                ),
                "surface_role": "ATLAS_PROJECTION",
                "role": "public_export_type_plane_card",
            },
            {
                "command": "./repo-python kernel.py --paper-module-coverage",
                "surface_role": "DRILLDOWN",
                "role": "coverage_health_receipt",
            },
        ],
        "required_prompt_shapes": [
            "microcosm paper module",
            "paper module coverage",
            "paper module depth",
            "microcosm atlas entry",
            "public microcosm exports",
        ],
        "authority_ceiling": (
            "entry_intent_drilldown_selection_only_not_control_entry_release_"
            "source_truth_proof_or_candidate_axiom_authority"
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
        "entry_intent_opening",
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
    assert "codex/doctrine/paper_modules/paper_module_entry_projection_integrity.md" in set(
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
    assert roles["entry_projection_integrity"] == (
        "codex/doctrine/paper_modules/paper_module_entry_projection_integrity.md"
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
    coverage_metabolism = (
        REPO_ROOT
        / "codex/doctrine/paper_modules/paper_module_coverage_metabolism.md"
    ).read_text(encoding="utf-8")
    entry_projection_integrity = (
        REPO_ROOT
        / "codex/doctrine/paper_modules/paper_module_entry_projection_integrity.md"
    ).read_text(encoding="utf-8")

    for required in [
        "std_microcosm.json::paper_module_coverage_contract",
        "microcosm_public_export_type_plane",
        "paper_module_coverage_metabolism",
        "paper_module_entry_projection_integrity",
        "generated sidecars",
        "supporting route-lattice modules",
        "module_depth_roles",
        "handoff sequence",
        "context-pack selected row order",
        "context-pack next command order",
        "microcosm_paper_module_depth",
        "navigation_type_plane",
        "entry-packet parity rule",
        "all authored modules up to date",
        "refresh/split/first-author/deprecate queues at zero",
    ]:
        assert required in entry_lattice

    depends_line = next(
        line for line in entry_lattice.splitlines() if line.startswith("**Depends on:**")
    )
    assert "`paper_module_coverage_metabolism`" in depends_line
    assert "`paper_module_entry_projection_integrity`" in depends_line
    assert (
        "direct dependency edges to `paper_module_coverage_metabolism` and "
        "`paper_module_entry_projection_integrity`"
    ) in entry_lattice
    assert "entry/count honesty as required depth rungs" in entry_lattice
    assert "Verify paper-module coverage/depth" in entry_lattice
    assert "Verify entry/count honesty" in entry_lattice
    assert "Route public Microcosm exports" in entry_lattice
    assert "Verify paper-module coverage without bloating this roof" in product_roof
    assert "paper_module_coverage_contract.module_depth_roles" in product_roof
    assert "paper_module_entry_projection_integrity" in product_roof
    assert "entry/count honesty" in product_roof
    assert "sidecars as source truth" in product_roof
    assert "first-screen <project>` emits the JSON one-screen reader map" in product_roof
    assert "entry-packet paper-module ref classification" in public_export_bridge
    assert "primary/support module taxonomy" in public_export_bridge
    assert "module depth roles" in public_export_bridge
    assert "type-plane row consumer" in public_export_bridge
    assert "entry-depth freshness binding" in public_export_bridge
    assert (
        "`public_microcosm_exports` opens this bridge before generated public files"
        in public_export_bridge
    )
    assert "focused coverage regression" in public_export_bridge
    assert "paper_module_entry_projection_integrity" in public_export_bridge
    assert "entry/count projection integrity" in public_export_bridge
    assert "microcosm_paper_module_depth" in coverage_metabolism
    assert "navigation_type_plane" in coverage_metabolism
    assert "cognitive_operators" in coverage_metabolism
    assert "explicit Microcosm consumers" in entry_projection_integrity
    assert "microcosm_public_export_type_plane" in entry_projection_integrity
    assert "entry/count projection honesty contract" in entry_projection_integrity


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
        "paper_module_entry_projection_integrity",
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
    assert row["compression_passport"]["safe_drilldown"] == (
        "./repo-python kernel.py --option-surface navigation_type_plane --band card "
        "--ids public_microcosm_exports"
    )
    assert "microcosm paper module depth" in row["compression_passport"][
        "cluster_keys"
    ]
    assert "generated public export files only after behavior proof" in (
        row["entry_depth_contract"]["export_depth_rule"]
    )
    assert "--entry" in row["entry_depth_contract"]["control_entry"]
    assert any(
        "microcosm_public_export_type_plane" in probe
        for probe in row["validation_probe"]
    )
