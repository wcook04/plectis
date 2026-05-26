"""
Registry of generated projection owners and their deterministic repair lanes.

[PURPOSE]
- Teleology: Keep generated projection drift repair narrow and owner-directed.
- Mechanism: Declare artifact owners, selected outputs, no-write check command,
  and the exact builder command allowed to repair that owner.
- Non-goal: This registry does not execute builders or decide semantic drift.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fnmatch import fnmatchcase
from typing import Iterable


@dataclass(frozen=True)
class GeneratedProjectionOwner:
    owner_id: str
    description: str
    artifacts: tuple[str, ...]
    source_authorities: tuple[str, ...]
    check_command: tuple[str, ...]
    repair_command: tuple[str, ...]
    manual_edit_boundary: str
    deterministic_regeneration_expectation: str
    stale_drift_handling: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


PROJECTION_REGISTRY: tuple[GeneratedProjectionOwner, ...] = (
    GeneratedProjectionOwner(
        owner_id="agent_entry_surface",
        description="Agent bootstrap/live instruction regions and bootstrap sidecars.",
        artifacts=(
            "AGENTS.md",
            "AGENTS.override.md",
            "CLAUDE.md",
            "CODEX.md",
            "codex/doctrine/agent_bootstrap_live.json",
            "codex/doctrine/agent_bootstrap_injection_strip.json",
        ),
        source_authorities=(
            "codex/doctrine/agent_bootstrap.json",
            "system/lib/agent_bootstrap_projection.py",
            "tools/meta/factory/build_agent_bootstrap_projection.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/check_agent_bootstrap_projection.py"),
        repair_command=("./repo-python", "tools/meta/factory/build_agent_bootstrap_projection.py"),
        manual_edit_boundary="Do not hand-edit managed instruction regions or bootstrap sidecars; mutate agent_bootstrap source authority and rerun the builder.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce artifacts from source_authorities for the current worktree.",
        stale_drift_handling="Run check_command before landing generated artifacts; on drift, rerun repair_command and land source-authority changes with generated outputs.",
    ),
    GeneratedProjectionOwner(
        owner_id="routing_hologram",
        description="Routing hologram JSON and managed agent routing markdown region.",
        artifacts=("codex/doctrine/routing_hologram.json", "AGENTS.md"),
        source_authorities=(
            "codex/doctrine/routing_anti_patterns.json",
            "codex/doctrine/skills/kernel/delegation_protocol.md",
            "codex/doctrine/skills/kernel/wave_conductor.md",
            "codex/doctrine/skills/skill_registry.json",
            "codex/standards/observe_apply/std_synth_seed.json",
            "state/agent_telemetry/latest_full/routing_candidates.json",
            "system/lib/routing_projection.py",
            "tools/meta/factory/build_routing_projection.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/build_routing_projection.py", "--check", "--target", "all"),
        repair_command=("./repo-python", "tools/meta/factory/build_routing_projection.py", "--target", "all"),
        manual_edit_boundary="Do not hand-edit routing_hologram.json or managed AGENTS routing regions; mutate routing source inputs and rerun the routing projection builder.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the routing projection from source_authorities for the current worktree.",
        stale_drift_handling="Treat dirty source inputs plus regenerated artifacts as coupled; do not land generated routing targets without the dirty source inputs that produced them.",
    ),
    GeneratedProjectionOwner(
        owner_id="skill_catalog",
        description="Skill catalog Rosetta seed, full skill-map browse projection, and generated Agent Skill facades.",
        artifacts=(
            "AGENTS.md",
            "codex/doctrine/skills/skill_map.md",
            ".agents/skills/*/SKILL.md",
            ".agents/skills/.ai_workflow_generated.json",
        ),
        source_authorities=(
            "codex/doctrine/skills/skill_registry.json",
            "system/lib/agent_bootstrap_projection.py",
            "system/lib/skill_surfaces.py",
            "tools/meta/factory/_skill_projection.py",
            "tools/meta/factory/build_skill_catalog_projection.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/build_skill_catalog_projection.py", "--check", "--target", "all"),
        repair_command=("./repo-python", "tools/meta/factory/build_skill_catalog_projection.py", "--target", "all"),
        manual_edit_boundary="Do not hand-edit generated skill-map, skill-catalog instruction blocks, Agent Skill facades, or the generated Agent Skill manifest; mutate skill_registry/source rendering rows and rerun the catalog builder.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce catalog artifacts from skill_registry source authority.",
        stale_drift_handling="Run check_command before landing catalog artifacts; if skill_registry or skill rendering code is dirty, land it with generated catalog outputs or leave outputs unstaged.",
    ),
    GeneratedProjectionOwner(
        owner_id="doctrine_graph_projection",
        description="Compiled doctrine graph, compiler IR, section units, and graph-adjacent doctrine projections.",
        artifacts=(
            "codex/doctrine/doctrine_graph.json",
            "codex/doctrine/doctrine_compiler_ir.json",
            "codex/doctrine/doctrine_section_units.json",
            "codex/doctrine/doctrine_surface.json",
            "codex/doctrine/doctrine_index.json",
            "codex/doctrine/doctrine_routing.json",
        ),
        source_authorities=(
            "obsidian/okay lets do this/*/raw_seed/raw_seed_principles.json",
            "codex/doctrine/concepts/*.json",
            "codex/doctrine/mechanisms/*.json",
            "codex/doctrine/skills/skill_registry.json",
            "codex/doctrine/resources/*.json",
            "codex/doctrine/components/*.md",
            "codex/doctrine/doctrine_approved_overlay.json",
            "system/lib/doctrine_graph.py",
            "tools/meta/factory/build_doctrine_graph_projection.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/build_doctrine_graph_projection.py", "--check"),
        repair_command=("./repo-python", "tools/meta/factory/build_doctrine_graph_projection.py"),
        manual_edit_boundary="Do not hand-edit compiled doctrine graph projections; mutate authored doctrine inputs, approved overlay state, or the compiler, then rerun the doctrine graph projection builder.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce normalized doctrine graph artifacts from authored doctrine sources for the current worktree.",
        stale_drift_handling="Run check_command before landing doctrine projection artifacts; on drift, rerun repair_command and land the authored source or compiler changes with regenerated doctrine outputs.",
    ),
    GeneratedProjectionOwner(
        owner_id="frontend_api_type_projection",
        description="Frontend OpenAPI JSON and TypeScript API sidecars generated from the live FastAPI app.",
        artifacts=(
            "system/server/ui/src/api/generated/openapi.json",
            "system/server/ui/src/api/generated/types.ts",
        ),
        source_authorities=(
            "system/server/main.py",
            "system/server/schemas.py",
            "tools/meta/factory/build_api_type_projection.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/build_api_type_projection.py", "--check"),
        repair_command=("./repo-python", "tools/meta/factory/build_api_type_projection.py"),
        manual_edit_boundary="Do not hand-edit generated OpenAPI or TypeScript API files; mutate FastAPI/schema sources and rerun the API type projection builder.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce generated API artifacts from the live FastAPI schema.",
        stale_drift_handling="Run check_command before frontend/API landings; on drift, regenerate and land schema/source changes with generated API sidecars.",
    ),
    GeneratedProjectionOwner(
        owner_id="frontend_navigation_graph_projection",
        description="Frontend route, surface, overlay, and capture navigation graph generated from cockpit source surfaces.",
        artifacts=(
            "state/frontend_navigation/navigation_graph.json",
            "state/frontend_navigation/navigation_graph.snapshot.md",
            "state/frontend_navigation/surface_relation_audit.v1.json",
            "state/frontend_navigation/wayfinding_capability_matrix.v1.json",
            "state/frontend_navigation/wayfinding_scenario_frontier.v1.json",
            "state/frontend_navigation/navigation_mission_control.v1.json",
        ),
        source_authorities=(
            "system/server/ui/src/App.tsx",
            "system/server/ui/src/navigation/surfaces.ts",
            "system/server/ui/src/navigation/overlays.ts",
            "system/server/ui/src/pages/StationLens.tsx",
            "tools/meta/observability/station_views.json",
            "tools/meta/observability/wayfinding_scenarios.json",
            "state/observability/render_load_index.json",
            "state/frontend_navigation/semantic_layer.v1.json",
            "state/frontend_navigation/component_index.json",
            "tools/meta/observability/frontend_nav_graph.py",
        ),
        check_command=("./repo-python", "tools/meta/observability/frontend_nav_graph.py", "--check"),
        repair_command=("./repo-python", "tools/meta/observability/frontend_nav_graph.py", "--write"),
        manual_edit_boundary="Do not hand-edit frontend navigation graph artifacts; mutate the route/surface/capture authorities or the graph builder, then rerun frontend_nav_graph.py --write.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the navigation graph JSON and snapshot markdown from the declared frontend navigation source authorities.",
        stale_drift_handling="Run check_command before landing frontend navigation graph artifacts; on drift, rerun repair_command and land source-authority changes with regenerated graph outputs.",
    ),
    GeneratedProjectionOwner(
        owner_id="frontend_component_index_projection",
        description="Frontend component browse index generated from exported TSX components.",
        artifacts=("state/frontend_navigation/component_index.json",),
        source_authorities=(
            "system/server/ui/src/**/*.tsx",
            "codex/standards/std_frontend_component_index.json",
            "tools/meta/observability/frontend_component_index.py",
        ),
        check_command=("./repo-python", "tools/meta/observability/frontend_component_index.py", "--check"),
        repair_command=("./repo-python", "tools/meta/observability/frontend_component_index.py", "--write"),
        manual_edit_boundary="Do not hand-edit component_index.json; mutate frontend TSX sources, the component-index standard, or the extractor, then rerun frontend_component_index.py --write.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce component_index.json from exported TSX components and the governing component-index standard.",
        stale_drift_handling="Run check_command before landing component index changes; on drift, rerun repair_command and land source-authority changes with the regenerated index.",
    ),
    GeneratedProjectionOwner(
        owner_id="work_ledger_index_projection",
        description="Per-phase Work Ledger read indexes generated from Work Ledger JSONL authority.",
        artifacts=("codex/ledger/*/work_ledger_index.json",),
        source_authorities=(
            "codex/ledger/*/work_ledger.jsonl",
            "tools/meta/factory/work_ledger.py",
            "system/lib/work_ledger_runtime.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/work_ledger.py", "project", "--check", "--all"),
        repair_command=("./repo-python", "tools/meta/factory/work_ledger.py", "project", "--all"),
        manual_edit_boundary="Do not hand-edit work_ledger_index.json; append Work Ledger events or fix the projector, then rerun projection.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce indexes from Work Ledger JSONL authority.",
        stale_drift_handling="Run check_command before landing Work Ledger projections; on drift, rerun repair_command and land the authority event log with generated indexes.",
    ),
    GeneratedProjectionOwner(
        owner_id="task_ledger_projection",
        description="Task Ledger read model and queue views generated from the Task Ledger event log.",
        artifacts=(
            "state/task_ledger/ledger.json",
            "state/task_ledger/sign_offs.json",
            "state/task_ledger/views/*.json",
        ),
        source_authorities=(
            "state/task_ledger/events.jsonl",
            "system/lib/task_ledger_events.py",
            "tools/meta/factory/task_ledger_apply.py",
            "tools/meta/factory/task_ledger_project.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/task_ledger_apply.py", "rebuild", "--check"),
        repair_command=("./repo-python", "tools/meta/factory/task_ledger_apply.py", "rebuild"),
        manual_edit_boundary="Do not hand-edit Task Ledger projections; append Task Ledger events or fix the projector, then rebuild projections.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce ledger.json, sign_offs.json, and views from state/task_ledger/events.jsonl.",
        stale_drift_handling="Run check_command before landing Task Ledger projections; on drift, rerun repair_command and land the event log with generated projections through the serial drainer lane.",
    ),
    GeneratedProjectionOwner(
        owner_id="imagination_index_projection",
        description="Imagination browse and validation sidecars generated from authored imagination markdown.",
        artifacts=(
            "codex/doctrine/imaginations/_index.json",
            "codex/doctrine/imaginations/_validation_report.json",
        ),
        source_authorities=(
            "codex/doctrine/imaginations/imn_*.md",
            "codex/standards/std_imagination.json",
            "codex/doctrine/skills/doctrine/imagination_authoring.md",
            "tools/meta/factory/build_imagination_index.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_imagination_index.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_imagination_index.py",
            "--write",
        ),
        manual_edit_boundary="Do not hand-edit imagination index sidecars; mutate authored imn_*.md files, std_imagination, the authoring skill, or the builder, then rerun build_imagination_index.py --write.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the imagination index and validation report from authored imagination markdown and std_imagination for the current worktree.",
        stale_drift_handling="Run check_command before landing imagination sidecars; on drift, rerun repair_command and land the authored imagination changes with the regenerated sidecars.",
    ),
    GeneratedProjectionOwner(
        owner_id="navigation_type_plane_projection",
        description="Queryable standard type-plane graph, index, and gap projection generated from std_standard_type_plane.",
        artifacts=(
            "state/navigation_type_plane/type_plane_graph.json",
            "state/navigation_type_plane/type_plane_index.json",
            "state/navigation_type_plane/type_plane_gaps.json",
        ),
        source_authorities=(
            "codex/standards/std_standard_type_plane.json",
            "system/lib/navigation_type_plane.py",
            "tools/meta/factory/build_navigation_type_plane.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/build_navigation_type_plane.py", "--check"),
        repair_command=("./repo-python", "tools/meta/factory/build_navigation_type_plane.py"),
        manual_edit_boundary="Do not hand-edit generated type-plane graph, index, or gaps; mutate std_standard_type_plane rows or the builder, then rerun the builder.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce graph, index, and gap projections from std_standard_type_plane for the current worktree.",
        stale_drift_handling="Run check_command before landing type-plane projections; on drift, rerun repair_command and land source-authority changes with generated outputs.",
    ),
    GeneratedProjectionOwner(
        owner_id="renderer_passport_projection",
        description="Renderer passport projection generated from standard type-plane rows and renderer profiles.",
        artifacts=("state/navigation_type_plane/renderer_passports.json",),
        source_authorities=(
            "codex/standards/std_standard_type_plane.json",
            "system/lib/renderer_passports.py",
            "tools/meta/factory/build_renderer_passports.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/build_renderer_passports.py", "--check"),
        repair_command=("./repo-python", "tools/meta/factory/build_renderer_passports.py"),
        manual_edit_boundary="Do not hand-edit generated renderer passports; mutate type-plane rows, renderer profiles, or the builder, then rerun the builder.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce renderer_passports.json from standard type-plane rows and renderer profiles.",
        stale_drift_handling="Run check_command before landing renderer passports; on drift, rerun repair_command and land source-authority changes with generated outputs.",
    ),
    GeneratedProjectionOwner(
        owner_id="generated_artifact_surface_summary_projection",
        description="Generated-artifact option-surface row counts materialized for the Kind Atlas hot path.",
        artifacts=("codex/hologram/generated_artifact_surfaces/kind_atlas_summary.json",),
        source_authorities=(
            "codex/standards/std_kind_atlas.json",
            "system/lib/generated_artifact_surface_summary.py",
            "system/lib/kernel/commands/generated_artifact_surfaces.py",
            "system/lib/artifact_projection_debt.py",
            "tools/meta/factory/build_generated_artifact_surface_summary.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/build_generated_artifact_surface_summary.py", "--check"),
        repair_command=("./repo-python", "tools/meta/factory/build_generated_artifact_surface_summary.py"),
        manual_edit_boundary="Do not hand-edit the generated-artifact Kind Atlas summary; mutate option-surface owners or the summary builder, then rerun build_generated_artifact_surface_summary.py.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce kind_atlas_summary.json from supported generated-artifact option surfaces for the current worktree.",
        stale_drift_handling="Run check_command before trusting materialized generated-artifact counts; on drift or missing summary, rerun repair_command and keep Kind Atlas as the cheap read-model consumer.",
    ),
    GeneratedProjectionOwner(
        owner_id="system_atlas_projection",
        description="System Atlas graph, summary, facts, governing-doctrine, unknown-queue, and dissemination gate projections.",
        artifacts=(
            "state/system_atlas/system_atlas.graph.json",
            "state/system_atlas/system_atlas_summary.json",
            "state/system_atlas/system_facts_at_a_glance.json",
            "state/system_atlas/dissemination_gate_report.json",
            "docs/system_atlas/generated_system_atlas_snapshot.md",
            "docs/system_atlas/generated_system_facts_at_a_glance.md",
            "docs/system_atlas/atlas_governing_doctrine.generated.md",
            "docs/system_atlas/unknown_unknowns_queue.generated.md",
            "docs/system_atlas/dissemination_gate_report.generated.md",
        ),
        source_authorities=(
            "codex/standards/std_system_atlas.json",
            "codex/standards/std_standard_type_plane.json",
            "codex/doctrine/paper_modules/_index.json",
            "codex/doctrine/paper_modules/_validation_report.json",
            "codex/doctrine/paper_modules/_route_coverage.json",
            "codex/doctrine/skills/skill_registry.json",
            "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json",
            "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json",
            "state/task_ledger/ledger.json",
            "state/task_ledger/views/*.json",
            "state/frontend_navigation/navigation_graph.json",
            "state/frontend_navigation/component_index.json",
            "tools/meta/factory/build_system_atlas.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/build_system_atlas.py", "--check"),
        repair_command=("./repo-python", "tools/meta/factory/build_system_atlas.py"),
        manual_edit_boundary="Do not hand-edit generated System Atlas projections; mutate the declared source authorities or the atlas builder, then rerun build_system_atlas.py.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce System Atlas graph, summaries, facts, governing-doctrine, queue, and dissemination projections from declared source authorities for the current worktree.",
        stale_drift_handling="Run check_command before trusting System Atlas projections; on source-coupling drift, repair through the source owner first, then rerun repair_command and land coupled source and generated outputs intentionally.",
    ),
    GeneratedProjectionOwner(
        owner_id="station_render_load_index_projection",
        description="Station render timing/load index generated by the Station render capture owner.",
        artifacts=("state/observability/render_load_index.json",),
        source_authorities=(
            "tools/meta/observability/station_render.py",
            "tools/meta/observability/station_views.json",
            "system/server/ui/src/**/*",
        ),
        check_command=(
            "./repo-python",
            "-m",
            "tools.meta.observability.station_render",
            "timings",
            "--limit",
            "20",
            "--json",
        ),
        repair_command=(
            "./repo-python",
            "-m",
            "tools.meta.observability.station_render",
            "render",
            "--view",
            "<view>",
            "--viewport",
            "<viewport>",
            "--engine",
            "<engine>",
        ),
        manual_edit_boundary="Do not hand-edit render_load_index.json; inspect timing metadata through station_render timings and add rows through focused station_render capture runs.",
        deterministic_regeneration_expectation="repair_command records metadata-only load timing rows from a focused Station render capture; raw browser output and visual artifacts remain outside this index.",
        stale_drift_handling="Use check_command as the fast read model before trusting load timings; when stale or missing, run a focused render for the affected view/viewport/engine instead of broad matrix capture.",
    ),
    GeneratedProjectionOwner(
        owner_id="compliance_ledger_projection",
        description="Cross-standard compliance digest generated from compliance adapters and Python compliance coverage.",
        artifacts=("codex/hologram/compliance/ledger.json",),
        source_authorities=(
            "codex/standards/std_compliance_coverage.json",
            "codex/standards/std_python_compliance_coverage.json",
            "state/meta_missions/python_std_compliance_authoring/python_std_compliance_coverage.json",
            "system/lib/compliance",
            "system/lib/standards_inventory.py",
            "tools/meta/factory/build_compliance_ledger.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/build_compliance_ledger.py", "--check"),
        repair_command=("./repo-python", "tools/meta/factory/build_compliance_ledger.py"),
        manual_edit_boundary="Do not hand-edit the compliance ledger projection; mutate compliance adapters, standards inventory, or the builder, then rerun build_compliance_ledger.py.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce codex/hologram/compliance/ledger.json from registered compliance adapters and Python compliance coverage for the current worktree.",
        stale_drift_handling="Run check_command before trusting compliance ledger navigation rows; on missing or stale projection, rerun repair_command and treat standard_projection_gaps as the discovery surface until the ledger exists.",
    ),
    GeneratedProjectionOwner(
        owner_id="standard_skill_map_projection",
        description="Per-standard skill pairing projection generated from skill_registry and standards inventory.",
        artifacts=("codex/hologram/skills/standard_skill_map.json",),
        source_authorities=(
            "codex/doctrine/skills/skill_registry.json",
            "codex/standards/**/*.json",
            "system/lib/standards_inventory.py",
            "tools/meta/factory/build_standard_skill_map.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/build_standard_skill_map.py", "--check"),
        repair_command=("./repo-python", "tools/meta/factory/build_standard_skill_map.py"),
        manual_edit_boundary="Do not hand-edit the standard-skill map projection; mutate skill_registry governing_standard_ids, standards inventory, or the builder, then rerun build_standard_skill_map.py.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce codex/hologram/skills/standard_skill_map.json from skill_registry and the shared standards inventory for the current worktree.",
        stale_drift_handling="Run check_command before trusting standard-skill map navigation rows; on missing or stale projection, rerun repair_command and keep missing_authoring_skill rows as read-model output, not source authority.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_research_operations_capability_map_projection",
        description="Formal-math research operations capability map generated from local proof, benchmark, routing, and Task Ledger receipt surfaces.",
        artifacts=(
            "state/formal_math_research_operations/capability_map.json",
            "state/formal_math_research_operations/capability_map_receipt.json",
            "docs/formal_math/generated_research_operations_capability_map.md",
        ),
        source_authorities=(
            "codex/doctrine/paper_modules/mathematics_mission_pipeline.md",
            "codex/doctrine/paper_modules/formal_maths_direction_atlas.md",
            "codex/doctrine/missions/prover_lab.md",
            "codex/doctrine/missions/prover_oracle.md",
            "codex/doctrine/missions/prover_evolve.md",
            "state/prover/residual_corpus_index.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/proofline_spine.json",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/result_board.json",
            "state/task_ledger/ledger.json",
            "tools/meta/factory/build_formal_math_research_operations_map.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_research_operations_map.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_research_operations_map.py",
        ),
        manual_edit_boundary="Do not hand-edit the formal-math research operations capability map, receipt, or markdown projection; update source receipts, Task Ledger state, or the builder, then rerun build_formal_math_research_operations_map.py.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the capability map, receipt, and markdown projection from local formal-math receipts plus dated external-source snapshot rows embedded in the builder.",
        stale_drift_handling="Run check_command before using the map to authorize provider spend or real-problem pilots; on drift, rerun the builder and land source-authority changes with generated outputs.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_erdos257_issue217_pilot_dossier_projection",
        description="Erdos #257 / teorth issue #217 pilot dossier generated as a claim-reconciliation and formalization-audit packet.",
        artifacts=(
            "state/formal_math_research_operations/pilots/erdos257_issue217/dossier.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/dossier_receipt.json",
            "docs/formal_math/generated_erdos257_issue217_pilot_dossier.md",
        ),
        source_authorities=(
            "state/formal_math_research_operations/capability_map.json",
            "tools/meta/factory/build_formal_math_research_operations_map.py",
            "tools/meta/factory/build_formal_math_erdos257_issue217_pilot_dossier.py",
            "https://www.erdosproblems.com/257",
            "https://www.erdosproblems.com/forum/thread/257",
            "https://github.com/google-deepmind/formal-conjectures/blob/main/FormalConjectures/ErdosProblems/257.lean",
            "https://github.com/teorth/erdosproblems/issues/217",
            "https://github.com/danuaemx/leanformal257",
            "https://zenodo.org/records/18321596",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_erdos257_issue217_pilot_dossier.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_erdos257_issue217_pilot_dossier.py",
        ),
        manual_edit_boundary="Do not hand-edit the Erdos #257 pilot dossier JSON, receipt, or markdown projection; update the dossier builder and rerun build_formal_math_erdos257_issue217_pilot_dossier.py.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the pilot dossier from the capability map and dated external-source snapshot rows embedded in the builder.",
        stale_drift_handling="Run check_command before using the dossier to authorize provider proof work; on source freshness changes, update the builder snapshot intentionally and regenerate outputs.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_erdos257_issue217_obligation_dag_projection",
        description="Erdos #257 / issue #217 proof-audit obligation DAG and finite adversarial stress harness generated from the pilot dossier.",
        artifacts=(
            "state/formal_math_research_operations/pilots/erdos257_issue217/obligation_dag.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/obligation_dag_receipt.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/finite_stress_harness.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/finite_stress_harness_receipt.json",
            "docs/formal_math/generated_erdos257_issue217_obligation_dag.md",
        ),
        source_authorities=(
            "state/formal_math_research_operations/pilots/erdos257_issue217/dossier.json",
            "tools/meta/factory/build_formal_math_erdos257_issue217_pilot_dossier.py",
            "tools/meta/factory/build_formal_math_erdos257_issue217_obligation_dag.py",
            "tools/meta/factory/run_formal_math_erdos257_finite_stress_harness.py",
            "https://zenodo.org/records/18321596",
            "https://github.com/danuaemx/leanformal257",
            "https://github.com/google-deepmind/formal-conjectures/blob/main/FormalConjectures/ErdosProblems/257.lean",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_erdos257_issue217_obligation_dag.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_erdos257_issue217_obligation_dag.py",
        ),
        manual_edit_boundary="Do not hand-edit the Erdos #257 obligation DAG, finite stress harness, receipts, or markdown projection; update the owning builders and rerun build_formal_math_erdos257_issue217_obligation_dag.py.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the obligation DAG and finite stress harness from the pilot dossier, embedded source snapshots, and deterministic finite probes.",
        stale_drift_handling="Run check_command before using the DAG to authorize provider critique packets; on source freshness changes, update builders intentionally and regenerate outputs.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_erdos257_period_noncollapse_strike_projection",
        description="Finite period-noncollapse theorem-strike projection generated from the Erdos #257 obligation DAG and finite stress harness.",
        artifacts=(
            "state/formal_math_research_operations/pilots/erdos257_issue217/period_noncollapse_strike.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/period_noncollapse_strike_receipt.json",
            "docs/formal_math/generated_erdos257_period_noncollapse_strike.md",
        ),
        source_authorities=(
            "state/formal_math_research_operations/pilots/erdos257_issue217/obligation_dag.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/finite_stress_harness.json",
            "tools/meta/factory/build_formal_math_erdos257_issue217_obligation_dag.py",
            "tools/meta/factory/run_formal_math_erdos257_finite_stress_harness.py",
            "tools/meta/factory/run_formal_math_erdos257_period_noncollapse_strike.py",
            "https://zenodo.org/records/18321596",
            "https://en.wikipedia.org/wiki/Zsigmondy%27s_theorem",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/run_formal_math_erdos257_period_noncollapse_strike.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/run_formal_math_erdos257_period_noncollapse_strike.py",
        ),
        manual_edit_boundary="Do not hand-edit the Erdos #257 period non-collapse strike JSON, receipt, or markdown projection; update the strike builder and rerun run_formal_math_erdos257_period_noncollapse_strike.py.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the strike projection from the obligation DAG, finite stress harness, and bounded finite certificate search.",
        stale_drift_handling="Run check_command before authorizing provider council packets or promoting a Lean target from the finite strike.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_erdos257_issue217_formal_evidence_cells_projection",
        description="Formal Evidence Cell manifest generated from the Erdos #257 pilot strike, dossier, obligation DAG, and capability receipts.",
        artifacts=(
            "state/formal_math_research_operations/pilots/erdos257_issue217/formal_evidence_cells.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/formal_evidence_cells_receipt.json",
            "docs/formal_math/generated_erdos257_issue217_formal_evidence_cells.md",
        ),
        source_authorities=(
            "state/formal_math_research_operations/pilots/erdos257_issue217/period_noncollapse_strike.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/period_noncollapse_strike_receipt.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/dossier_receipt.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/obligation_dag_receipt.json",
            "state/formal_math_research_operations/capability_map_receipt.json",
            "tools/meta/factory/build_formal_math_erdos257_issue217_formal_evidence_cells.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_erdos257_issue217_formal_evidence_cells.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_erdos257_issue217_formal_evidence_cells.py",
        ),
        manual_edit_boundary="Do not hand-edit the Erdos #257 formal-evidence-cell manifest, receipt, or markdown projection; update the pilot receipts or builder, then rerun build_formal_math_erdos257_issue217_formal_evidence_cells.py.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the cell manifest, receipt, and markdown projection from the current pilot receipts.",
        stale_drift_handling="Run check_command before trusting the pilot cell manifest or landing registry outputs that consume it; on source freshness changes, rerun repair_command and land the manifest plus dependent registry projections.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_evidence_cell_registry_projection",
        description="Formal evidence cell registry generated from registered formal-math cell manifests and experiment receipts.",
        artifacts=(
            "state/formal_math_research_operations/formal_evidence_cell_registry.json",
            "state/formal_math_research_operations/formal_evidence_cell_registry_receipt.json",
            "docs/formal_math/generated_formal_evidence_cell_registry.md",
        ),
        source_authorities=(
            "codex/standards/std_paper_module.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/formal_evidence_cells.json",
            "state/formal_math_research_operations/pilots/erdos257_issue217/formal_evidence_cells_receipt.json",
            "state/formal_math_research_operations/experiment_receipts/*.json",
            "tools/meta/factory/build_formal_math_evidence_cell_registry.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_evidence_cell_registry.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_evidence_cell_registry.py",
        ),
        manual_edit_boundary="Do not hand-edit the formal evidence cell registry, receipt, or markdown projection; update registered manifests, experiment receipts, std_paper_module formal-evidence contract, or the registry builder, then rerun build_formal_math_evidence_cell_registry.py.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the registry, receipt, and markdown projection from registered formal-evidence manifests and experiment receipts for the current worktree.",
        stale_drift_handling="Run check_command before trusting formal-evidence cell inventory or landing registry outputs; on drift, rerun repair_command and land the relevant manifest, receipt, standard, or builder changes with generated outputs.",
    ),
    GeneratedProjectionOwner(
        owner_id="lean_mathematics_microcosm_projection",
        description="Dynamic Lean mathematics microcosm generated from local Lean projects, formal-math operation receipts, docs, and tests.",
        artifacts=(
            "state/system_atlas/lean_mathematics_microcosm.json",
            "state/system_atlas/lean_mathematics_microcosm_receipt.json",
            "docs/system_atlas/lean_mathematics_microcosm.generated.md",
        ),
        source_authorities=(
            "formal_math/**/*.lean",
            "formal_math/**/lakefile.*",
            "formal_math/**/lean-toolchain",
            "formal_math/**/lake-manifest.json",
            "state/formal_math_research_operations/**/*.json",
            "docs/formal_math/*.md",
            "system/server/tests/test_formal_math*.py",
            "tools/meta/factory/build_lean_mathematics_microcosm_projection.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_lean_mathematics_microcosm_projection.py",
            "--check",
            "--compact",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_lean_mathematics_microcosm_projection.py",
            "--write",
            "--compact",
        ),
        manual_edit_boundary="Do not hand-edit the Lean mathematics microcosm projection, receipt, or markdown; update formal-math source surfaces or the builder, then rerun build_lean_mathematics_microcosm_projection.py --write.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the dynamic Lean microcosm from local Lean project files, formal-math operation receipts, generated docs, and tests.",
        stale_drift_handling="Run check_command before trusting the Lean microcosm as a current route surface; on drift, rerun repair_command and land source-authority changes with generated outputs.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_residual_corpus_index_projection",
        description="Private formal-math residual corpus index generated from InitialFailureScoreRun residual candidates and traces.",
        artifacts=(
            "state/prover/residual_corpus_index.json",
            "state/prover/residual_corpus_index_receipt.json",
        ),
        source_authorities=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/latest.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_*/decision_point_traces.jsonl",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_*/failure_score_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_*/residual_candidates.jsonl",
            "tools/meta/factory/build_formal_math_residual_corpus_index.py",
        ),
        check_command=("./repo-python", "tools/meta/factory/build_formal_math_residual_corpus_index.py", "--check"),
        repair_command=("./repo-python", "tools/meta/factory/build_formal_math_residual_corpus_index.py"),
        manual_edit_boundary="Do not hand-edit the residual corpus index artifacts; mutate InitialFailureScoreRun receipts or the index builder, then rerun the builder.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the private residual index and receipt from tracked failure-score runs plus the current latest run.",
        stale_drift_handling="Run check_command before landing the residual index; on drift, rerun the builder and land the relevant run receipts with the generated index.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_proofline_spine_projection",
        description="Private formal-math Lab-to-Oracle proofline spine generated from formal-math receipts and residual projections.",
        artifacts=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/proofline_spine.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/proofline_spine_receipt.json",
        ),
        source_authorities=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/latest.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_*/failure_score_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_*/decision_point_traces.jsonl",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_*/oracle_ingress_selection_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_*/oracle_ingress_microgate_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_*/formal_problem_resolution_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_*/oracle_ingress_adapter_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_*/oracle_environment_gate_receipt.json",
            "state/prover/residual_corpus_index.json",
            "state/prover/residual_corpus_index_receipt.json",
            "tools/meta/factory/build_formal_math_proofline_spine.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_proofline_spine.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_proofline_spine.py",
        ),
        manual_edit_boundary="Do not hand-edit the proofline spine artifacts; mutate the formal-math receipts, residual index, or spine builder, then rerun the builder.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the private proofline spine and receipt from formal-math Lab, adapter, environment, and residual receipts.",
        stale_drift_handling="Run check_command before landing the proofline spine; on drift, rerun the builder and land the relevant receipt changes with the generated spine.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_proof_repair_lane_projection",
        description="Private formal-math one-row proof-repair lane contract generated from the proofline spine, adapter, and environment-gate receipts.",
        artifacts=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_input_packet.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_receipt.json",
        ),
        source_authorities=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/proofline_spine.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/proofline_spine_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/oracle_ingress_adapter_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/oracle_environment_gate_receipt.json",
            "state/task_ledger/ledger.json",
            "tools/meta/factory/build_formal_math_proof_repair_lane.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_proof_repair_lane.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_proof_repair_lane.py",
        ),
        manual_edit_boundary="Do not hand-edit proof repair lane artifacts; mutate proofline/adapter/environment receipts or the repair-lane builder, then rerun the builder.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the one-row repair input packet and lane receipt from the current proofline, adapter, environment, and WorkItem state.",
        stale_drift_handling="Run check_command before landing proof repair lane artifacts; on drift, rerun repair_command and land the relevant receipt changes with the generated repair lane.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_proof_repair_attempt_projection",
        description="Private one-shot proof-repair invocation receipts generated from the formal-math repair lane packet and evaluated through the ArkLib Lake/Lean environment.",
        artifacts=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_model_inventory_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_model_canary_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_attempt_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_attempt_transform_job_manifest.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_attempt_dispatch_manifest.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_attempt_transform_jobs/state/compute_workers/transform_jobs/2026-05/*.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_attempt_environment_reducer/*/*.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_attempt_environment_reducer/*/*.txt",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_attempt_environment_reducer/*/*.lean",
        ),
        source_authorities=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_input_packet.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/proofline_spine.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/oracle_ingress_adapter_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/oracle_environment_gate_receipt.json",
            "state/task_ledger/ledger.json",
            "tools/meta/factory/run_formal_math_proof_repair_attempt.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/run_formal_math_proof_repair_attempt.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/run_formal_math_proof_repair_attempt.py",
            "--check",
        ),
        manual_edit_boundary="Do not hand-edit proof repair attempt receipts; rerun the explicit one-shot proof-repair attempt runner for live dispatch or use --check to validate landed receipts.",
        deterministic_regeneration_expectation="Live provider output is not deterministically regenerated; check_command validates committed one-shot receipts and repair_command is intentionally check-only.",
        stale_drift_handling="Run check_command before landing proof-repair attempt artifacts; if stale or missing, rerun the explicit invocation only when the repair lane contract and provider policy allow it.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_statement_scope_gate_projection",
        description="Private formal-math statement-scope receipts that test whether a target theorem statement typechecks under allowed prompt-boundary imports before proof repair.",
        artifacts=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_statement_scope_gate/statement_scope_gate_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_statement_scope_gate/*.lean",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_statement_scope_gate/*.txt",
        ),
        source_authorities=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_input_packet.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/oracle_environment_gate_receipt.json",
            "tools/meta/factory/build_formal_math_statement_scope_gate.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_statement_scope_gate.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_statement_scope_gate.py",
        ),
        manual_edit_boundary="Do not hand-edit formal statement-scope gate receipts; rerun the statement-scope gate builder.",
        deterministic_regeneration_expectation="repair_command reruns Lean statement-scope checks and rewrites diagnostic receipts from the current proof-repair packet.",
        stale_drift_handling="Run check_command before landing statement-scope gate artifacts; on drift, rerun the builder and land the receipt with the source-authority change that caused it.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_statement_scope_support_projection",
        description="Private pre-target Lean support prefixes generated for formal-math proof repair when the legal statement needs definitions from the target source file without exposing the target theorem proof.",
        artifacts=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_statement_scope_support/statement_scope_support_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_statement_scope_support/*.lean",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_statement_scope_support/*.txt",
        ),
        source_authorities=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_input_packet.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/oracle_environment_gate_receipt.json",
            "tools/meta/factory/build_formal_math_statement_scope_support.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_statement_scope_support.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_statement_scope_support.py",
        ),
        manual_edit_boundary="Do not hand-edit formal statement-scope support prefixes or receipts; rerun the support builder.",
        deterministic_regeneration_expectation="repair_command deterministically extracts the pre-target prefix from the pinned Lean workspace source file and reruns the supported statement check.",
        stale_drift_handling="Run check_command before landing statement-scope support artifacts; on drift, rerun the builder and land the receipt with the source-authority change that caused it.",
    ),
    GeneratedProjectionOwner(
        owner_id="formal_math_support_affordance_finder_projection",
        description="Private support-aware proof-affordance finder receipts generated after a supported formal-math proof-repair attempt is Lean-rejected.",
        artifacts=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_support_affordance_finder/affordance_finder_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_support_affordance_finder/local_declaration_index.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_support_affordance_finder/tactic_probe_manifest.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_support_affordance_finder/tactic_probe_*.lean",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_support_affordance_finder/tactic_probe_*_stdout.txt",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_support_affordance_finder/tactic_probe_*_stderr.txt",
        ),
        source_authorities=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_statement_scope_support/statement_scope_support_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_statement_scope_support/pretarget_scope_support.lean",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_attempt_receipt.json",
            "tools/meta/factory/build_formal_math_support_affordance_finder.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_support_affordance_finder.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_formal_math_support_affordance_finder.py",
        ),
        manual_edit_boundary="Do not hand-edit formal support-affordance finder receipts or probe artifacts; rerun the finder builder.",
        deterministic_regeneration_expectation="repair_command reruns bounded local Lean tactic probes against the committed support prefix and may rewrite probe timing/output receipts.",
        stale_drift_handling="Run check_command before landing support-affordance artifacts; rerun the builder after support-prefix, prior-attempt, or proofline changes.",
    ),
    GeneratedProjectionOwner(
        owner_id="external_benchmark_calibration_spine_projection",
        description="Private external benchmark calibration spine and operator-facing VeriSoftBench micro-10 scorecard generated from evaluator-backed formal-math receipts.",
        artifacts=(
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/slice_manifest.json",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/result_board.json",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/row_execution/row_execution_manifest.json",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/row_execution/verisoftbench_*/*.json",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/row_execution/verisoftbench_*/*.lean",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/row_execution/verisoftbench_*/*.txt",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/harness_differential/harness_differential_manifest.json",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/harness_differential/verisoftbench_*/*.json",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/c_arm_provider_repair/c_arm_provider_repair_manifest.json",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/c_arm_provider_repair/verisoftbench_*/*.json",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/c_arm_provider_repair/verisoftbench_*/*.lean",
            "state/benchmarks/external_calibration/verisoftbench_micro_10_v0/c_arm_provider_repair/verisoftbench_*/*.txt",
            "docs/benchmarks/generated_verisoftbench_micro_10_scorecard.md",
        ),
        source_authorities=(
            "state/benchmarks/formal_math_decision_point_microcosm_v0/proofline_spine.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_problem_resolution_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/oracle_ingress_selection_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_statement_scope_support/statement_scope_support_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_support_affordance_finder/affordance_finder_receipt.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/formal_support_affordance_finder/tactic_probe_manifest.json",
            "state/benchmarks/formal_math_decision_point_microcosm_v0/run_initial_failure_score_20260512T195745Z/proof_repair_attempt_receipt.json",
            "state/benchmarks/verisoftbench_no_solve_manifest_v0/manifest.json",
            "annexes/verisoftbench/repo/data/verisoftbench.jsonl",
            "annexes/verisoftbench/repo/core/lean_interface.py",
            "annexes/verisoftbench/repo/utils/utils.py",
            "tools/meta/factory/build_external_benchmark_calibration_spine.py",
            "tools/meta/factory/run_verisoftbench_micro10_calibration_rows.py",
            "tools/meta/factory/run_verisoftbench_micro10_harness_differential.py",
            "tools/meta/factory/run_verisoftbench_micro10_c_arm_provider_repair.py",
            "system/lib/openrouter_free_runtime.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_external_benchmark_calibration_spine.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_external_benchmark_calibration_spine.py",
        ),
        manual_edit_boundary="Do not hand-edit the external calibration result board or scorecard; mutate source receipts or the calibration builder and rerun the builder.",
        deterministic_regeneration_expectation="repair_command deterministically rebuilds the micro-slice manifest, result board, and markdown projection from committed formal-math, row-execution, harness, and C-arm receipts; execution receipts are refreshed by their explicit runners, not by this builder.",
        stale_drift_handling="Run check_command before landing calibration artifacts; on drift, rerun the builder and land the source receipt changes that changed the scorecard. Rerun execution tools only when the cap explicitly permits fresh provider or Lean work.",
    ),
    GeneratedProjectionOwner(
        owner_id="annex_navigation_artifacts",
        description="Annex navigation read-models generated from annex metadata, notes, distillation, and external-source manifests.",
        artifacts=(
            "annexes/*/annex_index.json",
            "annexes/*/annex_contents.json",
            "annexes/annex_catalog.json",
            "annexes/annex_distillation_index.json",
            "annexes/annex_sync_digest.json",
            "annexes/annex_sync_digest.md",
            "annexes/annex_sync_digest_run_state.json",
        ),
        source_authorities=(
            "annexes/*/annex_family.json",
            "annexes/*/annex_notes.json",
            "annexes/*/distillation.json",
            "annex_import.py",
            "system/lib/annex_registry.py",
            "tools/meta/factory/build_annex_distillation_projection.py",
        ),
        check_command=("./repo-python", "annex_import.py", "validate", "--all", "--read-only"),
        repair_command=("./repo-python", "annex_import.py", "catalog", "--write"),
        manual_edit_boundary="Do not hand-edit annex_index.json, annex_contents.json, annex_catalog.json, annex_distillation_index.json, or annex_sync_digest surfaces; mutate annex metadata/distillation or run the annex owner tools.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce repo-wide annex catalog and distillation projections from annex source authorities; sync digest refreshes through annex_import.py digest; per-annex indexes refresh through annex_import.py refresh --slug.",
        stale_drift_handling="Run check_command before landing annex read-model artifacts; run annex_import.py digest for sync-digest freshness; external source payloads and repo checkouts remain manifest/pointer or local-only unless an owner standard explicitly claims durability.",
    ),
    GeneratedProjectionOwner(
        owner_id="extracted_pattern_route_readiness",
        description="Macro-side mined-pattern route readiness validation report generated from the extracted pattern ledger and organ-routing overlays.",
        artifacts=(
            "state/microcosm_portfolio/extracted_pattern_route_readiness_validation_report.json",
        ),
        source_authorities=(
            "codex/standards/std_extracted_pattern_route_readiness.json",
            "state/microcosm_portfolio/extracted_patterns_ledger.jsonl",
            "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json",
            "state/microcosm_portfolio/extracted_pattern_route_readiness_audit.json",
            "state/microcosm_portfolio/extracted_pattern_row_to_organ_router.json",
            "state/microcosm_portfolio/extracted_pattern_organ_route_cards.json",
            "state/microcosm_portfolio/extracted_pattern_organ_fixture_specs.json",
            "state/microcosm_portfolio/extracted_pattern_route_decision_matrix.json",
            "state/microcosm_portfolio/extracted_pattern_organ_dependency_dag.json",
            "state/microcosm_portfolio/extracted_pattern_internal_routing_graph.json",
            "tools/meta/factory/check_extracted_pattern_route_readiness.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/check_extracted_pattern_route_readiness.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/check_extracted_pattern_route_readiness.py",
            "--write-report",
        ),
        manual_edit_boundary="Do not hand-edit the route-readiness validation report; mutate the mined-pattern routing overlays or checker, then rerun the checker.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the validation report from the current ledger and route-readiness overlays.",
        stale_drift_handling="Run check_command before selecting pattern organs for reconstruction; on drift, repair the named overlay or rerun repair_command and land the report with source-overlay changes.",
    ),
    GeneratedProjectionOwner(
        owner_id="microcosm_executable_doctrine_grammar_receipts",
        description="Public microcosm executable-doctrine-grammar receipts generated from synthetic fixture inputs.",
        artifacts=(
            "microcosm-substrate/receipts/first_wave/executable_doctrine_grammar/*.json",
            "microcosm-substrate/receipts/acceptance/first_wave/executable_doctrine_grammar_fixture_acceptance.json",
        ),
        source_authorities=(
            "microcosm-substrate/core/executable_doctrine_grammar.json",
            "microcosm-substrate/core/fixture_manifests/executable_doctrine_grammar.fixture_manifest.json",
            "microcosm-substrate/fixtures/first_wave/executable_doctrine_grammar/input/**",
            "microcosm-substrate/src/microcosm_core/organs/executable_doctrine_grammar.py",
            "tools/meta/factory/build_microcosm_executable_doctrine_grammar_receipts.py",
        ),
        check_command=(
            "./repo-python",
            "tools/meta/factory/build_microcosm_executable_doctrine_grammar_receipts.py",
            "--check",
        ),
        repair_command=(
            "./repo-python",
            "tools/meta/factory/build_microcosm_executable_doctrine_grammar_receipts.py",
            "--write",
        ),
        manual_edit_boundary="Do not hand-edit executable-doctrine-grammar fixture receipts; mutate the synthetic fixture, validator, or contract, then rerun the owner tool.",
        deterministic_regeneration_expectation="repair_command regenerates schema-stable receipt payloads from public synthetic fixture inputs; receipt timestamps refresh by design.",
        stale_drift_handling="Run check_command before landing executable-doctrine-grammar receipts; on drift, rerun repair_command and land validator, fixture, or contract changes with regenerated receipts.",
    ),
    GeneratedProjectionOwner(
        owner_id="microcosm_runtime_shell_project_state",
        description="Runtime-shell demo project state index generated by replaying the public Microcosm runtime workflow.",
        artifacts=(
            "microcosm-substrate/examples/runtime_shell/*/.microcosm/state_index.json",
        ),
        source_authorities=(
            "microcosm-substrate/src/microcosm_core/runtime_shell.py",
            "microcosm-substrate/src/microcosm_core/project_substrate.py",
            "microcosm-substrate/src/microcosm_core/cli.py",
            "microcosm-substrate/examples/runtime_shell/*",
            "microcosm-substrate/tests/test_runtime_shell.py",
        ),
        check_command=(
            "./repo-pytest",
            "microcosm-substrate/tests/test_runtime_shell.py::test_runtime_shell_runs_demo_workflow_against_exported_bundles",
            "-q",
        ),
        repair_command=(
            "./repo-env",
            "PYTHONPATH=microcosm-substrate/src",
            "./repo-python",
            "-m",
            "microcosm_core.cli",
            "run",
            "examples/runtime_shell/demo_project",
        ),
        manual_edit_boundary="Do not hand-edit runtime-shell .microcosm state indexes; mutate runtime shell/project substrate sources or fixture inputs, then rerun the runtime workflow.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the demo project's state index from committed runtime-shell sources and public example inputs.",
        stale_drift_handling="Run check_command before landing runtime-shell state projections; on drift, rerun repair_command and land source or fixture changes with regenerated state artifacts.",
    ),
    GeneratedProjectionOwner(
        owner_id="microcosm_mission_transaction_work_spine_receipts",
        description="Public microcosm mission-transaction work-spine receipts generated from first-wave fixture inputs.",
        artifacts=(
            "microcosm-substrate/receipts/first_wave/mission_transaction_work_spine/*.json",
            "microcosm-substrate/receipts/preflight/mission_transaction_work_spine.json",
            "microcosm-substrate/receipts/runtime_shell/*/organs/mission_transaction_work_spine/*.json",
        ),
        source_authorities=(
            "microcosm-substrate/src/microcosm_core/organs/mission_transaction_work_spine.py",
            "microcosm-substrate/src/microcosm_core/macro_tools/mission_transaction_preflight.py",
            "microcosm-substrate/src/microcosm_core/macro_tools/work_landing.py",
            "microcosm-substrate/core/fixture_manifests/mission_transaction_work_spine.fixture_manifest.json",
            "microcosm-substrate/fixtures/first_wave/mission_transaction_work_spine/input/**",
            "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/**",
            "microcosm-substrate/tests/test_mission_transaction_work_spine.py",
        ),
        check_command=(
            "./repo-pytest",
            "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_observes_required_negative_cases",
            "-q",
        ),
        repair_command=(
            "./repo-env",
            "PYTHONPATH=microcosm-substrate/src",
            "./repo-python",
            "-m",
            "microcosm_core.cli",
            "mission-transaction-work-spine",
            "run",
            "--input",
            "microcosm-substrate/fixtures/first_wave/mission_transaction_work_spine/input",
            "--out",
            "microcosm-substrate/receipts/first_wave/mission_transaction_work_spine",
        ),
        manual_edit_boundary="Do not hand-edit mission-transaction work-spine receipts; mutate fixture inputs, macro-tool sources, or the organ, then rerun the owner command.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce schema-stable mission-transaction receipts from public first-wave fixtures; volatile live ledger state is not source authority.",
        stale_drift_handling="Run check_command before landing work-spine receipts; on drift, rerun repair_command and land fixture/source changes with regenerated receipts.",
    ),
    GeneratedProjectionOwner(
        owner_id="idea_microcosm_seed_projection",
        description="Idea-first GitHub microcosm seed projected from principles, axiom candidates, standards, deliverables, and selected code patterns.",
        artifacts=(
            "docs/dissemination/generated/idea_microcosm/idea_microcosm_seed.json",
            "docs/dissemination/generated/idea_microcosm/idea_microcosm_seed.md",
            "docs/dissemination/generated/idea_microcosm/idea_microcosm_projection_receipt.json",
        ),
        source_authorities=(
            "tools/meta/dissemination/build_idea_microcosm_seed.py",
            "docs/dissemination/idea_first_microcosm_deliverables.md",
            "docs/dissemination/microcosm_operator_thesis.md",
            "docs/dissemination/github_repo_ontology_v0.md",
            "docs/dissemination/workitem_ordered_build_plan.md",
            "codex/standards/std_standard_type_plane.json",
            "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json",
            "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json",
        ),
        check_command=("./repo-python", "tools/meta/dissemination/build_idea_microcosm_seed.py", "--check"),
        repair_command=("./repo-python", "tools/meta/dissemination/build_idea_microcosm_seed.py"),
        manual_edit_boundary="Do not hand-edit generated idea_microcosm seed artifacts; mutate the builder or source authorities, then rerun the builder.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce seed JSON, seed markdown, and internal receipt from the declared source authorities.",
        stale_drift_handling="Run check_command before landing the generated seed; on drift, rerun repair_command and land source-authority changes with generated outputs.",
    ),
    GeneratedProjectionOwner(
        owner_id="idea_microcosm_repo_scaffold_projection",
        description="Runnable Idea-first public microcosm scaffold generated from the mined microcosm seed.",
        artifacts=("self-indexing-cognitive-substrate/**",),
        source_authorities=(
            "tools/meta/dissemination/scaffold_idea_microcosm_repo.py",
            "tools/meta/dissemination/build_idea_microcosm_seed.py",
            "docs/dissemination/generated/idea_microcosm/idea_microcosm_seed.json",
            "docs/dissemination/idea_first_microcosm_deliverables.md",
            "docs/dissemination/microcosm_operator_thesis.md",
            "docs/dissemination/github_repo_ontology_v0.md",
            "docs/dissemination/workitem_ordered_build_plan.md",
        ),
        check_command=("./repo-python", "tools/meta/dissemination/scaffold_idea_microcosm_repo.py", "--check"),
        repair_command=("./repo-python", "tools/meta/dissemination/scaffold_idea_microcosm_repo.py"),
        manual_edit_boundary="Do not hand-edit the generated scaffold snapshot when changing its baseline; mutate the scaffold builder or seed authorities, then rerun the scaffold builder. Runtime receipts and strategy ticks belong in test/temp/public-run lanes unless intentionally promoted.",
        deterministic_regeneration_expectation="repair_command must deterministically reproduce the committed scaffold snapshot from the mined seed for the current worktree.",
        stale_drift_handling="Run check_command before landing scaffold changes; on drift, rerun repair_command and land source-authority changes with the regenerated scaffold snapshot.",
    ),
)


def _normalize_path_token(path: str) -> str:
    token = str(path or "").replace("\\", "/").strip("/")
    while token.startswith("./"):
        token = token[2:]
    return token


def _has_glob_token(pattern: str) -> bool:
    return any(token in pattern for token in ("*", "?", "["))


def projection_pattern_matches_path(pattern: str, path: str) -> bool:
    """Return whether a registry artifact/source pattern covers a repo path."""
    normalized_pattern = _normalize_path_token(pattern)
    normalized_path = _normalize_path_token(path)
    if not normalized_pattern or not normalized_path:
        return False
    if _has_glob_token(normalized_pattern):
        return fnmatchcase(normalized_path, normalized_pattern)
    return (
        normalized_path == normalized_pattern
        or normalized_path.startswith(f"{normalized_pattern}/")
        or normalized_pattern.startswith(f"{normalized_path}/")
    )


def owner_matches_path(owner: GeneratedProjectionOwner, path: str) -> bool:
    patterns = tuple(owner.artifacts) + tuple(owner.source_authorities)
    return any(projection_pattern_matches_path(pattern, path) for pattern in patterns)


def projection_owners_for_paths(
    paths: Iterable[str],
    owner_ids: Iterable[str] | None = None,
) -> list[GeneratedProjectionOwner]:
    selected: list[GeneratedProjectionOwner] = []
    for owner in iter_projection_owners(owner_ids):
        if any(owner_matches_path(owner, path) for path in paths):
            selected.append(owner)
    return selected


def iter_projection_owners(owner_ids: Iterable[str] | None = None) -> list[GeneratedProjectionOwner]:
    requested = {str(owner_id) for owner_id in (owner_ids or []) if str(owner_id).strip()}
    rows = list(PROJECTION_REGISTRY)
    if requested:
        rows = [row for row in rows if row.owner_id in requested]
    return rows


def get_projection_owner(owner_id: str) -> GeneratedProjectionOwner:
    for row in PROJECTION_REGISTRY:
        if row.owner_id == owner_id:
            return row
    known = ", ".join(row.owner_id for row in PROJECTION_REGISTRY)
    raise KeyError(f"unknown projection owner {owner_id!r}; known owners: {known}")


def projection_registry_payload() -> dict[str, object]:
    return {
        "kind": "generated_projection_registry",
        "schema_version": "generated_projection_registry_v2",
        "contract_fields": [
            "source_authorities",
            "check_command",
            "repair_command",
            "manual_edit_boundary",
            "deterministic_regeneration_expectation",
            "stale_drift_handling",
        ],
        "owners": [row.to_dict() for row in PROJECTION_REGISTRY],
    }
