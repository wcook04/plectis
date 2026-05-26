"""
Budgeted navigation context-pack composer.

This is the production-facing control layer above kind-atlas, option-surface,
semantic routing, and command-card landmine knowledge. It selects before
rendering: high-cardinality kinds get cluster-level overview rows, likely
relevant rows get card-level drilldowns, and source bodies stay behind explicit
commands.
"""
from __future__ import annotations

import importlib.util
import json
import multiprocessing as mp
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

from system.lib.kind_atlas import build_kind_atlas
from system.lib.agent_operating_packet import load_agent_operating_packet_strip
from system.lib.candidate_runtime_pressure_policy import filter_first_contact_candidate_pressure
from system.lib.compliance.diagnostics_projection import project_compliance_diagnostics
from system.lib.capture_reflex_diagnostics import project_capture_reflex_diagnostics
from system.lib.entrypoint_health import project_entry_surface_diagnostics
from system.lib.paper_module_freshness_diagnostics import project_paper_module_freshness_diagnostics
from system.lib.standard_option_surface import (
    build_option_surface,
    candidate_runtime_pressure_rows,
    no_edit_pass_floor_card,
    _standard_validation_rule_texts,
)
from system.lib.navigation_index_spine import build_navigation_index_spine
from system.lib.python_target_resolution import (
    python_target_candidates,
    python_target_candidates_from_resolution,
    resolve_python_targets,
)
from system.lib.workitem_target_resolution import (
    resolve_workitem_targets,
    workitem_target_candidates,
    workitem_target_candidates_from_resolution,
)
from system.lib.root_navigator_ai import is_root_navigator_ai_native_query
from system.lib import work_ledger_runtime
from system.lib.work_ledger_commands import (
    WORK_LEDGER_CLAIM_CARDS_COMMAND,
    WORK_LEDGER_FULL_CLAIMS_COMMAND,
    WORK_LEDGER_SEED_SPEED_COMMAND,
)


SEMANTIC_SOURCE_KINDS = [
    "paper_modules",
    "skills",
    "standards_json",
    "annex_notes",
    "raw_seed_shards",
]
HIGH_CARDINALITY_THRESHOLD = 80
DEFAULT_SELECTED_LIMIT = 14
DEFAULT_SEMANTIC_TIMEOUT_MS = 1500
ROUTINE_CONTEXT_PACK_BUDGET_MS = 3000
ROUTINE_SEMANTIC_BUDGET_MS = 500
BUDGET_METADATA_HEADROOM_TOKENS = 64
ROUTINE_CONTEXT_PACK_SOFT_CEILING_TOKENS = 9000
ROUTINE_CONTEXT_PACK_SOFT_CEILING_BYTES = 32_000
ROUTINE_CONTEXT_PACK_SELECTED_ROWS_SOFT_CEILING_BYTES = 12_000
ROUTINE_LARGE_BUDGET_RESERVE_TOKENS = 600
COGNITIVE_OPERATOR_SELECTED_ID = "cogop_capability_gap_ladder"
COGNITIVE_OPERATOR_DISCONFIRMATION_ID = "cogop_disconfirmation_harness"
COGNITIVE_OPERATOR_CAUSAL_TRIAL_ID = "cogop_causal_trial_harness"
COGNITIVE_OPERATOR_COMPOSITION_ID = "cogop_operator_composition_sequencer"
COGNITIVE_OPERATOR_AFFORDANCE_PASSPORT_ID = "cogop_affordance_passport_author"
COGNITIVE_OPERATOR_PASSPORT_PROPAGATOR_ID = "cogop_operator_passport_propagator"
COGNITIVE_OPERATOR_ROUTE_LEASE_EXECUTOR_ID = "cogop_route_lease_executor"
COGNITIVE_OPERATOR_PROMPT_ROUTE_ASSIMILATOR_ID = "cogop_prompt_route_assimilator"
COGNITIVE_OPERATOR_PRESSURE_REDUCER_ID = "cogop_pressure_to_action_reducer"
COGNITIVE_OPERATOR_ACCRETION_GOVERNOR_ID = "cogop_operator_accretion_governor"
COGNITIVE_OPERATOR_ATTENTION_FRAME_REHYDRATOR_ID = "cogop_attention_frame_rehydrator"
COGNITIVE_OPERATOR_LANDING_HANDOFF_COMPILER_ID = "cogop_landing_handoff_compiler"
WORKITEM_SPINE_SELECTED_ID = "task_work_ledger_spine_v1"
GENERATED_PROJECTION_OWNER_SELECTED_ID = "generated_projection_ownership_v1"
TYPE_A_AUTONOMOUS_SEED_SELECTED_ID = "system_atlas_crystal_architecture_comprehension"
TYPE_A_AUTONOMOUS_SEED_SPEED_SELECTED_ID = "agent_session_diagnostics_timing"
EXTERNAL_BENCHMARK_CALIBRATION_SELECTED_ID = "verisoftbench_micro_10_calibration_spine_v1"
MISSION_OPERATING_PICTURE_REL = Path("state/task_ledger/views/mission_operating_picture.json")
WORK_LEDGER_RUNTIME_STATUS_REL = Path("state/work_ledger/runtime_status.json")
COGNITIVE_OPERATOR_CONTEXT_TRIGGERS = (
    "missing cognitive operator",
    "cognitive operator",
    "thinking substrate",
    "changes cognition",
    "structurally incapable",
    "highest compounding value",
)
COGNITIVE_OPERATOR_DISCONFIRMATION_TRIGGERS = (
    "disconfirmation harness",
    "disconfirming evidence",
    "counterevidence",
    "counter evidence",
    "counterexample",
    "falsifier",
    "negative evidence",
    "route disagreement",
    "entry context-pack disagreement",
    "entry context pack disagreement",
    "contradictory evidence",
)
COGNITIVE_OPERATOR_CAUSAL_TRIAL_TRIGGERS = (
    "causal trial harness",
    "pre/post prediction",
    "pre post prediction",
    "pre-action prediction",
    "pre action prediction",
    "post-action observation",
    "post action observation",
    "causal evidence",
    "prove cognition changed",
    "dogfood proof",
    "prediction result",
)
COGNITIVE_OPERATOR_COMPOSITION_TRIGGERS = (
    "operator composition",
    "operator sequence",
    "operator chain",
    "operator stack",
    "compose cognitive operators",
    "multiple cognitive operators",
    "operator ordering",
    "operator pipeline",
    "composition sequencer",
    "sequenced operators",
)
COGNITIVE_OPERATOR_AFFORDANCE_PASSPORT_TRIGGERS = (
    "affordance passport",
    "compression passport",
    "operator affordance",
    "row-owned triggers",
    "row owned triggers",
    "passport author",
    "operator passport",
    "when to open",
    "when not to open",
    "anti trigger",
    "anti-trigger",
    "landmine",
    "task fit passport",
)
COGNITIVE_OPERATOR_PASSPORT_PROPAGATOR_TRIGGERS = (
    "passport propagation",
    "operator passport propagation",
    "passport backfill",
    "backfill passport",
    "missing compression passports",
    "passport coverage",
    "trigger-only operator",
    "trigger only operator",
    "unpassportized operator",
    "operator passport propagator",
)
COGNITIVE_OPERATOR_ROUTE_LEASE_TRIGGERS = (
    "route lease",
    "route lease executor",
    "consume route lease",
    "route lease consumption",
    "direct action after entry",
    "second kernel call before direct action",
    "broad route repeated",
    "broad route repeated without new authority question",
    "mode control signal",
    "stop navigating and act",
)
COGNITIVE_OPERATOR_PROMPT_ROUTE_TRIGGERS = (
    "prompt route assimilator",
    "prompt route assimilation",
    "prompt-derived route miss",
    "prompt derived route miss",
    "prompt phrase route",
    "seed prompt phrase",
    "autonomous seed for routing",
    "autonomous routing seed",
    "typed semantic relation graph",
    "authority planes",
    "authority plane",
    "route proof obligation",
    "proof obligation",
    "unresolved targets",
    "duplicate routes",
    "dead surfaces",
    "private phrase lists",
    "wrong-plane handoffs",
    "wrong plane handoffs",
    "wake prompts",
    "route misses",
    "docs-route miss",
    "docs route miss",
    "unresolved route phrase",
    "trace continuation",
)
COGNITIVE_OPERATOR_PRESSURE_REDUCTION_TRIGGERS = (
    "pressure to action",
    "pressure-to-action",
    "backlog pressure",
    "queue pressure",
    "reduce pressure",
    "status binding",
    "status-bound action",
    "bounded action",
    "one bounded action",
    "task ledger pressure",
    "row patch pressure",
    "row patches",
    "transform job receipts",
    "receipt pressure",
    "ledger pressure",
    "which backlog",
    "what should i do next",
)
COGNITIVE_OPERATOR_ACCRETION_TRIGGERS = (
    "operator accretion",
    "operator accretion governor",
    "operator novelty",
    "novelty gate",
    "new operator gate",
    "add another cognitive operator",
    "another cognitive operator",
    "install another operator",
    "installing more",
    "installing new cognitive operators",
    "new cognitive operators",
    "merge reuse existing operator",
    "merge or reuse existing operator",
    "merge existing operator",
    "operator sprawl",
    "operator proliferation",
    "should this be a new operator",
    "operator stack saturation",
    "repeated autonomous seed",
)
COGNITIVE_OPERATOR_ATTENTION_FRAME_TRIGGERS = (
    "attention frame",
    "attentionframe",
    "attention-state",
    "attention state",
    "working attention",
    "working attention frame",
    "task-local attention",
    "task local attention",
    "reread same files",
    "re-read same files",
    "reread cluster",
    "rediscovery cost",
    "stale read",
    "stale write",
    "file modified since read",
    "file has not been read",
    "selected handles",
    "focused handles",
    "mutation boundary",
    "resume from frame ids",
    "rehydrate attention",
    "rehydrate working context",
)
COGNITIVE_OPERATOR_LANDING_HANDOFF_TRIGGERS = (
    "landing handoff",
    "landing continuity",
    "validated slice",
    "validated work",
    "validated but uncommitted",
    "uncommitted validated",
    "uncommitted slice",
    "commit blocked",
    "scoped commit blocked",
    "git metadata",
    ".git metadata",
    "metadata write denied",
    "protected git metadata",
    "commit authority",
    "owned path set",
    "exact owned paths",
    "landing blocker",
    "handoff packet",
    "reentry rule",
    "commit finalizer",
    "scoped landing",
    "landed validation evidence",
)
WORKITEM_SPINE_QUERY_PHRASES = (
    "workitem spine",
    "work item spine",
    "task ledger work ledger",
    "task ledger and work ledger",
    "task ledger / work ledger",
    "task ledger, work ledger",
    "work ledger task ledger",
    "caps operational seeds",
    "cap operational seeds",
    "operational seeds workitem",
    "operational seeds work item",
    "session claims workitem",
    "session claims work item",
)
WORKITEM_SPINE_REQUIRED_TERM_GROUPS = (
    {"task", "ledger"},
    {"work", "ledger"},
    {"workitem", "workitems", "work-item", "work-items"},
    {"cap", "caps"},
)
GENERATED_PROJECTION_OWNER_QUERY_PHRASES = (
    "generated projection ownership",
    "generated projection owner",
    "generated projections ownership",
    "generated projection registry",
    "generated state drainer",
    "generated-state drainer",
    "source coupling",
    "dirty source inputs",
    "manual edit boundary",
    "manual-edit boundary",
    "projection authority boundary",
    "projection authority inversion",
    "source vs generated",
    "source/generated boundary",
)
GENERATED_PROJECTION_OWNER_REQUIRED_TERM_GROUPS = (
    {"generated", "readmodel", "read-model", "sidecar", "sidecars"},
    {"owner", "owners", "ownership", "registry", "tool", "tools"},
    {"source", "authority", "coupling", "dirty", "freshness", "currentness"},
)
TYPE_A_AUTONOMOUS_SEED_QUERY_PHRASES = (
    "autonomous seed",
    "autonomous seeds",
    "type a autonomous seed",
    "type a autonomous seeds",
    "type a seed loop",
    "autonomous seed prompt",
    "autonomous seed prompts",
    "wake prompt",
    "wake prompts",
    "seed prompt",
    "seed prompts",
    "repeated prompt cluster",
    "repeated prompt clusters",
    "replay receipt",
    "replay receipts",
    "seed replay",
    "seed replay receipt",
    "continuation receipt",
    "continuation receipts",
    "seed continuation",
    "seed continuity",
    "seed rehydration",
    "live seed rehydration",
    "replay dogfood",
    "dogfood hardening",
    "seed corpus",
    "seed cohort",
    "raw seed autonomous seed",
    "raw-seed autonomous seed",
    "autonomous seed loop",
    "autonomous seed bundle",
    "saved autonomous seed",
    "do that seed",
    "run that seed",
    "execute that seed",
    "run the seed",
    "execute the seed",
    "actually execute the seed",
    "start knocking caps off",
    "knock caps off",
    "system atlas crystal architecture comprehension",
)
TYPE_A_AUTONOMOUS_SEED_MATCH_STOP_TERMS = {
    "a",
    "about",
    "agent",
    "agents",
    "and",
    "atlas",
    "autonomous",
    "binding",
    "bindings",
    "body",
    "bundle",
    "bundles",
    "card",
    "continuation",
    "continuity",
    "current",
    "doctrine",
    "dogfood",
    "floor",
    "framework",
    "gap",
    "hardening",
    "into",
    "live",
    "loop",
    "loops",
    "owner",
    "pattern",
    "patterns",
    "prompt",
    "prompts",
    "receipt",
    "receipts",
    "rehydration",
    "replay",
    "rewrite",
    "routability",
    "route",
    "seed",
    "seeds",
    "selected",
    "strongest",
    "the",
    "trace",
    "capsule",
    "type",
    "wake",
}
SPEED_REFINEMENT_QUERY_PHRASES = (
    "speed refinement",
    "speed refinements",
    "command telemetry",
    "command timing",
    "command timings",
    "command latency",
    "meta diagnostic",
    "meta diagnostics",
    "process bottleneck",
    "process bottlenecks",
    "latency seed",
    "latency speedboard",
    "wait tax",
    "command profile",
    "command startup",
    "startup profile",
    "slow command",
    "slow commands",
    "command surface inventory",
)
EXTERNAL_BENCHMARK_CALIBRATION_QUERY_PHRASES = (
    "external benchmark calibration",
    "external benchmark calibration spine",
    "verisoftbench",
    "verisoftbench micro",
    "verisoftbench micro-10",
    "verisoftbench micro 10",
    "c-arm provider repair",
    "c arm provider repair",
    "formal math proof repair",
    "formal-math proof repair",
    "formal math benchmark",
    "nvidia nim proof repair",
    "nim provider proof repair",
    "provider proof repair",
)
OVERVIEW_TRIM_PROTECTED_KIND_IDS = {
    "annex_distillation_patterns",
    "annex_patterns",
    "artifact_projection_debt",
    "cognitive_operators",
    "derived_facts",
    "frontend_components",
    "paper_modules",
    "principles",
    "python_files",
    "python_scopes",
    "row_patches",
    "skill_compression_debt",
    "skills",
    "standard_skill_map",
    "standards",
    "task_ledger",
}
CLUSTER_FIRST_KIND_IDS = {
    "artifact_projection_debt",
    "derived_facts",
    "standard_skill_map",
}
NEXT_COMMAND_TRIM_PROTECTED_SUBSTRINGS = (
    "--option-surface cognitive_operators --band flag",
    "--option-surface cognitive_operators --band card",
    "--option-surface concepts --band card",
    "--option-surface standards --band card",
    "--option-surface mechanisms --band card",
    "validate_cognitive_operator_registry.py --json",
    "--paper-module system_self_comprehension_root",
    "check_dissemination_atlas_gate.py --check",
    "prompt_shelf_runs_index.py --check",
    "prompt_shelf_runs_index.py --summary",
    "prompt_shelf_runs_index.py --coverage",
    '--docs-route "system crystal"',
    "--option-surface task_ledger --band cluster_flag",
    "task_ledger_apply.py validate",
    "work_ledger.py session-status --seed-speed",
    "work_ledger.py session-claims",
    "generated_state_drainer.py",
    "generated_projection_registry.py",
    "mission_transaction_preflight.py",
    "build_system_atlas.py --check",
    "build_root_coverage_state.py --check",
    "--option-surface system_atlas --band cluster_flag",
    "--option-surface system_atlas --band unknowns",
    "--option-surface system_atlas --band card --ids dom_system_atlas",
    "--option-surface external_benchmark_calibration --band card",
    "build_external_benchmark_calibration_spine.py --check",
    "run_verisoftbench_micro10_c_arm_provider_repair.py --check",
    "build_system_crystal.py --check",
    "latency_seed_preflight",
    "process_bottleneck_triage",
    "command_surface_inventory",
    "--latency-seed-digest",
    "--process-bottlenecks",
    "--command-profile latency-speedboard",
    "--option-surface type_a_autonomous_seeds --band card",
    "--raw-seed-autonomous-seed-bundle",
)
SOURCE_SURFACE_TRIM_PROTECTED_SUBSTRINGS = (
    "tools/meta/factory/check_dissemination_atlas_gate.py",
    "tools/meta/factory/build_system_crystal.py",
    "tools/meta/observability/operator_thread_memory.py",
    "tools/meta/observability/prompt_shelf_runs_index.py",
    "system/lib/generated_projection_registry.py",
    "tools/meta/control/generated_state_drainer.py",
    "tools/meta/factory/build_external_benchmark_calibration_spine.py",
)
BUDGET_TRIM_PROTECTED_ROWS = {
    ("cognitive_operators", COGNITIVE_OPERATOR_SELECTED_ID),
    ("cognitive_operators", COGNITIVE_OPERATOR_DISCONFIRMATION_ID),
    ("cognitive_operators", COGNITIVE_OPERATOR_CAUSAL_TRIAL_ID),
    ("cognitive_operators", COGNITIVE_OPERATOR_COMPOSITION_ID),
    ("cognitive_operators", COGNITIVE_OPERATOR_AFFORDANCE_PASSPORT_ID),
    ("cognitive_operators", COGNITIVE_OPERATOR_PASSPORT_PROPAGATOR_ID),
    ("cognitive_operators", COGNITIVE_OPERATOR_ROUTE_LEASE_EXECUTOR_ID),
    ("cognitive_operators", COGNITIVE_OPERATOR_PROMPT_ROUTE_ASSIMILATOR_ID),
    ("cognitive_operators", COGNITIVE_OPERATOR_PRESSURE_REDUCER_ID),
    ("cognitive_operators", COGNITIVE_OPERATOR_ACCRETION_GOVERNOR_ID),
    ("cognitive_operators", COGNITIVE_OPERATOR_LANDING_HANDOFF_COMPILER_ID),
    ("skills", "type_a_autonomous_seed_loop"),
    ("skills", "autonomous_seed_prompt_author"),
    ("skills", "local_to_general_propagation"),
    ("paper_modules", "local_to_general_propagation"),
    ("mechanisms", "mech_034"),
    ("mechanisms", "mechanism:mech_034::card"),
    ("frontend_views", "rootNavigator"),
    ("paper_modules", "autonomous_seed_anatomy"),
    ("concepts", "con_039"),
    ("concepts", "concept:con_039::card"),
    ("mechanisms", "mech_035"),
    ("mechanisms", "mechanism:mech_035::card"),
    ("type_a_autonomous_seeds", TYPE_A_AUTONOMOUS_SEED_SELECTED_ID),
    ("type_a_autonomous_seeds", TYPE_A_AUTONOMOUS_SEED_SPEED_SELECTED_ID),
    ("paper_modules", "frontend_page_meta_contract"),
    ("dissemination_gate", "public_safe_atlas_gate_v1"),
    ("prompt_shelf_metadata", "prompt_shelf_runs_index_v1"),
    ("system_crystal", "private_system_crystal_v1"),
    ("operator_thread_continuation_card", "thread_id_required"),
    ("workitem_spine", WORKITEM_SPINE_SELECTED_ID),
    ("generated_projection_ownership", GENERATED_PROJECTION_OWNER_SELECTED_ID),
    ("external_benchmark_calibration", EXTERNAL_BENCHMARK_CALIBRATION_SELECTED_ID),
    ("paper_modules", "system_self_comprehension_root"),
    ("standards", "std_autonomous_seed_prompt"),
    ("standards", "std_uppropagation_intake"),
    ("standards", "std_doctrine_section_unit"),
    ("standards", "std_teleology_node"),
    ("paper_modules", "federated_config_plane"),
    ("standards", "std_config_authority_registry"),
    ("config_authorities", "master_config.bridge"),
    ("config_authorities", "frontend.configs_board.config_ref"),
    ("config_authorities", "api.config.system"),
}
DISSEMINATION_ENTRY_SKILL_IDS = {
    "dissemination_cycle",
    "dissemination_research_assimilation",
    "dissemination_research_prompting",
    "dissemination_understanding",
}
ROW_FLAG_COMPATIBILITY_SHIM_KINDS = {
    "annex_distillation_patterns",
    "annex_patterns",
    "frontend_components",
    "paper_modules",
    "principles",
    "python_files",
    "python_scopes",
    "standards",
}
FACT_NAVIGATION_CACHE = Path("codex/hologram/facts/navigation_cache.json")
FACT_LEDGER = Path("codex/hologram/facts/ledger.json")
FACT_AUDIT = Path("codex/hologram/facts/audit.json")
FACT_STANDARD = Path("codex/standards/std_derived_fact.json")
FACT_REGISTRY = Path("codex/doctrine/facts/fact_registry.json")
QUERY_CONTROL_PLANE_TERMS = {
    "agent",
    "band",
    "budgeted",
    "claude",
    "cli",
    "codex",
    "command",
    "commands",
    "compressed",
    "compression",
    "context",
    "diagnostic",
    "diagnostics",
    "doctrine",
    "edge",
    "edges",
    "flag",
    "instruction",
    "instructions",
    "navigation",
    "output",
    "pack",
    "paper",
    "route",
    "routes",
    "routing",
    "startup",
    "surface",
    "token",
    "traces",
    "workers",
}
SYSTEM_ATLAS_QUERY_TERMS = {
    "atlas",
    "capability",
    "capabilities",
    "comprehension",
    "coverage",
    "dissemination",
    "drill",
    "drilldown",
    "exists",
    "feed",
    "feeds",
    "frontend",
    "leaf",
    "provider",
    "providers",
    "public",
    "stale",
    "system",
    "unknown",
    "unknowns",
}
SYSTEM_ATLAS_QUERY_PHRASES = (
    "artifact kind index",
    "index spine",
    "navigation index",
    "what exists",
    "where to drill",
    "where do i drill",
    "public leaf",
    "self comprehension",
    "system self-comprehension",
    "whole system",
    "unified index",
)
PUBLIC_SAFE_DISSEMINATION_GATE_QUERY_PHRASES = (
    "atlas refs",
    "atlas ref",
    "atlas gate",
    "dissemination gate",
    "dissemination atlas",
    "public safe",
    "public-safe",
    "public leaf",
    "leaf readiness",
    "safe leaf",
    "disclosure projection",
    "recipient packet",
    "send ready",
    "send-ready",
)
PROMPT_SHELF_METADATA_QUERY_PHRASES = (
    "prompt shelf",
    "prompt-shelf",
    "prompt ledger",
    "prompt run",
    "prompt runs",
    "prompt shelf runs",
    "type b reasoning extraction",
    "type-b reasoning extraction",
    "type b self-description lessons",
    "type-b self-description lessons",
    "metadata-only prompt",
    "metadata only prompt",
    "raw event sidecars",
)
DIRTY_TREE_BANKRUPTCY_QUERY_PHRASES = (
    "dirty tree",
    "dirty-tree",
    "commit bankruptcy",
    "bankruptcy prevention",
    "auto commit",
    "auto-commit",
    "uncommitted work",
    "uncommitted dirty",
    "lease expired",
    "lease-expired",
    "stale agent work",
    "stale sessions",
    "orphaned sessions",
    "private backup",
    "private-backup",
    "session finalizer",
    "dirty-tree finalizer",
)
DIRTY_TREE_BANKRUPTCY_AUTHORIZATION_QUERY_PHRASES = (
    "bankruptcy authorized",
    "operator authorized",
    "operator-authorized",
    "dirty tree bankruptcy lane",
    "dirty-tree bankruptcy lane",
    "dirty tree bankruptcy recovery",
    "dirty-tree bankruptcy recovery",
    "bankruptcy fix",
    "fix my dirty tree",
    "broad checkpoint",
    "mainline checkpoint",
    "commit everything",
    "save everything",
    "checkpoint everything",
    "push it all",
    "land dirty tree state",
    "checkpoint --arbiter",
    "--arbiter",
    "clean branch",
    "clean the branch",
)
OPERATOR_THREAD_CONTINUATION_CARD_QUERY_PHRASES = (
    "continuation card",
    "continuation-card",
    "operator thread continuation",
    "operator continuation card",
    "operator_thread_memory",
    "turn stack",
    "turn-stack",
    "thread semantic summary",
    "response skeleton",
    "type b grounding packet",
    "type-b grounding packet",
    "type b grounding",
    "a to b shuttle",
    "a↔b shuttle",
)
OPERATOR_THREAD_ID_RE = re.compile(r"\bchatgpt_[A-Za-z0-9][A-Za-z0-9_-]{8,}\b")
OPERATOR_CARD_FORBIDDEN_MARKERS = (
    "private_preview",
    "private_title",
    "raw_turn_text",
    "raw_response_body",
    "SENTINEL_",
    '"text"',
)
SYSTEM_CRYSTAL_QUERY_PHRASES = (
    "system crystal",
    "private system crystal",
    "internal crystal",
    "ultimate distillation",
    "ultimate distillation one point",
    "densest private self-model",
    "dense private self-model",
    "cap of caps",
    "one point system",
    "whole-system crystal",
    "annex crystal",
    "annex crystal navigation spine",
    "crystal navigation spine",
    "idea crystal",
    "idea-first crystal",
    "idea graph adapter",
)
TRANSACTION_CONTROL_PLANE_QUERY_TERMS = {
    "bloat",
    "claim",
    "commit",
    "concurrency",
    "convergence",
    "drain",
    "finalizer",
    "github",
    "index",
    "intake",
    "landing",
    "ledger",
    "preflight",
    "push",
    "quarantine",
    "receipt",
    "reconcile",
    "rollup",
    "staged",
    "transaction",
    "workitem",
}
TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT = "cap_live_concurrency_transactional_workitems"


def _entry_surface_structural_triggers_from_selected_rows(
    selected_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    config_rows = [
        row
        for row in selected_rows
        if str(row.get("selection_source_kind") or "") == "config_plane_protocol_anchor"
    ]
    if config_rows:
        return [
            {
                "trigger_id": "selected_config_plane_projected_context_rows",
                "recognized_situation": "config_authority_plane",
                "selected_lane_id": "config_authority_plane",
                "selected_kind_ids": sorted({
                    str(row.get("kind_id") or "")
                    for row in config_rows
                    if str(row.get("kind_id") or "")
                }),
                "selected_row_ids": sorted({
                    str(row.get("row_id") or "")
                    for row in config_rows
                    if str(row.get("row_id") or "")
                }),
                "source": "navigation_context_pack.selected_rows",
                "reason": (
                    "Context-pack selected stable config authority rows; carry the entry "
                    "generated-region and source-coupling receipt without requiring diagnostic query tokens."
                ),
            }
        ]
    dissemination_row_ids = sorted({
        str(row.get("row_id") or "")
        for row in selected_rows
        if str(row.get("kind_id") or "") == "skills"
        and str(row.get("row_id") or "") in DISSEMINATION_ENTRY_SKILL_IDS
    })
    if not dissemination_row_ids:
        return []
    return [
        {
            "trigger_id": "selected_dissemination_projected_context_rows",
            "recognized_situation": "dissemination_agent_entry",
            "selected_lane_id": "dissemination_agent_entry",
            "selected_kind_ids": ["skills"],
            "selected_row_ids": dissemination_row_ids,
            "source": "navigation_context_pack.selected_rows",
            "reason": (
                "Context-pack selected stable dissemination skill rows; carry the entry "
                "generated-region and source-coupling receipt without requiring diagnostic query tokens."
            ),
        }
    ]


def _query_mentions_transaction_control_plane(query: str) -> bool:
    lowered = str(query or "").lower()
    return any(term in lowered for term in TRANSACTION_CONTROL_PLANE_QUERY_TERMS)


def _is_system_crystal_query(query: str) -> bool:
    lowered = str(query or "").casefold()
    terms = _query_terms(query)
    if any(phrase in lowered for phrase in SYSTEM_CRYSTAL_QUERY_PHRASES):
        return True
    if "system_crystal" in lowered or "build_system_crystal" in lowered:
        return True
    if "crystal" in terms and ("system" in terms or "whole" in terms or "private" in terms):
        return True
    if "distillation" in terms and ({"system", "self", "whole", "private"} & terms):
        return True
    if "densest" in terms and ({"system", "self", "whole"} & terms):
        return True
    return False


def _transaction_control_plane_hint() -> dict[str, Any]:
    status = "omitted_from_routine_context_pack"
    drilldown = (
        "./repo-python tools/meta/control/mission_transaction_preflight.py "
        f"--subject-id {TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT} --control-summary"
    )
    return {
        "schema": "transaction_control_plane_summary_v0",
        "consumer_surface": "kernel.context_pack",
        "status": status,
        "reason": "Routine context-pack carries a drilldown hint instead of running transaction preflight.",
        "next_action": drilldown,
        "shared_index_quarantine": {
            "schema": "shared_index_quarantine_v0",
            "status": status,
            "next_action": drilldown,
        },
        "workspace_bloat_pressure": {
            "schema": "workspace_bloat_pressure_v0",
            "status": status,
            "next_action": drilldown,
        },
        "github_push_bloat_gate": {
            "schema": "github_push_bloat_gate_v1",
            "status": status,
            "next_action": drilldown,
        },
        "drilldown_commands": [
            drilldown,
            (
                "./repo-python tools/meta/control/mission_transaction_preflight.py "
                f"--subject-id {TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT} --staged-index-quarantine"
            ),
            (
                "./repo-python tools/meta/control/mission_transaction_preflight.py "
                f"--subject-id {TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT} --workspace-bloat-pressure"
            ),
            (
                "./repo-python tools/meta/control/mission_transaction_preflight.py "
                f"--subject-id {TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT} --github-push-bloat-gate"
            ),
        ],
    }


def _transaction_control_plane_context(root: Path, query: str) -> dict[str, Any] | None:
    if not _query_mentions_transaction_control_plane(query):
        return None
    try:
        from system.lib.mission_transaction_landing_preflight import (
            build_mission_transaction_landing_preflight,
            mission_transaction_control_summary,
        )

        packet = build_mission_transaction_landing_preflight(
            root,
            target_ids=[TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT],
        )
        return mission_transaction_control_summary(packet, consumer_surface="kernel.context_pack")
    except Exception as exc:  # pragma: no cover - context-pack must degrade on sparse fixtures.
        return {
            "schema": "transaction_control_plane_summary_v0",
            "consumer_surface": "kernel.context_pack",
            "status": "watch",
            "next_action": "open_mission_transaction_preflight_drilldown",
            "unavailable_reason": type(exc).__name__,
            "drilldown_commands": [
                "./repo-python tools/meta/control/mission_transaction_preflight.py --subject-id "
                f"{TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT} --control-summary",
            ],
        }


MISSION_TRACE_LATEST_FIELDS = (
    "mission_context_status",
    "identity_kind",
    "identity_value",
    "mission_id",
    "subject_id",
    "fallback_subject",
    "trace_id",
    "event_id",
    "last_event_at",
    "last_surface",
    "last_actor_class",
    "last_step_id",
    "parent_step_id",
    "last_prompt_refs",
    "last_lane",
    "last_decision_state",
    "last_reason",
    "current_receipt_ref",
    "receipt_refs",
    "next_safe_action",
    "plan_id",
    "action_id",
)


def _compact_mission_trace_row(row: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for field in MISSION_TRACE_LATEST_FIELDS:
        value = row.get(field)
        if value in (None, "", [], {}):
            continue
        if field == "receipt_refs" and isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            compact[field] = [str(item) for item in value if item][:6]
            continue
        if field == "last_prompt_refs" and isinstance(value, Mapping):
            prompt_refs = {
                str(key): val
                for key, val in value.items()
                if val not in (None, "", [], {})
            }
            if prompt_refs:
                compact[field] = prompt_refs
            continue
        compact[field] = value
    return compact


def _mission_trace_current_state_context(root: Path) -> dict[str, Any]:
    source_view = str(MISSION_OPERATING_PICTURE_REL)
    source_field = "mission_trace_current_state"
    authority_boundary = (
        "task_ledger_overlay_from_prompt_ledger_projection_not_safety_authority"
    )
    base: dict[str, Any] = {
        "schema": "mission_trace_context_pack_card_v0",
        "status": "missing",
        "authority_boundary": authority_boundary,
        "projection_only": True,
        "safety_authority": False,
        "source_view": source_view,
        "source_field": source_field,
    }
    payload = _load_json(root / MISSION_OPERATING_PICTURE_REL)
    if not payload:
        return {
            **base,
            "next_discovery": (
                "refresh Prompt Ledger and Task Ledger projections or inspect "
                "mission_trace_context_pack_surface_gap"
            ),
        }
    rollup = payload.get(source_field)
    if not isinstance(rollup, Mapping):
        return {
            **base,
            "status": "unmatched",
            "next_discovery": (
                "refresh Prompt Ledger and Task Ledger projections or inspect "
                "mission_trace_context_pack_surface_gap"
            ),
        }

    status = str(rollup.get("status") or "unmatched")
    card: dict[str, Any] = {
        **base,
        "status": status,
        "row_count": int(rollup.get("row_count") or 0),
        "current_receipt_ref": rollup.get("current_receipt_ref"),
        "next_safe_action": rollup.get("next_safe_action"),
        "source_projection": rollup.get("source_projection"),
        "source_authority": rollup.get("source_authority"),
    }
    latest = rollup.get("latest_row")
    if isinstance(latest, Mapping):
        compact_latest = _compact_mission_trace_row(latest)
        if compact_latest:
            card["latest"] = compact_latest
    if status != "available" or not card.get("latest"):
        card["next_discovery"] = (
            "refresh Prompt Ledger and Task Ledger projections or inspect "
            "mission_trace_context_pack_surface_gap"
        )
    return {key: value for key, value in card.items() if value not in (None, "", [], {})}


def _query_mentions_dirty_tree_bankruptcy(query: str) -> bool:
    lowered = str(query or "").lower()
    return any(phrase in lowered for phrase in DIRTY_TREE_BANKRUPTCY_QUERY_PHRASES)


def _query_authorizes_dirty_tree_bankruptcy(query: str) -> bool:
    lowered = str(query or "").lower()
    return any(
        phrase in lowered
        for phrase in DIRTY_TREE_BANKRUPTCY_AUTHORIZATION_QUERY_PHRASES
    )


def _dirty_paths_from_git_status(repo_root: Path) -> tuple[list[str], str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain=v1", "-z"],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return [], f"git_status_unavailable:{type(exc).__name__}"
    if completed.returncode != 0:
        stderr = " ".join((completed.stderr or "").split())
        return [], f"git_status_failed:{stderr or completed.returncode}"
    paths: list[str] = []
    entries = completed.stdout.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:] if len(entry) > 3 else ""
        if path:
            paths.append(path)
        if status[:1] in {"R", "C"} or status[1:2] in {"R", "C"}:
            index += 1
    return paths, "git_status_porcelain_v1_z"


def _dirty_tree_bankruptcy_pressure_context(root: Path, query: str) -> dict[str, Any] | None:
    if not _query_mentions_dirty_tree_bankruptcy(query):
        return None
    bankruptcy_authorized = _query_authorizes_dirty_tree_bankruptcy(query)
    source_command = (
        "./repo-python tools/meta/factory/work_ledger.py "
        "session-sweep --dry-run --dirty-tree-pressure"
    )
    if bankruptcy_authorized:
        source_command = f"{source_command} --bankruptcy-authorized"
        dirty_paths, dirty_scan_status = _dirty_paths_from_git_status(root)
    else:
        dirty_paths = None
        dirty_scan_status = "omitted_from_context_pack"
    source_view = str(WORK_LEDGER_RUNTIME_STATUS_REL)
    try:
        status = work_ledger_runtime.load_runtime_status(root)
        card = work_ledger_runtime.build_dirty_tree_bankruptcy_pressure(
            root,
            status=status,
            dirty_paths=dirty_paths,
            dirty_scan_status=dirty_scan_status,
            bankruptcy_authorized=bankruptcy_authorized,
        )
    except Exception as exc:  # noqa: BLE001 - context-pack should orient, not fail.
        return {
            "schema": "dirty_tree_bankruptcy_pressure_context_pack_card_v0",
            "status": "unavailable",
            "authority_boundary": "orientation_overlay_not_safety_authority",
            "projection_only": True,
            "safety_authority": False,
            "source_view": source_view,
            "reason": f"{type(exc).__name__}: {exc}",
            "source_command": source_command,
            "bankruptcy_authorized": bankruptcy_authorized,
            "next_discovery": source_command,
        }
    compact = {
        "schema": "dirty_tree_bankruptcy_pressure_context_pack_card_v0",
        "status": "available",
        "authority_boundary": card.get("authority_boundary")
        or "orientation_overlay_not_safety_authority",
        "projection_only": True,
        "safety_authority": False,
        "source_view": source_view,
        "source_command": source_command,
        "bankruptcy_authorized": card.get("bankruptcy_authorized"),
        "operator_authorized_mainline_checkpoint": card.get(
            "operator_authorized_mainline_checkpoint"
        ),
        "dirty_scan_status": card.get("dirty_scan_status"),
        "dirty_total": card.get("dirty_total"),
        "dirty_path_rows": card.get("dirty_path_rows"),
        "work_ledger_counts": card.get("work_ledger_counts"),
        "expired_sessions_needing_finalizer": card.get("expired_sessions_needing_finalizer"),
        "expired_claims_needing_sweep": card.get("expired_claims_needing_sweep"),
        "dirty_path_class_counts": card.get("dirty_path_class_counts"),
        "class_counts": card.get("class_counts") or card.get("dirty_path_class_counts"),
        "active_claim_session_groups": card.get("active_claim_session_groups"),
        "scoped_work_unblock": card.get("scoped_work_unblock"),
        "containment_plan": card.get("containment_plan"),
        "last_finalizer_receipt_ref": card.get("last_finalizer_receipt_ref"),
        "rescue_refs": card.get("rescue_refs"),
        "rescue_coverage": card.get("rescue_coverage"),
        "rescue_repeat_policy": card.get("rescue_repeat_policy"),
        "repeat_policy": card.get("repeat_policy") or card.get("rescue_repeat_policy"),
        "mainline_commit_candidates": card.get("mainline_commit_candidates"),
        "blocked_residuals": card.get("blocked_residuals"),
        "next_safe_action": card.get("next_safe_action"),
        "commands": card.get("commands"),
        "policy": card.get("policy"),
    }
    keep_empty_fields = {"mainline_commit_candidates"}
    return {
        key: value
        for key, value in compact.items()
        if key in keep_empty_fields or value not in (None, "", [], {})
    }


CONFIG_PLANE_QUERY_TERMS = {
    "config",
    "configuration",
    "configurable",
    "configurables",
    "settings",
    "master_config",
    "master",
    "authority",
    "registry",
    "effective",
    "resolver",
    "config_ref",
    "mutability",
    "redaction",
    "knob",
    "knobs",
}
CONFIG_PLANE_QUERY_PHRASES = (
    "master config",
    "master_config",
    "config authority",
    "config authority registry",
    "config plane",
    "config surface",
    "effective config",
    "settings config",
    "config_ref",
    "safe edit",
)
STATE_AXIS_QUERY_PHRASES = (
    "state axes",
    "state axis",
    "states can things be in",
    "compressed state universe",
    "state universe",
    "state facts",
    "fact state plane",
    "fact state",
    "state rows",
)
CONTROL_PLANE_ANCHORS: tuple[tuple[str, str, float, str], ...] = (
    (
        "paper_modules",
        "navigation_rosetta_math",
        0.98,
        "Defines the budgeted context-atom / knapsack grammar this composer is instantiating.",
    ),
    (
        "paper_modules",
        "holographic_navigation_compression",
        0.95,
        "Owns the Russian-doll compression theory for navigation surfaces.",
    ),
    (
        "paper_modules",
        "navigation_hologram_theory",
        0.94,
        "Root navigation theory and option-surface boundary.",
    ),
    (
        "paper_modules",
        "unified_navigation_layer",
        0.9,
        "Whole-plane navigation composition surface.",
    ),
    (
        "skills",
        "navigation_metabolism",
        0.93,
        "Unified ratchet for navigation, context bloat, route behavior, entrypoint health, and surface-debt prioritization.",
    ),
    (
        "skills",
        "profile_governed_compression",
        0.91,
        "Governs band contracts, omission receipts, and profile-first compression.",
    ),
    (
        "skills",
        "navigation_seed",
        0.89,
        "Cold-start ladder that this command should replace for task-conditioned packing.",
    ),
    (
        "skills",
        "agent_session_diagnostics",
        0.86,
        "Turns recent Claude/Codex session traces and route failures into navigation repair signals.",
    ),
    (
        "skills",
        "context_window_exhaustion_protocol",
        0.82,
        "Context-window pressure protocol related to budget enforcement and resumability.",
    ),
)
PAPER_LATTICE_SUPPORTED_SLUGS = {"navigation_hologram_theory"}
CONTEXT_ANCHOR_STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "how",
    "into",
    "not",
    "the",
    "this",
    "through",
    "what",
    "when",
    "where",
    "with",
}
PYTHON_EXPLICIT_TARGET_HINT_RE = re.compile(
    r"(?:(?:[A-Za-z0-9_.-]+/)+)?[A-Za-z0-9_.-]+\.py(?:::[A-Za-z_][A-Za-z0-9_.]*)?"
    r"|\b(?:python\s+)?(?:file|function|method|class|scope|symbol)\s+[A-Za-z_][A-Za-z0-9_]*\b",
    flags=re.IGNORECASE,
)


def _semantic_query_worker(
    queue: "mp.Queue[dict[str, Any]]",
    repo_root: str,
    query: str,
    top_k: int,
) -> None:
    try:
        from system.lib.semantic_routing import query_routes

        routed = query_routes(
            Path(repo_root),
            query=query,
            source_kinds=SEMANTIC_SOURCE_KINDS,
            top_k=top_k,
            check_live_staleness=False,
        )
        queue.put({"ok": True, "payload": routed})
    except Exception as exc:  # noqa: BLE001 - caller converts this to semantic_status
        queue.put({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(payload: Mapping[str, Any]) -> int:
    # Kernel CLI emits context packs as pretty JSON. Budget against that
    # rendered shape so estimated_tokens and final byte checks agree.
    return len(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))


def _estimate_tokens(payload: Mapping[str, Any]) -> int:
    return max(1, (_json_bytes(payload) + 3) // 4)


def _trim(text: Any, *, max_chars: int = 300) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max(0, max_chars - 1)].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _query_terms(query: str) -> set[str]:
    return {part.strip(".,:;!?()[]{}\"'`").lower() for part in str(query or "").split() if part.strip()}


def _is_control_plane_query(query: str) -> bool:
    return bool(_query_terms(query) & QUERY_CONTROL_PLANE_TERMS)


def _is_state_axis_query(query: str) -> bool:
    lower_query = str(query or "").lower().replace("-", " ")
    terms = _query_terms(lower_query)
    if any(phrase in lower_query for phrase in STATE_AXIS_QUERY_PHRASES):
        return True
    return bool({"state", "states"} & terms and {"axis", "axes", "facts", "universe", "rows"} & terms)


def _is_system_atlas_query(query: str) -> bool:
    if _is_state_axis_query(query):
        return False
    lower_query = str(query or "").lower()
    terms = _query_terms(query)
    return bool(terms & SYSTEM_ATLAS_QUERY_TERMS) or any(
        phrase in lower_query for phrase in SYSTEM_ATLAS_QUERY_PHRASES
    )


def _is_public_safe_dissemination_gate_query(query: str) -> bool:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _query_terms(lower_query)
    if any(phrase.replace("-", " ") in lower_query for phrase in PUBLIC_SAFE_DISSEMINATION_GATE_QUERY_PHRASES):
        return True
    return bool(
        {"atlas", "capability", "disclosure", "dissemination", "gate", "leaf", "public", "recipient", "send"}
        & terms
        and {"refs", "ref", "readiness", "safe", "gate", "release", "artifact"} & terms
    )


def _is_prompt_shelf_metadata_query(query: str) -> bool:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _query_terms(lower_query)
    if any(phrase.replace("-", " ") in lower_query for phrase in PROMPT_SHELF_METADATA_QUERY_PHRASES):
        return True
    has_prompt_shelf = {"prompt", "prompts"} & terms and {"shelf", "ledger", "run", "runs"} & terms
    has_type_b_extraction = (
        ({"type", "typeb", "b"} & terms)
        and {"reasoning", "lesson", "lessons", "extraction", "extract"} & terms
        and {"metadata", "self", "description", "descriptive"} & terms
    )
    return bool(has_prompt_shelf or has_type_b_extraction)


def _operator_thread_id_from_query(query: str) -> str | None:
    match = OPERATOR_THREAD_ID_RE.search(str(query or ""))
    return match.group(0) if match else None


def _is_operator_thread_continuation_card_query(query: str) -> bool:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _query_terms(lower_query)
    if _operator_thread_id_from_query(query):
        return True
    if any(phrase.replace("-", " ") in lower_query for phrase in OPERATOR_THREAD_CONTINUATION_CARD_QUERY_PHRASES):
        return True
    has_operator_thread = {"operator"} & terms and {"thread", "threads"} & terms
    has_card_or_grounding = {"continuation", "card", "grounding", "shuttle", "stack", "skeleton"} & terms
    return bool(has_operator_thread and has_card_or_grounding)


def _is_type_a_autonomous_seed_query(query: str) -> bool:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _query_terms(lower_query)
    if any(phrase.replace("-", " ") in lower_query for phrase in TYPE_A_AUTONOMOUS_SEED_QUERY_PHRASES):
        return True
    has_type_a_seed = bool({"type", "typea", "a"} & terms and {"autonomous"} & terms and {"seed", "seeds"} & terms)
    has_raw_seed_autonomy = bool({"raw", "rawseed"} & terms and {"autonomous"} & terms and {"seed", "seeds"} & terms)
    has_seed_loop_owner = bool(
        {"autonomous"} & terms
        and {"seed", "seeds"} & terms
        and {
            "bundle",
            "bundles",
            "loop",
            "metadata",
            "owner",
            "card",
            "route",
            "receipt",
            "receipts",
            "replay",
            "continuation",
            "continuity",
            "rehydration",
            "dogfood",
            "hardening",
        } & terms
    )
    return has_type_a_seed or has_raw_seed_autonomy or has_seed_loop_owner


def _autonomous_seed_match_text(value: Any) -> str:
    text = str(value or "").casefold().replace("_", " ").replace("-", " ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def _autonomous_seed_match_terms(value: Any) -> set[str]:
    return {
        term
        for term in _autonomous_seed_match_text(value).split()
        if len(term) > 1 and term not in TYPE_A_AUTONOMOUS_SEED_MATCH_STOP_TERMS
    }


def _type_a_autonomous_seed_matches_for_query(
    repo_root: Path,
    query: str,
) -> list[dict[str, Any]]:
    query_text = _autonomous_seed_match_text(query)
    query_terms = _autonomous_seed_match_terms(query)
    if not query_text or not query_terms:
        return []
    try:
        surface = build_option_surface(repo_root, "type_a_autonomous_seeds", band="flag")
    except Exception:
        return []
    rows = surface.get("rows") if isinstance(surface.get("rows"), list) else []
    seed_identity_terms_by_id: dict[str, set[str]] = {}
    seed_term_counts: Counter[str] = Counter()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        seed_id = str(row.get("seed_id") or row.get("id") or "").strip()
        if not seed_id:
            continue
        terms: set[str] = set()
        for field in (
            "seed_id",
            "id",
            "title",
            "selection_label",
            "selection_token",
        ):
            terms |= _autonomous_seed_match_terms(row.get(field))
        seed_identity_terms_by_id[seed_id] = terms
        seed_term_counts.update(terms)

    matches: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        seed_id = str(row.get("seed_id") or row.get("id") or "").strip()
        if not seed_id:
            continue
        seed_phrase = _autonomous_seed_match_text(seed_id)
        score = 0.0
        reason_bits: list[str] = []
        if seed_phrase and seed_phrase in query_text:
            score += 8.0
            reason_bits.append("operator named saved seed id")
        seed_terms = _autonomous_seed_match_terms(seed_id)
        seed_overlap = sorted(query_terms & seed_terms)
        if len(seed_overlap) >= 2:
            score += 3.0 + min(len(seed_overlap), 4) * 0.35
            reason_bits.append("seed id term overlap: " + ", ".join(seed_overlap[:4]))
        unique_seed_overlap = sorted(
            term
            for term in (query_terms & seed_identity_terms_by_id.get(seed_id, set()))
            if seed_term_counts.get(term) == 1 and len(term) >= 8
        )
        if unique_seed_overlap:
            score += min(len(unique_seed_overlap), 3) * 3.0
            reason_bits.append(
                "unique saved-seed term overlap: " + ", ".join(unique_seed_overlap[:4])
            )
        metadata_overlap: set[str] = set()
        for field in (
            "title",
            "selection_label",
            "selection_token",
            "purpose",
            "goal",
            "current_focus",
            "next_wave_objective",
            "flag",
            "claim",
        ):
            metadata_overlap |= query_terms & _autonomous_seed_match_terms(row.get(field))
        if len(metadata_overlap) >= 3:
            score += min(len(metadata_overlap), 6) * 0.25
            reason_bits.append(
                "seed metadata term overlap: " + ", ".join(sorted(metadata_overlap)[:5])
            )
        if score < 3.0:
            continue
        matches.append(
            {
                "seed_id": seed_id,
                "score": round(score, 6),
                "reason": "; ".join(reason_bits)
                or "Query matched saved autonomous-seed metadata.",
            }
        )
    matches.sort(key=lambda item: (-float(item["score"]), str(item["seed_id"])))
    return matches[:3]


def _is_speed_refinement_query(query: str) -> bool:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _query_terms(lower_query)
    if any(phrase.replace("-", " ") in lower_query for phrase in SPEED_REFINEMENT_QUERY_PHRASES):
        return True
    speed_terms = {
        "speed",
        "latency",
        "efficient",
        "efficiency",
        "optimise",
        "optimising",
        "optimisation",
        "optimize",
        "optimizing",
        "optimization",
        "timing",
        "timings",
        "throughput",
        "bottleneck",
        "bottlenecks",
        "wait",
        "tax",
    }
    telemetry_terms = {
        "command",
        "commands",
        "telemetry",
        "diagnostic",
        "diagnostics",
        "meta",
        "process",
        "profile",
        "profiles",
        "speedboard",
        "pytest",
        "validation",
        "runtime",
        "surface",
        "surfaces",
        "kernel",
        "startup",
    }
    return bool((terms & speed_terms) and (terms & telemetry_terms))


def _is_external_benchmark_calibration_query(query: str) -> bool:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _query_terms(lower_query)
    if any(phrase.replace("-", " ") in lower_query for phrase in EXTERNAL_BENCHMARK_CALIBRATION_QUERY_PHRASES):
        return True
    has_formal_math = bool({"formal"} & terms and {"math"} & terms)
    has_benchmark = bool({"benchmark", "benchmarks", "calibration", "verisoftbench", "micro10"} & terms)
    has_provider_repair = bool({"provider", "nim", "nvidia", "repair", "proof"} & terms)
    return has_formal_math and has_benchmark and has_provider_repair


def _is_workitem_spine_query(query: str) -> bool:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _query_terms(lower_query)
    if any(phrase.replace("-", " ") in lower_query for phrase in WORKITEM_SPINE_QUERY_PHRASES):
        return True
    matched_groups = sum(1 for group in WORKITEM_SPINE_REQUIRED_TERM_GROUPS if group & terms)
    spine_terms = {
        "authority",
        "boundary",
        "claim",
        "claims",
        "currentness",
        "drilldown",
        "mutation",
        "operational",
        "projection",
        "seed",
        "seeds",
        "session",
        "validation",
    }
    return matched_groups >= 2 and bool(spine_terms & terms)


def _is_generated_projection_owner_query(query: str) -> bool:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _query_terms(lower_query)
    if any(phrase.replace("-", " ") in lower_query for phrase in GENERATED_PROJECTION_OWNER_QUERY_PHRASES):
        return True
    matched_groups = sum(1 for group in GENERATED_PROJECTION_OWNER_REQUIRED_TERM_GROUPS if group & terms)
    boundary_terms = {
        "boundary",
        "check",
        "command",
        "drainer",
        "manual",
        "mutation",
        "repair",
        "safe",
        "settle",
        "stale",
        "state",
        "validation",
    }
    return matched_groups >= 2 and bool(boundary_terms & terms)


def _is_frontend_page_meta_contract_query(query: str) -> bool:
    """Narrow context-pack predicate for the frontend page-meta contract.

    Mirrors the entry-classifier predicate at
    ``system.lib.kernel.commands.comprehension_snapshot._task_mentions_frontend_page_meta_contract``.
    Requires either an exact phrase (``page meta``, ``PageHeader``, etc.) or a
    conjunction of (role: frontend/station/lens) AND (surface: page/lens) AND
    (meta-scent: meta/metadata/self-description/purpose/principles/decisions/
    overwhelm). Bare ``frontend``, bare ``coverage``, bare ``documentation``
    must not trigger this anchor or the system-atlas anchors would be hijacked
    on every frontend query.
    """
    if not query:
        return False
    text = str(query).casefold()
    terms = {
        part.strip(".,:;!?()[]{}\"'`").lower()
        for part in str(query).split()
        if part.strip(".,:;!?()[]{}\"'`")
    }
    phrases = (
        "page meta",
        "page-meta",
        "page_meta",
        "page metadata",
        "page meta documentation",
        "page meta contract",
        "page-meta contract",
        "frontend page meta",
        "lens self description",
        "lens self-description",
        "page self description",
        "page self-description",
        "station lens meta",
        "station coverage page",
        "pageheader purpose",
        "pageidentitybadge purpose",
        "page purpose principles decisions",
        "purpose principles decisions navigation",
    )
    if any(phrase in text for phrase in phrases):
        return True
    component_terms = {"pageheader", "pageidentitybadge"}
    if component_terms & terms:
        return True
    role_terms = {"frontend", "station", "lens"}
    surface_terms = {"page", "lens", "lenses", "pages"}
    meta_terms = {
        "meta",
        "metadata",
        "self-description",
        "purpose",
        "principles",
        "decisions",
        "overwhelm",
    }
    has_role = bool(role_terms & terms)
    has_surface = bool(surface_terms & terms)
    has_meta = bool(meta_terms & terms) or "self-description" in text or "self description" in text
    if has_role and has_surface and has_meta:
        return True
    return False


def _is_config_plane_query(query: str) -> bool:
    lower_query = str(query or "").lower().replace("-", " ")
    terms = _query_terms(lower_query)
    return any(phrase in lower_query for phrase in CONFIG_PLANE_QUERY_PHRASES) or len(terms & CONFIG_PLANE_QUERY_TERMS) >= 3


def _normalize_hit(kind: str, row_id: str) -> tuple[str, str] | None:
    source_kind = str(kind or "").strip()
    raw_id = str(row_id or "").strip()
    if not source_kind or not raw_id:
        return None
    if source_kind == "paper_modules":
        return "paper_modules", raw_id
    if source_kind == "skills":
        return "skills", raw_id.rsplit(".", 1)[-1]
    if source_kind == "standards_json":
        return "standards", raw_id.rsplit("/", 1)[-1].removesuffix(".json")
    if source_kind == "annex_notes":
        return "annex_patterns", raw_id.replace("::", ":")
    if source_kind == "raw_seed_shards":
        return "raw_seed_shards", raw_id
    return None


def _semantic_candidates(
    repo_root: Path,
    query: str,
    *,
    top_k: int = 24,
    include_semantic: bool | None = None,
    semantic_timeout_ms: int = DEFAULT_SEMANTIC_TIMEOUT_MS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if include_semantic is False:
        return [], {
            "status": "disabled",
            "reason": "caller_disabled_semantic_routing",
            "source_kinds": list(SEMANTIC_SOURCE_KINDS),
        }
    if os.environ.get("AIW_CONTEXT_PACK_DISABLE_SEMANTIC") == "1":
        return [], {
            "status": "disabled",
            "reason": "AIW_CONTEXT_PACK_DISABLE_SEMANTIC=1",
            "source_kinds": list(SEMANTIC_SOURCE_KINDS),
        }
    start = time.perf_counter()
    timeout_seconds = max(0, int(semantic_timeout_ms or 0)) / 1000.0
    if timeout_seconds > 0:
        queue: mp.Queue[dict[str, Any]] = mp.Queue(maxsize=1)
        proc = mp.Process(
            target=_semantic_query_worker,
            args=(queue, str(repo_root), query, top_k),
            daemon=True,
        )
        proc.start()
        proc.join(timeout_seconds)
        wall_ms = int(round((time.perf_counter() - start) * 1000))
        if proc.is_alive():
            proc.terminate()
            proc.join(0.2)
            return [], {
                "status": "timeout_deferred",
                "reason": f"semantic route expansion exceeded {semantic_timeout_ms}ms budget",
                "wall_ms": wall_ms,
                "timeout_ms": int(semantic_timeout_ms),
                "source_kinds": list(SEMANTIC_SOURCE_KINDS),
                "fallback": "authored anchors and cluster surfaces",
            }
        try:
            message = queue.get_nowait()
        except Exception:
            message = {"ok": False, "error": "semantic worker exited without payload"}
        if not message.get("ok"):
            return [], {
                "status": "unavailable",
                "reason": str(message.get("error") or "semantic worker failed"),
                "wall_ms": wall_ms,
                "source_kinds": list(SEMANTIC_SOURCE_KINDS),
            }
        routed = message.get("payload")
    else:
        try:
            from system.lib.semantic_routing import query_routes

            routed = query_routes(
                repo_root,
                query=query,
                source_kinds=SEMANTIC_SOURCE_KINDS,
                top_k=top_k,
                check_live_staleness=False,
            )
        except Exception as exc:
            return [], {
                "status": "unavailable",
                "reason": str(exc),
                "source_kinds": list(SEMANTIC_SOURCE_KINDS),
            }
    wall_ms = int(round((time.perf_counter() - start) * 1000))
    try:
        routed_mapping = dict(routed) if isinstance(routed, Mapping) else None
    except Exception:
        routed_mapping = None
    if routed_mapping is None:
        return [], {
            "status": "unavailable",
            "reason": "non_mapping_route_payload",
            "wall_ms": wall_ms,
            "source_kinds": list(SEMANTIC_SOURCE_KINDS),
        }
    routed = routed_mapping
    if routed.get("error"):
        return [], {
            "status": "unavailable",
            "reason": str(routed.get("error")),
            "wall_ms": wall_ms,
            "source_kinds": list(SEMANTIC_SOURCE_KINDS),
        }

    out: list[dict[str, Any]] = []
    for hit in routed.get("seed_hits") or []:
        if not isinstance(hit, Mapping):
            continue
        normalized = _normalize_hit(str(hit.get("source_kind") or ""), str(hit.get("id") or ""))
        if not normalized:
            continue
        kind_id, row_id = normalized
        out.append(
            {
                "kind_id": kind_id,
                "id": row_id,
                "score": float(hit.get("score") or 0.0),
                "reason": f"semantic seed hit from {hit.get('source_kind')}:{hit.get('facet')}",
                "source_kind": hit.get("source_kind"),
                "facet": hit.get("facet"),
                "preview": _trim(hit.get("preview"), max_chars=220),
            }
        )
    for hit in routed.get("fallback_hits") or []:
        if not isinstance(hit, Mapping):
            continue
        normalized = _normalize_hit(str(hit.get("source_kind") or ""), str(hit.get("id") or ""))
        if not normalized:
            continue
        kind_id, row_id = normalized
        out.append(
            {
                "kind_id": kind_id,
                "id": row_id,
                "score": min(float(hit.get("score") or 0.0) / 10.0, 0.72),
                "reason": f"{hit.get('match_backend') or 'fallback'} hit from {hit.get('source_kind')}:{hit.get('facet')}",
                "source_kind": hit.get("source_kind"),
                "facet": hit.get("facet"),
                "preview": _trim(hit.get("preview"), max_chars=220),
            }
        )
    for hit in routed.get("route_hits") or []:
        if not isinstance(hit, Mapping):
            continue
        normalized = _normalize_hit(str(hit.get("target_kind") or ""), str(hit.get("target_id") or ""))
        if not normalized:
            continue
        kind_id, row_id = normalized
        out.append(
            {
                "kind_id": kind_id,
                "id": row_id,
                "score": float(hit.get("combined_score") or hit.get("semantic_score") or 0.0),
                "reason": f"semantic route expansion from {hit.get('seed_source_kind')}",
                "source_kind": hit.get("target_kind"),
                "facet": hit.get("target_facet"),
                "preview": _trim(hit.get("target_source_path"), max_chars=220),
            }
        )
    status = {
        "status": "available",
        "source_kinds": list(routed.get("source_kinds") or SEMANTIC_SOURCE_KINDS),
        "seed_hit_count": len(routed.get("seed_hits") or []),
        "route_hit_count": len(routed.get("route_hits") or []),
        "fallback_hit_count": len(routed.get("fallback_hits") or []),
        "graph_path": routed.get("graph_path"),
        "wall_ms": wall_ms,
        "timeout_ms": int(semantic_timeout_ms or 0) if semantic_timeout_ms else None,
    }
    return out, status


def _deferred_semantic_status(query: str) -> dict[str, Any]:
    return {
        "status": "deferred_due_to_routine_latency_budget",
        "reason": "routine context-pack uses authored anchors and materialized surfaces by default",
        "timeout_ms": ROUTINE_SEMANTIC_BUDGET_MS,
        "source_kinds": list(SEMANTIC_SOURCE_KINDS),
        "fallback": "authored anchors and bounded kind signposts",
        "deep_command": (
            "AIW_CONTEXT_PACK_PROFILE=deep ./repo-python kernel.py --context-pack "
            f"{json.dumps(str(query or ''))} --context-budget 12000"
        ),
    }


def _context_anchor_matches(query: str, trigger_phrases: list[Any]) -> bool:
    lower_query = str(query or "").lower()
    query_terms = _query_terms(query)
    for phrase in trigger_phrases:
        lower_phrase = str(phrase or "").strip().lower()
        if not lower_phrase:
            continue
        if lower_phrase in lower_query:
            return True
        phrase_terms = {
            term
            for term in _query_terms(lower_phrase)
            if len(term) > 2 and term not in CONTEXT_ANCHOR_STOPWORDS
        }
        if phrase_terms and phrase_terms <= query_terms:
            return True
    return False


def _registry_context_pack_anchors(repo_root: Path, query: str) -> list[dict[str, Any]]:
    registry = _load_json(repo_root / "codex/doctrine/skills/skill_registry.json")
    rows: list[dict[str, Any]] = []
    families = registry.get("families") if isinstance(registry.get("families"), list) else []
    for family in families:
        if not isinstance(family, dict):
            continue
        skills = family.get("skills") if isinstance(family.get("skills"), list) else []
        for skill in skills:
            if not isinstance(skill, dict):
                continue
            anchors = skill.get("context_pack_anchors")
            if not isinstance(anchors, dict):
                continue
            triggers = anchors.get("trigger_phrases")
            if not isinstance(triggers, list) or not _context_anchor_matches(query, triggers):
                continue
            skill_id = str(skill.get("id") or "").strip()
            include = anchors.get("include") if isinstance(anchors.get("include"), list) else []
            for item in include:
                if not isinstance(item, dict):
                    continue
                item_triggers = item.get("trigger_phrases")
                item_trigger_matched = False
                if isinstance(item_triggers, list):
                    item_trigger_matched = _context_anchor_matches(query, item_triggers)
                    if not item_trigger_matched:
                        continue
                kind_id = str(item.get("kind") or item.get("kind_id") or "").strip()
                row_id = str(item.get("id") or item.get("row_id") or "").strip()
                if not kind_id or not row_id:
                    continue
                score = float(item.get("relevance") or item.get("score") or 0.9)
                if item_trigger_matched:
                    score = max(score, 0.985)
                rows.append(
                    {
                        "kind_id": kind_id,
                        "id": row_id,
                        "score": score,
                        "reason": str(item.get("reason") or f"Selected by {skill_id}.context_pack_anchors."),
                        "source_kind": "skill_registry_context_pack_anchor",
                        "facet": skill_id,
                    }
                )
    return rows


def _cognitive_operator_anchor_candidates(query: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_CONTEXT_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_SELECTED_ID,
                "score": 0.998,
                "reason": (
                    "Autonomous capability-discovery task matched the cognitive-operator "
                    "anchor; open the dogfooded Capability Gap Ladder before generic backlog work."
                ),
                "source_kind": "cognitive_operator_discovery_anchor",
                "facet": "capability_gap_ladder",
            }
        )
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_DISCONFIRMATION_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_DISCONFIRMATION_ID,
                "score": 0.999,
                "reason": (
                    "Task names route disagreement, counterevidence, or falsifiers; open the "
                    "Disconfirmation Harness before committing to a plausible selected route."
                ),
                "source_kind": "cognitive_operator_disconfirmation_anchor",
                "facet": "disconfirmation_harness",
            }
        )
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_CAUSAL_TRIAL_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_CAUSAL_TRIAL_ID,
                "score": 1.0,
                "reason": (
                    "Task asks for causal evidence, pre/post prediction, or dogfood proof; open the "
                    "Causal Trial Harness before claiming a substrate changed cognition."
                ),
                "source_kind": "cognitive_operator_causal_trial_anchor",
                "facet": "causal_trial_harness",
            }
        )
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_COMPOSITION_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_COMPOSITION_ID,
                "score": 1.0,
                "reason": (
                    "Task asks for operator composition, sequencing, or a multi-operator chain; open the "
                    "Operator Composition Sequencer before applying operators ad hoc."
                ),
                "source_kind": "cognitive_operator_composition_anchor",
                "facet": "operator_composition_sequencer",
            }
        )
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_AFFORDANCE_PASSPORT_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_AFFORDANCE_PASSPORT_ID,
                "score": 1.0,
                "reason": (
                    "Task asks for row-owned operator affordances, compression passports, "
                    "anti-triggers, or landmines; open the Affordance Passport Author before "
                    "adding another hardcoded route phrase."
                ),
                "source_kind": "cognitive_operator_affordance_passport_anchor",
                "facet": "affordance_passport_author",
            }
        )
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_PASSPORT_PROPAGATOR_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_PASSPORT_PROPAGATOR_ID,
                "score": 1.0,
                "reason": (
                    "Task asks to propagate operator passports, backfill missing compression passports, "
                    "or inspect passport coverage; open the Operator Passport Propagator before "
                    "manual one-row passport edits."
                ),
                "source_kind": "cognitive_operator_passport_propagation_anchor",
                "facet": "operator_passport_propagator",
            }
        )
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_ROUTE_LEASE_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_ROUTE_LEASE_EXECUTOR_ID,
                "score": 1.0,
                "reason": (
                    "Task names route leases, repeated broad routing, or direct action after entry; "
                    "open the Route Lease Executor before calling another broad route."
                ),
                "source_kind": "cognitive_operator_route_lease_anchor",
                "facet": "route_lease_executor",
            }
        )
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_PROMPT_ROUTE_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_PROMPT_ROUTE_ASSIMILATOR_ID,
                "score": 1.0,
                "reason": (
                    "Task names prompt-derived route misses, wake prompts, docs-route misses, "
                    "or trace-continuation phrases; open the Prompt Route Assimilator before "
                    "leaving the phrase in diagnostics."
                ),
                "source_kind": "cognitive_operator_prompt_route_anchor",
                "facet": "prompt_route_assimilator",
            }
        )
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_PRESSURE_REDUCTION_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_PRESSURE_REDUCER_ID,
                "score": 1.0,
                "reason": (
                    "Task names backlog, queue, receipt, row-patch, or status-binding pressure; "
                    "open the Pressure-to-Action Reducer before expanding broad pressure surfaces."
                ),
                "source_kind": "cognitive_operator_pressure_reduction_anchor",
                "facet": "pressure_to_action_reducer",
            }
        )
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_ACCRETION_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_ACCRETION_GOVERNOR_ID,
                "score": 1.0,
                "reason": (
                    "Task asks whether to add another cognitive operator, merge into an existing "
                    "operator, or control operator sprawl; open the Operator Accretion Governor "
                    "before installing more operator rows."
                ),
                "source_kind": "cognitive_operator_accretion_anchor",
                "facet": "operator_accretion_governor",
            }
        )
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_ATTENTION_FRAME_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_ATTENTION_FRAME_REHYDRATOR_ID,
                "score": 1.0,
                "reason": (
                    "Task names attention-frame, reread, stale-read, rediscovery, selected-handle, "
                    "or mutation-boundary pressure; open the Attention Frame Rehydrator before "
                    "broad rereads or edits from stale context."
                ),
                "source_kind": "cognitive_operator_attention_frame_anchor",
                "facet": "attention_frame_rehydrator",
            }
        )
    if _context_anchor_matches(query, list(COGNITIVE_OPERATOR_LANDING_HANDOFF_TRIGGERS)):
        rows.append(
            {
                "kind_id": "cognitive_operators",
                "id": COGNITIVE_OPERATOR_LANDING_HANDOFF_COMPILER_ID,
                "score": 1.0,
                "reason": (
                    "Task names validated but uncommitted work, commit authority, owned paths, "
                    "or a landing blocker; open the Landing Handoff Compiler before yielding "
                    "with only prose about stranded changes."
                ),
                "source_kind": "cognitive_operator_landing_handoff_anchor",
                "facet": "landing_handoff_compiler",
            }
        )
    return rows


def _detected_workitem_ids(workitem_target_resolution: Mapping[str, Any]) -> list[str]:
    detected = (
        workitem_target_resolution.get("detected")
        if isinstance(workitem_target_resolution.get("detected"), Mapping)
        else {}
    )
    return [
        str(item)
        for item in list(detected.get("work_item_ids") or [])
        if str(item or "").strip()
    ]


def _should_skip_python_target_resolution_for_workitem(
    query: str,
    workitem_target_resolution: Mapping[str, Any],
) -> bool:
    if not _detected_workitem_ids(workitem_target_resolution):
        return False
    return PYTHON_EXPLICIT_TARGET_HINT_RE.search(str(query or "")) is None


def _python_target_resolution_skipped_for_workitem(
    query: str,
    workitem_target_resolution: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "python_target_resolution_v0",
        "status": "no_python_target",
        "source_ref": "codex/standards/std_python_scope_index.json",
        "projection_currentness": {
            "status": "index_load_skipped_workitem_target_resolution",
            "source_ref": "codex/standards/std_python_scope_index.json",
        },
        "detected": {
            "paths": [],
            "explicit_scope_ids": [],
            "symbol_names": [],
            "query_terms": sorted(_query_terms(query)),
            "suppressed_work_item_ids": _detected_workitem_ids(workitem_target_resolution),
        },
        "files": [],
        "scopes": [],
        "unresolved": [],
        "source_span_policy": "Open source spans only after file/scope card or graph-context evidence is insufficient for the task.",
        "provider_population_gap_route": "./repo-python kernel.py --option-surface row_patches --band cluster_flag",
        "provider_population_lane_command": "./repo-python tools/meta/control/python_navigation_population_lane.py select --limit 3 --gap-kind both",
        "provider_boundary": "row_patch_candidate_only_no_direct_mutation",
    }


def _merge_candidates(
    repo_root: Path,
    semantic: list[dict[str, Any]],
    query: str,
    *,
    workitem_target_resolution: Mapping[str, Any],
    python_target_resolution: Mapping[str, Any],
) -> list[dict[str, Any]]:
    best: dict[tuple[str, str], dict[str, Any]] = {}

    def add(kind_id: str, row_id: str, score: float, reason: str, **extra: Any) -> None:
        key = (kind_id, row_id)
        row = {
            "kind_id": kind_id,
            "id": row_id,
            "score": round(float(score), 6),
            "reason": reason,
            **extra,
        }
        current = best.get(key)
        if current is None or float(row["score"]) > float(current["score"]):
            best[key] = row

    for row in semantic:
        add(
            str(row["kind_id"]),
            str(row["id"]),
            float(row.get("score") or 0.0),
            str(row.get("reason") or "semantic candidate"),
            source_kind=row.get("source_kind"),
            facet=row.get("facet"),
            preview=row.get("preview"),
        )

    for row in _registry_context_pack_anchors(repo_root, query):
        add(
            str(row["kind_id"]),
            str(row["id"]),
            float(row.get("score") or 0.0),
            str(row.get("reason") or "registry context-pack anchor"),
            source_kind=row.get("source_kind"),
            facet=row.get("facet"),
        )

    for row in _cognitive_operator_anchor_candidates(query):
        add(
            str(row["kind_id"]),
            str(row["id"]),
            float(row.get("score") or 0.0),
            str(row.get("reason") or "cognitive operator anchor"),
            source_kind=row.get("source_kind"),
            facet=row.get("facet"),
        )

    if _is_operator_thread_continuation_card_query(query):
        thread_id = _operator_thread_id_from_query(query) or "thread_id_required"
        add(
            "operator_thread_continuation_card",
            thread_id,
            1.0 if thread_id != "thread_id_required" else 0.94,
            "Operator thread continuation-card query should carry the metadata-only card through context-pack instead of raw transcript paste.",
            source_kind="operator_thread_continuation_card_anchor",
            facet="metadata_only_type_b_grounding",
            thread_id=thread_id,
        )

    for row in workitem_target_candidates_from_resolution(workitem_target_resolution):
        add(
            str(row["kind_id"]),
            str(row["id"]),
            float(row.get("score") or 0.0),
            str(row.get("reason") or "workitem target resolution"),
            source_kind=row.get("source_kind"),
            facet=row.get("facet"),
        )

    for row in python_target_candidates_from_resolution(python_target_resolution):
        add(
            str(row["kind_id"]),
            str(row["id"]),
            float(row.get("score") or 0.0),
            str(row.get("reason") or "python target resolution"),
            source_kind=row.get("source_kind"),
            facet=row.get("facet"),
            target_packet=row.get("target_packet"),
        )

    if _is_state_axis_query(query):
        add(
            "derived_facts",
            "state_axis_artifact",
            0.997,
            "Generic state-axis question should open the generated fact navigation artifact, not a prose inventory.",
            source_kind="state_axis_artifact_anchor",
            facet="state_axis_overview",
        )

    if _is_control_plane_query(query):
        for kind_id, row_id, score, reason in CONTROL_PLANE_ANCHORS:
            add(kind_id, row_id, score, reason, source_kind="control_plane_anchor", facet="route_contract")
        if "context" in _query_terms(query) or "compression" in _query_terms(query):
            add(
                "annex_prior_art",
                "arxiv-2604-19572",
                0.88,
                "Indexed TACO prior-art annex for terminal-agent observational context compression.",
                source_kind="annex_catalog",
                facet="context_compression",
            )
    if is_root_navigator_ai_native_query(query):
        add(
            "frontend_views",
            "rootNavigator",
            1.0,
            "Root Navigator/constitutional atlas/frontend-readiness task should open the AI-native Root Navigator view packet before visual redesign or broad frontend browsing.",
            source_kind="root_navigator_ai_native_anchor",
            facet="constitutional_atlas_frontend_readiness",
        )
        add(
            "system_atlas",
            "dom_system_atlas",
            0.996,
            "Root Navigator dogfood needs the generated System Atlas as measured substrate projection, not source authority.",
            source_kind="root_navigator_ai_native_anchor",
            facet="measured_substrate_projection",
        )
    if _is_frontend_page_meta_contract_query(query):
        add(
            "paper_modules",
            "frontend_page_meta_contract",
            0.999,
            "Frontend page-meta query carries strong page/lens metadata scent; the constitutional contract names the five-facet self-description shape (purpose, principles, decisions, navigation, overwhelm control) every Station lens must carry.",
            source_kind="frontend_page_meta_protocol_anchor",
            facet="page_meta_contract",
        )
        add(
            "paper_modules",
            "frontend_station_cockpit",
            0.997,
            "Cockpit module is the Station lens registry over PageHeader / PageIdentityBadge / surfaces.ts; open after the contract for current-state details.",
            source_kind="frontend_page_meta_protocol_anchor",
            facet="cockpit_sibling",
        )
        add(
            "paper_modules",
            "frontend_navigation_plane",
            0.995,
            "Navigation plane owns the F4 navigation facet via surfaces.ts outboundTo / isCulDeSac / navigation_graph.json projections.",
            source_kind="frontend_page_meta_protocol_anchor",
            facet="navigation_plane_sibling",
        )
    if _is_public_safe_dissemination_gate_query(query):
        add(
            "dissemination_gate",
            "public_safe_atlas_gate_v1",
            1.0,
            "Public-safe dissemination, atlas-ref, or leaf-readiness query should open the gate/report/audit owner route before treating generated System Atlas rows as sendable evidence.",
            source_kind="public_safe_dissemination_gate_anchor",
            facet="atlas_ref_disclosure_gate",
        )
    if _is_prompt_shelf_metadata_query(query):
        add(
            "prompt_shelf_metadata",
            "prompt_shelf_runs_index_v1",
            1.0,
            "Prompt-shelf, Type B reasoning, or self-description lesson extraction query should open the metadata-only run index before any raw run or raw event body.",
            source_kind="prompt_shelf_metadata_anchor",
            facet="metadata_only_reasoning_extraction",
        )
    if _is_speed_refinement_query(query):
        add(
            "skills",
            "navigation_metabolism",
            1.004,
            "Speed/refinement query should open navigation metabolism plus command telemetry surfaces before generic autonomous-seed or cognitive-operator routing.",
            source_kind="speed_refinement_command_telemetry_anchor",
            facet="command_latency_route",
        )
        add(
            "skills",
            "agent_session_diagnostics",
            1.003,
            "Speed/refinement query should use session diagnostics and command timing surfaces rather than broad repository search.",
            source_kind="speed_refinement_command_telemetry_anchor",
            facet="session_command_timing",
        )
        add(
            "type_a_autonomous_seeds",
            TYPE_A_AUTONOMOUS_SEED_SPEED_SELECTED_ID,
            1.002,
            "Speed/refinement autonomous-seed query should select the existing agent-session-diagnostics timing seed instead of the generic autonomous-seed owner row.",
            source_kind="speed_refinement_command_telemetry_anchor",
            facet="autonomous_seed_command_timing",
        )
    if _is_type_a_autonomous_seed_query(query):
        matched_seed_rows = _type_a_autonomous_seed_matches_for_query(repo_root, query)
        if not matched_seed_rows and _is_speed_refinement_query(query):
            matched_seed_rows = [
                {
                    "seed_id": TYPE_A_AUTONOMOUS_SEED_SPEED_SELECTED_ID,
                    "score": 3.0,
                    "reason": "speed/refinement seed query maps to the timing seed",
                }
            ]
        if matched_seed_rows:
            for index, seed_match in enumerate(matched_seed_rows):
                seed_id = str(seed_match["seed_id"])
                add(
                    "type_a_autonomous_seeds",
                    seed_id,
                    max(1.006 - index * 0.001, 1.001),
                    (
                        "Type A autonomous-seed replay query matched a saved seed owner "
                        f"card from the seed corpus: {seed_match['reason']}."
                    ),
                    source_kind="type_a_autonomous_seed_anchor",
                    facet="matched_saved_seed_owner_route",
                    match_score=seed_match["score"],
                )
        else:
            add(
                "type_a_autonomous_seeds",
                TYPE_A_AUTONOMOUS_SEED_SELECTED_ID,
                1.0,
                "Type A autonomous seed or saved seed-loop query should open the seed owner card before raw seed files or bundle commands.",
                source_kind="type_a_autonomous_seed_anchor",
                facet="saved_seed_owner_route",
            )
        add(
            "concepts",
            "con_039",
            0.999,
            "Autonomous-seed framework queries should expose the concept row that defines the manual queue, Type A execution, no-null edit, and compaction-continuity ontology.",
            source_kind="type_a_autonomous_seed_anchor",
            facet="autonomous_seed_ontology",
        )
        add(
            "mechanisms",
            "mech_035",
            0.998,
            "Autonomous-seed framework queries should expose the mission-loop mechanism for detection, rehydration, mutation, validation, continuity, and reentry rewrite.",
            source_kind="type_a_autonomous_seed_anchor",
            facet="autonomous_seed_mission_loop",
        )
        add(
            "standards",
            "std_autonomous_seed_prompt",
            0.997,
            "Autonomous-seed replay and continuation queries should expose the seed prompt standard that owns detection, no-null edits, and replay receipt contracts.",
            source_kind="type_a_autonomous_seed_anchor",
            facet="autonomous_seed_standard",
        )
        add(
            "skills",
            "type_a_autonomous_seed_loop",
            0.996,
            "Autonomous-seed replay and continuation queries should expose the Type A receiver skill before generic navigation or cognitive-operator surfaces.",
            source_kind="type_a_autonomous_seed_anchor",
            facet="autonomous_seed_receiver_skill",
        )
        add(
            "skills",
            "autonomous_seed_prompt_author",
            0.995,
            "Autonomous-seed replay and continuation queries should expose the authoring skill so Type A and Type B seed prompt roles stay separated.",
            source_kind="type_a_autonomous_seed_anchor",
            facet="autonomous_seed_authoring_skill",
        )
        add(
            "paper_modules",
            "autonomous_seed_anatomy",
            0.994,
            "Autonomous-seed replay and continuation queries should expose the anatomy module as the compact explanatory owner.",
            source_kind="type_a_autonomous_seed_anchor",
            facet="autonomous_seed_anatomy",
        )
    if _is_workitem_spine_query(query):
        add(
            "workitem_spine",
            WORKITEM_SPINE_SELECTED_ID,
            1.0,
            "Task Ledger / Work Ledger / CAP / operational-seed query should open the operational WorkItem spine before generic authority or mutation-boundary operators.",
            source_kind="workitem_spine_anchor",
            facet="task_work_ledger_operational_spine",
        )
    if _is_generated_projection_owner_query(query):
        add(
            "generated_projection_ownership",
            GENERATED_PROJECTION_OWNER_SELECTED_ID,
            1.001,
            "Generated projection ownership/currentness query should open the registry, owner-check, dirty-source, and drainer route before refreshing or hand-editing generated outputs.",
            source_kind="generated_projection_owner_anchor",
            facet="projection_source_coupling_owner_route",
        )
    if _is_external_benchmark_calibration_query(query):
        add(
            "external_benchmark_calibration",
            EXTERNAL_BENCHMARK_CALIBRATION_SELECTED_ID,
            1.002,
            "Formal-math external benchmark/proof-repair query should open the VeriSoftBench micro-10 calibration owner card before raw provider output, generated scorecards, or broad proof search.",
            source_kind="external_benchmark_calibration_anchor",
            facet="verisoftbench_micro_10_provider_repair_owner_route",
        )
    if _is_system_atlas_query(query):
        add(
            "paper_modules",
            "system_self_comprehension_root",
            0.999,
            "Canonical root contract for the system_self_comprehension_packet family; first funnel tip for broad system identity questions.",
            source_kind="system_atlas_protocol_anchor",
            facet="self_comprehension_root",
        )
        add(
            "compression_profiles",
            "ai_workflow_system_packet_v1",
            0.998,
            "Full system packet render profile governed by system_self_comprehension_root.",
            source_kind="system_atlas_protocol_anchor",
            facet="full_packet_profile",
        )
        add(
            "system_atlas",
            "dom_system_atlas",
            0.995,
            "Broad system/coverage query should use the generated atlas as a drilldown row under the self-comprehension root, not a graph dump.",
            source_kind="system_atlas_protocol_anchor",
            facet="control_plane_drilldown",
        )
        add(
            "paper_modules",
            "system_self_comprehension_spine",
            0.994,
            "Compatibility/evidence spine for the generated atlas and substrate coverage graph under system_self_comprehension_root.",
            source_kind="system_atlas_protocol_anchor",
            facet="spine_paper_module",
        )
        terms = _query_terms(query)
        if "type" in terms or "typeb" in terms or "type-b" in str(query).lower() or "external" in terms:
            add(
                "compression_profiles",
                "type_b_external_grounding_v1",
                0.997,
                "Compact Type B grounding render profile governed by system_self_comprehension_root.",
                source_kind="system_atlas_protocol_anchor",
                facet="compact_type_b_profile",
            )
    if _is_system_crystal_query(query):
        add(
            "system_crystal",
            "private_system_crystal_v1",
            1.0,
            "Private generated cap surface for the self-comprehension family; dense internal projection with JSON/check builder and bounded markdown renders.",
            source_kind="system_crystal_protocol_anchor",
            facet="private_crystal",
        )
    if _is_config_plane_query(query):
        add(
            "paper_modules",
            "federated_config_plane",
            0.999,
            "Config authority query should open the federated config plane before grep, raw Settings, or direct master_config edits.",
            source_kind="config_plane_protocol_anchor",
            facet="config_plane_root",
        )
        add(
            "standards",
            "std_config_authority_registry",
            0.998,
            "Config authority rows are governed by std_config_authority_registry.",
            source_kind="config_plane_protocol_anchor",
            facet="config_row_contract",
        )
        add(
            "config_authorities",
            "master_config.bridge",
            0.997,
            "Representative root_effective_config row with effective trace and compatibility-writer semantics.",
            source_kind="config_plane_protocol_anchor",
            facet="root_effective_config",
        )
        add(
            "config_authorities",
            "frontend.configs_board.config_ref",
            0.996,
            "Representative frontend config_ref resolver row for Control Room ConfigsBoard.",
            source_kind="config_plane_protocol_anchor",
            facet="config_ref_resolver",
        )
        add(
            "config_authorities",
            "api.config.system",
            0.995,
            "Compatibility edit endpoint row; confirms /api/config/system remains scoped instead of becoming the new plane.",
            source_kind="config_plane_protocol_anchor",
            facet="compatibility_api",
        )
    terms = _query_terms(query)
    lower_query = str(query or "").lower()
    if (
        "lattice" in terms
        or ("dynamic" in terms and "paper" in terms)
        or ({"row", "rows", "edge", "edges"} & terms and ({"paper", "doctrine", "theory", "navigation"} & terms))
    ):
        add(
            "skills",
            "dynamic_paper_lattice",
            0.9,
            "Paper/doctrine task asks for the dynamic paper lattice drilldown skill.",
            source_kind="task_anchor",
            facet="paper_lattice",
        )
        add(
            "paper_modules",
            "navigation_hologram_theory",
            0.92,
            "Current supported paper-lattice exemplar and root navigation theory slug.",
            source_kind="task_anchor",
            facet="paper_lattice",
        )
    if (
        "session" in terms
        or "sessions" in terms
        or "telemetry" in terms
        or "workers" in terms
        or "wandering" in terms
        or "traces" in terms
        or "movement" in terms
        or "claude" in terms
        or "codex" in terms
        or "route failures" in lower_query
        or "first commands" in lower_query
        or "wasted time" in lower_query
    ):
        add(
            "skills",
            "agent_session_diagnostics",
            0.91,
            "Task mentions recent agent/session/route behavior; use the diagnostic substrate skill.",
            source_kind="task_anchor",
            facet="agent_path_telemetry",
        )
        add(
            "skills",
            "navigation_metabolism",
            0.9,
            "Navigation behavior complaints should enter the metabolism ledger before raw session dumps.",
            source_kind="task_anchor",
            facet="surface_debt_ratchet",
        )
    if (
        "entrypoint" in terms
        or "startup" in terms
        or "instruction" in terms
        or "instructions" in terms
        or "agents.md" in lower_query
        or "route health" in lower_query
        or "old routes" in lower_query
    ):
        add(
            "skills",
            "navigation_metabolism",
            0.92,
            "Entrypoint budget and route-health work belongs in the unified metabolism ledger.",
            source_kind="task_anchor",
            facet="entrypoint_health",
        )
    if (
        "terminal" in terms
        and ({"observation", "observations", "shrinking", "compression", "context"} & terms)
    ):
        add(
            "annex_prior_art",
            "arxiv-2604-19572",
            0.88,
            "Indexed TACO prior-art annex for terminal-agent observational context compression.",
            source_kind="annex_catalog",
            facet="context_compression",
        )

    rows = sorted(best.values(), key=lambda item: (-float(item["score"]), item["kind_id"], item["id"]))
    return rows[:DEFAULT_SELECTED_LIMIT]


def _suppress_python_unresolved_for_workitem_hints(
    python_target_resolution: Mapping[str, Any],
    workitem_target_resolution: Mapping[str, Any],
) -> dict[str, Any]:
    detected = (
        workitem_target_resolution.get("detected")
        if isinstance(workitem_target_resolution.get("detected"), Mapping)
        else {}
    )
    work_item_ids = {
        str(item)
        for item in list(detected.get("work_item_ids") or [])
        if str(item or "").strip()
    }
    if not work_item_ids:
        return dict(python_target_resolution)

    unresolved = [
        row
        for row in list(python_target_resolution.get("unresolved") or [])
        if isinstance(row, Mapping)
    ]
    if not unresolved:
        return dict(python_target_resolution)

    kept: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for row in unresolved:
        row_id = str(row.get("id") or "").strip()
        if str(row.get("kind") or "") == "python_scope" and row_id in work_item_ids:
            suppressed.append(dict(row))
            continue
        kept.append(dict(row))
    if not suppressed:
        return dict(python_target_resolution)

    out = dict(python_target_resolution)
    out["unresolved"] = kept
    original_detected = (
        dict(python_target_resolution.get("detected") or {})
        if isinstance(python_target_resolution.get("detected"), Mapping)
        else {}
    )
    if isinstance(original_detected.get("symbol_names"), list):
        original_detected["symbol_names"] = [
            str(item)
            for item in original_detected.get("symbol_names") or []
            if str(item) not in work_item_ids
        ]
    out["detected"] = original_detected
    out["suppressed_by_workitem_target_resolution"] = [
        {
            "id": str(row.get("id") or ""),
            "reason": "exact_workitem_id_has_stronger_task_ledger_route",
        }
        for row in suppressed
    ]
    if not out.get("files") and not out.get("scopes") and not kept:
        out["status"] = "no_python_target"
    elif kept:
        out["status"] = "unresolved"
    else:
        out["status"] = "resolved"
    return out


def _row_identity(row: Mapping[str, Any], kind_id: str) -> str:
    keys_by_kind = {
        "paper_modules": ("slug",),
        "skills": ("skill_id", "id"),
        "principles": ("principle_id", "id", "row_id"),
        "standards": ("standard_id", "id"),
        "imaginations": ("imagination_id", "slug", "id"),
        "config_authorities": ("config_id",),
        "annex_patterns": ("annex_pattern_id", "pattern_id", "id"),
        "raw_seed_shards": ("shard_id", "id"),
        "frontend_views": ("view_id", "id", "row_id"),
        "python_files": ("file_id", "path", "id", "row_id"),
        "python_scopes": ("scope_id", "symbol_id", "id", "row_id"),
    }
    for key in keys_by_kind.get(kind_id, ("id", "row_id")):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    row_id = str(row.get("row_id") or "").strip()
    if ":" in row_id:
        return row_id.split(":", 1)[1].split("::", 1)[0]
    return row_id


_AFFORDANCE_PASSPORT_FIELDS: tuple[str, ...] = (
    "cluster_keys",
    "atom",
    "when_to_open",
    "when_not_to_open",
    "safe_drilldown",
    "landmines",
    "sufficiency_claims",
)


def _passport_standard_ref(kind_id: str) -> str:
    if kind_id == "system_atlas":
        return "codex/standards/std_system_atlas.json"
    if kind_id == "skills":
        return "codex/standards/std_skill.json::compression_passport"
    return f"codex/standards/std_{kind_id.rstrip('s')}.json"


def _affordance_passport(row: Mapping[str, Any], *, kind_id: str) -> dict[str, Any]:
    """Extract the standard-owned affordance fields a row carries, without inventing.

    Reads from `row.compression_passport` first (the std_skill-owned source per
    `codex/standards/std_skill.json::compression_passport`; same shape can be
    populated on paper-module / standard rows once those standards adopt the
    passport), then falls back to top-level row fields. Values are preserved as
    is; absent fields are simply omitted so consumers can detect coverage.

    Operator B2 directive 2026-04-29: the passport is route authority, lexical
    similarity is a hint. This helper is the projection-layer guarantee that
    the affordance fields actually reach selected_rows; selector ranking by
    these fields is a separate downstream change.
    """
    passport_source = row.get("compression_passport") if isinstance(row.get("compression_passport"), Mapping) else {}
    out: dict[str, Any] = {}
    for field in _AFFORDANCE_PASSPORT_FIELDS:
        if isinstance(passport_source, Mapping) and field in passport_source and passport_source.get(field) is not None:
            out[field] = passport_source.get(field)
            continue
        if field in row and row.get(field) is not None:
            out[field] = row.get(field)
    # Skills carry a top-level `not_when` distinct from `when_not_to_open`; preserve it explicitly.
    if isinstance(row.get("not_when"), str) and row.get("not_when"):
        out["not_when"] = row.get("not_when")
    if not out:
        return {
            "status": "absent",
            "reason": (
                "kind has not adopted compression_passport authoring yet"
                if kind_id != "skills"
                else "skill row predates compression_passport migration; falls back to legacy fields"
            ),
            "owning_standard_for_passport": f"{_passport_standard_ref(kind_id)} (passport not yet authored for this kind)",
        }
    out["status"] = "present"
    out["source"] = "compression_passport" if isinstance(passport_source, Mapping) and passport_source else "row_top_level_fallback"
    out["owning_standard"] = _passport_standard_ref(kind_id)
    return out


_AFFORDANCE_GATE_STOPWORDS = CONTEXT_ANCHOR_STOPWORDS | {
    "a", "an", "as", "at", "be", "by", "i", "in", "is", "it", "me", "my",
    "need", "needs", "of", "on", "or", "so", "surface", "surfaces", "that",
    "to", "us", "we", "whether", "which", "you", "your",
}


def _gate_tokens(text: Any) -> frozenset[str]:
    parts = _query_terms(text or "")
    return frozenset(token for token in parts if token and token not in _AFFORDANCE_GATE_STOPWORDS)


def _gate_overlap_count(query_tokens: frozenset[str], target_text: Any) -> int:
    if not query_tokens or not target_text:
        return 0
    target = _gate_tokens(target_text)
    return len(query_tokens & target)


def _gate_overlap_count_array(query_tokens: frozenset[str], target_array: Any) -> int:
    if not query_tokens or not isinstance(target_array, (list, tuple, set, frozenset)):
        return 0
    total = 0
    for item in target_array:
        total += _gate_overlap_count(query_tokens, item)
    return total


def _match_terms(text: Any) -> frozenset[str]:
    terms = re.split(r"[^a-z0-9]+", str(text or "").casefold())
    return frozenset(term for term in terms if term and term not in _AFFORDANCE_GATE_STOPWORDS)


def _query_matched_standard_validation_rules(
    repo_root: Path,
    row: Mapping[str, Any],
    query: str,
    *,
    limit: int = 4,
) -> list[str]:
    query_terms = _match_terms(query)
    if not query_terms:
        return []
    source_ref = str(row.get("source_ref") or "")
    if not source_ref.endswith(".json"):
        return []
    payload = _load_json(repo_root / source_ref)
    validation_rules = _standard_validation_rule_texts(payload)
    if not validation_rules:
        return []
    top_rules = {str(rule) for rule in row.get("top_validation_rules") or []}
    matches: list[tuple[int, int, str]] = []
    for rule in validation_rules:
        text = str(rule)
        if text in top_rules:
            continue
        overlap = len(query_terms & _match_terms(text))
        if overlap < 2:
            continue
        matches.append((-overlap, len(matches), text))
    matches.sort()
    return [text for _, _, text in matches[:limit]]


def _affordance_compatibility(
    selected_row: Mapping[str, Any],
    *,
    query_tokens: frozenset[str],
) -> dict[str, Any]:
    """Compute the typed affordance compatibility bucket for one selected row.

    Operator B2 directive 2026-04-29: when_not_to_open / not_when must beat
    semantic relevance; when_to_open / cluster_keys must boost; absent passport
    must demote (the affordance fields are authority, lexical/semantic is hint).

    Buckets (lower wins in the sort key):
      0 = strong_affordance_match
      1 = neutral_or_no_passport
      2 = weak_or_schema_absent
      3 = anti_trigger_match
    """
    selected_by_context_anchor = (
        str(selected_row.get("selection_source_kind") or "") == "skill_registry_context_pack_anchor"
    )
    selected_by_root_navigator_anchor = (
        str(selected_row.get("selection_source_kind") or "") == "root_navigator_ai_native_anchor"
    )
    selected_by_workitem_anchor = (
        str(selected_row.get("selection_source_kind") or "") == "workitem_target_resolution"
    )
    passport = selected_row.get("affordance_passport") or {}
    if not isinstance(passport, Mapping):
        passport = {}
    status = str(passport.get("status") or "")
    if status == "absent":
        if selected_by_workitem_anchor:
            return {
                "compatibility_bucket": 0,
                "compatibility_label": "strong_workitem_target_match",
                "affordance_boost": 1.0,
                "anti_trigger_overlap": 0,
                "landmine_overlap": 0,
                "positive_trigger_overlap": 0,
                "reason": "row selected by exact Task Ledger WorkItem id target resolution",
            }
        if selected_by_root_navigator_anchor:
            return {
                "compatibility_bucket": 0,
                "compatibility_label": "strong_root_navigator_ai_native_anchor_match",
                "affordance_boost": 1.0,
                "anti_trigger_overlap": 0,
                "landmine_overlap": 0,
                "positive_trigger_overlap": 0,
                "reason": "row selected by Root Navigator AI-native context anchor",
            }
        if selected_by_context_anchor:
            return {
                "compatibility_bucket": 0,
                "compatibility_label": "strong_context_anchor_match",
                "affordance_boost": 1.0,
                "anti_trigger_overlap": 0,
                "landmine_overlap": 0,
                "positive_trigger_overlap": 0,
                "reason": "row selected by standard-owned skill_registry context_pack_anchors",
            }
        return {
            "compatibility_bucket": 2,
            "compatibility_label": "weak_or_schema_absent",
            "affordance_boost": 0.0,
            "anti_trigger_overlap": 0,
            "landmine_overlap": 0,
            "positive_trigger_overlap": 0,
            "reason": "row carries no compression_passport (kind has not adopted authoring)",
        }
    when_to_open = passport.get("when_to_open")
    when_not_to_open = passport.get("when_not_to_open")
    not_when = passport.get("not_when")
    cluster_keys = passport.get("cluster_keys")
    summary = selected_row.get("summary")

    pos_overlap = (
        _gate_overlap_count(query_tokens, when_to_open)
        + _gate_overlap_count_array(query_tokens, cluster_keys)
        + (_gate_overlap_count(query_tokens, summary) // 2)
    )
    neg_overlap = _gate_overlap_count(query_tokens, when_not_to_open) + _gate_overlap_count(query_tokens, not_when)
    # Landmines are diagnostic warnings / anti-pattern receipts. They must not
    # demote a row by themselves: a diagnostic skill often names the exact bad
    # behavior it is meant to catch. True route exclusion remains owned by
    # when_not_to_open and top-level not_when.
    landmine_overlap = _gate_overlap_count_array(query_tokens, passport.get("landmines"))

    if neg_overlap > 0 and neg_overlap >= pos_overlap:
        return {
            "compatibility_bucket": 3,
            "compatibility_label": "anti_trigger_match",
            "affordance_boost": 0.0,
            "anti_trigger_overlap": neg_overlap,
            "landmine_overlap": landmine_overlap,
            "positive_trigger_overlap": pos_overlap,
            "reason": "query overlaps when_not_to_open / not_when as strongly as when_to_open",
        }
    if selected_by_context_anchor:
        return {
            "compatibility_bucket": 0,
            "compatibility_label": "strong_context_anchor_match",
            "affordance_boost": 1.0,
            "anti_trigger_overlap": neg_overlap,
            "landmine_overlap": landmine_overlap,
            "positive_trigger_overlap": pos_overlap,
            "reason": "row selected by standard-owned skill_registry context_pack_anchors",
        }
    if selected_by_root_navigator_anchor:
        return {
            "compatibility_bucket": 0,
            "compatibility_label": "strong_root_navigator_ai_native_anchor_match",
            "affordance_boost": 1.0,
            "anti_trigger_overlap": neg_overlap,
            "landmine_overlap": landmine_overlap,
            "positive_trigger_overlap": pos_overlap,
            "reason": "row selected by Root Navigator AI-native context anchor",
        }
    if selected_by_workitem_anchor:
        return {
            "compatibility_bucket": 0,
            "compatibility_label": "strong_workitem_target_match",
            "affordance_boost": 1.0,
            "anti_trigger_overlap": neg_overlap,
            "landmine_overlap": landmine_overlap,
            "positive_trigger_overlap": pos_overlap,
            "reason": "row selected by exact Task Ledger WorkItem id target resolution",
        }
    if pos_overlap > 0:
        boost = float(min(pos_overlap, 6)) / 6.0
        return {
            "compatibility_bucket": 0,
            "compatibility_label": "strong_affordance_match",
            "affordance_boost": round(boost, 4),
            "anti_trigger_overlap": neg_overlap,
            "landmine_overlap": landmine_overlap,
            "positive_trigger_overlap": pos_overlap,
            "reason": "query overlaps when_to_open or cluster_keys at row's compression_passport",
        }
    return {
        "compatibility_bucket": 1,
        "compatibility_label": "neutral_or_no_passport",
        "affordance_boost": 0.0,
        "anti_trigger_overlap": neg_overlap,
        "landmine_overlap": landmine_overlap,
        "positive_trigger_overlap": pos_overlap,
        "reason": "passport present but no positive overlap with when_to_open / cluster_keys",
    }


def _compact_option_row(
    row: Mapping[str, Any],
    *,
    kind_id: str,
    score: float,
    reason: str,
) -> dict[str, Any]:
    row_id = _row_identity(row, kind_id)
    title = row.get("title") or row.get("name") or row.get("canonical_label") or row.get("slug") or row.get("skill_id") or row_id
    summary = (
        row.get("claim")
        or row.get("summary")
        or row.get("description")
        or row.get("stored_default_current_effective_semantics")
        or row.get("mutability_class")
        or row.get("tldr_excerpt")
        or row.get("purpose_or_intent")
        or row.get("flag")
    )
    drilldown = (
        row.get("drilldown_command")
        or (row.get("owner_routes") or {}).get("entry_command")
        or (row.get("omission_receipt") or {}).get("drilldown")
        or row.get("evidence_command")
    )
    debug_trace = row.get("debug_trace_command")
    evidence_command = row.get("evidence_command")
    if isinstance(evidence_command, str) and "--skill-find" in evidence_command and "--debug" not in evidence_command:
        debug_trace = f"{evidence_command} --debug"
        evidence_command = None
    card_drilldown = f"./repo-python kernel.py --option-surface {kind_id} --band card --ids {row_id}"
    result: dict[str, Any] = {
        "kind_id": kind_id,
        "row_id": row_id,
        "title": _trim(title, max_chars=140),
        "selected_band": str(row.get("band") or "card"),
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(score), 6),
        "reason": _trim(reason, max_chars=260),
        "summary": _trim(summary, max_chars=360),
        "source_ref": row.get("source_ref") or row.get("file") or row.get("registry_ref") or row.get("authority_path"),
        "drilldown_command": drilldown or card_drilldown,
        "evidence_command": evidence_command,
        "debug_trace_command": debug_trace,
        "cost_estimate_tokens": max(24, (_json_bytes(dict(row)) + 15) // 16),
        "affordance_passport": _affordance_passport(row, kind_id=kind_id),
    }
    if isinstance(row.get("currentness"), Mapping):
        currentness = dict(row.get("currentness") or {})
        if kind_id == "system_atlas":
            result["currentness"] = {
                key: currentness.get(key)
                for key in (
                    "status",
                    "source_coupling_status",
                    "changed_source_count",
                    "safe_to_commit_generated_outputs_without_sources",
                )
                if key in currentness
            }
        else:
            result["currentness"] = currentness
    if isinstance(row.get("nearest_standard"), Mapping):
        result["nearest_standard"] = dict(row.get("nearest_standard") or {})
    if isinstance(row.get("omission_receipt"), Mapping):
        result["omission_receipt"] = dict(row.get("omission_receipt") or {})
    if kind_id == "compression_profiles":
        if isinstance(row.get("owner_routes"), Mapping):
            owner_routes = dict(row.get("owner_routes") or {})
            result["owner_routes"] = owner_routes
            result["route_summary"] = {
                "has_refresh_command": bool(owner_routes.get("refresh_command")),
                "has_check_command": bool(owner_routes.get("check_command")),
                "has_status_command": bool(owner_routes.get("status_command")),
                "has_root_drilldown_command": bool(owner_routes.get("root_drilldown_command")),
            }
        if isinstance(row.get("render_profile"), Mapping):
            render_profile = dict(row.get("render_profile") or {})
            result["render_profile"] = {
                key: render_profile.get(key)
                for key in (
                    "output_path",
                    "last_green_output_path",
                    "operator_packet_path",
                    "status_sidecar_path",
                    "source_model",
                    "root_slug",
                    "authority_contract_path",
                    "projection_not_authority",
                    "refresh_owner",
                    "authority_boundary",
                )
                if key in render_profile
            }
        if isinstance(row.get("sibling_profiles"), list):
            result["sibling_profiles"] = [
                dict(sibling)
                for sibling in row.get("sibling_profiles") or []
                if isinstance(sibling, Mapping)
            ][:8]
        if isinstance(row.get("sibling_profile_summary"), Mapping):
            result["sibling_profile_summary"] = dict(row.get("sibling_profile_summary") or {})
        result["context_pack_contract"] = {
            "role": "COMPRESSION_PROFILE_CARD",
            "native_band": "compression_profile_card",
            "source_bodies_omitted": True,
            "allowed_payload": "Profile identity, render-profile boundary, owner routes, sibling render-profile bridge, currentness, omission receipt, and source registry drilldown.",
            "forbidden_payload": "treating generated packet output as source authority or assigning Type A refresh/check work to the Type B receiver.",
            "entry_consumption_obligation": "Render-profile packets selected by context-pack should expose owner_routes and sibling profile bridges so agents do not rediscover refresh, status, and source-authority commands from prompt prose.",
        }
    if isinstance(row.get("next_safe_moves"), list):
        result["next_safe_moves"] = [
            str(command)
            for command in row.get("next_safe_moves") or []
            if str(command or "").strip()
        ][:8]
    if kind_id == "task_ledger":
        if isinstance(row.get("source_refs"), list):
            result["source_refs"] = list(row.get("source_refs") or [])[:8]
        if row.get("state"):
            result["state"] = row.get("state")
        if row.get("work_item_type") or row.get("candidate_work_item_type"):
            result["work_item_type"] = row.get("work_item_type") or row.get("candidate_work_item_type")
        if isinstance(row.get("dependency_status"), Mapping):
            result["dependency_status"] = dict(row.get("dependency_status") or {})
        if isinstance(row.get("contracts"), Mapping):
            result["contracts"] = dict(row.get("contracts") or {})
        result["context_pack_contract"] = {
            "role": "WORKITEM_CARD",
            "native_band": "task_ledger_card",
            "source_bodies_omitted": True,
            "allowed_payload": "Task Ledger card, state, statement summary, contracts, dependency status, source refs, and drilldown commands",
            "forbidden_payload": "direct projection edits, raw event-chain expansion, or substituting adjacent skill cards for the owning WorkItem",
            "entry_consumption_obligation": "Exact WorkItem IDs in task text should reach selected_rows before supplemental skills, docs, or source reads.",
            "failure_route": "Missing or stale IDs are reported by workitem_target_resolution and route to Task Ledger cluster/rebuild lanes.",
        }
    if kind_id == "python_files":
        result["context_pack_contract"] = {
            "role": "PYTHON_FILE_CARD",
            "native_band": "file_card",
            "source_bodies_omitted": True,
            "allowed_payload": "std_python file card, public symbol handles, currentness, omission receipt, and source/compile drilldowns",
            "forbidden_payload": "full source body, direct mutation, or unproven subsystem-wide claims",
            "entry_consumption_obligation": "Exact file mentions in task text should reach selected_rows before source reads.",
        }
        result["provider_population_gap_route"] = "./repo-python kernel.py --option-surface row_patches --band cluster_flag"
        result["provider_population_lane_command"] = (
            "./repo-python tools/meta/control/python_navigation_population_lane.py select --limit 3 --gap-kind both"
        )
        result["provider_boundary"] = "row_patch_candidate_only_no_direct_mutation"
    if kind_id == "python_scopes":
        result["context_pack_contract"] = {
            "role": "PYTHON_SYMBOL_CAPSULE",
            "native_band": "symbol_capsule",
            "graph_context_available": bool(
                row.get("callee_refs") or row.get("inbound_dependents") or row.get("related_symbols")
            ),
            "source_bodies_omitted": True,
            "allowed_payload": "std_python scope card, signature, line span, local routing atoms, graph hints, and parent file command",
            "forbidden_payload": "blind body summary, direct mutation, or file/subsystem role claims not carried by the packet",
            "entry_consumption_obligation": "Exact function/class/method mentions in task text should reach selected_rows as scope cards.",
        }
        result["provider_population_gap_route"] = "./repo-python kernel.py --option-surface row_patches --band cluster_flag"
        result["provider_population_lane_command"] = (
            "./repo-python tools/meta/control/python_navigation_population_lane.py select --limit 3 --gap-kind both"
        )
        result["provider_boundary"] = "row_patch_candidate_only_no_direct_mutation"
        if isinstance(row.get("source_span"), Mapping):
            result["source_span"] = dict(row.get("source_span") or {})
        if row.get("parent_file_command"):
            result["parent_file_command"] = row.get("parent_file_command")
    if kind_id == "system_atlas":
        result["context_pack_contract"] = {
            "role": "CONTROL_PLANE_DRILLDOWN",
            "full_graph_omitted": True,
            "allowed_payload": "selected atlas card, omission receipt, authority/disclosure cues, and drilldown commands",
            "forbidden_payload": "entities[], edges[], full findings[], private state, or source bodies",
        }
    if kind_id == "frontend_views" and row_id == "rootNavigator":
        result["context_pack_contract"] = {
            "role": "ROOT_NAVIGATOR_AI_NATIVE_DRILLDOWN",
            "view_agent_packet_required": True,
            "constitutional_atlas_required": True,
            "allowed_payload": "rootNavigator frontend view card, typed view-agent packet command, constitutional atlas receipt, screenshot/currentness evidence, and Claude handoff command",
            "forbidden_payload": "frontend-invented ontology, generated-image facts, full TSX bodies, raw JSON as default operator content, or runtime counts without freshness receipt",
        }
        result["ai_native_view_packet"] = {
            "schema": "root_navigator_ai_native_view_packet_pointer_v0",
            "view_id": "rootNavigator",
            "view_agent_packet_command": "./repo-python kernel.py --view-agent-packet rootNavigator",
            "claude_handoff_packet_command": "./repo-python kernel.py --root-navigator-handoff",
            "constitutional_atlas_ref": "docs/dissemination/station_view_direction_specs/root_navigator_constitutional_atlas.json",
            "frontend_view_card_command": "./repo-python kernel.py --option-surface frontend_views --band card --ids rootNavigator",
            "authority_boundary": "Use the view-agent packet and Constitutional Atlas as navigation/handoff context; do not infer ontology from screenshots or TSX.",
        }
    if kind_id == "paper_modules" and row_id in PAPER_LATTICE_SUPPORTED_SLUGS:
        lattice_command = f"./repo-python kernel.py --paper-lattice {row_id} --band card --context-budget 12000"
        result["drilldowns"] = {
            "card": card_drilldown,
            "lattice": lattice_command,
            "evidence": f"./repo-python kernel.py --paper-module {row_id}",
        }
        result["paper_lattice"] = {
            "status": "supported_exemplar",
            "command": lattice_command,
            "entry_condition": "stable paper-module slug selected by context-pack or paper_modules cluster/card surface",
            "not_yet_generic": True,
        }
    return result


def _selected_python_target_row(candidate: Mapping[str, Any], *, kind_id: str) -> dict[str, Any] | None:
    """Render exact Python target candidates without reopening the full option surface."""
    packet = candidate.get("target_packet")
    if not isinstance(packet, Mapping):
        return None
    if kind_id == "python_files":
        path = str(packet.get("path") or candidate.get("id") or "").strip()
        if not path:
            return None
        scope_count = packet.get("scope_count")
        public_symbol_count = packet.get("public_symbol_count")
        option_row: dict[str, Any] = {
            "file_id": path,
            "path": path,
            "title": path,
            "band": packet.get("native_band") or "file_card",
            "summary": (
                f"Resolved Python file target from task text; scope_count={scope_count or 0}, "
                f"public_symbol_count={public_symbol_count or 0}."
            ),
            "source_ref": packet.get("source_ref") or "codex/standards/std_python_scope_index.json",
            "drilldown_command": packet.get("card_command")
            or f"./repo-python kernel.py --option-surface python_files --band card --ids {path}",
            "evidence_command": f"./repo-python kernel.py --compile {path}",
            "currentness": dict(packet.get("projection_currentness") or {})
            if isinstance(packet.get("projection_currentness"), Mapping)
            else {},
            "nearest_standard": {
                "ref": "codex/standards/std_python.py",
                "why": "The Python scope index governs file-card navigation before source reads.",
            },
            "omission_receipt": {
                "omitted": [
                    "full Python source body",
                    "full symbol list",
                    "cross-file dependency closure",
                ],
                "reason": "Context-pack already resolved the exact file handle; use the Python option-surface card when richer generated metadata is needed.",
                "drilldown": packet.get("card_command")
                or f"./repo-python kernel.py --option-surface python_files --band card --ids {path}",
            },
        }
    elif kind_id == "python_scopes":
        scope_id = str(packet.get("scope_id") or packet.get("symbol_id") or candidate.get("id") or "").strip()
        if not scope_id:
            return None
        path = str(packet.get("path") or "").strip()
        name = str(packet.get("name") or scope_id).strip()
        source_span = packet.get("source_span") if isinstance(packet.get("source_span"), Mapping) else {}
        line_start = source_span.get("line_start") if isinstance(source_span, Mapping) else None
        line_end = source_span.get("line_end") if isinstance(source_span, Mapping) else None
        option_row = {
            "scope_id": scope_id,
            "symbol_id": packet.get("symbol_id") or scope_id,
            "title": f"{name} ({path})" if path else name,
            "name": name,
            "band": packet.get("native_band") or "symbol_capsule",
            "summary": (
                f"Resolved Python {packet.get('scope_kind') or 'scope'} target in {path}"
                + (f" at lines {line_start}-{line_end}." if line_start else ".")
            ),
            "source_ref": packet.get("source_ref") or "codex/standards/std_python_scope_index.json",
            "drilldown_command": packet.get("card_command")
            or f"./repo-python kernel.py --option-surface python_scopes --band card --ids {scope_id}",
            "evidence_command": packet.get("parent_file_command"),
            "currentness": dict(packet.get("projection_currentness") or {})
            if isinstance(packet.get("projection_currentness"), Mapping)
            else {},
            "nearest_standard": {
                "ref": "codex/standards/std_python.py",
                "why": "The Python scope index governs symbol-capsule navigation before source reads.",
            },
            "omission_receipt": {
                "omitted": [
                    "full Python source body",
                    "complete caller/callee neighborhood",
                    "unbounded source span text",
                ],
                "reason": "Context-pack already resolved the exact symbol handle; use the Python option-surface card when richer generated metadata is needed.",
                "drilldown": packet.get("card_command")
                or f"./repo-python kernel.py --option-surface python_scopes --band card --ids {scope_id}",
            },
            "source_span": dict(source_span) if isinstance(source_span, Mapping) else {},
            "parent_file_command": packet.get("parent_file_command"),
        }
    else:
        return None

    compact = _compact_option_row(
        option_row,
        kind_id=kind_id,
        score=float(candidate.get("score") or 0.0),
        reason=str(candidate.get("reason") or "Python target resolution"),
    )
    source_kind = str(candidate.get("source_kind") or "")
    if source_kind:
        compact["selection_source_kind"] = source_kind
    facet = str(candidate.get("facet") or "")
    if facet:
        compact["selection_facet"] = facet
    return compact


def _selected_rows(
    repo_root: Path,
    candidates: list[dict[str, Any]],
    *,
    query: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_kind: dict[str, list[dict[str, Any]]] = {}
    selected: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    for candidate in candidates:
        by_kind.setdefault(str(candidate["kind_id"]), []).append(candidate)

    for kind_id, rows in by_kind.items():
        if kind_id == "annex_prior_art":
            for candidate in rows:
                selected.append(
                    {
                        "kind_id": "annex_prior_art",
                        "row_id": candidate["id"],
                        "title": "A Self-Evolving Framework for Efficient Terminal Agents via Observational Context Compression",
                        "selected_band": "catalog_card",
                        "relevance": candidate["score"],
                        "reason": candidate["reason"],
                        "summary": "Prior-art annex on terminal-agent observation compression and adaptive rule evolution.",
                        "source_ref": f"annexes/{candidate['id']}",
                        "drilldown_command": './repo-python kernel.py --annex-search "context compression"',
                        "evidence_command": './repo-python kernel.py --annex-search "context compression"',
                        "cost_estimate_tokens": 120,
                    }
                )
            continue
        if kind_id == "derived_facts":
            for candidate in rows:
                selected.append(_state_axis_artifact_selected_row(repo_root, candidate))
            continue
        if kind_id == "system_crystal":
            for candidate in rows:
                selected.append(_system_crystal_selected_row(repo_root, candidate))
            continue
        if kind_id == "dissemination_gate":
            for candidate in rows:
                selected.append(_dissemination_gate_selected_row(repo_root, candidate))
            continue
        if kind_id == "prompt_shelf_metadata":
            for candidate in rows:
                selected.append(_prompt_shelf_metadata_selected_row(repo_root, candidate))
            continue
        if kind_id == "operator_thread_continuation_card":
            for candidate in rows:
                selected.append(_operator_thread_continuation_card_selected_row(repo_root, candidate))
            continue
        if kind_id == "type_a_autonomous_seeds":
            for candidate in rows:
                selected.append(_type_a_autonomous_seed_selected_row(repo_root, candidate))
            continue
        if kind_id == "workitem_spine":
            for candidate in rows:
                selected.append(_workitem_spine_selected_row(repo_root, candidate))
            continue
        if kind_id == "generated_projection_ownership":
            for candidate in rows:
                selected.append(_generated_projection_owner_selected_row(repo_root, candidate))
            continue
        if kind_id == "external_benchmark_calibration":
            for candidate in rows:
                selected.append(_external_benchmark_calibration_selected_row(repo_root, candidate))
            continue
        if kind_id in {"python_files", "python_scopes"}:
            unresolved_python_rows: list[dict[str, Any]] = []
            for candidate in rows:
                compact = _selected_python_target_row(candidate, kind_id=kind_id)
                if compact is None:
                    unresolved_python_rows.append(candidate)
                else:
                    selected.append(compact)
            if not unresolved_python_rows:
                continue
            rows = unresolved_python_rows

        ids = [str(row["id"]) for row in rows]
        payload = build_option_surface(repo_root, kind_id, band="card", ids=ids)
        option_rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
        score_by_id = {str(row["id"]): float(row.get("score") or 0.0) for row in rows}
        reason_by_id = {str(row["id"]): str(row.get("reason") or "") for row in rows}
        source_kind_by_id = {str(row["id"]): str(row.get("source_kind") or "") for row in rows}
        facet_by_id = {str(row["id"]): str(row.get("facet") or "") for row in rows}
        seen: set[str] = set()
        for option_row in option_rows:
            if not isinstance(option_row, Mapping):
                continue
            row_id = _row_identity(option_row, kind_id)
            candidate_id = row_id
            if kind_id == "annex_patterns":
                candidate_id = row_id.replace("::", ":")
            elif kind_id == "compression_profiles" and row_id.startswith("compression_profile:"):
                candidate_id = row_id.removeprefix("compression_profile:").removesuffix("::card")
            score = score_by_id.get(candidate_id, score_by_id.get(row_id, 0.5))
            reason = reason_by_id.get(candidate_id, reason_by_id.get(row_id, "selected option row"))
            compact = _compact_option_row(option_row, kind_id=kind_id, score=score, reason=reason)
            if kind_id == "standards":
                matched_rules = _query_matched_standard_validation_rules(repo_root, option_row, query)
                if matched_rules:
                    compact["matched_validation_rules"] = matched_rules
            source_kind = source_kind_by_id.get(candidate_id, source_kind_by_id.get(row_id, ""))
            if source_kind:
                compact["selection_source_kind"] = source_kind
            facet = facet_by_id.get(candidate_id, facet_by_id.get(row_id, ""))
            if facet:
                compact["selection_facet"] = facet
            selected.append(compact)
            seen.add(candidate_id)
            seen.add(row_id)
        missing = [row for row in rows if str(row["id"]) not in seen]
        for row in missing:
            omitted.append(
                {
                    "kind_id": kind_id,
                    "row_id": row["id"],
                    "reason": "candidate did not resolve through the option-surface card adapter",
                    "safe_drilldown": f"./repo-python kernel.py --option-surface {kind_id} --band card --ids {row['id']}",
                }
            )
    # Affordance-first routing (operator B2 directive 2026-04-29; pri_pending):
    # the standard-owned compression_passport fields are routing authority;
    # lexical/semantic similarity is candidate-proposal hint only. Compute the
    # typed compatibility bucket per row and sort by it before relevance
    # within bucket. when_not_to_open / not_when must beat a
    # textually similar candidate that says "not for this situation."
    query_tokens = _gate_tokens(query)
    for row in selected:
        if str(row.get("kind_id") or "") == "derived_facts":
            row.setdefault(
                "affordance_compatibility",
                {
                    "compatibility_bucket": 0,
                    "compatibility_label": "state_axis_artifact_anchor",
                    "affordance_boost": 1.0,
                    "anti_trigger_overlap": 0,
                    "positive_trigger_overlap": 1,
                    "reason": "State-axis query matched generated fact artifact trigger.",
                },
            )
            continue
        if str(row.get("kind_id") or "") == "annex_prior_art":
            row["affordance_compatibility"] = {
                "compatibility_bucket": 1,
                "compatibility_label": "neutral_or_no_passport",
                "affordance_boost": 0.0,
                "anti_trigger_overlap": 0,
                "positive_trigger_overlap": 0,
                "reason": "annex prior-art catalog row; passport authoring is not in scope for this kind",
            }
            continue
        if str(row.get("kind_id") or "") == "system_crystal":
            row["affordance_compatibility"] = {
                "compatibility_bucket": 0,
                "compatibility_label": "system_crystal_protocol_anchor",
                "affordance_boost": 1.0,
                "anti_trigger_overlap": 0,
                "positive_trigger_overlap": 1,
                "reason": "System Crystal query matched the private generated self-model anchor.",
            }
            continue
        if str(row.get("kind_id") or "") == "dissemination_gate":
            row["affordance_compatibility"] = {
                "compatibility_bucket": 0,
                "compatibility_label": "public_safe_dissemination_gate_anchor",
                "affordance_boost": 1.0,
                "anti_trigger_overlap": 0,
                "positive_trigger_overlap": 1,
                "reason": "Public-safe dissemination query matched the atlas-ref/disclosure gate anchor.",
            }
            continue
        if str(row.get("kind_id") or "") == "prompt_shelf_metadata":
            row["affordance_compatibility"] = {
                "compatibility_bucket": 0,
                "compatibility_label": "prompt_shelf_metadata_anchor",
                "affordance_boost": 1.0,
                "anti_trigger_overlap": 0,
                "positive_trigger_overlap": 1,
                "reason": "Prompt-shelf or Type B reasoning-extraction query matched the metadata-only owner route.",
            }
            continue
        if str(row.get("kind_id") or "") == "workitem_spine":
            row["affordance_compatibility"] = {
                "compatibility_bucket": 0,
                "compatibility_label": "workitem_spine_anchor",
                "affordance_boost": 1.25,
                "anti_trigger_overlap": 0,
                "positive_trigger_overlap": 1,
                "reason": "Task Ledger / Work Ledger / CAP query matched the operational spine owner route.",
            }
            continue
        if str(row.get("kind_id") or "") == "generated_projection_ownership":
            row["affordance_compatibility"] = {
                "compatibility_bucket": 0,
                "compatibility_label": "generated_projection_owner_anchor",
                "affordance_boost": 1.3,
                "anti_trigger_overlap": 0,
                "positive_trigger_overlap": 1,
                "reason": "Generated projection ownership/currentness query matched the source-coupling owner route.",
            }
            continue
        row["affordance_compatibility"] = _affordance_compatibility(row, query_tokens=query_tokens)
    selected.sort(
        key=lambda row: (
            int((row.get("affordance_compatibility") or {}).get("compatibility_bucket", 1)),
            -float((row.get("affordance_compatibility") or {}).get("affordance_boost", 0.0)),
            -float(row["relevance"]),
            row["kind_id"],
            row["row_id"],
        )
    )
    return selected[:DEFAULT_SELECTED_LIMIT], omitted


def _state_axis_artifact_selected_row(repo_root: Path, candidate: Mapping[str, Any]) -> dict[str, Any]:
    cache = _load_json(repo_root / FACT_NAVIGATION_CACHE)
    summary = cache.get("summary") if isinstance(cache.get("summary"), Mapping) else {}
    tag_count = len(cache.get("tag_index") or []) if isinstance(cache.get("tag_index"), list) else 0
    facet_count = len(cache.get("facet_index") or []) if isinstance(cache.get("facet_index"), list) else 0
    family_count = len(cache.get("fact_family_index") or []) if isinstance(cache.get("fact_family_index"), list) else 0
    return {
        "kind_id": "derived_facts",
        "row_id": "state_axis_artifact",
        "title": "Generated State-Axis Artifact",
        "selected_band": "cluster_flag",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 0.997), 6),
        "reason": _trim(str(candidate.get("reason") or "state-axis artifact anchor"), max_chars=260),
        "summary": (
            "Compressed fact/state contents page over generated fact rows: "
            f"{summary.get('fact_count', 0)} facts, {tag_count} tags, {facet_count} facets, {family_count} families."
        ),
        "source_ref": str(FACT_NAVIGATION_CACHE),
        "drilldown_command": "./repo-python kernel.py --facts --band cluster_flag",
        "evidence_command": "./repo-python tools/meta/factory/build_fact_hologram.py --check",
        "debug_trace_command": None,
        "cost_estimate_tokens": 120,
        "selection_source_kind": str(candidate.get("source_kind") or "state_axis_artifact_anchor"),
        "selection_facet": str(candidate.get("facet") or "state_axis_overview"),
        "currentness": {
            "status": str(cache.get("artifact_role") or "generated_state_axis_artifact"),
            "generated_at": str(cache.get("generated_at") or ""),
            "source_refs_checked": [
                str(FACT_NAVIGATION_CACHE),
                str(FACT_LEDGER),
                str(FACT_AUDIT),
                str(FACT_REGISTRY),
                str(FACT_STANDARD),
            ],
        },
        "context_pack_contract": {
            "role": "STATE_AXIS_DRILLDOWN",
            "full_cache_omitted": True,
            "allowed_payload": "summary counts, source refs, drilldown commands, and artifact currentness",
            "forbidden_payload": "full fact rows, raw provider payloads, private bodies, or complete cache indexes",
        },
        "omission_receipt": {
            "omitted": ["full navigation_cache rows/indexes", "full fact ledger rows", "raw source payloads"],
            "reason": "Context-pack selects the generated state-axis artifact; --facts is the accessor for row/index expansion.",
            "drilldown": "./repo-python kernel.py --facts --band cluster_flag",
        },
        "state_axis_packet": {
            "question_class": "system_state_axis_overview",
            "artifact_role": cache.get("artifact_role") or "generated_state_axis_artifact",
            "drilldowns": [
                "./repo-python kernel.py --facts --band cluster_flag",
                "./repo-python kernel.py --fact-audit",
            ],
        },
        "affordance_compatibility": {
            "compatibility_bucket": 0,
            "compatibility_label": "state_axis_artifact_anchor",
            "affordance_boost": 1.0,
            "anti_trigger_overlap": 0,
            "positive_trigger_overlap": 1,
            "reason": "State-axis query matched generated fact artifact trigger.",
        },
    }


def _dissemination_gate_selected_row(repo_root: Path, candidate: Mapping[str, Any]) -> dict[str, Any]:
    report = repo_root / "docs/system_atlas/dissemination_gate_report.generated.md"
    report_json = repo_root / "state/system_atlas/dissemination_gate_report.json"
    disclosure_map = repo_root / "docs/system_atlas/disclosure_projection_map.md"
    readiness_audit = repo_root / "docs/dissemination/public_leaf_readiness_audit.md"
    required_paths = [report, report_json, disclosure_map, readiness_audit]
    status = "available_unverified_freshness" if all(path.exists() for path in required_paths) else "missing_outputs"
    return {
        "kind_id": "dissemination_gate",
        "row_id": "public_safe_atlas_gate_v1",
        "title": "Public-Safe Dissemination Atlas Gate",
        "selected_band": "generated_gate_card",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 1.0), 6),
        "reason": _trim(str(candidate.get("reason") or "public-safe dissemination gate anchor"), max_chars=260),
        "summary": (
            "Owner route for public-safe dissemination claim grounding: atlas ids, capability ids, "
            "disclosure posture, safe artifact routes, readiness audit, and no-send boundaries."
        ),
        "source_ref": "docs/system_atlas/dissemination_gate_report.generated.md",
        "source_refs": [
            "docs/system_atlas/dissemination_gate_report.generated.md",
            "state/system_atlas/dissemination_gate_report.json",
            "docs/system_atlas/disclosure_projection_map.md",
            "docs/dissemination/public_leaf_readiness_audit.md",
        ],
        "drilldown_command": "./repo-python tools/meta/factory/check_dissemination_atlas_gate.py --check",
        "evidence_command": "./repo-python tools/meta/factory/check_dissemination_atlas_gate.py --check",
        "debug_trace_command": None,
        "cost_estimate_tokens": 150,
        "selection_source_kind": str(candidate.get("source_kind") or "public_safe_dissemination_gate_anchor"),
        "selection_facet": str(candidate.get("facet") or "atlas_ref_disclosure_gate"),
        "currentness": {
            "status": status,
            "tracked_outputs": [
                "docs/system_atlas/dissemination_gate_report.generated.md",
                "state/system_atlas/dissemination_gate_report.json",
            ],
            "supporting_surfaces": [
                "docs/system_atlas/disclosure_projection_map.md",
                "docs/dissemination/public_leaf_readiness_audit.md",
            ],
            "freshness_command": "./repo-python tools/meta/factory/check_dissemination_atlas_gate.py --check",
        },
        "nearest_standard": {
            "ref": "codex/standards/std_system_atlas.json",
            "why": "Dissemination gate rows are System Atlas disclosure/lineage projections and must preserve source authority plus public-boundary checks.",
        },
        "context_pack_contract": {
            "role": "PUBLIC_SAFE_ATLAS_GATE_DRILLDOWN",
            "safe_issue_summaries_only": True,
            "public_release_safe": False,
            "allowed_payload": "gate status, ids, issue summaries, owner/check command, disclosure map route, readiness audit route, and no-send boundary handles",
            "forbidden_payload": "raw evidence bodies, private raw voice, prompt/provider payloads, hidden reasoning, publication action, or send-ready claim without gate proof",
        },
        "omission_receipt": {
            "omitted": ["raw evidence bodies", "private-root artifacts", "recipient-specific private packets"],
            "reason": "Context-pack selects the gate owner route; gate/report/check surfaces own safe issue summaries and disclosure posture.",
            "drilldown": "./repo-python tools/meta/factory/check_dissemination_atlas_gate.py --check",
        },
    }


def _prompt_shelf_metadata_selected_row(repo_root: Path, candidate: Mapping[str, Any]) -> dict[str, Any]:
    index_tool = repo_root / "tools/meta/observability/prompt_shelf_runs_index.py"
    projection = repo_root / "state/prompt_shelf/prompt_shelf_runs_index.json"
    ledger = repo_root / "obsidian/prompt_shelf/B2 Continue Ledger.md"
    status = "available_unverified_freshness" if index_tool.exists() and projection.exists() else "missing_outputs"
    if not ledger.exists():
        status = "partial_missing_prompt_ledger"
    return {
        "kind_id": "prompt_shelf_metadata",
        "row_id": "prompt_shelf_runs_index_v1",
        "title": "Prompt-Shelf Runs Metadata Index",
        "selected_band": "metadata_owner_card",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 1.0), 6),
        "reason": _trim(str(candidate.get("reason") or "prompt-shelf metadata anchor"), max_chars=260),
        "summary": (
            "Metadata-only owner route for prompt-shelf runs, receipts, slot coverage, and Type B "
            "reasoning extraction candidates without opening raw run or raw event bodies."
        ),
        "source_ref": "tools/meta/observability/prompt_shelf_runs_index.py",
        "source_refs": [
            "tools/meta/observability/prompt_shelf_runs_index.py",
            "state/prompt_shelf/prompt_shelf_runs_index.json",
            "obsidian/prompt_shelf/B2 Continue Ledger.md",
        ],
        "drilldown_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
        "evidence_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
        "debug_trace_command": None,
        "cost_estimate_tokens": 150,
        "selection_source_kind": str(candidate.get("source_kind") or "prompt_shelf_metadata_anchor"),
        "selection_facet": str(candidate.get("facet") or "metadata_only_reasoning_extraction"),
        "currentness": {
            "status": status,
            "tracked_outputs": ["state/prompt_shelf/prompt_shelf_runs_index.json"],
            "metadata_commands": [
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage",
            ],
            "freshness_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
        },
        "nearest_standard": {
            "ref": "codex/standards/std_agent_entry_surface.json::type_b_to_type_a_handoff_framing_contract",
            "why": "Type B and prompt-shelf signals must enter Type A as bounded, operator-mediated evidence with explicit authority limits.",
        },
        "context_pack_contract": {
            "role": "PROMPT_SHELF_METADATA_EXTRACTION_DRILLDOWN",
            "metadata_only": True,
            "raw_bodies_omitted": True,
            "public_release_safe": False,
            "allowed_payload": "run ids, slots, receipt counts, coverage status, issue summaries, selected-row handles, owner commands, and WorkItem/up-propagation routes",
            "forbidden_payload": "raw run markdown, raw event JSON, prompt/provider payloads, hidden reasoning, private raw voice, or public artifact claims",
        },
        "omission_receipt": {
            "omitted": [
                "raw prompt/provider bodies",
                "raw run markdown",
                "raw event sidecars",
                "full Type B transcript text",
            ],
            "reason": "Context-pack selects metadata and owner checks only; open one governed run id only after summary/coverage selects it.",
            "drilldown": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
        },
    }


def _operator_thread_continuation_card_selected_row(
    repo_root: Path,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    _ = repo_root
    thread_id = str(candidate.get("thread_id") or candidate.get("id") or "thread_id_required").strip()
    has_thread_id = bool(thread_id and thread_id != "thread_id_required")
    evidence_command = (
        f"./repo-python tools/meta/observability/operator_thread_memory.py --continuation-card --thread {thread_id}"
        if has_thread_id
        else "./repo-python tools/meta/observability/operator_thread_memory.py --continuation-card --thread <thread_id>"
    )
    handoff_command = (
        f"./repo-python tools/meta/observability/operator_thread_memory.py --type-b-handoff-packet --thread {thread_id} --packet-format markdown"
        if has_thread_id
        else "./repo-python tools/meta/observability/operator_thread_memory.py --type-b-handoff-packet --thread <thread_id> --packet-format markdown"
    )
    return {
        "kind_id": "operator_thread_continuation_card",
        "row_id": thread_id if has_thread_id else "thread_id_required",
        "title": "Operator Thread Continuation Card",
        "selected_band": "metadata_shuttle_card",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 0.99), 6),
        "reason": _trim(
            str(candidate.get("reason") or "operator thread continuation-card anchor"),
            max_chars=260,
        ),
        "summary": (
            "Carries turn-stack, response-skeleton, receipt, and WorkItem/CAP ownership signals "
            "through context-pack without raw transcript bodies."
        ),
        "source_ref": "tools/meta/observability/operator_thread_memory.py",
        "source_refs": [
            "tools/meta/observability/operator_thread_memory.py",
            "tools/meta/observability/operator_turn_stack_projection.py",
            "state/operator_bridge/thread_memory/",
        ],
        "source_projection_boundary": "metadata_only_card_not_raw_transcript_authority",
        "owner_surface": "Operator Thread Memory",
        "owner_tool": "tools/meta/observability/operator_thread_memory.py",
        "drilldown_command": evidence_command,
        "evidence_command": evidence_command,
        "type_b_handoff_packet_command": handoff_command,
        "selection_source_kind": str(candidate.get("source_kind") or "operator_thread_continuation_card_anchor"),
        "selection_facet": str(candidate.get("facet") or "metadata_only_type_b_grounding"),
        "currentness": {
            "status": "available_unverified_freshness" if has_thread_id else "requires_thread_id",
            "freshness_command": (
                "./repo-python tools/meta/observability/operator_thread_memory.py --check"
            ),
            "card_command": evidence_command,
            "type_b_handoff_packet_command": handoff_command,
        },
        "context_pack_contract": {
            "role": "OPERATOR_THREAD_CONTINUATION_CARD",
            "metadata_only": True,
            "raw_bodies_omitted": True,
            "source_bodies_omitted": True,
            "public_release_safe": False,
            "external_type_b_render_profile": "operator_approved_external_type_b_handoff_v0",
            "allowed_payload": (
                "thread ids, hashes, block counts, receipt types, response anatomy flags, "
                "and ownership refs"
            ),
            "forbidden_payload": (
                "raw captured transcript bodies, assistant bodies, and private preview/title payload fields"
            ),
            "entry_consumption_obligation": (
                "Use the top-level operator_thread_continuation_card packet as the default Type B "
                "grounding object when a concrete operator thread id is present, then render the "
                "copyable Type B handoff packet for external web-app continuation."
            ),
        },
        "omission_receipt": {
            "omitted": ["raw captured transcript bodies", "assistant bodies", "private projection previews"],
            "reason": "Context-pack carries the continuation card only; raw drilldown stays in the private thread-memory lane.",
            "drilldown": evidence_command,
        },
    }


def _load_operator_thread_memory_module(repo_root: Path) -> Any:
    module_path = repo_root / "tools/meta/observability/operator_thread_memory.py"
    spec = importlib.util.spec_from_file_location("_aiw_operator_thread_memory_context_pack", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load operator_thread_memory.py from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _privacy_scan_operator_card(card: Mapping[str, Any]) -> dict[str, Any]:
    body = json.dumps(card, sort_keys=True, ensure_ascii=True)
    finding_count = sum(1 for marker in OPERATOR_CARD_FORBIDDEN_MARKERS if marker in body)
    return {
        "status": "clean" if finding_count == 0 else "blocked",
        "checked_marker_count": len(OPERATOR_CARD_FORBIDDEN_MARKERS),
        "finding_count": finding_count,
        "raw_payload_included": False if finding_count == 0 else None,
    }


def _operator_card_sufficiency_probe(card: Mapping[str, Any]) -> dict[str, Any]:
    summary = card.get("thread_semantic_summary") if isinstance(card.get("thread_semantic_summary"), Mapping) else {}
    block_counts = summary.get("block_type_counts") if isinstance(summary.get("block_type_counts"), Mapping) else {}
    detected_receipts = set(str(item) for item in (card.get("detected_receipt_types") or []) if item)
    recent_responses = [
        item for item in (card.get("recent_response_skeletons") or [])
        if isinstance(item, Mapping)
    ]
    anatomy_flags = {
        str(flag)
        for response in recent_responses
        for flag in ((response.get("decision_anatomy_true") or []) + (response.get("anatomy_flags") or []))
        if flag
    }
    missing: list[str] = []
    if int(block_counts.get("operator_live_addendum") or 0) <= 0:
        missing.append("operator_live_addendum")
    if not (detected_receipts & {"workitem_binding_receipt", "commit_receipt", "validation_receipt"}):
        missing.append("receipt_or_ownership_signal")
    if not anatomy_flags:
        missing.append("response_skeleton_anatomy")
    continuation_use = card.get("continuation_use") if isinstance(card.get("continuation_use"), Mapping) else {}
    if continuation_use.get("can_continue_without_raw_transcript") is not True:
        missing.append("continuation_use_contract")
    return {
        "schema_version": "operator_continuation_card_sufficiency_probe_v0",
        "status": "sufficient_for_metadata_only_shuttle" if not missing else "needs_raw_drilldown",
        "raw_trace_replacement": not missing,
        "missing": missing,
        "signals": {
            "live_addendum_count": int(block_counts.get("operator_live_addendum") or 0),
            "receipt_types": sorted(detected_receipts),
            "response_anatomy_flags": sorted(anatomy_flags),
        },
    }


def _operator_thread_continuation_card_context(repo_root: Path, query: str) -> dict[str, Any] | None:
    if not _is_operator_thread_continuation_card_query(query):
        return None
    thread_id = _operator_thread_id_from_query(query)
    if not thread_id:
        return {
            "schema_version": "operator_thread_continuation_card_context_v0",
            "status": "requires_thread_id",
            "payload_policy": "metadata_only",
            "consumer_surface": "kernel.context_pack",
            "next_command": (
                "./repo-python tools/meta/observability/operator_thread_memory.py "
                "--continuation-card --thread <thread_id>"
            ),
            "type_b_handoff_packet_command": (
                "./repo-python tools/meta/observability/operator_thread_memory.py "
                "--type-b-handoff-packet --thread <thread_id> --packet-format markdown"
            ),
        }
    try:
        thread_memory = _load_operator_thread_memory_module(repo_root)
        card = thread_memory.build_thread_continuation_card(thread_id)
    except Exception as exc:  # noqa: BLE001 - context-pack should return a receipt, not fail.
        return {
            "schema_version": "operator_thread_continuation_card_context_v0",
            "status": "unavailable",
            "payload_policy": "metadata_only",
            "consumer_surface": "kernel.context_pack",
            "thread_id": thread_id,
            "reason": f"{type(exc).__name__}: {exc}",
            "next_command": (
                f"./repo-python tools/meta/observability/operator_thread_memory.py "
                f"--continuation-card --thread {thread_id}"
            ),
            "type_b_handoff_packet_command": (
                f"./repo-python tools/meta/observability/operator_thread_memory.py "
                f"--type-b-handoff-packet --thread {thread_id} --packet-format markdown"
            ),
        }
    privacy_scan = _privacy_scan_operator_card(card) if isinstance(card, Mapping) else {"status": "blocked"}
    return {
        "schema_version": "operator_thread_continuation_card_context_v0",
        "status": "available" if card.get("status") != "missing" else "missing_thread",
        "payload_policy": "metadata_only",
        "consumer_surface": "kernel.context_pack",
        "thread_id": thread_id,
        "raw_trace_replacement_role": "default_type_b_grounding_object_for_operator_thread_continuation",
        "type_b_handoff_packet_command": (
            f"./repo-python tools/meta/observability/operator_thread_memory.py "
            f"--type-b-handoff-packet --thread {thread_id} --packet-format markdown"
        ),
        "type_b_handoff_export_profile": "operator_approved_external_type_b_handoff_v0",
        "privacy_scan": privacy_scan,
        "sufficiency_probe": _operator_card_sufficiency_probe(card) if isinstance(card, Mapping) else {},
        "card": card,
    }


def _type_a_autonomous_seed_selected_row(repo_root: Path, candidate: Mapping[str, Any]) -> dict[str, Any]:
    seed_id = str(candidate.get("id") or TYPE_A_AUTONOMOUS_SEED_SELECTED_ID).strip()
    surface = build_option_surface(repo_root, "type_a_autonomous_seeds", band="card", ids=[seed_id])
    option_row = {}
    rows = surface.get("rows") if isinstance(surface.get("rows"), list) else []
    if rows and isinstance(rows[0], Mapping):
        option_row = dict(rows[0])
    currentness = option_row.get("currentness") if isinstance(option_row.get("currentness"), Mapping) else {}
    context_contract = (
        option_row.get("context_pack_contract")
        if isinstance(option_row.get("context_pack_contract"), Mapping)
        else {
            "role": "TYPE_A_AUTONOMOUS_SEED_OWNER_DRILLDOWN",
            "metadata_only": True,
            "raw_bodies_omitted": True,
            "public_release_safe": False,
        }
    )
    return {
        "kind_id": "type_a_autonomous_seeds",
        "row_id": seed_id,
        "title": str(option_row.get("title") or seed_id.replace("_", " ").title()),
        "selected_band": "seed_owner_card",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 1.0), 6),
        "reason": _trim(str(candidate.get("reason") or "Type A autonomous seed owner-route anchor"), max_chars=260),
        "summary": _trim(
            option_row.get("summary")
            or "Metadata-only owner route for saved Type A autonomous seed bundles.",
            max_chars=360,
        ),
        "identity": option_row.get("identity"),
        "purpose": _trim(str(option_row.get("purpose") or ""), max_chars=360),
        "source_ref": option_row.get("source_ref"),
        "source_refs": list(option_row.get("source_refs") or []),
        "source_projection_boundary": option_row.get("source_projection_boundary"),
        "drilldown_command": option_row.get("drilldown_command")
        or f"./repo-python kernel.py --option-surface type_a_autonomous_seeds --band card --ids {seed_id}",
        "evidence_command": option_row.get("evidence_command")
        or f"./repo-python kernel.py --raw-seed-autonomous-seed-bundle {seed_id}",
        "debug_trace_command": None,
        "cost_estimate_tokens": 260,
        "selection_source_kind": str(candidate.get("source_kind") or "type_a_autonomous_seed_anchor"),
        "selection_facet": str(candidate.get("facet") or "saved_seed_owner_route"),
        "authority_posture": option_row.get("authority_posture") or "seed_metadata_projection_not_raw_seed_authority",
        "disclosure_posture": option_row.get("disclosure_posture") or "private_root_only",
        "currentness": currentness,
        "governing_doctrine": list(option_row.get("governing_doctrine") or []),
        "graph_neighbors": list(option_row.get("graph_neighbors") or []),
        "workitem_pressure": option_row.get("workitem_pressure"),
        "validation_route": list(option_row.get("validation_route") or []),
        "mutation_route": list(option_row.get("mutation_route") or []),
        "owner_routes": option_row.get("owner_routes"),
        "context_pack_contract": context_contract,
        "replay_receipt_contract": option_row.get("replay_receipt_contract"),
        "omission_receipt": option_row.get("omission_receipt"),
    }


def _workitem_spine_selected_row(repo_root: Path, candidate: Mapping[str, Any]) -> dict[str, Any]:
    task_events = repo_root / "state/task_ledger/events.jsonl"
    task_projection = repo_root / "state/task_ledger/ledger.json"
    task_views = repo_root / "state/task_ledger/views"
    work_runtime = repo_root / "state/work_ledger/runtime_status.json"
    spine_module = repo_root / "codex/doctrine/paper_modules/operational_work_item_spine.md"
    required_paths = [task_events, task_projection, task_views, work_runtime]
    status = "available_unverified_freshness" if all(path.exists() for path in required_paths) else "partial_missing_outputs"
    ledger = _load_json(task_projection)
    generated_at = str(ledger.get("generated_at") or ledger.get("updated_at") or "")
    return {
        "kind_id": "workitem_spine",
        "row_id": WORKITEM_SPINE_SELECTED_ID,
        "title": "Task / Work Ledger Operational Spine",
        "selected_band": "operational_spine_card",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 1.0), 6),
        "reason": _trim(str(candidate.get("reason") or "WorkItem spine owner-route anchor"), max_chars=260),
        "summary": (
            "Compact owner route for how Task Ledger WorkItems/CAPs, Work Ledger session claims, "
            "operational seeds, and generated projections coordinate a Type A execution wave."
        ),
        "identity": "Operational spine for durable work intent, runtime coordination claims, CAP pressure, and autonomous-seed execution handoff.",
        "purpose": "Preserve intent beyond chat, prevent concurrent write collisions, expose live pressure, and make execution/mutation routes explicit before source edits.",
        "source_ref": "codex/doctrine/paper_modules/operational_work_item_spine.md",
        "source_refs": [
            "codex/doctrine/paper_modules/operational_work_item_spine.md",
            "codex/standards/std_task_ledger.json",
            "codex/standards/std_forward_integration_policy.json",
            "state/task_ledger/events.jsonl",
            "state/task_ledger/ledger.json",
            "state/task_ledger/views/",
            "tools/meta/factory/task_ledger_apply.py",
            "tools/meta/factory/work_ledger.py",
            "state/work_ledger/runtime_status.json",
            "state/meta_missions/type_a_autonomous_seed_loop/seeds/",
        ],
        "source_projection_boundary": {
            "task_ledger_authority": "state/task_ledger/events.jsonl is append-only authority; ledger.json and views/*.json are projections.",
            "work_ledger_authority": "tools/meta/factory/work_ledger.py owns session bootstrap, path claims, progress, and finalize records over runtime Work Ledger state.",
            "atlas_boundary": "System Atlas may project WorkItem entities and coverage diagnostics, but mutation routes back to Task/Work Ledger owner tools.",
            "seed_boundary": "Autonomous seeds are operational prompts/handoffs, not ledger authority; they should cite or create WorkItems rather than replace them.",
        },
        "governing_doctrine": [
            "codex/standards/std_task_ledger.json",
            "codex/standards/std_task_sign_off.json",
            "codex/standards/std_forward_integration_policy.json",
            "codex/doctrine/paper_modules/operational_work_item_spine.md",
            "codex/doctrine/skills/task_ledger/task_ledger.md",
        ],
        "graph_neighbors": [
            "System Atlas WorkItem entities and kind_task_ledger materialization",
            "Task Ledger views: execution_menu, dependency_graph, active_wip, work_ledger_unlinked",
            "Work Ledger session claims and path leases",
            "CAP cards and Task Ledger capture/sign-off rows",
            "type_a_autonomous_seed_loop seeds and phase synth packets",
            "generated_state_drainer for generated projection settlement after source work",
        ],
        "workitem_cap_pressure": {
            "task_ledger_cluster": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            "active_claims": WORK_LEDGER_CLAIM_CARDS_COMMAND,
            "active_claims_full": WORK_LEDGER_FULL_CLAIMS_COMMAND,
            "organizer_report": "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2",
        },
        "validation_route": [
            "./repo-python tools/meta/factory/task_ledger_apply.py validate",
            WORK_LEDGER_CLAIM_CARDS_COMMAND,
            "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            "./repo-python kernel.py --option-surface system_atlas --band card --ids kind_task_ledger",
        ],
        "mutation_route": [
            "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --title <title> --statement <statement> --rebuild",
            "./repo-python tools/meta/factory/task_ledger_apply.py claim --subject-id <work_item_id> --payload-json '<json>' --rebuild",
            "./repo-python tools/meta/factory/work_ledger.py session-preflight --path <path> --require-exclusive",
            "./repo-python tools/meta/factory/work_ledger.py session-finalize --session-id <session_id> --action codex-turn-end",
        ],
        "currentness": {
            "status": status,
            "task_ledger_projection_generated_at": generated_at,
            "task_ledger_freshness_command": "./repo-python tools/meta/factory/task_ledger_apply.py validate",
            "work_ledger_freshness_command": WORK_LEDGER_CLAIM_CARDS_COMMAND,
            "work_ledger_full_claims_command": WORK_LEDGER_FULL_CLAIMS_COMMAND,
            "atlas_freshness_command": "./repo-python tools/meta/factory/build_system_atlas.py --check",
        },
        "disclosure_posture": "controlled_private_review",
        "drilldown_commands": [
            "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            "./repo-python kernel.py --option-surface task_ledger --band card --ids <work_item_id>",
            WORK_LEDGER_CLAIM_CARDS_COMMAND,
            "./repo-python kernel.py --option-surface system_atlas --band card --ids kind_task_ledger",
            "./repo-python kernel.py --paper-module operational_work_item_spine",
        ],
        "drilldown_command": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
        "evidence_command": "./repo-python tools/meta/factory/task_ledger_apply.py validate",
        "debug_trace_command": None,
        "cost_estimate_tokens": 260,
        "selection_source_kind": str(candidate.get("source_kind") or "workitem_spine_anchor"),
        "selection_facet": str(candidate.get("facet") or "task_work_ledger_operational_spine"),
        "nearest_standard": {
            "ref": "codex/standards/std_forward_integration_policy.json",
            "why": "The forward-integration standard binds dirty-tree tolerance, Task Ledger event authority, Work Ledger coordination, and closeout obligations.",
        },
        "context_pack_contract": {
            "role": "WORKITEM_OPERATIONAL_SPINE_DRILLDOWN",
            "source_bodies_omitted": True,
            "public_release_safe": False,
            "allowed_payload": "owner routes, source/projection boundaries, validation/mutation commands, currentness commands, and disclosure posture",
            "forbidden_payload": "raw Work Ledger runtime bodies, raw prompt/operator text, generated projection edits, or treating session claims as Task Ledger authority",
        },
        "omission_receipt": {
            "omitted": [
                "full Task Ledger rows",
                "full Work Ledger runtime status",
                "raw operational seed bodies",
                "per-session transcript details",
            ],
            "reason": "Context-pack selects the operational spine route; row/card expansion and runtime coordination stay behind owner commands.",
            "drilldown": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
        },
    }


def _generated_projection_owner_selected_row(repo_root: Path, candidate: Mapping[str, Any]) -> dict[str, Any]:
    registry = repo_root / "system/lib/generated_projection_registry.py"
    drainer = repo_root / "tools/meta/control/generated_state_drainer.py"
    preflight = repo_root / "tools/meta/control/mission_transaction_preflight.py"
    atlas_builder = repo_root / "tools/meta/factory/build_system_atlas.py"
    root_builder = repo_root / "tools/meta/factory/build_root_coverage_state.py"
    crystal_builder = repo_root / "tools/meta/factory/build_system_crystal.py"
    gate_checker = repo_root / "tools/meta/factory/check_dissemination_atlas_gate.py"
    required_paths = [registry, drainer, preflight, atlas_builder, root_builder, crystal_builder, gate_checker]
    status = "owner_routes_available" if all(path.exists() for path in required_paths) else "partial_missing_owner_routes"
    return {
        "kind_id": "generated_projection_ownership",
        "row_id": GENERATED_PROJECTION_OWNER_SELECTED_ID,
        "title": "Generated Projection Ownership and Source Coupling",
        "selected_band": "owner_route_card",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 1.0), 6),
        "reason": _trim(str(candidate.get("reason") or "generated projection owner-route anchor"), max_chars=260),
        "summary": (
            "Compact owner route for generated/read-model surfaces: source authority, owner builder/check, "
            "manual-edit boundary, dirty-source refresh policy, generated-state settlement, and scoped landing."
        ),
        "identity": "Projection governance spine for generated Atlas/Crystal/root/gate/fact/read-model outputs.",
        "purpose": "Prevent projection authority inversion and false freshness by routing repairs to source owners, builders, registry mappings, and generated-state settlement tools.",
        "source_ref": "system/lib/generated_projection_registry.py",
        "source_refs": [
            "system/lib/generated_projection_registry.py",
            "tools/meta/control/generated_state_drainer.py",
            "tools/meta/control/mission_transaction_preflight.py",
            "tools/meta/factory/build_system_atlas.py",
            "tools/meta/factory/build_root_coverage_state.py",
            "tools/meta/factory/build_system_crystal.py",
            "tools/meta/factory/check_dissemination_atlas_gate.py",
            "system/lib/agent_bootstrap_projection.py",
            "codex/standards/std_system_atlas.json",
            "codex/standards/std_agent_entry_surface.json",
            "codex/doctrine/paper_modules/system_self_comprehension_root.md",
        ],
        "source_projection_boundary": {
            "source_authority": "Source files, event ledgers, standards, doctrine, and owner tools remain authority.",
            "generated_outputs": "Generated markdown, JSON sidecars, read models, and coverage state are operational projections, not mutation authority.",
            "registry_boundary": "system/lib/generated_projection_registry.py maps generated outputs to owners/checks; it is a routing contract, not a substitute source.",
            "manual_edit_boundary": "Patch the source, builder, standard, registry, or checker first; never hand-edit generated regions to make a claim current.",
            "dirty_source_policy": "If an owner check reports dirty changed sources, do not refresh or commit generated outputs until the dirty source lane is owned or settled.",
        },
        "governing_doctrine": [
            "pri_142 Generated Projections Are Operational Interfaces With Source Lineage",
            "pri_121 Compression Via Substrate-Derived Projection",
            "codex/standards/std_system_atlas.json",
            "codex/standards/std_agent_entry_surface.json",
            "codex/doctrine/paper_modules/system_self_comprehension_root.md",
        ],
        "graph_neighbors": [
            "System Atlas graph/summary/facts projections and source-coupling checks",
            "Private System Crystal builder and tracked markdown renders",
            "Root coverage state and Root Navigator packet currentness",
            "Dissemination gate report and disclosure projection map",
            "Task Ledger and Work Ledger generated projections",
            "agent bootstrap generated regions in AGENTS/CODEX/CLAUDE surfaces",
            "mission transaction preflight and scoped_commit landing gates",
        ],
        "workitem_cap_pressure": {
            "task_ledger_pressure": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            "work_ledger_claims": WORK_LEDGER_CLAIM_CARDS_COMMAND,
            "work_ledger_claims_full": WORK_LEDGER_FULL_CLAIMS_COMMAND,
            "transaction_preflight": "./repo-python tools/meta/control/mission_transaction_preflight.py --subject-id <id> --owned-path <path>",
        },
        "validation_route": [
            "./repo-python tools/meta/factory/build_system_atlas.py --check",
            "./repo-python tools/meta/factory/build_system_crystal.py --check",
            "./repo-python tools/meta/factory/build_root_coverage_state.py --check --compact",
            "./repo-python tools/meta/factory/check_dissemination_atlas_gate.py --check",
            "./repo-python tools/meta/control/mission_transaction_preflight.py --subject-id <id> --owned-path <path>",
        ],
        "mutation_route": [
            "Patch the source authority, builder, checker, standard, or registry owner first.",
            "./repo-python tools/meta/control/generated_state_drainer.py settle --owner-id <owner_id> --dry-run",
            "./repo-python tools/meta/control/generated_state_drainer.py settle --owner-id <owner_id>",
            "./repo-python tools/meta/control/scoped_commit.py full-paths --expected-parent <current_head> --remote-fallback-on-metadata-block --path <owned_source_path> --message <message>",
        ],
        "currentness": {
            "status": status,
            "atlas_check": "./repo-python tools/meta/factory/build_system_atlas.py --check",
            "crystal_check": "./repo-python tools/meta/factory/build_system_crystal.py --check",
            "root_coverage_check": "./repo-python tools/meta/factory/build_root_coverage_state.py --check --compact",
            "gate_check": "./repo-python tools/meta/factory/check_dissemination_atlas_gate.py --check",
            "dirty_source_rule": "dirty_changed_source_count > 0 means generated refresh is blocked until source ownership/settlement is clear.",
        },
        "disclosure_posture": "controlled_private_review",
        "drilldown_commands": [
            "./repo-python tools/meta/control/mission_transaction_preflight.py --owned-path <path>",
            "./repo-python tools/meta/control/generated_state_drainer.py settle --owner-id <owner_id> --dry-run",
            "./repo-python tools/meta/factory/build_system_atlas.py --check",
            "./repo-python tools/meta/factory/build_root_coverage_state.py --check --compact",
            "./repo-python kernel.py --option-surface system_atlas --band card --ids dom_system_atlas",
        ],
        "drilldown_command": "./repo-python tools/meta/control/mission_transaction_preflight.py --owned-path <path>",
        "evidence_command": "./repo-python tools/meta/factory/build_system_atlas.py --check",
        "debug_trace_command": None,
        "cost_estimate_tokens": 270,
        "selection_source_kind": str(candidate.get("source_kind") or "generated_projection_owner_anchor"),
        "selection_facet": str(candidate.get("facet") or "projection_source_coupling_owner_route"),
        "nearest_standard": {
            "ref": "codex/standards/std_system_atlas.json",
            "why": "Generated Atlas and downstream self-description projections must expose source lineage, owner checks, disclosure posture, and safe refresh boundaries.",
        },
        "context_pack_contract": {
            "role": "GENERATED_PROJECTION_OWNER_DRILLDOWN",
            "source_bodies_omitted": True,
            "public_release_safe": False,
            "allowed_payload": "owner/check/repair commands, source-vs-generated boundary, dirty-source policy, disclosure posture, and drilldown handles",
            "forbidden_payload": "hand-editing generated outputs, raw private evidence bodies, hidden reasoning, or claiming stale projections are fresh",
        },
        "omission_receipt": {
            "omitted": [
                "full generated projection registry body",
                "full generated-state drainer owner registry",
                "raw private evidence behind generated projections",
                "full dirty path diff bodies",
            ],
            "reason": "Context-pack selects the owner route and safety boundary; owner tools emit the current source-coupling and settlement details.",
            "drilldown": "./repo-python tools/meta/control/mission_transaction_preflight.py --owned-path <path>",
        },
    }


def _external_benchmark_calibration_selected_row(repo_root: Path, candidate: Mapping[str, Any]) -> dict[str, Any]:
    surface = build_option_surface(
        repo_root,
        "external_benchmark_calibration",
        band="card",
        ids=[EXTERNAL_BENCHMARK_CALIBRATION_SELECTED_ID],
    )
    option_row: dict[str, Any] = {}
    rows = surface.get("rows") if isinstance(surface.get("rows"), list) else []
    if rows and isinstance(rows[0], Mapping):
        option_row = dict(rows[0])
    context_contract = (
        option_row.get("context_pack_contract")
        if isinstance(option_row.get("context_pack_contract"), Mapping)
        else {
            "role": "EXTERNAL_BENCHMARK_CALIBRATION_DRILLDOWN",
            "metadata_only": True,
            "raw_bodies_omitted": True,
            "public_release_safe": False,
        }
    )
    return {
        "kind_id": "external_benchmark_calibration",
        "row_id": EXTERNAL_BENCHMARK_CALIBRATION_SELECTED_ID,
        "title": str(
            option_row.get("title")
            or "VeriSoftBench Micro-10 External Benchmark Calibration Spine"
        ),
        "selected_band": "owner_route_card",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 1.0), 6),
        "reason": _trim(
            str(candidate.get("reason") or "external benchmark calibration owner-route anchor"),
            max_chars=260,
        ),
        "summary": _trim(
            option_row.get("summary")
            or "Owner route for formal-math external benchmark calibration and provider proof-repair receipts.",
            max_chars=360,
        ),
        "identity": option_row.get("identity"),
        "purpose": _trim(str(option_row.get("purpose") or ""), max_chars=360),
        "source_ref": option_row.get("source_ref"),
        "source_refs": list(option_row.get("source_refs") or []),
        "source_projection_boundary": option_row.get("source_projection_boundary"),
        "owner_surface": option_row.get("owner_surface"),
        "owner_tool": option_row.get("owner_tool"),
        "drilldown_command": option_row.get("drilldown_command")
        or (
            "./repo-python kernel.py --option-surface external_benchmark_calibration "
            f"--band card --ids {EXTERNAL_BENCHMARK_CALIBRATION_SELECTED_ID}"
        ),
        "evidence_command": option_row.get("evidence_command")
        or "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py --check",
        "debug_trace_command": None,
        "cost_estimate_tokens": 290,
        "selection_source_kind": str(candidate.get("source_kind") or "external_benchmark_calibration_anchor"),
        "selection_facet": str(candidate.get("facet") or "verisoftbench_micro_10_provider_repair_owner_route"),
        "authority_posture": option_row.get("authority_posture") or "owner_route_card_not_benchmark_authority",
        "disclosure_posture": option_row.get("disclosure_posture") or "controlled_private_review",
        "currentness": option_row.get("currentness") if isinstance(option_row.get("currentness"), Mapping) else {},
        "counts": option_row.get("counts") if isinstance(option_row.get("counts"), Mapping) else {},
        "governing_doctrine": list(option_row.get("governing_doctrine") or []),
        "graph_neighbors": list(option_row.get("graph_neighbors") or []),
        "workitem_pressure": option_row.get("workitem_pressure"),
        "validation_route": list(option_row.get("validation_route") or []),
        "mutation_route": list(option_row.get("mutation_route") or []),
        "owner_routes": option_row.get("owner_routes"),
        "context_pack_contract": context_contract,
        "omission_receipt": option_row.get("omission_receipt"),
    }


def _system_crystal_selected_row(repo_root: Path, candidate: Mapping[str, Any]) -> dict[str, Any]:
    output = repo_root / "docs/system_crystal/system_crystal.generated.md"
    one_page = repo_root / "docs/system_crystal/system_crystal_one_page.generated.md"
    five_page = repo_root / "docs/system_crystal/system_crystal_five_page.generated.md"
    status = "available" if output.exists() and one_page.exists() and five_page.exists() else "missing_outputs"
    return {
        "kind_id": "system_crystal",
        "row_id": "private_system_crystal_v1",
        "title": "Private System Crystal v1",
        "selected_band": "generated_artifact_card",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 1.0), 6),
        "reason": _trim(str(candidate.get("reason") or "private System Crystal anchor"), max_chars=260),
        "summary": (
            "Generated private cap surface over the self-comprehension family: bounded claims, "
            "routes, evidence handles, hashes, freshness, and public-hold boundaries."
        ),
        "source_ref": "docs/system_crystal/system_crystal.generated.md",
        "drilldown_command": './repo-python kernel.py --docs-route "system crystal"',
        "evidence_command": "./repo-python tools/meta/factory/build_system_crystal.py --check",
        "debug_trace_command": None,
        "cost_estimate_tokens": 150,
        "selection_source_kind": str(candidate.get("source_kind") or "system_crystal_protocol_anchor"),
        "selection_facet": str(candidate.get("facet") or "private_crystal"),
        "currentness": {
            "status": status,
            "tracked_outputs": [
                "docs/system_crystal/system_crystal.generated.md",
                "docs/system_crystal/system_crystal_one_page.generated.md",
                "docs/system_crystal/system_crystal_five_page.generated.md",
            ],
            "ignored_runtime_output": "state/system_crystal/system_crystal.json",
            "freshness_command": "./repo-python tools/meta/factory/build_system_crystal.py --check",
        },
        "nearest_standard": {
            "ref": "codex/standards/std_agent_entry_surface.json",
            "why": "The crystal is discoverability/routing substrate and must preserve projection_not_authority plus public-release hold.",
        },
        "context_pack_contract": {
            "role": "PRIVATE_SELF_MODEL_DRILLDOWN",
            "full_json_omitted": True,
            "public_release_safe": False,
            "allowed_payload": "generated markdown handles, builder/check command, ownership lane, and boundary claims",
            "forbidden_payload": "full ignored JSON payload, raw source bodies, private raw voice, public release action, or new authority claims",
        },
        "omission_receipt": {
            "omitted": ["state/system_crystal/system_crystal.json", "full source excerpts", "full graph payload"],
            "reason": "Context-pack selects the crystal surface; the builder owns dense JSON and tracked markdown renders.",
            "drilldown": './repo-python kernel.py --docs-route "system crystal"',
        },
    }


def _cluster_rows(repo_root: Path, kind_id: str, *, limit: int = 6) -> list[dict[str, Any]]:
    if kind_id == "derived_facts":
        cache = _load_json(repo_root / FACT_NAVIGATION_CACHE)
        tag_rows = cache.get("tag_index") if isinstance(cache.get("tag_index"), list) else []
        out: list[dict[str, Any]] = []
        for row in tag_rows[:limit]:
            if not isinstance(row, Mapping):
                continue
            tag = str(row.get("tag") or "")
            out.append(
                {
                    "cluster_id": f"tag:{tag}" if tag else row.get("cluster_id"),
                    "label": tag,
                    "count": row.get("fact_count"),
                    "top_ids": [str(item) for item in list(row.get("sample_fact_ids") or [])[:6]],
                    "drilldown": row.get("drilldown_command"),
                }
            )
        return out

    payload = build_option_surface(repo_root, kind_id, band="cluster_flag")
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    out: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        if kind_id == "paper_modules":
            out.append(
                {
                    "cluster_id": row.get("cluster_id"),
                    "label": row.get("label"),
                    "count": row.get("count"),
                    "top_ids": list(row.get("top_ids") or [])[:6],
                    "drilldown": row.get("drilldown_command"),
                }
            )
        elif kind_id == "skills":
            out.append(
                {
                    "cluster_id": row.get("family_id"),
                    "label": row.get("family_title"),
                    "count": row.get("count"),
                    "top_ids": [str(skill_id) for skill_id in list(row.get("skill_ids") or [])[:6]],
                    "drilldown": row.get("drilldown_command"),
                }
            )
        elif kind_id in {
            "standards",
            "task_ledger",
            "python_files",
            "python_scopes",
            "frontend_components",
            "principles",
            "annex_patterns",
            "annex_distillation_patterns",
        }:
            out.append(
                {
                    "cluster_id": row.get("cluster_id"),
                    "label": row.get("label") or row.get("group_label") or row.get("annex_slug"),
                    "count": row.get("count") or row.get("scope_count") or row.get("file_count"),
                    "top_ids": [str(item) for item in list(row.get("top_ids") or [])[:6]],
                    "drilldown": row.get("drilldown_command"),
                }
            )
        else:
            cluster_id = row.get("cluster_id") or row.get("row_id")
            out.append(
                {
                    "cluster_id": cluster_id,
                    "label": row.get("label") or row.get("title") or row.get("cluster_id") or cluster_id,
                    "count": row.get("count") or row.get("scope_count") or row.get("file_count"),
                    "top_ids": [str(item) for item in list(row.get("top_ids") or [])[:6]],
                    "drilldown": row.get("drilldown_command"),
                }
            )
    return out


def _cluster_first_fallback_cluster(
    atlas_row: Mapping[str, Any],
    *,
    kind_id: str,
    cluster_command: str | None,
) -> list[dict[str, Any]]:
    currentness = (
        atlas_row.get("currentness")
        if isinstance(atlas_row.get("currentness"), Mapping)
        else {}
    )
    row_count_semantics = (
        atlas_row.get("row_count_semantics")
        if isinstance(atlas_row.get("row_count_semantics"), Mapping)
        else {}
    )
    status = str(currentness.get("status") or row_count_semantics.get("status") or "projection_gap")
    return [
        {
            "cluster_id": f"{kind_id}:projection_gap",
            "label": atlas_row.get("title") or kind_id,
            "count": atlas_row.get("row_count"),
            "top_ids": [],
            "drilldown": cluster_command or atlas_row.get("option_surface_command"),
            "projection_status": status,
            "reason": "cluster-first surface is present but its row projection is empty or unavailable",
        }
    ]


def _cluster_flag_command(atlas_row: Mapping[str, Any]) -> str | None:
    cluster_command = str(atlas_row.get("cluster_command") or "").strip()
    if "--band cluster_flag" in cluster_command:
        return cluster_command
    command = str(atlas_row.get("option_surface_command") or "").strip()
    if "--band cluster_flag" in command:
        return command
    return None


def _dedupe_commands(commands: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for command in commands:
        command = str(command or "").strip()
        if not command or command in seen:
            continue
        seen.add(command)
        out.append(command)
    return out


def _next_commands(selected_rows: list[dict[str, Any]], lattice_commands: list[str]) -> list[str]:
    selected = {(str(row.get("kind_id") or ""), str(row.get("row_id") or "")) for row in selected_rows}
    commands: list[str] = []
    selected_seed_ids = [
        row_id
        for kind_id, row_id in sorted(selected)
        if kind_id == "type_a_autonomous_seeds" and row_id
    ]
    if TYPE_A_AUTONOMOUS_SEED_SPEED_SELECTED_ID in selected_seed_ids:
        commands.append(WORK_LEDGER_SEED_SPEED_COMMAND)
    if selected_seed_ids:
        commands.append("./repo-python kernel.py --option-surface type_a_autonomous_seeds --band flag")
        for seed_id in selected_seed_ids:
            commands.extend(
                [
                    (
                        "./repo-python kernel.py --option-surface type_a_autonomous_seeds "
                        f"--band card --ids {seed_id}"
                    ),
                    f"./repo-python kernel.py --raw-seed-autonomous-seed-bundle {seed_id}",
                ]
            )
    if TYPE_A_AUTONOMOUS_SEED_SPEED_SELECTED_ID in selected_seed_ids:
        commands.extend(
            [
                WORK_LEDGER_SEED_SPEED_COMMAND,
                "./repo-python tools/meta/control/action_quote.py --action latency_seed_preflight",
                "./repo-python tools/meta/control/action_quote.py --action process_bottleneck_triage",
                "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory",
                "./repo-python kernel.py --latency-seed-digest",
                "./repo-python kernel.py --process-bottlenecks",
            ]
        )
    if ("workitem_spine", WORKITEM_SPINE_SELECTED_ID) in selected:
        commands.extend(
            [
                "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
                "./repo-python tools/meta/factory/task_ledger_apply.py validate",
                WORK_LEDGER_CLAIM_CARDS_COMMAND,
                "./repo-python kernel.py --option-surface system_atlas --band card --ids kind_task_ledger",
            ]
        )
    if ("generated_projection_ownership", GENERATED_PROJECTION_OWNER_SELECTED_ID) in selected:
        commands.extend(
            [
                "./repo-python tools/meta/factory/build_system_atlas.py --check",
                "./repo-python tools/meta/control/mission_transaction_preflight.py --owned-path <path>",
                "./repo-python tools/meta/control/generated_state_drainer.py settle --owner-id <owner_id> --dry-run",
                "./repo-python tools/meta/factory/build_root_coverage_state.py --check --compact",
                "./repo-python tools/meta/factory/build_system_crystal.py --check",
            ]
        )
    if ("external_benchmark_calibration", EXTERNAL_BENCHMARK_CALIBRATION_SELECTED_ID) in selected:
        commands.extend(
            [
                (
                    "./repo-python kernel.py --option-surface external_benchmark_calibration "
                    f"--band card --ids {EXTERNAL_BENCHMARK_CALIBRATION_SELECTED_ID}"
                ),
                "./repo-python tools/meta/factory/build_external_benchmark_calibration_spine.py --check",
                (
                    "./repo-python tools/meta/factory/run_verisoftbench_micro10_c_arm_provider_repair.py "
                    "--check --json"
                ),
                (
                    "./repo-python kernel.py --option-surface task_ledger --band card "
                    "--ids cap_external_benchmark_calibration_spine_verisoftbench_micro_10"
                ),
            ]
        )
    if ("derived_facts", "state_axis_artifact") in selected:
        commands.extend(
            [
                "./repo-python kernel.py --facts --band cluster_flag",
                "./repo-python kernel.py --fact-audit",
            ]
        )
    if ("paper_modules", "system_self_comprehension_root") in selected:
        commands.extend(
            [
                "./repo-python kernel.py --paper-module system_self_comprehension_root",
                "./repo-python kernel.py --option-surface compression_profiles --band card --ids ai_workflow_system_packet_v1,type_b_external_grounding_v1",
                "./repo-python kernel.py --vantage --band card",
            ]
        )
    if ("system_crystal", "private_system_crystal_v1") in selected:
        commands.extend(
            [
                './repo-python kernel.py --docs-route "system crystal"',
                "./repo-python tools/meta/factory/build_system_crystal.py --check",
                "./repo-python kernel.py --option-surface task_ledger --band card --ids task_0947_system_self_comprehension_surface_entry_flow",
            ]
        )
    if ("system_atlas", "dom_system_atlas") in selected:
        commands.extend(
            [
                "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
                "./repo-python kernel.py --option-surface system_atlas --band unknowns",
                "./repo-python kernel.py --option-surface system_atlas --band card --ids dom_system_atlas",
            ]
        )
    if ("dissemination_gate", "public_safe_atlas_gate_v1") in selected:
        commands.extend(
            [
                "./repo-python tools/meta/factory/check_dissemination_atlas_gate.py --check",
                "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
                "./repo-python kernel.py --option-surface task_ledger --band card --ids cap_dissemination_launch_surface_v0",
            ]
        )
    if ("prompt_shelf_metadata", "prompt_shelf_runs_index_v1") in selected:
        commands.extend(
            [
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --coverage",
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --check",
            ]
        )
    operator_thread_ids = [
        row_id
        for kind_id, row_id in sorted(selected)
        if kind_id == "operator_thread_continuation_card" and row_id and row_id != "thread_id_required"
    ]
    if operator_thread_ids:
        commands.extend(
            [
                *[
                    (
                        "./repo-python tools/meta/observability/operator_thread_memory.py "
                        f"--type-b-handoff-packet --thread {thread_id} --packet-format markdown"
                    )
                    for thread_id in operator_thread_ids[:2]
                ],
                *[
                    (
                        "./repo-python tools/meta/observability/operator_thread_memory.py "
                        f"--continuation-card --thread {thread_id}"
                    )
                    for thread_id in operator_thread_ids[:2]
                ],
                "./repo-python tools/meta/observability/operator_thread_memory.py --check",
            ]
        )
    elif ("operator_thread_continuation_card", "thread_id_required") in selected:
        commands.extend(
            [
                "./repo-python tools/meta/observability/operator_thread_memory.py --type-b-handoff-packet --thread <thread_id> --packet-format markdown",
                "./repo-python tools/meta/observability/operator_thread_memory.py --continuation-card --thread <thread_id>",
                "./repo-python tools/meta/observability/operator_thread_memory.py --check",
            ]
        )
    if (
        ("paper_modules", "federated_config_plane") in selected
        or ("standards", "std_config_authority_registry") in selected
        or any(kind_id == "config_authorities" for kind_id, _row_id in selected)
    ):
        commands.extend(
            [
                './repo-python kernel.py --docs-route "master_config settings config authority registry config_ref effective config"',
                "./repo-python kernel.py --option-surface config_authorities --band cluster_flag",
                "./repo-python tools/meta/factory/build_config_authority_registry.py --check",
            ]
        )
    if (
        ("skills", "imagination_authoring") in selected
        or ("standards", "std_imagination") in selected
        or any(kind_id == "imaginations" for kind_id, _row_id in selected)
    ):
        commands.extend(
            [
                "./repo-python kernel.py --option-surface skills --band card --ids imagination_authoring",
                "./repo-python kernel.py --option-surface imaginations --band flag",
                "./repo-python kernel.py --option-surface standards --band card --ids std_imagination",
            ]
        )
        if ("imaginations", "imn_008_navigation_meta_diagnostic_plane_steady_state") in selected:
            commands.append(
                "./repo-python kernel.py --imagination imn_008_navigation_meta_diagnostic_plane_steady_state"
            )
    selected_cognitive_operator_ids = [
        row_id for kind_id, row_id in sorted(selected) if kind_id == "cognitive_operators" and row_id
    ]
    if selected_cognitive_operator_ids:
        commands.extend(
            [
                "./repo-python kernel.py --option-surface cognitive_operators --band flag",
                (
                    "./repo-python kernel.py --option-surface cognitive_operators --band card --ids "
                    + ",".join(selected_cognitive_operator_ids)
                ),
                "./repo-python tools/meta/factory/validate_cognitive_operator_registry.py --json",
            ]
        )
    for row in selected_rows:
        next_safe_moves = row.get("next_safe_moves")
        if not isinstance(next_safe_moves, list):
            continue
        commands.extend(
            str(command)
            for command in next_safe_moves
            if str(command or "").strip()
        )
    commands.extend(
        [
            "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            *lattice_commands[:2],
            "./repo-python kernel.py --row paper_modules:navigation_rosetta_math --band card",
            "./repo-python kernel.py --option-surface skills --band card --ids profile_governed_compression",
        ]
    )
    return _dedupe_commands(commands)[:8]


def _next_command_objects(selected_rows: list[dict[str, Any]], lattice_commands: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for command in _next_commands(selected_rows, lattice_commands):
        surface_role = "DRILLDOWN"
        if "--option-surface" in command:
            surface_role = "ATLAS_PROJECTION"
        elif "--imagination-find" in command or "--skill-find" in command:
            surface_role = "DEBUG_TRACE"
        rows.append(
            {
                "command": command,
                "surface_role": surface_role,
                "authority": "drilldown_hint_not_control_edge",
                "allowed_after": "entry/context-pack selected the relevant row or kind",
            }
        )
    return rows


def _trim_next_command_objects(commands: Sequence[Mapping[str, Any]], limit: int) -> list[Mapping[str, Any]]:
    rows = list(commands)
    if len(rows) <= limit:
        return rows
    protected: list[Mapping[str, Any]] = []
    seen_protected: set[str] = set()
    for row in rows:
        command = str(row.get("command") or "")
        if not any(token in command for token in NEXT_COMMAND_TRIM_PROTECTED_SUBSTRINGS):
            continue
        if command in seen_protected:
            continue
        seen_protected.add(command)
        protected.append(row)
    if not protected:
        return rows[:limit]
    if len(protected) >= limit:
        return protected
    trimmed = rows[: max(0, limit - len(protected))]
    seen = {str(row.get("command") or "") for row in trimmed}
    for row in protected:
        command = str(row.get("command") or "")
        if command in seen:
            continue
        trimmed.append(row)
        seen.add(command)
    for row in rows:
        if len(trimmed) >= limit:
            break
        command = str(row.get("command") or "")
        if command in seen:
            continue
        trimmed.append(row)
        seen.add(command)
    return trimmed[:limit]


def _trim_source_surfaces(source_surfaces: Sequence[Any], limit: int) -> list[str]:
    rows = [str(surface) for surface in source_surfaces if str(surface or "")]
    if len(rows) <= limit:
        return rows
    protected: list[str] = []
    seen_protected: set[str] = set()
    for surface in rows:
        if not any(token in surface for token in SOURCE_SURFACE_TRIM_PROTECTED_SUBSTRINGS):
            continue
        if surface in seen_protected:
            continue
        seen_protected.add(surface)
        protected.append(surface)
    if not protected:
        return rows[:limit]
    if len(protected) >= limit:
        return protected[:limit]
    trimmed = rows[: max(0, limit - len(protected))]
    seen = set(trimmed)
    for surface in protected:
        if surface in seen:
            continue
        trimmed.append(surface)
        seen.add(surface)
    for surface in rows:
        if len(trimmed) >= limit:
            break
        if surface in seen:
            continue
        trimmed.append(surface)
        seen.add(surface)
    return trimmed[:limit]


def _overview(
    repo_root: Path,
    atlas_rows: list[dict[str, Any]],
    *,
    profile: str = "routine",
    compact_routine_deferred_status: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cluster_expansion_allowed = profile == "deep"
    deferred_cluster_count = 0
    for atlas_row in atlas_rows:
        kind_id = str(atlas_row.get("kind_id") or "")
        row_count = int(atlas_row.get("row_count") or 0)
        high_cardinality = row_count >= HIGH_CARDINALITY_THRESHOLD
        cluster_command = _cluster_flag_command(atlas_row)
        cluster_first = kind_id in CLUSTER_FIRST_KIND_IDS
        concrete_cluster = bool(cluster_command and (high_cardinality or cluster_first))
        overview_row: dict[str, Any] = {
            "kind_id": kind_id,
            "title": atlas_row.get("title"),
            "row_count": row_count,
            "selected_band": "cluster_flag" if concrete_cluster else "kind_flag",
            "why": (
                "high cardinality; concrete cluster surface exists before row expansion"
                if concrete_cluster and high_cardinality
                else "cluster-first index surface; use contents page even when row count is zero or unavailable"
                if concrete_cluster
                else "high cardinality; represented only as a kind signpost until a cluster adapter exists"
                if high_cardinality
                else "low enough cardinality for kind-level signpost"
            ),
            "drilldown_command": (
                cluster_command
                if concrete_cluster
                else atlas_row.get("card_command")
                if high_cardinality
                else atlas_row.get("option_surface_command")
            ),
        }
        row_count_semantics = atlas_row.get("row_count_semantics")
        if (
            isinstance(row_count_semantics, Mapping)
            and str(row_count_semantics.get("mode") or "exact") != "exact"
        ):
            overview_row["row_count_semantics"] = row_count_semantics
        if concrete_cluster:
            if cluster_expansion_allowed:
                clusters = _cluster_rows(repo_root, kind_id)
                if not clusters and cluster_first:
                    clusters = _cluster_first_fallback_cluster(
                        atlas_row,
                        kind_id=kind_id,
                        cluster_command=cluster_command,
                    )
                overview_row["clusters"] = clusters
                overview_row["cluster_status"] = {
                    "status": "expanded" if clusters else "empty",
                    "mode": "deep",
                    "live_full_scan": bool(clusters and not (cluster_first and row_count == 0)),
                }
            else:
                deferred_cluster_count += 1
                overview_row["clusters"] = []
                if compact_routine_deferred_status:
                    overview_row["cluster_status_ref"] = "routine_deferred_cluster_status"
                else:
                    overview_row["cluster_status"] = {
                        "status": "deferred_due_to_routine_latency_budget",
                        "mode": "bounded_kind_signpost",
                        "live_full_scan": False,
                        "drilldown_command": cluster_command,
                    }
        rows.append(overview_row)
    status = {
        "mode": "deep_live_clusters" if cluster_expansion_allowed else "routine_bounded_kind_signposts",
        "live_full_scan": cluster_expansion_allowed,
        "cluster_expansion_allowed": cluster_expansion_allowed,
        "deferred_cluster_count": deferred_cluster_count,
        "overview_row_count": len(rows),
    }
    if deferred_cluster_count and compact_routine_deferred_status:
        status["routine_deferred_cluster_status"] = {
            "status": "deferred_due_to_routine_latency_budget",
            "mode": "bounded_kind_signpost",
            "live_full_scan": False,
            "row_drilldown_field": "drilldown_command",
        }
    return rows, status


def _landmines(atlas_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    high = [row for row in atlas_rows if int(row.get("row_count") or 0) >= HIGH_CARDINALITY_THRESHOLD]
    out = []
    for row in high:
        kind_id = str(row.get("kind_id") or "")
        cluster_command = _cluster_flag_command(row)
        landmine = {
            "surface": f"{kind_id}.row_flag_all",
            "observed_or_predicted": (
                f"high-cardinality row set ({row.get('row_count')} rows); "
                "all-row expansion is a legacy/library reference, not the first browse rung"
            ),
            "safe_alternative": (
                cluster_command
                or row.get("card_command")
                or row.get("option_surface_command")
            ),
            "reason": "select ids or use a composer packet before row expansion",
        }
        if cluster_command and kind_id in ROW_FLAG_COMPATIBILITY_SHIM_KINDS:
            landmine["compatibility_behavior"] = (
                "CLI redirects all-row flag calls to cluster_flag unless --ids is explicit"
            )
            landmine["live_cli_regression"] = False
        if kind_id == "paper_modules":
            landmine["library_reference_only"] = True
            landmine["source_debt_id"] = "projection:paper_modules.row_flag_all.library"
        out.append(landmine)
    return out[:8]


def _compact_routine_landmines(packet: dict[str, Any]) -> None:
    landmines = [row for row in list(packet.get("landmines") or []) if isinstance(row, Mapping)]
    if not landmines:
        return
    packet["landmines"] = [
        {
            key: row.get(key)
            for key in (
                "surface",
                "safe_alternative",
            )
            if row.get(key) not in (None, "", [], {})
        }
        for row in landmines
    ]
    packet.setdefault("budget", {})["routine_landmine_economy"] = {
        "status": "first_contact_handles_only",
        "landmine_count": len(landmines),
        "preserved": ["surface", "safe_alternative"],
    }
    packet.setdefault("omitted", []).append(
        {
            "section": "landmines.detail",
            "reason": (
                "routine context-pack keeps high-cardinality surface handles and safe alternatives; "
                "full risk prose stays behind deep context-pack or option-surface drilldowns"
            ),
            "drilldown": (
                "./repo-python kernel.py --context-pack \"<task>\" "
                "--context-budget 20000"
            ),
        }
    )


def _compact_routine_selected_row_affordances(packet: dict[str, Any]) -> None:
    selected_rows = [
        row for row in list(packet.get("selected_rows") or []) if isinstance(row, MutableMapping)
    ]
    compacted_count = 0
    metadata_field_omissions: dict[str, int] = {}

    def compact_list(value: Any, *, limit: int) -> list[Any]:
        if not isinstance(value, list):
            return []
        return [item for item in value[:limit] if item not in (None, "", [], {})]

    def omit_row_field(row: MutableMapping[str, Any], key: str) -> None:
        if key not in row:
            return
        row.pop(key, None)
        metadata_field_omissions[key] = metadata_field_omissions.get(key, 0) + 1

    for row in selected_rows:
        passport = row.get("affordance_passport")
        if isinstance(passport, Mapping):
            compact_passport = {
                key: value
                for key, value in {
                    "status": passport.get("status"),
                    "source": passport.get("source"),
                    "cluster_keys": compact_list(passport.get("cluster_keys"), limit=8),
                    "sufficiency_claims": compact_list(passport.get("sufficiency_claims"), limit=4),
                    "when_to_open": compact_list(passport.get("when_to_open"), limit=4),
                    "anti_triggers": compact_list(passport.get("anti_triggers"), limit=4),
                }.items()
                if value not in (None, "", [], {})
            }
            if compact_passport and compact_passport != passport:
                row["affordance_passport"] = compact_passport
                compacted_count += 1

        compatibility = row.get("affordance_compatibility")
        if isinstance(compatibility, Mapping):
            compact_compatibility = {
                key: value
                for key, value in {
                    "compatibility_label": compatibility.get("compatibility_label"),
                    "compatibility_bucket": compatibility.get("compatibility_bucket"),
                    "affordance_boost": compatibility.get("affordance_boost"),
                    "matched_when_to_open": compact_list(
                        compatibility.get("matched_when_to_open"),
                        limit=3,
                    ),
                    "matched_cluster_keys": compact_list(
                        compatibility.get("matched_cluster_keys"),
                        limit=5,
                    ),
                    "anti_trigger_overlap": compact_list(
                        compatibility.get("anti_trigger_overlap"),
                        limit=3,
                    ),
                }.items()
                if value not in (None, "", [], {})
            }
            if compact_compatibility and compact_compatibility != compatibility:
                row["affordance_compatibility"] = compact_compatibility
                compacted_count += 1

        currentness = row.get("currentness")
        if isinstance(currentness, Mapping):
            compact_currentness = {
                key: value
                for key, value in {
                    "status": currentness.get("status"),
                    "source_coupling_status": currentness.get("source_coupling_status"),
                    "source_ref": currentness.get("source_ref"),
                    "registry_ref": currentness.get("registry_ref"),
                    "index_has_file_row": currentness.get("index_has_file_row"),
                    "safe_to_commit_generated_outputs_without_sources": currentness.get(
                        "safe_to_commit_generated_outputs_without_sources"
                    ),
                    "work_ledger_full_claims_command": currentness.get(
                        "work_ledger_full_claims_command"
                    ),
                    "dirty_source_rule": currentness.get("dirty_source_rule"),
                    "checker_command": currentness.get("checker_command"),
                    "refresh_command": currentness.get("refresh_command"),
                    "source_exists": currentness.get("source_exists"),
                }.items()
                if value not in (None, "", [], {})
            }
            if not compact_currentness:
                compact_currentness = {
                    key: value
                    for key, value in {
                        "status": currentness.get("status"),
                        "recommended_action": currentness.get("recommended_action"),
                        "code_loci_freshness": currentness.get("code_loci_freshness"),
                        "module_recommended_action": currentness.get("module_recommended_action"),
                        "trust_boundary": currentness.get("trust_boundary"),
                        "source_newer_than_module_count": currentness.get("source_newer_than_module_count"),
                        "newest_source_path": currentness.get("newest_source_path"),
                    }.items()
                    if value not in (None, "", [], {})
                }
            if compact_currentness and compact_currentness != currentness:
                row["currentness"] = compact_currentness
                compacted_count += 1

        omission_receipt = row.get("omission_receipt")
        if isinstance(omission_receipt, Mapping):
            compact_omission = {
                key: value
                for key, value in {
                    "omitted": compact_list(omission_receipt.get("omitted"), limit=4),
                    "drilldown": omission_receipt.get("drilldown"),
                    "source_ref": omission_receipt.get("source_ref"),
                }.items()
                if value not in (None, "", [], {})
            }
            if compact_omission and compact_omission != omission_receipt:
                row["omission_receipt"] = compact_omission
                compacted_count += 1

        for metadata_key in ("debug_trace_command", "nearest_standard", "cost_estimate_tokens"):
            omit_row_field(row, metadata_key)

    if compacted_count:
        packet.setdefault("budget", {})["routine_selected_row_economy"] = {
            "status": "affordance_fields_compacted",
            "compacted_field_count": compacted_count,
            "omitted_metadata_fields": dict(sorted(metadata_field_omissions.items())),
            "preserved": [
                "selected_rows",
                "affordance_passport.status",
                "affordance_passport.source",
                "affordance_passport.cluster_keys",
                "affordance_compatibility.compatibility_label",
                "currentness.status",
                "currentness.recommended_action",
                "omission_receipt.drilldown",
            ],
        }
        packet.setdefault("omitted", []).append(
            {
                "section": "selected_rows.affordance_detail",
                "reason": (
                    "routine context-pack preserves row identity and routing fields while "
                    "compacting detailed affordance lists and drilldown-owned metadata"
                ),
                "drilldown": (
                    "./repo-python kernel.py --context-pack \"<task>\" "
                    "--context-budget 20000"
                ),
            }
        )


def _budget_trim(
    packet: dict[str, Any],
    context_budget: int,
    *,
    reserve_tokens: int = 0,
) -> dict[str, Any]:
    omitted = packet.setdefault("omitted", [])
    reserve = max(0, int(reserve_tokens or 0))
    if reserve:
        packet.setdefault("budget", {})["routine_economy_reserve_tokens"] = reserve
        packet.setdefault("budget", {})["routine_economy_effective_ceiling_tokens"] = max(
            1000,
            int(context_budget or 0) - BUDGET_METADATA_HEADROOM_TOKENS - reserve,
        )
    effective_budget = max(
        1000,
        int(context_budget or 0) - BUDGET_METADATA_HEADROOM_TOKENS - reserve,
    )
    routine_byte_economy_active = bool(reserve and int(context_budget or 0) <= 12000)

    def compact_sequence_steps(steps: Any, max_steps: int) -> list[dict[str, Any]]:
        compact: list[dict[str, Any]] = []
        for step in list(steps or [])[:max_steps]:
            if not isinstance(step, Mapping):
                continue
            row = {
                key: step.get(key)
                for key in (
                    "step_id",
                    "order",
                    "command",
                    "surface_role",
                    "kind_id",
                    "matched_intent_id",
                    "allowed_after",
                    "required",
                )
                if step.get(key) not in (None, "", [])
            }
            proof = step.get("proof") if isinstance(step.get("proof"), Mapping) else {}
            if proof:
                row["proof"] = {
                    key: proof.get(key)
                    for key in ("emits", "success_check")
                    if proof.get(key) not in (None, "", [])
                }
            compact.append(row)
        return compact

    def compact_reentry_receipt(receipt: Any) -> dict[str, Any]:
        if not isinstance(receipt, Mapping):
            return {}
        return {
            key: value
            for key, value in {
                "schema_version": receipt.get("schema_version"),
                "status": receipt.get("status"),
                "task_bound": receipt.get("task_bound"),
                "matched_intent_ids": list(receipt.get("matched_intent_ids") or [])[:3],
                "first_kind_id": receipt.get("first_kind_id"),
                "first_command": receipt.get("first_command"),
                "handoff_step_count": receipt.get("handoff_step_count"),
                "proof_chain": [
                    {
                        inner_key: row.get(inner_key)
                        for inner_key in ("step_id", "emits", "success_check", "required")
                        if isinstance(row, Mapping) and row.get(inner_key) not in (None, "", [])
                    }
                    for row in list(receipt.get("proof_chain") or [])[:3]
                    if isinstance(row, Mapping)
                ],
            }.items()
            if value not in (None, "", [])
        }

    def compact_coverage_closure_receipt(receipt: Any) -> dict[str, Any]:
        if not isinstance(receipt, Mapping):
            return {}
        snapshot = (
            receipt.get("coverage_watch_snapshot")
            if isinstance(receipt.get("coverage_watch_snapshot"), Mapping)
            else {}
        )
        if snapshot.get("status") == "matrix_not_supplied":
            compact_snapshot = {
                "schema_version": snapshot.get("schema_version"),
                "status": snapshot.get("status"),
            }
        else:
            compact_snapshot = {
                key: value
                for key, value in {
                    "schema_version": snapshot.get("schema_version"),
                    "status": snapshot.get("status"),
                    "coverage_status_counts": snapshot.get("coverage_status_counts"),
                    "watch_row_count": snapshot.get("watch_row_count"),
                    "watch_kind_ids": list(snapshot.get("watch_kind_ids") or [])[:4],
                    "top_watch_rows": list(snapshot.get("top_watch_rows") or [])[:2],
                    "top_behavior_rows": list(snapshot.get("top_behavior_rows") or [])[:2],
                    "closure_success_check": snapshot.get("closure_success_check"),
                }.items()
                if value not in (None, "", [], {})
            }
        return {
            key: value
            for key, value in {
                "schema_version": receipt.get("schema_version"),
                "status": receipt.get("status"),
                "coverage_surface_available_count": receipt.get("coverage_surface_available_count"),
                "coverage_surface_resolution_kind_count": receipt.get(
                    "coverage_surface_resolution_kind_count"
                ),
                "kind_atlas_coverage_surface_available_count": receipt.get(
                    "kind_atlas_coverage_surface_available_count"
                ),
                "standard_type_plane_resolved_surface_count": receipt.get(
                    "standard_type_plane_resolved_surface_count"
                ),
                "coverage_surface_resolution_sources": receipt.get(
                    "coverage_surface_resolution_sources"
                ),
                "entry_visible_kind_count": receipt.get("entry_visible_kind_count"),
                "coverage_surface_gap_count": receipt.get("coverage_surface_gap_count"),
                "high_cardinality_cluster_gap_count": receipt.get("high_cardinality_cluster_gap_count"),
                "coverage_count_policy": receipt.get("coverage_count_policy"),
                "coverage_is_not_permission": receipt.get("coverage_is_not_permission"),
                "behavior_watch_status": receipt.get("behavior_watch_status"),
                "matrix_command": receipt.get("matrix_command"),
                "watch_row_selector": receipt.get("watch_row_selector"),
                "watch_repair_source_fields": list(receipt.get("watch_repair_source_fields") or [])[:1],
                "watch_closure_success_check": receipt.get("watch_closure_success_check"),
                "watch_drilldown_sequence": compact_sequence_steps(
                    receipt.get("watch_drilldown_sequence"),
                    4,
                ),
                "coverage_watch_snapshot": compact_snapshot,
            }.items()
            if value not in (None, "", [])
        }

    def compact_diagnostic_rows(payload: Any, *, max_rows: int = 2) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            return {}
        compact_rows: list[dict[str, Any]] = []
        for row in list(payload.get("rows") or [])[:max_rows]:
            if not isinstance(row, Mapping):
                continue
            observed = row.get("observed_state") if isinstance(row.get("observed_state"), Mapping) else {}
            compact_observed = {
                key: observed.get(key)
                for key in (
                    "status",
                    "freshness_sync_status",
                    "freshness_status",
                    "source_coupling_status",
                    "safe_to_commit_generated_outputs_without_sources",
                    "module_count",
                    "status_counts",
                    "queue_counts",
                    "source_projection_index",
                    "recommended_action",
                    "action_cause",
                    "reason",
                )
                if observed.get(key) not in (None, "", [], {})
            }
            compact_row = {
                key: row.get(key)
                for key in (
                    "diagnostic_id",
                    "slug",
                    "title",
                    "severity",
                    "recommended_action",
                    "checker_command",
                    "source_projection",
                    "governing_standard_ref",
                    "governing_standard_ref_status",
                    "is_hard_gate",
                )
                if row.get(key) not in (None, "", [], {})
            }
            if compact_observed:
                compact_row["observed_state"] = compact_observed
            compact_rows.append(compact_row)
        return {
            key: value
            for key, value in {
                "count": payload.get("count"),
                "triggered": payload.get("triggered"),
                "matched_triggers": list(payload.get("matched_triggers") or [])[:3],
                "source_projection": payload.get("source_projection"),
                "checker_command": payload.get("checker_command"),
                "diagnostic_family": payload.get("diagnostic_family"),
                "non_blocking": payload.get("non_blocking"),
                "rows": compact_rows,
                "trimmed_for_context_pack_budget": True,
            }.items()
            if value not in (None, "", [], {})
        }

    def compact_candidate_runtime_pressure_for_context_budget(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            return {
                "status": "omitted_for_hard_ceiling",
                "reason": "candidate runtime pressure payload was unavailable during hard compaction",
            }
        return {
            key: value
            for key, value in {
                "count": payload.get("count", 0),
                "suppressed_count": payload.get("suppressed_count", 0),
                "filter_policy": payload.get("filter_policy"),
                "contract_ref": payload.get("contract_ref"),
                "source_standard": payload.get("source_standard"),
                "non_law_warning": payload.get("non_law_warning"),
                "match_strategy": payload.get("match_strategy"),
                "match_strategy_ref": payload.get("match_strategy_ref"),
                "suppressed_surface_reasons": payload.get("suppressed_surface_reasons") or [],
                "evidence_surface_reasons": payload.get("evidence_surface_reasons") or [],
                "status": "rows_omitted_for_hard_ceiling",
                "reason": (
                    "routine context-pack exceeded the hard budget after row and spine compaction; "
                    "candidate pressure rows remain behind the explicit drilldown"
                ),
                "drilldown": (
                    "./repo-python kernel.py --context-pack \"<task>\" "
                    "--context-budget 20000"
                ),
                "trimmed_for_context_pack_budget": True,
            }.items()
            if value not in (None, "", {})
        }

    def compact_selected_rows(max_rows: int) -> None:
        selected_rows = [row for row in list(packet.get("selected_rows") or []) if isinstance(row, Mapping)]
        rows_to_compact: list[Mapping[str, Any]] = []
        included: set[tuple[str, str]] = set()

        def add_selected_row(row: Mapping[str, Any]) -> None:
            key = (str(row.get("kind_id") or ""), str(row.get("row_id") or ""))
            if key in included:
                return
            included.add(key)
            rows_to_compact.append(row)

        for row in selected_rows[:max_rows]:
            add_selected_row(row)
        for row in selected_rows[max_rows:]:
            if protected_selected_row(row):
                add_selected_row(row)

        compact_rows: list[dict[str, Any]] = []
        for row in rows_to_compact:
            compact_row = {
                key: row.get(key)
                for key in (
                    "kind_id",
                    "row_id",
                    "title",
                    "selected_band",
                    "row_role",
                    "route_authority",
                    "relevance",
                    "reason",
                    "summary",
                    "identity",
                    "purpose",
                    "source_ref",
                    "source_refs",
                    "source_projection_boundary",
                    "owner_surface",
                    "owner_tool",
                    "governing_doctrine",
                    "graph_neighbors",
                    "workitem_cap_pressure",
                    "workitem_pressure",
                    "validation_route",
                    "mutation_route",
                    "disclosure_posture",
                    "counts",
                    "drilldown_commands",
                    "drilldown_command",
                    "evidence_command",
                    "selection_source_kind",
                    "selection_facet",
                    "matched_validation_rules",
                    "next_safe_moves",
                    "provider_population_gap_route",
                    "provider_population_lane_command",
                    "provider_boundary",
                    "owner_routes",
                    "replay_receipt_contract",
                    "route_summary",
                    "render_profile",
                    "sibling_profiles",
                    "sibling_profile_summary",
                )
                if row.get(key) not in (None, "", [], {})
            }
            if isinstance(row.get("currentness"), Mapping):
                compact_row["currentness"] = dict(row.get("currentness") or {})
            if isinstance(row.get("context_pack_contract"), Mapping):
                compact_row["context_pack_contract"] = dict(row.get("context_pack_contract") or {})
            if isinstance(row.get("ai_native_view_packet"), Mapping):
                compact_row["ai_native_view_packet"] = dict(row.get("ai_native_view_packet") or {})
            if isinstance(row.get("affordance_passport"), Mapping):
                compact_row["affordance_passport"] = dict(row.get("affordance_passport") or {})
            if isinstance(row.get("affordance_compatibility"), Mapping):
                compact_row["affordance_compatibility"] = dict(row.get("affordance_compatibility") or {})
            if isinstance(row.get("omission_receipt"), Mapping):
                receipt = row.get("omission_receipt") or {}
                compact_row["omission_receipt"] = {
                    key: receipt.get(key)
                    for key in ("omitted", "reason", "drilldown")
                    if receipt.get(key) not in (None, "", [], {})
                }
            compact_rows.append(compact_row)
        for row in selected_rows:
            key = (str(row.get("kind_id") or ""), str(row.get("row_id") or ""))
            if key in included:
                continue
            packet.setdefault("omitted", []).append(
                {
                    "kind_id": row.get("kind_id"),
                    "row_id": row.get("row_id"),
                    "reason": "dropped by final hard budget compaction",
                    "drilldown": row.get("drilldown_command"),
                }
            )
        packet["selected_rows"] = compact_rows
        packet.setdefault("omitted", []).append(
            {
                "section": "selected_rows.extra_fields",
                "reason": "compacted by final hard budget trim",
                "drilldown": "./repo-python kernel.py --context-pack \"<task>\" --context-budget <larger-budget>",
            }
        )

    def compact_navigation_index_spine() -> None:
        spine = packet.get("navigation_index_spine")
        if not isinstance(spine, Mapping):
            return
        route_digest = spine.get("route_digest") if isinstance(spine.get("route_digest"), Mapping) else {}
        task_conditioned = {}
        entry_intent_openings = (
            spine.get("entry_intent_openings") if isinstance(spine.get("entry_intent_openings"), Mapping) else {}
        )
        kind_group_rollup = (
            spine.get("kind_group_rollup") if isinstance(spine.get("kind_group_rollup"), Mapping) else {}
        )
        if isinstance(entry_intent_openings, Mapping):
            task_conditioned = (
                entry_intent_openings.get("task_conditioned")
                if isinstance(entry_intent_openings.get("task_conditioned"), Mapping)
                else {}
            )
        compact_groups: list[dict[str, Any]] = []
        if isinstance(kind_group_rollup, Mapping):
            for group in list(kind_group_rollup.get("groups") or [])[:2]:
                if not isinstance(group, Mapping):
                    continue
                compact_group = {
                    key: group.get(key)
                    for key in (
                        "group_id",
                        "label",
                        "row_level_gap_count",
                        "coverage_status",
                        "top_gap_kind_ids",
                        "recommended_openings",
                    )
                    if group.get(key) not in (None, "", [], {})
                }
                if isinstance(compact_group.get("top_gap_kind_ids"), list):
                    compact_group["top_gap_kind_ids"] = compact_group["top_gap_kind_ids"][:4]
                if isinstance(compact_group.get("recommended_openings"), list):
                    compact_group["recommended_openings"] = compact_group["recommended_openings"][:2]
                compact_groups.append(compact_group)
        packet["navigation_index_spine"] = {
            key: value
            for key, value in {
                "schema_version": spine.get("schema_version"),
                "surface_role": spine.get("surface_role"),
                "authority_posture": spine.get("authority_posture"),
                "available": spine.get("available"),
                "summary": spine.get("summary"),
                "route_digest": {
                    compact_key: route_digest.get(compact_key)
                    for compact_key in (
                        "schema_version",
                        "kind_atlas_available",
                        "entry_visible_kind_count",
                        "coverage_surface_available_count",
                        "coverage_surface_gap_count",
                        "high_cardinality_cluster_gap_count",
                        "first_contact_policy",
                    )
                    if route_digest.get(compact_key) not in (None, "", [], {})
                },
                "coverage_closure_receipt": compact_coverage_closure_receipt(
                    spine.get("coverage_closure_receipt")
                ),
                "kind_group_rollup": {
                    "schema_version": kind_group_rollup.get("schema_version"),
                    "group_count": kind_group_rollup.get("group_count"),
                    "groups": compact_groups,
                    "trimmed_for_context_pack_budget": True,
                }
                if compact_groups
                else None,
                "entry_intent_openings": {
                    "default_control_sequence": compact_sequence_steps(
                        entry_intent_openings.get("default_control_sequence"),
                        3,
                    ),
                    "task_conditioned": {
                        "matched_intent_count": task_conditioned.get("matched_intent_count"),
                        "matched_intent_ids": list(task_conditioned.get("matched_intent_ids") or [])[:3],
                        "selected_openings": list(task_conditioned.get("selected_openings") or [])[:2],
                        "first_opening": task_conditioned.get("first_opening"),
                        "handoff_sequence": compact_sequence_steps(
                            task_conditioned.get("handoff_sequence"),
                            3,
                        ),
                        "reentry_receipt": compact_reentry_receipt(task_conditioned.get("reentry_receipt")),
                    }
                }
                if task_conditioned
                else None,
                "top_projection_gaps": list(spine.get("top_projection_gaps") or [])[:4],
                "legal_drilldowns": list(spine.get("legal_drilldowns") or [])[:2],
                "recursive_seed_handoff": spine.get("recursive_seed_handoff"),
                "entry_policy": spine.get("entry_policy"),
                "currentness": spine.get("currentness"),
                "source_refs": list(spine.get("source_refs") or [])[:4],
                "omission_receipt": {
                    "omitted": ["kind_group_rollup", "coverage_closure_receipt", "full entry intent catalog"],
                    "reason": "Compacted by final hard budget trim; use System Atlas drilldowns for full projection detail.",
                    "drilldown": "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
                },
                "trimmed_for_context_pack_budget": True,
            }.items()
            if value not in (None, "", [], {})
        }

    def ultra_compact_selected_rows() -> None:
        compact_rows: list[dict[str, Any]] = []
        for row in list(packet.get("selected_rows") or []):
            if not isinstance(row, Mapping):
                continue
            compact_rows.append(
                {
                    key: row.get(key)
                    for key in (
                        "kind_id",
                        "row_id",
                        "title",
                        "selected_band",
                        "row_role",
                        "route_authority",
                        "relevance",
                        "identity",
                        "purpose",
                        "source_ref",
                        "source_refs",
                        "source_projection_boundary",
                        "owner_surface",
                        "owner_tool",
                        "workitem_pressure",
                        "validation_route",
                        "mutation_route",
                        "currentness",
                        "counts",
                        "disclosure_posture",
                        "drilldown_command",
                        "evidence_command",
                        "selection_source_kind",
                        "selection_facet",
                        "matched_validation_rules",
                        "next_safe_moves",
                        "owner_routes",
                        "replay_receipt_contract",
                        "route_summary",
                        "render_profile",
                        "sibling_profiles",
                        "sibling_profile_summary",
                        "context_pack_contract",
                        "omission_receipt",
                        "affordance_passport",
                        "affordance_compatibility",
                        "ai_native_view_packet",
                    )
                    if row.get(key) not in (None, "", [], {})
                }
            )
        packet["selected_rows"] = compact_rows
        packet.setdefault("omitted", []).append(
            {
                "section": "selected_rows.narrative_fields",
                "reason": "compacted by final hard budget trim after protected row preservation",
                "drilldown": "./repo-python kernel.py --context-pack \"<task>\" --context-budget <larger-budget>",
            }
        )

    def compact_owner_routes(routes: Any) -> dict[str, Any]:
        if not isinstance(routes, Mapping):
            return {}
        return {
            key: routes.get(key)
            for key in (
                "entry_command",
                "card_command",
                "check_command",
                "refresh_command",
                "status_command",
                "root_drilldown_command",
                "provider_repair_check_command",
            )
            if routes.get(key) not in (None, "", [], {})
        }

    def compact_render_profile(profile: Any) -> dict[str, Any]:
        if not isinstance(profile, Mapping):
            return {}
        return {
            key: profile.get(key)
            for key in (
                "output_path",
                "status_sidecar_path",
                "projection_not_authority",
            )
            if profile.get(key) not in (None, "", [], {})
        }

    def compact_sibling_profile_summary(summary: Any) -> dict[str, Any]:
        if not isinstance(summary, Mapping):
            return {}
        return {
            key: summary.get(key)
            for key in (
                "count",
                "profile_ids",
            )
            if summary.get(key) not in (None, "", [], {})
        }

    def compact_hard_ceiling_mapping(value: Any, *, keys: tuple[str, ...]) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            return {}
        return {
            key: value.get(key)
            for key in keys
            if value.get(key) not in (None, "", [], {})
        }

    def compact_hard_ceiling_sequence(value: Any, *, limit: int) -> list[Any]:
        if not isinstance(value, list):
            return []
        return [item for item in value[:limit] if item not in (None, "", [], {})]

    def compact_hard_ceiling_omission(receipt: Any) -> dict[str, Any]:
        if not isinstance(receipt, Mapping):
            return {}
        return {
            key: value
            for key, value in {
                "omitted": compact_hard_ceiling_sequence(receipt.get("omitted"), limit=3),
                "drilldown": receipt.get("drilldown"),
                "source_ref": receipt.get("source_ref"),
            }.items()
            if value not in (None, "", [], {})
        }

    query_text = str(packet.get("query") or "").lower()
    preserve_rich_compression_profiles = (
        "compression profile" in query_text
        and ("owner route" in query_text or "owner routes" in query_text or "render profile" in query_text)
    )
    speed_or_context_economy_query = any(
        term in query_text
        for term in (
            "speed",
            "latency",
            "optimisation",
            "optimization",
            "context bloat",
            "context economy",
            "command economy",
        )
    )
    autonomous_seed_economy_query = (
        "autonomous seed" in query_text
        or ("self" in query_text and "propagat" in query_text)
        or "self-up" in query_text
        or "self up" in query_text
    )
    aggressive_hard_ceiling_economy = (
        ("improve speed" in query_text and "meta infra" in query_text)
        or (speed_or_context_economy_query and autonomous_seed_economy_query)
        or (
            "system integration unification duplicate surfaces" in query_text
            and "type b thread" in query_text
        )
    )
    minimal_hard_ceiling_economy = aggressive_hard_ceiling_economy or routine_byte_economy_active

    def hard_ceiling_selected_row_handles() -> None:
        compact_rows: list[dict[str, Any]] = []
        for row in list(packet.get("selected_rows") or []):
            if not isinstance(row, Mapping):
                continue
            if not minimal_hard_ceiling_economy:
                compact_row = {
                    key: row.get(key)
                    for key in (
                        "kind_id",
                        "row_id",
                        "title",
                        "selected_band",
                        "row_role",
                        "route_authority",
                        "relevance",
                        "source_ref",
                        "source_refs",
                        "source_projection_boundary",
                        "owner_surface",
                        "owner_tool",
                        "workitem_pressure",
                        "validation_route",
                        "mutation_route",
                        "currentness",
                        "counts",
                        "disclosure_posture",
                        "drilldown_command",
                        "evidence_command",
                        "selection_source_kind",
                        "selection_facet",
                        "matched_validation_rules",
                        "next_safe_moves",
                        "route_summary",
                        "render_profile",
                        "sibling_profiles",
                        "sibling_profile_summary",
                    )
                    if row.get(key) not in (None, "", [], {})
                }
                owner_routes = compact_owner_routes(row.get("owner_routes"))
                if owner_routes:
                    compact_row["owner_routes"] = owner_routes
                if isinstance(row.get("omission_receipt"), Mapping):
                    compact_row["omission_receipt"] = dict(row.get("omission_receipt") or {})
                if isinstance(row.get("affordance_passport"), Mapping):
                    compact_row["affordance_passport"] = dict(row.get("affordance_passport") or {})
                if isinstance(row.get("context_pack_contract"), Mapping):
                    contract = row.get("context_pack_contract") or {}
                    compact_contract = {
                        key: contract.get(key)
                        for key in (
                            "role",
                            "native_band",
                            "metadata_only",
                            "raw_bodies_omitted",
                            "source_bodies_omitted",
                            "safe_issue_summaries_only",
                            "public_release_safe",
                            "full_graph_omitted",
                            "full_json_omitted",
                            "allowed_payload",
                            "forbidden_payload",
                            "entry_consumption_obligation",
                            "external_type_b_render_profile",
                        )
                        if contract.get(key) not in (None, "", [], {})
                    }
                    if compact_contract:
                        compact_row["context_pack_contract"] = compact_contract
                if isinstance(row.get("ai_native_view_packet"), Mapping):
                    view_packet = row.get("ai_native_view_packet") or {}
                    compact_view_packet = {
                        key: view_packet.get(key)
                        for key in (
                            "schema",
                            "view_id",
                            "view_agent_packet_command",
                            "claude_handoff_packet_command",
                            "authority_boundary",
                        )
                        if view_packet.get(key) not in (None, "", [], {})
                    }
                    if compact_view_packet:
                        compact_row["ai_native_view_packet"] = compact_view_packet
                compact_rows.append(compact_row)
                continue
            is_compression_profile = str(row.get("kind_id") or "") == "compression_profiles"
            preserve_rich_row = preserve_rich_compression_profiles and is_compression_profile
            compact_row = {
                key: row.get(key)
                for key in (
                    "kind_id",
                    "row_id",
                    "title",
                    "selected_band",
                    "source_ref",
                    "owner_surface",
                    "owner_tool",
                    "workitem_pressure",
                    "counts",
                    "disclosure_posture",
                    "drilldown_command",
                    "evidence_command",
                    "selection_source_kind",
                    "selection_facet",
                    "matched_validation_rules",
                )
                if row.get(key) not in (None, "", [], {})
            }
            if preserve_rich_row:
                for key in (
                    "row_role",
                    "route_authority",
                    "relevance",
                    "evidence_command",
                    "selection_facet",
                    "route_summary",
                ):
                    if row.get(key) not in (None, "", [], {}):
                        compact_row[key] = row.get(key)
            source_refs = compact_hard_ceiling_sequence(row.get("source_refs"), limit=3)
            if source_refs:
                compact_row["source_refs"] = source_refs
            source_projection_boundary = compact_hard_ceiling_mapping(
                row.get("source_projection_boundary"),
                keys=(
                    "source_authority",
                    "json_source_authority",
                    "markdown_projection",
                    "navigation_map_projection",
                    "option_surface_role",
                    "generated_outputs",
                    "manual_edit_boundary",
                    "dirty_source_policy",
                ),
            )
            if source_projection_boundary:
                compact_row["source_projection_boundary"] = source_projection_boundary
            validation_route = compact_hard_ceiling_sequence(row.get("validation_route"), limit=2)
            if validation_route:
                compact_row["validation_route"] = validation_route
            mutation_route = compact_hard_ceiling_sequence(row.get("mutation_route"), limit=2)
            if mutation_route:
                compact_row["mutation_route"] = mutation_route
            next_safe_moves = compact_hard_ceiling_sequence(row.get("next_safe_moves"), limit=1)
            if preserve_rich_row and next_safe_moves:
                compact_row["next_safe_moves"] = next_safe_moves
            currentness = compact_hard_ceiling_mapping(
                row.get("currentness"),
                keys=(
                    "status",
                    "source_coupling_status",
                    "safe_to_commit_generated_outputs_without_sources",
                    "checker_command",
                    "refresh_command",
                    "source_exists",
                ),
            )
            if currentness:
                compact_row["currentness"] = currentness
            render_profile = compact_render_profile(row.get("render_profile"))
            if render_profile:
                compact_row["render_profile"] = render_profile
            sibling_summary = compact_sibling_profile_summary(row.get("sibling_profile_summary"))
            if sibling_summary:
                compact_row["sibling_profile_summary"] = sibling_summary
            if preserve_rich_row and isinstance(row.get("sibling_profiles"), list):
                compact_row["sibling_profiles"] = list(row.get("sibling_profiles") or [])[:1]
            owner_routes = compact_owner_routes(row.get("owner_routes"))
            if owner_routes:
                compact_row["owner_routes"] = owner_routes
            if isinstance(row.get("replay_receipt_contract"), Mapping):
                compact_replay_receipt_contract = compact_hard_ceiling_mapping(
                    row.get("replay_receipt_contract"),
                    keys=(
                        "schema_version",
                        "purpose",
                        "required_fields",
                        "detection_evidence_options",
                        "write_targets",
                        "non_success_states",
                        "receipt_is_not_success_by_itself",
                    ),
                )
                if compact_replay_receipt_contract:
                    compact_row["replay_receipt_contract"] = compact_replay_receipt_contract
            omission_receipt = compact_hard_ceiling_omission(row.get("omission_receipt"))
            if omission_receipt:
                compact_row["omission_receipt"] = omission_receipt
            if isinstance(row.get("affordance_passport"), Mapping):
                compact_row["affordance_passport"] = compact_hard_ceiling_mapping(
                    row.get("affordance_passport"),
                    keys=("status", "source", "cluster_keys", "sufficiency_claims"),
                )
            if isinstance(row.get("affordance_compatibility"), Mapping):
                compact_row["affordance_compatibility"] = compact_hard_ceiling_mapping(
                    row.get("affordance_compatibility"),
                    keys=(
                        "compatibility_label",
                        "compatibility_bucket",
                        "affordance_boost",
                    ),
                )
            if isinstance(row.get("context_pack_contract"), Mapping):
                contract = row.get("context_pack_contract") or {}
                contract_keys = [
                    "role",
                    "native_band",
                    "metadata_only",
                    "raw_bodies_omitted",
                    "source_bodies_omitted",
                    "safe_issue_summaries_only",
                    "public_release_safe",
                    "full_graph_omitted",
                    "full_json_omitted",
                    "external_type_b_render_profile",
                ]
                if preserve_rich_row:
                    contract_keys.extend(
                        [
                            "entry_consumption_obligation",
                        ]
                    )
                compact_contract = {
                    key: contract.get(key)
                    for key in contract_keys
                    if contract.get(key) not in (None, "", [], {})
                }
                if compact_contract:
                    compact_row["context_pack_contract"] = compact_contract
            if isinstance(row.get("ai_native_view_packet"), Mapping):
                view_packet = row.get("ai_native_view_packet") or {}
                compact_view_packet = {
                    key: view_packet.get(key)
                    for key in (
                        "schema",
                        "view_id",
                        "view_agent_packet_command",
                        "claude_handoff_packet_command",
                        "authority_boundary",
                    )
                    if view_packet.get(key) not in (None, "", [], {})
                }
                if compact_view_packet:
                    compact_row["ai_native_view_packet"] = compact_view_packet
            compact_rows.append(compact_row)
        packet["selected_rows"] = compact_rows
        packet.setdefault("omitted", []).append(
            {
                "section": "selected_rows.rich_payloads",
                "reason": "hard ceiling handle compaction preserves row handles and drilldowns instead of carrying full card payloads",
                "drilldown": "./repo-python kernel.py --row <kind_id>:<row_id> --band card",
            }
        )

    def compact_navigation_index_first_opening(opening: Any) -> dict[str, Any]:
        if not isinstance(opening, Mapping):
            return {}
        return {
            key: opening.get(key)
            for key in (
                "kind_id",
                "title",
                "command",
                "surface_role",
                "allowed_after",
                "reason",
                "matched_intent_id",
            )
            if opening.get(key) not in (None, "", [], {})
        }

    def hard_ceiling_navigation_index_spine() -> None:
        spine = packet.get("navigation_index_spine")
        if not isinstance(spine, Mapping):
            return
        summary = spine.get("summary") if isinstance(spine.get("summary"), Mapping) else {}
        route_digest = spine.get("route_digest") if isinstance(spine.get("route_digest"), Mapping) else {}
        currentness = spine.get("currentness") if isinstance(spine.get("currentness"), Mapping) else {}
        entry_intent_openings = (
            spine.get("entry_intent_openings") if isinstance(spine.get("entry_intent_openings"), Mapping) else {}
        )
        task_conditioned = (
            entry_intent_openings.get("task_conditioned")
            if isinstance(entry_intent_openings.get("task_conditioned"), Mapping)
            else {}
        )
        coverage_receipt = (
            spine.get("coverage_closure_receipt")
            if isinstance(spine.get("coverage_closure_receipt"), Mapping)
            else {}
        )
        top_projection_gaps: list[dict[str, Any]] = []
        for gap in list(spine.get("top_projection_gaps") or [])[:3]:
            if not isinstance(gap, Mapping):
                continue
            top_projection_gaps.append(
                {
                    key: gap.get(key)
                    for key in (
                        "kind_id",
                        "title",
                        "gap_count",
                        "source_drilldown_command",
                        "coverage_surface_command",
                    )
                    if gap.get(key) not in (None, "", [], {})
                }
            )
        compact_groups: list[dict[str, Any]] = []
        kind_group_rollup = (
            spine.get("kind_group_rollup") if isinstance(spine.get("kind_group_rollup"), Mapping) else {}
        )
        if isinstance(kind_group_rollup, Mapping):
            for group in list(kind_group_rollup.get("groups") or [])[:1]:
                if not isinstance(group, Mapping):
                    continue
                recommended_openings: list[dict[str, Any]] = []
                for opening in list(group.get("recommended_openings") or [])[:1]:
                    if not isinstance(opening, Mapping):
                        continue
                    recommended_openings.append(
                        {
                            key: opening.get(key)
                            for key in ("kind_id", "surface_role", "command")
                            if opening.get(key) not in (None, "", [], {})
                        }
                    )
                compact_groups.append(
                    {
                        key: value
                        for key, value in {
                            "group_id": group.get("group_id"),
                            "label": group.get("label"),
                            "row_level_gap_count": group.get("row_level_gap_count"),
                            "coverage_status": group.get("coverage_status"),
                            "top_gap_kind_ids": list(group.get("top_gap_kind_ids") or [])[:2],
                            "recommended_openings": recommended_openings,
                        }.items()
                        if value not in (None, "", [], {})
                    }
                )
        if aggressive_hard_ceiling_economy:
            coverage_closure_value = {
                receipt_key: coverage_receipt.get(receipt_key)
                for receipt_key in (
                    "schema_version",
                    "status",
                    "coverage_surface_available_count",
                    "coverage_surface_gap_count",
                    "behavior_watch_status",
                    "matrix_command",
                )
                if coverage_receipt.get(receipt_key) not in (None, "", [], {})
            }
            if task_conditioned:
                reentry_receipt = (
                    task_conditioned.get("reentry_receipt")
                    if isinstance(task_conditioned.get("reentry_receipt"), Mapping)
                    else {}
                )
                entry_intent_value = {
                    "task_conditioned": {
                        "matched_intent_ids": list(task_conditioned.get("matched_intent_ids") or [])[:3],
                        "first_opening": compact_navigation_index_first_opening(
                            task_conditioned.get("first_opening")
                        ),
                        "reentry_receipt": {
                            receipt_key: reentry_receipt.get(receipt_key)
                            for receipt_key in (
                                "schema_version",
                                "status",
                                "first_kind_id",
                                "first_command",
                                "handoff_step_count",
                            )
                            if reentry_receipt.get(receipt_key) not in (None, "", [], {})
                        },
                    }
                }
            else:
                entry_intent_value = None
        else:
            coverage_closure_value = compact_coverage_closure_receipt(
                spine.get("coverage_closure_receipt")
            )
            entry_intent_value = (
                {
                    "default_control_sequence": compact_sequence_steps(
                        entry_intent_openings.get("default_control_sequence"),
                        3,
                    ),
                    "task_conditioned": {
                        "matched_intent_count": task_conditioned.get("matched_intent_count"),
                        "matched_intent_ids": list(task_conditioned.get("matched_intent_ids") or [])[:3],
                        "selected_openings": list(task_conditioned.get("selected_openings") or [])[:2],
                        "first_opening": compact_navigation_index_first_opening(
                            task_conditioned.get("first_opening")
                        ),
                        "handoff_sequence": compact_sequence_steps(
                            task_conditioned.get("handoff_sequence"),
                            3,
                        ),
                        "reentry_receipt": compact_reentry_receipt(task_conditioned.get("reentry_receipt")),
                    }
                }
                if task_conditioned
                else None
            )
        packet["navigation_index_spine"] = {
            key: value
            for key, value in {
                "schema_version": spine.get("schema_version"),
                "surface_role": spine.get("surface_role"),
                "authority_posture": spine.get("authority_posture"),
                "available": spine.get("available"),
                "summary": {
                    summary_key: summary.get(summary_key)
                    for summary_key in (
                        "artifact_kind_count",
                        "kind_group_count",
                        "row_level_projection_gap_count",
                        "entry_visible_kind_count",
                        "coverage_surface_gap_count",
                        "high_cardinality_cluster_gap_count",
                        "coverage_closure_status",
                        "top_gap_group_id",
                    )
                    if summary.get(summary_key) not in (None, "", [], {})
                },
                "route_digest": {
                    digest_key: route_digest.get(digest_key)
                    for digest_key in (
                        "kind_atlas_available",
                        "entry_visible_kind_count",
                        "coverage_surface_available_count",
                        "coverage_surface_gap_count",
                        "high_cardinality_cluster_gap_count",
                        "first_contact_policy",
                    )
                    if route_digest.get(digest_key) not in (None, "", [], {})
                },
                "coverage_closure_receipt": coverage_closure_value,
                "kind_group_rollup": {
                    "schema_version": kind_group_rollup.get("schema_version"),
                    "group_count": kind_group_rollup.get("group_count"),
                    "groups": compact_groups,
                    "hard_ceiling_handle_compacted": True,
                }
                if compact_groups
                else None,
                "entry_intent_openings": entry_intent_value,
                "top_projection_gaps": top_projection_gaps,
                "recursive_seed_handoff": None
                if aggressive_hard_ceiling_economy
                else spine.get("recursive_seed_handoff"),
                "entry_policy": spine.get("entry_policy"),
                "currentness": {
                    current_key: currentness.get(current_key)
                    for current_key in (
                        "status",
                        "source_coupling_status",
                        "changed_source_count",
                        "safe_to_commit_generated_outputs_without_sources",
                        "freshness_command",
                    )
                    if currentness.get(current_key) not in (None, "", [], {})
                },
                "source_refs": list(spine.get("source_refs") or [])[:3],
                "omission_receipt": {
                    "omitted": [
                        "coverage closure drilldown sequence",
                        "kind group rollup",
                        "full entry intent catalog",
                        "full projection gap rows",
                    ],
                    "reason": "Hard ceiling compaction kept entry-visible route handles and source-coupling status; full detail remains behind System Atlas drilldowns.",
                    "drilldown": "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
                },
                "trimmed_for_context_pack_budget": True,
                "hard_ceiling_handle_compacted": True,
            }.items()
            if value not in (None, "", [], {})
        }

    def hard_ceiling_compact_omitted(max_rows: int = 6) -> None:
        omitted_rows = [row for row in list(packet.get("omitted") or []) if isinstance(row, Mapping)]
        total_count = len(omitted_rows)
        compact_rows: list[dict[str, Any]] = []
        for row in omitted_rows[:max_rows]:
            compact_rows.append(
                {
                    key: row.get(key)
                    for key in ("kind_id", "row_id", "section", "reason", "drilldown")
                    if row.get(key) not in (None, "", [], {})
                }
            )
        if total_count > max_rows:
            compact_rows.append(
                {
                    "section": "omitted.extra_rows",
                    "omitted_count": total_count - max_rows,
                    "reason": "hard ceiling compaction summarized additional omitted rows",
                    "drilldown": "./repo-python kernel.py --context-pack \"<task>\" --context-budget <larger-budget>",
                }
            )
        packet["omitted"] = compact_rows

    def protected_selected_row(row: Mapping[str, Any]) -> bool:
        if (str(row.get("kind_id") or ""), str(row.get("row_id") or "")) in BUDGET_TRIM_PROTECTED_ROWS:
            return True
        if str(row.get("kind_id") or "") == "cognitive_operators":
            return True
        return str(row.get("selection_source_kind") or "") in {
            "python_target_resolution",
            "workitem_target_resolution",
            "system_atlas_protocol_anchor",
            "state_axis_artifact_anchor",
            "config_plane_protocol_anchor",
            "operator_thread_continuation_card_anchor",
            "skill_registry_context_pack_anchor",
            "type_a_autonomous_seed_anchor",
            "speed_refinement_command_telemetry_anchor",
        }

    def trim_overview_rows(max_rows: int) -> None:
        overview_rows = list(packet.get("overview") or [])
        if len(overview_rows) <= max_rows:
            packet["overview"] = overview_rows
            return
        keep_ids = [str(row.get("kind_id") or "") for row in overview_rows[:max_rows]]
        for row in overview_rows[max_rows:]:
            kind_id = str(row.get("kind_id") or "")
            if kind_id not in OVERVIEW_TRIM_PROTECTED_KIND_IDS or kind_id in keep_ids:
                continue
            for index in range(len(keep_ids) - 1, -1, -1):
                if keep_ids[index] not in OVERVIEW_TRIM_PROTECTED_KIND_IDS:
                    keep_ids.pop(index)
                    break
            if len(keep_ids) < max_rows:
                keep_ids.append(kind_id)
        keep_id_set = set(keep_ids)
        packet["overview"] = [
            row for row in overview_rows if str(row.get("kind_id") or "") in keep_id_set
        ][:max_rows]

    def trim_clusters(max_clusters: int, max_top_ids: int, *, drop_drilldown: bool = False) -> None:
        for overview_row in packet.get("overview") or []:
            clusters = overview_row.get("clusters")
            if isinstance(clusters, list):
                for cluster in clusters:
                    if isinstance(cluster, dict):
                        cluster["top_ids"] = list(cluster.get("top_ids") or [])[:max_top_ids]
                        if drop_drilldown:
                            cluster.pop("drilldown", None)
                overview_row["clusters"] = clusters[:max_clusters]

    def section_bytes(key: str) -> int:
        value = packet.get(key)
        if value in (None, "", [], {}):
            return 0
        return _json_bytes({key: value})

    def apply_routine_byte_soft_ceiling() -> None:
        if not routine_byte_economy_active:
            return
        if _estimate_tokens(packet) > effective_budget:
            return
        budget_state = packet.setdefault("budget", {})
        if budget_state.get("hard_ceiling_repair_status"):
            return
        before_output_bytes = _json_bytes(packet)
        before_selected_rows_bytes = section_bytes("selected_rows")
        triggered_by: list[str] = []
        if before_output_bytes > ROUTINE_CONTEXT_PACK_SOFT_CEILING_BYTES:
            triggered_by.append("output_bytes")
        if before_selected_rows_bytes > ROUTINE_CONTEXT_PACK_SELECTED_ROWS_SOFT_CEILING_BYTES:
            triggered_by.append("selected_rows_bytes")
        if not triggered_by:
            return

        hard_ceiling_selected_row_handles()
        spine_compacted = False
        if (
            _json_bytes(packet) > ROUTINE_CONTEXT_PACK_SOFT_CEILING_BYTES
            and isinstance(packet.get("navigation_index_spine"), Mapping)
        ):
            hard_ceiling_navigation_index_spine()
            spine_compacted = True
        if _json_bytes(packet) > ROUTINE_CONTEXT_PACK_SOFT_CEILING_BYTES:
            trim_overview_rows(12)
            packet["landmines"] = list(packet.get("landmines") or [])[:2]
            packet["next_commands"] = _trim_next_command_objects(
                packet.get("next_commands") or [],
                4,
            )

        receipt = {
            "status": "selected_row_handle_compaction_applied",
            "triggered_by": triggered_by,
            "output_soft_ceiling_bytes": ROUTINE_CONTEXT_PACK_SOFT_CEILING_BYTES,
            "selected_rows_soft_ceiling_bytes": ROUTINE_CONTEXT_PACK_SELECTED_ROWS_SOFT_CEILING_BYTES,
            "before_output_bytes": before_output_bytes,
            "before_selected_rows_bytes": before_selected_rows_bytes,
            "spine_handle_compaction_applied": spine_compacted,
        }
        packet.setdefault("budget", {})["routine_byte_soft_ceiling"] = receipt
        packet.setdefault("omitted", []).append(
            {
                "section": "routine_byte_soft_ceiling",
                "reason": (
                    "routine context-pack crossed byte soft ceilings even though the token contract fit; "
                    "selected rows were collapsed to handles with drilldowns"
                ),
                "drilldown": (
                    "./repo-python kernel.py --context-pack \"<task>\" "
                    "--context-budget 20000"
                ),
            }
        )
        receipt["after_output_bytes"] = _json_bytes(packet)
        receipt["after_selected_rows_bytes"] = section_bytes("selected_rows")

    if _estimate_tokens(packet) > effective_budget:
        spine = packet.get("navigation_index_spine")
        if isinstance(spine, dict):
            spine["top_projection_gaps"] = list(spine.get("top_projection_gaps") or [])[:4]
            spine["legal_drilldowns"] = list(spine.get("legal_drilldowns") or [])[:4]
            spine["coverage_closure_receipt"] = compact_coverage_closure_receipt(
                spine.get("coverage_closure_receipt")
            )
            kind_group_rollup = spine.get("kind_group_rollup")
            if isinstance(kind_group_rollup, dict):
                compact_groups: list[dict[str, Any]] = []
                for group in list(kind_group_rollup.get("groups") or [])[:4]:
                    if not isinstance(group, Mapping):
                        continue
                    compact_group = dict(group)
                    compact_group["kind_ids"] = list(compact_group.get("kind_ids") or [])[:8]
                    compact_group["top_gap_kind_ids"] = list(compact_group.get("top_gap_kind_ids") or [])[:4]
                    compact_group["coverage_surface_gap_kind_ids"] = list(
                        compact_group.get("coverage_surface_gap_kind_ids") or []
                    )[:4]
                    compact_group["recommended_openings"] = list(
                        compact_group.get("recommended_openings") or []
                    )[:1]
                    compact_group["drilldown_commands"] = list(compact_group.get("drilldown_commands") or [])[:1]
                    compact_groups.append(compact_group)
                kind_group_rollup["groups"] = compact_groups
                kind_group_rollup["trimmed_for_context_pack_budget"] = True
            entry_intent_openings = spine.get("entry_intent_openings")
            if isinstance(entry_intent_openings, dict):
                entry_intent_openings["default_control_sequence"] = compact_sequence_steps(
                    entry_intent_openings.get("default_control_sequence"),
                    3,
                )
                compact_intents: list[dict[str, Any]] = []
                for intent in list(entry_intent_openings.get("intents") or [])[:3]:
                    if not isinstance(intent, Mapping):
                        continue
                    compact_intent = dict(intent)
                    compact_intent["trigger_terms"] = list(compact_intent.get("trigger_terms") or [])[:3]
                    compact_intent["fallback_openings"] = []
                    compact_intents.append(compact_intent)
                entry_intent_openings["intents"] = compact_intents
                task_conditioned = entry_intent_openings.get("task_conditioned")
                if isinstance(task_conditioned, dict):
                    task_conditioned["matched_intents"] = list(task_conditioned.get("matched_intents") or [])[:2]
                    task_conditioned["selected_openings"] = list(task_conditioned.get("selected_openings") or [])[:2]
                    task_conditioned["handoff_sequence"] = compact_sequence_steps(
                        task_conditioned.get("handoff_sequence"),
                        3,
                    )
                    task_conditioned["reentry_receipt"] = compact_reentry_receipt(
                        task_conditioned.get("reentry_receipt")
                    )
                entry_intent_openings["trimmed_for_context_pack_budget"] = True
            spine["omission_receipt"] = {
                "omitted": ["full graph payload", "full findings", "source bodies"],
                "reason": "Trimmed for context-pack budget; rerun System Atlas drilldowns for full detail.",
                "drilldown": "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
            }
        for max_clusters, max_top_ids, drop_drilldown in (
            (4, 3, False),
            (3, 2, False),
            (2, 2, True),
            (1, 1, True),
        ):
            trim_clusters(max_clusters, max_top_ids, drop_drilldown=drop_drilldown)
            if _estimate_tokens(packet) <= effective_budget:
                break
    if _estimate_tokens(packet) > effective_budget:
        for max_overview_rows in (24, 16, 12):
            trim_overview_rows(max_overview_rows)
            if _estimate_tokens(packet) <= effective_budget:
                break
    while _estimate_tokens(packet) > effective_budget and len(packet.get("selected_rows") or []) > 4:
        selected_rows = packet["selected_rows"]
        pop_index: int | None = None
        for index in range(len(selected_rows) - 1, -1, -1):
            if not protected_selected_row(selected_rows[index]):
                pop_index = index
                break
        if pop_index is None:
            break
        row = selected_rows.pop(pop_index)
        omitted.append(
            {
                "kind_id": row.get("kind_id"),
                "row_id": row.get("row_id"),
                "reason": "dropped by final budget trim",
                "drilldown": row.get("drilldown_command"),
            }
        )
    if _estimate_tokens(packet) > effective_budget:
        spine = packet.get("navigation_index_spine")
        entry_intent_openings = spine.get("entry_intent_openings") if isinstance(spine, dict) else None
        if isinstance(entry_intent_openings, dict):
            entry_intent_openings["default_control_sequence"] = compact_sequence_steps(
                entry_intent_openings.get("default_control_sequence"),
                2,
            )
            entry_intent_openings["intents"] = []
            task_conditioned = entry_intent_openings.get("task_conditioned")
            if isinstance(task_conditioned, dict):
                task_conditioned["matched_intents"] = list(task_conditioned.get("matched_intents") or [])[:1]
                task_conditioned["selected_openings"] = list(task_conditioned.get("selected_openings") or [])[:1]
                task_conditioned["handoff_sequence"] = compact_sequence_steps(
                    task_conditioned.get("handoff_sequence"),
                    3,
                )
                task_conditioned["reentry_receipt"] = compact_reentry_receipt(
                    task_conditioned.get("reentry_receipt")
                )
            entry_intent_openings["omitted_for_context_pack_budget"] = [
                "entry intent catalog rows beyond task-conditioned first opening"
            ]
        if isinstance(spine, dict):
            spine["coverage_closure_receipt"] = compact_coverage_closure_receipt(
                spine.get("coverage_closure_receipt")
            )
    if _estimate_tokens(packet) > effective_budget:
        packet["landmines"] = list(packet.get("landmines") or [])[:4]
        packet["next_commands"] = _trim_next_command_objects(packet.get("next_commands") or [], 5)
    if _estimate_tokens(packet) > effective_budget:
        spine = packet.get("navigation_index_spine")
        if isinstance(spine, dict):
            spine["top_projection_gaps"] = list(spine.get("top_projection_gaps") or [])[:4]
            spine["legal_drilldowns"] = list(spine.get("legal_drilldowns") or [])[:3]
            spine["source_refs"] = list(spine.get("source_refs") or [])[:4]
            spine["coverage_closure_receipt"] = compact_coverage_closure_receipt(
                spine.get("coverage_closure_receipt")
            )
            route_digest = spine.get("route_digest")
            if isinstance(route_digest, dict):
                route_digest["top_route_rungs"] = list(route_digest.get("top_route_rungs") or [])[:3]
            kind_group_rollup = spine.get("kind_group_rollup")
            if isinstance(kind_group_rollup, dict):
                compact_groups = []
                for group in list(kind_group_rollup.get("groups") or [])[:2]:
                    if not isinstance(group, Mapping):
                        continue
                    compact_group = dict(group)
                    compact_group["kind_ids"] = list(compact_group.get("kind_ids") or [])[:5]
                    compact_group["top_gap_kind_ids"] = list(compact_group.get("top_gap_kind_ids") or [])[:2]
                    compact_group["recommended_openings"] = list(
                        compact_group.get("recommended_openings") or []
                    )[:1]
                    compact_group["drilldown_commands"] = []
                    compact_groups.append(compact_group)
                kind_group_rollup["groups"] = compact_groups
                kind_group_rollup["extra_trimmed_for_context_pack_budget"] = True
        packet["overview"] = list(packet.get("overview") or [])[:8]
        packet["landmines"] = list(packet.get("landmines") or [])[:2]
        next_commands = list(packet.get("next_commands") or [])
        packet["next_commands"] = _trim_next_command_objects(next_commands, 5)
        if _estimate_tokens(packet) > effective_budget:
            packet["next_commands"] = _trim_next_command_objects(next_commands, 3)
    if _estimate_tokens(packet) > effective_budget:
        for diagnostic_key in (
            "entry_surface_diagnostics",
            "paper_module_freshness_diagnostics",
            "capture_reflex_diagnostics",
            "compliance_diagnostics",
        ):
            if isinstance(packet.get(diagnostic_key), Mapping):
                packet[diagnostic_key] = compact_diagnostic_rows(packet.get(diagnostic_key), max_rows=2)
        candidate_pressure = packet.get("candidate_runtime_pressure")
        if isinstance(candidate_pressure, dict):
            candidate_pressure["suppressed_rows"] = list(candidate_pressure.get("suppressed_rows") or [])[:1]
            candidate_pressure["trimmed_for_context_pack_budget"] = True
    if _estimate_tokens(packet) > effective_budget:
        compact_navigation_index_spine()
    if aggressive_hard_ceiling_economy and _estimate_tokens(packet) > effective_budget:
        before_output_bytes = _json_bytes(packet)
        before_selected_rows_bytes = section_bytes("selected_rows")
        hard_ceiling_selected_row_handles()
        hard_ceiling_navigation_index_spine()
        packet.setdefault("budget", {})["routine_speed_economy"] = {
            "status": "selected_row_handle_compaction_applied",
            "triggered_by": [
                "speed_or_context_economy_query",
                "autonomous_seed_economy_query",
            ],
            "before_output_bytes": before_output_bytes,
            "before_selected_rows_bytes": before_selected_rows_bytes,
            "after_output_bytes": _json_bytes(packet),
            "after_selected_rows_bytes": section_bytes("selected_rows"),
        }
    if _estimate_tokens(packet) > effective_budget:
        compact_selected_rows(4)
        packet["overview"] = list(packet.get("overview") or [])[:6]
        packet["landmines"] = list(packet.get("landmines") or [])[:1]
        packet["next_commands"] = _trim_next_command_objects(packet.get("next_commands") or [], 2)
        packet["source_surfaces"] = _trim_source_surfaces(packet.get("source_surfaces") or [], 8)
    if _estimate_tokens(packet) > effective_budget:
        packet.setdefault("budget", {})["hard_ceiling_repair_status"] = "last_resort_compaction_required"
        compact_selected_rows(3)
        packet["overview"] = list(packet.get("overview") or [])[:3]
        packet["landmines"] = []
        packet["next_commands"] = _trim_next_command_objects(packet.get("next_commands") or [], 1)
    if _estimate_tokens(packet) > effective_budget:
        packet.setdefault("budget", {})["hard_ceiling_repair_status"] = "last_resort_selected_row_field_compaction"
        ultra_compact_selected_rows()
        packet["source_surfaces"] = _trim_source_surfaces(packet.get("source_surfaces") or [], 4)
    if _estimate_tokens(packet) > effective_budget:
        packet.setdefault("budget", {})["hard_ceiling_repair_status"] = "hard_ceiling_handle_compaction"
        hard_ceiling_selected_row_handles()
        hard_ceiling_navigation_index_spine()
        hard_ceiling_compact_omitted()
        packet["overview"] = list(packet.get("overview") or [])[:2]
        packet["next_commands"] = _trim_next_command_objects(packet.get("next_commands") or [], 1)
        packet["source_surfaces"] = _trim_source_surfaces(packet.get("source_surfaces") or [], 4)
    if _estimate_tokens(packet) > effective_budget:
        packet.setdefault("budget", {})[
            "hard_ceiling_repair_status"
        ] = "hard_ceiling_nonessential_section_omission"
        if isinstance(packet.get("candidate_runtime_pressure"), Mapping):
            packet["candidate_runtime_pressure"] = compact_candidate_runtime_pressure_for_context_budget(
                packet.get("candidate_runtime_pressure")
            )
        if isinstance(packet.get("transaction_control_plane"), Mapping):
            packet["transaction_control_plane"] = {
                "status": "omitted_for_hard_ceiling",
                "reason": "transaction control-plane detail omitted after selected rows and freshness receipts were preserved",
                "drilldown": (
                    "./repo-python kernel.py --context-pack \"transaction control plane <task>\" "
                    "--context-budget 20000"
                ),
            }
        agent_packet = (
            packet.get("agent_operating_packet")
            if isinstance(packet.get("agent_operating_packet"), Mapping)
            else {}
        )
        if agent_packet:
            packet["agent_operating_packet"] = {
                key: value
                for key, value in {
                    "kind": agent_packet.get("kind"),
                    "status": agent_packet.get("status"),
                    "global_principle_ids": list(agent_packet.get("global_principle_ids") or [])[:6],
                    "agent_principle_ids": list(agent_packet.get("agent_principle_ids") or [])[:8],
                    "strip_command": agent_packet.get("strip_command"),
                    "global_capsule_command": agent_packet.get("global_capsule_command"),
                    "trimmed_for_context_pack_budget": True,
                }.items()
                if value not in (None, "", [], {})
            }
        packet.setdefault("omitted", []).append(
            {
                "section": "nonessential_sections",
                "reason": (
                    "hard ceiling preserved selected-row handles, source-coupling currentness, "
                    "and navigation-index receipts before omitting lower-priority sections"
                ),
                "drilldown": (
                    "./repo-python kernel.py --context-pack \"<task>\" "
                    "--context-budget 20000"
                ),
            }
        )
    apply_routine_byte_soft_ceiling()
    return packet


def build_navigation_context_pack(
    repo_root: Path | str,
    query: str,
    *,
    context_budget: int = 12000,
    include_semantic: bool | None = None,
    semantic_timeout_ms: int = DEFAULT_SEMANTIC_TIMEOUT_MS,
    profile: str | None = None,
    include_transaction_control_plane: bool | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    budget = max(1000, int(context_budget or 12000))
    normalized_profile = str(profile or os.environ.get("AIW_CONTEXT_PACK_PROFILE") or "routine").strip().lower()
    if normalized_profile not in {"routine", "deep"}:
        normalized_profile = "routine"
    timings: dict[str, int] = {}
    stage_start = time.perf_counter()
    atlas = build_kind_atlas(root, band="flag", fast=normalized_profile == "routine")
    timings["kind_atlas"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    atlas_rows = [dict(row) for row in atlas.get("rows", []) if isinstance(row, Mapping)]
    if normalized_profile == "routine" and include_semantic is None:
        semantic_candidates = []
        semantic_status = _deferred_semantic_status(query)
    else:
        semantic_candidates, semantic_status = _semantic_candidates(
            root,
            query,
            include_semantic=include_semantic,
            semantic_timeout_ms=semantic_timeout_ms,
        )
    timings["semantic_candidates"] = int(round((time.perf_counter() - stage_start) * 1000))
    if isinstance(semantic_status, dict):
        semantic_status["wall_ms"] = timings["semantic_candidates"]
    stage_start = time.perf_counter()
    workitem_target_resolution = resolve_workitem_targets(root, query)
    timings["workitem_target_resolution"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    if _should_skip_python_target_resolution_for_workitem(query, workitem_target_resolution):
        python_target_resolution = _python_target_resolution_skipped_for_workitem(
            query,
            workitem_target_resolution,
        )
    else:
        python_target_resolution = _suppress_python_unresolved_for_workitem_hints(
            resolve_python_targets(root, query),
            workitem_target_resolution,
        )
    timings["python_target_resolution"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    candidates = _merge_candidates(
        root,
        semantic_candidates,
        query,
        workitem_target_resolution=workitem_target_resolution,
        python_target_resolution=python_target_resolution,
    )
    timings["anchor_merge"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    selected_rows, unresolved = _selected_rows(root, candidates, query=query)
    timings["selected_rows"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    reserve_tokens = 0
    if (
        normalized_profile == "routine"
        and budget <= 12000
        and budget > ROUTINE_CONTEXT_PACK_SOFT_CEILING_TOKENS
    ):
        reserve_tokens = max(
            0,
            budget - BUDGET_METADATA_HEADROOM_TOKENS - ROUTINE_CONTEXT_PACK_SOFT_CEILING_TOKENS,
        )
    elif normalized_profile == "routine" and budget > 12000:
        reserve_tokens = ROUTINE_LARGE_BUDGET_RESERVE_TOKENS
    overview_rows, overview_status = _overview(
        root,
        atlas_rows,
        profile=normalized_profile,
        compact_routine_deferred_status=bool(reserve_tokens),
    )
    timings["overview"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    candidate_pressure = filter_first_contact_candidate_pressure(
        candidate_runtime_pressure_rows(root, query)
    )
    timings["candidate_runtime_pressure"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    no_edit_pass_floor = no_edit_pass_floor_card(root, query)
    if no_edit_pass_floor is not None:
        timings["no_edit_pass_floor"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    agent_operating_packet = load_agent_operating_packet_strip(root)
    timings["agent_operating_packet"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    entry_surface_content_sync_mode = (
        "source_coupling_only" if normalized_profile == "routine" else "auto"
    )
    entry_surface_diagnostics = project_entry_surface_diagnostics(
        root,
        query,
        structural_triggers=_entry_surface_structural_triggers_from_selected_rows(selected_rows),
        content_sync_mode=entry_surface_content_sync_mode,
    )
    timings["entry_surface_diagnostics"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    compliance_diagnostics = project_compliance_diagnostics(root, query)
    timings["compliance_diagnostics"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    capture_reflex_diagnostics = project_capture_reflex_diagnostics(root, query)
    capture_reflex_elapsed = int(round((time.perf_counter() - stage_start) * 1000))
    if capture_reflex_diagnostics.get("triggered"):
        timings["capture_reflex_diagnostics"] = capture_reflex_elapsed
    stage_start = time.perf_counter()
    paper_module_freshness_diagnostics = project_paper_module_freshness_diagnostics(root, query)
    paper_module_freshness_elapsed = int(round((time.perf_counter() - stage_start) * 1000))
    if paper_module_freshness_diagnostics.get("triggered"):
        timings["paper_module_freshness_diagnostics"] = paper_module_freshness_elapsed
    stage_start = time.perf_counter()
    mission_trace_current_state = _mission_trace_current_state_context(root)
    timings["mission_trace_current_state"] = int(round((time.perf_counter() - stage_start) * 1000))
    stage_start = time.perf_counter()
    dirty_tree_bankruptcy_pressure = _dirty_tree_bankruptcy_pressure_context(root, query)
    if dirty_tree_bankruptcy_pressure is not None:
        timings["dirty_tree_bankruptcy_pressure"] = int(round((time.perf_counter() - stage_start) * 1000))
    lattice_commands = [
        str(((row.get("drilldowns") or {}).get("lattice")))
        for row in selected_rows
        if isinstance(row.get("drilldowns"), Mapping) and (row.get("drilldowns") or {}).get("lattice")
    ]
    include_navigation_index_spine = not _is_system_crystal_query(query) and (
        _is_system_atlas_query(query)
        or is_root_navigator_ai_native_query(query)
        or any(str(row.get("kind_id") or "") == "system_atlas" for row in selected_rows)
        or any(str(row.get("kind_id") or "") == "cognitive_operators" for row in selected_rows)
    )
    navigation_index_spine = (
        build_navigation_index_spine(root, max_gap_kinds=6, kind_atlas_rows=atlas_rows, task_text=query)
        if include_navigation_index_spine
        else None
    )
    stage_start = time.perf_counter()
    operator_thread_card_context = _operator_thread_continuation_card_context(root, query)
    if operator_thread_card_context is not None:
        timings["operator_thread_continuation_card"] = int(round((time.perf_counter() - stage_start) * 1000))

    packet: dict[str, Any] = {
        "kind": "navigation_context_pack",
        "schema_version": "navigation_context_pack_v0",
        "surface_role": "CONTROL_ENTRY",
        "first_contact_allowed": True,
        "generated_at": _utc_now(),
        "query": query,
        "budget": {
            "requested_tokens": budget,
            "hard_ceiling": True,
            "enforcement": "selection_before_render",
        },
        "strategy": {
            "selection_model": "coverage_first_information_density_knapsack_v1",
            "profile": normalized_profile,
            "routine_budget_ms": ROUTINE_CONTEXT_PACK_BUDGET_MS,
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "mixed_band": True,
            "cluster_before_row_expansion": True,
            "selected_rows_role": "SELECTED_CONTEXT",
            "selected_rows_are_not_control_edges": True,
            "next_commands_role": "drilldown_hints_not_route_authority",
            "entry_surface_diagnostics_content_sync_mode": entry_surface_content_sync_mode,
            "semantic_status": semantic_status,
            "overview_status": overview_status,
            "stage_timings_ms": timings,
        },
        "overview": overview_rows,
        "selected_rows": selected_rows,
        "agent_operating_packet": agent_operating_packet,
        "candidate_runtime_pressure": {
            **candidate_pressure,
            "contract_ref": "codex/standards/std_agent_entry_surface.json::candidate_runtime_pressure_contract",
            "source_standard": "codex/standards/principles/std_system_axiom_candidate.json::promotion_contract.candidate_to_runtime_packet",
            "non_law_warning": "Candidate axioms surfaced as provisional pressure; not active doctrine. Do not treat as binding.",
            "match_strategy": "layered_priority_explicit_id_then_explicit_slug_then_workitem_evidence_overlap_then_deterministic_query_overlap_min_2",
            "match_strategy_ref": "codex/standards/std_agent_entry_surface.json::candidate_runtime_pressure_contract::match_strategy",
        },
        "no_edit_pass_floor": no_edit_pass_floor,
        "entry_surface_diagnostics": entry_surface_diagnostics,
        "compliance_diagnostics": compliance_diagnostics,
        "capture_reflex_diagnostics": capture_reflex_diagnostics,
        "mission_trace_current_state": mission_trace_current_state,
        "omitted": unresolved,
        "landmines": _landmines(atlas_rows),
        "next_commands": _next_command_objects(selected_rows, lattice_commands),
        "source_surfaces": [
            "system/lib/kind_atlas.py",
            "system/lib/standard_option_surface.py",
            "system/lib/agent_operating_packet.py",
            "system/lib/semantic_routing.py",
            "codex/standards/std_navigation_rosetta_grammar.json",
            "codex/standards/principles/std_system_axiom_candidate.json",
            "codex/standards/std_agent_entry_surface.json",
            "codex/doctrine/command_cards/agent_movement.json",
            str(MISSION_OPERATING_PICTURE_REL),
        ],
    }
    if python_target_resolution.get("status") == "unresolved":
        packet["python_target_resolution"] = python_target_resolution
        packet["source_surfaces"].append("system/lib/python_target_resolution.py")
    if workitem_target_resolution.get("status") != "no_workitem_target":
        packet["workitem_target_resolution"] = workitem_target_resolution
        packet["source_surfaces"].append("system/lib/workitem_target_resolution.py")
    if no_edit_pass_floor is None:
        packet.pop("no_edit_pass_floor", None)
    if navigation_index_spine is not None:
        packet["navigation_index_spine"] = navigation_index_spine
        packet["source_surfaces"].append("system/lib/navigation_index_spine.py")
    if operator_thread_card_context is not None:
        packet["operator_thread_continuation_card"] = operator_thread_card_context
        packet["source_surfaces"].extend(
            [
                "tools/meta/observability/operator_thread_memory.py",
                "tools/meta/observability/operator_turn_stack_projection.py",
                "state/operator_bridge/thread_memory/",
            ]
        )
    if dirty_tree_bankruptcy_pressure is not None:
        packet["dirty_tree_bankruptcy_pressure"] = dirty_tree_bankruptcy_pressure
        packet["dirty_tree_pressure"] = {
            "schema": "dirty_tree_pressure_context_pack_alias_v0",
            "alias_of": "dirty_tree_bankruptcy_pressure",
            "status": dirty_tree_bankruptcy_pressure.get("status"),
            "authority_boundary": dirty_tree_bankruptcy_pressure.get("authority_boundary"),
            "projection_only": dirty_tree_bankruptcy_pressure.get("projection_only"),
            "safety_authority": dirty_tree_bankruptcy_pressure.get("safety_authority"),
            "source_view": dirty_tree_bankruptcy_pressure.get("source_view"),
            "source_command": dirty_tree_bankruptcy_pressure.get("source_command"),
            "bankruptcy_authorized": dirty_tree_bankruptcy_pressure.get(
                "bankruptcy_authorized"
            ),
            "dirty_scan_status": dirty_tree_bankruptcy_pressure.get("dirty_scan_status"),
            "dirty_total": dirty_tree_bankruptcy_pressure.get("dirty_total"),
            "class_counts": dirty_tree_bankruptcy_pressure.get("class_counts")
            or dirty_tree_bankruptcy_pressure.get("dirty_path_class_counts"),
            "operator_authorized_mainline_checkpoint": dirty_tree_bankruptcy_pressure.get(
                "operator_authorized_mainline_checkpoint"
            ),
            "active_claim_session_groups": dirty_tree_bankruptcy_pressure.get(
                "active_claim_session_groups"
            ),
            "scoped_work_unblock": dirty_tree_bankruptcy_pressure.get("scoped_work_unblock"),
            "containment_plan": dirty_tree_bankruptcy_pressure.get("containment_plan"),
            "repeat_policy": dirty_tree_bankruptcy_pressure.get("repeat_policy")
            or dirty_tree_bankruptcy_pressure.get("rescue_repeat_policy"),
            "next_safe_action": dirty_tree_bankruptcy_pressure.get("next_safe_action"),
            "commands": dirty_tree_bankruptcy_pressure.get("commands"),
        }
        packet["source_surfaces"].extend(
            [
                str(WORK_LEDGER_RUNTIME_STATUS_REL),
                "system/lib/work_ledger_runtime.py",
                "tools/meta/factory/work_ledger.py",
            ]
        )
    if any(str(row.get("kind_id") or "") == "cognitive_operators" for row in selected_rows):
        packet["source_surfaces"].extend(
            [
                "system/lib/cognitive_operator_registry.py",
                "codex/standards/std_cognitive_operator.json",
                "codex/doctrine/cognitive_operators.json",
            ]
        )
    if is_root_navigator_ai_native_query(query):
        try:
            from system.lib.frontend_surface_contracts import build_root_navigator_ai_native_context

            packet["root_navigator_ai_native_context"] = build_root_navigator_ai_native_context(root)
        except Exception as exc:  # noqa: BLE001 - context-pack should emit a receipt, not fail.
            packet["root_navigator_ai_native_context"] = {
                "schema": "root_navigator_ai_native_context_v0",
                "status": "unavailable",
                "reason": f"{type(exc).__name__}: {exc}",
                "view_agent_packet_command": "./repo-python kernel.py --view-agent-packet rootNavigator",
            }
        packet["source_surfaces"].extend(
            [
                "system/lib/frontend_surface_contracts.py",
                "system/lib/root_navigator_ai.py",
            ]
        )
    if paper_module_freshness_diagnostics.get("triggered"):
        packet["paper_module_freshness_diagnostics"] = paper_module_freshness_diagnostics
    transaction_query = query
    if include_transaction_control_plane is True and not _query_mentions_transaction_control_plane(query):
        transaction_query = f"transaction control plane {query}"
    if include_transaction_control_plane is True:
        transaction_control_plane = _transaction_control_plane_context(root, transaction_query)
    elif _query_mentions_transaction_control_plane(transaction_query):
        transaction_control_plane = _transaction_control_plane_hint()
    else:
        transaction_control_plane = None
    if transaction_control_plane is not None:
        packet["transaction_control_plane"] = transaction_control_plane
        packet["source_surfaces"].append("system/lib/mission_transaction_landing_preflight.py")
    if any(str(row.get("kind_id") or "") == "dissemination_gate" for row in selected_rows):
        packet["source_surfaces"].extend(
            [
                "tools/meta/factory/check_dissemination_atlas_gate.py",
                "docs/system_atlas/dissemination_gate_report.generated.md",
                "docs/system_atlas/disclosure_projection_map.md",
                "docs/dissemination/public_leaf_readiness_audit.md",
            ]
        )
    if any(str(row.get("kind_id") or "") == "prompt_shelf_metadata" for row in selected_rows):
        packet["source_surfaces"].extend(
            [
                "tools/meta/observability/prompt_shelf_runs_index.py",
                "state/prompt_shelf/prompt_shelf_runs_index.json",
                "obsidian/prompt_shelf/B2 Continue Ledger.md",
            ]
        )
    if any(str(row.get("kind_id") or "") == "system_crystal" for row in selected_rows):
        packet["source_surfaces"].extend(
            [
                "tools/meta/factory/build_system_crystal.py",
                "docs/system_crystal/system_crystal.generated.md",
            ]
        )
    if any(str(row.get("kind_id") or "") == "generated_projection_ownership" for row in selected_rows):
        packet["source_surfaces"].extend(
            [
                "system/lib/generated_projection_registry.py",
                "tools/meta/control/generated_state_drainer.py",
                "tools/meta/control/mission_transaction_preflight.py",
                "tools/meta/factory/build_system_atlas.py",
                "tools/meta/factory/build_root_coverage_state.py",
            ]
        )
    if normalized_profile == "routine" and budget <= 12000:
        _compact_routine_selected_row_affordances(packet)
        _compact_routine_landmines(packet)
    stage_start = time.perf_counter()
    packet = _budget_trim(packet, budget, reserve_tokens=reserve_tokens)
    timings["budget_trim"] = int(round((time.perf_counter() - stage_start) * 1000))
    estimated_tokens = int(_estimate_tokens(packet))
    packet["budget"]["estimated_tokens"] = estimated_tokens
    packet["budget"]["estimated_output_bytes"] = _json_bytes(packet)
    packet["budget"]["remaining_tokens"] = budget - estimated_tokens
    packet["budget"]["over_budget"] = estimated_tokens > budget
    packet["budget"]["contract_status"] = "over_budget" if estimated_tokens > budget else "within_budget"
    return packet
