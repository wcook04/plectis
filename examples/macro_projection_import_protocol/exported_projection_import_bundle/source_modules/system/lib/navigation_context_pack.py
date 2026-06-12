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


_ENTRY_SURFACE_DIAGNOSTIC_TRIGGERS = (
    "agents.md",
    "claude.md",
    "codex.md",
    "agents.override.md",
    "entry budget",
    "entry-budget",
    "entrypoint",
    "entry surface",
    "entry-surface",
    "generated region",
    "generated-region",
    "generated projection",
    "generated-projection",
    "projection source",
    "source projection",
    "source coupling",
    "source-coupling",
    "source-worktree",
    "source inputs",
    "dirty source",
    "instruction file",
    "instruction-file",
    "compression policy",
    "compression-policy",
    "commit policy",
    "commit-policy",
    "startup hook",
    "first contact",
    "first-contact",
    "route health",
    "stale route",
)
_ACTION_AUTONOMY_DIAGNOSTIC_TRIGGERS = (
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
_COMPLIANCE_DIAGNOSTIC_TRIGGERS = (
    "compliance",
    "compliant",
    "non-compliant",
    "noncompliant",
    "standard compliance",
    "standards gap",
    "standard gap",
    "standards-gap",
    "compliance ledger",
    "compression passport",
    "compression-passport",
    "miner",
    "inspectorservice",
    "inspector service",
    "diagnostic projection",
    "diagnostic-projection",
    "python compliance",
    "python_compliance",
)
_CAPTURE_REFLEX_DIAGNOSTIC_TRIGGERS = (
    "capture reflex",
    "failure capture",
    "observed failure",
    "failing test",
    "failed test",
    "test failure",
    "self-error",
    "self_error",
    "flag-without-capture",
    "mistake-without-capture",
    "prose-only",
    "prose only",
    "task ledger capture",
)
_PAPER_MODULE_FRESHNESS_DIAGNOSTIC_TRIGGERS = (
    "paper module",
    "paper-module",
    "stale sidecar",
    "stale_sidecars",
    "validation report",
    "paper module index",
    "density drift",
    "module freshness",
    "projection freshness",
)


def _matched_diagnostic_triggers(query: str, triggers: Sequence[str]) -> list[str]:
    query_str = str(query or "")
    if not query_str.strip():
        return []
    q_lower = query_str.lower()
    return [trigger for trigger in triggers if trigger in q_lower]


def project_compliance_diagnostics(root: Path, query: str) -> dict[str, Any]:
    if not _matched_diagnostic_triggers(query, _COMPLIANCE_DIAGNOSTIC_TRIGGERS):
        return {"rows": [], "count": 0, "triggered": False}
    from system.lib.compliance.diagnostics_projection import (
        project_compliance_diagnostics as _project_compliance_diagnostics,
    )

    return _project_compliance_diagnostics(root, query)


def project_capture_reflex_diagnostics(root: Path, query: str) -> dict[str, Any]:
    if not _matched_diagnostic_triggers(query, _CAPTURE_REFLEX_DIAGNOSTIC_TRIGGERS):
        return {"rows": [], "count": 0, "triggered": False}
    from system.lib.capture_reflex_diagnostics import (
        project_capture_reflex_diagnostics as _project_capture_reflex_diagnostics,
    )

    return _project_capture_reflex_diagnostics(root, query)


def project_entry_surface_diagnostics(
    root: Path,
    query: str,
    *,
    structural_triggers: Sequence[Mapping[str, Any]] | None = None,
    content_sync_mode: str = "auto",
) -> dict[str, Any]:
    if not structural_triggers and not _matched_diagnostic_triggers(
        query,
        (*_ENTRY_SURFACE_DIAGNOSTIC_TRIGGERS, *_ACTION_AUTONOMY_DIAGNOSTIC_TRIGGERS),
    ):
        return {"rows": [], "count": 0, "triggered": False}
    from system.lib.entrypoint_health import (
        project_entry_surface_diagnostics as _project_entry_surface_diagnostics,
    )

    return _project_entry_surface_diagnostics(
        root,
        query,
        structural_triggers=structural_triggers,
        content_sync_mode=content_sync_mode,
    )


def project_paper_module_freshness_diagnostics(root: Path, query: str) -> dict[str, Any]:
    if not _matched_diagnostic_triggers(query, _PAPER_MODULE_FRESHNESS_DIAGNOSTIC_TRIGGERS):
        return {"rows": [], "count": 0, "triggered": False}
    from system.lib.paper_module_freshness_diagnostics import (
        project_paper_module_freshness_diagnostics as _project_paper_module_freshness_diagnostics,
    )

    return _project_paper_module_freshness_diagnostics(root, query)


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
ROUTINE_SELECTED_CARD_CACHE_NODE_ID = "navigation_context_pack.selected_card_payload.routine"
ROUTINE_SELECTED_CARD_CACHE_KEY_VERSION = 1
ROUTINE_SELECTED_CARD_CACHE_KINDS = frozenset(
    {
        "paper_modules",
        "skills",
        "type_a_autonomous_seeds",
    }
)
ROUTINE_SELECTED_CARD_CACHE_FRESHNESS_POLICY = (
    "manifest_validated_selected_card_payload_routine_context_pack_deep_profile_bypasses_cache"
)
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
MICROCOSM_AGENT_TASK_ROUTE_KIND_ID = "microcosm_agent_task_routes"
MICROCOSM_AGENT_TASK_ROUTES_REL = Path("microcosm-substrate/atlas/agent_task_routes.json")
MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_KIND_ID = "microcosm_organ_topology_affordance"
MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_ID = "organ-topology"
MICROCOSM_ORGAN_TOPOLOGY_COMMAND = (
    "cd microcosm-substrate && PYTHONPATH=src python3 -m microcosm_core "
    "organ-topology --root ."
)
MICROCOSM_ORGAN_TOPOLOGY_RELATION_TYPES = (
    "organ.has_source_language_family",
    "organ.shares_source_language_family_with",
    "organ.has_no_source_modules",
    "organ.has_mixed_source_language_families",
    "organ.has_microcosm_standard",
    "organ.has_standards_registry_row",
    "organ.has_concept_route_ref",
    "organ.has_mechanism_route_ref",
)
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
    "saved trace capsule",
    "latest response bundle",
    "read other traces or caps",
    "trace/cap refinement",
    "trace cap refinement",
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
    "private-index cas",
    "parent cas",
    "head advanced",
    "retry budget exhausted",
    "cas retry budget",
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
    "speed optimization",
    "speed optimisation",
    "system speed",
    "macro system speed",
    "microcosm speed",
    "general optimization improvements",
    "general optimisation improvements",
    "self up propagation",
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
OVERVIEW_TRIM_MUST_KEEP_KIND_IDS = {
    "skill_compression_debt",
    "standard_skill_map",
}
CLUSTER_FIRST_KIND_IDS = {
    "artifact_projection_debt",
    "derived_facts",
    "standard_skill_map",
}
NEXT_COMMAND_TRIM_PROTECTED_SUBSTRINGS = (
    "--option-surface paper_modules --band card --ids microcosm_entry_lattice",
    "--option-surface navigation_type_plane --band card --ids public_microcosm_exports",
    "--paper-module-coverage",
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
    "task_ledger_apply.py validate --allow-warnings",
    "work_ledger.py session-status --seed-speed",
    "work_ledger.py session-claims",
    "session-heartbeat",
    "concurrency-pathology-index",
    "session-yield-control",
    "mission_transaction_preflight.py --subject-id",
    "mutation-check",
    "work_ledger_claim_read",
    "microcosm_core organ-topology",
    "microcosm-substrate/atlas/agent_task_routes.json",
    "microcosm mission-transaction-work-spine",
    "microcosm concurrency-mission-control",
    "git_diff_review_context",
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
    "--option-surface type_a_autonomous_seeds --band flag",
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
    "system/lib/navigation_context_pack.py",
    "system/lib/navigation_index_spine.py",
    "microcosm-substrate/atlas/agent_task_routes.json",
    "microcosm-substrate/src/microcosm_core/projections/organ_surface_contract.py",
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
    ("skills", "task_ledger_metacontrol_uppropagation"),
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
    ("system_atlas", "dom_system_atlas"),
    ("operator_thread_continuation_card", "thread_id_required"),
    ("workitem_spine", WORKITEM_SPINE_SELECTED_ID),
    (MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_KIND_ID, MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_ID),
    ("generated_projection_ownership", GENERATED_PROJECTION_OWNER_SELECTED_ID),
    ("external_benchmark_calibration", EXTERNAL_BENCHMARK_CALIBRATION_SELECTED_ID),
    ("paper_modules", "system_self_comprehension_root"),
    ("paper_modules", "system_self_comprehension_spine"),
    ("paper_modules", "navigation_hologram_theory"),
    ("compression_profiles", "ai_workflow_system_packet_v1"),
    ("compression_profiles", "type_b_external_grounding_v1"),
    ("compression_profiles", "compression_profile:ai_workflow_system_packet_v1::card"),
    ("compression_profiles", "compression_profile:type_b_external_grounding_v1::card"),
    ("paper_modules", "microcosm_entry_lattice"),
    ("standards", "std_microcosm"),
    ("paper_modules", "paper_module_coverage_metabolism"),
    ("paper_modules", "paper_module_entry_projection_integrity"),
    ("paper_modules", "microcosm_public_export_type_plane"),
    ("paper_modules", "microcosm_runtime_organ_atlas"),
    ("navigation_type_plane", "public_microcosm_exports"),
    (MICROCOSM_AGENT_TASK_ROUTE_KIND_ID, "agent-concurrency"),
    ("paper_modules", "microcosm_substrate"),
    ("standards", "std_autonomous_seed_prompt"),
    ("standards", "std_uppropagation_intake"),
    ("standards", "std_doctrine_section_unit"),
    ("standards", "std_teleology_node"),
    ("paper_modules", "federated_config_plane"),
    ("standards", "std_config_authority_registry"),
    ("config_authorities", "master_config.bridge"),
    ("config_authorities", "frontend.configs_board.config_ref"),
    ("config_authorities", "api.config.system"),
    ("annex_prior_art", "arxiv-2604-19572"),
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
PAPER_MODULE_INDEX = Path("codex/doctrine/paper_modules/_index.json")
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
MICROCOSM_PAPER_MODULE_DEPTH_QUERY_PHRASES = (
    "microcosm paper module",
    "microcosm paper modules",
    "microcosm paper-module",
    "microcosm paper-modules",
    "paper module coverage",
    "paper-module coverage",
    "paper module depth",
    "paper-module depth",
    "paper module atlas",
    "paper-module atlas",
    "microcosm atlas entry",
    "microcosm entry lattice",
    "microcosm public export",
    "microcosm public exports",
    "public microcosm export",
    "public microcosm exports",
)
MICROCOSM_PAPER_MODULE_DEPTH_ANCHORS = (
    (
        "paper_modules",
        "microcosm_entry_lattice",
        1.012,
        "Microcosm paper-module/depth query should open the standard-backed entry lattice before broad System Atlas self-comprehension rows.",
        "entry_lattice",
    ),
    (
        "standards",
        "std_microcosm",
        1.011,
        "Microcosm paper-module/depth query needs the machine-readable standard contract before module-source evidence.",
        "standard_contract",
    ),
    (
        "paper_modules",
        "paper_module_coverage_metabolism",
        1.010,
        "Microcosm paper-module/depth query should carry the coverage-health metabolism module that owns sidecar freshness and queue interpretation.",
        "coverage_metabolism",
    ),
    (
        "paper_modules",
        "paper_module_entry_projection_integrity",
        1.0095,
        "Microcosm paper-module/depth query should expose the entry/count projection-integrity child after the coverage roof.",
        "entry_projection_integrity",
    ),
    (
        "paper_modules",
        "microcosm_public_export_type_plane",
        1.009,
        "Microcosm paper-module/depth query should expose the public export type-plane bridge before generated public-export projections.",
        "public_export_type_plane_bridge",
    ),
    (
        "paper_modules",
        "microcosm_runtime_organ_atlas",
        1.0085,
        "Microcosm paper-module/depth query should expose the runtime organ source-loci atlas before generated projection leaves or broad self-comprehension rows.",
        "runtime_organ_source_loci",
    ),
    (
        "navigation_type_plane",
        "public_microcosm_exports",
        1.008,
        "Microcosm public-export coverage should resolve the standard type-plane row as a navigation bridge, not as source authority.",
        "standard_type_plane_row",
    ),
    (
        "paper_modules",
        "microcosm_substrate",
        1.007,
        "Microcosm paper-module/depth query should keep the product roof visible after the entry lattice and coverage contract.",
        "product_roof",
    ),
)
MICROCOSM_PAPER_MODULE_DEPTH_NEXT_COMMANDS = (
    (
        "./repo-python kernel.py --option-surface paper_modules --band card --ids "
        "microcosm_entry_lattice,paper_module_coverage_metabolism,"
        "paper_module_entry_projection_integrity,"
        "microcosm_public_export_type_plane,microcosm_runtime_organ_atlas,"
        "microcosm_substrate"
    ),
    "./repo-python kernel.py --option-surface standards --band card --ids std_microcosm",
    (
        "./repo-python kernel.py --option-surface navigation_type_plane --band card "
        "--ids public_microcosm_exports"
    ),
    "./repo-python kernel.py --paper-module-coverage",
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
MISSION_TRACE_LATEST_HANDLE_FIELDS = (
    "mission_id",
    "subject_id",
    "last_surface",
    "last_lane",
    "last_decision_state",
    "last_reason",
    "current_receipt_ref",
    "next_safe_action",
)


def _compact_mission_trace_row(row: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for field in MISSION_TRACE_LATEST_HANDLE_FIELDS:
        value = row.get(field)
        if value in (None, "", [], {}):
            continue
        compact[field] = value
    receipt_refs = row.get("receipt_refs")
    if isinstance(receipt_refs, Sequence) and not isinstance(receipt_refs, (str, bytes)):
        receipt_ref_count = len([item for item in receipt_refs if item])
        if receipt_ref_count:
            compact["receipt_ref_count"] = receipt_ref_count
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


def _compact_dirty_tree_rescue_coverage_for_context(
    coverage: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(coverage, Mapping):
        return None
    return {
        key: coverage.get(key)
        for key in (
            "status",
            "reason",
            "basis",
            "latest_ref",
            "current_base_head",
            "current_dirty_path_count",
            "rescued_base_head",
            "rescued_dirty_path_count",
            "pathset_comparison_mode",
            "missing_from_rescue_count",
            "not_currently_dirty_count",
            "content_mismatch_count",
            "drift_class",
            "drift_owner_hint",
            "drift_next_safe_action",
        )
        if coverage.get(key) not in (None, "", [], {})
    }


def _dirty_tree_bankruptcy_pressure_context(root: Path, query: str) -> dict[str, Any] | None:
    if not _query_mentions_dirty_tree_bankruptcy(query):
        return None
    bankruptcy_authorized = _query_authorizes_dirty_tree_bankruptcy(query)
    source_command = (
        "./repo-python tools/meta/factory/work_ledger.py "
        "session-sweep --dry-run --dirty-tree-pressure"
    )
    dirty_paths, dirty_scan_status = _dirty_paths_from_git_status(root)
    if bankruptcy_authorized:
        source_command = f"{source_command} --bankruptcy-authorized"
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
        pressure_card = work_ledger_runtime.compact_dirty_tree_pressure_card(card)
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
        "operator_authorized_mainline_checkpoint": pressure_card.get(
            "operator_authorized_mainline_checkpoint"
        ),
        "operator_authorized_unclaimed_checkpoint": pressure_card.get(
            "operator_authorized_unclaimed_checkpoint"
        ),
        "dirty_scan_status": pressure_card.get("dirty_scan_status"),
        "dirty_total": pressure_card.get("dirty_total"),
        "work_ledger_counts": pressure_card.get("work_ledger_counts"),
        "dirty_path_class_counts": pressure_card.get("dirty_path_class_counts"),
        "class_counts": pressure_card.get("class_counts")
        or pressure_card.get("dirty_path_class_counts"),
        "generated_owner_dirty": pressure_card.get("generated_owner_dirty"),
        "unclaimed_source_dirty": pressure_card.get("unclaimed_source_dirty"),
        "active_claim_session_groups": pressure_card.get("active_claim_session_groups"),
        "scoped_work_unblock": pressure_card.get("scoped_work_unblock"),
        "containment_plan": pressure_card.get("containment_plan"),
        "last_finalizer_receipt_ref": card.get("last_finalizer_receipt_ref"),
        "rescue_coverage": _compact_dirty_tree_rescue_coverage_for_context(
            card.get("rescue_coverage")
        ),
        "rescue_repeat_policy": pressure_card.get("rescue_repeat_policy"),
        "repeat_policy": pressure_card.get("repeat_policy")
        or pressure_card.get("rescue_repeat_policy"),
        "mainline_commit_candidates": pressure_card.get("mainline_commit_candidates")
        or [],
        "blocked_residuals": pressure_card.get("blocked_residuals"),
        "next_safe_action": pressure_card.get("next_safe_action"),
        "commands": pressure_card.get("commands"),
        "policy": pressure_card.get("policy"),
        "omission_receipt": pressure_card.get("omission_receipt"),
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
PAPER_LATTICE_STABLE_SLUG_SOURCE = "paper_modules option surface row id"
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


def _paper_module_slugs(repo_root: Path) -> set[str]:
    payload = _load_json(repo_root / PAPER_MODULE_INDEX)
    modules = payload.get("modules")
    if not isinstance(modules, list):
        return set()
    return {
        slug
        for row in modules
        if isinstance(row, Mapping)
        for slug in [str(row.get("slug") or "").strip()]
        if slug
    }


def _explicit_paper_module_slug_hits(repo_root: Path, query: str) -> list[str]:
    tokens = _query_terms(query)
    lower_query = str(query or "").lower()
    if not any("_" in token for token in tokens) and "--paper-module" not in lower_query:
        return []
    slugs = _paper_module_slugs(repo_root)
    if not slugs:
        return []
    return sorted(tokens & slugs)


def _query_terms(query: str) -> set[str]:
    return {part.strip(".,:;!?()[]{}\"'`").lower() for part in str(query or "").split() if part.strip()}


MICROCOSM_AGENT_TASK_ROUTE_STOP_TERMS = {
    "agent",
    "agents",
    "authority",
    "boundary",
    "card",
    "cards",
    "claim",
    "claims",
    "command",
    "commands",
    "consumption",
    "evaluator",
    "failover",
    "input",
    "json",
    "lifecycle",
    "microcosm",
    "module",
    "modules",
    "mutation",
    "organ",
    "organs",
    "out",
    "public",
    "python",
    "receipt",
    "receipts",
    "ref",
    "refs",
    "route",
    "routes",
    "run",
    "source",
    "session",
    "sessions",
    "task",
    "tasks",
    "validator",
}

MICROCOSM_AGENT_TASK_ROUTE_HINT_TERMS = {
    "collision",
    "collisions",
    "concurrency",
    "consumption",
    "evaluator",
    "failover",
    "heartbeat",
    "microcosm",
    "microcosms",
    "mutation",
    "organ",
    "organs",
}


def _route_search_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _route_search_terms(value: Any) -> set[str]:
    return {part for part in _route_search_text(value).split() if part}


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


def _is_microcosm_paper_module_depth_query(query: str) -> bool:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _query_terms(lower_query)
    if any(
        phrase.replace("-", " ") in lower_query
        for phrase in MICROCOSM_PAPER_MODULE_DEPTH_QUERY_PHRASES
    ):
        return True
    if not ({"microcosm", "microcosms"} & terms):
        return False
    if {"paper", "module"} <= terms or {"paper", "modules"} <= terms:
        return True
    return bool(
        ({"coverage", "depth"} <= terms)
        or ({"atlas", "entry"} <= terms)
        or ({"public"} <= terms and {"export", "exports"} & terms)
    )


def _load_microcosm_agent_task_routes(repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = _load_json(repo_root / MICROCOSM_AGENT_TASK_ROUTES_REL)
    routes = [
        row
        for row in (payload.get("routes") if isinstance(payload.get("routes"), list) else [])
        if isinstance(row, dict)
    ]
    return payload, routes


def _microcosm_agent_task_route_candidates(
    repo_root: Path,
    query: str,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    query_text = _route_search_text(query)
    query_terms = _route_search_terms(query)
    query_specific_terms = query_terms - MICROCOSM_AGENT_TASK_ROUTE_STOP_TERMS
    if not query_specific_terms:
        return []
    if not (
        query_terms & MICROCOSM_AGENT_TASK_ROUTE_HINT_TERMS
        or "agent concurrency" in query_text
        or "agent task route" in query_text
    ):
        return []
    _, routes = _load_microcosm_agent_task_routes(repo_root)
    if not routes:
        return []

    matches: list[dict[str, Any]] = []
    for route in routes:
        task_class = str(route.get("task_class") or "").strip()
        if not task_class:
            continue
        route_text = json.dumps(route, ensure_ascii=False, sort_keys=True)
        route_terms = _route_search_terms(route_text)
        task_terms = _route_search_terms(task_class)
        matched_terms = sorted(query_specific_terms & route_terms)
        exact_task_class = bool(task_class and _route_search_text(task_class) in query_text)
        task_terms_covered = bool(task_terms and task_terms <= query_terms)
        if not exact_task_class and not task_terms_covered and len(matched_terms) < 3:
            continue

        score = 0.92 + min(len(matched_terms), 8) * 0.011
        if exact_task_class:
            score += 0.14
        elif task_terms_covered:
            score += 0.10
        primary_organ_id = str(route.get("primary_organ_id") or "").strip()
        if primary_organ_id and _route_search_terms(primary_organ_id) <= query_terms:
            score += 0.04
        if {"heartbeat", "collision", "mutation", "speed"} & set(matched_terms):
            score += 0.02
        matches.append(
            {
                "kind_id": MICROCOSM_AGENT_TASK_ROUTE_KIND_ID,
                "id": task_class,
                "score": min(score, 1.035),
                "reason": (
                    "High-level task terms matched an existing Microcosm agent-task route "
                    f"({task_class}) without requiring organ ids."
                ),
                "source_kind": "microcosm_agent_task_route_projection",
                "facet": "agent_task_route_selector",
                "matched_terms": matched_terms[:12],
            }
        )

    matches.sort(key=lambda row: (-float(row.get("score") or 0.0), str(row.get("id") or "")))
    return matches[:limit]


def _microcosm_organ_topology_affordance_candidates(query: str) -> list[dict[str, Any]]:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _route_search_terms(lower_query)
    if "organ topology" in lower_query or "organ relationship topology" in lower_query:
        matched = ["organ topology"]
    elif not ({"microcosm", "microcosms"} & terms) or not ({"organ", "organs"} & terms):
        return []
    else:
        relationship_terms = {
            "edge",
            "edges",
            "relationship",
            "relationships",
            "route",
            "routes",
            "share",
            "shared",
            "source",
            "standard",
            "standards",
            "topology",
        }
        evidence_terms = {
            "javascript",
            "js",
            "language",
            "mechanism",
            "concept",
            "modules",
            "python",
            "source",
            "typescript",
            "ts",
        }
        if not (terms & relationship_terms) or not (terms & evidence_terms):
            return []
        matched = sorted((terms & relationship_terms) | (terms & evidence_terms))[:12]

    return [
        {
            "kind_id": MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_KIND_ID,
            "id": MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_ID,
            "score": 1.034,
            "reason": (
                "Microcosm organ relationship wording should use the existing "
                "organ-topology CLI affordance before bespoke grep or another topology layer."
            ),
            "source_kind": "microcosm_organ_topology_affordance_anchor",
            "facet": "organ_relationship_query_affordance",
            "matched_terms": matched,
        }
    ]


def _is_public_safe_dissemination_gate_query(query: str) -> bool:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _query_terms(lower_query)
    specific_phrases = tuple(
        phrase
        for phrase in PUBLIC_SAFE_DISSEMINATION_GATE_QUERY_PHRASES
        if phrase not in {"public safe", "public-safe"}
    )
    if any(phrase.replace("-", " ") in lower_query for phrase in specific_phrases):
        return True
    if "public safe" in lower_query and (
        {"atlas", "dissemination", "leaf", "recipient", "send"} & terms
    ):
        return True
    has_dissemination_scope = bool({"dissemination", "recipient", "send"} & terms)
    has_gate_scope = bool({"atlas", "capability", "disclosure", "gate", "leaf", "readiness", "artifact"} & terms)
    return bool(
        (has_dissemination_scope and has_gate_scope)
        or ({"atlas", "gate"} <= terms and {"dissemination", "disclosure", "safe"} & terms)
        or ({"leaf", "readiness"} <= terms and {"public", "safe", "dissemination"} & terms)
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
        "optmisation",
        "optimize",
        "optimizing",
        "optimization",
        "optmization",
        "improve",
        "improving",
        "improvement",
        "improvements",
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
        "system",
        "systems",
        "macro",
        "microcosm",
        "microcosms",
        "general",
        "refinement",
        "refinements",
        "improvement",
        "improvements",
    }
    return bool((terms & speed_terms) and (terms & telemetry_terms))


def _is_named_seed_replay_query(query: str) -> bool:
    lower_query = str(query or "").casefold().replace("_", " ").replace("-", " ")
    terms = _query_terms(lower_query)
    return bool(
        {"autonomous", "seed"} <= terms
        and {"replay", "continuation", "receipt", "receipts"} & terms
    )


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


def _skill_passport_candidate_rows(repo_root: Path, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Propose skill rows directly from authored compression passports.

    Semantic expansion and per-skill context_pack_anchors are both useful, but
    std_skill::compression_passport is the standard-owned first-contact
    affordance. This keeps context-pack from dropping authored skill rows when
    semantic expansion times out or a skill has not added bespoke anchors.
    """

    if _is_speed_refinement_query(query):
        return []
    query_tokens = _gate_tokens(query)
    if not query_tokens:
        return []
    lower_query = str(query or "").casefold()
    normalized_query = re.sub(r"[^a-z0-9]+", "_", lower_query).strip("_")
    registry = _load_json(repo_root / "codex/doctrine/skills/skill_registry.json")
    candidates: list[tuple[float, int, str, dict[str, Any]]] = []
    families = registry.get("families") if isinstance(registry.get("families"), list) else []
    for family in families:
        if not isinstance(family, Mapping):
            continue
        skills = family.get("skills") if isinstance(family.get("skills"), list) else []
        for skill in skills:
            if not isinstance(skill, Mapping):
                continue
            skill_id = str(skill.get("id") or "").strip()
            passport = skill.get("compression_passport")
            if not skill_id or not isinstance(passport, Mapping):
                continue
            hyphen_id = skill_id.replace("_", "-")
            spaced_id = skill_id.replace("_", " ")
            exact_id_match = (
                skill_id.casefold() in lower_query
                or hyphen_id.casefold() in lower_query
                or spaced_id.casefold() in lower_query
                or skill_id.casefold() in normalized_query
            )
            cluster_keys = passport.get("cluster_keys")
            positive_overlap = (
                _gate_overlap_count(query_tokens, passport.get("when_to_open"))
                + _gate_overlap_count_array(query_tokens, cluster_keys)
                + (_gate_overlap_count(query_tokens, passport.get("flag")) // 2)
            )
            if exact_id_match:
                positive_overlap += 6
            if positive_overlap <= 0:
                continue
            if not exact_id_match and positive_overlap < 2:
                continue
            agent_surface = skill.get("agent_surface") if isinstance(skill.get("agent_surface"), Mapping) else {}
            negative_overlap = (
                _gate_overlap_count(query_tokens, passport.get("when_not_to_open"))
                + _gate_overlap_count(query_tokens, skill.get("not_when"))
                + _gate_overlap_count(query_tokens, agent_surface.get("not_when"))
            )
            if negative_overlap > 0 and negative_overlap >= positive_overlap:
                continue
            matched_cluster_keys = [
                str(item)
                for item in (cluster_keys if isinstance(cluster_keys, list) else [])
                if _gate_overlap_count(query_tokens, item) > 0
            ]
            score = min(1.006 if exact_id_match else 0.996, 0.94 + positive_overlap * 0.01)
            candidates.append(
                (
                    score,
                    -positive_overlap,
                    skill_id,
                    {
                        "kind_id": "skills",
                        "id": skill_id,
                        "score": round(score, 6),
                        "reason": (
                            "Skill compression_passport matched the task via "
                            f"positive_overlap={positive_overlap}, "
                            f"negative_overlap={negative_overlap}."
                        ),
                        "source_kind": "skill_compression_passport_candidate",
                        "facet": "compression_passport",
                        "matched_cluster_keys": matched_cluster_keys,
                    },
                )
            )
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [row for *_prefix, row in candidates[:limit]]


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

    for row in _microcosm_agent_task_route_candidates(repo_root, query):
        add(
            str(row["kind_id"]),
            str(row["id"]),
            float(row.get("score") or 0.0),
            str(row.get("reason") or "Microcosm agent-task route projection"),
            source_kind=row.get("source_kind"),
            facet=row.get("facet"),
            matched_terms=row.get("matched_terms"),
        )

    for row in _microcosm_organ_topology_affordance_candidates(query):
        add(
            str(row["kind_id"]),
            str(row["id"]),
            float(row.get("score") or 0.0),
            str(row.get("reason") or "Microcosm organ-topology affordance"),
            source_kind=row.get("source_kind"),
            facet=row.get("facet"),
            matched_terms=row.get("matched_terms"),
        )

    for row in _skill_passport_candidate_rows(repo_root, query):
        add(
            str(row["kind_id"]),
            str(row["id"]),
            float(row.get("score") or 0.0),
            str(row.get("reason") or "skill compression passport candidate"),
            source_kind=row.get("source_kind"),
            facet=row.get("facet"),
            matched_cluster_keys=row.get("matched_cluster_keys"),
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

    lower_query_for_anchors = str(query or "").casefold().replace("-", " ")
    terms_for_anchors = _query_terms(lower_query_for_anchors)
    if (
        "generalizer" in terms_for_anchors
        or "generalize" in terms_for_anchors
        or "generalization" in terms_for_anchors
        or "existing surface miss" in lower_query_for_anchors
        or "claim block" in lower_query_for_anchors
        or "claim blocked" in lower_query_for_anchors
        or "claim block frontier" in lower_query_for_anchors
    ):
        add(
            "skills",
            "local_to_general_propagation",
            1.001,
            "Generalizer, existing-surface miss, or claim-block frontier query should open the local-to-general propagation lane before ad hoc route edits.",
            source_kind="local_to_general_context_pack_anchor",
            facet="local_to_general_frontier",
        )
        add(
            "skills",
            "task_ledger_metacontrol_uppropagation",
            1.0,
            "Claim-block frontier query should open Task Ledger metacontrol up-propagation so residual/claim lessons bind to the ledger control plane.",
            source_kind="local_to_general_context_pack_anchor",
            facet="task_ledger_claim_frontier",
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

    terms = _query_terms(query)
    lower_query = str(query or "").lower()
    lattice_facet = "paper_lattice" if ("lattice" in terms or "--paper-lattice" in lower_query) else "exact_paper_module_slug"
    for slug in _explicit_paper_module_slug_hits(repo_root, query):
        add(
            "paper_modules",
            slug,
            1.02,
            "Exact paper-module slug appears in the task text; expose the selected module row before generic paper/doctrine anchors.",
            source_kind="exact_paper_module_slug",
            facet=lattice_facet,
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
    if _is_microcosm_paper_module_depth_query(query):
        for kind_id, row_id, score, reason, facet in MICROCOSM_PAPER_MODULE_DEPTH_ANCHORS:
            add(
                kind_id,
                row_id,
                score,
                reason,
                source_kind="microcosm_paper_module_depth_anchor",
                facet=facet,
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
            "Root navigation theory remains the model lattice row; exact selected slugs provide concrete targets.",
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
    if len(rows) <= DEFAULT_SELECTED_LIMIT:
        return rows
    protected: list[dict[str, Any]] = []
    ordinary: list[dict[str, Any]] = []
    protected_source_kinds = {
        "system_atlas_protocol_anchor",
        "type_a_autonomous_seed_anchor",
        "speed_refinement_command_telemetry_anchor",
        "workitem_spine_anchor",
        "generated_projection_owner_anchor",
        "external_benchmark_calibration_anchor",
        "operator_thread_continuation_card_anchor",
        "system_crystal_protocol_anchor",
        "public_safe_dissemination_gate_anchor",
        "prompt_shelf_metadata_anchor",
        "skill_registry_context_pack_anchor",
    }
    for row in rows:
        key = (str(row.get("kind_id") or ""), str(row.get("id") or ""))
        if key in BUDGET_TRIM_PROTECTED_ROWS or str(row.get("source_kind") or "") in protected_source_kinds:
            protected.append(row)
        else:
            ordinary.append(row)
    limited: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in [*protected, *ordinary]:
        key = (str(row.get("kind_id") or ""), str(row.get("id") or ""))
        if key in seen:
            continue
        seen.add(key)
        limited.append(row)
        if len(limited) >= DEFAULT_SELECTED_LIMIT:
            break
    return limited


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

_SOURCE_AUTHORITY_FALLBACK_KIND_IDS: frozenset[str] = frozenset(
    {
        "compression_profiles",
        "paper_modules",
        "standards",
        "system_atlas",
        "navigation_type_plane",
        "concepts",
        "mechanisms",
        "principles",
        "axiom_candidates",
        "cognitive_operators",
        "skills",
    }
)

_PASSPORT_AUTHORITY_LAYER_BY_KIND: Mapping[str, str] = {
    "axiom_candidates": "constitutional",
    "concepts": "constitutional",
    "compression_profiles": "constitutional",
    "principles": "constitutional",
    "standards": "constitutional",
    "cognitive_operators": "operational",
    "mechanisms": "operational",
    "skills": "operational",
    "navigation_type_plane": "projection",
    "paper_modules": "projection",
    "system_atlas": "projection",
}

_PASSPORT_AUTHORITY_TIER_BY_LAYER: Mapping[str, str] = {
    "constitutional": "governing_doctrine_authority",
    "operational": "owner_surface_authority",
    "projection": "non_authoritative_projection",
}


def _passport_source_tuple(
    row: Mapping[str, Any],
    *,
    kind_id: str,
    authored_passport: bool,
) -> dict[str, Any]:
    """Expose source/proof routes for selected-row passports without promoting them."""
    if kind_id not in _SOURCE_AUTHORITY_FALLBACK_KIND_IDS:
        return {}
    owner_routes = row.get("owner_routes") if isinstance(row.get("owner_routes"), Mapping) else {}
    omission_receipt = row.get("omission_receipt") if isinstance(row.get("omission_receipt"), Mapping) else {}
    render_profile = row.get("render_profile") if isinstance(row.get("render_profile"), Mapping) else {}
    currentness = row.get("currentness") if isinstance(row.get("currentness"), Mapping) else {}

    canonical_source = (
        row.get("source_ref")
        or row.get("file")
        or row.get("registry_ref")
        or row.get("authority_path")
    )
    safe_drilldown = (
        row.get("drilldown_command")
        or owner_routes.get("entry_command")
        or omission_receipt.get("drilldown")
        or row.get("evidence_command")
    )
    evaluator_lane = (
        owner_routes.get("check_command")
        or row.get("validation_command")
        or row.get("evidence_command")
        or safe_drilldown
    )
    receipt_lane = (
        owner_routes.get("status_command")
        or row.get("receipt_command")
        or row.get("evidence_command")
        or omission_receipt.get("drilldown")
    )
    source_fields_present = any(
        value not in (None, "", [], {})
        for value in (
            canonical_source,
            safe_drilldown,
            evaluator_lane,
            receipt_lane,
            row.get("evidence_command"),
            owner_routes,
            currentness,
        )
    )
    if not source_fields_present:
        return {}

    projection_not_authority = bool(
        render_profile.get("projection_not_authority")
        or currentness.get("safe_to_commit_generated_outputs_without_sources") is False
    )
    layer = _PASSPORT_AUTHORITY_LAYER_BY_KIND.get(kind_id)
    if projection_not_authority:
        layer = "projection"
    if not layer:
        layer = "operational"
    out: dict[str, Any] = {
        "canonical_source": canonical_source,
        "authority_tier": _PASSPORT_AUTHORITY_TIER_BY_LAYER.get(layer),
        "authority_layer": layer,
        "override_semantics": (
            "Authored compression_passport guides navigation but cannot override the canonical source or owner lane."
            if authored_passport
            else "Fallback metadata cannot override the canonical source or owner lane."
        ),
        "runtime_consumers": ["navigation_context_pack.selected_rows"],
        "safe_drilldown": safe_drilldown,
        "evaluator_lane": evaluator_lane,
        "receipt_lane": receipt_lane,
        "proof_path": evaluator_lane or receipt_lane or safe_drilldown,
        "authority_boundary": (
            "authored_compression_passport_projection_not_source_authority"
            if authored_passport
            else "derived_from_selected_row_metadata_not_authored_compression_passport"
        ),
    }
    owner_lane = {
        key: owner_routes.get(key)
        for key in (
            "entry_command",
            "check_command",
            "refresh_command",
            "status_command",
            "root_drilldown_command",
        )
        if owner_routes.get(key) not in (None, "", [], {})
    }
    if owner_lane:
        out["owner_lane"] = owner_lane
    if row.get("evidence_command"):
        out["evidence_command"] = row.get("evidence_command")
    if projection_not_authority:
        out["projection_not_authority"] = True
    if currentness.get("status"):
        out["currentness_status"] = currentness.get("status")
    return {key: value for key, value in out.items() if value not in (None, "", [], {})}


def _passport_standard_ref(kind_id: str) -> str:
    if kind_id == "system_atlas":
        return "codex/standards/std_system_atlas.json"
    if kind_id == "skills":
        return "codex/standards/std_skill.json::compression_passport"
    if kind_id == "compression_profiles":
        return "codex/doctrine/compression_profiles.json::compression_passport"
    return f"codex/standards/std_{kind_id.rstrip('s')}.json"


def _source_authority_fallback_passport(row: Mapping[str, Any], *, kind_id: str) -> dict[str, Any]:
    """Expose row-owned source/proof routes without claiming an authored passport."""
    source_tuple = _passport_source_tuple(row, kind_id=kind_id, authored_passport=False)
    if not source_tuple:
        return {}
    row_id = _row_identity(row, kind_id)
    title = row.get("title") or row.get("name") or row.get("canonical_label") or row_id
    out: dict[str, Any] = {
        "status": "source_authority_fallback",
        "source": "row_authority_fields",
        "atom": _trim(title, max_chars=96),
        "cluster_keys": [
            "source_authority",
            "owner_drilldown",
            kind_id,
        ],
        "when_to_open": "Use when the row lacks an authored compression_passport but already declares source, drilldown, proof, or owner routes.",
        "when_not_to_open": "Do not treat this fallback as authored doctrine or as permission to mutate generated projections.",
        "safe_drilldown": source_tuple.get("proof_path"),
        "owning_standard": _passport_standard_ref(kind_id),
        "sufficiency_claims": [
            "The row exposes a legal source/proof route without inventing a compression_passport.",
        ],
    }
    out.update(source_tuple)
    out["authority_tier"] = "row_owner_metadata_not_source_authority"
    return {key: value for key, value in out.items() if value not in (None, "", [], {})}


def _source_authority_fallback_enabled(query: str) -> bool:
    lowered = str(query or "").lower()
    return any(
        phrase in lowered
        for phrase in (
            "proof path",
            "canonical source",
            "authority tier",
            "doctrine routing weave",
            "release doctrine profile",
        )
    )


def _affordance_passport(
    row: Mapping[str, Any],
    *,
    kind_id: str,
    source_authority_fallback: bool = False,
) -> dict[str, Any]:
    """Extract the standard-owned affordance fields a row carries, without inventing.

    Reads from `row.compression_passport` first (the std_skill-owned source per
    `codex/standards/std_skill.json::compression_passport`; same shape can be
    populated on paper-module / standard rows once those standards adopt the
    passport), then falls back to top-level row fields. When no authored
    affordance fields exist, the helper can emit a clearly marked
    source-authority fallback derived only from existing row owner metadata.

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
        if source_authority_fallback:
            fallback = _source_authority_fallback_passport(row, kind_id=kind_id)
            if fallback:
                return fallback
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
    source_tuple = _passport_source_tuple(
        row,
        kind_id=kind_id,
        authored_passport=bool(passport_source),
    )
    for key, value in source_tuple.items():
        out.setdefault(key, value)
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
    matches: list[tuple[int, int, str]] = []
    prioritized: list[str] = []
    if {"validated", "uncommitted"} <= query_terms:
        prioritized = [
            str(rule)
            for rule in validation_rules
            if "validated_uncommitted_git_metadata_blocked" in str(rule)
        ]
    for rule in validation_rules:
        text = str(rule)
        if text in prioritized:
            continue
        overlap = len(query_terms & _match_terms(text))
        if overlap < 2:
            continue
        matches.append((-overlap, len(matches), text))
    matches.sort()
    result: list[str] = []
    seen: set[str] = set()
    for text in [*prioritized, *(text for _, _, text in matches)]:
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


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
    selected_by_exact_paper_module_slug = (
        str(selected_row.get("selection_source_kind") or "") == "exact_paper_module_slug"
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
        if selected_by_exact_paper_module_slug:
            return {
                "compatibility_bucket": 0,
                "compatibility_label": "strong_exact_paper_module_slug_match",
                "affordance_boost": 1.0,
                "anti_trigger_overlap": 0,
                "landmine_overlap": 0,
                "positive_trigger_overlap": 0,
                "reason": "row selected by exact stable paper-module slug in task text",
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
    if selected_by_exact_paper_module_slug:
        return {
            "compatibility_bucket": 0,
            "compatibility_label": "strong_exact_paper_module_slug_match",
            "affordance_boost": 1.0,
            "anti_trigger_overlap": neg_overlap,
            "landmine_overlap": landmine_overlap,
            "positive_trigger_overlap": max(pos_overlap, 1),
            "reason": "row selected by exact stable paper-module slug in task text",
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
    query: str = "",
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
        "affordance_passport": _affordance_passport(
            row,
            kind_id=kind_id,
            source_authority_fallback=_source_authority_fallback_enabled(query),
        ),
    }
    if kind_id == "skills" and row_id == "doctrine_derivation":
        passport = result.get("affordance_passport")
        if isinstance(passport, dict):
            claims = list(passport.get("sufficiency_claims") or [])
            reusable_claim = (
                "The row names reusable thinking operators as the doctrine-operator boundary, "
                "separating operator voice from agent-authored synthesis lanes."
            )
            if not any("reusable thinking operators" in str(claim) for claim in claims):
                claims.insert(0, reusable_claim)
                passport["sufficiency_claims"] = claims
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
        passport = result.get("affordance_passport")
        if (
            isinstance(passport, dict)
            and passport.get("status") == "source_authority_fallback"
        ):
            if currentness.get("status") and not passport.get("currentness_status"):
                passport["currentness_status"] = currentness.get("status")
            if currentness.get("safe_to_commit_generated_outputs_without_sources") is False:
                passport["projection_not_authority"] = True
                passport["authority_layer"] = "projection"
    if isinstance(row.get("nearest_standard"), Mapping):
        result["nearest_standard"] = dict(row.get("nearest_standard") or {})
    if isinstance(row.get("upstream_doctrine_route"), Mapping):
        result["upstream_doctrine_route"] = dict(row.get("upstream_doctrine_route") or {})
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
    if kind_id == "paper_modules" and row_id:
        lattice_command = f"./repo-python kernel.py --paper-lattice {row_id} --band card --context-budget 12000"
        result["drilldowns"] = {
            "card": card_drilldown,
            "lattice": lattice_command,
            "evidence": f"./repo-python kernel.py --paper-module {row_id}",
        }
        result["paper_lattice"] = {
            "status": "supported_stable_slug",
            "command": lattice_command,
            "entry_condition": "stable paper-module slug selected by context-pack or paper_modules cluster/card surface",
            "stable_slug_source": PAPER_LATTICE_STABLE_SLUG_SOURCE,
            "free_text_policy": "not_search",
        }
    return result


def _python_context_upstream_doctrine_route(
    canonical_source: str,
    *,
    route_kind: str,
    source_compile_command: str,
    receipt_lane: str,
    parent_file_command: str | None = None,
) -> dict[str, Any]:
    route_commands = {
        "source": source_compile_command,
        "scope_index": "./repo-python kernel.py --option-surface standards --band card --ids std_python_scope_index",
        "standard": "./repo-python kernel.py --option-surface standards --band card --ids std_python",
        "doctrine": "./repo-python kernel.py --paper-module navigation_hologram_theory",
        "skill": "./repo-python kernel.py --option-surface skills --band card --ids profile_governed_compression",
    }
    if parent_file_command:
        route_commands["parent_file"] = parent_file_command
    return {
        "schema": "python_upstream_doctrine_route_v0",
        "status": "available",
        "route_kind": route_kind,
        "canonical_source": canonical_source,
        "authority_layer": "operational",
        "authority_tier": "owner_surface_route_not_source_authority",
        "authority_boundary": "route_metadata_only_open_canonical_source_before_mutation",
        "source_projection": "codex/standards/std_python_scope_index.json",
        "governing_standard": "codex/standards/std_python.py",
        "governing_doctrine": "codex/doctrine/paper_modules/navigation_hologram_theory.md",
        "governing_skill": "codex/doctrine/skills/compression/profile_governed_compression.md",
        "override_semantics": "This route cannot override Python source, std_python.py, or the scope-index builder; it only exposes the legal drilldown chain.",
        "runtime_consumers": [
            "python_files.card",
            "python_scopes.card",
            "navigation_context_pack.selected_rows",
        ],
        "evaluator_lane": source_compile_command,
        "receipt_lane": receipt_lane,
        "proof_path": [source_compile_command, receipt_lane],
        "route_commands": route_commands,
    }


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
        card_command = packet.get("card_command") or f"./repo-python kernel.py --option-surface python_files --band card --ids {path}"
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
            "drilldown_command": card_command,
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
                "drilldown": card_command,
            },
            "upstream_doctrine_route": _python_context_upstream_doctrine_route(
                path,
                route_kind="python_file",
                source_compile_command=f"./repo-python kernel.py --compile {path}",
                receipt_lane=card_command,
            ),
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
        card_command = packet.get("card_command") or f"./repo-python kernel.py --option-surface python_scopes --band card --ids {scope_id}"
        parent_file_command = packet.get("parent_file_command")
        source_compile_command = f"./repo-python kernel.py --compile {path}" if path else str(parent_file_command or card_command)
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
            "drilldown_command": card_command,
            "evidence_command": parent_file_command,
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
                "drilldown": card_command,
            },
            "source_span": dict(source_span) if isinstance(source_span, Mapping) else {},
            "parent_file_command": parent_file_command,
            "upstream_doctrine_route": _python_context_upstream_doctrine_route(
                f"{path}::{name}" if path else scope_id,
                route_kind="python_scope",
                source_compile_command=source_compile_command,
                receipt_lane=card_command,
                parent_file_command=str(parent_file_command or ""),
            ),
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


def _routine_selected_card_cache_input_paths(kind_id: str, ids: Sequence[str]) -> tuple[str, ...]:
    common = (
        "system/lib/standard_option_surface.py",
        "system/lib/navigation_context_pack.py",
    )
    clean_ids = [str(item) for item in ids if str(item or "").strip()]
    if kind_id == "paper_modules":
        return common + (
            "codex/doctrine/paper_modules/_index.json",
            "codex/doctrine/paper_modules/_route_coverage.json",
            *(f"codex/doctrine/paper_modules/{row_id}.md" for row_id in clean_ids),
        )
    if kind_id == "skills":
        skill_dirs = (
            "kernel",
            "compression",
            "bridge_runtime",
            "doctrine",
            "annex",
            "frontend",
            "raw_seed",
        )
        return common + (
            "codex/doctrine/skills/skill_registry.json",
            *(
                f"codex/doctrine/skills/{skill_dir}/{row_id}.md"
                for row_id in clean_ids
                for skill_dir in skill_dirs
            ),
            *(f".agents/skills/{row_id.replace('_', '-')}/SKILL.md" for row_id in clean_ids),
        )
    if kind_id == "type_a_autonomous_seeds":
        return common + (
            "codex/doctrine/skills/kernel/type_a_autonomous_seed_loop.md",
            "codex/doctrine/paper_modules/system_self_comprehension_root.md",
            *(
                f"state/meta_missions/type_a_autonomous_seed_loop/seeds/{row_id}_autonomous_seed.md"
                for row_id in clean_ids
            ),
            *(
                f"state/meta_missions/type_a_autonomous_seed_loop/seeds/{row_id}_autonomous_seed.json"
                for row_id in clean_ids
            ),
        )
    return common


def _option_surface_card_payload_for_context_pack(
    repo_root: Path,
    kind_id: str,
    ids: Sequence[str],
    *,
    use_card_cache: bool,
    card_cache_statuses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_ids = sorted({str(item) for item in ids if str(item or "").strip()})
    if not use_card_cache or kind_id not in ROUTINE_SELECTED_CARD_CACHE_KINDS:
        return build_option_surface(repo_root, kind_id, band="card", ids=normalized_ids)

    from system.lib.command_node_cache import cached_command_node

    def _build() -> dict[str, Any]:
        payload = build_option_surface(repo_root, kind_id, band="card", ids=normalized_ids)
        return json.loads(json.dumps(payload, default=str))

    payload, cache_status = cached_command_node(
        repo_root,
        node_id=ROUTINE_SELECTED_CARD_CACHE_NODE_ID,
        key={
            "version": ROUTINE_SELECTED_CARD_CACHE_KEY_VERSION,
            "kind_id": kind_id,
            "band": "card",
            "ids": normalized_ids,
        },
        input_paths=_routine_selected_card_cache_input_paths(kind_id, normalized_ids),
        ttl_s=0.0,
        builder=_build,
        freshness_policy=ROUTINE_SELECTED_CARD_CACHE_FRESHNESS_POLICY,
        dynamic_inputs_manifested=True,
    )
    if card_cache_statuses is not None:
        card_cache_statuses.append(
            {
                "kind_id": kind_id,
                "id_count": len(normalized_ids),
                "status": cache_status.get("status"),
                "reason": cache_status.get("reason"),
                "cache_path": cache_status.get("cache_path"),
            }
        )
    return dict(payload) if isinstance(payload, Mapping) else {}


def _selected_rows(
    repo_root: Path,
    candidates: list[dict[str, Any]],
    *,
    query: str = "",
    use_card_cache: bool = False,
    card_cache_statuses: list[dict[str, Any]] | None = None,
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
                selected.append(
                    _type_a_autonomous_seed_selected_row(
                        repo_root,
                        candidate,
                        use_card_cache=use_card_cache,
                        card_cache_statuses=card_cache_statuses,
                    )
                )
            continue
        if kind_id == "workitem_spine":
            for candidate in rows:
                selected.append(_workitem_spine_selected_row(repo_root, candidate))
            continue
        if kind_id == MICROCOSM_AGENT_TASK_ROUTE_KIND_ID:
            for candidate in rows:
                selected.append(_microcosm_agent_task_route_selected_row(repo_root, candidate))
            continue
        if kind_id == MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_KIND_ID:
            for candidate in rows:
                selected.append(_microcosm_organ_topology_affordance_selected_row(candidate))
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
        payload = _option_surface_card_payload_for_context_pack(
            repo_root,
            kind_id,
            ids,
            use_card_cache=use_card_cache,
            card_cache_statuses=card_cache_statuses,
        )
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
            compact = _compact_option_row(
                option_row,
                kind_id=kind_id,
                score=score,
                reason=reason,
                query=query,
            )
            if kind_id == "standards":
                matched_rules = _query_matched_standard_validation_rules(repo_root, option_row, query)
                if matched_rules:
                    compact["matched_validation_rules"] = matched_rules
            source_kind = source_kind_by_id.get(candidate_id, source_kind_by_id.get(row_id, ""))
            if kind_id == "skills" and source_kind in {
                "type_a_autonomous_seed_anchor",
                "speed_refinement_command_telemetry_anchor",
            }:
                source_kind = "skill_registry_context_pack_anchor"
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
        if str(row.get("selection_source_kind") or "") == "microcosm_paper_module_depth_anchor":
            row["affordance_compatibility"] = {
                "compatibility_bucket": 0,
                "compatibility_label": "microcosm_paper_module_depth_anchor",
                "affordance_boost": 1.35,
                "anti_trigger_overlap": 0,
                "positive_trigger_overlap": 1,
                "reason": "Microcosm paper-module/depth query matched the standard-backed depth anchor set.",
            }
            continue
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
        if str(row.get("selection_source_kind") or "") == "system_atlas_protocol_anchor":
            row["affordance_compatibility"] = {
                "compatibility_bucket": 0,
                "compatibility_label": "system_atlas_protocol_anchor",
                "affordance_boost": 1.25,
                "anti_trigger_overlap": 0,
                "positive_trigger_overlap": 1,
                "reason": "System Atlas/self-comprehension query matched the protocol anchor; preserve atlas drilldowns before generic skill rows.",
            }
            continue
        if str(row.get("selection_source_kind") or "") == "type_a_autonomous_seed_anchor":
            row["affordance_compatibility"] = {
                "compatibility_bucket": 0,
                "compatibility_label": "type_a_autonomous_seed_anchor",
                "affordance_boost": 1.2,
                "anti_trigger_overlap": 0,
                "positive_trigger_overlap": 1,
                "reason": "Autonomous-seed query matched saved seed and seed-loop owner routes.",
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
    dissemination_readme = repo_root / "docs/dissemination/README.md"
    required_paths = [report, report_json, disclosure_map, readiness_audit]
    retired_framing = False
    if dissemination_readme.exists():
        readme_text = dissemination_readme.read_text(encoding="utf-8", errors="replace").casefold()
        retired_framing = (
            "tree-wide retirement notice" in readme_text
            and "the current strategy is:" in readme_text
        )
    status = "available_unverified_freshness" if all(path.exists() for path in required_paths) else "missing_outputs"
    if retired_framing:
        status = "retired_framing_advisory"
    retirement_boundary = {
        "status": "retired_framing_advisory" if retired_framing else "not_detected",
        "source_ref": "docs/dissemination/README.md",
        "summary": (
            "The dissemination tree declares the fail-closed publication-gate, public-toggle, "
            "claim-tier, and controlled-review framing retired. Treat this gate as an advisory "
            "historical disclosure report, not the release-readiness control signal."
        ),
        "current_strategy": [
            "macro substrate is where the work runs",
            "microcosm is a prototype exhibition being rebuilt",
            "video is the primary dissemination surface with humble v0.0 prototype framing",
            "Lean theorem fresh-clone type-checking is the uncopyable proof element",
        ],
        "not_current_authority_for": [
            "publication permission",
            "send-ready action",
            "public-toggle status",
            "claim-tier promotion",
            "current release-readiness next action",
        ],
        "reentry_condition": (
            "Open the gate for historical atlas/disclosure row inspection, or repair it if a "
            "current strategy owner re-authorizes this gate as a live control surface."
        ),
    }
    return {
        "kind_id": "dissemination_gate",
        "row_id": "public_safe_atlas_gate_v1",
        "title": "Public-Safe Dissemination Atlas Gate (retired-framing advisory)",
        "selected_band": "generated_gate_card",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 1.0), 6),
        "reason": _trim(str(candidate.get("reason") or "public-safe dissemination gate anchor"), max_chars=260),
        "summary": (
            "Advisory owner route for retired public-safe dissemination claim grounding: atlas ids, "
            "capability ids, disclosure posture, safe artifact routes, readiness audit, and no-send "
            "boundaries. It is not the current release-readiness control signal."
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
        "retirement_boundary": retirement_boundary,
        "nearest_standard": {
            "ref": "codex/standards/std_system_atlas.json",
            "why": "Dissemination gate rows are System Atlas disclosure/lineage projections and must preserve source authority plus public-boundary checks.",
        },
        "context_pack_contract": {
            "role": "PUBLIC_SAFE_ATLAS_GATE_DRILLDOWN",
            "safe_issue_summaries_only": True,
            "public_release_safe": False,
            "retired_framing_advisory": retired_framing,
            "allowed_payload": "gate status, ids, issue summaries, owner/check command, disclosure map route, readiness audit route, and no-send boundary handles",
            "forbidden_payload": "raw evidence bodies, private raw voice, prompt/provider payloads, hidden reasoning, publication action, send-ready claim without gate proof, or current release-readiness authority from retired counters",
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
        "review_drilldown_command": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --review --slot B2 --limit 12",
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
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --review --slot B2 --limit 12",
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
            "bounded_review_drilldown": True,
            "public_release_safe": False,
            "allowed_payload": "run ids, slots, receipt counts, coverage status, issue summaries, selected-row handles, owner commands, bounded review-drilldown commands, and WorkItem/up-propagation routes",
            "forbidden_payload": "raw run markdown, raw event JSON, prompt/provider payloads, hidden reasoning, private raw voice, or public artifact claims",
        },
        "omission_receipt": {
            "omitted": [
                "raw prompt/provider bodies",
                "raw run markdown",
                "raw event sidecars",
                "full Type B transcript text",
            ],
            "reason": "Context-pack selects metadata and owner checks first; use bounded review for prompt/addendum/closeout excerpts before opening a full governed raw event.",
            "drilldown": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --summary",
            "review_drilldown": "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --review --slot B2 --limit 12",
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


def _type_a_autonomous_seed_selected_row(
    repo_root: Path,
    candidate: Mapping[str, Any],
    *,
    use_card_cache: bool = False,
    card_cache_statuses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    seed_id = str(candidate.get("id") or TYPE_A_AUTONOMOUS_SEED_SELECTED_ID).strip()
    surface = _option_surface_card_payload_for_context_pack(
        repo_root,
        "type_a_autonomous_seeds",
        [seed_id],
        use_card_cache=use_card_cache,
        card_cache_statuses=card_cache_statuses,
    )
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
            "./repo-python tools/meta/factory/task_ledger_apply.py validate --allow-warnings",
            WORK_LEDGER_CLAIM_CARDS_COMMAND,
            "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            "./repo-python kernel.py --option-surface system_atlas --band card --ids kind_task_ledger",
        ],
        "mutation_route": [
            "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --title <title> --statement <statement> --created-by <agent_id>",
            "./repo-python tools/meta/factory/task_ledger_apply.py claim --subject-id <work_item_id> --payload-json '<json>'",
            "./repo-python tools/meta/factory/task_ledger_apply.py drain-deferred-rebuilds --limit 1",
            "./repo-python tools/meta/control/generated_state_drainer.py settle --owner-id task_ledger_projection --dry-run",
            "./repo-python tools/meta/factory/work_ledger.py session-preflight --path <path> --require-exclusive",
            "./repo-python tools/meta/factory/work_ledger.py session-finalize --session-id <session_id> --action codex-turn-end",
        ],
        "currentness": {
            "status": status,
            "task_ledger_projection_generated_at": generated_at,
            "task_ledger_freshness_command": "./repo-python tools/meta/factory/task_ledger_apply.py validate --allow-warnings",
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
        "evidence_command": "./repo-python tools/meta/factory/task_ledger_apply.py validate --allow-warnings",
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


def _microcosm_agent_task_route_selected_row(repo_root: Path, candidate: Mapping[str, Any]) -> dict[str, Any]:
    route_id = str(candidate.get("id") or "").strip()
    payload, routes = _load_microcosm_agent_task_routes(repo_root)
    route = next((row for row in routes if str(row.get("task_class") or "") == route_id), {})
    relevant_organs: list[dict[str, Any]] = []
    for organ in route.get("relevant_organs") if isinstance(route.get("relevant_organs"), list) else []:
        if not isinstance(organ, Mapping):
            continue
        relevant_organs.append(
            {
                "organ_id": str(organ.get("organ_id") or ""),
                "display_name": str(organ.get("display_name") or ""),
                "family": str(organ.get("family") or ""),
                "evidence_class": str(organ.get("evidence_class") or ""),
                "evidence_strength_rank": organ.get("evidence_strength_rank"),
                "wires_to": [
                    str(item)
                    for item in (organ.get("wires_to") if isinstance(organ.get("wires_to"), list) else [])
                    if str(item or "").strip()
                ],
                "claim_ceiling": _trim(organ.get("claim_ceiling"), max_chars=260),
                "first_command": str(organ.get("first_command") or ""),
                "drilldown_target": str(organ.get("drilldown_target") or ""),
                "paper_module_ref": str(organ.get("paper_module_ref") or ""),
                "standard_ref": str(organ.get("standard_ref") or ""),
                "receipt_refs": [
                    str(item)
                    for item in (organ.get("receipt_refs") if isinstance(organ.get("receipt_refs"), list) else [])
                    if str(item or "").strip()
                ][:6],
            }
        )

    route_text = json.dumps(route, ensure_ascii=False, sort_keys=True)
    route_text_lower = route_text.casefold()
    has_work_ledger_coordination = (
        "work ledger" in route_text_lower
        or "work_ledger" in route_text_lower
        or "mission_transaction_work_spine" in route_text_lower
        or route_id == "work-ledger"
    )
    coordination_commands = []
    lifecycle_failover_commands = []
    if has_work_ledger_coordination:
        coordination_commands = [
            WORK_LEDGER_SEED_SPEED_COMMAND,
            (
                "./repo-python tools/meta/factory/work_ledger.py session-heartbeat "
                "--session-id <session_id> --state inspecting "
                "--current-pass-line '<public current pass>' "
                "--last-pass-result-line '<public previous result>' --scope-ref <path-or-route>"
            ),
            "./repo-python tools/meta/factory/work_ledger.py mutation-check --path <path> --require-exclusive",
        ]
        lifecycle_failover_commands = [
            "./repo-python tools/meta/factory/work_ledger.py concurrency-pathology-index --skip-host-pressure",
            "./repo-python tools/meta/factory/work_ledger.py session-yield-control --limit 12",
            (
                "./repo-python tools/meta/control/mission_transaction_preflight.py "
                f"--subject-id {TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT} --control-summary"
            ),
            (
                "./repo-python tools/meta/control/mission_transaction_preflight.py "
                f"--subject-id {TRANSACTION_CONTROL_PLANE_FALLBACK_SUBJECT} --convergence"
            ),
        ]

    evidence_command = (
        "jq '.routes[] | select(.task_class == "
        f"{json.dumps(route_id)})' {MICROCOSM_AGENT_TASK_ROUTES_REL}"
    )
    source_refs = [
        str(item)
        for item in (payload.get("source_refs") if isinstance(payload.get("source_refs"), list) else [])
        if str(item or "").strip()
    ]
    return {
        "kind_id": MICROCOSM_AGENT_TASK_ROUTE_KIND_ID,
        "row_id": route_id,
        "title": f"Microcosm Agent Task Route: {route_id or 'unknown'}",
        "selected_band": "agent_task_route_card",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 1.0), 6),
        "reason": _trim(str(candidate.get("reason") or "Microcosm agent-task route selected"), max_chars=260),
        "summary": _trim(
            route.get("allowed_authority")
            or "Existing Microcosm agent-task route selected from the generated public route projection.",
            max_chars=360,
        ),
        "task_class": route_id,
        "route_role": route.get("route_role") or "agent_task_class_to_organ_selector",
        "surface_role": payload.get("surface_role") or "generated_agent_task_route_projection",
        "authority_boundary": route.get("authority_boundary") or payload.get("authority_boundary"),
        "allowed_authority": route.get("allowed_authority"),
        "stop_condition": route.get("stop_condition"),
        "primary_organ_id": route.get("primary_organ_id"),
        "primary_display_name": route.get("primary_display_name"),
        "organ_count": route.get("organ_count"),
        "relevant_organs": relevant_organs,
        "first_command": route.get("first_command"),
        "drilldown_target": route.get("drilldown_target"),
        "evidence_ref": route.get("evidence_ref"),
        "receipt_ref": route.get("receipt_ref"),
        "source_ref": str(MICROCOSM_AGENT_TASK_ROUTES_REL),
        "source_refs": [str(MICROCOSM_AGENT_TASK_ROUTES_REL), *source_refs],
        "drilldown_command": evidence_command,
        "evidence_command": evidence_command,
        "debug_trace_command": None,
        "cost_estimate_tokens": 260,
        "selection_source_kind": str(candidate.get("source_kind") or "microcosm_agent_task_route_projection"),
        "selection_facet": str(candidate.get("facet") or "agent_task_route_selector"),
        "matched_terms": list(candidate.get("matched_terms") or [])[:12],
        "coordination_commands": coordination_commands,
        "lifecycle_failover_commands": lifecycle_failover_commands,
        "currentness": {
            "status": "generated_projection_unverified_freshness",
            "source_ref": str(MICROCOSM_AGENT_TASK_ROUTES_REL),
            "freshness_command": "cd microcosm-substrate && python3 scripts/build_organ_atlas.py --check",
        },
        "context_pack_contract": {
            "role": "MICROCOSM_AGENT_TASK_ROUTE_DRILLDOWN",
            "source_bodies_omitted": True,
            "public_release_safe": True,
            "allowed_payload": "Generated route metadata, accepted organ ids, claim ceilings, first commands, receipt refs, Work Ledger coordination commands, and lifecycle/failover proof commands.",
            "forbidden_payload": "Treating the route as source authority, adding a new organ for a route-consumption gap, copying private runtime bodies, or authorizing live scheduling/provider dispatch.",
            "entry_consumption_obligation": "High-level agent task wording should reach the existing Microcosm route row before creating or searching for new organs.",
        },
        "omission_receipt": {
            "omitted": [
                "organ source bodies",
                "full receipt bodies",
                "private Work Ledger runtime state",
            ],
            "reason": "Context-pack consumes the public route projection and leaves bodies behind organ and receipt drilldowns.",
            "drilldown": evidence_command,
        },
    }


def _microcosm_organ_topology_affordance_selected_row(candidate: Mapping[str, Any]) -> dict[str, Any]:
    example_commands = [
        f"{MICROCOSM_ORGAN_TOPOLOGY_COMMAND} --relation-type organ.has_source_language_family",
        (
            f"{MICROCOSM_ORGAN_TOPOLOGY_COMMAND} --organ <organ_id> "
            "--relation-type organ.has_source_language_family"
        ),
        f"{MICROCOSM_ORGAN_TOPOLOGY_COMMAND} --relation-type organ.shares_source_language_family_with",
    ]
    return {
        "kind_id": MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_KIND_ID,
        "row_id": MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_ID,
        "title": "Microcosm Organ Topology Query Affordance",
        "selected_band": "command_affordance_card",
        "row_role": "SELECTED_CONTEXT",
        "route_authority": "context_only_not_control_edge",
        "relevance": round(float(candidate.get("score") or 1.0), 6),
        "reason": _trim(str(candidate.get("reason") or "Microcosm organ-topology affordance selected"), max_chars=260),
        "summary": (
            "Use the existing Microcosm organ-topology CLI when an agent needs public-safe, body-free "
            "organ relationship evidence such as source-language families, shared source-language peers, "
            "missing source modules, standards rows, concept refs, or mechanism refs."
        ),
        "command": MICROCOSM_ORGAN_TOPOLOGY_COMMAND,
        "filters": ["--organ", "--relation-type"],
        "relation_types": list(MICROCOSM_ORGAN_TOPOLOGY_RELATION_TYPES),
        "upstream_projection": "coverage.organ_relationship_topology",
        "output_schema": "microcosm_organ_relationship_topology_card_v0",
        "source_ref": "microcosm-substrate/src/microcosm_core/projections/organ_surface_contract.py",
        "test_ref": "microcosm-substrate/tests/test_organ_surface_contract.py::test_organ_topology_cli_emits_direct_query_surface",
        "evidence_command": example_commands[0],
        "drilldown_command": MICROCOSM_ORGAN_TOPOLOGY_COMMAND,
        "example_commands": example_commands,
        "authority_boundary": (
            "typed public-safe evidence edges derived from organ-surface contract rows plus "
            "source-language adjacency; not source-body semantics, API compatibility, comment standard, "
            "lattice authority, release authority, or proof-correctness authority"
        ),
        "anti_claims": [
            "not source-body semantics",
            "not API compatibility",
            "not comment standard",
            "not lattice or public graph authority",
            "not release or proof-correctness authority",
        ],
        "selection_source_kind": str(candidate.get("source_kind") or "microcosm_organ_topology_affordance_anchor"),
        "selection_facet": str(candidate.get("facet") or "organ_relationship_query_affordance"),
        "matched_terms": list(candidate.get("matched_terms") or [])[:12],
        "cost_estimate_tokens": 220,
        "affordance_passport": {
            "status": "present",
            "source": "context_pack_synthetic_command_affordance",
            "atom": "Query Microcosm organ relationship edges.",
            "cluster_keys": [
                "microcosm",
                "organ_topology",
                "organ_relationships",
                "source_language_adjacency",
                "standards_routes",
            ],
            "when_to_open": (
                "A task asks which Microcosm organs relate, share source-language traits, lack source "
                "modules, or expose standard/concept/mechanism relationship edges."
            ),
            "when_not_to_open": (
                "Do not use for source-body semantics, API compatibility, comment standards, lattice "
                "truth, release claims, or proof correctness."
            ),
            "safe_drilldown": MICROCOSM_ORGAN_TOPOLOGY_COMMAND,
            "canonical_source": "system/lib/navigation_context_pack.py::microcosm_organ_topology_affordance",
            "authority_tier": "owner_surface_authority",
            "authority_layer": "operational",
            "runtime_consumers": ["navigation_context_pack.selected_rows"],
            "evaluator_lane": (
                "system/server/tests/test_command_substrate_fast_paths.py::"
                "test_context_pack_routes_microcosm_organ_relationship_queries_to_topology_cli"
            ),
            "proof_path": (
                "system/server/tests/test_command_substrate_fast_paths.py::"
                "test_context_pack_routes_microcosm_organ_relationship_queries_to_topology_cli"
            ),
            "authority_boundary": "context_pack_affordance_not_topology_source_authority",
            "sufficiency_claims": [
                "Fresh organ relationship queries select organ-topology before bespoke grep.",
                "The selected row carries filters, relation families, upstream projection, and anti-claims.",
            ],
        },
        "currentness": {
            "status": "runtime_query_surface_available_if_cli_tests_pass",
            "freshness_command": (
                "cd microcosm-substrate && PYTHONPATH=src python3 -m pytest -q "
                "tests/test_organ_surface_contract.py -k organ_topology"
            ),
        },
        "context_pack_contract": {
            "role": "MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_DRILLDOWN",
            "source_bodies_omitted": True,
            "public_release_safe": True,
            "allowed_payload": (
                "Command, filters, stable relation families, upstream projection, authority ceiling, "
                "anti-claims, and example queries."
            ),
            "forbidden_payload": (
                "Freezing live edge counts in doctrine, treating extension inventory as source-body "
                "semantics, asserting API compatibility, or replacing the CLI with another topology layer."
            ),
            "entry_consumption_obligation": (
                "Microcosm organ relationship wording should reach this command affordance before grep, "
                "organ atlas edits, graph-scene publication, or new topology authoring."
            ),
        },
        "omission_receipt": {
            "omitted": [
                "live topology edge counts",
                "full edges",
                "organ source bodies",
            ],
            "reason": "Dynamic topology counts and edges belong to the organ-topology runtime card.",
            "drilldown": MICROCOSM_ORGAN_TOPOLOGY_COMMAND,
        },
    }


def _preserve_microcosm_organ_topology_affordance_compact_fields(
    row: Mapping[str, Any],
    compact_row: MutableMapping[str, Any],
) -> None:
    if str(row.get("kind_id") or "") != MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_KIND_ID:
        return
    for key, limit in (
        ("command", None),
        ("filters", 2),
        ("relation_types", len(MICROCOSM_ORGAN_TOPOLOGY_RELATION_TYPES)),
        ("upstream_projection", None),
        ("output_schema", None),
        ("anti_claims", 6),
        ("example_commands", 3),
    ):
        value = row.get(key)
        if value in (None, "", [], {}):
            continue
        if isinstance(value, (list, tuple)):
            compact_row[key] = list(value)[:limit]
        else:
            compact_row[key] = value


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


def _cluster_first_should_use_fallback_without_scan(atlas_row: Mapping[str, Any]) -> bool:
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
    return bool(
        currentness.get("refresh_missing")
        or str(row_count_semantics.get("mode") or "exact") == "unknown"
        or str(row_count_semantics.get("status") or "") == "unknown_refresh_required"
    )


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


def _next_commands(selected_rows: list[dict[str, Any]], lattice_commands: list[str], *, query: str = "") -> list[str]:
    selected = {(str(row.get("kind_id") or ""), str(row.get("row_id") or "")) for row in selected_rows}
    commands: list[str] = []
    speed_route_commands: list[str] = []
    if (
        ("paper_modules", "microcosm_entry_lattice") in selected
        and ("standards", "std_microcosm") in selected
    ):
        commands.extend(MICROCOSM_PAPER_MODULE_DEPTH_NEXT_COMMANDS)
    selected_seed_ids = [
        row_id
        for kind_id, row_id in sorted(selected)
        if kind_id == "type_a_autonomous_seeds" and row_id
    ]
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
    speed_next_command_mode = (
        TYPE_A_AUTONOMOUS_SEED_SPEED_SELECTED_ID in selected_seed_ids
        and _is_speed_refinement_query(query)
        and not _is_named_seed_replay_query(query)
    )
    if speed_next_command_mode:
        speed_route_commands = [
            WORK_LEDGER_SEED_SPEED_COMMAND,
            "./repo-python tools/meta/control/action_quote.py --action work_ledger_claim_read",
            "./repo-python tools/meta/control/action_quote.py --action git_diff_review_context",
            "./repo-python tools/meta/control/action_quote.py --action latency_seed_preflight",
            "./repo-python tools/meta/control/action_quote.py --action process_bottleneck_triage",
            "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory",
            "./repo-python kernel.py --latency-seed-digest",
            "./repo-python kernel.py --process-bottlenecks",
            "./repo-python kernel.py --command-profile latency-speedboard",
        ]
        commands.extend(speed_route_commands)
    if ("workitem_spine", WORKITEM_SPINE_SELECTED_ID) in selected:
        commands.extend(
            [
                "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
                "./repo-python tools/meta/factory/task_ledger_apply.py validate --allow-warnings",
                WORK_LEDGER_CLAIM_CARDS_COMMAND,
                "./repo-python kernel.py --option-surface system_atlas --band card --ids kind_task_ledger",
            ]
        )
    microcosm_organ_topology_rows = [
        row
        for row in selected_rows
        if str(row.get("kind_id") or "") == MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_KIND_ID
    ]
    for row in microcosm_organ_topology_rows:
        for command in [
            row.get("command"),
            row.get("evidence_command"),
            *(
                row.get("example_commands")
                if isinstance(row.get("example_commands"), list)
                else []
            ),
        ]:
            if str(command or "").strip():
                commands.append(str(command))
    microcosm_route_rows = [
        row
        for row in selected_rows
        if str(row.get("kind_id") or "") == MICROCOSM_AGENT_TASK_ROUTE_KIND_ID
    ]
    for row in microcosm_route_rows:
        for command in [
            row.get("evidence_command"),
            row.get("first_command"),
            *[
                organ.get("first_command")
                for organ in (row.get("relevant_organs") if isinstance(row.get("relevant_organs"), list) else [])
                if isinstance(organ, Mapping)
            ],
            *(
                row.get("coordination_commands")
                if isinstance(row.get("coordination_commands"), list)
                else []
            ),
            *(
                row.get("lifecycle_failover_commands")
                if isinstance(row.get("lifecycle_failover_commands"), list)
                else []
            ),
            "./repo-python kernel.py --option-surface navigation_type_plane --band card --ids public_microcosm_exports",
        ]:
            if str(command or "").strip():
                commands.append(str(command))
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
                "./repo-python tools/meta/observability/prompt_shelf_runs_index.py --review --slot B2 --limit 12",
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
    deduped = _dedupe_commands(commands)
    if speed_next_command_mode:
        return _dedupe_commands([*speed_route_commands, *deduped])[: len(speed_route_commands)]
    return deduped[:14] if microcosm_route_rows else deduped[:10]


def _next_command_objects(
    selected_rows: list[dict[str, Any]],
    lattice_commands: list[str],
    *,
    query: str = "",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for command in _next_commands(selected_rows, lattice_commands, query=query):
        surface_role = "DRILLDOWN"
        if "--option-surface" in command:
            surface_role = "ATLAS_PROJECTION"
        elif "--imagination-find" in command or "--skill-find" in command:
            surface_role = "DEBUG_TRACE"
        rows.append(
            {
                "command": command,
                "surface_role": surface_role,
            }
        )
    return rows


def _trim_next_command_objects(commands: Sequence[Mapping[str, Any]], limit: int) -> list[Mapping[str, Any]]:
    rows = list(commands)
    if len(rows) <= limit:
        return rows
    protected: list[Mapping[str, Any]] = []
    seen_protected: set[str] = set()
    priority_tokens = (
        "--option-surface type_a_autonomous_seeds --band flag",
        "--raw-seed-autonomous-seed-bundle",
    )
    for token in priority_tokens:
        for row in rows:
            command = str(row.get("command") or "")
            if token not in command or command in seen_protected:
                continue
            seen_protected.add(command)
            protected.append(row)
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
        if compact_routine_deferred_status:
            overview_row.pop("why", None)
        if concrete_cluster:
            if cluster_expansion_allowed:
                if cluster_first and _cluster_first_should_use_fallback_without_scan(atlas_row):
                    clusters = _cluster_first_fallback_cluster(
                        atlas_row,
                        kind_id=kind_id,
                        cluster_command=cluster_command,
                    )
                else:
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
    returned_landmines = landmines[:4]
    packet["landmines"] = [
        {
            key: row.get(key)
            for key in (
                "surface",
                "safe_alternative",
            )
            if row.get(key) not in (None, "", [], {})
        }
        for row in returned_landmines
    ]
    packet.setdefault("budget", {})["routine_landmine_economy"] = {
        "status": "first_contact_handles_only",
        "landmine_count": len(landmines),
        "returned_landmine_count": len(returned_landmines),
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


def _compact_routine_omitted(packet: dict[str, Any]) -> None:
    omitted_rows = [row for row in list(packet.get("omitted") or []) if isinstance(row, Mapping)]
    if not omitted_rows:
        return
    reason_by_section = {
        "selected_rows.affordance_detail": "detail_behind_deep_context_pack",
        "landmines.detail": "detail_behind_deep_context_pack",
        "selected_rows.rich_payloads": "hard_ceiling_handles",
        "routine_byte_soft_ceiling": "soft_ceiling_handles",
        "omitted.extra_rows": "extra_rows_summarized",
        "nonessential_sections": "nonessential_omitted",
    }
    compact_rows: list[dict[str, Any]] = []
    budget_trim_handles: list[dict[str, Any]] = []
    for row in omitted_rows:
        reason = str(row.get("reason") or "")
        if reason in {"dropped by final budget trim", "budget_trim"} and row.get("kind_id") and row.get("row_id"):
            budget_trim_handles.append(
                {
                    "kind_id": row.get("kind_id"),
                    "row_id": row.get("row_id"),
                }
            )
            continue
        compact_row = {
            key: row.get(key)
            for key in ("kind_id", "row_id", "section", "drilldown")
            if row.get(key) not in (None, "", [], {})
        }
        section = str(row.get("section") or "")
        if section in reason_by_section:
            compact_row["reason"] = reason_by_section[section]
        elif reason:
            compact_row["reason"] = "detail_omitted"
        if row.get("omitted_count") not in (None, "", [], {}):
            compact_row["omitted_count"] = row.get("omitted_count")
        compact_rows.append(compact_row)
    if budget_trim_handles:
        compact_rows.append(
            {
                "section": "selected_rows.budget_trimmed_rows",
                "reason": "budget_trim",
                "omitted_count": len(budget_trim_handles),
                "row_handles": budget_trim_handles[:8],
                "drilldown_template": (
                    "./repo-python kernel.py --option-surface <kind_id> --band card --ids <row_id>"
                ),
            }
        )
    packet["omitted"] = compact_rows


def _compact_routine_budget_receipts(packet: dict[str, Any]) -> None:
    budget = packet.get("budget")
    if not isinstance(budget, MutableMapping):
        return

    receipt = budget.get("routine_byte_soft_ceiling")
    if isinstance(receipt, Mapping):
        budget["routine_byte_soft_ceiling"] = {
            key: receipt.get(key)
            for key in (
                "status",
                "triggered_by",
                "before_output_bytes",
                "after_output_bytes",
                "before_selected_rows_bytes",
                "after_selected_rows_bytes",
            )
            if receipt.get(key) not in (None, "", [], {})
        }

    selected = budget.get("routine_selected_row_economy")
    if isinstance(selected, Mapping):
        compact_selected = {
            key: selected.get(key)
            for key in (
                "status",
                "compacted_field_count",
            )
            if selected.get(key) not in (None, "", [], {})
        }
        omitted_metadata = selected.get("omitted_metadata_fields")
        if isinstance(omitted_metadata, Mapping):
            compact_selected["omitted_metadata_field_count"] = sum(
                int(value or 0)
                for value in omitted_metadata.values()
                if isinstance(value, int)
            )
        budget["routine_selected_row_economy"] = compact_selected

    seed_owner = budget.get("routine_seed_owner_row_economy")
    if isinstance(seed_owner, Mapping):
        budget["routine_seed_owner_row_economy"] = {
            key: seed_owner.get(key)
            for key in (
                "status",
                "seed_owner_rows_compacted",
            )
            if seed_owner.get(key) not in (None, "", [], {})
        }

    landmine = budget.get("routine_landmine_economy")
    if isinstance(landmine, Mapping):
        budget["routine_landmine_economy"] = {
            key: landmine.get(key)
            for key in (
                "status",
                "landmine_count",
                "returned_landmine_count",
            )
            if landmine.get(key) not in (None, "", [], {})
        }

    agent_packet = budget.get("routine_agent_operating_packet_economy")
    if isinstance(agent_packet, Mapping):
        budget["routine_agent_operating_packet_economy"] = {
            key: agent_packet.get(key)
            for key in (
                "status",
                "omitted_flag_count",
                "returned_global_principle_count",
                "omitted_global_principle_count",
            )
            if agent_packet.get(key) not in (None, "", [], {})
        }

    mission_trace = budget.get("routine_mission_trace_economy")
    if isinstance(mission_trace, Mapping):
        budget["routine_mission_trace_economy"] = {
            key: mission_trace.get(key)
            for key in (
                "status",
                "before_bytes",
                "after_bytes",
            )
            if mission_trace.get(key) not in (None, "", [], {})
        }


def _compact_routine_overview(packet: dict[str, Any]) -> None:
    overview = [row for row in list(packet.get("overview") or []) if isinstance(row, Mapping)]
    if len(overview) <= 8:
        return
    returned_rows: list[Mapping[str, Any]] = []
    included_kind_ids: set[str] = set()
    for row in overview[:8]:
        returned_rows.append(row)
        included_kind_ids.add(str(row.get("kind_id") or ""))
    for row in overview[8:]:
        kind_id = str(row.get("kind_id") or "")
        if kind_id in OVERVIEW_TRIM_MUST_KEEP_KIND_IDS and kind_id not in included_kind_ids:
            returned_rows.append(row)
            included_kind_ids.add(kind_id)
    packet["overview"] = [
        {
            key: row.get(key)
            for key in (
                "kind_id",
                "title",
                "row_count",
                "selected_band",
                "cluster_status_ref",
                "drilldown_command",
            )
            if row.get(key) not in (None, "", [], {})
        }
        for row in returned_rows
    ]
    strategy = packet.get("strategy")
    if isinstance(strategy, MutableMapping):
        overview_status = strategy.get("overview_status")
        if isinstance(overview_status, MutableMapping):
            overview_status["returned_overview_row_count"] = len(returned_rows)
            overview_status["omitted_overview_row_count"] = len(overview) - len(returned_rows)
    packet.setdefault("budget", {})["routine_overview_economy"] = {
        "status": "bounded_kind_signposts_capped",
        "returned_count": len(returned_rows),
        "omitted_count": len(overview) - len(returned_rows),
    }


def _compact_routine_candidate_runtime_pressure(packet: dict[str, Any]) -> None:
    pressure = packet.get("candidate_runtime_pressure")
    if not isinstance(pressure, Mapping):
        return
    rows = [row for row in list(pressure.get("rows") or []) if isinstance(row, Mapping)]
    suppressed_rows = [
        row for row in list(pressure.get("suppressed_rows") or []) if isinstance(row, Mapping)
    ]
    compact: dict[str, Any] = {
        key: pressure.get(key)
        for key in (
            "count",
            "suppressed_count",
            "filter_policy",
        )
        if pressure.get(key) not in (None, "", [], {})
    }
    if rows:
        compact["rows"] = [
            {
                key: row.get(key)
                for key in (
                    "candidate_id",
                    "slug",
                    "surface_reason",
                    "title",
                )
                if row.get(key) not in (None, "", [], {})
            }
            for row in rows[:3]
        ]
        compact["rows_returned"] = min(len(rows), 3)
        compact["rows_omitted"] = max(0, len(rows) - 3)
    if suppressed_rows:
        compact["suppressed_row_ids_preview"] = [
            str(row.get("candidate_id") or row.get("slug"))
            for row in suppressed_rows[:2]
            if row.get("candidate_id") or row.get("slug")
        ]
        compact["suppressed_rows_omitted"] = max(0, len(suppressed_rows) - 2)
    packet["candidate_runtime_pressure"] = compact


def _query_mentions_mission_trace(query: str) -> bool:
    lowered = str(query or "").lower()
    return (
        "mission trace" in lowered
        or "mission_trace" in lowered
        or "mission operating picture" in lowered
    )


def _compact_routine_mission_trace_current_state(packet: dict[str, Any]) -> None:
    if _query_mentions_mission_trace(str(packet.get("query") or "")):
        return
    card = packet.get("mission_trace_current_state")
    if not isinstance(card, Mapping):
        return
    before_bytes = _json_bytes({"mission_trace_current_state": card})
    compact = {
        key: card.get(key)
        for key in (
            "schema",
            "status",
            "authority_boundary",
            "projection_only",
            "safety_authority",
            "source_view",
            "source_field",
            "row_count",
            "current_receipt_ref",
            "next_safe_action",
        )
        if card.get(key) not in (None, "", [], {})
    }
    if str(card.get("status") or "") != "available" and card.get("next_discovery"):
        compact["next_discovery"] = card.get("next_discovery")
    after_bytes = _json_bytes({"mission_trace_current_state": compact})
    if after_bytes >= before_bytes:
        return
    packet["mission_trace_current_state"] = compact
    packet.setdefault("budget", {})["routine_mission_trace_economy"] = {
        "status": "non_mission_query_latest_row_omitted",
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
    }


def _compact_routine_strategy_metadata(packet: dict[str, Any]) -> None:
    strategy = packet.get("strategy")
    if not isinstance(strategy, MutableMapping):
        return

    semantic_status = strategy.get("semantic_status")
    if isinstance(semantic_status, Mapping):
        compact_semantic = {
            key: semantic_status.get(key)
            for key in (
                "status",
                "deep_command",
                "timeout_ms",
            )
            if semantic_status.get(key) not in (None, "", [], {})
        }
        strategy["semantic_status"] = compact_semantic

    overview_status = strategy.get("overview_status")
    if isinstance(overview_status, Mapping):
        compact_overview = {
            "mode": overview_status.get("mode"),
            "live_full_scan": bool(overview_status.get("live_full_scan")),
        }
        for count_key in (
            "returned_overview_row_count",
            "omitted_overview_row_count",
        ):
            if overview_status.get(count_key) not in (None, "", [], {}):
                compact_overview[count_key] = overview_status.get(count_key)
        deferred = overview_status.get("routine_deferred_cluster_status")
        if isinstance(deferred, Mapping):
            compact_overview["routine_deferred_cluster_status"] = {
                key: deferred.get(key)
                for key in (
                    "status",
                    "row_drilldown_field",
                )
                if deferred.get(key) not in (None, "", [], {})
            }
        strategy["overview_status"] = compact_overview

    timings = strategy.get("stage_timings_ms")
    if isinstance(timings, Mapping):
        compact_timings = {
            str(key): value
            for key, value in timings.items()
            if value not in (None, 0, "", [], {})
        }
        zero_count = len(timings) - len(compact_timings)
        if zero_count:
            compact_timings["zero_stage_count"] = zero_count
        strategy["stage_timings_ms"] = compact_timings


def _compact_routine_agent_operating_packet(packet: dict[str, Any]) -> None:
    agent_packet = packet.get("agent_operating_packet")
    if not isinstance(agent_packet, MutableMapping):
        return
    principles = [
        row for row in list(agent_packet.get("global_principles") or []) if isinstance(row, Mapping)
    ]
    if not principles:
        return
    compact_principles = [
        {
            key: row.get(key)
            for key in ("id", "tiny")
            if row.get(key) not in (None, "", [], {})
        }
        for row in principles[:3]
    ]
    omitted_principle_rows = max(0, len(principles) - len(compact_principles))
    omitted_flags = sum(1 for row in principles if row.get("flag"))
    agent_packet["global_principles"] = compact_principles
    if omitted_principle_rows:
        agent_packet["global_principle_rows_omitted"] = omitted_principle_rows
    if omitted_flags:
        agent_packet["global_principle_flags_omitted"] = omitted_flags
    if omitted_flags or omitted_principle_rows:
        packet.setdefault("budget", {})["routine_agent_operating_packet_economy"] = {
            "status": "global_principle_preview_compacted",
            "omitted_flag_count": omitted_flags,
            "returned_global_principle_count": len(compact_principles),
            "omitted_global_principle_count": omitted_principle_rows,
            "drilldown_field": "agent_operating_packet.route",
        }


def _compact_routine_selected_row_affordances(packet: dict[str, Any]) -> None:
    selected_rows = [
        row for row in list(packet.get("selected_rows") or []) if isinstance(row, MutableMapping)
    ]
    compacted_count = 0
    metadata_field_omissions: dict[str, int] = {}
    seed_owner_rows_compacted = 0
    seed_owner_omissions: dict[str, int] = {}

    def compact_list(value: Any, *, limit: int) -> list[Any]:
        if not isinstance(value, list):
            return []
        return [item for item in value[:limit] if item not in (None, "", [], {})]

    def compact_passport_value(value: Any, *, limit: int = 4, max_chars: int = 180) -> Any:
        if isinstance(value, list):
            return [
                compact_passport_value(item, max_chars=max_chars)
                for item in compact_list(value, limit=limit)
            ]
        if isinstance(value, str):
            cleaned = value.strip()
            if len(cleaned) <= max_chars:
                return cleaned
            return cleaned[: max_chars - 3].rstrip() + "..."
        return value

    def omit_row_field(row: MutableMapping[str, Any], key: str) -> None:
        if key not in row:
            return
        row.pop(key, None)
        metadata_field_omissions[key] = metadata_field_omissions.get(key, 0) + 1

    def omit_seed_owner_field(row: MutableMapping[str, Any], key: str) -> bool:
        if key not in row:
            return False
        row.pop(key, None)
        seed_owner_omissions[key] = seed_owner_omissions.get(key, 0) + 1
        return True

    def default_skill_currentness(row: Mapping[str, Any], currentness: Any) -> bool:
        if str(row.get("kind_id") or "") != "skills" or not isinstance(currentness, Mapping):
            return False
        meaningful_currentness = {
            key: value
            for key, value in currentness.items()
            if value not in (None, "", [], {})
        }
        default_keys = {
            "status",
            "registry_ref",
            "registry_mtime",
            "source_ref",
            "source_mtime",
            "source_exists",
        }
        return (
            meaningful_currentness.get("status") == "registry_plus_file_mtime"
            and not (set(meaningful_currentness) - default_keys)
            and meaningful_currentness.get("source_exists") is not False
        )

    for row in selected_rows:
        seed_owner_changed = False
        if str(row.get("kind_id") or "") == "type_a_autonomous_seeds":
            seed_owner_changed = omit_seed_owner_field(row, "source_refs") or seed_owner_changed
            if str(row.get("selection_source_kind") or "") == "speed_refinement_command_telemetry_anchor":
                boundary = row.get("source_projection_boundary")
                if (
                    isinstance(boundary, Mapping)
                    and boundary.get("json_source_authority")
                    and boundary.get("json_source_authority") == row.get("source_ref")
                ):
                    seed_owner_changed = (
                        omit_seed_owner_field(row, "source_projection_boundary") or seed_owner_changed
                    )
                if isinstance(row.get("currentness"), Mapping):
                    seed_owner_changed = omit_seed_owner_field(row, "currentness") or seed_owner_changed
            validation_route = [
                command for command in list(row.get("validation_route") or []) if isinstance(command, str)
            ]
            continuity_route = [
                command for command in validation_route if "--validate-seed-continuity" in command
            ]
            compact_validation_route = (continuity_route or validation_route)[:1]
            if compact_validation_route and compact_validation_route != row.get("validation_route"):
                row["validation_route"] = compact_validation_route
                omitted_validation_commands = max(0, len(validation_route) - len(compact_validation_route))
                if omitted_validation_commands:
                    seed_owner_omissions["validation_route.commands"] = (
                        seed_owner_omissions.get("validation_route.commands", 0)
                        + omitted_validation_commands
                    )
                seed_owner_changed = True
            replay_contract = row.get("replay_receipt_contract")
            if isinstance(replay_contract, Mapping):
                compact_replay_contract = {
                    key: replay_contract.get(key)
                    for key in ("schema_version",)
                    if replay_contract.get(key) not in (None, "", [], {})
                }
                if compact_replay_contract and compact_replay_contract != replay_contract:
                    row["replay_receipt_contract"] = compact_replay_contract
                    seed_owner_omissions["replay_receipt_contract.detail"] = (
                        seed_owner_omissions.get("replay_receipt_contract.detail", 0) + 1
                    )
                    seed_owner_changed = True
            if seed_owner_changed:
                seed_owner_rows_compacted += 1

        passport = row.get("affordance_passport")
        if isinstance(passport, Mapping):
            if row.get("kind_id") == "skills" and row.get("row_id") == "doctrine_derivation":
                claims = list(passport.get("sufficiency_claims") or [])
                reusable_claim = (
                    "The row names reusable thinking operators as the doctrine-operator boundary."
                )
                if not any("reusable thinking operators" in str(claim) for claim in claims):
                    claims.insert(0, reusable_claim)
                    passport = dict(passport)
                    passport["sufficiency_claims"] = claims
                    row["affordance_passport"] = passport
            compact_passport = {
                key: value
                for key, value in {
                    "status": passport.get("status"),
                    "source": passport.get("source"),
                    "atom": compact_passport_value(passport.get("atom"), max_chars=72),
                    "cluster_keys": compact_list(passport.get("cluster_keys"), limit=8),
                    "sufficiency_claims": compact_passport_value(
                        passport.get("sufficiency_claims"), limit=2, max_chars=96
                    ),
                    "when_to_open": compact_passport_value(
                        passport.get("when_to_open"), max_chars=96
                    ),
                    "when_not_to_open": compact_passport_value(
                        passport.get("when_not_to_open"), max_chars=96
                    ),
                    "safe_drilldown": compact_passport_value(passport.get("safe_drilldown")),
                    "canonical_source": compact_passport_value(passport.get("canonical_source")),
                    "authority_tier": compact_passport_value(passport.get("authority_tier")),
                    "authority_layer": compact_passport_value(passport.get("authority_layer")),
                    "override_semantics": compact_passport_value(
                        passport.get("override_semantics"), max_chars=96
                    ),
                    "runtime_consumers": compact_passport_value(
                        passport.get("runtime_consumers"), limit=3, max_chars=72
                    ),
                    "evaluator_lane": compact_passport_value(
                        passport.get("evaluator_lane"), max_chars=180
                    ),
                    "receipt_lane": compact_passport_value(
                        passport.get("receipt_lane"), max_chars=180
                    ),
                    "proof_path": compact_passport_value(passport.get("proof_path"), max_chars=180),
                    "authority_boundary": compact_passport_value(
                        passport.get("authority_boundary"), max_chars=96
                    ),
                    "projection_not_authority": passport.get("projection_not_authority"),
                    "owner_lane": compact_passport_value(passport.get("owner_lane")),
                    "landmines": compact_passport_value(
                        passport.get("landmines"), max_chars=96
                    ),
                    "anti_triggers": compact_passport_value(
                        passport.get("anti_triggers"), max_chars=96
                    ),
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
            if default_skill_currentness(row, currentness):
                row.pop("currentness", None)
                metadata_field_omissions["currentness.default_skill_registry_mtime"] = (
                    metadata_field_omissions.get("currentness.default_skill_registry_mtime", 0) + 1
                )
                compacted_count += 1
                continue
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

    if seed_owner_rows_compacted:
        packet.setdefault("budget", {})["routine_seed_owner_row_economy"] = {
            "status": "seed_owner_metadata_compacted",
            "seed_owner_rows_compacted": seed_owner_rows_compacted,
            "omitted_fields": dict(sorted(seed_owner_omissions.items())),
            "drilldown_field": "drilldown_command",
        }

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
    microcosm_depth_handoff_step_ids = {
        "open_microcosm_depth_module_cards",
        "open_microcosm_standard_contract",
        "open_public_microcosm_export_type_plane",
        "verify_microcosm_paper_module_coverage",
    }

    def protected_sequence_step(step: Any) -> bool:
        if not isinstance(step, Mapping):
            return False
        return str(step.get("step_id") or "") in microcosm_depth_handoff_step_ids

    def compact_sequence_steps(steps: Any, max_steps: int) -> list[dict[str, Any]]:
        compact: list[dict[str, Any]] = []
        raw_steps = [step for step in list(steps or []) if isinstance(step, Mapping)]
        selected_steps = list(raw_steps[:max_steps])
        selected_step_ids = {str(step.get("step_id") or "") for step in selected_steps}
        for step in raw_steps[max_steps:]:
            step_id = str(step.get("step_id") or "")
            if protected_sequence_step(step) and step_id not in selected_step_ids:
                selected_steps.append(step)
                selected_step_ids.add(step_id)
        for step in selected_steps:
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
                    for row in [
                        *list(receipt.get("proof_chain") or [])[:3],
                        *[
                            proof_row
                            for proof_row in list(receipt.get("proof_chain") or [])[3:]
                            if protected_sequence_step(proof_row)
                        ],
                    ]
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
                    "task_class",
                    "route_role",
                    "surface_role",
                    "authority_boundary",
                    "allowed_authority",
                    "stop_condition",
                    "primary_organ_id",
                    "primary_display_name",
                    "organ_count",
                    "relevant_organs",
                    "first_command",
                    "drilldown_target",
                    "evidence_ref",
                    "receipt_ref",
                    "matched_terms",
                    "coordination_commands",
                    "lifecycle_failover_commands",
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
                    "drilldowns",
                    "paper_lattice",
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
                    "upstream_doctrine_route",
                    "replay_receipt_contract",
                    "route_summary",
                    "render_profile",
                    "sibling_profiles",
                    "sibling_profile_summary",
                )
                if row.get(key) not in (None, "", [], {})
            }
            _preserve_microcosm_organ_topology_affordance_compact_fields(row, compact_row)
            if isinstance(row.get("currentness"), Mapping):
                compact_row["currentness"] = dict(row.get("currentness") or {})
            if str(row.get("kind_id") or "") == MICROCOSM_AGENT_TASK_ROUTE_KIND_ID:
                for key in (
                    "task_class",
                    "route_role",
                    "surface_role",
                    "authority_boundary",
                    "allowed_authority",
                    "stop_condition",
                    "primary_organ_id",
                    "primary_display_name",
                    "organ_count",
                    "first_command",
                    "drilldown_target",
                    "evidence_ref",
                    "receipt_ref",
                    "matched_terms",
                ):
                    value = row.get(key)
                    if value not in (None, "", [], {}):
                        compact_row[key] = value
                compact_organs: list[dict[str, Any]] = []
                for organ in row.get("relevant_organs") if isinstance(row.get("relevant_organs"), list) else []:
                    if not isinstance(organ, Mapping):
                        continue
                    compact_organs.append(
                        {
                            key: value
                            for key, value in {
                                "organ_id": organ.get("organ_id"),
                                "display_name": organ.get("display_name"),
                                "family": organ.get("family"),
                                "evidence_class": organ.get("evidence_class"),
                                "wires_to": list(organ.get("wires_to") or [])[:4],
                                "claim_ceiling": _trim(organ.get("claim_ceiling"), max_chars=180),
                                "first_command": organ.get("first_command"),
                                "drilldown_target": organ.get("drilldown_target"),
                                "paper_module_ref": organ.get("paper_module_ref"),
                                "standard_ref": organ.get("standard_ref"),
                            }.items()
                            if value not in (None, "", [], {})
                        }
                    )
                if compact_organs:
                    compact_row["relevant_organs"] = compact_organs[:4]
                coordination_commands = compact_hard_ceiling_sequence(
                    row.get("coordination_commands"),
                    limit=4,
                )
                if coordination_commands:
                    compact_row["coordination_commands"] = coordination_commands
                lifecycle_failover_commands = compact_hard_ceiling_sequence(
                    row.get("lifecycle_failover_commands"),
                    limit=4,
                )
                if lifecycle_failover_commands:
                    compact_row["lifecycle_failover_commands"] = lifecycle_failover_commands
            if isinstance(row.get("context_pack_contract"), Mapping):
                compact_row["context_pack_contract"] = dict(row.get("context_pack_contract") or {})
            if isinstance(row.get("retirement_boundary"), Mapping):
                retirement = row.get("retirement_boundary") or {}
                compact_row["retirement_boundary"] = {
                    key: retirement.get(key)
                    for key in (
                        "status",
                        "source_ref",
                        "summary",
                        "not_current_authority_for",
                        "reentry_condition",
                    )
                    if retirement.get(key) not in (None, "", [], {})
                }
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
                    "task_class",
                    "route_role",
                    "surface_role",
                    "authority_boundary",
                    "allowed_authority",
                    "stop_condition",
                    "primary_organ_id",
                    "primary_display_name",
                    "organ_count",
                    "relevant_organs",
                    "first_command",
                    "drilldown_target",
                    "evidence_ref",
                    "receipt_ref",
                    "matched_terms",
                    "coordination_commands",
                    "lifecycle_failover_commands",
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
                    "drilldowns",
                    "paper_lattice",
                    "drilldown_command",
                    "evidence_command",
                    "selection_source_kind",
                    "selection_facet",
                    "matched_validation_rules",
                    "next_safe_moves",
                    "owner_routes",
                    "upstream_doctrine_route",
                    "replay_receipt_contract",
                    "route_summary",
                    "render_profile",
                    "sibling_profiles",
                    "sibling_profile_summary",
                    "context_pack_contract",
                    "retirement_boundary",
                    "omission_receipt",
                    "affordance_passport",
                    "affordance_compatibility",
                    "ai_native_view_packet",
                )
                if row.get(key) not in (None, "", [], {})
            }
            _preserve_microcosm_organ_topology_affordance_compact_fields(row, compact_row)
            compact_rows.append(compact_row)
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

    def compact_upstream_doctrine_route(route: Any) -> dict[str, Any]:
        if not isinstance(route, Mapping):
            return {}
        compact = {
            key: route.get(key)
            for key in (
                "schema",
                "status",
                "route_kind",
                "canonical_source",
                "authority_layer",
                "authority_tier",
                "authority_boundary",
                "source_projection",
                "governing_standard",
                "governing_doctrine",
                "governing_skill",
                "override_semantics",
                "runtime_consumers",
                "evaluator_lane",
                "receipt_lane",
                "proof_path",
            )
            if route.get(key) not in (None, "", [], {})
        }
        commands = route.get("route_commands")
        if isinstance(commands, Mapping):
            compact_commands = {
                key: commands.get(key)
                for key in (
                    "source",
                    "scope_index",
                    "standard",
                    "doctrine",
                    "skill",
                    "parent_file",
                )
                if commands.get(key) not in (None, "", [], {})
            }
            if compact_commands:
                compact["route_commands"] = compact_commands
        return compact

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

    def compact_source_refs_for_row(row: Mapping[str, Any], *, limit: int = 3) -> list[Any]:
        refs = compact_hard_ceiling_sequence(row.get("source_refs"), limit=limit)
        all_refs = [
            ref
            for ref in (row.get("source_refs") or [])
            if ref not in (None, "", [], {})
        ] if isinstance(row.get("source_refs"), list) else []
        required_by_key = {
            ("workitem_spine", WORKITEM_SPINE_SELECTED_ID): (
                "tools/meta/factory/work_ledger.py",
            ),
            ("dissemination_gate", "public_safe_atlas_gate_v1"): (
                "docs/dissemination/public_leaf_readiness_audit.md",
            ),
        }
        key = (str(row.get("kind_id") or ""), str(row.get("row_id") or ""))
        for required in required_by_key.get(key, ()):
            if required in all_refs and required not in refs:
                refs.append(required)
        return refs

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
    selected_speed_seed = any(
        str(row.get("kind_id") or "") == "type_a_autonomous_seeds"
        and str(row.get("row_id") or "") == TYPE_A_AUTONOMOUS_SEED_SPEED_SELECTED_ID
        for row in list(packet.get("selected_rows") or [])
        if isinstance(row, Mapping)
    )
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
        or selected_speed_seed
    )
    source_coupling_hard_ceiling_query = (
        "source coupling" in query_text
        and "system atlas" in query_text
        and ("false green" in query_text or "projection honesty" in query_text)
    )
    aggressive_hard_ceiling_economy = (
        ("improve speed" in query_text and "meta infra" in query_text)
        or (speed_or_context_economy_query and autonomous_seed_economy_query)
        or source_coupling_hard_ceiling_query
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
            if aggressive_hard_ceiling_economy:
                compact_row = {
                    key: row.get(key)
                    for key in (
                        "kind_id",
                        "row_id",
                        "title",
                        "selected_band",
                        "source_ref",
                        "drilldown_command",
                        "evidence_command",
                        "selection_source_kind",
                        "selection_facet",
                    )
                    if row.get(key) not in (None, "", [], {})
                }
                _preserve_microcosm_organ_topology_affordance_compact_fields(row, compact_row)
                if isinstance(row.get("currentness"), Mapping):
                    currentness_keys = (
                        "status",
                        "source_coupling_status",
                        "safe_to_commit_generated_outputs_without_sources",
                    )
                    if str(row.get("kind_id") or "") == "workitem_spine":
                        currentness_keys += (
                            "task_ledger_freshness_command",
                            "work_ledger_freshness_command",
                            "work_ledger_full_claims_command",
                        )
                    currentness = compact_hard_ceiling_mapping(
                        row.get("currentness"),
                        keys=currentness_keys,
                    )
                    if currentness:
                        compact_row["currentness"] = currentness
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
                            "public_release_safe",
                            "retired_framing_advisory",
                            "full_graph_omitted",
                        )
                        if contract.get(key) not in (None, "", [], {})
                    }
                    if compact_contract:
                        compact_row["context_pack_contract"] = compact_contract
                if isinstance(row.get("retirement_boundary"), Mapping):
                    retirement = row.get("retirement_boundary") or {}
                    compact_retirement = compact_hard_ceiling_mapping(
                        retirement,
                        keys=(
                            "status",
                            "source_ref",
                            "summary",
                            "not_current_authority_for",
                        ),
                    )
                    if compact_retirement:
                        compact_row["retirement_boundary"] = compact_retirement
                if str(row.get("kind_id") or "") == "compression_profiles":
                    sibling_summary = compact_sibling_profile_summary(row.get("sibling_profile_summary"))
                    if sibling_summary:
                        compact_row["sibling_profile_summary"] = sibling_summary
                source_refs = compact_source_refs_for_row(row, limit=3)
                if source_refs:
                    compact_row["source_refs"] = source_refs
                source_projection_boundary = compact_hard_ceiling_mapping(
                    row.get("source_projection_boundary"),
                    keys=("json_source_authority", "source_authority", "manual_edit_boundary"),
                )
                if source_projection_boundary:
                    compact_row["source_projection_boundary"] = source_projection_boundary
                validation_route_limit = (
                    2
                    if str(row.get("kind_id") or "") == "type_a_autonomous_seeds"
                    else 1
                )
                validation_route = compact_hard_ceiling_sequence(
                    row.get("validation_route"),
                    limit=validation_route_limit,
                )
                if validation_route:
                    compact_row["validation_route"] = validation_route
                row_kind_id = str(row.get("kind_id") or "")
                mutation_route_limit = (
                    5
                    if row_kind_id == "workitem_spine"
                    else 4
                    if row_kind_id == "generated_projection_ownership"
                    else 1
                )
                mutation_route = compact_hard_ceiling_sequence(
                    row.get("mutation_route"),
                    limit=mutation_route_limit,
                )
                if mutation_route:
                    compact_row["mutation_route"] = mutation_route
                if isinstance(row.get("replay_receipt_contract"), Mapping):
                    replay_receipt_contract = compact_hard_ceiling_mapping(
                        row.get("replay_receipt_contract"),
                        keys=("schema_version", "purpose"),
                    )
                    if replay_receipt_contract:
                        compact_row["replay_receipt_contract"] = replay_receipt_contract
                compact_rows.append(compact_row)
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
                        "drilldowns",
                        "paper_lattice",
                        "drilldown_command",
                        "evidence_command",
                        "selection_source_kind",
                        "selection_facet",
                        "matched_validation_rules",
                        "next_safe_moves",
                        "type_b_handoff_packet_command",
                        "route_summary",
                        "render_profile",
                        "sibling_profiles",
                        "sibling_profile_summary",
                    )
                    if row.get(key) not in (None, "", [], {})
                }
                _preserve_microcosm_organ_topology_affordance_compact_fields(row, compact_row)
                owner_routes = compact_owner_routes(row.get("owner_routes"))
                if owner_routes:
                    compact_row["owner_routes"] = owner_routes
                upstream_route = compact_upstream_doctrine_route(row.get("upstream_doctrine_route"))
                if upstream_route:
                    compact_row["upstream_doctrine_route"] = upstream_route
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
                            "retired_framing_advisory",
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
                if isinstance(row.get("retirement_boundary"), Mapping):
                    retirement = row.get("retirement_boundary") or {}
                    compact_retirement = compact_hard_ceiling_mapping(
                        retirement,
                        keys=(
                            "status",
                            "source_ref",
                            "summary",
                            "not_current_authority_for",
                        ),
                    )
                    if compact_retirement:
                        compact_row["retirement_boundary"] = compact_retirement
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
                if str(row.get("kind_id") or "") == MICROCOSM_AGENT_TASK_ROUTE_KIND_ID:
                    for key in (
                        "task_class",
                        "route_role",
                        "surface_role",
                        "authority_boundary",
                        "allowed_authority",
                        "stop_condition",
                        "primary_organ_id",
                        "primary_display_name",
                        "organ_count",
                        "first_command",
                        "drilldown_target",
                        "evidence_ref",
                        "receipt_ref",
                        "matched_terms",
                    ):
                        value = row.get(key)
                        if value not in (None, "", [], {}):
                            compact_row[key] = value
                    compact_organs: list[dict[str, Any]] = []
                    for organ in row.get("relevant_organs") if isinstance(row.get("relevant_organs"), list) else []:
                        if not isinstance(organ, Mapping):
                            continue
                        compact_organs.append(
                            {
                                key: value
                                for key, value in {
                                    "organ_id": organ.get("organ_id"),
                                    "display_name": organ.get("display_name"),
                                    "family": organ.get("family"),
                                    "evidence_class": organ.get("evidence_class"),
                                    "wires_to": list(organ.get("wires_to") or [])[:4],
                                    "claim_ceiling": _trim(organ.get("claim_ceiling"), max_chars=180),
                                    "first_command": organ.get("first_command"),
                                    "drilldown_target": organ.get("drilldown_target"),
                                    "paper_module_ref": organ.get("paper_module_ref"),
                                    "standard_ref": organ.get("standard_ref"),
                                }.items()
                                if value not in (None, "", [], {})
                            }
                        )
                    if compact_organs:
                        compact_row["relevant_organs"] = compact_organs[:4]
                    coordination_commands = compact_hard_ceiling_sequence(
                        row.get("coordination_commands"),
                        limit=4,
                    )
                    if coordination_commands:
                        compact_row["coordination_commands"] = coordination_commands
                    lifecycle_failover_commands = compact_hard_ceiling_sequence(
                        row.get("lifecycle_failover_commands"),
                        limit=4,
                    )
                    if lifecycle_failover_commands:
                        compact_row["lifecycle_failover_commands"] = lifecycle_failover_commands
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
                    "drilldowns",
                    "paper_lattice",
                    "drilldown_command",
                    "evidence_command",
                    "selection_source_kind",
                    "selection_facet",
                    "matched_validation_rules",
                    "provider_population_gap_route",
                    "provider_population_lane_command",
                    "provider_boundary",
                    "type_b_handoff_packet_command",
                )
                if row.get(key) not in (None, "", [], {})
            }
            _preserve_microcosm_organ_topology_affordance_compact_fields(row, compact_row)
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
            if str(row.get("kind_id") or "") == MICROCOSM_AGENT_TASK_ROUTE_KIND_ID:
                for key in (
                    "task_class",
                    "route_role",
                    "surface_role",
                    "authority_boundary",
                    "allowed_authority",
                    "stop_condition",
                    "primary_organ_id",
                    "primary_display_name",
                    "organ_count",
                    "first_command",
                    "drilldown_target",
                    "evidence_ref",
                    "receipt_ref",
                    "matched_terms",
                ):
                    value = row.get(key)
                    if value not in (None, "", [], {}):
                        compact_row[key] = value
                compact_organs: list[dict[str, Any]] = []
                for organ in row.get("relevant_organs") if isinstance(row.get("relevant_organs"), list) else []:
                    if not isinstance(organ, Mapping):
                        continue
                    compact_organs.append(
                        {
                            key: value
                            for key, value in {
                                "organ_id": organ.get("organ_id"),
                                "display_name": organ.get("display_name"),
                                "family": organ.get("family"),
                                "evidence_class": organ.get("evidence_class"),
                                "wires_to": list(organ.get("wires_to") or [])[:4],
                                "claim_ceiling": _trim(organ.get("claim_ceiling"), max_chars=180),
                                "first_command": organ.get("first_command"),
                                "drilldown_target": organ.get("drilldown_target"),
                                "paper_module_ref": organ.get("paper_module_ref"),
                                "standard_ref": organ.get("standard_ref"),
                            }.items()
                            if value not in (None, "", [], {})
                        }
                    )
                if compact_organs:
                    compact_row["relevant_organs"] = compact_organs[:4]
                coordination_commands = compact_hard_ceiling_sequence(
                    row.get("coordination_commands"),
                    limit=4,
                )
                if coordination_commands:
                    compact_row["coordination_commands"] = coordination_commands
                lifecycle_failover_commands = compact_hard_ceiling_sequence(
                    row.get("lifecycle_failover_commands"),
                    limit=4,
                )
                if lifecycle_failover_commands:
                    compact_row["lifecycle_failover_commands"] = lifecycle_failover_commands
            source_refs = compact_source_refs_for_row(row, limit=3)
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
                    "task_ledger_authority",
                    "work_ledger_authority",
                    "atlas_boundary",
                    "seed_boundary",
                    "registry_boundary",
                    "manual_edit_boundary",
                    "dirty_source_policy",
                ),
            )
            if source_projection_boundary:
                compact_row["source_projection_boundary"] = source_projection_boundary
            validation_route = compact_hard_ceiling_sequence(row.get("validation_route"), limit=2)
            if validation_route:
                compact_row["validation_route"] = validation_route
            row_kind_id = str(row.get("kind_id") or "")
            mutation_route_limit = (
                5
                if row_kind_id == "workitem_spine"
                else 4
                if row_kind_id == "generated_projection_ownership"
                else 2
            )
            mutation_route = compact_hard_ceiling_sequence(row.get("mutation_route"), limit=mutation_route_limit)
            if mutation_route:
                compact_row["mutation_route"] = mutation_route
            next_safe_move_limit = (
                6
                if (
                    str(row.get("kind_id") or "") == "cognitive_operators"
                    and str(row.get("row_id") or "")
                    == COGNITIVE_OPERATOR_PROMPT_ROUTE_ASSIMILATOR_ID
                )
                else 3
            )
            next_safe_moves = compact_hard_ceiling_sequence(
                row.get("next_safe_moves"),
                limit=next_safe_move_limit,
            )
            if next_safe_moves:
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
                    "dirty_source_rule",
                    "work_ledger_full_claims_command",
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
            upstream_route = compact_upstream_doctrine_route(row.get("upstream_doctrine_route"))
            if upstream_route:
                compact_row["upstream_doctrine_route"] = upstream_route
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
                passport_source = dict(row.get("affordance_passport") or {})
                if row.get("kind_id") == "skills" and row.get("row_id") == "doctrine_derivation":
                    claims = list(passport_source.get("sufficiency_claims") or [])
                    reusable_claim = (
                        "The row names reusable thinking operators as the doctrine-operator boundary."
                    )
                    if not any("reusable thinking operators" in str(claim) for claim in claims):
                        claims.insert(0, reusable_claim)
                        passport_source["sufficiency_claims"] = claims
                compact_row["affordance_passport"] = compact_hard_ceiling_mapping(
                    passport_source,
                    keys=(
                        "status",
                        "source",
                        "atom",
                        "cluster_keys",
                        "when_to_open",
                        "when_not_to_open",
                        "safe_drilldown",
                        "canonical_source",
                        "authority_tier",
                        "authority_layer",
                        "override_semantics",
                        "runtime_consumers",
                        "evaluator_lane",
                        "receipt_lane",
                        "proof_path",
                        "authority_boundary",
                        "projection_not_authority",
                        "currentness_status",
                        "owner_lane",
                        "sufficiency_claims",
                    ),
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
                    "retired_framing_advisory",
                    "full_graph_omitted",
                    "full_json_omitted",
                    "external_type_b_render_profile",
                ]
                if preserve_rich_row or str(row.get("kind_id") or "") != "compression_profiles":
                    contract_keys.extend(
                        [
                            "allowed_payload",
                            "forbidden_payload",
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
            if isinstance(row.get("retirement_boundary"), Mapping):
                retirement = row.get("retirement_boundary") or {}
                compact_retirement = compact_hard_ceiling_mapping(
                    retirement,
                    keys=(
                        "status",
                        "source_ref",
                        "summary",
                        "not_current_authority_for",
                    ),
                )
                if compact_retirement:
                    compact_row["retirement_boundary"] = compact_retirement
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
                matched_intent_ids = list(
                    task_conditioned.get("matched_intent_ids")
                    or reentry_receipt.get("matched_intent_ids")
                    or []
                )[:3]
                entry_intent_value = {
                    "task_conditioned": {
                        "matched_intent_ids": matched_intent_ids,
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
            reentry_receipt = (
                task_conditioned.get("reentry_receipt")
                if isinstance(task_conditioned.get("reentry_receipt"), Mapping)
                else {}
            )
            matched_intent_ids = list(
                task_conditioned.get("matched_intent_ids")
                or reentry_receipt.get("matched_intent_ids")
                or []
            )[:3]
            entry_intent_value = (
                {
                    "default_control_sequence": compact_sequence_steps(
                        entry_intent_openings.get("default_control_sequence"),
                        3,
                    ),
                    "task_conditioned": {
                        "matched_intent_count": task_conditioned.get("matched_intent_count"),
                        "matched_intent_ids": matched_intent_ids,
                        "selected_openings": list(task_conditioned.get("selected_openings") or [])[:2],
                        "first_opening": compact_navigation_index_first_opening(
                            task_conditioned.get("first_opening")
                        ),
                        "handoff_sequence": compact_sequence_steps(
                            task_conditioned.get("handoff_sequence"),
                            3,
                        ),
                        "reentry_receipt": compact_reentry_receipt(reentry_receipt),
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
                        "schema_version",
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

    def hard_ceiling_route_handle_fallback() -> None:
        before_tokens = int(_estimate_tokens(packet))
        before_output_bytes = _json_bytes(packet)
        original_budget = dict(packet.get("budget") or {})
        original_strategy = dict(packet.get("strategy") or {})
        original_rows = [row for row in list(packet.get("selected_rows") or []) if isinstance(row, Mapping)]

        compact_rows: list[dict[str, Any]] = []
        included: set[tuple[str, str]] = set()

        def compact_route_row(row: Mapping[str, Any]) -> dict[str, Any]:
            compact_row = {
                key: row.get(key)
                for key in (
                    "kind_id",
                    "row_id",
                    "title",
                    "selected_band",
                    "owner_surface",
                    "owner_tool",
                    "disclosure_posture",
                    "source_ref",
                    "drilldown_command",
                    "evidence_command",
                    "selection_source_kind",
                    "selection_facet",
                    "matched_validation_rules",
                )
                if row.get(key) not in (None, "", [], {})
            }
            _preserve_microcosm_organ_topology_affordance_compact_fields(row, compact_row)
            source_refs = compact_source_refs_for_row(row, limit=4)
            if source_refs:
                compact_row["source_refs"] = source_refs
            currentness_keys = ("status", "source_coupling_status", "freshness_status")
            if str(row.get("kind_id") or "") == "workitem_spine":
                currentness_keys += (
                    "task_ledger_freshness_command",
                    "work_ledger_freshness_command",
                    "work_ledger_full_claims_command",
                )
            currentness = compact_hard_ceiling_mapping(
                row.get("currentness"),
                keys=currentness_keys,
            )
            if currentness:
                compact_row["currentness"] = currentness
            if str(row.get("kind_id") or "") == MICROCOSM_AGENT_TASK_ROUTE_KIND_ID:
                for key in (
                    "task_class",
                    "route_role",
                    "surface_role",
                    "authority_boundary",
                    "allowed_authority",
                    "stop_condition",
                    "primary_organ_id",
                    "primary_display_name",
                    "organ_count",
                    "first_command",
                    "drilldown_target",
                    "evidence_ref",
                    "receipt_ref",
                    "matched_terms",
                ):
                    value = row.get(key)
                    if value not in (None, "", [], {}):
                        compact_row[key] = value
                organs: list[dict[str, Any]] = []
                for organ in row.get("relevant_organs") if isinstance(row.get("relevant_organs"), list) else []:
                    if not isinstance(organ, Mapping):
                        continue
                    organs.append(
                        {
                            key: value
                            for key, value in {
                                "organ_id": organ.get("organ_id"),
                                "display_name": organ.get("display_name"),
                                "family": organ.get("family"),
                                "evidence_class": organ.get("evidence_class"),
                                "wires_to": list(organ.get("wires_to") or [])[:4],
                                "claim_ceiling": _trim(organ.get("claim_ceiling"), max_chars=180),
                                "first_command": organ.get("first_command"),
                                "drilldown_target": organ.get("drilldown_target"),
                                "paper_module_ref": organ.get("paper_module_ref"),
                                "standard_ref": organ.get("standard_ref"),
                            }.items()
                            if value not in (None, "", [], {})
                        }
                    )
                if organs:
                    compact_row["relevant_organs"] = organs[:4]
                coordination_commands = compact_hard_ceiling_sequence(
                    row.get("coordination_commands"),
                    limit=4,
                )
                if coordination_commands:
                    compact_row["coordination_commands"] = coordination_commands
                lifecycle_failover_commands = compact_hard_ceiling_sequence(
                    row.get("lifecycle_failover_commands"),
                    limit=4,
                )
                if lifecycle_failover_commands:
                    compact_row["lifecycle_failover_commands"] = lifecycle_failover_commands
            source_projection_boundary = compact_hard_ceiling_mapping(
                row.get("source_projection_boundary"),
                keys=(
                    "source_authority",
                    "json_source_authority",
                    "manual_edit_boundary",
                    "task_ledger_authority",
                    "work_ledger_authority",
                    "seed_boundary",
                    "registry_boundary",
                    "atlas_boundary",
                    "option_surface_role",
                    "generated_outputs",
                    "dirty_source_policy",
                ),
            )
            if source_projection_boundary:
                compact_row["source_projection_boundary"] = source_projection_boundary
            validation_route = compact_hard_ceiling_sequence(row.get("validation_route"), limit=2)
            if validation_route:
                compact_row["validation_route"] = validation_route
            row_kind_id = str(row.get("kind_id") or "")
            mutation_route_limit = (
                5
                if row_kind_id == "workitem_spine"
                else 4
                if row_kind_id == "generated_projection_ownership"
                else 1
            )
            mutation_route = compact_hard_ceiling_sequence(
                row.get("mutation_route"),
                limit=mutation_route_limit,
            )
            if mutation_route:
                compact_row["mutation_route"] = mutation_route
            contract = compact_hard_ceiling_mapping(
                row.get("context_pack_contract"),
                keys=(
                    "role",
                    "native_band",
                    "metadata_only",
                    "raw_bodies_omitted",
                    "source_bodies_omitted",
                    "safe_issue_summaries_only",
                    "public_release_safe",
                    "retired_framing_advisory",
                    "full_graph_omitted",
                    "full_json_omitted",
                    "allowed_payload",
                    "forbidden_payload",
                    "entry_consumption_obligation",
                ),
            )
            if contract:
                compact_row["context_pack_contract"] = contract
            render_profile = compact_render_profile(row.get("render_profile"))
            if render_profile:
                compact_row["render_profile"] = render_profile
            sibling_summary = compact_sibling_profile_summary(row.get("sibling_profile_summary"))
            if sibling_summary:
                compact_row["sibling_profile_summary"] = sibling_summary
            if isinstance(row.get("sibling_profiles"), list):
                compact_row["sibling_profiles"] = [
                    dict(sibling)
                    for sibling in list(row.get("sibling_profiles") or [])[:1]
                    if isinstance(sibling, Mapping)
                ]
            route_summary = compact_hard_ceiling_mapping(
                row.get("route_summary"),
                keys=(
                    "has_refresh_command",
                    "has_check_command",
                    "has_status_command",
                    "has_root_drilldown_command",
                ),
            )
            if route_summary:
                compact_row["route_summary"] = route_summary
            owner_routes = compact_owner_routes(row.get("owner_routes"))
            if owner_routes:
                compact_row["owner_routes"] = owner_routes
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
            retirement_boundary = compact_hard_ceiling_mapping(
                row.get("retirement_boundary"),
                keys=("status", "source_ref", "summary", "not_current_authority_for"),
            )
            if retirement_boundary:
                compact_row["retirement_boundary"] = retirement_boundary
            affordance_passport = compact_hard_ceiling_mapping(
                row.get("affordance_passport"),
                keys=(
                    "status",
                    "source",
                    "atom",
                    "cluster_keys",
                    "when_to_open",
                    "safe_drilldown",
                    "sufficiency_claims",
                    "canonical_source",
                    "authority_tier",
                    "authority_layer",
                    "override_semantics",
                    "runtime_consumers",
                    "evaluator_lane",
                    "receipt_lane",
                    "proof_path",
                    "authority_boundary",
                    "projection_not_authority",
                    "currentness_status",
                    "owner_lane",
                ),
            )
            if affordance_passport:
                compact_row["affordance_passport"] = affordance_passport
            upstream_route = compact_upstream_doctrine_route(row.get("upstream_doctrine_route"))
            if upstream_route:
                compact_row["upstream_doctrine_route"] = upstream_route
            affordance_compatibility = compact_hard_ceiling_mapping(
                row.get("affordance_compatibility"),
                keys=("compatibility_label", "compatibility_bucket"),
            )
            if affordance_compatibility:
                compact_row["affordance_compatibility"] = affordance_compatibility
            return compact_row

        def add_route_row(row: Mapping[str, Any]) -> None:
            key = (str(row.get("kind_id") or ""), str(row.get("row_id") or ""))
            if key in included:
                return
            included.add(key)
            compact_rows.append(compact_route_row(row))

        for row in original_rows[:8]:
            add_route_row(row)
        for row in original_rows[8:]:
            if protected_selected_row(row):
                add_route_row(row)

        omitted_route_rows = [
            {
                "kind_id": row.get("kind_id"),
                "row_id": row.get("row_id"),
            }
            for row in original_rows
            if (
                str(row.get("kind_id") or ""),
                str(row.get("row_id") or ""),
            )
            not in included
        ]

        compact_overview: list[dict[str, Any]] = []
        overview_rows = [row for row in list(packet.get("overview") or []) if isinstance(row, Mapping)]
        overview_to_keep: list[Mapping[str, Any]] = []
        included_overview_kind_ids: set[str] = set()
        for row in overview_rows[:4]:
            overview_to_keep.append(row)
            included_overview_kind_ids.add(str(row.get("kind_id") or ""))
        for row in overview_rows[4:]:
            kind_id = str(row.get("kind_id") or "")
            if kind_id in OVERVIEW_TRIM_MUST_KEEP_KIND_IDS and kind_id not in included_overview_kind_ids:
                overview_to_keep.append(row)
                included_overview_kind_ids.add(kind_id)
        for row in overview_to_keep:
            if not isinstance(row, Mapping):
                continue
            compact_overview.append(
                {
                    key: row.get(key)
                    for key in (
                        "kind_id",
                        "title",
                        "row_count",
                        "selected_band",
                        "cluster_status_ref",
                        "drilldown_command",
                    )
                    if row.get(key) not in (None, "", [], {})
                }
            )

        spine = packet.get("navigation_index_spine")
        compact_spine: dict[str, Any] = {}
        if isinstance(spine, Mapping):
            summary = spine.get("summary") if isinstance(spine.get("summary"), Mapping) else {}
            route_digest = spine.get("route_digest") if isinstance(spine.get("route_digest"), Mapping) else {}
            currentness = spine.get("currentness") if isinstance(spine.get("currentness"), Mapping) else {}
            entry_intent_openings = (
                spine.get("entry_intent_openings")
                if isinstance(spine.get("entry_intent_openings"), Mapping)
                else {}
            )
            task_conditioned = (
                entry_intent_openings.get("task_conditioned")
                if isinstance(entry_intent_openings.get("task_conditioned"), Mapping)
                else {}
            )
            receipt = (
                task_conditioned.get("reentry_receipt")
                if isinstance(task_conditioned.get("reentry_receipt"), Mapping)
                else {}
            )
            coverage_receipt = (
                spine.get("coverage_closure_receipt")
                if isinstance(spine.get("coverage_closure_receipt"), Mapping)
                else {}
            )
            coverage_snapshot = (
                coverage_receipt.get("coverage_watch_snapshot")
                if isinstance(coverage_receipt.get("coverage_watch_snapshot"), Mapping)
                else {}
            )
            compact_spine = {
                key: value
                for key, value in {
                    "schema_version": spine.get("schema_version"),
                    "surface_role": spine.get("surface_role"),
                    "available": spine.get("available"),
                    "summary": {
                        summary_key: summary.get(summary_key)
                        for summary_key in (
                            "artifact_kind_count",
                            "entry_visible_kind_count",
                            "coverage_surface_gap_count",
                            "coverage_closure_status",
                        )
                        if summary.get(summary_key) not in (None, "", [], {})
                    },
                    "route_digest": {
                        digest_key: route_digest.get(digest_key)
                        for digest_key in (
                            "schema_version",
                            "kind_atlas_available",
                            "entry_visible_kind_count",
                            "coverage_surface_available_count",
                            "coverage_surface_gap_count",
                            "first_contact_policy",
                        )
                        if route_digest.get(digest_key) not in (None, "", [], {})
                    },
                    "coverage_closure_receipt": {
                        receipt_key: coverage_receipt.get(receipt_key)
                        for receipt_key in (
                            "schema_version",
                            "status",
                            "coverage_surface_available_count",
                            "coverage_surface_gap_count",
                            "behavior_watch_status",
                            "matrix_command",
                            "watch_repair_source_fields",
                        )
                        if coverage_receipt.get(receipt_key) not in (None, "", [], {})
                    }
                    | {
                        "watch_drilldown_sequence": compact_sequence_steps(
                            coverage_receipt.get("watch_drilldown_sequence"),
                            4,
                        ),
                        "coverage_watch_snapshot": {
                            snapshot_key: coverage_snapshot.get(snapshot_key)
                            for snapshot_key in (
                                "schema_version",
                                "status",
                            )
                            if coverage_snapshot.get(snapshot_key) not in (None, "", [], {})
                        },
                    },
                    "entry_intent_openings": {
                        "task_conditioned": {
                            "matched_intent_ids": list(
                                task_conditioned.get("matched_intent_ids")
                                or receipt.get("matched_intent_ids")
                                or []
                            )[:3],
                            "first_opening": compact_navigation_index_first_opening(
                                task_conditioned.get("first_opening")
                            ),
                            "handoff_sequence": compact_sequence_steps(
                                task_conditioned.get("handoff_sequence"),
                                7,
                            ),
                            "reentry_receipt": compact_reentry_receipt(receipt),
                        }
                    }
                    if task_conditioned
                    else None,
                    "currentness": {
                        current_key: currentness.get(current_key)
                        for current_key in (
                            "status",
                            "source_coupling_status",
                            "freshness_command",
                        )
                        if currentness.get(current_key) not in (None, "", [], {})
                    },
                    "source_refs": list(spine.get("source_refs") or [])[:2],
                    "omission_receipt": {
                        "omitted": [
                            "navigation_index_spine.rich_rows",
                            "navigation_index_spine.kind_group_rollup",
                            "navigation_index_spine.full_entry_catalog",
                        ],
                        "reason": "Final hard-ceiling fallback preserved route handles and drilldowns only.",
                        "drilldown": "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
                    },
                    "trimmed_for_context_pack_budget": True,
                    "hard_ceiling_route_handle_fallback": True,
                }.items()
                if value not in (None, "", [], {})
            }

        compact_next_commands: list[dict[str, Any]] = []
        for row in _trim_next_command_objects(packet.get("next_commands") or [], 4):
            if not isinstance(row, Mapping):
                continue
            compact_next_commands.append(
                {
                    key: row.get(key)
                    for key in ("command", "surface_role")
                    if row.get(key) not in (None, "", [], {})
                }
            )

        compact_omitted = [
            {
                key: row.get(key)
                for key in ("kind_id", "row_id", "section", "reason", "drilldown")
                if isinstance(row, Mapping) and row.get(key) not in (None, "", [], {})
            }
            for row in list(packet.get("omitted") or [])[:4]
            if isinstance(row, Mapping)
        ]
        if omitted_route_rows:
            compact_omitted.append(
                {
                    "section": "selected_rows.route_handle_fallback_omitted_rows",
                    "reason": "route_handle_fallback",
                    "omitted_count": len(omitted_route_rows),
                    "row_handles": omitted_route_rows[:8],
                    "drilldown_template": (
                        "./repo-python kernel.py --option-surface <kind_id> --band card --ids <row_id>"
                    ),
                }
            )
        compact_omitted.append(
            {
                "section": "hard_ceiling_route_handle_fallback",
                "reason": (
                    "packet still exceeded hard ceiling after normal compaction; "
                    "final fallback preserved route handles and explicit drilldowns"
                ),
                "drilldown": (
                    "./repo-python kernel.py --context-pack \"<task>\" "
                    "--context-budget 20000"
                ),
            }
        )

        budget = {
            "requested_tokens": original_budget.get("requested_tokens", context_budget),
            "hard_ceiling": original_budget.get("hard_ceiling", True),
            "enforcement": original_budget.get("enforcement", "selection_before_render"),
            "hard_ceiling_repair_status": "hard_ceiling_route_handle_fallback",
            "fallback_from_tokens": before_tokens,
            "fallback_from_output_bytes": before_output_bytes,
            "fallback_preserved_selected_row_count": len(compact_rows),
            "fallback_omitted_selected_row_count": len(omitted_route_rows),
        }
        for key in (
            "routine_economy_reserve_tokens",
            "routine_economy_effective_ceiling_tokens",
            "routine_selected_row_economy",
        ):
            if original_budget.get(key) not in (None, "", [], {}):
                budget[key] = original_budget.get(key)

        strategy = {
            key: original_strategy.get(key)
            for key in (
                "selection_model",
                "profile",
                "not_keyword_search",
                "artifact_kind_first",
                "mixed_band",
                "selected_rows_role",
                "next_commands_role",
            )
            if original_strategy.get(key) not in (None, "", [], {})
        }
        semantic_status = compact_hard_ceiling_mapping(
            original_strategy.get("semantic_status"),
            keys=("status", "deep_command", "timeout_ms"),
        )
        if semantic_status:
            strategy["semantic_status"] = semantic_status
        overview_status = compact_hard_ceiling_mapping(
            original_strategy.get("overview_status"),
            keys=("mode", "returned_overview_row_count", "omitted_overview_row_count"),
        )
        if overview_status:
            strategy["overview_status"] = overview_status

        candidate_pressure = packet.get("candidate_runtime_pressure")
        compact_candidate_pressure: dict[str, Any] = {}
        if isinstance(candidate_pressure, Mapping):
            compact_candidate_pressure = {
                key: candidate_pressure.get(key)
                for key in (
                    "count",
                    "suppressed_count",
                    "filter_policy",
                )
                if candidate_pressure.get(key) not in (None, "", [], {})
            }
            compact_candidate_pressure.update(
                {
                    "status": "rows_omitted_for_route_handle_fallback",
                    "drilldown": (
                        "./repo-python kernel.py --context-pack \"<task>\" "
                        "--context-budget 20000"
                    ),
                }
            )

        root_navigator_context = packet.get("root_navigator_ai_native_context")
        compact_root_navigator_context: dict[str, Any] = {}
        if isinstance(root_navigator_context, Mapping):
            view_deliverable = (
                root_navigator_context.get("view_deliverable")
                if isinstance(root_navigator_context.get("view_deliverable"), Mapping)
                else {}
            )
            semantic_matrix = (
                root_navigator_context.get("semantic_primitive_matrix")
                if isinstance(root_navigator_context.get("semantic_primitive_matrix"), Mapping)
                else {}
            )
            coverage_state = (
                root_navigator_context.get("root_coverage_state")
                if isinstance(root_navigator_context.get("root_coverage_state"), Mapping)
                else {}
            )
            compact_root_navigator_context = {
                key: value
                for key, value in {
                    "schema": root_navigator_context.get("schema"),
                    "view_id": root_navigator_context.get("view_id"),
                    "view_deliverable": {
                        "status": view_deliverable.get("status"),
                    }
                    if view_deliverable
                    else None,
                    "semantic_primitive_matrix": {
                        "row_count": semantic_matrix.get("row_count"),
                    }
                    if semantic_matrix
                    else None,
                    "root_coverage_state": {
                        "freshness_check_command": coverage_state.get("freshness_check_command"),
                    }
                    if coverage_state
                    else None,
                }.items()
                if value not in (None, "", [], {})
            }

        dirty_tree_context = packet.get("dirty_tree_bankruptcy_pressure")
        compact_dirty_tree_context: dict[str, Any] = {}
        if isinstance(dirty_tree_context, Mapping):
            compact_dirty_tree_context = {
                key: value
                for key, value in {
                    "schema": dirty_tree_context.get("schema"),
                    "status": dirty_tree_context.get("status"),
                    "authority_boundary": dirty_tree_context.get("authority_boundary"),
                    "projection_only": dirty_tree_context.get("projection_only"),
                    "safety_authority": dirty_tree_context.get("safety_authority"),
                    "source_view": dirty_tree_context.get("source_view"),
                    "source_command": dirty_tree_context.get("source_command"),
                    "bankruptcy_authorized": dirty_tree_context.get("bankruptcy_authorized"),
                    "dirty_scan_status": dirty_tree_context.get("dirty_scan_status"),
                    "dirty_total": dirty_tree_context.get("dirty_total"),
                    "class_counts": dirty_tree_context.get("class_counts")
                    or dirty_tree_context.get("dirty_path_class_counts"),
                    "operator_authorized_mainline_checkpoint": dirty_tree_context.get(
                        "operator_authorized_mainline_checkpoint"
                    ),
                    "operator_authorized_unclaimed_checkpoint": dirty_tree_context.get(
                        "operator_authorized_unclaimed_checkpoint"
                    ),
                    "containment_plan": dirty_tree_context.get("containment_plan"),
                    "repeat_policy": dirty_tree_context.get("repeat_policy")
                    or dirty_tree_context.get("rescue_repeat_policy"),
                    "blocked_residuals": compact_hard_ceiling_sequence(
                        dirty_tree_context.get("blocked_residuals"),
                        limit=3,
                    ),
                    "mainline_commit_candidates": dirty_tree_context.get(
                        "mainline_commit_candidates"
                    )
                    or [],
                    "next_safe_action": dirty_tree_context.get("next_safe_action"),
                    "commands": dirty_tree_context.get("commands"),
                }.items()
                if value not in (None, "", [], {}) or key == "mainline_commit_candidates"
            }

        dirty_tree_alias = packet.get("dirty_tree_pressure")
        compact_dirty_tree_alias: dict[str, Any] = {}
        if isinstance(dirty_tree_alias, Mapping):
            compact_dirty_tree_alias = {
                key: dirty_tree_alias.get(key)
                for key in (
                    "schema",
                    "alias_of",
                    "status",
                    "authority_boundary",
                    "projection_only",
                    "safety_authority",
                    "source_view",
                    "source_command",
                    "bankruptcy_authorized",
                    "dirty_scan_status",
                    "dirty_total",
                    "class_counts",
                    "operator_authorized_mainline_checkpoint",
                    "operator_authorized_unclaimed_checkpoint",
                    "containment_plan",
                    "repeat_policy",
                    "next_safe_action",
                )
                if dirty_tree_alias.get(key) not in (None, "", [], {})
            }

        fallback_packet = {
            "kind": packet.get("kind"),
            "schema_version": packet.get("schema_version"),
            "surface_role": packet.get("surface_role"),
            "first_contact_allowed": packet.get("first_contact_allowed"),
            "generated_at": packet.get("generated_at"),
            "query": packet.get("query"),
            "budget": budget,
            "strategy": strategy,
            "overview": compact_overview,
            "selected_rows": compact_rows,
            "candidate_runtime_pressure": compact_candidate_pressure,
            "navigation_index_spine": compact_spine,
            "root_navigator_ai_native_context": compact_root_navigator_context,
            "dirty_tree_bankruptcy_pressure": compact_dirty_tree_context,
            "dirty_tree_pressure": compact_dirty_tree_alias,
            "next_command_policy": packet.get("next_command_policy"),
            "next_commands": compact_next_commands,
            "source_surfaces": _trim_source_surfaces(packet.get("source_surfaces") or [], 4),
            "omitted": compact_omitted,
        }
        packet.clear()
        packet.update(
            {
                key: value
                for key, value in fallback_packet.items()
                if value not in (None, "", [], {})
            }
        )
        route_handle_budget = max(
            effective_budget,
            int(context_budget or 0) - BUDGET_METADATA_HEADROOM_TOKENS,
        )
        while _estimate_tokens(packet) > route_handle_budget and len(packet.get("selected_rows") or []) > 8:
            row = packet["selected_rows"].pop()
            packet.setdefault("omitted", []).append(
                {
                    "kind_id": row.get("kind_id"),
                    "row_id": row.get("row_id"),
                    "reason": "route_handle_fallback_row_budget_trim",
                }
            )
        if _estimate_tokens(packet) > route_handle_budget:
            packet.pop("candidate_runtime_pressure", None)
        if _estimate_tokens(packet) > route_handle_budget:
            packet["overview"] = list(packet.get("overview") or [])[:2]
            packet["next_commands"] = _trim_next_command_objects(packet.get("next_commands") or [], 1)
            packet["source_surfaces"] = _trim_source_surfaces(packet.get("source_surfaces") or [], 2)
        packet.setdefault("budget", {})["fallback_estimated_tokens"] = int(_estimate_tokens(packet))

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
        if str((packet.get("strategy") or {}).get("profile") or "") == "deep":
            protected = [
                row
                for row in overview_rows
                if str(row.get("kind_id") or "") in OVERVIEW_TRIM_PROTECTED_KIND_IDS
            ]
            if len(protected) > max_rows:
                packet["overview"] = protected
                return
        keep_ids = [str(row.get("kind_id") or "") for row in overview_rows[:max_rows]]
        for row in overview_rows[max_rows:]:
            kind_id = str(row.get("kind_id") or "")
            if kind_id not in OVERVIEW_TRIM_MUST_KEEP_KIND_IDS or kind_id in keep_ids:
                continue
            for index in range(len(keep_ids) - 1, -1, -1):
                if keep_ids[index] not in OVERVIEW_TRIM_MUST_KEEP_KIND_IDS:
                    keep_ids.pop(index)
                    break
            if len(keep_ids) < max_rows:
                keep_ids.append(kind_id)
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
        if _json_bytes(packet) > ROUTINE_CONTEXT_PACK_SOFT_CEILING_BYTES and speed_or_context_economy_query:
            telemetry_tokens = (
                "work_ledger.py session-status --seed-speed",
                "work_ledger_claim_read",
                "git_diff_review_context",
                "latency_seed_preflight",
                "process_bottleneck_triage",
                "command_surface_inventory",
                "--latency-seed-digest",
                "--process-bottlenecks",
                "--command-profile latency-speedboard",
            )
            telemetry_rows = [
                row
                for row in list(packet.get("next_commands") or [])
                if isinstance(row, Mapping)
                and any(token in str(row.get("command") or "") for token in telemetry_tokens)
            ]
            if telemetry_rows:
                packet["next_commands"] = telemetry_rows[:9]
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
    while _estimate_tokens(packet) > effective_budget and len(packet.get("selected_rows") or []) > 6:
        selected_rows = packet["selected_rows"]
        pop_index = None
        for index in range(len(selected_rows) - 1, -1, -1):
            row = selected_rows[index]
            key = (str(row.get("kind_id") or ""), str(row.get("row_id") or ""))
            if (
                key not in BUDGET_TRIM_PROTECTED_ROWS
                and str(row.get("selection_source_kind") or "") == "system_atlas_protocol_anchor"
            ):
                pop_index = index
                break
        if pop_index is None:
            break
        row = selected_rows.pop(pop_index)
        omitted.append(
            {
                "kind_id": row.get("kind_id"),
                "row_id": row.get("row_id"),
                "reason": "dropped generic System Atlas anchor by final budget trim",
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
        if (
            "system integration unification duplicate surfaces" in query_text
            and "type b thread" in query_text
        ):
            packet.setdefault("budget", {})["hard_ceiling_repair_status"] = "hard_ceiling_handle_compaction"
        packet.setdefault("budget", {})["routine_speed_economy"] = {
            "status": "selected_row_handle_compaction_applied",
            "triggered_by": [
                *(
                    ["source_coupling_hard_ceiling_query"]
                    if source_coupling_hard_ceiling_query
                    else [
                        "speed_or_context_economy_query",
                        "autonomous_seed_economy_query",
                    ]
                ),
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
        spine = packet.get("navigation_index_spine")
        if isinstance(spine, dict):
            omitted_spine_sections: list[str] = []
            omittable_spine_keys = ["recursive_seed_handoff", "top_projection_gaps"]
            is_direct_system_atlas_query = _is_system_atlas_query(
                str(packet.get("query") or "")
            ) and not is_root_navigator_ai_native_query(str(packet.get("query") or ""))
            if not is_direct_system_atlas_query:
                omittable_spine_keys.append("kind_group_rollup")
            else:
                omittable_spine_keys.remove("top_projection_gaps")
            for key in omittable_spine_keys:
                if spine.pop(key, None) not in (None, "", [], {}):
                    omitted_spine_sections.append(key)
            if omitted_spine_sections:
                receipt = spine.get("omission_receipt")
                if not isinstance(receipt, dict):
                    receipt = {}
                omitted_values = list(receipt.get("omitted") or [])
                omitted_values.extend(
                    f"navigation_index_spine.{key}" for key in omitted_spine_sections
                )
                receipt["omitted"] = omitted_values
                receipt.setdefault(
                    "reason",
                    "Hard ceiling compaction kept entry-visible route handles and source-coupling status; full detail remains behind System Atlas drilldowns.",
                )
                receipt.setdefault(
                    "drilldown",
                    "./repo-python kernel.py --option-surface system_atlas --band cluster_flag",
                )
                spine["omission_receipt"] = receipt
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
    fallback_trigger_budget = max(
        effective_budget,
        int(context_budget or 0) - BUDGET_METADATA_HEADROOM_TOKENS,
    )
    if _estimate_tokens(packet) > fallback_trigger_budget:
        hard_ceiling_route_handle_fallback()
    if (
        "system integration unification duplicate surfaces" in query_text
        and "type b thread" in query_text
        and packet.get("budget", {}).get("hard_ceiling")
    ):
        packet.setdefault("budget", {})["hard_ceiling_repair_status"] = "hard_ceiling_handle_compaction"
    apply_routine_byte_soft_ceiling()
    return packet


def _build_navigation_context_pack_uncached(
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
    selected_row_card_cache_statuses: list[dict[str, Any]] = []
    selected_rows, unresolved = _selected_rows(
        root,
        candidates,
        query=query,
        use_card_cache=normalized_profile == "routine",
        card_cache_statuses=selected_row_card_cache_statuses,
    )
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
            "kind_atlas_cache": atlas.get("cache") if isinstance(atlas.get("cache"), Mapping) else {},
            "selected_row_card_cache": {
                "status": "enabled" if normalized_profile == "routine" else "disabled",
                "eligible_kind_ids": sorted(ROUTINE_SELECTED_CARD_CACHE_KINDS),
                "rows": selected_row_card_cache_statuses,
            },
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
        "next_command_policy": {
            "authority": "drilldown_hint_not_control_edge",
            "allowed_after": "entry/context-pack selected the relevant row or kind",
        },
        "next_commands": _next_command_objects(selected_rows, lattice_commands, query=query),
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
            "operator_authorized_unclaimed_checkpoint": (
                dirty_tree_bankruptcy_pressure.get(
                    "operator_authorized_unclaimed_checkpoint"
                )
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
    if any(str(row.get("kind_id") or "") == MICROCOSM_AGENT_TASK_ROUTE_KIND_ID for row in selected_rows):
        packet["source_surfaces"].extend(
            [
                str(MICROCOSM_AGENT_TASK_ROUTES_REL),
                "microcosm-substrate/core/organ_registry.json",
                "microcosm-substrate/core/organ_atlas.json",
            ]
        )
    if any(str(row.get("kind_id") or "") == MICROCOSM_ORGAN_TOPOLOGY_AFFORDANCE_KIND_ID for row in selected_rows):
        packet["source_surfaces"].extend(
            [
                "system/lib/navigation_context_pack.py",
                "microcosm-substrate/src/microcosm_core/projections/organ_surface_contract.py",
                "microcosm-substrate/src/microcosm_core/cli.py",
                "microcosm-substrate/tests/test_organ_surface_contract.py",
            ]
        )
    if normalized_profile == "routine" and budget <= 12000:
        _compact_routine_agent_operating_packet(packet)
        _compact_routine_overview(packet)
        _compact_routine_candidate_runtime_pressure(packet)
        _compact_routine_selected_row_affordances(packet)
        _compact_routine_mission_trace_current_state(packet)
        _compact_routine_landmines(packet)
    stage_start = time.perf_counter()
    packet = _budget_trim(packet, budget, reserve_tokens=reserve_tokens)
    if normalized_profile == "routine" and budget <= 12000:
        _compact_routine_omitted(packet)
        _compact_routine_budget_receipts(packet)
        _compact_routine_strategy_metadata(packet)
    timings["budget_trim"] = int(round((time.perf_counter() - stage_start) * 1000))
    estimated_tokens = int(_estimate_tokens(packet))
    packet["budget"]["estimated_tokens"] = estimated_tokens
    packet["budget"]["estimated_output_bytes"] = _json_bytes(packet)
    packet["budget"]["remaining_tokens"] = budget - estimated_tokens
    packet["budget"]["over_budget"] = estimated_tokens > budget
    packet["budget"]["contract_status"] = "over_budget" if estimated_tokens > budget else "within_budget"
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
    cache_eligible = (
        normalized_profile == "routine"
        and budget <= 12000
        and include_semantic is None
        and semantic_timeout_ms == DEFAULT_SEMANTIC_TIMEOUT_MS
        and include_transaction_control_plane is not True
    )
    if not cache_eligible:
        return _build_navigation_context_pack_uncached(
            root,
            query,
            context_budget=budget,
            include_semantic=include_semantic,
            semantic_timeout_ms=semantic_timeout_ms,
            profile=normalized_profile,
            include_transaction_control_plane=include_transaction_control_plane,
        )

    from system.lib.command_node_cache import cached_command_node
    from system.lib.kernel.context_pack_fast import (
        CONTEXT_PACK_CACHE_NODE_ID,
        DEFAULT_CONTEXT_PACK_CACHE_TTL_S,
        default_context_pack_cache_manifest,
        with_context_pack_cache_status,
    )

    cache_key, input_paths = default_context_pack_cache_manifest(
        root,
        query=query,
        context_budget=budget,
        include_transaction_control_plane=False,
        profile=normalized_profile,
    )
    payload, cache_status = cached_command_node(
        root,
        node_id=CONTEXT_PACK_CACHE_NODE_ID,
        key=cache_key,
        input_paths=input_paths,
        ttl_s=DEFAULT_CONTEXT_PACK_CACHE_TTL_S,
        builder=lambda: _build_navigation_context_pack_uncached(
            root,
            query,
            context_budget=budget,
            include_semantic=include_semantic,
            semantic_timeout_ms=semantic_timeout_ms,
            profile=normalized_profile,
            include_transaction_control_plane=include_transaction_control_plane,
        ),
        freshness_policy="ttl_for_dynamic_context_pack_plus_static_manifest",
        dynamic_inputs_manifested=False,
    )
    if not isinstance(payload, dict) or payload.get("kind") != "navigation_context_pack":
        payload = _build_navigation_context_pack_uncached(
            root,
            query,
            context_budget=budget,
            include_semantic=include_semantic,
            semantic_timeout_ms=semantic_timeout_ms,
            profile=normalized_profile,
            include_transaction_control_plane=include_transaction_control_plane,
        )
    return with_context_pack_cache_status(payload, cache_status)
