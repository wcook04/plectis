"""Build idea-first navigation projections for the release microcosm.

[PURPOSE]
Generate atlas, entry packet, and cards that route agents from ideas to evidence.

[INTERFACE]
Exports build_navigation plus small query surfaces for release-local validation flows.

[FLOW]
Load the idea graph, write card projections, and emit atlas and entry-packet JSON.

[DEPENDENCIES]
Uses JSON state, pathlib, regex slugging, and public-safe idea graph rows.

[CONSTRAINTS]
Generated navigation is a projection; source authority remains in state/idea_graph.json.
- When-needed: Open when a task needs the release microcosm's first-hop atlas, entry packet, or idea card generation path.
- Escalates-to: navigation/entry_packet.json; navigation/atlas.json; src/idea_microcosm/release_root_compiler.py::build_std_python_report
- Navigation-group: microcosm_navigation_projection
- Validator: validator.projection_preservation; validator.artifact_manifest
- Receipt: receipts/validation_run.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Sequence

LEAF_ENTRY_CARD_BEGIN = "<!-- BEGIN leaf_entry_card -->"
LEAF_ENTRY_CARD_END = "<!-- END leaf_entry_card -->"
TELEOLOGY_GATE_PATH = Path("strategy/microcosm_teleology_gate.json")
SANDBOX_GATE_PATH = Path("sandbox/microcosm_sandbox_gate.json")


def _safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def _optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _retired_leaf_ids(root: Path) -> set[str]:
    gate = _optional_json(root / TELEOLOGY_GATE_PATH)
    return {str(value) for value in gate.get("retired_leaf_ids", []) if isinstance(value, str)}


def _active_leaf_rows(root: Path, contract: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    retired_ids = _retired_leaf_ids(root)
    active_rows: list[dict[str, Any]] = []
    retired_seen: list[str] = []
    for row in contract.get("leaf_rows", []) or []:
        if not isinstance(row, dict) or not row.get("leaf_id"):
            continue
        leaf_id = str(row["leaf_id"])
        if leaf_id in retired_ids:
            retired_seen.append(leaf_id)
            continue
        active_rows.append(row)
    return active_rows, sorted(retired_seen)


def _card(idea: dict[str, Any]) -> str:
    lines = [
        f"# `{idea['id']}`",
        "",
        "Projection, not authority. Source authority: `state/idea_graph.json`.",
        "",
        idea["claim"],
        "",
        f"- Type: `{idea['type']}`",
        f"- Standards: {', '.join(f'`{item}`' for item in idea.get('standard_refs', []))}",
        f"- Validators: {', '.join(f'`{item}`' for item in idea.get('validators', []))}",
        f"- Next moves: {', '.join(f'`{item}`' for item in idea.get('next_moves', []))}",
        f"- Deliverables: {', '.join(f'`{item}`' for item in idea.get('deliverable_refs', []))}",
        "",
        "Omissions:",
    ]
    lines.extend(f"- {item}" for item in idea.get("omissions", []))
    lines.append("")
    return "\n".join(lines)


EXOGENOUS_AGENT_ENTRY_MODES: list[dict[str, Any]] = [
    {
        "mode_id": "orientation_reader",
        "when": "A cold human or agent needs the thesis, boundaries, and safest first proof.",
        "route": [
            "AGENTS.md",
            "strategy/seed.md",
            "strategy/microcosm_teleology_gate.json",
            "strategy/microcosm_reconstruction_posture.json",
            "sandbox/microcosm_sandbox_gate.json",
            "navigation/entry_packet.json",
            "navigation/microcosm_index.json",
            "microcosms/leaf_entry_contract.json",
            "microcosms/summary_ladders/summary_ladders.json",
        ],
        "success_check": "Can state the core claim and name one receipt-backed reviewer route without opening private context.",
        "stop_rule": "Stop before editing or strengthening claims.",
    },
    {
        "mode_id": "claim_verifier",
        "when": "A reviewer wants to test whether a public claim is supported.",
        "route": [
            "AGENTS.md",
            "navigation/microcosm_index.json",
            "microcosms/summary_ladders/summary_ladders.json",
            "PYTHONPATH=src python3 -m idea_microcosm.cli query-route-composition --root . --band cluster_flag",
            "selected route card",
            "selected route receipt refs",
            "release/publication_gate.json when the claim concerns publication or hosted-public posture",
        ],
        "success_check": "Every stronger claim cites a receipt, validator, and anti-claim boundary.",
        "stop_rule": "Do not treat a local pass as hosted-public readiness or publication approval.",
    },
    {
        "mode_id": "leaf_editor",
        "when": "An external repo agent is changing one mechanism leaf.",
        "route": [
            "AGENTS.md",
            "PYTHONPATH=src python3 -m idea_microcosm.cli query-entry-routes --root . --band card --ids entry_route.leaf_editor",
            "PYTHONPATH=src python3 -m idea_microcosm.cli query-route-composition --root . --band card --ids route_surface.leaf_code_routes",
            "selected leaf README",
            "microcosms/leaf_entry_contract.json::leaf_rows[leaf_id=<leaf_id>]",
            "selected leaf builder command",
            "selected receipt",
            "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
        ],
        "success_check": "Patch stays inside one leaf or its owning builder and validation stays green.",
        "stop_rule": "If a file is added or removed, rebuild the artifact manifest before final claims.",
    },
    {
        "mode_id": "concurrent_editor",
        "when": "Multiple agents or humans may be editing leaves, builders, or generated projections at once.",
        "route": [
            "AGENTS.md",
            "navigation/microcosm_index.json",
            "microcosms/leaf_entry_contract.json",
            "microcosms/concurrency_mission_control/README.md",
            "selected leaf README",
            "selected builder or std_python card",
            "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
        ],
        "success_check": "One leaf or one root compiler owner is selected, shared generated surfaces are rebuilt only through their owner command, and residuals are captured as receipt or repair rows.",
        "stop_rule": "Do not edit two leaves or shared root reports in the same pass unless the route explicitly selects a root compiler owner.",
    },
    {
        "mode_id": "sandbox_auditor",
        "when": "A reviewer is checking whether the active microcosm stays a system sandbox instead of release machinery.",
        "route": [
            "strategy/microcosm_teleology_gate.json",
            "sandbox/microcosm_sandbox_gate.json",
            "microcosms/leaf_entry_contract.json",
            "microcosms/meta_diagnostics_workbench/receipt.json",
            "receipts/validation_run.json",
        ],
        "success_check": "Active routes use system-organ leaves and retired downstream-release rows stay outside active selection.",
        "stop_rule": "Any website, recipient, package, hosted-public, or public-clone path in active selection is a teleology-gate failure.",
    },
]


CLAIM_STRENGTH_LADDER: list[dict[str, Any]] = [
    {
        "tier": "folder_seen",
        "allowed_claim": "A named leaf exists in the public constellation.",
        "required_evidence": ["microcosms/README.md"],
        "blocked_upgrade": "Folder presence does not prove the mechanism runs.",
    },
    {
        "tier": "receipt_backed_leaf",
        "allowed_claim": "A local fixture validates one mechanism leaf.",
        "required_evidence": ["leaf receipt", "leaf validator/probe"],
        "blocked_upgrade": "A leaf receipt does not prove whole-root readiness.",
    },
    {
        "tier": "root_validated",
        "allowed_claim": "The local public-safe root passes its validator chain.",
        "required_evidence": ["receipts/validation_run.json", "state/artifact_manifest.json"],
        "blocked_upgrade": "Local validation does not prove hosted-public readiness.",
    },
    {
        "tier": "external_release_support",
        "allowed_claim": "External release evidence may be reviewed only outside the active microcosm ontology.",
        "required_evidence": [
            "strategy/microcosm_teleology_gate.json",
            "release/publication_gate.json",
        ],
        "blocked_upgrade": "External release evidence does not define active system-organ leaves.",
    },
    {
        "tier": "publication_permission",
        "allowed_claim": "Publication language may be used only when the publication gate grants that exact posture.",
        "required_evidence": ["release/publication_gate.json", "fresh package and rights receipts"],
        "blocked_upgrade": "No other tier may imply publication approval.",
    },
]


ORGANISATION_MODEL: dict[str, Any] = {
    "schema_version": "microcosm_constellation_organisation_v0",
    "root_role": "composer_of_public_safe_leaf_proofs",
    "leaf_role": "one_organ_one_fixture_one_receipt_one_anti_claim_set",
    "route_role": "reviewer_question_to_first_leaf_supporting_leaves_and_receipts",
    "claim_role": "claim_strength_ladder_controls_what_language_an_agent_may_use",
    "default_read_order": [
        "root boundary",
        "entry packet",
        "microcosm index",
        "summary ladders",
        "reviewer route",
        "leaf receipt",
        "publication gate",
    ],
}


ROOT_ENTRY_CONTRACT: dict[str, Any] = {
    "schema_version": "root_microcosm_entry_contract_v0",
    "root_role": "composition_wrapper_for_public_safe_leaf_proofs",
    "leaf_role": "self_contained_evidence_cell_with_local_receipt",
    "root_only_owns": [
        "cross-leaf composition",
        "release and publication gates",
        "artifact manifest coverage",
        "std_python report refresh",
        "claim-strength decisions beyond leaf-local evidence",
    ],
    "leaf_only_owns": [
        "local README",
        "primary board, fixture, projection, or manifest",
        "receipt",
        "validator or probe",
        "anti-claims",
        "one-command run or inspect path",
    ],
    "authority_order": [
        "source JSON and code",
        "validator and receipt outputs",
        "generated indexes and reports",
        "Markdown reader projections",
        "folder names and rank labels",
    ],
    "claim_rule": "A root route may compose leaf evidence but may not upgrade any leaf beyond the strongest receipt and gate it cites.",
    "single_leaf_clone_rule": (
        "A leaf cloned without the parent root remains inspectable as a local evidence cell; "
        "root composition, standards closure, report refresh, hosted-public readiness, and publication permission are absent."
    ),
    "concurrency_rule": (
        "Concurrent work must claim one leaf or one root compiler owner before mutation; shared generated surfaces "
        "are settlement outputs, not coordination authority."
    ),
}


ROOT_CONCURRENCY_GUARD: dict[str, Any] = {
    "schema_version": "microcosm_concurrency_guard_v0",
    "purpose": "Keep parallel edits legible in the clonable root without importing the private work-ledger stack.",
    "entry_mode": "concurrent_editor",
    "primary_leaf": "microcosms/concurrency_mission_control/",
    "owner_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
    "validation_command": "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
    "route_order": [
        "select entry mode concurrent_editor",
        "choose one leaf_id or one root compiler owner",
        "read that leaf README, receipt, and std_python card before source",
        "patch only the selected owner surface and its direct generated outputs",
        "run the owner command or validate command",
        "leave unresolved cross-leaf work as a receipt or repair row instead of chat prose",
    ],
    "shared_surfaces": [
        "navigation/entry_packet.json",
        "navigation/microcosm_index.json",
        "microcosms/specimen_suite/std_python_compliance_report.json",
        "microcosms/specimen_suite/release_branch_graph.json",
        "state/artifact_manifest.json",
        "receipts/validation_run.json",
    ],
    "do_not": [
        "do not use a generated report as a lock",
        "do not edit two independent leaves in one patch without a root compiler owner",
        "do not treat a passing concurrent leaf receipt as whole-root readiness",
    ],
    "evidence_refs": [
        "microcosms/concurrency_mission_control/README.md",
        "microcosms/concurrency_mission_control/work_metabolism_bridge.json",
        "microcosms/concurrency_mission_control/receipt.json",
        "microcosms/leaf_entry_contract.json",
    ],
}


ROOT_ENTRY_ROUTE_MAP_BRIDGE: dict[str, Any] = {
    "schema_version": "root_entry_route_map_bridge_v0",
    "query_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-entry-routes --root . --band cluster_flag",
    "band_order": ["cluster_flag", "flag", "card"],
    "mode_count": len(EXOGENOUS_AGENT_ENTRY_MODES),
    "source_refs": [
        "navigation/entry_packet.json",
        "navigation/microcosm_index.json",
        "microcosms/leaf_entry_contract.json",
        "microcosms/summary_ladders/summary_ladders.json",
    ],
    "purpose": "Select the cold-entry operating mode before choosing a reviewer route, leaf route, or source span.",
    "boundary": "Entry-route rows choose the next legal navigation surface; they are not locks, receipts, release gates, or publication permission.",
}


ROOT_NAVIGATION_LADDER: list[dict[str, Any]] = [
    {
        "step_id": "root_contract",
        "surface": "AGENTS.md",
        "opens": "root rules, claim boundaries, and the one-command smoke check",
        "exit_condition": "The reader knows whether they are orienting, verifying, editing a leaf, or reviewing release posture.",
    },
    {
        "step_id": "entry_packet",
        "surface": "navigation/entry_packet.json",
        "opens": "machine-readable root contract, entry modes, claim ladder, and constellation routes",
        "exit_condition": "A reviewer question or leaf route is selected.",
    },
    {
        "step_id": "microcosm_index",
        "surface": "navigation/microcosm_index.json",
        "opens": "banded candidate routes, reviewer routes, leaf contract, and supporting leaves",
        "exit_condition": "The first leaf and its support leaves are known.",
    },
    {
        "step_id": "summary_ladders",
        "surface": "microcosms/summary_ladders/summary_ladders.json",
        "opens": "one-sentence, concise, medium, and deep descriptions plus band flags for every declared leaf",
        "exit_condition": "A leaf, band, or reviewer question is selected without opening folders blindly.",
    },
    {
        "step_id": "leaf_evidence",
        "surface": "microcosms/*/README.md plus board/fixture/manifest and receipt",
        "opens": "local organ, local proof path, validator/probe, receipt, and anti-claims",
        "exit_condition": "The leaf-local claim and its forbidden upgrades are explicit.",
    },
    {
        "step_id": "std_python_report",
        "surface": "microcosms/specimen_suite/std_python_compliance_report.json",
        "opens": "Python file rows, scope cards, route-atom sources, leaf-entry inference, and exact source spans",
        "exit_condition": "The precise code owner or source_span_ref is selected.",
    },
    {
        "step_id": "source_span",
        "surface": "src/idea_microcosm/**/*.py, probes/*.py, tests/test_*.py",
        "opens": "source authority for mutation or proof",
        "exit_condition": "The change is rebuilt into projections and validated.",
    },
]


STD_PYTHON_POPULATION_BRIDGE: dict[str, Any] = {
    "schema_version": "microcosm_std_python_population_bridge_v0",
    "local_standard": "codex/standards/std_python.py",
    "report": "microcosms/specimen_suite/std_python_compliance_report.json",
    "query_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band cluster_flag",
    "query_aliases": [
        "PYTHONPATH=src python3 -m idea_microcosm.cli query-code-navigation --root . --band cluster_flag",
    ],
    "owner_builder": "src/idea_microcosm/release_root_compiler.py::build_std_python_report",
    "purpose": "Join root entry, leaf entry, and implementation source without making code search the first move.",
    "population_order": [
        "root entry contract",
        "microcosm index route",
        "leaf evidence surfaces",
        "std_python file row",
        "std_python scope card",
        "exact source span",
    ],
    "accepted_population_modes": [
        "authored_route_atoms",
        "inferred_leaf_entry_contract",
        "inferred_support_route_contract",
        "authored_docstring_ast_fallback",
        "derived_ast_fallback",
    ],
    "query_bands": ["cluster_flag", "flag", "card", "source_span"],
    "inference_boundary": (
        "Leaf-entry inference may project existing README, receipt, validator, and index facts into file-level route atoms. "
        "Support-route inference may project local support-role profiles into package, library, probe, and test cards. "
        "Both remain lower-authority navigation projections and must not invent new doctrine, new standards authority, or stronger claims."
    ),
    "refresh_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-release-root-compiler --root . --write-receipt",
}


SUMMARY_LADDER_BRIDGE: dict[str, Any] = {
    "schema_version": "microcosm_summary_ladder_bridge_v0",
    "query_or_build_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-summary-ladders-specimen --root . --write-receipt",
    "output": "microcosms/summary_ladders/summary_ladders.json",
    "readme": "microcosms/summary_ladders/README.md",
    "receipt_ref": "microcosms/summary_ladders/receipt.json",
    "human_read_layer": "microcosms/summary_ladders/README.md",
    "ai_native_layer": "microcosms/summary_ladders/summary_ladders.json",
    "source_ref": "microcosms/leaf_entry_contract.json",
    "standard_ref": "standards/summary_ladder.json",
    "paper_module_ref": "paper_modules/summary_ladder_projection.md",
    "code_drilldown_ref": "codex/standards/std_python.py::PYTHON_STANDARD.summary_ladder_code_drilldown_contract",
    "length_levels": ["one_sentence", "concise", "medium", "deep"],
    "purpose": "Project every leaf into human-readable and AI-native drilldown layers, including std_python code-card commands, before opening leaf folders or source spans.",
    "boundary": "Summary ladders are compressed navigation projections; receipts, validators, source files, and release gates remain authority.",
}


MACRO_PATTERN_ROUTE_BRIDGE: dict[str, Any] = {
    "schema_version": "macro_pattern_route_bridge_v0",
    "query_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-pattern-routes --root . --band cluster_flag",
    "band_order": ["cluster_flag", "flag", "card"],
    "source_refs": [
        "registry/internal_pattern_inventory.json",
        "registry/annex_patterns.json",
        "modules/module_blueprints.json",
        "ports/port_packets.json",
        "microcosms/specimen_suite/std_python_compliance_report.json",
    ],
    "purpose": "Route imported macro-system patterns to local leaves, blueprints, port packets, receipts, and code cards.",
    "boundary": "This is a clean-room adoption map over existing surfaces, not a new doctrine authority plane.",
}


LEAF_CODE_ROUTE_BRIDGE: dict[str, Any] = {
    "schema_version": "microcosm_leaf_code_route_bridge_v0",
    "query_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band cluster_flag",
    "band_order": ["cluster_flag", "flag", "card", "source_span"],
    "source_refs": [
        "microcosms/leaf_entry_contract.json",
        "microcosms/summary_ladders/summary_ladders.json",
        "microcosms/specimen_suite/std_python_compliance_report.json",
    ],
    "purpose": "Route a selected leaf to its receipt, validator, generated std_python code cards, and exact source spans without broad source search.",
    "boundary": "Leaf-code route rows are navigation projections over existing leaf and std_python evidence; they are not source authority, standalone-wrapper proof, or publication permission.",
    "card_examples": [
        {
            "example_id": "cold_agent_leaf_drilldown",
            "question": "Which files explain and implement the cold-agent entry leaf?",
            "select": "leaf_code_route.self_comprehension_navigator",
            "commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band card --ids leaf_code_route.self_comprehension_navigator",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band source_span --ids leaf_code_route.self_comprehension_navigator",
            ],
            "claim_ceiling": "leaf_local_navigation_projection",
            "stop_before": "Do not turn a leaf-code card into standalone-wrapper proof or source authority.",
        },
        {
            "example_id": "diagnostic_leaf_drilldown",
            "question": "Which leaf owns command-speed, wait-tax, or wrapper-readiness diagnostics?",
            "select": "leaf_code_route.meta_diagnostics_workbench",
            "commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band card --ids leaf_code_route.meta_diagnostics_workbench",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band source_span --ids leaf_code_route.meta_diagnostics_workbench",
            ],
            "claim_ceiling": "synthetic_fixture_diagnostic_only",
            "stop_before": "Do not treat diagnostic source spans as live telemetry or performance certification.",
        },
    ],
}


IMPLEMENTATION_ATLAS_BRIDGE: dict[str, Any] = {
    "schema_version": "microcosm_implementation_atlas_bridge_v0",
    "projection_ref": "navigation/microcosm_index.json::implementation_atlas",
    "source_refs": [
        "microcosms/leaf_entry_contract.json",
        "microcosms/summary_ladders/summary_ladders.json",
        "microcosms/specimen_suite/std_python_compliance_report.json",
        "codex/standards/std_python.py",
    ],
    "query_commands": {
        "all_leaf_clusters": "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band cluster_flag",
        "selected_leaf_card": "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band card --ids leaf_code_route.<leaf_id>",
        "selected_leaf_source_spans": "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band source_span --ids leaf_code_route.<leaf_id>",
        "selected_std_python_card": "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band card --cluster microcosm_leaf.<leaf_id>",
        "selected_std_python_card_alias": "PYTHONPATH=src python3 -m idea_microcosm.cli query-code-navigation --root . --band card --cluster microcosm_leaf.<leaf_id>",
    },
    "purpose": "Compress every leaf's implementation route into one root-level code map while preserving leaf-code and std_python query surfaces as drilldown authority.",
    "boundary": "The implementation atlas is a generated navigation projection. It is not source authority, standalone-wrapper proof, hosted-public evidence, or publication permission.",
}


DIAGNOSTIC_ROUTE_BRIDGE: dict[str, Any] = {
    "schema_version": "microcosm_diagnostic_route_bridge_v0",
    "primary_leaf": "meta_diagnostics_workbench",
    "query_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-command-latency-inventory --root . --slow-only",
    "build_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-meta-diagnostics-workbench-specimen --root . --write-receipt",
    "code_card_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band card --ids leaf_code_route.meta_diagnostics_workbench",
    "source_span_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band source_span --ids leaf_code_route.meta_diagnostics_workbench",
    "portability_matrix_ref": "microcosms/meta_diagnostics_workbench/diagnostic_board.json::portability_authority_matrix",
    "standalone_split_contract_ref": "microcosms/meta_diagnostics_workbench/diagnostic_board.json::dogfood_preflight.standalone_split_contract",
    "source_refs": [
        "microcosms/meta_diagnostics_workbench/diagnostic_board.json",
        "microcosms/meta_diagnostics_workbench/receipt.json",
        "microcosms/concurrency_mission_control/mission_board.json",
        "microcosms/leaf_entry_contract.json",
        "microcosms/specimen_suite/std_python_compliance_report.json",
    ],
    "purpose": "Route command-speed, wait-tax, context-fit, and wrapper-readiness diagnostics through public-safe fixture rows before source or live telemetry.",
    "route_order": [
        "meta diagnostics README or board",
        "command latency inventory query",
        "repair route or owner surface",
        "leaf-code card",
        "source span only after one diagnostic row is selected",
        "portability authority matrix before any standalone claim strengthens",
    ],
    "boundary": "Diagnostic route rows are synthetic fixture evidence. They are not live telemetry, performance certification, hosted CI evidence, benchmark evidence, or publication permission.",
    "anti_claims": [
        "command latency inventory is live private telemetry",
        "synthetic wait-tax rows certify runtime performance",
        "diagnostic bridge grants hosted-public or publication readiness",
    ],
    "card_examples": [
        {
            "example_id": "slow_command_triage",
            "question": "Which public fixture row explains slow or duplicate validation pressure?",
            "commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-command-latency-inventory --root . --slow-only --limit 5",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-route-composition --root . --band card --ids route_surface.command_concurrency",
            ],
            "then_open": [
                "microcosms/meta_diagnostics_workbench/diagnostic_board.json::command_latency_inventory",
                "microcosms/concurrency_mission_control/mission_board.json::command_coordination",
            ],
            "claim_ceiling": "synthetic_fixture_diagnostic_only",
            "stop_before": "Do not cite these rows as live runtime telemetry, hosted CI evidence, or benchmark proof.",
        },
        {
            "example_id": "standalone_wrapper_readiness",
            "question": "Can a single leaf be cloned and run outside the root?",
            "commands": [
                "python3 probes/leaf_wrapper_readiness_probe.py --root . --leaf meta_diagnostics_workbench",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band card --ids leaf_code_route.meta_diagnostics_workbench",
            ],
            "then_open": [
                "microcosms/meta_diagnostics_workbench/diagnostic_board.json::dogfood_preflight.standalone_split_contract",
                "microcosms/leaf_entry_contract.json::summary",
            ],
            "claim_ceiling": "root_backed_inspection_supported_standalone_wrapper_required",
            "stop_before": "Do not claim private-root equivalence or standalone subrepo readiness without wrapper evidence.",
        },
    ],
}


UPGRADE_ROBUST_PROJECTION_PATTERN: dict[str, Any] = {
    "schema_version": "microcosm_upgrade_robust_projection_pattern_v0",
    "pattern_id": "upgrade_robust_projection_pattern",
    "purpose": (
        "Keep drift-prone microcosm projections upgradeable by separating stable interpretation rules "
        "from live facts, receipts, generated indexes, and claim ceilings."
    ),
    "route_order": [
        "select the owner route or leaf before opening source",
        "read source files, generated projection, receipt, and validator together",
        "bind live counts and currentness to JSON projections or receipts, not README prose",
        "state the claim ceiling and blocked upgrades before summarizing the pattern",
        "refresh the owner builder and validation receipt after source or projection-shape changes",
    ],
    "source_refs": [
        "navigation/entry_packet.json",
        "navigation/microcosm_index.json",
        "state/artifact_manifest.json",
        "microcosms/*/receipt.json",
        "release/publication_gate.json",
    ],
    "fact_boundary": "Current counts, freshness, and readiness live in generated JSON or receipts; prose names interpretation rules and reentry routes.",
    "claim_ceiling": "projection_not_authority_until_validator_receipt_and_gate_support_a_stronger_claim",
    "drift_policy": "Expected drift is an owner-builder refresh signal, not permission to infer from folders or hard-code current facts in prose.",
    "microcosm_rule": (
        "A leaf, root index, or route may be upgraded only by changing its owner surface, rebuilding projections, "
        "and keeping anti-claims attached to the receipt that supports the stronger language."
    ),
    "anti_claims": [
        "generated projection is source authority",
        "fresh local JSON proves hosted-public readiness",
        "current counts in prose are stable facts",
        "receipt-backed local validation grants publication permission",
    ],
}


ROUTE_COMPOSITION_BRIDGE: dict[str, Any] = {
    "schema_version": "microcosm_route_composition_bridge_v0",
    "query_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-route-composition --root . --band cluster_flag",
    "band_order": ["cluster_flag", "flag", "card"],
    "source_refs": [
        "navigation/entry_packet.json",
        "navigation/microcosm_index.json",
        "microcosms/leaf_entry_contract.json",
        "microcosms/summary_ladders/summary_ladders.json",
        "microcosms/specimen_suite/std_python_compliance_report.json",
        "microcosms/meta_diagnostics_workbench/diagnostic_board.json",
        "microcosms/concurrency_mission_control/mission_board.json",
        "microcosms/task_ledger_cap_economy/projection.json",
    ],
    "purpose": "Select the existing root, leaf, code, pattern, diagnostic, upgrade-robust projection, Task Ledger, settlement, or validation surface that owns the next move.",
    "boundary": "Route-composition rows compare existing navigation and settlement surfaces; they are not locks, receipts, source authority, live telemetry, release gates, or publication permission.",
    "example_discovery_policy": (
        "Cluster and flag bands expose example_count, example_ids, and example_card_refs so a cold agent can "
        "find example-bearing cards before opening full card payloads."
    ),
}


STD_PYTHON_NAVIGATION_REPORT = "microcosms/specimen_suite/std_python_compliance_report.json"
STD_PYTHON_NAVIGATION_BANDS = ("cluster_flag", "flag", "card", "source_span")
ROOT_ENTRY_ROUTE_BANDS = ("cluster_flag", "flag", "card")
ROUTE_COMPOSITION_BANDS = ("cluster_flag", "flag", "card")
MACRO_PATTERN_ROUTE_BANDS = ("cluster_flag", "flag", "card")
LEAF_CODE_ROUTE_BANDS = ("cluster_flag", "flag", "card", "source_span")
PRIMARY_CAPABILITY_ORDER = (
    "capability.navigation_before_search",
    "capability.standard_governed_artifacts",
    "capability.autonomous_strategy_seed",
    "capability.workitem_feedback_loop",
    "capability.publication_and_benchmark_gates",
    "capability.microcosm_self_proof",
    "capability.annex_pattern_transfer",
    "capability.module_blueprint_porter",
)
CAPABILITY_REVIEWER_ROUTES = {
    "capability.navigation_before_search": ["cold_agent_entry"],
    "capability.standard_governed_artifacts": ["cold_agent_entry", "release_restraint"],
    "capability.autonomous_strategy_seed": ["durable_work"],
    "capability.workitem_feedback_loop": ["durable_work"],
    "capability.publication_and_benchmark_gates": ["release_restraint", "diagnostic_review"],
    "capability.microcosm_self_proof": ["cold_agent_entry", "release_restraint"],
    "capability.annex_pattern_transfer": ["diagnostic_review"],
}


def _tokens(value: str | None) -> list[str]:
    return [part for part in re.split(r"\s+", (value or "").strip().lower()) if part]


def _row_text(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True).lower()


def _ids(row: dict[str, Any]) -> set[str]:
    values = {
        str(row.get(key))
        for key in (
            "row_id",
            "leaf_route_id",
            "scope_id",
            "cluster_id",
            "path",
            "source_span_ref",
            "source_pattern_ref",
            "module_blueprint_ref",
            "port_packet_ref",
            "leaf_id",
            "mode_id",
            "route_id",
            "surface_id",
        )
        if row.get(key)
    }
    if row.get("row_id"):
        values.add(f"macro_pattern_routes[row_id={row['row_id']}]")
        values.add(f"macro_pattern_routes.cards[row_id={row['row_id']}]")
        values.add(f"leaf_code_routes[row_id={row['row_id']}]")
        values.add(f"leaf_code_routes.cards[row_id={row['row_id']}]")
        values.add(f"entry_routes[row_id={row['row_id']}]")
        values.add(f"entry_routes.cards[row_id={row['row_id']}]")
    return values


def _wanted_id_aliases(values: Sequence[str] | None) -> set[str]:
    aliases: set[str] = set()
    for value in values or []:
        text = str(value)
        if not text:
            continue
        aliases.add(text)
        for match in re.finditer(r"(?:row_id|scope_id|cluster_id|mode_id|path|source_span_ref)=([^\]]+)", text):
            aliases.add(match.group(1))
    return aliases


def _filter_rows(
    rows: Sequence[dict[str, Any]],
    *,
    ids: Sequence[str] | None = None,
    cluster: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    wanted_ids = _wanted_id_aliases(ids)
    query_tokens = _tokens(query)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if wanted_ids and not (_ids(row) & wanted_ids):
            continue
        if cluster:
            if row.get("cluster_id") != cluster and row.get("navigation_group") != cluster:
                continue
        text = _row_text(row)
        if query_tokens and not all(token in text for token in query_tokens):
            continue
        filtered.append(row)
    return filtered


def _source_span_rows(scope_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in scope_rows:
        rows.append(
            {
                "band": "source_span",
                "row_id": row.get("scope_id"),
                "title": row.get("qualname"),
                "path": row.get("path"),
                "scope_kind": row.get("scope_kind"),
                "navigation_group": row.get("navigation_group"),
                "population_mode": row.get("population_mode"),
                "source_span_ref": row.get("source_span_ref"),
                "line_start": row.get("line_start"),
                "line_end": row.get("line_end"),
                "authority_boundary": row.get("authority_boundary"),
                "anti_claims": row.get("anti_claims", []),
                "omission_receipt": {
                    "omitted": [
                        "source body",
                        "full caller/callee graph",
                        "runtime execution state",
                    ],
                    "reason": "Source-span band names the exact code range without replacing source.",
                    "drilldown": row.get("source_span_ref"),
                },
            }
        )
    return rows


def _json_rows(root: Path, rel_path: str) -> list[dict[str, Any]]:
    payload = json.loads((root / rel_path).read_text(encoding="utf-8"))
    return [row for row in payload.get("rows", []) if isinstance(row, dict)]


def _json_object(root: Path, rel_path: str) -> dict[str, Any]:
    path = root / rel_path
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _target_microcosms(target_refs: Sequence[str]) -> list[str]:
    ids: set[str] = set()
    for ref in target_refs:
        match = re.search(r"(?:^|/)microcosms/([^/*]+)", str(ref))
        if match:
            ids.add(match.group(1))
    return sorted(ids)


def _primary_capability(capability_refs: Sequence[str], source_kind: str) -> str:
    for capability in PRIMARY_CAPABILITY_ORDER:
        if capability in capability_refs:
            return capability
    if source_kind == "annex_pattern":
        return "capability.annex_pattern_transfer"
    return "capability.module_blueprint_porter"


def _std_python_scope_refs_for_targets(report: dict[str, Any], target_refs: Sequence[str]) -> list[str]:
    cards = (report.get("navigation_index") or {}).get("cards") or []
    refs: list[str] = []
    seen: set[str] = set()
    for target in target_refs:
        target_text = str(target).rstrip("/")
        if not target_text:
            continue
        prefix = target_text.split("*", 1)[0].rstrip("/")
        for card in cards:
            if not isinstance(card, dict):
                continue
            path = str(card.get("path", ""))
            if path == target_text or (prefix and path.startswith(f"{prefix}/")):
                ref = card.get("scope_report_ref")
                if isinstance(ref, str) and ref not in seen:
                    seen.add(ref)
                    refs.append(ref)
            if len(refs) >= 12:
                return refs
    return refs


def _reviewer_route_refs(
    microcosm_index: dict[str, Any],
    *,
    target_microcosms: Sequence[str],
    capability_refs: Sequence[str],
) -> list[dict[str, Any]]:
    wanted_route_ids: set[str] = set()
    for capability in capability_refs:
        wanted_route_ids.update(CAPABILITY_REVIEWER_ROUTES.get(str(capability), []))
    wanted_microcosms = set(target_microcosms)
    rows: list[dict[str, Any]] = []
    for route in microcosm_index.get("reviewer_routes", []) or []:
        if not isinstance(route, dict):
            continue
        route_microcosms = {route.get("first_microcosm"), *route.get("supporting_microcosms", [])}
        route_id = str(route.get("route_id", ""))
        if route_id not in wanted_route_ids and not (wanted_microcosms & {str(item) for item in route_microcosms if item}):
            continue
        rows.append(
            {
                "route_id": route_id,
                "first_microcosm": route.get("first_microcosm"),
                "proof_refs": route.get("proof_refs", []),
                "anti_claim": route.get("anti_claim"),
            }
        )
    return rows


def _macro_pattern_route_base_rows(root: Path) -> list[dict[str, Any]]:
    internal_rows = _json_rows(root, "registry/internal_pattern_inventory.json")
    annex_rows = _json_rows(root, "registry/annex_patterns.json")
    module_rows = _json_rows(root, "modules/module_blueprints.json")
    packet_rows = _json_rows(root, "ports/port_packets.json")
    modules_by_pattern = {str(row.get("source_pattern_ref")): row for row in module_rows}
    packets_by_pattern = {str(row.get("source_pattern_ref")): row for row in packet_rows}
    std_report = _json_object(root, STD_PYTHON_NAVIGATION_REPORT)
    microcosm_index = _json_object(root, "navigation/microcosm_index.json")

    rows: list[dict[str, Any]] = []
    for pattern in [*internal_rows, *annex_rows]:
        pattern_ref = str(pattern.get("pattern_id", ""))
        module = modules_by_pattern.get(pattern_ref, {})
        packet = packets_by_pattern.get(pattern_ref, {})
        source_kind = str(module.get("source_kind") or ("annex_pattern" if ":" in pattern_ref else "internal_code_pattern"))
        capability_refs = list(packet.get("capability_refs") or module.get("capability_refs") or [])
        target_refs = list(packet.get("target_artifact_refs") or module.get("target_artifact_refs") or pattern.get("microcosm_artifacts") or [])
        primary_capability = _primary_capability(capability_refs, source_kind)
        cluster_id = primary_capability.replace("capability.", "macro_pattern.")
        target_microcosms = _target_microcosms(target_refs)
        related_scope_refs = _std_python_scope_refs_for_targets(std_report, target_refs)
        reviewer_routes = _reviewer_route_refs(
            microcosm_index,
            target_microcosms=target_microcosms,
            capability_refs=capability_refs,
        )
        rows.append(
            {
                "row_id": f"macro_pattern.{_safe_slug(pattern_ref)}",
                "source_pattern_ref": pattern_ref,
                "title": pattern.get("title", pattern_ref),
                "source_kind": source_kind,
                "cluster_id": cluster_id,
                "primary_capability_ref": primary_capability,
                "capability_refs": capability_refs,
                "public_transfer": pattern.get("public_transfer") or module.get("public_contract") or packet.get("public_contract"),
                "port_mode": packet.get("port_mode") or module.get("port_mode"),
                "module_blueprint_ref": module.get("id"),
                "port_packet_ref": packet.get("id"),
                "target_artifact_refs": target_refs,
                "target_microcosms": target_microcosms,
                "reviewer_route_refs": reviewer_routes,
                "related_std_python_scope_refs": related_scope_refs,
                "authority_boundary": (
                    "Macro-pattern route rows are local clean-room adoption maps. They connect patterns to "
                    "existing modules, leaves, receipts, and code cards without becoming a new source authority."
                ),
                "anti_claims": [
                    "pattern adoption rows copy private internals",
                    "module blueprints are source authority",
                    "pattern routes grant publication permission",
                ],
            }
        )
    return rows


def _macro_pattern_route_surfaces(root: Path) -> dict[str, list[dict[str, Any]]]:
    base_rows = _macro_pattern_route_base_rows(root)
    clusters: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    for cluster_id in sorted({row["cluster_id"] for row in base_rows}):
        cluster_rows = [row for row in base_rows if row["cluster_id"] == cluster_id]
        clusters.append(
            {
                "cluster_id": cluster_id,
                "band": "cluster_flag",
                "pattern_count": len(cluster_rows),
                "source_kinds": sorted({row["source_kind"] for row in cluster_rows}),
                "first_flag_refs": [f"macro_pattern_routes[row_id={row['row_id']}]" for row in cluster_rows[:8]],
                "authority_boundary": "Cluster rows group portable macro patterns by primary capability, not source authority.",
            }
        )

    for row in base_rows:
        flags.append(
            {
                "row_id": row["row_id"],
                "band": "flag",
                "cluster_id": row["cluster_id"],
                "title": row["title"],
                "source_pattern_ref": row["source_pattern_ref"],
                "source_kind": row["source_kind"],
                "flag": row["public_transfer"],
                "port_mode": row["port_mode"],
                "card_ref": f"macro_pattern_routes.cards[row_id={row['row_id']}]",
                "target_artifact_refs": row["target_artifact_refs"][:6],
            }
        )
        cards.append(
            {
                "row_id": row["row_id"],
                "band": "card",
                "cluster_id": row["cluster_id"],
                "title": row["title"],
                "source_pattern_ref": row["source_pattern_ref"],
                "source_kind": row["source_kind"],
                "public_transfer": row["public_transfer"],
                "primary_capability_ref": row["primary_capability_ref"],
                "capability_refs": row["capability_refs"],
                "port_mode": row["port_mode"],
                "module_blueprint_ref": row["module_blueprint_ref"],
                "port_packet_ref": row["port_packet_ref"],
                "target_artifact_refs": row["target_artifact_refs"],
                "target_microcosms": row["target_microcosms"],
                "reviewer_route_refs": row["reviewer_route_refs"],
                "related_std_python_scope_refs": row["related_std_python_scope_refs"],
                "authority_boundary": row["authority_boundary"],
                "omission_receipt": {
                    "omitted": ["private source bodies", "full macro-system trace", "provider/runtime state"],
                    "reason": "Pattern cards expose adoption routes and implementation drilldowns without copying private internals.",
                    "drilldown": row.get("port_packet_ref") or row.get("module_blueprint_ref") or row["source_pattern_ref"],
                },
                "anti_claims": row["anti_claims"],
            }
        )
    return {"cluster_flag": clusters, "flag": flags, "card": cards}


def _leaf_code_cards_by_leaf(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    for card in (report.get("navigation_index") or {}).get("cards", []) or []:
        if not isinstance(card, dict):
            continue
        cluster_id = str(card.get("cluster_id", ""))
        if not cluster_id.startswith("microcosm_leaf."):
            continue
        rows.setdefault(cluster_id.removeprefix("microcosm_leaf."), []).append(card)
    return rows


def _leaf_code_source_spans_by_leaf(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    for scope_row in report.get("scope_rows", []) or []:
        if not isinstance(scope_row, dict):
            continue
        navigation_group = str(scope_row.get("navigation_group", ""))
        if not navigation_group.startswith("microcosm_leaf."):
            continue
        leaf_id = navigation_group.removeprefix("microcosm_leaf.")
        rows.setdefault(leaf_id, []).append(scope_row)
    return rows


def _summary_ladder_leaf_refs(root: Path) -> dict[str, str]:
    payload = _json_object(root, "microcosms/summary_ladders/summary_ladders.json")
    refs: dict[str, str] = {}
    for row in payload.get("rows", []) or []:
        if isinstance(row, dict) and row.get("leaf_id"):
            refs[str(row["leaf_id"])] = f"microcosms/summary_ladders/summary_ladders.json::rows[{row['leaf_id']}]"
    return refs


def _leaf_code_route_base_rows(root: Path) -> list[dict[str, Any]]:
    contract = _json_object(root, "microcosms/leaf_entry_contract.json")
    report = _json_object(root, STD_PYTHON_NAVIGATION_REPORT)
    cards_by_leaf = _leaf_code_cards_by_leaf(report)
    summary_refs = _summary_ladder_leaf_refs(root)
    rows: list[dict[str, Any]] = []
    active_leaves, _retired_seen = _active_leaf_rows(root, contract)
    for leaf in active_leaves:
        if not isinstance(leaf, dict) or not leaf.get("leaf_id"):
            continue
        leaf_id = str(leaf["leaf_id"])
        cards = cards_by_leaf.get(leaf_id, [])
        code_card_refs = [
            card.get("scope_report_ref") or f"{STD_PYTHON_NAVIGATION_REPORT}::navigation_index.cards[row_id={card.get('row_id')}]"
            for card in cards
            if card.get("row_id")
        ]
        source_span_refs = [str(card.get("source_span_ref")) for card in cards if card.get("source_span_ref")]
        cluster_id = f"entry_track.{leaf.get('entry_track')}"
        organ = leaf.get("organ")
        if leaf_id == "atlas_navigation_bands":
            organ = "compressed, technical, evidence, and sandbox navigation bands"
        rows.append(
            {
                "row_id": f"leaf_code_route.{leaf_id}",
                "leaf_id": leaf_id,
                "cluster_id": cluster_id,
                "title": leaf_id.replace("_", " ").title(),
                "organ": organ,
                "entry_track": leaf.get("entry_track"),
                "path": leaf.get("path"),
                "first_surface": leaf.get("first_surface"),
                "evidence_surface": leaf.get("evidence_surface"),
                "receipt_or_probe": leaf.get("receipt_or_probe"),
                "standards_subset": leaf.get("standards_subset", []),
                "std_python_posture": leaf.get("std_python_posture"),
                "clone_posture": leaf.get("clone_posture"),
                "summary_ladder_ref": summary_refs.get(leaf_id),
                "std_python_report_ref": STD_PYTHON_NAVIGATION_REPORT,
                "code_status": "code_cards_available" if code_card_refs else "code_cards_missing",
                "code_card_count": len(code_card_refs),
                "code_card_refs": code_card_refs[:12],
                "source_span_refs": source_span_refs[:12],
                "query_commands": {
                    "flag": f"PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band flag --cluster {cluster_id}",
                    "card": f"PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band card --ids leaf_code_route.{leaf_id}",
                    "std_python_card": (
                        "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . "
                        f"--band card --cluster microcosm_leaf.{leaf_id}"
                    ),
                    "source_span": (
                        "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . "
                        f"--band source_span --ids leaf_code_route.{leaf_id}"
                    ),
                },
                "standalone_wrapper": {
                    "current_clone_posture": leaf.get("clone_posture"),
                    "status": (
                        "standalone_wrapper_target_declared"
                        if leaf.get("clone_posture") == "standalone_leaf_target"
                        else "wrapper_required_before_standalone_claim"
                    ),
                    "rule": "A leaf card may route to code and receipt evidence, but standalone execution still requires an explicit wrapper projection.",
                },
                "route_order": [
                    "leaf contract row",
                    "summary ladder row",
                    "leaf README or first surface",
                    "evidence surface",
                    "receipt or probe",
                    "std_python card query",
                    "source span only after card selection",
                ],
                "authority_boundary": "Leaf-code rows compose existing leaf and std_python evidence; source files, receipts, validators, and release gates remain authority.",
                "anti_claims": [
                    *leaf.get("anti_claims", []),
                    "leaf-code route row is not source authority",
                    "code-card availability is not standalone wrapper readiness",
                    "local leaf receipt is not hosted-public or publication permission",
                ],
            }
        )
    return rows


def _leaf_code_route_surfaces(root: Path) -> dict[str, list[dict[str, Any]]]:
    base_rows = _leaf_code_route_base_rows(root)
    report = _json_object(root, STD_PYTHON_NAVIGATION_REPORT)
    source_spans_by_leaf = _leaf_code_source_spans_by_leaf(report)
    clusters: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    source_spans: list[dict[str, Any]] = []
    for cluster_id in sorted({row["cluster_id"] for row in base_rows}):
        cluster_rows = [row for row in base_rows if row["cluster_id"] == cluster_id]
        clusters.append(
            {
                "cluster_id": cluster_id,
                "band": "cluster_flag",
                "leaf_count": len(cluster_rows),
                "code_cards_available_count": sum(1 for row in cluster_rows if row["code_status"] == "code_cards_available"),
                "clone_postures": sorted({str(row.get("clone_posture")) for row in cluster_rows}),
                "first_flag_refs": [f"leaf_code_routes[row_id={row['row_id']}]" for row in cluster_rows[:8]],
                "authority_boundary": "Entry-track clusters group leaves for code drilldown; they do not prove standalone readiness.",
            }
        )
    for row in base_rows:
        flags.append(
            {
                "row_id": row["row_id"],
                "leaf_id": row["leaf_id"],
                "band": "flag",
                "cluster_id": row["cluster_id"],
                "title": row["title"],
                "flag": row["organ"],
                "path": row["path"],
                "first_surface": row["first_surface"],
                "receipt_or_probe": row["receipt_or_probe"],
                "code_status": row["code_status"],
                "code_card_count": row["code_card_count"],
                "card_ref": f"leaf_code_routes.cards[row_id={row['row_id']}]",
            }
        )
        cards.append({**row, "band": "card"})
        for scope_row in source_spans_by_leaf.get(row["leaf_id"], []):
            scope_id = str(scope_row.get("scope_id"))
            source_spans.append(
                {
                    "row_id": f"{row['row_id']}::{scope_id}",
                    "leaf_route_id": row["row_id"],
                    "leaf_id": row["leaf_id"],
                    "band": "source_span",
                    "cluster_id": row["cluster_id"],
                    "title": scope_row.get("qualname"),
                    "path": scope_row.get("path"),
                    "scope_kind": scope_row.get("scope_kind"),
                    "population_mode": scope_row.get("population_mode"),
                    "source_span_ref": scope_row.get("source_span_ref"),
                    "line_start": scope_row.get("line_start"),
                    "line_end": scope_row.get("line_end"),
                    "scope_report_ref": scope_row.get("scope_report_ref"),
                    "file_report_ref": scope_row.get("file_report_ref"),
                    "card_ref": f"{STD_PYTHON_NAVIGATION_REPORT}::navigation_index.cards[row_id={scope_id}]",
                    "receipt_or_probe": row["receipt_or_probe"],
                    "authority_boundary": (
                        "Leaf-code source-span rows name exact code ranges after a leaf has been selected; "
                        "the source file remains authority."
                    ),
                    "omission_receipt": {
                        "omitted": ["source body", "full caller/callee graph", "runtime execution state"],
                        "reason": "Leaf-code source-span band gives exact mutation/proof coordinates without replacing source.",
                        "drilldown": scope_row.get("source_span_ref"),
                    },
                    "anti_claims": [
                        "leaf-code source-span row is source authority",
                        "source-span availability proves standalone leaf export",
                        "leaf-local source span grants hosted-public or publication permission",
                    ],
                }
            )
    return {"cluster_flag": clusters, "flag": flags, "card": cards, "source_span": source_spans}


def build_microcosm_implementation_atlas(root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Project the whole microcosm code surface into one compact leaf-to-implementation atlas.
    - Guarantee: Returns one row per leaf with route commands, code-card counts, source-span counts, and claim boundaries.
    - Fails: Raises file or JSON errors when leaf or std_python projections are absent.
    - When-needed: Open from the root index when a cold agent needs to see every leaf's implementation route before picking one.
    - Escalates-to: query_leaf_code_routes; query_std_python_navigation; microcosms/specimen_suite/std_python_compliance_report.json
    """
    root = root.resolve()
    rows = _leaf_code_route_base_rows(root)
    clusters: list[dict[str, Any]] = []
    for cluster_id in sorted({str(row["cluster_id"]) for row in rows}):
        cluster_rows = [row for row in rows if row["cluster_id"] == cluster_id]
        clusters.append(
            {
                "cluster_id": cluster_id,
                "entry_track": cluster_id.removeprefix("entry_track."),
                "leaf_count": len(cluster_rows),
                "code_cards_available_count": sum(
                    1 for row in cluster_rows if row.get("code_status") == "code_cards_available"
                ),
                "source_span_ref_count": sum(len(row.get("source_span_refs") or []) for row in cluster_rows),
                "first_leaf_refs": [row["row_id"] for row in cluster_rows[:8]],
                "query_command": (
                    "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes "
                    f"--root . --band flag --cluster {cluster_id}"
                ),
                "authority_boundary": "Implementation-atlas clusters summarize leaf-code route rows; selected leaf cards remain the next authority-preserving drilldown.",
            }
        )

    leaf_rows: list[dict[str, Any]] = []
    for row in rows:
        code_card_refs = [str(ref) for ref in row.get("code_card_refs", [])]
        source_span_refs = [str(ref) for ref in row.get("source_span_refs", [])]
        leaf_rows.append(
            {
                "leaf_id": row["leaf_id"],
                "row_id": row["row_id"],
                "cluster_id": row["cluster_id"],
                "entry_track": row.get("entry_track"),
                "organ": row.get("organ"),
                "leaf_entry_contract_ref": f"microcosms/leaf_entry_contract.json::leaf_rows[leaf_id={row['leaf_id']}]",
                "first_surface": row.get("first_surface"),
                "evidence_surface": row.get("evidence_surface"),
                "receipt_or_probe": row.get("receipt_or_probe"),
                "summary_ladder_ref": row.get("summary_ladder_ref"),
                "std_python_posture": row.get("std_python_posture"),
                "clone_posture": row.get("clone_posture"),
                "code_status": row.get("code_status"),
                "code_card_count": row.get("code_card_count", 0),
                "source_span_count": len(source_span_refs),
                "primary_code_card_ref": code_card_refs[0] if code_card_refs else None,
                "primary_source_span_ref": source_span_refs[0] if source_span_refs else None,
                "query_commands": row.get("query_commands", {}),
                "standalone_wrapper": row.get("standalone_wrapper", {}),
                "route_order": [
                    "implementation atlas row",
                    "leaf-code card",
                    "std_python code card",
                    "leaf-scoped source span",
                    "source file remains authority",
                ],
                "authority_boundary": row.get("authority_boundary"),
                "anti_claims": row.get("anti_claims", []),
            }
        )

    leaf_count = len(leaf_rows)
    rows_with_code_cards = sum(1 for row in leaf_rows if row["code_card_count"] > 0)
    rows_with_source_spans = sum(1 for row in leaf_rows if row["source_span_count"] > 0)
    return {
        "kind": "microcosm_implementation_atlas",
        "schema_version": "microcosm_implementation_atlas_v0",
        "authority_posture": "generated_code_navigation_projection_not_source_authority",
        "source_refs": IMPLEMENTATION_ATLAS_BRIDGE["source_refs"],
        "bridge": IMPLEMENTATION_ATLAS_BRIDGE,
        "route_order": [
            "navigation/microcosm_index.json::implementation_atlas",
            "entry-track cluster",
            "leaf row",
            "leaf-code card query",
            "std_python card query",
            "source span only after leaf/card selection",
        ],
        "summary": {
            "leaf_count": leaf_count,
            "cluster_count": len(clusters),
            "rows_with_code_cards": rows_with_code_cards,
            "rows_with_source_spans": rows_with_source_spans,
            "all_leaves_have_code_cards": rows_with_code_cards == leaf_count,
            "all_leaves_have_source_spans": rows_with_source_spans == leaf_count,
            "claim_ceiling": "code_navigation_projection_not_source_or_standalone_authority",
        },
        "clusters": clusters,
        "leaf_rows": leaf_rows,
        "anti_claims": [
            "implementation atlas rows are source authority",
            "all-leaf code-card coverage proves standalone wrapper readiness",
            "implementation atlas coverage grants hosted-public or publication permission",
        ],
    }


def _leaf_implementation_navigation(row: dict[str, Any]) -> dict[str, Any]:
    leaf_id = str(row.get("leaf_id"))
    code_card_count = int(row.get("code_card_count") or 0)
    source_span_count = int(row.get("source_span_count") or 0)
    query_commands = dict(row.get("query_commands") or {})
    contract_ref = f"microcosms/leaf_entry_contract.json::leaf_rows[leaf_id={leaf_id}]"
    status = (
        "code_and_source_span_ready"
        if code_card_count and source_span_count
        else ("code_card_ready_source_span_missing" if code_card_count else "code_card_missing")
    )
    return {
        "schema_version": "microcosm_leaf_implementation_navigation_v0",
        "status": status,
        "implementation_atlas_ref": f"navigation/microcosm_index.json::implementation_atlas.leaf_rows[leaf_id={leaf_id}]",
        "leaf_entry_contract_ref": contract_ref,
        "leaf_code_route_ref": f"leaf_code_routes.cards[row_id=leaf_code_route.{leaf_id}]",
        "std_python_report_ref": STD_PYTHON_NAVIGATION_REPORT,
        "primary_code_card_ref": row.get("primary_code_card_ref"),
        "primary_source_span_ref": row.get("primary_source_span_ref"),
        "code_card_count": code_card_count,
        "source_span_count": source_span_count,
        "query_commands": {
            "leaf_card": query_commands.get("card")
            or f"PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band card --ids leaf_code_route.{leaf_id}",
            "std_python_card": query_commands.get("std_python_card")
            or (
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . "
                f"--band card --cluster microcosm_leaf.{leaf_id}"
            ),
            "source_span": query_commands.get("source_span")
            or (
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . "
                f"--band source_span --ids leaf_code_route.{leaf_id}"
            ),
        },
        "read_order": [
            row.get("first_surface"),
            contract_ref,
            row.get("summary_ladder_ref"),
            row.get("evidence_surface"),
            row.get("receipt_or_probe"),
            "leaf_code_route_ref",
            "std_python_card query",
            "source_span query only after leaf/card selection",
        ],
        "root_wrapper_required_for": [
            "running builder commands",
            "refreshing std_python report rows",
            "validating shared standards and receipts",
            "composing cross-leaf claims",
            "hosted-public or publication gates",
        ],
        "standalone_claim_status": (
            "not_export_target"
            if row.get("clone_posture") == "composition_only"
            else "blocked_until_explicit_leaf_wrapper_projection"
        ),
        "authority_boundary": (
            "Leaf implementation navigation is a root-backed wrapper projection over existing leaf rows "
            "and std_python cards; source files, receipts, validators, and release gates remain authority."
        ),
        "anti_claims": [
            "leaf implementation navigation is source authority",
            "code-card coverage proves standalone leaf execution",
            "leaf-local implementation route grants hosted-public or publication permission",
        ],
    }


def _title_from_leaf_id(leaf_id: str) -> str:
    return leaf_id.replace("_", " ").title()


def _managed_markdown_section(existing: str, section: str) -> str:
    if LEAF_ENTRY_CARD_BEGIN in existing and LEAF_ENTRY_CARD_END in existing:
        before, rest = existing.split(LEAF_ENTRY_CARD_BEGIN, 1)
        _, after = rest.split(LEAF_ENTRY_CARD_END, 1)
        return before.rstrip() + "\n\n" + section.rstrip() + "\n" + after.lstrip("\n")
    return existing.rstrip() + "\n\n" + section.rstrip() + "\n"


def _leaf_entry_card_markdown(row: dict[str, Any]) -> str:
    leaf_id = str(row["leaf_id"])
    implementation_navigation = row.get("implementation_navigation", {})
    leaf_packet = row.get("leaf_first_entry_packet", {})
    query_commands = implementation_navigation.get("query_commands", {})
    anti_claims = row.get("anti_claims", []) + implementation_navigation.get("anti_claims", [])
    lines = [
        LEAF_ENTRY_CARD_BEGIN,
        "## Leaf Entry Card",
        "",
        "_Generated from `microcosms/leaf_entry_contract.json`; refresh with "
        "`PYTHONPATH=src python3 -m idea_microcosm.cli build-atlas-navigation-bands-specimen --root . --write-receipt`._",
        "",
        f"- Leaf id: `{leaf_id}`",
        f"- Entry track: `{row.get('entry_track')}`",
        f"- Organ: {row.get('organ')}",
        f"- Clone posture: `{row.get('clone_posture')}`",
        f"- Evidence: `{row.get('evidence_surface')}`",
        f"- Receipt/probe: `{row.get('receipt_or_probe')}`",
        f"- Contract row: `{implementation_navigation.get('leaf_entry_contract_ref')}`",
        f"- Primary source span: `{implementation_navigation.get('primary_source_span_ref')}`",
        "",
        "Root-backed implementation route:",
        "",
        f"```bash\n{query_commands.get('leaf_card', '')}\n```",
        f"```bash\n{query_commands.get('std_python_card', '')}\n```",
        f"```bash\n{query_commands.get('source_span', '')}\n```",
        "",
        "Local inspection is supported from this README, the evidence file, and the receipt/probe. "
        "Rebuilds, validation, std_python refresh, cross-leaf composition, and stronger release claims require the parent root.",
        "",
        "Do not claim:",
    ]
    lines.extend(f"- {item}" for item in anti_claims[:6])
    if leaf_packet.get("parent_root_required_for"):
        lines.extend(
            [
                "",
                "Parent root required for:",
                *[f"- {item}" for item in leaf_packet["parent_root_required_for"]],
            ]
        )
    lines.append(LEAF_ENTRY_CARD_END)
    return "\n".join(lines)


def build_leaf_entry_contract_projection(
    root: Path,
    *,
    implementation_atlas: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Enrich the leaf-entry contract with root-backed implementation wrappers.
    - Guarantee: Returns the existing leaf contract plus per-leaf std_python code routes and clone boundaries.
    - Fails: Raises file or JSON errors when the source contract is absent or malformed.
    - When-needed: Open when a leaf is entered directly and needs a compact path from README to code.
    - Escalates-to: build_microcosm_implementation_atlas; query_leaf_code_routes; query_std_python_navigation
    """
    root = root.resolve()
    contract = _json_object(root, "microcosms/leaf_entry_contract.json")
    if not contract:
        return {}
    implementation_atlas = implementation_atlas or build_microcosm_implementation_atlas(root)
    impl_by_leaf = {
        str(row.get("leaf_id")): row
        for row in implementation_atlas.get("leaf_rows", []) or []
        if isinstance(row, dict) and row.get("leaf_id")
    }

    leaf_rows: list[dict[str, Any]] = []
    rows_with_navigation = 0
    rows_with_code_cards = 0
    rows_with_source_spans = 0
    retired_leaf_ids = sorted(_retired_leaf_ids(root))
    active_leaves, retired_seen = _active_leaf_rows(root, contract)
    for leaf in active_leaves:
        if not isinstance(leaf, dict) or not leaf.get("leaf_id"):
            continue
        leaf_id = str(leaf["leaf_id"])
        enriched = {
            key: value
            for key, value in leaf.items()
            if key not in {"implementation_navigation", "leaf_first_entry_packet"}
        }
        if leaf_id == "atlas_navigation_bands":
            enriched["organ"] = "compressed, technical, evidence, and sandbox navigation bands"
        impl_row = impl_by_leaf.get(leaf_id, {})
        implementation_navigation = (
            _leaf_implementation_navigation(impl_row)
            if impl_row
            else {
                "schema_version": "microcosm_leaf_implementation_navigation_v0",
                "status": "implementation_atlas_row_missing",
                "implementation_atlas_ref": (
                    f"navigation/microcosm_index.json::implementation_atlas.leaf_rows[leaf_id={leaf_id}]"
                ),
                "leaf_entry_contract_ref": f"microcosms/leaf_entry_contract.json::leaf_rows[leaf_id={leaf_id}]",
                "authority_boundary": (
                    "No implementation atlas row was available; use the leaf README, receipt, and root validation before source."
                ),
                "anti_claims": ["missing implementation row grants no standalone or publication claim"],
            }
        )
        rows_with_navigation += 1 if implementation_navigation.get("status") != "implementation_atlas_row_missing" else 0
        rows_with_code_cards += 1 if int(implementation_navigation.get("code_card_count") or 0) > 0 else 0
        rows_with_source_spans += 1 if int(implementation_navigation.get("source_span_count") or 0) > 0 else 0
        leaf_entry_card_ref = f"{leaf.get('first_surface')}#leaf-entry-card"
        enriched["leaf_entry_card_ref"] = leaf_entry_card_ref
        enriched["implementation_navigation"] = implementation_navigation
        enriched["leaf_first_entry_packet"] = {
            "schema_version": "microcosm_leaf_first_entry_packet_v0",
            "status": "root_backed_leaf_entry_ready",
            "leaf_entry_card_ref": leaf_entry_card_ref,
            "read_order": implementation_navigation.get("read_order", []),
            "leaf_local_supported_now": [
                "read the selected leaf README",
                "read the generated Leaf Entry Card in that README",
                "inspect the declared evidence surface",
                "inspect the declared receipt or probe",
                "use implementation_navigation query commands when the parent root is present",
            ],
            "parent_root_required_for": implementation_navigation.get("root_wrapper_required_for", []),
            "standalone_boundary": implementation_navigation.get("standalone_claim_status"),
        }
        leaf_rows.append(enriched)

    summary = dict(contract.get("summary") or {})
    leaf_count = len(leaf_rows)
    composition_only_count = sum(
        1 for row in leaf_rows if str(row.get("clone_posture") or "") == "composition_only"
    )
    root_clone_supported_count = sum(
        1 for row in leaf_rows if str(row.get("clone_posture") or "") == "root_clone_supported"
    )
    standalone_leaf_supported_count = sum(
        1 for row in leaf_rows if str(row.get("clone_posture") or "") == "standalone_leaf_supported"
    )
    summary.update(
        {
            "leaf_count": leaf_count,
            "root_clone_supported_count": root_clone_supported_count,
            "composition_only_count": composition_only_count,
            "standalone_leaf_supported_count": standalone_leaf_supported_count,
            "retired_leaf_count": len(retired_leaf_ids),
            "implementation_navigation_leaf_count": rows_with_navigation,
            "rows_with_code_cards": rows_with_code_cards,
            "rows_with_source_spans": rows_with_source_spans,
            "rows_with_leaf_entry_cards": leaf_count,
            "all_leaves_have_implementation_navigation": rows_with_navigation == leaf_count,
            "all_leaves_have_code_cards": rows_with_code_cards == leaf_count,
            "all_leaves_have_source_spans": rows_with_source_spans == leaf_count,
            "all_leaves_have_leaf_entry_cards": True,
            "single_leaf_wrapper_status": "root_backed_wrapper_projected_not_standalone_subrepo",
        }
    )

    enriched_contract = dict(contract)
    enriched_contract["leaf_rows"] = leaf_rows
    enriched_contract["teleology_gate_ref"] = TELEOLOGY_GATE_PATH.as_posix()
    enriched_contract["sandbox_gate_ref"] = SANDBOX_GATE_PATH.as_posix()
    enriched_contract["active_leaf_scope"] = "system_organ_microcosms_only"
    enriched_contract["retired_leaf_ids"] = retired_leaf_ids
    enriched_contract["summary"] = summary
    enriched_contract["implementation_navigation_bridge"] = {
        "schema_version": "microcosm_leaf_implementation_navigation_bridge_v0",
        "implementation_atlas_ref": "navigation/microcosm_index.json::implementation_atlas",
        "leaf_readme_card_rule": (
            "Every leaf README carries a generated Leaf Entry Card that mirrors the contract row, "
            "implementation navigation commands, source-span handle, and root-backed boundary."
        ),
        "leaf_code_route_command": (
            "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band cluster_flag"
        ),
        "std_python_query_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band cluster_flag",
        "std_python_query_aliases": [
            "PYTHONPATH=src python3 -m idea_microcosm.cli query-code-navigation --root . --band cluster_flag",
        ],
        "coverage": {
            "leaf_count": leaf_count,
            "implementation_navigation_leaf_count": rows_with_navigation,
            "all_leaves_have_implementation_navigation": rows_with_navigation == leaf_count,
        },
        "route_order": [
            "selected leaf README",
            "microcosms/leaf_entry_contract.json::leaf_rows[leaf_id=<leaf_id>]",
            "leaf_first_entry_packet",
            "implementation_navigation leaf card",
            "std_python card",
            "source span only after card selection",
        ],
        "authority_boundary": (
            "This bridge makes a single leaf easier to enter from a root-backed checkout; it does not "
            "make the leaf an independently runnable subrepo."
        ),
    }
    enriched_contract["single_leaf_wrapper_protocol"] = {
        "schema_version": "microcosm_single_leaf_wrapper_protocol_v0",
        "current_supported_mode": "root_backed_leaf_entry",
        "leaf_link_entry_rule": (
            "If a reviewer enters from one leaf, read that leaf README, then its row in "
            "microcosms/leaf_entry_contract.json, then implementation_navigation before opening source."
        ),
        "future_export_requirement": (
            "A standalone leaf export must carry local standards, fixture data, validator/probe, receipt, "
            "README, and a std_python wrapper projection generated from this contract."
        ),
        "forbid": [
            "treating root-backed implementation navigation as standalone execution",
            "treating a leaf receipt as root validation or publication permission",
            "copying parent standards without naming the inherited subset",
        ],
    }
    return enriched_contract


def build_leaf_entry_readme_cards(
    root: Path,
    *,
    leaf_entry_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Project root-backed leaf entry cards into the leaf README a direct entrant opens first.
    - Guarantee: Updates only the managed Leaf Entry Card section in each declared leaf README.
    - Fails: Raises when a declared README path is missing or unwritable.
    - When-needed: Run after leaf_entry_contract or std_python implementation routes change.
    - Escalates-to: build_leaf_entry_contract_projection; build_atlas_navigation_specimen
    """
    root = root.resolve()
    leaf_entry_contract = leaf_entry_contract or build_leaf_entry_contract_projection(root)
    written: list[str] = []
    missing: list[str] = []
    for row in leaf_entry_contract.get("leaf_rows", []) or []:
        first_surface = row.get("first_surface")
        if not first_surface:
            continue
        result = project_leaf_entry_card_to_readme(root, row)
        if result["status"] == "missing_readme":
            missing.append(str(first_surface))
            continue
        written.append(result["path"])
    return {
        "kind": "leaf_entry_readme_card_projection",
        "schema_version": "leaf_entry_readme_card_projection_v0",
        "status": "ok" if not missing else "missing_readmes",
        "written_count": len(written),
        "missing_count": len(missing),
        "written_paths": written,
        "missing_paths": missing,
        "authority_boundary": (
            "Leaf README cards are generated navigation projections. They do not make a leaf standalone, "
            "replace source authority, or grant hosted-public/publication permission."
        ),
    }


def project_leaf_entry_card_to_readme(root: Path, row: dict[str, Any]) -> dict[str, str]:
    """
    [ACTION]
    - Teleology: Re-project one leaf entry card after a leaf README builder rewrites its human surface.
    - Guarantee: Replaces only the managed Leaf Entry Card section for one declared leaf.
    - Fails: Returns missing_readme when the declared first_surface does not exist.
    - When-needed: Call from leaf-specific README builders that would otherwise clobber the generated card.
    - Escalates-to: build_leaf_entry_readme_cards
    """
    first_surface = row.get("first_surface")
    if not first_surface:
        return {"status": "missing_first_surface", "path": ""}
    readme_path = root.resolve() / first_surface
    if not readme_path.exists():
        return {"status": "missing_readme", "path": str(first_surface)}
    existing = readme_path.read_text(encoding="utf-8")
    section = _leaf_entry_card_markdown(row)
    readme_path.write_text(_managed_markdown_section(existing, section), encoding="utf-8")
    return {"status": "ok", "path": str(first_surface)}


def _entry_route_cluster(mode_id: str) -> str:
    if mode_id == "orientation_reader":
        return "entry_route.orientation"
    if mode_id == "claim_verifier":
        return "entry_route.review"
    if mode_id == "sandbox_auditor":
        return "entry_route.sandbox_boundary"
    if mode_id == "leaf_editor":
        return "entry_route.leaf_mutation"
    if mode_id == "concurrent_editor":
        return "entry_route.concurrent_mutation"
    return "entry_route.other"


def _entry_route_claim_ceiling(mode_id: str) -> str:
    if mode_id in {"leaf_editor", "concurrent_editor"}:
        return "one_owner_then_validate"
    if mode_id == "sandbox_auditor":
        return "sandbox_gate_evidence_only"
    return "navigation_projection_only"


def _entry_route_mutation_allowed(mode_id: str) -> bool:
    return mode_id in {"leaf_editor", "concurrent_editor"}


def _entry_route_next_commands(mode_id: str) -> list[str]:
    if mode_id == "concurrent_editor":
        return [
            "PYTHONPATH=src python3 -m idea_microcosm.cli query-command-latency-inventory --root . --slow-only",
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
            "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
        ]
    if mode_id == "leaf_editor":
        return [
            "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band cluster_flag",
            "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
        ]
    if mode_id == "sandbox_auditor":
        return [
            "PYTHONPATH=src python3 -m idea_microcosm.cli query-entry-routes --root . --band card --ids entry_route.sandbox_auditor",
            "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
        ]
    if mode_id == "claim_verifier":
        return [
            "PYTHONPATH=src python3 -m idea_microcosm.cli query-pattern-routes --root . --band cluster_flag",
            "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
        ]
    return [
        "PYTHONPATH=src python3 -m idea_microcosm.cli query-entry-routes --root . --band flag --cluster entry_route.orientation",
        "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band cluster_flag",
    ]


def _entry_route_mode_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mode in EXOGENOUS_AGENT_ENTRY_MODES:
        mode_id = str(mode["mode_id"])
        rows.append(
            {
                "row_id": f"entry_route.{mode_id}",
                "mode_id": mode_id,
                "cluster_id": _entry_route_cluster(mode_id),
                "title": mode_id.replace("_", " ").title(),
                "when": mode.get("when"),
                "route": mode.get("route", []),
                "success_check": mode.get("success_check"),
                "stop_rule": mode.get("stop_rule"),
                "mutation_allowed": _entry_route_mutation_allowed(mode_id),
                "claim_ceiling": _entry_route_claim_ceiling(mode_id),
                "first_command": (
                    "PYTHONPATH=src python3 -m idea_microcosm.cli "
                    f"query-entry-routes --root . --band card --ids entry_route.{mode_id}"
                ),
                "next_commands": _entry_route_next_commands(mode_id),
                "authority_boundary": (
                    "Entry-route cards choose the next surface before leaf, code, or release drilldown; "
                    "receipts, validators, source files, and release gates remain authority."
                ),
                "omission_receipt": {
                    "omitted": ["source bodies", "live git status", "external hosted-public evidence"],
                    "reason": "Entry-route cards orient a cold agent without replacing current validation or source authority.",
                    "drilldown": "AGENTS.md",
                },
                "anti_claims": [
                    "entry route selection grants publication permission",
                    "entry route selection proves hosted-public readiness",
                    "entry route selection replaces receipt or validator evidence",
                ],
            }
        )
    return rows


def _entry_route_surfaces() -> dict[str, list[dict[str, Any]]]:
    base_rows = _entry_route_mode_rows()
    clusters: list[dict[str, Any]] = []
    for cluster_id in sorted({row["cluster_id"] for row in base_rows}):
        cluster_rows = [row for row in base_rows if row["cluster_id"] == cluster_id]
        clusters.append(
            {
                "cluster_id": cluster_id,
                "band": "cluster_flag",
                "mode_count": len(cluster_rows),
                "mutation_mode_count": sum(1 for row in cluster_rows if row["mutation_allowed"]),
                "first_flag_refs": [f"entry_routes[row_id={row['row_id']}]" for row in cluster_rows],
                "authority_boundary": "Entry-route clusters group allowed first-hop modes; they are not locks or release gates.",
            }
        )
    flags = [
        {
            "row_id": row["row_id"],
            "mode_id": row["mode_id"],
            "band": "flag",
            "cluster_id": row["cluster_id"],
            "title": row["title"],
            "when": row["when"],
            "mutation_allowed": row["mutation_allowed"],
            "claim_ceiling": row["claim_ceiling"],
            "card_ref": f"entry_routes.cards[row_id={row['row_id']}]",
        }
        for row in base_rows
    ]
    cards = [{**row, "band": "card"} for row in base_rows]
    return {"cluster_flag": clusters, "flag": flags, "card": cards}


def query_entry_routes(
    root: Path,
    *,
    band: str = "cluster_flag",
    ids: Sequence[str] | None = None,
    cluster: str | None = None,
    query: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Select the root operating mode before reviewer, leaf, code, or release drilldown.
    - Guarantee: Returns compressed clusters, mode flags, or one actionable mode card without opening source.
    - Fails: Raises ValueError for unknown bands.
    - When-needed: Open at cold start, especially when deciding whether to orient, verify claims, edit one leaf, coordinate concurrent work, or review release posture.
    - Escalates-to: navigation/entry_packet.json; microcosms/leaf_entry_contract.json; microcosms/concurrency_mission_control/README.md
    """
    if band not in ROOT_ENTRY_ROUTE_BANDS:
        raise ValueError(f"band must be one of {', '.join(ROOT_ENTRY_ROUTE_BANDS)}")
    _ = root.resolve()
    surfaces = _entry_route_surfaces()
    source_rows = surfaces[band]
    selected = _filter_rows(
        [row for row in source_rows if isinstance(row, dict)],
        ids=ids,
        cluster=cluster,
        query=query,
    )
    bounded_limit = max(1, int(limit))
    rows = selected[:bounded_limit]
    return {
        "kind": "root_entry_route_query",
        "schema_version": "root_entry_route_query_v0",
        "authority_posture": "entry_route_projection_not_source_or_release_authority",
        "band": band,
        "band_order": list(ROOT_ENTRY_ROUTE_BANDS),
        "source_refs": ROOT_ENTRY_ROUTE_MAP_BRIDGE["source_refs"],
        "filters": {
            "ids": list(ids or []),
            "cluster": cluster,
            "query": query,
            "limit": bounded_limit,
        },
        "summary": {
            "source_row_count": len(source_rows),
            "matched_row_count": len(selected),
            "returned_row_count": len(rows),
            "truncated": len(selected) > len(rows),
        },
        "rows": rows,
        "next": [
            {
                "band": "flag",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-entry-routes --root . --band flag --cluster <cluster_id>",
                "when": "After selecting a route cluster.",
            },
            {
                "band": "card",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-entry-routes --root . --band card --ids <row_id>",
                "when": "After selecting one entry mode.",
            },
            {
                "band": "validate",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
                "when": "Before strengthening any root, leaf, hosted-public, or publication claim.",
            },
        ],
        "anti_claims": [
            "entry routes are mutation locks",
            "entry routes prove hosted-public readiness",
            "entry routes grant publication permission",
        ],
    }


def _route_composition_base_rows() -> list[dict[str, Any]]:
    rows = [
        {
            "row_id": "route_surface.entry_modes",
            "surface_id": "entry_modes",
            "route_id": "query-entry-routes",
            "cluster_id": "route_family.entry",
            "title": "Root Entry Modes",
            "surface_kind": "query",
            "command": ROOT_ENTRY_ROUTE_MAP_BRIDGE["query_command"],
            "owner_bridge_ref": "navigation/entry_packet.json::root_entry_route_map",
            "available_bands": list(ROOT_ENTRY_ROUTE_BANDS),
            "first_band": "cluster_flag",
            "reads": ROOT_ENTRY_ROUTE_MAP_BRIDGE["source_refs"],
            "writes": [],
            "mutation_policy": "read_only_mode_selection",
            "shared_surface_risk": "none",
            "claim_ceiling": "selects_next_surface_only",
            "next_when": "Use first when the operator role is unclear or before reviewer, leaf, diagnostic, or release drilldown.",
            "downstream_commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-entry-routes --root . --band card --ids entry_route.<mode_id>",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band cluster_flag",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-pattern-routes --root . --band cluster_flag",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-command-latency-inventory --root . --slow-only",
            ],
            "route_order": [
                "choose entry mode",
                "open that mode card",
                "follow its next_commands",
                "validate before strengthening claims",
            ],
            "authority_boundary": "Entry-mode routing chooses an operating posture. It does not mutate, lock, validate, or approve release language.",
            "anti_claims": [
                "entry-mode card is a work lock",
                "entry-mode selection proves any receipt",
                "entry-mode selection grants release or publication permission",
            ],
        },
        {
            "row_id": "route_surface.leaf_code_routes",
            "surface_id": "leaf_code_routes",
            "route_id": "query-leaf-code-routes",
            "cluster_id": "route_family.leaf_code",
            "title": "Leaf To Code Routes",
            "surface_kind": "query",
            "command": LEAF_CODE_ROUTE_BRIDGE["query_command"],
            "owner_bridge_ref": "navigation/entry_packet.json::leaf_code_route_bridge",
            "available_bands": list(LEAF_CODE_ROUTE_BANDS),
            "first_band": "cluster_flag",
            "reads": LEAF_CODE_ROUTE_BRIDGE["source_refs"],
            "writes": [],
            "mutation_policy": "read_only_leaf_to_code_selection",
            "shared_surface_risk": "source_span_requires_one_selected_leaf",
            "claim_ceiling": "leaf_local_navigation_projection",
            "next_when": "Use after selecting one leaf, one entry-track cluster, or one reviewer route.",
            "downstream_commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band card --ids leaf_code_route.<leaf_id>",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band card --cluster microcosm_leaf.<leaf_id>",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-code-navigation --root . --band card --cluster microcosm_leaf.<leaf_id>",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band source_span --ids leaf_code_route.<leaf_id>",
            ],
            "examples": LEAF_CODE_ROUTE_BRIDGE["card_examples"],
            "route_order": [
                "leaf contract row",
                "summary ladder row",
                "leaf receipt or probe",
                "std_python card",
                "source span only after selecting one leaf",
            ],
            "authority_boundary": LEAF_CODE_ROUTE_BRIDGE["boundary"],
            "anti_claims": [
                "leaf-code route is source authority",
                "leaf-code route proves standalone wrapper readiness",
                "leaf-code route grants hosted-public or publication permission",
            ],
        },
        {
            "row_id": "route_surface.std_python_navigation",
            "surface_id": "std_python_navigation",
            "route_id": "query-std-python",
            "route_aliases": ["query-code-navigation"],
            "cluster_id": "route_family.source_drilldown",
            "title": "Std Python Navigation",
            "surface_kind": "query",
            "command": STD_PYTHON_POPULATION_BRIDGE["query_command"],
            "owner_bridge_ref": "navigation/entry_packet.json::std_python_population_bridge",
            "available_bands": list(STD_PYTHON_NAVIGATION_BANDS),
            "first_band": "cluster_flag",
            "reads": [STD_PYTHON_NAVIGATION_REPORT, STD_PYTHON_POPULATION_BRIDGE["local_standard"]],
            "writes": [],
            "mutation_policy": "read_only_code_card_and_source_span_selection",
            "shared_surface_risk": "source_span_requires_one_selected_card",
            "claim_ceiling": "implementation_drilldown_projection",
            "next_when": "Use after a leaf, pattern, diagnostic, or route card names a std_python cluster or scope ref.",
            "downstream_commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band card --ids <row_id>",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-code-navigation --root . --band card --ids <row_id>",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band source_span --ids <row_id>",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-code-navigation --root . --band source_span --ids <row_id>",
            ],
            "route_order": [
                "cluster",
                "flag",
                "card",
                "source span",
                "source file remains authority",
            ],
            "authority_boundary": "std_python rows are generated code-navigation projections; source files and tests remain authority.",
            "anti_claims": [
                "std_python row is source authority",
                "std_python compliance proves hosted-public readiness",
                "std_python source span grants publication permission",
            ],
        },
        {
            "row_id": "route_surface.macro_pattern_routes",
            "surface_id": "macro_pattern_routes",
            "route_id": "query-pattern-routes",
            "cluster_id": "route_family.pattern",
            "title": "Macro Pattern Routes",
            "surface_kind": "query",
            "command": MACRO_PATTERN_ROUTE_BRIDGE["query_command"],
            "owner_bridge_ref": "navigation/entry_packet.json::macro_pattern_route_bridge",
            "available_bands": list(MACRO_PATTERN_ROUTE_BANDS),
            "first_band": "cluster_flag",
            "reads": MACRO_PATTERN_ROUTE_BRIDGE["source_refs"],
            "writes": [],
            "mutation_policy": "read_only_pattern_to_leaf_selection",
            "shared_surface_risk": "none",
            "claim_ceiling": "clean_room_pattern_route_projection",
            "next_when": "Use when mining ambitious macro-system patterns into local leaves, port packets, receipts, and code cards.",
            "downstream_commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-pattern-routes --root . --band card --ids <row_id>",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band card --ids <related_std_python_scope_ref>",
            ],
            "route_order": [
                "pattern capability cluster",
                "pattern flag",
                "pattern card",
                "port packet or std_python card",
            ],
            "authority_boundary": MACRO_PATTERN_ROUTE_BRIDGE["boundary"],
            "anti_claims": [
                "macro-pattern route copies private source",
                "macro-pattern route is doctrine authority",
                "macro-pattern route grants publication permission",
            ],
        },
        {
            "row_id": "route_surface.upgrade_robust_projection_pattern",
            "surface_id": "upgrade_robust_projection_pattern",
            "route_id": "upgrade-robust-projection-pattern",
            "cluster_id": "route_family.pattern",
            "title": "Upgrade-Robust Projection Pattern",
            "surface_kind": "pattern_contract",
            "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-route-composition --root . --band card --ids route_surface.upgrade_robust_projection_pattern",
            "owner_bridge_ref": "navigation/entry_packet.json::upgrade_robust_projection_pattern",
            "available_bands": ["card"],
            "first_band": "card",
            "reads": UPGRADE_ROBUST_PROJECTION_PATTERN["source_refs"],
            "writes": [],
            "mutation_policy": "read_owner_projection_then_refresh_builder_or_receipt",
            "shared_surface_risk": "do_not_edit_generated_projection_or_strengthen_claim_from_prose",
            "claim_ceiling": UPGRADE_ROBUST_PROJECTION_PATTERN["claim_ceiling"],
            "next_when": "Use when a root, leaf, generated projection, or summary is expected to drift but still needs stable agent wiring.",
            "downstream_commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli build-atlas-navigation-bands-specimen --root . --write-receipt",
                "PYTHONPATH=src python3 -m idea_microcosm.cli build-artifact-manifest --root . --write-receipt",
                "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
            ],
            "route_order": UPGRADE_ROBUST_PROJECTION_PATTERN["route_order"],
            "authority_boundary": UPGRADE_ROBUST_PROJECTION_PATTERN["fact_boundary"],
            "anti_claims": UPGRADE_ROBUST_PROJECTION_PATTERN["anti_claims"],
        },
        {
            "row_id": "route_surface.diagnostic_latency_inventory",
            "surface_id": "diagnostic_latency_inventory",
            "route_id": "query-command-latency-inventory",
            "cluster_id": "route_family.diagnostics",
            "title": "Diagnostic Latency Inventory",
            "surface_kind": "query",
            "command": DIAGNOSTIC_ROUTE_BRIDGE["query_command"],
            "owner_bridge_ref": "navigation/entry_packet.json::diagnostic_route_bridge",
            "available_bands": ["ranked_rows"],
            "first_band": "ranked_rows",
            "reads": DIAGNOSTIC_ROUTE_BRIDGE["source_refs"],
            "writes": [],
            "mutation_policy": "read_only_fixture_diagnostic_selection",
            "shared_surface_risk": "source_span_requires_one_diagnostic_row",
            "claim_ceiling": "synthetic_fixture_diagnostic_only",
            "next_when": "Use when a command-speed, wait-tax, singleflight, or wrapper-readiness question appears.",
            "downstream_commands": [
                DIAGNOSTIC_ROUTE_BRIDGE["query_command"],
                DIAGNOSTIC_ROUTE_BRIDGE["code_card_command"],
                DIAGNOSTIC_ROUTE_BRIDGE["source_span_command"],
            ],
            "examples": DIAGNOSTIC_ROUTE_BRIDGE["card_examples"],
            "route_order": DIAGNOSTIC_ROUTE_BRIDGE["route_order"],
            "authority_boundary": DIAGNOSTIC_ROUTE_BRIDGE["boundary"],
            "anti_claims": DIAGNOSTIC_ROUTE_BRIDGE["anti_claims"],
        },
        {
            "row_id": "route_surface.command_concurrency",
            "surface_id": "command_concurrency",
            "route_id": "query-command-concurrency",
            "cluster_id": "route_family.diagnostics",
            "title": "Command Concurrency Join",
            "surface_kind": "query",
            "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-command-concurrency --root . --duplicates-only",
            "owner_bridge_ref": "src/idea_microcosm/cli.py::COMMAND_CONCURRENCY_ROUTE_BRIDGE",
            "available_bands": ["joined_rows"],
            "first_band": "joined_rows",
            "reads": [
                "microcosms/concurrency_mission_control/mission_board.json",
                "microcosms/meta_diagnostics_workbench/diagnostic_board.json::command_latency_inventory",
            ],
            "writes": [],
            "mutation_policy": "read_only_duplicate_command_selection",
            "shared_surface_risk": "duplicate_command_rows_route_to_attach_or_reuse_policy_before_new_command_launch",
            "claim_ceiling": "synthetic_fixture_concurrency_diagnostic_only",
            "next_when": "Use when an agent is about to launch validation or sees duplicate command-key pressure.",
            "downstream_commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-command-concurrency --root . --duplicates-only",
                "PYTHONPATH=src python3 -m idea_microcosm.cli query-command-latency-inventory --root . --slow-only --limit 5",
                "PYTHONPATH=src python3 -m idea_microcosm.cli plan-fast-validation --root . --path <changed-path>",
            ],
            "route_order": [
                "route composition diagnostics cluster",
                "command-concurrency joined rows",
                "duplicate command key",
                "latency inventory row",
                "fast validation plan before broad command launch",
            ],
            "authority_boundary": "Command-concurrency rows are synthetic fixture joins over mission and latency boards; they are not live process tables, private session telemetry, hosted CI proof, or performance certification.",
            "anti_claims": [
                "command-concurrency row is a live process table",
                "duplicate command fixture proves runtime performance",
                "joined latency fixture grants hosted-public or publication permission",
            ],
        },
        {
            "row_id": "route_surface.task_ledger_capture_reflex",
            "surface_id": "task_ledger_capture_reflex",
            "route_id": "build-task-ledger-specimen:self_error_capture_repair_extension",
            "cluster_id": "route_family.settlement",
            "title": "Task Ledger Capture Reflex",
            "surface_kind": "builder_projection",
            "command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-task-ledger-specimen --root . --write-receipt",
            "owner_bridge_ref": "microcosms/task_ledger_cap_economy/projection.json::self_error_capture_repair_extension",
            "available_bands": ["extension_summary", "receipt"],
            "first_band": "extension_summary",
            "reads": [
                "microcosms/task_ledger_cap_economy/events.jsonl",
                "microcosms/concurrency_mission_control/provider_repair_bridge.json",
                "microcosms/task_ledger_cap_economy/projection.json::self_error_capture_repair_extension",
            ],
            "writes": [
                "microcosms/task_ledger_cap_economy/projection.json",
                "microcosms/task_ledger_cap_economy/receipt.json",
                "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json",
            ],
            "mutation_policy": "settles_task_ledger_leaf_only_then_validate",
            "shared_surface_risk": "capture_fixture_is_not_private_task_ledger_export_or_broad_staging_permission",
            "claim_ceiling": "fixture_validated_capture_before_prose_behavior_only",
            "next_when": "Use when a mistake, side finding, no-op stewardship result, or residual needs durable capture-before-prose behavior.",
            "downstream_commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli build-task-ledger-specimen --root . --write-receipt",
                "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
            ],
            "route_order": [
                "route composition settlement cluster",
                "task ledger capture-reflex card",
                "blocked_until_capture cases",
                "projection visibility validators",
                "receipt before closeout prose",
            ],
            "authority_boundary": "Task Ledger capture-reflex rows are synthetic public-safe fixture behavior; they are not private Task Ledger export, issue-tracker replacement authority, public-release approval, or publication permission.",
            "anti_claims": [
                "capture-reflex fixture exports private Task Ledger contents",
                "capture projection is source authority",
                "captured side finding authorizes broad staging",
                "capture receipt grants publication permission",
            ],
        },
        {
            "row_id": "route_surface.concurrency_settlement",
            "surface_id": "concurrency_settlement",
            "route_id": "build-concurrency-mission-control-specimen",
            "cluster_id": "route_family.settlement",
            "title": "Concurrency Settlement",
            "surface_kind": "builder",
            "command": ROOT_CONCURRENCY_GUARD["owner_command"],
            "owner_bridge_ref": "navigation/entry_packet.json::root_concurrency_guard",
            "available_bands": ["owner_command", "receipt"],
            "first_band": "owner_command",
            "reads": ROOT_CONCURRENCY_GUARD["evidence_refs"],
            "writes": [
                "microcosms/concurrency_mission_control/mission_board.json",
                "microcosms/concurrency_mission_control/receipt.json",
            ],
            "mutation_policy": "settles_concurrency_leaf_only_then_validate",
            "shared_surface_risk": "do_not_use_generated_reports_as_locks",
            "claim_ceiling": "fixture_validated_concurrency_guard",
            "next_when": "Use when concurrent work, owner selection, or residual carryforward needs a local settlement receipt.",
            "downstream_commands": [
                ROOT_CONCURRENCY_GUARD["owner_command"],
                ROOT_CONCURRENCY_GUARD["validation_command"],
            ],
            "route_order": ROOT_CONCURRENCY_GUARD["route_order"],
            "authority_boundary": "Concurrency settlement writes only the public-safe concurrency leaf artifacts; it does not coordinate live private missions.",
            "anti_claims": [
                *ROOT_CONCURRENCY_GUARD["do_not"],
                "concurrency settlement proves whole-root readiness",
                "concurrency settlement is a live private work lock",
            ],
        },
        {
            "row_id": "route_surface.root_validation",
            "surface_id": "root_validation",
            "route_id": "validate",
            "cluster_id": "route_family.settlement",
            "title": "Root Validation",
            "surface_kind": "validator",
            "command": "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
            "owner_bridge_ref": "receipts/validation_run.json",
            "available_bands": ["validator_summary", "receipt"],
            "first_band": "validator_summary",
            "reads": [
                "navigation/entry_packet.json",
                "navigation/microcosm_index.json",
                "state/artifact_manifest.json",
                "microcosms/*/receipt.json",
            ],
            "writes": ["receipts/validation_run.json when --write-receipt is passed"],
            "mutation_policy": "validation_only_or_receipt_write_when_requested",
            "shared_surface_risk": "shared_receipt_output_requires_owner_intent",
            "claim_ceiling": "local_root_validated_only",
            "next_when": "Use before strengthening any root, leaf, hosted-public, or publication claim.",
            "downstream_commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root . --write-receipt",
                "PYTHONPATH=src python3 -m idea_microcosm.cli build-artifact-manifest --root . --write-receipt",
            ],
            "route_order": [
                "run focused owner builder if a leaf changed",
                "validate root",
                "write receipt only as settlement output",
                "never upgrade hosted-public or publication claims without outside-world receipts",
            ],
            "authority_boundary": "Validation proves local fixture coherence only; hosted-public readiness and publication permission remain gated elsewhere.",
            "anti_claims": [
                "local validation proves hosted-public readiness",
                "local validation grants publication permission",
                "validation receipt replaces source or leaf receipts",
            ],
        },
        {
            "row_id": "route_surface.artifact_manifest_refresh",
            "surface_id": "artifact_manifest_refresh",
            "route_id": "build-artifact-manifest",
            "cluster_id": "route_family.settlement",
            "title": "Artifact Manifest Refresh",
            "surface_kind": "builder",
            "command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-artifact-manifest --root . --write-receipt",
            "owner_bridge_ref": "state/artifact_manifest.json",
            "available_bands": ["manifest_rows", "receipt"],
            "first_band": "manifest_rows",
            "reads": ["root file tree", "standards/artifact_manifest.json"],
            "writes": ["state/artifact_manifest.json", "receipts/artifact_manifest.json when --write-receipt is passed"],
            "mutation_policy": "refresh_after_file_add_remove_or_projection_shape_change",
            "shared_surface_risk": "shared_generated_output_settle_last",
            "claim_ceiling": "file_inventory_projection",
            "next_when": "Use after adding, removing, or reclassifying public microcosm files.",
            "downstream_commands": [
                "PYTHONPATH=src python3 -m idea_microcosm.cli build-artifact-manifest --root . --write-receipt",
                "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
            ],
            "route_order": [
                "finish source or leaf edits",
                "refresh manifest",
                "validate",
                "treat manifest as projection, not authority",
            ],
            "authority_boundary": "The artifact manifest is a generated file inventory; file contents and owner builders remain authority.",
            "anti_claims": [
                "manifest row is source authority",
                "manifest refresh proves release readiness",
                "manifest refresh grants publication permission",
            ],
        },
    ]
    return rows


def _route_example_ids(row: dict[str, Any]) -> list[str]:
    return [
        str(example["example_id"])
        for example in row.get("examples", [])
        if isinstance(example, dict) and example.get("example_id")
    ]


def _route_example_refs(row: dict[str, Any]) -> list[str]:
    if not _route_example_ids(row):
        return []
    return [f"route_composition.cards[row_id={row['row_id']}].examples"]


def _route_composition_surfaces() -> dict[str, list[dict[str, Any]]]:
    base_rows = _route_composition_base_rows()
    clusters: list[dict[str, Any]] = []
    for cluster_id in sorted({row["cluster_id"] for row in base_rows}):
        cluster_rows = [row for row in base_rows if row["cluster_id"] == cluster_id]
        example_ids = [
            example_id
            for row in cluster_rows
            for example_id in _route_example_ids(row)
        ]
        example_refs = [
            ref
            for row in cluster_rows
            for ref in _route_example_refs(row)
        ]
        clusters.append(
            {
                "cluster_id": cluster_id,
                "band": "cluster_flag",
                "route_surface_count": len(cluster_rows),
                "surface_kinds": sorted({str(row["surface_kind"]) for row in cluster_rows}),
                "mutation_surface_count": sum(1 for row in cluster_rows if row.get("writes")),
                "first_flag_refs": [f"route_composition[row_id={row['row_id']}]" for row in cluster_rows],
                "example_count": len(example_ids),
                "example_ids": example_ids,
                "example_card_refs": example_refs,
                "authority_boundary": "Route-composition clusters choose an owner surface; they do not replace that surface.",
            }
        )
    flags = [
        {
            "row_id": row["row_id"],
            "surface_id": row["surface_id"],
            "route_id": row["route_id"],
            "band": "flag",
            "cluster_id": row["cluster_id"],
            "title": row["title"],
            "surface_kind": row["surface_kind"],
            "command": row["command"],
            "mutation_policy": row["mutation_policy"],
            "claim_ceiling": row["claim_ceiling"],
            "card_ref": f"route_composition.cards[row_id={row['row_id']}]",
            "example_count": len(_route_example_ids(row)),
            "example_ids": _route_example_ids(row),
            "example_card_refs": _route_example_refs(row),
        }
        for row in base_rows
    ]
    cards = [{**row, "band": "card"} for row in base_rows]
    return {"cluster_flag": clusters, "flag": flags, "card": cards}


def query_route_composition(
    root: Path,
    *,
    band: str = "cluster_flag",
    ids: Sequence[str] | None = None,
    cluster: str | None = None,
    query: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Unify the microcosm's query, diagnostic, settlement, and validation routes into one owner-selection surface.
    - Guarantee: Returns clusters, flags, or cards for existing route surfaces without broad file search or live private telemetry.
    - Fails: Raises ValueError for unknown bands.
    - When-needed: Open when a cold or concurrent agent needs to decide which route surface owns the next action.
    - Escalates-to: navigation/entry_packet.json; navigation/microcosm_index.json; receipts/validation_run.json
    """
    if band not in ROUTE_COMPOSITION_BANDS:
        raise ValueError(f"band must be one of {', '.join(ROUTE_COMPOSITION_BANDS)}")
    _ = root.resolve()
    surfaces = _route_composition_surfaces()
    source_rows = surfaces[band]
    selected = _filter_rows(
        [row for row in source_rows if isinstance(row, dict)],
        ids=ids,
        cluster=cluster,
        query=query,
    )
    bounded_limit = max(1, int(limit))
    rows = selected[:bounded_limit]
    return {
        "kind": "route_composition_query",
        "schema_version": "route_composition_query_v0",
        "authority_posture": "route_composition_projection_not_source_lock_or_release_authority",
        "band": band,
        "band_order": list(ROUTE_COMPOSITION_BANDS),
        "source_refs": ROUTE_COMPOSITION_BRIDGE["source_refs"],
        "filters": {
            "ids": list(ids or []),
            "cluster": cluster,
            "query": query,
            "limit": bounded_limit,
        },
        "summary": {
            "source_row_count": len(source_rows),
            "matched_row_count": len(selected),
            "returned_row_count": len(rows),
            "truncated": len(selected) > len(rows),
        },
        "rows": rows,
        "next": [
            {
                "band": "flag",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-route-composition --root . --band flag --cluster <cluster_id>",
                "when": "After selecting a route family.",
            },
            {
                "band": "card",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-route-composition --root . --band card --ids <row_id>",
                "when": "After selecting one owner route surface.",
            },
            {
                "band": "validate",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
                "when": "Before strengthening any claim or after a settlement command writes shared outputs.",
            },
        ],
        "anti_claims": [
            "route composition is a lock manager",
            "route composition replaces receipts, validators, source files, or release gates",
            "route composition proves hosted-public readiness or grants publication permission",
        ],
    }


def query_std_python_navigation(
    root: Path,
    *,
    band: str = "cluster_flag",
    ids: Sequence[str] | None = None,
    cluster: str | None = None,
    query: str | None = None,
    limit: int = 20,
    report_path: str = STD_PYTHON_NAVIGATION_REPORT,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Query the release-local std_python navigation index as a tiny option-surface ladder.
    - Guarantee: Returns cluster, flag, card, or source-span rows without opening source bodies.
    - Fails: Raises file or JSON errors when the std_python report has not been built.
    - When-needed: Open when a cold agent has selected a root or leaf route and needs implementation drilldown without broad source search.
    - Escalates-to: microcosms/specimen_suite/std_python_compliance_report.json; src/idea_microcosm/release_root_compiler.py::build_std_python_report
    """
    if band not in STD_PYTHON_NAVIGATION_BANDS:
        raise ValueError(f"band must be one of {', '.join(STD_PYTHON_NAVIGATION_BANDS)}")
    root = root.resolve()
    report_ref = report_path
    report = json.loads((root / report_path).read_text(encoding="utf-8"))
    navigation_index = report.get("navigation_index") or {}
    if band == "cluster_flag":
        source_rows = navigation_index.get("clusters") or []
    elif band == "flag":
        source_rows = navigation_index.get("flags") or []
    elif band == "card":
        source_rows = navigation_index.get("cards") or []
    else:
        source_rows = _source_span_rows(report.get("scope_rows") or [])

    selected = _filter_rows(
        [row for row in source_rows if isinstance(row, dict)],
        ids=ids,
        cluster=cluster,
        query=query,
    )
    bounded_limit = max(1, int(limit))
    rows = selected[:bounded_limit]
    return {
        "kind": "std_python_navigation_query",
        "schema_version": "std_python_navigation_query_v0",
        "authority_posture": "generated_query_projection_not_source_authority",
        "band": band,
        "band_order": list(STD_PYTHON_NAVIGATION_BANDS),
        "report_ref": report_ref,
        "standard_ref": "codex/standards/std_python.py",
        "query_command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band cluster_flag",
        "query_aliases": [
            "PYTHONPATH=src python3 -m idea_microcosm.cli query-code-navigation --root . --band cluster_flag",
        ],
        "filters": {
            "ids": list(ids or []),
            "cluster": cluster,
            "query": query,
            "limit": bounded_limit,
        },
        "summary": {
            "source_row_count": len(source_rows),
            "matched_row_count": len(selected),
            "returned_row_count": len(rows),
            "truncated": len(selected) > len(rows),
        },
        "rows": rows,
        "next": [
            {
                "band": "flag",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band flag --cluster <cluster_id>",
                "alias": "PYTHONPATH=src python3 -m idea_microcosm.cli query-code-navigation --root . --band flag --cluster <cluster_id>",
                "when": "After selecting a cluster.",
            },
            {
                "band": "card",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band card --ids <row_id>",
                "alias": "PYTHONPATH=src python3 -m idea_microcosm.cli query-code-navigation --root . --band card --ids <row_id>",
                "when": "After selecting a flag row.",
            },
            {
                "band": "source_span",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band source_span --ids <row_id>",
                "alias": "PYTHONPATH=src python3 -m idea_microcosm.cli query-code-navigation --root . --band source_span --ids <row_id>",
                "when": "Only for mutation, proof, or ambiguity resolution.",
            },
        ],
        "anti_claims": [
            "code navigation rows are source authority",
            "std_python navigation proves hosted public readiness",
            "local diagnostics certify private-root-wide compliance",
        ],
    }


def query_leaf_code_routes(
    root: Path,
    *,
    band: str = "cluster_flag",
    ids: Sequence[str] | None = None,
    cluster: str | None = None,
    query: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Join leaf entry rows to std_python cards so a cold agent can move from one selected microcosm to exact code.
    - Guarantee: Returns entry-track clusters, leaf flags, leaf cards, or leaf-scoped source spans without opening source bodies.
    - Fails: Raises file or JSON errors when the leaf contract or std_python report has not been built.
    - When-needed: Open after choosing a leaf, reviewer route, or summary ladder row and before broad source traversal.
    - Escalates-to: microcosms/leaf_entry_contract.json; microcosms/specimen_suite/std_python_compliance_report.json
    """
    if band not in LEAF_CODE_ROUTE_BANDS:
        raise ValueError(f"band must be one of {', '.join(LEAF_CODE_ROUTE_BANDS)}")
    root = root.resolve()
    surfaces = _leaf_code_route_surfaces(root)
    source_rows = surfaces[band]
    selected = _filter_rows(
        [row for row in source_rows if isinstance(row, dict)],
        ids=ids,
        cluster=cluster,
        query=query,
    )
    bounded_limit = max(1, int(limit))
    rows = selected[:bounded_limit]
    return {
        "kind": "leaf_code_route_query",
        "schema_version": "leaf_code_route_query_v0",
        "authority_posture": "leaf_code_navigation_projection_not_source_authority",
        "band": band,
        "band_order": list(LEAF_CODE_ROUTE_BANDS),
        "source_refs": [
            "microcosms/leaf_entry_contract.json",
            "microcosms/summary_ladders/summary_ladders.json",
            STD_PYTHON_NAVIGATION_REPORT,
        ],
        "filters": {
            "ids": list(ids or []),
            "cluster": cluster,
            "query": query,
            "limit": bounded_limit,
        },
        "summary": {
            "source_row_count": len(source_rows),
            "matched_row_count": len(selected),
            "returned_row_count": len(rows),
            "truncated": len(selected) > len(rows),
        },
        "rows": rows,
        "next": [
            {
                "band": "flag",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band flag --cluster <cluster_id>",
                "when": "After selecting an entry-track cluster.",
            },
            {
                "band": "card",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band card --ids <row_id>",
                "when": "After selecting a leaf flag.",
            },
            {
                "band": "source_span",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band source_span --ids <row_id>",
                "when": "Only after a leaf-code card selects one leaf for proof or mutation.",
            },
        ],
        "anti_claims": [
            "leaf-code route rows are source authority",
            "code-card availability proves standalone leaf export",
            "leaf-local receipt grants hosted-public or publication permission",
        ],
    }


def query_macro_pattern_routes(
    root: Path,
    *,
    band: str = "cluster_flag",
    ids: Sequence[str] | None = None,
    cluster: str | None = None,
    query: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Route macro-system patterns through the microcosm's existing blueprint, leaf, receipt, and std_python surfaces.
    - Guarantee: Returns cluster, flag, or card rows that join source pattern refs to local implementation drilldowns.
    - Fails: Raises file or JSON errors when pattern, blueprint, packet, or index sources are absent.
    - When-needed: Open when deciding which ambitious private-system pattern is represented by a leaf or source module.
    - Escalates-to: registry/internal_pattern_inventory.json; modules/module_blueprints.json; ports/port_packets.json; microcosms/specimen_suite/std_python_compliance_report.json
    """
    if band not in MACRO_PATTERN_ROUTE_BANDS:
        raise ValueError(f"band must be one of {', '.join(MACRO_PATTERN_ROUTE_BANDS)}")
    root = root.resolve()
    surfaces = _macro_pattern_route_surfaces(root)
    source_rows = surfaces[band]
    selected = _filter_rows(
        [row for row in source_rows if isinstance(row, dict)],
        ids=ids,
        cluster=cluster,
        query=query,
    )
    bounded_limit = max(1, int(limit))
    rows = selected[:bounded_limit]
    return {
        "kind": "macro_pattern_route_query",
        "schema_version": "macro_pattern_route_query_v0",
        "authority_posture": "clean_room_pattern_route_projection_not_source_authority",
        "band": band,
        "band_order": list(MACRO_PATTERN_ROUTE_BANDS),
        "source_refs": [
            "registry/internal_pattern_inventory.json",
            "registry/annex_patterns.json",
            "modules/module_blueprints.json",
            "ports/port_packets.json",
            "navigation/microcosm_index.json",
            STD_PYTHON_NAVIGATION_REPORT,
        ],
        "filters": {
            "ids": list(ids or []),
            "cluster": cluster,
            "query": query,
            "limit": bounded_limit,
        },
        "summary": {
            "source_row_count": len(source_rows),
            "matched_row_count": len(selected),
            "returned_row_count": len(rows),
            "truncated": len(selected) > len(rows),
        },
        "rows": rows,
        "next": [
            {
                "band": "flag",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-pattern-routes --root . --band flag --cluster <cluster_id>",
                "when": "After selecting a macro-pattern capability cluster.",
            },
            {
                "band": "card",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-pattern-routes --root . --band card --ids <row_id>",
                "when": "After selecting a pattern row.",
            },
            {
                "band": "code",
                "command": "PYTHONPATH=src python3 -m idea_microcosm.cli query-std-python --root . --band card --ids <related_std_python_scope_ref>",
                "when": "Only after the pattern card names a related std_python scope ref.",
            },
        ],
        "anti_claims": [
            "macro pattern route rows are private-source copies",
            "module blueprints are source authority",
            "pattern-route evidence grants publication permission",
        ],
    }


def build_navigation(root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Regenerate the idea atlas and card projections that cold agents read before source.
    - Guarantee: Writes atlas, entry packet, and one card per idea graph row.
    - Fails: Raises file or JSON errors when the source idea graph is absent or malformed.
    - When-needed: Open when debugging entry-packet contents, card generation, or a navigation projection freshness issue.
    - Escalates-to: state/idea_graph.json; navigation/entry_packet.json; navigation/atlas.json
    """
    root = root.resolve()
    idea_graph = json.loads((root / "state" / "idea_graph.json").read_text(encoding="utf-8"))
    implementation_atlas = build_microcosm_implementation_atlas(root)
    leaf_entry_contract = build_leaf_entry_contract_projection(root, implementation_atlas=implementation_atlas)
    ideas = idea_graph["ideas"]
    rows = []
    cards_dir = root / "cards"
    cards_dir.mkdir(exist_ok=True)
    for idea in ideas:
        card_path = f"cards/{_safe_slug(idea['id'])}.md"
        rows.append(
            {
                "idea_id": idea["id"],
                "cluster": str(idea["type"]).replace("idea_type.", ""),
                "claim": idea["claim"],
                "card": card_path,
                "source_ref": "state/idea_graph.json",
                "standard_refs": idea.get("standard_refs", []),
                "validator_refs": idea.get("validators", []),
                "next_moves": idea.get("next_moves", []),
            }
        )
        (root / card_path).write_text(_card(idea), encoding="utf-8")
    atlas = {
        "kind": "idea_atlas",
        "schema_version": "idea_atlas_v0",
        "authority_posture": "projection_not_authority",
        "source_authority": "state/idea_graph.json",
        "rows": rows,
    }
    constellation_routes = [
        {
            "route_id": "core_status_boundary",
            "reviewer_question": "What is the core claim?",
            "first_refs": [
                "microcosms/status_preserving_control_plane/README.md",
                "fixtures/status/status_collapse_adversarial_suite.json",
            ],
            "run_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-status-preserving-control-plane-specimen --root . --write-receipt",
            "proves": "source, interpretation, work, receipt, projection, review, hosted, public, and publication status do not collapse",
            "anti_claim": "status proof is fixture-level and does not grant public release or private-root equivalence",
        },
        {
            "route_id": "durable_work_boundary",
            "reviewer_question": "How does work survive context loss?",
            "first_refs": [
                "microcosms/task_ledger_cap_economy/README.md",
                "microcosms/concurrency_mission_control/README.md",
            ],
            "run_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-task-ledger-specimen --root . --write-receipt",
            "proves": "events, projections, receipts, residual routes, and transaction claims remain separate",
            "anti_claim": "synthetic work rows are not the private Task Ledger",
        },
        {
            "route_id": "cold_agent_boundary",
            "reviewer_question": "How should a cold agent enter?",
            "first_refs": [
                "AGENTS.md",
                "navigation/microcosm_index.json",
                "microcosms/summary_ladders/summary_ladders.json",
                "microcosms/concept_graph_cards/cold_entry_atlas.json",
                "microcosms/self_comprehension_navigator/README.md",
            ],
            "run_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-self-comprehension-navigator-specimen --root . --write-receipt",
            "proves": "agents route through entry packets, bands, cards, receipts, and owner surfaces before broad source traversal",
            "anti_claim": "public entry packets are not the private bootstrap",
        },
        {
            "route_id": "sandbox_system_boundary",
            "reviewer_question": "What proves this is a runnable system sandbox rather than release packaging?",
            "first_refs": [
                "sandbox/microcosm_sandbox_gate.json",
                "strategy/microcosm_teleology_gate.json",
                "strategy/microcosm_reconstruction_posture.json",
                "microcosms/concurrency_mission_control/README.md",
                "microcosms/meta_diagnostics_workbench/README.md",
            ],
            "run_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
            "proves": "claims, leases, diagnostics, receipts, and validation stay inside the active sandbox ontology",
            "anti_claim": "sandbox validation is not release packaging, hosted-public proof, or publication permission",
        },
        {
            "route_id": "control_surface_boundary",
            "reviewer_question": "What can I inspect visually?",
            "first_refs": [
                "microcosms/frontend_cockpit_hud/README.md",
                "microcosms/status_preserving_control_plane/README.md",
                "microcosms/meta_diagnostics_workbench/README.md",
            ],
            "run_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-frontend-hud-control-surface-specimen --root . --write-receipt",
            "proves": "visual control surfaces display status, diagnostics, and receipts without becoming evidence authority",
            "anti_claim": "UI state is not source authority, sandbox proof, or publication evidence",
        },
        {
            "route_id": "diagnostic_specimen_boundary",
            "reviewer_question": "How does it handle evaluator or benchmark-shaped evidence?",
            "first_refs": [
                "microcosms/provider_harness_canary/README.md",
                "microcosms/lab_evolve_failure_replay/README.md",
                "microcosms/verisoftbench_diagnostic/README.md",
            ],
            "run_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-provider-harness-canary-specimen --root . --write-receipt",
            "proves": "provider output, evaluator decision, schema validity, failure replay, and benchmark-shaped diagnosis stay typed",
            "anti_claim": "diagnostic fixtures are not benchmark wins or external evaluator endorsements",
        },
    ]
    entry_packet = {
        "kind": "idea_microcosm_entry_packet",
        "schema_version": "entry_packet_v0",
        "authority_posture": "navigation_projection_not_source_authority",
        "release_object": "public_safe_beta_microcosm_constellation",
        "first_move": "Read AGENTS.md, then strategy gates, then this packet, then microcosm_index, then the leaf entry contract, then summary ladders, then the selected route card, then source authority.",
        "root_primitive": "Idea",
        "core_claim": idea_graph.get("core_claim", "Ideas become standards, navigation, work, receipts, strategy, and release gates."),
        "root_entry_contract": ROOT_ENTRY_CONTRACT,
        "root_concurrency_guard": ROOT_CONCURRENCY_GUARD,
        "root_entry_route_map": {**ROOT_ENTRY_ROUTE_MAP_BRIDGE, "rows": _entry_route_mode_rows()},
        "route_composition_bridge": {**ROUTE_COMPOSITION_BRIDGE, "rows": _route_composition_base_rows()},
        "upgrade_robust_projection_pattern": UPGRADE_ROBUST_PROJECTION_PATTERN,
        "implementation_atlas": implementation_atlas,
        "leaf_implementation_navigation_bridge": leaf_entry_contract.get("implementation_navigation_bridge", {}),
        "root_navigation_ladder": ROOT_NAVIGATION_LADDER,
        "std_python_population_bridge": STD_PYTHON_POPULATION_BRIDGE,
        "summary_ladder_bridge": SUMMARY_LADDER_BRIDGE,
        "macro_pattern_route_bridge": MACRO_PATTERN_ROUTE_BRIDGE,
        "leaf_code_route_bridge": LEAF_CODE_ROUTE_BRIDGE,
        "diagnostic_route_bridge": DIAGNOSTIC_ROUTE_BRIDGE,
        "start_here": [
            "AGENTS.md",
            "strategy/seed.md",
            "strategy/microcosm_teleology_gate.json",
            "strategy/microcosm_reconstruction_posture.json",
            "sandbox/microcosm_sandbox_gate.json",
            "navigation/entry_packet.json",
            "navigation/microcosm_index.json",
            "microcosms/leaf_entry_contract.json",
            "microcosms/summary_ladders/summary_ladders.json",
            "microcosms/README.md",
            "release/microcosm_constellation.json",
            "navigation/atlas.json",
            "state/idea_graph.json",
            "state/artifact_manifest.json",
            "state/principle_enforcement_matrix.json",
            "state/teleology_map.json",
            "state/axiom_kernel.json",
            "registry/internal_pattern_inventory.json",
            "modules/module_blueprints.json",
            "ports/port_packets.json",
            "runs/work_packets/dogfood_operator_prompt.json",
            "fixtures/ideas/synthetic_autonomous_seed.json",
            "strategy/strategy.json",
            "receipts/autonomous_seed_fixture.json",
            "receipts/seed_projection.json",
        ],
        "exogenous_agent_entry": {
            "purpose": "Let a cold external agent inspect or modify this public-safe root without private context.",
            "modes": EXOGENOUS_AGENT_ENTRY_MODES,
            "route_order": [
                "read AGENTS.md for operating rules",
                "read strategy and sandbox gates for current posture before retired release framing",
                "read navigation/microcosm_index.json before opening leaf folders",
                "read microcosms/leaf_entry_contract.json before treating any leaf as standalone or root-backed",
                "read microcosms/summary_ladders/summary_ladders.json for the smallest useful leaf summaries",
                "if concurrent editing is possible, select one leaf or root compiler owner before mutation",
                "use query-route-composition when the next owner surface is unclear",
                "use upgrade_robust_projection_pattern when current facts may drift but the route must stay stable",
                "choose one constellation route by reviewer question",
                "run validate or the route command before strengthening any claim",
                "if files change, rebuild state/artifact_manifest.json and rerun validate",
            ],
            "one_command_smoke": "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
            "do_not": [
                "do not infer private-root capability from public fixtures",
                "do not use rank, README copy, screenshots, or cards as release permission",
                "do not use generated root reports as coordination locks",
                "do not add files without refreshing the artifact manifest",
                "do not claim hosted-public readiness unless hosted receipts prove it",
            ],
        },
        "organisation_model": ORGANISATION_MODEL,
        "claim_strength_ladder": CLAIM_STRENGTH_LADDER,
        "constellation_routes": constellation_routes,
        "leaf_contract": {
            "parent_root": "self-indexing-cognitive-substrate/",
            "machine_readable_contract": "microcosms/leaf_entry_contract.json",
            "governing_standard": "standards/leaf_entry_contract.json",
            "standalone_clone_posture": "leaf_inspectable_root_rebuildable",
            "leaf_must_name": [
                "organ_proved",
                "public_files",
                "one_command_run_or_inspect_path",
                "receipt_path",
                "validator_or_probe",
                "purpose_edges",
                "anti_claims",
                "release_gate",
            ],
            "standalone_clone_protocol": [
                "a leaf README plus primary board/fixture plus receipt is enough for local inspection",
                "parent-root standards, validators, and registries remain lineage refs until the full root is present",
                "rebuilds and stronger claims must happen from the parent root with validate --root .",
                "leaf-local evidence never proves hosted-public readiness, publication permission, or private-root equivalence",
            ],
            "composition_rule": "Parent-root indexes compose leaves but never upgrade a leaf beyond local receipt and validator evidence.",
            "root_composition_rule": "The root compresses and composes leaf evidence; standalone leaves remain inspectable shards until the root wrapper rebuilds and validates them.",
            "clone_posture_rule": "Root-backed execution is supported now; standalone leaf exports require an explicit wrapper projection.",
            "implementation_navigation_bridge": leaf_entry_contract.get("implementation_navigation_bridge", {}),
            "single_leaf_wrapper_protocol": leaf_entry_contract.get("single_leaf_wrapper_protocol", {}),
            "summary": leaf_entry_contract.get("summary", {}),
        },
        "legal_drilldowns": [
            {"surface": "microcosm index", "path": "navigation/microcosm_index.json", "reason": "release-local leaf routing by band and reviewer question"},
            {"surface": "idea graph", "path": "state/idea_graph.json", "reason": "source authority for fixture ideas"},
            {"surface": "artifact manifest", "path": "state/artifact_manifest.json", "reason": "file-type projection map for every public file"},
            {"surface": "principle enforcement", "path": "state/principle_enforcement_matrix.json", "reason": "proof that axioms and principles became executable gates"},
            {"surface": "teleology", "path": "state/teleology_map.json", "reason": "purpose-pressure map from axioms and principles to deliverables, modules, receipts, and next moves"},
            {"surface": "axiom kernel", "path": "state/axiom_kernel.json", "reason": "agent-actionable rules compiled from principles and candidate axioms"},
            {"surface": "internal pattern inventory", "path": "registry/internal_pattern_inventory.json", "reason": "architecture-pattern source rows before module blueprints, not a new pattern authority plane"},
            {"surface": "summary ladders", "path": "microcosms/summary_ladders/summary_ladders.json", "reason": "one-sentence through deep summaries for every leaf before proof/code drilldown"},
            {"surface": "microcosm teleology gate", "path": "strategy/microcosm_teleology_gate.json", "reason": "machine-readable distinction between active system-organ leaves and downstream release support"},
            {"surface": "microcosm reconstruction posture", "path": "strategy/microcosm_reconstruction_posture.json", "reason": "provisional 10/10 coherence bar and pattern-population dependency before final ontology"},
            {"surface": "microcosm sandbox gate", "path": "sandbox/microcosm_sandbox_gate.json", "reason": "active sandbox command and leaf allowlist before release or website surfaces"},
            {"surface": "route composition query", "path": "PYTHONPATH=src python3 -m idea_microcosm.cli query-route-composition --root . --band cluster_flag", "reason": "typed owner selection across entry, leaf-code, std_python, pattern, diagnostics, concurrency settlement, and validation surfaces"},
            {"surface": "upgrade-robust projection pattern", "path": "navigation/entry_packet.json::upgrade_robust_projection_pattern", "reason": "keeps drift-prone projections fact-bound, receipt-bound, and claim-ceiling-bound before source or prose upgrades"},
            {"surface": "root entry route query", "path": "PYTHONPATH=src python3 -m idea_microcosm.cli query-entry-routes --root . --band cluster_flag", "reason": "banded route from cold-entry mode to reviewer, leaf, code, or release drilldown"},
            {"surface": "implementation atlas", "path": "navigation/microcosm_index.json::implementation_atlas", "reason": "compressed all-leaf code map before choosing one leaf-code or std_python card"},
            {"surface": "leaf code route query", "path": "PYTHONPATH=src python3 -m idea_microcosm.cli query-leaf-code-routes --root . --band cluster_flag", "reason": "banded route from selected leaf to std_python cards, receipts, and exact source spans"},
            {"surface": "macro pattern route query", "path": "PYTHONPATH=src python3 -m idea_microcosm.cli query-pattern-routes --root . --band cluster_flag", "reason": "banded bridge from macro-pattern rows to local leaves, port packets, std_python cards, and receipts"},
            {"surface": "diagnostic route bridge", "path": "PYTHONPATH=src python3 -m idea_microcosm.cli query-command-latency-inventory --root . --slow-only", "reason": "public-safe command-speed and wait-tax diagnostics before live telemetry, broad process search, or source mutation"},
            {"surface": "standards", "path": "registry/standards.json", "reason": "read and write contracts"},
            {"surface": "std_python report", "path": "microcosms/specimen_suite/std_python_compliance_report.json", "reason": "implementation drilldown from root or leaf routes to file rows, scope cards, and source spans"},
            {"surface": "work", "path": "state/work_items.jsonl", "reason": "ordered next moves"},
            {"surface": "module blueprints", "path": "modules/module_blueprints.json", "reason": "clean porting contracts for source logic"},
            {"surface": "port packets", "path": "ports/port_packets.json", "reason": "cold-agent implementation packets for each module blueprint"},
            {"surface": "work packets", "path": "runs/work_packets/dogfood_operator_prompt.json", "reason": "operator prompt compiled into selected ideas, rules, packets, validators, receipts, and next moves"},
            {"surface": "autonomous seed", "path": "fixtures/ideas/synthetic_autonomous_seed.json", "reason": "public-safe autonomous seed fixture and no-release boundary"},
            {"surface": "strategy", "path": "strategy/strategy.json", "reason": "autonomous seed and pivot rules"},
            {"surface": "proof", "path": "receipts/", "reason": "claim-strength receipts"},
            {"surface": "release", "path": "release/publication_gate.json", "reason": "fail-closed publication posture"},
        ],
        "omissions": idea_graph.get("non_goals", []),
        "cold_agent_rule": "Do not infer governance from folders. Route from Idea to Standard to Receipt to WorkItem.",
    }
    (root / "navigation" / "atlas.json").write_text(json.dumps(atlas, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "navigation" / "entry_packet.json").write_text(json.dumps(entry_packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "ok", "atlas_rows": len(rows), "cards_written": len(rows)}
