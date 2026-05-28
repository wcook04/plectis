"""
Build standard-owned option surfaces for artifact-kind-first navigation.

Supported microcosms include paper modules, standards, Task Ledger WorkItems, Prompt Ledger traces,
Prompt Shelf metadata, frontend views, skills, system terms, principles, concepts, mechanisms,
axiom candidates, raw-seed shards, Type A autonomous seeds, external benchmark calibration,
and compression profiles:
enumerate rows at a cheap flag band, then drill selected ids to card band
without a keyword query.

Rosetta routing header (std_navigation_rosetta_grammar.json::noun_shape):
  kind: python_module
    role: rung-1 option surface emitter; takes one kind_id (paper_modules,
        standards, task_ledger, prompt_ledger, prompt_shelf_metadata, principles, concepts,
        mechanisms, axiom_candidates, frontend_views, skills, system_terms, raw_seed_shards,
        type_a_autonomous_seeds,
        external_benchmark_calibration,
        compression_profiles, kinds) plus a band
        (cluster_flag, flag, card, tape when owned) and returns selectable rows
        without keyword search; the legal expansion target for a kind row whose
        support_status=option_surface_supported in std_kind_atlas.json.
  depends_on:
    - system/lib/kind_atlas.py: feeds - kind_atlas names which kind_ids are option_surface_supported; this module emits rows for those kinds.
    - codex/standards/std_paper_module.json: governs - the paper_modules option surface row shape and freshness contract.
    - codex/doctrine/paper_modules/_index.json: feeds - the authored paper-module set; this module renders flag and card rows from it.
    - codex/standards/standards_registry.json: feeds - the standards option surface enumerates registered std_*.json files.
    - codex/standards/std_kind_atlas.json: governs - aliases (paper_modules / paper-module / etc.) and the supported-bands contract per std_kind_atlas.json::band_contracts.
    - codex/standards/std_navigation_rosetta_grammar.json: governs - selector_policy=direct_enumeration is the policy this surface implements (cf. annex_pattern_refs: PageIndex / Corpus2Skill / RIG).
  governed_by:
    - codex/standards/std_kind_atlas.json
    - codex/standards/std_paper_module.json
    - codex/standards/std_navigation_rosetta_grammar.json
  code_loci:
    - build_option_surface: top-level constructor; resolves alias + band, dispatches to the kind-specific row builder, returns the selection packet.
    - parse_ids: shared id-parsing helper across kinds.
    - _normalize_artifact_kind: alias normalization to the canonical kind_id (paper_modules / standards / kinds).
    - _flag_row: paper-module flag-band row shape (slug, title, claim, status, currentness, depends_on / depended_on_by counts, evidence_command).
  evidence_command: ./repo-python kernel.py --option-surface paper_modules --band flag
  source_authority: codex/standards/std_paper_module.json for paper-module rows; codex/standards/principles/std_raw_seed_principles.json for principle rows; std_system_axiom_candidate.json for axiom candidate rows; std_kind_atlas.json for the kind atlas contract.
"""
from __future__ import annotations

from collections import Counter
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib.compression_profiles import (
    PROFILE_REGISTRY_REL,
    compression_profile_pointer,
    load_compression_profile_registry,
)
from system.lib.system_vocabulary import (
    BANDS as SYSTEM_TERM_BANDS,
    REGISTRY_REL as SYSTEM_TERM_REGISTRY_REL,
    load_system_vocabulary,
    system_vocabulary_terms,
)
from system.lib.navigation_surface_contracts import (
    ATLAS_PROJECTION,
    DEBUG_TRACE,
    ENTRY_REPLACEMENT,
    atlas_projection_contract,
)
from system.lib.principle_projection import resolve_principle_capsule
from system.lib import prompt_ledger_events, task_ledger_events
from system.lib.teleology_intent_capsule import build_teleology_intent_capsule

try:
    from system.lib.python_runtime_usage import (
        STATS_REL as PYTHON_USAGE_STATS_REL,
        load_usage_stats as _load_python_usage_stats,
        usage_for_file as _runtime_usage_for_file,
        usage_for_scope as _runtime_usage_for_scope,
    )
except ImportError:  # pragma: no cover - option surface should still import in partial envs
    PYTHON_USAGE_STATS_REL = Path("state/python_usage/python_usage_stats.json")
    _load_python_usage_stats = None  # type: ignore[assignment]
    _runtime_usage_for_file = None  # type: ignore[assignment]
    _runtime_usage_for_scope = None  # type: ignore[assignment]


PAPER_MODULE_INDEX = Path("codex/doctrine/paper_modules/_index.json")
PAPER_MODULE_ROUTE_COVERAGE = Path("codex/doctrine/paper_modules/_route_coverage.json")
PAPER_MODULE_STANDARD = Path("codex/standards/std_paper_module.json")
PAPER_MODULE_CLUSTER_TOP_ID_LIMIT = 2
IMAGINATION_INDEX = Path("codex/doctrine/imaginations/_index.json")
IMAGINATION_VALIDATION = Path("codex/doctrine/imaginations/_validation_report.json")
IMAGINATION_DIR = Path("codex/doctrine/imaginations")
STD_IMAGINATION = Path("codex/standards/std_imagination.json")
IMAGINATION_AUTHORING_SKILL = Path("codex/doctrine/skills/doctrine/imagination_authoring.md")
STANDARDS_ROOT = Path("codex/standards")
STANDARDS_REGISTRY = Path("codex/standards/standards_registry.json")
STANDARDS_REGISTRY_STANDARD = Path("codex/standards/std_standards_registry.json")
RAW_SEED_PRINCIPLES = Path(
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json"
)
RAW_SEED_PRINCIPLES_STANDARD = Path("codex/standards/principles/std_raw_seed_principles.json")
TELEOLOGY_NODES = Path("codex/doctrine/teleology_nodes.json")
TELEOLOGY_NODE_STANDARD = Path("codex/standards/principles/std_teleology_node.json")
DOCTRINE_TELEOLOGY_SCHEMA_VERSION = "doctrine_teleology_profile_v1"
DOCTRINE_TELEOLOGY_NODE_REGISTRY_SCHEMA_VERSION = "doctrine_teleology_node_registry_v1"
RAW_SEED_AXIOM_CANDIDATES = Path(
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json"
)
RAW_SEED_SHARDS = Path(
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_shards.json"
)
CONCEPT_DIR = Path("codex/doctrine/concepts")
CONCEPT_STANDARD = Path("codex/standards/principles/std_concept.json")
MECHANISM_DIR = Path("codex/doctrine/mechanisms")
MECHANISM_STANDARD = Path("codex/standards/principles/std_mechanism.json")
CONCEPT_MECHANISM_CANDIDATES = Path("codex/doctrine/concept_mechanism_candidates.json")
CONCEPT_MECHANISM_CANDIDATE_CURATION = Path("codex/doctrine/concept_mechanism_candidate_curation.json")
STD_AXIOM_CANDIDATE = Path("codex/standards/principles/std_system_axiom_candidate.json")
RAW_SEED_STANDARD = Path("codex/standards/observe_apply/std_raw_seed.md")
CORE_AUTHORITY_INDEX = Path("codex/standards/core_authority_index.json")
SYSTEM_TERM_STANDARD = Path("codex/standards/std_system_term.json")
SKILL_REGISTRY = Path("codex/doctrine/skills/skill_registry.json")
SKILL_STANDARD = Path("codex/standards/std_skill.json")
SKILL_TYPES_STANDARD = Path("codex/standards/std_skill_types.json")
SKILL_CLUSTER_KEY_PREVIEW_LIMIT = 16
TASK_LEDGER_LEDGER = Path("state/task_ledger/ledger.json")
TASK_LEDGER_EVENTS = Path("state/task_ledger/events.jsonl")
TASK_LEDGER_VIEWS_ROOT = Path("state/task_ledger/views")
TASK_LEDGER_STANDARD = Path("codex/standards/std_task_ledger.json")
TASK_LEDGER_SKILL = Path("codex/doctrine/skills/task_ledger/task_ledger.md")
TASK_LEDGER_PAPER_MODULE = Path("codex/doctrine/paper_modules/operational_work_item_spine.md")
PROMPT_LEDGER_EVENTS = prompt_ledger_events.EVENTS_REL
PROMPT_LEDGER_LEDGER = prompt_ledger_events.LEDGER_REL
PROMPT_LEDGER_VIEWS_ROOT = prompt_ledger_events.VIEWS_REL
PROMPT_LEDGER_STANDARD = Path("codex/standards/std_prompt_ledger.json")
PROMPT_LEDGER_TOOL = Path("tools/meta/observability/prompt_ledger.py")
PROMPT_SHELF_RUNS_INDEX = Path("state/prompt_shelf/prompt_shelf_runs_index.json")
PROMPT_SHELF_RUNS_INDEX_TOOL = Path("tools/meta/observability/prompt_shelf_runs_index.py")
PROMPT_SHELF_LEDGER = Path("obsidian/prompt_shelf/B2 Continue Ledger.md")
PROMPT_SHELF_USAGE_RUNS = Path("obsidian/prompt_shelf/usage/runs")
PROMPT_SHELF_USAGE_RAW_EVENTS = Path("obsidian/prompt_shelf/usage/raw_events")
PROMPT_SHELF_METADATA_ROW_ID = "prompt_shelf_runs_index_v1"
TYPE_A_AUTONOMOUS_SEED_ROOT = Path("state/meta_missions/type_a_autonomous_seed_loop/seeds")
TYPE_A_AUTONOMOUS_SEED_STANDARD = Path("codex/standards/std_autonomous_seed_prompt.json")
TYPE_A_AUTONOMOUS_SEED_SKILL = Path("codex/doctrine/skills/kernel/type_a_autonomous_seed_loop.md")
TYPE_A_AUTONOMOUS_SEED_MISSION = Path(
    "codex/standards/observe/mission_templates/meta_missions/type_a_autonomous_seed_loop/mission.json"
)
TYPE_A_AUTONOMOUS_SEED_TEMPLATE = Path(
    "codex/standards/observe/mission_templates/meta_missions/type_a_autonomous_seed_loop/seed_template.json"
)
EXTERNAL_BENCHMARK_CALIBRATION_ROW_ID = "verisoftbench_micro_10_calibration_spine_v1"
EXTERNAL_BENCHMARK_CALIBRATION_ROOT = Path(
    "state/benchmarks/external_calibration/verisoftbench_micro_10_v0"
)
EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD = EXTERNAL_BENCHMARK_CALIBRATION_ROOT / "result_board.json"
EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST = EXTERNAL_BENCHMARK_CALIBRATION_ROOT / "slice_manifest.json"
EXTERNAL_BENCHMARK_CALIBRATION_SCORECARD = Path(
    "docs/benchmarks/generated_verisoftbench_micro_10_scorecard.md"
)
EXTERNAL_BENCHMARK_CALIBRATION_BUILDER = Path(
    "tools/meta/factory/build_external_benchmark_calibration_spine.py"
)
EXTERNAL_BENCHMARK_ROW_EXECUTION = Path(
    "tools/meta/factory/run_verisoftbench_micro10_calibration_rows.py"
)
EXTERNAL_BENCHMARK_HARNESS_DIFFERENTIAL = Path(
    "tools/meta/factory/run_verisoftbench_micro10_harness_differential.py"
)
EXTERNAL_BENCHMARK_C_ARM_PROVIDER_REPAIR = Path(
    "tools/meta/factory/run_verisoftbench_micro10_c_arm_provider_repair.py"
)
EXTERNAL_BENCHMARK_PROJECTION_OWNER_ID = "external_benchmark_calibration_spine_projection"
EXTERNAL_BENCHMARK_WORK_ITEM_ID = "cap_external_benchmark_calibration_spine_verisoftbench_micro_10"
EXTERNAL_BENCHMARK_TELEOLOGY_ID = "tel_ai_native_formal_math_laboratory"
PROFILE_SKILL = Path("codex/doctrine/skills/compression/profile_governed_compression.md")
RAW_SEED_CONTEXTUAL_COMPRESSION_SKILL = Path(
    "codex/doctrine/skills/compression/raw_seed_contextual_compression.md"
)
RAW_SEED_NAVIGATION_SKILL = Path("codex/doctrine/skills/raw_seed/raw_seed_navigation.md")
NAVIGATION_THEORY = Path("codex/doctrine/paper_modules/navigation_hologram_theory.md")
FRONTEND_NAV_GRAPH = Path("state/frontend_navigation/navigation_graph.json")
FRONTEND_NAV_DOCTRINE = Path("codex/doctrine/paper_modules/frontend_navigation_plane.md")
FRONTEND_VIEW_OBSERVATION_INDEX = Path(
    "state/observability/view_quality/frontend_view_observation_index_v0.json"
)
FRONTEND_VISUAL_SETTLEMENT = Path(
    "state/observability/view_quality/frontend_visual_settlement_v0.json"
)
FRONTEND_VISUAL_MEMORY_ALIAS_TERMS = (
    "screenshot ledger",
    "frontend screenshot ledger",
    "view observation memory",
    "view observation packet",
    "visual memory cell",
    "frontend visual memory",
    "frontend visual settlement",
    "latest visual delta",
)
RAW_SEED_PROFILE_ID = "raw_seed_voice_context_v1"
RAW_SEED_NATIVE_PROFILE_BANDS = ["flag", "card", "context", "deep"]
ANNEX_ROOT = Path("annexes")
ANNEX_CATALOG = ANNEX_ROOT / "annex_catalog.json"
ANNEX_NOTES_FILE_NAME = "annex_notes.json"
ANNEX_AUTHORITY_INDEX = Path("codex/standards/annex/annex_authority_index.json")
ANNEX_CATALOG_STANDARD = Path("codex/standards/annex/std_annex_catalog.json")
ANNEX_PATTERN_FLOOR_RUNTIME_FORK_SKILL = Path(
    "codex/doctrine/skills/annex/annex_pattern_floor_runtime_fork.md"
)
ANNEX_PATTERN_TRANSFER_SKILL = Path(
    "codex/doctrine/skills/annex/annex_pattern_transfer.md"
)
ANNEX_PATTERN_PROFILE_ID = "annex_pattern_navigation_v0"
ANNEX_PATTERN_NATIVE_PROFILE_BANDS = ["family", "contents", "pattern_notes", "source"]
MICROCOSM_EXTRACTED_PATTERN_LEDGER = Path("state/microcosm_portfolio/extracted_patterns_ledger.jsonl")
MICROCOSM_EXTRACTED_PATTERN_README = Path("state/microcosm_portfolio/extracted_patterns_ledger_README.md")
MICROCOSM_EXTRACTED_PATTERN_BINDINGS = Path(
    "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json"
)
MICROCOSM_EXTRACTED_PATTERN_WEAK_BINDINGS = Path(
    "state/microcosm_portfolio/extracted_pattern_weak_bindings.json"
)
MICROCOSM_EXTRACTED_PATTERN_READINESS_AUDIT = Path(
    "state/microcosm_portfolio/extracted_pattern_route_readiness_audit.json"
)
MICROCOSM_EXTRACTED_PATTERN_ROW_TO_ORGAN_ROUTER = Path(
    "state/microcosm_portfolio/extracted_pattern_row_to_organ_router.json"
)
MICROCOSM_EXTRACTED_PATTERN_ORGAN_ROUTE_CARDS = Path(
    "state/microcosm_portfolio/extracted_pattern_organ_route_cards.json"
)
MICROCOSM_EXTRACTED_PATTERN_SUBSTRATE_STANDARD = Path(
    "codex/standards/std_extracted_pattern_substrate_bindings.json"
)
MICROCOSM_EXTRACTED_PATTERN_ROUTE_STANDARD = Path(
    "codex/standards/std_extracted_pattern_route_readiness.json"
)
MICROCOSM_SUBSTRATE_MODULE = Path("codex/doctrine/paper_modules/microcosm_substrate.md")
PYTHON_STANDARD = Path("codex/standards/std_python.py")
PYTHON_SCOPE_INDEX = Path("codex/standards/std_python_scope_index.json")
FRONTEND_COMPONENT_INDEX = Path("state/frontend_navigation/component_index.json")
FRONTEND_COMPONENT_STANDARD = Path("codex/standards/std_frontend_component_index.json")
FRONTEND_COMPONENT_EXTRACTOR = Path("tools/meta/observability/frontend_component_index.py")
FRONTEND_COMPONENT_PROFILE_ID = "frontend_component_navigation_v0"
FRONTEND_COMPONENT_NATIVE_PROFILE_BANDS = ["component_id", "purpose", "props_state", "source"]
FRONTEND_COMPONENT_NATIVE_PROFILE_FACETS = ["props", "state", "children", "view_ownership"]
FRONTEND_COMPONENT_PRIMARY_CONFIDENCE = {"high", "medium"}
FRONTEND_COMPONENT_OMITTED_CONFIDENCE = {"low"}
SYSTEM_ATLAS_GRAPH = Path("state/system_atlas/system_atlas.graph.json")
SYSTEM_ATLAS_SUMMARY = Path("state/system_atlas/system_atlas_summary.json")
SYSTEM_ATLAS_STANDARD = Path("codex/standards/std_system_atlas.json")
SYSTEM_ATLAS_BUILDER = Path("tools/meta/factory/build_system_atlas.py")
STANDARD_TYPE_PLANE = Path("codex/standards/std_standard_type_plane.json")
PYTHON_FILE_PROFILE_ID = "python_scope_navigation_v0"
PYTHON_FILE_NATIVE_PROFILE_BANDS = [
    "module_docs",
    "file_card",
    "symbol_capsule",
    "graph_context",
    "source_span",
]
PYTHON_SCOPE_PROFILE_ID = "python_scope_navigation_v0"
PYTHON_SCOPE_NATIVE_PROFILE_BANDS = list(PYTHON_FILE_NATIVE_PROFILE_BANDS)
PYTHON_SCOPE_NATIVE_PROFILE_SCOPES = ["module", "class", "function", "method", "source_span"]
PYTHON_SCOPE_NATIVE_PROFILE_FACETS = [
    "module_docstring",
    "signature",
    "contract_atoms",
    "body",
    "symbol_graph",
    "source_span",
]

SUPPORTED_PAPER_MODULE_ALIASES = {"paper_modules", "paper_module", "paper-modules", "paper-module"}
SUPPORTED_STANDARDS_ALIASES = {"standards", "standard", "std", "stds"}
SUPPORTED_PRINCIPLES_ALIASES = {"principles", "principle", "pri", "pri_rows", "raw_seed_principles"}
SUPPORTED_CONCEPT_ALIASES = {
    "concepts",
    "concept",
    "con",
    "con_rows",
    "doctrine_concepts",
    "doctrine-concepts",
}
SUPPORTED_MECHANISM_ALIASES = {
    "mechanisms",
    "mechanism",
    "mech",
    "mech_rows",
    "doctrine_mechanisms",
    "doctrine-mechanisms",
}
SUPPORTED_CONCEPT_MECHANISM_CANDIDATE_ALIASES = {
    "concept_mechanism_candidates",
    "concept_mechanism_candidate",
    "concept-mechanism-candidates",
    "cm_candidates",
    "cmc",
}
SUPPORTED_CONCEPT_MECHANISM_CURATION_ALIASES = {
    "concept_mechanism_candidate_curations",
    "concept_mechanism_candidate_curation",
    "concept-mechanism-candidate-curations",
    "concept-mechanism-candidate-curation",
    "cm_curations",
    "cmc_curations",
    "cmc_receipts",
    "candidate_curations",
}
SUPPORTED_AXIOM_ALIASES = {
    "axiom_candidates",
    "axiom_candidate",
    "axioms",
    "system_axiom_candidates",
    "axiom_ledger",
}
SUPPORTED_COMPRESSION_PROFILE_ALIASES = {
    "compression_profiles",
    "compression_profile",
    "compression-profile",
    "profiles",
}
SUPPORTED_SYSTEM_TERM_ALIASES = {
    "system_terms",
    "system_term",
    "system-terms",
    "system-term",
    "terms",
    "term",
    "vocabulary",
}
SUPPORTED_SKILL_ALIASES = {
    "skills",
    "skill",
    "capabilities",
    "capability",
    "agent_skills",
    "agent-skills",
    "skill_registry",
    "skill-registry",
}
SUPPORTED_TASK_LEDGER_ALIASES = {
    "task_ledger",
    "task-ledger",
    "work_items",
    "work_item",
    "work-items",
    "work-item",
    "workitem",
    "workitems",
    "tasks",
    "task_spine",
    "work_item_spine",
}
SUPPORTED_PROMPT_LEDGER_ALIASES = {
    "prompt_ledger",
    "prompt-ledger",
    "prompt_traces",
    "prompt-traces",
    "prompt_trace_provenance",
    "prompt-trace-provenance",
    "prompt_provenance",
    "prompt-provenance",
    "type_b_traces",
    "type-b-traces",
}
SUPPORTED_PROMPT_SHELF_METADATA_ALIASES = {
    "prompt_shelf_metadata",
    "prompt-shelf-metadata",
    "prompt_shelf_runs_index",
    "prompt-shelf-runs-index",
    "prompt_shelf_runs",
    "prompt-shelf-runs",
    "prompt_shelf_extraction",
    "prompt-shelf-extraction",
    "type_b_metadata",
    "type-b-metadata",
    "type_b_extraction",
    "type-b-extraction",
}
SUPPORTED_FRONTEND_VIEW_ALIASES = {
    "frontend_views",
    "frontend_view",
    "frontend-views",
    "frontend-view",
    "views",
    "view",
    "station_views",
    "station-views",
}
SUPPORTED_RAW_SEED_SHARD_ALIASES = {
    "raw_seed_shards",
    "raw_seed_shard",
    "raw-seed-shards",
    "raw-seed-shard",
    "raw_shards",
    "raw-shards",
    "shards",
}
SUPPORTED_TYPE_A_AUTONOMOUS_SEED_ALIASES = {
    "type_a_autonomous_seeds",
    "type_a_autonomous_seed",
    "type-a-autonomous-seeds",
    "type-a-autonomous-seed",
    "type_a_seed_loop",
    "type-a-seed-loop",
    "autonomous_seeds",
    "autonomous_seed",
    "autonomous-seeds",
    "autonomous-seed",
    "seed_loop",
    "seed-loop",
}
SUPPORTED_EXTERNAL_BENCHMARK_CALIBRATION_ALIASES = {
    "external_benchmark_calibration",
    "external-benchmark-calibration",
    "external_benchmark_calibration_spine",
    "benchmark_calibration",
    "benchmark-calibration",
    "formal_math_benchmark_calibration",
    "formal-math-benchmark-calibration",
    "verisoftbench",
    "verisoftbench_micro10",
    "verisoftbench_micro_10",
    "verisoftbench-micro-10",
    "c_arm_provider_repair",
    "c-arm-provider-repair",
    "formal_math_proof_repair",
    "formal-math-proof-repair",
}
RAW_SEED_ROUTE_ALIASES = {"raw_seed", "raw-seed", "raw_seed_navigation", "raw-seed-navigation"}
RAW_SEED_PAPER_ROUTE_ALIASES = {"raw_seed_paper", "raw-seed-paper", "raw_seed_papers", "raw-seed-papers"}
SUPPORTED_ANNEX_PATTERN_ALIASES = {
    "annex_patterns",
    "annex_pattern",
    "annex-patterns",
    "annex-pattern",
    "annex_notes",
    "annex_note",
    "annex-notes",
    "annex-note",
    "annexes",
    "annex",
}
SUPPORTED_ANNEX_DISTILLATION_PATTERN_ALIASES = {
    "annex_distillation_patterns",
    "annex_distillation_pattern",
    "annex-distillation-patterns",
    "annex-distillation-pattern",
    "distillation_patterns",
    "distillation_pattern",
    "distillation-patterns",
    "distillation-pattern",
    "annex_pattern_rows",
    "annex-pattern-rows",
}
SUPPORTED_MICROCOSM_EXTRACTED_PATTERN_ALIASES = {
    "microcosm_extracted_patterns",
    "microcosm_extracted_pattern",
    "microcosm-extracted-patterns",
    "microcosm-extracted-pattern",
    "microcosm_patterns",
    "microcosm_pattern",
    "microcosm-patterns",
    "microcosm-pattern",
    "microcosm_pattern_ledger",
    "microcosm-pattern-ledger",
    "extracted_patterns_ledger",
    "extracted-patterns-ledger",
    "extracted_patterns",
    "extracted-patterns",
    "microcosm_portfolio_patterns",
    "microcosm-portfolio-patterns",
}
SUPPORTED_PYTHON_FILE_ALIASES = {
    "python_files",
    "python_file",
    "python-files",
    "python-file",
    "py_files",
    "py_file",
    "py-files",
    "py-file",
}
SUPPORTED_PYTHON_SCOPE_ALIASES = {
    "python_scopes",
    "python_scope",
    "python-scopes",
    "python-scope",
    "py_scopes",
    "py_scope",
    "py-scopes",
    "py-scope",
}
SUPPORTED_FRONTEND_COMPONENT_ALIASES = {
    "frontend_components",
    "frontend_component",
    "frontend-components",
    "frontend-component",
    "components",
    "component",
    "tsx_components",
    "tsx-components",
    "ui_components",
    "ui-components",
}
SUPPORTED_KIND_ALIASES = {"kinds", "kind", "kind_atlas", "artifact_kinds", "artifact-kind", "artifact-kinds"}
SUPPORTED_IMAGINATION_ALIASES = {
    "imaginations",
    "imagination",
    "imn",
    "imn_rows",
}
SUPPORTED_AUTHORING_CONTRACT_ALIASES = {
    "authoring_contracts",
    "authoring_contract_surface",
    "authoring-contracts",
    "authoring-contract-surface",
    "authoring_lanes",
}
SUPPORTED_SYSTEM_ATLAS_ALIASES = {
    "system_atlas",
    "system-atlas",
    "atlas",
    "atlas_domains",
    "atlas_entities",
    "atlas_findings",
    "atlas_stale",
    "atlas_unknowns",
    "atlas_private_root",
    "atlas_public_candidates",
    "capability_coverage",
    "substrate_atlas",
    "self_comprehension",
}
SUPPORTED_CONFIG_AUTHORITY_ALIASES = {
    "config_authorities",
    "config_authority",
    "config-authorities",
    "config-authority",
    "config_surface",
    "config-surface",
    "config_registry",
    "config-registry",
    "master_config_plane",
    "master-config-plane",
    "effective_config",
    "effective-config",
    "config_ref",
    "settings_config",
}
SUPPORTED_NAVIGATION_TYPE_PLANE_ALIASES = {
    "navigation_type_plane",
    "navigation-type-plane",
    "type_plane",
    "type-plane",
    "standards_type_plane",
    "standards-type-plane",
}
# flag/card: row-select surfaces. tape: full compression ladder in one
# token-efficient JSON row per id. cluster_flag is the cardinality-safe rung
# above all-row flag for large families.
OPTION_SURFACE_BANDS = {"cluster_flag", "atom", "flag", "card", "tape", "stale", "unknowns"}
PRINCIPLE_TYPE_ORDER = {
    "meta": 0,
    "architectural": 1,
    "strategic": 2,
    "operational": 3,
    "substance": 4,
    "untyped": 5,
}

PAPER_MODULE_CLUSTER_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "navigation_compression",
        "Navigation / compression / routing",
        ("navigation", "hologram", "compression", "rosetta", "routing", "route", "entry_surface"),
    ),
    (
        "agent_runtime",
        "Agent runtime / hooks / observability",
        ("agent", "hook", "runtime", "trace", "observability", "subagent", "entrypoint"),
    ),
    (
        "raw_seed_doctrine",
        "Raw seed / principles / voice",
        ("raw_seed", "seed", "principle", "voice", "shard", "axiom"),
    ),
    (
        "bridge_observe_apply",
        "Bridge / observe / apply / phase",
        ("bridge", "observe", "apply", "phase", "work_ledger", "mission", "campaign"),
    ),
    (
        "frontend_station",
        "Frontend / Station / UI",
        ("frontend", "station", "ui", "cockpit", "view"),
    ),
    (
        "annex_external_patterns",
        "Annex / external patterns",
        ("annex", "external", "pattern", "distillation"),
    ),
]

DEFAULT_PRINCIPLE_LAYERS: list[dict[str, Any]] = [
    {
        "band_id": "identity",
        "rung": "L0",
        "order": 0,
        "label": "Identity",
        "one_line_job": "Select a principle by id, title, type, and authority status.",
        "char_budget_soft": 160,
        "default_route_template": "./repo-python kernel.py --option-surface principles --band flag",
        "population_deliverable_id": "principle_layer_L0",
        "unpopulated_signal": "Missing id, slug, or title in registry row",
    },
    {
        "band_id": "statement",
        "rung": "L1",
        "order": 1,
        "label": "Statement",
        "one_line_job": "The single-sentence load-bearing claim.",
        "char_budget_soft": 280,
        "default_route_template": "./repo-python kernel.py --option-surface principles --band card --ids <pri_id>",
        "population_deliverable_id": "principle_layer_L1",
        "unpopulated_signal": "Empty or placeholder statement",
    },
    {
        "band_id": "operating_card",
        "rung": "L2",
        "order": 2,
        "label": "Operating card",
        "one_line_job": "Tests, failure modes, and decision examples for apply/reject without opening evidence yet.",
        "char_budget_soft": 1200,
        "default_route_template": "./repo-python kernel.py --option-surface principles --band card --ids <pri_id>",
        "population_deliverable_id": "principle_layer_L2",
        "unpopulated_signal": "No tests and no failure_modes; decision_examples only is thin",
    },
    {
        "band_id": "edge_context",
        "rung": "L3",
        "order": 3,
        "label": "Edge context",
        "one_line_job": "Typed doctrine graph neighborhood (edges, related reference groups summary).",
        "char_budget_soft": 2000,
        "default_route_template": "./repo-python kernel.py --docs-route raw_seed_principles",
        "population_deliverable_id": "principle_layer_L3",
        "unpopulated_signal": "Zero edges when principle should relate to con/mech/pri; optional for seed rows",
    },
    {
        "band_id": "evidence",
        "rung": "L4",
        "order": 4,
        "label": "Evidence",
        "one_line_job": "Source authority: par_/sec_ refs, reference_groups, curation/promotion packets.",
        "char_budget_soft": 4000,
        "default_route_template": "./repo-python kernel.py --docs-route raw_seed_principles",
        "population_deliverable_id": "principle_layer_L4",
        "unpopulated_signal": "No evidence and no reference_groups; doctrine-only rows may be intentional per evidence rule",
    },
]


def _compression_char_budget(meta: Mapping[str, Any]) -> int:
    return int(meta.get("char_budget_soft") or meta.get("token_budget_chars_soft") or 0)


DEFAULT_AXIOM_LAYERS: list[dict[str, Any]] = [
    {
        "band_id": "tiny",
        "rung": "A0",
        "order": 0,
        "label": "Tiny",
        "one_line_job": "Minimum predicate hook for search and embedding.",
        "token_budget_chars_soft": 64,
        "default_route_template": "./repo-python kernel.py --option-surface axiom_candidates --band flag",
    },
    {
        "band_id": "flag",
        "rung": "A1",
        "order": 1,
        "label": "Flag",
        "one_line_job": "Route-card existence and stance before detail.",
        "token_budget_chars_soft": 200,
        "default_route_template": "./repo-python kernel.py --option-surface axiom_candidates --band flag",
    },
    {
        "band_id": "card",
        "rung": "A2",
        "order": 2,
        "label": "Card",
        "one_line_job": "Bounded natural-language reading (dense) plus formal head.",
        "token_budget_chars_soft": 800,
        "default_route_template": "./repo-python kernel.py --option-surface axiom_candidates --band card --ids <id>",
    },
    {
        "band_id": "context",
        "rung": "A3",
        "order": 3,
        "label": "Context",
        "one_line_job": "Implications, dependency neighborhood, and when to use the axiom.",
        "token_budget_chars_soft": 2500,
        "default_route_template": "jq '(.axiom_candidates[] | select(.id==\"<id>\"))' 'obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json'",
    },
    {
        "band_id": "deep",
        "rung": "A4",
        "order": 4,
        "label": "Deep",
        "one_line_job": "Extrapolation, future proof surface, and explicit unknowns; still candidate.",
        "token_budget_chars_soft": 8000,
        "default_route_template": "codex/doctrine/skills/doctrine/system_axiom_candidate_curation.md + ledger row",
        "population_deliverable_id": "axiom_layer_A4",
        "unpopulated_signal": "Deep may say what should be filled; empty string is debt",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_JSON_FILE_CACHE: dict[str, tuple[tuple[int, int], dict[str, Any]]] = {}


def _load_json(path: Path) -> dict[str, Any]:
    cacheable = path.name == PYTHON_SCOPE_INDEX.name and str(path).endswith(str(PYTHON_SCOPE_INDEX))
    if not cacheable:
        return json.loads(path.read_text(encoding="utf-8"))
    stat = path.stat()
    cache_key = str(path.resolve())
    fingerprint = (int(stat.st_mtime_ns), int(stat.st_size))
    cached = _JSON_FILE_CACHE.get(cache_key)
    if cached is not None and cached[0] == fingerprint:
        return cached[1]
    payload = json.loads(path.read_text(encoding="utf-8"))
    data = payload if isinstance(payload, dict) else {}
    _JSON_FILE_CACHE[cache_key] = (fingerprint, data)
    return data


def _load_prefixed_top_level_dict(path: Path, key: str, *, prefix_bytes: int = 262_144) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            prefix = handle.read(prefix_bytes)
    except FileNotFoundError:
        return {}
    marker = json.dumps(key)
    key_index = prefix.find(marker)
    if key_index < 0:
        return {}
    colon_index = prefix.find(":", key_index + len(marker))
    if colon_index < 0:
        return {}
    decoder = json.JSONDecoder()
    try:
        value, _ = decoder.raw_decode(prefix[colon_index + 1 :].lstrip())
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _normalize_artifact_kind(value: str) -> str:
    raw = str(value or "").strip().lower().replace(" ", "_")
    if raw in SUPPORTED_PAPER_MODULE_ALIASES:
        return "paper_modules"
    if raw in SUPPORTED_STANDARDS_ALIASES:
        return "standards"
    if raw in SUPPORTED_PRINCIPLES_ALIASES:
        return "principles"
    if raw in SUPPORTED_CONCEPT_ALIASES:
        return "concepts"
    if raw in SUPPORTED_MECHANISM_ALIASES:
        return "mechanisms"
    if raw in SUPPORTED_CONCEPT_MECHANISM_CANDIDATE_ALIASES:
        return "concept_mechanism_candidates"
    if raw in SUPPORTED_CONCEPT_MECHANISM_CURATION_ALIASES:
        return "concept_mechanism_candidate_curations"
    if raw in SUPPORTED_AXIOM_ALIASES:
        return "axiom_candidates"
    if raw in SUPPORTED_COMPRESSION_PROFILE_ALIASES:
        return "compression_profiles"
    if raw in SUPPORTED_SYSTEM_TERM_ALIASES:
        return "system_terms"
    if raw in SUPPORTED_SKILL_ALIASES:
        return "skills"
    if raw in SUPPORTED_TASK_LEDGER_ALIASES:
        return "task_ledger"
    if raw in SUPPORTED_PROMPT_LEDGER_ALIASES:
        return "prompt_ledger"
    if raw in SUPPORTED_PROMPT_SHELF_METADATA_ALIASES:
        return "prompt_shelf_metadata"
    if raw in SUPPORTED_FRONTEND_VIEW_ALIASES:
        return "frontend_views"
    if raw in SUPPORTED_RAW_SEED_SHARD_ALIASES:
        return "raw_seed_shards"
    if raw in SUPPORTED_TYPE_A_AUTONOMOUS_SEED_ALIASES:
        return "type_a_autonomous_seeds"
    if raw in SUPPORTED_EXTERNAL_BENCHMARK_CALIBRATION_ALIASES:
        return "external_benchmark_calibration"
    if raw in RAW_SEED_ROUTE_ALIASES:
        return "raw_seed"
    if raw in RAW_SEED_PAPER_ROUTE_ALIASES:
        return "raw_seed_paper"
    if raw in SUPPORTED_ANNEX_PATTERN_ALIASES:
        return "annex_patterns"
    if raw in SUPPORTED_ANNEX_DISTILLATION_PATTERN_ALIASES:
        return "annex_distillation_patterns"
    if raw in SUPPORTED_MICROCOSM_EXTRACTED_PATTERN_ALIASES:
        return "microcosm_extracted_patterns"
    if raw in SUPPORTED_PYTHON_FILE_ALIASES:
        return "python_files"
    if raw in SUPPORTED_PYTHON_SCOPE_ALIASES:
        return "python_scopes"
    if raw in SUPPORTED_FRONTEND_COMPONENT_ALIASES:
        return "frontend_components"
    if raw in SUPPORTED_KIND_ALIASES:
        return "kinds"
    if raw in SUPPORTED_IMAGINATION_ALIASES:
        return "imaginations"
    if raw in SUPPORTED_AUTHORING_CONTRACT_ALIASES:
        return "authoring_contracts"
    if raw in SUPPORTED_SYSTEM_ATLAS_ALIASES:
        return "system_atlas"
    if raw in SUPPORTED_CONFIG_AUTHORITY_ALIASES:
        return "config_authorities"
    if raw in SUPPORTED_NAVIGATION_TYPE_PLANE_ALIASES:
        return "navigation_type_plane"
    return raw


def parse_ids(ids: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if ids is None:
        return []
    if isinstance(ids, str):
        parts = re.split(r"[,\s]+", ids.strip())
        return [part for part in parts if part]
    return [str(item).strip() for item in ids if str(item).strip()]


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _truncate_words(text: str, *, max_chars: int) -> str:
    compact = _collapse_ws(text)
    if len(compact) <= max_chars:
        return compact
    clipped = compact[: max(0, max_chars - 1)].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..."


def _first_sentence(text: str, *, max_chars: int = 260) -> str:
    compact = _collapse_ws(re.sub(r"[*_`#>\[\]()]+", " ", str(text or "")))
    if not compact:
        return ""
    match = re.search(r"(?<=[.!?])\s+", compact)
    if match:
        return _truncate_words(compact[: match.start() + 1], max_chars=max_chars)
    return _truncate_words(compact, max_chars=max_chars)


def _extract_markdown_section(path: Path, heading: str, *, max_chars: int = 520) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return ""
    body = re.sub(r"```.*?```", " ", match.group("body"), flags=re.DOTALL)
    body = re.sub(r"\[[^\]]+\]\([^)]+\)", lambda m: m.group(0).split("](", 1)[0].lstrip("["), body)
    body = re.sub(r"[*_`#>|-]+", " ", body)
    return _truncate_words(body, max_chars=max_chars)


def _atom_row(module: dict[str, Any], *, index: dict[str, Any]) -> dict[str, Any]:
    """Atom band: cheapest selection-affordance row for whole-system reasoning.

    Per std_paper_module.json::compression_authoring_contract and the band-binding contract in
    system_constitution_seed.md, this row stays atom-sized — slug, atom, compression_status,
    trust_chip, drilldown_command. Flag/open_when belong on `band: flag` and above. Atom field is
    sourced from authored `Compression atom` frontmatter when present, falling back through
    previews.compression with explicit per-field source markers in the underlying index entry.
    """
    slug = str(module.get("slug") or "")
    compression = module.get("compression") if isinstance(module.get("compression"), dict) else {}
    drilldown = (
        str(compression.get("safe_drilldown") or "").strip()
        or f"./repo-python kernel.py --option-surface paper_modules --band card --ids {slug}"
    )
    return {
        "row_id": f"paper_module:{slug}::atom",
        "artifact_kind": "paper_module",
        "band": "atom",
        "slug": slug,
        "atom": str(compression.get("atom") or ""),
        "compression_status": str(compression.get("compression_status") or "missing"),
        "trust_chip": {
            "status": str(module.get("status") or "unknown"),
            "recommended_action": module.get("recommended_action"),
        },
        "drilldown_command": drilldown,
    }


def _paper_module_currentness(module: Mapping[str, Any], *, index: Mapping[str, Any]) -> dict[str, Any]:
    index_freshness = index.get("freshness") if isinstance(index.get("freshness"), Mapping) else {}
    code_loci_freshness = (
        module.get("code_loci_freshness")
        if isinstance(module.get("code_loci_freshness"), Mapping)
        else {}
    )
    code_loci_status = code_loci_freshness.get("status")
    currentness = {
        "recommended_action": module.get("recommended_action"),
        "action_reason": module.get("action_reason"),
        "index_freshness": index_freshness.get("status") or index_freshness.get("sync_status"),
        "index_generated_at": index.get("generated_at"),
        "code_loci_freshness": code_loci_status,
    }
    if code_loci_status == "source_changed":
        currentness.update(
            {
                "recommended_action": "verify_code_loci_before_trust",
                "action_reason": (
                    "Module text passes its projection-class contract, but one or more code loci changed "
                    "after the module; use it as a browse surface and verify live source before relying on "
                    "counts, implementation details, or freshness-sensitive claims."
                ),
                "module_recommended_action": module.get("recommended_action"),
                "trust_boundary": "paper_module_projection_requires_code_loci_verification",
                "source_newer_than_module_count": code_loci_freshness.get("source_newer_than_module_count"),
                "newest_source_path": code_loci_freshness.get("newest_source_path"),
                "newest_source_mtime": code_loci_freshness.get("newest_source_mtime"),
            }
        )
    return currentness


def _paper_module_compression_packet(module: dict[str, Any]) -> dict[str, Any]:
    """Return the authored-compression projection for a paper-module row.

    The standard's compression_authoring_contract names ``open_when``,
    ``do_not_open_when``, and ``safe_drilldown`` as required navigation fields.
    They live on ``module["compression"]`` once authored. This helper surfaces
    them on row outputs along with a per-field source map so the trust posture
    travels with the value. A row with ``compression_status`` of ``fallback`` /
    ``missing`` reports authoring debt instead of leaking fallback prose into
    the navigation lane.
    """
    comp = module.get("compression") if isinstance(module.get("compression"), dict) else {}
    status = str(comp.get("compression_status") or comp.get("status") or "missing").strip() or "missing"
    sources = comp.get("compression_sources") or {}
    findings = comp.get("findings") or []
    packet: dict[str, Any] = {
        "compression_status": status,
        "compression_sources": {k: str(v) for k, v in sources.items() if isinstance(k, str)},
    }
    if findings:
        packet["compression_findings"] = list(findings)

    def _is_authored(field: str) -> bool:
        marker = str(sources.get(field) or "").lower()
        return marker.startswith("authored")

    open_when = comp.get("open_when")
    if isinstance(open_when, str) and open_when.strip() and _is_authored("open_when"):
        packet["open_when"] = open_when.strip()
    do_not_open = comp.get("do_not_open_when")
    if isinstance(do_not_open, str) and do_not_open.strip() and _is_authored("do_not_open_when"):
        packet["do_not_open_when"] = do_not_open.strip()
    safe_drill = comp.get("safe_drilldown")
    if isinstance(safe_drill, str) and safe_drill.strip() and _is_authored("safe_drilldown"):
        packet["safe_drilldown"] = safe_drill.strip()

    if status != "authored":
        packet["authoring_debt"] = (
            "Compression fields are not authored; navigation rung uses fallbacks. "
            "Promote via `./repo-python kernel.py --paper-module-coverage` worklist."
        )
    return packet


def _paper_module_compression_passport(module: dict[str, Any]) -> dict[str, Any]:
    comp = module.get("compression") if isinstance(module.get("compression"), dict) else {}
    status = str(comp.get("compression_status") or comp.get("status") or "missing").strip()
    if status != "authored":
        return {}
    sources = comp.get("compression_sources") if isinstance(comp.get("compression_sources"), Mapping) else {}

    def _is_authored(field: str) -> bool:
        return str(sources.get(field) or "").lower().startswith("authored")

    passport: dict[str, Any] = {
        "source_contract": "codex/standards/std_paper_module.json::compression_passport_projection_contract",
    }
    cluster_keys = comp.get("cluster_keys")
    if isinstance(cluster_keys, list) and _is_authored("cluster_keys"):
        filtered_keys = [str(item).strip() for item in cluster_keys if str(item).strip()]
        if filtered_keys:
            passport["cluster_keys"] = filtered_keys

    for source_field, passport_field in (
        ("atom", "atom"),
        ("open_when", "when_to_open"),
        ("do_not_open_when", "when_not_to_open"),
        ("safe_drilldown", "safe_drilldown"),
    ):
        value = comp.get(source_field)
        if isinstance(value, str) and value.strip() and _is_authored(source_field):
            passport[passport_field] = value.strip()

    if set(passport) == {"source_contract"}:
        return {}
    return passport


def _flag_row(module: dict[str, Any], *, index: dict[str, Any]) -> dict[str, Any]:
    slug = str(module.get("slug") or "")
    previews = module.get("previews") if isinstance(module.get("previews"), dict) else {}
    depends_on = list(module.get("depends_on") or [])
    depended_on_by = list(module.get("depended_on_by") or [])
    governing_principles = [str(item) for item in list(module.get("governing_principles") or [])]
    governing_concepts = [str(item) for item in list(module.get("governing_concepts") or [])]
    row = {
        "row_id": f"paper_module:{slug}::flag",
        "artifact_kind": "paper_module",
        "band": "flag",
        "slug": slug,
        "title": str(module.get("title") or slug),
        "claim": _first_sentence(str(previews.get("tldr") or module.get("action_reason") or "")),
        "status": str(module.get("status") or "unknown"),
        "currentness": _paper_module_currentness(module, index=index),
        "dependency_counts": {
            "depends_on": len(depends_on),
            "depended_on_by": len(depended_on_by),
        },
        "governing_counts": {
            "principles": len(governing_principles),
            "concepts": len(governing_concepts),
        },
        "governing_principles": governing_principles[:3],
        "governing_concepts": governing_concepts[:3],
        "governing_refs": {
            "principles": governing_principles[:3],
            "concepts": governing_concepts[:3],
        },
        "drilldown_command": f"./repo-python kernel.py --option-surface paper_modules --band card --ids {slug}",
        "source_ref": module.get("file"),
        "standard_ref": str(PAPER_MODULE_STANDARD),
        "evidence_command": f"./repo-python kernel.py --paper-module {slug}",
    }
    compression = _paper_module_compression_packet(module)
    row["compression"] = compression
    compression_passport = _paper_module_compression_passport(module)
    if compression_passport:
        row["compression_passport"] = compression_passport
    if compression.get("open_when"):
        row["open_when"] = compression["open_when"]
    return row


def _card_row(module: dict[str, Any], *, index: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    row = _flag_row(module, index=index)
    slug = row["slug"]
    previews = module.get("previews") if isinstance(module.get("previews"), dict) else {}
    module_file = repo_root / str(module.get("file") or "")
    depends_on = [str(item) for item in list(module.get("depends_on") or [])]
    depended_on_by = [str(item) for item in list(module.get("depended_on_by") or [])]
    governing_principles = [str(item) for item in list(module.get("governing_principles") or [])]
    governing_concepts = [str(item) for item in list(module.get("governing_concepts") or [])]
    compression = row.get("compression") or _paper_module_compression_packet(module)
    update: dict[str, Any] = {
        "row_id": f"paper_module:{slug}::card",
        "band": "card",
        "tldr_excerpt": _truncate_words(str(previews.get("tldr") or ""), max_chars=700),
        "purpose_or_intent": _extract_markdown_section(module_file, "Intent"),
        "top_dependencies": depends_on[:5],
        "top_dependents": depended_on_by[:5],
        "governing_refs": {
            "principles": governing_principles[:8],
            "concepts": governing_concepts[:8],
        },
        "nearest_standard": {
            "ref": str(PAPER_MODULE_STANDARD),
            "why": "The standard defines required sections, TLDR compression budgets, and currentness expectations for paper modules.",
        },
        "nearest_skill": {
            "ref": str(PROFILE_SKILL),
            "why": "The skill describes profile-governed compression and drilldown through the same profile used to create rows.",
        },
        "evidence_commands": [
            f"./repo-python kernel.py --paper-module {slug}",
            f"./repo-python kernel.py --option-surface paper_modules --band flag",
        ],
        "omission_receipt": {
            "omitted": [
                "full markdown body",
                "full dependency transitive closure",
                "full code loci list",
                "full planned surfaces list",
            ],
            "reason": "The card band supports selecting the next read, not replacing source or context-band work.",
            "drilldown": f"./repo-python kernel.py --paper-module {slug}",
        },
    }
    if compression.get("open_when"):
        update["open_when"] = compression["open_when"]
    if compression.get("do_not_open_when"):
        update["do_not_open_when"] = compression["do_not_open_when"]
    if compression.get("safe_drilldown"):
        update["safe_drilldown"] = compression["safe_drilldown"]
    row.update(update)
    return row


def _paper_module_route_targets(route_row: dict[str, Any], axis: str) -> list[str]:
    targets: list[str] = []
    for route in route_row.get("routes") or []:
        if not isinstance(route, dict) or route.get("axis") != axis:
            continue
        target = str(route.get("target") or "").strip()
        if target and target not in targets:
            targets.append(target)
    return targets


def _paper_module_suggested_route_targets(route_row: dict[str, Any], axis: str) -> list[str]:
    targets: list[str] = []
    for route in route_row.get("suggested_routes") or []:
        if not isinstance(route, dict) or route.get("axis") != axis:
            continue
        target = str(route.get("target") or "").strip()
        if target and target not in targets:
            targets.append(target)
    return targets


def _paper_module_subdomain_label(prefix: str, subdomain: str) -> str:
    label = str(subdomain or "").replace("_", " ").replace("-", " ").title()
    return f"{prefix} / {label}" if label else prefix


def _normalize_cluster_id(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "").lower()).strip("_") or "unknown"


def _paper_module_cluster_key(module: dict[str, Any], route_row: dict[str, Any] | None = None) -> tuple[str, str, str]:
    # Cluster identity is keyed by canonical subdomain regardless of whether
    # the value came from authored primary_subdomain or heuristic
    # suggested_primary_subdomain. The authority distinction is preserved in
    # cluster_source_axis (per-row) and route_metadata counts (per-bucket) so
    # the contents-page rung does not list the same subdomain twice. See
    # std_paper_module.json::cluster_authority_collapse_rule.
    route_row = route_row or {}
    primary_subdomains = _paper_module_route_targets(route_row, "primary_subdomain")
    if primary_subdomains:
        subdomain = primary_subdomains[0]
        return (
            f"subdomain_{_normalize_cluster_id(subdomain)}",
            _paper_module_subdomain_label("Subdomain", subdomain),
            "primary_subdomain",
        )

    suggested_subdomains = _paper_module_suggested_route_targets(route_row, "suggested_primary_subdomain")
    if suggested_subdomains:
        subdomain = suggested_subdomains[0]
        return (
            f"subdomain_{_normalize_cluster_id(subdomain)}",
            _paper_module_subdomain_label("Subdomain", subdomain),
            "suggested_primary_subdomain",
        )

    hierarchy_context = module.get("hierarchy_context") if isinstance(module.get("hierarchy_context"), dict) else {}
    assembly_role = str(hierarchy_context.get("assembly_role") or "").strip()
    if assembly_role:
        return (
            f"hierarchy_{_normalize_cluster_id(assembly_role)}",
            _paper_module_subdomain_label("Dependency assembly role", assembly_role),
            "hierarchy_context.assembly_role",
        )

    slug = str(module.get("slug") or "")
    title = str(module.get("title") or slug)
    haystack = " ".join(
        [
            slug,
            title,
            str(module.get("projection_class") or ""),
            str(module.get("action_reason") or ""),
            _collapse_ws(str((module.get("previews") or {}).get("tldr") or ""))
            if isinstance(module.get("previews"), dict)
            else "",
        ]
    ).lower()
    for cluster_id, label, needles in PAPER_MODULE_CLUSTER_RULES:
        if any(needle in haystack for needle in needles):
            return f"heuristic_{cluster_id}", f"Heuristic fallback / {label}", "heuristic_text_bucket"
    return "unclassified_route_metadata", "Unclassified / route metadata missing", "unclassified"


def _paper_module_cluster_rows(
    modules: list[dict[str, Any]],
    *,
    index: dict[str, Any],
    route_rows: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    route_rows = route_rows or {}
    grouped: dict[str, dict[str, Any]] = {}
    for module in sorted(modules, key=lambda item: str(item.get("slug") or "")):
        slug = str(module.get("slug") or "")
        cluster_id, label, source_axis = _paper_module_cluster_key(module, route_rows.get(slug))
        bucket = grouped.setdefault(
            cluster_id,
            {
                "band": "cluster_flag",
                "cluster_id": cluster_id,
                "label": label,
                "cluster_source_axis": source_axis,
                "count": 0,
                "top_ids": [],
                "sample_titles": [],
                "route_metadata": {
                    "authored_primary_count": 0,
                    "suggested_primary_count": 0,
                    "hierarchy_fallback_count": 0,
                    "heuristic_fallback_count": 0,
                    "unclassified_count": 0,
                },
            },
        )
        bucket["count"] += 1
        route_metadata = bucket["route_metadata"]
        if source_axis == "primary_subdomain":
            route_metadata["authored_primary_count"] += 1
        elif source_axis == "suggested_primary_subdomain":
            route_metadata["suggested_primary_count"] += 1
        elif source_axis == "hierarchy_context.assembly_role":
            route_metadata["hierarchy_fallback_count"] += 1
        elif source_axis == "heuristic_text_bucket":
            route_metadata["heuristic_fallback_count"] += 1
        else:
            route_metadata["unclassified_count"] += 1
        if slug and len(bucket["top_ids"]) < PAPER_MODULE_CLUSTER_TOP_ID_LIMIT:
            bucket["top_ids"].append(slug)

    index_freshness = index.get("freshness") if isinstance(index.get("freshness"), dict) else {}
    # Resolve final cluster_source_axis per bucket from accumulated route_metadata.
    # A merged subdomain cluster reports the most authoritative axis represented in
    # the bucket so a future agent can read the contents-page chip without opening
    # row-level data: authored primary > suggested primary > hierarchy fallback >
    # heuristic fallback > unclassified. The split between authored and suggested
    # is preserved in route_metadata and surfaced in authority_distribution.
    for row in grouped.values():
        rm = row.get("route_metadata") or {}
        if int(rm.get("authored_primary_count") or 0) > 0:
            row["cluster_source_axis"] = "primary_subdomain"
        elif int(rm.get("suggested_primary_count") or 0) > 0:
            row["cluster_source_axis"] = "suggested_primary_subdomain"
        elif int(rm.get("hierarchy_fallback_count") or 0) > 0:
            row["cluster_source_axis"] = "hierarchy_context.assembly_role"
        elif int(rm.get("heuristic_fallback_count") or 0) > 0:
            row["cluster_source_axis"] = "heuristic_text_bucket"
        elif int(rm.get("unclassified_count") or 0) > 0:
            row["cluster_source_axis"] = "unclassified"

    order = {
        "primary_subdomain": 0,
        "suggested_primary_subdomain": 1,
        "hierarchy_context.assembly_role": 2,
        "heuristic_text_bucket": 3,
        "unclassified": 4,
    }
    rows = sorted(
        grouped.values(),
        key=lambda row: (
            order.get(str(row.get("cluster_source_axis") or ""), 9),
            str(row.get("cluster_id") or ""),
        ),
    )
    for row in rows:
        ids = ",".join(row["top_ids"])
        label = str(row.get("label") or row.get("cluster_id") or "paper-module cluster")
        rm = row.get("route_metadata") or {}
        authored = int(rm.get("authored_primary_count") or 0)
        suggested = int(rm.get("suggested_primary_count") or 0)
        hierarchy = int(rm.get("hierarchy_fallback_count") or 0)
        heuristic = int(rm.get("heuristic_fallback_count") or 0)
        unclassified = int(rm.get("unclassified_count") or 0)
        total = max(authored + suggested + hierarchy + heuristic + unclassified, 1)
        # authority_distribution: per-cluster trust-chip the contents page can read
        # without opening any row. Lets a future agent gauge whether subsequent
        # row drilldowns will hit authored frontmatter or heuristic fallback.
        chip_parts: list[str] = []
        if authored:
            chip_parts.append(f"{authored} authored")
        if suggested:
            chip_parts.append(f"{suggested} suggested")
        if hierarchy:
            chip_parts.append(f"{hierarchy} hierarchy")
        if heuristic:
            chip_parts.append(f"{heuristic} heuristic")
        if unclassified:
            chip_parts.append(f"{unclassified} unclassified")
        row["authority_distribution"] = {
            "authored_primary": authored,
            "suggested_primary": suggested,
            "hierarchy_fallback": hierarchy,
            "heuristic_fallback": heuristic,
            "unclassified": unclassified,
        }
        chip = ", ".join(chip_parts) if chip_parts else "no contributors"
        row["claim"] = _truncate_words(
            f"{label}: {row.get('count')} paper modules ({chip}).",
            max_chars=160,
        )
        if int(row.get("count") or 0) > len(row["top_ids"]):
            row["top_ids_omitted"] = int(row.get("count") or 0) - len(row["top_ids"])
        row["drilldown_command"] = (
            f"./repo-python kernel.py --option-surface paper_modules --band flag --ids {ids}"
            if ids
            else "./repo-python kernel.py --option-surface paper_modules --band flag --ids <slug>"
        )
        row["omission_policy"] = "details via drilldown"
        row.pop("route_metadata", None)
    for row in rows:
        row.pop("sample_titles", None)
    return rows


def _paper_module_cluster_authority_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-bucket authority breakdown into a contents-page-level chip.

    Tells a contents-page reader, in one row, what fraction of the corpus is
    routed by authored frontmatter versus heuristic suggestion versus fallback.
    Pairs with the per-row authority_distribution emitted by
    _paper_module_cluster_rows.
    """
    totals = {
        "authored_primary": 0,
        "suggested_primary": 0,
        "hierarchy_fallback": 0,
        "heuristic_fallback": 0,
        "unclassified": 0,
    }
    for row in rows or []:
        distribution = row.get("authority_distribution")
        if isinstance(distribution, Mapping) and distribution:
            totals["authored_primary"] += int(distribution.get("authored_primary") or 0)
            totals["suggested_primary"] += int(distribution.get("suggested_primary") or 0)
            totals["hierarchy_fallback"] += int(distribution.get("hierarchy_fallback") or 0)
            totals["heuristic_fallback"] += int(distribution.get("heuristic_fallback") or 0)
            totals["unclassified"] += int(distribution.get("unclassified") or 0)
            continue
        rm = row.get("route_metadata") or {}
        totals["authored_primary"] += int(rm.get("authored_primary_count") or 0)
        totals["suggested_primary"] += int(rm.get("suggested_primary_count") or 0)
        totals["hierarchy_fallback"] += int(rm.get("hierarchy_fallback_count") or 0)
        totals["heuristic_fallback"] += int(rm.get("heuristic_fallback_count") or 0)
        totals["unclassified"] += int(rm.get("unclassified_count") or 0)
    grand = max(sum(totals.values()), 1)
    chip_parts: list[str] = []
    if totals["authored_primary"]:
        chip_parts.append(f"{totals['authored_primary']} authored")
    if totals["suggested_primary"]:
        chip_parts.append(f"{totals['suggested_primary']} suggested")
    if totals["hierarchy_fallback"]:
        chip_parts.append(f"{totals['hierarchy_fallback']} hierarchy")
    if totals["heuristic_fallback"]:
        chip_parts.append(f"{totals['heuristic_fallback']} heuristic")
    if totals["unclassified"]:
        chip_parts.append(f"{totals['unclassified']} unclassified")
    return {
        **totals,
        "authored_share": round(totals["authored_primary"] / grand, 3),
        "suggested_share": round(totals["suggested_primary"] / grand, 3),
        "fallback_share": round(
            (totals["hierarchy_fallback"] + totals["heuristic_fallback"] + totals["unclassified"]) / grand,
            3,
        ),
        "chip": ", ".join(chip_parts) if chip_parts else "no contributors",
        "next_population_route": "./repo-python kernel.py --paper-module-coverage",
    }


def _source_mtime(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _concept_entries(repo_root: Path) -> list[dict[str, Any]]:
    concepts_root = repo_root / CONCEPT_DIR
    rows: list[dict[str, Any]] = []
    if not concepts_root.exists():
        return rows
    for path in sorted(concepts_root.glob("con_*.json")):
        try:
            concept = _load_json(path)
        except Exception:
            continue
        if not isinstance(concept, dict):
            continue
        concept_id = str(concept.get("id") or path.stem.split("_", 2)[0]).strip()
        if not concept_id:
            continue
        concept["_source_ref"] = _relative(path, repo_root)
        rows.append(concept)
    return sorted(rows, key=lambda row: str(row.get("id") or ""))


def _concept_by_id(repo_root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for concept in _concept_entries(repo_root):
        concept_id = str(concept.get("id") or "").strip()
        slug = str(concept.get("slug") or "").strip()
        source_stem = Path(str(concept.get("_source_ref") or "")).stem
        if concept_id:
            out[concept_id] = concept
        if slug:
            out[slug] = concept
        if source_stem:
            out.setdefault(source_stem, concept)
    return out


def _mechanism_entries(repo_root: Path) -> list[dict[str, Any]]:
    mechanisms_root = repo_root / MECHANISM_DIR
    rows: list[dict[str, Any]] = []
    if not mechanisms_root.exists():
        return rows
    for path in sorted(mechanisms_root.glob("mech_*.json")):
        try:
            mechanism = _load_json(path)
        except Exception:
            continue
        if not isinstance(mechanism, dict):
            continue
        mechanism_id = str(mechanism.get("id") or path.stem.split("_", 2)[0]).strip()
        if not mechanism_id:
            continue
        mechanism["_source_ref"] = _relative(path, repo_root)
        rows.append(mechanism)
    return sorted(rows, key=lambda row: str(row.get("id") or ""))


def _mechanism_by_id(repo_root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for mechanism in _mechanism_entries(repo_root):
        mechanism_id = str(mechanism.get("id") or "").strip()
        slug = str(mechanism.get("slug") or "").strip()
        if mechanism_id:
            out[mechanism_id] = mechanism
        if slug:
            out[slug] = mechanism
    return out


MECHANISM_WORKITEM_STOPWORDS = {
    "about",
    "active",
    "agent",
    "agents",
    "apply",
    "artifact",
    "artifacts",
    "build",
    "capture",
    "captured",
    "card",
    "cards",
    "codex",
    "control",
    "data",
    "docs",
    "done",
    "entry",
    "event",
    "events",
    "fix",
    "flow",
    "from",
    "graph",
    "item",
    "items",
    "lane",
    "lanes",
    "ledger",
    "local",
    "mechanism",
    "mechanisms",
    "meta",
    "model",
    "module",
    "modules",
    "node",
    "nodes",
    "plane",
    "projection",
    "projections",
    "route",
    "routes",
    "routing",
    "seed",
    "standard",
    "standards",
    "state",
    "surface",
    "surfaces",
    "system",
    "task",
    "tasks",
    "type",
    "view",
    "views",
    "work",
    "workitem",
    "workitems",
}
MECHANISM_WORKITEM_CLUSTER_TOP_IDS = 8
MECHANISM_WORKITEM_CLUSTER_FULL_TOP_IDS_THRESHOLD = 10
MECHANISM_WORKITEM_CLUSTER_OVERVIEW_LIMIT = 18
MECHANISM_WORKITEM_CLUSTER_COMPACT_OVERVIEW_LIMIT = 3
MECHANISM_WORKITEM_CLUSTER_COMPACT_TOP_IDS = 2
_MECHANISM_WORKITEM_MATCH_CACHE: dict[
    str,
    tuple[tuple[Any, ...], dict[str, list[dict[str, Any]]], list[dict[str, Any]]],
] = {}


def _mechanism_workitem_cache_fingerprint(
    repo_root: Path,
    mechanisms: Sequence[Mapping[str, Any]],
) -> tuple[Any, ...] | None:
    ledger_path = repo_root / TASK_LEDGER_LEDGER
    if not ledger_path.exists():
        return None
    ledger_stat = ledger_path.stat()
    mechanism_parts: list[tuple[Any, ...]] = []
    for mechanism in mechanisms:
        mechanism_id = str(mechanism.get("id") or "")
        source_ref = str(mechanism.get("_source_ref") or "")
        source_path = repo_root / source_ref if source_ref else None
        if source_path and source_path.exists():
            stat = source_path.stat()
            mechanism_parts.append((mechanism_id, source_ref, int(stat.st_mtime_ns), int(stat.st_size)))
        else:
            mechanism_parts.append(
                (
                    mechanism_id,
                    str(mechanism.get("slug") or ""),
                    str(mechanism.get("title") or ""),
                    tuple(str(item) for item in mechanism.get("tags") or []),
                )
            )
    return (
        str(ledger_path),
        int(ledger_stat.st_mtime_ns),
        int(ledger_stat.st_size),
        tuple(mechanism_parts),
    )


def _mechanism_workitem_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) >= 3 and token not in MECHANISM_WORKITEM_STOPWORDS
    }


def _mechanism_workitem_text(value: Any, *, depth: int = 0) -> list[str]:
    if depth > 4:
        return []
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    if isinstance(value, Mapping):
        parts: list[str] = []
        for nested in value.values():
            parts.extend(_mechanism_workitem_text(nested, depth=depth + 1))
        return parts
    if isinstance(value, list):
        parts = []
        for nested in value:
            parts.extend(_mechanism_workitem_text(nested, depth=depth + 1))
        return parts
    return []


def _mechanism_workitem_corpus(item: Mapping[str, Any]) -> tuple[str, set[str]]:
    fields = [
        "id",
        "title",
        "statement",
        "work_item_type",
        "candidate_work_item_type",
        "tags",
        "dependencies",
        "depends_on",
    ]
    text_parts: list[str] = []
    for field in fields:
        text_parts.extend(_mechanism_workitem_text(item.get(field)))
    text = " ".join(part for part in text_parts if part).lower()
    return text, _mechanism_workitem_tokens(text)


def _mechanism_signal_profile(mechanism: Mapping[str, Any]) -> dict[str, Any]:
    mechanism_id = str(mechanism.get("id") or "").strip()
    slug = str(mechanism.get("slug") or "").strip()
    title = str(mechanism.get("title") or "").strip()
    tags = [str(item).strip() for item in mechanism.get("tags") or [] if str(item or "").strip()]
    direct_phrases = {mechanism_id.lower()} if mechanism_id else set()
    if slug:
        direct_phrases.update(
            {
                slug.lower(),
                slug.replace("-", "_").lower(),
                slug.replace("-", " ").lower(),
            }
        )
    title_tokens = _mechanism_workitem_tokens(title)
    slug_tokens = _mechanism_workitem_tokens(slug.replace("-", " "))
    if title and len(title_tokens | slug_tokens) >= 2:
        direct_phrases.add(title.lower())
    return {
        "mechanism_id": mechanism_id,
        "slug": slug,
        "title": title,
        "direct_phrases": {phrase for phrase in direct_phrases if phrase},
        "name_tokens": title_tokens | slug_tokens,
        "tag_tokens": set().union(*(_mechanism_workitem_tokens(tag) for tag in tags)) if tags else set(),
    }


def _mechanism_workitem_match(
    mechanism: Mapping[str, Any],
    item: Mapping[str, Any],
    *,
    corpus: tuple[str, set[str]] | None = None,
    profile: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    profile = profile or _mechanism_signal_profile(mechanism)
    text, item_tokens = corpus if corpus is not None else _mechanism_workitem_corpus(item)
    reasons: list[str] = []
    evidence_terms: list[str] = []

    for phrase in sorted(profile["direct_phrases"], key=len, reverse=True):
        if phrase and phrase in text:
            reasons.append("direct_mechanism_ref")
            evidence_terms.append(phrase)
            break

    name_overlap = sorted(profile["name_tokens"] & item_tokens)
    name_threshold = 2 if len(profile["name_tokens"]) <= 3 else 3
    if len(name_overlap) >= name_threshold:
        reasons.append("mechanism_name_token_overlap")
        evidence_terms.extend(name_overlap[:5])

    tag_overlap = sorted(profile["tag_tokens"] & item_tokens)
    if len(tag_overlap) >= 2 and (name_overlap or reasons):
        reasons.append("mechanism_tag_overlap")
        evidence_terms.extend(tag_overlap[:5])

    if not reasons:
        return None
    work_item_id = str(item.get("id") or "")
    return {
        "id": work_item_id,
        "title": _truncate_words(str(item.get("title") or work_item_id), max_chars=120),
        "state": str(item.get("state") or item.get("status") or "unknown"),
        "work_item_type": str(item.get("work_item_type") or "unknown"),
        "match_reasons": sorted(set(reasons)),
        "evidence_terms": sorted(set(term for term in evidence_terms if term))[:8],
    }


def _mechanism_workitem_match_index(
    repo_root: Path,
    mechanisms: Sequence[Mapping[str, Any]],
    *,
    ledger_items: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    mechanism_ids = tuple(sorted(str(mechanism.get("id") or "") for mechanism in mechanisms))
    cache_key = f"{repo_root.resolve()}|{','.join(mechanism_ids)}"
    cache_fingerprint = _mechanism_workitem_cache_fingerprint(repo_root, mechanisms)
    if cache_fingerprint is not None:
        cached = _MECHANISM_WORKITEM_MATCH_CACHE.get(cache_key)
        if cached is not None and cached[0] == cache_fingerprint:
            return cached[1], cached[2]

    if ledger_items is None:
        ledger_path = repo_root / TASK_LEDGER_LEDGER
        if not ledger_path.exists():
            return {}, []
        ledger_items = _task_ledger_items(_load_json(ledger_path))

    prepared_items = [
        (item, _mechanism_workitem_corpus(item))
        for item in ledger_items
    ]
    match_index: dict[str, list[dict[str, Any]]] = {}
    matched_item_ids: set[str] = set()
    for mechanism in mechanisms:
        mechanism_id = str(mechanism.get("id") or "").strip()
        if not mechanism_id:
            continue
        profile = _mechanism_signal_profile(mechanism)
        matches = [
            match
            for item, corpus in prepared_items
            if (match := _mechanism_workitem_match(mechanism, item, corpus=corpus, profile=profile)) is not None
        ]
        matches.sort(key=lambda row: (row["state"], row["id"]))
        if matches:
            match_index[mechanism_id] = matches
            matched_item_ids.update(str(match.get("id") or "") for match in matches)

    unclassified: list[dict[str, Any]] = []
    for item, corpus in prepared_items:
        item_id = str(item.get("id") or "")
        if not item_id or item_id in matched_item_ids:
            continue
        text, _tokens = corpus
        if "mechanism_candidate" in text or "mechanism" in text:
            unclassified.append(
                {
                    "id": item_id,
                    "title": _truncate_words(str(item.get("title") or item_id), max_chars=120),
                    "state": str(item.get("state") or item.get("status") or "unknown"),
                    "work_item_type": str(item.get("work_item_type") or "unknown"),
                    "match_reasons": ["generic_mechanism_pressure"],
                    "evidence_terms": ["mechanism"],
                }
            )
    unclassified.sort(key=lambda row: (row["state"], row["id"]))
    if cache_fingerprint is not None:
        _MECHANISM_WORKITEM_MATCH_CACHE[cache_key] = (
            cache_fingerprint,
            match_index,
            unclassified,
        )
    return match_index, unclassified


def _mechanism_workitem_cluster_top_ids(matches: Sequence[Mapping[str, Any]]) -> list[str]:
    item_ids = [str(match.get("id") or "") for match in matches if str(match.get("id") or "")]
    if len(item_ids) <= MECHANISM_WORKITEM_CLUSTER_FULL_TOP_IDS_THRESHOLD:
        return item_ids
    return item_ids[:MECHANISM_WORKITEM_CLUSTER_TOP_IDS]


def _mechanism_workitem_pressure_summary(
    matches: Sequence[Mapping[str, Any]],
    *,
    mechanism_id: str,
) -> dict[str, Any]:
    return {
        "workitem_pressure_count": len(matches),
        "top_workitem_ids": _mechanism_workitem_cluster_top_ids(matches),
        "task_ledger_cluster_id": f"mechanism:{mechanism_id}",
        "task_ledger_cluster_drilldown": (
            f"./repo-python kernel.py --option-surface task_ledger --band cluster_flag --ids mechanism:{mechanism_id}"
        ),
    }


def _concept_edge_items(concept: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = concept.get(key) if isinstance(concept.get(key), list) else []
    out: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        target = str(item.get("target") or "").strip()
        if not target:
            continue
        out.append(
            {
                "target": target,
                "relation": str(item.get("relation") or ""),
                "gloss": _truncate_words(
                    str(item.get("forward_gloss") or item.get("gloss") or ""),
                    max_chars=220,
                ),
            }
        )
    return out


def _principle_edge_affordance(repo_root: Path, edge: dict[str, Any]) -> dict[str, Any]:
    target = str(edge.get("target") or "").strip()
    row = {
        "target": target,
        "relation": str(edge.get("relation") or ""),
        "gloss": str(edge.get("gloss") or ""),
        "drilldown_command": f"./repo-python kernel.py --option-surface principles --band card --ids {target}",
    }
    principle = _principle_by_id(repo_root).get(target)
    if not principle:
        return {
            **row,
            "missing_projection_reason": "principle id did not resolve in raw_seed_principles.json",
        }
    return {
        **row,
        "label": str(principle.get("title") or principle.get("slug") or target),
        "compression": _first_sentence(str(principle.get("statement") or ""), max_chars=220),
        "source_ref": str(RAW_SEED_PRINCIPLES),
        "evidence_command": "./repo-python kernel.py --docs-route raw_seed_principles",
    }


def _concept_edge_affordance(repo_root: Path, edge: dict[str, Any]) -> dict[str, Any]:
    target = str(edge.get("target") or "").strip()
    row = {
        "target": target,
        "relation": str(edge.get("relation") or ""),
        "gloss": str(edge.get("gloss") or ""),
        "drilldown_command": f"./repo-python kernel.py --option-surface concepts --band card --ids {target}",
    }
    concept = _concept_by_id(repo_root).get(target)
    if not concept:
        return {
            **row,
            "missing_projection_reason": "concept id did not resolve under codex/doctrine/concepts",
        }
    source_ref = str(concept.get("_source_ref") or "")
    return {
        **row,
        "label": str(concept.get("title") or concept.get("slug") or target),
        "compression": _first_sentence(str(concept.get("statement") or ""), max_chars=220),
        "source_ref": source_ref,
        "evidence_command": f"jq '.' {source_ref}" if source_ref else "",
    }


def _mechanism_edge_affordance(repo_root: Path, edge: dict[str, Any]) -> dict[str, Any]:
    target = str(edge.get("target") or "").strip()
    row = {
        "target": target,
        "relation": str(edge.get("relation") or ""),
        "gloss": str(edge.get("gloss") or ""),
        "drilldown_command": f"./repo-python kernel.py --option-surface mechanisms --band card --ids {target}",
    }
    mechanism = _mechanism_by_id(repo_root).get(target)
    if not mechanism:
        return {
            **row,
            "missing_projection_reason": "mechanism id did not resolve under codex/doctrine/mechanisms",
        }
    source_ref = str(mechanism.get("_source_ref") or "")
    return {
        **row,
        "label": str(mechanism.get("title") or mechanism.get("slug") or target),
        "compression": _first_sentence(str(mechanism.get("statement") or ""), max_chars=220),
        "source_ref": source_ref,
        "evidence_command": f"jq '.' {source_ref}" if source_ref else "",
    }


def _concept_flag_edge_summary(concept: dict[str, Any]) -> dict[str, Any]:
    principle_edges = _concept_edge_items(concept, "principle_edges")
    mechanism_edges = _concept_edge_items(concept, "mechanism_edges")
    synthesis = concept.get("synthesis") if isinstance(concept.get("synthesis"), dict) else {}
    synthesis_status = str(synthesis.get("status") or "") if isinstance(synthesis, dict) else ""
    return {
        "principle_edge_count": len(principle_edges),
        "mechanism_edge_count": len(mechanism_edges),
        "top_principle_edges": [
            {"target": edge["target"], "relation": edge["relation"]}
            for edge in principle_edges[:4]
        ],
        "top_mechanism_edges": [
            {"target": edge["target"], "relation": edge["relation"]}
            for edge in mechanism_edges[:4]
        ],
        "synthesis_status": synthesis_status,
    }


def _concept_flag_row(concept: dict[str, Any]) -> dict[str, Any]:
    concept_id = str(concept.get("id") or "")
    source_ref = str(concept.get("_source_ref") or "")
    edge_summary = _concept_flag_edge_summary(concept)
    return {
        "row_id": f"concept:{concept_id}::flag",
        "artifact_kind": "concept",
        "band": "flag",
        "concept_id": concept_id,
        "slug": str(concept.get("slug") or concept_id),
        "title": str(concept.get("title") or concept_id),
        "label": str(concept.get("title") or concept.get("slug") or concept_id),
        "status": str(concept.get("status") or "unknown"),
        "scope": str(concept.get("scope") or "unknown"),
        "tags": [str(item) for item in list(concept.get("tags") or [])],
        "claim": _first_sentence(str(concept.get("statement") or ""), max_chars=280),
        "compression": _first_sentence(str(concept.get("statement") or ""), max_chars=280),
        "principle_edge_count": edge_summary["principle_edge_count"],
        "mechanism_edge_count": edge_summary["mechanism_edge_count"],
        "top_principle_edges": edge_summary["top_principle_edges"],
        "top_mechanism_edges": edge_summary["top_mechanism_edges"],
        "synthesis_status": edge_summary["synthesis_status"],
        "source_ref": source_ref,
        "standard_ref": str(CONCEPT_STANDARD),
        "drilldown_command": f"./repo-python kernel.py --option-surface concepts --band card --ids {concept_id}",
        "evidence_command": f"jq '.' {source_ref}" if source_ref else "",
    }


def _principle_incoming_concept_edges(repo_root: Path) -> dict[str, list[dict[str, Any]]]:
    edges_by_principle: dict[str, list[dict[str, Any]]] = {}
    concepts = {
        id(row): row
        for row in _concept_by_id(repo_root).values()
        if isinstance(row, dict)
    }.values()
    for concept in concepts:
        concept_id = str(concept.get("id") or "")
        if not concept_id:
            continue
        title = str(concept.get("title") or concept.get("slug") or concept_id)
        for edge in _concept_edge_items(concept, "principle_edges"):
            target = str(edge.get("target") or "")
            if not target:
                continue
            edges_by_principle.setdefault(target, []).append(
                {
                    "concept_id": concept_id,
                    "title": title,
                    "relation": str(edge.get("relation") or ""),
                    "gloss": _truncate_words(str(edge.get("gloss") or ""), max_chars=180),
                    "mechanism_targets": [item["target"] for item in _concept_edge_items(concept, "mechanism_edges")[:4]],
                    "drilldown_command": f"./repo-python kernel.py --option-surface concepts --band card --ids {concept_id}",
                }
            )
    for rows in edges_by_principle.values():
        rows.sort(key=lambda row: (str(row.get("concept_id") or ""), str(row.get("relation") or "")))
    return edges_by_principle


def _concept_card_row(repo_root: Path, concept: dict[str, Any]) -> dict[str, Any]:
    row = _concept_flag_row(concept)
    evidence = concept.get("evidence") if isinstance(concept.get("evidence"), list) else []
    tests = concept.get("tests") if isinstance(concept.get("tests"), list) else []
    failure_modes = concept.get("failure_modes") if isinstance(concept.get("failure_modes"), list) else []
    decision_examples = concept.get("decision_examples") if isinstance(concept.get("decision_examples"), list) else []
    principle_edges = [
        _principle_edge_affordance(repo_root, edge)
        for edge in _concept_edge_items(concept, "principle_edges")
    ]
    mechanism_edges = [
        _mechanism_edge_affordance(repo_root, edge)
        for edge in _concept_edge_items(concept, "mechanism_edges")
    ]
    synthesis = concept.get("synthesis") if isinstance(concept.get("synthesis"), dict) else {}
    row.update(
        {
            "row_id": f"concept:{row['concept_id']}::card",
            "band": "card",
            "statement": str(concept.get("statement") or ""),
            "provenance": concept.get("provenance"),
            "principle_edges": principle_edges[:8],
            "mechanism_edges": mechanism_edges[:8],
            "linked_principles": [edge["target"] for edge in principle_edges],
            "linked_mechanisms": [edge["target"] for edge in mechanism_edges],
            "evidence_refs": [
                {
                    "ref": str(item.get("ref") or ""),
                    "role": str(item.get("role") or ""),
                    "gloss": _truncate_words(str(item.get("gloss") or ""), max_chars=240),
                }
                for item in evidence[:5]
                if isinstance(item, dict)
            ],
            "top_tests": [
                {
                    "check": _truncate_words(str(item.get("check") or ""), max_chars=260),
                    "locus": _truncate_words(str(item.get("locus") or ""), max_chars=180),
                    "violation": _truncate_words(str(item.get("violation") or ""), max_chars=220),
                }
                for item in tests[:3]
                if isinstance(item, dict)
            ],
            "top_failure_modes": [_truncate_words(str(item), max_chars=220) for item in failure_modes[:5]],
            "decision_examples": [_truncate_words(str(item), max_chars=220) for item in decision_examples[:4]],
            "note_excerpt": _truncate_words(str(concept.get("note") or ""), max_chars=360),
            "synthesis_status": synthesis.get("status"),
            "nearest_standard": {
                "ref": str(CONCEPT_STANDARD),
                "why": "The concept standard owns concept identity, statement, edges, evidence, tests, and synthesis posture.",
            },
            "nearest_skill": {
                "ref": "codex/doctrine/skills/doctrine/concept_mechanism_curation.md",
                "why": "Concept/mechanism curation governs when concept rows should be added, refined, or connected.",
            },
            "omission_receipt": {
                "omitted": [
                    "full synthesis body",
                    "full reference_groups",
                    "transitive principle/mechanism neighborhoods",
                ],
                "reason": "The concept card supports selection and first application; deep concept work must reopen the source JSON.",
                "drilldown": f"jq '.' {row['source_ref']}",
            },
        }
    )
    return row


def build_concepts_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="concepts",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "unsupported_band_for_kind",
                "message": f"Band {band!r} is not supported for concepts. Supported bands: flag, card.",
                "supported_bands": ["flag", "card"],
            }
        )
        return payload

    if not (repo_root / CONCEPT_DIR).exists() or not (repo_root / CONCEPT_STANDARD).exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="concepts",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The concept directory or concept standard file is missing.",
                "refs": [str(CONCEPT_DIR), str(CONCEPT_STANDARD)],
            }
        )
        return payload

    concepts_by_key = _concept_by_id(repo_root)
    all_concepts = sorted({id(row): row for row in concepts_by_key.values()}.values(), key=lambda r: str(r.get("id") or ""))
    if ids:
        rows_source = [concepts_by_key[item] for item in ids if item in concepts_by_key]
        missing_ids = [item for item in ids if item not in concepts_by_key]
    else:
        rows_source = all_concepts
        missing_ids = []

    rows = (
        [_concept_card_row(repo_root, row) for row in rows_source]
        if band == "card"
        else [_concept_flag_row(row) for row in rows_source]
    )
    status_counts: dict[str, int] = {}
    for row in all_concepts:
        status = str(row.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    principle_edge_target_counter: Counter[str] = Counter()
    mechanism_edge_target_counter: Counter[str] = Counter()
    synthesis_status_counts: dict[str, int] = {}
    concepts_with_principle_edges = 0
    concepts_with_mechanism_edges = 0
    concepts_isolated = 0
    principle_edge_total = 0
    mechanism_edge_total = 0
    for row in all_concepts:
        principle_targets = [edge["target"] for edge in _concept_edge_items(row, "principle_edges")]
        mechanism_targets = [edge["target"] for edge in _concept_edge_items(row, "mechanism_edges")]
        principle_edge_target_counter.update(principle_targets)
        mechanism_edge_target_counter.update(mechanism_targets)
        principle_edge_total += len(principle_targets)
        mechanism_edge_total += len(mechanism_targets)
        if principle_targets:
            concepts_with_principle_edges += 1
        if mechanism_targets:
            concepts_with_mechanism_edges += 1
        if not principle_targets and not mechanism_targets:
            concepts_isolated += 1
        synthesis = row.get("synthesis") if isinstance(row.get("synthesis"), dict) else {}
        synthesis_status = str(synthesis.get("status") or "missing") if isinstance(synthesis, dict) else "missing"
        if not synthesis:
            synthesis_status = "missing"
        synthesis_status_counts[synthesis_status] = synthesis_status_counts.get(synthesis_status, 0) + 1

    edge_population = {
        "concepts_total": len(all_concepts),
        "concepts_with_principle_edges": concepts_with_principle_edges,
        "concepts_with_mechanism_edges": concepts_with_mechanism_edges,
        "concepts_isolated_no_cross_kind_edges": concepts_isolated,
        "principle_edge_total": principle_edge_total,
        "mechanism_edge_total": mechanism_edge_total,
        "synthesis_status_counts": synthesis_status_counts,
        "top_principle_targets": [
            {"target": target, "incoming_concept_edges": count}
            for target, count in principle_edge_target_counter.most_common(8)
        ],
        "top_mechanism_targets": [
            {"target": target, "incoming_concept_edges": count}
            for target, count in mechanism_edge_target_counter.most_common(8)
        ],
    }

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "concepts",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "standard_owned_projection_not_source_authority",
        "governing_standard": {
            "ref": str(CONCEPT_STANDARD),
            "schema_version": "doctrine_concept_standard_v2",
            "owned_bands": ["flag", "card"],
        },
        "source_refs": [str(CONCEPT_DIR), str(CONCEPT_STANDARD)],
        "summary": {
            "row_count": len(rows),
            "total_available": len(all_concepts),
            "selection_method": "artifact_kind_enumeration_from_concept_json",
            "drilldown_by": "concept_id_slug_or_source_stem",
            "status_counts": status_counts,
            "edge_population": edge_population,
            "query_used": False,
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["flag", "card"],
            "source_authority_remains_concept_json": True,
            "flag_surfaces_cross_kind_edges": True,
            "flag_edge_keys": [
                "principle_edge_count",
                "mechanism_edge_count",
                "top_principle_edges",
                "top_mechanism_edges",
                "synthesis_status",
            ],
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface concepts --band flag",
                "reason": "Browse all concepts with compact statements, cross-kind edge counts, and source refs.",
            },
            {
                "command": "./repo-python kernel.py --option-surface concepts --band card --ids <con_id>",
                "reason": "Drill one concept to edge, evidence, test, and omission context.",
            },
        ],
        "warnings": [],
    }


def _mechanism_edge_items(mechanism: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = mechanism.get(key) if isinstance(mechanism.get(key), list) else []
    out: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        target = str(item.get("target") or "").strip()
        if target:
            out.append(
                {
                    "target": target,
                    "relation": str(item.get("relation") or ""),
                    "gloss": _truncate_words(str(item.get("gloss") or item.get("forward_gloss") or ""), max_chars=220),
                }
            )
    return out


def _mechanism_flag_edge_summary(mechanism: dict[str, Any]) -> dict[str, Any]:
    concept_edges = _mechanism_edge_items(mechanism, "concept_edges")
    upstream_raw = list(mechanism.get("upstream") or []) if isinstance(mechanism.get("upstream"), list) else []
    downstream_raw = list(mechanism.get("downstream") or []) if isinstance(mechanism.get("downstream"), list) else []
    upstream = [str(item).strip() for item in upstream_raw if str(item or "").strip()]
    downstream = [str(item).strip() for item in downstream_raw if str(item or "").strip()]
    code_loci_raw = mechanism.get("code_loci") if isinstance(mechanism.get("code_loci"), list) else []
    code_loci_count = sum(1 for item in code_loci_raw if isinstance(item, dict))
    return {
        "concept_edge_count": len(concept_edges),
        "top_concept_edges": [
            {"target": edge["target"], "relation": edge["relation"]}
            for edge in concept_edges[:4]
        ],
        "upstream_count": len(upstream),
        "top_upstream": upstream[:4],
        "downstream_count": len(downstream),
        "top_downstream": downstream[:4],
        "code_loci_count": code_loci_count,
        "drift_sensitivity": str(mechanism.get("drift_sensitivity") or ""),
    }


def _mechanism_flag_row(
    mechanism: dict[str, Any],
    *,
    workitem_matches: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    mechanism_id = str(mechanism.get("id") or "")
    source_ref = str(mechanism.get("_source_ref") or "")
    edge_summary = _mechanism_flag_edge_summary(mechanism)
    row = {
        "row_id": f"mechanism:{mechanism_id}::flag",
        "artifact_kind": "mechanism",
        "band": "flag",
        "mechanism_id": mechanism_id,
        "slug": str(mechanism.get("slug") or mechanism_id),
        "title": str(mechanism.get("title") or mechanism_id),
        "label": str(mechanism.get("title") or mechanism.get("slug") or mechanism_id),
        "status": str(mechanism.get("status") or "unknown"),
        "scope": str(mechanism.get("scope") or "unknown"),
        "tags": [str(item) for item in list(mechanism.get("tags") or [])],
        "claim": _first_sentence(str(mechanism.get("statement") or ""), max_chars=280),
        "compression": _first_sentence(str(mechanism.get("statement") or ""), max_chars=280),
        "concept_edge_count": edge_summary["concept_edge_count"],
        "top_concept_edges": edge_summary["top_concept_edges"],
        "upstream_count": edge_summary["upstream_count"],
        "top_upstream": edge_summary["top_upstream"],
        "downstream_count": edge_summary["downstream_count"],
        "top_downstream": edge_summary["top_downstream"],
        "code_loci_count": edge_summary["code_loci_count"],
        "drift_sensitivity": edge_summary["drift_sensitivity"],
        "source_ref": source_ref,
        "standard_ref": str(MECHANISM_STANDARD),
        "drilldown_command": f"./repo-python kernel.py --option-surface mechanisms --band card --ids {mechanism_id}",
        "evidence_command": f"jq '.' {source_ref}" if source_ref else "",
    }
    if workitem_matches is not None:
        row.update(_mechanism_workitem_pressure_summary(workitem_matches, mechanism_id=mechanism_id))
    return row


def _mechanism_relationship_refs(repo_root: Path, ids: list[Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in ids:
        mechanism_id = str(item or "").strip()
        if not mechanism_id:
            continue
        ref = _mechanism_edge_affordance(repo_root, {"target": mechanism_id})
        ref["id"] = mechanism_id
        refs.append(ref)
    return refs


def _python_scope_lookup(index: dict[str, Any]) -> dict[tuple[str, str], list[tuple[str, dict[str, Any]]]]:
    scopes = _python_scope_entries(index)
    symbol_id_counts: dict[str, int] = {}
    for scope in scopes:
        symbol_id = str(scope.get("symbol_id") or "").strip()
        if symbol_id:
            symbol_id_counts[symbol_id] = symbol_id_counts.get(symbol_id, 0) + 1

    by_path_name: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]] = {}
    for scope in scopes:
        path = str(scope.get("path") or "").strip()
        name = str(scope.get("name") or "").strip()
        if not path or not name:
            continue
        scope_id = _python_scope_id_for(scope, symbol_id_counts=symbol_id_counts)
        by_path_name.setdefault((path, name), []).append((scope_id, scope))
    return by_path_name


def _mechanism_code_function_ref(
    *,
    path: str,
    function_name: str,
    scope_lookup: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "name": function_name,
    }
    matches = scope_lookup.get((path, function_name), [])
    if not matches:
        return {
            **row,
            "scope_id": f"{path}::{function_name}",
            "scope_drilldown_command": (
                f"./repo-python kernel.py --option-surface python_scopes --band card --ids {path}::{function_name}"
            ),
            "missing_projection_reason": "function name did not resolve to a Python scope for this path",
        }
    if len(matches) > 1:
        candidate_scope_ids = [scope_id for scope_id, _scope in matches]
        return {
            **row,
            "candidate_scope_ids": candidate_scope_ids,
            "missing_projection_reason": "function name resolved to multiple Python scopes; choose one candidate scope_id",
        }

    scope_id, scope = matches[0]
    return {
        **row,
        "scope_id": scope_id,
        "scope_kind": str(scope.get("scope_kind") or ""),
        "line_start": scope.get("line_start"),
        "line_end": scope.get("line_end"),
        "scope_drilldown_command": f"./repo-python kernel.py --option-surface python_scopes --band card --ids {scope_id}",
        "evidence_command": _python_scope_evidence_command(scope, scope_id=scope_id),
    }


def _mechanism_code_locus_row(
    item: dict[str, Any],
    *,
    scope_lookup: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]],
) -> dict[str, Any]:
    path = str(item.get("path") or "").strip()
    function_names = [str(fn) for fn in list(item.get("functions") or []) if str(fn or "").strip()]
    return {
        "path": path,
        "file_drilldown_command": f"./repo-python kernel.py --option-surface python_files --band card --ids {path}" if path else "",
        "file_evidence_command": f"./repo-python kernel.py --compile {path}" if path else "",
        "functions": [
            _mechanism_code_function_ref(
                path=path,
                function_name=function_name,
                scope_lookup=scope_lookup,
            )
            for function_name in function_names
        ],
        "role": _truncate_words(str(item.get("role") or ""), max_chars=240),
    }


def _mechanism_card_row(
    repo_root: Path,
    mechanism: dict[str, Any],
    *,
    workitem_matches: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    mechanism_id = str(mechanism.get("id") or "")
    if workitem_matches is None:
        match_index, _unclassified = _mechanism_workitem_match_index(repo_root, [mechanism])
        workitem_matches = match_index.get(mechanism_id, [])
    row = _mechanism_flag_row(mechanism, workitem_matches=workitem_matches)
    evidence = mechanism.get("evidence") if isinstance(mechanism.get("evidence"), list) else []
    tests = mechanism.get("tests") if isinstance(mechanism.get("tests"), list) else []
    failure_modes = mechanism.get("failure_modes") if isinstance(mechanism.get("failure_modes"), list) else []
    decision_examples = mechanism.get("decision_examples") if isinstance(mechanism.get("decision_examples"), list) else []
    code_loci = mechanism.get("code_loci") if isinstance(mechanism.get("code_loci"), list) else []
    scope_lookup = _python_scope_lookup(_python_file_load_index(repo_root))
    concept_edges = [
        _concept_edge_affordance(repo_root, edge)
        for edge in _mechanism_edge_items(mechanism, "concept_edges")
    ]
    upstream = [str(item) for item in list(mechanism.get("upstream") or [])[:8]]
    downstream = [str(item) for item in list(mechanism.get("downstream") or [])[:8]]
    row.update(
        {
            "row_id": f"mechanism:{row['mechanism_id']}::card",
            "band": "card",
            "statement": str(mechanism.get("statement") or ""),
            "provenance": mechanism.get("provenance"),
            "concept_edges": concept_edges[:8],
            "linked_concepts": [edge["target"] for edge in concept_edges],
            "code_loci": [
                _mechanism_code_locus_row(item, scope_lookup=scope_lookup)
                for item in code_loci[:6]
                if isinstance(item, dict)
            ],
            "upstream": upstream,
            "downstream": downstream,
            "upstream_refs": _mechanism_relationship_refs(repo_root, upstream),
            "downstream_refs": _mechanism_relationship_refs(repo_root, downstream),
            "drift_sensitivity": str(mechanism.get("drift_sensitivity") or ""),
            "evidence_refs": [
                {
                    "ref": str(item.get("ref") or ""),
                    "role": str(item.get("role") or ""),
                    "gloss": _truncate_words(str(item.get("gloss") or ""), max_chars=240),
                }
                for item in evidence[:5]
                if isinstance(item, dict)
            ],
            "top_tests": [
                {
                    "check": _truncate_words(str(item.get("check") or ""), max_chars=260),
                    "locus": _truncate_words(str(item.get("locus") or ""), max_chars=180),
                    "violation": _truncate_words(str(item.get("violation") or ""), max_chars=220),
                }
                for item in tests[:3]
                if isinstance(item, dict)
            ],
            "top_failure_modes": [_truncate_words(str(item), max_chars=220) for item in failure_modes[:5]],
            "decision_examples": [_truncate_words(str(item), max_chars=220) for item in decision_examples[:4]],
            "workitem_pressure": {
                "count": len(workitem_matches),
                "top_matches": list(workitem_matches[:8]),
                "authority": "Task Ledger events remain WorkItem authority; this mechanism row only exposes deterministic affinity for browsing.",
                "cluster_drilldown": (
                    f"./repo-python kernel.py --option-surface task_ledger --band cluster_flag --ids mechanism:{row['mechanism_id']}"
                ),
            },
            "note_excerpt": _truncate_words(str(mechanism.get("note") or ""), max_chars=360),
            "nearest_standard": {
                "ref": str(MECHANISM_STANDARD),
                "why": "The mechanism standard owns code-grounded mechanism identity, statement, loci, edges, evidence, and drift posture.",
            },
            "nearest_skill": {
                "ref": "codex/doctrine/skills/doctrine/concept_mechanism_curation.md",
                "why": "Concept/mechanism curation governs when mechanism rows should be added, refined, or connected.",
            },
            "omission_receipt": {
                "omitted": [
                    "full reference_groups",
                    "transitive concept/mechanism neighborhoods",
                    "full code context for code_loci",
                    "full WorkItem match evidence beyond bounded top_matches",
                ],
                "reason": "The mechanism card supports selection and first application; deep mechanism work must reopen the source JSON and named code loci.",
                "drilldown": f"jq '.' {row['source_ref']}",
            },
        }
    )
    return row


def build_mechanisms_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="mechanisms",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "unsupported_band_for_kind",
                "message": f"Band {band!r} is not supported for mechanisms. Supported bands: flag, card.",
                "supported_bands": ["flag", "card"],
            }
        )
        return payload

    if not (repo_root / MECHANISM_DIR).exists() or not (repo_root / MECHANISM_STANDARD).exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="mechanisms",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The mechanism directory or mechanism standard file is missing.",
                "refs": [str(MECHANISM_DIR), str(MECHANISM_STANDARD)],
            }
        )
        return payload

    mechanisms_by_key = _mechanism_by_id(repo_root)
    all_mechanisms = sorted(
        {id(row): row for row in mechanisms_by_key.values()}.values(),
        key=lambda r: str(r.get("id") or ""),
    )
    if ids:
        rows_source = [mechanisms_by_key[item] for item in ids if item in mechanisms_by_key]
        missing_ids = [item for item in ids if item not in mechanisms_by_key]
    else:
        rows_source = all_mechanisms
        missing_ids = []

    workitem_match_index, unclassified_workitem_pressure = _mechanism_workitem_match_index(
        repo_root,
        all_mechanisms,
    )
    rows = (
        [
            _mechanism_card_row(
                repo_root,
                row,
                workitem_matches=workitem_match_index.get(str(row.get("id") or ""), []),
            )
            for row in rows_source
        ]
        if band == "card"
        else [
            _mechanism_flag_row(
                row,
                workitem_matches=workitem_match_index.get(str(row.get("id") or ""), []),
            )
            for row in rows_source
        ]
    )
    status_counts: dict[str, int] = {}
    for row in all_mechanisms:
        status = str(row.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    concept_edge_target_counter: Counter[str] = Counter()
    upstream_target_counter: Counter[str] = Counter()
    downstream_target_counter: Counter[str] = Counter()
    drift_sensitivity_counts: dict[str, int] = {}
    mechanisms_with_concept_edges = 0
    mechanisms_with_upstream = 0
    mechanisms_with_downstream = 0
    mechanisms_with_code_loci = 0
    mechanisms_isolated = 0
    mechanisms_with_workitem_pressure = 0
    workitem_pressure_total = 0
    concept_edge_total = 0
    upstream_total = 0
    downstream_total = 0
    for row in all_mechanisms:
        concept_targets = [edge["target"] for edge in _mechanism_edge_items(row, "concept_edges")]
        upstream_targets = [
            str(item).strip()
            for item in (row.get("upstream") or [])
            if isinstance(row.get("upstream"), list) and str(item or "").strip()
        ]
        downstream_targets = [
            str(item).strip()
            for item in (row.get("downstream") or [])
            if isinstance(row.get("downstream"), list) and str(item or "").strip()
        ]
        code_loci_present = bool(
            isinstance(row.get("code_loci"), list)
            and any(isinstance(item, dict) for item in row.get("code_loci") or [])
        )
        concept_edge_target_counter.update(concept_targets)
        upstream_target_counter.update(upstream_targets)
        downstream_target_counter.update(downstream_targets)
        concept_edge_total += len(concept_targets)
        upstream_total += len(upstream_targets)
        downstream_total += len(downstream_targets)
        if concept_targets:
            mechanisms_with_concept_edges += 1
        if upstream_targets:
            mechanisms_with_upstream += 1
        if downstream_targets:
            mechanisms_with_downstream += 1
        if code_loci_present:
            mechanisms_with_code_loci += 1
        if not concept_targets and not upstream_targets and not downstream_targets:
            mechanisms_isolated += 1
        mechanism_matches = workitem_match_index.get(str(row.get("id") or ""), [])
        if mechanism_matches:
            mechanisms_with_workitem_pressure += 1
            workitem_pressure_total += len(mechanism_matches)
        drift_value = str(row.get("drift_sensitivity") or "missing")
        if not row.get("drift_sensitivity"):
            drift_value = "missing"
        drift_sensitivity_counts[drift_value] = drift_sensitivity_counts.get(drift_value, 0) + 1

    edge_population = {
        "mechanisms_total": len(all_mechanisms),
        "mechanisms_with_concept_edges": mechanisms_with_concept_edges,
        "mechanisms_with_upstream": mechanisms_with_upstream,
        "mechanisms_with_downstream": mechanisms_with_downstream,
        "mechanisms_with_code_loci": mechanisms_with_code_loci,
        "mechanisms_isolated_no_edges_or_internal_graph": mechanisms_isolated,
        "mechanisms_with_workitem_pressure": mechanisms_with_workitem_pressure,
        "workitem_pressure_match_total": workitem_pressure_total,
        "unclassified_mechanism_pressure_count": len(unclassified_workitem_pressure),
        "concept_edge_total": concept_edge_total,
        "upstream_total": upstream_total,
        "downstream_total": downstream_total,
        "drift_sensitivity_counts": drift_sensitivity_counts,
        "top_concept_targets": [
            {"target": target, "incoming_mechanism_edges": count}
            for target, count in concept_edge_target_counter.most_common(8)
        ],
        "top_upstream_targets": [
            {"target": target, "incoming_upstream_refs": count}
            for target, count in upstream_target_counter.most_common(8)
        ],
        "top_downstream_targets": [
            {"target": target, "incoming_downstream_refs": count}
            for target, count in downstream_target_counter.most_common(8)
        ],
        "top_workitem_pressure": [
            {
                "target": mechanism_id,
                "matching_workitem_count": len(matches),
                "top_workitem_ids": _mechanism_workitem_cluster_top_ids(matches),
            }
            for mechanism_id, matches in sorted(
                workitem_match_index.items(),
                key=lambda item: (-len(item[1]), item[0]),
            )[:8]
        ],
    }

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "mechanisms",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "standard_owned_projection_not_source_authority",
        "governing_standard": {
            "ref": str(MECHANISM_STANDARD),
            "schema_version": "doctrine_mechanism_v1",
            "owned_bands": ["flag", "card"],
        },
        "source_refs": [str(MECHANISM_DIR), str(MECHANISM_STANDARD), str(TASK_LEDGER_LEDGER)],
        "summary": {
            "row_count": len(rows),
            "total_available": len(all_mechanisms),
            "selection_method": "artifact_kind_enumeration_from_mechanism_json",
            "drilldown_by": "mechanism_id_or_slug",
            "status_counts": status_counts,
            "edge_population": edge_population,
            "query_used": False,
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["flag", "card"],
            "source_authority_remains_mechanism_json": True,
            "workitem_pressure_authority_remains_task_ledger": True,
            "flag_surfaces_cross_kind_edges": True,
            "flag_edge_keys": [
                "concept_edge_count",
                "top_concept_edges",
                "upstream_count",
                "top_upstream",
                "downstream_count",
                "top_downstream",
                "code_loci_count",
                "drift_sensitivity",
                "workitem_pressure_count",
                "top_workitem_ids",
            ],
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface mechanisms --band flag",
                "reason": "Browse all mechanisms with compact statements, cross-kind edge counts, internal-graph counts, and source refs.",
            },
            {
                "command": "./repo-python kernel.py --option-surface mechanisms --band card --ids <mech_id>",
                "reason": "Drill one mechanism to concept edges, code loci, evidence, tests, and omission context.",
            },
        ],
        "warnings": [],
    }


def _candidate_flag_row(candidate: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id") or "")
    compression_hint = _truncate_words(str(candidate.get("compression_hint") or ""), max_chars=260)
    title_hint = str(candidate.get("title_hint") or "")
    claim = compression_hint or title_hint or candidate_id
    return {
        "row_id": f"concept_mechanism_candidate:{candidate_id}::flag",
        "artifact_kind": "concept_mechanism_candidate",
        "band": "flag",
        "candidate_id": candidate_id,
        "candidate_kind": str(candidate.get("candidate_kind") or ""),
        "recommended_action": str(candidate.get("recommended_action") or ""),
        "title": title_hint or candidate_id,
        "label": title_hint or candidate_id,
        "claim": claim,
        "compression": compression_hint,
        "source_pressure": [str(item) for item in list(candidate.get("source_pressure") or [])],
        "confidence": candidate.get("confidence"),
        "primary_anchor": (candidate.get("evidence_anchors") or [{}])[0],
        "nearest_existing_count": len(candidate.get("nearest_existing") or []),
        "source_ref": str(CONCEPT_MECHANISM_CANDIDATES),
        "drilldown_command": (
            f"./repo-python kernel.py --option-surface concept_mechanism_candidates --band card --ids {candidate_id}"
        ),
        "evidence_command": f"jq --arg id '{candidate_id}' '.candidates[] | select(.candidate_id==$id)' {CONCEPT_MECHANISM_CANDIDATES}",
    }


def _candidate_card_row(candidate: dict[str, Any]) -> dict[str, Any]:
    row = _candidate_flag_row(candidate)
    row.update(
        {
            "row_id": f"concept_mechanism_candidate:{row['candidate_id']}::card",
            "band": "card",
            "compression_hint": str(candidate.get("compression_hint") or ""),
            "evidence_anchors": [
                {
                    "kind": str(anchor.get("kind") or ""),
                    "ref": str(anchor.get("ref") or ""),
                    "why": _truncate_words(str(anchor.get("why") or ""), max_chars=260),
                }
                for anchor in list(candidate.get("evidence_anchors") or [])
                if isinstance(anchor, dict)
            ],
            "nearest_existing": [
                {
                    "id": str(item.get("id") or ""),
                    "kind": str(item.get("kind") or ""),
                    "similarity_reason": str(item.get("similarity_reason") or ""),
                }
                for item in list(candidate.get("nearest_existing") or [])
                if isinstance(item, dict)
            ],
            "why_not_existing": str(candidate.get("why_not_existing") or ""),
            "missing_edges": candidate.get("missing_edges") if isinstance(candidate.get("missing_edges"), dict) else {},
            "next_command": str(candidate.get("next_command") or row["drilldown_command"]),
            "nearest_standard": {
                "ref": "codex/standards/principles/std_concept.json + codex/standards/principles/std_mechanism.json",
                "why": "Candidate rows route governed concept/mechanism curation; they are not doctrine authority.",
            },
            "nearest_skill": {
                "ref": "codex/doctrine/skills/doctrine/concept_mechanism_curation.md",
                "why": "The curation skill owns decisions to author, refresh, merge, or add edges after this report names pressure.",
            },
            "omission_receipt": {
                "omitted": [
                    "full source artifact bodies",
                    "semantic embedding scores",
                    "final doctrine row content",
                    "transitive evidence neighborhoods",
                ],
                "reason": "The candidate card routes coverage pressure; curation must reopen anchors before authoring doctrine.",
                "drilldown": row["evidence_command"],
            },
        }
    )
    return row


def build_concept_mechanism_candidates_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="concept_mechanism_candidates",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "unsupported_band_for_kind",
                "message": "Concept/mechanism candidates support flag and card bands.",
                "supported_bands": ["flag", "card"],
            }
        )
        return payload

    warnings: list[dict[str, Any]] = []
    report_path = repo_root / CONCEPT_MECHANISM_CANDIDATES
    report = _load_json(report_path) if report_path.exists() else {}
    if not isinstance(report.get("candidates"), list):
        from system.lib.concept_mechanism_coverage import build_concept_mechanism_candidate_report

        report = build_concept_mechanism_candidate_report(repo_root, generated_at=generated_at)
        warnings.append(
            {
                "kind": "missing_or_invalid_report",
                "message": "Generated report was missing or invalid; emitted a live fallback. Run the builder to persist it.",
                "command": "./repo-python tools/meta/factory/build_concept_mechanism_candidates.py --report",
            }
        )
    candidates = [item for item in report.get("candidates", []) if isinstance(item, dict)]
    by_id = {str(item.get("candidate_id") or ""): item for item in candidates}
    if ids:
        rows_source = [by_id[item] for item in ids if item in by_id]
        missing_ids = [item for item in ids if item not in by_id]
    else:
        rows_source = candidates
        missing_ids = []

    rows = [_candidate_card_row(row) for row in rows_source] if band == "card" else [_candidate_flag_row(row) for row in rows_source]
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "concept_mechanism_candidates",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "coverage_metabolism_routing_surface_not_doctrine_authority",
        "governing_standard": {
            "ref": "codex/standards/principles/std_concept.json + codex/standards/principles/std_mechanism.json",
            "schema_version": "concept_mechanism_candidate_report_v0",
            "owned_bands": ["flag", "card"],
        },
        "source_refs": list(report.get("source_refs") or []),
        "summary": {
            **(report.get("summary") if isinstance(report.get("summary"), dict) else {}),
            "row_count": len(rows),
            "total_available": len(candidates),
            "selection_method": "coverage_metabolism_report",
            "query_used": False,
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "source_authority_remains_input_artifacts": True,
            "candidate_rows_are_not_doctrine_rows": True,
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python tools/meta/factory/build_concept_mechanism_candidates.py --report",
                "reason": "Refresh the candidate report from current substrate pressure.",
            },
            {
                "command": "./repo-python kernel.py --option-surface concept_mechanism_candidates --band card --ids <candidate_id>",
                "reason": "Drill a candidate to anchors, nearest existing rows, missing edges, and curation route.",
            },
        ],
        "warnings": warnings,
    }


def _load_concept_mechanism_candidate_report(repo_root: Path, *, generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    report_path = repo_root / CONCEPT_MECHANISM_CANDIDATES
    report = _load_json(report_path) if report_path.exists() else {}
    if not isinstance(report.get("candidates"), list) or not isinstance(report.get("resolved_candidates"), list):
        from system.lib.concept_mechanism_coverage import build_concept_mechanism_candidate_report

        report = build_concept_mechanism_candidate_report(repo_root, generated_at=generated_at)
        warnings.append(
            {
                "kind": "missing_or_stale_report",
                "message": "Generated candidate report lacked receipt fields; emitted a live fallback. Run the builder to persist it.",
                "command": "./repo-python tools/meta/factory/build_concept_mechanism_candidates.py --report",
            }
        )
    return report, warnings


def _curation_effect(packet: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(packet.get("candidate_id") or "")
    action_taken = str(packet.get("action_taken") or "")
    open_ids = {
        str(item.get("candidate_id") or "")
        for item in list(report.get("candidates") or [])
        if isinstance(item, dict)
    }
    resolved_by_id = {
        str(item.get("candidate_id") or ""): item
        for item in list(report.get("resolved_candidates") or [])
        if isinstance(item, dict)
    }
    if candidate_id in resolved_by_id:
        effect = str(resolved_by_id[candidate_id].get("candidate_report_effect") or "resolved_suppressed")
    elif candidate_id in open_ids:
        effect = "stale_packet" if action_taken in {"author_new", "add_edges", "merge_duplicate", "covered_by_existing", "reject"} else "still_open"
    else:
        effect = "missing_candidate_history"
    return {
        "one_of": effect,
        "candidate_report_ref": str(CONCEPT_MECHANISM_CANDIDATES),
        "candidate_present_in_open_rows": candidate_id in open_ids,
        "candidate_present_in_resolved_rows": candidate_id in resolved_by_id,
        "refresh_command": "./repo-python tools/meta/factory/build_concept_mechanism_candidates.py --report",
    }


def _curation_flag_row(packet: dict[str, Any], *, report: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(packet.get("candidate_id") or "")
    effect = _curation_effect(packet, report)
    decision_reason = _truncate_words(str(packet.get("decision_reason") or ""), max_chars=260)
    action_taken = str(packet.get("action_taken") or "")
    label = f"{candidate_id} -> {action_taken or 'unknown'}"
    claim = decision_reason or label
    return {
        "row_id": f"concept_mechanism_candidate_curation:{candidate_id}::flag",
        "artifact_kind": "concept_mechanism_candidate_curation",
        "band": "flag",
        "candidate_id": candidate_id,
        "action_taken": action_taken,
        "title": candidate_id,
        "label": label,
        "claim": claim,
        "decision_reason": decision_reason,
        "files_changed_count": len(packet.get("files_changed") or []),
        "candidate_report_effect": effect,
        "source_ref": str(CONCEPT_MECHANISM_CANDIDATE_CURATION),
        "drilldown_command": (
            f"./repo-python kernel.py --option-surface concept_mechanism_candidate_curations --band card --ids {candidate_id}"
        ),
        "evidence_command": (
            f"jq --arg id '{candidate_id}' '.packets[] | select(.candidate_id==$id)' {CONCEPT_MECHANISM_CANDIDATE_CURATION}"
        ),
    }


def _curation_card_row(packet: dict[str, Any], *, report: dict[str, Any]) -> dict[str, Any]:
    row = _curation_flag_row(packet, report=report)
    candidate_id = row["candidate_id"]
    resolved_by_id = {
        str(item.get("candidate_id") or ""): item
        for item in list(report.get("resolved_candidates") or [])
        if isinstance(item, dict)
    }
    row.update(
        {
            "row_id": f"concept_mechanism_candidate_curation:{candidate_id}::card",
            "band": "card",
            "evidence_reopened": [
                {"kind": str(item.get("kind") or ""), "ref": str(item.get("ref") or "")}
                for item in list(packet.get("evidence_reopened") or [])
                if isinstance(item, dict)
            ],
            "nearest_existing_reviewed": [str(item) for item in list(packet.get("nearest_existing_reviewed") or [])],
            "decision_reason": str(packet.get("decision_reason") or ""),
            "files_changed": [str(item) for item in list(packet.get("files_changed") or [])],
            "followup_command": str(packet.get("followup_command") or ""),
            "resolved_candidate_report_row": resolved_by_id.get(candidate_id),
            "nearest_standard": {
                "ref": "codex/standards/principles/std_concept.json + codex/standards/principles/std_mechanism.json",
                "why": "Candidate curation receipts explain decisions against concept/mechanism standards without becoming doctrine rows.",
            },
            "nearest_skill": {
                "ref": "codex/doctrine/skills/doctrine/concept_mechanism_curation.md",
                "why": "The curation skill owns the packet lifecycle and proof loop for candidate resolutions.",
            },
            "omission_receipt": {
                "omitted": [
                    "full reopened evidence bodies",
                    "full source diff",
                    "unselected candidate report rows",
                    "transitive concept/mechanism neighborhoods",
                ],
                "reason": "The receipt card audits a completed candidate decision; source authority remains in the packet, report, and changed files.",
                "drilldown": row["evidence_command"],
            },
        }
    )
    return row


def build_concept_mechanism_candidate_curations_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="concept_mechanism_candidate_curations",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "unsupported_band_for_kind",
                "message": "Concept/mechanism candidate curations support flag and card bands.",
                "supported_bands": ["flag", "card"],
            }
        )
        return payload

    curation_path = repo_root / CONCEPT_MECHANISM_CANDIDATE_CURATION
    curation = _load_json(curation_path) if curation_path.exists() else {}
    packets = [item for item in list(curation.get("packets") or []) if isinstance(item, dict)]
    report, warnings = _load_concept_mechanism_candidate_report(repo_root, generated_at=generated_at)
    by_id = {str(item.get("candidate_id") or ""): item for item in packets}
    if ids:
        rows_source = [by_id[item] for item in ids if item in by_id]
        missing_ids = [item for item in ids if item not in by_id]
    else:
        rows_source = packets
        missing_ids = []

    rows = (
        [_curation_card_row(row, report=report) for row in rows_source]
        if band == "card"
        else [_curation_flag_row(row, report=report) for row in rows_source]
    )
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "concept_mechanism_candidate_curations",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "curation_receipt_surface_not_doctrine_authority",
        "governing_standard": {
            "ref": "codex/standards/principles/std_concept.json + codex/standards/principles/std_mechanism.json",
            "schema_version": "concept_mechanism_candidate_curation_v0",
            "owned_bands": ["flag", "card"],
        },
        "source_refs": [str(CONCEPT_MECHANISM_CANDIDATE_CURATION), str(CONCEPT_MECHANISM_CANDIDATES)],
        "summary": {
            "row_count": len(rows),
            "total_available": len(packets),
            "resolved_candidate_count": len(report.get("resolved_candidates") or []),
            "selection_method": "curation_packet_receipts",
            "query_used": False,
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "source_authority_remains_packet_and_changed_files": True,
            "curation_receipts_are_not_doctrine_rows": True,
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface concept_mechanism_candidate_curations --band card --ids <candidate_id>",
                "reason": "Drill a completed curation receipt to decision reason, reopened evidence, changed files, and report effect.",
            },
            {
                "command": "./repo-python tools/meta/factory/build_concept_mechanism_candidates.py --report",
                "reason": "Refresh resolved_candidates[] and candidate_report_effect after any packet or substrate change.",
            },
        ],
        "warnings": warnings,
    }


def _principle_type(principle: dict[str, Any]) -> str:
    raw = str(principle.get("kind") or "").strip().lower()
    return raw if raw in PRINCIPLE_TYPE_ORDER else "untyped"


def _principle_sort_key(principle: dict[str, Any]) -> tuple[int, str]:
    return (PRINCIPLE_TYPE_ORDER[_principle_type(principle)], str(principle.get("id") or ""))


def _principle_scope_id(principle: dict[str, Any]) -> str | None:
    scope_profile = principle.get("scope_profile")
    if isinstance(scope_profile, dict) and scope_profile.get("scope_id"):
        return str(scope_profile["scope_id"])
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _load_teleology_nodes(repo_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    path = repo_root / TELEOLOGY_NODES
    if not path.exists():
        return {}, {}, [
            {
                "kind": "missing_projection_input",
                "message": "The shared teleology/desire registry is missing.",
                "refs": [str(TELEOLOGY_NODES), str(TELEOLOGY_NODE_STANDARD)],
            }
        ]
    try:
        payload = _load_json(path)
    except json.JSONDecodeError:
        return {}, {}, [
            {
                "kind": "malformed_projection_input",
                "message": "The shared teleology/desire registry is not valid JSON.",
                "refs": [str(TELEOLOGY_NODES)],
            }
        ]
    nodes = payload.get("teleology_nodes")
    if nodes is None:
        nodes = payload.get("desire_nodes")
    by_id: dict[str, dict[str, Any]] = {}
    if isinstance(nodes, dict):
        iterator = nodes.values()
    elif isinstance(nodes, list):
        iterator = nodes
    else:
        iterator = []
    for node in iterator:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        if node_id:
            by_id[node_id] = node
    return payload, by_id, []


def _teleology_refs(row: dict[str, Any]) -> list[str]:
    return _string_list(row.get("teleology_refs"))


def _resolved_teleology_nodes(
    row: dict[str, Any],
    teleology_nodes_by_id: dict[str, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    nodes = teleology_nodes_by_id or {}
    return [nodes[ref] for ref in _teleology_refs(row) if ref in nodes]


def _legacy_teleology_projection(
    row: dict[str, Any],
    teleology_nodes_by_id: dict[str, dict[str, Any]] | None,
) -> dict[str, Any] | None:
    profile = row.get("teleology")
    if isinstance(profile, dict) and profile.get("schema_version") == DOCTRINE_TELEOLOGY_SCHEMA_VERSION:
        return dict(profile)
    nodes = _resolved_teleology_nodes(row, teleology_nodes_by_id)
    if not nodes:
        return None
    first = nodes[0]
    return {
        "schema_version": DOCTRINE_TELEOLOGY_SCHEMA_VERSION,
        "legacy_projection_from": str(TELEOLOGY_NODES),
        "teleology_node_id": str(first.get("id") or ""),
        "teleology_refs": [str(node.get("id") or "") for node in nodes],
        "title": str(first.get("title") or ""),
        "desire_statement": str(first.get("desire_statement") or ""),
        "end_state": str(first.get("end_state") or ""),
        "agent_experience": str(first.get("agent_experience") or ""),
        "operator_experience": str(first.get("operator_experience") or ""),
        "deliverables": [dict(item) for item in first.get("deliverables") or [] if isinstance(item, dict)],
        "success_signals": _string_list(first.get("success_signals")),
        "non_goals": _string_list(first.get("non_goals")),
        "evidence_refs": list(first.get("evidence_refs") or []),
        "owner_standard": str(TELEOLOGY_NODE_STANDARD),
    }


def _teleology_profile_status(
    row: dict[str, Any],
    teleology_nodes_by_id: dict[str, dict[str, Any]] | None = None,
) -> str:
    profile = row.get("teleology")
    if isinstance(profile, dict) and profile.get("schema_version") == DOCTRINE_TELEOLOGY_SCHEMA_VERSION:
        return "authored"
    if isinstance(profile, dict):
        return "malformed"
    refs = _teleology_refs(row)
    if refs:
        missing = [ref for ref in refs if ref not in (teleology_nodes_by_id or {})]
        return "missing_shared_node" if missing else "shared_ref"
    return "missing"


def _teleology_glance(profile: dict[str, Any] | None) -> str:
    if not profile:
        return ""
    return _first_sentence(
        str(profile.get("desire_statement") or profile.get("end_state") or profile.get("agent_experience") or ""),
        max_chars=220,
    )


def _teleology_population_summary(
    rows: list[dict[str, Any]],
    *,
    teleology_nodes_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    statuses = {
        status: [str(row.get("id") or "") for row in rows if _teleology_profile_status(row, teleology_nodes_by_id) == status]
        for status in ("authored", "shared_ref", "missing_shared_node", "malformed", "missing")
    }
    refs = sorted({ref for row in rows for ref in _teleology_refs(row)})
    return {
        "schema_version": DOCTRINE_TELEOLOGY_SCHEMA_VERSION,
        "shared_registry_schema_version": DOCTRINE_TELEOLOGY_NODE_REGISTRY_SCHEMA_VERSION,
        "teleology_node_count": len(teleology_nodes_by_id or {}),
        "teleology_ref_count": len(refs),
        "teleology_refs": refs,
        "authored_profile_count": len(statuses["authored"]),
        "shared_ref_count": len(statuses["shared_ref"]),
        "missing_shared_node_count": len(statuses["missing_shared_node"]),
        "missing_profile_or_ref_count": len(statuses["missing"]),
        "malformed_profile_count": len(statuses["malformed"]),
        "authored_profile_ids": statuses["authored"],
        "shared_ref_ids": statuses["shared_ref"],
        "missing_shared_node_ids": statuses["missing_shared_node"],
        "missing_profile_or_ref_ids": statuses["missing"],
        "malformed_profile_ids": statuses["malformed"],
    }


def _anti_profile(row: dict[str, Any], key: str) -> dict[str, Any] | None:
    profile = row.get(key)
    return dict(profile) if isinstance(profile, dict) else None


def _principle_flag_row(
    principle: dict[str, Any],
    *,
    teleology_nodes_by_id: dict[str, dict[str, Any]] | None = None,
    incoming_concept_edges_by_principle: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    principle_id = str(principle.get("id") or "")
    principle_type = _principle_type(principle)
    teleology = _legacy_teleology_projection(principle, teleology_nodes_by_id)
    anti = _anti_profile(principle, "anti_principle")
    incoming_concept_edges = [
        dict(edge)
        for edge in (incoming_concept_edges_by_principle or {}).get(principle_id, [])
        if isinstance(edge, Mapping)
    ]
    return {
        "row_id": f"principle:{principle_id}::flag",
        "artifact_kind": "principle",
        "band": "flag",
        "principle_id": principle_id,
        "slug": str(principle.get("slug") or principle_id),
        "title": str(principle.get("title") or principle_id),
        "type": principle_type,
        "status": str(principle.get("status") or "unknown"),
        "scope": str(principle.get("scope") or "unknown"),
        "scope_id": _principle_scope_id(principle),
        "claim": _first_sentence(str(principle.get("statement") or ""), max_chars=280),
        "one_sentence_description": _first_sentence(str(principle.get("statement") or ""), max_chars=280),
        "teleology_refs": _teleology_refs(principle),
        "teleology_role": str(principle.get("teleology_role") or ""),
        "teleology_profile_status": _teleology_profile_status(principle, teleology_nodes_by_id),
        "teleology_glance": _teleology_glance(teleology),
        "anti_principle_id": str((anti or {}).get("id") or ""),
        "anti_principle_title": str((anti or {}).get("title") or ""),
        "incoming_concept_edge_count": len(incoming_concept_edges),
        "top_incoming_concept_edges": incoming_concept_edges[:4],
        "top_concept_targets": [{"target": str(edge.get("concept_id") or ""), "incoming_concept_edges": 1} for edge in incoming_concept_edges[:3]],
        "top_mechanism_targets": [{"target": target, "incoming_concept_edges": count} for target, count in Counter(str(target) for edge in incoming_concept_edges for target in list(edge.get("mechanism_targets") or []) if str(target or "").strip()).most_common(3)],
        "drilldown_command": f"./repo-python kernel.py --option-surface principles --band card --ids {principle_id}",
        "source_ref": str(RAW_SEED_PRINCIPLES),
        "standard_ref": str(RAW_SEED_PRINCIPLES_STANDARD),
        "evidence_command": "./repo-python kernel.py --docs-route raw_seed_principles",
    }


def _principle_card_row(
    principle: dict[str, Any],
    *,
    teleology_nodes_by_id: dict[str, dict[str, Any]] | None = None,
    incoming_concept_edges_by_principle: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    row = _principle_flag_row(
        principle,
        teleology_nodes_by_id=teleology_nodes_by_id,
        incoming_concept_edges_by_principle=incoming_concept_edges_by_principle,
    )
    evidence = principle.get("evidence") if isinstance(principle.get("evidence"), list) else []
    tests = principle.get("tests") if isinstance(principle.get("tests"), list) else []
    edges = principle.get("edges") if isinstance(principle.get("edges"), list) else []
    failure_modes = principle.get("failure_modes") if isinstance(principle.get("failure_modes"), list) else []
    teleology = _legacy_teleology_projection(principle, teleology_nodes_by_id)
    teleology_nodes = _resolved_teleology_nodes(principle, teleology_nodes_by_id)
    row.update(
        {
            "row_id": f"principle:{row['principle_id']}::card",
            "band": "card",
            "statement": str(principle.get("statement") or ""),
            "teleology": teleology,
            "teleology_nodes": [
                {
                    "id": str(node.get("id") or ""),
                    "title": str(node.get("title") or ""),
                    "desire_statement": str(node.get("desire_statement") or ""),
                    "end_state": str(node.get("end_state") or ""),
                }
                for node in teleology_nodes
            ],
            "anti_principle": _anti_profile(principle, "anti_principle"),
            "teleology_population_debt": None
            if _teleology_profile_status(principle, teleology_nodes_by_id) in {"authored", "shared_ref"}
            else {
                "kind": "missing_shared_teleology_ref",
                "shared_standard": str(TELEOLOGY_NODE_STANDARD),
                "signal": "Principle row lacks a valid teleology_refs link; this is population debt, not a hard legacy-row failure.",
            },
            "epistemic_posture": principle.get("epistemic_posture"),
            "top_tests": [
                {
                    "check": _truncate_words(str(item.get("check") or ""), max_chars=260),
                    "violation": _truncate_words(str(item.get("violation") or ""), max_chars=220),
                }
                for item in tests[:3]
                if isinstance(item, dict)
            ],
            "edge_summary": [
                {
                    "target": str(item.get("target") or ""),
                    "relation": str(item.get("relation") or ""),
                    "gloss": _truncate_words(str(item.get("gloss") or item.get("forward_gloss") or ""), max_chars=240),
                }
                for item in edges[:8]
                if isinstance(item, dict)
            ],
            "evidence_refs": [
                {
                    "ref": str(item.get("ref") or ""),
                    "role": str(item.get("role") or ""),
                    "gloss": _truncate_words(str(item.get("gloss") or ""), max_chars=260),
                }
                for item in evidence[:5]
                if isinstance(item, dict)
            ],
            "top_failure_modes": [_truncate_words(str(item), max_chars=220) for item in failure_modes[:5]],
            "nearest_standard": {
                "ref": str(RAW_SEED_PRINCIPLES_STANDARD),
                "why": "The raw-seed principles standard owns the identity, statement, operating-card, edge, and evidence bands.",
            },
            "nearest_skill": {
                "ref": "codex/doctrine/skills/doctrine/principles_curation.md",
                "why": "Principles curation governs when a compact row can be refined, activated, retired, or connected to evidence.",
            },
            "omission_receipt": {
                "omitted": [
                    "full note",
                    "full decision examples",
                    "full reference_groups",
                    "raw-seed paragraph bodies",
                ],
                "reason": "The principle card supports selection and first application; curation or promotion work must reopen the source authority.",
                "drilldown": "./repo-python kernel.py --docs-route raw_seed_principles",
            },
        }
    )
    return row


def _principle_type_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("type") or "untyped"), []).append(row)
    groups: list[dict[str, Any]] = []
    for principle_type in sorted(grouped, key=lambda item: PRINCIPLE_TYPE_ORDER.get(item, 99)):
        group_rows = grouped[principle_type]
        groups.append(
            {
                "type": principle_type,
                "count": len(group_rows),
                "principle_ids": [str(row["principle_id"]) for row in group_rows],
                "rows": [
                    {
                        "principle_id": row["principle_id"],
                        "title": row["title"],
                        "status": row["status"],
                        "one_sentence_description": row["one_sentence_description"],
                    }
                    for row in group_rows
                ],
            }
        )
    return groups


def _principle_cluster_rows(flag_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in flag_rows:
        grouped.setdefault(str(row.get("type") or "untyped"), []).append(row)

    rows: list[dict[str, Any]] = []
    for principle_type in sorted(grouped, key=lambda item: PRINCIPLE_TYPE_ORDER.get(item, 99)):
        group_rows = grouped[principle_type]
        top_ids = [str(row["principle_id"]) for row in group_rows[:8] if row.get("principle_id")]
        ids = ",".join(top_ids)
        status_counts = Counter(str(row.get("status") or "unknown") for row in group_rows)
        scope_counts = Counter(str(row.get("scope") or "unknown") for row in group_rows)
        incoming_edge_count = sum(int(row.get("incoming_concept_edge_count") or 0) for row in group_rows)
        top_incoming_edges = [
            dict(edge)
            for row in group_rows
            for edge in list(row.get("top_incoming_concept_edges") or [])
            if isinstance(edge, Mapping)
        ][:8]
        label = f"{principle_type.title()} principles" if principle_type != "untyped" else "Untyped principles"
        rows.append(
            {
                "row_id": f"principle_type_cluster:{principle_type}::cluster_flag",
                "artifact_kind": "principle_type_cluster",
                "band": "cluster_flag",
                "cluster_id": principle_type,
                "type": principle_type,
                "label": label,
                "count": len(group_rows),
                "top_ids": top_ids,
                "status_counts": dict(sorted(status_counts.items())),
                "scope_counts": dict(sorted(scope_counts.items())),
                "incoming_concept_edge_count": incoming_edge_count,
                "principles_with_incoming_concept_edges": sum(
                    1 for row in group_rows if int(row.get("incoming_concept_edge_count") or 0) > 0
                ),
                "top_incoming_concept_edges": top_incoming_edges,
                "top_concept_targets": [{"target": target, "incoming_concept_edges": count} for target, count in Counter(str(edge.get("concept_id") or "") for edge in top_incoming_edges if str(edge.get("concept_id") or "").strip()).most_common(3)],
                "top_mechanism_targets": [{"target": target, "incoming_concept_edges": count} for target, count in Counter(str(item.get("target") or "") for row in group_rows for item in list(row.get("top_mechanism_targets") or []) if isinstance(item, Mapping) and str(item.get("target") or "").strip()).most_common(3)],
                "claim": f"{label}: {len(group_rows)} rows",
                "drilldown_command": (
                    f"./repo-python kernel.py --option-surface principles --band flag --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface principles --band flag --ids <pri_id>"
                ),
                "card_drilldown_command": (
                    f"./repo-python kernel.py --option-surface principles --band card --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface principles --band card --ids <pri_id>"
                ),
                "omission_receipt": {
                    "omitted": [
                        "row-level principle statements outside top_ids",
                        "operating cards",
                        "edge and evidence neighborhoods",
                        "raw-seed paragraph bodies",
                    ],
                    "reason": "cluster_flag is the principle type contents page; row flags, cards, and tape bands require explicit principle ids.",
                    "drilldown": (
                        f"./repo-python kernel.py --option-surface principles --band flag --ids {ids}"
                        if ids
                        else "./repo-python kernel.py --option-surface principles --band flag --ids <pri_id>"
                    ),
                },
            }
        )
    return rows


def _substitute_route_template(template: str, *, row_id: str) -> str:
    t = str(template or "")
    return t.replace("<pri_id>", row_id).replace("<id>", row_id).replace("<axiom_candidate_id>", row_id)


def _principle_layer_registry(standard: dict[str, Any]) -> list[dict[str, Any]]:
    nav = standard.get("navigation_contract") if isinstance(standard.get("navigation_contract"), dict) else {}
    reg = nav.get("compression_layer_registry") if isinstance(nav.get("compression_layer_registry"), dict) else {}
    layers = reg.get("layers")
    if isinstance(layers, list) and layers:
        return [dict(layer) for layer in layers if isinstance(layer, dict)]
    return [dict(layer) for layer in DEFAULT_PRINCIPLE_LAYERS]


def _axiom_layer_registry(standard: dict[str, Any]) -> list[dict[str, Any]]:
    routing = standard.get("compression_layer_routing") if isinstance(standard.get("compression_layer_routing"), dict) else {}
    layers = routing.get("layers")
    if isinstance(layers, list) and layers:
        return [dict(layer) for layer in layers if isinstance(layer, dict)]
    return [dict(layer) for layer in DEFAULT_AXIOM_LAYERS]


def _l2_operating_shape(principle: dict[str, Any]) -> str:
    tests = principle.get("tests") if isinstance(principle.get("tests"), list) else []
    failure_modes = principle.get("failure_modes") if isinstance(principle.get("failure_modes"), list) else []
    decision_examples = principle.get("decision_examples") if isinstance(principle.get("decision_examples"), list) else []
    has_tests = any(isinstance(t, dict) and str(t.get("check") or "").strip() for t in tests)
    has_fail = any(str(f).strip() for f in failure_modes if f is not None)
    has_de = any(str(d).strip() for d in decision_examples if d is not None) if decision_examples else False
    if has_tests or has_fail:
        return "full"
    if has_de:
        return "thin"
    return "empty"


def _principle_tape_excerpt(principle: dict[str, Any], band_id: str) -> str:
    pid = str(principle.get("id") or "")
    ptype = _principle_type(principle)
    if band_id == "identity":
        return _truncate_words(f"{pid} · {principle.get('slug') or ''} · {principle.get('title') or ''} · {ptype}", max_chars=200)
    if band_id == "statement":
        return _truncate_words(str(principle.get("statement") or ""), max_chars=300)
    if band_id == "operating_card":
        tests = principle.get("tests") if isinstance(principle.get("tests"), list) else []
        failure_modes = principle.get("failure_modes") if isinstance(principle.get("failure_modes"), list) else []
        parts: list[str] = []
        for item in tests[:2]:
            if isinstance(item, dict) and str(item.get("check") or "").strip():
                parts.append(f"T:{_truncate_words(str(item.get('check') or ''), max_chars=180)}")
        for item in failure_modes[:2]:
            if str(item or "").strip():
                parts.append(f"F:{_truncate_words(str(item), max_chars=120)}")
        if not parts:
            de = principle.get("decision_examples") if isinstance(principle.get("decision_examples"), list) else []
            for item in de[:1]:
                if str(item or "").strip():
                    parts.append(f"DE:{_truncate_words(str(item), max_chars=220)}")
        return _truncate_words(" | ".join(parts), max_chars=1100)
    if band_id == "edge_context":
        edges = principle.get("edges") if isinstance(principle.get("edges"), list) else []
        parts = []
        for item in edges[:5]:
            if not isinstance(item, dict):
                continue
            target = str(item.get("target") or "")
            rel = str(item.get("relation") or "")
            g = str(item.get("gloss") or item.get("forward_gloss") or "")
            if target or rel or g:
                parts.append(f"{target}—{rel}:{_truncate_words(g, max_chars=100)}")
        return _truncate_words(" · ".join(parts), max_chars=1800)
    if band_id == "evidence":
        evidence = principle.get("evidence") if isinstance(principle.get("evidence"), list) else []
        ref_groups = principle.get("reference_groups") if isinstance(principle.get("reference_groups"), list) else []
        parts = []
        for item in evidence[:4]:
            if isinstance(item, dict) and (item.get("ref") or item.get("gloss")):
                parts.append(
                    f"{str(item.get('ref') or '')}:{_truncate_words(str(item.get('gloss') or ''), max_chars=140)}"
                )
        if ref_groups and not parts:
            parts.append(f"reference_groups×{len(ref_groups)}")
        return _truncate_words(" | ".join(parts), max_chars=3600)
    return ""


def _principle_tape_row(
    principle: dict[str, Any],
    *,
    layers: list[dict[str, Any]],
    teleology_nodes_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    principle_id = str(principle.get("id") or "")
    slug = str(principle.get("slug") or "")
    title = str(principle.get("title") or "")
    statement = str(principle.get("statement") or "").strip()
    evidence = principle.get("evidence") if isinstance(principle.get("evidence"), list) else []
    ref_groups = principle.get("reference_groups") if isinstance(principle.get("reference_groups"), list) else []
    edges = principle.get("edges") if isinstance(principle.get("edges"), list) else []
    teleology_status = _teleology_profile_status(principle, teleology_nodes_by_id)
    teleology = _legacy_teleology_projection(principle, teleology_nodes_by_id)
    l2 = _l2_operating_shape(principle)

    layer_rows: list[dict[str, Any]] = []
    debt: list[dict[str, Any]] = []
    for meta in layers:
        band_id = str(meta.get("band_id") or "")
        rung = str(meta.get("rung") or "")
        budget = _compression_char_budget(meta) or 4000
        template = str(meta.get("default_route_template") or "")
        route = _substitute_route_template(template, row_id=principle_id)
        excerpt = _principle_tape_excerpt(principle, band_id)
        char_est = len(excerpt) if excerpt else 0
        populated = False
        quality = "empty"
        if band_id == "identity":
            populated = bool(principle_id and slug.strip() and title.strip())
        elif band_id == "statement":
            populated = bool(statement)
        elif band_id == "operating_card":
            if l2 == "full":
                populated, quality = True, "full"
            elif l2 == "thin":
                populated, quality = True, "thin"
            else:
                populated, quality = False, "empty"
        elif band_id == "edge_context":
            populated = any(isinstance(e, dict) and (e.get("target") or e.get("relation")) for e in edges)
        elif band_id == "evidence":
            populated = bool(
                (any(isinstance(x, dict) and str(x.get("ref") or "").strip() for x in evidence)) or ref_groups
            )

        over_budget = char_est > budget if budget else False
        if band_id == "operating_card" and quality == "thin":
            debt.append(
                {
                    "band_id": band_id,
                    "rung": rung,
                    "population_deliverable_id": meta.get("population_deliverable_id") or "principle_layer_L2",
                    "signal": str(meta.get("unpopulated_signal") or "Operating card is thin: decision_examples only"),
                }
            )
        elif not populated:
            debt.append(
                {
                    "band_id": band_id,
                    "rung": rung,
                    "population_deliverable_id": meta.get("population_deliverable_id"),
                    "signal": str(meta.get("unpopulated_signal") or f"{band_id} layer is empty or missing"),
                }
            )
        elif over_budget:
            debt.append(
                {
                    "band_id": band_id,
                    "rung": rung,
                    "signal": f"excerpt {char_est} chars exceeds soft budget {budget} (use route to expand)",
                }
            )
        entry: dict[str, Any] = {
            "band_id": band_id,
            "rung": rung,
            "order": meta.get("order"),
            "label": meta.get("label") or band_id,
            "one_line_job": meta.get("one_line_job") or "",
            "char_budget_soft": budget,
            "default_route_template": template,
            "route": route,
            "populated": populated,
            "layer_quality": quality if band_id == "operating_card" else ("full" if populated else "empty"),
            "char_estimate": char_est,
            "over_budget": over_budget,
            "excerpt": excerpt,
        }
        if meta.get("population_deliverable_id"):
            entry["population_deliverable_id"] = meta.get("population_deliverable_id")
        layer_rows.append(entry)

    return {
        "row_id": f"principle:{principle_id}::tape",
        "artifact_kind": "principle",
        "band": "tape",
        "principle_id": principle_id,
        "slug": slug,
        "title": title,
        "status": str(principle.get("status") or "unknown"),
        "type": _principle_type(principle),
        "compression_layer_rungs": "L0–L4",
        "compression_layers": layer_rows,
        "teleology_refs": _teleology_refs(principle),
        "teleology_profile_status": teleology_status,
        "teleology": teleology,
        "anti_principle": _anti_profile(principle, "anti_principle"),
        "layer_debt": debt,
        "source_ref": str(RAW_SEED_PRINCIPLES),
        "standard_ref": str(RAW_SEED_PRINCIPLES_STANDARD),
        "drilldown_command": f"./repo-python kernel.py --option-surface principles --band card --ids {principle_id}",
        "evidence_command": "./repo-python kernel.py --docs-route raw_seed_principles",
    }


def _axiom_bands_object(axiom: dict[str, Any]) -> dict[str, str]:
    raw = axiom.get("compression_expansion_bands")
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v or "") for k, v in raw.items()}


def _candidate_to_runtime_packet(axiom: dict[str, Any]) -> dict[str, Any]:
    """Surface std_system_axiom_candidate.json::promotion_contract.candidate_to_runtime_packet.

    Type A operating packets MAY surface candidate clauses when the row is marked
    candidate and drilldown refs are present. Eligibility is row-level; whether to
    actually surface in a given task belongs to the entry/context-pack assembler,
    not this option-surface row.
    """
    ax_id = str(axiom.get("id") or "")
    bands = _axiom_bands_object(axiom)
    formal_clause = str(axiom.get("formal_clause") or "").strip()
    flag_band = str(bands.get("flag") or "").strip()
    card_band = str(bands.get("card") or "").strip()
    has_activation = isinstance(axiom.get("activation_packet_behavior"), dict) and bool(axiom.get("activation_packet_behavior"))
    has_dep_neighborhood = isinstance(axiom.get("dependency_neighborhood_evidence"), dict) and bool(axiom.get("dependency_neighborhood_evidence"))
    has_runtime_band = bool(flag_band) or bool(card_band)
    has_drilldown_ref = has_activation or has_dep_neighborhood or has_runtime_band
    eligible = bool(formal_clause) and has_drilldown_ref
    blockers: list[str] = []
    if not formal_clause:
        blockers.append("missing_formal_clause")
    if not has_drilldown_ref:
        blockers.append("missing_drilldown_refs")
    return {
        "eligible": eligible,
        "authority_posture": str(axiom.get("authority_posture") or "candidate_not_active_doctrine"),
        "use_mode": "provisional_candidate_pressure_not_settled_law",
        "clause": formal_clause,
        "flag_band": flag_band,
        "why_surfaceable": "std_system_axiom_candidate.json::promotion_contract.candidate_to_runtime_packet",
        "non_law_warning": "Candidate axiom; not active doctrine. Surfaceable in Type A operating packets as provisional pressure for failure-explanatory tasks.",
        "promotion_route": "docs/raw_seed_principles_curation.md + tools/meta/factory/raw_seed_apply_loop.py hand-mint-principle (operator/controller governed; do not hand-mint pri_* from this axiom alone)",
        "drilldown": f"./repo-python kernel.py --option-surface axiom_candidates --band tape --ids {ax_id}",
        "eligibility_reasons": [
            label for label, present in (
                ("activation_packet_behavior", has_activation),
                ("dependency_neighborhood_evidence", has_dep_neighborhood),
                ("flag_band", bool(flag_band)),
                ("card_band", bool(card_band)),
            ) if present
        ],
        "eligibility_blockers": blockers,
    }


def candidate_to_runtime_packet(axiom: Mapping[str, Any]) -> dict[str, Any]:
    """Public wrapper for std_system_axiom_candidate runtime-pressure projection."""
    return _candidate_to_runtime_packet(dict(axiom))


_RUNTIME_PRESSURE_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "be", "as", "at", "by", "with", "this", "that", "these", "those", "it",
    "its", "from", "into", "across", "any", "all", "must", "should", "not",
    "do", "does", "did", "can", "will", "would", "could", "may", "might",
    "we", "our", "your", "you", "i", "me", "my", "they", "them", "their",
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "but", "if", "then", "else", "than", "so", "because", "about", "via",
    "have", "has", "had", "been", "being", "was", "were",
    "while", "during", "after", "before", "use", "using", "used", "edit",
    "edits", "editing", "fix", "fixes", "fixing", "make", "makes", "making",
    "continue", "continues", "continuing", "work", "works", "working",
    "task", "tasks", "thing", "things", "stuff", "now", "today", "yesterday",
    "tomorrow", "current", "currently", "still", "yet", "ever", "never",
    "also", "only", "just", "really", "very", "kind", "sort",
})


# Generic axiom-canonical tokens — appear in nearly every axiom-related text and
# therefore add no signal to workitem_evidence_overlap unless paired with a
# concrete doctrinal token. Used to require >= 1 non-generic overlap below.
_RUNTIME_PRESSURE_GENERIC_DOMAIN_TOKENS = frozenset({
    "axiom", "axioms", "candidate", "candidates", "doctrine", "principle",
    "principles", "system", "agent", "agents", "operator", "evidence",
    "surface", "surfaces", "projection", "projections", "feedback",
    "policy", "rule", "rules",
})


# High-signal operator-voice phrases that name the action-autonomy / permission-
# gating complaint class. Presence of any of these in the task query elevates
# matching autonomy-relevant axiom candidates out of the first-contact
# query-only-token-overlap suppression filter, so the runtime entry packet
# actually surfaces the rule instead of silently dropping it as noise.
# Source pressure: std_agent_entry_surface.json::common_sense_helpfulness_floor::action_over_pointless_inaction
# plus the 2026-05-07 operator correction naming the failure mode.
_RUNTIME_PRESSURE_AUTONOMY_PHRASES: tuple[str, ...] = (
    "permission gate",
    "permission gates",
    "permission-gated",
    "permission-gating",
    "permission ceremony",
    "approval gate",
    "approval gating",
    "approval fatigue",
    "authorize next",
    "authorize the next",
    "your call",
    "redirect or proceed",
    "micro slice",
    "micro slices",
    "micro-slice",
    "micro-slices",
    "micro-sliced",
    "micro-slicing",
    "largest coherent",
    "coherent wave",
    "coherent verified wave",
    "safe wave",
    "autonomous seed",
    "seed should work",
    "work for anything",
    "twiddling thumbs",
    "twiddle thumbs",
    "action autonomy",
    "agent autonomy",
)

# Axiom-candidate slugs whose runtime pressure is genuinely about action
# autonomy / largest-coherent-wave / common-sense execution. Restricting the
# elevation to this whitelist prevents autonomy-language queries from lifting
# unrelated axiom candidates whose token-overlap happens to clear the
# threshold for incidental reasons.
_RUNTIME_PRESSURE_AUTONOMY_AXIOM_SLUGS = frozenset({
    "common-sense-up-propagates",
    "high-class-type-b-as-prefrontal-cortex-type-a-as-rest-of-brain",
    "evolution-proves-in-microcosm",
    "actionability-drives-alerting",
    "availability-before-invention",
    "integration-not-greenfield-substrate-growth",
})


def _runtime_pressure_tokens(text: str) -> frozenset[str]:
    if not text:
        return frozenset()
    raw = re.findall(r"[a-z][a-z_]+", text.lower()) if isinstance(text, str) else []
    return frozenset(t for t in raw if len(t) >= 4 and t not in _RUNTIME_PRESSURE_STOPWORDS)


def candidate_runtime_pressure_rows(
    repo_root: Path,
    query: str,
    *,
    evidence_texts: list[str] | None = None,
    max_rows: int = 3,
    overlap_threshold: int = 2,
) -> list[dict[str, Any]]:
    """Return axiom-candidate runtime-pressure rows that match the task query.

    Implements the consumer side of:
      - std_system_axiom_candidate.json::promotion_contract.candidate_to_runtime_packet
      - std_system_axiom_candidate.json::curation_cadence_contract::runtime_pressure_rule
      - std_agent_entry_surface.json::candidate_runtime_pressure_contract

    Eligibility mirrors the standard's consumer_eligibility (non-empty formal_clause AND
    at least one of activation_packet_behavior, dependency_neighborhood_evidence,
    flag band, or card band).

    Matching is layered, in priority order (lower number = higher priority):
      0. explicit_candidate_id  — query/evidence contains literal axiom id substring
      1. explicit_candidate_slug — query/evidence contains literal slug substring (>=4)
      2. workitem_evidence_overlap — token overlap (>= threshold) against evidence_texts
      3. deterministic_token_overlap — token overlap (>= threshold) against query

    `evidence_texts` is intended for selected-WorkItem context (title, statement snippet,
    notes, source_refs, dependencies) and any other already-loaded packet context that
    cites a candidate by id/slug or by failure-explanatory token overlap. Surfaced rows
    remain marked `candidate_not_active_doctrine`; they do NOT promote and they do NOT
    bind.
    """
    query_str = str(query or "")
    has_query = bool(query_str.strip())
    has_evidence = bool(evidence_texts)
    if not has_query and not has_evidence:
        return []
    ledger_path = repo_root / RAW_SEED_AXIOM_CANDIDATES
    if not ledger_path.exists():
        return []
    try:
        data = _load_json(ledger_path)
    except json.JSONDecodeError:
        return []
    candidates = data.get("axiom_candidates") if isinstance(data.get("axiom_candidates"), list) else []
    query_lower = query_str.lower()
    evidence_blob = " ".join(str(t) for t in (evidence_texts or []) if t)
    evidence_lower = evidence_blob.lower()
    q_tokens = _runtime_pressure_tokens(query_str)
    e_tokens = _runtime_pressure_tokens(evidence_blob) if evidence_blob else frozenset()
    autonomy_phrase_matches = [
        phrase
        for phrase in _RUNTIME_PRESSURE_AUTONOMY_PHRASES
        if phrase in query_lower
    ]
    scored: list[tuple[int, int, str, dict[str, Any]]] = []
    for axiom in candidates:
        if not isinstance(axiom, dict):
            continue
        packet = _candidate_to_runtime_packet(axiom)
        if not packet.get("eligible"):
            continue
        ax_id = str(axiom.get("id") or "").strip()
        ax_id_lower = ax_id.lower()
        slug = str(axiom.get("slug") or "").strip()
        slug_lower = slug.lower()
        bands = _axiom_bands_object(axiom)
        activation = axiom.get("activation_packet_behavior") if isinstance(axiom.get("activation_packet_behavior"), dict) else {}
        match_text = " ".join((
            str(axiom.get("title") or ""),
            slug,
            str(axiom.get("formal_clause") or ""),
            str(bands.get("flag") or ""),
            str(bands.get("card") or ""),
            str(activation.get("surface_when") or ""),
            str(activation.get("packet_clause") or ""),
        ))
        a_tokens = _runtime_pressure_tokens(match_text)
        priority: int | None = None
        surface_reason = ""
        match_overlap: list[str] = []
        if ax_id_lower and len(ax_id_lower) >= 6 and (ax_id_lower in query_lower or ax_id_lower in evidence_lower):
            priority = 0
            surface_reason = "explicit_candidate_id"
            match_overlap = [ax_id]
        elif slug_lower and len(slug_lower) >= 4 and (slug_lower in query_lower or slug_lower in evidence_lower):
            priority = 1
            surface_reason = "explicit_candidate_slug"
            match_overlap = [slug]
        elif e_tokens:
            ev_overlap = e_tokens & a_tokens
            ev_specific = ev_overlap - _RUNTIME_PRESSURE_GENERIC_DOMAIN_TOKENS
            if len(ev_overlap) >= overlap_threshold and len(ev_specific) >= 1:
                priority = 2
                surface_reason = "workitem_evidence_overlap"
                match_overlap = sorted(ev_overlap)[:6]
        if priority is None and q_tokens:
            q_overlap = q_tokens & a_tokens
            if len(q_overlap) >= overlap_threshold:
                priority = 3
                surface_reason = "deterministic_token_overlap"
                match_overlap = sorted(q_overlap)[:6]
        # Elevate query-only matches when the operator's task contains a high-signal
        # action-autonomy / permission-gating phrase AND the candidate is one of the
        # whitelisted autonomy-relevant axioms. This routes the existing standard
        # (std_agent_entry_surface.json::common_sense_helpfulness_floor) into runtime
        # entry packets so the rule can actually pressure agent behavior, instead of
        # being filtered out as generic-token noise. Promotion stays bounded: only
        # whitelisted axiom slugs and named phrases qualify; the surface_reason is
        # distinct and recorded in EVIDENCE_SURFACE_REASONS so downstream filters
        # treat the row as evidence-bearing rather than query-only.
        if (
            priority == 3
            and surface_reason == "deterministic_token_overlap"
            and slug_lower in _RUNTIME_PRESSURE_AUTONOMY_AXIOM_SLUGS
            and autonomy_phrase_matches
        ):
            priority = 2
            surface_reason = "operator_autonomy_pressure_phrase"
            # Surface the matched phrases plus the original token overlap so
            # debug consumers see exactly why the row was elevated.
            match_overlap = (autonomy_phrase_matches[:3] + sorted(q_overlap))[:6]
        if (
            priority is None
            and slug_lower == "availability-before-invention"
            and autonomy_phrase_matches
            and any(
                phrase in autonomy_phrase_matches
                for phrase in ("autonomous seed", "seed should work", "work for anything")
            )
        ):
            priority = 2
            surface_reason = "operator_autonomy_pressure_phrase"
            match_overlap = autonomy_phrase_matches[:3]
        if priority is None:
            continue
        scored.append((
            priority,
            -len(match_overlap),
            ax_id,
            {
                "candidate_id": ax_id,
                "title": str(axiom.get("title") or ""),
                "slug": slug,
                "authority_posture": packet["authority_posture"],
                "use_mode": packet["use_mode"],
                "clause": packet["clause"],
                "flag_band": packet["flag_band"],
                "why_surfaceable": packet["why_surfaceable"],
                "non_law_warning": packet["non_law_warning"],
                "drilldown": packet["drilldown"],
                "surface_reason": surface_reason,
                "match_overlap": match_overlap,
                "match_overlap_size": len(match_overlap),
            },
        ))
    scored.sort(key=lambda t: (t[0], t[1], t[2]))
    return [row for _, _, _, row in scored[:max_rows]]


def _axiom_tape_row(
    axiom: dict[str, Any],
    *,
    layers: list[dict[str, Any]],
    teleology_nodes_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ax_id = str(axiom.get("id") or "")
    bands = _axiom_bands_object(axiom)
    teleology_status = _teleology_profile_status(axiom, teleology_nodes_by_id)
    teleology = _legacy_teleology_projection(axiom, teleology_nodes_by_id)
    layer_rows: list[dict[str, Any]] = []
    debt: list[dict[str, Any]] = []
    if teleology_status not in {"authored", "shared_ref"}:
        debt.append(
            {
                "band_id": "teleology",
                "rung": "profile",
                "population_deliverable_id": "axiom_profile_teleology_refs",
                "signal": f"Missing shared teleology ref; profile status is {teleology_status}.",
            }
        )
    band_keys = ("tiny", "flag", "card", "context", "deep")
    for meta in layers:
        band_id = str(meta.get("band_id") or "")
        if band_id not in band_keys:
            continue
        rung = str(meta.get("rung") or "")
        budget = int(meta.get("token_budget_chars_soft") or 0) or 200
        text = str(bands.get(band_id) or "").strip()
        char_est = len(text)
        populated = bool(text)
        template = str(meta.get("default_route_template") or "")
        route = _substitute_route_template(template, row_id=ax_id)
        over_budget = char_est > budget if budget else False
        if not populated and band_id in ("deep",):
            debt.append(
                {
                    "band_id": band_id,
                    "rung": rung,
                    "population_deliverable_id": meta.get("population_deliverable_id") or "axiom_layer_A4",
                    "signal": str(meta.get("unpopulated_signal") or "empty band (candidate debt)"),
                }
            )
        elif not populated:
            debt.append(
                {
                    "band_id": band_id,
                    "rung": rung,
                    "signal": f"{band_id} band text is empty (candidate scaffold debt)",
                }
            )
        elif over_budget:
            debt.append(
                {
                    "band_id": band_id,
                    "rung": rung,
                    "signal": f"text {char_est} chars exceeds soft budget {budget}",
                }
            )
        layer_rows.append(
            {
                "band_id": band_id,
                "rung": rung,
                "order": meta.get("order"),
                "label": meta.get("label") or band_id,
                "one_line_job": meta.get("one_line_job") or "",
                "token_budget_chars_soft": budget,
                "default_route_template": template,
                "route": route,
                "populated": populated,
                "char_estimate": char_est,
                "over_budget": over_budget,
                "excerpt": _truncate_words(text, max_chars=budget) if text else "",
            }
        )
    return {
        "row_id": f"axiom_candidate:{ax_id}::tape",
        "artifact_kind": "axiom_candidate",
        "band": "tape",
        "axiom_candidate_id": ax_id,
        "slug": str(axiom.get("slug") or ax_id),
        "title": str(axiom.get("title") or ax_id),
        "status": str(axiom.get("status") or "candidate"),
        "authority_posture": str(axiom.get("authority_posture") or "candidate_not_active_doctrine"),
        "compression_layer_rungs": "A0–A4",
        "compression_expansion_bands": bands,
        "teleological_deliverables": axiom.get("teleological_deliverables") if isinstance(axiom.get("teleological_deliverables"), list) else [],
        "teleology_refs": _teleology_refs(axiom),
        "teleology_profile_status": teleology_status,
        "teleology_profile_source": "shared_teleology_node" if teleology_status == "shared_ref" else teleology_status,
        "teleology": teleology,
        "anti_axiom": _anti_profile(axiom, "anti_axiom"),
        "compression_layers": layer_rows,
        "layer_debt": debt,
        "candidate_to_runtime_packet": _candidate_to_runtime_packet(axiom),
        "activation_packet_behavior": axiom.get("activation_packet_behavior") if isinstance(axiom.get("activation_packet_behavior"), dict) else None,
        "violation_predicates": axiom.get("violation_predicates") if isinstance(axiom.get("violation_predicates"), list) else None,
        "source_ref": str(RAW_SEED_AXIOM_CANDIDATES),
        "standard_ref": str(STD_AXIOM_CANDIDATE),
        "drilldown_command": f"./repo-python kernel.py --option-surface axiom_candidates --band card --ids {ax_id}",
    }


def _axiom_flag_row(
    axiom: dict[str, Any],
    *,
    teleology_nodes_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ax_id = str(axiom.get("id") or "")
    bands = _axiom_bands_object(axiom)
    teleology_status = _teleology_profile_status(axiom, teleology_nodes_by_id)
    teleology = _legacy_teleology_projection(axiom, teleology_nodes_by_id)
    anti = _anti_profile(axiom, "anti_axiom")
    return {
        "row_id": f"axiom_candidate:{ax_id}::flag",
        "artifact_kind": "axiom_candidate",
        "band": "flag",
        "axiom_candidate_id": ax_id,
        "slug": str(axiom.get("slug") or ax_id),
        "title": str(axiom.get("title") or ax_id),
        "claim": str(axiom.get("formal_clause") or ""),
        "formal_clause": str(axiom.get("formal_clause") or ""),
        "one_sentence": _first_sentence(str(axiom.get("dense_clause") or axiom.get("formal_clause") or ""), max_chars=300),
        "status": str(axiom.get("status") or "unknown"),
        "candidate_posture": str(axiom.get("authority_posture") or "candidate_not_active_doctrine"),
        "teleology_refs": _teleology_refs(axiom),
        "teleology_role": str(axiom.get("teleology_role") or ""),
        "teleology_profile_status": teleology_status,
        "teleology_profile_source": "shared_teleology_node" if teleology_status == "shared_ref" else teleology_status,
        "teleology_glance": _teleology_glance(teleology),
        "anti_axiom_id": str((anti or {}).get("id") or ""),
        "anti_axiom_title": str((anti or {}).get("title") or ""),
        "tiny_excerpt": _truncate_words(bands.get("tiny") or axiom.get("formal_clause") or "", max_chars=80),
        "drilldown_command": f"./repo-python kernel.py --option-surface axiom_candidates --band card --ids {ax_id}",
        "tape_command": f"./repo-python kernel.py --option-surface axiom_candidates --band tape --ids {ax_id}",
        "source_ref": str(RAW_SEED_AXIOM_CANDIDATES),
        "standard_ref": str(STD_AXIOM_CANDIDATE),
    }


def _axiom_card_row(
    axiom: dict[str, Any],
    *,
    teleology_nodes_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    base = _axiom_flag_row(axiom, teleology_nodes_by_id=teleology_nodes_by_id)
    ax_id = base["axiom_candidate_id"]
    bands = _axiom_bands_object(axiom)
    evidence = axiom.get("evidence_refs") if isinstance(axiom.get("evidence_refs"), list) else []
    rel_pri = axiom.get("related_principles") if isinstance(axiom.get("related_principles"), list) else []
    teleology = _legacy_teleology_projection(axiom, teleology_nodes_by_id)
    teleology_nodes = _resolved_teleology_nodes(axiom, teleology_nodes_by_id)
    return {
        **base,
        "row_id": f"axiom_candidate:{ax_id}::card",
        "band": "card",
        "dense_clause": str(axiom.get("dense_clause") or ""),
        "compression_bands": {k: _truncate_words(bands.get(k) or "", max_chars=900) for k in ("tiny", "flag", "card", "context", "deep")},
        "teleological_deliverables": axiom.get("teleological_deliverables") if isinstance(axiom.get("teleological_deliverables"), list) else [],
        "teleology": teleology,
        "teleology_nodes": [
            {
                "id": str(node.get("id") or ""),
                "title": str(node.get("title") or ""),
                "desire_statement": str(node.get("desire_statement") or ""),
                "end_state": str(node.get("end_state") or ""),
            }
            for node in teleology_nodes
        ],
        "anti_axiom": _anti_profile(axiom, "anti_axiom"),
        "top_evidence_refs": [
            {
                "ref": str(item.get("ref") or ""),
                "role": str(item.get("role") or ""),
                "gloss": _truncate_words(str(item.get("gloss") or ""), max_chars=200),
            }
            for item in evidence[:5]
            if isinstance(item, dict)
        ],
        "related_principles": [str(p) for p in rel_pri[:12]],
        "candidate_to_runtime_packet": _candidate_to_runtime_packet(axiom),
        "omission_receipt": {
            "omitted": [
                "full russian_doll_exemplar_chain",
                "full dependency_neighborhood_evidence",
                "violation_predicates (full set)",
                "activation_packet_behavior full body (drilldown to tape band)",
            ],
            "reason": "The card band is for selecting the candidate row; the tape band lists per-layer budget, debt, and the full activation_packet_behavior + violation_predicates body.",
            "drilldown": f"./repo-python kernel.py --option-surface axiom_candidates --band tape --ids {ax_id}",
        },
    }


def _doctrine_link_rows(repo_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    principles_payload = _load_json(repo_root / RAW_SEED_PRINCIPLES) if (repo_root / RAW_SEED_PRINCIPLES).exists() else {}
    axioms_payload = _load_json(repo_root / RAW_SEED_AXIOM_CANDIDATES) if (repo_root / RAW_SEED_AXIOM_CANDIDATES).exists() else {}
    principles = [row for row in principles_payload.get("principles") or [] if isinstance(row, dict)]
    axioms = [row for row in axioms_payload.get("axiom_candidates") or [] if isinstance(row, dict)]
    return principles, axioms


def _teleology_backlinks(
    principles: list[dict[str, Any]],
    axioms: list[dict[str, Any]],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    backlinks: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for node_ref in sorted({ref for row in principles + axioms for ref in _teleology_refs(row)}):
        backlinks[node_ref] = {
            "principles": [],
            "anti_principles": [],
            "axiom_candidates": [],
            "anti_axioms": [],
        }
    for principle in principles:
        anti = _anti_profile(principle, "anti_principle")
        for ref in _teleology_refs(principle):
            bucket = backlinks.setdefault(
                ref,
                {"principles": [], "anti_principles": [], "axiom_candidates": [], "anti_axioms": []},
            )
            bucket["principles"].append(principle)
            if anti:
                bucket["anti_principles"].append({"parent": principle, "anti": anti})
    for axiom in axioms:
        anti = _anti_profile(axiom, "anti_axiom")
        for ref in _teleology_refs(axiom):
            bucket = backlinks.setdefault(
                ref,
                {"principles": [], "anti_principles": [], "axiom_candidates": [], "anti_axioms": []},
            )
            bucket["axiom_candidates"].append(axiom)
            if anti:
                bucket["anti_axioms"].append({"parent": axiom, "anti": anti})
    return backlinks


def _teleology_flag_row(
    node: dict[str, Any],
    *,
    backlinks: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    node_id = str(node.get("id") or "")
    linked = backlinks.get(node_id, {})
    principle_ids = [str(row.get("id") or "") for row in linked.get("principles", [])]
    axiom_ids = [str(row.get("id") or "") for row in linked.get("axiom_candidates", [])]
    return {
        "row_id": f"teleology:{node_id}::flag",
        "artifact_kind": "teleology_node",
        "band": "flag",
        "teleology_id": node_id,
        "desire_id": node_id,
        "title": str(node.get("title") or node_id),
        "claim": _first_sentence(str(node.get("desire_statement") or node.get("end_state") or ""), max_chars=280),
        "desire_statement": str(node.get("desire_statement") or ""),
        "end_state_glance": _first_sentence(str(node.get("end_state") or ""), max_chars=240),
        "linked_principle_count": len(principle_ids),
        "linked_anti_principle_count": len(linked.get("anti_principles", [])),
        "linked_axiom_candidate_count": len(axiom_ids),
        "linked_anti_axiom_count": len(linked.get("anti_axioms", [])),
        "principle_ids": principle_ids,
        "axiom_candidate_ids": axiom_ids,
        "drilldown_command": f"./repo-python kernel.py --option-surface teleologies --band card --ids {node_id}",
        "principles_command": f"./repo-python kernel.py --option-surface principles_by_teleology --band flag --ids {node_id}",
        "axioms_command": f"./repo-python kernel.py --option-surface axioms_by_teleology --band flag --ids {node_id}",
        "source_ref": str(TELEOLOGY_NODES),
        "standard_ref": str(TELEOLOGY_NODE_STANDARD),
    }


def _teleology_cluster_row(
    node: dict[str, Any],
    *,
    backlinks: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    row = _teleology_flag_row(node, backlinks=backlinks)
    node_id = row["teleology_id"]
    row.update(
        {
            "row_id": f"teleology:{node_id}::cluster_flag",
            "artifact_kind": "teleology_node_cluster",
            "band": "cluster_flag",
            "claim": (
                f"{row['title']}: "
                f"{row['linked_principle_count']} principles, "
                f"{row['linked_axiom_candidate_count']} axiom candidates"
            ),
            "top_principle_ids": row["principle_ids"][:8],
            "top_axiom_candidate_ids": row["axiom_candidate_ids"][:8],
            "drilldown_command": f"./repo-python kernel.py --option-surface teleologies --band flag --ids {node_id}",
            "card_drilldown_command": f"./repo-python kernel.py --option-surface teleologies --band card --ids {node_id}",
            "omission_receipt": {
                "omitted": [
                    "full desire-node card fields",
                    "row-level principle and axiom details",
                    "anti-profile bodies",
                ],
                "reason": "cluster_flag is the desire-node contents page; open flag or card rows before traversing positive/anti doctrine rows.",
                "drilldown": f"./repo-python kernel.py --option-surface teleologies --band flag --ids {node_id}",
            },
        }
    )
    return row


def _teleology_card_row(
    node: dict[str, Any],
    *,
    backlinks: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    row = _teleology_flag_row(node, backlinks=backlinks)
    node_id = row["teleology_id"]
    linked = backlinks.get(node_id, {})
    row.update(
        {
            "row_id": f"teleology:{node_id}::card",
            "band": "card",
            "end_state": str(node.get("end_state") or ""),
            "agent_experience": str(node.get("agent_experience") or ""),
            "operator_experience": str(node.get("operator_experience") or ""),
            "deliverables": [dict(item) for item in node.get("deliverables") or [] if isinstance(item, dict)],
            "success_signals": _string_list(node.get("success_signals")),
            "non_goals": _string_list(node.get("non_goals")),
            "evidence_refs": list(node.get("evidence_refs") or []),
            "linked_principles": [
                {
                    "principle_id": str(item.get("id") or ""),
                    "title": str(item.get("title") or ""),
                    "teleology_role": str(item.get("teleology_role") or ""),
                    "anti_principle_id": str((_anti_profile(item, "anti_principle") or {}).get("id") or ""),
                }
                for item in linked.get("principles", [])
            ],
            "linked_axiom_candidates": [
                {
                    "axiom_candidate_id": str(item.get("id") or ""),
                    "title": str(item.get("title") or ""),
                    "teleology_role": str(item.get("teleology_role") or ""),
                    "anti_axiom_id": str((_anti_profile(item, "anti_axiom") or {}).get("id") or ""),
                }
                for item in linked.get("axiom_candidates", [])
            ],
            "anti_principles": [dict(item["anti"]) for item in linked.get("anti_principles", []) if isinstance(item.get("anti"), dict)],
            "anti_axioms": [dict(item["anti"]) for item in linked.get("anti_axioms", []) if isinstance(item.get("anti"), dict)],
            "omission_receipt": {
                "omitted": [
                    "full principle cards",
                    "full axiom candidate tape rows",
                    "source raw-seed bodies",
                ],
                "reason": "The teleology card proves the shared desire and reverse links; positive and anti rows drill through their own option surfaces.",
                "drilldown": f"./repo-python kernel.py --option-surface principles_by_teleology --band card --ids {node_id}",
            },
        }
    )
    return row


def build_teleologies_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="teleologies",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
    registry, nodes_by_id, warnings = _load_teleology_nodes(repo_root)
    principles, axioms = _doctrine_link_rows(repo_root)
    backlinks = _teleology_backlinks(principles, axioms)
    if ids:
        rows_source = [nodes_by_id[item] for item in ids if item in nodes_by_id]
        missing_ids = [item for item in ids if item not in nodes_by_id]
    else:
        rows_source = sorted(nodes_by_id.values(), key=lambda item: str(item.get("id") or ""))
        missing_ids = []
    if band == "card":
        rows = [_teleology_card_row(node, backlinks=backlinks) for node in rows_source]
    elif band == "cluster_flag":
        rows = [_teleology_cluster_row(node, backlinks=backlinks) for node in rows_source]
    else:
        rows = [_teleology_flag_row(node, backlinks=backlinks) for node in rows_source]
    pair_count = sum(row.get("linked_anti_principle_count", 0) + row.get("linked_anti_axiom_count", 0) for row in rows)
    node_count_for_pair_comparison = len(rows) if ids else len(nodes_by_id)
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "teleologies",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported" if nodes_by_id else "profile_gap",
        "authority_posture": "shared_desire_registry_projection_not_source_authority",
        "governing_standard": {
            "ref": str(TELEOLOGY_NODE_STANDARD),
            "schema_version": _load_json(repo_root / TELEOLOGY_NODE_STANDARD).get("schema_version")
            if (repo_root / TELEOLOGY_NODE_STANDARD).exists()
            else None,
            "owned_bands": ["cluster_flag", "flag", "card"],
        },
        "source_refs": [str(TELEOLOGY_NODES), str(TELEOLOGY_NODE_STANDARD), str(RAW_SEED_PRINCIPLES), str(RAW_SEED_AXIOM_CANDIDATES)],
        "summary": {
            "row_count": len(rows),
            "total_available": len(nodes_by_id),
            "query_used": False,
            "selection_method": "artifact_kind_enumeration",
            "drilldown_by": "teleology_id",
            "cluster_first_for_shared_desires": band == "cluster_flag",
            "positive_anti_pair_count": pair_count,
            "teleologies_less_than_pairs": node_count_for_pair_comparison < pair_count if pair_count else None,
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "desire_nodes_are_shared": True,
            "anti_profiles_share_parent_teleology_refs": True,
            "cluster_first_for_high_cardinality": band == "cluster_flag",
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface teleologies --band cluster_flag",
                "reason": "Start with shared desire nodes before opening row-level doctrine crosswalks.",
            },
            {
                "command": "./repo-python kernel.py --option-surface teleologies --band flag",
                "reason": "Browse shared desires before opening principle or axiom rows.",
            },
            {
                "command": "./repo-python kernel.py --option-surface principles_by_teleology --band flag --ids <tel_id>",
                "reason": "Traverse desire -> principles -> anti-principles.",
            },
            {
                "command": "./repo-python kernel.py --option-surface axioms_by_teleology --band flag --ids <tel_id>",
                "reason": "Traverse desire -> axiom candidates -> anti-axioms.",
            },
        ],
        "warnings": warnings,
    }


def _principle_by_teleology_row(
    principle: dict[str, Any],
    *,
    band: str,
    teleology_nodes_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row = _principle_card_row(principle, teleology_nodes_by_id=teleology_nodes_by_id) if band == "card" else _principle_flag_row(principle, teleology_nodes_by_id=teleology_nodes_by_id)
    row.update(
        {
            "row_id": f"principle_by_teleology:{row['principle_id']}::{band}",
            "artifact_kind": "principle_by_teleology",
            "band": band,
            "back_to_teleologies_command": "./repo-python kernel.py --option-surface teleologies --band card --ids "
            + ",".join(_teleology_refs(principle)),
        }
    )
    return row


def _principles_by_teleology_cluster_rows(
    principles: list[dict[str, Any]],
    teleology_nodes_by_id: dict[str, dict[str, Any]],
    *,
    ids: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in principles:
        for ref in _teleology_refs(row):
            grouped.setdefault(ref, []).append(row)

    selected_refs = sorted(grouped)
    if ids:
        selected_refs = [ref for ref in selected_refs if ref in ids]
    missing_ids = [item for item in ids if item not in grouped and item not in teleology_nodes_by_id]

    rows: list[dict[str, Any]] = []
    for ref in selected_refs:
        group_rows = grouped[ref]
        top_ids = [str(row.get("id") or "") for row in group_rows[:8] if row.get("id")]
        joined_ids = ",".join(top_ids)
        anti_count = sum(1 for row in group_rows if _anti_profile(row, "anti_principle"))
        teleology_node = teleology_nodes_by_id.get(ref) or {}
        title = str(teleology_node.get("title") or ref)
        rows.append(
            {
                "row_id": f"principles_by_teleology_cluster:{ref}::cluster_flag",
                "artifact_kind": "principles_by_teleology_cluster",
                "band": "cluster_flag",
                "teleology_id": ref,
                "title": title,
                "claim": f"{title}: {len(group_rows)} linked principles",
                "linked_principle_count": len(group_rows),
                "linked_anti_principle_count": anti_count,
                "top_principle_ids": top_ids,
                "drilldown_command": f"./repo-python kernel.py --option-surface principles_by_teleology --band flag --ids {ref}",
                "card_drilldown_command": (
                    f"./repo-python kernel.py --option-surface principles_by_teleology --band card --ids {joined_ids}"
                    if joined_ids
                    else "./repo-python kernel.py --option-surface principles_by_teleology --band card --ids <pri_id>"
                ),
                "teleology_command": f"./repo-python kernel.py --option-surface teleologies --band card --ids {ref}",
                "anti_principles_command": f"./repo-python kernel.py --option-surface anti_principles --band flag --ids {ref}",
                "omission_receipt": {
                    "omitted": [
                        "row-level principle statements outside top_principle_ids",
                        "full anti-principle bodies",
                        "raw-seed paragraph bodies",
                    ],
                    "reason": "cluster_flag is the desire-group contents page; row flags and cards require explicit teleology or principle ids.",
                    "drilldown": f"./repo-python kernel.py --option-surface principles_by_teleology --band flag --ids {ref}",
                },
            }
        )
    return rows, missing_ids


def build_principles_by_teleology_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="principles_by_teleology",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
    _, nodes_by_id, warnings = _load_teleology_nodes(repo_root)
    principles, _ = _doctrine_link_rows(repo_root)
    if ids:
        rows_source = [
            row for row in principles
            if str(row.get("id") or "") in ids or any(ref in ids for ref in _teleology_refs(row))
        ]
        matched = {str(row.get("id") or "") for row in rows_source} | {ref for row in rows_source for ref in _teleology_refs(row)}
        missing_ids = [item for item in ids if item not in matched and item not in nodes_by_id]
    else:
        rows_source = [row for row in principles if _teleology_refs(row)]
        missing_ids = []
    if band == "cluster_flag":
        rows, missing_ids = _principles_by_teleology_cluster_rows(
            rows_source,
            nodes_by_id,
            ids=ids,
        )
    else:
        rows = [_principle_by_teleology_row(row, band=band, teleology_nodes_by_id=nodes_by_id) for row in rows_source]
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "principles_by_teleology",
        "band": band,
        "selection": {"mode": "ids" if ids else "all", "ids": ids, "missing_ids": missing_ids},
        "profile_status": "supported",
        "authority_posture": "teleology_crosswalk_projection_not_source_authority",
        "governing_standard": {"ref": str(TELEOLOGY_NODE_STANDARD), "owned_bands": ["cluster_flag", "flag", "card"]},
        "source_refs": [str(TELEOLOGY_NODES), str(RAW_SEED_PRINCIPLES), str(TELEOLOGY_NODE_STANDARD)],
        "summary": {
            "row_count": len(rows),
            "total_available": len([row for row in principles if _teleology_refs(row)]),
            "query_used": False,
            "selection_method": "teleology_ref_crosswalk",
            "drilldown_by": "teleology_id" if band == "cluster_flag" else "teleology_id_or_principle_id",
            "cluster_first_for_reverse_teleology": band == "cluster_flag",
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "desire_to_principle_crosswalk": True,
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface anti_principles --band flag --ids <tel_id>",
                "reason": "From a desire or principle, inspect the negative-space failure profiles.",
            }
        ],
        "warnings": warnings,
    }


def _anti_principle_surface_row(
    principle: dict[str, Any],
    *,
    teleology_nodes_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    anti = _anti_profile(principle, "anti_principle")
    if not anti:
        return None
    principle_id = str(principle.get("id") or "")
    refs = _teleology_refs(principle)
    anti_refs = _string_list(anti.get("teleology_refs"))
    return {
        "row_id": f"anti_principle:{anti.get('id') or principle_id}::flag",
        "artifact_kind": "anti_principle",
        "band": "flag",
        "anti_principle_id": str(anti.get("id") or ""),
        "parent_principle_id": principle_id,
        "parent_principle_title": str(principle.get("title") or ""),
        "title": str(anti.get("title") or ""),
        "claim": _first_sentence(str(anti.get("failure_statement") or ""), max_chars=280),
        "failure_statement": str(anti.get("failure_statement") or ""),
        "teleology_refs": refs,
        "anti_teleology_refs": anti_refs,
        "shares_parent_teleology_refs": refs == anti_refs,
        "resolved_teleology_nodes": [
            {"id": ref, "title": str((teleology_nodes_by_id.get(ref) or {}).get("title") or "")}
            for ref in refs
        ],
        "failure_modes": _string_list(anti.get("failure_modes")),
        "detection_signals": _string_list(anti.get("detection_signals")),
        "prevention": str(anti.get("prevention") or ""),
        "drilldown_command": f"./repo-python kernel.py --option-surface principles --band card --ids {principle_id}",
        "teleology_command": "./repo-python kernel.py --option-surface teleologies --band card --ids " + ",".join(refs),
    }


def build_anti_principles_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="anti_principles",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
    _, nodes_by_id, warnings = _load_teleology_nodes(repo_root)
    principles, _ = _doctrine_link_rows(repo_root)
    all_rows = [row for row in (_anti_principle_surface_row(p, teleology_nodes_by_id=nodes_by_id) for p in principles) if row]
    if ids:
        rows = [
            row for row in all_rows
            if row["anti_principle_id"] in ids
            or row["parent_principle_id"] in ids
            or any(ref in ids for ref in row["teleology_refs"])
        ]
        matched = {row["anti_principle_id"] for row in rows} | {row["parent_principle_id"] for row in rows} | {ref for row in rows for ref in row["teleology_refs"]}
        missing_ids = [item for item in ids if item not in matched]
    else:
        rows = all_rows
        missing_ids = []
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "anti_principles",
        "band": band,
        "selection": {"mode": "ids" if ids else "all", "ids": ids, "missing_ids": missing_ids},
        "profile_status": "supported",
        "authority_posture": "negative_space_projection_not_source_authority",
        "governing_standard": {"ref": str(TELEOLOGY_NODE_STANDARD), "owned_bands": ["flag", "card"]},
        "source_refs": [str(RAW_SEED_PRINCIPLES), str(TELEOLOGY_NODES), str(TELEOLOGY_NODE_STANDARD)],
        "summary": {
            "row_count": len(rows),
            "total_available": len(all_rows),
            "query_used": False,
            "selection_method": "anti_profile_crosswalk",
            "drilldown_by": "anti_principle_id_or_parent_principle_id_or_teleology_id",
            "all_rows_share_parent_teleology_refs": all(bool(row.get("shares_parent_teleology_refs")) for row in rows),
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "anti_profiles_define_no_own_teleology": True,
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface teleologies --band card --ids <tel_id>",
                "reason": "Return from the failure mode to the desired world it blocks.",
            }
        ],
        "warnings": warnings,
    }


def _anti_axiom_surface_row(
    axiom: dict[str, Any],
    *,
    band: str,
    teleology_nodes_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    anti = _anti_profile(axiom, "anti_axiom")
    if not anti:
        return None
    axiom_id = str(axiom.get("id") or "")
    refs = _teleology_refs(axiom)
    anti_refs = _string_list(anti.get("teleology_refs"))
    resolved = [
        {
            "id": ref,
            "title": str((teleology_nodes_by_id.get(ref) or {}).get("title") or ""),
        }
        for ref in refs
    ]
    row = {
        "row_id": f"anti_axiom:{anti.get('id') or axiom_id}::{band}",
        "artifact_kind": "anti_axiom",
        "band": band,
        "anti_axiom_id": str(anti.get("id") or ""),
        "parent_axiom_candidate_id": axiom_id,
        "parent_axiom_candidate_slug": str(axiom.get("slug") or ""),
        "parent_axiom_candidate_title": str(axiom.get("title") or ""),
        "title": str(anti.get("title") or ""),
        "claim": _first_sentence(str(anti.get("failure_statement") or ""), max_chars=280),
        "failure_statement": str(anti.get("failure_statement") or ""),
        "teleology_refs": refs,
        "anti_teleology_refs": anti_refs,
        "shares_parent_teleology_refs": refs == anti_refs,
        "resolved_teleology_nodes": resolved,
        "failure_modes": _string_list(anti.get("failure_modes")),
        "detection_signals": _string_list(anti.get("detection_signals")),
        "prevention": str(anti.get("prevention") or ""),
        "failure_attractor": str(anti.get("failure_attractor") or ""),
        "constitutional_risk": str(anti.get("constitutional_risk") or ""),
        "blocked_axiom_commitment": str(anti.get("blocked_axiom_commitment") or ""),
        "recovery_protocol": str(anti.get("recovery_protocol") or ""),
        "route_when_detected": str(anti.get("route_when_detected") or ""),
        "route_surfaces": _string_list(anti.get("route_surfaces")),
        "route_commands": [dict(item) for item in anti.get("route_commands") or [] if isinstance(item, dict)],
        "boundary_conditions": _string_list(anti.get("boundary_conditions")),
        "failure_evidence_refs": _string_list(anti.get("failure_evidence_refs")),
        "drilldown_command": f"./repo-python kernel.py --option-surface axiom_candidates --band card --ids {axiom_id}",
        "tape_command": f"./repo-python kernel.py --option-surface axiom_candidates --band tape --ids {axiom_id}",
        "teleology_command": "./repo-python kernel.py --option-surface teleologies --band card --ids " + ",".join(refs),
        "axioms_by_teleology_command": "./repo-python kernel.py --option-surface axioms_by_teleology --band flag --ids " + ",".join(refs),
        "source_ref": str(RAW_SEED_AXIOM_CANDIDATES),
        "standard_ref": str(STD_AXIOM_CANDIDATE),
    }
    if band == "card":
        row.update(
            {
                "parent_formal_clause": str(axiom.get("formal_clause") or ""),
                "parent_dense_clause": str(axiom.get("dense_clause") or ""),
                "parent_teleology_role": str(axiom.get("teleology_role") or ""),
                "teleology_glance": [
                    {
                        "id": str(node.get("id") or ""),
                        "title": str(node.get("title") or ""),
                        "desire_statement": _first_sentence(str(node.get("desire_statement") or ""), max_chars=260),
                        "end_state": _first_sentence(str(node.get("end_state") or ""), max_chars=260),
                    }
                    for node in _resolved_teleology_nodes(axiom, teleology_nodes_by_id)
                ],
                "navigation_receipt": {
                    "anti_profile_defines_no_own_teleology": "teleology" not in anti,
                    "same_desire_as_parent_axiom": refs == anti_refs,
                    "route_count": len([item for item in anti.get("route_commands") or [] if isinstance(item, dict)]),
                },
            }
        )
    return row


def build_anti_axioms_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="anti_axioms",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
    _, nodes_by_id, warnings = _load_teleology_nodes(repo_root)
    _, axioms = _doctrine_link_rows(repo_root)
    all_rows = [
        row
        for row in (
            _anti_axiom_surface_row(axiom, band=band, teleology_nodes_by_id=nodes_by_id)
            for axiom in axioms
        )
        if row
    ]
    if ids:
        rows = [
            row for row in all_rows
            if row["anti_axiom_id"] in ids
            or row["parent_axiom_candidate_id"] in ids
            or row["parent_axiom_candidate_slug"] in ids
            or any(ref in ids for ref in row["teleology_refs"])
        ]
        matched = (
            {row["anti_axiom_id"] for row in rows}
            | {row["parent_axiom_candidate_id"] for row in rows}
            | {row["parent_axiom_candidate_slug"] for row in rows}
            | {ref for row in rows for ref in row["teleology_refs"]}
        )
        missing_ids = [item for item in ids if item not in matched]
    else:
        rows = all_rows
        missing_ids = []
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "anti_axioms",
        "band": band,
        "selection": {"mode": "ids" if ids else "all", "ids": ids, "missing_ids": missing_ids},
        "profile_status": "supported",
        "authority_posture": "negative_space_projection_not_source_authority",
        "governing_standard": {"ref": str(TELEOLOGY_NODE_STANDARD), "owned_bands": ["flag", "card"]},
        "source_refs": [str(RAW_SEED_AXIOM_CANDIDATES), str(TELEOLOGY_NODES), str(TELEOLOGY_NODE_STANDARD)],
        "summary": {
            "row_count": len(rows),
            "total_available": len(all_rows),
            "query_used": False,
            "selection_method": "anti_axiom_crosswalk",
            "drilldown_by": "anti_axiom_id_or_parent_axiom_candidate_id_or_slug_or_teleology_id",
            "all_rows_share_parent_teleology_refs": all(bool(row.get("shares_parent_teleology_refs")) for row in rows),
            "routed_profile_count": len([row for row in rows if row.get("route_commands")]),
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "anti_profiles_define_no_own_teleology": True,
            "anti_axioms_are_not_separate_goals": True,
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface teleologies --band card --ids <tel_id>",
                "reason": "Return from the constitutional failure mode to the shared desire it blocks.",
            },
            {
                "command": "./repo-python kernel.py --option-surface axiom_candidates --band tape --ids <axiom_candidate_id>",
                "reason": "Expand the parent candidate axiom when the failure profile alone is insufficient.",
            },
        ],
        "warnings": warnings,
    }


def _axiom_by_teleology_row(
    axiom: dict[str, Any],
    *,
    band: str,
    teleology_nodes_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row = _axiom_card_row(axiom, teleology_nodes_by_id=teleology_nodes_by_id) if band == "card" else _axiom_flag_row(axiom, teleology_nodes_by_id=teleology_nodes_by_id)
    row.update(
        {
            "row_id": f"axiom_by_teleology:{row['axiom_candidate_id']}::{band}",
            "artifact_kind": "axiom_by_teleology",
            "band": band,
            "back_to_teleologies_command": "./repo-python kernel.py --option-surface teleologies --band card --ids "
            + ",".join(_teleology_refs(axiom)),
        }
    )
    return row


def _axioms_by_teleology_cluster_rows(
    axioms: list[dict[str, Any]],
    teleology_nodes_by_id: dict[str, dict[str, Any]],
    *,
    ids: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in axioms:
        for ref in _teleology_refs(row):
            grouped.setdefault(ref, []).append(row)

    selected_refs = sorted(grouped)
    if ids:
        selected_refs = [ref for ref in selected_refs if ref in ids]
    missing_ids = [item for item in ids if item not in grouped and item not in teleology_nodes_by_id]

    rows: list[dict[str, Any]] = []
    for ref in selected_refs:
        group_rows = grouped[ref]
        top_ids = [str(row.get("id") or "") for row in group_rows[:8] if row.get("id")]
        joined_ids = ",".join(top_ids)
        anti_count = sum(1 for row in group_rows if _anti_profile(row, "anti_axiom"))
        teleology_node = teleology_nodes_by_id.get(ref) or {}
        title = str(teleology_node.get("title") or ref)
        rows.append(
            {
                "row_id": f"axioms_by_teleology_cluster:{ref}::cluster_flag",
                "artifact_kind": "axioms_by_teleology_cluster",
                "band": "cluster_flag",
                "teleology_id": ref,
                "title": title,
                "claim": f"{title}: {len(group_rows)} linked axiom candidates",
                "linked_axiom_candidate_count": len(group_rows),
                "linked_anti_axiom_count": anti_count,
                "top_axiom_candidate_ids": top_ids,
                "drilldown_command": f"./repo-python kernel.py --option-surface axioms_by_teleology --band flag --ids {ref}",
                "card_drilldown_command": (
                    f"./repo-python kernel.py --option-surface axioms_by_teleology --band card --ids {joined_ids}"
                    if joined_ids
                    else "./repo-python kernel.py --option-surface axioms_by_teleology --band card --ids <axiom_candidate_id>"
                ),
                "teleology_command": f"./repo-python kernel.py --option-surface teleologies --band card --ids {ref}",
                "anti_axioms_command": f"./repo-python kernel.py --option-surface anti_axioms --band flag --ids {ref}",
                "omission_receipt": {
                    "omitted": [
                        "row-level axiom candidate statements outside top_axiom_candidate_ids",
                        "full anti-axiom bodies",
                        "raw-seed paragraph bodies",
                    ],
                    "reason": "cluster_flag is the desire-group contents page; row flags and cards require explicit teleology or axiom ids.",
                    "drilldown": f"./repo-python kernel.py --option-surface axioms_by_teleology --band flag --ids {ref}",
                },
            }
        )
    return rows, missing_ids


def build_axioms_by_teleology_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="axioms_by_teleology",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
    _, nodes_by_id, warnings = _load_teleology_nodes(repo_root)
    _, axioms = _doctrine_link_rows(repo_root)
    if ids:
        rows_source = [
            row for row in axioms
            if str(row.get("id") or "") in ids
            or str(row.get("slug") or "") in ids
            or any(ref in ids for ref in _teleology_refs(row))
        ]
        matched = {str(row.get("id") or "") for row in rows_source} | {str(row.get("slug") or "") for row in rows_source} | {ref for row in rows_source for ref in _teleology_refs(row)}
        missing_ids = [item for item in ids if item not in matched and item not in nodes_by_id]
    else:
        rows_source = [row for row in axioms if _teleology_refs(row)]
        missing_ids = []
    if band == "cluster_flag":
        rows, missing_ids = _axioms_by_teleology_cluster_rows(
            rows_source,
            nodes_by_id,
            ids=ids,
        )
    else:
        rows = [_axiom_by_teleology_row(row, band=band, teleology_nodes_by_id=nodes_by_id) for row in rows_source]
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "axioms_by_teleology",
        "band": band,
        "selection": {"mode": "ids" if ids else "all", "ids": ids, "missing_ids": missing_ids},
        "profile_status": "supported",
        "authority_posture": "teleology_crosswalk_projection_not_source_authority",
        "governing_standard": {"ref": str(TELEOLOGY_NODE_STANDARD), "owned_bands": ["cluster_flag", "flag", "card"]},
        "source_refs": [str(TELEOLOGY_NODES), str(RAW_SEED_AXIOM_CANDIDATES), str(TELEOLOGY_NODE_STANDARD)],
        "summary": {
            "row_count": len(rows),
            "total_available": len([row for row in axioms if _teleology_refs(row)]),
            "query_used": False,
            "selection_method": "teleology_ref_crosswalk",
            "drilldown_by": "teleology_id" if band == "cluster_flag" else "teleology_id_or_axiom_candidate_id",
            "cluster_first_for_reverse_teleology": band == "cluster_flag",
            "all_anti_axioms_share_parent_teleology_refs": all(
                not _anti_profile(row, "anti_axiom")
                or _string_list((_anti_profile(row, "anti_axiom") or {}).get("teleology_refs")) == _teleology_refs(row)
                for row in rows_source
            ),
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "desire_to_axiom_crosswalk": True,
            "anti_profiles_define_no_own_teleology": True,
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface teleologies --band card --ids <tel_id>",
                "reason": "Return from the candidate or anti-axiom to the desired world it serves.",
            }
        ],
        "warnings": warnings,
    }


def _load_core_authority(root: Path) -> dict[str, dict[str, Any]]:
    path = root / CORE_AUTHORITY_INDEX
    if not path.exists():
        return {}
    try:
        data = _load_json(path)
    except json.JSONDecodeError:
        return {}
    artifacts = data.get("artifacts") if isinstance(data.get("artifacts"), dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for key, value in artifacts.items():
        if not isinstance(value, dict):
            continue
        standard_ref = value.get("json_standard")
        if isinstance(standard_ref, str) and standard_ref:
            out[standard_ref] = {"artifact_key": key, **value}
    return out


def _standard_files(root: Path) -> list[Path]:
    standards_root = root / STANDARDS_ROOT
    if not standards_root.exists():
        return []
    return sorted(
        path
        for path in standards_root.rglob("std_*.json")
        if path.is_file()
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    )


def _python_standard_row(root: Path) -> dict[str, Any] | None:
    path = root / PYTHON_STANDARD
    if not path.exists():
        return None
    try:
        from codex.standards.std_python import PYTHON_STANDARD as python_standard_data
    except ImportError:
        python_standard_data = {}
    data = dict(python_standard_data) if isinstance(python_standard_data, dict) else {}
    data.setdefault("id", "std_python")
    data.setdefault("title", "Python Standard")
    data.setdefault(
        "purpose",
        "Constitution for Python comprehension, compression, routing, and provider-backed population.",
    )
    if isinstance(data.get("compression_population_constitution"), dict):
        data.setdefault(
            "summary",
            str(data["compression_population_constitution"].get("summary") or "").strip(),
        )
    return {
        "id": "std_python",
        "path": path,
        "source_ref": _relative(path, root),
        "data": data,
        "authority": {
            "artifact_key": "std_python",
            "lifecycle": "authored_python_standard",
            "authority_posture": "python_module_standard_bridge",
        },
    }


def _standard_id(path: Path, data: dict[str, Any]) -> str:
    raw = data.get("id") or data.get("slug") or path.stem
    return str(raw).strip() or path.stem


def _standard_title(path: Path, data: dict[str, Any]) -> str:
    raw = data.get("title") or data.get("name") or _standard_id(path, data).replace("_", " ").title()
    return str(raw).strip()


def _standard_group(path: Path, repo_root: Path) -> str:
    try:
        rel = path.relative_to(repo_root / STANDARDS_ROOT)
    except ValueError:
        return "unknown"
    if len(rel.parts) <= 1:
        return "core"
    return rel.parts[0]


def _standard_claim(data: dict[str, Any]) -> str:
    core_law = data.get("core_law") if isinstance(data.get("core_law"), dict) else {}
    for value in (
        core_law.get("flag"),
        data.get("summary"),
        data.get("purpose"),
        data.get("description"),
        data.get("scope"),
    ):
        if isinstance(value, str) and value.strip():
            return _first_sentence(value)
    validation = data.get("validation_rules")
    if isinstance(validation, list) and validation:
        return _first_sentence(str(validation[0]))
    flattened_validation = _standard_validation_rule_texts(data)
    if flattened_validation:
        return _first_sentence(flattened_validation[0])
    return ""


def _standard_validation_rule_texts(data: Mapping[str, Any]) -> list[str]:
    """Return validation rules from legacy list and structured rule-block standards."""
    validation = data.get("validation_rules")
    if isinstance(validation, list):
        return [str(item).strip() for item in validation if str(item).strip()]
    if not isinstance(validation, Mapping):
        return []

    preferred_keys = (
        "hard_errors",
        "errors",
        "warnings",
        "advisories",
        "checks",
    )
    ordered_keys = [key for key in preferred_keys if key in validation]
    ordered_keys.extend(str(key) for key in validation.keys() if str(key) not in set(ordered_keys))

    rules: list[str] = []
    for key in ordered_keys:
        value = validation.get(key)
        label = str(key).replace("_", " ").rstrip("s")
        if isinstance(value, str) and value.strip():
            rules.append(f"{label}: {value.strip()}")
        elif isinstance(value, list):
            rules.extend(f"{label}: {str(item).strip()}" for item in value if str(item).strip())
    return rules


def _navigation_contract_summary(data: dict[str, Any]) -> dict[str, Any] | None:
    contract = data.get("navigation_contract")
    if not isinstance(contract, dict):
        return None
    bands = contract.get("navigable_bands") if isinstance(contract.get("navigable_bands"), list) else []
    facets = contract.get("telescope_facets") if isinstance(contract.get("telescope_facets"), list) else []
    return {
        "profile_id": contract.get("profile_id"),
        "artifact_kind": contract.get("artifact_kind"),
        "navigable_bands": [str(item) for item in bands],
        "telescope_facets": [
            str(item.get("facet") or item.get("id") or item)
            if isinstance(item, Mapping)
            else str(item)
            for item in facets[:10]
            if isinstance(item, (Mapping, str))
        ],
        "source_authority": contract.get("source_authority"),
        "currentness_policy": contract.get("currentness_policy"),
        "validation_probe": contract.get("validation_probe"),
    }


def _standard_validation_probe_commands(
    data: Mapping[str, Any],
    navigation_contract: Mapping[str, Any] | None,
) -> list[str]:
    """Return source-declared validation probes in stable display order."""
    commands: list[str] = []
    for value in (data.get("validation_probe"), (navigation_contract or {}).get("validation_probe")):
        if isinstance(value, str) and value.strip():
            commands.append(value.strip())
        elif isinstance(value, list):
            commands.extend(str(item).strip() for item in value if str(item).strip())
    return list(dict.fromkeys(commands))


def _standard_compact_mechanisms(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expose small operational mechanism cards without copying the full standard."""
    mechanisms: list[dict[str, Any]] = []

    handoff = data.get("type_b_to_type_a_handoff_framing_contract")
    if isinstance(handoff, Mapping):
        shuttle = handoff.get("shuttle_trace_context_contract")
        if isinstance(shuttle, Mapping):
            floor = shuttle.get("no_edit_pass_floor")
            if isinstance(floor, Mapping):
                outputs = floor.get("valid_no_edit_outputs")
                mechanisms.append(
                    {
                        "id": "no_edit_pass_floor",
                        "purpose": str(floor.get("purpose") or ""),
                        "valid_outputs": [str(item) for item in (outputs or [])[:6]]
                        if isinstance(outputs, list)
                        else [],
                        "forbidden_closeout": str(floor.get("forbidden_closeout") or ""),
                        "resolved_blocker_acceleration_rule": str(
                            floor.get("resolved_blocker_acceleration_rule") or ""
                        ),
                    }
                )

    common_sense = data.get("common_sense_helpfulness_floor")
    if isinstance(common_sense, Mapping):
        non_null = common_sense.get("non_null_pass_yield")
        if isinstance(non_null, Mapping):
            mechanisms.append(
                {
                    "id": "non_null_pass_yield",
                    "purpose": str(non_null.get("rule") or non_null.get("test") or ""),
                    "forbidden_closeout": str(non_null.get("no_repeated_null_pass_rule") or ""),
                    "pro_forma_clearance_invalid_rule": str(
                        non_null.get("pro_forma_clearance_invalid_rule") or ""
                    ),
                    "resolved_blocker_acceleration_rule": str(
                        non_null.get("resolved_blocker_acceleration_rule") or ""
                    ),
                    "egress_detector": str(non_null.get("egress_detector") or ""),
                }
            )

    return mechanisms[:6]


_NO_EDIT_PASS_TRIGGER_TERMS = (
    "no edit",
    "no edits",
    "no-edit",
    "zero edits",
    "zero file edits",
    "no file edit",
    "no file edits",
    "no code patch",
    "no source patch",
    "verify-only",
    "verify only",
    "verification pass",
    "nothing to refine",
    "nothing_to_refine",
    "already landed",
    "already exists",
    "already true",
    "resolved blocker",
    "blocker resolved",
    "stale blocker",
    "pasted blocker",
    "no-op",
    "null pass",
    "no-null",
)


_AUTONOMOUS_SEED_NO_NULL_TERMS = (
    "autonomous seed",
    "autonomous seeds",
    "type a seed",
    "type a seeds",
    "seed pass",
    "seed passes",
    "queued seed",
    "queued seeds",
    "rotautonomous",
)


def _autonomous_seed_no_null_edit_mechanism(repo_root: Path) -> dict[str, Any] | None:
    standard_path = repo_root / TYPE_A_AUTONOMOUS_SEED_STANDARD
    try:
        data = _load_json(standard_path)
    except Exception:
        return None
    ban = data.get("autonomous_seed_no_null_edit_ban")
    if not isinstance(ban, Mapping):
        return None
    exception_policy = ban.get("exception_policy") if isinstance(ban.get("exception_policy"), Mapping) else {}
    speed_binding = ban.get("speed_refinement_binding") if isinstance(ban.get("speed_refinement_binding"), Mapping) else {}
    return {
        "id": "autonomous_seed_no_null_edit_ban",
        "purpose": str(ban.get("purpose") or ""),
        "rule": str(ban.get("rule") or ""),
        "hard_required_outputs": [
            str(item) for item in (ban.get("hard_required_outputs") or [])[:8]
        ]
        if isinstance(ban.get("hard_required_outputs"), list)
        else [],
        "forbidden_closeout": str(ban.get("forbidden_closeout") or ""),
        "typed_no_edit_receipt_is_success": False,
        "exception_valid_only_when": [
            str(item) for item in (exception_policy.get("valid_only_when") or [])[:6]
        ]
        if isinstance(exception_policy.get("valid_only_when"), list)
        else [],
        "speed_refinement_first_routes": [
            str(item) for item in (speed_binding.get("first_route_commands") or [])[:6]
        ]
        if isinstance(speed_binding.get("first_route_commands"), list)
        else [],
    }


def no_edit_pass_floor_card(repo_root: Path, query: str | None) -> dict[str, Any] | None:
    """Return the compact no-null-pass mechanism when the task shape asks for it."""
    query_text = str(query or "").lower()
    if not any(term in query_text for term in _NO_EDIT_PASS_TRIGGER_TERMS):
        return None

    standard_path = repo_root / "codex/standards/std_agent_entry_surface.json"
    try:
        data = _load_json(standard_path)
    except Exception:
        return {
            "schema": "no_edit_pass_floor_card_v0",
            "status": "unavailable",
            "reason": "std_agent_entry_surface_unreadable",
            "source_ref": "codex/standards/std_agent_entry_surface.json",
        }

    mechanisms = _standard_compact_mechanisms(data)
    selected = [
        item
        for item in mechanisms
        if str(item.get("id") or "") in {"no_edit_pass_floor", "non_null_pass_yield"}
    ]
    if any(term in query_text for term in _AUTONOMOUS_SEED_NO_NULL_TERMS):
        autonomous_seed_ban = _autonomous_seed_no_null_edit_mechanism(repo_root)
        if autonomous_seed_ban is not None:
            selected.append(autonomous_seed_ban)
    if not selected:
        return {
            "schema": "no_edit_pass_floor_card_v0",
            "status": "missing",
            "reason": "compact_mechanism_absent",
            "source_ref": "codex/standards/std_agent_entry_surface.json",
            "standards_card_command": (
                "./repo-python kernel.py --option-surface standards --band card --ids std_agent_entry_surface"
            ),
        }

    return {
        "schema": "no_edit_pass_floor_card_v0",
        "status": "available",
        "authority_boundary": "orientation_from_std_agent_entry_surface_not_completion_authority",
        "source_ref": "codex/standards/std_agent_entry_surface.json",
        "standards_card_command": (
            "./repo-python kernel.py --option-surface standards --band card --ids std_agent_entry_surface"
        ),
        "trigger_terms_matched": [
            term for term in _NO_EDIT_PASS_TRIGGER_TERMS if term in query_text
        ][:6],
        "compact_mechanisms": selected,
        "typed_no_edit_receipt_required_fields": [
            "stewardship_checked",
            "next_best_lane_checked",
            "unsafe_or_absent_lane_reason",
            "reentry_condition",
        ],
        "cheapest_sufficient_route": (
            "./repo-python kernel.py --option-surface standards --band card --ids std_agent_entry_surface"
        ),
    }


def _standard_status(data: dict[str, Any], authority: dict[str, Any] | None) -> str:
    for value in (data.get("status"), data.get("lifecycle"), (authority or {}).get("lifecycle")):
        if isinstance(value, str) and value.strip():
            return value
    return "unknown"


def _standard_index(root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    authority_by_ref = _load_core_authority(root)
    rows: list[dict[str, Any]] = []
    python_row = _python_standard_row(root)
    if python_row is not None:
        rows.append(python_row)
    for path in _standard_files(root):
        rel = _relative(path, root)
        try:
            data = _load_json(path)
        except json.JSONDecodeError:
            continue
        standard_id = _standard_id(path, data)
        rows.append(
            {
                "id": standard_id,
                "path": path,
                "source_ref": rel,
                "data": data,
                "authority": authority_by_ref.get(rel, {}),
            }
        )
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        by_id[row["id"]] = row
        by_id[Path(str(row["source_ref"])).stem] = row
    return rows, by_id


def _standard_evidence_command(row: dict[str, Any]) -> str:
    rel = str(row["source_ref"])
    if str(row.get("id") or "") == "std_python" and rel.endswith(".py"):
        return f"./repo-python kernel.py --option-surface python_files --band card --ids {rel}"
    return f"jq '.' {rel}"


def _standard_source_check_command(row: dict[str, Any]) -> str:
    rel = str(row["source_ref"])
    if rel.endswith(".py"):
        return f"./repo-python -m py_compile {rel}"
    return f"./repo-python -m json.tool {rel}"


def _standard_disclosure_posture(data: Mapping[str, Any]) -> str:
    for key in ("disclosure_posture", "disclosure_class", "public_disclosure_posture"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "controlled_private_review"


def _standard_architecture_fields(
    row: dict[str, Any],
    *,
    data: Mapping[str, Any],
    repo_root: Path,
    navigation_contract: Mapping[str, Any] | None,
    related_surfaces: Mapping[str, Any],
) -> dict[str, Any]:
    rel = str(row["source_ref"])
    standard_id = str(row["id"])
    card_command = f"./repo-python kernel.py --option-surface standards --band card --ids {standard_id}"
    system_atlas_command = (
        f"./repo-python kernel.py --option-surface system_atlas --band card --ids {standard_id}"
    )
    source_check_command = _standard_source_check_command(row)
    evidence_command = _standard_evidence_command(row)
    validation_route: list[str] = [source_check_command, card_command]
    if evidence_command not in validation_route:
        validation_route.append(evidence_command)

    for probe in reversed(_standard_validation_probe_commands(data, navigation_contract)):
        if probe not in validation_route:
            validation_route.insert(0, probe)

    governed_artifact_kinds: list[str] = []
    artifact_kind = (navigation_contract or {}).get("artifact_kind")
    if isinstance(artifact_kind, str) and artifact_kind.strip():
        governed_artifact_kinds.append(artifact_kind.strip())
    for key in ("artifact_kind", "governed_artifact_kind", "governed_artifact_kinds"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            governed_artifact_kinds.append(value.strip())
        elif isinstance(value, list):
            governed_artifact_kinds.extend(str(item).strip() for item in value if str(item).strip())
    governed_artifact_kinds = sorted(dict.fromkeys(governed_artifact_kinds))

    related_surface_refs: list[str] = []
    for key, value in related_surfaces.items():
        if isinstance(value, str) and value.strip():
            related_surface_refs.append(f"{key}: {value.strip()}")
        elif isinstance(value, list):
            for item in value[:8]:
                if isinstance(item, str) and item.strip():
                    related_surface_refs.append(f"{key}: {item.strip()}")
                elif isinstance(item, Mapping):
                    ref = item.get("ref") or item.get("path") or item.get("command") or item.get("id")
                    if isinstance(ref, str) and ref.strip():
                        related_surface_refs.append(f"{key}: {ref.strip()}")
        elif isinstance(value, Mapping):
            ref = value.get("ref") or value.get("path") or value.get("command") or value.get("id")
            if isinstance(ref, str) and ref.strip():
                related_surface_refs.append(f"{key}: {ref.strip()}")

    return {
        "owner_surface": {
            "source_authority": rel,
            "source_authority_kind": "python_standard_module" if rel.endswith(".py") else "standard_json",
            "projection_owner": "system/lib/standard_option_surface.py::_standard_card_row",
            "registry_source": str(STANDARDS_REGISTRY),
            "governing_standard": str(STANDARDS_REGISTRY_STANDARD),
        },
        "source_projection_boundary": {
            "source_authority": rel,
            "projection_surfaces": [
                "standards option-surface rows",
                "System Atlas standard/entity cards",
                "generated markdown or frontend views that cite standard rows",
            ],
            "manual_edit_boundary": "Patch the source standard or owning builder, then rerun the card route and focused checks; do not hand-edit generated projections.",
            "disclosure_decision_boundary": "Standards cards are private/control-plane projections; dissemination gates decide what is public-safe to show.",
        },
        "governed_artifact_kinds": governed_artifact_kinds,
        "graph_neighbors": {
            "depends_on": [rel, str(STANDARDS_REGISTRY), str(STANDARDS_REGISTRY_STANDARD)],
            "exposes": [card_command, evidence_command],
            "projects_to": ["standards option-surface card", system_atlas_command],
            "related_surfaces": related_surface_refs[:12],
            "governs_artifact_kinds": governed_artifact_kinds,
        },
        "validation_route": validation_route,
        "mutation_route": [
            (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                f"--path {rel} --require-exclusive"
            ),
            f"apply_patch {rel}",
            source_check_command,
            card_command,
        ],
        "workitem_cap_pressure": {
            "status": "lookup_required",
            "reason": "Live WorkItem/CAP pressure is owned by Task Ledger projections, not embedded in standard source rows.",
            "context_pack_command": (
                f"./repo-python kernel.py --context-pack \"{standard_id} standard WorkItem CAP pressure\" "
                "--context-budget 12000"
            ),
            "task_ledger_command": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
        },
        "disclosure_posture": _standard_disclosure_posture(data),
        "drilldown_commands": [card_command, evidence_command, system_atlas_command],
    }


def _standard_flag_row(row: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    data = row["data"]
    path = row["path"]
    rel = str(row["source_ref"])
    standard_id = str(row["id"])
    companion = path.with_suffix(".md")
    authority = row.get("authority") if isinstance(row.get("authority"), dict) else {}
    claim = _standard_claim(data)
    navigation_contract = _navigation_contract_summary(data)
    result = {
        "row_id": f"standard:{standard_id}::flag",
        "artifact_kind": "standard",
        "band": "flag",
        "standard_id": standard_id,
        "slug": standard_id,
        "title": _standard_title(path, data),
        "claim": claim,
        "status": _standard_status(data, authority),
        "group": _standard_group(path, repo_root),
        "teleology_intent_capsule": build_teleology_intent_capsule(
            purpose=claim or f"Govern standard {standard_id}.",
            original_intent=data.get("purpose") or data.get("summary") or data.get("description") or claim,
            served_deliverable=(
                f"Standard-owned navigation and validation for {navigation_contract.get('artifact_kind') or standard_id}."
                if navigation_contract
                else f"Standard-owned contract for {standard_id}."
            ),
            non_purpose=[
                "Projection capsule only; the source standard remains authority.",
                "Do not hand-edit generated option-surface rows.",
            ],
            evidence_refs=[rel, str(STANDARDS_REGISTRY), str(STANDARDS_REGISTRY_STANDARD)],
            freshness=f"source_mtime:{_source_mtime(path)}",
            owner_standard=str(STANDARDS_REGISTRY_STANDARD),
            source_confidence="generated_from_standard_metadata",
        ),
        "currentness": {
            "source_mtime": _source_mtime(path),
            "companion_exists": companion.exists(),
            "authority_lifecycle": authority.get("lifecycle"),
            "authority_key": authority.get("artifact_key"),
        },
        "source_ref": rel,
        "companion_ref": _relative(companion, repo_root) if companion.exists() else None,
        "drilldown_command": f"./repo-python kernel.py --option-surface standards --band card --ids {standard_id}",
        "evidence_command": _standard_evidence_command(row),
    }
    if isinstance(data.get("compression_passport"), Mapping):
        result["compression_passport"] = dict(data.get("compression_passport") or {})
    return result


def _standard_card_row(row: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    data = row["data"]
    card = _standard_flag_row(row, repo_root=repo_root)
    core_law = data.get("core_law") if isinstance(data.get("core_law"), dict) else {}
    available_shards = data.get("available_shards") if isinstance(data.get("available_shards"), list) else []
    naming_layers = data.get("naming_layers") if isinstance(data.get("naming_layers"), list) else []
    validation_rules = _standard_validation_rule_texts(data)
    related_surfaces = data.get("related_surfaces") if isinstance(data.get("related_surfaces"), dict) else {}
    navigation_contract = _navigation_contract_summary(data)
    current_projection_fields = (
        dict(data.get("current_projection_fields"))
        if isinstance(data.get("current_projection_fields"), Mapping)
        else {}
    )
    compact_mechanisms = _standard_compact_mechanisms(data)
    architecture_fields = _standard_architecture_fields(
        row,
        data=data,
        repo_root=repo_root,
        navigation_contract=navigation_contract,
        related_surfaces=related_surfaces,
    )
    card.update(
        {
            "row_id": f"standard:{card['standard_id']}::card",
            "band": "card",
            "summary_excerpt": _truncate_words(str(data.get("summary") or data.get("purpose") or data.get("description") or ""), max_chars=700),
            "core_law": {key: core_law.get(key) for key in ("word", "phrase", "flag", "card", "context") if core_law.get(key)},
            "option_shards": [
                {
                    "id": str(item.get("id") or ""),
                    "label": str(item.get("label") or item.get("id") or ""),
                    "compressed_rule": str(item.get("compressed_rule") or ""),
                    "uncompress_when": str(item.get("uncompress_when") or ""),
                }
                for item in available_shards[:12]
                if isinstance(item, dict)
            ],
            "naming_layers": [
                {
                    "id": str(item.get("id") or ""),
                    "purpose": str(item.get("purpose") or ""),
                    "repair_bias": str(item.get("repair_bias") or ""),
                }
                for item in naming_layers[:12]
                if isinstance(item, dict)
            ],
            "top_validation_rules": [str(item) for item in validation_rules[:8]],
            "validation_probe": _standard_validation_probe_commands(data, navigation_contract),
            "current_projection_fields": current_projection_fields,
            "navigation_contract": navigation_contract,
            "compact_mechanisms": compact_mechanisms,
            "related_surfaces": related_surfaces,
            "nearest_standard": {
                "ref": str(STANDARDS_REGISTRY_STANDARD),
                "why": "The standards-registry standard governs how standards advertise family, path, and navigation posture.",
            },
            "nearest_skill": {
                "ref": str(PROFILE_SKILL),
                "why": "The compression skill says to read the owning profile/standard before compressing or drilling rows.",
            },
            "evidence_commands": [
                _standard_evidence_command(row),
                "./repo-python kernel.py --standards",
            ],
            **architecture_fields,
            "omission_receipt": {
                "omitted": [
                    "full JSON standard body",
                    "full markdown companion",
                    "full cross-registry authority neighborhood",
                ],
                "reason": "The standards card band supports selecting and understanding the next standard read, not replacing standard authority.",
                "drilldown": _standard_evidence_command(row),
            },
        }
    )
    return card


def _standard_cluster_rows(rows_source: list[dict[str, Any]], *, repo_root: Path) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows_source:
        grouped.setdefault(_standard_group(row["path"], repo_root), []).append(row)

    rows: list[dict[str, Any]] = []
    for group, group_rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        group_rows = sorted(group_rows, key=lambda item: str(item.get("id") or ""))
        top_ids = [str(row["id"]) for row in group_rows[:8] if row.get("id")]
        ids = ",".join(top_ids)
        status_counts = Counter(
            _standard_status(
                row["data"],
                row.get("authority") if isinstance(row.get("authority"), dict) else {},
            )
            for row in group_rows
        )
        authority_counts = Counter(
            str((row.get("authority") or {}).get("artifact_key") or "unmapped")
            for row in group_rows
            if isinstance(row.get("authority"), dict)
        )
        label = "Core standards" if group == "core" else f"{group.replace('_', ' ').title()} standards"
        rows.append(
            {
                "row_id": f"standard_group:{group}::cluster_flag",
                "artifact_kind": "standard_group",
                "band": "cluster_flag",
                "cluster_id": group,
                "group": group,
                "label": label,
                "count": len(group_rows),
                "top_ids": top_ids,
                "sample_titles": [_standard_title(row["path"], row["data"]) for row in group_rows[:4]],
                "status_counts": dict(sorted(status_counts.items())),
                "authority_key_counts": dict(sorted(authority_counts.items())),
                "claim": f"{label}: {len(group_rows)} standards",
                "drilldown_command": (
                    f"./repo-python kernel.py --option-surface standards --band flag --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface standards --band flag --ids <standard_id>"
                ),
                "card_drilldown_command": (
                    f"./repo-python kernel.py --option-surface standards --band card --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface standards --band card --ids <standard_id>"
                ),
                "omission_receipt": {
                    "omitted": [
                        "row-level standard flags outside top_ids",
                        "full JSON standard bodies",
                        "markdown companions",
                        "cross-registry authority neighborhoods",
                    ],
                    "reason": "cluster_flag is the standards group contents page; row flags and cards require explicit standard ids.",
                    "drilldown": (
                        f"./repo-python kernel.py --option-surface standards --band flag --ids {ids}"
                        if ids
                        else "./repo-python kernel.py --option-surface standards --band flag --ids <standard_id>"
                    ),
                },
            }
        )
    return rows


def _system_term_ladder(term: dict[str, Any]) -> dict[str, str]:
    ladder = term.get("definition_ladder") if isinstance(term.get("definition_ladder"), dict) else {}
    return {band: str(ladder.get(band) or "") for band in SYSTEM_TERM_BANDS}


def _system_term_id(term: dict[str, Any]) -> str:
    return str(term.get("id") or "").strip()


def _system_term_title(term: dict[str, Any]) -> str:
    term_id = _system_term_id(term)
    return str(term.get("term") or term_id).strip()


def _system_term_currentness(
    term: dict[str, Any],
    *,
    repo_root: Path,
    registry: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "authored_registry",
        "source_ref": str(SYSTEM_TERM_REGISTRY_REL),
        "source_mtime": _source_mtime(repo_root / SYSTEM_TERM_REGISTRY_REL),
        "registry_updated_at": registry.get("updated_at"),
        "term_updated_at": term.get("updated_at"),
    }


def _system_term_evidence_command(term_id: str) -> str:
    return f"./repo-python kernel.py --term {term_id} --term-band context"


def _system_term_flag_row(
    term: dict[str, Any],
    *,
    repo_root: Path,
    registry: dict[str, Any],
) -> dict[str, Any]:
    term_id = _system_term_id(term)
    ladder = _system_term_ladder(term)
    return {
        "row_id": f"system_term:{term_id}::flag",
        "artifact_kind": "system_term",
        "band": "flag",
        "term_id": term_id,
        "slug": term_id,
        "title": _system_term_title(term),
        "claim": ladder.get("flag") or ladder.get("card") or "",
        "flag": ladder.get("flag") or ladder.get("card") or "",
        "phrase": ladder.get("phrase") or "",
        "aliases": [str(alias) for alias in list(term.get("aliases") or [])],
        "term_kind": term.get("term_kind"),
        "status": term.get("status"),
        "source_ref": str(SYSTEM_TERM_REGISTRY_REL),
        "standard_ref": str(SYSTEM_TERM_STANDARD),
        "drilldown_command": f"./repo-python kernel.py --option-surface system_terms --band card --ids {term_id}",
        "evidence_command": _system_term_evidence_command(term_id),
        "currentness": _system_term_currentness(term, repo_root=repo_root, registry=registry),
    }


def _system_term_card_row(
    term: dict[str, Any],
    *,
    repo_root: Path,
    registry: dict[str, Any],
) -> dict[str, Any]:
    row = _system_term_flag_row(term, repo_root=repo_root, registry=registry)
    term_id = row["term_id"]
    row.update(
        {
            "row_id": f"system_term:{term_id}::card",
            "band": "card",
            "definition_ladder": _system_term_ladder(term),
            "native_bands": list(SYSTEM_TERM_BANDS),
            "adapter_supported_bands": ["flag", "card"],
            "authority_posture": term.get("authority_posture"),
            "source_refs": list(term.get("source_refs") or []),
            "relationships": list(term.get("relationships") or []),
            "evidence_commands": list(term.get("evidence_commands") or []),
            "nearest_standard": {
                "ref": str(SYSTEM_TERM_STANDARD),
                "why": "The system-term standard owns the authored definition ladder, source refs, relationships, evidence commands, and currentness policy.",
            },
            "omission_receipt": {
                "omitted": [
                    "full source bodies behind source_refs",
                    "second-order relationship closure",
                    "legacy context/deep command output beyond the registry ladder",
                ],
                "reason": "The card band supports selecting and applying the term; full authority remains in the term registry and legacy term context command.",
                "drilldown": _system_term_evidence_command(term_id),
            },
        }
    )
    return row


def build_system_terms_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="system_terms",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    registry = load_system_vocabulary(repo_root)
    standard_path = repo_root / SYSTEM_TERM_STANDARD
    standard = _load_json(standard_path) if standard_path.exists() else {}
    terms = system_vocabulary_terms(repo_root)
    by_id: dict[str, dict[str, Any]] = {}
    for term in terms:
        term_id = _system_term_id(term)
        if term_id:
            by_id[term_id] = term

    if ids:
        rows_source = [by_id[item] for item in ids if item in by_id]
        missing_ids = [item for item in ids if item not in by_id]
    else:
        rows_source = sorted(terms, key=lambda item: _system_term_id(item))
        missing_ids = []

    rows = (
        [
            _system_term_card_row(term, repo_root=repo_root, registry=registry)
            for term in rows_source
        ]
        if band == "card"
        else [
            _system_term_flag_row(term, repo_root=repo_root, registry=registry)
            for term in rows_source
        ]
    )

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "system_terms",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "standard_owned_projection_not_source_authority",
        "governing_standard": {
            "ref": str(SYSTEM_TERM_STANDARD),
            "schema_version": standard.get("schema_version"),
            "owned_bands": ["flag", "card"],
            "native_ladder_bands_are_data_not_adapter_support": True,
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "source_refs": [
            str(SYSTEM_TERM_REGISTRY_REL),
            str(SYSTEM_TERM_STANDARD),
            str(NAVIGATION_THEORY),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(terms),
            "query_used": False,
            "selection_method": "artifact_kind_enumeration",
            "drilldown_by": "term_id",
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["flag", "card"],
            "native_ladder_bands": list(SYSTEM_TERM_BANDS),
            "native_ladder_bands_are_data_not_adapter_support": True,
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface system_terms --band flag",
                "reason": "Browse vocabulary rows before choosing a term or opening the registry.",
            },
            {
                "command": "./repo-python kernel.py --option-surface system_terms --band card --ids <term_id>",
                "reason": "Drill one term to its authored ladder, relationships, currentness, and evidence commands.",
            },
            {
                "command": "./repo-python kernel.py --term <term_id> --term-band context",
                "reason": "Use the legacy term reader for context/deep expansion; those bands are not option-surface adapter support.",
            },
        ],
        "warnings": [],
    }


def _frontend_view_entries(graph: dict[str, Any]) -> list[dict[str, Any]]:
    views = graph.get("views")
    if isinstance(views, list):
        return [dict(view) for view in views if isinstance(view, dict)]
    if isinstance(views, dict):
        entries: list[dict[str, Any]] = []
        for key, view in views.items():
            if not isinstance(view, dict):
                continue
            entry = dict(view)
            entry.setdefault("id", str(key))
            entries.append(entry)
        return entries
    return []


def _frontend_view_id(view: dict[str, Any]) -> str:
    return str(view.get("id") or view.get("slug") or view.get("route") or "").strip()


def _frontend_view_selector_variants(selector: str) -> list[str]:
    raw = str(selector or "").strip()
    if not raw:
        return []
    aliases: list[str] = [raw]
    lowered = raw.lower()
    aliases.append(lowered)

    compact = re.sub(r"[^a-z0-9]+", "", lowered)
    if compact:
        aliases.append(compact)

    words = [
        part
        for part in re.split(r"[^A-Za-z0-9]+", raw)
        if part
    ]
    if len(words) > 1:
        aliases.append(words[0].lower() + "".join(word[:1].upper() + word[1:] for word in words[1:]))
        aliases.append("_".join(word.lower() for word in words))
        aliases.append("-".join(word.lower() for word in words))

    deduped: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        if alias and alias not in seen:
            seen.add(alias)
            deduped.append(alias)
    return deduped


def _frontend_view_title(view: dict[str, Any]) -> str:
    view_id = _frontend_view_id(view)
    return str(view.get("label") or view.get("name") or view.get("title") or view_id).strip()


def _frontend_view_evidence(view: dict[str, Any]) -> dict[str, Any]:
    evidence = view.get("evidence")
    return dict(evidence) if isinstance(evidence, dict) else {}


def _frontend_view_capture(view: dict[str, Any]) -> dict[str, Any]:
    capture = view.get("capture")
    return dict(capture) if isinstance(capture, dict) else {}


def _frontend_view_validation_contract(view: dict[str, Any]) -> dict[str, Any]:
    validation_contract = view.get("validation_contract")
    return dict(validation_contract) if isinstance(validation_contract, dict) else {}


def _frontend_view_validation_summary(view: dict[str, Any]) -> dict[str, Any] | None:
    validation_contract = _frontend_view_validation_contract(view)
    if not validation_contract:
        return None
    browser_requirement = validation_contract.get("browser_visual_requirement")
    browser_requirement = browser_requirement if isinstance(browser_requirement, Mapping) else {}
    return {
        "schema": validation_contract.get("schema"),
        "route_class": validation_contract.get("route_class"),
        "required_lanes": list(validation_contract.get("required_lanes") or []),
        "browser_visual_requirement": {
            "status": browser_requirement.get("status"),
            "lane": browser_requirement.get("lane"),
            "capture_slug": browser_requirement.get("capture_slug"),
            "target_view_id": browser_requirement.get("target_view_id"),
            "direct_route_capture_authoritative": browser_requirement.get(
                "direct_route_capture_authoritative"
            ),
        },
        "acceptance_command_refs": list(validation_contract.get("acceptance_command_refs") or []),
    }


def _frontend_view_observation_index(repo_root: Path) -> dict[str, Any]:
    path = repo_root / FRONTEND_VIEW_OBSERVATION_INDEX
    if not path.exists():
        return {}
    try:
        payload = _load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _frontend_view_observation_rows(
    observation_index: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in (observation_index or {}).get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        view_id = str(row.get("view_id") or "").strip()
        if view_id:
            rows[view_id] = dict(row)
    return rows


def _frontend_view_observation_ref(
    view_id: str,
    observation_rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    row = observation_rows.get(view_id)
    if not row:
        return None
    return {
        "schema": "frontend_view_observation_option_surface_ref_v0",
        "index_ref": str(FRONTEND_VIEW_OBSERVATION_INDEX),
        "packet_path": row.get("packet_path"),
        "markdown_path": row.get("markdown_path"),
        "screenshot_status": row.get("screenshot_status"),
        "refresh_due": row.get("refresh_due"),
        "latest_screenshot": row.get("latest_screenshot"),
        "refresh_command": row.get("refresh_command"),
        "visual_delta_status": row.get("visual_delta_status"),
        "visual_delta_receipt_path": row.get("visual_delta_receipt_path"),
        "visual_delta_changed_percent": row.get("visual_delta_changed_percent"),
    }


def _frontend_visual_memory_discovery(view_id: str = "<view_id>") -> dict[str, Any]:
    selector = str(view_id or "<view_id>")
    return {
        "schema": "frontend_visual_memory_discovery_v0",
        "alias_terms": list(FRONTEND_VISUAL_MEMORY_ALIAS_TERMS),
        "docs_route": './repo-python kernel.py --docs-route "screenshot ledger"',
        "view_option_surface": "./repo-python kernel.py --option-surface frontend_views --band cluster_flag",
        "open_view_card": f"./repo-python kernel.py --option-surface frontend_views --band card --ids {selector}",
        "packet_index_ref": str(FRONTEND_VIEW_OBSERVATION_INDEX),
        "visual_settlement_ref": str(FRONTEND_VISUAL_SETTLEMENT),
        "owner_builder": "tools/meta/observability/view_quality_census.py",
        "capture_engine": "tools/meta/observability/station_render.py",
        "authority_boundary": "view memory packets and settlement receipts are generated projections over navigation graph, station_render receipts, and view quality census rows",
    }


def _frontend_visual_settlement_index(repo_root: Path) -> dict[str, Any]:
    path = repo_root / FRONTEND_VISUAL_SETTLEMENT
    if not path.exists():
        return {}
    try:
        payload = _load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _frontend_visual_settlement_rows(
    settlement_index: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in (settlement_index or {}).get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        view_id = str(row.get("view_id") or "").strip()
        if view_id:
            rows[view_id] = dict(row)
    return rows


def _frontend_visual_settlement_ref(
    view_id: str,
    settlement_rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    row = settlement_rows.get(view_id)
    if not row:
        return None
    latest_delta = row.get("latest_visual_delta")
    latest_delta = latest_delta if isinstance(latest_delta, Mapping) else {}
    refs = row.get("refs")
    refs = refs if isinstance(refs, Mapping) else {}
    return {
        "schema": "frontend_visual_settlement_option_surface_ref_v0",
        "settlement_index_ref": str(FRONTEND_VISUAL_SETTLEMENT),
        "settlement_status": row.get("settlement_status"),
        "requires_review": row.get("requires_review"),
        "screenshot_status": row.get("screenshot_status"),
        "screenshot_refresh_due": row.get("screenshot_refresh_due"),
        "refresh_command": row.get("refresh_command"),
        "visual_delta_status": latest_delta.get("status"),
        "visual_delta_receipt_path": latest_delta.get("receipt_path"),
        "visual_delta_changed_percent": latest_delta.get("changed_percent"),
        "packet_path": refs.get("packet_path"),
        "markdown_path": refs.get("markdown_path"),
        "open_view_card": refs.get("open_view_card"),
    }


def _frontend_view_currentness(
    view: dict[str, Any],
    *,
    repo_root: Path,
    graph: dict[str, Any],
    observation_ref: Mapping[str, Any] | None = None,
    settlement_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = _frontend_view_evidence(view)
    evidence_file = str(evidence.get("file") or "")
    evidence_path = repo_root / evidence_file if evidence_file else None
    packet_path_raw = str((observation_ref or {}).get("packet_path") or "")
    packet_path = repo_root / packet_path_raw if packet_path_raw else None
    return {
        "status": "frontend_navigation_graph_available",
        "graph_ref": str(FRONTEND_NAV_GRAPH),
        "graph_mtime": _source_mtime(repo_root / FRONTEND_NAV_GRAPH),
        "graph_generated_at": graph.get("generated_at"),
        "view_observation_index_ref": str(FRONTEND_VIEW_OBSERVATION_INDEX),
        "view_observation_index_mtime": _source_mtime(
            repo_root / FRONTEND_VIEW_OBSERVATION_INDEX
        ),
        "view_observation_packet_mtime": _source_mtime(packet_path) if packet_path else None,
        "visual_settlement_index_ref": str(FRONTEND_VISUAL_SETTLEMENT),
        "visual_settlement_index_mtime": _source_mtime(
            repo_root / FRONTEND_VISUAL_SETTLEMENT
        ),
        "visual_settlement_status": (settlement_ref or {}).get("settlement_status"),
        "source_hashes": dict(graph.get("source_hashes") or {}),
        "source_ref": evidence_file or None,
        "source_line": evidence.get("line"),
        "source_mtime": _source_mtime(evidence_path) if evidence_path else None,
    }


def _frontend_view_evidence_command(view_id: str) -> str:
    return f"./repo-python kernel.py --view {view_id}"


def _frontend_view_source_component_ref(view: dict[str, Any]) -> dict[str, Any] | None:
    evidence = _frontend_view_evidence(view)
    file_ref = str(evidence.get("file") or "")
    if not file_ref:
        return None
    return {
        "file": file_ref,
        "line": evidence.get("line"),
        "why": "Frontend navigation graph evidence for this view row.",
    }


def _frontend_view_omission_receipt(view_id: str, *, band: str) -> dict[str, Any]:
    omitted = [
        "full UI source bodies",
        "full navigation graph edge list",
        "render/capture artifact bodies and screenshots",
    ]
    if band == "flag":
        omitted.append("card-level capture timing and source-hash details")
    return {
        "omitted": omitted,
        "reason": "The frontend view option surface selects stable view ids from the generated navigation graph; UI source, graph edges, and render artifacts remain source/evidence drilldowns.",
        "drilldown": _frontend_view_evidence_command(view_id),
    }


def _frontend_view_cluster_id(view: dict[str, Any]) -> str:
    shell_group = str(view.get("shell_group") or "").strip()
    if shell_group:
        return f"shell_group:{shell_group}"
    station_group = str(view.get("station_group") or "").strip()
    if station_group:
        return f"station_group:{station_group}"
    kind = str(view.get("kind") or "").strip()
    return f"kind:{kind or 'ungrouped'}"


def _frontend_view_cluster_label(cluster_id: str) -> str:
    _, _, raw = cluster_id.partition(":")
    label = raw or cluster_id
    return label.replace("_", " ").replace("-", " ").title()


def _frontend_view_cluster_rows(
    views: list[dict[str, Any]],
    *,
    repo_root: Path,
    graph: dict[str, Any],
    observation_rows: Mapping[str, Mapping[str, Any]],
    settlement_rows: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for view in views:
        grouped.setdefault(_frontend_view_cluster_id(view), []).append(view)

    cluster_currentness = {
        "status": "frontend_navigation_graph_available",
        "graph_ref": str(FRONTEND_NAV_GRAPH),
        "graph_mtime": _source_mtime(repo_root / FRONTEND_NAV_GRAPH),
        "graph_generated_at": graph.get("generated_at"),
        "source_hashes": dict(graph.get("source_hashes") or {}),
    }
    rows: list[dict[str, Any]] = []
    for cluster_id, group_views in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        top_ids = [_frontend_view_id(view) for view in group_views[:8] if _frontend_view_id(view)]
        ids = ",".join(top_ids)
        label = _frontend_view_cluster_label(cluster_id)
        kind_counts = Counter(str(view.get("kind") or "unknown") for view in group_views)
        station_group_counts = Counter(str(view.get("station_group") or "none") for view in group_views)
        capture_group_counts = Counter(
            str(_frontend_view_capture(view).get("capture_group") or "none") for view in group_views
        )
        observation_refs = [
            _frontend_view_observation_ref(_frontend_view_id(view), observation_rows)
            for view in group_views
        ]
        screenshot_status_counts = Counter(
            str((ref or {}).get("screenshot_status") or "missing_packet")
            for ref in observation_refs
        )
        visual_delta_status_counts = Counter(
            str((ref or {}).get("visual_delta_status") or "missing_packet")
            for ref in observation_refs
        )
        validation_route_class_counts = Counter(
            str(
                (_frontend_view_validation_contract(view).get("route_class"))
                or "missing_validation_contract"
            )
            for view in group_views
        )
        validation_browser_status_counts = Counter(
            str(
                (
                    _frontend_view_validation_contract(view).get(
                        "browser_visual_requirement"
                    )
                    or {}
                ).get("status")
                or "missing_requirement"
            )
            for view in group_views
        )
        settlement_refs = [
            _frontend_visual_settlement_ref(_frontend_view_id(view), settlement_rows)
            for view in group_views
        ]
        settlement_status_counts = Counter(
            str((ref or {}).get("settlement_status") or "not_in_active_settlement")
            for ref in settlement_refs
        )
        semantic_health_counts = Counter(
            str((view.get("surface_audit") or {}).get("semantic_health") or "unknown")
            for view in group_views
            if isinstance(view.get("surface_audit") or {}, dict)
        )
        rows.append(
            {
                "row_id": f"frontend_view_cluster:{cluster_id}::cluster_flag",
                "artifact_kind": "frontend_view_cluster",
                "band": "cluster_flag",
                "cluster_id": cluster_id,
                "group_label": label,
                "cluster_source_axis": cluster_id.split(":", 1)[0],
                "count": len(group_views),
                "top_ids": top_ids,
                "sample_routes": [str(view.get("route") or "") for view in group_views[:6] if view.get("route")],
                "kind_counts": dict(sorted(kind_counts.items())),
                "station_group_counts": dict(sorted(station_group_counts.items())),
                "capture_group_counts": dict(sorted(capture_group_counts.items())),
                "screenshot_status_counts": dict(sorted(screenshot_status_counts.items())),
                "visual_delta_status_counts": dict(sorted(visual_delta_status_counts.items())),
                "validation_route_class_counts": dict(
                    sorted(validation_route_class_counts.items())
                ),
                "validation_browser_requirement_status_counts": dict(
                    sorted(validation_browser_status_counts.items())
                ),
                "visual_settlement_status_counts": dict(sorted(settlement_status_counts.items())),
                "semantic_health_counts": dict(sorted(semantic_health_counts.items())),
                "capture_bound_count": sum(1 for view in group_views if bool(_frontend_view_capture(view))),
                "station_lens_eligible_count": sum(
                    1 for view in group_views if bool(view.get("station_lens_eligible"))
                ),
                "claim": f"{label}: {len(group_views)} frontend views from the navigation graph.",
                "drilldown_command": (
                    f"./repo-python kernel.py --option-surface frontend_views --band flag --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface frontend_views --band flag --ids <view_id>"
                ),
                "card_drilldown_command": (
                    f"./repo-python kernel.py --option-surface frontend_views --band card --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface frontend_views --band card --ids <view_id>"
                ),
                "evidence_command": "./repo-python kernel.py --view-graph",
                "currentness": cluster_currentness,
                "omission_receipt": {
                    "omitted": [
                        "row-level frontend view flags outside top_ids",
                        "card-level capture timing and source-hash details",
                        "full UI source bodies",
                        "full navigation graph edge list",
                        "render/capture artifact bodies and screenshots",
                    ],
                    "reason": "cluster_flag is the frontend view contents page; row flags and cards require explicit view ids.",
                    "drilldown": (
                        f"./repo-python kernel.py --option-surface frontend_views --band flag --ids {ids}"
                        if ids
                        else "./repo-python kernel.py --option-surface frontend_views --band flag --ids <view_id>"
                    ),
                },
            }
        )
    return rows


def _frontend_view_flag_row(
    view: dict[str, Any],
    *,
    repo_root: Path,
    graph: dict[str, Any],
    observation_rows: Mapping[str, Mapping[str, Any]],
    settlement_rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    view_id = _frontend_view_id(view)
    capture = _frontend_view_capture(view)
    source_component_ref = _frontend_view_source_component_ref(view)
    observation_ref = _frontend_view_observation_ref(view_id, observation_rows)
    settlement_ref = _frontend_visual_settlement_ref(view_id, settlement_rows)
    row: dict[str, Any] = {
        "row_id": f"frontend_view:{view_id}::flag",
        "artifact_kind": "frontend_view",
        "band": "flag",
        "view_id": view_id,
        "title": _frontend_view_title(view),
        "name": _frontend_view_title(view),
        "claim": _first_sentence(str(view.get("purpose") or ""), max_chars=260),
        "flag": _first_sentence(str(view.get("purpose") or ""), max_chars=260),
        "purpose": str(view.get("purpose") or ""),
        "kind": view.get("kind"),
        "route": view.get("route"),
        "path": view.get("route"),
        "entry_route": view.get("entry_route"),
        "route_aliases": [str(item) for item in list(view.get("route_aliases") or [])],
        "capture_slug": capture.get("slug"),
        "fanout_count": view.get("fanout_count"),
        "fanin_count": view.get("fanin_count"),
        "source_ref": (source_component_ref or {}).get("file"),
        "source_line": (source_component_ref or {}).get("line"),
        "source_component_ref": source_component_ref,
        "validation_contract": _frontend_view_validation_summary(view),
        "view_observation": observation_ref,
        "visual_settlement": settlement_ref,
        "visual_memory": {
            **_frontend_visual_memory_discovery(view_id),
            "packet_path": (observation_ref or {}).get("packet_path"),
            "markdown_path": (observation_ref or {}).get("markdown_path"),
            "screenshot_status": (observation_ref or {}).get("screenshot_status"),
            "refresh_due": (observation_ref or {}).get("refresh_due"),
            "visual_delta_status": (observation_ref or {}).get("visual_delta_status"),
            "settlement_status": (settlement_ref or {}).get("settlement_status"),
            "requires_review": (settlement_ref or {}).get("requires_review"),
        },
        "graph_ref": str(FRONTEND_NAV_GRAPH),
        "drilldown_command": f"./repo-python kernel.py --option-surface frontend_views --band card --ids {view_id}",
        "evidence_command": _frontend_view_evidence_command(view_id),
        "currentness": _frontend_view_currentness(
            view,
            repo_root=repo_root,
            graph=graph,
            observation_ref=observation_ref,
            settlement_ref=settlement_ref,
        ),
        "nearest_doctrine": {
            "ref": str(FRONTEND_NAV_DOCTRINE),
            "why": "The frontend navigation plane owns view-graph navigation posture; this adapter only exposes flag/card rows from the existing graph.",
        },
        "omission_receipt": _frontend_view_omission_receipt(view_id, band="flag"),
    }
    return row


def _frontend_view_card_row(
    view: dict[str, Any],
    *,
    repo_root: Path,
    graph: dict[str, Any],
    observation_rows: Mapping[str, Mapping[str, Any]],
    settlement_rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    row = _frontend_view_flag_row(
        view,
        repo_root=repo_root,
        graph=graph,
        observation_rows=observation_rows,
        settlement_rows=settlement_rows,
    )
    view_id = row["view_id"]
    capture = _frontend_view_capture(view)
    validation_contract = _frontend_view_validation_contract(view)
    validation_matrix = (
        graph.get("validation_matrix") if isinstance(graph.get("validation_matrix"), Mapping) else {}
    )
    graph_counts = graph.get("counts") if isinstance(graph.get("counts"), dict) else {}
    source_evidence = graph.get("source_evidence") if isinstance(graph.get("source_evidence"), dict) else {}
    row.update(
        {
            "row_id": f"frontend_view:{view_id}::card",
            "band": "card",
            "keywords": [str(item) for item in list(view.get("keywords") or [])],
            "shortcut": view.get("shortcut"),
            "shell_group": view.get("shell_group"),
            "station_group": view.get("station_group"),
            "home_tile_order": view.get("home_tile_order"),
            "station_lens_eligible": view.get("station_lens_eligible"),
            "overlay_of": view.get("overlay_of"),
            "cul_de_sac": dict(view.get("cul_de_sac") or {}),
            "capture": capture or None,
            "capture_contract": {
                "slug": capture.get("slug"),
                "route": capture.get("route"),
                "ready_selector": capture.get("ready_selector"),
                "stabilize_ms": capture.get("stabilize_ms"),
                "capture_group": capture.get("capture_group"),
                "bound_via": capture.get("bound_via"),
            }
            if capture
            else None,
            "edge_counts": {
                "fanout": view.get("fanout_count"),
                "fanin": view.get("fanin_count"),
            },
            "validation_contract": validation_contract or None,
            "validation_matrix": {
                "schema": validation_matrix.get("schema"),
                "route_class_counts": dict(
                    validation_matrix.get("route_class_counts") or {}
                ),
                "browser_visual_requirement_status_counts": dict(
                    validation_matrix.get("browser_visual_requirement_status_counts")
                    or {}
                ),
                "acceptance_commands": list(
                    validation_matrix.get("acceptance_commands") or []
                ),
            }
            if validation_matrix
            else None,
            "graph_counts": graph_counts,
            "source_evidence": source_evidence,
            "source_refs": [
                str(FRONTEND_NAV_GRAPH),
                str(FRONTEND_VIEW_OBSERVATION_INDEX),
                str(FRONTEND_VISUAL_SETTLEMENT),
                *[str(value) for value in source_evidence.values() if value],
            ],
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "native_graph_facets": [
                "route",
                "purpose",
                "component_tree",
                "source_capture",
                "validation_contract",
            ],
            "nearest_doctrine": {
                "ref": str(FRONTEND_NAV_DOCTRINE),
                "why": "The frontend navigation plane owns the graph semantics; the row card is a browse adapter over state/frontend_navigation/navigation_graph.json.",
            },
            "omission_receipt": _frontend_view_omission_receipt(view_id, band="card"),
        }
    )
    return row


def build_frontend_views_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="frontend_views",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    graph_path = repo_root / FRONTEND_NAV_GRAPH
    if not graph_path.exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="frontend_views",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The frontend navigation graph is missing.",
                "refs": [_relative(graph_path, repo_root)],
            }
        )
        return payload

    graph = _load_json(graph_path)
    observation_index = _frontend_view_observation_index(repo_root)
    observation_rows = _frontend_view_observation_rows(observation_index)
    settlement_index = _frontend_visual_settlement_index(repo_root)
    settlement_rows = _frontend_visual_settlement_rows(settlement_index)
    entries = _frontend_view_entries(graph)
    by_selector: dict[str, dict[str, Any]] = {}
    for entry in entries:
        selectors = [
            _frontend_view_id(entry),
            str(entry.get("slug") or ""),
            str(entry.get("label") or ""),
            str(entry.get("name") or ""),
            str(entry.get("title") or ""),
            str(entry.get("route") or ""),
            str(entry.get("entry_route") or ""),
            *[str(item) for item in list(entry.get("route_aliases") or [])],
        ]
        for selector in selectors:
            for alias in _frontend_view_selector_variants(selector):
                by_selector.setdefault(alias, entry)

    if ids:
        rows_source: list[dict[str, Any]] = []
        missing_ids: list[str] = []
        resolved_ids: dict[str, str] = {}
        seen: set[str] = set()
        for item in ids:
            entry = by_selector.get(item)
            if not entry:
                missing_ids.append(item)
                continue
            view_id = _frontend_view_id(entry)
            resolved_ids[item] = view_id
            if view_id in seen:
                continue
            seen.add(view_id)
            rows_source.append(entry)
    else:
        rows_source = entries
        missing_ids = []
        resolved_ids = {}

    if band == "cluster_flag":
        rows = _frontend_view_cluster_rows(
            rows_source,
            repo_root=repo_root,
            graph=graph,
            observation_rows=observation_rows,
            settlement_rows=settlement_rows,
        )
    elif band == "card":
        rows = [
            _frontend_view_card_row(
                entry,
                repo_root=repo_root,
                graph=graph,
                observation_rows=observation_rows,
                settlement_rows=settlement_rows,
            )
            for entry in rows_source
        ]
    else:
        rows = [
            _frontend_view_flag_row(
                entry,
                repo_root=repo_root,
                graph=graph,
                observation_rows=observation_rows,
                settlement_rows=settlement_rows,
            )
            for entry in rows_source
        ]
    graph_counts = graph.get("counts") if isinstance(graph.get("counts"), dict) else {}
    validation_matrix = (
        graph.get("validation_matrix") if isinstance(graph.get("validation_matrix"), Mapping) else {}
    )
    settlement_summary = (
        settlement_index.get("summary") if isinstance(settlement_index.get("summary"), Mapping) else {}
    )

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "frontend_views",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
            "resolved_ids": resolved_ids,
        },
        "profile_status": "supported",
        "authority_posture": "standard_owned_projection_not_source_authority",
        "governing_standard": {
            "ref": str(FRONTEND_NAV_DOCTRINE),
            "kind": "paper_module",
            "owned_bands": ["cluster_flag", "flag", "card"],
            "native_graph_facets_are_data_not_adapter_support": True,
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "source_refs": [
            str(FRONTEND_NAV_GRAPH),
            str(FRONTEND_NAV_DOCTRINE),
            str(FRONTEND_VIEW_OBSERVATION_INDEX),
            str(FRONTEND_VISUAL_SETTLEMENT),
            str(NAVIGATION_THEORY),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(entries),
            "query_used": False,
            "selection_method": (
                "artifact_kind_cluster_overview_from_view_graph"
                if band == "cluster_flag"
                else "artifact_kind_enumeration_from_view_graph"
            ),
            "drilldown_by": "shell_group" if band == "cluster_flag" else "view_id",
            "grouping_keys": ["shell_group", "station_group", "kind"] if band == "cluster_flag" else [],
            "graph_counts": graph_counts,
            "validation_matrix": {
                "schema": validation_matrix.get("schema"),
                "route_class_counts": dict(validation_matrix.get("route_class_counts") or {}),
                "browser_visual_requirement_status_counts": dict(
                    validation_matrix.get("browser_visual_requirement_status_counts")
                    or {}
                ),
                "acceptance_commands": list(
                    validation_matrix.get("acceptance_commands") or []
                ),
            }
            if validation_matrix
            else None,
            "view_observation_index": {
                "ref": str(FRONTEND_VIEW_OBSERVATION_INDEX),
                "row_count": len(observation_rows),
                "generated_at": observation_index.get("generated_at"),
                "status": (
                    "available"
                    if observation_rows
                    else "missing_or_empty"
                ),
            },
            "visual_settlement": {
                "ref": str(FRONTEND_VISUAL_SETTLEMENT),
                "row_count": len(settlement_rows),
                "generated_at": settlement_index.get("generated_at"),
                "status": (
                    "available"
                    if settlement_index
                    else "missing_or_empty"
                ),
                "status_counts": dict(
                    settlement_summary.get("status_counts") or {}
                ),
                "review_queue_count": settlement_summary.get("review_queue_count"),
            },
            "visual_memory_discovery": _frontend_visual_memory_discovery(),
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "native_graph_facets": [
                "route",
                "purpose",
                "component_tree",
                "source_capture",
                "validation_contract",
            ],
            "native_graph_facets_are_data_not_adapter_support": True,
            "source_graph_reused": str(FRONTEND_NAV_GRAPH),
            "visual_memory_source": str(FRONTEND_VIEW_OBSERVATION_INDEX),
            "visual_settlement_source": str(FRONTEND_VISUAL_SETTLEMENT),
            "visual_memory_docs_route": './repo-python kernel.py --docs-route "screenshot ledger"',
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "cluster_row_shape": (
                "compact_shell_group_counts_with_top_ids"
                if band == "cluster_flag"
                else "view_rows"
            ),
        },
        "rows": rows,
        "cluster_omission_receipt": (
            {
                "omitted": [
                    "all row-level frontend view flags",
                    "all card-level capture contracts",
                    "full UI source bodies",
                    "full navigation graph edge list",
                ],
                "reason": "cluster_flag groups frontend views before row expansion so agents can select a route family without reopening RootNavigator/App source.",
                "drilldown": "./repo-python kernel.py --option-surface frontend_views --band flag --ids <view_id>",
            }
            if band == "cluster_flag"
            else None
        ),
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface frontend_views --band cluster_flag",
                "reason": "Browse frontend view clusters before expanding row-level view flags.",
            },
            {
                "command": "./repo-python kernel.py --option-surface frontend_views --band flag --ids <view_id>[,<view_id>...]",
                "reason": "Browse explicit frontend view rows by stable view id before opening UI source or the full graph.",
            },
            {
                "command": "./repo-python kernel.py --option-surface frontend_views --band card --ids <view_id>",
                "reason": "Drill one view to route, source evidence, graph currentness, capture contract, view observation packet, screenshot ledger, and visual settlement state.",
            },
            {
                "command": './repo-python kernel.py --docs-route "screenshot ledger"',
                "reason": "Resolve the View Observation Memory / screenshot-ledger route from natural language before opening lower-level packets.",
            },
            {
                "command": "./repo-python kernel.py --view <view_id>",
                "reason": "Use the legacy view command as evidence drilldown after selecting a frontend view row.",
            },
        ],
        "warnings": [],
    }


def _raw_seed_shard_entries(projection: dict[str, Any]) -> list[dict[str, Any]]:
    shards = projection.get("shards")
    return [dict(shard) for shard in shards if isinstance(shard, dict)] if isinstance(shards, list) else []


def _raw_seed_shard_id(shard: dict[str, Any]) -> str:
    return str(shard.get("shard_id") or shard.get("id") or "").strip()


def _raw_seed_shard_groups(shard: dict[str, Any]) -> list[str]:
    groups = shard.get("idea_group_ids")
    return [str(group) for group in groups if str(group).strip()] if isinstance(groups, list) else []


def _raw_seed_shard_parent(shard: dict[str, Any]) -> str:
    return str(shard.get("parent_paragraph_id") or shard.get("raw_seed_anchor") or "").strip()


def _raw_seed_shard_title(shard: dict[str, Any]) -> str:
    shard_id = _raw_seed_shard_id(shard)
    groups = _raw_seed_shard_groups(shard)
    if groups:
        return f"{shard_id} - {groups[0]}"
    parent = _raw_seed_shard_parent(shard)
    if parent:
        return f"{shard_id} - {parent}"
    return shard_id


def _raw_seed_shard_flag(shard: dict[str, Any]) -> str:
    shard_id = _raw_seed_shard_id(shard)
    groups = _raw_seed_shard_groups(shard)
    status = str(shard.get("status") or "unknown")
    sibling_count = len(shard.get("sibling_shard_ids") or []) if isinstance(shard.get("sibling_shard_ids"), list) else 0
    group_text = f" in {', '.join(groups[:3])}" if groups else ""
    return f"Raw-seed shard {shard_id}{group_text}; status={status}; sibling_count={sibling_count}."


def _raw_seed_shard_source_refs(projection: dict[str, Any]) -> list[str]:
    source = projection.get("source") if isinstance(projection.get("source"), dict) else {}
    refs = [
        str(RAW_SEED_SHARDS),
        str(source.get("raw_seed_json_path") or ""),
        str(source.get("raw_seed_markdown_path") or ""),
    ]
    return [ref for ref in refs if ref]


def _raw_seed_shard_currentness(
    projection: dict[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    source = projection.get("source") if isinstance(projection.get("source"), dict) else {}
    counts = projection.get("counts") if isinstance(projection.get("counts"), dict) else {}
    return {
        "status": "raw_seed_shards_projection_available",
        "source_ref": str(RAW_SEED_SHARDS),
        "source_mtime": _source_mtime(repo_root / RAW_SEED_SHARDS),
        "projection_generated_at": projection.get("generated_at"),
        "registry_updated_at": source.get("registry_updated_at"),
        "total_shards": counts.get("total_shards"),
        "total_paragraphs": counts.get("total_paragraphs"),
        "total_idea_groups": counts.get("total_idea_groups"),
    }


def _raw_seed_shard_evidence_command(shard_id: str) -> str:
    return f"./repo-python kernel.py --shard {shard_id} --shards-source raw_seed"


def _raw_seed_shard_packet_commands(shard: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    parent = _raw_seed_shard_parent(shard)
    if parent:
        commands.append(
            "./repo-python kernel.py --shards --shards-source raw_seed "
            f"--shards-paragraph {parent} --shards-limit 12 --shards-packet"
        )
    groups = _raw_seed_shard_groups(shard)
    if groups:
        commands.append(
            "./repo-python kernel.py --shards --shards-source raw_seed "
            f"--shards-group {groups[0]} --shards-limit 12 --shards-packet"
        )
    return commands


def _raw_seed_shard_omission_receipt(shard: dict[str, Any], *, band: str) -> dict[str, Any]:
    omitted = [
        "raw voice paragraph body",
        "plain_text/text fields from shard drilldown",
        "context/deep profile-band expansion",
        "reversal neighborhood",
        "full source ancestry",
        "route-review context and apply decisions",
    ]
    if band == "flag":
        omitted.append("card-level sibling ids, dedication scores, and source projection metadata")
    return {
        "omitted": omitted,
        "reason": "The raw-seed shard option surface is a browse adapter over raw_seed_shards.json. It selects shard ids and source refs without replacing raw-seed authority or copying operator voice bodies.",
        "drilldown": _raw_seed_shard_evidence_command(_raw_seed_shard_id(shard)),
    }


def _raw_seed_shard_flag_row(
    shard: dict[str, Any],
    *,
    projection: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    shard_id = _raw_seed_shard_id(shard)
    parent = _raw_seed_shard_parent(shard)
    groups = _raw_seed_shard_groups(shard)
    sibling_ids = [str(item) for item in list(shard.get("sibling_shard_ids") or [])]
    return {
        "row_id": f"raw_seed_shard:{shard_id}::flag",
        "artifact_kind": "raw_seed_shard",
        "band": "flag",
        "shard_id": shard_id,
        "title": _raw_seed_shard_title(shard),
        "claim": _raw_seed_shard_flag(shard),
        "flag": _raw_seed_shard_flag(shard),
        "teleology_intent_capsule": build_teleology_intent_capsule(
            purpose=_raw_seed_shard_flag(shard),
            original_intent=shard.get("clarified_statement") or shard.get("raw_seed_anchor") or parent,
            served_deliverable=(
                "Selectable operator-intent shard for routing, doctrine lift, or contextual compression without reopening raw voice by default."
            ),
            non_purpose=[
                "Not raw operator voice authority.",
                "Not a license to mutate raw_seed.md or copy full paragraph text into projections.",
            ],
            evidence_refs=[str(RAW_SEED_SHARDS), parent, *_raw_seed_shard_packet_commands(shard)],
            freshness=f"projection_generated_at:{projection.get('generated_at') or ''}",
            owner_standard="codex/standards/observe_apply/std_extracted_shards.json",
            source_confidence="generated_from_raw_seed_shards_projection",
        ),
        "status": str(shard.get("status") or "unknown"),
        "family_id": projection.get("family_id"),
        "family_number": projection.get("family_number"),
        "source_substrate": shard.get("source_substrate"),
        "authored_by": shard.get("authored_by"),
        "parent_paragraph_id": parent,
        "source_paragraph_ref": parent,
        "paragraph_fingerprint": shard.get("paragraph_fingerprint"),
        "idea_group_ids": groups,
        "primary_idea_group_id": groups[0] if groups else None,
        "sibling_shard_count": len(sibling_ids),
        "dedication_max": shard.get("dedication_max"),
        "profile_id": RAW_SEED_PROFILE_ID,
        "source_ref": str(RAW_SEED_SHARDS),
        "source_refs": _raw_seed_shard_source_refs(projection),
        "drilldown_command": f"./repo-python kernel.py --option-surface raw_seed_shards --band card --ids {shard_id}",
        "evidence_command": _raw_seed_shard_evidence_command(shard_id),
        "currentness": _raw_seed_shard_currentness(projection, repo_root=repo_root),
        "omission_receipt": _raw_seed_shard_omission_receipt(shard, band="flag"),
    }


def _raw_seed_shard_card_row(
    shard: dict[str, Any],
    *,
    projection: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    row = _raw_seed_shard_flag_row(shard, projection=projection, repo_root=repo_root)
    shard_id = row["shard_id"]
    source = projection.get("source") if isinstance(projection.get("source"), dict) else {}
    counts = projection.get("counts") if isinstance(projection.get("counts"), dict) else {}
    sibling_ids = [str(item) for item in list(shard.get("sibling_shard_ids") or [])]
    row.update(
        {
            "row_id": f"raw_seed_shard:{shard_id}::card",
            "band": "card",
            "sibling_shard_ids": sibling_ids,
            "dedication_scores": dict(shard.get("dedication_scores") or {}),
            "projection_counts": {
                "total_paragraphs": counts.get("total_paragraphs"),
                "total_shards": counts.get("total_shards"),
                "total_idea_groups": counts.get("total_idea_groups"),
            },
            "projection_source": {
                "raw_seed_json_path": source.get("raw_seed_json_path"),
                "raw_seed_markdown_path": source.get("raw_seed_markdown_path"),
                "registry_updated_at": source.get("registry_updated_at"),
            },
            "available_projection_fields": sorted(str(key) for key in shard.keys()),
            "status_or_extraction_state": shard.get("status"),
            "concept_ids": [],
            "themes_or_routing_hints": row["idea_group_ids"],
            "related_principles": [],
            "doctrine_routes": [],
            "profile_id": RAW_SEED_PROFILE_ID,
            "native_profile_bands": list(RAW_SEED_NATIVE_PROFILE_BANDS),
            "adapter_supported_bands": ["flag", "card"],
            "nearest_profile": f"{PROFILE_REGISTRY_REL}::{RAW_SEED_PROFILE_ID}",
            "nearest_skill": {
                "ref": str(RAW_SEED_CONTEXTUAL_COMPRESSION_SKILL),
                "why": "The compression skill governs reversible raw-seed context rows, profile ids, drilldown refs, and omission receipts.",
            },
            "nearest_skills": [
                {
                    "ref": str(RAW_SEED_CONTEXTUAL_COMPRESSION_SKILL),
                    "skill_id": "raw_seed_contextual_compression",
                    "why": "Creator-side profile row discipline for raw-seed contextual compression.",
                },
                {
                    "ref": str(RAW_SEED_NAVIGATION_SKILL),
                    "skill_id": "raw_seed_navigation",
                    "why": "Navigator-side entry map for raw-seed read, shard, packet, and evidence commands.",
                },
            ],
            "evidence_commands": [
                _raw_seed_shard_evidence_command(shard_id),
                *_raw_seed_shard_packet_commands(shard),
            ],
            "omission_receipt": _raw_seed_shard_omission_receipt(shard, band="card"),
        }
    )
    return row


def build_raw_seed_shards_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="raw_seed_shards",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    projection_path = repo_root / RAW_SEED_SHARDS
    if not projection_path.exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="raw_seed_shards",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The raw-seed shard projection is missing.",
                "refs": [_relative(projection_path, repo_root)],
            }
        )
        return payload

    projection = _load_json(projection_path)
    entries = _raw_seed_shard_entries(projection)
    by_selector: dict[str, dict[str, Any]] = {}
    for entry in entries:
        selectors = [
            _raw_seed_shard_id(entry),
            _raw_seed_shard_parent(entry),
            str(entry.get("paragraph_fingerprint") or ""),
        ]
        for selector in selectors:
            if selector:
                by_selector.setdefault(selector, entry)

    if ids:
        rows_source: list[dict[str, Any]] = []
        missing_ids: list[str] = []
        seen: set[str] = set()
        for item in ids:
            entry = by_selector.get(item)
            if not entry:
                missing_ids.append(item)
                continue
            shard_id = _raw_seed_shard_id(entry)
            if shard_id in seen:
                continue
            seen.add(shard_id)
            rows_source.append(entry)
    else:
        rows_source = entries
        missing_ids = []

    rows = (
        [_raw_seed_shard_card_row(entry, projection=projection, repo_root=repo_root) for entry in rows_source]
        if band == "card"
        else [_raw_seed_shard_flag_row(entry, projection=projection, repo_root=repo_root) for entry in rows_source]
    )

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "raw_seed_shards",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "profile_governed_projection_not_source_authority",
        "governing_standard": {
            "ref": str(RAW_SEED_STANDARD),
            "profile_ref": f"{PROFILE_REGISTRY_REL}::{RAW_SEED_PROFILE_ID}",
            "owned_bands": ["flag", "card"],
            "native_profile_bands_are_data_not_adapter_support": True,
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "skill_refs": [
            str(RAW_SEED_CONTEXTUAL_COMPRESSION_SKILL),
            str(RAW_SEED_NAVIGATION_SKILL),
        ],
        "source_refs": [
            str(RAW_SEED_SHARDS),
            str(RAW_SEED_STANDARD),
            PROFILE_REGISTRY_REL,
            str(RAW_SEED_CONTEXTUAL_COMPRESSION_SKILL),
            str(RAW_SEED_NAVIGATION_SKILL),
            str(NAVIGATION_THEORY),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(entries),
            "query_used": False,
            "selection_method": "artifact_kind_enumeration_from_raw_seed_shards_projection",
            "drilldown_by": "shard_id",
            "source_projection_reused": str(RAW_SEED_SHARDS),
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["flag", "card"],
            "native_profile_bands": list(RAW_SEED_NATIVE_PROFILE_BANDS),
            "native_profile_bands_are_data_not_adapter_support": True,
            "source_projection_reused": str(RAW_SEED_SHARDS),
            "raw_seed_mutation_allowed": False,
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface raw_seed_shards --band flag",
                "reason": "Browse generated raw-seed shard ids without reopening raw_seed.md.",
            },
            {
                "command": "./repo-python kernel.py --option-surface raw_seed_shards --band card --ids <shard_id>",
                "reason": "Drill one shard to source refs, currentness, profile boundaries, and evidence commands.",
            },
            {
                "command": "./repo-python kernel.py --shard <shard_id> --shards-source raw_seed",
                "reason": "Use the raw-seed shard command as evidence drilldown after selecting a row.",
            },
        ],
        "warnings": [],
    }


def _annex_pattern_notes_path(repo_root: Path, slug: str) -> Path:
    return repo_root / ANNEX_ROOT / slug / ANNEX_NOTES_FILE_NAME


def _annex_pattern_notes_files(repo_root: Path) -> list[Path]:
    annex_root = repo_root / ANNEX_ROOT
    if not annex_root.exists():
        return []
    return sorted(annex_root.glob(f"*/{ANNEX_NOTES_FILE_NAME}"))


def _annex_pattern_entries(repo_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for notes_path in _annex_pattern_notes_files(repo_root):
        try:
            payload = _load_json(notes_path)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        slug = str(payload.get("slug") or notes_path.parent.name).strip()
        if not slug:
            continue
        notes = payload.get("notes")
        if not isinstance(notes, list):
            continue
        for note in notes:
            if not isinstance(note, dict):
                continue
            note_id = str(note.get("id") or "").strip()
            if not note_id:
                continue
            entries.append(
                {
                    "annex_slug": slug,
                    "note_id": note_id,
                    "note": note,
                    "notes_path": notes_path,
                }
            )
    return entries


def _annex_pattern_catalog_by_slug(repo_root: Path) -> dict[str, dict[str, Any]]:
    try:
        payload = _load_json(repo_root / ANNEX_CATALOG)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    rows = payload.get("annexes")
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slug") or "").strip()
        if slug:
            out[slug] = row
    return out


def _annex_pattern_catalog_row(
    entry: dict[str, Any],
    *,
    catalog_by_slug: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    return catalog_by_slug.get(str(entry.get("annex_slug") or ""), {})


def _annex_pattern_catalog_routing(
    entry: dict[str, Any],
    *,
    catalog_by_slug: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    row = _annex_pattern_catalog_row(entry, catalog_by_slug=catalog_by_slug)
    routing = row.get("routing_summary") if isinstance(row, Mapping) else {}
    return routing if isinstance(routing, Mapping) else {}


def _annex_pattern_routing_list(value: Any) -> list[str]:
    return [str(item) for item in value if str(item).strip()] if isinstance(value, list) else []


def _annex_pattern_cluster_key(
    entry: dict[str, Any],
    *,
    catalog_by_slug: Mapping[str, Mapping[str, Any]],
) -> str:
    routing = _annex_pattern_catalog_routing(entry, catalog_by_slug=catalog_by_slug)
    problem_spaces = _annex_pattern_routing_list(routing.get("problem_spaces"))
    return problem_spaces[0] if problem_spaces else "unrouted"


def _annex_pattern_source_kind(
    entry: dict[str, Any],
    *,
    catalog_by_slug: Mapping[str, Mapping[str, Any]],
) -> str:
    row = _annex_pattern_catalog_row(entry, catalog_by_slug=catalog_by_slug)
    return str(row.get("source_kind") or "unknown") if isinstance(row, Mapping) else "unknown"


def _annex_pattern_id(entry: dict[str, Any]) -> str:
    return f"{entry['annex_slug']}:{entry['note_id']}"


def _annex_pattern_targets(entry: dict[str, Any]) -> list[str]:
    targets = entry["note"].get("targets")
    return [str(item) for item in targets if str(item).strip()] if isinstance(targets, list) else []


def _annex_pattern_tags(entry: dict[str, Any]) -> list[str]:
    tags = entry["note"].get("tags")
    return [str(item) for item in tags if str(item).strip()] if isinstance(tags, list) else []


def _annex_pattern_routing(entry: dict[str, Any]) -> dict[str, list[str]]:
    routing = entry["note"].get("routing")
    if not isinstance(routing, dict):
        return {"problem_spaces": [], "capabilities": [], "ai_workflow_surfaces": []}
    return {
        "problem_spaces": [str(item) for item in (routing.get("problem_spaces") or []) if str(item).strip()],
        "capabilities": [str(item) for item in (routing.get("capabilities") or []) if str(item).strip()],
        "ai_workflow_surfaces": [str(item) for item in (routing.get("ai_workflow_surfaces") or []) if str(item).strip()],
    }


def _annex_pattern_title(entry: dict[str, Any]) -> str:
    targets = _annex_pattern_targets(entry)
    note_text = _collapse_ws(str(entry["note"].get("note") or ""))
    if targets:
        return f"{entry['annex_slug']}:{entry['note_id']} - {targets[0]}"
    if note_text:
        return f"{entry['annex_slug']}:{entry['note_id']} - {_truncate_words(note_text, max_chars=80)}"
    return f"{entry['annex_slug']}:{entry['note_id']}"


def _annex_pattern_flag_text(entry: dict[str, Any]) -> str:
    note_text = _collapse_ws(str(entry["note"].get("note") or ""))
    return _truncate_words(note_text, max_chars=200)


def _annex_pattern_evidence_command(entry: dict[str, Any], *, repo_root: Path) -> str:
    rel = _relative(_annex_pattern_notes_path(repo_root, entry["annex_slug"]), repo_root)
    return f"jq '.notes[] | select(.id==\"{entry['note_id']}\")' '{rel}'"


def _annex_pattern_annex_evidence_command(entry: dict[str, Any]) -> str:
    return f"./repo-python kernel.py --annex-search {entry['annex_slug']}"


def _annex_pattern_currentness(entry: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    notes_path = _annex_pattern_notes_path(repo_root, entry["annex_slug"])
    return {
        "status": "annex_notes_available",
        "source_ref": _relative(notes_path, repo_root),
        "source_mtime": _source_mtime(notes_path),
    }


def _annex_pattern_omission_receipt(entry: dict[str, Any], *, band: str, repo_root: Path) -> dict[str, Any]:
    omitted = [
        "external source repository body",
        "full annex source tree",
        "full note prose beyond bounded excerpt",
        "transitive local transfer closure",
        "runtime adoption decision",
    ]
    if band == "flag":
        omitted.append("card-level note excerpt, routing detail, and relevance justification")
    return {
        "omitted": omitted,
        "reason": (
            "The annex_patterns option surface is a read-only catalog adapter over local annex annotations."
            " It selects pattern ids and source refs without mining external repos or making adoption decisions."
        ),
        "drilldown": _annex_pattern_evidence_command(entry, repo_root=repo_root),
    }


def _annex_pattern_flag_row(
    entry: dict[str, Any],
    *,
    repo_root: Path,
    catalog_by_slug: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    pattern_id = _annex_pattern_id(entry)
    relevance = entry["note"].get("relevance")
    catalog = catalog_by_slug or {}
    routing = _annex_pattern_catalog_routing(entry, catalog_by_slug=catalog)
    cluster_key = _annex_pattern_cluster_key(entry, catalog_by_slug=catalog)
    return {
        "row_id": f"annex_pattern:{pattern_id}::flag",
        "artifact_kind": "annex_pattern",
        "band": "flag",
        "annex_slug": entry["annex_slug"],
        "note_id": entry["note_id"],
        "pattern_id": pattern_id,
        "annex_pattern_cluster_key": cluster_key,
        "cluster_key_provenance": "annex_catalog.routing_summary.problem_spaces[0]",
        "catalog_problem_spaces": _annex_pattern_routing_list(routing.get("problem_spaces")),
        "catalog_capabilities": _annex_pattern_routing_list(routing.get("capabilities")),
        "source_kind": _annex_pattern_source_kind(entry, catalog_by_slug=catalog),
        "title": _annex_pattern_title(entry),
        "claim": _annex_pattern_flag_text(entry),
        "flag": _annex_pattern_flag_text(entry),
        "targets": _annex_pattern_targets(entry),
        "tags": _annex_pattern_tags(entry),
        "relevance": relevance if isinstance(relevance, int) else None,
        "routing": _annex_pattern_routing(entry),
        "profile_id": ANNEX_PATTERN_PROFILE_ID,
        "source_ref": _relative(_annex_pattern_notes_path(repo_root, entry["annex_slug"]), repo_root),
        "drilldown_command": (
            f"./repo-python kernel.py --option-surface annex_patterns --band card --ids {pattern_id}"
        ),
        "evidence_command": _annex_pattern_evidence_command(entry, repo_root=repo_root),
        "annex_evidence_command": _annex_pattern_annex_evidence_command(entry),
        "currentness": _annex_pattern_currentness(entry, repo_root=repo_root),
        "omission_receipt": _annex_pattern_omission_receipt(entry, band="flag", repo_root=repo_root),
}


def _annex_pattern_card_row(
    entry: dict[str, Any],
    *,
    repo_root: Path,
    catalog_by_slug: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    row = _annex_pattern_flag_row(entry, repo_root=repo_root, catalog_by_slug=catalog_by_slug)
    pattern_id = row["pattern_id"]
    note_text = str(entry["note"].get("note") or "")
    note_compact = _collapse_ws(note_text)
    note_excerpt = _truncate_words(note_compact, max_chars=600)
    relevance_justification = entry["note"].get("relevance_justification")
    added_at = entry["note"].get("added_at")
    notes_path_rel = _relative(_annex_pattern_notes_path(repo_root, entry["annex_slug"]), repo_root)
    row.update(
        {
            "row_id": f"annex_pattern:{pattern_id}::card",
            "band": "card",
            "note_excerpt": note_excerpt,
            "note_char_count": len(note_text),
            "note_word_count": len(note_compact.split()) if note_compact else 0,
            "relevance_justification": str(relevance_justification) if relevance_justification else None,
            "added_at": str(added_at) if added_at else None,
            "available_note_fields": sorted(str(key) for key in entry["note"].keys()),
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "native_annex_facets": list(ANNEX_PATTERN_NATIVE_PROFILE_BANDS),
            "nearest_standard": {
                "ref": str(ANNEX_AUTHORITY_INDEX),
                "why": "Annex authority and artifact standards index governs annex notes, distillation, and pattern transfer contracts.",
            },
            "nearest_skills": [
                {
                    "ref": str(ANNEX_PATTERN_FLOOR_RUNTIME_FORK_SKILL),
                    "skill_id": "annex_pattern_floor_runtime_fork",
                    "why": "Distinguishes the universal annex pattern floor from the rare runtime adoption fork.",
                },
                {
                    "ref": str(ANNEX_PATTERN_TRANSFER_SKILL),
                    "skill_id": "annex_pattern_transfer",
                    "why": "Names the move from annex pattern recognition to local doctrine/skill translation without copying code.",
                },
            ],
            "evidence_commands": [
                _annex_pattern_evidence_command(entry, repo_root=repo_root),
                _annex_pattern_annex_evidence_command(entry),
            ],
            "source_refs": [notes_path_rel],
            "omission_receipt": _annex_pattern_omission_receipt(entry, band="card", repo_root=repo_root),
        }
    )
    return row


def _annex_pattern_cluster_rows(
    entries: list[dict[str, Any]],
    *,
    repo_root: Path,
    catalog_by_slug: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        grouped.setdefault(_annex_pattern_cluster_key(entry, catalog_by_slug=catalog_by_slug), []).append(entry)

    rows: list[dict[str, Any]] = []
    for cluster_id, group_entries in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        top_ids = [_annex_pattern_id(entry) for entry in group_entries[:4]]
        annex_slugs = sorted({str(entry.get("annex_slug") or "") for entry in group_entries if entry.get("annex_slug")})
        label = "Unrouted annex notes" if cluster_id == "unrouted" else cluster_id.replace("-", " ").title()
        rows.append(
            {
                "cluster_id": cluster_id,
                "label": label,
                "count": len(group_entries),
                "annex_count": len(annex_slugs),
                "top_ids": top_ids,
                "claim": f"{label}: {len(group_entries)} annex note rows across {len(annex_slugs)} annexes",
            }
        )
    return rows


def build_annex_patterns_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="annex_patterns",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    annex_root = repo_root / ANNEX_ROOT
    if not annex_root.exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="annex_patterns",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The annexes/ directory is missing.",
                "refs": [_relative(annex_root, repo_root)],
            }
        )
        return payload

    entries = _annex_pattern_entries(repo_root)
    catalog_by_slug = _annex_pattern_catalog_by_slug(repo_root)
    by_id: dict[str, dict[str, Any]] = {}
    for entry in entries:
        by_id.setdefault(_annex_pattern_id(entry), entry)

    if ids:
        rows_source: list[dict[str, Any]] = []
        missing_ids: list[str] = []
        seen: set[str] = set()
        for item in ids:
            entry = by_id.get(item)
            if not entry:
                missing_ids.append(item)
                continue
            pattern_id = _annex_pattern_id(entry)
            if pattern_id in seen:
                continue
            seen.add(pattern_id)
            rows_source.append(entry)
    else:
        rows_source = entries
        missing_ids = []

    if band == "cluster_flag":
        rows = _annex_pattern_cluster_rows(rows_source, repo_root=repo_root, catalog_by_slug=catalog_by_slug)
    elif band == "card":
        rows = [
            _annex_pattern_card_row(entry, repo_root=repo_root, catalog_by_slug=catalog_by_slug)
            for entry in rows_source
        ]
    else:
        rows = [
            _annex_pattern_flag_row(entry, repo_root=repo_root, catalog_by_slug=catalog_by_slug)
            for entry in rows_source
        ]

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "annex_patterns",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "local_annex_annotation_catalog_not_source_authority",
        "governing_standard": {
            "ref": str(ANNEX_AUTHORITY_INDEX),
            "cluster_key_standard_ref": str(ANNEX_CATALOG_STANDARD),
            "profile_ref": ANNEX_PATTERN_PROFILE_ID,
            "owned_bands": ["cluster_flag", "flag", "card"],
            "native_profile_bands_are_data_not_adapter_support": True,
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "skill_refs": [
            str(ANNEX_PATTERN_FLOOR_RUNTIME_FORK_SKILL),
            str(ANNEX_PATTERN_TRANSFER_SKILL),
        ],
        "source_refs": [
            str(ANNEX_ROOT),
            str(ANNEX_CATALOG),
            str(ANNEX_AUTHORITY_INDEX),
            str(ANNEX_CATALOG_STANDARD),
            str(ANNEX_PATTERN_FLOOR_RUNTIME_FORK_SKILL),
            str(ANNEX_PATTERN_TRANSFER_SKILL),
            str(NAVIGATION_THEORY),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(entries),
            "query_used": False,
            "selection_method": (
                "artifact_kind_cluster_overview_from_annex_catalog_problem_spaces"
                if band == "cluster_flag"
                else "artifact_kind_enumeration_from_annex_notes"
            ),
            "drilldown_by": "annex_pattern_cluster_key" if band == "cluster_flag" else "pattern_id",
            "source_projection_reused": str(ANNEX_CATALOG) if band == "cluster_flag" else str(ANNEX_ROOT),
            "grouping_keys": (
                ["annex_pattern_cluster_key", "annex_catalog.routing_summary.problem_spaces[0]"]
                if band == "cluster_flag"
                else []
            ),
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "native_profile_bands": list(ANNEX_PATTERN_NATIVE_PROFILE_BANDS),
            "native_profile_bands_are_data_not_adapter_support": True,
            "source_projection_reused": str(ANNEX_CATALOG) if band == "cluster_flag" else str(ANNEX_ROOT),
            "annex_repair_or_population_allowed": False,
            "external_source_fetch_allowed": False,
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "cluster_row_shape": (
                "compact_problem_space_counts_with_top_ids"
                if band == "cluster_flag"
                else "pattern_rows"
            ),
        },
        "omission_receipt": {
            "omitted": [
                "row-level flag/card bodies outside each cluster's top_ids",
                "full annex_notes.json prose",
                "external source repository bodies",
                "transitive local transfer closure and runtime adoption decisions",
            ],
            "reason": (
                "cluster_flag is the annex_patterns contents page. It groups local annex notes "
                "by the standard-owned annex_catalog routing_summary.problem_spaces primary key; "
                "rows without that controlled routing metadata remain visible in the unrouted bucket."
            ),
            "drilldown": "./repo-python kernel.py --option-surface annex_patterns --band flag --ids <slug>:<note_id>",
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface annex_patterns --band cluster_flag",
                "reason": "Browse problem-space clusters before expanding local annex annotation rows.",
            },
            {
                "command": "./repo-python kernel.py --option-surface annex_patterns --band flag --ids <slug>:<note_id>[,<slug>:<note_id>...]",
                "reason": "Browse explicit local annex annotations as stable rows before opening external source repos.",
            },
            {
                "command": "./repo-python kernel.py --option-surface annex_patterns --band card --ids <slug>:<note_id>",
                "reason": "Drill one annex annotation to bounded excerpt, routing facets, evidence commands, and omission receipt.",
            },
            {
                "command": "./repo-python kernel.py --annex-search <slug>",
                "reason": "Use the annex search command for slug-level annex evidence after selecting a row.",
            },
        ],
        "warnings": [],
    }


def _microcosm_extracted_pattern_entries(repo_root: Path) -> list[dict[str, Any]]:
    ledger_path = repo_root / MICROCOSM_EXTRACTED_PATTERN_LEDGER
    entries: list[dict[str, Any]] = []
    try:
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return entries
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        pattern_id = str(row.get("pattern_id") or "").strip()
        if not pattern_id:
            continue
        entries.append(
            {
                "pattern_id": pattern_id,
                "pattern": row,
                "source_path": ledger_path,
                "line_number": line_number,
            }
        )
    return entries


def _microcosm_extracted_pattern_evidence_command(entry: dict[str, Any], *, repo_root: Path) -> str:
    source_ref = _relative(entry["source_path"], repo_root)
    return f"rg -n '\"pattern_id\":\"{entry['pattern_id']}\"' {source_ref}"


def _microcosm_extracted_pattern_currentness(entry: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    pattern = entry["pattern"]
    source_path = entry["source_path"]
    return {
        "status": "macro_side_extracted_pattern_ledger_available",
        "source_ref": _relative(source_path, repo_root),
        "source_mtime": _source_mtime(source_path),
        "line_number": entry.get("line_number"),
        "extracted_at": str(pattern.get("extracted_at") or ""),
        "extracted_by": str(pattern.get("extracted_by") or ""),
    }


def _microcosm_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _microcosm_extracted_pattern_binding_index(repo_root: Path) -> dict[str, dict[str, Any]]:
    try:
        payload = _load_json(repo_root / MICROCOSM_EXTRACTED_PATTERN_BINDINGS)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    rows = payload.get("pattern_bindings")
    if not isinstance(rows, list):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        pattern_id = str(row.get("pattern_id") or "").strip()
        if pattern_id:
            index[pattern_id] = row
    return index


def _microcosm_extracted_pattern_binding_summary(
    entry: dict[str, Any],
    *,
    binding_index: Mapping[str, Any] | None,
) -> dict[str, Any]:
    index = binding_index if isinstance(binding_index, Mapping) else {}
    binding = index.get(entry["pattern_id"])
    if not isinstance(binding, Mapping):
        return {
            "status": "missing_detailed_binding",
            "binding_ref": str(MICROCOSM_EXTRACTED_PATTERN_BINDINGS),
            "authority": (
                "absence from the detailed binding sidecar is an import-readiness gap; "
                "the extracted ledger row remains macro-side pattern evidence only"
            ),
        }
    substrate = binding.get("substrate_bindings") if isinstance(binding.get("substrate_bindings"), Mapping) else {}
    ref_counts = {
        key: len(value)
        for key, value in sorted(substrate.items())
        if isinstance(value, list)
    }
    return {
        "status": "detailed_binding_available",
        "binding_ref": str(MICROCOSM_EXTRACTED_PATTERN_BINDINGS),
        "grounding_status": str(binding.get("grounding_status") or ""),
        "public_projection_posture": str(binding.get("public_projection_posture") or ""),
        "missing_bindings": _string_list(binding.get("missing_bindings")),
        "substrate_ref_counts": ref_counts,
        "standard_refs": _string_list(substrate.get("standards"))[:6],
        "code_owner_refs": _string_list(substrate.get("code_owners"))[:6],
        "test_validator_receipt_refs": _string_list(substrate.get("tests_validators_proofs"))[:6],
        "generated_artifact_receipt_refs": _string_list(substrate.get("generated_artifacts_receipts"))[:6],
        "command_surfaces": _string_list(substrate.get("command_surfaces"))[:4],
        "fixture_strategy": _truncate_words(str(binding.get("fixture_strategy") or ""), max_chars=520),
        "anti_claim": _truncate_words(str(binding.get("anti_claim") or ""), max_chars=520),
        "next_binding_action": _truncate_words(str(binding.get("next_binding_action") or ""), max_chars=520),
        "authority": (
            "detailed binding sidecar summary only; source files, standards, tests, "
            "fixtures, receipts, and owner tools remain the underlying authorities"
        ),
    }


def _microcosm_extracted_pattern_binding_overlay(
    entry: dict[str, Any],
    *,
    route_readiness_index: Mapping[str, Any] | None,
    binding_index: Mapping[str, Any] | None,
) -> dict[str, Any]:
    membership = _microcosm_extracted_pattern_route_readiness_membership(
        entry,
        route_readiness_index=route_readiness_index,
    )
    binding = _microcosm_extracted_pattern_binding_summary(
        entry,
        binding_index=binding_index,
    )
    route_status = str(membership.get("status") or "unknown")
    binding_status = str(binding.get("status") or "unknown")
    routed = route_status == "routed_to_organ_bundle"
    detailed = binding_status == "detailed_binding_available"
    if routed and detailed:
        overlay_status = "routed_with_detailed_binding"
    elif routed:
        overlay_status = "routed_missing_detailed_binding"
    elif detailed:
        overlay_status = "detailed_binding_not_routed"
    else:
        overlay_status = "unrouted_missing_detailed_binding"
    return {
        "status": overlay_status,
        "route_readiness_status": route_status,
        "substrate_binding_status": binding_status,
        "route_to_organ_ids": _string_list(membership.get("route_to_organ_ids"))[:6],
        "readiness_ids": _string_list(membership.get("readiness_ids"))[:6],
        "binding_ref": str(MICROCOSM_EXTRACTED_PATTERN_BINDINGS),
        "readiness_ref": str(MICROCOSM_EXTRACTED_PATTERN_READINESS_AUDIT),
        "authority": (
            "binding-aware routability overlay only; current_microcosm_status remains the "
            "raw extraction snapshot, and public Microcosm release authority stays with the "
            "target organ, tests, receipts, and owner tools"
        ),
    }


def _microcosm_extracted_pattern_route_readiness_index(repo_root: Path) -> dict[str, Any]:
    try:
        router = _load_json(repo_root / MICROCOSM_EXTRACTED_PATTERN_ROW_TO_ORGAN_ROUTER)
        cards = _load_json(repo_root / MICROCOSM_EXTRACTED_PATTERN_ORGAN_ROUTE_CARDS)
        audit = _load_json(repo_root / MICROCOSM_EXTRACTED_PATTERN_READINESS_AUDIT)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"by_pattern_id": {}}
    try:
        bindings = _load_json(repo_root / MICROCOSM_EXTRACTED_PATTERN_BINDINGS)
    except (FileNotFoundError, json.JSONDecodeError):
        bindings = {}

    by_pattern_id: dict[str, dict[str, Any]] = {}
    organ_to_cards: dict[str, list[dict[str, Any]]] = {}
    pattern_to_cards: dict[str, list[dict[str, Any]]] = {}
    organ_to_readiness: dict[str, list[dict[str, Any]]] = {}

    for card in _microcosm_list(cards.get("route_cards")):
        if not isinstance(card, Mapping):
            continue
        for organ_id in _string_list(card.get("organ_ids")):
            organ_to_cards.setdefault(organ_id, []).append(dict(card))
        for pattern_id in _string_list(card.get("anchor_pattern_ids")):
            pattern_to_cards.setdefault(pattern_id, []).append(dict(card))

    for readiness in _microcosm_list(audit.get("organ_readiness")):
        if not isinstance(readiness, Mapping):
            continue
        readiness_id = str(readiness.get("readiness_id") or "").strip()
        if readiness_id:
            organ_to_readiness.setdefault(readiness_id, []).append(dict(readiness))
        for organ_id in _string_list(readiness.get("route_to_organ_ids")):
            organ_to_readiness.setdefault(organ_id, []).append(dict(readiness))

    selector = audit.get("selector_contract") if isinstance(audit.get("selector_contract"), Mapping) else {}
    selector_may_select = set(_string_list(selector.get("selector_may_select")))
    selector_may_select_after_roots = set(_string_list(selector.get("selector_may_select_after_roots")))
    selector_must_fold_or_defer = set(_string_list(selector.get("selector_must_fold_or_defer")))

    def selector_posture(readiness_id: str) -> str:
        if readiness_id in selector_may_select:
            return "selector_may_select"
        if readiness_id in selector_may_select_after_roots:
            return "selector_may_select_after_roots"
        if readiness_id in selector_must_fold_or_defer:
            return "selector_must_fold_or_defer"
        return "selector_not_declared"

    def membership_for(pattern_id: str) -> dict[str, Any]:
        return by_pattern_id.setdefault(
            pattern_id,
            {
                "router_ids": [],
                "combination_route_ids": [],
                "route_collections": [],
                "route_to_organ_ids": [],
                "carry_with_organ_ids": [],
                "route_card_ids": [],
                "readiness_ids": [],
                "selector_postures": [],
                "selection_postures": [],
                "individual_row_selection": [],
                "standalone_postures": [],
            },
        )

    def attach_organ_context(membership: dict[str, Any], *, pattern_id: str, organ_id: str) -> None:
        cards_for_route = [*organ_to_cards.get(organ_id, []), *pattern_to_cards.get(pattern_id, [])]
        for card in cards_for_route:
            if str(card.get("card_id") or "").strip():
                membership["route_card_ids"].append(str(card.get("card_id") or "").strip())
            if str(card.get("selection_posture") or "").strip():
                membership["selection_postures"].append(str(card.get("selection_posture") or "").strip())
        for readiness in organ_to_readiness.get(organ_id, []):
            readiness_id = str(readiness.get("readiness_id") or "").strip()
            if readiness_id:
                membership["readiness_ids"].append(readiness_id)
                membership["selector_postures"].append(selector_posture(readiness_id))
            if str(readiness.get("individual_row_selection") or "").strip():
                membership["individual_row_selection"].append(
                    str(readiness.get("individual_row_selection") or "").strip()
                )

    for router_row in _microcosm_list(router.get("family_routers")):
        if not isinstance(router_row, Mapping):
            continue
        route_to = str(router_row.get("primary_route_to_organ_id") or "").strip()
        if not route_to:
            continue
        for pattern_id in _string_list(router_row.get("match_pattern_ids")):
            membership = membership_for(pattern_id)
            membership["router_ids"].append(str(router_row.get("router_id") or ""))
            membership["route_to_organ_ids"].append(route_to)
            membership["carry_with_organ_ids"].extend(_string_list(router_row.get("carry_with_organ_ids")))
            if str(router_row.get("selection_posture") or "").strip():
                membership["selection_postures"].append(str(router_row.get("selection_posture") or "").strip())
            if str(router_row.get("standalone_posture") or "").strip():
                membership["standalone_postures"].append(str(router_row.get("standalone_posture") or "").strip())
            attach_organ_context(membership, pattern_id=pattern_id, organ_id=route_to)

    for collection_name in ("foundation_combination_routes", "frontier_combination_routes"):
        for route in _microcosm_list(bindings.get(collection_name) if isinstance(bindings, Mapping) else None):
            if not isinstance(route, Mapping):
                continue
            route_id = str(route.get("route_id") or "").strip()
            target_organs = _string_list(route.get("target_existing_organs"))
            route_pattern_ids = _string_list(route.get("available_pattern_ids"))
            if not route_id or not target_organs or not route_pattern_ids:
                continue
            for pattern_id in route_pattern_ids:
                membership = membership_for(pattern_id)
                membership["combination_route_ids"].append(route_id)
                membership["route_collections"].append(collection_name)
                membership["route_to_organ_ids"].extend(target_organs)
                selection_boundary = str(route.get("selection_boundary") or "").strip()
                if selection_boundary:
                    membership["selection_postures"].append(selection_boundary)
                for organ_id in target_organs:
                    attach_organ_context(membership, pattern_id=pattern_id, organ_id=organ_id)

    for membership in by_pattern_id.values():
        for key in (
            "router_ids",
            "combination_route_ids",
            "route_collections",
            "route_to_organ_ids",
            "carry_with_organ_ids",
            "route_card_ids",
            "readiness_ids",
            "selector_postures",
            "selection_postures",
            "individual_row_selection",
            "standalone_postures",
        ):
            membership[key] = sorted({item for item in membership[key] if item})
        membership["status"] = "routed_to_organ_bundle"
        membership["validation_hooks"] = [
            "./repo-python tools/meta/factory/check_extracted_pattern_route_readiness.py --check",
            "./repo-python tools/meta/factory/build_extracted_pattern_substrate_bindings.py --check --report",
        ]
        membership["authority"] = (
            "macro-side route-readiness membership only; not standalone pattern selection, "
            "public leaf projection, release authority, or row truth certification"
        )

    return {"by_pattern_id": by_pattern_id}


def _microcosm_extracted_pattern_route_readiness_membership(
    entry: dict[str, Any],
    *,
    route_readiness_index: Mapping[str, Any] | None,
) -> dict[str, Any]:
    index = route_readiness_index if isinstance(route_readiness_index, Mapping) else {}
    by_pattern_id = index.get("by_pattern_id") if isinstance(index.get("by_pattern_id"), Mapping) else {}
    membership = by_pattern_id.get(entry["pattern_id"])
    if isinstance(membership, Mapping):
        return dict(membership)
    return {
        "status": "unrouted_in_route_readiness_overlays",
        "validation_hooks": [
            "./repo-python tools/meta/factory/check_extracted_pattern_route_readiness.py --check",
            "./repo-python tools/meta/factory/build_extracted_pattern_substrate_bindings.py --check --report",
        ],
        "authority": (
            "absence from route-readiness overlays is a routing gap or deferred posture, "
            "not proof that the pattern is invalid"
        ),
    }


def _microcosm_extracted_pattern_omission_receipt(
    entry: dict[str, Any], *, band: str, repo_root: Path
) -> dict[str, Any]:
    omitted = [
        "full macro-private source refs beyond row-local handles",
        "public projection or release authorization",
        "future reconstruction-pass output",
        "full sidecar binding/readiness reports",
    ]
    if band == "flag":
        omitted.append("card-level fixture, load-bearing rationale, and notes")
    return {
        "omitted": omitted,
        "reason": (
            "The microcosm_extracted_patterns option surface exposes the macro-side distilled"
            " pattern pool for Microcosm reconstruction. Rows are extraction records, not"
            " public microcosm release authority."
        ),
        "drilldown": _microcosm_extracted_pattern_evidence_command(entry, repo_root=repo_root),
    }


def _microcosm_extracted_pattern_flag_row(
    entry: dict[str, Any],
    *,
    repo_root: Path,
    route_readiness_index: Mapping[str, Any] | None = None,
    binding_index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pattern = entry["pattern"]
    pattern_id = entry["pattern_id"]
    one_line = _truncate_words(str(pattern.get("one_line") or ""), max_chars=420)
    source_refs = _string_list(pattern.get("source_refs"))
    binding_overlay = _microcosm_extracted_pattern_binding_overlay(
        entry,
        route_readiness_index=route_readiness_index,
        binding_index=binding_index,
    )
    return {
        "row_id": f"microcosm_extracted_pattern:{pattern_id}::flag",
        "artifact_kind": "microcosm_extracted_pattern",
        "band": "flag",
        "pattern_id": pattern_id,
        "title": str(pattern.get("title") or pattern_id),
        "claim": one_line,
        "flag": one_line,
        "one_line": one_line,
        "organ_family": str(pattern.get("organ_family") or "missing"),
        "macro_subdomain": str(pattern.get("macro_subdomain") or ""),
        "novelty_band": str(pattern.get("novelty_band") or ""),
        "private_state_risk": str(pattern.get("private_state_risk") or ""),
        "current_microcosm_status": str(pattern.get("current_microcosm_status") or ""),
        "binding_overlay_status": binding_overlay["status"],
        "route_readiness_status": binding_overlay["route_readiness_status"],
        "substrate_binding_status": binding_overlay["substrate_binding_status"],
        "route_to_organ_ids": binding_overlay["route_to_organ_ids"],
        "readiness_ids": binding_overlay["readiness_ids"],
        "candidate_leaf_name": str(pattern.get("candidate_leaf_name") or ""),
        "candidate_paper_module_slug": str(pattern.get("candidate_paper_module_slug") or ""),
        "source_refs": source_refs[:6],
        "source_ref_count": len(source_refs),
        "profile_id": "microcosm_extracted_pattern_navigation_v0",
        "source_ref": _relative(entry["source_path"], repo_root),
        "drilldown_command": (
            "./repo-python kernel.py --option-surface microcosm_extracted_patterns "
            f"--band card --ids {pattern_id}"
        ),
        "evidence_command": _microcosm_extracted_pattern_evidence_command(entry, repo_root=repo_root),
        "currentness": _microcosm_extracted_pattern_currentness(entry, repo_root=repo_root),
        "omission_receipt": _microcosm_extracted_pattern_omission_receipt(
            entry, band="flag", repo_root=repo_root
        ),
    }


def _microcosm_extracted_pattern_card_row(
    entry: dict[str, Any],
    *,
    repo_root: Path,
    route_readiness_index: Mapping[str, Any] | None = None,
    binding_index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = _microcosm_extracted_pattern_flag_row(
        entry,
        repo_root=repo_root,
        route_readiness_index=route_readiness_index,
        binding_index=binding_index,
    )
    pattern = entry["pattern"]
    row.update(
        {
            "row_id": f"microcosm_extracted_pattern:{entry['pattern_id']}::card",
            "band": "card",
            "why_load_bearing": _truncate_words(
                str(pattern.get("why_load_bearing") or ""), max_chars=900
            ),
            "candidate_fixture": _truncate_words(
                str(pattern.get("candidate_fixture") or ""), max_chars=900
            ),
            "failure_mode_prevented": _truncate_words(
                str(pattern.get("failure_mode_prevented") or ""), max_chars=700
            ),
            "axioms_principles_likely_instantiated": _string_list(
                pattern.get("axioms_principles_likely_instantiated")
            ),
            "depends_on_patterns": _string_list(pattern.get("depends_on_patterns")),
            "feeds_patterns": _string_list(pattern.get("feeds_patterns")),
            "evidence_kind": str(pattern.get("evidence_kind") or ""),
            "notes": _truncate_words(str(pattern.get("notes") or ""), max_chars=900),
            "available_pattern_fields": sorted(str(key) for key in pattern.keys()),
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "nearest_standards": [
                {
                    "ref": str(MICROCOSM_EXTRACTED_PATTERN_SUBSTRATE_STANDARD),
                    "why": "Governs substrate binding sidecars for the extracted pattern ledger.",
                },
                {
                    "ref": str(MICROCOSM_EXTRACTED_PATTERN_ROUTE_STANDARD),
                    "why": "Governs route-readiness overlays for projecting ledger rows into microcosm organs.",
                },
            ],
            "nearest_paper_module": {
                "ref": str(MICROCOSM_SUBSTRATE_MODULE),
                "why": "Owns Microcosm as public-safe compression rather than raw private-root release.",
            },
            "sidecar_refs": [
                str(MICROCOSM_EXTRACTED_PATTERN_BINDINGS),
                str(MICROCOSM_EXTRACTED_PATTERN_WEAK_BINDINGS),
                str(MICROCOSM_EXTRACTED_PATTERN_READINESS_AUDIT),
            ],
            "binding_overlay": _microcosm_extracted_pattern_binding_overlay(
                entry,
                route_readiness_index=route_readiness_index,
                binding_index=binding_index,
            ),
            "route_readiness_membership": _microcosm_extracted_pattern_route_readiness_membership(
                entry,
                route_readiness_index=route_readiness_index,
            ),
            "substrate_binding_summary": _microcosm_extracted_pattern_binding_summary(
                entry,
                binding_index=binding_index,
            ),
            "evidence_commands": [
                _microcosm_extracted_pattern_evidence_command(entry, repo_root=repo_root),
                "./repo-python tools/meta/factory/build_extracted_pattern_substrate_bindings.py --check",
                "./repo-python tools/meta/factory/check_extracted_pattern_route_readiness.py",
            ],
            "omission_receipt": _microcosm_extracted_pattern_omission_receipt(
                entry, band="card", repo_root=repo_root
            ),
        }
    )
    return row


def _microcosm_extracted_pattern_cluster_rows(
    entries: list[dict[str, Any]],
    *,
    route_readiness_index: Mapping[str, Any] | None = None,
    binding_index: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for entry in sorted(entries, key=lambda item: str(item.get("pattern_id") or "")):
        pattern = entry["pattern"]
        binding_overlay = _microcosm_extracted_pattern_binding_overlay(
            entry,
            route_readiness_index=route_readiness_index,
            binding_index=binding_index,
        )
        family = str(pattern.get("organ_family") or "missing")
        bucket = grouped.setdefault(
            family,
            {
                "cluster_id": family,
                "count": 0,
                "top_ids": [],
                "_novelty": [],
                "_risk": [],
                "_status": [],
                "_binding_overlay_status": [],
                "_route_readiness_status": [],
                "_substrate_binding_status": [],
                "_route_to_organ_ids": [],
            },
        )
        bucket["count"] += 1
        if len(bucket["top_ids"]) < 4:
            bucket["top_ids"].append(entry["pattern_id"])
        bucket["_novelty"].append(pattern.get("novelty_band") or "unknown")
        bucket["_risk"].append(pattern.get("private_state_risk") or "unknown")
        bucket["_status"].append(pattern.get("current_microcosm_status") or "unknown")
        bucket["_binding_overlay_status"].append(binding_overlay["status"])
        bucket["_route_readiness_status"].append(binding_overlay["route_readiness_status"])
        bucket["_substrate_binding_status"].append(binding_overlay["substrate_binding_status"])
        bucket["_route_to_organ_ids"].extend(binding_overlay["route_to_organ_ids"])

    rows = sorted(grouped.values(), key=lambda row: (-int(row.get("count") or 0), str(row.get("cluster_id") or "")))
    for row in rows:
        row["novelty_band_counts"] = _python_counter(row.pop("_novelty", []))
        row["private_state_risk_counts"] = _python_counter(row.pop("_risk", []))
        row["current_microcosm_status_counts"] = _python_counter(row.pop("_status", []))
        row["binding_overlay_status_counts"] = _python_counter(row.pop("_binding_overlay_status", []))
        row["route_readiness_status_counts"] = _python_counter(row.pop("_route_readiness_status", []))
        row["substrate_binding_status_counts"] = _python_counter(row.pop("_substrate_binding_status", []))
        route_to_organ_counts = _python_counter(row.pop("_route_to_organ_ids", []))
        row["top_route_to_organ_ids"] = [
            key
            for key, _count in sorted(
                route_to_organ_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:6]
        ]
        row["route_to_organ_id_counts"] = {
            key: route_to_organ_counts[key] for key in row["top_route_to_organ_ids"]
        }
        row["status_boundary"] = (
            "current_microcosm_status_counts is the raw extraction snapshot; "
            "binding_overlay_status_counts and route_readiness_status_counts are "
            "computed from the binding/readiness sidecars for routability."
        )
        row["claim"] = f"{row['cluster_id']}: {row['count']} macro-side distilled Microcosm patterns"
    return rows


def build_microcosm_extracted_patterns_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="microcosm_extracted_patterns",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    entries = _microcosm_extracted_pattern_entries(repo_root)
    by_id = {entry["pattern_id"]: entry for entry in entries}
    if ids:
        rows_source: list[dict[str, Any]] = []
        missing_ids: list[str] = []
        seen: set[str] = set()
        for item in ids:
            entry = by_id.get(item)
            if not entry:
                missing_ids.append(item)
                continue
            if entry["pattern_id"] in seen:
                continue
            seen.add(entry["pattern_id"])
            rows_source.append(entry)
    else:
        rows_source = entries
        missing_ids = []

    route_readiness_index = _microcosm_extracted_pattern_route_readiness_index(repo_root)
    binding_index = _microcosm_extracted_pattern_binding_index(repo_root)
    if band == "cluster_flag":
        rows = _microcosm_extracted_pattern_cluster_rows(
            rows_source,
            route_readiness_index=route_readiness_index,
            binding_index=binding_index,
        )
    elif band == "card":
        rows = [
            _microcosm_extracted_pattern_card_row(
                entry,
                repo_root=repo_root,
                route_readiness_index=route_readiness_index,
                binding_index=binding_index,
            )
            for entry in rows_source
        ]
    else:
        rows = [
            _microcosm_extracted_pattern_flag_row(
                entry,
                repo_root=repo_root,
                route_readiness_index=route_readiness_index,
                binding_index=binding_index,
            )
            for entry in rows_source
        ]

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "microcosm_extracted_patterns",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "macro_side_extraction_record_not_public_microcosm_authority",
        "governing_standard": {
            "ref": str(MICROCOSM_EXTRACTED_PATTERN_SUBSTRATE_STANDARD),
            "route_readiness_ref": str(MICROCOSM_EXTRACTED_PATTERN_ROUTE_STANDARD),
            "owned_bands": ["cluster_flag", "flag", "card"],
        },
        "theory_ref": str(MICROCOSM_SUBSTRATE_MODULE),
        "source_refs": [
            str(MICROCOSM_EXTRACTED_PATTERN_LEDGER),
            str(MICROCOSM_EXTRACTED_PATTERN_README),
            str(MICROCOSM_EXTRACTED_PATTERN_BINDINGS),
            str(MICROCOSM_EXTRACTED_PATTERN_WEAK_BINDINGS),
            str(MICROCOSM_EXTRACTED_PATTERN_READINESS_AUDIT),
            str(MICROCOSM_EXTRACTED_PATTERN_SUBSTRATE_STANDARD),
            str(MICROCOSM_EXTRACTED_PATTERN_ROUTE_STANDARD),
            str(MICROCOSM_SUBSTRATE_MODULE),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(entries),
            "query_used": False,
            "selection_method": (
                "artifact_kind_cluster_overview_from_microcosm_extracted_pattern_ledger"
                if band == "cluster_flag"
                else "artifact_kind_enumeration_from_microcosm_extracted_pattern_ledger"
            ),
            "drilldown_by": "organ_family" if band == "cluster_flag" else "pattern_id",
            "source_projection_reused": str(MICROCOSM_EXTRACTED_PATTERN_LEDGER),
            "grouping_keys": ["organ_family", "pattern_id"] if band == "cluster_flag" else [],
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "macro_side_only": True,
            "public_release_authority": False,
            "microcosm_leaf_projection_authority": False,
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "cluster_row_shape": (
                "compact_organ_family_counts_with_top_ids"
                if band == "cluster_flag"
                else "microcosm_extracted_pattern_rows"
            ),
        },
        "omission_receipt": {
            "omitted": [
                "pattern-level flag rows outside each cluster's top_ids",
                "full macro-private source bodies",
                "public release or leaf projection authorization",
                "full sidecar binding and readiness payloads",
            ],
            "reason": (
                "cluster_flag is the Microcosm extracted-pattern contents page. It groups the"
                " macro-side distilled pattern ledger by organ_family; flag/card rows require"
                " explicit pattern ids."
            ),
            "drilldown": (
                "./repo-python kernel.py --option-surface microcosm_extracted_patterns "
                "--band flag --ids <pattern_id>"
            ),
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface microcosm_extracted_patterns --band cluster_flag",
                "reason": "Browse organ-family clusters before expanding macro-side Microcosm pattern rows.",
            },
            {
                "command": "./repo-python kernel.py --option-surface microcosm_extracted_patterns --band flag --ids <pattern_id>[,<pattern_id>...]",
                "reason": "Browse explicit distilled Microcosm pattern rows by stable pattern_id.",
            },
            {
                "command": "./repo-python kernel.py --option-surface microcosm_extracted_patterns --band card --ids <pattern_id>",
                "reason": "Drill one pattern to load-bearing rationale, fixture proposal, bindings, and readiness checks.",
            },
        ],
        "warnings": [],
    }


def _annex_distillation_entries(repo_root: Path) -> list[dict[str, Any]]:
    annex_root = repo_root / ANNEX_ROOT
    entries: list[dict[str, Any]] = []
    for distillation_path in sorted(annex_root.glob("*/distillation.json")):
        try:
            data = json.loads(distillation_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        slug = str(data.get("slug") or distillation_path.parent.name).strip()
        patterns = data.get("patterns")
        if not slug or not isinstance(patterns, list):
            continue
        for pattern in patterns:
            if not isinstance(pattern, dict):
                continue
            pattern_id = str(pattern.get("id") or "").strip()
            if not pattern_id:
                continue
            entries.append(
                {
                    "annex_slug": slug,
                    "pattern_id": pattern_id,
                    "stable_id": f"{slug}:{pattern_id}",
                    "pattern": pattern,
                    "distillation": data,
                    "source_path": distillation_path,
                }
            )
    return entries


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _annex_distillation_evidence_command(entry: dict[str, Any], *, repo_root: Path) -> str:
    source_ref = _relative(entry["source_path"], repo_root)
    return f"jq --arg id '{entry['pattern_id']}' '.patterns[] | select(.id==$id)' '{source_ref}'"


def _annex_distillation_currentness(entry: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    pattern = entry["pattern"]
    distillation = entry["distillation"]
    return {
        "status": "distillation_json_available",
        "source_ref": _relative(entry["source_path"], repo_root),
        "source_mtime": _source_mtime(entry["source_path"]),
        "distillation_status": str(distillation.get("distillation_status") or ""),
        "last_distilled_at": str(distillation.get("last_distilled_at") or ""),
        "pattern_last_refreshed_at": str(pattern.get("last_refreshed_at") or ""),
        "pattern_added_at": str(pattern.get("added_at") or ""),
    }


def _annex_distillation_omission_receipt(
    entry: dict[str, Any], *, band: str, repo_root: Path
) -> dict[str, Any]:
    omitted = [
        "external source repository body",
        "full annex source tree",
        "full distillation.json sibling metadata outside selected pattern rows",
        "runtime proof that the local target still matches the extracted pattern",
    ]
    if band == "flag":
        omitted.append("card-level adoption_action, relevance_justification, and decision support detail")
    return {
        "omitted": omitted,
        "reason": (
            "The annex_distillation_patterns option surface is a read-only browse adapter over"
            " extracted adoption metadata in annex distillation rows. It exposes implementation"
            " decision fields without changing adoption status or landing a pattern."
        ),
        "drilldown": _annex_distillation_evidence_command(entry, repo_root=repo_root),
    }


def _annex_distillation_flag_row(entry: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    pattern = entry["pattern"]
    stable_id = entry["stable_id"]
    one_liner = _truncate_words(str(pattern.get("one_liner") or ""), max_chars=420)
    return {
        "row_id": f"annex_distillation_pattern:{stable_id}::flag",
        "artifact_kind": "annex_distillation_pattern",
        "band": "flag",
        "pattern_id": stable_id,
        "native_pattern_id": entry["pattern_id"],
        "annex_slug": entry["annex_slug"],
        "title": str(pattern.get("name") or entry["pattern_id"]),
        "claim": one_liner,
        "flag": one_liner,
        "one_liner": one_liner,
        "adoption_status": str(pattern.get("adoption_status") or ""),
        "authored_artifact": str(pattern.get("authored_artifact") or ""),
        "axis": str(pattern.get("axis") or ""),
        "adoption_lane": pattern.get("adoption_lane"),
        "source_locus": _string_list(pattern.get("source_locus")),
        "local_target": _string_list(pattern.get("local_target")),
        "profile_id": "annex_distillation_pattern_navigation_v0",
        "source_ref": _relative(entry["source_path"], repo_root),
        "drilldown_command": (
            f"./repo-python kernel.py --option-surface annex_distillation_patterns --band card --ids {stable_id}"
        ),
        "evidence_command": _annex_distillation_evidence_command(entry, repo_root=repo_root),
        "currentness": _annex_distillation_currentness(entry, repo_root=repo_root),
        "omission_receipt": _annex_distillation_omission_receipt(entry, band="flag", repo_root=repo_root),
    }


def _annex_distillation_card_row(entry: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    row = _annex_distillation_flag_row(entry, repo_root=repo_root)
    pattern = entry["pattern"]
    source_ref = _relative(entry["source_path"], repo_root)
    row.update(
        {
            "row_id": f"annex_distillation_pattern:{entry['stable_id']}::card",
            "band": "card",
            "adoption_action": str(pattern.get("adoption_action") or ""),
            "relevance": pattern.get("relevance"),
            "relevance_justification": _truncate_words(
                str(pattern.get("relevance_justification") or ""), max_chars=900
            ),
            "confidence": str(pattern.get("confidence") or ""),
            "added_at": str(pattern.get("added_at") or ""),
            "last_refreshed_at": str(pattern.get("last_refreshed_at") or ""),
            "available_pattern_fields": sorted(str(key) for key in pattern.keys()),
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "decision_support": {
                "implementation_decision_fields": [
                    "adoption_status",
                    "authored_artifact",
                    "adoption_action",
                    "source_locus",
                    "local_target",
                    "currentness",
                ],
                "status_interpretation": (
                    "proposed means inspect adoption_action and local_target before implementation;"
                    " non-empty authored_artifact is evidence of a landed or partially landed local translation."
                ),
            },
            "nearest_standard": {
                "ref": str(ANNEX_AUTHORITY_INDEX),
                "why": "The annex authority index governs annex distillation rows and adoption metadata.",
            },
            "nearest_paper_module": {
                "ref": "codex/doctrine/paper_modules/annex_distillation_layer.md",
                "why": "Names distillation rows as the pattern-level sibling of annex_notes.json.",
            },
            "evidence_commands": [
                _annex_distillation_evidence_command(entry, repo_root=repo_root),
                f"./repo-python kernel.py --annex-search {entry['annex_slug']}",
            ],
            "source_refs": [source_ref],
            "omission_receipt": _annex_distillation_omission_receipt(
                entry, band="card", repo_root=repo_root
            ),
        }
    )
    return row


def _annex_distillation_cluster_rows(
    entries: list[dict[str, Any]],
    *,
    repo_root: Path,
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for entry in sorted(entries, key=lambda item: str(item.get("stable_id") or "")):
        slug = str(entry.get("annex_slug") or "missing")
        pattern = entry["pattern"]
        bucket = grouped.setdefault(
            slug,
            {
                "cluster_id": slug,
                "count": 0,
                "authored_artifact_count": 0,
                "top_ids": [],
                "_status": [],
            },
        )
        stable_id = str(entry.get("stable_id") or "")
        bucket["count"] += 1
        if str(pattern.get("authored_artifact") or "").strip():
            bucket["authored_artifact_count"] += 1
        if stable_id and len(bucket["top_ids"]) < 3:
            bucket["top_ids"].append(stable_id)
        bucket["_status"].append(pattern.get("adoption_status") or "unknown")

    rows = sorted(grouped.values(), key=lambda row: (-int(row.get("count") or 0), str(row.get("cluster_id") or "")))
    for row in rows:
        top_ids = [str(item) for item in row.get("top_ids") or []]
        row["adoption_status_counts"] = _python_counter(row.pop("_status", []))
        row["claim"] = f"{row['cluster_id']}: {row['count']} extracted patterns"
    return rows


def build_annex_distillation_patterns_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="annex_distillation_patterns",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    entries = _annex_distillation_entries(repo_root)
    by_id = {entry["stable_id"]: entry for entry in entries}
    if ids:
        rows_source: list[dict[str, Any]] = []
        missing_ids: list[str] = []
        seen: set[str] = set()
        for item in ids:
            entry = by_id.get(item)
            if not entry:
                missing_ids.append(item)
                continue
            if entry["stable_id"] in seen:
                continue
            seen.add(entry["stable_id"])
            rows_source.append(entry)
    else:
        rows_source = entries
        missing_ids = []

    if band == "cluster_flag":
        rows = _annex_distillation_cluster_rows(rows_source, repo_root=repo_root)
    elif band == "card":
        rows = [_annex_distillation_card_row(entry, repo_root=repo_root) for entry in rows_source]
    else:
        rows = [_annex_distillation_flag_row(entry, repo_root=repo_root) for entry in rows_source]

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "annex_distillation_patterns",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "local_annex_distillation_metadata_not_adoption_authority",
        "governing_standard": {
            "ref": str(ANNEX_AUTHORITY_INDEX),
            "owned_bands": ["cluster_flag", "flag", "card"],
        },
        "theory_ref": "codex/doctrine/paper_modules/annex_distillation_layer.md",
        "source_refs": [str(ANNEX_ROOT), str(ANNEX_AUTHORITY_INDEX)],
        "summary": {
            "row_count": len(rows),
            "total_available": len(entries),
            "query_used": False,
            "selection_method": (
                "artifact_kind_cluster_overview_from_annex_distillation_json"
                if band == "cluster_flag"
                else "artifact_kind_enumeration_from_annex_distillation_json"
            ),
            "drilldown_by": "annex_slug" if band == "cluster_flag" else "pattern_id",
            "source_projection_reused": str(ANNEX_ROOT),
            "grouping_keys": ["annex_slug", "stable_id", "pattern_id"] if band == "cluster_flag" else [],
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "annex_repair_or_population_allowed": False,
            "adoption_status_mutation_allowed": False,
            "external_source_fetch_allowed": False,
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "cluster_row_shape": (
                "compact_annex_slug_counts_with_top_ids"
                if band == "cluster_flag"
                else "pattern_rows"
            ),
        },
        "omission_receipt": {
            "omitted": [
                "pattern-level flag rows outside each cluster's top_ids",
                "card-level adoption actions",
                "full distillation.json sibling metadata",
                "external source repository bodies",
            ],
            "reason": (
                "cluster_flag is the annex distillation contents page; row flags and cards require "
                "explicit stable ids from top_ids or a selected annex slug drilldown."
            ),
            "drilldown": "./repo-python kernel.py --option-surface annex_distillation_patterns --band flag --ids <slug>:<pNNN>",
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface annex_distillation_patterns --band cluster_flag",
                "reason": "Browse annex_slug clusters before expanding extracted pattern rows.",
            },
            {
                "command": "./repo-python kernel.py --option-surface annex_distillation_patterns --band flag --ids <slug>:<pNNN>[,<slug>:<pNNN>...]",
                "reason": "Browse explicit extracted annex adoption metadata rows by stable ids.",
            },
            {
                "command": "./repo-python kernel.py --option-surface annex_distillation_patterns --band card --ids <slug>:<pNNN>",
                "reason": "Drill one extracted pattern to adoption action, source locus, local target, and currentness.",
            },
        ],
        "warnings": [],
    }


def _python_file_load_index(repo_root: Path) -> dict[str, Any]:
    return _load_json(repo_root / PYTHON_SCOPE_INDEX)


def _python_runtime_usage_stats(repo_root: Path) -> Mapping[str, Any]:
    if _load_python_usage_stats is None:
        return {}
    return _load_python_usage_stats(repo_root)


def _python_runtime_usage_summary(stats: Mapping[str, Any]) -> dict[str, Any]:
    meta = stats.get("__meta") if isinstance(stats.get("__meta"), Mapping) else {}
    return {
        "source_ref": str(PYTHON_USAGE_STATS_REL),
        "schema_version": meta.get("schema_version"),
        "file_count": int(meta.get("file_count") or 0),
        "scope_count": int(meta.get("scope_count") or 0),
        "event_count": int(meta.get("event_count") or 0),
        "generated_at": meta.get("generated_at"),
        "status": "available" if int(meta.get("event_count") or 0) else "empty",
        "authority_posture": "runtime_observation_projection_not_source_authority",
    }


def _python_apply_file_usage(entries: list[dict[str, Any]], stats: Mapping[str, Any]) -> None:
    if _runtime_usage_for_file is None:
        return
    for entry in entries:
        entry["usage"] = _runtime_usage_for_file(stats, _python_file_id(entry))


def _python_apply_scope_usage(scopes: list[dict[str, Any]], stats: Mapping[str, Any]) -> None:
    if _runtime_usage_for_scope is None:
        return
    for scope in scopes:
        symbol_id = str(scope.get("symbol_id") or "").strip()
        scope["usage"] = _runtime_usage_for_scope(stats, symbol_id)


def _python_file_entries(index: dict[str, Any]) -> list[dict[str, Any]]:
    files = index.get("files")
    return [dict(entry) for entry in files if isinstance(entry, dict)] if isinstance(files, list) else []


def _python_file_scopes_by_path(index: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    scopes_by_path: dict[str, list[dict[str, Any]]] = {}
    scopes = index.get("scopes")
    if isinstance(scopes, list):
        for scope in scopes:
            if not isinstance(scope, dict):
                continue
            path = str(scope.get("path") or "").strip()
            if not path:
                continue
            scopes_by_path.setdefault(path, []).append(dict(scope))
    return scopes_by_path


def _python_file_id(entry: dict[str, Any]) -> str:
    return str(entry.get("path") or "").strip()


def _python_file_summary(entry: dict[str, Any]) -> str:
    return _collapse_ws(str(entry.get("summary") or ""))


def _python_file_browse_summary(entry: dict[str, Any]) -> str:
    return _collapse_ws(str(entry.get("browse_summary") or ""))


def _python_file_evidence_command(file_id: str) -> str:
    return f"./repo-python kernel.py --compile {file_id}"


def _python_file_index_evidence_command(file_id: str) -> str:
    return f"jq '.files[] | select(.path==\"{file_id}\")' codex/standards/std_python_scope_index.json"


def _python_file_currentness(index: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    meta = index.get("__meta") if isinstance(index.get("__meta"), dict) else {}
    return {
        "status": "python_scope_index_available",
        "source_ref": str(PYTHON_SCOPE_INDEX),
        "source_mtime": _source_mtime(repo_root / PYTHON_SCOPE_INDEX),
        "index_generated_at": meta.get("generated_at"),
        "schema_version": meta.get("schema_version"),
        "fidelity_level": meta.get("fidelity_level"),
        "file_count": meta.get("file_count"),
        "scope_count": meta.get("scope_count"),
    }


def _python_file_scope_summary(scopes: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"function": 0, "class": 0, "method": 0, "other": 0}
    for scope in scopes:
        kind = str(scope.get("scope_kind") or "").strip()
        if kind in summary:
            summary[kind] += 1
        else:
            summary["other"] += 1
    summary["total"] = len(scopes)
    return summary


def _python_file_top_scopes(scopes: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scope in scopes[:limit]:
        rows.append(
            {
                "name": str(scope.get("name") or ""),
                "scope_kind": str(scope.get("scope_kind") or ""),
                "line_start": scope.get("line_start"),
                "line_end": scope.get("line_end"),
                "owner_symbol_id": scope.get("owner_symbol_id"),
            }
        )
    return rows


def _python_file_omission_receipt(entry: dict[str, Any], *, band: str) -> dict[str, Any]:
    omitted = [
        "full Python source body",
        "all source spans and line-bounded body content",
        "full symbol-graph callers/callees and inbound dependents",
        "cross-file dependency closure",
        "python_scopes expansion (per-symbol cards live on the python_scopes adapter when it lands)",
    ]
    if band == "flag":
        omitted.append(
            "card-level public symbol ids, related paths, scope summary, and top-scope listing"
        )
    return {
        "omitted": omitted,
        "reason": (
            "The python_files option surface is a read-only catalog adapter over the existing"
            " std_python_scope_index.json projection. It selects file ids and bounded module"
            " metadata without compiling source or replacing the symbol graph."
        ),
        "drilldown": _python_file_evidence_command(_python_file_id(entry)),
    }


def _python_file_flag_row(
    entry: dict[str, Any],
    *,
    scopes_by_path: dict[str, list[dict[str, Any]]],
    currentness: dict[str, Any],
) -> dict[str, Any]:
    file_id = _python_file_id(entry)
    public_symbols = entry.get("public_symbol_ids") if isinstance(entry.get("public_symbol_ids"), list) else []
    related_paths = entry.get("related_paths") if isinstance(entry.get("related_paths"), list) else []
    scopes = scopes_by_path.get(file_id, [])
    return {
        "row_id": f"python_file:{file_id}::flag",
        "artifact_kind": "python_file",
        "band": "flag",
        "file_id": file_id,
        "path": file_id,
        "title": file_id,
        "claim": _truncate_words(_python_file_summary(entry) or _python_file_browse_summary(entry), max_chars=200),
        "flag": _truncate_words(_python_file_summary(entry) or _python_file_browse_summary(entry), max_chars=200),
        "teleology_intent_capsule": build_teleology_intent_capsule(
            purpose=_python_file_summary(entry) or _python_file_browse_summary(entry) or f"Represent Python file {file_id}.",
            original_intent=entry.get("when_needed") or entry.get("browse_summary") or entry.get("summary"),
            served_deliverable=(
                "File-level navigation row that lets agents understand purpose, scope, and related code before opening source."
            ),
            non_purpose=[
                "Not source authority; open the file or scope card before editing.",
                "Not a replacement for tests, symbol graph, or owner standards.",
            ],
            evidence_refs=[str(PYTHON_SCOPE_INDEX), str(PYTHON_STANDARD), file_id],
            freshness=f"index_generated_at:{currentness.get('index_generated_at') or ''}",
            owner_standard=str(PYTHON_STANDARD),
            source_confidence="generated_from_python_scope_index",
        ),
        "summary": _python_file_summary(entry),
        "complexity_hint": entry.get("complexity_hint"),
        "line_count": entry.get("line_count"),
        "group_id": entry.get("group_id"),
        "group_label": entry.get("group_label"),
        "navigation_group": entry.get("navigation_group"),
        "navigation_status": entry.get("navigation_status"),
        "status": entry.get("status"),
        "usage": _python_usage_record(entry.get("usage"), count_fields=["run_count", "function_call_count"]),
        "scope_count": len(scopes),
        "public_symbol_count": len(public_symbols),
        "related_paths_count": len(related_paths),
        "profile_id": PYTHON_FILE_PROFILE_ID,
        "source_ref": str(PYTHON_SCOPE_INDEX),
        "projection_refs": [str(PYTHON_SCOPE_INDEX), str(PYTHON_STANDARD)],
        "drilldown_command": (
            f"./repo-python kernel.py --option-surface python_files --band card --ids {file_id}"
        ),
        "evidence_command": _python_file_evidence_command(file_id),
        "currentness": currentness,
        "omission_receipt": _python_file_omission_receipt(entry, band="flag"),
    }


def _python_file_card_row(
    entry: dict[str, Any],
    *,
    scopes_by_path: dict[str, list[dict[str, Any]]],
    currentness: dict[str, Any],
) -> dict[str, Any]:
    row = _python_file_flag_row(entry, scopes_by_path=scopes_by_path, currentness=currentness)
    file_id = row["file_id"]
    scopes = scopes_by_path.get(file_id, [])
    public_symbols = entry.get("public_symbol_ids") if isinstance(entry.get("public_symbol_ids"), list) else []
    related_paths = entry.get("related_paths") if isinstance(entry.get("related_paths"), list) else []
    couples = entry.get("couples") if isinstance(entry.get("couples"), list) else []
    escalates_to = entry.get("escalates_to") if isinstance(entry.get("escalates_to"), list) else []
    quality_flags = entry.get("quality_flags") if isinstance(entry.get("quality_flags"), list) else []
    derivation_warnings = entry.get("derivation_warnings") if isinstance(entry.get("derivation_warnings"), list) else []
    row.update(
        {
            "row_id": f"python_file:{file_id}::card",
            "band": "card",
            "browse_summary": _python_file_browse_summary(entry),
            "when_needed": _collapse_ws(str(entry.get("when_needed") or "")),
            "public_symbol_ids": [str(item) for item in public_symbols],
            "related_paths": [
                {"edge": str(rp.get("edge") or ""), "path": str(rp.get("path") or "")}
                for rp in related_paths
                if isinstance(rp, dict)
            ],
            "couples": [str(item) for item in couples],
            "escalates_to": [str(item) for item in escalates_to],
            "quality_flags": [str(item) for item in quality_flags],
            "derivation_warnings": [str(item) for item in derivation_warnings],
            "scope_summary": _python_file_scope_summary(scopes),
            "top_scopes": _python_file_top_scopes(scopes),
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "native_python_facets": list(PYTHON_FILE_NATIVE_PROFILE_BANDS),
            "nearest_standard": {
                "ref": str(PYTHON_STANDARD),
                "why": "PYTHON_STANDARD declares the navigation_contract bands, scopes, and facets governing Python source compression.",
            },
            "nearest_index": {
                "ref": str(PYTHON_SCOPE_INDEX),
                "why": "std_python_scope_index.json is the projection-of-record for file/scope rowability.",
            },
            "evidence_commands": [
                _python_file_evidence_command(file_id),
                _python_file_index_evidence_command(file_id),
            ],
            "omission_receipt": _python_file_omission_receipt(entry, band="card"),
        }
    )
    return row


def _python_cluster_label(group_id: str, *, labels: dict[str, str] | None = None) -> str:
    if labels and labels.get(group_id):
        return str(labels[group_id])
    return group_id.replace("_", " ").replace(".", " ").title() if group_id else "Ungrouped"


def _python_group_id(value: Any) -> str:
    raw = str(value or "").strip().rstrip(".")
    return raw or "ungrouped"


def _python_counter(values: list[Any]) -> dict[str, int]:
    return {
        str(key): int(count)
        for key, count in sorted(Counter(str(value or "unknown") for value in values).items())
    }


def _python_usage_record(raw: Any, *, count_fields: list[str]) -> dict[str, Any]:
    payload = dict(raw) if isinstance(raw, dict) else {}
    counts = {field: int(payload.get(field) or 0) for field in count_fields}
    return {
        "status": "observed" if any(value > 0 for value in counts.values()) else "unobserved",
        **counts,
        "last_seen_at": payload.get("last_seen_at"),
        "source_ref": payload.get("source_ref") or "state/python_usage/python_usage_stats.json",
    }


def _python_usage_latest(left: Any, right: Any) -> str | None:
    left_s = str(left or "").strip()
    right_s = str(right or "").strip()
    if not left_s:
        return right_s or None
    if not right_s:
        return left_s
    return max(left_s, right_s)


def _python_file_cluster_rows(
    entries: list[dict[str, Any]],
    *,
    scopes_by_path: dict[str, list[dict[str, Any]]],
    currentness: dict[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for entry in sorted(entries, key=lambda item: _python_file_id(item)):
        group_id = _python_group_id(entry.get("group_id") or entry.get("navigation_group"))
        label = str(entry.get("group_label") or _python_cluster_label(group_id))
        bucket = grouped.setdefault(
            group_id,
            {
                "row_id": f"python_file_cluster:{group_id}::cluster_flag",
                "artifact_kind": "python_file_cluster",
                "band": "cluster_flag",
                "cluster_id": group_id,
                "group_id": group_id,
                "group_label": label,
                "count": 0,
                "file_count": 0,
                "scope_count": 0,
                "public_symbol_count": 0,
                "related_paths_count": 0,
                "top_ids": [],
                "_usage_run_count": 0,
                "_usage_function_call_count": 0,
                "_usage_observed_file_count": 0,
                "_usage_last_seen_at": None,
                "_complexity": [],
                "_status": [],
                "_navigation_status": [],
            },
        )
        file_id = _python_file_id(entry)
        scopes = scopes_by_path.get(file_id, [])
        public_symbols = entry.get("public_symbol_ids") if isinstance(entry.get("public_symbol_ids"), list) else []
        related_paths = entry.get("related_paths") if isinstance(entry.get("related_paths"), list) else []
        bucket["count"] += 1
        bucket["file_count"] += 1
        bucket["scope_count"] += len(scopes)
        bucket["public_symbol_count"] += len(public_symbols)
        bucket["related_paths_count"] += len(related_paths)
        usage = _python_usage_record(entry.get("usage"), count_fields=["run_count", "function_call_count"])
        bucket["_usage_run_count"] += int(usage.get("run_count") or 0)
        bucket["_usage_function_call_count"] += int(usage.get("function_call_count") or 0)
        if usage.get("status") == "observed":
            bucket["_usage_observed_file_count"] += 1
        bucket["_usage_last_seen_at"] = _python_usage_latest(
            bucket.get("_usage_last_seen_at"),
            usage.get("last_seen_at"),
        )
        bucket["_complexity"].append(entry.get("complexity_hint") or "unknown")
        bucket["_status"].append(entry.get("status") or "unknown")
        bucket["_navigation_status"].append(entry.get("navigation_status") or "unknown")
        if file_id and len(bucket["top_ids"]) < 6:
            bucket["top_ids"].append(file_id)

    rows = sorted(grouped.values(), key=lambda row: (-int(row.get("count") or 0), str(row.get("cluster_id") or "")))
    for row in rows:
        top_ids = [str(item) for item in row.get("top_ids") or []]
        ids = ",".join(top_ids)
        row["complexity_counts"] = _python_counter(row.pop("_complexity", []))
        row["status_counts"] = _python_counter(row.pop("_status", []))
        row["navigation_status_counts"] = _python_counter(row.pop("_navigation_status", []))
        observed_file_count = int(row.pop("_usage_observed_file_count", 0) or 0)
        run_count = int(row.pop("_usage_run_count", 0) or 0)
        function_call_count = int(row.pop("_usage_function_call_count", 0) or 0)
        row["usage"] = {
            "status": "observed" if observed_file_count else "unobserved",
            "observed_file_count": observed_file_count,
            "unobserved_file_count": max(0, int(row.get("file_count") or 0) - observed_file_count),
            "run_count": run_count,
            "function_call_count": function_call_count,
            "last_seen_at": row.pop("_usage_last_seen_at", None),
            "source_ref": "state/python_usage/python_usage_stats.json",
        }
        row["claim"] = _truncate_words(
            f"{row['group_label']}: {row['file_count']} Python files, {row['scope_count']} scopes. "
            f"Observed files: {observed_file_count}. Top files: {', '.join(top_ids[:4]) or '<none>'}.",
            max_chars=260,
        )
        row["grouping_keys"] = ["group_id", "group_label", "navigation_group"]
        row["drilldown_command"] = (
            f"./repo-python kernel.py --option-surface python_files --band flag --ids {ids}"
            if ids
            else "./repo-python kernel.py --option-surface python_files --band flag --ids <path>"
        )
        row["source_ref"] = str(PYTHON_SCOPE_INDEX)
        row["omission_receipt"] = {
            "omitted": [
                "file-level flag rows",
                "card fields",
                "source bodies",
                "symbol graph closure",
            ],
            "reason": "cluster_flag keeps Python files group-browsable; row flags require explicit ids.",
            "drilldown": row["drilldown_command"],
        }
    return rows


def build_python_files_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="python_files",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    index_path = repo_root / PYTHON_SCOPE_INDEX
    if not index_path.exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="python_files",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The Python scope index projection is missing.",
                "refs": [_relative(index_path, repo_root)],
            }
        )
        return payload

    index = _python_file_load_index(repo_root)
    entries = _python_file_entries(index)
    scopes_by_path = _python_file_scopes_by_path(index)
    usage_stats = _python_runtime_usage_stats(repo_root)
    _python_apply_file_usage(entries, usage_stats)
    for scope_rows in scopes_by_path.values():
        _python_apply_scope_usage(scope_rows, usage_stats)
    by_id: dict[str, dict[str, Any]] = {}
    for entry in entries:
        by_id.setdefault(_python_file_id(entry), entry)

    if ids:
        rows_source: list[dict[str, Any]] = []
        missing_ids: list[str] = []
        seen: set[str] = set()
        for item in ids:
            entry = by_id.get(item)
            if not entry:
                missing_ids.append(item)
                continue
            file_id = _python_file_id(entry)
            if file_id in seen:
                continue
            seen.add(file_id)
            rows_source.append(entry)
    else:
        rows_source = entries
        missing_ids = []

    requested_band = band
    band_redirect: dict[str, Any] | None = None
    if band == "card" and not ids:
        band = "cluster_flag"
        band_redirect = {
            "from": "card",
            "to": "cluster_flag",
            "reason": (
                "python_files all-card is a high-cardinality Python file expansion; "
                "row-level cards require explicit --ids."
            ),
            "explicit_row_card_command": "./repo-python kernel.py --option-surface python_files --band card --ids <path>",
        }

    currentness = _python_file_currentness(index, repo_root=repo_root)
    if band == "cluster_flag":
        rows = _python_file_cluster_rows(rows_source, scopes_by_path=scopes_by_path, currentness=currentness)
    elif band == "card":
        rows = [
            _python_file_card_row(entry, scopes_by_path=scopes_by_path, currentness=currentness)
            for entry in rows_source
        ]
    else:
        rows = [
            _python_file_flag_row(entry, scopes_by_path=scopes_by_path, currentness=currentness)
            for entry in rows_source
        ]

    payload = {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "python_files",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "browse_index_projection_not_source_authority",
        "governing_standard": {
            "ref": str(PYTHON_STANDARD),
            "profile_ref": PYTHON_FILE_PROFILE_ID,
            "owned_bands": ["cluster_flag", "flag", "card"],
            "native_profile_bands_are_data_not_adapter_support": True,
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "skill_refs": [str(PROFILE_SKILL)],
        "source_refs": [
            str(PYTHON_SCOPE_INDEX),
            str(PYTHON_STANDARD),
            str(NAVIGATION_THEORY),
            str(PROFILE_SKILL),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(entries),
            "query_used": False,
            "selection_method": (
                "artifact_kind_cluster_overview_from_python_scope_index"
                if band == "cluster_flag"
                else "artifact_kind_enumeration_from_python_scope_index"
            ),
            "drilldown_by": "group_id" if band == "cluster_flag" else "file_id",
            "source_projection_reused": str(PYTHON_SCOPE_INDEX),
            "runtime_usage_projection": _python_runtime_usage_summary(usage_stats),
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "native_profile_bands": list(PYTHON_FILE_NATIVE_PROFILE_BANDS),
            "native_profile_bands_are_data_not_adapter_support": True,
            "source_projection_reused": str(PYTHON_SCOPE_INDEX),
            "python_scope_index_rebuild_allowed": False,
            "python_source_mutation_allowed": False,
            "python_scopes_expansion_in_this_adapter": False,
            "cluster_first_for_high_cardinality": band == "cluster_flag",
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface python_files --band cluster_flag",
                "reason": "Browse Python file clusters before expanding row-level flags.",
            },
            {
                "command": "./repo-python kernel.py --option-surface python_files --band flag --ids <path1>,<path2>",
                "reason": "Expand selected file rows from the existing scope index before opening source.",
            },
            {
                "command": "./repo-python kernel.py --option-surface python_files --band card --ids <path>",
                "reason": "Drill one file to scope summary, top scopes, related paths, evidence commands, and omission receipt.",
            },
            {
                "command": "./repo-python kernel.py --compile <path>",
                "reason": "Use the compile command for file-level source/relationship evidence after selecting a row.",
            },
        ],
        "warnings": [],
    }
    if band_redirect is not None:
        payload["requested_band"] = requested_band
        payload["band_redirect"] = band_redirect
        payload["warnings"].append(
            {
                "kind": "high_cardinality_card_redirect",
                "message": "Rendered cluster_flag instead of all Python file cards.",
            }
        )
    return payload


def _python_scope_entries(index: dict[str, Any]) -> list[dict[str, Any]]:
    scopes = index.get("scopes")
    if not isinstance(scopes, list):
        return []
    return [dict(scope) for scope in scopes if isinstance(scope, dict)]


def _python_scope_id_for(scope: dict[str, Any], *, symbol_id_counts: dict[str, int]) -> str:
    symbol_id = str(scope.get("symbol_id") or "").strip()
    if not symbol_id:
        path = str(scope.get("path") or "").strip()
        name = str(scope.get("name") or "").strip()
        line_start = scope.get("line_start")
        return f"{path}::{name}@L{line_start}"
    if symbol_id_counts.get(symbol_id, 0) > 1:
        line_start = scope.get("line_start")
        return f"{symbol_id}@L{line_start}"
    return symbol_id


def _python_scope_evidence_command(scope: dict[str, Any], *, scope_id: str) -> str:
    symbol_id = str(scope.get("symbol_id") or "").strip()
    if scope_id != symbol_id and symbol_id:
        line_start = scope.get("line_start")
        return (
            f"jq --arg sid '{symbol_id}' --argjson ls {line_start} "
            "'.scopes[] | select(.symbol_id==$sid and .line_start==$ls)' "
            "codex/standards/std_python_scope_index.json"
        )
    target = symbol_id or scope_id
    return (
        f"jq --arg sid '{target}' "
        "'.scopes[] | select(.symbol_id==$sid)' "
        "codex/standards/std_python_scope_index.json"
    )


def _python_scope_currentness(index: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    meta = index.get("__meta") if isinstance(index.get("__meta"), dict) else {}
    return {
        "status": "python_scope_index_available",
        "source_ref": str(PYTHON_SCOPE_INDEX),
        "source_mtime": _source_mtime(repo_root / PYTHON_SCOPE_INDEX),
        "index_generated_at": meta.get("generated_at"),
        "schema_version": meta.get("schema_version"),
        "fidelity_level": meta.get("fidelity_level"),
        "file_count": meta.get("file_count"),
        "scope_count": meta.get("scope_count"),
    }


def _python_scope_omission_receipt(scope: dict[str, Any], *, band: str, evidence_command: str) -> dict[str, Any]:
    omitted = [
        "full Python source body",
        "all source spans and line-bounded body content",
        "complete callers/callees graph closure",
        "cross-file dependency closure",
        "native module_docs/file_card/symbol_capsule/graph_context/source_span bands are profile data, not option-surface adapter support",
    ]
    if band == "flag":
        omitted.append(
            "card-level related_symbols, callee_refs, inbound_dependents, couples, escalates_to, signature, when_needed"
        )
    return {
        "omitted": omitted,
        "reason": (
            "The python_scopes option surface is a read-only catalog adapter over the existing"
            " std_python_scope_index.json projection. It selects scope rows by symbol_id without"
            " compiling source or expanding the call graph."
        ),
        "drilldown": evidence_command,
    }


def _python_scope_flag_row(
    scope: dict[str, Any],
    *,
    scope_id: str,
    currentness: dict[str, Any],
) -> dict[str, Any]:
    related = scope.get("related_symbols") if isinstance(scope.get("related_symbols"), list) else []
    callee_refs = scope.get("callee_refs") if isinstance(scope.get("callee_refs"), list) else []
    inbound = scope.get("inbound_dependents") if isinstance(scope.get("inbound_dependents"), list) else []
    path = str(scope.get("path") or "").strip()
    name = str(scope.get("name") or "").strip()
    summary = _truncate_words(_collapse_ws(str(scope.get("summary") or "")), max_chars=200)
    evidence_command = _python_scope_evidence_command(scope, scope_id=scope_id)
    return {
        "row_id": f"python_scope:{scope_id}::flag",
        "artifact_kind": "python_scope",
        "band": "flag",
        "scope_id": scope_id,
        "symbol_id": str(scope.get("symbol_id") or ""),
        "path": path,
        "name": name,
        "scope_kind": str(scope.get("scope_kind") or ""),
        "owner_symbol_id": scope.get("owner_symbol_id"),
        "line_start": scope.get("line_start"),
        "line_end": scope.get("line_end"),
        "title": scope.get("symbol_id") or f"{path}::{name}",
        "claim": summary,
        "flag": summary,
        "summary": _collapse_ws(str(scope.get("summary") or "")),
        "group_id": scope.get("group_id"),
        "navigation_group": scope.get("navigation_group"),
        "status": scope.get("status"),
        "usage": _python_usage_record(scope.get("usage"), count_fields=["call_count"]),
        "related_symbol_count": len(related),
        "callee_count": len(callee_refs),
        "inbound_dependents_count": len(inbound),
        "profile_id": PYTHON_SCOPE_PROFILE_ID,
        "source_ref": str(PYTHON_SCOPE_INDEX),
        "projection_refs": [str(PYTHON_SCOPE_INDEX), str(PYTHON_STANDARD)],
        "drilldown_command": (
            f"./repo-python kernel.py --option-surface python_scopes --band card --ids {scope_id}"
        ),
        "evidence_command": evidence_command,
        "currentness": currentness,
        "omission_receipt": _python_scope_omission_receipt(
            scope, band="flag", evidence_command=evidence_command
        ),
    }


def _python_scope_card_row(
    scope: dict[str, Any],
    *,
    scope_id: str,
    currentness: dict[str, Any],
) -> dict[str, Any]:
    row = _python_scope_flag_row(scope, scope_id=scope_id, currentness=currentness)
    path = row["path"]
    related = scope.get("related_symbols") if isinstance(scope.get("related_symbols"), list) else []
    callee_refs = scope.get("callee_refs") if isinstance(scope.get("callee_refs"), list) else []
    inbound = scope.get("inbound_dependents") if isinstance(scope.get("inbound_dependents"), list) else []
    couples = scope.get("couples") if isinstance(scope.get("couples"), list) else []
    escalates_to = scope.get("escalates_to") if isinstance(scope.get("escalates_to"), list) else []
    quality_flags = scope.get("quality_flags") if isinstance(scope.get("quality_flags"), list) else []
    issues = scope.get("issues") if isinstance(scope.get("issues"), list) else []
    evidence_command = row["evidence_command"]
    parent_file_command = (
        f"./repo-python kernel.py --option-surface python_files --band card --ids {path}"
    )
    row.update(
        {
            "row_id": f"python_scope:{scope_id}::card",
            "band": "card",
            "signature": str(scope.get("signature") or ""),
            "when_needed": _collapse_ws(str(scope.get("when_needed") or "")),
            "related_symbols": [str(item) for item in related],
            "callee_refs": [str(item) for item in callee_refs],
            "inbound_dependents": [str(item) for item in inbound],
            "couples": [str(item) for item in couples],
            "escalates_to": [str(item) for item in escalates_to],
            "quality_flags": [str(item) for item in quality_flags],
            "issues": [str(item) for item in issues],
            "source_span": {
                "path": path,
                "line_start": scope.get("line_start"),
                "line_end": scope.get("line_end"),
            },
            "parent_file_command": parent_file_command,
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "native_python_facets": list(PYTHON_SCOPE_NATIVE_PROFILE_BANDS),
            "native_python_scopes": list(PYTHON_SCOPE_NATIVE_PROFILE_SCOPES),
            "native_python_facets_detail": list(PYTHON_SCOPE_NATIVE_PROFILE_FACETS),
            "nearest_standard": {
                "ref": str(PYTHON_STANDARD),
                "why": "PYTHON_STANDARD declares the navigation_contract bands, scopes, and facets governing Python scope compression.",
            },
            "nearest_index": {
                "ref": str(PYTHON_SCOPE_INDEX),
                "why": "std_python_scope_index.json is the projection-of-record for file/scope rowability.",
            },
            "evidence_commands": [
                evidence_command,
                f"./repo-python kernel.py --compile {path}",
                parent_file_command,
            ],
            "omission_receipt": _python_scope_omission_receipt(
                scope, band="card", evidence_command=evidence_command
            ),
        }
    )
    return row


def _python_scope_cluster_rows(
    scopes_with_ids: list[tuple[str, dict[str, Any]]],
    *,
    currentness: dict[str, Any],
    group_labels: dict[str, str],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    path_sets: dict[str, set[str]] = {}
    for scope_id, scope in sorted(scopes_with_ids, key=lambda item: item[0]):
        group_id = _python_group_id(scope.get("group_id") or scope.get("navigation_group"))
        scope_kind = str(scope.get("scope_kind") or "other").strip() or "other"
        cluster_id = group_id
        label = _python_cluster_label(group_id, labels=group_labels)
        bucket = grouped.setdefault(
            cluster_id,
            {
                "row_id": f"python_scope_cluster:{cluster_id}::cluster_flag",
                "artifact_kind": "python_scope_cluster",
                "band": "cluster_flag",
                "cluster_id": cluster_id,
                "group_id": group_id,
                "group_label": _python_cluster_label(group_id, labels=group_labels),
                "label": label,
                "count": 0,
                "scope_count": 0,
                "file_count": 0,
                "top_ids": [],
                "top_paths": [],
                "_usage_call_count": 0,
                "_usage_observed_scope_count": 0,
                "_usage_last_seen_at": None,
                "callee_count": 0,
                "inbound_dependents_count": 0,
                "_status": [],
                "_scope_kind": [],
            },
        )
        path = str(scope.get("path") or "").strip()
        callee_refs = scope.get("callee_refs") if isinstance(scope.get("callee_refs"), list) else []
        inbound = scope.get("inbound_dependents") if isinstance(scope.get("inbound_dependents"), list) else []
        path_set = path_sets.setdefault(cluster_id, set())
        if path:
            path_set.add(path)
        bucket["count"] += 1
        bucket["scope_count"] += 1
        bucket["callee_count"] += len(callee_refs)
        bucket["inbound_dependents_count"] += len(inbound)
        usage = _python_usage_record(scope.get("usage"), count_fields=["call_count"])
        bucket["_usage_call_count"] += int(usage.get("call_count") or 0)
        if usage.get("status") == "observed":
            bucket["_usage_observed_scope_count"] += 1
        bucket["_usage_last_seen_at"] = _python_usage_latest(
            bucket.get("_usage_last_seen_at"),
            usage.get("last_seen_at"),
        )
        bucket["_status"].append(scope.get("status") or "unknown")
        bucket["_scope_kind"].append(scope_kind)
        if scope_id and len(bucket["top_ids"]) < 3:
            bucket["top_ids"].append(scope_id)
        if path and path not in bucket["top_paths"] and len(bucket["top_paths"]) < 3:
            bucket["top_paths"].append(path)

    rows = sorted(grouped.values(), key=lambda row: (-int(row.get("count") or 0), str(row.get("cluster_id") or "")))
    for row in rows:
        cluster_id = str(row.get("cluster_id") or "")
        top_ids = [str(item) for item in row.get("top_ids") or []]
        ids = ",".join(top_ids)
        top_ids_total = int(row.get("scope_count") or 0)
        row["top_ids_total"] = top_ids_total
        row["top_ids_omitted"] = max(0, top_ids_total - len(top_ids))
        row["file_count"] = len(path_sets.get(cluster_id, set()))
        row["status_counts"] = _python_counter(row.pop("_status", []))
        row["scope_kind_counts"] = _python_counter(row.pop("_scope_kind", []))
        observed_scope_count = int(row.pop("_usage_observed_scope_count", 0) or 0)
        call_count = int(row.pop("_usage_call_count", 0) or 0)
        row["usage"] = {
            "status": "observed" if observed_scope_count else "unobserved",
            "observed_scope_count": observed_scope_count,
            "unobserved_scope_count": max(0, int(row.get("scope_count") or 0) - observed_scope_count),
            "call_count": call_count,
            "last_seen_at": row.pop("_usage_last_seen_at", None),
            "source_ref": "state/python_usage/python_usage_stats.json",
        }
        kind_bits = ", ".join(f"{key}={value}" for key, value in row["scope_kind_counts"].items())
        row["claim"] = _truncate_words(
            f"{row['label']}: {row['scope_count']} scopes across {row['file_count']} files. "
            f"Kinds: {kind_bits or 'unknown'}. Observed scopes: {observed_scope_count}. "
            f"Top scopes: {', '.join(top_ids[:2]) or '<none>'}.",
            max_chars=280,
        )
        row["grouping_keys"] = ["group_id", "scope_kind", "path", "owner_symbol_id"]
        row["cluster_drilldown_command"] = (
            f"./repo-python kernel.py --option-surface python_scopes --band cluster_flag --ids {cluster_id}"
        )
        row["drilldown_command"] = (
            f"./repo-python kernel.py --option-surface python_scopes --band flag --ids {ids}"
            if ids
            else "./repo-python kernel.py --option-surface python_scopes --band flag --ids <symbol_id>"
        )
        row["source_ref"] = str(PYTHON_SCOPE_INDEX)
        row["omission_receipt"] = {
            "omitted": [
                "scope-level flag rows",
                f"{row['top_ids_omitted']} scope ids beyond the preview top_ids",
                "signature/source-span detail",
                "call graph closure",
                "source bodies",
            ],
            "reason": "cluster_flag keeps Python scopes group-browsable; row flags require explicit ids.",
            "drilldown": row["cluster_drilldown_command"],
            "sample_scope_drilldown": row["drilldown_command"],
        }
    return rows


def build_python_scopes_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="python_scopes",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    index_path = repo_root / PYTHON_SCOPE_INDEX
    if not index_path.exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="python_scopes",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The Python scope index projection is missing.",
                "refs": [_relative(index_path, repo_root)],
            }
        )
        return payload

    index = _load_json(index_path)
    scopes = _python_scope_entries(index)
    file_entries = _python_file_entries(index)
    usage_stats = _python_runtime_usage_stats(repo_root)
    _python_apply_scope_usage(scopes, usage_stats)
    _python_apply_file_usage(file_entries, usage_stats)
    group_labels = {
        _python_group_id(entry.get("group_id") or entry.get("navigation_group")): str(
            entry.get("group_label") or ""
        )
        for entry in file_entries
        if entry.get("group_id") or entry.get("navigation_group")
    }

    symbol_id_counts: dict[str, int] = {}
    for scope in scopes:
        symbol_id = str(scope.get("symbol_id") or "").strip()
        if symbol_id:
            symbol_id_counts[symbol_id] = symbol_id_counts.get(symbol_id, 0) + 1

    by_id: dict[str, dict[str, Any]] = {}
    scope_ids: list[str] = []
    for scope in scopes:
        scope_id = _python_scope_id_for(scope, symbol_id_counts=symbol_id_counts)
        scope_ids.append(scope_id)
        by_id.setdefault(scope_id, scope)

    if band == "cluster_flag":
        rows_source = list(zip(scope_ids, scopes))
        missing_ids = []
    elif ids:
        rows_source: list[tuple[str, dict[str, Any]]] = []
        missing_ids: list[str] = []
        seen: set[str] = set()
        for item in ids:
            scope = by_id.get(item)
            if not scope:
                missing_ids.append(item)
                continue
            if item in seen:
                continue
            seen.add(item)
            rows_source.append((item, scope))
    else:
        rows_source = list(zip(scope_ids, scopes))
        missing_ids = []

    currentness = _python_scope_currentness(index, repo_root=repo_root)
    if band == "cluster_flag":
        rows = _python_scope_cluster_rows(
            rows_source,
            currentness=currentness,
            group_labels=group_labels,
        )
        if ids:
            by_cluster_handle: dict[str, dict[str, Any]] = {}
            for row in rows:
                for handle in (row.get("cluster_id"), row.get("group_id"), row.get("row_id")):
                    if handle:
                        by_cluster_handle[str(handle)] = row
            selected_rows: list[dict[str, Any]] = []
            seen_cluster_ids: set[str] = set()
            missing_ids = []
            for item in ids:
                row = by_cluster_handle.get(item)
                if not row:
                    missing_ids.append(item)
                    continue
                cluster_id = str(row.get("cluster_id") or item)
                if cluster_id in seen_cluster_ids:
                    continue
                seen_cluster_ids.add(cluster_id)
                selected_rows.append(row)
            rows = selected_rows
    elif band == "card":
        rows = [
            _python_scope_card_row(scope, scope_id=scope_id, currentness=currentness)
            for scope_id, scope in rows_source
        ]
    else:
        rows = [
            _python_scope_flag_row(scope, scope_id=scope_id, currentness=currentness)
            for scope_id, scope in rows_source
        ]

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "python_scopes",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "browse_index_projection_not_source_authority",
        "governing_standard": {
            "ref": str(PYTHON_STANDARD),
            "profile_ref": PYTHON_SCOPE_PROFILE_ID,
            "owned_bands": ["cluster_flag", "flag", "card"],
            "native_profile_bands_are_data_not_adapter_support": True,
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "skill_refs": [str(PROFILE_SKILL)],
        "source_refs": [
            str(PYTHON_SCOPE_INDEX),
            str(PYTHON_STANDARD),
            str(NAVIGATION_THEORY),
            str(PROFILE_SKILL),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(scopes),
            "query_used": False,
            "selection_method": (
                "artifact_kind_cluster_overview_from_python_scope_index"
                if band == "cluster_flag"
                else "artifact_kind_enumeration_from_python_scope_index"
            ),
            "drilldown_by": "group_id" if band == "cluster_flag" else "scope_id",
            "scope_id_strategy": "symbol_id_when_unique_else_symbol_id_with_line_start_suffix",
            "symbol_id_collision_count": sum(1 for c in symbol_id_counts.values() if c > 1),
            "source_projection_reused": str(PYTHON_SCOPE_INDEX),
            "runtime_usage_projection": _python_runtime_usage_summary(usage_stats),
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "native_profile_bands": list(PYTHON_SCOPE_NATIVE_PROFILE_BANDS),
            "native_profile_bands_are_data_not_adapter_support": True,
            "source_projection_reused": str(PYTHON_SCOPE_INDEX),
            "python_scope_index_rebuild_allowed": False,
            "python_source_mutation_allowed": False,
            "python_scope_callgraph_closure_in_this_adapter": False,
            "cluster_first_for_high_cardinality": band == "cluster_flag",
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface python_scopes --band cluster_flag",
                "reason": "Browse Python scope clusters before expanding row-level flags.",
            },
            {
                "command": "./repo-python kernel.py --option-surface python_scopes --band flag --ids <symbol_id>",
                "reason": "Expand selected scope rows from the existing scope index before opening source.",
            },
            {
                "command": "./repo-python kernel.py --option-surface python_scopes --band card --ids <symbol_id>",
                "reason": "Drill one scope to signature, related symbols, callees, inbound dependents, source span, evidence commands, and omission receipt.",
            },
            {
                "command": "./repo-python kernel.py --option-surface python_files --band card --ids <path>",
                "reason": "Climb from a scope row to its parent file card.",
            },
            {
                "command": "./repo-python kernel.py --compile <path>",
                "reason": "Use the compile command for file-level source/relationship evidence after selecting a row.",
            },
        ],
        "warnings": [],
    }


def _load_skill_registry(repo_root: Path) -> dict[str, Any]:
    path = repo_root / SKILL_REGISTRY
    if not path.exists():
        return {}
    return _load_json(path)


def _skill_entries(registry: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    families = registry.get("families") if isinstance(registry.get("families"), list) else []
    for family_order, family in enumerate(families):
        if not isinstance(family, dict):
            continue
        family_id = str(family.get("family_id") or "").strip()
        family_title = str(family.get("title") or family_id).strip()
        skills = family.get("skills") if isinstance(family.get("skills"), list) else []
        for skill_order, skill in enumerate(skills):
            if not isinstance(skill, dict):
                continue
            skill_id = str(skill.get("id") or "").strip()
            if not skill_id:
                continue
            entries.append(
                {
                    "family_id": family_id,
                    "family_title": family_title,
                    "family_description": str(family.get("description") or ""),
                    "family_order": family_order,
                    "skill_order": skill_order,
                    "skill": skill,
                }
            )
    return entries


def _skill_id(skill: dict[str, Any]) -> str:
    return str(skill.get("id") or "").strip()


def _skill_title(skill: dict[str, Any]) -> str:
    return str(skill.get("title") or _skill_id(skill)).strip()


def _skill_source_ref(skill: dict[str, Any]) -> str:
    return str(skill.get("file") or "").strip()


def _skill_description(skill: dict[str, Any]) -> str:
    return _collapse_ws(str(skill.get("description") or ""))


def _skill_holographic(skill: dict[str, Any]) -> dict[str, Any]:
    holographic = skill.get("holographic")
    return dict(holographic) if isinstance(holographic, dict) else {}


def _skill_agent_surface(skill: dict[str, Any]) -> dict[str, Any]:
    agent_surface = skill.get("agent_surface")
    return dict(agent_surface) if isinstance(agent_surface, dict) else {}


def _skill_compression_passport(skill: dict[str, Any]) -> dict[str, Any]:
    passport = skill.get("compression_passport")
    return dict(passport) if isinstance(passport, dict) else {}


def _doctrine_json_ref(repo_root: Path, directory: Path, ref_id: str) -> tuple[dict[str, Any], str]:
    exact = repo_root / directory / f"{ref_id}.json"
    if exact.exists():
        return _load_json(exact), _relative(exact, repo_root)
    matches = sorted((repo_root / directory).glob(f"{ref_id}_*.json"))
    if matches:
        return _load_json(matches[0]), _relative(matches[0], repo_root)
    return {}, ""


def _principle_by_id(repo_root: Path) -> dict[str, dict[str, Any]]:
    payload = _load_json(repo_root / RAW_SEED_PRINCIPLES)
    rows = payload.get("principles") if isinstance(payload.get("principles"), list) else []
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        principle_id = str(row.get("id") or "").strip()
        slug = str(row.get("slug") or "").strip()
        if principle_id:
            out[principle_id] = row
        if slug:
            out[slug] = row
    return out


def _doctrine_edge_affordance(
    repo_root: Path,
    *,
    skill_id: str,
    edge_kind: str,
    ref_id: str,
    principle_capsule_cache: dict[str, dict[str, Any]] | None = None,
    concepts_by_key: dict[str, dict[str, Any]] | None = None,
    mechanisms_by_key: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ref_id = str(ref_id or "").strip()
    base: dict[str, Any] = {
        "id": ref_id,
        "kind": edge_kind.removesuffix("s") if edge_kind.endswith("s") else edge_kind,
        "why_here": f"Referenced by {skill_id}.doctrine_edges.{edge_kind}.",
    }
    if not ref_id:
        return {**base, "missing_projection_reason": "blank doctrine edge id"}

    if edge_kind == "principles":
        capsule_cache_key = f"{skill_id}\0{ref_id}"
        if principle_capsule_cache is not None and capsule_cache_key in principle_capsule_cache:
            capsule = principle_capsule_cache[capsule_cache_key]
        else:
            capsule = resolve_principle_capsule(
                repo_root,
                ref_id,
                requested_band="statement",
                relation_role="doctrine_edges.principles",
                consumer_context={"surface": "skills.card", "skill_id": skill_id},
            )
            if principle_capsule_cache is not None:
                principle_capsule_cache[capsule_cache_key] = capsule
        if not capsule.get("resolved"):
            return {
                **base,
                "drilldown_command": f"./repo-python kernel.py --option-surface principles --band card --ids {ref_id}",
                "missing_projection_reason": "principle id did not resolve in raw_seed_principles.json",
                "projection_capsule": capsule,
            }
        return {
            **base,
            "label": str(capsule.get("title") or ref_id),
            "compression": _first_sentence(str(capsule.get("projection_text") or ""), max_chars=220),
            "source_ref": str(capsule.get("source_ref") or RAW_SEED_PRINCIPLES),
            "drilldown_command": str(capsule.get("drilldown_route") or f"./repo-python kernel.py --option-surface principles --band card --ids {ref_id}"),
            "evidence_command": str(capsule.get("evidence_route") or "./repo-python kernel.py --docs-route raw_seed_principles"),
            "projection_capsule": capsule,
        }

    if edge_kind == "concepts":
        concept = (
            concepts_by_key if concepts_by_key is not None else _concept_by_id(repo_root)
        ).get(ref_id)
        if not concept:
            return {
                **base,
                "drilldown_command": f"./repo-python kernel.py --option-surface concepts --band card --ids {ref_id}",
                "missing_projection_reason": "concept id did not resolve under codex/doctrine/concepts",
            }
        source_ref = str(concept.get("_source_ref") or "")
        return {
            **base,
            "label": str(concept.get("title") or concept.get("slug") or ref_id),
            "compression": _first_sentence(str(concept.get("statement") or ""), max_chars=220),
            "source_ref": source_ref,
            "drilldown_command": f"./repo-python kernel.py --option-surface concepts --band card --ids {ref_id}",
            "evidence_command": f"jq '.' {source_ref}" if source_ref else "",
        }

    if edge_kind == "mechanisms":
        mechanism = (
            mechanisms_by_key if mechanisms_by_key is not None else _mechanism_by_id(repo_root)
        ).get(ref_id)
        if not mechanism:
            return {
                **base,
                "drilldown_command": f"./repo-python kernel.py --option-surface mechanisms --band card --ids {ref_id}",
                "missing_projection_reason": "mechanism id did not resolve under codex/doctrine/mechanisms",
            }
        source_ref = str(mechanism.get("_source_ref") or "")
        return {
            **base,
            "label": str(mechanism.get("title") or mechanism.get("slug") or ref_id),
            "compression": _first_sentence(str(mechanism.get("statement") or ""), max_chars=220),
            "source_ref": source_ref,
            "drilldown_command": f"./repo-python kernel.py --option-surface mechanisms --band card --ids {ref_id}",
            "evidence_command": f"jq '.' {source_ref}",
        }

    return {
        **base,
        "missing_projection_reason": f"{edge_kind} doctrine edge projection is not registered.",
    }


def _skill_doctrine_edge_refs(
    skill: dict[str, Any],
    *,
    repo_root: Path,
    principle_capsule_cache: dict[str, dict[str, Any]] | None = None,
    concepts_by_key: dict[str, dict[str, Any]] | None = None,
    mechanisms_by_key: dict[str, dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    edges = skill.get("doctrine_edges")
    if not isinstance(edges, dict):
        return {}
    skill_id = _skill_id(skill)
    refs: dict[str, list[dict[str, Any]]] = {}
    for edge_kind, values in edges.items():
        if not isinstance(values, list):
            continue
        refs[str(edge_kind)] = [
            _doctrine_edge_affordance(
                repo_root,
                skill_id=skill_id,
                edge_kind=str(edge_kind),
                ref_id=str(value),
                principle_capsule_cache=principle_capsule_cache,
                concepts_by_key=concepts_by_key,
                mechanisms_by_key=mechanisms_by_key,
            )
            for value in values
        ]
    return refs


def _skill_cluster_keys(skill: dict[str, Any]) -> list[str]:
    passport = _skill_compression_passport(skill)
    keys = passport.get("cluster_keys") if isinstance(passport.get("cluster_keys"), list) else []
    return [str(key) for key in keys if str(key).strip()]


def _skill_atom(skill: dict[str, Any]) -> str:
    passport = _skill_compression_passport(skill)
    atom = str(passport.get("atom") or "").strip()
    if atom:
        return _truncate_words(atom, max_chars=80)
    holographic = _skill_holographic(skill)
    return _truncate_words(str(holographic.get("one_liner") or _skill_title(skill)), max_chars=80)


def _skill_flag(skill: dict[str, Any]) -> str:
    passport = _skill_compression_passport(skill)
    authored_flag = str(passport.get("flag") or "").strip()
    if authored_flag:
        return _truncate_words(authored_flag, max_chars=180)
    holographic = _skill_holographic(skill)
    agent_surface = _skill_agent_surface(skill)
    source = (
        _skill_description(skill)
        or str(holographic.get("one_liner") or "")
        or str(agent_surface.get("does") or "")
    )
    return _truncate_words(source, max_chars=280)


def _skill_currentness(entry: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    skill = entry["skill"]
    source_ref = _skill_source_ref(skill)
    source_path = repo_root / source_ref if source_ref else None
    return {
        "status": "registry_plus_file_mtime",
        "registry_ref": str(SKILL_REGISTRY),
        "registry_mtime": _source_mtime(repo_root / SKILL_REGISTRY),
        "source_ref": source_ref,
        "source_mtime": _source_mtime(source_path) if source_path else None,
        "source_exists": bool(source_path and source_path.exists()),
    }


def _skill_evidence_command(skill_id: str) -> str:
    return f"./repo-python kernel.py --row skills:{skill_id} --band card"


def _skill_debug_trace_command(skill_id: str) -> str:
    return f"./repo-python kernel.py --skill-find {skill_id} --debug"


def _skill_flag_row(entry: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    skill = entry["skill"]
    skill_id = _skill_id(skill)
    return {
        "row_id": f"skill:{skill_id}::flag",
        "artifact_kind": "skill",
        "band": "flag",
        "skill_id": skill_id,
        "title": _skill_title(skill),
        "atom": _skill_atom(skill),
        "cluster_keys": _skill_cluster_keys(skill),
        "claim": _skill_flag(skill),
        "flag": _skill_flag(skill),
        "family_id": entry["family_id"],
        "family_title": entry["family_title"],
        "skill_type": skill.get("skill_type"),
        "kind": skill.get("kind"),
        "status": skill.get("status"),
        "compression_source": "authored_compression_passport"
        if _skill_compression_passport(skill)
        else "legacy_inferred_fields",
        "source_ref": _skill_source_ref(skill),
        "registry_ref": str(SKILL_REGISTRY),
        "drilldown_command": f"./repo-python kernel.py --option-surface skills --band card --ids {skill_id}",
        "evidence_command": _skill_evidence_command(skill_id),
        "debug_trace_command": _skill_debug_trace_command(skill_id),
        "currentness": _skill_currentness(entry, repo_root=repo_root),
    }


def _skill_card_row(
    entry: dict[str, Any],
    *,
    repo_root: Path,
    doctrine_lookup_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    skill = entry["skill"]
    row = _skill_flag_row(entry, repo_root=repo_root)
    skill_id = row["skill_id"]
    agent_surface = _skill_agent_surface(skill)
    doctrine_context = doctrine_lookup_context or {}
    row.update(
        {
            "row_id": f"skill:{skill_id}::card",
            "band": "card",
            "description": _skill_description(skill),
            "summary": str(
                _skill_compression_passport(skill).get("card")
                or _skill_holographic(skill).get("one_liner")
                or _skill_description(skill)
            ),
            "compression_passport": _skill_compression_passport(skill),
            "triggers": [str(item) for item in list(skill.get("triggers") or [])],
            "entry": str(agent_surface.get("entry") or skill.get("entry") or ""),
            "focus_paths": [str(item) for item in list(skill.get("focus_paths") or [])],
            "doc_links": [str(item) for item in list(skill.get("doc_links") or [])],
            "doctrine_edges": dict(skill.get("doctrine_edges") or {}),
            "doctrine_edge_refs": _skill_doctrine_edge_refs(
                skill,
                repo_root=repo_root,
                principle_capsule_cache=doctrine_context.get("principle_capsule_cache"),
                concepts_by_key=doctrine_context.get("concepts_by_key"),
                mechanisms_by_key=doctrine_context.get("mechanisms_by_key"),
            ),
            "composes_with": [str(item) for item in list(skill.get("composes_with") or [])],
            "kernel_commands": [str(item) for item in list(skill.get("kernel_commands") or [])],
            "governing_principles": [
                str(item) for item in list(skill.get("governing_principles") or [])
            ],
            "outputs": [str(item) for item in list(skill.get("outputs") or [])],
            "anti_patterns": [str(item) for item in list(skill.get("anti_patterns") or [])],
            "agent_surface": agent_surface,
            "holographic": _skill_holographic(skill),
            "routing_priority": skill.get("routing_priority"),
            "native_bands": ["triggers", "card", "workflow", "evidence"],
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "nearest_standard": {
                "ref": str(SKILL_STANDARD),
                "why": "The skill standard owns reusable capability rows, trigger metadata, doctrine edges, workflow fields, and agent-surface contracts.",
            },
            "nearest_term": {
                "term_id": "skill",
                "ref": str(SYSTEM_TERM_REGISTRY_REL),
                "why": "The system vocabulary defines skill as an agent-operable procedure; capability is currently an alias on that row.",
            },
            "omission_receipt": {
                "omitted": [
                    "full skill markdown body",
                    "full workflow narrative beyond registry fields",
                    "transitive composes_with and doctrine-edge neighborhoods",
                    "generated Agent Skill surface bodies",
                ],
                "reason": "The card band selects and orients a capability; source authority remains in skill_registry.json plus the skill markdown file.",
                "drilldown": _skill_evidence_command(skill_id),
                "debug_trace": _skill_debug_trace_command(skill_id),
            },
        }
    )
    return row


def _compact_skill_doctrine_edge_refs_for_multi_card(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep multi-skill card drilldowns compact without dropping edge routes."""
    if len(rows) <= 1:
        return rows
    compacted_rows: list[dict[str, Any]] = []
    for row in rows:
        next_row = dict(row)
        edge_refs = next_row.get("doctrine_edge_refs")
        if isinstance(edge_refs, dict):
            compacted_edge_refs: dict[str, list[dict[str, Any]]] = {}
            omitted_capsule_count = 0
            for edge_kind, refs in edge_refs.items():
                if not isinstance(refs, list):
                    continue
                compacted_refs: list[dict[str, Any]] = []
                for ref in refs:
                    if not isinstance(ref, dict):
                        continue
                    compact_ref = dict(ref)
                    if "projection_capsule" in compact_ref:
                        compact_ref.pop("projection_capsule", None)
                        compact_ref["projection_capsule_omitted"] = True
                        omitted_capsule_count += 1
                    compacted_refs.append(compact_ref)
                compacted_edge_refs[str(edge_kind)] = compacted_refs
            next_row["doctrine_edge_refs"] = compacted_edge_refs
            if omitted_capsule_count:
                next_row["doctrine_edge_ref_compaction"] = {
                    "profile": "multi_skill_card_fast_path",
                    "omitted_projection_capsule_count": omitted_capsule_count,
                    "reason": (
                        "Multi-id skill-card drilldowns keep doctrine ids, labels, compression, "
                        "source refs, and drilldown/evidence commands; full resolver capsules stay "
                        "on exact single-skill card rows."
                    ),
                    "full_capsule_drilldown": _skill_evidence_command(str(next_row.get("skill_id") or "")),
                }
        receipt = dict(next_row.get("omission_receipt") or {})
        omitted = list(receipt.get("omitted") or [])
        if "full principle projection capsules for multi-skill card rows" not in omitted:
            omitted.append("full principle projection capsules for multi-skill card rows")
        receipt["omitted"] = omitted
        receipt.setdefault(
            "reason",
            "The card band selects and orients a capability; source authority remains in skill_registry.json plus the skill markdown file.",
        )
        receipt.setdefault("drilldown", _skill_evidence_command(str(next_row.get("skill_id") or "")))
        next_row["omission_receipt"] = receipt
        compacted_rows.append(next_row)
    return compacted_rows


def _skill_family_groups(entries: list[dict[str, Any]], *, repo_root: Path) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    by_family: dict[str, list[dict[str, Any]]] = {}
    family_meta: dict[str, dict[str, Any]] = {}
    for entry in entries:
        family_id = str(entry["family_id"])
        by_family.setdefault(family_id, []).append(entry)
        family_meta[family_id] = entry

    for family_id in sorted(
        by_family,
        key=lambda item: (
            int(family_meta[item].get("family_order") or 0),
            item,
        ),
    ):
        group_entries = by_family[family_id]
        flag_rows = [_skill_flag_row(entry, repo_root=repo_root) for entry in group_entries]
        skill_types = sorted({str(row.get("skill_type") or "untyped") for row in flag_rows})
        meta = family_meta[family_id]
        groups.append(
            {
                "family_id": family_id,
                "family_title": meta["family_title"],
                "description": meta["family_description"],
                "count": len(flag_rows),
                "skill_ids": [row["skill_id"] for row in flag_rows],
                "skill_types": skill_types,
                "rows": [
                    {
                        "skill_id": row["skill_id"],
                        "title": row["title"],
                        "skill_type": row.get("skill_type"),
                        "status": row.get("status"),
                        "flag": row.get("flag"),
                    }
                    for row in flag_rows
                ],
            }
        )
    return groups


def _skill_family_cluster_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    by_family: dict[str, list[dict[str, Any]]] = {}
    family_meta: dict[str, dict[str, Any]] = {}
    for entry in entries:
        family_id = str(entry["family_id"])
        by_family.setdefault(family_id, []).append(entry)
        family_meta[family_id] = entry

    for family_id in sorted(
        by_family,
        key=lambda item: (
            int(family_meta[item].get("family_order") or 0),
            item,
        ),
    ):
        group_entries = sorted(
            by_family[family_id],
            key=lambda item: (
                int(item.get("skill_order") or 0),
                _skill_id(item["skill"]),
            ),
        )
        skill_ids = [_skill_id(entry["skill"]) for entry in group_entries]
        meta = family_meta[family_id]
        skill_type_counts: dict[str, int] = {}
        cluster_key_counts: dict[str, int] = {}
        for entry in group_entries:
            skill_type = str(entry["skill"].get("skill_type") or "untyped")
            skill_type_counts[skill_type] = skill_type_counts.get(skill_type, 0) + 1
            for key in _skill_cluster_keys(entry["skill"]):
                cluster_key_counts[key] = cluster_key_counts.get(key, 0) + 1
        sorted_cluster_key_counts = sorted(
            cluster_key_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
        cluster_key_count_omitted = max(0, len(sorted_cluster_key_counts) - SKILL_CLUSTER_KEY_PREVIEW_LIMIT)
        cluster_key_count_omissions = (
            ["cluster_key_counts beyond top preview; use flag/card drilldowns for full skill rows"]
            if cluster_key_count_omitted
            else []
        )
        ids = ",".join(skill_ids[:8])
        family_title = str(meta["family_title"])
        groups.append(
            {
                "row_id": f"skill_family:{family_id}::cluster_flag",
                "artifact_kind": "skill_family",
                "band": "cluster_flag",
                "family_id": family_id,
                "family_title": family_title,
                "claim": _truncate_words(
                    f"{family_title}: {len(skill_ids)} skills. Top ids: {', '.join(skill_ids[:4]) or '<none>'}.",
                    max_chars=220,
                ),
                "count": len(skill_ids),
                "skill_ids": skill_ids,
                "skill_type_counts": dict(sorted(skill_type_counts.items())),
                "cluster_key_counts": dict(sorted_cluster_key_counts[:SKILL_CLUSTER_KEY_PREVIEW_LIMIT]),
                "cluster_key_counts_total": len(sorted_cluster_key_counts),
                "cluster_key_counts_omitted": cluster_key_count_omitted,
                "cluster_key_counts_preview_limit": SKILL_CLUSTER_KEY_PREVIEW_LIMIT,
                "cluster_key_counts_order": "count_desc_then_key",
                "drilldown_command": (
                    f"./repo-python kernel.py --option-surface skills --band flag --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface skills --band flag --ids <skill_id>"
                ),
                "card_drilldown_command": (
                    f"./repo-python kernel.py --option-surface skills --band card --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface skills --band card --ids <skill_id>"
                ),
                "omission_receipt": {
                    "omitted": [
                        "skill descriptions",
                        "trigger prose",
                        "workflow/evidence bodies",
                        "doctrine-edge and composes_with neighborhoods",
                        *cluster_key_count_omissions,
                    ],
                    "reason": "cluster_flag is the all-skills contents page: every skill id/title/type is visible, but meaning and evidence require explicit row drilldown.",
                },
            }
        )
    return groups


def build_skills_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="skills",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    registry_path = repo_root / SKILL_REGISTRY
    standard_path = repo_root / SKILL_STANDARD
    if not registry_path.exists() or not standard_path.exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="skills",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The skill registry or skill standard file is missing.",
                "refs": [_relative(registry_path, repo_root), _relative(standard_path, repo_root)],
            }
        )
        return payload

    registry = _load_skill_registry(repo_root)
    standard = _load_json(standard_path)
    entries = _skill_entries(registry)
    by_id = {_skill_id(entry["skill"]): entry for entry in entries}

    if ids:
        rows_source = [by_id[item] for item in ids if item in by_id]
        missing_ids = [item for item in ids if item not in by_id]
    else:
        rows_source = sorted(
            entries,
            key=lambda item: (
                int(item.get("family_order") or 0),
                int(item.get("skill_order") or 0),
                _skill_id(item["skill"]),
            ),
        )
        missing_ids = []

    if band == "cluster_flag":
        rows = _skill_family_cluster_rows(entries if not ids else rows_source)
    elif band == "card":
        doctrine_lookup_context = {
            "principle_capsule_cache": {},
            "concepts_by_key": _concept_by_id(repo_root),
            "mechanisms_by_key": _mechanism_by_id(repo_root),
        }
        rows = [
            _skill_card_row(
                entry,
                repo_root=repo_root,
                doctrine_lookup_context=doctrine_lookup_context,
            )
            for entry in rows_source
        ]
        rows = _compact_skill_doctrine_edge_refs_for_multi_card(rows)
    else:
        rows = [_skill_flag_row(entry, repo_root=repo_root) for entry in rows_source]
    family_groups = [] if band == "cluster_flag" else _skill_family_groups(rows_source if ids else entries, repo_root=repo_root)
    skill_type_counts: dict[str, int] = {}
    for entry in entries:
        skill_type = str(entry["skill"].get("skill_type") or "untyped")
        skill_type_counts[skill_type] = skill_type_counts.get(skill_type, 0) + 1

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "skills",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "standard_owned_projection_not_source_authority",
        "governing_standard": {
            "ref": str(SKILL_STANDARD),
            "schema_version": standard.get("schema_version"),
            "owned_bands": ["cluster_flag", "flag", "card"],
            "native_skill_bands_are_data_not_adapter_support": True,
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "source_refs": [
            str(SKILL_REGISTRY),
            str(SKILL_STANDARD),
            str(SKILL_TYPES_STANDARD),
            str(NAVIGATION_THEORY),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(entries),
            "query_used": False,
            "selection_method": (
                "artifact_kind_cluster_overview"
                if band == "cluster_flag"
                else "artifact_kind_enumeration_grouped_by_family"
            ),
            "drilldown_by": "family_id" if band == "cluster_flag" else "skill_id",
            "family_count": len(_skill_family_groups(entries, repo_root=repo_root)),
            "skill_type_counts": dict(sorted(skill_type_counts.items())),
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "grouped_by_registry_family": True,
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "native_skill_bands": ["triggers", "card", "workflow", "evidence"],
            "native_skill_bands_are_data_not_adapter_support": True,
        },
        "family_groups": family_groups,
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface skills --band cluster_flag",
                "reason": "Browse all skill families and ids at contents-page density before guessing a trigger query.",
            },
            {
                "command": "./repo-python kernel.py --option-surface skills --band card --ids <skill_id>",
                "reason": "Drill one skill to triggers, entry, source authority, currentness, and omission receipt.",
            },
            {
                "command": "./repo-python kernel.py --skill-find <query> --debug",
                "reason": "Use legacy skill-find only as an explicit debug/search trace after a candidate skill row is selected.",
            },
        ],
        "warnings": [],
    }


def _profile_source_mtime(repo_root: Path) -> str | None:
    return _source_mtime(repo_root / PROFILE_REGISTRY_REL)


def _compression_profile_evidence_command(profile_id: str) -> str:
    return (
        "jq '.profiles[] | select(.profile_id == "
        f"\"{profile_id}\")' {PROFILE_REGISTRY_REL}"
    )


def _compression_profile_title(profile: dict[str, Any]) -> str:
    return str(profile.get("title") or profile.get("profile_id") or "").strip()


def _compression_profile_flag(profile: dict[str, Any]) -> str:
    return _first_sentence(str(profile.get("purpose") or ""), max_chars=260)


def _compression_profile_currentness(repo_root: Path) -> dict[str, Any]:
    return {
        "status": "profile_registry_available",
        "source_mtime": _profile_source_mtime(repo_root),
        "authority_lifecycle": "candidate",
        "source_ref": PROFILE_REGISTRY_REL,
    }


def _compression_profile_flag_row(profile: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    pointer = compression_profile_pointer(profile)
    profile_id = str(pointer.get("profile_id") or "")
    return {
        "row_id": f"compression_profile:{profile_id}::flag",
        "artifact_kind": "compression_profile",
        "band": "flag",
        "profile_id": profile_id,
        "profile_artifact_kind": pointer.get("artifact_kind"),
        "title": _compression_profile_title(profile),
        "claim": _compression_profile_flag(profile),
        "flag": _compression_profile_flag(profile),
        "profile_bands": list(pointer.get("bands") or []),
        "creator_skill_id": pointer.get("creator_skill_id"),
        "navigator_skill_id": pointer.get("navigator_skill_id"),
        "source_ref": PROFILE_REGISTRY_REL,
        "drilldown_command": f"./repo-python kernel.py --option-surface compression_profiles --band card --ids {profile_id}",
        "evidence_command": _compression_profile_evidence_command(profile_id),
        "currentness": _compression_profile_currentness(repo_root),
    }


def _compression_profile_family_key(pointer: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(pointer.get("surface_family_id") or ""),
        str(pointer.get("root_slug") or ""),
        str(pointer.get("context_profile_id") or ""),
    )


def _compression_profile_sibling_row(profile: dict[str, Any]) -> dict[str, Any]:
    pointer = compression_profile_pointer(profile)
    profile_id = str(pointer.get("profile_id") or "")
    owner_routes = dict(pointer.get("owner_routes") or {})
    return {
        "profile_id": profile_id,
        "relationship": "sibling_render_profile",
        "same_surface_family_id": pointer.get("surface_family_id"),
        "same_root_slug": pointer.get("root_slug"),
        "same_context_profile_id": pointer.get("context_profile_id"),
        "title": _compression_profile_title(profile),
        "audience": pointer.get("audience"),
        "artifact_role": pointer.get("artifact_role"),
        "output_path": pointer.get("output_path"),
        "status_sidecar_path": pointer.get("status_sidecar_path"),
        "authority_boundary": pointer.get("authority_boundary"),
        "projection_not_authority": pointer.get("projection_not_authority"),
        "card_command": f"./repo-python kernel.py --option-surface compression_profiles --band card --ids {profile_id}",
        "refresh_command": owner_routes.get("refresh_command"),
        "check_command": owner_routes.get("check_command"),
        "status_command": owner_routes.get("status_command"),
    }


def _compression_profile_sibling_profiles(
    profile: dict[str, Any],
    *,
    all_profiles: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    pointer = compression_profile_pointer(profile)
    profile_id = str(pointer.get("profile_id") or "")
    family_key = _compression_profile_family_key(pointer)
    if not any(family_key):
        return []
    siblings: list[dict[str, Any]] = []
    for candidate in all_profiles:
        candidate_pointer = compression_profile_pointer(candidate)
        candidate_id = str(candidate_pointer.get("profile_id") or "")
        if not candidate_id or candidate_id == profile_id:
            continue
        if _compression_profile_family_key(candidate_pointer) != family_key:
            continue
        siblings.append(_compression_profile_sibling_row(candidate))
    siblings.sort(key=lambda row: str(row.get("profile_id") or ""))
    return siblings


def _compression_profile_card_row(
    profile: dict[str, Any],
    *,
    repo_root: Path,
    all_profiles: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pointer = compression_profile_pointer(profile)
    profile_id = str(pointer.get("profile_id") or "")
    source_ladder = list(pointer.get("source_ladder") or [])
    band_contracts = dict(pointer.get("band_contracts") or {})
    owner_routes = dict(pointer.get("owner_routes") or {})
    sibling_profiles = _compression_profile_sibling_profiles(
        profile,
        all_profiles=all_profiles or (),
    )
    return {
        "row_id": f"compression_profile:{profile_id}::card",
        "artifact_kind": "compression_profile",
        "band": "card",
        "profile_id": profile_id,
        "profile_kind": pointer.get("profile_kind"),
        "artifact_role": pointer.get("artifact_role"),
        "context_profile_id": pointer.get("context_profile_id"),
        "profile_artifact_kind": pointer.get("artifact_kind"),
        "title": _compression_profile_title(profile),
        "purpose": str(profile.get("purpose") or ""),
        "audience": pointer.get("audience"),
        "render_profile": {
            "output_path": pointer.get("output_path"),
            "last_green_output_path": pointer.get("last_green_output_path"),
            "candidate_output_path": pointer.get("candidate_output_path"),
            "operator_packet_path": pointer.get("operator_packet_path"),
            "status_sidecar_path": pointer.get("status_sidecar_path"),
            "source_model": pointer.get("source_model"),
            "surface_family_id": pointer.get("surface_family_id"),
            "root_slug": pointer.get("root_slug"),
            "authority_contract_path": pointer.get("authority_contract_path"),
            "projection_not_authority": pointer.get("projection_not_authority"),
            "disclosure_posture": pointer.get("disclosure_posture"),
            "receiver_intent": pointer.get("receiver_intent"),
            "job_to_be_done": pointer.get("job_to_be_done"),
            "command_policy": pointer.get("command_policy"),
            "refresh_owner": pointer.get("refresh_owner"),
            "authority_boundary": pointer.get("authority_boundary"),
        },
        "owner_routes": owner_routes,
        "route_summary": {
            "has_refresh_command": bool(owner_routes.get("refresh_command")),
            "has_check_command": bool(owner_routes.get("check_command")),
            "has_status_command": bool(owner_routes.get("status_command")),
            "has_root_drilldown_command": bool(owner_routes.get("root_drilldown_command")),
        },
        "sibling_profiles": sibling_profiles,
        "sibling_profile_summary": {
            "count": len(sibling_profiles),
            "profile_ids": [str(row.get("profile_id") or "") for row in sibling_profiles],
            "relationship": "same_surface_family_root_and_context_profile",
            "source_authority": PROFILE_REGISTRY_REL,
        },
        "source_manifest_fields_used": list(pointer.get("source_manifest_fields_used") or []),
        "auxiliary_sources": list(pointer.get("auxiliary_sources") or []),
        "profile_bands": list(pointer.get("bands") or []),
        "source_ladder": source_ladder,
        "source_ladder_summary": {
            "count": len(source_ladder),
            "brackets": [str(item.get("bracket") or "") for item in source_ladder if isinstance(item, dict)],
        },
        "band_contracts": band_contracts,
        "band_contract_summary": {
            "count": len(band_contracts),
            "bands": list(band_contracts.keys()),
        },
        "creator_skill_id": pointer.get("creator_skill_id"),
        "navigator_skill_id": pointer.get("navigator_skill_id"),
        "mandatory_preserve": list(pointer.get("mandatory_preserve") or []),
        "allowed_loss": list(pointer.get("allowed_loss") or []),
        "forbidden_collapse": list(pointer.get("forbidden_collapse") or []),
        "worker_tier_policy": dict(pointer.get("worker_tier_policy") or {}),
        "validation_probe": dict(pointer.get("validation_probe") or {}),
        "drilldown_policy": dict(pointer.get("drilldown_policy") or {}),
        "source_ref": PROFILE_REGISTRY_REL,
        "evidence_command": _compression_profile_evidence_command(profile_id),
        "currentness": _compression_profile_currentness(repo_root),
        "nearest_skill": {
            "ref": str(PROFILE_SKILL),
            "why": "The skill governs profile-first compression, band selection, omission receipts, and row-job boundaries.",
        },
        "omission_receipt": {
            "omitted": [
                "full raw source ancestry",
                "full sibling row neighborhoods",
                "full registry-wide future profile set if added later",
            ],
            "reason": "The card band supports selecting and applying the profile; full authority remains in compression_profiles.json.",
            "drilldown": f"jq '.' {PROFILE_REGISTRY_REL}",
        },
    }


def build_compression_profiles_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="compression_profiles",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    registry = load_compression_profile_registry(repo_root)
    profiles = [item for item in registry.get("profiles") or [] if isinstance(item, dict)]
    by_id: dict[str, dict[str, Any]] = {}
    for profile in profiles:
        profile_id = str(profile.get("profile_id") or "")
        if profile_id:
            by_id[profile_id] = profile

    if ids:
        rows_source = [by_id[item] for item in ids if item in by_id]
        missing_ids = [item for item in ids if item not in by_id]
    else:
        rows_source = sorted(profiles, key=lambda item: str(item.get("profile_id") or ""))
        missing_ids = []

    rows = (
        [
            _compression_profile_card_row(profile, repo_root=repo_root, all_profiles=profiles)
            for profile in rows_source
        ]
        if band == "card"
        else [_compression_profile_flag_row(profile, repo_root=repo_root) for profile in rows_source]
    )

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "compression_profiles",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "standard_owned_projection_not_source_authority",
        "governing_standard": {
            "ref": PROFILE_REGISTRY_REL,
            "schema_version": registry.get("schema_version"),
            "owned_bands": ["flag", "card"],
            "profile_declared_bands_are_data_not_adapter_support": True,
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "skill_ref": str(PROFILE_SKILL),
        "source_refs": [
            PROFILE_REGISTRY_REL,
            str(PROFILE_SKILL),
            str(NAVIGATION_THEORY),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(profiles),
            "query_used": False,
            "selection_method": "artifact_kind_enumeration",
            "drilldown_by": "profile_id",
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["flag", "card"],
            "profile_declared_bands_are_data_not_adapter_support": True,
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface compression_profiles --band flag",
                "reason": "Browse compression profiles before choosing a profile or opening raw JSON.",
            },
            {
                "command": "./repo-python kernel.py --option-surface compression_profiles --band card --ids <profile_id>",
                "reason": "Drill one compression profile to its contract, authority, and omission receipt.",
            },
        ],
        "warnings": [],
    }


def _frontend_component_load_index(repo_root: Path) -> dict[str, Any] | None:
    path = repo_root / FRONTEND_COMPONENT_INDEX
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _frontend_component_currentness(index: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    meta = index.get("__meta") if isinstance(index.get("__meta"), dict) else {}
    return {
        "status": "frontend_component_index_available",
        "source_ref": str(FRONTEND_COMPONENT_INDEX),
        "source_mtime": _source_mtime(repo_root / FRONTEND_COMPONENT_INDEX),
        "index_generated_at": meta.get("generated_at"),
        "schema_version": meta.get("schema_version"),
        "file_count": meta.get("file_count"),
        "component_count": meta.get("component_count"),
        "extractor": meta.get("extractor"),
        "standard": meta.get("standard"),
    }


def _frontend_component_evidence_command(component_id: str) -> str:
    return (
        f"jq --arg cid '{component_id}' "
        f"'.components[] | select(.component_id==$cid)' {FRONTEND_COMPONENT_INDEX}"
    )


def _frontend_component_source_evidence_command(component: dict[str, Any]) -> str:
    path = str(component.get("path") or "")
    line_start = component.get("line_start")
    line_end = component.get("line_end")
    if path and isinstance(line_start, int) and isinstance(line_end, int):
        return f"sed -n '{line_start},{line_end}p' {path}"
    return f"cat {path}" if path else "true"


def _frontend_component_flag_summary(component: dict[str, Any]) -> str:
    display = str(component.get("display_name") or component.get("export_name") or "")
    declaration = str(component.get("declaration_kind") or "")
    line_start = component.get("line_start")
    confidence = str(component.get("classification_confidence") or "")
    parts = [display, declaration, f"L{line_start}" if isinstance(line_start, int) else "", confidence]
    flag = " · ".join(part for part in parts if part)
    return _truncate_words(flag, max_chars=160)


def _frontend_component_cluster_id(component: dict[str, Any]) -> str:
    path = str(component.get("path") or component.get("source_ref") or "missing")
    if path.startswith("system/server/ui/src/"):
        parts = path.split("/")
        if len(parts) > 5:
            return "/".join(parts[:5])
    return path.rsplit("/", 1)[0] if "/" in path else path


def _frontend_component_cluster_rows(
    components: list[dict[str, Any]],
    *,
    currentness: dict[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for component in components:
        grouped.setdefault(_frontend_component_cluster_id(component), []).append(component)

    rows: list[dict[str, Any]] = []
    for cluster_id, group_components in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        group_components = sorted(group_components, key=lambda item: str(item.get("component_id") or ""))
        top_ids = [
            str(component.get("component_id") or "")
            for component in group_components[:8]
            if str(component.get("component_id") or "").strip()
        ]
        ids = ",".join(top_ids)
        declaration_counts = Counter(str(component.get("declaration_kind") or "unknown") for component in group_components)
        confidence_counts = Counter(
            str(component.get("classification_confidence") or "unknown") for component in group_components
        )
        label = cluster_id.rsplit("/", 1)[-1] if "/" in cluster_id else cluster_id
        label = label.replace("_", " ").title() if label else "Frontend Components"
        rows.append(
            {
                "row_id": f"frontend_component_cluster:{cluster_id}::cluster_flag",
                "artifact_kind": "frontend_component_cluster",
                "band": "cluster_flag",
                "cluster_id": cluster_id,
                "group_label": label,
                "count": len(group_components),
                "top_ids": top_ids,
                "sample_paths": sorted({str(component.get("path") or "") for component in group_components if component.get("path")})[:4],
                "declaration_kind_counts": dict(sorted(declaration_counts.items())),
                "classification_confidence_counts": dict(sorted(confidence_counts.items())),
                "default_export_count": sum(1 for component in group_components if bool(component.get("is_default_export"))),
                "claim": f"{label}: {len(group_components)} primary components",
                "drilldown_command": (
                    f"./repo-python kernel.py --option-surface frontend_components --band flag --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface frontend_components --band flag --ids <component_id>"
                ),
                "card_drilldown_command": (
                    f"./repo-python kernel.py --option-surface frontend_components --band card --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface frontend_components --band card --ids <component_id>"
                ),
                "currentness": currentness,
                "omission_receipt": {
                    "omitted": [
                        "row-level component flags outside top_ids",
                        "card-level source spans and wrappers",
                        "full TSX source bodies",
                        "low-confidence omitted candidates",
                    ],
                    "reason": "cluster_flag is the frontend component source-directory contents page; row flags and cards require explicit component ids.",
                    "drilldown": (
                        f"./repo-python kernel.py --option-surface frontend_components --band flag --ids {ids}"
                        if ids
                        else "./repo-python kernel.py --option-surface frontend_components --band flag --ids <component_id>"
                    ),
                },
            }
        )
    return rows


def _frontend_component_omission_receipt(*, band: str) -> dict[str, Any]:
    omitted = [
        "full TSX source body",
        "complete prop and state contract",
        "view ownership / route attachment edges",
        "wrapped HOC / context provider transitive closure",
        "import graph and downstream usage",
    ]
    if band == "flag":
        omitted.append("card-level wrappers list, jsx_returns flag, classification reasons, source span")
    return {
        "omitted": omitted,
        "reason": (
            "The frontend_components option surface is a read-only adapter over the generated"
            " state/frontend_navigation/component_index.json projection. It selects component"
            " ids and bounded extractor metadata without parsing TSX or replacing source authority."
        ),
        "drilldown": str(FRONTEND_COMPONENT_INDEX),
    }


def _frontend_component_flag_row(
    component: dict[str, Any],
    *,
    currentness: dict[str, Any],
) -> dict[str, Any]:
    component_id = str(component.get("component_id") or "")
    return {
        "row_id": f"frontend_component:{component_id}::flag",
        "artifact_kind": "frontend_component",
        "band": "flag",
        "component_id": component_id,
        "path": component.get("path"),
        "export_name": component.get("export_name"),
        "display_name": component.get("display_name"),
        "declaration_kind": component.get("declaration_kind"),
        "is_default_export": bool(component.get("is_default_export")),
        "line_start": component.get("line_start"),
        "line_end": component.get("line_end"),
        "classification_confidence": component.get("classification_confidence"),
        "claim": _frontend_component_flag_summary(component),
        "flag": _frontend_component_flag_summary(component),
        "source_ref": component.get("source_ref") or component.get("path"),
        "profile_id": FRONTEND_COMPONENT_PROFILE_ID,
        "drilldown_command": (
            f"./repo-python kernel.py --option-surface frontend_components --band card --ids {component_id}"
        ),
        "evidence_command": _frontend_component_evidence_command(component_id),
        "currentness": currentness,
        "omission_receipt": _frontend_component_omission_receipt(band="flag"),
    }


def _frontend_component_card_row(
    component: dict[str, Any],
    *,
    currentness: dict[str, Any],
) -> dict[str, Any]:
    row = _frontend_component_flag_row(component, currentness=currentness)
    component_id = row["component_id"]
    wrappers = component.get("wrappers") if isinstance(component.get("wrappers"), list) else []
    classification_reasons = component.get("classification_reasons") if isinstance(component.get("classification_reasons"), list) else []
    row.update(
        {
            "row_id": f"frontend_component:{component_id}::card",
            "band": "card",
            "wrappers": [str(item) for item in wrappers],
            "jsx_returns": bool(component.get("jsx_returns")),
            "classification_reasons": [str(item) for item in classification_reasons],
            "source_span": {
                "path": component.get("path"),
                "line_start": component.get("line_start"),
                "line_end": component.get("line_end"),
            },
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "native_frontend_component_bands": list(FRONTEND_COMPONENT_NATIVE_PROFILE_BANDS),
            "native_frontend_component_facets": list(FRONTEND_COMPONENT_NATIVE_PROFILE_FACETS),
            "nearest_standard": {
                "ref": str(FRONTEND_COMPONENT_STANDARD),
                "why": (
                    "std_frontend_component_index.json governs the generated projection's"
                    " row_unit, stable_id_strategy, required fields, and validation rules."
                ),
            },
            "nearest_extractor": {
                "ref": str(FRONTEND_COMPONENT_EXTRACTOR),
                "why": (
                    "frontend_component_index.py is the projection-of-record extractor;"
                    " the option surface reads its output and never reparses TSX itself."
                ),
            },
            "evidence_commands": [
                _frontend_component_evidence_command(component_id),
                _frontend_component_source_evidence_command(component),
            ],
            "omission_receipt": _frontend_component_omission_receipt(band="card"),
        }
    )
    return row


def _frontend_component_omitted_receipt(component: dict[str, Any]) -> dict[str, Any]:
    component_id = str(component.get("component_id") or "")
    classification_reasons = component.get("classification_reasons") if isinstance(component.get("classification_reasons"), list) else []
    return {
        "component_id": component_id,
        "omitted": True,
        "reason": "low_confidence_classification",
        "classification_confidence": component.get("classification_confidence"),
        "classification_reasons": [str(item) for item in classification_reasons],
        "path": component.get("path"),
        "export_name": component.get("export_name"),
        "declaration_kind": component.get("declaration_kind"),
        "line_start": component.get("line_start"),
        "line_end": component.get("line_end"),
        "evidence_command": _frontend_component_evidence_command(component_id),
        "policy": (
            "Helper functions, exported constants, and other non-React-component shapes detected by"
            " the extractor are preserved as omitted candidates rather than first-class component rows."
        ),
    }


def build_frontend_components_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="frontend_components",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    index = _frontend_component_load_index(repo_root)
    if index is None:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="frontend_components",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"] = [
            {
                "kind": "missing_projection_input",
                "message": (
                    "The frontend component index projection is missing. Regenerate it with the"
                    " extractor before requesting frontend_components rows."
                ),
                "refs": [
                    str(FRONTEND_COMPONENT_INDEX),
                    str(FRONTEND_COMPONENT_EXTRACTOR),
                    str(FRONTEND_COMPONENT_STANDARD),
                ],
            }
        ]
        payload["next"] = [
            {
                "command": f"./repo-python {FRONTEND_COMPONENT_EXTRACTOR} --check",
                "reason": "Verify the projection matches disk before regenerating.",
            },
            {
                "command": (
                    f"./repo-python {FRONTEND_COMPONENT_EXTRACTOR} --print > {FRONTEND_COMPONENT_INDEX}"
                ),
                "reason": "Regenerate the projection. The option-surface adapter never writes the projection itself.",
            },
        ]
        return payload

    components = list(index.get("components") or []) if isinstance(index.get("components"), list) else []
    components_by_id: dict[str, dict[str, Any]] = {}
    for component in components:
        if not isinstance(component, dict):
            continue
        component_id = str(component.get("component_id") or "").strip()
        if not component_id:
            continue
        components_by_id.setdefault(component_id, component)

    primary_components = [
        component
        for component in components_by_id.values()
        if str(component.get("classification_confidence") or "") in FRONTEND_COMPONENT_PRIMARY_CONFIDENCE
    ]
    omitted_components = [
        component
        for component in components_by_id.values()
        if str(component.get("classification_confidence") or "") in FRONTEND_COMPONENT_OMITTED_CONFIDENCE
    ]
    primary_components.sort(key=lambda item: str(item.get("component_id") or ""))
    omitted_components.sort(key=lambda item: str(item.get("component_id") or ""))

    primary_by_id = {str(c.get("component_id") or ""): c for c in primary_components}
    omitted_by_id = {str(c.get("component_id") or ""): c for c in omitted_components}

    currentness = _frontend_component_currentness(index, repo_root=repo_root)

    if ids:
        rows_source: list[dict[str, Any]] = []
        omitted_source: list[dict[str, Any]] = []
        missing_ids: list[str] = []
        seen: set[str] = set()
        for item in ids:
            if item in seen:
                continue
            seen.add(item)
            if item in primary_by_id:
                rows_source.append(primary_by_id[item])
            elif item in omitted_by_id:
                omitted_source.append(omitted_by_id[item])
            else:
                missing_ids.append(item)
    else:
        rows_source = primary_components
        omitted_source = omitted_components
        missing_ids = []

    if band == "cluster_flag":
        rows = _frontend_component_cluster_rows(rows_source, currentness=currentness)
    elif band == "card":
        rows = [_frontend_component_card_row(component, currentness=currentness) for component in rows_source]
    else:
        rows = [_frontend_component_flag_row(component, currentness=currentness) for component in rows_source]
    omissions = [] if band == "cluster_flag" else [_frontend_component_omitted_receipt(component) for component in omitted_source]

    candidate_count = len(components_by_id)
    primary_total = len(primary_components)
    omitted_total = len(omitted_components)

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "frontend_components",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "generated_projection_not_source_authority",
        "governing_standard": {
            "ref": str(FRONTEND_COMPONENT_STANDARD),
            "owned_bands": ["cluster_flag", "flag", "card"],
        },
        "extractor_ref": str(FRONTEND_COMPONENT_EXTRACTOR),
        "projection_path": str(FRONTEND_COMPONENT_INDEX),
        "source_refs": [
            str(FRONTEND_COMPONENT_INDEX),
            str(FRONTEND_COMPONENT_STANDARD),
            str(FRONTEND_COMPONENT_EXTRACTOR),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": primary_total,
            "primary_row_count": primary_total,
            "candidate_count": candidate_count,
            "omitted_low_confidence_count": omitted_total,
            "query_used": False,
            "selection_method": (
                "artifact_kind_cluster_overview_from_frontend_component_index"
                if band == "cluster_flag"
                else "artifact_kind_enumeration_from_frontend_component_index"
            ),
            "drilldown_by": "source_directory" if band == "cluster_flag" else "component_id",
            "source_projection_reused": str(FRONTEND_COMPONENT_INDEX),
            "grouping_keys": ["path", "classification_confidence", "declaration_kind"]
            if band == "cluster_flag"
            else [],
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "native_profile_bands": list(FRONTEND_COMPONENT_NATIVE_PROFILE_BANDS),
            "native_profile_facets": list(FRONTEND_COMPONENT_NATIVE_PROFILE_FACETS),
            "tsx_parsing_in_this_adapter": False,
            "projection_regeneration_in_this_adapter": False,
            "low_confidence_first_class_rows_allowed": False,
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "cluster_row_shape": (
                "compact_source_directory_counts_with_top_ids"
                if band == "cluster_flag"
                else "component_rows"
            ),
        },
        "currentness": currentness,
        "rows": rows,
        "omissions": omissions,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface frontend_components --band cluster_flag",
                "reason": "Browse source-directory clusters before expanding row-level component flags.",
            },
            {
                "command": "./repo-python kernel.py --option-surface frontend_components --band flag --ids <component_id>[,<component_id>...]",
                "reason": "Browse explicit high+medium-confidence React components extracted from system/server/ui/src.",
            },
            {
                "command": (
                    "./repo-python kernel.py --option-surface frontend_components --band card --ids "
                    "<component_id>"
                ),
                "reason": "Drill one component to source span, wrappers, classification reasons, and evidence commands.",
            },
            {
                "command": f"./repo-python {FRONTEND_COMPONENT_EXTRACTOR} --check",
                "reason": "Confirm the generated projection matches disk before trusting card output.",
            },
        ],
        "warnings": [],
    }


def _system_atlas_load_graph(repo_root: Path) -> dict[str, Any]:
    graph_path = repo_root / SYSTEM_ATLAS_GRAPH
    if not graph_path.exists():
        return {}
    try:
        graph = _load_json(graph_path)
    except Exception:
        return {}
    return graph if isinstance(graph, dict) else {}


def _system_atlas_source_input_key(row: Mapping[str, Any]) -> str:
    return f"{row.get('source_id') or ''}\0{row.get('path') or ''}"


def _system_atlas_current_source_inputs(repo_root: Path) -> list[dict[str, Any]]:
    try:
        from tools.meta.factory import build_system_atlas
    except Exception:
        return []
    try:
        rows = build_system_atlas.collect_source_inputs()
    except Exception:
        return []
    return [row for row in rows if isinstance(row, dict)]


def _system_atlas_source_coupling(
    graph: Mapping[str, Any],
    *,
    current_source_inputs: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    existing_rows = {
        _system_atlas_source_input_key(row): row
        for row in graph.get("source_inputs", [])
        if isinstance(row, Mapping)
    }
    current_rows = {
        _system_atlas_source_input_key(row): row
        for row in (current_source_inputs or [])
        if isinstance(row, Mapping)
    }
    if not existing_rows:
        return {
            "status": "source_inputs_missing_from_graph",
            "changed_source_count": 0,
            "changed_sources": [],
            "safe_to_commit_generated_outputs_without_sources": False,
            "reason": "System Atlas graph does not carry source-input fingerprints, so freshness cannot be established.",
        }
    if not current_rows:
        return {
            "status": "current_source_inputs_unavailable",
            "changed_source_count": 0,
            "changed_sources": [],
            "safe_to_commit_generated_outputs_without_sources": False,
            "reason": "Current System Atlas source inputs could not be collected; run the builder check before trusting this projection.",
        }

    changed: list[dict[str, Any]] = []
    for key in sorted(set(existing_rows) | set(current_rows)):
        before = existing_rows.get(key)
        after = current_rows.get(key)
        if before == after:
            continue
        row = after or before or {}
        changed.append(
            {
                "source_id": row.get("source_id"),
                "path": row.get("path"),
                "previous_latest_mtime": before.get("latest_mtime") if before else None,
                "current_latest_mtime": after.get("latest_mtime") if after else None,
                "previous_count": before.get("count") if before else None,
                "current_count": after.get("count") if after else None,
            }
        )

    if changed:
        return {
            "status": "source_inputs_changed_since_artifact_generation",
            "changed_source_count": len(changed),
            "changed_sources": changed[:12],
            "truncated_changed_sources": max(0, len(changed) - 12),
            "safe_to_commit_generated_outputs_without_sources": False,
            "reason": "System Atlas source inputs changed after the checked artifact was generated; rebuild after the moving source lane settles.",
        }
    return {
        "status": "source_inputs_match_checked_artifact",
        "changed_source_count": 0,
        "changed_sources": [],
        "safe_to_commit_generated_outputs_without_sources": True,
        "reason": "System Atlas source inputs in the checked artifact match the current builder inputs.",
    }


def _system_atlas_currentness(graph: Mapping[str, Any], source_coupling: Mapping[str, Any]) -> dict[str, Any]:
    safe_to_commit = source_coupling.get("safe_to_commit_generated_outputs_without_sources") is True
    return {
        "status": "source_inputs_match_checked_artifact" if safe_to_commit else "stale_source_coupling",
        "graph_generated_at": graph.get("generated_at"),
        "source_coupling_status": source_coupling.get("status"),
        "changed_source_count": source_coupling.get("changed_source_count", 0),
        "safe_to_commit_generated_outputs_without_sources": safe_to_commit,
        "freshness_command": f"./repo-python {SYSTEM_ATLAS_BUILDER} --check",
        "recommended_action": "trust" if safe_to_commit else "rerun owner check and rebuild only after moving sources settle",
    }


def _apply_system_atlas_currentness(
    rows: list[dict[str, Any]],
    *,
    currentness: Mapping[str, Any],
) -> list[dict[str, Any]]:
    for row in rows:
        row["currentness"] = dict(currentness)
        row["projection_freshness_status"] = currentness.get("status")
        row["source_coupling_status"] = currentness.get("source_coupling_status")
        row["safe_to_commit_generated_outputs_without_sources"] = currentness.get(
            "safe_to_commit_generated_outputs_without_sources"
        )
    return rows


def _system_atlas_entity_flag(entity: dict[str, Any]) -> dict[str, Any]:
    entity_id = str(entity.get("id") or "")
    return {
        "row_id": f"system_atlas:{entity_id}::flag",
        "artifact_kind": "system_atlas_entity",
        "band": "flag",
        "id": entity_id,
        "kind": str(entity.get("kind") or ""),
        "title": str(entity.get("title") or entity_id),
        "summary": _truncate_words(str(entity.get("summary") or ""), max_chars=320),
        "authority_class": str(entity.get("authority_class") or ""),
        "maturity": str(entity.get("maturity") or ""),
        "risk_level": str(entity.get("risk_level") or ""),
        "disclosure_class": str(entity.get("disclosure_class") or ""),
        "freshness_status": str(entity.get("freshness_status") or ""),
        "evidence_paths": [str(item) for item in list(entity.get("evidence_paths") or [])[:6]],
        "related_workitems": [str(item) for item in list(entity.get("related_workitems") or [])[:6]],
        "owning_module": entity.get("owning_module"),
        "drilldown_command": f"./repo-python kernel.py --option-surface system_atlas --band card --ids {entity_id}",
    }


def _system_atlas_live_type_plane_overlay_entities(
    repo_root: Path,
    *,
    requested_ids: Sequence[str],
    existing_entity_ids: set[str],
) -> list[dict[str, Any]]:
    requested = {str(item) for item in requested_ids if str(item).strip()}
    if not requested:
        return []
    try:
        from tools.meta.factory import build_system_atlas
    except Exception:
        return []
    try:
        type_rows = build_system_atlas._type_plane_rows()
        candidates = (
            build_system_atlas._type_plane_artifact_entities(
                type_rows,
                existing_entity_ids=existing_entity_ids,
            )
            + build_system_atlas._type_plane_surface_entities(type_rows)
            + build_system_atlas._type_plane_validator_entities(type_rows)
        )
    except Exception:
        return []

    out: list[dict[str, Any]] = []
    seen = set(existing_entity_ids)
    source_ref = str(STANDARD_TYPE_PLANE)
    for candidate in candidates:
        entity_id = str(candidate.get("id") or "")
        if entity_id not in requested or entity_id in seen:
            continue
        seen.add(entity_id)
        entity = dict(candidate)
        metrics = dict(entity.get("metrics") if isinstance(entity.get("metrics"), dict) else {})
        metrics["system_atlas_live_overlay"] = {
            "status": "live_standard_type_plane_overlay",
            "source_ref": source_ref,
            "reason": (
                "Requested type-plane entity is absent from the generated System Atlas graph; "
                "the option surface projected it from the current standards type-plane source."
            ),
            "freshness_boundary": f"./repo-python {SYSTEM_ATLAS_BUILDER} --check",
            "drilldown": (list(entity.get("next_drilldowns") or [None])[0])
            or "./repo-python kernel.py --option-surface navigation_type_plane --band card",
        }
        entity["metrics"] = metrics
        source_of_truth = [str(item) for item in list(entity.get("source_of_truth") or [])]
        if source_ref not in source_of_truth:
            source_of_truth.insert(0, source_ref)
        entity["source_of_truth"] = source_of_truth
        evidence_paths = [str(item) for item in list(entity.get("evidence_paths") or [])]
        if source_ref not in evidence_paths:
            evidence_paths.insert(0, source_ref)
        entity["evidence_paths"] = evidence_paths
        out.append(entity)
    return out


def _system_atlas_entity_card(entity: dict[str, Any], *, graph: dict[str, Any]) -> dict[str, Any]:
    row = _system_atlas_entity_flag(entity)
    next_drilldowns = [str(item) for item in list(entity.get("next_drilldowns") or [])]
    metrics = entity.get("metrics") if isinstance(entity.get("metrics"), dict) else {}
    overlay = metrics.get("system_atlas_live_overlay") if isinstance(metrics, dict) else None
    overlay = overlay if isinstance(overlay, dict) else None
    omission_reason = "The System Atlas card is a control-plane row over generated state. Reopen evidence paths before promoting a claim."
    omission_drilldown = f"jq '.entities[] | select(.id==\"{row['id']}\")' state/system_atlas/system_atlas.graph.json"
    if overlay:
        omission_reason = (
            "This System Atlas card is a source-backed standards type-plane overlay. "
            "Use the type-plane drilldown for the live contract and the builder check for generated graph freshness."
        )
        omission_drilldown = str(overlay.get("drilldown") or omission_drilldown)
    row.update(
        {
            "row_id": f"system_atlas:{row['id']}::card",
            "band": "card",
            "generated_by": str(entity.get("generated_by") or graph.get("generated_by") or ""),
            "source_inputs": [str(item) for item in list(entity.get("source_of_truth") or [])[:10]],
            "source_of_truth": [str(item) for item in list(entity.get("source_of_truth") or [])[:10]],
            "safe_agent_actions": [str(item) for item in list(entity.get("safe_agent_actions") or [])],
            "forbidden_agent_actions": [str(item) for item in list(entity.get("forbidden_agent_actions") or [])],
            "next_drilldowns": next_drilldowns,
            "next_drilldown_command": next_drilldowns[0]
            if next_drilldowns
            else f"./repo-python kernel.py --option-surface system_atlas --band card --ids {row['id']}",
            "metrics": metrics,
            "omission_receipt": {
                "omitted": [
                    "source file bodies",
                    "private state contents",
                    "provider/browser/feed artifact bodies",
                    "transitive graph neighborhoods",
                ],
                "reason": omission_reason,
                "drilldown": omission_drilldown,
            },
        }
    )
    return row


def _system_atlas_cluster_rows(entities: list[dict[str, Any]], findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for entity in entities:
        kind = str(entity.get("kind") or "unknown")
        cluster_id = re.sub(r"[^a-z0-9_]+", "_", kind.lower()).strip("_") or "unknown"
        bucket = grouped.setdefault(
            cluster_id,
            {
                "row_id": f"system_atlas_cluster:{cluster_id}::cluster_flag",
                "artifact_kind": "system_atlas_cluster",
                "band": "cluster_flag",
                "cluster_id": cluster_id,
                "label": kind,
                "count": 0,
                "top_ids": [],
                "authority_classes": {},
                "disclosure_classes": {},
            },
        )
        bucket["count"] += 1
        if len(bucket["top_ids"]) < 8:
            bucket["top_ids"].append(str(entity.get("id") or ""))
        authority = str(entity.get("authority_class") or "unknown")
        disclosure = str(entity.get("disclosure_class") or "unknown")
        bucket["authority_classes"][authority] = int(bucket["authority_classes"].get(authority, 0)) + 1
        bucket["disclosure_classes"][disclosure] = int(bucket["disclosure_classes"].get(disclosure, 0)) + 1

    rows = sorted(grouped.values(), key=lambda row: str(row.get("cluster_id") or ""))
    if findings:
        rows.append(
            {
                "row_id": "system_atlas_cluster:findings::cluster_flag",
                "artifact_kind": "system_atlas_cluster",
                "band": "cluster_flag",
                "cluster_id": "findings",
                "label": "Findings",
                "count": len(findings),
                "top_ids": [str(item.get("id") or "") for item in findings[:8]],
                "drilldown_command": "./repo-python kernel.py --option-surface system_atlas --band unknowns",
                "omission_receipt": {
                    "omitted": ["full finding payloads", "source file bodies"],
                    "reason": "cluster_flag names the finding cluster; unknowns/stale bands render finding rows.",
                    "drilldown": "./repo-python kernel.py --option-surface system_atlas --band unknowns",
                },
            }
        )
    for row in rows:
        ids = ",".join(str(item) for item in list(row.get("top_ids") or []) if item)
        row.setdefault(
            "drilldown_command",
            f"./repo-python kernel.py --option-surface system_atlas --band flag --ids {ids}"
            if ids
            else "./repo-python kernel.py --option-surface system_atlas --band flag",
        )
        row.setdefault(
            "card_drilldown_command",
            f"./repo-python kernel.py --option-surface system_atlas --band card --ids {ids}"
            if ids
            else "./repo-python kernel.py --option-surface system_atlas --band card --ids <entity_id>",
        )
        row.setdefault(
            "omission_receipt",
            {
                "omitted": ["row-level entity cards", "source file bodies", "private generated state contents"],
                "reason": "cluster_flag is the contents-page rung for the generated atlas graph.",
                "drilldown": row["drilldown_command"],
            },
        )
    return rows


def _system_atlas_finding_row(finding: dict[str, Any], *, band: str) -> dict[str, Any]:
    finding_id = str(finding.get("id") or "")
    return {
        "row_id": f"system_atlas_finding:{finding_id}::{band}",
        "artifact_kind": "system_atlas_finding",
        "band": band,
        "id": finding_id,
        "kind": str(finding.get("kind") or ""),
        "severity": str(finding.get("severity") or ""),
        "title": str(finding.get("title") or finding_id),
        "summary": _truncate_words(str(finding.get("summary") or ""), max_chars=360),
        "authority_class": str(finding.get("authority_class") or ""),
        "evidence_paths": [str(item) for item in list(finding.get("evidence_paths") or [])[:6]],
        "related_entity_ids": [str(item) for item in list(finding.get("related_entity_ids") or [])[:8]],
        "recommended_action": _truncate_words(str(finding.get("recommended_action") or ""), max_chars=360),
        "drilldown_command": "jq '.findings[] | select(.id==\"%s\")' state/system_atlas/system_atlas.graph.json"
        % finding_id,
    }


def build_system_atlas_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card", "stale", "unknowns"}:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="system_atlas",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "unsupported_band_for_kind",
                "message": "System Atlas supports cluster_flag, flag, card, stale, and unknowns bands.",
                "supported_bands": ["cluster_flag", "flag", "card", "stale", "unknowns"],
            }
        )
        return payload

    graph = _system_atlas_load_graph(repo_root)
    if not graph:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="system_atlas",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The System Atlas graph is missing. Run the builder before browsing this surface.",
                "refs": [str(SYSTEM_ATLAS_GRAPH), str(SYSTEM_ATLAS_BUILDER)],
                "repair_command": f"./repo-python {SYSTEM_ATLAS_BUILDER}",
            }
        )
        return payload

    entities = [item for item in list(graph.get("entities") or []) if isinstance(item, dict)]
    generated_graph_entity_count = len(entities)
    findings = [item for item in list(graph.get("findings") or []) if isinstance(item, dict)]
    by_id = {str(entity.get("id") or ""): entity for entity in entities}
    selected = [by_id[item] for item in ids if item in by_id] if ids else entities
    missing_ids = [item for item in ids if item not in by_id]
    live_type_plane_overlay_entities: list[dict[str, Any]] = []
    if ids and band in {"flag", "card"} and missing_ids:
        live_type_plane_overlay_entities = _system_atlas_live_type_plane_overlay_entities(
            repo_root,
            requested_ids=missing_ids,
            existing_entity_ids=set(by_id),
        )
        if live_type_plane_overlay_entities:
            for entity in live_type_plane_overlay_entities:
                entity_id = str(entity.get("id") or "")
                if not entity_id or entity_id in by_id:
                    continue
                by_id[entity_id] = entity
                entities.append(entity)
            selected = [by_id[item] for item in ids if item in by_id] if ids else entities
            missing_ids = [item for item in ids if item not in by_id]
    overlay_entity_ids = [str(entity.get("id") or "") for entity in live_type_plane_overlay_entities]
    source_coupling = _system_atlas_source_coupling(
        graph,
        current_source_inputs=_system_atlas_current_source_inputs(repo_root),
    )
    currentness = _system_atlas_currentness(graph, source_coupling)
    requested_band = band
    band_redirect: dict[str, Any] | None = None
    if band == "card" and not ids:
        band = "cluster_flag"
        band_redirect = {
            "from": "card",
            "to": "cluster_flag",
            "reason": (
                "system_atlas all-card is a high-cardinality projection expansion; "
                "row-level cards require explicit --ids."
            ),
            "explicit_row_card_command": "./repo-python kernel.py --option-surface system_atlas --band card --ids <entity_id>",
        }

    if band == "cluster_flag":
        rows = _system_atlas_cluster_rows(entities, findings)
    elif band == "card":
        rows = [_system_atlas_entity_card(entity, graph=graph) for entity in selected]
    elif band == "stale":
        stale_entities = [
            entity
            for entity in entities
            if str(entity.get("freshness_status") or "") in {"stale", "source_changed", "generated_missing", "unknown"}
        ]
        rows = [_system_atlas_entity_flag(entity) for entity in stale_entities] + [
            _system_atlas_finding_row(finding, band=band)
            for finding in findings
            if str(finding.get("kind") or "").startswith("missing") or "stale" in str(finding.get("kind") or "")
        ]
    elif band == "unknowns":
        unknown_entities = [
            entity
            for entity in entities
            if str(entity.get("maturity") or "") in {"partial", "planned", "stale", "unknown"}
            or str(entity.get("freshness_status") or "") in {"unknown", "generated_missing", "source_changed", "stale"}
        ]
        rows = [_system_atlas_entity_flag(entity) for entity in unknown_entities] + [
            _system_atlas_finding_row(finding, band=band) for finding in findings
        ]
    else:
        rows = [_system_atlas_entity_flag(entity) for entity in selected]
    rows = _apply_system_atlas_currentness(rows, currentness=currentness)
    warnings: list[dict[str, Any]] = []
    if source_coupling.get("safe_to_commit_generated_outputs_without_sources") is not True:
        warnings.append(
            {
                "kind": "system_atlas_source_coupling_not_clean",
                "message": "System Atlas projection is not source-clean; treat rows as stale generated projection until the owner check passes.",
                "source_coupling_status": source_coupling.get("status"),
                "changed_source_count": source_coupling.get("changed_source_count", 0),
                "repair_command": f"./repo-python {SYSTEM_ATLAS_BUILDER} --check",
            }
        )
    if live_type_plane_overlay_entities:
        warnings.append(
            {
                "kind": "system_atlas_live_type_plane_overlay",
                "message": (
                    "Resolved requested standards type-plane ids from std_standard_type_plane because "
                    "they were absent from the generated System Atlas graph."
                ),
                "resolved_ids": overlay_entity_ids,
                "source_ref": str(STANDARD_TYPE_PLANE),
                "freshness_boundary": f"./repo-python {SYSTEM_ATLAS_BUILDER} --check",
            }
        )

    payload = {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "system_atlas",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "generated_control_plane_projection_not_source_authority",
        "governing_standard": {
            "ref": str(SYSTEM_ATLAS_STANDARD),
            "schema_version": "std_system_atlas_v1",
            "owned_bands": ["cluster_flag", "flag", "card", "stale", "unknowns"],
        },
        "source_refs": [
            str(SYSTEM_ATLAS_GRAPH),
            str(SYSTEM_ATLAS_SUMMARY),
            str(SYSTEM_ATLAS_STANDARD),
            str(SYSTEM_ATLAS_BUILDER),
            str(STANDARD_TYPE_PLANE),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(entities),
            "generated_graph_entity_count": generated_graph_entity_count,
            "live_type_plane_overlay_count": len(live_type_plane_overlay_entities),
            "missing_ids_resolved_by_live_overlay": overlay_entity_ids,
            "finding_count": len(findings),
            "query_used": False,
            "selection_method": "generated_system_atlas_graph_plus_live_type_plane_overlay"
            if live_type_plane_overlay_entities
            else "generated_system_atlas_graph",
            "drilldown_by": "entity_id" if band in {"flag", "card"} else "cluster_or_finding",
            "graph_generated_at": graph.get("generated_at"),
            "projection_freshness_status": currentness.get("status"),
            "source_coupling_status": source_coupling.get("status"),
            "safe_to_commit_generated_outputs_without_sources": source_coupling.get(
                "safe_to_commit_generated_outputs_without_sources"
            ),
        },
        "currentness": currentness,
        "source_coupling": source_coupling,
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "adapter_supported_bands": ["cluster_flag", "flag", "card", "stale", "unknowns"],
            "first_contact_allowed": False,
            "control_replacement": ENTRY_REPLACEMENT,
            "mutation_rule": f"Refresh with ./repo-python {SYSTEM_ATLAS_BUILDER}; do not hand-edit state/system_atlas/*.json.",
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "live_type_plane_overlay_count": len(live_type_plane_overlay_entities),
            "source_coupling_status": source_coupling.get("status"),
            "safe_to_commit_generated_outputs_without_sources": source_coupling.get(
                "safe_to_commit_generated_outputs_without_sources"
            ),
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
                "reason": "Browse generated atlas entity clusters before row expansion.",
            },
            {
                "command": "./repo-python kernel.py --option-surface system_atlas --band card --ids dom_system_atlas",
                "reason": "Inspect the atlas control-plane root card with evidence and omission receipts.",
            },
            {
                "command": f"./repo-python {SYSTEM_ATLAS_BUILDER} --check",
                "reason": "Validate graph/schema/redaction freshness before promoting atlas-backed claims.",
            },
        ],
        "warnings": warnings,
    }
    if band_redirect is not None:
        payload["requested_band"] = requested_band
        payload["band_redirect"] = band_redirect
        warnings.append(
            {
                "kind": "high_cardinality_card_redirect",
                "message": "Rendered cluster_flag instead of all System Atlas entity cards.",
            }
        )
    return payload


def _profile_gap_payload(
    *,
    repo_root: Path,
    artifact_kind: str,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": artifact_kind,
        "band": band,
        "selection": {"mode": "ids" if ids else "all", "ids": ids},
        "profile_status": "profile_gap",
        "summary": {
            "row_count": 0,
            "total_available": 0,
            "query_used": False,
            "selection_method": "artifact_kind_enumeration",
        },
        "rows": [],
        "warnings": [
            {
                "kind": "unsupported_artifact_kind_or_band",
                "message": "No standard-owned option-surface projection is registered for this artifact kind and band.",
            }
        ],
        "next": [
            {
                "command": "./repo-python kernel.py --entry \"profile governed compression\" --context-budget 12000",
                "reason": "Enter through the control compiler before selecting a compression skill or debug trace.",
            }
        ],
        "source_refs": [_relative(repo_root / str(PROFILE_SKILL), repo_root)],
    }


def _route_affordance_gap_payload(
    *,
    repo_root: Path,
    artifact_kind: str,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if artifact_kind == "raw_seed_paper":
        title = "Raw seed paper is governed by existing paper-module and authoring-skill routes."
        message = (
            "No standalone raw_seed_paper option-surface projection is registered. "
            "Use the existing paper-module surface for authored doctrine, and the raw-seed-paper authoring "
            "skill for concept/instance authoring modes."
        )
        next_steps = [
            {
                "command": "./repo-python kernel.py --option-surface paper_modules --band card --ids raw_seed_paper",
                "reason": "Open the raw-seed-paper paper-module card when you need authored doctrine context.",
            },
            {
                "command": "./repo-python kernel.py --option-surface skills --band card --ids raw_seed_paper_authoring",
                "reason": "Open the mode chooser for concept_lens_mode, family_instance_mode, coverage_ledger_mode, work_conversion_mode, and propagation_mode.",
            },
            {
                "command": "./repo-python kernel.py --context-pack \"raw seed paper authoring\" --context-budget 12000",
                "reason": "Use the control compiler when the exact raw-seed-paper task is not already selected.",
            },
        ]
        source_refs = [
            RAW_SEED_NAVIGATION_SKILL,
            Path("codex/doctrine/skills/raw_seed/raw_seed_paper_authoring.md"),
            Path("codex/doctrine/paper_modules/raw_seed_paper.md"),
            Path("codex/doctrine/paper_modules/raw_seed_metabolism.md"),
        ]
        mode_cards = [
            {
                "mode": "concept_lens_mode",
                "use_when": "You are authoring or reviewing reusable raw-seed-paper concepts rather than one family instance.",
            },
            {
                "mode": "family_instance_mode",
                "use_when": "You are applying raw-seed-paper machinery to a concrete family or phase instance.",
            },
            {
                "mode": "coverage_ledger_mode",
                "use_when": "You are checking coverage, companion ledgers, or paper-module currentness.",
            },
            {
                "mode": "work_conversion_mode",
                "use_when": "You are turning raw-seed-paper findings into Task Ledger or Work Ledger objects.",
            },
            {
                "mode": "propagation_mode",
                "use_when": "You are routing a reusable lesson into standards, skills, paper modules, or bootstrap surfaces.",
            },
        ]
    else:
        title = "Raw seed is governed by existing navigation, shard, principle, and context routes."
        message = (
            "No standalone raw_seed option-surface projection is registered. "
            "Use the raw-seed navigation skill, raw_seed_shards option surface, principles/axioms surfaces, "
            "or context-pack depending on the task."
        )
        next_steps = [
            {
                "command": "./repo-python kernel.py --option-surface skills --band card --ids raw_seed_navigation",
                "reason": "Open the raw-seed navigation skill card for read/write/distill/assimilate route choice.",
            },
            {
                "command": "./repo-python kernel.py --option-surface raw_seed_shards --band flag",
                "reason": "Browse distilled raw-seed shards when you need selectable row evidence.",
            },
            {
                "command": "./repo-python kernel.py --option-surface principles --band cluster_flag",
                "reason": "Browse raw-seed-derived principles before opening principle cards.",
            },
            {
                "command": "./repo-python kernel.py --context-pack \"raw seed\" --context-budget 12000",
                "reason": "Use the control compiler when the task is broader than a known raw-seed row surface.",
            },
        ]
        source_refs = [
            RAW_SEED_NAVIGATION_SKILL,
            RAW_SEED_SHARDS,
            RAW_SEED_PRINCIPLES,
            RAW_SEED_STANDARD,
            NAVIGATION_THEORY,
        ]
        mode_cards = []

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": artifact_kind,
        "band": band,
        "selection": {"mode": "ids" if ids else "all", "ids": ids},
        "profile_status": "profile_gap",
        "profile_gap_kind": "route_affordance_alias",
        "summary": {
            "row_count": 0,
            "total_available": 0,
            "query_used": False,
            "selection_method": "route_affordance_alias_card",
        },
        "rows": [],
        "warnings": [
            {
                "kind": "unsupported_alias_with_canonical_routes",
                "message": message,
                "title": title,
            }
        ],
        "next": next_steps,
        "route_card": {
            "alias": artifact_kind,
            "status": "unsupported_by_design_helpful_route",
            "claim": title,
            "canonical_routes": next_steps,
            "mode_cards": mode_cards,
            "closure_note": (
                "This is a route-affordance response, not evidence that the underlying raw-seed surfaces are absent."
            ),
        },
        "source_refs": [_relative(repo_root / str(path), repo_root) for path in source_refs],
    }


# When a task_ledger cluster_flag row covers ≤ this many WorkItems, the
# cluster surfaces every id in `top_ids` instead of the compact 3-id digest.
# Triage agents reading the cluster_flag projection can then see all
# candidates without an extra `--band flag --ids <top_ids>` drilldown for
# small queues like execution_menu (cap 7), execution_menu_schedulable,
# promotion_candidates, provider_assignable, metabolic_running,
# meta_mission_active, blocked, bridge_assignable, legacy_snapshot_unmodeled,
# and active_wip. Larger clusters (operator_needed ~38, work_ledger_unlinked,
# needs_signoff, propagation_needed, merge_or_retire_candidates, signoffs,
# unlocks_by_rank, missing_*_contract, capture_inbox/triage, dependency_graph)
# keep the 3-id digest so the projection stays bounded for capture_inbox-scale
# rows. Downstream consumers (navigation_context_pack.trim_clusters,
# raw_seed_compressed_projection, annex_navigation_dogfood, etc.) all
# self-bound their own slices, so widening here does not cascade into
# other surfaces.
TASK_LEDGER_CLUSTER_FULL_TOP_IDS_THRESHOLD = 12
TASK_LEDGER_CLUSTER_DIGEST_TOP_IDS = 3

TASK_LEDGER_VIEW_DEFS: tuple[tuple[str, str, str], ...] = (
    ("execution_menu", "Execution Menu", "explicitly promoted or claimed WorkItems eligible for execution"),
    ("execution_menu_schedulable", "Execution Menu Schedulable", "execution-menu WorkItems whose hard dependencies are satisfied"),
    ("promotion_candidates", "Promotion Candidates", "shaped captures that need review before commitment"),
    ("schedulable_by_rank", "Schedulable By Rank", "ready or accepted WorkItems whose hard dependencies are satisfied"),
    ("dependency_blocked", "Dependency Blocked", "ready or execution-relevant WorkItems blocked by unsatisfied hard dependencies"),
    ("dependency_anomalies", "Dependency Anomalies", "dangling ids, self-deps, cycles, and routing inconsistencies in the WorkItem graph"),
    ("dependency_graph", "Dependency Graph", "all WorkItems as dependency nodes with typed edge status and downstream unlocks"),
    ("unlocks_by_rank", "Unlocks By Rank", "upstream WorkItems ordered by rank whose completion or resolution unlocks downstream WorkItems"),
    ("ready_by_rank", "Ready By Rank", "ranked WorkItems that are ready for local action"),
    ("active_wip", "Active WIP", "currently active WorkItems"),
    ("blocked", "Blocked", "WorkItems blocked by authority, dependency, or evidence gaps"),
    ("operator_needed", "Operator Needed", "WorkItems waiting on operator authority or signoff posture"),
    ("bridge_assignable", "Bridge Assignable", "WorkItems shaped for bridge delegation or bridge evidence"),
    ("provider_assignable", "Provider Assignable", "WorkItems shaped for provider jobs or provider receipts"),
    ("metabolic_running", "Metabolic Running", "background reflex WorkItems and recurring metabolism lanes"),
    ("meta_mission_active", "Meta-Mission Active", "foreground bounded campaign WorkItems"),
    (
        "mission_operating_picture",
        "Mission Operating Picture",
        "graph-shaped read model over current missions, execution candidates, dependencies, and umbrella gaps",
    ),
    (
        "cap_census",
        "Cap Census",
        "cap-universe read model reconciling cap_ namespace rows, typed caps, proof, integration, and current operating-picture membership",
    ),
    (
        "cap_cartography",
        "Cap Cartography",
        "map-ready cap-universe read model with clusters, representative nodes, typed edges, lineage, and level-of-detail hints",
    ),
    ("capture_triage", "Capture Triage", "captured items grouped by shaping and merge/retire needs"),
    (
        "capture_inbox",
        "Capture Inbox",
        "complete low-friction capture log; use raw_capture_inbox_count for active untriaged pressure",
    ),
    ("missing_contracts_ranked", "Missing Contracts Ranked", "items needing contract shaping before execution"),
    ("missing_satisfaction_contract", "Missing Satisfaction Contract", "WorkItems missing served-outcome proof"),
    ("missing_integration_contract", "Missing Integration Contract", "WorkItems missing exact landing surfaces"),
    ("incomplete_work_items", "Incomplete WorkItems", "WorkItems missing contract, completion, or signoff requirements"),
    ("needs_signoff", "Needs Signoff", "finished or signoff-ready items still requiring Task Ledger closeout"),
    ("propagation_needed", "Propagation Needed", "closed WorkItems with generalization signals awaiting propagation disposition"),
    ("merge_or_retire_candidates", "Merge Or Retire Candidates", "captures likely duplicated, stale, or superseded"),
    ("legacy_snapshot_unmodeled", "Legacy Snapshot Unmodeled", "legacy rows whose fields still need event-model adoption"),
    ("prompt_trace_unlinked", "Prompt Trace Unlinked", "WorkItems without adopted prompt trace provenance"),
    ("work_ledger_unlinked", "Work Ledger Unlinked", "WorkItems without execution/concurrency linkage"),
    ("stale_review", "Stale Review", "aging traces that need defer, refresh, merge, block, or retire decisions"),
    ("recent_events", "Recent Events", "latest Task Ledger event stream for organizer replay"),
    ("signoffs", "Signoffs", "completed WorkItem signoff records for consolidation review"),
)

TASK_LEDGER_DEFAULT_ORGANIZER_ROUTE: dict[str, Any] = {
    "organizer_role": "planning_memory",
    "organizer_actions": ["inspect", "shape", "promote", "defer", "retire"],
    "recommended_next_events": ["work_item.triaged", "work_item.note_added"],
    "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
    "common_file_hints": [str(TASK_LEDGER_STANDARD), str(TASK_LEDGER_SKILL)],
}

TASK_LEDGER_EVENT_COMMAND_HINTS: dict[str, str] = {
    "work_item.captured": "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --title <title> --statement <statement> --rebuild",
    "work_item.triaged": "./repo-python tools/meta/factory/task_ledger_apply.py triage --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.promoted": "./repo-python tools/meta/factory/task_ledger_apply.py promote --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.shaped": "./repo-python tools/meta/factory/task_ledger_apply.py shape --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.claimed": "./repo-python tools/meta/factory/task_ledger_apply.py claim --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.released": "./repo-python tools/meta/factory/task_ledger_apply.py release --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.note_added": "./repo-python tools/meta/factory/task_ledger_apply.py note --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.state_transitioned": "./repo-python tools/meta/factory/task_ledger_apply.py transition --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.blocked": "./repo-python tools/meta/factory/task_ledger_apply.py block --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.unblocked": "./repo-python tools/meta/factory/task_ledger_apply.py unblock --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.rerank_proposed": "./repo-python tools/meta/factory/task_ledger_apply.py rerank-propose --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.rerank_committed": "./repo-python tools/meta/factory/task_ledger_apply.py rerank-commit --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.signoff_recorded": "./repo-python tools/meta/factory/task_ledger_apply.py sign-off --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.bridge_delegated": "./repo-python tools/meta/factory/task_ledger_apply.py bridge-delegate --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.provider_job_created": "./repo-python tools/meta/factory/task_ledger_apply.py provider-job-create --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.schema_migrated": "./repo-python tools/meta/factory/task_ledger_apply.py schema-migrate --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.propagation_recorded": "./repo-python tools/meta/factory/task_ledger_apply.py propagate --subject-id <work_item_id> --payload-json '<json>' --rebuild",
    "work_item.retired": "./repo-python tools/meta/factory/task_ledger_apply.py retire --subject-id <work_item_id> --payload-json '<json>' --rebuild",
}

TASK_LEDGER_ORGANIZER_ROUTES: dict[str, dict[str, Any]] = {
    "capture_inbox": {
        "organizer_role": "salience_inbox",
        "cluster_claim": "Cheap observations land here as an append-only capture log; total count includes closed and shaped audit rows, while raw_capture_inbox_count is the active untriaged pressure.",
        "organizer_actions": ["triage", "merge", "shape", "defer", "retire"],
        "recommended_next_events": ["work_item.triaged", "work_item.shaped", "work_item.retired"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), "operator_prompt", "raw_seed", "prompt_trace"],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), str(TASK_LEDGER_SKILL)],
    },
    "capture_triage": {
        "organizer_role": "gating_triage",
        "cluster_claim": "Organizer pass turns captured traces into shape, promote, block, merge, or retire decisions.",
        "organizer_actions": ["shape", "promote", "block", "merge", "retire"],
        "recommended_next_events": ["work_item.triaged", "work_item.shaped", "work_item.promoted", "work_item.retired"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_VIEWS_ROOT / "capture_inbox.json")],
        "common_file_hints": [
            str(TASK_LEDGER_STANDARD),
            str(TASK_LEDGER_SKILL),
            str(TASK_LEDGER_PAPER_MODULE),
        ],
    },
    "execution_menu": {
        "organizer_role": "commitment_boundary",
        "cluster_claim": "Only WorkItems with explicit promote, claim, state-transition, or rerank-commit events belong in the execution menu.",
        "organizer_actions": ["claim", "execute", "block", "defer", "retire_if_obsolete"],
        "recommended_next_events": ["work_item.claimed", "work_item.state_transitioned", "work_item.blocked", "work_item.retired"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), "codex/ledger/<phase_id>/work_ledger.jsonl"],
    },
    "execution_menu_schedulable": {
        "organizer_role": "dependency_scheduling",
        "cluster_claim": "Committed WorkItems here retain execution-menu authority and have satisfied hard dependencies.",
        "organizer_actions": ["claim", "execute", "block_if_new_dependency", "record_dependency_resolution"],
        "recommended_next_events": ["work_item.claimed", "work_item.state_transitioned", "work_item.blocked", "work_item.shaped"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_VIEWS_ROOT / "execution_menu.json")],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), "system/lib/task_ledger_events.py"],
        "salience_boundary": "Schedulability is a dependency filter over execution-menu authority; it does not replace rank, owner, or Work Ledger claim checks.",
    },
    "promotion_candidates": {
        "organizer_role": "promotion_review",
        "cluster_claim": "Shaped captures here are review candidates; they are not implementation commitments until promoted or claimed.",
        "organizer_actions": ["promote", "shape_completion", "block", "retire"],
        "recommended_next_events": ["work_item.promoted", "work_item.shaped", "work_item.blocked", "work_item.retired"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_VIEWS_ROOT / "capture_triage.json")],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), str(TASK_LEDGER_SKILL)],
        "salience_boundary": "Promotion candidates are attention-ready, not commitment-ready; execution priority starts only after promotion, claim, or explicit operator/controller override.",
    },
    "missing_contracts_ranked": {
        "organizer_role": "contract_shaping",
        "cluster_claim": "Items here need explicit satisfaction, integration, or completion contracts before execution.",
        "organizer_actions": ["shape", "request_evidence", "block", "defer"],
        "recommended_next_events": ["work_item.shaped", "work_item.blocked", "work_item.note_added"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), str(TASK_LEDGER_SKILL)],
    },
    "missing_satisfaction_contract": {
        "organizer_role": "satisfaction_shaping",
        "cluster_claim": "Items here lack the served outcome and proof of satisfaction.",
        "organizer_actions": ["shape", "request_operator_evidence", "block", "retire"],
        "recommended_next_events": ["work_item.shaped", "work_item.blocked", "work_item.retired"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), "raw_seed", "operator_prompt"],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), "codex/doctrine/principles"],
    },
    "missing_integration_contract": {
        "organizer_role": "landing_surface_shaping",
        "cluster_claim": "Items here lack exact substrate surfaces and anti-parallel-board checks.",
        "organizer_actions": ["discover_surfaces", "shape", "block", "retire"],
        "recommended_next_events": ["work_item.shaped", "work_item.blocked", "work_item.retired"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), "system/lib", "tools/meta/factory"],
    },
    "incomplete_work_items": {
        "organizer_role": "completion_gap_review",
        "cluster_claim": "Items here are not yet safe to treat as complete or implementation-ready.",
        "organizer_actions": ["shape", "signoff", "block", "retire"],
        "recommended_next_events": ["work_item.shaped", "work_item.signoff_recorded", "work_item.blocked"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), str(TASK_LEDGER_SKILL)],
    },
    "needs_signoff": {
        "organizer_role": "consolidation",
        "cluster_claim": "Finished or signoff-ready work needs evidence, lessons, and residual capture.",
        "organizer_actions": ["signoff", "capture_residual", "propagate", "retire"],
        "recommended_next_events": [
            "work_item.signoff_recorded",
            "work_item.propagation_recorded",
            "work_item.captured",
        ],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_VIEWS_ROOT / "signoffs.json")],
        "common_file_hints": [str(TASK_LEDGER_SKILL), "codex/doctrine/skills/doctrine/local_to_general_propagation.md"],
    },
    "propagation_needed": {
        "organizer_role": "local_to_general_disposition",
        "cluster_claim": (
            "Closed WorkItems with generalization signals need owner-surface actuation or "
            "verification before propagation or an explicit nothing_to_refine receipt."
        ),
        "organizer_actions": [
            "inspect_owner_surface",
            "patch_or_verify_owner",
            "propagate",
            "record_nothing_to_refine",
        ],
        "recommended_next_events": ["work_item.propagation_recorded"],
        "common_source_surfaces": [
            str(TASK_LEDGER_EVENTS),
            str(TASK_LEDGER_VIEWS_ROOT / "propagation_needed.json"),
            "state/task_ledger/sign_offs.json",
        ],
        "common_file_hints": [
            "codex/doctrine/skills/doctrine/local_to_general_propagation.md",
            str(TASK_LEDGER_SKILL),
        ],
        "salience_boundary": (
            "Propagation-needed rows are consolidation obligations, not execution priority; "
            "organizer-report should route to the owner surface before mutation receipts."
        ),
    },
    "merge_or_retire_candidates": {
        "organizer_role": "trace_evaporation",
        "cluster_claim": "Closed, duplicate, stale, or superseded traces should not keep reinforcing the execution menu.",
        "organizer_actions": ["merge", "retire", "leave_closed", "link_as_evidence"],
        "recommended_next_events": ["work_item.retired", "work_item.note_added", "work_item.propagation_recorded"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_VIEWS_ROOT / "capture_triage.json")],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), str(TASK_LEDGER_SKILL)],
        "governance_route": {
            "owner_view": str(TASK_LEDGER_VIEWS_ROOT / "merge_or_retire_candidates.json"),
            "owner_report": "task_ledger_apply.py organizer-report::merge_or_retire_diagnostic",
            "decision_authority": "merge and supersede are dispositions represented by supported retire, note, propagation, shape, or capture events; direct merge/supersede events are not apply-lane affordances.",
            "review_required_for": ["semantic_duplicate_capture_group", "canonical-row selection", "retiring open work"],
        },
    },
    "stale_review": {
        "organizer_role": "trace_evaporation",
        "cluster_claim": "Aging traces require refresh, merge, block, or retirement before they pollute planning.",
        "organizer_actions": ["refresh", "merge", "block", "retire"],
        "recommended_next_events": ["work_item.note_added", "work_item.blocked", "work_item.retired"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), str(TASK_LEDGER_SKILL)],
    },
    "prompt_trace_unlinked": {
        "organizer_role": "provenance_linkage",
        "cluster_claim": "WorkItems here need prompt provenance adoption or an explicit no-link receipt.",
        "organizer_actions": ["link_prompt_trace", "note_no_link", "shape"],
        "recommended_next_events": ["work_item.note_added", "work_item.shaped", "work_item.propagation_recorded"],
        "common_source_surfaces": ["state/prompt_ledger/events.jsonl", "state/prompt_shelf"],
        "common_file_hints": ["state/prompt_ledger/views", "state/prompt_shelf/uppropagation_index.json"],
    },
    "work_ledger_unlinked": {
        "organizer_role": "execution_linkage",
        "cluster_claim": "Active or signoff work without execution receipts needs Work Ledger linkage or an explicit exception.",
        "organizer_actions": ["link_work_ledger", "close_session", "note_exception"],
        "recommended_next_events": ["work_item.claimed", "work_item.note_added", "work_item.signoff_recorded"],
        "common_source_surfaces": ["codex/ledger/<phase_id>/work_ledger.jsonl", "state/work_ledger/runtime_status.json"],
        "common_file_hints": ["codex/ledger/<phase_id>/work_ledger_index.json", "tools/meta/factory/work_ledger.py"],
    },
    "active_wip": {
        "organizer_role": "operations_watch",
        "cluster_claim": "Currently active WorkItems need owner, claim, and closeout discipline.",
        "organizer_actions": ["continue", "block", "release", "signoff"],
        "recommended_next_events": ["work_item.note_added", "work_item.blocked", "work_item.released", "work_item.signoff_recorded"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), "state/work_ledger/runtime_status.json"],
        "common_file_hints": ["tools/meta/factory/work_ledger.py", str(TASK_LEDGER_SKILL)],
    },
    "blocked": {
        "organizer_role": "blocker_review",
        "cluster_claim": "Blocked WorkItems need owner evidence, dependency resolution, or retirement.",
        "organizer_actions": ["unblock", "request_owner", "defer", "retire"],
        "recommended_next_events": ["work_item.unblocked", "work_item.note_added", "work_item.retired"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), str(TASK_LEDGER_SKILL)],
    },
    "operator_needed": {
        "organizer_role": "authority_gate",
        "cluster_claim": "Rows here need operator judgment before the system can safely decide.",
        "organizer_actions": ["request_operator", "block", "signoff"],
        "recommended_next_events": ["work_item.note_added", "work_item.blocked", "work_item.signoff_recorded"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), "operator_prompt"],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), str(TASK_LEDGER_SKILL)],
    },
    "ready_by_rank": {
        "organizer_role": "commitment_queue",
        "cluster_claim": "Ready ranked rows are eligible for execution after Work Ledger claim checks.",
        "organizer_actions": ["claim", "execute", "defer", "rerank"],
        "recommended_next_events": ["work_item.claimed", "work_item.state_transitioned", "work_item.rerank_committed"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), "tools/meta/factory/work_ledger.py"],
    },
    "schedulable_by_rank": {
        "organizer_role": "dependency_scheduling",
        "cluster_claim": "Ready rows here are rank-ordered and have satisfied hard WorkItem dependencies.",
        "organizer_actions": ["claim", "execute", "rerank", "record_dependency_resolution"],
        "recommended_next_events": ["work_item.claimed", "work_item.state_transitioned", "work_item.rerank_committed", "work_item.shaped"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_VIEWS_ROOT / "ready_by_rank.json")],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), "system/lib/task_ledger_priority.py"],
        "salience_boundary": "Schedulable means dependency-eligible; rank and operator authority still decide preference among eligible rows.",
    },
    "dependency_blocked": {
        "organizer_role": "dependency_blocker_review",
        "cluster_claim": "Rows here are otherwise execution-relevant but blocked by unsatisfied hard WorkItem dependencies.",
        "organizer_actions": ["complete_upstream", "rewire_dependency", "waive_dependency", "block"],
        "recommended_next_events": ["work_item.blocked", "work_item.shaped", "work_item.note_added"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), "system/lib/task_ledger_events.py"],
        "salience_boundary": "Dependency-blocked rows are not execution candidates until their hard dependency status is resolved.",
    },
    "dependency_anomalies": {
        "organizer_role": "dependency_graph_hygiene",
        "cluster_claim": "Graph anomalies need repair before dependency-aware routing can be trusted.",
        "organizer_actions": ["repair_edge", "rewire_dependency", "record_resolution", "audit_reducer"],
        "recommended_next_events": ["work_item.shaped", "work_item.note_added", "work_item.blocked"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), "tools/meta/factory/task_ledger_apply.py", "system/lib/task_ledger_events.py"],
        "salience_boundary": "Anomaly rows are graph hygiene evidence, not execution priority.",
    },
    "dependency_graph": {
        "organizer_role": "dependency_map",
        "cluster_claim": "All WorkItems as dependency graph nodes with hard-edge status, broad dependency context, and downstream unlocks.",
        "organizer_actions": ["inspect", "trace_downstream", "repair_edge"],
        "recommended_next_events": ["work_item.note_added", "work_item.shaped"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), "system/lib/task_ledger_events.py"],
        "salience_boundary": "Graph membership is browse context; use schedulable views for execution eligibility.",
    },
    "unlocks_by_rank": {
        "organizer_role": "unlock_impact_review",
        "cluster_claim": "Upstream WorkItems here have downstream rows waiting on their completion or explicit resolution.",
        "organizer_actions": ["complete_upstream", "record_resolution", "inspect_downstream"],
        "recommended_next_events": ["work_item.state_transitioned", "work_item.signoff_recorded", "work_item.shaped"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_VIEWS_ROOT / "dependency_graph.json")],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), "system/lib/task_ledger_events.py"],
        "salience_boundary": "Unlock count is impact context, not a replacement for rank or operator intent.",
    },
    "bridge_assignable": {
        "organizer_role": "delegation_queue",
        "cluster_claim": "Bridge-shaped rows need packet, evidence, and receipt boundaries before delegation.",
        "organizer_actions": ["delegate", "shape_packet", "block"],
        "recommended_next_events": ["work_item.shaped", "work_item.blocked", "work_item.bridge_delegated"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), "bridge_receipts"],
        "common_file_hints": ["tools/meta/bridge", str(TASK_LEDGER_STANDARD)],
    },
    "provider_assignable": {
        "organizer_role": "provider_queue",
        "cluster_claim": "Provider-shaped rows need receipt requirements before external model work.",
        "organizer_actions": ["create_provider_job", "shape_receipt", "block"],
        "recommended_next_events": ["work_item.shaped", "work_item.blocked", "work_item.provider_job_created"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), "state/provider_receipts"],
        "common_file_hints": ["system/lib/type_a_worker_harness.py", "system/lib/compute_throughput.py"],
    },
    "metabolic_running": {
        "organizer_role": "recurring_reflex_watch",
        "cluster_claim": "Background reflexes need cadence, owner, and closeout receipts distinct from foreground missions.",
        "organizer_actions": ["inspect_cadence", "block", "signoff"],
        "recommended_next_events": ["work_item.note_added", "work_item.blocked", "work_item.signoff_recorded"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), "state/work_ledger/runtime_status.json"],
        "common_file_hints": ["system/lib/metabolism_scheduler.py", str(TASK_LEDGER_STANDARD)],
    },
    "meta_mission_active": {
        "organizer_role": "foreground_campaign_watch",
        "cluster_claim": "Foreground campaigns stay WorkItems, not parallel boards.",
        "organizer_actions": ["shape_campaign", "claim", "block", "signoff"],
        "recommended_next_events": ["work_item.shaped", "work_item.claimed", "work_item.blocked", "work_item.signoff_recorded"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), "state/mission_blackboard/board.json"],
        "common_file_hints": ["codex/standards/std_autonomy_runtime.json", "codex/standards/std_meta_mission_queue.json"],
    },
    "mission_operating_picture": {
        "organizer_role": "mission_operating_picture_review",
        "cluster_claim": "The Mission Operating Picture is a projection over Task Ledger and mission-blackboard authority; it reveals current mission pressure and missing umbrella refs without mutating WorkItems.",
        "organizer_actions": ["inspect_projection", "select_mission_slice", "shape_umbrella_refs", "block_if_authority_missing"],
        "recommended_next_events": ["work_item.shaped", "work_item.blocked", "work_item.note_added"],
        "common_source_surfaces": [
            str(TASK_LEDGER_EVENTS),
            str(TASK_LEDGER_VIEWS_ROOT / "mission_operating_picture.json"),
            "state/mission_blackboard/board.json",
        ],
        "common_file_hints": [
            "system/lib/task_ledger_events.py",
            "system/lib/standard_option_surface.py",
            str(TASK_LEDGER_STANDARD),
        ],
        "salience_boundary": "This view is an operating-picture read model; Task Ledger events remain authority and umbrella population belongs in a later apply/reducer slice.",
    },
    "cap_census": {
        "organizer_role": "cap_universe_census",
        "cluster_claim": "Cap Census is the source-of-truth reconciliation between the broad cap_ namespace, strict typed-cap rows, current operating-picture membership, and proof/integration readiness.",
        "organizer_actions": ["inspect_projection", "select_cap_slice", "shape_contracts", "block_if_authority_missing"],
        "recommended_next_events": ["work_item.shaped", "work_item.blocked", "work_item.note_added"],
        "common_source_surfaces": [
            str(TASK_LEDGER_EVENTS),
            str(TASK_LEDGER_VIEWS_ROOT / "cap_census.json"),
            str(TASK_LEDGER_VIEWS_ROOT / "mission_operating_picture.json"),
        ],
        "common_file_hints": [
            "system/lib/task_ledger_events.py",
            "system/lib/standard_option_surface.py",
            str(TASK_LEDGER_STANDARD),
        ],
        "salience_boundary": "This view explains the cap universe; it does not create caps, rank work, or replace Mission Operating Picture as the current operating subset.",
    },
    "cap_cartography": {
        "organizer_role": "cap_cartography_review",
        "cluster_claim": "Cap Cartography is the frontend-agnostic map contract for the broad cap universe: clusters, bounded representative nodes, typed source-evidenced edges, lineage, and level-of-detail hints.",
        "organizer_actions": ["inspect_projection", "select_cluster", "trace_lineage", "shape_contracts"],
        "recommended_next_events": ["work_item.shaped", "work_item.note_added"],
        "common_source_surfaces": [
            str(TASK_LEDGER_EVENTS),
            str(TASK_LEDGER_VIEWS_ROOT / "cap_cartography.json"),
            str(TASK_LEDGER_VIEWS_ROOT / "cap_census.json"),
            str(TASK_LEDGER_VIEWS_ROOT / "mission_operating_picture.json"),
        ],
        "common_file_hints": [
            "system/lib/task_ledger_events.py",
            "system/lib/standard_option_surface.py",
            str(TASK_LEDGER_STANDARD),
        ],
        "salience_boundary": "This view is map-ready substrate for downstream exposition; it is not a frontend route, cap CRUD surface, or source authority.",
    },
    "legacy_snapshot_unmodeled": {
        "organizer_role": "migration_review",
        "cluster_claim": "Legacy fields need adoption into event payloads or retirement as old evidence.",
        "organizer_actions": ["migrate", "note_legacy_boundary", "retire"],
        "recommended_next_events": ["work_item.note_added", "work_item.retired", "work_item.schema_migrated"],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), str(TASK_LEDGER_LEDGER)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), "system/lib/task_ledger_events.py"],
    },
    "recent_events": {
        "organizer_role": "memory_replay",
        "cluster_claim": "Recent event replay lets organizer passes consolidate without treating every new trace as next work.",
        "organizer_actions": ["replay", "link", "capture_residual", "retire"],
        "recommended_next_events": [
            "work_item.note_added",
            "work_item.retired",
            "work_item.captured",
        ],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS)],
        "common_file_hints": [str(TASK_LEDGER_STANDARD), str(TASK_LEDGER_SKILL)],
    },
    "signoffs": {
        "organizer_role": "after_action_memory",
        "cluster_claim": "Signoffs are consolidation evidence and source material for propagation, not new priority claims.",
        "organizer_actions": ["propagate", "capture_residual", "link_evidence"],
        "recommended_next_events": [
            "work_item.propagation_recorded",
            "work_item.note_added",
            "work_item.captured",
        ],
        "common_source_surfaces": [str(TASK_LEDGER_EVENTS), "state/task_ledger/sign_offs.json"],
        "common_file_hints": ["codex/doctrine/skills/doctrine/local_to_general_propagation.md", str(TASK_LEDGER_SKILL)],
    },
}


def _task_ledger_items(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("work_items")
    if not isinstance(items, list):
        items = payload.get("items")
    return [item for item in items or [] if isinstance(item, dict)]


def _task_ledger_source_refs(item: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    for ref in item.get("evidence_refs") or []:
        if isinstance(ref, str):
            refs.append(ref)
        elif isinstance(ref, Mapping):
            value = ref.get("ref")
            if value:
                refs.append(str(value))
    provenance = item.get("provenance")
    if isinstance(provenance, Mapping):
        for key in ("source_ref", "discovery_receipt"):
            value = provenance.get(key)
            if value:
                refs.append(str(value))
        source_refs = provenance.get("source_refs")
        if isinstance(source_refs, list):
            refs.extend(str(value) for value in source_refs if value)
    for event_id in item.get("source_event_ids") or []:
        if event_id:
            refs.append(f"state/task_ledger/events.jsonl::{event_id}")
    return list(dict.fromkeys(refs))


def _task_ledger_contract_refs(item: Mapping[str, Any]) -> dict[str, Any]:
    satisfaction = item.get("satisfaction_contract")
    integration = item.get("integration_contract")
    completion = item.get("completion")
    closeout_assurance = item.get("closeout_assurance")
    refs: dict[str, Any] = {
        "satisfaction_refs": list(satisfaction.get("satisfaction_refs") or []) if isinstance(satisfaction, Mapping) else [],
        "raw_seed_refs": list(satisfaction.get("raw_seed_refs") or []) if isinstance(satisfaction, Mapping) else [],
        "imagined_state_refs": list(satisfaction.get("imagined_state_refs") or []) if isinstance(satisfaction, Mapping) else [],
        "integration_paths": list(integration.get("exact_paths") or []) if isinstance(integration, Mapping) else [],
        "acceptance_checks": list(completion.get("acceptance_checks") or []) if isinstance(completion, Mapping) else [],
        "depends_on": [str(value) for value in item.get("depends_on") or [] if value],
        "dependencies": [str(value) for value in item.get("dependencies") or [] if value],
    }
    if isinstance(closeout_assurance, Mapping) and closeout_assurance:
        refs["closeout_evidence_refs"] = list(closeout_assurance.get("evidence_refs") or [])
        refs["closeout_counterexample_checks"] = list(closeout_assurance.get("counterexample_checks") or [])
        strength = closeout_assurance.get("corrective_action_strength")
        if strength:
            refs["corrective_action_strength"] = strength
        blocked = closeout_assurance.get("blocked_primary_continuation")
        if isinstance(blocked, Mapping) and blocked:
            receipt = blocked.get("receipt") if isinstance(blocked.get("receipt"), Mapping) else {}
            validation = blocked.get("validation") if isinstance(blocked.get("validation"), Mapping) else {}
            continuation_status = blocked.get("status") or validation.get("status")
            validation_status = validation.get("status")
            selected = blocked.get("selected_legal_continuation") or receipt.get("selected_legal_continuation")
            reentry = blocked.get("reentry_condition") or receipt.get("reentry_condition")
            if continuation_status:
                refs["blocked_primary_continuation_status"] = continuation_status
            if validation_status:
                refs["blocked_primary_validation_status"] = validation_status
            if selected:
                refs["blocked_primary_selected_legal_continuation"] = selected
            if reentry:
                refs["blocked_primary_reentry_condition"] = reentry
            standard_ref = (
                blocked.get("standard_ref")
                or validation.get("standard_ref")
                or receipt.get("standard_ref")
            )
            if standard_ref:
                refs["blocked_primary_standard_ref"] = standard_ref
    return refs


def _task_ledger_view_item_ids(items: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for item in items:
        item_id = item.get("id")
        if item_id:
            ids.append(str(item_id))
        group_ids = item.get("item_ids")
        if isinstance(group_ids, list):
            ids.extend(str(value) for value in group_ids if value)
    return list(dict.fromkeys(ids))


def _task_ledger_source_surface(ref: str) -> str:
    lowered = ref.lower()
    if ref.startswith("state/task_ledger/events.jsonl::"):
        return str(TASK_LEDGER_EVENTS)
    if "prompt_ledger" in lowered:
        return "state/prompt_ledger/events.jsonl"
    if "prompt_shelf" in lowered:
        return "state/prompt_shelf"
    if "work_ledger" in lowered or ref.startswith("codex/ledger/"):
        return "codex/ledger/<phase_id>/work_ledger.jsonl"
    if "raw_seed" in lowered:
        return "raw_seed"
    if ref.startswith("conversation:"):
        return "operator_prompt"
    if ref.startswith("OPERATOR_VOICE") or "operator_voice" in lowered:
        return "operator_prompt"
    if ref.startswith("TYPE_B_PACKET") or ref.startswith("codex_chat") or ref.startswith("codex_"):
        return "prompt_trace"
    if "/" in ref and not ref.startswith("http"):
        return ref.split("::", 1)[0]
    return ref


def _task_ledger_common_item_hints(
    item_ids: list[str],
    by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[str]]:
    source_surfaces: list[str] = []
    integration_paths: list[str] = []
    for item_id in item_ids:
        item = by_id.get(item_id)
        if not item:
            continue
        for ref in _task_ledger_source_refs(item):
            source_surfaces.append(_task_ledger_source_surface(ref))
        integration_paths.extend(_task_ledger_contract_refs(item)["integration_paths"])
    return {
        "source_surfaces": list(dict.fromkeys(source_surfaces))[:10],
        "integration_paths": list(dict.fromkeys(str(path) for path in integration_paths if path))[:10],
    }


def _task_ledger_routing_event_affordances(
    events: list[str],
    conceptual_events: list[str],
) -> dict[str, Any]:
    supported_events: list[str] = []
    supported_commands: list[dict[str, str]] = []
    unsupported_events: list[str] = []
    missing_refs: list[str] = []
    for event_type in dict.fromkeys(str(event) for event in events if event):
        command = TASK_LEDGER_EVENT_COMMAND_HINTS.get(event_type)
        if command:
            supported_events.append(event_type)
            supported_commands.append({"event_type": event_type, "command": command})
        else:
            unsupported_events.append(event_type)
    conceptual = list(
        dict.fromkeys(
            unsupported_events + [str(event) for event in conceptual_events if event]
        )
    )
    for event_type in conceptual:
        missing_refs.append(f"tools/meta/factory/task_ledger_apply.py::EVENT_BY_COMMAND lacks {event_type}")
    return {
        "recommended_next_events": supported_events,
        "supported_commands": supported_commands,
        "conceptual_next_events": conceptual,
        "missing_affordance_refs": missing_refs,
    }


def _task_ledger_organizer_routing(
    view_id: str,
    *,
    purpose: str,
    item_ids: list[str],
    by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    route = {
        **TASK_LEDGER_DEFAULT_ORGANIZER_ROUTE,
        **TASK_LEDGER_ORGANIZER_ROUTES.get(view_id, {}),
    }
    derived = _task_ledger_common_item_hints(item_ids, by_id)
    source_surfaces = list(
        dict.fromkeys(list(route.get("common_source_surfaces") or []) + derived["source_surfaces"])
    )[:12]
    integration_paths = derived["integration_paths"]
    file_hints = list(
        dict.fromkeys(list(route.get("common_file_hints") or []) + integration_paths)
    )[:12]
    affordances = _task_ledger_routing_event_affordances(
        list(route.get("recommended_next_events") or []),
        list(route.get("conceptual_next_events") or []),
    )
    return {
        "organizer_role": route.get("organizer_role"),
        "cluster_claim": route.get("cluster_claim") or purpose,
        "organizer_actions": list(route.get("organizer_actions") or []),
        "recommended_next_events": affordances["recommended_next_events"],
        "supported_commands": affordances["supported_commands"],
        "conceptual_next_events": affordances["conceptual_next_events"],
        "missing_affordance_refs": affordances["missing_affordance_refs"],
        "common_source_surfaces": source_surfaces,
        "common_integration_paths": integration_paths,
        "common_file_hints": file_hints,
        "routing_scent_not_authority": True,
        "governance_route": route.get("governance_route"),
        "salience_boundary": route.get("salience_boundary")
        or "View membership is an organizer signal, not priority authority; execution priority starts at execution_menu or explicit promote/claim/state-transition/rerank-commit evidence.",
    }


def _task_ledger_organizer_routing_cluster_summary(
    routing: Mapping[str, Any],
) -> dict[str, Any]:
    missing_affordance_refs = list(routing.get("missing_affordance_refs") or [])
    summary = {
        "organizer_role": routing.get("organizer_role"),
        "recommended_next_events": list(routing.get("recommended_next_events") or []),
        "conceptual_next_events": list(routing.get("conceptual_next_events") or []),
        "missing_affordance_count": len(missing_affordance_refs),
        "routing_scent_not_authority": True,
    }
    governance_route = routing.get("governance_route")
    if isinstance(governance_route, Mapping):
        summary["governance_route"] = {
            "owner_view": governance_route.get("owner_view"),
            "owner_report": governance_route.get("owner_report"),
            "review_required_count": len(governance_route.get("review_required_for") or []),
        }
    return summary


def _task_ledger_mechanism_cluster_rows(
    repo_root: Path,
    ledger_items: Sequence[Mapping[str, Any]],
    *,
    selected_cluster_ids: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    mechanisms = _mechanism_entries(repo_root)
    if not mechanisms:
        return []
    selected_ids = {str(item) for item in (selected_cluster_ids or []) if str(item or "")}
    match_index, unclassified = _mechanism_workitem_match_index(
        repo_root,
        mechanisms,
        ledger_items=ledger_items,
    )
    mechanisms_by_id = {
        str(mechanism.get("id") or ""): mechanism
        for mechanism in mechanisms
        if str(mechanism.get("id") or "")
    }
    rows: list[dict[str, Any]] = []
    ranked_mechanism_matches = sorted(
        match_index.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )
    if selected_ids:
        ranked_mechanism_matches = [
            item
            for item in ranked_mechanism_matches
            if item[0] in selected_ids or f"mechanism:{item[0]}" in selected_ids
        ]
    else:
        ranked_mechanism_matches = ranked_mechanism_matches[:MECHANISM_WORKITEM_CLUSTER_OVERVIEW_LIMIT]

    for mechanism_id, matches in ranked_mechanism_matches:
        mechanism = mechanisms_by_id.get(mechanism_id) or {}
        top_ids = _mechanism_workitem_cluster_top_ids(matches)
        reason_counts = Counter(
            reason
            for match in matches
            for reason in list(match.get("match_reasons") or [])
        )
        row: dict[str, Any] = {
            "row_id": f"task_ledger_mechanism_cluster:{mechanism_id}::cluster_flag",
            "cluster_id": f"mechanism:{mechanism_id}",
            "label": f"Mechanism / {mechanism.get('title') or mechanism_id}",
            "purpose": (
                "WorkItems whose text, tags, or refs deterministically match this mechanism; "
                "this is a clustering lens, not WorkItem authority."
            ),
            "artifact_kind": "task_ledger_mechanism_cluster",
            "band": "cluster_flag",
            "mechanism_id": mechanism_id,
            "mechanism_slug": mechanism.get("slug"),
            "mechanism_title": mechanism.get("title"),
            "count": len(matches),
            "top_ids": top_ids,
            "state_counts": dict(Counter(str(match.get("state") or "unknown") for match in matches)),
            "match_reason_counts": dict(reason_counts),
            "drilldown_command": (
                "./repo-python kernel.py --option-surface task_ledger --band flag --ids <top_ids>"
                if top_ids
                else "./repo-python kernel.py --option-surface task_ledger --band flag"
            ),
            "mechanism_drilldown_command": (
                f"./repo-python kernel.py --option-surface mechanisms --band card --ids {mechanism_id}"
            ),
            "source_ref": str(mechanism.get("_source_ref") or MECHANISM_DIR),
            "organizer_routing": {
                "organizer_role": "mechanism_pressure_cluster",
                "recommended_next_events": [
                    "work_item.shaped",
                    "work_item.note_added",
                    "work_item.retired",
                ],
                "conceptual_next_events": [],
                "missing_affordance_count": 0,
                "routing_scent_not_authority": True,
            },
        }
        rows.append(row)

    include_unclassified = not selected_ids or bool(
        {"mechanism:unclassified_pressure", "unclassified_pressure"} & selected_ids
    )
    if unclassified and include_unclassified:
        top_ids = _mechanism_workitem_cluster_top_ids(unclassified)
        rows.append(
            {
                "row_id": "task_ledger_mechanism_cluster:unclassified_pressure::cluster_flag",
                "cluster_id": "mechanism:unclassified_pressure",
                "label": "Mechanism / Unclassified Pressure",
                "purpose": (
                    "WorkItems that mention mechanisms but do not deterministically map to an existing mech_* row; "
                    "use this to shape, retire, or bind vague mechanism pressure."
                ),
                "artifact_kind": "task_ledger_mechanism_cluster",
                "band": "cluster_flag",
                "mechanism_id": None,
                "count": len(unclassified),
                "top_ids": top_ids,
                "state_counts": dict(Counter(str(match.get("state") or "unknown") for match in unclassified)),
                "match_reason_counts": {"generic_mechanism_pressure": len(unclassified)},
                "drilldown_command": (
                    "./repo-python kernel.py --option-surface task_ledger --band flag --ids <top_ids>"
                    if top_ids
                    else "./repo-python kernel.py --option-surface task_ledger --band flag"
                ),
                "source_ref": str(TASK_LEDGER_LEDGER),
                "organizer_routing": {
                    "organizer_role": "mechanism_pressure_triage",
                    "recommended_next_events": [
                        "work_item.shaped",
                        "work_item.note_added",
                        "work_item.retired",
                    ],
                    "conceptual_next_events": [],
                    "missing_affordance_count": 0,
                    "routing_scent_not_authority": True,
                },
            }
        )
    return rows


def _task_ledger_mechanism_cluster_overview(
    repo_root: Path,
    ledger_items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    mechanisms = _mechanism_entries(repo_root)
    if not mechanisms:
        return {
            "available_count": 0,
            "emitted_row_count": 0,
            "default_row_policy": "no_mechanism_index_available",
            "top_clusters": [],
        }

    match_index, unclassified = _mechanism_workitem_match_index(
        repo_root,
        mechanisms,
        ledger_items=ledger_items,
    )
    mechanisms_by_id = {
        str(mechanism.get("id") or ""): mechanism
        for mechanism in mechanisms
        if str(mechanism.get("id") or "")
    }
    ranked_mechanism_matches = sorted(
        match_index.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )
    available_count = len(ranked_mechanism_matches) + (1 if unclassified else 0)
    top_clusters: list[dict[str, Any]] = []
    for mechanism_id, matches in ranked_mechanism_matches[
        :MECHANISM_WORKITEM_CLUSTER_COMPACT_OVERVIEW_LIMIT
    ]:
        mechanism = mechanisms_by_id.get(mechanism_id) or {}
        top_clusters.append(
            {
                "cluster_id": f"mechanism:{mechanism_id}",
                "mechanism_id": mechanism_id,
                "mechanism_title": mechanism.get("title"),
                "count": len(matches),
                "top_ids": _mechanism_workitem_cluster_top_ids(matches)[
                    :MECHANISM_WORKITEM_CLUSTER_COMPACT_TOP_IDS
                ],
                "drilldown_command": (
                    "./repo-python kernel.py --option-surface task_ledger "
                    f"--band cluster_flag --ids mechanism:{mechanism_id}"
                ),
            }
        )
    return {
        "available_count": available_count,
        "emitted_row_count": 0,
        "default_row_policy": (
            "mechanism affinity clusters are summarized on the contents page and "
            "emitted as rows only through exact --ids mechanism:<mech_id> drilldown"
        ),
        "overview_limit": MECHANISM_WORKITEM_CLUSTER_COMPACT_OVERVIEW_LIMIT,
        "top_clusters": top_clusters,
        "unclassified_count": len(unclassified),
    }


def _task_ledger_views(repo_root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    view_payloads: dict[str, dict[str, Any]] = {}
    overlays: dict[str, dict[str, Any]] = {}
    for view_id, _label, _purpose in TASK_LEDGER_VIEW_DEFS:
        path = repo_root / TASK_LEDGER_VIEWS_ROOT / f"{view_id}.json"
        if not path.exists():
            continue
        payload = _load_json(path)
        view_payloads[view_id] = payload
        for index, row in enumerate(_task_ledger_items(payload), start=1):
            work_item_id = str(row.get("id") or "")
            if not work_item_id:
                continue
            overlay = overlays.setdefault(work_item_id, {"views": []})
            overlay["views"].append(view_id)
            overlay.setdefault("view_positions", {})[view_id] = index
            for key in (
                "triage_status",
                "recommended_action",
                "missing_fields",
                "categories",
                "linkage",
                "dependency_status",
                "depends_on",
                "dependencies",
                "downstream_unlock_ids",
                "unsatisfied_dep_ids",
                "dangling_dep_ids",
                "anomaly_refs",
                "in_execution_menu",
                "menu_rank",
                "rank",
                "required_next_event",
                "why_recommended",
            ):
                value = row.get(key)
                if value not in (None, [], {}, ""):
                    overlay.setdefault(key, value)
    return view_payloads, overlays


def _task_ledger_cluster_rows(
    repo_root: Path,
    ledger_items: list[dict[str, Any]],
    *,
    view_payloads: Mapping[str, Mapping[str, Any]],
    overlays: Mapping[str, Mapping[str, Any]],
    selected_cluster_ids: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_id = {str(item.get("id") or ""): item for item in ledger_items}
    for view_id, label, purpose in TASK_LEDGER_VIEW_DEFS:
        payload = view_payloads.get(view_id) or {}
        items = _task_ledger_items(payload)
        item_ids = _task_ledger_view_item_ids(items)
        # Surface every id when the cluster is small enough to enumerate
        # (≤ TASK_LEDGER_CLUSTER_FULL_TOP_IDS_THRESHOLD); otherwise keep the
        # compact digest so the projection stays bounded for huge clusters.
        if len(item_ids) <= TASK_LEDGER_CLUSTER_FULL_TOP_IDS_THRESHOLD:
            top_ids = list(item_ids)
        else:
            top_ids = item_ids[:TASK_LEDGER_CLUSTER_DIGEST_TOP_IDS]
        organizer_routing = _task_ledger_organizer_routing(
            view_id,
            purpose=purpose,
            item_ids=item_ids,
            by_id=by_id,
        )
        # Some task_ledger views (e.g. dependency_anomalies) carry an
        # anomaly_type field on each item rather than the standard work-item
        # state. Without a parallel summarization, state_counts collapses to
        # {"unknown": N} which is true but uninformative — the row reports
        # `state=unknown` for what is in fact a typed anomaly. Emit
        # anomaly_type_counts alongside when at least one item carries
        # anomaly_type so the cluster row becomes self-describing instead of
        # delegating discovery to a drilldown.
        anomaly_type_counter = Counter(
            str(item.get("anomaly_type"))
            for item in items
            if item.get("anomaly_type")
        )
        row: dict[str, Any] = {
            "row_id": f"task_ledger_view:{view_id}::cluster_flag",
            "cluster_id": view_id,
            "label": label,
            "purpose": purpose,
            "artifact_kind": "task_ledger_view",
            "band": "cluster_flag",
            "count": int(payload.get("count") or len(items)),
            "top_ids": top_ids,
            "state_counts": dict(Counter(str(item.get("state") or "unknown") for item in items)),
            "triage_counts": dict(Counter(str(item.get("triage_status") or "untriaged") for item in items)),
            "drilldown_command": (
                "./repo-python kernel.py --option-surface task_ledger --band flag --ids <top_ids>"
                if top_ids
                else "./repo-python kernel.py --option-surface task_ledger --band flag"
            ),
            "source_ref": f"{TASK_LEDGER_VIEWS_ROOT}/{view_id}.json",
            "organizer_routing": _task_ledger_organizer_routing_cluster_summary(
                organizer_routing
            ),
        }
        for key in (
            "count_semantics",
            "projection_semantics",
            "total_capture_count",
            "raw_capture_inbox_count",
            "active_raw_capture_count",
            "closed_or_signed_off_count",
        ):
            value = payload.get(key)
            if value not in (None, [], {}, ""):
                row[key] = value
        if anomaly_type_counter:
            row["anomaly_type_counts"] = dict(anomaly_type_counter)
        rows.append(row)
    if selected_cluster_ids:
        rows.extend(
            _task_ledger_mechanism_cluster_rows(
                repo_root,
                ledger_items,
                selected_cluster_ids=selected_cluster_ids,
            )
        )
    if not rows:
        state_counts = Counter(str(item.get("state") or "unknown") for item in ledger_items)
        for state, count in sorted(state_counts.items()):
            matching = [str(item.get("id")) for item in ledger_items if str(item.get("state") or "unknown") == state]
            top_ids = matching[:8]
            rows.append(
                {
                    "row_id": f"task_ledger_state:{state}::cluster_flag",
                    "cluster_id": state,
                    "label": state.replace("_", " ").title(),
                    "purpose": "fallback grouping from state/task_ledger/ledger.json",
                    "artifact_kind": "task_ledger_state",
                    "band": "cluster_flag",
                    "count": count,
                    "top_ids": top_ids,
                    "state_counts": {state: count},
                    "triage_counts": {},
                    "drilldown_command": f"./repo-python kernel.py --option-surface task_ledger --band flag --ids {','.join(top_ids)}",
                    "source_ref": str(TASK_LEDGER_LEDGER),
                }
            )
    return rows


def _task_ledger_flag_row(item: Mapping[str, Any], *, overlay: Mapping[str, Any]) -> dict[str, Any]:
    work_item_id = str(item.get("id") or "")
    completeness = item.get("projection_completeness") if isinstance(item.get("projection_completeness"), Mapping) else {}
    missing_fields = list(overlay.get("missing_fields") or [])
    linkage = overlay.get("linkage") if isinstance(overlay.get("linkage"), Mapping) else {}
    if not linkage:
        linkage = {
            "prompt_trace_linked": bool(completeness.get("has_prompt_trace_ref")),
            "work_ledger_linked": bool(completeness.get("has_work_ledger_claim_ref")),
        }
    return {
        "row_id": f"task_ledger:{work_item_id}::flag",
        "band": "flag",
        "id": work_item_id,
        "title": item.get("title"),
        "state": item.get("state") or item.get("status"),
        "work_item_type": item.get("work_item_type"),
        "candidate_work_item_type": item.get("candidate_work_item_type"),
        "tags": list(item.get("tags") or []),
        "confidence": item.get("confidence"),
        "created_by": item.get("created_by"),
        "triage_status": overlay.get("triage_status"),
        "recommended_action": overlay.get("recommended_action"),
        "missing_contracts": missing_fields,
        "dependency_status": overlay.get("dependency_status"),
        "source_refs": _task_ledger_source_refs(item)[:12],
        "linkage": linkage,
        "rank": overlay.get("rank") if overlay.get("rank") is not None else item.get("rank"),
        "views": list(overlay.get("views") or []),
        "updated_at": item.get("updated_at"),
        "drilldown_command": f"./repo-python kernel.py --option-surface task_ledger --band card --ids {work_item_id}",
    }


def _task_ledger_card_row(item: Mapping[str, Any], *, overlay: Mapping[str, Any]) -> dict[str, Any]:
    row = _task_ledger_flag_row(item, overlay=overlay)
    row["row_id"] = f"task_ledger:{row['id']}::card"
    row["band"] = "card"
    row["statement"] = item.get("statement")
    row["contracts"] = _task_ledger_contract_refs(item)
    row["dependency_status"] = overlay.get("dependency_status") or {
        "schedulable": None,
        "hard_dep_count": len(item.get("depends_on") or []),
        "satisfied_dep_ids": [],
        "unsatisfied_dep_ids": [],
        "dangling_dep_ids": [],
        "downstream_unlock_ids": [],
        "anomaly_refs": [],
    }
    row["completion"] = item.get("completion") if isinstance(item.get("completion"), Mapping) else {}
    row["closeout_assurance"] = (
        item.get("closeout_assurance") if isinstance(item.get("closeout_assurance"), Mapping) else {}
    )
    row["authority"] = item.get("authority") if isinstance(item.get("authority"), Mapping) else {}
    row["execution"] = item.get("execution") if isinstance(item.get("execution"), Mapping) else {}
    row["projection_completeness"] = item.get("projection_completeness") if isinstance(item.get("projection_completeness"), Mapping) else {}
    row["source_event_ids"] = list(item.get("source_event_ids") or [])
    row["omission_receipt"] = {
        "omitted": ["full raw event payload chain", "full source documents"],
        "reason": "The card row is a WorkItem decision surface. Use source_refs and source_event_ids for raw evidence.",
        "drilldown": f"jq '.work_items[] | select(.id==\"{row['id']}\")' state/task_ledger/ledger.json",
    }
    return row


def build_task_ledger_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        authority_health = task_ledger_events.authority_health(repo_root, ids=ids)
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="task_ledger",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    authority_ids = [] if band == "cluster_flag" else ids
    authority_health = task_ledger_events.authority_health(repo_root, ids=authority_ids)

    ledger_path = repo_root / TASK_LEDGER_LEDGER
    if not ledger_path.exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="task_ledger",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "Task Ledger projection is missing; rebuild state/task_ledger/ledger.json first.",
                "refs": [str(TASK_LEDGER_LEDGER)],
            }
        )
        payload["authority_health"] = authority_health
        return payload

    ledger = _load_json(ledger_path)
    ledger_items = _task_ledger_items(ledger)
    by_id = {str(item.get("id") or ""): item for item in ledger_items}
    view_payloads, overlays = _task_ledger_views(repo_root)

    if ids and band != "cluster_flag":
        rows_source = [by_id[item] for item in ids if item in by_id]
        missing_ids = [item for item in ids if item not in by_id]
        unrecovered_authority_gap_ids = [
            item
            for item in missing_ids
            if item in set(authority_health.get("lost_subject_ids") or [])
        ]
        if unrecovered_authority_gap_ids:
            missing_ids = [
                item
                for item in missing_ids
                if item not in set(unrecovered_authority_gap_ids)
            ]
    elif band == "card":
        execution_ids = [
            str(item.get("id"))
            for item in _task_ledger_items(view_payloads.get("execution_menu", {}))
            if item.get("id") in by_id
        ]
        rows_source = [by_id[item] for item in execution_ids]
        missing_ids = []
        unrecovered_authority_gap_ids = []
    else:
        rows_source = sorted(ledger_items, key=lambda item: (str(item.get("state") or ""), str(item.get("id") or "")))
        missing_ids = []
        unrecovered_authority_gap_ids = []

    if band == "cluster_flag":
        rows = _task_ledger_cluster_rows(
            repo_root,
            ledger_items,
            view_payloads=view_payloads,
            overlays=overlays,
            selected_cluster_ids=ids,
        )
        if ids:
            rows_by_view_id: dict[str, dict[str, Any]] = {}
            for row in rows:
                cluster_id = str(row.get("cluster_id") or "")
                mechanism_id = str(row.get("mechanism_id") or "")
                for key in (cluster_id, mechanism_id, f"mechanism:{mechanism_id}" if mechanism_id else ""):
                    if key:
                        rows_by_view_id[key] = row
            rows = [rows_by_view_id[item] for item in ids if item in rows_by_view_id]
            missing_ids = [item for item in ids if item not in rows_by_view_id]
            unrecovered_authority_gap_ids = []
    elif band == "card":
        rows = [_task_ledger_card_row(item, overlay=overlays.get(str(item.get("id") or ""), {})) for item in rows_source]
    else:
        rows = [_task_ledger_flag_row(item, overlay=overlays.get(str(item.get("id") or ""), {})) for item in rows_source]

    state_counts = Counter(str(item.get("state") or "unknown") for item in ledger_items)
    type_counts = Counter(str(item.get("work_item_type") or "unknown") for item in ledger_items)
    mechanism_cluster_overview = (
        _task_ledger_mechanism_cluster_overview(repo_root, ledger_items)
        if band == "cluster_flag"
        else {}
    )
    mechanism_cluster_row_count = (
        sum(
            1
            for row in rows
            if isinstance(row, Mapping)
            and row.get("artifact_kind") == "task_ledger_mechanism_cluster"
        )
        if band == "cluster_flag"
        else None
    )
    if band == "cluster_flag":
        mechanism_cluster_overview = dict(mechanism_cluster_overview)
        mechanism_cluster_overview["emitted_row_count"] = mechanism_cluster_row_count or 0
    warnings: list[dict[str, Any]] = []
    if authority_health.get("status") != "clean":
        warnings.append(
            {
                "kind": "task_ledger_authority_recovery_required",
                "message": "events_audit.jsonl contains events missing from events.jsonl; selected ids may be audit-durable but not projection-visible.",
                "unrecovered_authority_gap_ids": unrecovered_authority_gap_ids,
                "next_step": authority_health.get("next_step"),
            }
        )
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "task_ledger",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
            "unrecovered_authority_gap_ids": unrecovered_authority_gap_ids,
        },
        "profile_status": "supported",
        "authority_posture": "projection_browse_only_events_are_authority",
        "authority_health": authority_health,
        "governing_standard": {
            "ref": str(TASK_LEDGER_STANDARD),
            "schema_version": _load_json(repo_root / TASK_LEDGER_STANDARD).get("schema_version"),
            "owned_bands": ["cluster_flag", "flag", "card"],
        },
        "source_refs": [
            str(TASK_LEDGER_EVENTS),
            str(TASK_LEDGER_LEDGER),
            str(TASK_LEDGER_VIEWS_ROOT),
            str(MECHANISM_DIR),
            str(MECHANISM_STANDARD),
            str(TASK_LEDGER_STANDARD),
            str(TASK_LEDGER_SKILL),
            str(TASK_LEDGER_PAPER_MODULE),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(ledger_items),
            "query_used": False,
            "selection_method": (
                "task_ledger_view_cluster_overview"
                if band == "cluster_flag"
                else "task_ledger_work_item_enumeration"
            ),
            "drilldown_by": "view_id" if band == "cluster_flag" else "work_item_id",
            "state_counts": dict(sorted(state_counts.items())),
            "work_item_type_counts": dict(sorted(type_counts.items())),
            "view_count": len(view_payloads),
            "mechanism_cluster_count": mechanism_cluster_row_count,
            "mechanism_cluster_available_count": mechanism_cluster_overview.get(
                "available_count"
            )
            if band == "cluster_flag"
            else None,
            "mechanism_cluster_overview_limit": MECHANISM_WORKITEM_CLUSTER_OVERVIEW_LIMIT
            if band == "cluster_flag"
            else None,
            "mechanism_cluster_compact_overview_limit": MECHANISM_WORKITEM_CLUSTER_COMPACT_OVERVIEW_LIMIT
            if band == "cluster_flag"
            else None,
            "cluster_row_output_policy": (
                "compact_organizer_routing; repeated command templates are hoisted "
                "to event_command_hints and per-view source/file/integration lists "
                "are deferred to organizer-report or selected WorkItem flag/card rows; "
                "mechanism affinity clusters are summarized by default and exact "
                "mechanism:<mech_id> clusters are emitted by id drilldown"
            )
            if band == "cluster_flag"
            else None,
        },
        "mechanism_cluster_overview": mechanism_cluster_overview,
        "event_command_hints": dict(TASK_LEDGER_EVENT_COMMAND_HINTS)
        if band == "cluster_flag"
        else {},
        "cluster_organizer_routing_omission_receipt": {
            "omitted": [
                "per-row supported command templates",
                "per-row common source surface lists",
                "per-row common integration path lists",
                "per-row common file hint lists",
                "per-row missing affordance refs",
                "per-match mechanism affinity evidence beyond state/type/reason counts",
                "default mechanism affinity cluster rows beyond compact mechanism_cluster_overview",
            ],
            "reason": "cluster_flag is the Task Ledger contents page; repeated routing detail is hoisted or deferred to owner drilldowns.",
            "drilldowns": [
                "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2",
                "./repo-python kernel.py --option-surface task_ledger --band flag --ids <work_item_id>",
                "./repo-python kernel.py --option-surface task_ledger --band card --ids <work_item_id>",
                "./repo-python kernel.py --option-surface task_ledger --band cluster_flag --ids mechanism:<mech_id>",
            ],
        }
        if band == "cluster_flag"
        else {},
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "mutation_rule": "append Task Ledger events; never edit projection rows from this surface",
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2",
                "reason": "Read backlog health and safe actuation recommendation templates before portfolio mutation.",
            },
            {
                "command": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
                "reason": "Browse Task Ledger views before raw JSON or all-row WorkItem expansion.",
            },
            {
                "command": "./repo-python kernel.py --option-surface task_ledger --band card --ids <work_item_id>",
                "reason": "Open the selected WorkItem with contracts, source refs, linkage, and acceptance checks.",
            },
            {
                "command": "./repo-python tools/meta/factory/task_ledger_apply.py validate",
                "reason": "Validate the event log and deterministic projections before mutating WorkItems.",
            },
        ],
        "warnings": warnings,
    }


def _prompt_shelf_runs_meta(repo_root: Path) -> dict[str, Any]:
    return _load_prefixed_top_level_dict(repo_root / PROMPT_SHELF_RUNS_INDEX, "__meta")


def _prompt_shelf_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _prompt_shelf_counts(meta: Mapping[str, Any]) -> dict[str, Any]:
    by_slot = meta.get("by_slot") if isinstance(meta.get("by_slot"), Mapping) else {}
    return {
        "run_count": _prompt_shelf_int(meta.get("run_count")),
        "receipt_present_count": _prompt_shelf_int(meta.get("receipt_present_count")),
        "issues_total": _prompt_shelf_int(meta.get("issues_total")),
        "duplicate_prompt_run_id_count": len(meta.get("duplicate_prompt_run_ids") or []),
        "b3_linted_count": _prompt_shelf_int(meta.get("b3_linted_count")),
        "b3_lint_issue_run_count": _prompt_shelf_int(meta.get("b3_lint_issue_run_count")),
        "run_count_by_slot": dict(meta.get("run_count_by_slot") or {}),
        "slot_count": len(by_slot),
    }


def _prompt_shelf_metadata_base_row(repo_root: Path, *, band: str) -> dict[str, Any]:
    meta = _prompt_shelf_runs_meta(repo_root)
    projection_exists = (repo_root / PROMPT_SHELF_RUNS_INDEX).exists()
    tool_exists = (repo_root / PROMPT_SHELF_RUNS_INDEX_TOOL).exists()
    status = "metadata_projection_available" if projection_exists and tool_exists else "metadata_projection_missing_or_partial"
    counts = _prompt_shelf_counts(meta)
    generated_at = str(meta.get("generated_at") or "")
    return {
        "row_id": f"prompt_shelf_metadata:{PROMPT_SHELF_METADATA_ROW_ID}::{band}",
        "id": PROMPT_SHELF_METADATA_ROW_ID,
        "metadata_id": PROMPT_SHELF_METADATA_ROW_ID,
        "band": band,
        "title": "Prompt-Shelf Runs Metadata Index",
        "flag": (
            "Metadata-only owner route over prompt-shelf runs, receipts, slot coverage, "
            "and Type B extraction handles without opening raw run or event bodies."
        ),
        "summary": (
            "Use this card before raw prompt-shelf search when recovering Type B/private reasoning "
            "lessons, capture coverage, or extraction owner routes."
        ),
        "authority_posture": "metadata_projection_not_raw_prompt_authority",
        "projection_only": True,
        "disclosure_posture": "private_root_only",
        "source_ref": str(PROMPT_SHELF_RUNS_INDEX_TOOL),
        "source_refs": [
            str(PROMPT_SHELF_RUNS_INDEX_TOOL),
            str(PROMPT_SHELF_RUNS_INDEX),
            str(PROMPT_SHELF_LEDGER),
        ],
        "source_projection_boundary": {
            "source_authority": [
                str(PROMPT_SHELF_USAGE_RUNS),
                str(PROMPT_SHELF_USAGE_RAW_EVENTS),
                "obsidian/prompt_shelf/* Ledger.md",
            ],
            "projection": str(PROMPT_SHELF_RUNS_INDEX),
            "option_surface_role": "metadata-only route card and counts; not prompt text authority",
            "raw_body_boundary": "raw prompt/provider bodies stay in prompt-shelf source refs and are omitted here",
        },
        "owner_surface": str(PROMPT_SHELF_RUNS_INDEX_TOOL),
        "owner_tool": str(PROMPT_SHELF_RUNS_INDEX_TOOL),
        "owner_summary_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
        "owner_coverage_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage",
        "owner_check_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
        "owner_review_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --review --slot B2 --limit 12",
        "owner_repair_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --write",
        "drilldown_command": (
            "./repo-python kernel.py --option-surface prompt_shelf_metadata "
            f"--band card --ids {PROMPT_SHELF_METADATA_ROW_ID}"
        ),
        "evidence_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
        "validation_route": [
            "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
            "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage",
            "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --review --slot B2 --limit 12",
        ],
        "mutation_route": [
            "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --write",
            "capture new source events through the prompt-shelf capture/observer lane, then rebuild this projection",
        ],
        "graph_neighbors": [
            "prompt_ledger",
            "workitem_spine",
            "operator_type_b_primer",
            "type_b_external_grounding_v1",
            "system_self_comprehension_root",
        ],
        "workitem_pressure": {
            "route": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            "query_hint": "prompt shelf Type B extraction self-description lessons",
        },
        "governing_doctrine": [
            "codex/standards/std_agent_entry_surface.json::type_b_to_type_a_handoff_framing_contract",
            "codex/doctrine/paper_modules/system_self_comprehension_root.md",
        ],
        "currentness": {
            "status": status,
            "projection_generated_at": generated_at,
            "schema_version": meta.get("schema_version"),
            "freshness_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
            "coverage_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage",
            "tracked_outputs": [str(PROMPT_SHELF_RUNS_INDEX)],
        },
        "counts": counts,
        "privacy_boundary": "metadata_and_hashes_only_no_raw_operator_or_type_b_thread_bodies",
        "context_pack_contract": {
            "role": "PROMPT_SHELF_METADATA_EXTRACTION_DRILLDOWN",
            "metadata_only": True,
            "raw_bodies_omitted": True,
            "public_release_safe": False,
            "allowed_payload": (
                "run ids, slots, receipt counts, coverage status, issue summaries, selected-row handles, "
                "owner commands, bounded private review-drilldown commands, and WorkItem/up-propagation routes"
            ),
            "forbidden_payload": (
                "raw run markdown, raw event JSON, prompt/provider payloads, hidden reasoning, "
                "private raw voice, or public artifact claims"
            ),
        },
        "omission_receipt": {
            "omitted": [
                "raw prompt/provider bodies",
                "raw run markdown",
                "raw event JSON",
                "full conversation URLs and private thread bodies",
            ],
            "reason": "The prompt-shelf metadata route exposes counts, hashes, source handles, and owner commands only.",
            "drilldowns": [
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage",
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --review --slot B2 --limit 12",
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
            ],
        },
    }


def _prompt_shelf_metadata_flag_row(repo_root: Path) -> dict[str, Any]:
    row = _prompt_shelf_metadata_base_row(repo_root, band="flag")
    row.pop("context_pack_contract", None)
    return row


def _prompt_shelf_metadata_card_row(repo_root: Path) -> dict[str, Any]:
    row = _prompt_shelf_metadata_base_row(repo_root, band="card")
    row["owner_routes"] = {
        "summary_command": row["owner_summary_command"],
        "coverage_command": row["owner_coverage_command"],
        "check_command": row["owner_check_command"],
        "review_command": row["owner_review_command"],
        "refresh_command": row["owner_repair_command"],
        "context_pack_command": (
            './repo-python kernel.py --context-pack "prompt shelf Type B reasoning extraction '
            'self-description lessons metadata-only" --context-budget 12000'
        ),
    }
    return row


def _prompt_shelf_metadata_cluster_rows(repo_root: Path) -> list[dict[str, Any]]:
    meta = _prompt_shelf_runs_meta(repo_root)
    by_slot = meta.get("by_slot") if isinstance(meta.get("by_slot"), Mapping) else {}
    run_count_by_slot = meta.get("run_count_by_slot") if isinstance(meta.get("run_count_by_slot"), Mapping) else {}
    slots = sorted({str(slot) for slot in by_slot} | {str(slot) for slot in run_count_by_slot})
    rows: list[dict[str, Any]] = []
    for slot in slots:
        slot_meta = by_slot.get(slot) if isinstance(by_slot.get(slot), Mapping) else {}
        run_count = _prompt_shelf_int(slot_meta.get("run_count") if slot_meta else run_count_by_slot.get(slot))
        cluster_id = f"slot:{slot}"
        owner_slot_summary_command = (
            f"./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary --slot {slot}"
        )
        owner_slot_coverage_command = (
            f"./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage --slot {slot}"
        )
        owner_slot_review_command = (
            f"./repo-python tools/meta/observability/prompt_shelf_runs_index.py --review --slot {slot} --limit 12"
        )
        rows.append(
            {
                "row_id": f"prompt_shelf_metadata_cluster:{cluster_id}::cluster_flag",
                "id": cluster_id,
                "cluster_id": cluster_id,
                "prompt_slot": slot,
                "band": "cluster_flag",
                "title": f"Prompt-Shelf {slot} Runs",
                "flag": (
                    f"{run_count} metadata-indexed prompt-shelf run(s) for slot {slot}; "
                    "use the owner summary/card before opening raw prompt bodies."
                ),
                "summary": (
                    "Slot-level metadata cluster over prompt-shelf run notes and raw-event sidecars. "
                    "This row exposes counts and owner commands only."
                ),
                "run_count": run_count,
                "receipt_present_count": _prompt_shelf_int(slot_meta.get("receipt_present_count")),
                "issue_count": _prompt_shelf_int(slot_meta.get("issues_count")),
                "nested_suspect_count": _prompt_shelf_int(slot_meta.get("nested_suspect_count")),
                "run_note_bytes": _prompt_shelf_int(slot_meta.get("run_note_bytes")),
                "raw_event_bytes": _prompt_shelf_int(slot_meta.get("raw_event_bytes")),
                "owner_summary_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
                "owner_slot_summary_command": owner_slot_summary_command,
                "owner_coverage_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage",
                "owner_slot_coverage_command": owner_slot_coverage_command,
                "owner_check_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
                "owner_slot_review_command": owner_slot_review_command,
                "card_command": (
                    "./repo-python kernel.py --option-surface prompt_shelf_metadata "
                    f"--band card --ids {PROMPT_SHELF_METADATA_ROW_ID}"
                ),
                "drilldown_command": owner_slot_summary_command,
                "privacy_boundary": "metadata_and_hashes_only_no_raw_operator_or_type_b_thread_bodies",
                "omission_receipt": {
                    "omitted": [
                        "per-run prompt/provider bodies",
                        "per-run raw event JSON",
                        "full run markdown bodies",
                    ],
                    "reason": "cluster_flag is the slot contents page; selected raw runs stay behind the prompt-shelf owner projection.",
                    "drilldowns": [
                        "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
                        owner_slot_summary_command,
                        "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage",
                        owner_slot_coverage_command,
                        owner_slot_review_command,
                        (
                            "./repo-python kernel.py --option-surface prompt_shelf_metadata "
                            f"--band card --ids {PROMPT_SHELF_METADATA_ROW_ID}"
                        ),
                    ],
                },
            }
        )
    return rows


def build_prompt_shelf_metadata_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="prompt_shelf_metadata",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "prompt_shelf_metadata_band_not_owned",
                "message": "Prompt Shelf metadata owns cluster_flag/flag/card browse rows; use cluster_flag first for slot coverage.",
                "owned_bands": ["cluster_flag", "flag", "card"],
            }
        )
        return payload

    aliases = {
        PROMPT_SHELF_METADATA_ROW_ID,
        "prompt_shelf_runs_index",
        "runs_index",
        "metadata_index",
    }
    meta = _prompt_shelf_runs_meta(repo_root)
    counts = _prompt_shelf_counts(meta)
    cluster_rows = _prompt_shelf_metadata_cluster_rows(repo_root) if band == "cluster_flag" else []
    cluster_aliases = {
        str(row.get("cluster_id") or "") for row in cluster_rows
    } | {
        str(row.get("prompt_slot") or "") for row in cluster_rows
    }
    allowed_ids = aliases | cluster_aliases if band == "cluster_flag" else aliases
    missing_ids = [item for item in ids if item not in allowed_ids]
    rows = []
    if band == "cluster_flag":
        if ids:
            rows = [
                row
                for row in cluster_rows
                if str(row.get("cluster_id") or "") in ids or str(row.get("prompt_slot") or "") in ids
            ]
        else:
            rows = cluster_rows
    elif not ids or any(item in aliases for item in ids):
        rows = [
            _prompt_shelf_metadata_card_row(repo_root)
            if band == "card"
            else _prompt_shelf_metadata_flag_row(repo_root)
        ]
    warnings: list[dict[str, Any]] = []
    if not (repo_root / PROMPT_SHELF_RUNS_INDEX).exists():
        warnings.append(
            {
                "kind": "missing_prompt_shelf_runs_index",
                "message": "Prompt Shelf runs metadata projection is missing; rebuild through the owner tool.",
                "repair_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --write",
            }
        )
    if counts["duplicate_prompt_run_id_count"]:
        warnings.append(
            {
                "kind": "duplicate_prompt_run_ids",
                "message": "Prompt Shelf metadata projection reports duplicate run ids.",
                "count": counts["duplicate_prompt_run_id_count"],
                "repair_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
            }
        )

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "prompt_shelf_metadata",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "metadata_projection_not_raw_prompt_authority",
        "governing_standard": {
            "ref": "codex/standards/std_agent_entry_surface.json::type_b_to_type_a_handoff_framing_contract",
            "schema_version": "std_agent_entry_surface_v1",
            "owned_bands": ["cluster_flag", "flag", "card"],
        },
        "source_refs": [
            str(PROMPT_SHELF_RUNS_INDEX_TOOL),
            str(PROMPT_SHELF_RUNS_INDEX),
            str(PROMPT_SHELF_LEDGER),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": counts["slot_count"] if band == "cluster_flag" else 1,
            "query_used": False,
            "selection_method": (
                "prompt_shelf_metadata_slot_clusters"
                if band == "cluster_flag"
                else "prompt_shelf_metadata_owner_card"
            ),
            "drilldown_by": "prompt_slot" if band == "cluster_flag" else "metadata_id",
            "run_count": counts["run_count"],
            "receipt_present_count": counts["receipt_present_count"],
            "issues_total": counts["issues_total"],
            "privacy_boundary": "metadata-only; raw prompt/provider bodies stay in source refs",
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "mutation_rule": "rebuild prompt-shelf metadata through prompt_shelf_runs_index.py; never paste raw prompt bodies into this surface",
        },
        "cluster_omission_receipt": {
            "omitted": [
                "per-run rows",
                "raw prompt/provider bodies",
                "raw event JSON",
                "full run markdown bodies",
            ],
            "reason": "cluster_flag groups the high-cardinality prompt-shelf run index by slot before owner-card or source drilldown.",
            "drilldowns": [
                f"./repo-python kernel.py --option-surface prompt_shelf_metadata --band card --ids {PROMPT_SHELF_METADATA_ROW_ID}",
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage",
            ],
        }
        if band == "cluster_flag"
        else {},
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface prompt_shelf_metadata --band cluster_flag",
                "reason": "Browse prompt-shelf metadata by slot before owner-card or raw source drilldown.",
            },
            {
                "command": f"./repo-python kernel.py --option-surface prompt_shelf_metadata --band card --ids {PROMPT_SHELF_METADATA_ROW_ID}",
                "reason": "Open the metadata owner card with boundary, owner routes, validation, and omission receipts.",
            },
            {
                "command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
                "reason": "Read run/receipt/issue counts without opening raw prompt bodies.",
            },
            {
                "command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage",
                "reason": "Check whether current prompt slots have metadata coverage before extraction or classifier work.",
            },
            {
                "command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
                "reason": "Validate the metadata projection before treating it as current.",
            },
        ],
        "warnings": warnings,
    }


def _external_benchmark_read_json(repo_root: Path, path: Path) -> dict[str, Any]:
    try:
        payload = _load_json(repo_root / path)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _external_benchmark_receipt_count(repo_root: Path, relative_glob: str) -> int:
    root = repo_root / EXTERNAL_BENCHMARK_CALIBRATION_ROOT
    if not root.exists():
        return 0
    return sum(1 for path in root.glob(relative_glob) if path.is_file())


def _external_benchmark_calibration_meta(repo_root: Path) -> dict[str, Any]:
    board = _external_benchmark_read_json(repo_root, EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD)
    manifest = _external_benchmark_read_json(repo_root, EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST)
    return {
        "board": board,
        "manifest": manifest,
        "result_board_exists": (repo_root / EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD).exists(),
        "slice_manifest_exists": (repo_root / EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST).exists(),
        "scorecard_exists": (repo_root / EXTERNAL_BENCHMARK_CALIBRATION_SCORECARD).exists(),
        "planned_task_count": _prompt_shelf_int(
            board.get("planned_task_count") or manifest.get("planned_task_count")
        ),
        "evaluated_task_count": _prompt_shelf_int(board.get("evaluated_task_count")),
        "solved_count": _prompt_shelf_int(board.get("solved_count")),
        "row_execution_receipt_count": _prompt_shelf_int(
            board.get("row_execution_receipt_count")
        )
        or _external_benchmark_receipt_count(repo_root, "row_execution/*/row_execution_receipt.json"),
        "harness_differential_receipt_count": _prompt_shelf_int(
            board.get("harness_differential_receipt_count")
        )
        or _external_benchmark_receipt_count(
            repo_root,
            "harness_differential/*/harness_differential_receipt.json",
        ),
        "c_arm_provider_repair_receipt_count": _external_benchmark_receipt_count(
            repo_root,
            "c_arm_provider_repair/*/c_arm_provider_repair_receipt.json",
        ),
        "provider_dispatch_success_count": _prompt_shelf_int(
            board.get("provider_dispatch_success_count")
        ),
        "public_claim_allowed": bool(board.get("public_claim_allowed")),
        "official_leaderboard_submission": bool(board.get("official_leaderboard_submission")),
        "schema_version": board.get("schema_version") or manifest.get("schema_version"),
        "created_from_source_receipts_at": board.get("created_from_source_receipts_at"),
    }


def _external_benchmark_calibration_base_row(repo_root: Path, *, band: str) -> dict[str, Any]:
    meta = _external_benchmark_calibration_meta(repo_root)
    status = (
        "result_board_available_owner_check_required"
        if meta["result_board_exists"] and meta["slice_manifest_exists"]
        else "result_board_or_slice_manifest_missing"
    )
    counts = {
        "planned_task_count": meta["planned_task_count"],
        "evaluated_task_count": meta["evaluated_task_count"],
        "solved_count": meta["solved_count"],
        "row_execution_receipt_count": meta["row_execution_receipt_count"],
        "harness_differential_receipt_count": meta["harness_differential_receipt_count"],
        "c_arm_provider_repair_receipt_count": meta["c_arm_provider_repair_receipt_count"],
        "provider_dispatch_success_count": meta["provider_dispatch_success_count"],
    }
    return {
        "row_id": f"external_benchmark_calibration:{EXTERNAL_BENCHMARK_CALIBRATION_ROW_ID}::{band}",
        "id": EXTERNAL_BENCHMARK_CALIBRATION_ROW_ID,
        "calibration_id": EXTERNAL_BENCHMARK_CALIBRATION_ROW_ID,
        "band": band,
        "title": "VeriSoftBench Micro-10 External Benchmark Calibration Spine",
        "flag": (
            "Owner route for the formal-math external benchmark calibration spine: "
            "VeriSoftBench micro-10 source receipts, row execution, harness differential, "
            "C-arm provider repair receipts, generated board/scorecard, and disclosure limits."
        ),
        "summary": (
            "Use this card before raw benchmark/provider search when asking how the repo calibrates "
            "formal-math external benchmark evidence or how provider proof-repair attempts are checked."
        ),
        "authority_posture": "owner_route_card_not_benchmark_authority",
        "projection_only": True,
        "disclosure_posture": "controlled_private_review",
        "source_ref": str(EXTERNAL_BENCHMARK_CALIBRATION_BUILDER),
        "source_refs": [
            str(EXTERNAL_BENCHMARK_CALIBRATION_BUILDER),
            str(EXTERNAL_BENCHMARK_ROW_EXECUTION),
            str(EXTERNAL_BENCHMARK_HARNESS_DIFFERENTIAL),
            str(EXTERNAL_BENCHMARK_C_ARM_PROVIDER_REPAIR),
            str(EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD),
            str(EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST),
            str(EXTERNAL_BENCHMARK_CALIBRATION_SCORECARD),
            "system/lib/generated_projection_registry.py::external_benchmark_calibration_spine_projection",
        ],
        "owner_surface": str(EXTERNAL_BENCHMARK_CALIBRATION_BUILDER),
        "owner_tool": str(EXTERNAL_BENCHMARK_CALIBRATION_BUILDER),
        "owner_check_command": (
            "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py --check"
        ),
        "owner_repair_command": (
            "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py"
        ),
        "provider_repair_check_command": (
            "./repo-python tools/meta/factory/run_verisoftbench_micro10_c_arm_provider_repair.py --check --json"
        ),
        "drilldown_command": (
            "./repo-python kernel.py --option-surface external_benchmark_calibration "
            f"--band card --ids {EXTERNAL_BENCHMARK_CALIBRATION_ROW_ID}"
        ),
        "evidence_command": (
            "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py --check"
        ),
        "identity": {
            "kind": "external_benchmark_calibration",
            "benchmark_slice": "verisoftbench_micro_10_v0",
            "projection_owner_id": EXTERNAL_BENCHMARK_PROJECTION_OWNER_ID,
            "work_item_id": EXTERNAL_BENCHMARK_WORK_ITEM_ID,
        },
        "purpose": (
            "Make external benchmark proof-repair evidence routeable without treating provider text, "
            "generated scorecards, or public comparator baselines as proof authority."
        ),
        "source_projection_boundary": {
            "source_authority": [
                "formal-math microcosm evaluator receipts",
                "VeriSoftBench annex/source refs selected by the calibration builder",
                str(EXTERNAL_BENCHMARK_ROW_EXECUTION),
                str(EXTERNAL_BENCHMARK_HARNESS_DIFFERENTIAL),
                str(EXTERNAL_BENCHMARK_C_ARM_PROVIDER_REPAIR),
            ],
            "generated_outputs": [
                str(EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD),
                str(EXTERNAL_BENCHMARK_CALIBRATION_SCORECARD),
            ],
            "owner_registry": (
                "system/lib/generated_projection_registry.py::"
                f"{EXTERNAL_BENCHMARK_PROJECTION_OWNER_ID}"
            ),
            "manual_edit_boundary": (
                "Do not hand-edit result boards, scorecards, provider outputs, or row receipts; "
                "patch the owner builder/runner or rerun the governed command."
            ),
            "authority_boundary": "Lean/Lake evaluator receipts certify proof status; provider output is advisory candidate text only.",
        },
        "governing_doctrine": [
            f"codex/doctrine/teleology_nodes.json::{EXTERNAL_BENCHMARK_TELEOLOGY_ID}",
            "codex/standards/std_compute_provider.json",
            "codex/standards/std_microcosm.json",
            "codex/standards/std_cognitive_operator.json",
            "codex/standards/std_node_reasoning.json",
            "codex/standards/std_system_atlas.json",
        ],
        "graph_neighbors": [
            "formal_math_decision_point_microcosm_v0",
            "formal_math_proof_repair_lane",
            "generated_projection_ownership",
            "verisoftbench_no_solve_manifest",
            "nvidia_nim_provider_route",
            "task_ledger",
            "system_atlas",
            "dissemination_gate",
        ],
        "workitem_pressure": {
            "work_item_id": EXTERNAL_BENCHMARK_WORK_ITEM_ID,
            "task_ledger_route": (
                "./repo-python kernel.py --option-surface task_ledger --band card "
                f"--ids {EXTERNAL_BENCHMARK_WORK_ITEM_ID}"
            ),
            "claims_route": "./repo-python tools/meta/factory/work_ledger.py session-claims --limit 20",
        },
        "validation_route": [
            "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py --check",
            "./repo-python tools/meta/factory/run_verisoftbench_micro10_c_arm_provider_repair.py --check --json",
            "./repo-python -m pytest system/server/tests/test_external_benchmark_calibration_spine.py",
            (
                "./repo-python kernel.py --option-surface external_benchmark_calibration "
                f"--band card --ids {EXTERNAL_BENCHMARK_CALIBRATION_ROW_ID}"
            ),
        ],
        "mutation_route": [
            "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py",
            (
                "./repo-python tools/meta/factory/run_verisoftbench_micro10_calibration_rows.py "
                "--check --json"
            ),
            (
                "./repo-python tools/meta/factory/run_verisoftbench_micro10_harness_differential.py "
                "--check --json"
            ),
            (
                "./repo-python tools/meta/factory/run_verisoftbench_micro10_c_arm_provider_repair.py "
                "--task-id <verisoftbench:N> --check --json"
            ),
            "Run provider/Lean mutation commands without --check only under the owning WorkItem/CAP and prompt-boundary contract.",
        ],
        "currentness": {
            "status": status,
            "schema_version": meta["schema_version"],
            "created_from_source_receipts_at": meta["created_from_source_receipts_at"],
            "result_board_mtime": _source_mtime(repo_root / EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD),
            "slice_manifest_mtime": _source_mtime(repo_root / EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST),
            "scorecard_mtime": _source_mtime(repo_root / EXTERNAL_BENCHMARK_CALIBRATION_SCORECARD),
            "freshness_command": (
                "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py --check"
            ),
            "source_coupling_status": "not_evaluated_in_option_surface_hot_path",
            "trust_boundary": "artifact presence does not prove generated board/scorecard freshness; run the owner check before treating them as current.",
            "tracked_outputs": [
                str(EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD),
                str(EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST),
                str(EXTERNAL_BENCHMARK_CALIBRATION_SCORECARD),
            ],
            "public_claim_allowed": meta["public_claim_allowed"],
            "official_leaderboard_submission": meta["official_leaderboard_submission"],
        },
        "counts": counts,
        "cluster_keys": [
            "external benchmark calibration",
            "verisoftbench micro-10",
            "formal math proof repair",
            "c-arm provider repair",
            "nvidia nim provider proof attempt",
        ],
        "when_to_open": (
            "Open when a task asks how VeriSoftBench micro-10 calibration, formal-math proof repair, "
            "provider repair receipts, generated scorecards, or benchmark disclosure boundaries connect."
        ),
        "when_not_to_open": (
            "Do not open for generic System Atlas freshness, generic provider config, or official benchmark "
            "submission questions unless the task names calibration/proof-repair evidence."
        ),
        "safe_drilldown": (
            "./repo-python kernel.py --option-surface external_benchmark_calibration "
            f"--band card --ids {EXTERNAL_BENCHMARK_CALIBRATION_ROW_ID}"
        ),
        "landmines": [
            "Do not treat generated scorecards as source authority.",
            "Do not quote raw provider output or benchmark-private proof bodies into public-safe surfaces.",
            "Do not claim official VeriSoftBench leaderboard status from this local micro-slice.",
        ],
        "sufficiency_claims": [
            "Names owner builder/checker, generated outputs, registry owner, WorkItem pressure, and mutation route.",
            "Carries disclosure posture and proof/provider authority boundary for cold Type A action.",
        ],
        "context_pack_contract": {
            "role": "EXTERNAL_BENCHMARK_CALIBRATION_DRILLDOWN",
            "metadata_only": True,
            "raw_bodies_omitted": True,
            "public_release_safe": False,
            "allowed_payload": (
                "owner commands, source/generated refs, receipt counts, WorkItem id, validation routes, "
                "disclosure posture, and authority boundaries"
            ),
            "forbidden_payload": (
                "raw provider outputs, hidden proof bodies, benchmark-private truth-side material, "
                "official leaderboard/submission claims, or generated-scorecard authority inversion"
            ),
        },
        "omission_receipt": {
            "omitted": [
                "raw provider outputs",
                "full Lean stdout/stderr bodies",
                "truth-side proof bodies",
                "full generated result-board row payloads",
            ],
            "reason": "This card is a compact owner route; evaluator/provider receipts stay behind governed source refs.",
            "drilldowns": [
                "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py --check",
                (
                    "./repo-python tools/meta/factory/run_verisoftbench_micro10_c_arm_provider_repair.py "
                    "--check --json"
                ),
            ],
        },
    }


def _external_benchmark_calibration_flag_row(repo_root: Path) -> dict[str, Any]:
    row = _external_benchmark_calibration_base_row(repo_root, band="flag")
    row.pop("context_pack_contract", None)
    return row


def _external_benchmark_calibration_card_row(repo_root: Path) -> dict[str, Any]:
    row = _external_benchmark_calibration_base_row(repo_root, band="card")
    row["owner_routes"] = {
        "card_command": row["drilldown_command"],
        "check_command": row["owner_check_command"],
        "refresh_command": row["owner_repair_command"],
        "provider_repair_check_command": row["provider_repair_check_command"],
        "context_pack_command": (
            './repo-python kernel.py --context-pack "provider formal math proof repair '
            'nvidia nim trickle verisoftbench external benchmark calibration spine" '
            "--context-budget 12000"
        ),
    }
    return row


def build_external_benchmark_calibration_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="external_benchmark_calibration",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "external_benchmark_calibration_band_not_owned",
                "message": "External benchmark calibration owns flag/card browse rows only; use card for the owner route.",
                "owned_bands": ["flag", "card"],
            }
        )
        return payload

    aliases = {
        EXTERNAL_BENCHMARK_CALIBRATION_ROW_ID,
        "verisoftbench_micro_10",
        "verisoftbench_micro10",
        "verisoftbench",
        "external_benchmark_calibration_spine_projection",
        EXTERNAL_BENCHMARK_PROJECTION_OWNER_ID,
        EXTERNAL_BENCHMARK_WORK_ITEM_ID,
    }
    missing_ids = [item for item in ids if item not in aliases]
    selected = not ids or any(item in aliases for item in ids)
    rows = []
    if selected:
        rows = [
            _external_benchmark_calibration_card_row(repo_root)
            if band == "card"
            else _external_benchmark_calibration_flag_row(repo_root)
        ]

    meta = _external_benchmark_calibration_meta(repo_root)
    warnings: list[dict[str, Any]] = []
    if not meta["result_board_exists"]:
        warnings.append(
            {
                "kind": "missing_external_benchmark_result_board",
                "message": "The VeriSoftBench micro-10 result board is missing; rebuild through the owner builder.",
                "repair_command": (
                    "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py"
                ),
            }
        )

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "external_benchmark_calibration",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "owner_route_card_not_benchmark_authority",
        "governing_standard": {
            "ref": "codex/standards/std_system_atlas.json::external_benchmark_calibration_route",
            "schema_version": "standard_owned_option_surface_v0",
            "owned_bands": ["flag", "card"],
        },
        "source_refs": [
            str(EXTERNAL_BENCHMARK_CALIBRATION_BUILDER),
            str(EXTERNAL_BENCHMARK_ROW_EXECUTION),
            str(EXTERNAL_BENCHMARK_HARNESS_DIFFERENTIAL),
            str(EXTERNAL_BENCHMARK_C_ARM_PROVIDER_REPAIR),
            str(EXTERNAL_BENCHMARK_CALIBRATION_RESULT_BOARD),
            str(EXTERNAL_BENCHMARK_CALIBRATION_SLICE_MANIFEST),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": 1,
            "query_used": False,
            "selection_method": "external_benchmark_calibration_owner_card",
            "drilldown_by": "calibration_id",
            "planned_task_count": meta["planned_task_count"],
            "evaluated_task_count": meta["evaluated_task_count"],
            "solved_count": meta["solved_count"],
            "c_arm_provider_repair_receipt_count": meta["c_arm_provider_repair_receipt_count"],
            "disclosure_posture": "controlled_private_review",
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "cluster_first_for_high_cardinality": False,
            "adapter_supported_bands": ["flag", "card"],
            "mutation_rule": (
                "Patch/rerun the external benchmark calibration owner builder or governed runners; "
                "never hand-edit result boards, scorecards, provider outputs, or proof receipts."
            ),
        },
        "rows": rows,
        "next": [
            {
                "command": (
                    "./repo-python kernel.py --option-surface external_benchmark_calibration "
                    f"--band card --ids {EXTERNAL_BENCHMARK_CALIBRATION_ROW_ID}"
                ),
                "reason": "Open the compact owner card before raw benchmark/provider search.",
            },
            {
                "command": (
                    "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py --check"
                ),
                "reason": "Check generated board/scorecard currentness without refreshing blindly.",
            },
            {
                "command": (
                    "./repo-python tools/meta/factory/run_verisoftbench_micro10_c_arm_provider_repair.py --check --json"
                ),
                "reason": "Check provider-repair receipts and Lean/Lake evaluator status before more repair attempts.",
            },
            {
                "command": (
                    "./repo-python kernel.py --option-surface task_ledger --band card "
                    f"--ids {EXTERNAL_BENCHMARK_WORK_ITEM_ID}"
                ),
                "reason": "Read live WorkItem pressure and acceptance boundary before mutating calibration artifacts.",
            },
        ],
        "warnings": warnings,
    }


def _type_a_seed_path_seed_id(path: Path, payload: Mapping[str, Any] | None = None) -> str:
    if payload:
        seed_id = str(payload.get("seed_id") or "").strip()
        if seed_id:
            return seed_id
    name = path.name
    suffix = "_autonomous_seed.json"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return path.stem


def _type_a_seed_load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _type_a_seed_mtime(path: Path) -> str | None:
    try:
        return (
            datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except FileNotFoundError:
        return None


def _type_a_seed_entries(repo_root: Path) -> list[dict[str, Any]]:
    seeds_root = repo_root / TYPE_A_AUTONOMOUS_SEED_ROOT
    entries: list[dict[str, Any]] = []
    if not seeds_root.exists():
        return entries
    for json_path in sorted(seeds_root.glob("*_autonomous_seed.json")):
        payload = _type_a_seed_load_json(json_path)
        seed_id = _type_a_seed_path_seed_id(json_path, payload)
        markdown_path = seeds_root / f"{seed_id}_autonomous_seed.md"
        navigation_map_path = seeds_root / f"{seed_id}_navigation_map.json"
        verification = payload.get("verification") if isinstance(payload.get("verification"), Mapping) else {}
        next_wave = payload.get("next_wave") if isinstance(payload.get("next_wave"), Mapping) else {}
        watchpoints = payload.get("watchpoints") if isinstance(payload.get("watchpoints"), list) else []
        entries.append(
            {
                "seed_id": seed_id,
                "payload": payload,
                "json_path": json_path,
                "markdown_path": markdown_path,
                "navigation_map_path": navigation_map_path,
                "json_rel": _relative(json_path, repo_root),
                "markdown_rel": _relative(markdown_path, repo_root),
                "navigation_map_rel": _relative(navigation_map_path, repo_root),
                "markdown_exists": markdown_path.exists(),
                "navigation_map_exists": navigation_map_path.exists(),
                "json_mtime": _type_a_seed_mtime(json_path),
                "markdown_mtime": _type_a_seed_mtime(markdown_path),
                "navigation_map_mtime": _type_a_seed_mtime(navigation_map_path),
                "verification_commands": [
                    str(command)
                    for command in (verification.get("commands") or [])
                    if isinstance(command, str)
                ],
                "next_wave": next_wave,
                "watchpoints": [str(item) for item in watchpoints if isinstance(item, str)],
            }
        )
    return entries


def _type_a_seed_entry_aliases(entry: Mapping[str, Any]) -> set[str]:
    seed_id = str(entry.get("seed_id") or "").strip()
    aliases = {seed_id}
    for suffix in ("_autonomous_seed", "_autonomous_seed.json", "_autonomous_seed.md", "_navigation_map.json"):
        aliases.add(f"{seed_id}{suffix}")
    for key in ("json_rel", "markdown_rel", "navigation_map_rel"):
        value = str(entry.get(key) or "").strip()
        if value:
            aliases.add(value)
            aliases.add(Path(value).name)
    return {alias for alias in aliases if alias}


def _type_a_seed_payload(entry: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = entry.get("payload")
    return payload if isinstance(payload, Mapping) else {}


def _type_a_seed_axis(entry: Mapping[str, Any], key: str) -> str:
    payload = _type_a_seed_payload(entry)
    value = str(payload.get(key) or "").strip()
    return value or "missing"


def _type_a_seed_cluster_id(entry: Mapping[str, Any]) -> str:
    return f"lane:{_normalize_cluster_id(_type_a_seed_axis(entry, 'lane'))}"


def _type_a_seed_cluster_label(cluster_id: str) -> str:
    _, _, raw = cluster_id.partition(":")
    return f"Lane / {(raw or 'missing').replace('_', ' ').replace('-', ' ').title()}"


def _type_a_seed_cluster_aliases(cluster_id: str, entries: Sequence[Mapping[str, Any]]) -> set[str]:
    aliases = {cluster_id, cluster_id.replace(":", "_")}
    for entry in entries:
        lane = _type_a_seed_axis(entry, "lane")
        lane_norm = _normalize_cluster_id(lane)
        aliases.update({lane, lane_norm, f"lane:{lane}", f"lane:{lane_norm}", f"lane_{lane_norm}"})
    return {alias for alias in aliases if alias}


def _type_a_seed_cluster_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        grouped.setdefault(_type_a_seed_cluster_id(entry), []).append(entry)

    rows: list[dict[str, Any]] = []
    for cluster_id, group_entries in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        top_ids = [str(entry.get("seed_id") or "") for entry in group_entries[:8] if entry.get("seed_id")]
        ids = ",".join(top_ids)
        label = _type_a_seed_cluster_label(cluster_id)
        scope_shape_counts = Counter(_type_a_seed_axis(entry, "scope_shape") for entry in group_entries)
        depth_tier_counts = Counter(_type_a_seed_axis(entry, "depth_tier") for entry in group_entries)
        mode_counts = Counter(_type_a_seed_axis(entry, "mode") for entry in group_entries)
        execution_mode_counts = Counter(_type_a_seed_axis(entry, "execution_mode") for entry in group_entries)
        latest_json_mtime = max(
            (str(entry.get("json_mtime") or "") for entry in group_entries),
            default="",
        )
        rows.append(
            {
                "row_id": f"type_a_autonomous_seed_cluster:{cluster_id}::cluster_flag",
                "artifact_kind": "type_a_autonomous_seed_cluster",
                "band": "cluster_flag",
                "cluster_id": cluster_id,
                "group_label": label,
                "cluster_source_axis": "lane",
                "count": len(group_entries),
                "top_ids": top_ids,
                "scope_shape_counts": dict(sorted(scope_shape_counts.items())),
                "depth_tier_counts": dict(sorted(depth_tier_counts.items())),
                "mode_counts": dict(sorted(mode_counts.items())),
                "execution_mode_counts": dict(sorted(execution_mode_counts.items())),
                "navigation_map_count": sum(1 for entry in group_entries if entry.get("navigation_map_exists")),
                "verification_command_count": sum(
                    len(entry.get("verification_commands") or []) for entry in group_entries
                ),
                "watchpoint_count": sum(len(entry.get("watchpoints") or []) for entry in group_entries),
                "claim": f"{label}: {len(group_entries)} saved Type A autonomous seed bundles.",
                "drilldown_command": (
                    f"./repo-python kernel.py --option-surface type_a_autonomous_seeds --band flag --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band flag --ids <seed_id>"
                ),
                "card_drilldown_command": (
                    f"./repo-python kernel.py --option-surface type_a_autonomous_seeds --band card --ids {ids}"
                    if ids
                    else "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band card --ids <seed_id>"
                ),
                "evidence_command": "./repo-python kernel.py --raw-seed-autonomous-seeds 09",
                "currentness": {
                    "status": "seed_cluster_metadata_available",
                    "latest_json_mtime": latest_json_mtime or None,
                    "freshness_command": "./repo-python kernel.py --raw-seed-autonomous-seeds 09",
                },
                "source_projection_boundary": {
                    "option_surface_role": "cluster contents page over seed metadata; not seed source authority",
                    "raw_seed_boundary": "raw_seed.md/operator voice stays behind raw-seed owner routes",
                    "drilldown_boundary": "open flag/card rows by seed id before reading source bundles",
                },
                "omission_receipt": {
                    "omitted": [
                        "row-level seed flags outside top_ids",
                        "full autonomous seed markdown bodies",
                        "raw_seed.md bodies and operator chat",
                        "raw proof bodies and provider payloads",
                    ],
                    "reason": "cluster_flag groups saved seeds by lane before row expansion so agents can select the right autonomous-seed family without raw-search rediscovery.",
                    "drilldown": (
                        f"./repo-python kernel.py --option-surface type_a_autonomous_seeds --band flag --ids {ids}"
                        if ids
                        else "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band flag --ids <seed_id>"
                    ),
                },
            }
        )
    return rows


def _type_a_seed_title(seed_id: str, payload: Mapping[str, Any]) -> str:
    title = str(payload.get("title") or "").strip()
    if title:
        return title
    return seed_id.replace("_", " ").title()


def _type_a_seed_base_row(entry: Mapping[str, Any], *, band: str) -> dict[str, Any]:
    payload = entry.get("payload") if isinstance(entry.get("payload"), Mapping) else {}
    seed_id = str(entry.get("seed_id") or "")
    title = _type_a_seed_title(seed_id, payload)
    goal = _truncate_words(str(payload.get("goal") or ""), max_chars=360)
    current_focus = _truncate_words(str(payload.get("current_focus") or ""), max_chars=300)
    next_wave = entry.get("next_wave") if isinstance(entry.get("next_wave"), Mapping) else {}
    next_objective = _truncate_words(str(next_wave.get("objective") or ""), max_chars=260)
    verification_commands = list(entry.get("verification_commands") or [])
    watchpoints = [
        _truncate_words(str(item), max_chars=180)
        for item in list(entry.get("watchpoints") or [])[:8]
    ]
    bundle_command = f"./repo-python kernel.py --raw-seed-autonomous-seed-bundle {seed_id}"
    refresh_command = f"./repo-python kernel.py --raw-seed-autonomous-seed-refresh {seed_id}"
    validate_command = f"./repo-python kernel.py --validate-seed-continuity {entry.get('json_rel')}"
    legacy_validate_command = f"./repo-python kernel.py --validate-seed-heartbeat {entry.get('json_rel')}"
    replay_receipt_contract = {
        "schema_version": "autonomous_seed_replay_receipt_v0",
        "purpose": (
            "Compact proof that a manually queued seed pass rehydrated live seed authority, "
            "landed or blocked one non-null mutation, validated it, and left the next run's first decision."
        ),
        "required_fields": [
            "selected_seed_id",
            "detection_evidence",
            "live_authority_opened",
            "mutation_landed_or_blocked",
            "owned_paths_mutated",
            "validation_refs",
            "continuation_written",
            "next_run_first_decision",
        ],
        "detection_evidence_options": [
            "wake_prompts.repeated_prompt_cluster",
            "wake_prompts.matched_candidate",
            "operator_named_seed_id",
            "seed_corpus_owner_card",
            "agent_entry_recognized_situation",
        ],
        "write_targets": [
            str(entry.get("json_rel") or ""),
            str(entry.get("markdown_rel") or ""),
            "state/task_ledger/events.jsonl when a residual/blocker is created",
            "codex/ledger/<phase_id>/work_ledger.jsonl when a live claim is opened",
        ],
        "non_success_states": [
            "no_patchable_lane",
            "unsafe_or_destructive",
            "same_path_claim_collision",
            "git_metadata_write_denied_after_validated_patch",
        ],
        "receipt_is_not_success_by_itself": True,
    }
    return {
        "row_id": f"type_a_autonomous_seed:{seed_id}::{band}",
        "id": seed_id,
        "seed_id": seed_id,
        "band": band,
        "title": title,
        "flag": current_focus or goal or "Saved Type A autonomous seed continuity bundle.",
        "summary": (
            "Metadata-only owner route for a saved Type A autonomous seed bundle. "
            "Use it to recover identity, owner commands, validation, currentness, and private-root boundaries "
            "before opening seed source files."
        ),
        "authority_posture": "seed_metadata_projection_not_raw_seed_authority",
        "projection_only": True,
        "disclosure_posture": "private_root_only",
        "source_ref": str(entry.get("json_rel") or ""),
        "source_refs": [
            str(entry.get("json_rel") or ""),
            str(entry.get("markdown_rel") or ""),
            str(entry.get("navigation_map_rel") or ""),
            str(TYPE_A_AUTONOMOUS_SEED_SKILL),
            str(TYPE_A_AUTONOMOUS_SEED_STANDARD),
        ],
        "owner_surface": str(TYPE_A_AUTONOMOUS_SEED_ROOT),
        "owner_tool": "system/lib/kernel/commands/substrate.py",
        "owner_bundle_command": bundle_command,
        "owner_refresh_command": refresh_command,
        "owner_list_command": "./repo-python kernel.py --raw-seed-autonomous-seeds 09",
        "owner_validate_command": validate_command,
        "legacy_validate_command": legacy_validate_command,
        "drilldown_command": f"./repo-python kernel.py --option-surface type_a_autonomous_seeds --band card --ids {seed_id}",
        "evidence_command": bundle_command,
        "source_projection_boundary": {
            "json_source_authority": str(entry.get("json_rel") or ""),
            "markdown_projection": str(entry.get("markdown_rel") or ""),
            "navigation_map_projection": str(entry.get("navigation_map_rel") or ""),
            "option_surface_role": "metadata route card; not seed source authority and not raw-seed voice",
            "raw_seed_boundary": "raw_seed.md/operator voice stays in the raw-seed lane and is not projected here",
        },
        "identity": {
            "kind": "type_a_autonomous_seed",
            "seed_id": seed_id,
            "lane": payload.get("lane"),
            "scope_shape": payload.get("scope_shape"),
            "depth_tier": payload.get("depth_tier"),
            "mode": payload.get("mode"),
        },
        "purpose": goal or next_objective,
        "governing_doctrine": [
            str(TYPE_A_AUTONOMOUS_SEED_STANDARD),
            str(TYPE_A_AUTONOMOUS_SEED_SKILL),
            str(TYPE_A_AUTONOMOUS_SEED_MISSION),
            "codex/doctrine/paper_modules/system_self_comprehension_root.md",
            "codex/standards/observe_apply/std_raw_seed.md",
        ],
        "graph_neighbors": [
            "raw_seed_shards",
            "task_ledger",
            "work_ledger",
            "system_atlas",
            "system_crystal",
            "root_coverage_state",
            "generated_projection_registry",
            "prompt_shelf_metadata",
        ],
        "workitem_pressure": {
            "route": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            "query_hint": f"autonomous seed {seed_id} residual work or CAP pressure",
        },
        "validation_route": [
            f"./repo-python -m json.tool {entry.get('json_rel')}",
            validate_command,
            "./repo-python kernel.py --raw-seed-autonomous-seeds 09",
            bundle_command,
        ],
        "legacy_compatibility_validation_route": [
            legacy_validate_command,
        ],
        "mutation_route": [
            refresh_command,
            "create or refresh saved seeds through kernel raw-seed autonomous seed commands; do not hand-edit raw_seed.md",
        ],
        "currentness": {
            "status": "seed_json_available" if payload else "seed_json_missing_or_invalid",
            "json_mtime": entry.get("json_mtime"),
            "markdown_exists": bool(entry.get("markdown_exists")),
            "markdown_mtime": entry.get("markdown_mtime"),
            "navigation_map_exists": bool(entry.get("navigation_map_exists")),
            "navigation_map_mtime": entry.get("navigation_map_mtime"),
            "freshness_command": bundle_command,
        },
        "counts": {
            "verification_command_count": len(verification_commands),
            "watchpoint_count": len(entry.get("watchpoints") or []),
        },
        "watchpoints": watchpoints,
        "next_wave_objective": next_objective,
        "context_pack_contract": {
            "role": "TYPE_A_AUTONOMOUS_SEED_OWNER_DRILLDOWN",
            "metadata_only": True,
            "raw_bodies_omitted": True,
            "public_release_safe": False,
            "allowed_payload": (
                "seed ids, source refs, owner commands, bounded goal/current-focus summaries, "
                "validation routes, currentness, and private-root disclosure posture"
            ),
            "forbidden_payload": (
                "raw_seed.md bodies, full seed markdown bodies, operator chat, prompt-shelf raw text, "
                "provider payloads, hidden reasoning, or raw proof bodies"
            ),
        },
        "replay_receipt_contract": replay_receipt_contract,
        "omission_receipt": {
            "omitted": [
                "raw_seed.md bodies",
                "full autonomous seed markdown bodies",
                "operator chat and raw prompt shelf text",
                "raw proof bodies and provider payloads",
            ],
            "reason": "The option surface exposes route handles and bounded metadata so cold agents can act without raw-search rediscovery.",
            "drilldowns": [bundle_command, validate_command, refresh_command],
        },
    }


def _type_a_seed_flag_row(entry: Mapping[str, Any]) -> dict[str, Any]:
    row = _type_a_seed_base_row(entry, band="flag")
    row.pop("context_pack_contract", None)
    row.pop("omission_receipt", None)
    row.pop("watchpoints", None)
    return row


def _type_a_seed_card_row(entry: Mapping[str, Any]) -> dict[str, Any]:
    row = _type_a_seed_base_row(entry, band="card")
    row["owner_routes"] = {
        "list_command": row["owner_list_command"],
        "bundle_command": row["owner_bundle_command"],
        "refresh_command": row["owner_refresh_command"],
        "validate_command": row["owner_validate_command"],
        "context_pack_command": (
            './repo-python kernel.py --context-pack "raw seed autonomous seed Type A seed loop '
            'architecture self comprehension" --context-budget 12000'
        ),
    }
    return row


def build_type_a_autonomous_seeds_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="type_a_autonomous_seeds",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "type_a_autonomous_seeds_band_not_owned",
                "message": "Type A autonomous seeds own cluster_flag/flag/card browse rows.",
                "owned_bands": ["cluster_flag", "flag", "card"],
            }
        )
        return payload

    entries = _type_a_seed_entries(repo_root)
    by_alias: dict[str, dict[str, Any]] = {}
    for entry in entries:
        for alias in _type_a_seed_entry_aliases(entry):
            by_alias[alias] = dict(entry)

    cluster_groups: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        cluster_groups.setdefault(_type_a_seed_cluster_id(entry), []).append(entry)
    cluster_aliases: dict[str, list[dict[str, Any]]] = {}
    for cluster_id, group_entries in cluster_groups.items():
        for alias in _type_a_seed_cluster_aliases(cluster_id, group_entries):
            cluster_aliases[alias] = list(group_entries)

    missing_ids: list[str] = []
    selected_entries: list[dict[str, Any]] = []
    if ids:
        for item in ids:
            if band == "cluster_flag" and item in cluster_aliases:
                selected_entries.extend(cluster_aliases[item])
            elif item in by_alias:
                selected_entries.append(by_alias[item])
            else:
                missing_ids.append(item)
    else:
        selected_entries = entries

    seen: set[str] = set()
    unique_entries: list[dict[str, Any]] = []
    for entry in selected_entries:
        seed_id = str(entry.get("seed_id") or "")
        if seed_id in seen:
            continue
        seen.add(seed_id)
        unique_entries.append(entry)

    if band == "cluster_flag":
        rows = _type_a_seed_cluster_rows(unique_entries)
    else:
        rows = [
            _type_a_seed_card_row(entry) if band == "card" else _type_a_seed_flag_row(entry)
            for entry in unique_entries
        ]
    warnings: list[dict[str, Any]] = []
    if not (repo_root / TYPE_A_AUTONOMOUS_SEED_ROOT).exists():
        warnings.append(
            {
                "kind": "missing_type_a_autonomous_seed_root",
                "message": "Saved Type A autonomous seed root is missing.",
                "expected_root": str(TYPE_A_AUTONOMOUS_SEED_ROOT),
            }
        )
    if missing_ids:
        warnings.append(
            {
                "kind": "missing_type_a_autonomous_seed_ids",
                "message": "One or more requested seed ids were not found in saved Type A autonomous seeds.",
                "missing_ids": missing_ids,
                "list_command": "./repo-python kernel.py --raw-seed-autonomous-seeds 09",
            }
        )

    navigation_map_count = sum(1 for entry in entries if entry.get("navigation_map_exists"))
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "type_a_autonomous_seeds",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "seed_metadata_projection_not_raw_seed_authority",
        "governing_standard": {
            "ref": str(TYPE_A_AUTONOMOUS_SEED_STANDARD),
            "mission_template": str(TYPE_A_AUTONOMOUS_SEED_MISSION),
            "seed_template": str(TYPE_A_AUTONOMOUS_SEED_TEMPLATE),
            "owned_bands": ["cluster_flag", "flag", "card"],
        },
        "source_refs": [
            str(TYPE_A_AUTONOMOUS_SEED_ROOT),
            str(TYPE_A_AUTONOMOUS_SEED_STANDARD),
            str(TYPE_A_AUTONOMOUS_SEED_SKILL),
            str(TYPE_A_AUTONOMOUS_SEED_MISSION),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(entries),
            "query_used": False,
            "selection_method": (
                "type_a_autonomous_seed_cluster_overview"
                if band == "cluster_flag"
                else "type_a_autonomous_seed_metadata_owner_card"
            ),
            "drilldown_by": "lane" if band == "cluster_flag" else "seed_id",
            "grouping_keys": ["lane", "scope_shape", "depth_tier", "mode"] if band == "cluster_flag" else [],
            "cluster_count": len(rows) if band == "cluster_flag" else None,
            "navigation_map_count": navigation_map_count,
            "privacy_boundary": "metadata-only; raw seed/operator/proof bodies stay behind source routes",
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "cluster_row_shape": "lane_counts_with_top_seed_ids" if band == "cluster_flag" else "seed_rows",
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "mutation_rule": (
                "refresh or create saved autonomous seeds through kernel raw-seed autonomous-seed commands; "
                "do not hand-edit raw_seed.md or generated projections from this card"
            ),
        },
        "rows": rows,
        "cluster_omission_receipt": (
            {
                "omitted": [
                    "all row-level seed flags",
                    "full autonomous seed markdown bodies",
                    "raw_seed.md bodies and operator chat",
                    "raw proof bodies and provider payloads",
                ],
                "reason": "cluster_flag groups saved Type A autonomous seeds by lane before owner-card drilldown.",
                "drilldown": "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band flag --ids <seed_id>",
            }
            if band == "cluster_flag"
            else None
        ),
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band cluster_flag",
                "reason": "Browse saved Type A autonomous seed lane clusters before expanding seed rows.",
            },
            {
                "command": "./repo-python kernel.py --raw-seed-autonomous-seeds 09",
                "reason": "List saved Type A autonomous seed bundles latest-first.",
            },
            {
                "command": (
                    "./repo-python kernel.py --option-surface type_a_autonomous_seeds "
                    "--band card --ids system_atlas_crystal_architecture_comprehension"
                ),
                "reason": "Open the self-description seed owner card with validation and disclosure boundaries.",
            },
            {
                "command": (
                    "./repo-python kernel.py --raw-seed-autonomous-seed-bundle "
                    "system_atlas_crystal_architecture_comprehension"
                ),
                "reason": "Read the source-backed continuity bundle after selecting the seed id.",
            },
        ],
        "warnings": warnings,
    }


PROMPT_LEDGER_VIEW_SPECS: tuple[tuple[str, Path, str, str], ...] = (
    (
        "ledger",
        PROMPT_LEDGER_LEDGER,
        "Prompt Ledger Trace Projection",
        "Trace-level projection over Prompt Ledger events.",
    ),
    (
        "adoption_posture",
        prompt_ledger_events.ADOPTION_POSTURE_REL,
        "Prompt Adoption Posture",
        "Candidate and receipt lifecycle counts for reusable prompt lessons.",
    ),
    (
        "mission_trace_current_state",
        prompt_ledger_events.MISSION_TRACE_CURRENT_STATE_REL,
        "Mission Trace Current State",
        "Mission trace controller receipt current-state rows without making trace context an authority store.",
    ),
    (
        "recent_prompt_traces",
        prompt_ledger_events.RECENT_PROMPT_TRACES_REL,
        "Recent Prompt Traces",
        "Recent trace handles without raw prompt or thread bodies.",
    ),
    (
        "unlinked_prompt_traces",
        prompt_ledger_events.UNLINKED_PROMPT_TRACES_REL,
        "Unlinked Prompt Traces",
        "Prompt traces not yet linked to WorkItems or adoption receipts.",
    ),
    (
        "workitem_prompt_links",
        prompt_ledger_events.WORKITEM_PROMPT_LINKS_REL,
        "WorkItem Prompt Links",
        "Prompt trace to WorkItem linkage projection.",
    ),
    (
        "source_stream_cursors",
        prompt_ledger_events.SOURCE_STREAM_CURSORS_REL,
        "Source Stream Cursors",
        "Observed prompt source cursors for freshness and idempotency checks.",
    ),
    (
        "source_idempotency_keys",
        prompt_ledger_events.SOURCE_IDEMPOTENCY_KEYS_REL,
        "Source Idempotency Keys",
        "Stable source keys used to detect duplicate imports.",
    ),
    (
        "source_drift",
        prompt_ledger_events.SOURCE_DRIFT_REL,
        "Source Drift",
        "Prompt source cursor/hash drift projection.",
    ),
)


def _prompt_ledger_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _prompt_ledger_projection_counts(view_id: str, payload: Mapping[str, Any]) -> dict[str, int]:
    count_keys = (
        "event_count",
        "trace_count",
        "source_stream_count",
        "idempotency_key_count",
        "source_drift_count",
        "count",
        "receipt_count",
        "candidate_count",
        "adopted_count",
        "behavior_projection_count",
    )
    counts: dict[str, int] = {}
    for key in count_keys:
        if key in payload:
            counts[key] = _prompt_ledger_int(payload.get(key))
    if "count" not in counts:
        list_keys = {
            "ledger": "traces",
            "adoption_posture": "candidates",
            "recent_prompt_traces": "traces",
            "unlinked_prompt_traces": "traces",
            "workitem_prompt_links": "links",
            "source_stream_cursors": "streams",
            "source_idempotency_keys": "keys",
            "source_drift": "drift",
            "mission_trace_current_state": "rows",
        }
        key = list_keys.get(view_id)
        value = payload.get(key) if key else None
        if isinstance(value, list):
            counts["count"] = len(value)
    return counts


def _prompt_ledger_sample_id(item: Mapping[str, Any]) -> str:
    for key in (
        "trace_id",
        "event_id",
        "candidate_id",
        "candidate_key",
        "receipt_id",
        "work_item_id",
        "identity_value",
        "current_receipt_ref",
        "source_stream_id",
        "source_cursor",
        "idempotency_key",
    ):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


def _prompt_ledger_card_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key, value in payload.items():
        if key in {"schema_version", "authority", "projection_only", "owner"}:
            summary[key] = value
            continue
        if isinstance(value, bool | int | float | str) or value is None:
            summary[key] = value
        elif isinstance(value, list):
            sample_ids = [
                sample
                for item in value[:5]
                if isinstance(item, Mapping)
                for sample in [_prompt_ledger_sample_id(item)]
                if sample
            ]
            summary[key] = {
                "count": len(value),
                "sample_ids": sample_ids,
                "raw_rows_omitted": True,
            }
        elif isinstance(value, Mapping):
            scalar_items = {
                str(inner_key): inner_value
                for inner_key, inner_value in value.items()
                if isinstance(inner_value, bool | int | float | str) or inner_value is None
            }
            summary[key] = {
                "entry_count": len(value),
                "scalar_items": scalar_items,
                "nested_rows_omitted": len(scalar_items) != len(value),
            }
    return summary


def _prompt_ledger_rows_source(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for view_id, rel_path, title, flag in PROMPT_LEDGER_VIEW_SPECS:
        payload = _load_json(repo_root / rel_path)
        rows.append(
            {
                "id": view_id,
                "view_id": view_id,
                "path": str(rel_path),
                "title": title,
                "flag": flag,
                "payload": payload,
                "exists": (repo_root / rel_path).exists(),
            }
        )
    return rows


def _prompt_ledger_flag_row(row: Mapping[str, Any]) -> dict[str, Any]:
    view_id = str(row.get("view_id") or "")
    payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
    path = str(row.get("path") or "")
    return {
        "row_id": f"prompt_ledger:{view_id}::flag",
        "id": view_id,
        "view_id": view_id,
        "band": "flag",
        "title": row.get("title"),
        "flag": row.get("flag"),
        "path": path,
        "exists": bool(row.get("exists")),
        "schema_version": payload.get("schema_version"),
        "authority": payload.get("authority") or str(PROMPT_LEDGER_EVENTS),
        "authority_posture": "projection_browse_only_events_are_authority",
        "projection_only": True,
        "counts": _prompt_ledger_projection_counts(view_id, payload),
        "owner_surface": str(PROMPT_LEDGER_STANDARD),
        "owner_tool": str(PROMPT_LEDGER_TOOL),
        "owner_check_command": "./repo-python tools/meta/observability/prompt_ledger.py rebuild --check",
        "owner_validate_command": "./repo-python tools/meta/observability/prompt_ledger.py validate",
        "owner_repair_command": "./repo-python tools/meta/observability/prompt_ledger.py rebuild",
        "drilldown_command": f"./repo-python kernel.py --option-surface prompt_ledger --band card --ids {view_id}",
        "evidence_command": f"jq 'keys' {path}",
        "privacy_boundary": "metadata_and_hashes_only_no_raw_operator_or_type_b_thread_bodies",
    }


def _prompt_ledger_card_row(row: Mapping[str, Any]) -> dict[str, Any]:
    card = _prompt_ledger_flag_row(row)
    view_id = str(card.get("view_id") or "")
    payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
    card["row_id"] = f"prompt_ledger:{view_id}::card"
    card["band"] = "card"
    card["projection_keys"] = sorted(str(key) for key in payload.keys())
    card["projection_summary"] = _prompt_ledger_card_summary(payload)
    card["omission_receipt"] = {
        "omitted": [
            "raw Type B/operator thread bodies",
            "raw prompt/response text",
            "full Prompt Ledger event chain",
            "full nested projection rows",
        ],
        "reason": "Prompt Ledger option cards expose provenance handles, counts, owner routes, and privacy-safe sample ids only.",
        "drilldowns": [
            "./repo-python tools/meta/observability/prompt_ledger.py validate",
            "./repo-python tools/meta/observability/prompt_ledger.py rebuild --check",
            f"jq '.' {card['path']}",
        ],
    }
    return card


def build_prompt_ledger_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="prompt_ledger",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "prompt_ledger_band_not_owned",
                "message": "Prompt Ledger owns flag/card browse rows only; use card ids for selected projection views.",
                "owned_bands": ["flag", "card"],
            }
        )
        return payload

    rows_source = _prompt_ledger_rows_source(repo_root)
    by_id = {str(row["id"]): row for row in rows_source}
    if ids:
        selected = [by_id[item] for item in ids if item in by_id]
        missing_ids = [item for item in ids if item not in by_id]
    else:
        selected = rows_source
        missing_ids = []
    rows = [_prompt_ledger_card_row(row) for row in selected] if band == "card" else [_prompt_ledger_flag_row(row) for row in selected]
    projection_check = prompt_ledger_events.check_projection_files(repo_root)
    ledger_payload = _load_json(repo_root / PROMPT_LEDGER_LEDGER)
    total_count = _prompt_ledger_int(ledger_payload.get("trace_count")) + len([row for row in rows_source if row.get("exists")])

    warnings: list[dict[str, Any]] = []
    missing_projection_paths = [str(row.get("path") or "") for row in rows_source if not row.get("exists")]
    if missing_projection_paths:
        warnings.append(
            {
                "kind": "missing_prompt_ledger_projection",
                "message": "One or more Prompt Ledger projections are missing; rebuild through the owner tool.",
                "refs": missing_projection_paths,
                "repair_command": "./repo-python tools/meta/observability/prompt_ledger.py rebuild",
            }
        )
    if not projection_check.get("ok"):
        warnings.append(
            {
                "kind": "prompt_ledger_projection_stale",
                "message": "Prompt Ledger projections do not match state/prompt_ledger/events.jsonl.",
                "mismatches": list(projection_check.get("mismatches") or []),
                "repair_command": "./repo-python tools/meta/observability/prompt_ledger.py rebuild",
            }
        )

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "prompt_ledger",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "projection_browse_only_events_are_authority",
        "projection_check": projection_check,
        "governing_standard": {
            "ref": str(PROMPT_LEDGER_STANDARD),
            "schema_version": _load_json(repo_root / PROMPT_LEDGER_STANDARD).get("schema_version"),
            "owned_bands": ["flag", "card"],
        },
        "source_refs": [
            str(PROMPT_LEDGER_EVENTS),
            str(PROMPT_LEDGER_LEDGER),
            str(PROMPT_LEDGER_VIEWS_ROOT),
            str(PROMPT_LEDGER_STANDARD),
            str(PROMPT_LEDGER_TOOL),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": total_count,
            "query_used": False,
            "selection_method": "prompt_ledger_projection_view_enumeration",
            "drilldown_by": "view_id",
            "trace_count": _prompt_ledger_int(ledger_payload.get("trace_count")),
            "event_count": _prompt_ledger_int(ledger_payload.get("event_count")),
            "view_count": len(rows_source),
            "privacy_boundary": "cards omit raw prompt/thread bodies and raw event payloads",
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "cluster_first_for_high_cardinality": False,
            "adapter_supported_bands": ["flag", "card"],
            "mutation_rule": "append Prompt Ledger events through prompt_ledger.py; never edit projections from this surface",
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface prompt_ledger --band card --ids adoption_posture",
                "reason": "Inspect prompt lesson adoption posture without opening raw thread bodies.",
            },
            {
                "command": "./repo-python tools/meta/observability/prompt_ledger.py validate",
                "reason": "Validate the event chain and strict JSON before adopting or linking traces.",
            },
            {
                "command": "./repo-python tools/meta/observability/prompt_ledger.py rebuild --check",
                "reason": "Check whether Prompt Ledger projections are fresh against the event log.",
            },
        ],
        "warnings": warnings,
    }


def _option_surface_lens_packet(payload: Mapping[str, Any], *, artifact_kind: str, band: str, command: str) -> dict[str, Any]:
    """Return the attention-lens metadata shared by option-surface packets."""
    source_refs = list(payload.get("source_refs") or []) if isinstance(payload.get("source_refs"), list) else []
    governing_standard = payload.get("governing_standard")
    standard_ref = None
    if isinstance(governing_standard, Mapping):
        standard_ref = governing_standard.get("ref")
    rows = payload.get("rows")
    row_count = len(rows) if isinstance(rows, list) else None
    return {
        "view_profile": "option_surface_lens_packet_v0",
        "surface_id": f"option_surface:{artifact_kind}",
        "view_surface": command,
        "authority_posture": payload.get("authority_posture") or "generated_artifact_projection",
        "safe_decision_supported": (
            "Select stable row handles, cluster/card drilldowns, omissions, and evidence routes; "
            "do not choose operational control flow from this packet alone."
        ),
        "source_payload_owner": {
            "authority_plane": "source_payload",
            "source_refs": source_refs[:8],
            "standard_ref": standard_ref,
            "source_mutation_allowed_by_this_profile": False,
        },
        "writes_attention_roles": [
            "selected_kind",
            "candidate_handles_seen",
            "focused_handles",
            "selected_handles_explicit_only",
            "trusted_authorities_explicit_only",
            "acted_on_handles_explicit_only",
            "source_refs",
            "omission_receipts",
            "drilldown_handles",
            "freshness_constraints",
        ],
        "attention_delta_shape": {
            "seen_surface": f"option_surface:{artifact_kind}",
            "selected_kind": artifact_kind,
            "selected_band": band,
            "row_count": row_count,
            "handle_source": "rows[].canonical_handle or rows[].handle; fallback_inference is reported by the reducer",
        },
        "mutation_allowed_by_this_profile": False,
    }


def _with_option_surface_contract(payload: dict[str, Any], *, normalized_kind: str) -> dict[str, Any]:
    artifact_kind = str(payload.get("artifact_kind") or normalized_kind)
    band = str(payload.get("band") or "flag")
    command = f"./repo-python kernel.py --option-surface {artifact_kind} --band {band}"
    payload.setdefault("surface_role", ATLAS_PROJECTION)
    payload.setdefault("first_contact_allowed", False)
    payload.setdefault("control_replacement", ENTRY_REPLACEMENT)
    payload.setdefault(
        "surface_contract",
        atlas_projection_contract(
            surface_id=f"option_surface:{artifact_kind}",
            command=command,
        ),
    )
    payload.setdefault(
        "lens_packet",
        _option_surface_lens_packet(payload, artifact_kind=artifact_kind, band=band, command=command),
    )
    boundary = payload.setdefault("navigation_boundary", {})
    if isinstance(boundary, dict):
        boundary.setdefault("surface_role", ATLAS_PROJECTION)
        boundary.setdefault("first_contact_allowed", False)
        boundary.setdefault("control_replacement", ENTRY_REPLACEMENT)
        boundary.setdefault("allowed_after", "entry_packet_selected_kind_or_explicit_operator_browse")
        boundary.setdefault("not_control_entry", True)
    rows = payload.get("rows")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and not str(row.get("claim") or "").strip():
                for key in (
                    "statement",
                    "formal_clause",
                    "flag",
                    "summary",
                    "one_liner",
                    "purpose",
                    "one_sentence_description",
                    "description",
                    "title",
                    "label",
                    "id",
                    "row_id",
                ):
                    value = _truncate_words(str(row.get(key) or ""), max_chars=260)
                    if value:
                        row["claim"] = value
                        row.setdefault("claim_source", f"projection_fallback:{key}")
                        break
    return payload


def build_option_surface(
    repo_root: Path | str,
    artifact_kind: str,
    *,
    band: str = "flag",
    ids: str | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Build a deterministic standard-owned option surface."""
    root = Path(repo_root)
    normalized_kind = _normalize_artifact_kind(artifact_kind)
    normalized_band = str(band or "flag").strip().lower()
    selected_ids = parse_ids(ids)
    generated_at = _utc_now()

    if normalized_band not in OPTION_SURFACE_BANDS:
        return _with_option_surface_contract(
            _profile_gap_payload(
                repo_root=root,
                artifact_kind=normalized_kind,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    # Per-kind atom-band gate. The atom band is paper-module-owned per
    # std_paper_module.json::compression_authoring_contract; other kinds either own their own
    # cluster_flag/flag/card surfaces or have not authored an atom contract yet. Returning a
    # profile_gap here prevents silent fallback to flag rows under a band:atom request.
    _ATOM_BAND_OWNERS = {"paper_modules"}
    if normalized_band == "atom" and normalized_kind not in _ATOM_BAND_OWNERS:
        gap_payload = _profile_gap_payload(
            repo_root=root,
            artifact_kind=normalized_kind,
            band=normalized_band,
            ids=selected_ids,
            generated_at=generated_at,
        )
        gap_payload["warnings"].append(
            {
                "kind": "atom_band_not_owned_by_kind",
                "message": (
                    "The atom band is paper-module-owned. "
                    f"Use --option-surface {normalized_kind} --band flag (or card) for this kind."
                ),
                "owners": sorted(_ATOM_BAND_OWNERS),
            }
        )
        return _with_option_surface_contract(gap_payload, normalized_kind=normalized_kind)

    if normalized_kind in {"raw_seed", "raw_seed_paper"}:
        return _with_option_surface_contract(
            _route_affordance_gap_payload(
                repo_root=root,
                artifact_kind=normalized_kind,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "derived_facts":
        cache_path = root / "codex/hologram/facts/navigation_cache.json"
        if cache_path.is_file():
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            cache = {"summary": {}, "warnings": [{"kind": "missing_navigation_cache", "path": str(cache_path)}]}

        rows: list[dict[str, Any]] = []
        index_names = (
            "tag_index",
            "facet_index",
            "value_index",
            "subject_kind_index",
            "fact_family_index",
            "mechanism_ref_index",
        )
        id_keys = (
            "key",
            "id",
            "value",
            "tag",
            "facet",
            "subject_kind",
            "family_id",
            "fact_family",
            "mechanism_ref",
        )
        for index_name in index_names:
            for row in cache.get(index_name) or []:
                if not isinstance(row, Mapping):
                    continue
                row_key = next((str(row[key]) for key in id_keys if row.get(key)), "unknown")
                rows.append(
                    {
                        "row_id": f"derived_fact_index:{index_name}:{row_key}",
                        "artifact_kind": "derived_fact_index",
                        "band": normalized_band,
                        "index": index_name,
                        **dict(row),
                    }
                )

        payload: dict[str, Any] = {
            "kind": "standard_owned_option_surface",
            "schema_version": "standard_owned_option_surface_v0",
            "generated_at": generated_at,
            "artifact_kind": "derived_facts",
            "band": normalized_band,
            "selection": {"mode": "all", "ids": selected_ids},
            "profile_status": "supported",
            "authority_posture": "generated_state_axis_artifact",
            "source_refs": [
                "codex/doctrine/facts/fact_registry.json",
                "codex/standards/std_derived_fact.json",
                "codex/hologram/facts/ledger.json",
                "codex/hologram/facts/navigation_cache.json",
            ],
            "summary": {
                "row_count": len(rows),
                "total_available": int((cache.get("summary") or {}).get("fact_count") or 0),
                "selection_method": "derived_fact_hologram_indexes",
            },
            "rows": rows,
            "next": [
                {
                    "command": "./repo-python kernel.py --facts --band cluster_flag",
                    "reason": "Open the native generated facts projection.",
                }
            ],
        }
        if cache.get("warnings"):
            payload["warnings"] = cache.get("warnings")
        return _with_option_surface_contract(payload, normalized_kind=normalized_kind)

    if normalized_kind == "kinds":
        from system.lib.kind_atlas import build_kind_atlas

        return build_kind_atlas(root, band=normalized_band, ids=selected_ids)

    if normalized_kind == "standards":
        return _with_option_surface_contract(
            build_standards_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "principles":
        return _with_option_surface_contract(
            build_principles_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "teleologies":
        return _with_option_surface_contract(
            build_teleologies_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "principles_by_teleology":
        return _with_option_surface_contract(
            build_principles_by_teleology_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "anti_principles":
        return _with_option_surface_contract(
            build_anti_principles_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "concepts":
        return _with_option_surface_contract(
            build_concepts_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "mechanisms":
        return _with_option_surface_contract(
            build_mechanisms_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "concept_mechanism_candidates":
        return _with_option_surface_contract(
            build_concept_mechanism_candidates_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "concept_mechanism_candidate_curations":
        return _with_option_surface_contract(
            build_concept_mechanism_candidate_curations_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "axiom_candidates":
        return _with_option_surface_contract(
            build_axiom_candidates_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "axioms_by_teleology":
        return _with_option_surface_contract(
            build_axioms_by_teleology_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "anti_axioms":
        return _with_option_surface_contract(
            build_anti_axioms_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "imaginations":
        return _with_option_surface_contract(
            build_imaginations_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "skills":
        return _with_option_surface_contract(
            build_skills_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "task_ledger":
        return _with_option_surface_contract(
            build_task_ledger_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "prompt_ledger":
        return _with_option_surface_contract(
            build_prompt_ledger_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "prompt_shelf_metadata":
        return _with_option_surface_contract(
            build_prompt_shelf_metadata_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "frontend_views":
        return _with_option_surface_contract(
            build_frontend_views_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "raw_seed_shards":
        return _with_option_surface_contract(
            build_raw_seed_shards_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "type_a_autonomous_seeds":
        return _with_option_surface_contract(
            build_type_a_autonomous_seeds_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "external_benchmark_calibration":
        return _with_option_surface_contract(
            build_external_benchmark_calibration_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "annex_patterns":
        return _with_option_surface_contract(
            build_annex_patterns_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "annex_distillation_patterns":
        return _with_option_surface_contract(
            build_annex_distillation_patterns_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "microcosm_extracted_patterns":
        return _with_option_surface_contract(
            build_microcosm_extracted_patterns_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "python_files":
        return _with_option_surface_contract(
            build_python_files_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "python_scopes":
        return _with_option_surface_contract(
            build_python_scopes_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "frontend_components":
        return _with_option_surface_contract(
            build_frontend_components_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "compression_profiles":
        return _with_option_surface_contract(
            build_compression_profiles_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "system_terms":
        return _with_option_surface_contract(
            build_system_terms_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "system_atlas":
        return _with_option_surface_contract(
            build_system_atlas_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    if normalized_kind == "config_authorities":
        from system.lib.config_authority_registry import build_config_authority_option_surface

        return _with_option_surface_contract(
            build_config_authority_option_surface(
                root,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    # Wave_003B: generated-artifact-surface fallback (transform_job_receipts,
    # row_patches, compliance_ledger, standard_skill_map). Returns None when
    # the kind is not one of the four; the caller falls through to the
    # paper-module branch below or the unsupported-kind profile gap.
    try:
        from system.lib.kernel.commands.generated_artifact_surfaces import build_extra_option_surface
        extra_payload = build_extra_option_surface(
            root,
            normalized_kind,
            band=normalized_band,
            ids=selected_ids,
            generated_at=generated_at,
        )
        if extra_payload is not None:
            return _with_option_surface_contract(extra_payload, normalized_kind=normalized_kind)
    except ImportError:
        pass

    if normalized_kind != "paper_modules":
        return _with_option_surface_contract(
            _profile_gap_payload(
                repo_root=root,
                artifact_kind=normalized_kind,
                band=normalized_band,
                ids=selected_ids,
                generated_at=generated_at,
            ),
            normalized_kind=normalized_kind,
        )

    index_path = root / PAPER_MODULE_INDEX
    standard_path = root / PAPER_MODULE_STANDARD
    if not index_path.exists() or not standard_path.exists():
        payload = _profile_gap_payload(
            repo_root=root,
            artifact_kind=normalized_kind,
            band=normalized_band,
            ids=selected_ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The paper-module index or standard file is missing.",
                "refs": [_relative(index_path, root), _relative(standard_path, root)],
            }
        )
        return _with_option_surface_contract(payload, normalized_kind=normalized_kind)

    index = _load_json(index_path)
    route_coverage_path = root / PAPER_MODULE_ROUTE_COVERAGE
    route_rows: dict[str, dict[str, Any]] = {}
    if route_coverage_path.exists():
        route_coverage = _load_json(route_coverage_path)
        raw_route_rows = route_coverage.get("paper_module_routes")
        if isinstance(raw_route_rows, dict):
            route_rows = {
                str(slug): row
                for slug, row in raw_route_rows.items()
                if isinstance(row, dict)
            }
    modules = list(index.get("modules") or [])
    modules_by_slug = {str(module.get("slug") or ""): module for module in modules}
    if selected_ids:
        rows_source = [modules_by_slug[slug] for slug in selected_ids if slug in modules_by_slug]
        missing_ids = [slug for slug in selected_ids if slug not in modules_by_slug]
    else:
        rows_source = sorted(modules, key=lambda item: str(item.get("slug") or ""))
        missing_ids = []

    if normalized_band == "cluster_flag":
        rows = _paper_module_cluster_rows(rows_source, index=index, route_rows=route_rows)
    elif normalized_band == "atom":
        rows = [_atom_row(module, index=index) for module in rows_source]
    elif normalized_band == "card":
        rows = [_card_row(module, index=index, repo_root=root) for module in rows_source]
    else:
        rows = [_flag_row(module, index=index) for module in rows_source]

    return _with_option_surface_contract({
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "paper_modules",
        "band": normalized_band,
        "selection": {
            "mode": "ids" if selected_ids else "all",
            "ids": selected_ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "standard_owned_projection_not_source_authority",
        "governing_standard": {
            "ref": str(PAPER_MODULE_STANDARD),
            "schema_version": _load_json(standard_path).get("schema_version"),
            "owned_bands": ["cluster_flag", "atom", "flag", "card"],
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "skill_ref": str(PROFILE_SKILL),
        "source_refs": [
            str(PAPER_MODULE_INDEX),
            str(PAPER_MODULE_ROUTE_COVERAGE),
            str(PAPER_MODULE_STANDARD),
            str(NAVIGATION_THEORY),
            str(PROFILE_SKILL),
        ],
        "raw_seed_anchors": [
            "raw_seed.md:3616",
            "raw_seed.md:3678",
            "raw_seed.md:3723",
            "raw_seed.md:3740",
            "raw_seed.md:3744",
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(modules),
            "query_used": False,
            "cluster_currentness": {
                "index_freshness": (
                    (index.get("freshness") or {}).get("status")
                    or (index.get("freshness") or {}).get("sync_status")
                )
                if isinstance(index.get("freshness"), Mapping)
                else None,
                "index_generated_at": index.get("generated_at"),
            }
            if normalized_band == "cluster_flag"
            else None,
            "cluster_semantics": (
                "canonical_subdomain_collapses_authored_and_suggested_then_hierarchy_then_labeled_heuristic_fallback"
                if normalized_band == "cluster_flag"
                else None
            ),
            "cluster_row_output_policy": (
                f"compact_clusters_top_{PAPER_MODULE_CLUSTER_TOP_ID_LIMIT}_ids_governance_by_drilldown"
                if normalized_band == "cluster_flag"
                else None
            ),
            "cluster_authority_distribution": (
                _paper_module_cluster_authority_summary(rows)
                if normalized_band == "cluster_flag"
                else None
            ),
            "selection_method": (
                "artifact_kind_cluster_overview"
                if normalized_band == "cluster_flag"
                else "artifact_kind_enumeration"
            ),
            "drilldown_by": "cluster_id" if normalized_band == "cluster_flag" else "stable_ids",
        },
        "cluster_omission_receipt": {
            "omitted": [
                "all row-level flag rows",
                "card/context module bodies",
                "transitive dependency closures",
                "per-cluster route metadata and governing refs",
            ],
            "reason": "cluster_flag is the global overview rung for high-cardinality paper modules; row-level flags require an explicit cluster/id drilldown.",
            "authority_collapse_rule": "Authored primary_subdomain and heuristic suggested_primary_subdomain collapse into one canonical subdomain cluster; per-row cluster_source_axis and per-cluster authority_distribution carry the trust posture without splitting the contents page.",
            "drilldown": "./repo-python kernel.py --option-surface paper_modules --band flag --ids <slug1>,<slug2>",
        }
        if normalized_band == "cluster_flag"
        else {},
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "normal_navigation_should_read_projection_not_rebuild_it": True,
            "cluster_first_for_high_cardinality": normalized_band == "cluster_flag",
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface paper_modules --band atom",
                "reason": "Cheapest selection-affordance row across all paper modules; for whole-system reasoning.",
            },
            {
                "command": "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
                "reason": "Browse paper-module clusters before expanding row-level flags.",
            },
            {
                "command": "./repo-python kernel.py --option-surface paper_modules --band card --ids <slug1>,<slug2>",
                "reason": "Drill selected ids without guessing hidden keywords.",
            },
        ],
        "warnings": [],
    }, normalized_kind=normalized_kind)


def build_principles_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    principles_path = repo_root / RAW_SEED_PRINCIPLES
    standard_path = repo_root / RAW_SEED_PRINCIPLES_STANDARD
    if not principles_path.exists() or not standard_path.exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="principles",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The raw-seed principles registry or standard file is missing.",
                "refs": [_relative(principles_path, repo_root), _relative(standard_path, repo_root)],
            }
        )
        return payload

    payload = _load_json(principles_path)
    principles = [item for item in payload.get("principles", []) if isinstance(item, dict)]
    _, teleology_nodes_by_id, teleology_warnings = _load_teleology_nodes(repo_root)
    incoming_concept_edges_by_principle = _principle_incoming_concept_edges(repo_root)
    principles_by_key: dict[str, dict[str, Any]] = {}
    for principle in principles:
        principle_id = str(principle.get("id") or "")
        slug = str(principle.get("slug") or "")
        if principle_id:
            principles_by_key[principle_id] = principle
            if principle_id == "pri_121":
                principles_by_key["pri_121_candidate"] = principle
        if slug:
            principles_by_key[slug] = principle

    if ids:
        rows_source = [principles_by_key[item] for item in ids if item in principles_by_key]
        missing_ids = [item for item in ids if item not in principles_by_key]
    else:
        rows_source = sorted(principles, key=_principle_sort_key)
        missing_ids = []

    flag_rows_for_summary = [
        _principle_flag_row(
            principle,
            teleology_nodes_by_id=teleology_nodes_by_id,
            incoming_concept_edges_by_principle=incoming_concept_edges_by_principle,
        )
        for principle in rows_source
    ]
    teleology_population = _teleology_population_summary(
        principles,
        teleology_nodes_by_id=teleology_nodes_by_id,
    )
    selected_teleology_population = _teleology_population_summary(
        rows_source,
        teleology_nodes_by_id=teleology_nodes_by_id,
    )
    requested_band = band
    band_redirect: dict[str, Any] | None = None
    if band == "card" and not ids:
        band = "cluster_flag"
        band_redirect = {
            "from": "card",
            "to": "cluster_flag",
            "reason": (
                "principles all-card is a high-cardinality raw-seed-principles expansion; "
                "row-level cards require explicit --ids."
            ),
            "explicit_row_card_command": "./repo-python kernel.py --option-surface principles --band card --ids <pri_id>",
        }

    if band == "cluster_flag":
        rows = _principle_cluster_rows(flag_rows_for_summary)
    elif band == "tape":
        if not ids:
            payload = _profile_gap_payload(
                repo_root=repo_root,
                artifact_kind="principles",
                band=band,
                ids=ids,
                generated_at=generated_at,
            )
            payload["warnings"].append(
                {
                    "kind": "tape_requires_ids",
                    "message": "The tape band emits one L0–L4 row per id; pass --ids <pri_id>[,...] (avoids enumerating the full registry).",
                }
            )
            return payload
        standard = _load_json(standard_path)
        layer_reg = _principle_layer_registry(standard)
        rows = [
            _principle_tape_row(
                principle,
                layers=layer_reg,
                teleology_nodes_by_id=teleology_nodes_by_id,
            )
            for principle in rows_source
        ]
    else:
        rows = (
            [
                _principle_card_row(
                    principle,
                    teleology_nodes_by_id=teleology_nodes_by_id,
                    incoming_concept_edges_by_principle=incoming_concept_edges_by_principle,
                )
                for principle in rows_source
            ]
            if band == "card"
            else [
                _principle_flag_row(
                    principle,
                    teleology_nodes_by_id=teleology_nodes_by_id,
                    incoming_concept_edges_by_principle=incoming_concept_edges_by_principle,
                )
                for principle in rows_source
            ]
        )
    type_groups = [] if band == "cluster_flag" else _principle_type_groups(flag_rows_for_summary)
    status_counts: dict[str, int] = {}
    for row in flag_rows_for_summary:
        status = str(row.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    selected_incoming_concept_edge_count = sum(
        int(row.get("incoming_concept_edge_count") or 0) for row in flag_rows_for_summary
    )

    warnings = list(teleology_warnings)
    payload = {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "principles",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "standard_owned_projection_not_source_authority",
        "governing_standard": {
            "ref": str(RAW_SEED_PRINCIPLES_STANDARD),
            "schema_version": _load_json(standard_path).get("schema_version"),
            "owned_bands": ["cluster_flag", "flag", "card", "tape"],
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "skill_ref": "codex/doctrine/skills/doctrine/principles_curation.md",
        "source_refs": [
            str(RAW_SEED_PRINCIPLES),
            str(RAW_SEED_PRINCIPLES_STANDARD),
            "codex/doctrine/skills/doctrine/principles_curation.md",
            str(NAVIGATION_THEORY),
        ],
        "raw_seed_anchors": [
            "par_phase_09_raw_seed__navigation_layer_principle_type_surface_001",
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(principles),
            "query_used": False,
            "selection_method": (
                "artifact_kind_cluster_overview_grouped_by_type"
                if band == "cluster_flag"
                else "ids_required_compression_tape"
                if band == "tape"
                else "artifact_kind_enumeration_grouped_by_type"
            ),
            "drilldown_by": "type" if band == "cluster_flag" else "principle_id_or_slug",
            "type_count": len(rows) if band == "cluster_flag" else len(type_groups),
            "status_counts": dict(sorted(status_counts.items())),
            "teleology_population": teleology_population,
            "selected_teleology_population": selected_teleology_population,
            "incoming_concept_edge_population": {
                "all_principles_with_incoming_concept_edges": len(incoming_concept_edges_by_principle),
                "all_incoming_concept_edge_count": sum(
                    len(edges) for edges in incoming_concept_edges_by_principle.values()
                ),
                "selected_incoming_concept_edge_count": selected_incoming_concept_edge_count,
            },
            "grouping_keys": ["type", "scope"] if band == "cluster_flag" else [],
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "grouped_by_native_type": True,
            "one_sentence_first": True,
            "source_authority_remains_raw_seed_principles": True,
            "tape_emits_full_compression_ladder": band == "tape",
            "adapter_supported_bands": ["cluster_flag", "flag", "card", "tape"],
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "cluster_row_shape": "compact_principle_type_counts_with_top_ids"
            if band == "cluster_flag"
            else "principle_rows",
            "flag_surfaces_incoming_concept_edges": True,
        },
        "type_groups": type_groups,
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface principles --band cluster_flag",
                "reason": "Browse principle type clusters before expanding row-level flags.",
            },
            {
                "command": "./repo-python kernel.py --option-surface principles --band flag --ids <pri_id>[,<pri_id>...]",
                "reason": "Browse explicit principles by id with one-sentence descriptions before opening the registry.",
            },
            {
                "command": "./repo-python kernel.py --option-surface principles --band card --ids <pri_id>",
                "reason": "Drill selected principle ids to tests, edge context, and evidence pointers.",
            },
            {
                "command": "./repo-python kernel.py --option-surface principles --band tape --ids <pri_id>[,<pri_id>...]",
                "reason": "Character-budgeted L0–L4 ladder, layer debt, and routes in one row per id.",
            },
        ],
        "warnings": warnings,
    }
    if band_redirect is not None:
        payload["requested_band"] = requested_band
        payload["band_redirect"] = band_redirect
        warnings.append(
            {
                "kind": "high_cardinality_card_redirect",
                "message": "Rendered cluster_flag instead of all principle cards.",
            }
        )
    return payload


def build_axiom_candidates_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    ledger_path = repo_root / RAW_SEED_AXIOM_CANDIDATES
    standard_path = repo_root / STD_AXIOM_CANDIDATE
    if not ledger_path.exists() or not standard_path.exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="axiom_candidates",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": "The system axiom candidates ledger or standard file is missing.",
                "refs": [_relative(ledger_path, repo_root), _relative(standard_path, repo_root)],
            }
        )
        return payload

    payload = _load_json(ledger_path)
    axiom_candidates = [row for row in payload.get("axiom_candidates", []) if isinstance(row, dict)]
    _, teleology_nodes_by_id, teleology_warnings = _load_teleology_nodes(repo_root)
    by_id: dict[str, dict[str, Any]] = {}
    for row in axiom_candidates:
        ax_id = str(row.get("id") or "")
        slug = str(row.get("slug") or "")
        if ax_id:
            by_id[ax_id] = row
        if slug:
            by_id[slug] = row

    if ids:
        rows_source = [by_id[i] for i in ids if i in by_id]
        missing_ids = [i for i in ids if i not in by_id]
    else:
        rows_source = sorted(axiom_candidates, key=lambda item: str(item.get("id") or ""))
        missing_ids = []

    if band == "tape" and not ids:
        oob = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="axiom_candidates",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        oob["warnings"].append(
            {
                "kind": "tape_requires_ids",
                "message": "The tape band emits A0–A4 rows; pass --ids <axiom_candidate_id>[,...].",
            }
        )
        return oob

    standard = _load_json(standard_path)
    layer_reg = _axiom_layer_registry(standard)
    teleology_population = _teleology_population_summary(
        axiom_candidates,
        teleology_nodes_by_id=teleology_nodes_by_id,
    )
    selected_teleology_population = _teleology_population_summary(
        rows_source,
        teleology_nodes_by_id=teleology_nodes_by_id,
    )
    if band == "card":
        rows = [_axiom_card_row(r, teleology_nodes_by_id=teleology_nodes_by_id) for r in rows_source]
    elif band == "tape":
        rows = [
            _axiom_tape_row(r, layers=layer_reg, teleology_nodes_by_id=teleology_nodes_by_id)
            for r in rows_source
        ]
    else:
        rows = [_axiom_flag_row(r, teleology_nodes_by_id=teleology_nodes_by_id) for r in rows_source]

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "axiom_candidates",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "candidate_projection_not_source_authority",
        "governing_standard": {
            "ref": str(STD_AXIOM_CANDIDATE),
            "schema_version": standard.get("schema_version"),
            "owned_bands": ["flag", "card", "tape"],
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "skill_ref": "codex/doctrine/skills/doctrine/system_axiom_candidate_curation.md",
        "source_refs": [
            str(RAW_SEED_AXIOM_CANDIDATES),
            str(STD_AXIOM_CANDIDATE),
            "codex/doctrine/skills/doctrine/system_axiom_candidate_curation.md",
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(axiom_candidates),
            "query_used": False,
            "selection_method": "ids_required_compression_tape" if band == "tape" else "artifact_kind_enumeration",
            "drilldown_by": "axiom_candidate_id_or_slug",
            "teleology_population": teleology_population,
            "selected_teleology_population": selected_teleology_population,
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "candidate_not_active_doctrine": True,
            "tape_emits_full_compression_ladder": band == "tape",
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface axiom_candidates --band flag",
                "reason": "Browse all candidate axioms with formal/dense hooks and drill routes.",
            },
            {
                "command": "./repo-python kernel.py --option-surface axiom_candidates --band card --ids <axiom_candidate_id>",
                "reason": "Bounded card: clauses, five-band text, and top evidence without opening the full ledger row.",
            },
            {
                "command": "./repo-python kernel.py --option-surface axiom_candidates --band tape --ids <axiom_candidate_id>",
                "reason": "Per-layer budget flags, population debt, and routes in one row.",
            },
        ],
        "warnings": teleology_warnings,
    }


def _imagination_flag_row(row: dict[str, Any]) -> dict[str, Any]:
    imagination_id = str(row.get("imagination_id") or "")
    title = str(row.get("title") or "")
    voice_anchor = str(row.get("voice_anchor_summary") or "")
    file_ref = str(row.get("file") or "")
    return {
        "imagination_id": imagination_id,
        "slug": str(row.get("slug") or ""),
        "title": title,
        "claim": voice_anchor or title,
        "status": str(row.get("status") or ""),
        "authored_at": str(row.get("authored_at") or ""),
        "authored_by": str(row.get("authored_by") or ""),
        "schema_version": str(row.get("schema_version") or ""),
        "voice_anchor_summary": voice_anchor,
        "primary_substrate_seam": str(row.get("primary_substrate_seam") or ""),
        "retirement_trigger_summary": str(row.get("retirement_trigger_summary") or ""),
        "migrated_from_count": int(row.get("migrated_from_count") or 0),
        "migrated_from_axiom_candidate_ids": list(row.get("migrated_from_axiom_candidate_ids") or []),
        "is_migrated": int(row.get("migrated_from_count") or 0) > 0,
        "source_ref": file_ref,
        "drilldown_command": (
            f"./repo-python kernel.py --option-surface imaginations --band card "
            f"--ids {imagination_id}"
            if imagination_id
            else ""
        ),
        "convenience_command": (
            f"./repo-python kernel.py --imagination {imagination_id}"
            if imagination_id
            else ""
        ),
    }


def _imagination_card_row(row: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    base = _imagination_flag_row(row)
    file_rel = str(row.get("file") or "")
    file_path = repo_root / file_rel if file_rel else None
    scene_excerpt = (
        _extract_markdown_section(file_path, "Present-tense scene", max_chars=900)
        if file_path
        else ""
    )
    deliverable_excerpt = (
        _extract_markdown_section(file_path, "Deliverable shape", max_chars=400)
        if file_path
        else ""
    )
    becomes_easy_excerpt = (
        _extract_markdown_section(file_path, "What becomes easy", max_chars=400)
        if file_path
        else ""
    )
    no_longer_excerpt = (
        _extract_markdown_section(file_path, "What no longer happens", max_chars=400)
        if file_path
        else ""
    )
    return {
        **base,
        "file": file_rel,
        "source_ref": file_rel,
        "truth_posture": str(row.get("truth_posture") or ""),
        "voice_anchor_count": int(row.get("voice_anchor_count") or 0),
        "voice_anchor_checked_counts": dict(row.get("voice_anchor_checked_counts") or {}),
        "substrate_count": int(row.get("substrate_count") or 0),
        "substrate_resolution_status_counts": dict(
            row.get("substrate_resolution_status_counts") or {}
        ),
        "scene_fixture_count": int(row.get("scene_fixture_count") or 0),
        "scene_fixture_posture_counts": dict(row.get("scene_fixture_posture_counts") or {}),
        "migrated_from_records": list(row.get("migrated_from_records") or []),
        "migrated_from_action_counts": dict(row.get("migrated_from_action_counts") or {}),
        "migrated_from_deliverable_ids": list(row.get("migrated_from_deliverable_ids") or []),
        "present_tense_scene_excerpt": scene_excerpt,
        "deliverable_shape_excerpt": deliverable_excerpt,
        "what_becomes_easy_excerpt": becomes_easy_excerpt,
        "what_no_longer_happens_excerpt": no_longer_excerpt,
        "evidence_command": (
            f"./repo-python kernel.py --imagination {base['imagination_id']}"
            if base["imagination_id"]
            else ""
        ),
        "preservation_note": (
            "If migrated_from_count > 0, the source teleological_deliverables[] array "
            "is preserved in system_axiom_candidates.json per std_system_axiom_candidate.json "
            "row contract; this imagination lifts the predecessor scaffolds without removing them."
        ),
    }


def build_imaginations_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"flag", "card"}:
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="imaginations",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "unsupported_band_for_kind",
                "message": (
                    f"Band {band!r} is not supported for imaginations. "
                    "Supported bands: flag, card."
                ),
                "supported_bands": ["flag", "card"],
            }
        )
        return payload

    index_path = repo_root / IMAGINATION_INDEX
    standard_path = repo_root / STD_IMAGINATION
    if not index_path.exists() or not standard_path.exists():
        payload = _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="imaginations",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )
        payload["warnings"].append(
            {
                "kind": "missing_projection_input",
                "message": (
                    "The imaginations index or standard file is missing. "
                    "Run ./repo-python tools/meta/factory/build_imagination_index.py --write."
                ),
                "refs": [_relative(index_path, repo_root), _relative(standard_path, repo_root)],
            }
        )
        return payload

    index = _load_json(index_path)
    rows_data = [r for r in (index.get("imaginations") or []) if isinstance(r, dict)]
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows_data:
        for key in (row.get("imagination_id"), row.get("slug")):
            if isinstance(key, str) and key:
                by_id[key] = row

    if ids:
        rows_source = [by_id[i] for i in ids if i in by_id]
        missing_ids = [i for i in ids if i not in by_id]
    else:
        rows_source = sorted(rows_data, key=lambda r: str(r.get("imagination_id") or ""))
        missing_ids = []

    if band == "card":
        rows = [_imagination_card_row(r, repo_root=repo_root) for r in rows_source]
    else:
        rows = [_imagination_flag_row(r) for r in rows_source]

    summary_in = index.get("summary") or {}
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "imaginations",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "imagination_v1_field_set_frozen",
        "governing_standard": {
            "ref": str(STD_IMAGINATION),
            "schema_version": "std_imagination_v1",
            "owned_bands": ["flag", "card"],
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "skill_ref": str(IMAGINATION_AUTHORING_SKILL),
        "source_refs": [
            str(IMAGINATION_INDEX),
            str(STD_IMAGINATION),
            str(IMAGINATION_AUTHORING_SKILL),
            "codex/doctrine/imaginations/_validation_report.json",
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(rows_data),
            "validation_status": summary_in.get("validation_status"),
            "field_set_status": summary_in.get("field_set_status"),
            "imagination_count": summary_in.get("imagination_count"),
            "migrated_imagination_count": summary_in.get("migrated_imagination_count"),
            "original_imagination_count": summary_in.get("original_imagination_count"),
            "status_counts": summary_in.get("status_counts") or {},
            "selection_method": "artifact_kind_enumeration",
            "drilldown_by": "imagination_id_or_slug",
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "field_set_frozen_at_v1": True,
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface imaginations --band flag",
                "reason": "Browse all imaginations with status, migration markers, and drill routes.",
            },
            {
                "command": "./repo-python kernel.py --option-surface imaginations --band card --ids <imagination_id>",
                "reason": "Bounded card: scene excerpt, deliverable shape, migration lineage, retirement trigger.",
            },
            {
                "command": "./repo-python kernel.py --imagination <slug|id>",
                "reason": "Convenience alias for the card band; resolves by id or slug.",
            },
            {
                "command": "./repo-python kernel.py --imagination-find <query>",
                "reason": "Search across imagination index fields with a ranked match list.",
            },
        ],
        "warnings": [],
    }


def build_standards_option_surface(
    repo_root: Path,
    *,
    band: str,
    ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    if band not in {"cluster_flag", "flag", "card"}:
        return _profile_gap_payload(
            repo_root=repo_root,
            artifact_kind="standards",
            band=band,
            ids=ids,
            generated_at=generated_at,
        )

    standards, standards_by_id = _standard_index(repo_root)
    if ids:
        rows_source = [standards_by_id[item] for item in ids if item in standards_by_id]
        missing_ids = [item for item in ids if item not in standards_by_id]
    else:
        rows_source = standards
        missing_ids = []

    if band == "cluster_flag":
        rows = _standard_cluster_rows(rows_source, repo_root=repo_root)
    elif band == "card":
        rows = [_standard_card_row(row, repo_root=repo_root) for row in rows_source]
    else:
        rows = [_standard_flag_row(row, repo_root=repo_root) for row in rows_source]

    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at,
        "artifact_kind": "standards",
        "band": band,
        "selection": {
            "mode": "ids" if ids else "all",
            "ids": ids,
            "missing_ids": missing_ids,
        },
        "profile_status": "supported",
        "authority_posture": "standard_owned_projection_not_source_authority",
        "governing_standard": {
            "ref": str(STANDARDS_REGISTRY_STANDARD),
            "owned_bands": ["cluster_flag", "flag", "card"],
        },
        "theory_ref": f"{NAVIGATION_THEORY}::Refinement: Option Surface, Not Trigger Zoo",
        "skill_ref": str(PROFILE_SKILL),
        "source_refs": [
            str(STANDARDS_REGISTRY),
            str(STANDARDS_REGISTRY_STANDARD),
            str(CORE_AUTHORITY_INDEX),
            str(PROFILE_SKILL),
        ],
        "summary": {
            "row_count": len(rows),
            "total_available": len(standards),
            "query_used": False,
            "selection_method": (
                "artifact_kind_cluster_overview_grouped_by_standard_group"
                if band == "cluster_flag"
                else "artifact_kind_enumeration"
            ),
            "drilldown_by": "group" if band == "cluster_flag" else "stable_ids",
            "grouping_keys": ["group"] if band == "cluster_flag" else [],
        },
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "standard_owned_band_rules": True,
            "standards_are_themselves_browse_rows": True,
            "adapter_supported_bands": ["cluster_flag", "flag", "card"],
            "cluster_first_for_high_cardinality": band == "cluster_flag",
            "cluster_row_shape": "compact_standard_group_counts_with_top_ids"
            if band == "cluster_flag"
            else "standard_rows",
        },
        "rows": rows,
        "next": [
            {
                "command": "./repo-python kernel.py --option-surface standards --band cluster_flag",
                "reason": "Browse standards groups before expanding row-level flags.",
            },
            {
                "command": "./repo-python kernel.py --option-surface standards --band flag --ids <standard_id>[,<standard_id>...]",
                "reason": "Browse explicit standard rows at the cheapest band.",
            },
            {
                "command": "./repo-python kernel.py --option-surface standards --band card --ids <standard_id>",
                "reason": "Drill one standard, including compressed laws and shard menus when present.",
            },
        ],
        "warnings": [],
    }
