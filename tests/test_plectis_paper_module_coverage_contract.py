from __future__ import annotations

import json
from pathlib import Path

import pytest


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


def _paper_module_instances() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((MICROCOSM_ROOT / "paper_modules").glob("*.json"))
    ]


def _paper_module_coverage() -> dict:
    return json.loads(
        (MICROCOSM_ROOT / "core/doctrine_lattice_coverage.json").read_text(
            encoding="utf-8"
        )
    )["paper_module_instance_corpus"]


def _paper_module_capsules() -> list[dict]:
    return json.loads(
        (MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(
            encoding="utf-8"
        )
    )["paper_modules"]


def _mechanism_sources() -> list[dict]:
    return json.loads(
        (MICROCOSM_ROOT / "core/mechanism_sources.json").read_text(
            encoding="utf-8"
        )
    )["mechanisms"]


BATCH8_CAPSULE_BINDING_IDS = {
    "paper_module.batch8_audio_level_rms_port",
    "paper_module.batch8_compliance_pipeline_capsule",
    "paper_module.batch8_policy_engines_capsule",
    "paper_module.batch8_station_surface_atlas_layout_port",
    "paper_module.batch8_structural_theses_capsule",
    "paper_module.batch8_tools_tail_primitives_capsule",
    "paper_module.batch8_validator_checker_capsule",
}

FORMAL_PROOF_CAPSULE_BINDING_IDS = {
    "paper_module.corpus_readiness_mathlib_absence_gate",
    "paper_module.formal_evidence_cell_anchor_resolver",
    "paper_module.formal_math_lean_proof_witness",
    "paper_module.formal_math_premise_retrieval",
    "paper_module.formal_math_readiness_gate",
    "paper_module.formal_math_verifier_trace_repair_loop",
    "paper_module.lean_std_premise_index",
    "paper_module.mathematical_strategy_atlas",
    "paper_module.proof_diagnostic_evidence_spine",
    "paper_module.ring2_premise_precision_recall",
}

AGENT_SAFETY_CAPSULE_BINDING_IDS = {
    "paper_module.agent_benchmark_integrity_anti_gaming_replay",
    "paper_module.agent_monitor_redteam_falsification_replay",
    "paper_module.agent_sabotage_scheming_monitor_replay",
    "paper_module.agent_sandbox_policy_escape_replay",
    "paper_module.belief_state_process_reward_replay",
    "paper_module.indirect_prompt_injection_information_flow_policy_replay",
    "paper_module.mcp_tool_authority_replay",
    "paper_module.mechanistic_interpretability_circuit_attribution_replay",
    "paper_module.sleeper_memory_poisoning_quarantine_replay",
    "paper_module.spatial_world_model_counterfactual_simulation_replay",
}

BATCH10_BATCH12_CAPSULE_BINDING_IDS = {
    "paper_module.batch10_cold_eval_honesty_capsule",
    "paper_module.batch10_frontend_work_market_cockpit_capsule",
    "paper_module.batch10_governance_compilers_capsule",
    "paper_module.batch10_live_source_drift_capsule",
    "paper_module.batch12_market_dashboard_read_model_capsule",
    "paper_module.batch12_prediction_market_board_capsule",
    "paper_module.batch12_release_claim_language_gate",
}

BATCH5_AUTHORITY_CAPSULE_BINDING_IDS = {
    "paper_module.batch5_authority_systems_capsule",
}

BATCH7_ORACLE_SIBLING_CAPSULE_BINDING_IDS = {
    "paper_module.batch7_oracle_sibling_capsule",
}

BATCH7_DEMO_TAKE_CONSOLE_CAPSULE_BINDING_IDS = {
    "paper_module.batch7_demo_take_console_capsule",
}

BATCH7_BATCH9_PATTERN_CAPSULE_BINDING_IDS = {
    "paper_module.batch7_macro_engines_capsule",
    "paper_module.batch7_station_runtime_capsule",
    "paper_module.batch9_macro_engines_capsule",
    "paper_module.pattern_assimilation",
}

WORK_COORDINATION_CAPSULE_BINDING_IDS = {
    "paper_module.agent_closeout_faithfulness_audit",
    "paper_module.bridge_phase_continuity_runtime",
    "paper_module.concurrency_mission_control",
    "paper_module.durable_agent_work_landing_replay",
    "paper_module.mission_transaction_work_spine",
    "paper_module.workstream_driver_recency_coalescer",
}

DOCTRINE_DIAGNOSTICS_CAPSULE_BINDING_IDS = {
    "paper_module.cognitive_operator_registry",
    "paper_module.doctrine_fact_claim_audit",
    "paper_module.executable_doctrine_grammar",
    "paper_module.pattern_binding_contract",
    "paper_module.self_ignorance_coverage_ledger",
    "paper_module.standards_meta_diagnostics",
    "paper_module.tool_server_pressure_inventory",
    "paper_module.undeclared_library_prior_classifier",
}

VERIFIER_PREDICTION_CAPSULE_BINDING_IDS = {
    "paper_module.finance_forecast_evaluation_spine",
    "paper_module.prediction_oracle_reconciliation",
    "paper_module.proof_derived_governed_mutation_authorization",
    "paper_module.provider_context_recipe_budget",
    "paper_module.tactic_portfolio_availability",
    "paper_module.target_shape_tactic_routing",
    "paper_module.verifier_lab_execution_spine",
    "paper_module.verifier_lab_kernel",
}

AGENT_ROUTE_RUNTIME_CAPSULE_BINDING_IDS = {
    "paper_module.agent_memory_temporal_conflict_replay",
    "paper_module.agent_route_observability_runtime",
    "paper_module.bounded_autonomy_campaign_packet",
    "paper_module.cold_reader_route_map",
    "paper_module.engine_room_demo",
    "paper_module.macro_projection_import_protocol",
    "paper_module.routing_anti_patterns_registry",
}

ENGINE_ROOM_LEGACY_REENTRY_LOCI = {
    "paper_module.engine_room_annex_knowledge_router": (
        "src/microcosm_core/engine_room/annex_knowledge_router.py"
    ),
    "paper_module.engine_room_derived_fact_provider_engine": (
        "src/microcosm_core/engine_room/derived_fact_provider_engine.py"
    ),
    "paper_module.engine_room_egress_self_compliance_gate": (
        "src/microcosm_core/engine_room/egress_self_compliance_gate.py"
    ),
    "paper_module.engine_room_lean_proof_search_lab": (
        "src/microcosm_core/engine_room/lean_proof_search_lab.py"
    ),
    "paper_module.engine_room_navigation_fitness_benchmark": (
        "src/microcosm_core/engine_room/navigation_fitness_benchmark.py"
    ),
}

ENGINE_ROOM_LEGACY_VALIDATION_TESTS = {
    "paper_module.engine_room_annex_knowledge_router": (
        "tests/test_engine_room_annex_knowledge_router.py"
    ),
    "paper_module.engine_room_derived_fact_provider_engine": (
        "tests/test_engine_room_derived_fact_provider_engine.py"
    ),
    "paper_module.engine_room_egress_self_compliance_gate": (
        "tests/test_engine_room_egress_self_compliance_gate.py"
    ),
    "paper_module.engine_room_lean_proof_search_lab": (
        "tests/test_engine_room_lean_proof_search_lab.py"
    ),
    "paper_module.engine_room_navigation_fitness_benchmark": (
        "tests/test_engine_room_navigation_fitness_benchmark.py"
    ),
}

NON_ENGINE_ROOM_LEGACY_REENTRY_LOCI = {
    "paper_module.batch7_secondary_runtime_capsule": (
        "src/microcosm_core/organs/batch7_secondary_runtime_capsule.py"
    ),
    "paper_module.batch7_zenith_macos_capsule": (
        "src/microcosm_core/organs/batch7_zenith_macos_capsule.py"
    ),
    "paper_module.first_screen_composition_root": (
        "src/microcosm_core/first_screen_composition.py"
    ),
    "paper_module.microcosm_axiom_substrate": (
        "src/microcosm_core/validators/axiom_support_cover.py"
    ),
    "paper_module.tactic_portfolio_availability_probe": (
        "src/microcosm_core/organs/tactic_portfolio_availability_probe.py"
    ),
}

LEGACY_REENTRY_LOCI = {
    **ENGINE_ROOM_LEGACY_REENTRY_LOCI,
    **NON_ENGINE_ROOM_LEGACY_REENTRY_LOCI,
}


def _coverage_legacy_ids() -> set[str]:
    coverage = _paper_module_coverage()
    coverage_legacy_ids = set(coverage["legacy_only_ids"])
    assert coverage_legacy_ids == set(coverage["required_subject_gap_ids"])
    assert coverage["legacy_only_count"] == len(coverage_legacy_ids)
    return coverage_legacy_ids


def _legacy_instance_rows() -> dict[str, dict]:
    return {
        row["id"]: row
        for row in _paper_module_instances()
        if row["paper_module_payload"]["source_authority"]
        == "legacy_markdown_projection"
    }


def _skip_when_legacy_projection_drifted() -> set[str]:
    coverage_legacy_ids = _coverage_legacy_ids()
    legacy_ids = set(_legacy_instance_rows())
    if legacy_ids != coverage_legacy_ids:
        pytest.skip(
            "legacy paper-module generated sidecars are not synced to "
            "coverage legacy_only_ids; worklist detail assertions are "
            "deferred to the sidecar settlement lane"
        )
    return coverage_legacy_ids

JSON_CAPSULE_BINDING_HEADING = "## JSON Capsule Binding"
CLAIM_CEILING_HEADING = "## Claim Ceiling"
PRIOR_ART_GROUNDING_HEADING = "## Prior Art Grounding"
VALIDATION_RECEIPT_PATH_HEADING = "## Validation Receipt Path"
READER_BOUNDARY_SECTION_HEADINGS = (
    "## Reader Evidence Routing",
    "## Reader Proof Boundary",
    "## Public Site Availability Boundary",
    "## Public-Safe Body Handling",
)


def _assert_json_capsule_binding_heading(markdown: str, row_id: str) -> None:
    assert JSON_CAPSULE_BINDING_HEADING in markdown.splitlines(), row_id


def _heading_count(markdown: str, heading: str) -> int:
    return sum(1 for line in markdown.splitlines() if line == heading)


def test_paper_module_reader_boundary_sections_are_not_duplicated() -> None:
    for row in _paper_module_instances():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")

        for heading in READER_BOUNDARY_SECTION_HEADINGS:
            assert _heading_count(markdown, heading) <= 1, (
                row["id"],
                heading,
            )


def test_paper_module_json_capsule_binding_sections_are_present_once() -> None:
    missing: list[str] = []
    duplicated: list[tuple[str, int]] = []

    for row in _paper_module_instances():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        heading_count = _heading_count(markdown, JSON_CAPSULE_BINDING_HEADING)
        if heading_count == 0:
            missing.append(row["id"])
        elif heading_count > 1:
            duplicated.append((row["id"], heading_count))

    assert missing == []
    assert duplicated == []


def test_paper_module_claim_ceiling_sections_are_present_once() -> None:
    missing: list[str] = []
    duplicated: list[tuple[str, int]] = []

    for row in _paper_module_instances():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        heading_count = _heading_count(markdown, CLAIM_CEILING_HEADING)
        if heading_count == 0:
            missing.append(row["id"])
        elif heading_count > 1:
            duplicated.append((row["id"], heading_count))

    assert missing == []
    assert duplicated == []


def test_paper_module_grounding_and_receipt_sections_are_present_once() -> None:
    missing: list[tuple[str, str]] = []
    duplicated: list[tuple[str, str, int]] = []

    for row in _paper_module_instances():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")

        for heading in (
            PRIOR_ART_GROUNDING_HEADING,
            VALIDATION_RECEIPT_PATH_HEADING,
        ):
            heading_count = _heading_count(markdown, heading)
            if heading_count == 0:
                missing.append((row["id"], heading))
            elif heading_count > 1:
                duplicated.append((row["id"], heading, heading_count))

    assert missing == []
    assert duplicated == []


def test_paper_module_json_instances_publish_source_and_validator_refs() -> None:
    missing_source_refs: list[str] = []
    missing_validator_refs: list[str] = []

    for row in _paper_module_instances():
        if not row["source_refs"]:
            missing_source_refs.append(row["id"])
        if not row["validator_refs"]:
            missing_validator_refs.append(row["id"])

    assert missing_source_refs == []
    assert missing_validator_refs == []


def test_json_capsule_organ_subjects_bind_matching_mechanism_subjects() -> None:
    mechanism_by_organ: dict[str, list[str]] = {}
    for mechanism in _mechanism_sources():
        runs_in = mechanism.get("runs_in") or []
        if len(runs_in) == 1:
            mechanism_by_organ.setdefault(runs_in[0], []).append(mechanism["id"])

    missing: dict[str, list[str]] = {}
    stale_notes: list[str] = []
    for capsule in _paper_module_capsules():
        if capsule.get("source_authority") != "json_capsule":
            continue
        subjects = capsule.get("subjects") or []
        organ_refs = [
            subject["ref"]
            for subject in subjects
            if subject.get("kind") == "organ"
        ]
        mechanism_refs = {
            subject["ref"]
            for subject in subjects
            if subject.get("kind") == "mechanism"
        }
        expected = [
            mechanism_id
            for organ_ref in organ_refs
            if organ_ref in mechanism_by_organ
            for mechanism_id in mechanism_by_organ[organ_ref]
        ]
        absent = [
            mechanism_id
            for mechanism_id in expected
            if mechanism_id not in mechanism_refs
        ]
        if absent:
            missing[capsule["id"]] = absent
        if (
            absent
            or any(mechanism_id in mechanism_refs for mechanism_id in expected)
        ) and "no mechanism subject is named" in capsule.get("strangler_note", ""):
            stale_notes.append(capsule["id"])

    assert missing == {}
    assert stale_notes == []


def test_plectis_paper_module_coverage_contract_is_standard_backed() -> None:
    standard = _std_microcosm()
    contract = standard["paper_module_coverage_contract"]

    assert contract["primary_modules"] == [
        "codex/doctrine/paper_modules/plectis_substrate.md",
        "codex/doctrine/paper_modules/plectis_entry_lattice.md",
        "codex/doctrine/paper_modules/plectis_public_export_type_plane.md",
        "codex/doctrine/paper_modules/plectis_runtime_organ_atlas.md",
        "codex/doctrine/paper_modules/paper_module_coverage_metabolism.md",
        "codex/doctrine/paper_modules/paper_module_entry_projection_integrity.md",
        "codex/doctrine/paper_modules/laboratory_metabolism.md",
        "codex/doctrine/paper_modules/public_constellation_strategy.md",
        "codex/doctrine/paper_modules/dissemination_strategy.md",
    ]
    assert contract["supporting_lattice_modules"] == [
        "codex/doctrine/paper_modules/prime_directives.md",
        "codex/doctrine/paper_modules/local_to_general_propagation.md",
        "codex/doctrine/paper_modules/navigation_hologram_theory.md",
    ]
    assert contract["module_depth_roles"] == {
        "product_roof": "codex/doctrine/paper_modules/plectis_substrate.md",
        "entry_lattice": "codex/doctrine/paper_modules/plectis_entry_lattice.md",
        "public_export_bridge": (
            "codex/doctrine/paper_modules/plectis_public_export_type_plane.md"
        ),
        "runtime_organ_source_loci": (
            "codex/doctrine/paper_modules/plectis_runtime_organ_atlas.md"
        ),
        "coverage_metabolism": (
            "codex/doctrine/paper_modules/paper_module_coverage_metabolism.md"
        ),
        "entry_projection_integrity": (
            "codex/doctrine/paper_modules/"
            "paper_module_entry_projection_integrity.md"
        ),
        "laboratory_boundary": (
            "codex/doctrine/paper_modules/laboratory_metabolism.md"
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
    all_corpus_dispatch = contract["all_corpus_compression_dispatch"]
    assert "all paper modules in compressed form" in all_corpus_dispatch["purpose"]
    assert "cluster_flag" in all_corpus_dispatch["entry_rule"]
    assert all_corpus_dispatch["canonical_sequence"] == [
        './repo-python kernel.py --entry "<task>" --context-budget 12000',
        (
            "AIW_CONTEXT_PACK_DISABLE_SEMANTIC=1 ./repo-python kernel.py "
            '--context-pack "<task>" --context-budget 12000'
        ),
        "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
        (
            "./repo-python kernel.py --option-surface paper_modules "
            "--band card --ids plectis_entry_lattice,"
            "paper_module_coverage_metabolism,"
            "paper_module_entry_projection_integrity,"
            "plectis_public_export_type_plane,"
            "plectis_runtime_organ_atlas,plectis_substrate"
        ),
        (
            "./repo-python kernel.py --option-surface standards "
            "--band card --ids std_microcosm"
        ),
        (
            "./repo-python kernel.py --option-surface navigation_type_plane "
            "--band card --ids public_plectis_exports"
        ),
        "./repo-python kernel.py --paper-module-coverage",
    ]
    assert [
        locus["source_ref"] for locus in all_corpus_dispatch["compression_owner_loci"]
    ] == [
        "system/lib/standard_option_surface.py::_paper_module_cluster_rows",
        "system/lib/standard_option_surface.py::_paper_module_compression_packet",
        "system/lib/standard_option_surface.py::_paper_module_compression_passport",
        (
            "system/lib/navigation_context_pack.py::"
            "PLECTIS_PAPER_MODULE_DEPTH_ANCHORS"
        ),
        "system/lib/navigation_index_spine.py::ENTRY_INTENT_SPECS",
        (
            "system/lib/navigation_coverage_matrix.py::"
            "build_coverage_enforcement_matrix"
        ),
    ]
    assert all_corpus_dispatch["selected_depth_slice"] == [
        "plectis_entry_lattice",
        "std_microcosm",
        "paper_module_coverage_metabolism",
        "paper_module_entry_projection_integrity",
        "plectis_public_export_type_plane",
        "plectis_runtime_organ_atlas",
        "public_plectis_exports",
        "plectis_substrate",
    ]
    assert "All-row flag remains a compatibility redirect" in all_corpus_dispatch[
        "compatibility_boundary"
    ]
    assert (
        "do not commit generated paper-module sidecars or System Atlas outputs"
        in all_corpus_dispatch["generated_sidecar_closeout_rule"]
    )
    assert all_corpus_dispatch["authority_ceiling"] == (
        "all_corpus_compression_navigation_only_not_source_truth_release_"
        "permission_proof_correctness_or_candidate_axiom_authority"
    )
    cluster_digest = contract["cluster_digest_contract"]
    assert "typed digest fields" in cluster_digest["purpose"]
    assert "cluster_flag" in cluster_digest["cluster_surface_rule"]
    assert cluster_digest["required_packet_fields"] == [
        "summary.row_count",
        "summary.total_available",
        "summary.cluster_currentness.index_freshness",
        "summary.cluster_currentness.index_generated_at",
        "summary.cluster_semantics",
        "summary.cluster_authority_distribution.authored_primary",
        "summary.cluster_authority_distribution.suggested_primary",
        "summary.cluster_authority_distribution.hierarchy_fallback",
        "summary.cluster_authority_distribution.heuristic_fallback",
        "summary.cluster_authority_distribution.unclassified",
        "summary.cluster_authority_distribution.authored_share",
        "summary.cluster_authority_distribution.suggested_share",
        "summary.cluster_authority_distribution.fallback_share",
        "summary.cluster_authority_distribution.chip",
        "summary.cluster_authority_distribution.next_population_route",
        "cluster_omission_receipt.omitted",
        "cluster_omission_receipt.reason",
        "cluster_omission_receipt.authority_collapse_rule",
        "cluster_omission_receipt.drilldown",
    ]
    assert cluster_digest["required_cluster_row_fields"] == [
        "rows[].cluster_id",
        "rows[].cluster_source_axis",
        "rows[].count",
        "rows[].top_ids",
        "rows[].route_metadata.authored_primary_count",
        "rows[].route_metadata.suggested_primary_count",
        "rows[].route_metadata.hierarchy_fallback_count",
        "rows[].route_metadata.heuristic_fallback_count",
        "rows[].route_metadata.unclassified_count",
        "rows[].authority_distribution.authored_primary",
        "rows[].authority_distribution.suggested_primary",
        "rows[].authority_distribution.hierarchy_fallback",
        "rows[].authority_distribution.heuristic_fallback",
        "rows[].authority_distribution.unclassified",
        "rows[].authority_distribution.authored_share",
        "rows[].authority_distribution.suggested_share",
        "rows[].authority_distribution.chip",
        "rows[].governing_counts.distinct_principles",
        "rows[].governing_counts.distinct_concepts",
        "rows[].top_governing_refs.principles",
        "rows[].top_governing_refs.concepts",
        "rows[].claim",
        "rows[].drilldown_command",
        "rows[].omission_policy",
    ]
    assert [
        locus["source_ref"] for locus in cluster_digest["owner_loci"]
    ] == [
        "system/lib/standard_option_surface.py::_paper_module_cluster_key",
        "system/lib/standard_option_surface.py::_paper_module_cluster_rows",
        "system/lib/standard_option_surface.py::_paper_module_cluster_authority_summary",
        "system/lib/standard_option_surface.py::build_option_surface",
        (
            "microcosm-substrate/tests/"
            "test_plectis_paper_module_coverage_contract.py::"
            "test_plectis_paper_module_coverage_contract_is_projected_into_modules"
        ),
    ]
    assert "authored primary_subdomain" in cluster_digest["typed_grouping_policy"]
    assert "card/evidence rungs" in cluster_digest["drilldown_rule"]
    assert cluster_digest["authority_ceiling"] == (
        "cluster_digest_navigation_only_not_module_authority_source_truth_"
        "release_permission_proof_correctness_or_candidate_axiom_authority"
    )
    budget_honesty = contract["context_pack_budget_honesty_contract"]
    assert "over-budget routine packet is repair evidence" in budget_honesty[
        "purpose"
    ]
    assert "budget.contract_status is within_budget" in budget_honesty[
        "budget_rule"
    ]
    assert "budget.over_budget is true" in budget_honesty["budget_rule"]
    assert "selected Plectis depth slice as handles" in budget_honesty[
        "budget_rule"
    ]
    assert "plectis_entry_lattice" in budget_honesty["protected_row_rule"]
    assert [
        locus["source_ref"] for locus in budget_honesty["owner_loci"]
    ] == [
        "system/lib/navigation_context_pack.py::BUDGET_TRIM_PROTECTED_ROWS",
        "system/lib/navigation_context_pack.py::_budget_trim",
        (
            "system/lib/navigation_context_pack.py::_budget_trim::"
            "hard_ceiling_selected_row_handles"
        ),
        (
            "system/server/tests/test_navigation_context_pack.py::"
            "test_context_pack_navigation_spine_long_query_stays_under_budget"
        ),
        (
            "system/server/tests/test_navigation_context_pack.py::"
            "test_context_pack_cli_emits_budgeted_json"
        ),
        (
            "microcosm-substrate/tests/"
            "test_plectis_paper_module_coverage_contract.py::"
            "test_plectis_paper_module_coverage_contract_is_projected_into_modules"
        ),
    ]
    assert budget_honesty["required_status_fields"] == [
        "budget.requested_tokens",
        "budget.estimated_tokens",
        "budget.over_budget",
        "budget.contract_status",
        "budget.hard_ceiling_repair_status",
        "budget.routine_selected_row_economy.status",
        "budget.routine_economy_effective_ceiling_tokens",
        (
            "navigation_index_spine.entry_intent_openings.task_conditioned."
            "reentry_receipt.status"
        ),
    ]
    assert any(
        "patch navigation_context_pack.py budget trimming" in action
        for action in budget_honesty["repair_actions"]
    )
    assert budget_honesty["authority_ceiling"] == (
        "context_pack_budget_honesty_only_not_source_truth_release_permission_"
        "proof_correctness_or_candidate_axiom_authority"
    )
    source_loci = contract["source_loci_depth_contract"]
    assert source_loci["coverage_claim_rule"] == (
        "100% paper-module coverage means every authored module is routed, "
        "current, and drilldown-visible through the paper-module route graph; "
        "explanation depth still requires the selected owner paper module, "
        "source loci, and focused regression to cite the live substrate behind "
        "the claim."
    )
    assert [
        locus["source_ref"] for locus in source_loci["runtime_loci"]
    ] == [
        "tools/meta/factory/build_paper_module_index.py::main",
        "system/lib/paper_modules.py::build_route_coverage",
        "system/lib/kernel/commands/navigate.py::cmd_paper_module_coverage",
        (
            "system/lib/kernel_navigation.py::"
            "KernelNavigation.build_paper_module_route_coverage"
        ),
        "system/lib/standard_option_surface.py::build_option_surface",
        "system/lib/navigation_index_spine.py::ENTRY_INTENT_SPECS",
        (
            "system/lib/navigation_context_pack.py::"
            "PLECTIS_PAPER_MODULE_DEPTH_ANCHORS"
        ),
        (
            "system/lib/navigation_context_pack.py::"
            "_is_plectis_paper_module_depth_query"
        ),
        (
            "microcosm-substrate/tests/"
            "test_plectis_paper_module_coverage_contract.py::"
            "test_plectis_paper_module_coverage_contract_is_projected_into_modules"
        ),
    ]
    assert source_loci["required_closeout_proof"] == [
        "./repo-python tools/meta/factory/build_paper_module_index.py --check --report",
        "./repo-python kernel.py --paper-module-coverage",
        (
            "PYTHONPATH=microcosm-substrate/src ./repo-pytest "
            "microcosm-substrate/tests/"
            "test_plectis_paper_module_coverage_contract.py -q"
        ),
    ]
    atlas_closeout = contract["atlas_source_coupling_closeout_contract"]
    assert "System Atlas source-coupling route" in atlas_closeout["purpose"]
    assert "System Atlas and Kind Atlas are navigation projections" in atlas_closeout[
        "projection_role_rule"
    ]
    assert [
        locus["source_ref"] for locus in atlas_closeout["source_coupling_loci"]
    ] == [
        "tools/meta/factory/build_system_atlas.py::main",
        "system/lib/navigation_index_spine.py::_system_atlas_source_coupling",
        "system/lib/navigation_index_spine.py::_system_atlas_currentness",
        "system/lib/kind_atlas.py::_system_atlas_currentness",
        "system/lib/navigation_context_pack.py::_generated_projection_owner_selected_row",
        (
            "microcosm-substrate/tests/"
            "test_plectis_paper_module_coverage_contract.py::"
            "test_plectis_paper_module_coverage_contract_is_standard_backed"
        ),
    ]
    assert atlas_closeout["required_closeout_proof"] == [
        "./repo-python tools/meta/factory/build_paper_module_index.py --check --report",
        "./repo-python tools/meta/factory/build_system_atlas.py --check",
        (
            'AIW_CONTEXT_PACK_DISABLE_SEMANTIC=1 ./repo-python kernel.py '
            '--context-pack "<Plectis paper-module depth task>" '
            "--context-budget 12000"
        ),
        (
            './repo-python kernel.py --coverage-enforcement-matrix '
            '"<Plectis paper-module depth task>" --context-budget 12000'
        ),
        (
            "PYTHONPATH=microcosm-substrate/src ./repo-pytest "
            "microcosm-substrate/tests/"
            "test_plectis_paper_module_coverage_contract.py -q"
        ),
    ]
    assert atlas_closeout["closeout_status_fields"] == [
        "navigation_index_spine.currentness.status",
        "source_coupling.status",
        "source_coupling.changed_source_count",
        "source_coupling.dirty_changed_source_count",
        "source_coupling.safe_to_commit_generated_outputs_without_sources",
    ]
    assert "do not refresh or commit state/system_atlas" in atlas_closeout[
        "blocked_refresh_rule"
    ]
    assert atlas_closeout["authority_ceiling"] == (
        "atlas_source_coupling_closeout_only_not_generated_atlas_source_truth_"
        "release_permission_proof_correctness_or_candidate_axiom_authority"
    )
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
        "plectis_substrate_product_roof",
        "plectis_entry_lattice_route_depth",
        "plectis_public_export_type_plane_bridge",
        "plectis_runtime_organ_atlas_source_loci_depth",
        "paper_module_coverage_metabolism_corpus_health",
        "paper_module_entry_projection_integrity_entry_count_honesty",
        "selected_module_card_then_source_evidence",
    ]
    assert contract["standard_type_plane_bridge"] == {
        "type_plane_row": (
            "codex/standards/std_standard_type_plane.json::"
            "type_plane_rows.public_plectis_exports"
        ),
        "paper_module": (
            "codex/doctrine/paper_modules/plectis_public_export_type_plane.md"
        ),
        "entry_route": (
            './repo-python kernel.py --entry "public Plectis export '
            'dissemination boundary" --context-budget 12000'
        ),
        "atlas_drilldowns": [
            "paper_modules:plectis_public_export_type_plane",
            "paper_modules:plectis_runtime_organ_atlas",
            "standards:std_microcosm",
            "standards:std_standard_type_plane",
        ],
        "authority_ceiling": (
            "type_plane_navigation_bridge_only_not_release_source_truth_provider_"
            "proof_or_candidate_axiom_authority"
        ),
    }
    assert contract["entry_intent_opening"] == {
        "intent_id": "plectis_paper_module_depth",
        "owner": "system/lib/navigation_index_spine.py::ENTRY_INTENT_SPECS",
        "purpose": (
            "Task-conditioned entry/context packets for Plectis paper-module, "
            "Atlas, coverage, and depth prompts must open Plectis paper-module "
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
                    "--band card --ids plectis_entry_lattice,"
                    "paper_module_coverage_metabolism,"
                    "paper_module_entry_projection_integrity,"
                    "plectis_public_export_type_plane,"
                    "plectis_runtime_organ_atlas,plectis_substrate"
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
                    "--band card --ids public_plectis_exports"
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
                "row_id": "plectis_entry_lattice",
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
                "row_id": "plectis_public_export_type_plane",
                "role": "public_export_type_plane_bridge",
            },
            {
                "kind_id": "paper_modules",
                "row_id": "plectis_runtime_organ_atlas",
                "role": "runtime_organ_source_loci",
            },
            {
                "kind_id": "navigation_type_plane",
                "row_id": "public_plectis_exports",
                "role": "standard_type_plane_row",
            },
            {
                "kind_id": "paper_modules",
                "row_id": "plectis_substrate",
                "role": "product_roof",
            },
        ],
        "context_pack_next_command_order": [
            {
                "command": (
                    "./repo-python kernel.py --option-surface paper_modules "
                    "--band card --ids plectis_entry_lattice,"
                    "paper_module_coverage_metabolism,"
                    "paper_module_entry_projection_integrity,"
                    "plectis_public_export_type_plane,"
                    "plectis_runtime_organ_atlas,plectis_substrate"
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
                    "--band card --ids public_plectis_exports"
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
        "codex/doctrine/paper_modules/plectis_entry_lattice.md::"
        "paper_module_coverage_contract"
    )
    assert rule["fields"] == [
        "primary_modules",
        "supporting_lattice_modules",
        "module_depth_roles",
        "required_projection_surfaces",
        "all_corpus_compression_dispatch",
        "cluster_digest_contract",
        "context_pack_budget_honesty_contract",
        "source_loci_depth_contract",
        "atlas_source_coupling_closeout_contract",
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


def test_plectis_paper_module_depth_roles_cover_all_classified_refs() -> None:
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
        "codex/doctrine/paper_modules/plectis_substrate.md"
    )
    assert roles["entry_lattice"] == (
        "codex/doctrine/paper_modules/plectis_entry_lattice.md"
    )
    assert roles["public_export_bridge"] == (
        "codex/doctrine/paper_modules/plectis_public_export_type_plane.md"
    )
    assert roles["runtime_organ_source_loci"] == (
        "codex/doctrine/paper_modules/plectis_runtime_organ_atlas.md"
    )
    assert roles["coverage_metabolism"] == (
        "codex/doctrine/paper_modules/paper_module_coverage_metabolism.md"
    )
    assert roles["entry_projection_integrity"] == (
        "codex/doctrine/paper_modules/paper_module_entry_projection_integrity.md"
    )
    assert roles["laboratory_boundary"] == (
        "codex/doctrine/paper_modules/laboratory_metabolism.md"
    )
    assert roles["route_governance_support"] == contract[
        "supporting_lattice_modules"
    ]


def test_batch8_capsule_paper_modules_explain_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in BATCH8_CAPSULE_BINDING_IDS
    }

    assert set(rows) == BATCH8_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        compact_markdown = " ".join(markdown.split())
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "Atlas card is linked" in markdown, row["id"]
        assert "authority ceiling" in markdown, row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert (
            payload["generated_projections"]["atlas_card"]["status"]
            == "linked_from_capsule_edges"
        ), row["id"]


def test_formal_proof_paper_modules_explain_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in FORMAL_PROOF_CAPSULE_BINDING_IDS
    }

    assert set(rows) == FORMAL_PROOF_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "generated Atlas projection" in markdown, row["id"]
        assert "authority ceiling" in markdown, row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert "validation receipts" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert payload["generated_projections"]["atlas_card"]["status"] in {
            "blocked_until_organ_atlas_owner_lane_binds_edges",
            "linked_from_capsule_edges",
        }, row["id"]


def test_agent_safety_replay_paper_modules_explain_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in AGENT_SAFETY_CAPSULE_BINDING_IDS
    }

    assert set(rows) == AGENT_SAFETY_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "generated Atlas projection" in markdown, row["id"]
        assert "authority ceiling" in markdown, row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert "validation receipts" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert payload["generated_projections"]["atlas_card"]["status"] in {
            "blocked_until_organ_atlas_owner_lane_binds_edges",
            "linked_from_capsule_edges",
        }, row["id"]


def test_batch10_batch12_paper_modules_explain_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in BATCH10_BATCH12_CAPSULE_BINDING_IDS
    }

    assert set(rows) == BATCH10_BATCH12_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "generated Atlas projection" in markdown, row["id"]
        assert "authority ceiling" in markdown, row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert "validation receipts" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert (
            payload["generated_projections"]["atlas_card"]["status"]
            == "linked_from_capsule_edges"
        ), row["id"]


def test_batch5_authority_paper_module_explains_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in BATCH5_AUTHORITY_CAPSULE_BINDING_IDS
    }

    assert set(rows) == BATCH5_AUTHORITY_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "generated Atlas projection" in markdown, row["id"]
        assert "authority ceiling" in markdown.lower(), row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert "validation receipts" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert (
            payload["generated_projections"]["atlas_card"]["status"]
            == "linked_from_capsule_edges"
        ), row["id"]


def test_batch7_oracle_sibling_paper_module_explains_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in BATCH7_ORACLE_SIBLING_CAPSULE_BINDING_IDS
    }

    assert set(rows) == BATCH7_ORACLE_SIBLING_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "generated Atlas projection" in markdown, row["id"]
        assert "authority ceiling" in markdown.lower(), row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert "validation receipts" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert (
            payload["generated_projections"]["atlas_card"]["status"]
            == "blocked_until_organ_atlas_owner_lane_binds_edges"
        ), row["id"]


def test_batch7_demo_take_console_paper_module_explains_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in BATCH7_DEMO_TAKE_CONSOLE_CAPSULE_BINDING_IDS
    }

    assert set(rows) == BATCH7_DEMO_TAKE_CONSOLE_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "generated Atlas projection" in markdown, row["id"]
        assert "authority ceiling" in markdown.lower(), row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert "validation receipts" in markdown, row["id"]
        assert "organ-atlas owner lane" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert (
            payload["generated_projections"]["atlas_card"]["status"]
            == "blocked_until_organ_atlas_owner_lane_binds_edges"
        ), row["id"]


def test_batch7_batch9_pattern_paper_modules_explain_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in BATCH7_BATCH9_PATTERN_CAPSULE_BINDING_IDS
    }

    assert set(rows) == BATCH7_BATCH9_PATTERN_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "generated Atlas projection" in markdown, row["id"]
        assert "authority ceiling" in markdown, row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert "validation receipts" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert (
            payload["generated_projections"]["atlas_card"]["status"]
            == "linked_from_capsule_edges"
        ), row["id"]


def test_work_coordination_paper_modules_explain_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in WORK_COORDINATION_CAPSULE_BINDING_IDS
    }

    assert set(rows) == WORK_COORDINATION_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "generated Atlas projection" in markdown, row["id"]
        assert "authority ceiling" in markdown, row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert "validation receipts" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert payload["generated_projections"]["atlas_card"]["status"] in {
            "blocked_until_organ_atlas_binding_lands",
            "linked_from_capsule_edges",
        }, row["id"]


def test_doctrine_diagnostics_paper_modules_explain_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in DOCTRINE_DIAGNOSTICS_CAPSULE_BINDING_IDS
    }

    assert set(rows) == DOCTRINE_DIAGNOSTICS_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "generated Atlas projection" in markdown, row["id"]
        assert "authority ceiling" in markdown, row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert "validation receipts" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert (
            payload["generated_projections"]["atlas_card"]["status"]
            == "linked_from_capsule_edges"
        ), row["id"]


def test_verifier_prediction_paper_modules_explain_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in VERIFIER_PREDICTION_CAPSULE_BINDING_IDS
    }

    assert set(rows) == VERIFIER_PREDICTION_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "generated Atlas projection" in markdown, row["id"]
        assert "authority ceiling" in markdown, row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert "validation receipts" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert (
            payload["generated_projections"]["atlas_card"]["status"]
            == "linked_from_capsule_edges"
        ), row["id"]


def test_agent_route_runtime_paper_modules_explain_json_capsule_binding() -> None:
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in AGENT_ROUTE_RUNTIME_CAPSULE_BINDING_IDS
    }

    assert set(rows) == AGENT_ROUTE_RUNTIME_CAPSULE_BINDING_IDS

    for row in rows.values():
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        source_ref = payload["source_row"]["source_ref"]

        assert payload["source_authority"] == "json_capsule", row["id"]
        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert "generated Atlas projection" in markdown, row["id"]
        assert "authority ceiling" in markdown, row["id"]
        assert "proof boundary" in markdown, row["id"]
        assert "validation receipts" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]
        assert (
            payload["generated_projections"]["atlas_card"]["status"]
            == "linked_from_capsule_edges"
        ), row["id"]


def test_all_json_capsule_paper_modules_publish_minimum_binding_contract() -> None:
    rows = [
        row
        for row in _paper_module_instances()
        if row["paper_module_payload"]["source_authority"] == "json_capsule"
    ]

    assert rows

    for row in rows:
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        compact_markdown = " ".join(markdown.split())
        source_ref = payload["source_row"]["source_ref"]

        _assert_json_capsule_binding_heading(markdown, row["id"])
        assert source_ref in markdown, row["id"]
        assert "source_authority: json_capsule" in markdown, row["id"]
        assert "This Markdown is a reader projection" in markdown, row["id"]
        assert "generated Mermaid projection" in markdown, row["id"]
        assert (
            "generated Atlas projection" in markdown
            or "Atlas card is linked" in markdown
        ), row["id"]
        assert "authority ceiling" in compact_markdown.lower(), row["id"]
        assert "proof boundary" in compact_markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "available_from_capsule_edges"
        ), row["id"]


def test_generated_projection_status_and_edges_match_source_authority() -> None:
    coverage = _paper_module_coverage()
    capsule_rows = []
    legacy_rows = []

    for row in _paper_module_instances():
        payload = row["paper_module_payload"]
        projections = payload["generated_projections"]
        edges = row["relationships"]["edges"]
        subject_edges = [
            edge
            for edge in edges
            if edge["relation_id"] == "paper_module.explains.organ_or_mechanism"
        ]

        if payload["source_authority"] == "json_capsule":
            capsule_rows.append(row)

            assert row["subjects"], row["id"]
            assert subject_edges, row["id"]
            assert len(edges) >= len(row["subjects"]), row["id"]
            assert projections["mermaid"] == {
                "generated": True,
                "projection_id": f"{row['id']}.mermaid",
                "status": "available_from_capsule_edges",
            }, row["id"]
            assert projections["atlas_card"]["generated"] is True, row["id"]
            assert projections["atlas_card"]["projection_id"].startswith(
                "organ_atlas."
            ), row["id"]
            assert projections["atlas_card"]["status"] in {
                "linked_from_capsule_edges",
                "linked_from_capsule_edges_after_atlas_binding",
                "blocked_until_organ_atlas_owner_lane_binds_edges",
                "blocked_until_organ_atlas_binding_lands",
                "blocked_until_core_organ_atlas_claim_clears",
            }, row["id"]
        elif payload["source_authority"] == "legacy_markdown_projection":
            legacy_rows.append(row)

            assert row["subjects"] == [], row["id"]
            assert edges == [], row["id"]
            assert projections["mermaid"] == {
                "generated": False,
                "projection_id": f"{row['id']}.mermaid",
                "status": "blocked_required_subject_gap",
            }, row["id"]
            assert projections["atlas_card"]["generated"] is False, row["id"]
            assert projections["atlas_card"]["status"] == (
                "blocked_required_subject_gap"
            ), row["id"]
        else:
            raise AssertionError(row["id"])

    assert len(capsule_rows) == coverage["json_capsule_backed_count"]
    assert len(legacy_rows) == coverage["legacy_only_count"]
    assert {row["id"] for row in legacy_rows} == set(
        coverage["required_subject_gap_ids"]
    )


def test_legacy_reentry_worklist_is_coverage_driven() -> None:
    legacy_ids = set(_legacy_instance_rows())
    coverage_legacy_ids = _coverage_legacy_ids()

    assert legacy_ids == coverage_legacy_ids


def test_microcosm_axiom_substrate_capsule_preserves_claim_ceiling_source_route() -> None:
    capsules = {row["id"]: row for row in _paper_module_capsules()}
    instances = {row["id"]: row for row in _paper_module_instances()}
    capsule = capsules["paper_module.microcosm_axiom_substrate"]
    instance = instances["paper_module.microcosm_axiom_substrate"]
    source_row = instance["paper_module_payload"]["source_row"]
    authority_texts = [
        capsule["compression"]["authority_ceiling"],
        capsule["strangler_note"],
        instance["compression"]["authority_ceiling"],
        source_row["compression"]["authority_ceiling"],
        source_row["strangler_note"],
    ]

    for text in authority_texts:
        assert "core/axiom_organ_routing.json" in text
        assert "validator.microcosm.axiom_support_cover" in text
        assert "claim_ceiling" in text
        assert "strongest_allowed_claim" in text
        assert "hand-stamped" in text


def test_coverage_legacy_rows_publish_cold_reader_boundary_markers() -> None:
    coverage_legacy_ids = _skip_when_legacy_projection_drifted()
    rows = {row["id"]: row for row in _paper_module_instances()}

    for row_id in sorted(coverage_legacy_ids):
        row = rows[row_id]
        payload = row["paper_module_payload"]
        projections = payload["generated_projections"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        compact_markdown = " ".join(markdown.split())

        assert payload["source_authority"] == "legacy_markdown_projection", row_id
        assert row["subjects"] == [], row_id
        assert row["relationships"]["edges"] == [], row_id
        assert projections["mermaid"]["status"] == (
            "blocked_required_subject_gap"
        ), row_id
        assert projections["atlas_card"]["status"] == (
            "blocked_required_subject_gap"
        ), row_id
        assert "## JSON Capsule Boundary" in markdown, row_id
        assert "## Reader Proof Boundary" in markdown, row_id
        assert "## Capsule Re-entry Packet" in markdown, row_id
        assert "paper_module_payload.source_authority" in markdown, row_id
        assert "legacy_markdown_projection" in markdown, row_id
        assert "Mermaid `blocked_required_subject_gap`" in markdown, row_id
        assert "Atlas `blocked_required_subject_gap`" in markdown, row_id
        assert "`core/paper_module_capsules.json`" in markdown, row_id
        assert "scripts/build_doctrine_projection.py" in markdown, row_id
        assert "--write-paper-module-corpus" in markdown, row_id
        assert "must not invent a subject row yet" in compact_markdown, row_id
        assert "proof boundary" in compact_markdown, row_id
        assert "exact re-entry condition" in compact_markdown, row_id
        assert "without claiming JSON capsule authority" in compact_markdown, row_id


def test_legacy_paper_modules_explain_json_capsule_boundary() -> None:
    _skip_when_legacy_projection_drifted()
    legacy_rows = list(_legacy_instance_rows().values())

    for row in legacy_rows:
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")

        assert "## JSON Capsule Boundary" in markdown, row["id"]
        assert "legacy Markdown projection" in markdown, row["id"]
        assert "JSON-capsule-backed" in markdown, row["id"]
        assert "`core/paper_module_capsules.json`" in markdown, row["id"]
        assert "scripts/build_doctrine_projection.py" in markdown, row["id"]
        assert "--write-paper-module-corpus" in markdown, row["id"]
        assert "Mermaid" in markdown, row["id"]
        assert "Atlas" in markdown, row["id"]
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "blocked_required_subject_gap"
        ), row["id"]


def test_tactic_portfolio_probe_markdown_is_capsule_owned_alias_not_legacy_row() -> None:
    coverage = _paper_module_coverage()
    rows = _paper_module_instances()
    row_ids = {row["id"] for row in rows}
    capsules = _paper_module_capsules()
    tactic_capsule = next(
        row
        for row in capsules
        if row["id"] == "paper_module.tactic_portfolio_availability"
    )

    assert "paper_module.tactic_portfolio_availability_probe" not in row_ids
    assert "paper_module.tactic_portfolio_availability_probe" not in set(
        coverage["legacy_only_ids"]
    )
    assert "paper_module.tactic_portfolio_availability_probe" not in set(
        coverage["required_subject_gap_ids"]
    )
    assert not (
        MICROCOSM_ROOT / "paper_modules/tactic_portfolio_availability_probe.json"
    ).exists()
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


def test_all_legacy_subject_gap_modules_publish_reentry_packets() -> None:
    _skip_when_legacy_projection_drifted()
    legacy_rows = list(_legacy_instance_rows().values())

    for row in legacy_rows:
        payload = row["paper_module_payload"]
        projections = payload["generated_projections"]
        mermaid_status = projections["mermaid"]["status"]
        atlas_status = projections["atlas_card"]["status"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        compact_markdown = " ".join(markdown.split())
        source_locus = LEGACY_REENTRY_LOCI[row["id"]]

        assert "## JSON Capsule Boundary" in markdown, row["id"]
        assert "## Capsule Re-entry Packet" in markdown, row["id"]
        assert mermaid_status == "blocked_required_subject_gap", row["id"]
        assert atlas_status == "blocked_required_subject_gap", row["id"]
        assert "paper_module_payload.source_authority:" in compact_markdown, (
            row["id"]
        )
        assert "legacy_markdown_projection" in compact_markdown, row["id"]
        assert f"Mermaid `{mermaid_status}`" in markdown, row["id"]
        assert f"Atlas `{atlas_status}`" in markdown, row["id"]
        assert any(
            f"{label}: `{source_locus}`" in compact_markdown
            for label in ("resolved code locus", "resolved source locus")
        ), row["id"]
        assert "must not invent a subject row yet" in compact_markdown, row["id"]
        assert f"append `{row['id']}` to" in compact_markdown, row["id"]
        assert "`core/paper_module_capsules.json`" in markdown, row["id"]
        assert "--write-paper-module-corpus" in markdown, row["id"]
        assert "verify" in compact_markdown, row["id"]
        assert "Mermaid" in compact_markdown, row["id"]
        assert "Atlas" in compact_markdown, row["id"]
        assert "aggregate doctrine-lattice coverage" in markdown, row["id"]


def test_legacy_projection_rows_sync_machine_boundary_with_markdown() -> None:
    _skip_when_legacy_projection_drifted()
    legacy_rows = list(_legacy_instance_rows().values())

    for row in legacy_rows:
        payload = row["paper_module_payload"]
        projections = payload["generated_projections"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        compact_markdown = " ".join(markdown.split()).lower()
        source_ref = payload["source_row"]["source_ref"]

        assert row["authority_boundary"] == (
            "legacy_markdown_indexed_as_governed_json_import_without_"
            "capsule_authority"
        ), row["id"]
        assert source_ref == payload["legacy_markdown_projection"], row["id"]
        assert source_ref in markdown, row["id"]
        assert (
            payload["projection_contract"]["authority_flip_status"]
            == "not_flipped"
        ), row["id"]
        assert payload["projection_contract"]["markdown_status"] == (
            "legacy_import_projection_until_roundtrip_builder"
        ), row["id"]
        assert payload["support_contract"]["support_status"] == (
            "legacy_markdown_path_indexed_required_subject_gap"
        ), row["id"]
        assert projections["markdown"]["generated"] is False, row["id"]
        assert projections["markdown"]["path"] == payload[
            "legacy_markdown_projection"
        ], row["id"]
        assert projections["markdown"]["status"] == (
            "legacy_markdown_projection_not_generated_from_json"
        ), row["id"]
        assert "proof boundary" in compact_markdown, row["id"]


def test_legacy_reentry_source_loci_resolve_on_disk() -> None:
    _skip_when_legacy_projection_drifted()
    rows = _legacy_instance_rows()

    for row_id in sorted(rows):
        source_locus = LEGACY_REENTRY_LOCI[row_id]
        assert not source_locus.startswith("/"), row_id

        source_path = MICROCOSM_ROOT / source_locus
        assert source_path.is_file(), row_id
        assert source_path.read_text(encoding="utf-8").strip(), row_id


def test_engine_room_legacy_modules_publish_capsule_reentry_packets() -> None:
    coverage_legacy_ids = _skip_when_legacy_projection_drifted()
    expected_ids = set(ENGINE_ROOM_LEGACY_REENTRY_LOCI) & coverage_legacy_ids
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in expected_ids
    }

    assert set(rows) == expected_ids

    for row_id in sorted(expected_ids):
        source_locus = ENGINE_ROOM_LEGACY_REENTRY_LOCI[row_id]
        row = rows[row_id]
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        compact_markdown = " ".join(markdown.split())

        assert payload["source_authority"] == "legacy_markdown_projection", row_id
        assert "## Capsule Re-entry Packet" in markdown, row_id
        assert source_locus in markdown, row_id
        assert "paper_module_payload.source_authority" in markdown, row_id
        assert "legacy_markdown_projection" in markdown, row_id
        assert "Mermaid `blocked_required_subject_gap`" in markdown, row_id
        assert "Atlas `blocked_required_subject_gap`" in markdown, row_id
        assert "must not invent a subject row yet" in compact_markdown, row_id
        assert f"append `{row_id}` to" in compact_markdown, row_id
        assert "--write-paper-module-corpus" in markdown, row_id
        assert "aggregate doctrine-lattice coverage" in markdown, row_id
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "blocked_required_subject_gap"
        ), row_id
        assert (
            payload["generated_projections"]["atlas_card"]["status"]
            == "blocked_required_subject_gap"
        ), row_id


def test_engine_room_legacy_modules_publish_reader_proof_boundaries() -> None:
    coverage_legacy_ids = _skip_when_legacy_projection_drifted()
    expected_ids = set(ENGINE_ROOM_LEGACY_REENTRY_LOCI) & coverage_legacy_ids
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in expected_ids
    }

    assert set(rows) == expected_ids

    for row_id in sorted(expected_ids):
        source_locus = ENGINE_ROOM_LEGACY_REENTRY_LOCI[row_id]
        row = rows[row_id]
        payload = row["paper_module_payload"]
        projections = payload["generated_projections"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        compact_markdown = " ".join(markdown.split())

        assert payload["source_authority"] == "legacy_markdown_projection", row_id
        assert "## Reader Proof Boundary" in markdown, row_id
        assert (
            "public reader projection over a staged Engine Room exercise"
            in compact_markdown
        ), row_id
        assert (
            "`paper_module_payload.source_authority: "
            "legacy_markdown_projection`"
        ) in markdown, row_id
        assert projections["mermaid"]["status"] == (
            "blocked_required_subject_gap"
        ), row_id
        assert projections["atlas_card"]["status"] == (
            "blocked_required_subject_gap"
        ), row_id
        assert (
            "Mermaid and Atlas projections must remain "
            "`blocked_required_subject_gap`"
        ) in compact_markdown, row_id
        assert "current source locus" in compact_markdown, row_id
        assert source_locus in markdown, row_id
        assert "exact re-entry condition" in compact_markdown, row_id
        assert "without claiming JSON capsule authority" in compact_markdown, row_id


def test_engine_room_legacy_modules_publish_validation_receipt_paths() -> None:
    coverage_legacy_ids = _skip_when_legacy_projection_drifted()
    expected_ids = set(ENGINE_ROOM_LEGACY_VALIDATION_TESTS) & coverage_legacy_ids
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in expected_ids
    }

    assert set(rows) == expected_ids

    for row_id in sorted(expected_ids):
        test_path = ENGINE_ROOM_LEGACY_VALIDATION_TESTS[row_id]
        row = rows[row_id]
        payload = row["paper_module_payload"]
        projections = payload["generated_projections"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        compact_markdown = " ".join(markdown.split())

        assert payload["source_authority"] == "legacy_markdown_projection", row_id
        assert "## Validation Receipt Path" in markdown, row_id
        assert test_path in markdown, row_id
        assert "--check-paper-module-corpus" in markdown, row_id
        assert "reader-verifiable receipt" in compact_markdown, row_id
        assert "does not flip Mermaid/Atlas status" in compact_markdown, row_id
        assert "create capsule authority" in compact_markdown, row_id
        assert projections["mermaid"]["status"] == (
            "blocked_required_subject_gap"
        ), row_id
        assert projections["atlas_card"]["status"] == (
            "blocked_required_subject_gap"
        ), row_id


def test_non_engine_room_legacy_modules_publish_capsule_reentry_packets() -> None:
    coverage_legacy_ids = _skip_when_legacy_projection_drifted()
    expected_ids = set(NON_ENGINE_ROOM_LEGACY_REENTRY_LOCI) & coverage_legacy_ids
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in expected_ids
    }

    assert set(rows) == expected_ids

    for row_id in sorted(expected_ids):
        source_locus = NON_ENGINE_ROOM_LEGACY_REENTRY_LOCI[row_id]
        row = rows[row_id]
        payload = row["paper_module_payload"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        compact_markdown = " ".join(markdown.split())

        assert payload["source_authority"] == "legacy_markdown_projection", row_id
        assert "## Capsule Re-entry Packet" in markdown, row_id
        assert source_locus in markdown, row_id
        assert "paper_module_payload.source_authority" in markdown, row_id
        assert "legacy_markdown_projection" in markdown, row_id
        assert "Mermaid `blocked_required_subject_gap`" in markdown, row_id
        assert "Atlas `blocked_required_subject_gap`" in markdown, row_id
        assert "must not invent a subject row yet" in compact_markdown, row_id
        assert f"append `{row_id}` to" in compact_markdown, row_id
        assert "--write-paper-module-corpus" in markdown, row_id
        assert "aggregate doctrine-lattice coverage" in markdown, row_id
        assert (
            payload["generated_projections"]["mermaid"]["status"]
            == "blocked_required_subject_gap"
        ), row_id
        assert (
            payload["generated_projections"]["atlas_card"]["status"]
            == "blocked_required_subject_gap"
        ), row_id


def test_non_engine_room_legacy_modules_publish_reader_proof_boundaries() -> None:
    coverage_legacy_ids = _skip_when_legacy_projection_drifted()
    expected_ids = set(NON_ENGINE_ROOM_LEGACY_REENTRY_LOCI) & coverage_legacy_ids
    rows = {
        row["id"]: row
        for row in _paper_module_instances()
        if row["id"] in expected_ids
    }

    assert set(rows) == expected_ids

    for row_id in sorted(expected_ids):
        source_locus = NON_ENGINE_ROOM_LEGACY_REENTRY_LOCI[row_id]
        row = rows[row_id]
        payload = row["paper_module_payload"]
        projections = payload["generated_projections"]
        markdown_path = MICROCOSM_ROOT / payload["legacy_markdown_projection"]
        markdown = markdown_path.read_text(encoding="utf-8")
        compact_markdown = " ".join(markdown.split())

        assert payload["source_authority"] == "legacy_markdown_projection", row_id
        assert "## Reader Proof Boundary" in markdown, row_id
        assert (
            "public reader projection over a legacy microcosm paper-module row"
            in compact_markdown
        ), row_id
        assert (
            "`paper_module_payload.source_authority: "
            "legacy_markdown_projection`"
        ) in markdown, row_id
        assert projections["mermaid"]["status"] == (
            "blocked_required_subject_gap"
        ), row_id
        assert projections["atlas_card"]["status"] == (
            "blocked_required_subject_gap"
        ), row_id
        assert (
            "Mermaid and Atlas projections must remain "
            "`blocked_required_subject_gap`"
        ) in compact_markdown, row_id
        assert "current source locus" in compact_markdown, row_id
        assert "generated row source ref" in compact_markdown, row_id
        assert source_locus in markdown, row_id
        assert "exact re-entry condition" in compact_markdown, row_id
        assert "without claiming JSON capsule authority" in compact_markdown, row_id


def test_plectis_paper_module_coverage_contract_is_projected_into_modules() -> None:
    entry_lattice = (
        REPO_ROOT / "codex/doctrine/paper_modules/plectis_entry_lattice.md"
    ).read_text(encoding="utf-8")
    product_roof = (
        REPO_ROOT / "codex/doctrine/paper_modules/plectis_substrate.md"
    ).read_text(encoding="utf-8")
    public_export_bridge = (
        REPO_ROOT
        / "codex/doctrine/paper_modules/plectis_public_export_type_plane.md"
    ).read_text(encoding="utf-8")
    runtime_organ_atlas = (
        REPO_ROOT
        / "codex/doctrine/paper_modules/plectis_runtime_organ_atlas.md"
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
        "plectis_public_export_type_plane",
        "plectis_runtime_organ_atlas",
        "runtime organ source-loci",
        "paper_module_coverage_metabolism",
        "paper_module_entry_projection_integrity",
        "generated sidecars",
        "supporting route-lattice modules",
        "module_depth_roles",
        "All-Paper-Module Compression Ladder",
        "all paper modules in compressed form",
        "paper_module_coverage_contract.all_corpus_compression_dispatch",
        "all_corpus_compression_dispatch",
        "paper_module_coverage_contract.cluster_digest_contract",
        "cluster_digest_contract",
        "summary.cluster_currentness",
        "summary.cluster_semantics",
        "summary.cluster_authority_distribution",
        "cluster_omission_receipt",
        "rows[].cluster_id",
        "rows[].cluster_source_axis",
        "rows[].top_ids",
        "rows[].governing_counts",
        "rows[].drilldown_command",
        './repo-python kernel.py --entry "<task>" --context-budget 12000',
        'AIW_CONTEXT_PACK_DISABLE_SEMANTIC=1 ./repo-python kernel.py --context-pack "<task>" --context-budget 12000',
        "--option-surface paper_modules --band cluster_flag",
        "--option-surface standards --band card --ids std_microcosm",
        "--option-surface navigation_type_plane --band card --ids public_plectis_exports",
        "--paper-module-coverage",
        "selected_depth_slice",
        "context_pack_budget_honesty_contract",
        "budget.contract_status",
        "budget.over_budget",
        "budget.hard_ceiling_repair_status",
        "budget.routine_selected_row_economy.status",
        "budget.routine_economy_effective_ceiling_tokens",
        "navigation_index_spine.entry_intent_openings.task_conditioned.reentry_receipt.status",
        "all-row `flag` is compatibility",
        "system/lib/standard_option_surface.py::_paper_module_cluster_rows",
        "system/lib/standard_option_surface.py::_paper_module_cluster_key",
        "system/lib/standard_option_surface.py::_paper_module_cluster_authority_summary",
        "system/lib/standard_option_surface.py::build_option_surface",
        "system/lib/standard_option_surface.py::_paper_module_compression_packet",
        "system/lib/standard_option_surface.py::_paper_module_compression_passport",
        "system/lib/navigation_context_pack.py::PLECTIS_PAPER_MODULE_DEPTH_ANCHORS",
        "system/lib/navigation_context_pack.py::BUDGET_TRIM_PROTECTED_ROWS",
        "system/lib/navigation_context_pack.py::_budget_trim",
        "hard_ceiling_selected_row_handles",
        "system/lib/navigation_index_spine.py::ENTRY_INTENT_SPECS",
        "system/lib/navigation_coverage_matrix.py::build_coverage_enforcement_matrix",
        "system/server/tests/test_navigation_context_pack.py::test_context_pack_navigation_spine_long_query_stays_under_budget",
        "system/server/tests/test_navigation_context_pack.py::test_context_pack_cli_emits_budgeted_json",
        "generated_sidecar_closeout_rule",
        "do not commit generated paper-module sidecars or System Atlas outputs",
        "all_corpus_compression_navigation_only_not_source_truth_release_permission_proof_correctness_or_candidate_axiom_authority",
        "context_pack_budget_honesty_only_not_source_truth_release_permission_proof_correctness_or_candidate_axiom_authority",
        "handoff sequence",
        "context-pack selected row order",
        "context-pack next command order",
        "source_loci_depth_contract",
        "runtime organ atlas",
        "atlas_source_coupling_closeout_contract",
        "System Atlas source-coupling",
        "build_system_atlas.py --check",
        "stale_source_coupling",
        "100% paper-module coverage means every authored module is routed, current, and drilldown-visible",
        "plectis_paper_module_depth",
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
        "standard-backed role edge to `plectis_runtime_organ_atlas` and "
        "the direct dependency edges to `paper_module_coverage_metabolism` and "
        "`paper_module_entry_projection_integrity`"
    ) in entry_lattice
    assert "runtime source-loci depth" in entry_lattice
    assert "entry/count honesty as required depth rungs" in entry_lattice
    assert "Verify paper-module coverage/depth" in entry_lattice
    assert "Verify entry/count honesty" in entry_lattice
    assert "Route public Plectis exports" in entry_lattice
    assert "Verify runtime organ source-loci depth" in entry_lattice
    assert "Verify paper-module coverage without bloating this roof" in product_roof
    assert "plectis_runtime_organ_atlas" in product_roof
    assert "Inspect runtime organ source-loci depth" in product_roof
    assert "paper_module_coverage_contract.module_depth_roles" in product_roof
    assert "paper_module_entry_projection_integrity" in product_roof
    assert "entry/count honesty" in product_roof
    assert "sidecars as source truth" in product_roof
    assert "first-screen <project>` emits the JSON one-screen reader map" in product_roof
    assert "Source-Loci Depth Contract" in product_roof
    assert "Atlas source-coupling closeout" in product_roof
    assert "paper_module_coverage_contract.atlas_source_coupling_closeout_contract" in product_roof
    assert "build_system_atlas.py --check" in product_roof
    assert "navigation_index_spine.currentness.status" in product_roof
    assert "microcosm_core/cli.py::main" in product_roof
    assert "microcosm_core/first_screen_composition.py::first_screen_composition_card" in product_roof
    assert "microcosm_core/project_substrate.py::compile_project" in product_roof
    assert "microcosm_core/runtime_shell.py::RuntimeShell" in product_roof
    assert "microcosm_core/validators/public_entry_docs.py::_entry_packet_route_contract" in product_roof
    assert "paper_module_coverage_contract.source_loci_depth_contract" in product_roof
    assert "test_plectis_paper_module_coverage_contract.py::" in product_roof
    assert "runtime truth belongs to these loci" in product_roof
    assert "entry-packet paper-module ref classification" in public_export_bridge
    assert "primary/support module taxonomy" in public_export_bridge
    assert "module depth roles" in public_export_bridge
    assert "type-plane row consumer" in public_export_bridge
    assert "plectis_runtime_organ_atlas" in public_export_bridge
    assert "entry-depth freshness binding" in public_export_bridge
    assert "paper_module_coverage_contract.source_loci_depth_contract" in public_export_bridge
    assert (
        "paper_module_coverage_contract.atlas_source_coupling_closeout_contract"
        in public_export_bridge
    )
    assert "Atlas source-coupling closeout" in public_export_bridge
    assert "source-loci depth" in public_export_bridge
    assert (
        "`public_plectis_exports` opens this bridge before generated public files"
        in public_export_bridge
    )
    assert "runtime organ source-loci depth" in public_export_bridge
    assert "focused coverage regression" in public_export_bridge
    assert "All-Corpus Export Dispatch" in public_export_bridge
    assert (
        "--option-surface paper_modules --band cluster_flag"
        in public_export_bridge
    )
    assert (
        "system/lib/standard_option_surface.py::_paper_module_cluster_rows"
        in public_export_bridge
    )
    assert (
        "system/lib/standard_option_surface.py::_paper_module_compression_packet"
        in public_export_bridge
    )
    assert (
        "system/lib/standard_option_surface.py::_paper_module_compression_passport"
        in public_export_bridge
    )
    assert (
        "system/lib/navigation_context_pack.py::PLECTIS_PAPER_MODULE_DEPTH_ANCHORS"
        in public_export_bridge
    )
    assert "system/lib/navigation_index_spine.py::ENTRY_INTENT_SPECS" in (
        public_export_bridge
    )
    assert (
        "system/lib/navigation_coverage_matrix.py::build_coverage_enforcement_matrix"
        in public_export_bridge
    )
    assert "Dirty Generated-Sidecar Boundary" in public_export_bridge
    assert (
        "do not commit generated paper-module sidecars or System Atlas outputs"
        in public_export_bridge
    )
    assert "Runtime Organ Families" in runtime_organ_atlas
    assert "microcosm-substrate/src/microcosm_core/cli.py::main" in runtime_organ_atlas
    assert "microcosm-substrate/src/microcosm_core/project_substrate.py::compile_project" in runtime_organ_atlas
    assert "microcosm-substrate/src/microcosm_core/runtime_shell.py::RuntimeShell" in runtime_organ_atlas
    assert "microcosm-substrate/src/microcosm_core/validators/public_entry_docs.py::_entry_packet_route_contract" in runtime_organ_atlas
    assert "microcosm-substrate/src/microcosm_core/organs/formal_math_premise_retrieval.py" in runtime_organ_atlas
    assert "microcosm-substrate/tests/test_formal_math_premise_retrieval.py" in runtime_organ_atlas
    assert "Entry and Atlas Integration" in runtime_organ_atlas
    assert "runtime_organ_source_loci" in runtime_organ_atlas
    assert "paper_module_entry_projection_integrity" in public_export_bridge
    assert "entry/count projection integrity" in public_export_bridge
    assert "plectis_paper_module_depth" in coverage_metabolism
    assert "plectis_runtime_organ_atlas" in coverage_metabolism
    assert "navigation_type_plane" in coverage_metabolism
    assert "cognitive_operators" in coverage_metabolism
    assert "All-Corpus Compression Dispatch" in coverage_metabolism
    assert "Typed Cluster Digest Contract" in coverage_metabolism
    assert "std_microcosm.json::paper_module_coverage_contract.cluster_digest_contract" in coverage_metabolism
    assert "summary.cluster_currentness" in coverage_metabolism
    assert "summary.cluster_semantics" in coverage_metabolism
    assert "summary.cluster_authority_distribution" in coverage_metabolism
    assert "cluster_omission_receipt" in coverage_metabolism
    assert "rows[].cluster_id" in coverage_metabolism
    assert "rows[].cluster_source_axis" in coverage_metabolism
    assert "rows[].top_ids" in coverage_metabolism
    assert "rows[].governing_counts" in coverage_metabolism
    assert "rows[].drilldown_command" in coverage_metabolism
    assert (
        "system/lib/standard_option_surface.py::_paper_module_cluster_key"
        in coverage_metabolism
    )
    assert (
        "system/lib/standard_option_surface.py::_paper_module_cluster_authority_summary"
        in coverage_metabolism
    )
    assert "all-row `flag` remains a compatibility redirect" in coverage_metabolism
    assert "context_pack_budget_honesty_contract" in coverage_metabolism
    assert "budget.contract_status" in coverage_metabolism
    assert "budget.over_budget" in coverage_metabolism
    assert "system/lib/navigation_context_pack.py::BUDGET_TRIM_PROTECTED_ROWS" in coverage_metabolism
    assert "system/lib/navigation_context_pack.py::_budget_trim" in coverage_metabolism
    assert "hard_ceiling_selected_row_handles" in coverage_metabolism
    assert (
        "system/server/tests/test_navigation_context_pack.py::"
        "test_context_pack_navigation_spine_long_query_stays_under_budget"
        in coverage_metabolism
    )
    assert (
        "system/server/tests/test_navigation_context_pack.py::"
        "test_context_pack_cli_emits_budgeted_json"
        in coverage_metabolism
    )
    assert (
        "system/lib/standard_option_surface.py::_paper_module_cluster_rows"
        in coverage_metabolism
    )
    assert (
        "system/lib/standard_option_surface.py::_paper_module_compression_packet"
        in coverage_metabolism
    )
    assert (
        "system/lib/standard_option_surface.py::_paper_module_compression_passport"
        in coverage_metabolism
    )
    assert "Dirty Generated-Sidecar Boundary" in coverage_metabolism
    assert (
        "`README.md`, `_index.json`, `_validation_report.json`, "
        "`_route_coverage.json`, and `_doctrine_to_paper_modules.json`"
        in coverage_metabolism
    )
    assert (
        "the correct closeout is not to commit generated sidecars"
        in coverage_metabolism
    )
    assert "Source-Loci Coverage Contract" in coverage_metabolism
    assert "Atlas Source-Coupling Closeout" in coverage_metabolism
    assert "std_microcosm.json::paper_module_coverage_contract.atlas_source_coupling_closeout_contract" in coverage_metabolism
    assert "system/lib/navigation_index_spine.py::_system_atlas_currentness" in coverage_metabolism
    assert "source_coupling.safe_to_commit_generated_outputs_without_sources" in coverage_metabolism
    assert "tools/meta/factory/build_paper_module_index.py::main" in coverage_metabolism
    assert "system/lib/paper_modules.py::build_route_coverage" in coverage_metabolism
    assert (
        "system/lib/kernel/commands/navigate.py::cmd_paper_module_coverage"
        in coverage_metabolism
    )
    assert (
        "system/lib/kernel_navigation.py::KernelNavigation.build_paper_module_route_coverage"
        in coverage_metabolism
    )
    assert "system/lib/standard_option_surface.py::build_option_surface" in coverage_metabolism
    assert "system/lib/navigation_index_spine.py::ENTRY_INTENT_SPECS" in coverage_metabolism
    assert (
        "system/lib/navigation_context_pack.py::PLECTIS_PAPER_MODULE_DEPTH_ANCHORS"
        in coverage_metabolism
    )
    assert (
        "system/lib/navigation_context_pack.py::_is_plectis_paper_module_depth_query"
        in coverage_metabolism
    )
    assert "std_microcosm.json::paper_module_coverage_contract.source_loci_depth_contract" in coverage_metabolism
    assert "System Atlas Source-Coupling Closeout" in entry_projection_integrity
    assert "Typed Cluster Digest Contract" in entry_projection_integrity
    assert "std_microcosm.json::paper_module_coverage_contract.cluster_digest_contract" in entry_projection_integrity
    assert "summary.cluster_currentness.index_freshness" in entry_projection_integrity
    assert "summary.cluster_authority_distribution" in entry_projection_integrity
    assert "cluster_omission_receipt" in entry_projection_integrity
    assert "rows[].cluster_id" in entry_projection_integrity
    assert "rows[].cluster_source_axis" in entry_projection_integrity
    assert "rows[].top_ids" in entry_projection_integrity
    assert "rows[].drilldown_command" in entry_projection_integrity
    assert (
        "system/lib/standard_option_surface.py::_paper_module_cluster_key"
        in entry_projection_integrity
    )
    assert (
        "system/lib/standard_option_surface.py::_paper_module_cluster_authority_summary"
        in entry_projection_integrity
    )
    assert "tools/meta/factory/build_system_atlas.py::main" in entry_projection_integrity
    assert "system/lib/navigation_index_spine.py::_system_atlas_source_coupling" in entry_projection_integrity
    assert "system/lib/kind_atlas.py::_system_atlas_currentness" in entry_projection_integrity
    assert "explicit Plectis consumers" in entry_projection_integrity
    assert "plectis_public_export_type_plane" in entry_projection_integrity
    assert "plectis_runtime_organ_atlas" in entry_projection_integrity
    assert "entry/count projection honesty contract" in entry_projection_integrity
    assert "Context-Pack Budget-Honesty Gate" in entry_projection_integrity
    assert "context_pack_budget_honesty_contract" in entry_projection_integrity
    assert "budget.contract_status == within_budget" in entry_projection_integrity
    assert "budget.over_budget == true" in entry_projection_integrity
    assert "system/lib/navigation_context_pack.py::BUDGET_TRIM_PROTECTED_ROWS" in entry_projection_integrity
    assert "system/lib/navigation_context_pack.py::_budget_trim" in entry_projection_integrity
    assert "hard_ceiling_selected_row_handles" in entry_projection_integrity


def test_public_plectis_exports_type_plane_row_has_paper_module_bridge() -> None:
    standard = _std_microcosm()
    bridge = standard["paper_module_coverage_contract"]["standard_type_plane_bridge"]
    type_plane = _std_standard_type_plane()
    row = next(
        row
        for row in type_plane["type_plane_rows"]
        if row["type_id"] == "public_plectis_exports"
    )

    assert bridge["paper_module"] in row["governing_standard_refs"]
    assert bridge["paper_module"] in row["projection_refs"]
    assert (
        "codex/doctrine/paper_modules/plectis_runtime_organ_atlas.md"
        in row["governing_standard_refs"]
    )
    assert (
        "codex/doctrine/paper_modules/plectis_runtime_organ_atlas.md"
        in row["projection_refs"]
    )
    assert row["entry_depth_contract"]["standard_bridge"] == (
        "codex/standards/std_microcosm.json::"
        "paper_module_coverage_contract.standard_type_plane_bridge"
    )
    assert row["entry_depth_contract"]["paper_module_depth_order"] == [
        "plectis_substrate",
        "plectis_entry_lattice",
        "plectis_public_export_type_plane",
        "plectis_runtime_organ_atlas",
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
        "laboratory_metabolism",
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
        "--ids public_plectis_exports"
    )
    assert "plectis paper module depth" in row["compression_passport"][
        "cluster_keys"
    ]
    assert "generated public export files only after behavior proof" in (
        row["entry_depth_contract"]["export_depth_rule"]
    )
    assert "--entry" in row["entry_depth_contract"]["control_entry"]
    assert any(
        "plectis_public_export_type_plane" in probe
        for probe in row["validation_probe"]
    )
